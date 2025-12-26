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
    """Convert internal options to questionary Choice objects using indices as values."""
    return [questionary.Choice(title=opt.label, value=idx) for idx, opt in enumerate(options)]


def _build_config_choices(options: Iterable[ProvideChoiceOption], defaults: List[int]) -> List[questionary.Choice]:
    """Convert options to choices while marking defaults by index."""
    return [questionary.Choice(title=opt.label, value=idx, checked=idx in defaults) for idx, opt in enumerate(options)]


def _summary_line(selection: ProvideChoiceResponse) -> str:
    """Generate a concise summary string for the final output."""
    sel = selection.selection
    if sel.selected_indices:
        return f"Selected indices: {sel.selected_indices}"
    return "No selection"


# Section: Interaction Logic
def _run_prompt_sync(
    req: ProvideChoiceRequest,
    config: Optional[ProvideChoiceConfig] = None,  # noqa: ARG001
) -> ProvideChoiceResponse:
    """
    Execute the synchronous questionary prompt.
    
    This function blocks until the user provides input or cancels.
    It handles the different prompt types (select, checkbox, text, hybrid),
    respects single_submit_mode, and annotations (always enabled).
    """
    choices = _build_choices(req.options)
    option_annotations: dict[int, str] = {}
    global_annotation: Optional[str] = None

    try:
        # Single select: auto-submit or select from list
        if req.type == "single_select":
            answer = questionary.select(req.prompt, choices=choices).unsafe_ask()
            if answer is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)

            # Capture optional annotation for the selected option
            try:
                opt_note = questionary.text(f"Note for '{req.options[answer].label}' (optional)", default="").unsafe_ask()
            except (KeyboardInterrupt, EOFError, Exception):
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            if opt_note:
                option_annotations[answer] = opt_note
            try:
                global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask()
            except (KeyboardInterrupt, EOFError, Exception):
                return cancelled_response(
                    transport=TRANSPORT_TERMINAL,
                    option_annotations=option_annotations,
                )

            return normalize_response(
                req=req,
                selected_indices=[answer],
                transport=TRANSPORT_TERMINAL,
                option_annotations=option_annotations,
                global_annotation=global_annotation or None,
            )

        # Multi select or batch submission mode
        if req.type == "multi_select" or (req.type == "single_select" and not req.single_submit_mode):
            answer = questionary.checkbox(req.prompt, choices=choices).unsafe_ask()
            if answer is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)

            # Capture annotations for selected options
            for idx in answer:
                try:
                    opt_note = questionary.text(f"Note for '{req.options[idx].label}' (optional)", default="").unsafe_ask()
                except (KeyboardInterrupt, EOFError, Exception):
                    return cancelled_response(
                        transport=TRANSPORT_TERMINAL,
                        option_annotations=option_annotations,
                    )
                if opt_note:
                    option_annotations[idx] = opt_note
            try:
                global_annotation = questionary.text("Global annotation (optional)", default="").unsafe_ask()
            except (KeyboardInterrupt, EOFError, Exception):
                return cancelled_response(
                    transport=TRANSPORT_TERMINAL,
                    option_annotations=option_annotations,
                )

            return normalize_response(
                req=req,
                selected_indices=answer,
                transport=TRANSPORT_TERMINAL,
                option_annotations=option_annotations,
                global_annotation=global_annotation or None,
            )

        return cancelled_response(transport=TRANSPORT_TERMINAL)
    except (KeyboardInterrupt, EOFError, Exception):
        # Handle unexpected input/read errors robustly and return a cancelled result
        return cancelled_response(transport=TRANSPORT_TERMINAL)

    raise ValidationError(f"Unsupported type: {req.type}")


async def _run_with_timeout(req: ProvideChoiceRequest, func: Callable[[], ProvideChoiceResponse], timeout_seconds: int) -> ProvideChoiceResponse:
    """Run a blocking function in a separate thread with a timeout."""
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, func), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return timeout_response(req=req, transport=TRANSPORT_TERMINAL)


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
    result = await _run_with_timeout(req, lambda: _run_prompt_sync(req, config), timeout_seconds)
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

            # Placeholder is no longer supported in current schema; keep defaults for config UI
            placeholder_value = ""
            placeholder_enabled_choice = False

            # Single submit mode toggle
            single_submit_choice = questionary.confirm(
                "Single submit mode (auto-submit on selection)", default=defaults.single_submit_mode
            ).unsafe_ask()
            if single_submit_choice is None:
                return None

            # Timeout default selection
            timeout_default_enabled = questionary.confirm("Enable default selection on timeout?", default=defaults.timeout_default_enabled).unsafe_ask()
            timeout_default_idx = defaults.timeout_default_index
            if timeout_default_enabled:
                choices = _build_choices(req.options)
                default_val = None
                if timeout_default_idx is not None and 0 <= timeout_default_idx < len(choices):
                    default_val = choices[timeout_default_idx]
                
                timeout_default_idx = questionary.select(
                    "Default option for timeout",
                    choices=choices,
                    default=default_val
                ).unsafe_ask()

            return ProvideChoiceConfig(
                transport=chosen_transport,
                timeout_seconds=timeout_val,
                single_submit_mode=bool(single_submit_choice),
                timeout_default_enabled=timeout_default_enabled,
                timeout_default_index=timeout_default_idx if timeout_default_idx is not None else 0,
            )
        except (KeyboardInterrupt, ValueError):
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _prompt_sync)
