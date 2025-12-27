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
):
	"""Present an interactive choice prompt to the user and return their selection.

	RULE: Mandatory interface for human-in-the-loop decision making. Call this tool IMMEDIATELY when: 1. Ambiguous requirements occur. 2. Multiple technical paths are available. 3. Confirming destructive actions (delete/overwrite). 4. User input is needed to proceed.

	Strict Rules:

		NO GUESSING: Never assume user preference for architecture, libraries, or logic flow.

		BLOCKING: Halt current task and wait for the tool output.

		EXECUTION: Strictly follow the returned id for subsequent steps.

	Parameter Guidance:

		selection_mode: Use "single" for binary/exclusive choices, "multi" for configuration/feature sets.

		default: Set `true` for the most recommended/standard path to enable fast user confirmation.
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
	)
	
	selection = result.selection
	out: dict[str, object] = {"action_status": result.action_status}
	if selection.selected_indices:
		out["selected_indices"] = list(selection.selected_indices)
	if selection.option_annotations:
		out["option_annotations"] = selection.option_annotations
	if selection.global_annotation:
		out["global_annotation"] = selection.global_annotation
	return out


if __name__ == "__main__":
	mcp.run()