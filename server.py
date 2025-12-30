from mcp.server.fastmcp import FastMCP

from src.core.orchestrator import ChoiceOrchestrator, safe_handle
from src.web import poll_session_result

# Section: Initialization
# Initialize the FastMCP server instance and the choice orchestrator.
# The orchestrator is responsible for routing requests to the appropriate
# interface (terminal or web) based on availability and configuration.
mcp = FastMCP("Interactive Choice")
orchestrator = ChoiceOrchestrator()


@mcp.tool()
async def provide_choice(
	title: str,
	prompt: str,
	selection_mode: str,
	options: list[dict],
	session_id: str | None = None,
):
	"""Initiates a human-in-the-loop interaction to resolve ambiguity, confirm actions, or validate task completion.

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
	"""

	# Delegate the execution to the orchestrator.
	# The orchestrator handles validation, interface selection, and the actual interaction loop.
	result = await safe_handle(
		orchestrator,
		title=title,
		prompt=prompt,
		selection_mode=selection_mode,
		options=options,
		timeout_seconds=None,
		session_id=session_id,
	)
	
	selection = result.selection
	out: dict[str, object] = {"action_status": result.action_status}

	# For terminal hand-off, include session info for the agent
	if result.action_status == "pending_terminal_launch":
		# Extract session_id from URL
		session_id_val = ""
		if selection.url:
			parts = selection.url.rstrip("/").split("/")
			if parts:
				session_id_val = parts[-1]
			out["url"] = selection.url
		
		out["session_id"] = session_id_val
		# Provide a clean, copy-paste ready command for the agent
		out["terminal_command"] = selection.summary
		return out

	if selection.summary:
		out["summary"] = selection.summary
		if selection.summary.startswith("validation_error"):
			out["validation_error"] = selection.summary
	if selection.selected_indices:
		out["selected_indices"] = list(selection.selected_indices)
	if selection.option_annotations:
		out["option_annotations"] = selection.option_annotations
	if selection.global_annotation:
		out["global_annotation"] = selection.global_annotation
	return out


@mcp.tool()
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
	result = await poll_session_result(session_id)
	
	if result is None:
		return {
			"action_status": "cancelled",
			"error": f"Session '{session_id}' not found or expired. Please create a new session.",
		}
	
	selection = result.selection
	out: dict[str, object] = {"action_status": result.action_status}

	if selection.summary:
		out["summary"] = selection.summary
	if selection.selected_indices:
		out["selected_indices"] = list(selection.selected_indices)
	if selection.option_annotations:
		out["option_annotations"] = selection.option_annotations
	if selection.global_annotation:
		out["global_annotation"] = selection.global_annotation
	return out


if __name__ == "__main__":
	mcp.run()