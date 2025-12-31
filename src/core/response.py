"""Response normalization helpers.

Provides functions to normalize, cancel, and generate timeout responses for choices.
"""
from __future__ import annotations

from typing import Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ProvideChoiceRequest, ProvideChoiceResponse

__all__ = [
    "normalize_response",
    "cancelled_response",
    "timeout_response",
    "pending_terminal_launch_response",
]


def normalize_response(
    *,
    req: "ProvideChoiceRequest",
    selected_indices: Sequence[str] | None,
    interface: str,
    url: Optional[str] = None,
    option_annotations: Optional[dict[str, str]] = None,
    additional_annotation: Optional[str] = None,
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

    if interface not in VALID_TRANSPORTS:
        raise ValidationError("invalid interface for response")

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
    if additional_annotation:
        summary_parts.append(f"additional_annotation={additional_annotation}")
    summary = ", ".join(summary_parts) if summary_parts else "no selection"

    selection = ProvideChoiceSelection(
        selected_indices=ordered_ids,
        interface=interface,
        summary=summary,
        url=url,
        option_annotations=option_annotations or {},
        additional_annotation=additional_annotation,
    )

    return ProvideChoiceResponse(action_status=action_status, selection=selection)


def cancelled_response(
    *,
    interface: str,
    url: Optional[str] = None,
    option_annotations: Optional[dict[str, str]] = None,
    additional_annotation: Optional[str] = None,
    summary: str = "cancelled",
) -> "ProvideChoiceResponse":
    from .models import ProvideChoiceResponse, ProvideChoiceSelection

    selection = ProvideChoiceSelection(
        selected_indices=[],
        interface=interface,
        summary=summary,
        url=url,
        option_annotations=option_annotations or {},
        additional_annotation=additional_annotation,
    )
    return ProvideChoiceResponse(action_status="cancelled", selection=selection)


def interrupted_response(
    *,
    interface: str,
    url: Optional[str] = None,
) -> "ProvideChoiceResponse":
    """Generate a response for an interrupted session (e.g., agent disconnected)."""
    from .models import ProvideChoiceResponse, ProvideChoiceSelection

    selection = ProvideChoiceSelection(
        selected_indices=[],
        interface=interface,
        summary="interrupted",
        url=url,
    )
    return ProvideChoiceResponse(action_status="interrupted", selection=selection)


def timeout_response(
    *,
    req: "ProvideChoiceRequest",
    interface: str,
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
        interface=interface,
        url=url,
        action_status=action_status,
    )


def pending_terminal_launch_response(
    *,
    session_id: str,
    url: str,
    launch_command: str,
) -> "ProvideChoiceResponse":
    """Generate a response indicating that the terminal UI should be launched externally.
    
    This response is returned immediately when terminal hand-off mode is used,
    providing the agent with:
    - `session_id`: The session identifier for polling the result
    - `url`: The HTTP endpoint for the session (used by the terminal client)
    - `launch_command`: The CLI command to run to open the terminal UI
    """
    from .models import ProvideChoiceResponse, ProvideChoiceSelection, TRANSPORT_TERMINAL

    selection = ProvideChoiceSelection(
        selected_indices=[],
        interface=TRANSPORT_TERMINAL,
        summary=launch_command,
        url=url,
    )
    return ProvideChoiceResponse(action_status="pending_terminal_launch", selection=selection)
