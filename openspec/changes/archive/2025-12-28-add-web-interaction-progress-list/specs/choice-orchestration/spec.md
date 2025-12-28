## MODIFIED Requirements
### Requirement: Web Bridge Flow
The system SHALL provide a transient FastAPI-based web portal as a fallback or when explicitly requested, exposing a local URL (e.g., `http://localhost:<port>/choice/<id>`), opening the browser when possible, collecting the choice via WebSocket or long-poll, and shutting down after completion. **The system SHALL use WebSocket to synchronize the remaining timeout duration between the server and the client in real-time, SHALL support browser notifications for timeout alerts, and SHALL render a left-side interaction list (temporarily replacing the standalone dashboard) that surfaces active interactions plus the five most recent completed ones with their status (pending, submitted, auto-submitted, cancelled, timeout) and transport type (web, terminal), supports filters such as active vs completed, and supports multiple concurrent agent-triggered interactions without cross-contamination.**

#### Scenario: WebSocket synchronization succeeds
- **WHEN** the web portal is loaded and a WebSocket connection is established
- **THEN** the server periodically pushes the remaining timeout seconds to the client, and the client updates its countdown UI to match the server's state.

#### Scenario: Browser notification triggered
- **WHEN** the timeout is approaching (e.g., < 10s) or has occurred, and the browser tab is not in focus
- **THEN** the system triggers a browser notification to alert the user.

#### Scenario: Re-entering an active interaction
- **WHEN** a user accidentally closes a web portal tab but the interaction is still active
- **THEN** the user can navigate to the root URL of the web portal to see the left-side list of active interactions (even without a standalone dashboard view) and select the one they wish to re-enter.

#### Scenario: Interaction list shows status and type
- **WHEN** the choice page renders
- **THEN** the left-side list displays each active interaction and the five most recent completed interactions with badges for status (pending, submitted, auto-submitted, cancelled, timeout) and transport type (web or terminal), including started time or relative age so users can pick the correct session.

#### Scenario: Filtering interactions
- **WHEN** a user switches the interaction list filter (e.g., active vs completed)
- **THEN** the list updates without page reload, remains bounded to the five most recent completed interactions for the selected filter, and continues to include terminal sessions alongside web sessions.

#### Scenario: Concurrent web sessions are isolated
- **WHEN** multiple agents or tool calls create more than one web interaction concurrently
- **THEN** each session appears as a distinct entry in the left-side list, status updates for one session do not overwrite others, and selecting an entry routes to that session while preserving its timeout and state without leaking data across sessions.
