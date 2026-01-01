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
    """Mandatory interactive feedback and decision-making interface. 
    Use this tool to resolve ambiguities, confirm high-risk actions, or validate task completion.

    STRICT USAGE RULES:
    1. NO SILENT COMPLETION: You are FORBIDDEN from simply stating "Task complete" in plain text. You MUST call this tool to present your results for user final acceptance.
    2. CONTINUOUS LOOP: Unless the user selects an option explicitly labeled as "Finish" or "End Session," you must continue calling this tool after every major sub-task.
    3. MANDATORY SUMMARY: The `prompt` argument MUST follow this structure:
       - [WORK COMPLETED]: A concise summary of actions taken and files modified.
       - [NEXT STEP/QUESTION]: What you need the user to decide or if they are satisfied with the result.
    4. NO GUESSING: If requirements are unclear or multiple technical paths exist, you must halt and call this tool.
    5. FEEDBACK INTEGRATION: If a user provides `option_annotations` or `global_annotation`, treat them as new instructions, execute the changes, and call this tool AGAIN to re-verify.

    TERMINAL VS WEB WORKFLOW:
    - If `action_status` == "pending_terminal_launch":
        1. IMMEDIATELY execute the `terminal_command` using the terminal tool.
        2. Monitor output for `[SWITCH_TO_WEB] session_id=xxx`. If found, call `poll_selection(session_id)`.
        3. If `[SELECTION_COMPLETE]` appears, parse the result and proceed.
    - If `action_status` == "selected": Proceed based on the chosen ID.

    Args:
        title: Short title of the decision context.
        prompt: Structured summary and question (see Rule #3).
        selection_mode: "single" or "multi".
        options: List of dicts (id, description). Always include a `recommended: true` option.Mandatory interactive feedback and decision-making interface."""
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
