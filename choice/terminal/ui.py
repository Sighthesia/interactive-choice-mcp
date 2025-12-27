"""Terminal UI helpers (questionary integration)."""
from __future__ import annotations

from typing import Iterable, List

import questionary

from ..models import ProvideChoiceOption, ProvideChoiceResponse

__all__ = [
    "_build_choices",
    "_build_config_choices",
    "_summary_line",
]


def _build_choices(options: Iterable[ProvideChoiceOption]) -> List[questionary.Choice]:
    return [
        questionary.Choice(
            title=f"{opt.id} (推荐)" if opt.recommended else opt.id,
            value=opt.id
        )
        for opt in options
    ]


def _build_config_choices(options: Iterable[ProvideChoiceOption], defaults: List[int]) -> List[questionary.Choice]:
    return [
        questionary.Choice(
            title=f"{opt.id} (推荐)" if opt.recommended else opt.id,
            value=idx,
            checked=idx in defaults
        )
        for idx, opt in enumerate(options)
    ]


def _summary_line(selection: ProvideChoiceResponse) -> str:
    sel = selection.selection
    status = selection.action_status
    if sel.selected_indices:
        return f"{status}: {sel.selected_indices}"
    return status or "No selection"
