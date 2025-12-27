from __future__ import annotations

import asyncio
import contextlib
import json
import os
import socket
import time
import uuid
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Dict, Iterable, Optional, Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from .models import (
	ProvideChoiceConfig,
	ProvideChoiceRequest,
	ProvideChoiceResponse,
	ValidationError,
	apply_configuration,
	cancelled_response,
	normalize_response,
	timeout_response,
	TRANSPORT_WEB,
	VALID_TRANSPORTS,
)


# Section: Constants
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_DEFAULT_WEB_HOST = "127.0.0.1"
_DEFAULT_WEB_PORT = 17863
_SESSION_RETENTION_SECONDS = 600


# Section: Utility Functions
def _resolve_port() -> int:
	"""Resolve the target port, allowing override via CHOICE_WEB_PORT."""
	raw = os.environ.get("CHOICE_WEB_PORT")
	if raw:
		try:
			return int(raw)
		except ValueError:
			pass
	return _DEFAULT_WEB_PORT


def _find_free_port(host: str, port: int) -> int:
	"""Return the requested port when free, otherwise fall back to an ephemeral port."""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		try:
			s.bind((host, port))
			return int(s.getsockname()[1])
		except OSError:
			s.bind((host, 0))
			return int(s.getsockname()[1])


def _load_template() -> Template:
	"""Load HTML template from external file."""
	template_path = _TEMPLATE_DIR / "choice.html"
	return Template(template_path.read_text(encoding="utf-8"))


def _load_dashboard_template() -> Template:
	"""Load dashboard HTML template."""
	template_path = _TEMPLATE_DIR / "dashboard.html"
	return Template(template_path.read_text(encoding="utf-8"))


def _deadline_from_seconds(seconds: int, *, now: Optional[float] = None) -> float:
	"""Compute an absolute deadline timestamp using monotonic clock."""
	base = now if now is not None else time.monotonic()
	return base + max(1, int(seconds))


def _remaining_seconds(deadline: float, *, now: Optional[float] = None) -> float:
	"""Calculate remaining seconds until deadline using monotonic clock."""
	base = now if now is not None else time.monotonic()
	return max(0.0, deadline - base)


def _status_label(action_status: str) -> str:
	if action_status.startswith("timeout"):
		return "timeout"
	if action_status == "cancelled":
		return "cancelled"
	return "submitted"


def _render_dashboard(sessions: Iterable["ChoiceSession"]) -> str:
	"""Render the dashboard listing active and recently completed choices."""
	template = _load_dashboard_template()
	rows = []
	now = time.monotonic()
	for session in sessions:
		remaining = _remaining_seconds(session.deadline, now=now) if session.status == "pending" else 0
		rows.append(
			{
				"choice_id": session.choice_id,
				"title": session.req.title,
				"url": session.url,
				"remaining": int(remaining),
				"status": session.status,
			}
		)
	rows.sort(key=lambda r: (r["status"] != "pending", r["remaining"]))
	items = []
	for row in rows:
		label = f"Open {row['title'] or row['choice_id']}"
		status_text = f" — {row['status']}" if row["status"] != "pending" else f" — {row['remaining']}s remaining"
		items.append(f"<li><a href='{row['url']}'>{label}</a>{status_text}</li>")
	list_html = "\n".join(items) if items else "<li>No active interactions</li>"
	return template.substitute(items=list_html)


def _render_html(
	req: ProvideChoiceRequest,
	*,
	choice_id: str,
	defaults: ProvideChoiceConfig,
	allow_terminal: bool,
	session_state: dict[str, object],
) -> str:
	"""Generate HTML that includes a configuration panel and the choice UI."""

	option_payload = [
		{"id": o.id, "description": o.description, "recommended": o.recommended}
		for o in req.options
	]

	defaults_payload = {
		"transport": defaults.transport,
		"timeout_seconds": defaults.timeout_seconds,
		"single_submit_mode": defaults.single_submit_mode,
		"timeout_default_enabled": defaults.timeout_default_enabled,
		"timeout_default_index": defaults.timeout_default_index,
		"use_default_option": defaults.use_default_option,
		"timeout_action": defaults.timeout_action,
	}

	transport_options = [
		"<option value='web' {sel}>Web Portal</option>".format(
			sel="selected" if defaults.transport == TRANSPORT_WEB else ""
		)
	]
	if allow_terminal:
		transport_options.append(
			"<option value='terminal' {sel}>Terminal</option>".format(
				sel="selected" if defaults.transport != TRANSPORT_WEB else ""
			)
		)

	template = _load_template()
	return template.substitute(
		title=req.title,
		prompt=req.prompt,
		prompt_type=req.selection_mode,
		choice_id=choice_id,
		defaults_json=json.dumps(defaults_payload),
		session_state_json=json.dumps(session_state),
		options_json=json.dumps(option_payload),
		transport_options="\n".join(transport_options),
		timeout_value=defaults.timeout_seconds,
		single_submit_checked="checked" if defaults.single_submit_mode else "",
		mcp_version="0.1.0",
		invocation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
	)


# Section: Session Runtime
@dataclass
class ChoiceSession:
	choice_id: str
	req: ProvideChoiceRequest
	defaults: ProvideChoiceConfig
	allow_terminal: bool
	url: str
	deadline: float
	result_future: asyncio.Future[ProvideChoiceResponse]
	connections: Set[WebSocket]
	config_used: ProvideChoiceConfig
	status: str = "pending"
	final_result: Optional[ProvideChoiceResponse] = None
	completed_at: Optional[float] = None
	monitor_task: Optional[asyncio.Task[None]] = None

	def effective_defaults(self) -> ProvideChoiceConfig:
		return self.config_used if self.final_result else self.defaults

	def update_deadline(self, seconds: int) -> None:
		self.deadline = _deadline_from_seconds(seconds)
		self.config_used.timeout_seconds = seconds

	def set_result(self, response: ProvideChoiceResponse) -> bool:
		if self.result_future.done():
			return False
		self.final_result = response
		self.status = _status_label(response.action_status)
		self.result_future.set_result(response)
		self.completed_at = time.monotonic()
		return True

	async def wait_for_result(self) -> ProvideChoiceResponse:
		return await self.result_future

	async def broadcast_sync(self) -> None:
		if not self.connections:
			return
		payload = {
			"type": "sync",
			"remaining_seconds": _remaining_seconds(self.deadline),
			"timeout_seconds": self.config_used.timeout_seconds,
		}
		stale: set[WebSocket] = set()
		for ws in list(self.connections):
			try:
				await ws.send_json(payload)
			except Exception:
				stale.add(ws)
		for ws in stale:
			self.connections.discard(ws)

	async def broadcast_status(self, status: str, action_status: Optional[str] = None) -> None:
		if not self.connections:
			return
		payload = {"type": "status", "status": status}
		if action_status:
			payload["action_status"] = action_status
		stale: set[WebSocket] = set()
		for ws in list(self.connections):
			try:
				await ws.send_json(payload)
			except Exception:
				stale.add(ws)
		for ws in stale:
			self.connections.discard(ws)

	def to_template_state(self) -> dict[str, object]:
		if not self.final_result:
			return {
				"status": "pending",
				"action_status": None,
				"selected_indices": [],
				"option_annotations": {},
				"global_annotation": None,
			}
		selection = self.final_result.selection
		return {
			"status": self.status,
			"action_status": self.final_result.action_status,
			"selected_indices": selection.selected_indices,
			"option_annotations": selection.option_annotations,
			"global_annotation": selection.global_annotation,
		}

	def is_expired(self, now: float) -> bool:
		return (
			self.final_result is not None
			and self.completed_at is not None
			and now - self.completed_at >= _SESSION_RETENTION_SECONDS
		)

	async def close(self) -> None:
		if self.monitor_task and not self.monitor_task.done():
			self.monitor_task.cancel()
			with contextlib.suppress(asyncio.CancelledError):
				await self.monitor_task
		for ws in list(self.connections):
			with contextlib.suppress(Exception):
				await ws.close()
		self.connections.clear()


# Section: Web Server Singleton
class WebChoiceServer:
	def __init__(self) -> None:
		self.host = _DEFAULT_WEB_HOST
		self.port = _find_free_port(self.host, _resolve_port())
		self.app = FastAPI()
		self.sessions: Dict[str, ChoiceSession] = {}
		self._server: Optional[uvicorn.Server] = None
		self._server_task: Optional[asyncio.Task[None]] = None
		self._cleanup_task: Optional[asyncio.Task[None]] = None
		self._register_routes()

	# Section: Route Registration
	def _register_routes(self) -> None:
		app = self.app

		@app.get("/")
		async def dashboard() -> HTMLResponse:  # noqa: ANN201
			html = _render_dashboard(self.sessions.values())
			return HTMLResponse(html)

		@app.get("/choice/{incoming_id}")
		async def choice_page(incoming_id: str):  # noqa: ANN201
			session = self.sessions.get(incoming_id)
			if not session:
				raise HTTPException(status_code=404)
			html = _render_html(
				req=session.req,
				choice_id=session.choice_id,
				defaults=session.effective_defaults(),
				allow_terminal=session.allow_terminal,
				session_state=session.to_template_state(),
			)
			return HTMLResponse(html)

		@app.websocket("/ws/{incoming_id}")
		async def websocket_channel(websocket: WebSocket, incoming_id: str) -> None:
			session = self.sessions.get(incoming_id)
			if not session:
				await websocket.close(code=1008)
				return
			await websocket.accept()
			session.connections.add(websocket)
			status_payload = session.to_template_state()
			status_text = status_payload.get("status", "connected")
			await websocket.send_json({"type": "status", "status": status_text, "action_status": status_payload.get("action_status")})
			await session.broadcast_sync()
			try:
				while not session.result_future.done():
					try:
						message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
					except asyncio.TimeoutError:
						continue

					try:
						data = json.loads(message)
					except Exception:
						continue
					msg_type = data.get("type")
					if msg_type == "ping":
						await websocket.send_json({"type": "status", "status": "alive"})
						continue
					if msg_type == "update_timeout":
						seconds_raw = data.get("seconds")
						try:
							seconds_val = int(seconds_raw)
						except Exception:
							continue
						if seconds_val > 0:
							session.update_deadline(seconds_val)
							await session.broadcast_sync()
						continue
			except WebSocketDisconnect:
				pass
			finally:
				session.connections.discard(websocket)

		@app.post("/choice/{incoming_id}/submit")
		async def submit_choice(incoming_id: str, payload: Dict[str, object]):  # noqa: ANN201
			session = self.sessions.get(incoming_id)
			if not session:
				raise HTTPException(status_code=404)
			if session.result_future.done():
				return JSONResponse({"status": "already-set", "state": session.to_template_state()})

			try:
				action = str(payload.get("action_status", ""))
				config_payload = payload.get("config") or {}
				if not isinstance(config_payload, dict):
					raise HTTPException(status_code=400, detail="config must be object")

				parsed_config = _parse_config_payload(session.defaults, config_payload, session.req)
				adjusted_req = apply_configuration(session.req, parsed_config)

				session.config_used = parsed_config
				session.update_deadline(parsed_config.timeout_seconds)

				option_annotations_raw = payload.get("option_annotations") or {}
				option_annotations: dict[str, str] = {}
				if isinstance(option_annotations_raw, dict):
					option_annotations = {str(k): str(v) for k, v in option_annotations_raw.items() if v}
				global_annotation_raw = payload.get("global_annotation")
				global_annotation: str | None = str(global_annotation_raw) if global_annotation_raw else None

				if action == "cancelled":
					response = cancelled_response(
						transport=TRANSPORT_WEB,
						url=session.url,
						option_annotations=option_annotations,
						global_annotation=global_annotation,
					)
					session.set_result(response)
					await session.broadcast_status("cancelled", action_status=response.action_status)
					return {"status": "ok"}

				if action == "selected":
					selected_ids = payload.get("selected_indices")
					if not isinstance(selected_ids, list):
						raise HTTPException(status_code=400, detail="selected_indices must be list")
					ids = [str(x) for x in selected_ids]
					valid_ids = {o.id for o in adjusted_req.options}
					if any(i not in valid_ids for i in ids):
						raise HTTPException(status_code=400, detail="selected_indices contains unknown id")

					response = normalize_response(
						req=adjusted_req,
						selected_indices=ids,
						transport=TRANSPORT_WEB,
						url=session.url,
						option_annotations=option_annotations,
						global_annotation=global_annotation,
					)
					session.set_result(response)
					await session.broadcast_status("submitted", action_status=response.action_status)
					return {"status": "ok"}

				if action == "timeout" or action in {"timeout_auto_submitted", "timeout_cancelled", "timeout_reinvoke_requested"}:
					response = timeout_response(
						req=adjusted_req,
						transport=TRANSPORT_WEB,
						url=session.url,
					)
					session.set_result(response)
					await session.broadcast_status("timeout", action_status=response.action_status)
					return {"status": "ok"}

				raise HTTPException(status_code=400, detail="invalid action_status")

			except HTTPException:
				raise
			except ValidationError as exc:
				raise HTTPException(status_code=400, detail=str(exc)) from exc
			except Exception as exc:
				import traceback
				print(f"Internal Server Error in submit_choice: {exc}")
				traceback.print_exc()
				raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(exc)}") from exc

	# Section: Lifecycle
	async def ensure_running(self) -> None:
		if self._server_task and not self._server_task.done():
			return
		config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="error")
		self._server = uvicorn.Server(config)
		self._server_task = asyncio.create_task(self._server.serve())
		if self._cleanup_task is None or self._cleanup_task.done():
			self._cleanup_task = asyncio.create_task(self._cleanup_loop())
		await asyncio.sleep(0.1)

	async def create_session(self, req: ProvideChoiceRequest, defaults: ProvideChoiceConfig, allow_terminal: bool) -> ChoiceSession:
		await self.ensure_running()
		choice_id = uuid.uuid4().hex
		defaults.transport = TRANSPORT_WEB
		loop = asyncio.get_running_loop()
		result_future: asyncio.Future[ProvideChoiceResponse] = loop.create_future()
		deadline = _deadline_from_seconds(defaults.timeout_seconds)
		session = ChoiceSession(
			choice_id=choice_id,
			req=req,
			defaults=defaults,
			allow_terminal=allow_terminal,
			url=f"http://{self.host}:{self.port}/choice/{choice_id}",
			deadline=deadline,
			result_future=result_future,
			connections=set(),
			config_used=defaults,
		)
		session.monitor_task = asyncio.create_task(self._monitor_deadline(session))
		self.sessions[choice_id] = session
		return session

	async def _monitor_deadline(self, session: ChoiceSession) -> None:
		try:
			while not session.result_future.done():
				remaining = _remaining_seconds(session.deadline)
				await session.broadcast_sync()
				if remaining <= 0:
					adjusted_req = apply_configuration(session.req, session.config_used)
					response = timeout_response(req=adjusted_req, transport=TRANSPORT_WEB, url=session.url)
					session.set_result(response)
					await session.broadcast_status("timeout", action_status=response.action_status)
					break
				await asyncio.sleep(1)
		except asyncio.CancelledError:
			raise
		finally:
			await session.broadcast_sync()

	async def _cleanup_loop(self) -> None:
		while True:
			await asyncio.sleep(10)
			now = time.monotonic()
			expired = [cid for cid, session in self.sessions.items() if session.is_expired(now)]
			for cid in expired:
				await self._remove_session(cid)

	async def _remove_session(self, choice_id: str) -> None:
		session = self.sessions.pop(choice_id, None)
		if not session:
			return
		await session.close()


_WEB_SERVER: Optional[WebChoiceServer] = None


async def _get_server() -> WebChoiceServer:
	global _WEB_SERVER
	if _WEB_SERVER is None:
		_WEB_SERVER = WebChoiceServer()
	await _WEB_SERVER.ensure_running()
	return _WEB_SERVER


# Section: Public Entrypoint
async def run_web_choice(
	req: ProvideChoiceRequest,
	*,
	defaults: ProvideChoiceConfig,
	allow_terminal: bool,
) -> tuple[ProvideChoiceResponse, ProvideChoiceConfig]:
	"""Run the web-based choice flow with a persistent server."""
	server = await _get_server()
	session = await server.create_session(req, defaults, allow_terminal)
	try:
		webbrowser.open(session.url)
	except Exception:
		pass

	result = await session.wait_for_result()
	final_config = session.config_used
	return result, final_config


def _parse_config_payload(defaults: ProvideChoiceConfig, payload: Dict[str, object], req: ProvideChoiceRequest) -> ProvideChoiceConfig:  # noqa: ARG001
	"""Parse config payload from web form submission."""
	transport_raw = payload.get("transport")
	transport = str(transport_raw) if transport_raw else TRANSPORT_WEB
	if transport not in VALID_TRANSPORTS:
		transport = TRANSPORT_WEB

	timeout_raw = payload.get("timeout_seconds")
	timeout_val = defaults.timeout_seconds
	if isinstance(timeout_raw, (int, float, str)):
		try:
			timeout_val = int(timeout_raw)
		except Exception:
			timeout_val = defaults.timeout_seconds
	if timeout_val <= 0:
		timeout_val = defaults.timeout_seconds

	single_submit_raw = payload.get("single_submit_mode")
	single_submit_val = defaults.single_submit_mode
	if isinstance(single_submit_raw, bool):
		single_submit_val = single_submit_raw

	timeout_default_enabled = payload.get("timeout_default_enabled")
	if not isinstance(timeout_default_enabled, bool):
		timeout_default_enabled = defaults.timeout_default_enabled

	timeout_default_idx_raw = payload.get("timeout_default_index")
	timeout_default_idx = defaults.timeout_default_index
	if isinstance(timeout_default_idx_raw, (int, float, str)):
		try:
			timeout_default_idx = int(timeout_default_idx_raw)
		except Exception:
			timeout_default_idx = defaults.timeout_default_index
	if timeout_default_idx is not None and (timeout_default_idx < 0 or timeout_default_idx >= len(req.options)):
		timeout_default_idx = defaults.timeout_default_index

	use_default_option_raw = payload.get("use_default_option")
	use_default_option = defaults.use_default_option
	if isinstance(use_default_option_raw, bool):
		use_default_option = use_default_option_raw

	timeout_action_raw = payload.get("timeout_action")
	timeout_action = defaults.timeout_action
	if isinstance(timeout_action_raw, str):
		timeout_action = timeout_action_raw

	return ProvideChoiceConfig(
		transport=transport,
		timeout_seconds=timeout_val,
		single_submit_mode=single_submit_val,
		timeout_default_enabled=timeout_default_enabled,
		timeout_default_index=timeout_default_idx,
		use_default_option=use_default_option,
		timeout_action=timeout_action,
	)
