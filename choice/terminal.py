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
def _run_prompt_sync(req: ProvideChoiceRequest) -> ProvideChoiceResponse:
    """
    Execute the synchronous questionary prompt.
    
    This function blocks until the user provides input or cancels.
    It handles the different prompt types (select, checkbox, text, hybrid).
    """
    choices = _build_choices(req.options)

    try:
        if req.type == "single_select":
            answer = questionary.select(req.prompt, choices=choices).unsafe_ask()
            if answer is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            return normalize_response(req=req, selected_ids=[answer], custom_input=None, transport=TRANSPORT_TERMINAL)

        if req.type == "multi_select":
            answer_list = questionary.checkbox(req.prompt, choices=choices).unsafe_ask()
            if answer_list is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            ordered_ids = [str(a) for a in answer_list]
            return normalize_response(req=req, selected_ids=ordered_ids, custom_input=None, transport=TRANSPORT_TERMINAL)

        if req.type == "text_input":
            answer_text = questionary.text(req.prompt, default=req.placeholder or "").unsafe_ask()
            if answer_text is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            return normalize_response(req=req, selected_ids=[], custom_input=str(answer_text), transport=TRANSPORT_TERMINAL)

        if req.type == "hybrid":
            # Hybrid mode: Add a special "Custom input" option to the list
            hybrid_choices = choices + [questionary.Choice(title="Custom input", value="__custom__")]
            picked = questionary.select(req.prompt, choices=hybrid_choices).unsafe_ask()
            if picked is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            if picked == "__custom__":
                custom = questionary.text("Enter value", default=req.placeholder or "").unsafe_ask()
                if custom is None:
                    return cancelled_response(transport=TRANSPORT_TERMINAL)
                return normalize_response(req=req, selected_ids=[], custom_input=str(custom), transport=TRANSPORT_TERMINAL)
            return normalize_response(req=req, selected_ids=[picked], custom_input=None, transport=TRANSPORT_TERMINAL)
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


async def run_terminal_choice(req: ProvideChoiceRequest, *, timeout_seconds: int) -> ProvideChoiceResponse:
    """
    Main entry point for terminal interaction.
    
    Wraps the synchronous prompt in a timeout handler and manages screen clearing.
    """
    result = await _run_with_timeout(lambda: _run_prompt_sync(req), timeout_seconds)
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

            choice_defaults = defaults.visible_option_ids or [opt.id for opt in req.options]
            visible = questionary.checkbox(
                "Visible options", choices=_build_config_choices(req.options, choice_defaults)
            ).unsafe_ask()
            if visible is None:
                return None
            visible_ids = [str(v) for v in visible] or [opt.id for opt in req.options]

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

            return ProvideChoiceConfig(
                transport=chosen_transport,
                visible_option_ids=visible_ids,
                timeout_seconds=timeout_val,
            )
        except KeyboardInterrupt:
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _prompt_sync)
