from mcp.server.fastmcp import FastMCP

from choice.orchestrator import ChoiceOrchestrator, safe_handle

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
		session_id: Used for polling terminal session results (see below).

	Terminal Mode Workflow:
		When `action_status` is "pending_terminal_launch":
		
		Step 1: Run the command in `terminal_command` field in a terminal
		Step 2: Wait for user to complete the terminal interaction  
		Step 3: Call provide_choice again with the same parameters + `session_id` to get result

		Response fields for terminal mode:
		- `terminal_command`: The exact command to run (copy-paste ready)
		- `session_id`: Use this to poll for results
		- `instructions`: Human-readable steps
		
		Example:
		{
		  "action_status": "pending_terminal_launch",
		  "terminal_command": "uv run python -m choice.terminal.client --session abc123 --url http://127.0.0.1:17863",
		  "session_id": "abc123",
		  "instructions": "1. Run the terminal_command...\n2. Wait for user...\n3. Poll with session_id"
		}

	Polling Result:
		When called with `session_id`, returns the final result if ready.
		If user hasn't completed, waits up to 30 seconds before returning.
	"""

	# Delegate the execution to the orchestrator.
	# The orchestrator handles validation, transport selection, and the actual interaction loop.
	result = await safe_handle(
		orchestrator,
		title=title,
		prompt=prompt,
		selection_mode=selection_mode,
		options=options,
		transport=None,
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
		# Simple instructions for the agent
		out["instructions"] = (
			f"1. Run the terminal_command in a terminal\n"
			f"2. Wait for user to complete the interaction\n"
			f"3. Call provide_choice again with session_id='{session_id_val}' to get the result"
		)
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


if __name__ == "__main__":
	mcp.run()