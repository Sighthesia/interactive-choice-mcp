## Context
The MCP server currently exposes no functional tools beyond a FastMCP stub. We need a schema-first `provide_choice` tool with dual transports (terminal via questionary, transient web via FastAPI) so AI agents can offload branching decisions to users instead of guessing. The design must ensure deterministic outputs, clear cancellation/timeout semantics, and shared orchestration that injects task context into prompts.

## Goals / Non-Goals
- Goals: CLI-first interaction with consistent result contract; web bridge fallback for non-interactive clients; strict schema validation; deterministic ordering for multi-select; timeout and cancel handling; prompt guidance explaining why a choice is needed.
- Non-Goals: Building a persistent web dashboard; adding additional tools beyond `provide_choice`; advanced theming or localization of the portal; implementing full e2e automation beyond manual smoke for transports.

## Decisions
- Decision: Default to terminal interface using questionary, falling back to a short-lived FastAPI portal when stdin is unavailable or the caller opts into web. This keeps local CLIs fast while preserving usability in GUI-only contexts.
- Decision: Enforce a schema-first contract (`title`, `prompt`, `type`, `options[id,label,description]`, `allow_cancel`, `placeholder`) with deterministic `action_status` values (`selected|custom_input|cancelled|timeout`) and ordered selections to simplify downstream automation.
- Decision: Apply a bounded wait with a configurable timeout (default 5 minutes) for user responses across transports; on timeout return `timeout` and shut down any transient servers to avoid zombie processes.
- Decision: Provide an explicit interface selector override for callers while preserving environment-based detection so web can be forced in GUI-only contexts and terminal remains the default where available.
- Decision: Orchestration layer must include current task context in prompts and must invoke `provide_choice` whenever branching paths exceed two, when operations are destructive, or when required config is missing, eliminating speculative defaults.

## Risks / Trade-offs
- Terminal-only automation may still require web fallback in constrained environments; mitigated by always enabling the FastAPI bridge.
- Browser auto-launch may fail on headless systems; mitigated by always returning the local URL and allowing manual navigation.
- Questionary interactive flows are harder to unit test; mitigate with separation between prompt rendering and choice normalization plus manual smoke guidance.

## Migration Plan
- Add orchestration and transports alongside existing stubs without breaking current main/server entrypoints.
- Introduce schema validation and transports behind the new `provide_choice` tool registration, then wire tests and manual smoke steps.

## Open Questions
- None at this time.
