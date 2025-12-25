## 1. Implementation
- [x] 1.1 Define the `provide_choice` request/response schema types with strict validation and deterministic `action_status` mapping.
- [x] 1.2 Add orchestration that selects terminal-first transport with web portal fallback, injecting task context into prompts and disallowing speculative defaults.
- [x] 1.3 Implement terminal interaction using questionary (arrow/space/enter), clear the UI after submission, and emit a concise summary only.
- [x] 1.4 Implement transient FastAPI web portal that serves choice UI at `http://localhost:<port>/choice/<id>`, opens the browser, streams selection via WebSocket/long-poll, and shuts down after completion.
- [x] 1.5 Enforce a configurable timeout (default 5 minutes) and cancel handling across transports, with ordered multi-select/hybrid normalization.
- [x] 1.6 Add tests: pytest for schema validation, selection normalization, timeout/cancel paths; perform manual smoke for terminal and web flows; run `openspec validate add-provide-choice-capability --strict`.
