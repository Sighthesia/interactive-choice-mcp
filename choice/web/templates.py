"""HTML template helpers for the web UI."""
from __future__ import annotations

import json
import time
from pathlib import Path
from string import Template
from typing import Iterable, TYPE_CHECKING

from ..models import TRANSPORT_WEB
from .session import _remaining_seconds

if TYPE_CHECKING:
    from .session import ChoiceSession
    from ..models import ProvideChoiceConfig, ProvideChoiceRequest

__all__ = [
    "_load_template",
    "_load_dashboard_template",
    "_render_html",
    "_render_dashboard",
]


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _load_template() -> Template:
    template_path = _TEMPLATE_DIR / "choice.html"
    return Template(template_path.read_text(encoding="utf-8"))


def _load_dashboard_template() -> Template:
    template_path = _TEMPLATE_DIR / "dashboard.html"
    return Template(template_path.read_text(encoding="utf-8"))


def _render_dashboard(sessions: Iterable["ChoiceSession"]) -> str:
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
    req: "ProvideChoiceRequest",
    *,
    choice_id: str,
    defaults: "ProvideChoiceConfig",
    allow_terminal: bool,
    session_state: dict[str, object],
    invocation_time: str,
) -> str:
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
        invocation_time=invocation_time,
    )
