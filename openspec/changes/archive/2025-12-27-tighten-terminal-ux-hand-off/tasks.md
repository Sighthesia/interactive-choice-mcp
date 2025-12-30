# Tasks: Tighten Terminal UX & Hand-off

1. Update tool contract prompt text and MCP response schema to surface `terminal_command`, `session_id`, optional `url`, and `instructions`; ensure polling blocks by default (spec-only for now).
2. Specify terminal UI requirements: timestamp + timeout display, j/k navigation, Tab to annotations, always-on annotations, cancel → global annotation, settings entry, interface switch behavior.
3. Specify configuration surface: settings accessible from terminal UI, persists changes, supports switching current session to web and cancelling terminal session.
4. Clarify URL semantics in hand-off contract: auxiliary/optional for agents, embedded in `terminal_command` for the client.
5. Run `openspec validate tighten-terminal-ux-hand-off --strict` and fix any issues.
