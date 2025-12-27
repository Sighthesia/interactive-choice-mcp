# Change: Refactor terminal launch flow

## Why
- Terminal transport currently blocks inside the MCP invocation, preventing the AI from triggering an external terminal UI command when `transport=terminal` is requested.
- We need the tool to return a launch address immediately so the AI can run a terminal command that opens the interactive UI for the user to make the selection.

## What Changes
- Add a terminal hand-off mode that allocates a session and returns a launch address/command immediately while preserving the existing questionary experience.
- Keep the selection lifecycle within the existing `provide_choice` contract by publishing the final response (selected/cancelled/timeout) from the terminal client back to the session.
- Extend the response/action status contract to represent the pending terminal launch state and to carry the launch address in `selection.url` and `selection.summary`.
- Ensure timeout/cancel handling, configuration persistence, and option visibility are enforced across the hand-off flow.

## Impact
- Affected specs: choice-orchestration
- Affected code: choice/orchestrator.py, choice/terminal.py, choice/web.py, choice/storage.py, CLI entrypoint for terminal hand-off, server/main tool registration
