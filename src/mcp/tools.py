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
):
    """Use this tool to resolve ambiguities, confirm high-risk actions, or validate task completion.

    USAGE RULES:
    1. SUMMARY: The `prompt` argument MUST follow this structure:
       - A concise summary of actions taken and files modified.
       - What you need the user to decide or if they are satisfied with the result.
    2. FEEDBACK INTEGRATION: If a user provides `option_annotations` or `additional_annotation`, treat them as new instructions, execute the changes, and call this tool AGAIN to re-verify.

    TERMINAL WORKFLOW:
    - If `action_status` == "pending_terminal_launch":
        1. IMMEDIATELY execute the `terminal_command` using the terminal tool.
        2. Monitor output for `[SWITCH_TO_WEB] session_id=xxx`. If found, call `poll_selection(session_id)`.
        3. If `[SELECTION_COMPLETE]` appears, parse the result and proceed.
    
    Args:
        selection_mode: "single" or "multi".
        options: List of dicts (id, description). Always include a `recommended: true` option."""
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
    )

    is_handoff = result.action_status == "pending_terminal_launch"
    return format_mcp_response(result, is_terminal_handoff=is_handoff)


async def poll_selection(session_id: str) -> dict[str, object]:
    """Polls for the result of an ongoing interaction session that was switched from Terminal to Web.
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
