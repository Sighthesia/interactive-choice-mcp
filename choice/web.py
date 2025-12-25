from __future__ import annotations

import asyncio
import socket
import uuid
import webbrowser
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from .models import (
    ProvideChoiceOption,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    cancelled_response,
    normalize_response,
    timeout_response,
    TRANSPORT_WEB,
)


# Section: Utility Functions
def _find_free_port() -> int:
    """Find an available ephemeral port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# Section: HTML Rendering
def _render_html(req: ProvideChoiceRequest, choice_id: str) -> str:
    """
    Generate the HTML content for the choice interface.
    
    Includes:
    - Option buttons
    - Custom input field (if applicable)
    - Cancel button (if allowed)
    - JavaScript for handling interactions and submitting data
    """
    option_buttons = "".join(
        f"""
        <div class='option'>
            <button onclick=selectOption('{o.id}')>{o.label}</button>
            <div class='desc'>{o.description}</div>
        </div>
        """
        for o in req.options
    )

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

    return f"""
<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <title>{req.title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 720px; margin: 24px auto; }}
    h1 {{ margin-bottom: 8px; }}
    .prompt {{ margin-bottom: 16px; }}
    .option {{ margin: 8px 0; }}
    .option button {{ padding: 8px 12px; }}
    .desc {{ color: #555; font-size: 14px; margin-left: 8px; display: inline-block; }}
    .custom {{ margin-top: 16px; display: flex; gap: 8px; }}
    .custom input {{ flex: 1; padding: 8px; }}
    .cancel {{ margin-top: 16px; background: #eee; }}
  </style>
</head>
<body>
  <h1>{req.title}</h1>
  <div class='prompt'>{req.prompt}</div>
  <div id='status'></div>
  <div id='options'>{option_buttons}</div>
  {custom_block}
  {cancel_block}
  <script>
    const choiceId = '{choice_id}';
    let submitting = false;

    async function postSelection(payload) {{
      if (submitting) return;
      submitting = true;
      const res = await fetch(`/choice/${{choiceId}}/submit`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload)
      }});
      if (!res.ok) {{
        document.getElementById('status').innerText = 'Submit failed';
        submitting = false;
      }} else {{
        document.getElementById('status').innerText = 'Submitted, you can close this tab.';
      }}
    }}

    async function selectOption(id) {{
      postSelection({{ action_status: 'selected', selected_ids: [id] }});
    }}

    async function submitCustom() {{
      const val = document.getElementById('customInput').value || '';
      postSelection({{ action_status: 'custom_input', custom_input: val }});
    }}

    async function submitCancel() {{
      postSelection({{ action_status: 'cancelled' }});
    }}
  </script>
</body>
</html>
"""


async def run_web_choice(req: ProvideChoiceRequest, *, timeout_seconds: int) -> ProvideChoiceResponse:
    choice_id = uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    result_future: asyncio.Future[ProvideChoiceResponse] = loop.create_future()

    app = FastAPI()

    @app.get("/choice/{incoming_id}")
    async def choice_page(incoming_id: str):
        if incoming_id != choice_id:
            raise HTTPException(status_code=404)
        return HTMLResponse(_render_html(req, choice_id))

    @app.post("/choice/{incoming_id}/submit")
    async def submit_choice(incoming_id: str, payload: Dict[str, object]):
        if incoming_id != choice_id:
            raise HTTPException(status_code=404)
        if result_future.done():
            return JSONResponse({"status": "already-set"})
        action = str(payload.get("action_status", ""))
        if action == "cancelled":
            result_future.set_result(cancelled_response(transport=TRANSPORT_WEB, url=session_url))
            return {"status": "ok"}
        if action == "selected":
            selected_ids = payload.get("selected_ids")
            if not isinstance(selected_ids, list):
                raise HTTPException(status_code=400, detail="selected_ids must be list")
            ordered_ids = [str(x) for x in selected_ids]
            result_future.set_result(
                normalize_response(
                    req=req,
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
                    req=req,
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
        result = await asyncio.wait_for(result_future, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        result = timeout_response(transport=TRANSPORT_WEB, url=session_url)
    finally:
        server.should_exit = True
        await server_task

    return result
