from fastmcp import FastMCP

from choice.orchestrator import ChoiceOrchestrator

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
	allow_cancel: bool,
	placeholder: str | None = None,
	transport: str | None = None,
	timeout_seconds: int | None = None,
):
	"""Collect a structured user choice with terminal-first flow and web fallback.

	This tool allows the AI to pause execution and request a decision from the user.
	It supports multiple interaction modes and handles timeouts and cancellations.
	"""

	# Delegate the execution to the orchestrator.
	# The orchestrator handles validation, transport selection, and the actual interaction loop.
	result = await orchestrator.handle(
		title=title,
		prompt=prompt,
		type=type,
		options=options,
		allow_cancel=allow_cancel,
		placeholder=placeholder,
		transport=transport,
		timeout_seconds=timeout_seconds,
	)
	
	# Return a structured response that separates the status from the data.
	return {
		"action_status": result.action_status,
		"selection": {
			"selected_ids": result.selection.selected_ids,
			"custom_input": result.selection.custom_input,
			"transport": result.selection.transport,
			"summary": result.selection.summary,
			"url": result.selection.url,
		},
	}


if __name__ == "__main__":
	mcp.run()