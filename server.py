from mcp.server.fastmcp import FastMCP

from src.core.orchestrator import ChoiceOrchestrator, safe_handle
from src.web import poll_session_result

# Section: Initialization
# Initialize the FastMCP server instance and the choice orchestrator.
# The orchestrator is responsible for routing requests to the appropriate
# transport (terminal or web) based on availability and configuration.
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
	"""Present an interactive choice prompt to the user and return their selection.

	RULE: Mandatory interface for human-in-the-loop decision making. Call this tool IMMEDIATELY when:
	1. Ambiguous requirements occur
	2. Multiple technical paths are available
	3. Confirming destructive actions (delete/overwrite)
	4. User input is needed to proceed

	Strict Rules:
		NO GUESSING: Never assume user preference.
		BLOCKING: Halt current task and wait for the tool output.
		EXECUTION: Strictly follow the returned id for subsequent steps.

	Parameter Guidance:
		selection_mode: Must be "single" or "multi".
		options: Each entry must include `id`, `description`; mark one with `recommended: true`.

	Terminal Mode Workflow:
		When `action_status` is "pending_terminal_launch":
		
		Step 1: Run the `terminal_command` in terminal
		Step 2: Parse terminal output for result markers:
		   - [SELECTION_COMPLETE] selected=A,B annotations={} global=note
		     → User made selection in terminal, use the parsed values
		   - [CANCELLED] global=note
		     → User cancelled in terminal
		   - [SWITCH_TO_WEB] session_id=xxx
		     → User switched to web, call poll_selection(session_id) to wait

	Web Mode:
		When terminal is not used, this tool blocks until user completes the interaction
		in the web browser.
	"""

	# Delegate the execution to the orchestrator.
	# The orchestrator handles validation, transport selection, and the actual interaction loop.
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
async def poll_selection(session_id: str, wait_seconds: int = 30) -> dict[str, object]:
	"""Poll for the result of a pending interaction session.

	This tool is used after `provide_choice` returns `pending_terminal_launch` status.
	It blocks until the user completes the interaction or the timeout is reached.

	Args:
		session_id: The session ID returned by provide_choice
		wait_seconds: Maximum seconds to wait for result (default 30, max 120)

	Returns:
		The selection result with same format as provide_choice:
		- action_status: "selected", "cancelled", "timeout_*", etc.
		- selected_indices: List of selected option IDs
		- option_annotations: Dict of option ID to annotation
		- global_annotation: Optional global note
		
	If session is not found or expired, returns:
		- action_status: "cancelled"
		- error: Error description
	"""
	# Clamp wait_seconds to reasonable bounds
	wait_seconds = max(1, min(120, wait_seconds))

	result = await poll_session_result(session_id, wait_seconds=wait_seconds)
	
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