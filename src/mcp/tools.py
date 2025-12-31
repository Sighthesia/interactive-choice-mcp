"""MCP tool definitions for interactive choice.

Exports provide_choice and poll_selection tools with proper documentation.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.orchestrator import ChoiceOrchestrator

from .response_formatter import format_mcp_response


# Global orchestrator instance, set during registration
_orchestrator: "ChoiceOrchestrator | None" = None


def set_orchestrator_for_testing(orchestrator: "ChoiceOrchestrator") -> None:
    """Set orchestrator instance for testing purposes."""
    global _orchestrator
    _orchestrator = orchestrator


async def provide_choice(
    title: str,
    prompt: str,
    selection_mode: str,
    options: list[dict],
    session_id: str | None = None,
):
    """Initiates a human-in-the-loop interaction to resolve ambiguity.

    This tool allows the LLM to present options to a human user and
    wait for their selection. Useful for confirming actions, making
    decisions, or gathering user input.

    Args:
        title: Short title for the choice dialog
        prompt: Detailed description of what is being decided
        selection_mode: Either 'single' or 'multi'
        options: List of option dicts with 'id' and 'description'
        session_id: Optional session ID for existing interaction

    Returns:
        Dictionary with action_status and selection details.
    """
    from ..core.orchestrator import safe_handle

    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized. Call register_tools first.")

    result = await safe_handle(
        _orchestrator,
        title=title,
        prompt=prompt,
        selection_mode=selection_mode,
        options=options,
        timeout_seconds=None,
        session_id=session_id,
    )

    is_handoff = result.action_status == "pending_terminal_launch"
    return format_mcp_response(result, is_terminal_handoff=is_handoff)


async def poll_selection(session_id: str) -> dict[str, object]:
    """Blocks and polls for the result of an ongoing interaction.

    Use this tool when provide_choice returns action_status='pending_terminal_launch'
    and you have executed the terminal_command. This tool waits for the user
    to complete the interaction and returns the final result.

    Args:
        session_id: The session ID from the previous provide_choice call

    Returns:
        Dictionary with action_status ('selected', 'cancelled', etc.) and
        selection details including summary, selected_indices, and annotations.
    """
    from ..web import poll_session_result

    result = await poll_session_result(session_id)

    if result is None:
        return {
            "action_status": "cancelled",
            "error": f"Session '{session_id}' not found or expired.",
        }

    return format_mcp_response(result, is_terminal_handoff=False)


def register_tools(
    mcp: "FastMCP", orchestrator: "ChoiceOrchestrator"
) -> None:
    """Register all MCP tools with the server instance."""
    global _orchestrator
    _orchestrator = orchestrator

    mcp.tool()(provide_choice)
    mcp.tool()(poll_selection)
