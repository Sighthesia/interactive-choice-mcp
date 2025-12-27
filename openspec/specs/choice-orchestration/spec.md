# choice-orchestration Specification

## Purpose
TBD - created by archiving change add-provide-choice-capability. Update Purpose after archive.
## Requirements
### Requirement: Provide Choice Tool Contract
The MCP server SHALL expose a `provide_choice` tool with a schema-first request contract including `title`, `prompt`, `selection_mode (single|multi|text_input|hybrid)`, `options[id,label,description,recommended]` (at least one recommended), `placeholder`, `default_selection_ids`, `min_selections`, `max_selections`, and a `single_submit_mode` flag that controls auto-submit vs batch submission. The server SHALL accept optional annotation fields (per-option appendable note and a global annotation), SHALL treat cancel as always available (ignoring disable attempts), and SHALL validate payloads (including min/max ordering, defaults within the option set, and type compatibility) before prompting.

#### Scenario: Valid tool invocation with extended schema
- **WHEN** `provide_choice` is called with required fields plus any of `default_selection_ids`, `min_selections`, `max_selections`, annotation toggles/values, placeholder visibility, and `single_submit_mode`
- **THEN** the server validates the payload (rejecting inverted limits, invalid defaults, or unsupported flags for the chosen type) and rejects malformed requests before starting any user interaction.

#### Scenario: Deterministic response payload with annotations
- **WHEN** a user completes the interaction across any transport
- **THEN** the tool returns `action_status (selected|custom_input|cancelled|timeout)` with a normalized selection payload that orders option ids, enforces min/max counts, preserves default selections when untouched, and includes any option-level or global annotations alongside optional custom input.

### Requirement: Terminal Choice Flow
The system SHALL default to an interactive terminal transport using questionary when stdin is available, rendering an ANSI list, supporting arrow/space/enter, clearing the UI after submission, and printing only a concise summary.

#### Scenario: Terminal selection succeeds
- **WHEN** terminal mode is available and the user confirms a selection via questionary
- **THEN** the prompt renders in the terminal, the UI is cleared after confirmation, and the summarized selection is returned following the result contract.

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

