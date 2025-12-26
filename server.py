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
	type: str,
	options: list[dict],
):
	"""
	Present an interactive choice prompt to the user and return their selection.

	Rule: 
	On any procedure that requires uesr's opnion, you MUST use this tool to collect the input.
	"""

	# Delegate the execution to the orchestrator.
	# The orchestrator handles validation, transport selection, and the actual interaction loop.
	result = await safe_handle(
		orchestrator,
		title=title,
		prompt=prompt,
		type=type,
		options=options,
		allow_cancel=True,
		placeholder=None,
		transport=None,
		timeout_seconds=None,
	)
	
	selection = result.selection
	out = {"action_status": result.action_status}
	if selection.selected_indices:
		out["selected_indices"] = list(selection.selected_indices)
	if selection.option_annotations:
		out["option_annotations"] = selection.option_annotations
	if selection.global_annotation:
		out["global_annotation"] = selection.global_annotation
	return out


if __name__ == "__main__":
	mcp.run()