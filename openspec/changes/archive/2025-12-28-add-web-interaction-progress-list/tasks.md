## 1. Implementation
- [x] 1.1 Extend the interaction/session model to capture transport type, started time, and status states (pending, submitted, auto-submitted, cancelled, timeout) for both terminal and web flows.
- [x] 1.2 Update orchestrator/session lifecycle to register new interactions (including terminal sessions), mark status transitions on submit/auto-submit/cancel/timeout, and expose a stable list of active sessions plus the five most recent completed ones (bounded to avoid unbounded growth).
- [x] 1.3 Add server endpoints/WS payloads to deliver the interaction list, filters (e.g., active vs completed), and per-session updates to the web client, including safeguards for concurrent agent-triggered sessions.
- [x] 1.4 Update web templates/layout to render a left-side interaction list with status/type badges, filter controls, and re-entry affordances; ensure selection highlights the active session and the sidebar replaces the separate dashboard view for now.
- [x] 1.5 Add tests covering concurrent session creation, filtering, and status transitions for web flows (unit for model/orchestrator, integration for web session list rendering and timeout updates).
- [x] 1.6 Refresh docs/spec references if needed after implementation (README, any in-app help text).
