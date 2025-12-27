"""Response normalization helpers extracted from `models.py`."""
from __future__ import annotations

from typing import Optional, Sequence

__all__ = [
    "normalize_response",
    "cancelled_response",
    "timeout_response",
]


def normalize_response(
    *,
    req: "ProvideChoiceRequest",
    selected_indices: Sequence[str] | None,
    transport: str,
    url: Optional[str] = None,
    option_annotations: Optional[dict[str, str]] = None,
    global_annotation: Optional[str] = None,
    action_status: str = "selected",
) -> "ProvideChoiceResponse":
    """Normalize response and validate selected option ids."""

    from .models import (
        ProvideChoiceResponse,
        ProvideChoiceSelection,
        VALID_ACTIONS,
        VALID_TRANSPORTS,
        ValidationError,
    )

    if transport not in VALID_TRANSPORTS:
        raise ValidationError("invalid transport for response")

    if action_status not in VALID_ACTIONS:
        raise ValidationError("invalid action_status for response")

    if selected_indices is None:
        selected_indices = []
    ordered_ids = list(selected_indices)

    valid_ids = {o.id for o in req.options}
    if any(i not in valid_ids for i in ordered_ids):
        raise ValidationError("selected_indices contains unknown option id")

    summary_parts: list[str] = []
    if ordered_ids:
        summary_parts.append(f"ids={ordered_ids}")
    if option_annotations:
        summary_parts.append(f"option_annotations={option_annotations}")
    if global_annotation:
        summary_parts.append(f"global_annotation={global_annotation}")
    summary = ", ".join(summary_parts) if summary_parts else "no selection"

    selection = ProvideChoiceSelection(
        selected_indices=ordered_ids,
        transport=transport,
        summary=summary,
        url=url,
        option_annotations=option_annotations or {},
        global_annotation=global_annotation,
    )

    return ProvideChoiceResponse(action_status=action_status, selection=selection)


def cancelled_response(
    *,
    transport: str,
    url: Optional[str] = None,
    option_annotations: Optional[dict[str, str]] = None,
    global_annotation: Optional[str] = None,
    summary: str = "cancelled",
) -> "ProvideChoiceResponse":
    from .models import ProvideChoiceResponse, ProvideChoiceSelection

    selection = ProvideChoiceSelection(
        selected_indices=[],
        transport=transport,
        summary=summary,
        url=url,
        option_annotations=option_annotations or {},
        global_annotation=global_annotation,
    )
    return ProvideChoiceResponse(action_status="cancelled", selection=selection)


def timeout_response(
    *,
    req: "ProvideChoiceRequest",
    transport: str,
    url: Optional[str] = None,
) -> "ProvideChoiceResponse":
    """Generate a timeout response, potentially with a default selection."""

    from .models import ProvideChoiceRequest, ValidationError

    ids: list[str] = []
    action_status = "timeout_cancelled"

    if req.timeout_action == "reinvoke":
        action_status = "timeout_reinvoke_requested"
    elif req.timeout_action == "cancel":
        action_status = "timeout_cancelled"
    else:
        if req.timeout_default_enabled and req.timeout_default_index is not None:
            idx = req.timeout_default_index
            if idx < 0 or idx >= len(req.options):
                raise ValidationError("timeout_default_index out of range")
            ids = [req.options[idx].id]
            action_status = "timeout_auto_submitted"
        else:
            action_status = "timeout_cancelled"

    return normalize_response(
        req=req,
        selected_indices=ids,
        transport=transport,
        url=url,
        action_status=action_status,
    )
