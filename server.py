from fastmcp import FastMCP

from choice.orchestrator import ChoiceOrchestrator

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
	"""Collect a structured user choice with terminal-first flow and web fallback."""

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