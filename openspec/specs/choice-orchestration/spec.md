# choice-orchestration Specification

## Purpose
TBD - created by archiving change add-provide-choice-capability. Update Purpose after archive.
## Requirements
### Requirement: Provide Choice Tool Contract
The MCP server SHALL expose a `provide_choice` tool with a schema-first request contract including `title`, `prompt`, `selection_mode (single|multi|text_input|hybrid)`, `options[id,label,description,recommended]` (at least one recommended), `placeholder`, `default_selection_ids`, `min_selections`, `max_selections`, and a `single_submit_mode` flag that controls auto-submit vs batch submission. The server SHALL accept optional annotation fields (per-option appendable note and a global annotation), SHALL treat cancel as always available (ignoring disable attempts), and SHALL validate payloads (including min/max ordering, defaults within the option set, and type compatibility) before prompting. The server SHALL support a terminal hand-off session/process identifier for polling an already-launched terminal session, SHALL allow the `action_status` value `pending_terminal_launch` when returning a launch address for the terminal UI, SHALL place the launch address/command in `selection.url` and/or `selection.summary` when deferring to the external terminal client, and SHALL document that terminal sessions are single-use (retries require launching a new session).

#### Scenario: Valid tool invocation with extended schema
- **WHEN** `provide_choice` is called with required fields plus any of `default_selection_ids`, `min_selections`, `max_selections`, annotation toggles/values, placeholder visibility, and `single_submit_mode`
- **THEN** the server validates the payload (rejecting inverted limits, invalid defaults, or unsupported flags for the chosen type) and rejects malformed requests before starting any user interaction.

#### Scenario: Deterministic response payload with annotations
- **WHEN** a user completes the interaction across any transport
- **THEN** the tool returns `action_status (selected|custom_input|cancelled|timeout)` with a normalized selection payload that orders option ids, enforces min/max counts, preserves default selections when untouched, and includes any option-level or global annotations alongside optional custom input.

#### Scenario: Terminal hand-off response
- **WHEN** the caller requests terminal transport and the server enables the hand-off launch mode
- **THEN** the tool responds immediately with `action_status=pending_terminal_launch`, populates `selection.url` and `selection.summary` with the launch address/command for the terminal UI (including the session/process id), and records that session id so a follow-up `provide_choice` call (using that session id) can return the finalized `ProvideChoiceResponse` once the user completes the interaction.

### Requirement: Terminal Choice Flow
The system SHALL default to an interactive terminal transport using questionary when stdin is available, rendering an ANSI list, supporting arrow/space/enter, clearing the UI after submission, and printing only a concise summary. The system SHALL also support a terminal hand-off flow where the MCP request allocates a session, returns immediately with a launch address/command for the external terminal client (to be executed by the AI via the terminal command tool), and keeps the session pending until the client posts the result or the session times out, enforcing the same timeout/cancel/default-selection rules as the in-process terminal flow. Sessions are single-use; reconnect attempts require launching a new session/command.

#### Scenario: Terminal selection succeeds
- **WHEN** terminal mode is available and the user confirms a selection via questionary
- **THEN** the prompt renders in the terminal, the UI is cleared after confirmation, and the summarized selection is returned following the result contract.

#### Scenario: Terminal hand-off launch
- **WHEN** terminal hand-off mode is used
- **THEN** the MCP tool returns immediately with a launch address/command for the terminal UI, records the session with timeout metadata, and the agent can execute the returned command to open the questionary UI for the user.

#### Scenario: Terminal hand-off completion
- **WHEN** the terminal client posts a selection, cancel, or timeout for a pending session
- **THEN** a subsequent `provide_choice` call that references the session id returns the finalized `ProvideChoiceResponse` (including annotations and selected ids), and the session is cleaned up to prevent reuse; reconnecting to the same session is not supported.

#### Scenario: Terminal hand-off timeout without attach
- **WHEN** no terminal client attaches or submits before the session deadline
- **THEN** the session transitions to timeout using the configured timeout action/default selection, and the follow-up `provide_choice` call for that session id returns the timeout response.

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
The system SHALL enforce a bounded wait with a configurable timeout (default 5 minutes) for user input across transports, SHALL honor cancellations with cancel always visible/enabled (no toggle to hide it), and SHALL return `timeout` or `cancelled` action statuses without executing further actions. **In the web transport, the timeout deadline SHALL be dynamically adjustable, and the server SHALL maintain the authoritative expiration time.**

#### Scenario: Dynamic timeout update in web portal
- **WHEN** a user adjusts the timeout value in the web portal configuration panel
- **THEN** the client notifies the server of the new timeout duration, the server updates its internal deadline, and the updated remaining time is synchronized back to the client via WebSocket.

### Requirement: Decision Policy and Prompt Context
The orchestration layer SHALL require callers to include current task context and the reason a choice is needed in the `prompt`, and SHALL invoke `provide_choice` whenever branching options exceed two, an action is destructive, or required configuration is missing, avoiding speculative defaults.

#### Scenario: Branching decision requires user choice
- **WHEN** the system detects more than two viable paths, a destructive action, or missing configuration
- **THEN** it triggers `provide_choice` with contextual prompting instead of selecting a default, ensuring the subsequent action follows the returned selection.

### Requirement: Interaction Configuration Surfaces
The system SHALL present a lightweight configuration surface before prompting, allowing users to choose transport (terminal or web), toggle visibility for any options (arbitrary selection), set a timeout override while preserving sensible defaults, and persist the last-used configuration for subsequent prompts. **The configuration SHALL include toggles for placeholder visibility and annotation capture.**

#### Scenario: Expanded configuration persisted
- **WHEN** a user modifies any interaction setting (transport, timeout, option visibility, placeholder visibility, or annotation toggle) in either the Terminal or Web configuration surface
- **THEN** the system SHALL serialize the entire configuration state to a local JSON file and reload it as the default for the next invocation.

### Requirement: Choice Interaction Settings
The system SHALL present interaction settings before prompting that let users switch between single-submit (auto-submit on selection) and batch submission (multi-select with explicit submit), preselect default options provided by the caller, toggle placeholder visibility for text-capable modes, and capture optional annotations (per-option notes and a global note). The settings SHALL enforce `min_selections`/`max_selections` bounds consistently across terminal and web flows and **SHALL persist the state of these settings (including annotation and placeholder toggles) across sessions.**

#### Scenario: Annotation toggle state persisted
- **WHEN** the user disables annotation capture in the configuration surface
- **THEN** subsequent prompts SHALL NOT show annotation input fields until the setting is re-enabled, and this preference SHALL survive server restarts.

### Requirement: Reduce large file size and enforce single-responsibility
- Description: The `choice` package MUST be organized so that individual source files are small and focused. Files that implement more than one high-level concern (data modeling, validation, transport runtime, template rendering, UI prompts) MUST be split into separate modules.

#### Scenario: Adding a new web feature (e.g., dashboard filter)
- Given an engineer needs to add a UI-only change to the web dashboard,
- When they implement it,
- Then they should only need to modify files under `choice/web/` and not change `models`/`validation`/`response` logic.

#### Scenario: Extending validation rules
- Given a change to request validation,
- When the engineer updates validation logic,
- Then they should only need to modify `choice/validation.py` and update tests focused on validation, without touching `web` or `terminal` modules.

#### Scenario: Unit testing
- Given the code is split by responsibilities,
- When running unit tests,
- Then developers can run focused tests (example: `pytest tests/test_validation.py`) that do not require spinning up web servers or prompts.

### Requirement: Maintain backward compatibility during migration
- Description: During the migration period, existing public imports and function signatures MUST remain usable. Short-term proxy exports are permitted so that importers don't break; proxies MUST include deprecation notes and be removed in a future breaking release.

#### Scenario: Import stability
- Given a consuming module imports `choice.models.parse_request`,
- When the implementation is moved to `choice/validation.py` and `choice/models.py` exposes a proxy,
- Then the existing import path continues to work and tests verify identical behavior.

