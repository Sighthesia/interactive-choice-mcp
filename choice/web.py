from __future__ import annotations

import asyncio
import contextlib
import json
import socket
import time
import uuid
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Dict, Optional, Set

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


@dataclass
class _ActiveChoice:
    choice_id: str
    title: str
    url: str
    deadline: float


ACTIVE_CHOICES: dict[str, _ActiveChoice] = {}


# Section: Utility Functions
def _find_free_port() -> int:
    """Find an available ephemeral port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
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


def _render_dashboard() -> str:
    """Render the dashboard listing active choices for recovery."""
    template = _load_dashboard_template()
    rows = []
    now = time.monotonic()
    for choice_id, meta in ACTIVE_CHOICES.items():
        remaining = _remaining_seconds(meta.deadline, now=now)
        rows.append(
            {
                "choice_id": choice_id,
                "title": meta.title,
                "url": meta.url,
                "remaining": int(remaining),
            }
        )
    rows.sort(key=lambda r: r["remaining"])
    items = []
    for row in rows:
        items.append(
            f"<li><a href='{row['url']}'>Open {row['title'] or row['choice_id']}</a>"
            f" — {row['remaining']}s remaining</li>"
        )
    list_html = "\n".join(items) if items else "<li>No active interactions</li>"
    return template.substitute(items=list_html)


# Section: HTML Rendering
def _render_html(
    req: ProvideChoiceRequest,
    *,
    choice_id: str,
    defaults: ProvideChoiceConfig,
    allow_terminal: bool,
) -> str:
    """Generate HTML that includes a configuration panel and the choice UI."""

    option_payload = [
        {"id": o.id, "description": o.description, "recommended": o.recommended}
        for o in req.options
    ]

    # Build defaults payload for JavaScript
    defaults_payload = {
        "transport": defaults.transport,
        "timeout_seconds": defaults.timeout_seconds,
        "single_submit_mode": defaults.single_submit_mode,
        "timeout_default_enabled": defaults.timeout_default_enabled,
        "timeout_default_index": defaults.timeout_default_index,
        "use_default_option": defaults.use_default_option,
        "timeout_action": defaults.timeout_action,
    }

    # Build transport options HTML
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

    # Load and render external template
    template = _load_template()
    return template.substitute(
        title=req.title,
        prompt=req.prompt,
        prompt_type=req.selection_mode,
        choice_id=choice_id,
        defaults_json=json.dumps(defaults_payload),
        options_json=json.dumps(option_payload),
        transport_options="\n".join(transport_options),
        timeout_value=defaults.timeout_seconds,
        single_submit_checked="checked" if defaults.single_submit_mode else "",
        mcp_version="0.1.0",
        invocation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


async def run_web_choice(
    req: ProvideChoiceRequest,
    *,
    defaults: ProvideChoiceConfig,
    allow_terminal: bool,
) -> tuple[ProvideChoiceResponse, ProvideChoiceConfig]:
    """Run the web-based choice flow with configuration panel."""
    choice_id = uuid.uuid4().hex
    session_url: str = ""
    loop = asyncio.get_running_loop()
    result_future: asyncio.Future[ProvideChoiceResponse] = loop.create_future()
    config_used: ProvideChoiceConfig = defaults

    defaults.transport = TRANSPORT_WEB
    app = FastAPI()

    # Deadline management
    deadline = _deadline_from_seconds(defaults.timeout_seconds)
    connections: Set[WebSocket] = set()

    def _register_active(url: str) -> None:
        ACTIVE_CHOICES[choice_id] = _ActiveChoice(
            choice_id=choice_id,
            title=req.title,
            url=url,
            deadline=deadline,
        )

    def _update_deadline(seconds: int) -> None:
        nonlocal deadline, config_used
        deadline = _deadline_from_seconds(seconds)
        config_used.timeout_seconds = seconds
        entry = ACTIVE_CHOICES.get(choice_id)
        if entry:
            entry.deadline = deadline

    async def _broadcast_sync() -> None:
        if not connections:
            return
        payload = {
            "type": "sync",
            "remaining_seconds": _remaining_seconds(deadline),
            "timeout_seconds": config_used.timeout_seconds,
        }
        stale: set[WebSocket] = set()
        for ws in list(connections):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.add(ws)
        for ws in stale:
            connections.discard(ws)

    async def _broadcast_status(status: str) -> None:
        if not connections:
            return
        payload = {"type": "status", "status": status}
        stale: set[WebSocket] = set()
        for ws in list(connections):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.add(ws)
        for ws in stale:
            connections.discard(ws)

    @app.get("/")
    async def dashboard() -> HTMLResponse:
        html = _render_dashboard()
        return HTMLResponse(html)

    @app.get("/choice/{incoming_id}")
    async def choice_page(incoming_id: str):
        if incoming_id != choice_id:
            raise HTTPException(status_code=404)
        html = _render_html(req, choice_id=choice_id, defaults=defaults, allow_terminal=allow_terminal)
        return HTMLResponse(html)

    @app.websocket("/ws/{incoming_id}")
    async def websocket_channel(websocket: WebSocket, incoming_id: str):
        if incoming_id != choice_id:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        connections.add(websocket)
        await websocket.send_json({"type": "status", "status": "connected"})
        await _broadcast_sync()
        try:
            while not result_future.done():
                message = await websocket.receive_text()
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
                        _update_deadline(seconds_val)
                        await _broadcast_sync()
                    continue
        except WebSocketDisconnect:
            pass
        finally:
            connections.discard(websocket)

    @app.post("/choice/{incoming_id}/submit")
    async def submit_choice(incoming_id: str, payload: Dict[str, object]):
        if incoming_id != choice_id:
            raise HTTPException(status_code=404)
        if result_future.done():
            return JSONResponse({"status": "already-set"})

        try:
            action = str(payload.get("action_status", ""))
            config_payload = payload.get("config") or {}
            if not isinstance(config_payload, dict):
                raise HTTPException(status_code=400, detail="config must be object")

            parsed_config = _parse_config_payload(defaults, config_payload, req)
            adjusted_req = apply_configuration(req, parsed_config)

            nonlocal config_used
            config_used = parsed_config
            _update_deadline(parsed_config.timeout_seconds)

            # Extract annotations from payload
            option_annotations_raw = payload.get("option_annotations") or {}
            option_annotations: dict[str, str] = {}
            if isinstance(option_annotations_raw, dict):
                option_annotations = {str(k): str(v) for k, v in option_annotations_raw.items() if v}
            global_annotation_raw = payload.get("global_annotation")
            global_annotation: str | None = str(global_annotation_raw) if global_annotation_raw else None

            if action == "cancelled":
                result_future.set_result(
                    cancelled_response(
                        transport=TRANSPORT_WEB,
                        url=session_url,
                        option_annotations=option_annotations,
                        global_annotation=global_annotation,
                    )
                )
                await _broadcast_status("cancelled")
                return {"status": "ok"}

            if action == "selected":
                selected_ids = payload.get("selected_indices")
                if not isinstance(selected_ids, list):
                    raise HTTPException(status_code=400, detail="selected_indices must be list")
                ids = [str(x) for x in selected_ids]
                valid_ids = {o.id for o in adjusted_req.options}
                if any(i not in valid_ids for i in ids):
                    raise HTTPException(status_code=400, detail="selected_indices contains unknown id")

                result_future.set_result(
                    normalize_response(
                        req=adjusted_req,
                        selected_indices=ids,
                        transport=TRANSPORT_WEB,
                        url=session_url,
                        option_annotations=option_annotations,
                        global_annotation=global_annotation,
                    )
                )
                await _broadcast_status("submitted")
                return {"status": "ok"}

            if action == "timeout" or action in {"timeout_auto_submitted", "timeout_cancelled"}:
                result_future.set_result(
                    timeout_response(
                        req=adjusted_req,
                        transport=TRANSPORT_WEB,
                        url=session_url,
                    )
                )
                await _broadcast_status("timeout")
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

    port = _find_free_port()
    session_url = f"http://127.0.0.1:{port}/choice/{choice_id}"
    _register_active(session_url)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    async def serve() -> None:
        await server.serve()

    async def monitor_deadline() -> None:
        nonlocal deadline
        while not result_future.done():
            remaining = _remaining_seconds(deadline)
            await _broadcast_sync()
            if remaining <= 0:
                adjusted_req = apply_configuration(req, config_used)
                result_future.set_result(
                    timeout_response(req=adjusted_req, transport=TRANSPORT_WEB, url=session_url)
                )
                await _broadcast_status("timeout")
                break
            await asyncio.sleep(1)

    server_task = asyncio.create_task(serve())
    monitor_task = asyncio.create_task(monitor_deadline())
    # Best-effort wait for startup
    await asyncio.sleep(0.2)
    try:
        webbrowser.open(session_url)
    except Exception:
        pass

    try:
        result = await result_future
        final_config = config_used
    finally:
        server.should_exit = True
        monitor_task.cancel()
        with contextlib.suppress(Exception):
            await monitor_task
        await server_task
        ACTIVE_CHOICES.pop(choice_id, None)

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

    # Timeout default
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
    # Clamp to valid range; fallback to defaults if out of range
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
