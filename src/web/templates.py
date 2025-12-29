"""HTML template helpers for the web UI."""
from __future__ import annotations

import json
import time
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from ..infra.i18n import get_text, TEXTS
from ..core.models import TRANSPORT_WEB, LANG_EN
from .bundler import get_asset_bundle

if TYPE_CHECKING:
    from .session import ChoiceSession
    from ..core.models import ProvideChoiceConfig, ProvideChoiceRequest

__all__ = [
    "_load_template",
    "_render_html",
    "_build_css_bundle",
    "_build_js_bundle",
]

# Section: Template Paths
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_LEGACY_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

def _load_template(use_modular: bool = True) -> Template:
    """Load the HTML shell template.
    
    Args:
        use_modular: If True, use the new modular template; otherwise fall back to legacy.
    """
    if use_modular:
        template_path = _TEMPLATE_DIR / "choice_base.html"
    else:
        template_path = _LEGACY_TEMPLATE_DIR / "choice.html"
    return Template(template_path.read_text(encoding="utf-8"))

# Section: Bundle Helpers
def _build_css_bundle(inline: bool = True, base_url: str = "/static") -> str:
    """Build CSS bundle as inline <style> or external <link>.
    
    Args:
        inline: If True, embed CSS directly; otherwise use external link with hash.
        base_url: Base URL for external assets.
    """
    bundle = get_asset_bundle()
    if inline:
        return f"<style>\n{bundle.css}\n</style>"
    return f'<link rel="stylesheet" href="{base_url}/bundle.{bundle.css_hash}.css">'

def _build_js_bundle(inline: bool = True, base_url: str = "/static") -> str:
    """Build JS bundle as inline <script> or external <script src>.
    
    Args:
        inline: If True, embed JS directly; otherwise use external link with hash.
        base_url: Base URL for external assets.
    """
    bundle = get_asset_bundle()
    if inline:
        return f"<script>\n{bundle.js}\n</script>"
    return f'<script src="{base_url}/bundle.{bundle.js_hash}.js"></script>'

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
    use_modular: bool = True,
    inline_assets: bool = True,
) -> str:
    """Render the choice UI HTML.
    
    Args:
        req: The choice request with title, prompt, and options.
        choice_id: Unique session identifier.
        defaults: Configuration defaults for the UI.
        allow_terminal: Whether terminal transport option is available.
        session_state: Current session state for restoration.
        invocation_time: Human-readable timestamp.
        use_modular: Use new modular template (default) vs legacy monolithic.
        inline_assets: Embed CSS/JS inline (default) vs external links.
    """
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

    template = _load_template(use_modular=use_modular)
    
    # Build substitution dict based on template type
    subs = {
        "title": req.title,
        "prompt": req.prompt,
        "prompt_type": req.selection_mode,
        "choice_id": choice_id,
        "defaults_json": json.dumps(defaults_payload),
        "session_state_json": json.dumps(session_state),
        "options_json": json.dumps(option_payload),
        "transport_options": "\n".join(transport_options),
        "timeout_value": defaults.timeout_seconds,
        "single_submit_checked": "checked" if defaults.single_submit_mode else "",
        "mcp_version": "0.1.0",
        "invocation_time": invocation_time,
        "i18n_json": json.dumps(_build_i18n_payload()),
        "lang": lang,
    }
    
    # Add bundle placeholders for modular template
    if use_modular:
        subs["css_bundle"] = _build_css_bundle(inline=inline_assets)
        subs["js_bundle"] = _build_js_bundle(inline=inline_assets)
    
    return template.substitute(**subs)
