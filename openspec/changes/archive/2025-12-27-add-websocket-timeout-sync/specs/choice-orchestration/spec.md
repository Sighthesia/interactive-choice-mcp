# choice-orchestration Specification Delta

## MODIFIED Requirements

### Requirement: Web Bridge Flow
The system SHALL provide a transient FastAPI-based web portal as a fallback or when explicitly requested, exposing a local URL (e.g., `http://localhost:<port>/choice/<id>`), opening the browser when possible, collecting the choice via WebSocket or long-poll, and shutting down after completion. **The system SHALL use WebSocket to synchronize the remaining timeout duration between the server and the client in real-time, SHALL support browser notifications for timeout alerts, and SHALL provide a dashboard to list and re-enter active interactions.**

#### Scenario: WebSocket synchronization succeeds
- **WHEN** the web portal is loaded and a WebSocket connection is established
- **THEN** the server periodically pushes the remaining timeout seconds to the client, and the client updates its countdown UI to match the server's state.

#### Scenario: Browser notification triggered
- **WHEN** the timeout is approaching (e.g., < 10s) or has occurred, and the browser tab is not in focus
- **THEN** the system triggers a browser notification to alert the user.

#### Scenario: Re-entering an active interaction
- **WHEN** a user accidentally closes a web portal tab but the interaction is still active
- **THEN** the user can navigate to the root URL of the web portal to see a list of active interactions and select the one they wish to re-enter.

### Requirement: Timeout and Cancel Handling
The system SHALL enforce a bounded wait with a configurable timeout (default 5 minutes) for user input across transports, SHALL honor cancellations with cancel always visible/enabled (no toggle to hide it), and SHALL return `timeout` or `cancelled` action statuses without executing further actions. **In the web interface, the timeout deadline SHALL be dynamically adjustable, and the server SHALL maintain the authoritative expiration time.**

#### Scenario: Dynamic timeout update in web portal
- **WHEN** a user adjusts the timeout value in the web portal configuration panel
- **THEN** the client notifies the server of the new timeout duration, the server updates its internal deadline, and the updated remaining time is synchronized back to the client via WebSocket.
