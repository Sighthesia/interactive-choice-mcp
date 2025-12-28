"""HTML template helpers for the web UI."""
from __future__ import annotations

import json
import time
from pathlib import Path
from string import Template
from typing import Iterable, TYPE_CHECKING

from ..i18n import get_text, TEXTS
from ..models import TRANSPORT_WEB, LANG_EN
from .session import _remaining_seconds

if TYPE_CHECKING:
    from .session import ChoiceSession
    from ..models import ProvideChoiceConfig, ProvideChoiceRequest

__all__ = [
    "_load_template",
    "_render_html",
]

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

def _load_template() -> Template:
    template_path = _TEMPLATE_DIR / "choice.html"
    return Template(template_path.read_text(encoding="utf-8"))

def _build_i18n_payload() -> dict[str, dict[str, str]]:
    """Build a dict of all i18n texts for all languages.
    
    Returns a nested dict: {key: {lang: text, ...}, ...}
    This allows the frontend to switch languages without reloading.
    """
    return {key: texts.copy() for key, texts in TEXTS.items()}

def _render_html(
    req: "ProvideChoiceRequest",
    *,
    choice_id: str,
    defaults: "ProvideChoiceConfig",
    allow_terminal: bool,
    session_state: dict[str, object],
    invocation_time: str,
) -> str:
    lang = defaults.language if hasattr(defaults, 'language') else LANG_EN
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
        "language": lang,
        "notify_new": defaults.notify_new,
        "notify_upcoming": defaults.notify_upcoming,
        "upcoming_threshold": defaults.upcoming_threshold,
        "notify_timeout": defaults.notify_timeout,
        "notify_if_foreground": defaults.notify_if_foreground,
        "notify_if_focused": defaults.notify_if_focused,
        "notify_if_background": defaults.notify_if_background,
        "notify_sound": defaults.notify_sound,
    }

    transport_options = [
        "<option value='web' {sel}>{label}</option>".format(
            sel="selected" if defaults.transport == TRANSPORT_WEB else "",
            label=get_text("settings.transport_web", lang),
        )
    ]
    if allow_terminal:
        transport_options.append(
            "<option value='terminal' {sel}>{label}</option>".format(
                sel="selected" if defaults.transport != TRANSPORT_WEB else "",
                label=get_text("settings.transport_terminal", lang),
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
        i18n_json=json.dumps(_build_i18n_payload()),
        lang=lang,
    )
