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
from datetime import datetime
from typing import Dict, Optional, cast

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from ..infra import get_logger, get_session_logger
from ..store import PersistedSession
from ..core.models import (
    ProvideChoiceOption,
    ProvideChoiceConfig,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    InteractionStatus,
    VALID_TRANSPORTS,
    VALID_LANGUAGES,
    ValidationError,
    DEFAULT_TIMEOUT_SECONDS,
    TRANSPORT_WEB,
    TRANSPORT_TERMINAL,
    TRANSPORT_TERMINAL_WEB,
)
from ..core.response import cancelled_response as cancelled_response_fn, normalize_response, timeout_response
from ..core.validation import apply_configuration as apply_configuration_fn
from .session import ChoiceSession, _deadline_from_seconds, _remaining_seconds
from .templates import _render_html

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..terminal.session import TerminalSession
    from ..store import PersistedSession

__all__ = [
    "WebChoiceServer",
    "run_web_choice",
    "create_terminal_handoff_session",
    "poll_terminal_session_result",
    "poll_session_result",
]

_logger = get_logger(__name__)

_DEFAULT_WEB_HOST = "127.0.0.1"
_DEFAULT_WEB_PORT = 17863


def _resolve_host() -> str:
    """Resolve web host from environment variable or use default."""
    raw = os.environ.get("CHOICE_WEB_HOST")
    if raw:
        return raw.strip()
    return _DEFAULT_WEB_HOST


def _resolve_port() -> int:
    """Resolve web port from environment variable or use default."""
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


# Section: Constants
_MAX_RECENT_COMPLETED = 10  # Maximum number of completed interactions to surface in the sidebar


class WebChoiceServer:
    def __init__(self) -> None:
        self.host = _resolve_host()
        self.port = _find_free_port(self.host, _resolve_port())
        self.app = FastAPI()
        self.sessions: Dict[str, ChoiceSession] = {}
        self._server: Optional[uvicorn.Server] = None
        self._server_task: Optional[asyncio.Task[None]] = None
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        # Global WebSocket connections for interaction list updates
        self._list_connections: set[WebSocket] = set()
        self._register_routes()

    def _register_routes(self) -> None:
        app = self.app
        
        # Section: Static Bundle Routes
        @app.get("/static/bundle.{hash}.css")
        async def serve_css_bundle(hash: str):  # noqa: ANN201
            """Serve the cached CSS bundle with long-term caching."""
            from .bundler import get_asset_bundle
            from fastapi.responses import Response
            
            bundle = get_asset_bundle()
            if hash != bundle.css_hash:
                raise HTTPException(status_code=404, detail="Bundle not found")
            return Response(
                content=bundle.css,
                media_type="text/css",
                headers={
                    "Cache-Control": "public, max-age=31536000, immutable",
                    "ETag": f'"{bundle.css_hash}"',
                },
            )
        
        @app.get("/static/bundle.{hash}.js")
        async def serve_js_bundle(hash: str):  # noqa: ANN201
            """Serve the cached JS bundle with long-term caching."""
            from .bundler import get_asset_bundle
            from fastapi.responses import Response
            
            bundle = get_asset_bundle()
            if hash != bundle.js_hash:
                raise HTTPException(status_code=404, detail="Bundle not found")
            return Response(
                content=bundle.js,
                media_type="application/javascript",
                headers={
                    "Cache-Control": "public, max-age=31536000, immutable",
                    "ETag": f'"{bundle.js_hash}"',
                },
            )

        @app.get("/choice/{incoming_id}")
        async def choice_page(incoming_id: str):  # noqa: ANN201
            session = self.sessions.get(incoming_id)
            persisted_session: PersistedSession | None = None
            if not session:
                from ..store.interaction_store import get_interaction_store

                store = get_interaction_store()
                persisted_session = store.get_by_id(incoming_id)
                if (
                    not persisted_session
                    or not persisted_session.result
                    or persisted_session.transport != TRANSPORT_WEB
                ):
                    raise HTTPException(status_code=404)
                assert persisted_session is not None
                persisted_session = cast(PersistedSession, persisted_session)

            if session:
                req = session.req
                allow_terminal = session.allow_terminal
                invocation_time = session.invocation_time
                # Merge session defaults with latest global config for UI display
                # This ensures UI always shows the latest saved settings
                from ..infra import ConfigStore
                latest_config = ConfigStore().load()
                display_defaults = session.effective_defaults()
                if latest_config:
                    # Use latest global settings for display, but keep session-specific values
                    display_defaults = ProvideChoiceConfig(
                        transport=latest_config.transport,
                        timeout_seconds=latest_config.timeout_seconds,
                        single_submit_mode=latest_config.single_submit_mode,
                        timeout_default_enabled=latest_config.timeout_default_enabled,
                        timeout_default_index=display_defaults.timeout_default_index,  # Keep session value
                        use_default_option=latest_config.use_default_option,
                        timeout_action=latest_config.timeout_action,
                        language=latest_config.language,
                        notify_new=latest_config.notify_new,
                        notify_upcoming=latest_config.notify_upcoming,
                        upcoming_threshold=latest_config.upcoming_threshold,
                        notify_timeout=latest_config.notify_timeout,
                        notify_if_foreground=latest_config.notify_if_foreground,
                        notify_if_focused=latest_config.notify_if_focused,
                        notify_if_background=latest_config.notify_if_background,
                        notify_sound=latest_config.notify_sound,
                    )
                session_state = session.to_template_state()
                choice_id = session.choice_id
            else:
                persisted = cast(PersistedSession, persisted_session)
                timeout_value = persisted.timeout_seconds or DEFAULT_TIMEOUT_SECONDS
                options = [
                    ProvideChoiceOption(
                        id=str(opt.get("id", "")),
                        description=str(opt.get("description", "")),
                        recommended=bool(opt.get("recommended", False)),
                    )
                    for opt in (persisted.options or [])
                ]
                req = ProvideChoiceRequest(
                    title=persisted.title,
                    prompt=persisted.prompt,
                    selection_mode=persisted.selection_mode,
                    options=options,
                    timeout_seconds=timeout_value,
                )
                from ..infra import ConfigStore
                latest_config = ConfigStore().load()
                if latest_config:
                    display_defaults = latest_config
                else:
                    display_defaults = ProvideChoiceConfig(
                        transport=TRANSPORT_WEB,
                        timeout_seconds=timeout_value,
                    )
                if isinstance(persisted.result, dict):
                    selection = persisted.result.get("selection", {})
                    action_status = str(persisted.result.get("action_status", "submitted"))
                else:
                    selection = {}
                    action_status = "submitted"
                session_state = {
                    "status": InteractionStatus.from_action_status(action_status).value,
                    "action_status": action_status,
                    "selected_indices": selection.get("selected_indices", []),
                    "option_annotations": selection.get("option_annotations", {}),
                    "global_annotation": selection.get("global_annotation"),
                }
                allow_terminal = False
                invocation_time = persisted.started_at
                choice_id = persisted.session_id

            html = _render_html(
                req=req,
                choice_id=choice_id,
                defaults=display_defaults,
                allow_terminal=allow_terminal,
                session_state=session_state,
                invocation_time=invocation_time,
            )
            return HTMLResponse(
                content=html,
                headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
            )

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
            # Send full state including selected_indices to support page refresh recovery
            await websocket.send_json({
                "type": "status",
                "status": status_text,
                "action_status": status_payload.get("action_status"),
                "selected_indices": status_payload.get("selected_indices"),
                "option_annotations": status_payload.get("option_annotations"),
                "global_annotation": status_payload.get("global_annotation"),
                "remaining_seconds": _remaining_seconds(session.deadline),
                "timeout_seconds": session.config_used.timeout_seconds,
            })
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
            _logger.debug(f"[submit] Received submit for {incoming_id[:8]}, payload action={payload.get('action_status')}")
            _logger.debug(f"[submit] self.sessions keys: {[k[:8] for k in self.sessions.keys()]}")
            session = self.sessions.get(incoming_id)
            if not session:
                _logger.warning(f"[submit] Session {incoming_id[:8]} NOT FOUND in self.sessions!")
                raise HTTPException(status_code=404)
            _logger.debug(f"[submit] Found session {incoming_id[:8]}: final_result={session.final_result is not None}, future_done={session.result_future.done()}")
            if session.result_future.done():
                _logger.debug(f"[submit] Session {incoming_id[:8]} already done, returning already-set")
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

                if action == "cancelled" or action == "cancel_with_annotation":
                    response = cancelled_response_fn(
                        transport=TRANSPORT_WEB,
                        url=session.url,
                        option_annotations=option_annotations,
                        global_annotation=global_annotation,
                    )
                    # Update action_status if it's cancel_with_annotation
                    if action == "cancel_with_annotation":
                        response = ProvideChoiceResponse(
                            action_status="cancel_with_annotation",
                            selection=response.selection,
                        )
                    result_set = session.set_result(response)
                    _logger.debug(f"Session {incoming_id[:8]} set_result returned: {result_set}")
                    _logger.debug(f"Session {incoming_id[:8]} final_result: {session.final_result}")
                    self.save_session_to_store(session)
                    await session.broadcast_status("cancelled", action_status=response.action_status)
                    await self.broadcast_interaction_list()
                    _logger.info(f"Session {incoming_id[:8]} cancelled by user (action={action})")
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
                    result_set = session.set_result(response)
                    _logger.debug(f"Session {incoming_id[:8]} set_result returned: {result_set}")
                    _logger.debug(f"Session {incoming_id[:8]} final_result: {session.final_result}")
                    self.save_session_to_store(session)
                    await session.broadcast_status("submitted", action_status=response.action_status)
                    await self.broadcast_interaction_list()
                    _logger.info(f"Session {incoming_id[:8]} submitted: selected={ids}")
                    return {"status": "ok"}

                if action == "timeout" or action in {"timeout_auto_submitted", "timeout_cancelled", "timeout_reinvoke_requested"}:
                    response = timeout_response(
                        req=adjusted_req,
                        transport=TRANSPORT_WEB,
                        url=session.url,
                    )
                    session.set_result(response)
                    self.save_session_to_store(session)
                    await session.broadcast_status("timeout", action_status=response.action_status)
                    await self.broadcast_interaction_list()
                    _logger.info(f"Session {incoming_id[:8]} timeout: action={response.action_status}")
                    return {"status": "ok"}

                raise HTTPException(status_code=400, detail="invalid action_status")

            except HTTPException:
                raise
            except ValidationError as exc:
                _logger.warning(f"Session {incoming_id[:8]} validation error: {exc}")
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except Exception as exc:
                _logger.exception(f"Session {incoming_id[:8]} internal error: {exc}")
                raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(exc)}") from exc

        # Section: Global Config Endpoint
        @app.post("/api/config")
        async def update_global_config(payload: Dict[str, object]):  # noqa: ANN201
            """Save global configuration settings.

            This endpoint persists settings like transport, timeout, language, etc.
            without requiring an active session.
            """
            from ..infra import ConfigStore
            from ..core.models import ProvideChoiceRequest, ProvideChoiceOption, DEFAULT_TIMEOUT_SECONDS, TRANSPORT_TERMINAL

            # Create a dummy request for config parsing (only needed for option count validation)
            dummy_req = ProvideChoiceRequest(
                title="",
                prompt="",
                selection_mode="single",
                options=[ProvideChoiceOption(id="dummy", description="")],
                timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
            )

            try:
                store = ConfigStore()
                current_config = store.load() or ProvideChoiceConfig(
                    transport=TRANSPORT_TERMINAL,
                    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                )
                parsed_config = _parse_config_payload(current_config, payload, dummy_req)
                store.save(parsed_config)
                _logger.info(f"Global config saved: transport={parsed_config.transport}, timeout={parsed_config.timeout_seconds}")
                return JSONResponse({
                    "status": "ok",
                    "config": {
                        "transport": parsed_config.transport,
                        "timeout_seconds": parsed_config.timeout_seconds,
                        "single_submit_mode": parsed_config.single_submit_mode,
                        "timeout_default_enabled": parsed_config.timeout_default_enabled,
                        "use_default_option": parsed_config.use_default_option,
                        "timeout_action": parsed_config.timeout_action,
                        "language": parsed_config.language,
                        "notify_new": parsed_config.notify_new,
                        "notify_upcoming": parsed_config.notify_upcoming,
                        "upcoming_threshold": parsed_config.upcoming_threshold,
                        "notify_timeout": parsed_config.notify_timeout,
                        "notify_if_foreground": parsed_config.notify_if_foreground,
                        "notify_if_focused": parsed_config.notify_if_focused,
                        "notify_if_background": parsed_config.notify_if_background,
                        "notify_sound": parsed_config.notify_sound,
                    },
                })
            except Exception as exc:
                _logger.exception(f"Failed to save global config: {exc}")
                raise HTTPException(status_code=500, detail=f"Failed to save config: {str(exc)}") from exc

        # Section: Terminal Hand-off Endpoints
        @app.get("/terminal/{session_id}")
        async def get_terminal_session(session_id: str):  # noqa: ANN201
            """Get terminal session info for the CLI client.
            
            Supports both unified ChoiceSession (new) and TerminalSession (legacy).
            """
            # First, check unified ChoiceSession store (new terminal sessions)
            web_session = self.sessions.get(session_id)
            if web_session is not None:
                if web_session.final_result is not None:
                    return JSONResponse({
                        "status": "completed",
                        "result": {
                            "action_status": web_session.final_result.action_status,
                            "selected_indices": web_session.final_result.selection.selected_indices,
                            "summary": web_session.final_result.selection.summary,
                        },
                    })
                return JSONResponse({
                    "status": "pending",
                    "remaining_seconds": _remaining_seconds(web_session.deadline),
                    "started_at": time.time() - (time.monotonic() - web_session.created_at),  # Convert to wall clock
                    "request": {
                        "title": web_session.req.title,
                        "prompt": web_session.req.prompt,
                        "selection_mode": web_session.req.selection_mode,
                        "options": [
                            {"id": o.id, "description": o.description, "recommended": o.recommended}
                            for o in web_session.req.options
                        ],
                    },
                    "config": {
                        "timeout_seconds": web_session.config_used.timeout_seconds,
                        "single_submit_mode": web_session.config_used.single_submit_mode,
                        "use_default_option": web_session.config_used.use_default_option,
                        "timeout_action": web_session.config_used.timeout_action,
                    },
                })
            
            # Fall back to legacy TerminalSession store
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
                "started_at": session.started_at,
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
            """Submit the result from the terminal CLI client.
            
            Supports both unified ChoiceSession (new) and TerminalSession (legacy).
            """
            action = str(payload.get("action_status", ""))
            selected_indices = payload.get("selected_indices", [])
            option_annotations = payload.get("option_annotations", {})
            global_annotation = payload.get("global_annotation")
            config_payload = payload.get("config") or {}
            if not isinstance(config_payload, dict):
                raise HTTPException(status_code=400, detail="config must be object")

            # First, check unified ChoiceSession store (new terminal sessions)
            web_session = self.sessions.get(session_id)
            if web_session is not None:
                if web_session.final_result is not None:
                    return JSONResponse({"status": "already-set"})

                req = web_session.req
                current_config = web_session.config_used
                url = f"http://{self.host}:{self.port}/terminal/{session_id}"

                if action == "update_settings":
                    parsed_config = _parse_config_payload(current_config, config_payload, req)
                    web_session.config_used = parsed_config
                    try:
                        from ..infra import ConfigStore
                        ConfigStore().save(parsed_config)
                    except Exception:
                        pass
                    return JSONResponse({
                        "status": "ok",
                        "config": {
                            "transport": parsed_config.transport,
                            "timeout_seconds": parsed_config.timeout_seconds,
                            "single_submit_mode": parsed_config.single_submit_mode,
                            "timeout_default_enabled": parsed_config.timeout_default_enabled,
                            "timeout_default_index": parsed_config.timeout_default_index,
                            "use_default_option": parsed_config.use_default_option,
                            "timeout_action": parsed_config.timeout_action,
                        },
                    })

                if action == "switch_to_web":
                    # For unified sessions, just open the web URL - it's the same session
                    # Mark transport as terminal-web to indicate the switch
                    from ..core.models import TRANSPORT_TERMINAL_WEB
                    web_session.transport = TRANSPORT_TERMINAL_WEB
                    parsed_config = _parse_config_payload(current_config, config_payload, req)
                    web_session.config_used = parsed_config
                    try:
                        from ..infra import ConfigStore
                        ConfigStore().save(parsed_config)
                    except Exception:
                        pass
                    return JSONResponse({
                        "status": "ok",
                        "web_url": f"http://{self.host}:{self.port}/choice/{session_id}",
                        "timeout_seconds": parsed_config.timeout_seconds,
                    })

                if action == "cancelled":
                    from ..core.response import cancelled_response
                    response = cancelled_response(
                        transport=TRANSPORT_WEB,
                        url=url,
                        option_annotations=option_annotations if isinstance(option_annotations, dict) else {},
                        global_annotation=str(global_annotation) if global_annotation else None,
                    )
                elif action == "selected":
                    if not isinstance(selected_indices, list):
                        raise HTTPException(status_code=400, detail="selected_indices must be list")
                    ids = [str(x) for x in selected_indices]
                    valid_ids = {o.id for o in req.options}
                    if any(i not in valid_ids for i in ids):
                        raise HTTPException(status_code=400, detail="selected_indices contains unknown id")
                    response = normalize_response(
                        req=req,
                        selected_indices=ids,
                        transport=TRANSPORT_WEB,
                        url=url,
                        option_annotations=option_annotations if isinstance(option_annotations, dict) else {},
                        global_annotation=str(global_annotation) if global_annotation else None,
                    )
                elif action.startswith("timeout"):
                    response = timeout_response(req=req, transport=TRANSPORT_WEB, url=url)
                else:
                    raise HTTPException(status_code=400, detail="invalid action_status")

                web_session.set_result(response)
                self.save_session_to_store(web_session)
                await self.broadcast_interaction_list()
                return JSONResponse({"status": "ok"})

            # Fall back to legacy TerminalSession store
            from ..terminal.session import get_terminal_session_store
            store = get_terminal_session_store()
            session = store.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="session not found or expired")
            if session.result is not None:
                return JSONResponse({"status": "already-set"})

            if action == "update_settings":
                # Persist updated configuration and apply to current session
                parsed_config = _parse_config_payload(session.config, config_payload, session.req)
                session.config = parsed_config
                try:
                    from ..infra import ConfigStore
                    ConfigStore().save(parsed_config)
                except Exception:
                    pass
                return JSONResponse({
                    "status": "ok",
                    "config": {
                        "transport": parsed_config.transport,
                        "timeout_seconds": parsed_config.timeout_seconds,
                        "single_submit_mode": parsed_config.single_submit_mode,
                        "timeout_default_enabled": parsed_config.timeout_default_enabled,
                        "timeout_default_index": parsed_config.timeout_default_index,
                        "use_default_option": parsed_config.use_default_option,
                        "timeout_action": parsed_config.timeout_action,
                    },
                })

            if action == "switch_to_web":
                parsed_config = _parse_config_payload(session.config, config_payload, session.req)
                session.config = parsed_config
                try:
                    from ..infra import ConfigStore
                    ConfigStore().save(parsed_config)
                except Exception:
                    pass

                server = await _get_server()
                web_session = await server.create_session(session.req, parsed_config, allow_terminal=False)
                # Mark the new web session as terminal-web to indicate the switch
                from ..core.models import TRANSPORT_TERMINAL_WEB
                web_session.transport = TRANSPORT_TERMINAL_WEB

                async def bridge_web_result() -> None:
                    try:
                        result = await web_session.wait_for_result()
                        session.set_result(result)
                    except Exception:
                        pass

                asyncio.create_task(bridge_web_result())
                return JSONResponse({
                    "status": "ok",
                    "web_url": web_session.url,
                    "timeout_seconds": parsed_config.timeout_seconds,
                })

            if action == "cancelled":
                from ..core.response import cancelled_response
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
            # Save terminal session to persistent store
            self._save_terminal_session(session)
            await self.broadcast_interaction_list()
            return JSONResponse({"status": "ok"})

        # Section: Interaction List Endpoints
        @app.get("/api/interactions")
        async def get_interactions():  # noqa: ANN201
            """Get the list of all interactions (active + recent completed)."""
            interactions = self.get_interaction_list()
            _logger.debug(f"GET /api/interactions: returning {len(interactions)} entries")
            for i in interactions:
                _logger.debug(f"  - {i.session_id[:8]}: status={i.status.value}, transport={i.transport}")
            return JSONResponse({
                "interactions": [i.to_dict() for i in interactions],
            })

        @app.get("/api/interaction/{interaction_id}")
        async def get_interaction_detail(interaction_id: str):  # noqa: ANN201
            """Get detailed information for a specific interaction (for in-page navigation)."""
            # Try active session first
            session = self.sessions.get(interaction_id)
            if session:
                from ..infra import ConfigStore
                latest_config = ConfigStore().load()
                display_defaults = session.effective_defaults()
                if latest_config:
                    display_defaults = ProvideChoiceConfig(
                        transport=latest_config.transport,
                        timeout_seconds=latest_config.timeout_seconds,
                        single_submit_mode=latest_config.single_submit_mode,
                        timeout_default_enabled=latest_config.timeout_default_enabled,
                        timeout_default_index=display_defaults.timeout_default_index,
                        use_default_option=latest_config.use_default_option,
                        timeout_action=latest_config.timeout_action,
                        language=latest_config.language,
                        notify_new=latest_config.notify_new,
                        notify_upcoming=latest_config.notify_upcoming,
                        upcoming_threshold=latest_config.upcoming_threshold,
                        notify_timeout=latest_config.notify_timeout,
                        notify_if_foreground=latest_config.notify_if_foreground,
                        notify_if_focused=latest_config.notify_if_focused,
                        notify_if_background=latest_config.notify_if_background,
                        notify_sound=latest_config.notify_sound,
                    )
                return JSONResponse({
                    "type": "active",
                    "choice_id": session.choice_id,
                    "title": session.req.title,
                    "prompt": session.req.prompt,
                    "selection_mode": session.req.selection_mode,
                    "options": [
                        {"id": o.id, "description": o.description, "recommended": o.recommended}
                        for o in session.req.options
                    ],
                    "allow_terminal": session.allow_terminal,
                    "invocation_time": session.invocation_time,
                    "session_state": session.to_template_state(),
                    "config": {
                        "transport": display_defaults.transport,
                        "timeout_seconds": display_defaults.timeout_seconds,
                        "single_submit_mode": display_defaults.single_submit_mode,
                        "timeout_default_enabled": display_defaults.timeout_default_enabled,
                        "timeout_default_index": display_defaults.timeout_default_index,
                        "use_default_option": display_defaults.use_default_option,
                        "timeout_action": display_defaults.timeout_action,
                        "language": display_defaults.language,
                    },
                    "remaining_seconds": _remaining_seconds(session.deadline),
                })

            # Try persisted session
            from ..store.interaction_store import get_interaction_store
            store = get_interaction_store()
            persisted = store.get_by_id(interaction_id)
            if not persisted or not persisted.result or persisted.transport != TRANSPORT_WEB:
                raise HTTPException(status_code=404)

            from ..infra import ConfigStore
            latest_config = ConfigStore().load()
            if latest_config:
                config_dict = {
                    "transport": latest_config.transport,
                    "timeout_seconds": latest_config.timeout_seconds,
                    "single_submit_mode": latest_config.single_submit_mode,
                    "timeout_default_enabled": latest_config.timeout_default_enabled,
                    "timeout_default_index": latest_config.timeout_default_index,
                    "use_default_option": latest_config.use_default_option,
                    "timeout_action": latest_config.timeout_action,
                    "language": latest_config.language,
                }
            else:
                config_dict = {
                    "transport": TRANSPORT_WEB,
                    "timeout_seconds": persisted.timeout_seconds or DEFAULT_TIMEOUT_SECONDS,
                }

            selection = persisted.result.get("selection", {}) if isinstance(persisted.result, dict) else {}
            action_status = str(persisted.result.get("action_status", "submitted")) if isinstance(persisted.result, dict) else "submitted"

            return JSONResponse({
                "type": "persisted",
                "choice_id": persisted.session_id,
                "title": persisted.title,
                "prompt": persisted.prompt,
                "selection_mode": persisted.selection_mode,
                "options": persisted.options or [],
                "allow_terminal": False,
                "invocation_time": persisted.started_at,
                "session_state": {
                    "status": InteractionStatus.from_action_status(action_status).value,
                    "action_status": action_status,
                    "selected_indices": selection.get("selected_indices", []),
                    "option_annotations": selection.get("option_annotations", {}),
                    "global_annotation": selection.get("global_annotation"),
                },
                "config": config_dict,
                "remaining_seconds": None,
            })

        @app.websocket("/ws/interactions")
        async def interaction_list_ws(websocket: WebSocket) -> None:
            """WebSocket for real-time interaction list updates."""
            await websocket.accept()
            self._list_connections.add(websocket)
            try:
                # Send initial list
                interactions = self.get_interaction_list()
                await websocket.send_json({
                    "type": "list",
                    "interactions": [i.to_dict() for i in interactions],
                })
                while True:
                    # Keep connection alive, handle pings
                    try:
                        message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                        try:
                            data = json.loads(message)
                            if data.get("type") == "ping":
                                await websocket.send_json({"type": "pong"})
                        except json.JSONDecodeError:
                            pass  # Ignore malformed messages
                    except asyncio.TimeoutError:
                        # Send periodic keepalive
                        try:
                            await websocket.send_json({"type": "ping"})
                        except Exception:
                            break  # Connection lost
            except WebSocketDisconnect:
                pass
            except Exception as e:
                _logger.debug(f"Interaction list WebSocket error: {e}")
            finally:
                self._list_connections.discard(websocket)

    async def ensure_running(self) -> None:
        if self._server_task and not self._server_task.done():
            return
        # Initialize interaction store and cleanup expired sessions
        from ..store.interaction_store import get_interaction_store
        store = get_interaction_store()
        store.load()
        cleaned = store.cleanup()
        if cleaned > 0:
            _logger.info(f"Cleaned up {cleaned} expired sessions on startup")

        _logger.info(f"Starting web server on http://{self.host}:{self.port}")
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="error")
        self._server = uvicorn.Server(config)
        assert self._server is not None
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
        now = time.monotonic()
        deadline = _deadline_from_seconds(defaults.timeout_seconds, now=now)
        invocation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            created_at=now,
            invocation_time=invocation_time,
        )
        session.monitor_task = asyncio.create_task(session.monitor_deadline())
        self.sessions[choice_id] = session
        _logger.info(f"Created session {choice_id[:8]}: title='{req.title}', timeout={defaults.timeout_seconds}s")
        # Broadcast updated interaction list
        await self.broadcast_interaction_list()
        return session

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(10)
            now = time.monotonic()
            expired = [cid for cid, session in self.sessions.items() if session.is_expired(now)]
            for cid in expired:
                _logger.debug(f"Cleaning up expired session {cid[:8]}")
                await self._remove_session(cid)

    async def _remove_session(self, choice_id: str) -> None:
        session = self.sessions.pop(choice_id, None)
        if not session:
            return
        _logger.debug(f"Removed session {choice_id[:8]}")
        await session.close()
        # Broadcast updated list after removal
        await self.broadcast_interaction_list()

    def get_interaction_list(self) -> list:
        """Get the interaction list: all active + up to 5 most recent completed.

        Combines web sessions, terminal sessions, and persisted historical sessions
        into a unified list, sorted by status (active first) and then by start time
        (newest first).
        """
        from ..core.models import InteractionEntry, InteractionStatus
        from ..terminal.session import get_terminal_session_store
        from ..store.interaction_store import get_interaction_store

        entries: list[InteractionEntry] = []

        # Collect web sessions (always use current host/port relative URL)
        # Note: This now includes both web and terminal sessions (unified storage)
        _logger.debug(f"[get_interaction_list] self.sessions has {len(self.sessions)} entries")
        for sid, session in self.sessions.items():
            _logger.debug(f"[get_interaction_list] Session {sid[:8]}: final_result={session.final_result is not None}, status={session.status}, transport={session.transport}")
            entry = session.to_interaction_entry()
            # Set relative URL based on transport type and status
            if entry.transport in (TRANSPORT_WEB, TRANSPORT_TERMINAL_WEB):
                entry.url = f"/choice/{entry.session_id}"
            elif entry.transport == TRANSPORT_TERMINAL and entry.status != InteractionStatus.PENDING:
                # Completed terminal sessions can be viewed in web UI
                entry.url = f"/choice/{entry.session_id}"
            else:
                entry.url = None  # Pending terminal sessions are not clickable in web UI
            _logger.debug(f"[get_interaction_list] Entry {sid[:8]}: status={entry.status.value}")
            entries.append(entry)

        # Collect legacy terminal sessions (for backward compatibility)
        # New terminal sessions use unified ChoiceSession storage above
        terminal_store = get_terminal_session_store()
        for session in terminal_store._sessions.values():
            entries.append(session.to_interaction_entry())

        # Separate active and completed from in-memory sessions
        active = [e for e in entries if e.status == InteractionStatus.PENDING]
        in_memory_completed = [e for e in entries if e.status != InteractionStatus.PENDING]
        in_memory_ids = {e.session_id for e in entries}

        # Get persisted historical sessions (exclude those already in memory)
        store = get_interaction_store()
        persisted = store.get_recent(limit=_MAX_RECENT_COMPLETED)
        historical: list[InteractionEntry] = []
        for entry in persisted:
            if entry.session_id in in_memory_ids:
                continue
            if entry.transport in (TRANSPORT_WEB, TRANSPORT_TERMINAL_WEB):
                entry.url = f"/choice/{entry.session_id}"
            elif entry.transport == TRANSPORT_TERMINAL and entry.status != InteractionStatus.PENDING:
                # Completed terminal sessions can be viewed in web UI
                entry.url = f"/choice/{entry.session_id}"
            else:
                entry.url = None
            historical.append(entry)

        # Combine completed sessions from both sources
        all_completed = in_memory_completed + historical

        # Sort: active by start time (newest first), completed by start time (newest first)
        active.sort(key=lambda e: e.started_at, reverse=True)
        all_completed.sort(key=lambda e: e.started_at, reverse=True)

        # Limit completed to 5 most recent
        all_completed = all_completed[:_MAX_RECENT_COMPLETED]

        return active + all_completed

    def save_session_to_store(self, session: ChoiceSession) -> None:
        """Save a completed session to the persistent store."""
        from ..store.interaction_store import get_interaction_store
        from datetime import datetime

        if not session.final_result:
            return

        store = get_interaction_store()
        completed_at = datetime.now().isoformat() if session.completed_at else None
        store.save_session(
            session_id=session.choice_id,
            req=session.req,
            result=session.final_result,
            started_at=session.invocation_time,
            completed_at=completed_at,
            url=session.url,
            transport=TRANSPORT_WEB,
        )

    def _save_terminal_session(self, session: "TerminalSession") -> None:
        """Save a completed terminal session to the persistent store."""
        from ..store.interaction_store import get_interaction_store
        from ..core.models import TRANSPORT_TERMINAL

        if not session.result:
            return

        store = get_interaction_store()
        completed_at = datetime.now().isoformat()
        store.save_session(
            session_id=session.session_id,
            req=session.req,
            result=session.result,
            started_at=session.started_at_iso,
            completed_at=completed_at,
            url=None,
            transport=TRANSPORT_TERMINAL,
        )

    async def broadcast_interaction_list(self) -> None:
        """Broadcast the interaction list to all connected WebSocket clients."""
        interactions = self.get_interaction_list()
        _logger.debug(f"Broadcasting interaction list: {len(interactions)} entries, {len(self._list_connections)} connections")
        if not self._list_connections:
            return
        payload = {
            "type": "list",
            "interactions": [i.to_dict() for i in interactions],
        }
        stale: set[WebSocket] = set()
        for ws in list(self._list_connections):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.add(ws)
        for ws in stale:
            self._list_connections.discard(ws)


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

    # Parse language field
    language_raw = payload.get("language")
    language = defaults.language
    if isinstance(language_raw, str) and language_raw in VALID_LANGUAGES:
        language = language_raw

    # Parse notification fields
    notify_new = payload.get("notify_new")
    if not isinstance(notify_new, bool):
        notify_new = defaults.notify_new

    notify_upcoming = payload.get("notify_upcoming")
    if not isinstance(notify_upcoming, bool):
        notify_upcoming = defaults.notify_upcoming

    upcoming_threshold_raw = payload.get("upcoming_threshold")
    upcoming_threshold = defaults.upcoming_threshold
    if isinstance(upcoming_threshold_raw, (int, float, str)):
        try:
            upcoming_threshold = int(upcoming_threshold_raw)
        except Exception:
            upcoming_threshold = defaults.upcoming_threshold

    notify_timeout = payload.get("notify_timeout")
    if not isinstance(notify_timeout, bool):
        notify_timeout = defaults.notify_timeout

    notify_if_foreground = payload.get("notify_if_foreground")
    if not isinstance(notify_if_foreground, bool):
        notify_if_foreground = defaults.notify_if_foreground

    notify_if_focused = payload.get("notify_if_focused")
    if not isinstance(notify_if_focused, bool):
        notify_if_focused = defaults.notify_if_focused

    notify_if_background = payload.get("notify_if_background")
    if not isinstance(notify_if_background, bool):
        notify_if_background = defaults.notify_if_background

    notify_sound = payload.get("notify_sound")
    if not isinstance(notify_sound, bool):
        notify_sound = defaults.notify_sound

    return ProvideChoiceConfig(
        transport=transport,
        timeout_seconds=timeout_val,
        single_submit_mode=single_submit_val,
        timeout_default_enabled=timeout_default_enabled,
        timeout_default_index=timeout_default_idx,
        use_default_option=use_default_option,
        timeout_action=timeout_action,
        language=language,
        notify_new=notify_new,
        notify_upcoming=notify_upcoming,
        upcoming_threshold=upcoming_threshold,
        notify_timeout=notify_timeout,
        notify_if_foreground=notify_if_foreground,
        notify_if_focused=notify_if_focused,
        notify_if_background=notify_if_background,
        notify_sound=notify_sound,
    )


# Section: Terminal Hand-off Functions
async def create_terminal_handoff_session(
    req: ProvideChoiceRequest,
    config: ProvideChoiceConfig,
) -> ProvideChoiceResponse:
    """Create a terminal hand-off session and return immediately with launch info.
    
    This function:
    1. Ensures the web server is running
    2. Creates a unified ChoiceSession (shared with web)
    3. Returns a `pending_terminal_launch` response with the launch command
    
    The agent should then:
    1. Run the returned command to open the terminal UI
    2. Call poll_selection to wait for the result
    
    Note: Terminal sessions now use the same ChoiceSession as web sessions,
    allowing seamless switching between terminal and web interfaces.
    """
    from ..core.response import pending_terminal_launch_response
    from ..core.models import TRANSPORT_TERMINAL

    server = await _get_server()
    
    # Create a unified ChoiceSession (same as web, but marked for terminal use)
    session = await server.create_session(req, config, allow_terminal=False)
    # Mark this session as terminal transport for display purposes
    session.transport = TRANSPORT_TERMINAL
    session.url = f"http://{server.host}:{server.port}/terminal/{session.choice_id}"
    
    launch_command = f"uv run python -m src.terminal.client --session {session.choice_id} --url http://{server.host}:{server.port}"

    return pending_terminal_launch_response(
        session_id=session.choice_id,
        url=session.url,
        launch_command=launch_command,
    )


async def poll_session_result(session_id: str) -> Optional[ProvideChoiceResponse]:
    """Poll for the result of any session (web or terminal) with blocking wait.
    
    This is the unified polling function that checks both web and terminal sessions.
    It implements a smart polling mechanism that:
    1. Returns immediately if the result is already available
    2. Waits up to 30 seconds for the result if still pending
    3. Returns None only if session not found in both stores
    4. Returns timeout response if session expired
    
    Args:
        session_id: The session ID to poll (from either web or terminal)
        
    Returns:
        The ProvideChoiceResponse if available, or None if session not found
    """
    from ..core.response import timeout_response

    # Internal wait time - fixed at 30s for consistent behavior
    wait_seconds = 30

    # First, check web sessions
    server = await _get_server()
    web_session = server.sessions.get(session_id)
    
    if web_session is not None:
        # Web session found - wait on it
        if web_session.final_result is not None:
            return web_session.final_result
        
        # Wait for result with timeout
        remaining = _remaining_seconds(web_session.deadline)
        effective_wait = min(wait_seconds, remaining)
        if effective_wait > 0:
            try:
                result = await asyncio.wait_for(web_session.wait_for_result(), timeout=effective_wait)
                return result
            except asyncio.TimeoutError:
                pass
        
        # Check final result after waiting
        if web_session.final_result is not None:
            return web_session.final_result
        
        # Still pending - return None to indicate caller should poll again
        return None
    
    # Fall back to terminal session store for backwards compatibility
    return await poll_terminal_session_result(session_id, wait_seconds=wait_seconds)


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
    from ..core.response import timeout_response

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
