## Context
- The web portal currently lists active interactions but lacks visibility into status transitions (submitted, auto-submitted, timeout, pending) and transport type (web vs terminal hand-off), which makes concurrent sessions ambiguous.
- Multiple agents can trigger `provide_choice` concurrently, creating overlapping web sessions that need isolation, stable routing, and user-friendly selection.
- Existing assets: FastAPI server, `choice/web/session.py` for session management, `choice/web/templates.py` and HTML templates for dashboard/choice pages, and WebSocket-based timeout sync.

## Goals / Non-Goals
- Goals: render a left-side interaction list showing active interactions and the five most recent completed ones (including terminal sessions) with status/type and filter controls, support re-entry into the correct session, and keep concurrent sessions isolated with live updates.
- Non-Goals: redesigning the entire dashboard layout beyond replacing it with the sidebar list for now, adding persistent history beyond the bounded recent list, or changing the terminal hand-off contract.

## Decisions
- Maintain a server-side interaction registry that tracks session id, transport type, created/updated timestamps, and status transitions (pending, submitted, auto-submitted, cancelled, timeout) for both web and terminal transports.
- Bound the recent list to the five most recent completed interactions while always showing all active ones; include terminal sessions in the same list.
- Broadcast interaction list changes over existing WebSocket channels (or an added channel) so the left panel stays current without page reloads; fall back to a lightweight polling endpoint if WS is unavailable.
- Render the interaction list as a left sidebar (replacing the separate dashboard view for now), with clear badges for status/type, filter controls for active vs completed, and a highlight for the active session.
- Preserve re-entry behavior: selecting an entry should navigate to the appropriate session route while validating that the session is still active or showing a finalized summary if completed/expired.

## Risks / Trade-offs
- Risk: unbounded session accumulation; Mitigation: enforce limits and cleanup on completion/timeout.
- Risk: race conditions from multiple agents updating the same session; Mitigation: session registry keyed by session id with atomic status transitions and idempotent updates.
- Risk: browser stale state if WS drops; Mitigation: periodic refresh/polling fallback.

## Migration Plan
- Add registry fields and WS/poll payloads without breaking existing session routes.
- Introduce sidebar templates behind feature-compatible markup to avoid regressions for current dashboard/choice pages.
- Validate via tests for concurrent session creation, status updates, and timeout handling before rollout.

## Open Questions
- Clarify whether any meaning was intended by "修改spen" in the feedback (assumed to request spec updates; confirm scope).
- Should terminal-only sessions always appear in the web list, or only when a web dashboard is requested? (current plan: always include)
- Do we need user-facing filters beyond active vs completed (e.g., transport-specific, status-specific) in the initial version?
