from __future__ import annotations

import asyncio
import sys
from typing import Callable, Iterable, List, Optional

import questionary

from .models import (
    ProvideChoiceOption,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    cancelled_response,
    normalize_response,
    timeout_response,
    ValidationError,
    TRANSPORT_TERMINAL,
)


def is_terminal_available() -> bool:
    return sys.stdin is not None and sys.stdin.isatty()


def _clear_terminal() -> None:
    # ANSI clear screen and move cursor home
    print("\033[2J\033[H", end="")


def _build_choices(options: Iterable[ProvideChoiceOption]) -> List[questionary.Choice]:
    return [questionary.Choice(title=opt.label, value=opt.id, short=opt.label) for opt in options]


def _summary_line(selection: ProvideChoiceResponse) -> str:
    sel = selection.selection
    if sel.custom_input:
        return f"Custom input: {sel.custom_input}"
    if sel.selected_ids:
        return f"Selected: {sel.selected_ids}"
    return "No selection"


def _run_prompt_sync(req: ProvideChoiceRequest) -> ProvideChoiceResponse:
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
            hybrid_choices = choices + [questionary.Choice(title="Custom input", value="__custom__", short="Custom")]
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
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, func), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return timeout_response(transport=TRANSPORT_TERMINAL)


async def run_terminal_choice(req: ProvideChoiceRequest, *, timeout_seconds: int) -> ProvideChoiceResponse:
    result = await _run_with_timeout(lambda: _run_prompt_sync(req), timeout_seconds)
    _clear_terminal()
    print(_summary_line(result))
    return result
