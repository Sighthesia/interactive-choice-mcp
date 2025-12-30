# Design: Terminal UX & Hand-off Tightening

## Current State
- Hand-off response uses `selection.summary` to embed a CLI command plus `selection.url`; agents must parse text and may skip execution. Polling returns pending immediately, leading to repeated agent calls.
- Terminal UI (questionary) shows title/prompt only; no invocation timestamp or timeout display. Annotation prompts are optional and disabled by default; cancel does not request global annotation. No in-flow settings or interface switch. Navigation relies on arrow keys/space/enter only.
- Terminal client requires the base URL to fetch the session payload; removing URL entirely would break standalone clients unless embedded in the command.

## Decisions
1) **Hand-off contract**
   - Keep `terminal_command` as the canonical, copy-paste-ready command; include `session_id` explicitly.
   - Retain `url` as auxiliary/debug info (needed by the terminal client inside the command), but agents MUST NOT need to parse/use it directly.
   - Add explicit instructions field; polling call blocks up to 30s by default to reduce missed execution.
2) **URL removal analysis**
   - The terminal client must reach the server; the base URL is already embedded in `terminal_command`. Returning `url` is useful for debugging but not required for the agent flow. Conclusion: **do not remove URL entirely**, but treat it as optional/auxiliary; the command + session_id are sufficient for agents.
3) **Terminal UI ergonomics**
   - Display invocation timestamp and timeout countdown in the header.
   - Navigation: support `j`/`k` as aliases for down/up; `Tab` moves focus to annotation input when annotations are shown.
   - Annotations always available; empty input means no note. Cancel action triggers a global-annotation prompt before finalizing cancel.
   - Add a settings entry in the terminal UI to edit global/terminal UI settings and choose to switch this session to web interface (hand-off to web portal with same request/options).
4) **Configuration surface**
   - Settings reachable from terminal UI; updates persist to existing config store and apply to the current session when switching interface.
   - Switching to web should reuse existing request/options and start a web session; terminal session should be cancelled/closed when switching.

## Open Questions / Clarifications
- None pending; URL decision recorded above.

## Scope Mapping
- Specs: Modify `choice-orchestration` for hand-off contract, terminal UX behaviors, configuration surface, annotation defaults, and navigation keys.
- Implementation (future): update MCP response fields, terminal client UI, orchestrator polling, settings switch logic, docs/tests.
