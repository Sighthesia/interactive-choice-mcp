from __future__ import annotations

import asyncio
import sys
from typing import Callable, Iterable, List, Optional

import questionary

from .models import (
    ProvideChoiceConfig,
    ProvideChoiceOption,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    cancelled_response,
    normalize_response,
    timeout_response,
    ValidationError,
    TRANSPORT_TERMINAL,
    TRANSPORT_WEB,
)


# Section: Environment Checks
def is_terminal_available() -> bool:
    """Check if the current process is attached to an interactive terminal."""
    return sys.stdin is not None and sys.stdin.isatty()


def _clear_terminal() -> None:
    """Clear the terminal screen to provide a clean UI for the summary."""
    # ANSI clear screen and move cursor home
    print("\033[2J\033[H", end="")


# Section: UI Construction
def _build_choices(options: Iterable[ProvideChoiceOption]) -> List[questionary.Choice]:
    """Convert internal options to questionary Choice objects."""
    return [questionary.Choice(title=opt.label, value=opt.id) for opt in options]


def _build_config_choices(options: Iterable[ProvideChoiceOption], defaults: List[str]) -> List[questionary.Choice]:
    """Convert options to choices while marking defaults."""
    return [questionary.Choice(title=opt.label, value=opt.id, checked=opt.id in defaults) for opt in options]


def _summary_line(selection: ProvideChoiceResponse) -> str:
    """Generate a concise summary string for the final output."""
    sel = selection.selection
    if sel.custom_input:
        return f"Custom input: {sel.custom_input}"
    if sel.selected_ids:
        return f"Selected: {sel.selected_ids}"
    return "No selection"


# Section: Interaction Logic
def _run_prompt_sync(
    req: ProvideChoiceRequest,
    config: Optional[ProvideChoiceConfig] = None,
) -> ProvideChoiceResponse:
    """
    Execute the synchronous questionary prompt.
    
    This function blocks until the user provides input or cancels.
    It handles the different prompt types (select, checkbox, text, hybrid),
    respects single_submit_mode, default selections, and annotations.
    """
    choices = _build_choices(req.options)
    default_ids = set(req.default_selection_ids) if req.default_selection_ids else set()
    annotations_enabled = config.annotations_enabled if config else False
    option_annotations: dict[str, str] = {}
    global_annotation: Optional[str] = None

    try:
        # Single select: auto-submit or select from list
        if req.type == "single_select":
            default_val = req.default_selection_ids[0] if req.default_selection_ids else None
            answer = questionary.select(req.prompt, choices=choices, default=default_val).unsafe_ask()
            if answer is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)

            # Capture optional annotation for the selected option
            if annotations_enabled:
                opt_note = questionary.text(f"Note for '{answer}' (optional)", default="").unsafe_ask()
                if opt_note:
                    option_annotations[answer] = opt_note
                global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask() or None

            return normalize_response(
                req=req,
                selected_ids=[answer],
                custom_input=None,
                transport=TRANSPORT_TERMINAL,
                option_annotations=option_annotations,
                global_annotation=global_annotation,
            )

        # Multi select or batch submission mode
        if req.type == "multi_select" or (req.type == "single_select" and not req.single_submit_mode):
            default_checked = [questionary.Choice(title=opt.label, value=opt.id, checked=opt.id in default_ids) for opt in req.options]
            answer_list = questionary.checkbox(req.prompt, choices=default_checked).unsafe_ask()
            if answer_list is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            ordered_ids = [str(a) for a in answer_list]

            # Capture per-option annotations
            if annotations_enabled:
                for oid in ordered_ids:
                    opt_note = questionary.text(f"Note for '{oid}' (optional)", default="").unsafe_ask()
                    if opt_note:
                        option_annotations[oid] = opt_note
                global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask() or None

            return normalize_response(
                req=req,
                selected_ids=ordered_ids,
                custom_input=None,
                transport=TRANSPORT_TERMINAL,
                option_annotations=option_annotations,
                global_annotation=global_annotation,
            )

        if req.type == "text_input":
            placeholder_text = req.placeholder if req.placeholder_enabled and req.placeholder else ""
            answer_text = questionary.text(req.prompt, default=placeholder_text).unsafe_ask()
            if answer_text is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)

            if annotations_enabled:
                global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask() or None

            return normalize_response(
                req=req,
                selected_ids=[],
                custom_input=str(answer_text),
                transport=TRANSPORT_TERMINAL,
                global_annotation=global_annotation,
            )

        if req.type == "hybrid":
            # Hybrid mode: Add a special "Custom input" option to the list
            hybrid_choices = choices + [questionary.Choice(title="Custom input", value="__custom__")]
            default_val = req.default_selection_ids[0] if req.default_selection_ids else None
            picked = questionary.select(req.prompt, choices=hybrid_choices, default=default_val).unsafe_ask()
            if picked is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            if picked == "__custom__":
                placeholder_text = req.placeholder if req.placeholder_enabled and req.placeholder else ""
                custom = questionary.text("Enter value", default=placeholder_text).unsafe_ask()
                if custom is None:
                    return cancelled_response(transport=TRANSPORT_TERMINAL)

                if annotations_enabled:
                    global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask() or None

                return normalize_response(
                    req=req,
                    selected_ids=[],
                    custom_input=str(custom),
                    transport=TRANSPORT_TERMINAL,
                    global_annotation=global_annotation,
                )

            if annotations_enabled:
                opt_note = questionary.text(f"Note for '{picked}' (optional)", default="").unsafe_ask()
                if opt_note:
                    option_annotations[picked] = opt_note
                global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask() or None

            return normalize_response(
                req=req,
                selected_ids=[picked],
                custom_input=None,
                transport=TRANSPORT_TERMINAL,
                option_annotations=option_annotations,
                global_annotation=global_annotation,
            )
    except KeyboardInterrupt:
        return cancelled_response(transport=TRANSPORT_TERMINAL)

    raise ValidationError(f"Unsupported type: {req.type}")


async def _run_with_timeout(func: Callable[[], ProvideChoiceResponse], timeout_seconds: int) -> ProvideChoiceResponse:
    """Run a blocking function in a separate thread with a timeout."""
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, func), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return timeout_response(transport=TRANSPORT_TERMINAL)


async def run_terminal_choice(
    req: ProvideChoiceRequest,
    *,
    timeout_seconds: int,
    config: Optional[ProvideChoiceConfig] = None,
) -> ProvideChoiceResponse:
    """
    Main entry point for terminal interaction.
    
    Wraps the synchronous prompt in a timeout handler and manages screen clearing.
    """
    result = await _run_with_timeout(lambda: _run_prompt_sync(req, config), timeout_seconds)
    _clear_terminal()
    print(_summary_line(result))
    return result


async def prompt_configuration(
    req: ProvideChoiceRequest,
    *,
    defaults: ProvideChoiceConfig,
    allow_web: bool,
) -> Optional[ProvideChoiceConfig]:
    """Collect configuration inputs before showing the main prompt."""

    def _prompt_sync() -> Optional[ProvideChoiceConfig]:
        transports = [questionary.Choice(title="Terminal", value=TRANSPORT_TERMINAL)]
        if allow_web:
            transports.append(questionary.Choice(title="Web", value=TRANSPORT_WEB))
        try:
            chosen_transport = questionary.select(
                "Transport", choices=transports, default=defaults.transport if defaults.transport in {c.value for c in transports} else TRANSPORT_TERMINAL
            ).unsafe_ask()
            if chosen_transport is None:
                return None

            # Visible options selection
            choice_defaults = defaults.visible_option_ids or [opt.id for opt in req.options]
            visible = questionary.checkbox(
                "Visible options", choices=_build_config_choices(req.options, choice_defaults)
            ).unsafe_ask()
            if visible is None:
                return None
            visible_ids = [str(v) for v in visible] or [opt.id for opt in req.options]

            # Timeout
            timeout_input = questionary.text(
                "Timeout (seconds)", default=str(defaults.timeout_seconds)
            ).unsafe_ask()
            if timeout_input is None:
                return None
            try:
                timeout_val = int(timeout_input)
            except Exception:
                timeout_val = defaults.timeout_seconds
            if timeout_val <= 0:
                timeout_val = defaults.timeout_seconds

            # Placeholder (for text-capable modes)
            placeholder_default = defaults.placeholder if defaults.placeholder is not None else (req.placeholder or "")
            placeholder_value = placeholder_default
            if req.type in {"text_input", "hybrid"}:
                placeholder_input = questionary.text("Placeholder (for text entry)", default=placeholder_default).unsafe_ask()
                if placeholder_input is None:
                    return None
                placeholder_value = placeholder_input

            # Single submit mode toggle
            single_submit_choice = questionary.confirm(
                "Single submit mode (auto-submit on selection)", default=defaults.single_submit_mode
            ).unsafe_ask()
            if single_submit_choice is None:
                return None

            # Default selections
            default_sel_defaults = defaults.default_selection_ids or []
            default_sel = questionary.checkbox(
                "Default selections", choices=_build_config_choices(req.options, default_sel_defaults)
            ).unsafe_ask()
            if default_sel is None:
                return None
            default_sel_ids = [str(d) for d in default_sel]

            # Min/max selections
            min_sel_input = questionary.text(
                "Min selections", default=str(defaults.min_selections)
            ).unsafe_ask()
            if min_sel_input is None:
                return None
            try:
                min_sel_val = int(min_sel_input)
            except Exception:
                min_sel_val = defaults.min_selections
            if min_sel_val < 0:
                min_sel_val = 0

            max_sel_default = str(defaults.max_selections) if defaults.max_selections is not None else ""
            max_sel_input = questionary.text(
                "Max selections (empty = no limit)", default=max_sel_default
            ).unsafe_ask()
            if max_sel_input is None:
                return None
            max_sel_val: Optional[int] = None
            if max_sel_input.strip():
                try:
                    max_sel_val = int(max_sel_input)
                except Exception:
                    max_sel_val = defaults.max_selections

            # Placeholder enabled toggle (text modes)
            placeholder_enabled_choice = defaults.placeholder_enabled
            if req.type in {"text_input", "hybrid"}:
                placeholder_enabled_choice = questionary.confirm(
                    "Show placeholder", default=defaults.placeholder_enabled
                ).unsafe_ask()
                if placeholder_enabled_choice is None:
                    return None

            # Annotations enabled toggle
            annotations_enabled_choice = questionary.confirm(
                "Enable annotations", default=defaults.annotations_enabled
            ).unsafe_ask()
            if annotations_enabled_choice is None:
                return None

            return ProvideChoiceConfig(
                transport=chosen_transport,
                visible_option_ids=visible_ids,
                timeout_seconds=timeout_val,
                placeholder=str(placeholder_value) if placeholder_value != "" else None,
                default_selection_ids=default_sel_ids,
                min_selections=min_sel_val,
                max_selections=max_sel_val,
                single_submit_mode=bool(single_submit_choice),
                placeholder_enabled=bool(placeholder_enabled_choice),
                annotations_enabled=bool(annotations_enabled_choice),
            )
        except KeyboardInterrupt:
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _prompt_sync)
