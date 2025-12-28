"""Terminal UI helpers (questionary integration)."""
from __future__ import annotations

from typing import Iterable, List

import questionary

from ..i18n import get_text
from ..models import ProvideChoiceOption, ProvideChoiceResponse, LANG_EN

__all__ = [
    "_build_choices",
    "_build_config_choices",
    "_summary_line",
]


def _build_choices(options: Iterable[ProvideChoiceOption], lang: str = LANG_EN) -> List[questionary.Choice]:
    recommended_label = get_text("label.recommended", lang)
    return [
        questionary.Choice(
            title=f"{opt.id} ({recommended_label})" if opt.recommended else opt.id,
            value=opt.id
        )
        for opt in options
    ]


def _build_config_choices(options: Iterable[ProvideChoiceOption], defaults: List[int], lang: str = LANG_EN) -> List[questionary.Choice]:
    recommended_label = get_text("label.recommended", lang)
    return [
        questionary.Choice(
            title=f"{opt.id} ({recommended_label})" if opt.recommended else opt.id,
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
