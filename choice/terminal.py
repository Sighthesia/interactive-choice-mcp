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
    """Convert internal options to questionary Choice objects using option IDs as values."""
    return [
        questionary.Choice(
            title=f"{opt.id} (推荐)" if opt.recommended else opt.id,
            value=opt.id
        )
        for opt in options
    ]


def _build_config_choices(options: Iterable[ProvideChoiceOption], defaults: List[int]) -> List[questionary.Choice]:
    """Convert options to choices while marking defaults by index.

    Note: config choices use numeric indices as values so the config UI remains
    index-based (keeps backward-compatibility for timeout_default_index).
    """
    return [
        questionary.Choice(
            title=f"{opt.id} (推荐)" if opt.recommended else opt.id,
            value=idx,
            checked=idx in defaults
        )
        for idx, opt in enumerate(options)
    ]


def _summary_line(selection: ProvideChoiceResponse) -> str:
    """Generate a concise summary string for the final output."""
    sel = selection.selection
    status = selection.action_status
    if sel.selected_indices:
        return f"{status}: {sel.selected_indices}"
    return status or "No selection"


# Section: Interaction Logic
def _run_prompt_sync(
    req: ProvideChoiceRequest,
    config: Optional[ProvideChoiceConfig] = None,
) -> ProvideChoiceResponse:
    """
    Execute the synchronous questionary prompt.
    
    This function blocks until the user provides input or cancels.
    It handles the different prompt types (select, checkbox, text, hybrid),
    respects single_submit_mode, and annotations (always enabled).
    """
    visible_options = list(req.options)
    choices = _build_choices(visible_options)
    option_annotations: dict[str, str] = {}
    global_annotation: Optional[str] = None
    annotation_enabled = True
    placeholder_visible = True

    # Determine default selection if use_default_option is enabled
    default_selection: List[str] = []
    if config and config.use_default_option:
        default_selection = [opt.id for opt in visible_options if opt.recommended]

    try:
        # Single select: auto-submit or select from list
        if req.selection_mode == "single":
            default_val = default_selection[0] if default_selection else None
            answer = questionary.select(
                req.prompt,
                choices=choices,
                default=default_val
            ).unsafe_ask()
            if answer is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)

            if annotation_enabled:
                try:
                    instruction = "Add note..." if placeholder_visible else ""
                    opt_note = questionary.text(
                        f"Note for '{answer}' (optional)",
                        default="",
                        instruction=instruction,
                    ).unsafe_ask()
                except (KeyboardInterrupt, EOFError, Exception):
                    return cancelled_response(transport=TRANSPORT_TERMINAL)
                if opt_note:
                    option_annotations[answer] = opt_note
                try:
                    global_instruction = "Optional note" if placeholder_visible else ""
                    global_annotation = questionary.text(
                        "Global annotation (optional)",
                        default="",
                        instruction=global_instruction,
                    ).unsafe_ask()
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
                global_annotation=global_annotation or None if annotation_enabled else None,
            )

        # Multi select or batch submission mode
        if req.selection_mode == "multi" or (req.selection_mode == "single" and not req.single_submit_mode):
            # For checkbox, we need to rebuild choices with 'checked' state if use_default_option is on
            if config and config.use_default_option:
                choices = [
                    questionary.Choice(
                        title=f"{opt.id} (推荐)" if opt.recommended else opt.id,
                        value=opt.id,
                        checked=opt.recommended
                    )
                    for opt in visible_options
                ]
            answer = questionary.checkbox(req.prompt, choices=choices).unsafe_ask()
            if answer is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)

            if annotation_enabled:
                for opt_id in answer:
                    try:
                        instruction = "Add note..." if placeholder_visible else ""
                        opt_note = questionary.text(
                            f"Note for '{opt_id}' (optional)",
                            default="",
                            instruction=instruction,
                        ).unsafe_ask()
                    except (KeyboardInterrupt, EOFError, Exception):
                        return cancelled_response(
                            transport=TRANSPORT_TERMINAL,
                            option_annotations=option_annotations,
                        )
                    if opt_note:
                        option_annotations[opt_id] = opt_note
                try:
                    global_instruction = "Optional note" if placeholder_visible else ""
                    global_annotation = questionary.text(
                        "Global annotation (optional)",
                        default="",
                        instruction=global_instruction,
                    ).unsafe_ask()
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
                global_annotation=global_annotation or None if annotation_enabled else None,
            )

        return cancelled_response(transport=TRANSPORT_TERMINAL)
    except (KeyboardInterrupt, EOFError, Exception):
        # Handle unexpected input/read errors robustly and return a cancelled result
        return cancelled_response(transport=TRANSPORT_TERMINAL)

    raise ValidationError(f"Unsupported selection_mode: {req.selection_mode}")


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

            # Single submit mode toggle
            single_submit_choice = questionary.confirm(
                "Single submit mode (auto-submit on selection)", default=defaults.single_submit_mode
            ).unsafe_ask()
            if single_submit_choice is None:
                return None

            # Use default option toggle
            use_default_option = questionary.confirm(
                "采用推荐选项 (自动勾选标记为推荐的选项)", default=defaults.use_default_option
            ).unsafe_ask()
            if use_default_option is None:
                return None

            # Timeout Action
            timeout_action = questionary.select(
                "Timeout Action",
                choices=[
                    questionary.Choice(title="Auto-submit selected", value="submit"),
                    questionary.Choice(title="Auto-cancel", value="cancel"),
                    questionary.Choice(title="Request re-invocation", value="reinvoke"),
                ],
                default=defaults.timeout_action
            ).unsafe_ask()
            if timeout_action is None:
                return None

            # Timeout default selection
            timeout_default_enabled = questionary.confirm("Enable default selection on timeout?", default=defaults.timeout_default_enabled).unsafe_ask()
            timeout_default_idx = defaults.timeout_default_index
            if timeout_default_enabled:
                choices = _build_config_choices(req.options, list(range(len(req.options))))
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
                use_default_option=bool(use_default_option),
                timeout_action=timeout_action,
            )
        except (KeyboardInterrupt, ValueError):
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _prompt_sync)
