"""Web server orchestration for the `choice.web` package.

Contains server routes, session management, and lifecycle helpers for
web-based choice interactions.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import time
import uuid
import webbrowser
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from ..models import (
    ProvideChoiceConfig,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    VALID_TRANSPORTS,
    ValidationError,
    TRANSPORT_WEB,
)
from ..response import cancelled_response as cancelled_response_fn, normalize_response, timeout_response
from ..validation import apply_configuration as apply_configuration_fn
from .session import ChoiceSession, _deadline_from_seconds
from .templates import _render_dashboard, _render_html

__all__ = [
    "WebChoiceServer",
    "run_web_choice",
    "create_terminal_handoff_session",
    "poll_terminal_session_result",
]

_DEFAULT_WEB_HOST = "127.0.0.1"
_DEFAULT_WEB_PORT = 17863
_SESSION_RETENTION_SECONDS = 600


def _resolve_port() -> int:
    raw = os.environ.get("CHOICE_WEB_PORT")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return _DEFAULT_WEB_PORT


def _find_free_port(host: str, port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return int(s.getsockname()[1])
        except OSError:
            s.bind((host, 0))
            return int(s.getsockname()[1])


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
                adjusted_req = apply_configuration_fn(session.req, parsed_config)

                session.config_used = parsed_config
                session.update_deadline(parsed_config.timeout_seconds)

                option_annotations_raw = payload.get("option_annotations") or {}
                option_annotations: dict[str, str] = {}
                if isinstance(option_annotations_raw, dict):
                    option_annotations = {str(k): str(v) for k, v in option_annotations_raw.items() if v}
                global_annotation_raw = payload.get("global_annotation")
                global_annotation: str | None = str(global_annotation_raw) if global_annotation_raw else None

                if action == "cancelled":
                    response = cancelled_response_fn(
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

        # Section: Terminal Hand-off Endpoints
        @app.get("/terminal/{session_id}")
        async def get_terminal_session(session_id: str):  # noqa: ANN201
            """Get terminal session info for the CLI client."""
            from ..terminal.session import get_terminal_session_store
            store = get_terminal_session_store()
            session = store.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="session not found or expired")
            if session.result is not None:
                return JSONResponse({
                    "status": "completed",
                    "result": {
                        "action_status": session.result.action_status,
                        "selected_indices": session.result.selection.selected_indices,
                        "summary": session.result.selection.summary,
                    },
                })
            return JSONResponse({
                "status": "pending",
                "remaining_seconds": session.remaining_seconds,
                "request": {
                    "title": session.req.title,
                    "prompt": session.req.prompt,
                    "selection_mode": session.req.selection_mode,
                    "options": [
                        {"id": o.id, "description": o.description, "recommended": o.recommended}
                        for o in session.req.options
                    ],
                },
                "config": {
                    "timeout_seconds": session.config.timeout_seconds,
                    "single_submit_mode": session.config.single_submit_mode,
                    "use_default_option": session.config.use_default_option,
                    "timeout_action": session.config.timeout_action,
                },
            })

        @app.post("/terminal/{session_id}/submit")
        async def submit_terminal_result(session_id: str, payload: Dict[str, object]):  # noqa: ANN201
            """Submit the result from the terminal CLI client."""
            from ..terminal.session import get_terminal_session_store
            store = get_terminal_session_store()
            session = store.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="session not found or expired")
            if session.result is not None:
                return JSONResponse({"status": "already-set"})

            action = str(payload.get("action_status", ""))
            selected_indices = payload.get("selected_indices", [])
            option_annotations = payload.get("option_annotations", {})
            global_annotation = payload.get("global_annotation")

            if action == "cancelled":
                from ..response import cancelled_response
                response = cancelled_response(
                    transport=TRANSPORT_WEB,
                    url=f"http://{self.host}:{self.port}/terminal/{session_id}",
                    option_annotations=option_annotations if isinstance(option_annotations, dict) else {},
                    global_annotation=str(global_annotation) if global_annotation else None,
                )
            elif action == "selected":
                if not isinstance(selected_indices, list):
                    raise HTTPException(status_code=400, detail="selected_indices must be list")
                ids = [str(x) for x in selected_indices]
                valid_ids = {o.id for o in session.req.options}
                if any(i not in valid_ids for i in ids):
                    raise HTTPException(status_code=400, detail="selected_indices contains unknown id")
                response = normalize_response(
                    req=session.req,
                    selected_indices=ids,
                    transport=TRANSPORT_WEB,
                    url=f"http://{self.host}:{self.port}/terminal/{session_id}",
                    option_annotations=option_annotations if isinstance(option_annotations, dict) else {},
                    global_annotation=str(global_annotation) if global_annotation else None,
                )
            elif action.startswith("timeout"):
                response = timeout_response(
                    req=session.req,
                    transport=TRANSPORT_WEB,
                    url=f"http://{self.host}:{self.port}/terminal/{session_id}",
                )
            else:
                raise HTTPException(status_code=400, detail="invalid action_status")

            session.set_result(response)
            return JSONResponse({"status": "ok"})

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
        session.monitor_task = asyncio.create_task(session.monitor_deadline())
        self.sessions[choice_id] = session
        return session

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


async def run_web_choice(
    req: ProvideChoiceRequest,
    *,
    defaults: ProvideChoiceConfig,
    allow_terminal: bool,
) -> tuple[ProvideChoiceResponse, ProvideChoiceConfig]:
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


# Section: Terminal Hand-off Functions
async def create_terminal_handoff_session(
    req: ProvideChoiceRequest,
    config: ProvideChoiceConfig,
) -> ProvideChoiceResponse:
    """Create a terminal hand-off session and return immediately with launch info.
    
    This function:
    1. Ensures the web server is running (for the terminal client to connect to)
    2. Creates a terminal session in the session store
    3. Returns a `pending_terminal_launch` response with the launch command
    
    The agent should then run the returned command to open the terminal UI.
    """
    from ..response import pending_terminal_launch_response
    from ..terminal.session import get_terminal_session_store

    server = await _get_server()
    store = get_terminal_session_store()
    session = store.create_session(req, config, config.timeout_seconds)

    url = f"http://{server.host}:{server.port}/terminal/{session.session_id}"
    launch_command = f"uv run python -m choice.terminal.client --session {session.session_id} --url http://{server.host}:{server.port}"

    return pending_terminal_launch_response(
        session_id=session.session_id,
        url=url,
        launch_command=launch_command,
    )


async def poll_terminal_session_result(session_id: str, wait_seconds: int = 30) -> Optional[ProvideChoiceResponse]:
    """Poll for the result of a terminal hand-off session with blocking wait.
    
    This function implements a smart polling mechanism that:
    1. Returns immediately if the result is already available
    2. Waits up to `wait_seconds` for the result if still pending
    3. Returns None only if session not found
    4. Returns timeout response if session expired
    
    The waiting behavior reduces the need for frequent polling by the AI agent.
    
    Args:
        session_id: The terminal session ID to poll
        wait_seconds: Maximum seconds to wait for result (default 30)
        
    Returns:
        The ProvideChoiceResponse if available, or None if session not found
    """
    from ..terminal.session import get_terminal_session_store
    from ..response import timeout_response

    store = get_terminal_session_store()
    session = store.get_session(session_id)
    if session is None:
        return None

    # If result already available, return immediately
    if session.result is not None:
        return session.result

    # If already expired, return timeout
    if session.is_expired:
        response = timeout_response(req=session.req, transport=TRANSPORT_WEB, url=None)
        session.set_result(response)
        return response

    # Wait for result with timeout (blocking wait to reduce polling)
    effective_wait = min(wait_seconds, session.remaining_seconds)
    if effective_wait > 0:
        result = await session.wait_for_result(timeout=effective_wait)
        if result is not None:
            return result
    
    # Check again after waiting
    if session.result is not None:
        return session.result
    
    if session.is_expired:
        response = timeout_response(req=session.req, transport=TRANSPORT_WEB, url=None)
        session.set_result(response)
        return response

    # Still pending - return None to indicate caller should poll again
    return None
