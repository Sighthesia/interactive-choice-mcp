from __future__ import annotations

import asyncio
import json
import socket
import uuid
import webbrowser
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


# Section: Utility Functions
def _find_free_port() -> int:
    """Find an available ephemeral port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


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

    custom_block = ""
    if req.type in {"text_input", "hybrid"}:
        placeholder = req.placeholder or "Enter a value"
        custom_block = f"""
  <div class='custom'>
    <input id='customInput' placeholder='{placeholder}' />
    <button onclick=submitCustom()>Submit</button>
  </div>
        """

    cancel_block = ""
    if req.allow_cancel:
        cancel_block = "<button class='cancel' onclick=submitCancel()>Cancel</button>"

    defaults_payload = {
        "transport": defaults.transport,
        "visible_option_ids": defaults.visible_option_ids,
        "timeout_seconds": defaults.timeout_seconds,
    }

    template = Template(
        """
<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <title>$title</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 820px; margin: 24px auto; }
    h1 { margin-bottom: 8px; }
    .prompt { margin-bottom: 16px; }
    .panel { padding: 12px; border: 1px solid #ddd; margin-bottom: 16px; }
    .option { margin: 8px 0; }
    .option button { padding: 8px 12px; }
    .desc { color: #555; font-size: 14px; margin-left: 8px; display: inline-block; }
    .custom { margin-top: 16px; display: flex; gap: 8px; }
    .custom input { flex: 1; padding: 8px; }
    .cancel { margin-top: 16px; background: #eee; }
    .config-row { margin-bottom: 8px; }
    .options-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; }
  </style>
</head>
<body>
  <h1>$title</h1>
  <div class='prompt'>$prompt</div>
  <div class='panel'>
    <div class='config-row'>
      <label>Transport
        <select id='transportSelect'>
          <option value='web' $transport_selected>Web</option>
        </select>
      </label>
    </div>
    <div class='config-row'>
      <label>Timeout (seconds)
        <input id='timeoutInput' type='number' min='1' value='$timeout_value' />
      </label>
    </div>
    <div class='config-row'>
      <div>Visible options</div>
      <div class='options-grid' id='visibilityToggles'></div>
    </div>
  </div>
  <div id='status'></div>
  <div id='options'></div>
  $custom_block
  $cancel_block
  <script>
    const choiceId = '$choice_id';
    const defaults = $defaults_json;
    const options = $options_json;
    let submitting = false;
    let visibleOptionIds = new Set(defaults.visible_option_ids.length ? defaults.visible_option_ids : options.map(o => o.id));

    function renderVisibilityToggles() {
      const container = document.getElementById('visibilityToggles');
      container.innerHTML = '';
      options.forEach(opt => {
        const wrapper = document.createElement('label');
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = opt.id;
        cb.className = 'vis-toggle';
        cb.checked = visibleOptionIds.has(opt.id);
        cb.onchange = syncVisibilityFromCheckboxes;
        wrapper.appendChild(cb);
        wrapper.appendChild(document.createTextNode(' ' + opt.label));
        container.appendChild(wrapper);
      });
    }

    function renderOptions() {
      const container = document.getElementById('options');
      container.innerHTML = '';
      options.forEach(opt => {
        if (!visibleOptionIds.has(opt.id)) return;
        const block = document.createElement('div');
        block.className = 'option';
        const btn = document.createElement('button');
        btn.innerText = opt.label;
        btn.onclick = () => submitPayload({ action_status: 'selected', selected_ids: [opt.id] });
        const desc = document.createElement('div');
        desc.className = 'desc';
        desc.innerText = opt.description;
        block.appendChild(btn);
        block.appendChild(desc);
        container.appendChild(block);
      });
    }

    function syncVisibilityFromCheckboxes() {
      const checks = Array.from(document.querySelectorAll('.vis-toggle')).filter(cb => cb.checked).map(cb => cb.value);
      if (checks.length === 0) {
        visibleOptionIds = new Set(options.map(o => o.id));
        renderVisibilityToggles();
      } else {
        visibleOptionIds = new Set(checks);
      }
      renderOptions();
    }

    function collectConfig() {
      const rawTimeout = parseInt(document.getElementById('timeoutInput').value || defaults.timeout_seconds, 10);
      const timeout = Number.isFinite(rawTimeout) && rawTimeout > 0 ? rawTimeout : defaults.timeout_seconds;
      const transportSelect = document.getElementById('transportSelect');
      const transport = transportSelect ? transportSelect.value : 'web';
      return {
        transport,
        visible_option_ids: Array.from(visibleOptionIds),
        timeout_seconds: timeout,
      };
    }

    async function postSelection(payload) {
      if (submitting) return;
      submitting = true;
      const res = await fetch('/choice/' + choiceId + '/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        document.getElementById('status').innerText = 'Submit failed';
        submitting = false;
      } else {
        document.getElementById('status').innerText = 'Submitted, you can close this tab.';
      }
    }

    async function selectOption(id) {
      submitPayload({ action_status: 'selected', selected_ids: [id] });
    }

    async function submitCustom() {
      const val = document.getElementById('customInput').value || '';
      submitPayload({ action_status: 'custom_input', custom_input: val });
    }

    async function submitCancel() {
      submitPayload({ action_status: 'cancelled' });
    }

    function submitPayload(base) {
      const config = collectConfig();
      base.config = config;
      postSelection(base);
    }

    renderVisibilityToggles();
    renderOptions();
  </script>
</body>
</html>
        """
    )

    return template.substitute(
        title=req.title,
        prompt=req.prompt,
        transport_selected="selected" if defaults.transport == TRANSPORT_WEB else "",
        timeout_value=defaults.timeout_seconds,
        custom_block=custom_block,
        cancel_block=cancel_block,
        choice_id=choice_id,
        defaults_json=json.dumps(defaults_payload),
        options_json=json.dumps(option_payload),
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
            result_future.set_result(
                normalize_response(
                    req=adjusted_req,
                    selected_ids=ordered_ids,
                    custom_input=None,
                    transport=TRANSPORT_WEB,
                    url=session_url,
                )
            )
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

    return ProvideChoiceConfig(transport=TRANSPORT_WEB, visible_option_ids=visible_ids, timeout_seconds=timeout_val)
