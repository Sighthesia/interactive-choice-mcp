"""Response formatting for MCP tools.

Converts internal ProvideChoiceResponse to MCP tool return format.
Handles special cases like terminal hand-off and session polling.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.models import ProvideChoiceResponse


def format_mcp_response(
    result: "ProvideChoiceResponse",
    is_terminal_handoff: bool = False,
) -> dict[str, object]:
    """Format ProvideChoiceResponse for MCP tool return.

    Args:
        result: Internal response from orchestrator
        is_terminal_handoff: Whether this is a terminal hand-off response

    Returns:
        Dictionary with keys: action_status, [session_id, url, terminal_command,
        summary, selected_indices, option_annotations, additional_annotation]
    """
    selection = result.selection
    out: dict[str, object] = {"action_status": result.action_status}

    # Handle terminal hand-off special case
    if is_terminal_handoff and result.action_status == "pending_terminal_launch":
        return _format_terminal_handoff(selection, out)

    # Standard response formatting
    return _format_standard_response(selection, out)


def _format_terminal_handoff(
    selection, out: dict[str, object]
) -> dict[str, object]:
    """Format terminal hand-off response with session info.

    Extracts session_id from URL and formats the terminal command.
    """
    session_id_val = ""
    if selection.url:
        parts = selection.url.rstrip("/").split("/")
        if parts:
            session_id_val = parts[-1]
            out["url"] = selection.url

    out["session_id"] = session_id_val
    return out


def _format_standard_response(
    selection, out: dict[str, object]
) -> dict[str, object]:
    """Format standard response with selection data.

    Adds optional fields like selected_indices, annotations, and validation_error.
    """
    # Handle validation_error separately (uses summary internally but exposed as validation_error)
    if selection.summary and selection.summary.startswith("validation_error"):
        out["validation_error"] = selection.summary
    if selection.selected_indices:
        out["selected_indices"] = list(selection.selected_indices)
    if selection.option_annotations:
        out["option_annotations"] = selection.option_annotations
    if selection.additional_annotation:
        out["additional_annotation"] = selection.additional_annotation
    return out
