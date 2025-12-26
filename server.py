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
	placeholder: str | None = None,
	transport: str | None = None,
	timeout_seconds: int | None = None,
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
		placeholder=placeholder,
		transport=transport,
		timeout_seconds=timeout_seconds,
	)
	
	# Return a structured response that separates the status from the data.
	out = {}
	selected = list(result.selection.selected_ids) if result.selection.selected_ids else []
	if result.selection.custom_input:
		selected.append(result.selection.custom_input)
	if selected:
		out["selected_ids"] = selected
	return out


if __name__ == "__main__":
	mcp.run()