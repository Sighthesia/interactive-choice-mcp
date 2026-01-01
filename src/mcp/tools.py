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
    """Initiates a mandatory human-in-the-loop interaction to resolve ambiguity, confirm actions, or validate task completion.

    MANDATORY USAGE RULES:
    1.  **Continuous Validation**: You MUST call this tool repeatedly at the end of every major step or when the task seems complete. Do not stop until the user explicitly selects an option indicating "Task Completed" or "End Session".
    2.  **Contextual Summary**: In the `prompt` argument, you MUST summarize what has been done so far and what specific decision is needed now.
    3.  **No Assumptions**: Never guess the user's preference. If multiple technical paths exist, ask. If a destructive action (delete/overwrite) is required, ask.
    4.  **Feedback Loop**: If the user selects an option with annotations (feedback), you must adjust your plan and call this tool again to confirm the new direction.

    Workflow & State Handling:
    This tool supports both Web and Terminal interfaces. You must handle the `action_status` in the return value strictly:

    [CASE A: Web Mode / Direct Result]
    If `action_status` is "selected" or "cancelled":
        - Action: Proceed immediately based on `selected_indices` and `option_annotations`.

    [CASE B: Terminal Mode]
    If `action_status` is "pending_terminal_launch":
        - Action: Use the `terminal` tool to execute the command provided in `terminal_command`.
        - **CRITICAL**: You must read the terminal output and parse for these markers:
            1. `[SELECTION_COMPLETE] selected=...`: Interaction finished in terminal. Use these values.
            2. `[CANCELLED]`: User cancelled in terminal.
            3. `[SWITCH_TO_WEB] session_id=...`: User requested to move to Web.
               -> **IMMEDIATE ACTION**: Call `poll_selection(session_id=...)` and wait for the result.

    Args:
        title: Short title for the decision context.
        prompt: Detailed context summary and the specific question/request for the user.
        selection_mode: "single" or "multi".
        options: List of dicts, e.g., [{"id": "opt1", "description": "Deploy to Prod", "recommended": True}]. At least one option must be marked as recommended.
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
    )

    is_handoff = result.action_status == "pending_terminal_launch"
    return format_mcp_response(result, is_terminal_handoff=is_handoff)


async def poll_selection(session_id: str) -> dict[str, object]:
    """Blocks and polls for the result of an ongoing interaction session that was switched from Terminal to Web.

    WHEN TO USE:
    - ONLY call this tool if you executed a command from `provide_choice` and the terminal output contained the marker: `[SWITCH_TO_WEB] session_id=...`.
    - Do not call this tool directly without a preceding `provide_choice` interaction.

    BEHAVIOR:
    - This tool acts as a blocking wait. It will pause execution until the user completes the selection in the browser or the session times out.
    - If the result implies further feedback (annotations), you must loop back and use `provide_choice` again after addressing the feedback.

    Args:
        session_id: The ID extracted from the `[SWITCH_TO_WEB]` terminal marker.
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
