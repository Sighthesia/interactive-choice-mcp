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

	RULE: Mandatory interface for human-in-the-loop decision making. Call this tool IMMEDIATELY when: 1. Ambiguous requirements occur. 2. Multiple technical paths are available. 3. Confirming destructive actions (delete/overwrite). 4. User input is needed to proceed.

	Strict Rules:

		NO GUESSING: Never assume user preference for architecture, libraries, or logic flow.

		BLOCKING: Halt current task and wait for the tool output.

		EXECUTION: Strictly follow the returned id for subsequent steps.

	Parameter Guidance:

		selection_mode: Must be "single" or "multi"; aliases such as "single_select" are rejected and will raise a validation error.

		options: Each entry must include `id`, `description`, and at least one option marked with `recommended: true`; missing or malformed fields will return a validation error instead of launching the UI.

		session_id: Optional. When provided, polls for the result of an existing terminal hand-off session instead of creating a new interaction.

	Terminal Hand-off Mode:

		When the tool returns `action_status: pending_terminal_launch` the call returns immediately with launch information instead of blocking.
		- `summary`: a CLI command you should run in a terminal (e.g. `uv run python -m choice.terminal.client --session <id> --url <url>`)
		- `url`: the HTTP endpoint backing the session (used by the client)
		- `session_id`: the session identifier (last path component of `url`) — use this value to poll the same `provide_choice` tool to obtain the final result.
		
		Agent steps:
		1. Call `provide_choice` (no `session_id`) and inspect the response. If `action_status` is `pending_terminal_launch`, extract `summary` / `session_id`.
		2. Execute the CLI command from `summary` in a terminal to open the interactive UI for the user.
		3. After the user completes the interaction, call `provide_choice(..., session_id=<id>)` to poll for the final `ProvideChoiceResponse` payload.
		
		Notes:
		- Sessions are single-use and will timeout according to `timeout_seconds`; if the session times out a timeout response will be returned on poll.
		- The returned `summary` is intended to be executed by the agent in a terminal tool; it should not be parsed for semantics beyond running it.
		
		Example response (abbreviated):
		{
		  "action_status": "pending_terminal_launch",
		  "summary": "uv run python -m choice.terminal.client --session abc123 --url http://127.0.0.1:17863",
		  "session_id": "abc123",
		  "url": "http://127.0.0.1:17863/terminal/abc123"
		}
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
		out["summary"] = selection.summary  # Contains launch command
		if selection.url:
			out["url"] = selection.url
		# Extract session_id from URL for polling
		if selection.url:
			parts = selection.url.rstrip("/").split("/")
			if parts:
				out["session_id"] = parts[-1]
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