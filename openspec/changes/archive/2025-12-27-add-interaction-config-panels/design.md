## Context
Users need an explicit configuration surface in both terminal and web flows to choose interface, adjust which options are presented, and tune timeout before answering. Current flows assume defaults and only present the choice prompt.

## Goals / Non-Goals
- Goals: expose interface selection, option visibility, and timeout settings ahead of both terminal and web prompts; feed selections into orchestrator and result payloads; keep defaults simple.
- Non-Goals: redesign the core choice schema or add persistent user profiles.

## Decisions
- Add a shared configuration model in orchestrator that both terminal and web renderers consume so settings stay consistent.
- Present configuration first, then render the actual choice prompt; keep summaries concise and maintain existing clear-screen/teardown behavior.
- Apply timeout overrides per invocation, falling back to default 5 minutes when unset.
- Persist last-used configuration (interface, option visibility, timeout) in a lightweight store (e.g., file or in-memory cache keyed to session) and prefill subsequent prompts with those values, while still allowing overrides.

## Risks / Trade-offs
- Additional steps before the prompt could add friction; mitigated by keeping defaults pre-selected and enabling quick acceptance.
- Terminal UI space is limited; configuration must stay minimal to avoid clutter.
- Persisted settings may become stale across contexts; mitigate by keeping reset-to-default controls and timestamping the saved profile.

## Open Questions
- None currently; option visibility must allow arbitrary selection, and settings persistence is required across invocations.
