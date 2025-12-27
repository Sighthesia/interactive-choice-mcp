## Context
- Terminal transport currently blocks inside the MCP request, so the AI cannot run an external terminal command after calling `provide_choice` with `transport=terminal`.
- The request is to let the tool return immediately with a launch address/command that the AI can execute to open the terminal UI, while still enforcing the existing choice orchestration behaviors (timeouts, cancel, annotations, config persistence).

## Goals / Non-Goals
- Goals: deliver a hand-off flow that returns a launch address instantly, preserves the questionary-based terminal UI, and returns the final `ProvideChoiceResponse` once the user completes the interaction.
- Goals: keep session-scoped timeout/cancel enforcement and option visibility/annotations consistent with the existing contract.
- Non-Goals: change the web bridge semantics or remove the existing terminal UI behaviors; expand beyond localhost networking; introduce third-party services.

## Decisions
- Introduce a terminal hand-off session: the MCP call allocates a session/process id and ephemeral local endpoint, then returns `action_status=pending_terminal_launch` plus `selection.url` (HTTP endpoint) and `selection.summary` (CLI command such as `choice-terminal --session <id>`). The caller uses the returned id to run the terminal command via the "在终端运行命令" tool.
- Add a small terminal client entrypoint that consumes the session endpoint, renders questionary UI, and POSTs the finalized selection/cancel/timeout back to the session endpoint using the existing `ProvideChoiceResponse` envelope.
- Keep result retrieval within the MCP contract: the session endpoint stores the finalized `ProvideChoiceResponse`, and a follow-up `provide_choice` call with `session_id=<id>` returns the stored result (or a pending status until completion), so agents have a deterministic path to the final payload.
- Enforce the same timeout budget on the session; if the client never attaches or the user is idle, the session auto-transitions to timeout with the configured timeout action and default selection rules. Sessions are single-use; no auto-reconnect is provided, and a new session/command is required for a retry.

## Risks / Trade-offs
- Adds a two-phase interaction (launch + fetch) that slightly complicates agent logic; mitigated by surfacing a single CLI command and a polling hook via `session_id`.
- Requires persistence of session state and results; must ensure cleanup on timeout/cancel to avoid leaking sessions.
- Need to ensure the new action status (`pending_terminal_launch`) is accepted by existing consumers and tests; requires contract updates and guardrails.

## Open Questions
- Is polling the result via `provide_choice(session_id=...)` acceptable, or should we also expose a direct file/HTTP result path in the initial response for agents that prefer not to re-invoke the tool?
- Should the CLI command auto-open in the existing terminal or spawn a new pseudo-TTY for better UX?
