from __future__ import annotations

import asyncio
import json
import socket
import uuid
import webbrowser
from pathlib import Path
from string import Template
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
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
        {"id": o.id, "label": o.label, "description": o.description}
        for o in req.options
    ]

    # Build defaults payload for JavaScript
    defaults_payload = {
        "transport": defaults.transport,
        "visible_option_ids": defaults.visible_option_ids,
        "timeout_seconds": defaults.timeout_seconds,
        "placeholder": defaults.placeholder or "",
        "default_selection_ids": defaults.default_selection_ids,
        "min_selections": defaults.min_selections,
        "max_selections": defaults.max_selections,
        "single_submit_mode": defaults.single_submit_mode,
        "placeholder_enabled": defaults.placeholder_enabled,
        "annotations_enabled": defaults.annotations_enabled,
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

    # Compute template substitution values
    max_sel_display = str(defaults.max_selections) if defaults.max_selections is not None else ""
    show_placeholder_row = req.type in {"text_input", "hybrid"}

    # Build custom input block if needed
    custom_block = ""
    if req.type in {"text_input", "hybrid"}:
        placeholder_shown = defaults.placeholder_enabled and (defaults.placeholder or req.placeholder)
        placeholder = (defaults.placeholder or req.placeholder or "Enter a value") if placeholder_shown else ""
        custom_block = f"""
            <div class="card custom-input-section">
                <input id="customInput" type="text" placeholder="{placeholder}" />
                <button class="btn btn-primary" onclick="submitCustom()">Submit Custom</button>
            </div>
        """

    # Load and render external template
    template = _load_template()
    return template.substitute(
        title=req.title,
        prompt=req.prompt,
        prompt_type=req.type,
        choice_id=choice_id,
        defaults_json=json.dumps(defaults_payload),
        options_json=json.dumps(option_payload),
        transport_options="\n".join(transport_options),
        timeout_value=defaults.timeout_seconds,
        single_submit_checked="checked" if defaults.single_submit_mode else "",
        min_selections=defaults.min_selections,
        max_selections=max_sel_display,
        placeholder_row_display="" if show_placeholder_row else "display:none;",
        placeholder_enabled_checked="checked" if defaults.placeholder_enabled else "",
        placeholder_value=defaults.placeholder or "",
        annotations_enabled_checked="checked" if defaults.annotations_enabled else "",
        custom_block_placeholder=custom_block,
    )


async def run_web_choice(
    req: ProvideChoiceRequest,
    *,
    defaults: ProvideChoiceConfig,
    allow_terminal: bool,
) -> tuple[ProvideChoiceResponse, ProvideChoiceConfig]:
    """Run the web-based choice flow with configuration panel."""

    choice_id = uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    result_future: asyncio.Future[ProvideChoiceResponse] = loop.create_future()
    config_used: ProvideChoiceConfig = defaults

    defaults.transport = TRANSPORT_WEB
    app = FastAPI()

    @app.get("/choice/{incoming_id}")
    async def choice_page(incoming_id: str):
        if incoming_id != choice_id:
            raise HTTPException(status_code=404)
        html = _render_html(req, choice_id=choice_id, defaults=defaults, allow_terminal=allow_terminal)
        return HTMLResponse(html)

    @app.post("/choice/{incoming_id}/submit")
    async def submit_choice(incoming_id: str, payload: Dict[str, object]):
        if incoming_id != choice_id:
            raise HTTPException(status_code=404)
        if result_future.done():
            return JSONResponse({"status": "already-set"})
        action = str(payload.get("action_status", ""))
        config_payload = payload.get("config") or {}
        if not isinstance(config_payload, dict):
            raise HTTPException(status_code=400, detail="config must be object")
        try:
            parsed_config = _parse_config_payload(defaults, config_payload, req)
            adjusted_req = apply_configuration(req, parsed_config)
        except ValidationError as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            nonlocal config_used
            config_used = parsed_config

        # Extract annotations from payload
        option_annotations_raw = payload.get("option_annotations") or {}
        option_annotations: dict[str, str] = {}
        if isinstance(option_annotations_raw, dict):
            option_annotations = {str(k): str(v) for k, v in option_annotations_raw.items() if v}
        global_annotation_raw = payload.get("global_annotation")
        global_annotation: str | None = str(global_annotation_raw) if global_annotation_raw else None

        if action == "cancelled":
            result_future.set_result(cancelled_response(transport=TRANSPORT_WEB, url=session_url))
            return {"status": "ok"}
        if action == "selected":
            selected_ids = payload.get("selected_ids")
            if not isinstance(selected_ids, list):
                raise HTTPException(status_code=400, detail="selected_ids must be list")
            ordered_ids = [str(x) for x in selected_ids]
            valid_ids = {opt.id for opt in adjusted_req.options}
            if not set(ordered_ids).issubset(valid_ids):
                raise HTTPException(status_code=400, detail="selected_ids not allowed")
            try:
                result_future.set_result(
                    normalize_response(
                        req=adjusted_req,
                        selected_ids=ordered_ids,
                        custom_input=None,
                        transport=TRANSPORT_WEB,
                        url=session_url,
                        option_annotations=option_annotations,
                        global_annotation=global_annotation,
                    )
                )
            except ValidationError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"status": "ok"}
        if action == "custom_input":
            custom_input = payload.get("custom_input", "")
            result_future.set_result(
                normalize_response(
                    req=adjusted_req,
                    selected_ids=[],
                    custom_input=str(custom_input),
                    transport=TRANSPORT_WEB,
                    url=session_url,
                    global_annotation=global_annotation,
                )
            )
            return {"status": "ok"}
        raise HTTPException(status_code=400, detail="invalid action_status")

    port = _find_free_port()
    session_url = f"http://127.0.0.1:{port}/choice/{choice_id}"

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    async def serve() -> None:
        await server.serve()

    server_task = asyncio.create_task(serve())
    # Best-effort wait for startup
    await asyncio.sleep(0.2)
    try:
        webbrowser.open(session_url)
    except Exception:
        pass

    try:
        result = await asyncio.wait_for(result_future, timeout=defaults.timeout_seconds)
        final_config = config_used
    except asyncio.TimeoutError:
        result = timeout_response(transport=TRANSPORT_WEB, url=session_url)
        final_config = defaults
    finally:
        server.should_exit = True
        await server_task

    return result, final_config


def _parse_config_payload(defaults: ProvideChoiceConfig, payload: Dict[str, object], req: ProvideChoiceRequest) -> ProvideChoiceConfig:
    """Parse config payload from web form submission."""
    transport_raw = payload.get("transport")
    transport = str(transport_raw) if transport_raw else TRANSPORT_WEB
    if transport not in VALID_TRANSPORTS:
        transport = TRANSPORT_WEB

    visible_raw = payload.get("visible_option_ids") or []
    visible_ids: list[str] = []
    if isinstance(visible_raw, list):
        visible_ids = [str(v) for v in visible_raw if any(opt.id == str(v) for opt in req.options)]
    if not visible_ids:
        visible_ids = [opt.id for opt in req.options]

    timeout_raw = payload.get("timeout_seconds")
    timeout_val = defaults.timeout_seconds
    if isinstance(timeout_raw, (int, float, str)):
        try:
            timeout_val = int(timeout_raw)
        except Exception:
            timeout_val = defaults.timeout_seconds
    if timeout_val <= 0:
        timeout_val = defaults.timeout_seconds

    placeholder_raw = payload.get("placeholder")
    placeholder_val = defaults.placeholder
    if isinstance(placeholder_raw, str):
        placeholder_val = placeholder_raw

    # Extended config fields
    default_sel_raw = payload.get("default_selection_ids") or []
    default_sel_ids: list[str] = []
    if isinstance(default_sel_raw, list):
        default_sel_ids = [str(d) for d in default_sel_raw if any(opt.id == str(d) for opt in req.options)]

    min_sel_raw = payload.get("min_selections")
    min_sel_val = defaults.min_selections
    if isinstance(min_sel_raw, (int, float, str)):
        try:
            min_sel_val = int(min_sel_raw)
        except Exception:
            min_sel_val = defaults.min_selections
    if min_sel_val < 0:
        min_sel_val = 0

    max_sel_raw = payload.get("max_selections")
    max_sel_val = defaults.max_selections
    if max_sel_raw is not None:
        if isinstance(max_sel_raw, (int, float, str)):
            try:
                max_sel_val = int(max_sel_raw) if max_sel_raw != "" else None
            except Exception:
                max_sel_val = defaults.max_selections

    single_submit_raw = payload.get("single_submit_mode")
    single_submit_val = defaults.single_submit_mode
    if isinstance(single_submit_raw, bool):
        single_submit_val = single_submit_raw

    placeholder_enabled_raw = payload.get("placeholder_enabled")
    placeholder_enabled_val = defaults.placeholder_enabled
    if isinstance(placeholder_enabled_raw, bool):
        placeholder_enabled_val = placeholder_enabled_raw

    annotations_enabled_raw = payload.get("annotations_enabled")
    annotations_enabled_val = defaults.annotations_enabled
    if isinstance(annotations_enabled_raw, bool):
        annotations_enabled_val = annotations_enabled_raw

    return ProvideChoiceConfig(
        transport=transport,
        visible_option_ids=visible_ids,
        timeout_seconds=timeout_val,
        placeholder=placeholder_val,
        default_selection_ids=default_sel_ids,
        min_selections=min_sel_val,
        max_selections=max_sel_val,
        single_submit_mode=single_submit_val,
        placeholder_enabled=placeholder_enabled_val,
        annotations_enabled=annotations_enabled_val,
    )
