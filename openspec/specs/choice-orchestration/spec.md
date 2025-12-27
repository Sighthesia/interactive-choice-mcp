# choice-orchestration Specification

## Purpose
TBD - created by archiving change add-provide-choice-capability. Update Purpose after archive.
## Requirements
### Requirement: Provide Choice Tool Contract
The MCP server SHALL expose a `provide_choice` tool with a schema-first request contract including `title`, `prompt`, `selection_mode (single|multi|text_input|hybrid)`, `options[id,label,description]`, `placeholder`, `default_selection_ids`, `min_selections`, `max_selections`, and a `single_submit_mode` flag that controls auto-submit vs batch submission. The server SHALL accept optional annotation fields (per-option appendable note and a global annotation), SHALL treat cancel as always available (ignoring disable attempts), and SHALL validate payloads (including min/max ordering, defaults within the option set, and type compatibility) before prompting.

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
The system SHALL provide a transient FastAPI-based web portal as a fallback or when explicitly requested, exposing a local URL (e.g., `http://localhost:<port>/choice/<id>`), opening the browser when possible, collecting the choice via WebSocket or long-poll, and shutting down after completion.

#### Scenario: Web portal completes
- **WHEN** terminal mode is unavailable or the caller opts into the web portal
- **THEN** the server starts the temporary FastAPI endpoint, returns the local URL, relays user selections through the portal, and tears down the server after returning the result payload.

### Requirement: Timeout and Cancel Handling
The system SHALL enforce a bounded wait with a configurable timeout (default 5 minutes) for user input across transports, SHALL honor cancellations with cancel always visible/enabled (no toggle to hide it), and SHALL return `timeout` or `cancelled` action statuses without executing further actions.

#### Scenario: User cancels interaction
- **WHEN** the user cancels during the prompt
- **THEN** the tool returns `action_status: cancelled` immediately and halts the current subtask, regardless of prior configuration.

#### Scenario: No response within timeout
- **WHEN** no user response is received within the configured timeout window (default or user override)
- **THEN** the tool returns `action_status: timeout`, shuts down any transient servers, and signals the caller to re-invoke if needed while keeping cancel available on re-entry.

### Requirement: Decision Policy and Prompt Context
The orchestration layer SHALL require callers to include current task context and the reason a choice is needed in the `prompt`, and SHALL invoke `provide_choice` whenever branching options exceed two, an action is destructive, or required configuration is missing, avoiding speculative defaults.

#### Scenario: Branching decision requires user choice
- **WHEN** the system detects more than two viable paths, a destructive action, or missing configuration
- **THEN** it triggers `provide_choice` with contextual prompting instead of selecting a default, ensuring the subsequent action follows the returned selection.

### Requirement: Interaction Configuration Surfaces
The system SHALL present a lightweight configuration surface before prompting, allowing users to choose transport (terminal or web), toggle visibility for any options (arbitrary selection), set a timeout override while preserving sensible defaults, and persist the last-used configuration for subsequent prompts.

#### Scenario: Terminal configuration applied
- **WHEN** terminal transport is selected and the configuration surface is shown
- **THEN** the user can accept defaults or adjust transport, option visibility (arbitrary toggles), and timeout, and the subsequent terminal prompt uses those selections while keeping the UI clear-and-summary behavior.

#### Scenario: Web configuration applied
- **WHEN** web transport is selected or required and the configuration panel is shown in the portal
- **THEN** the panel exposes transport choice (when applicable), option visibility, and timeout controls, and the ensuing web prompt honors the selections and tears down after returning the result payload.

#### Scenario: Persisted configuration reused
- **WHEN** a subsequent invocation starts and a saved configuration exists
- **THEN** the configuration surface pre-populates transport, option visibility, and timeout from the saved values while still allowing overrides, and updates the stored profile after completion.

### Requirement: Choice Interaction Settings
The system SHALL present interaction settings before prompting that let users switch between single-submit (auto-submit on selection) and batch submission (multi-select with explicit submit), preselect default options provided by the caller, toggle placeholder visibility for text-capable modes, and capture optional annotations (per-option notes and a global note). The settings SHALL enforce `min_selections`/`max_selections` bounds consistently across terminal and web flows and persist last-used defaults.

#### Scenario: Single submit vs batch submission
- **WHEN** the settings panel is shown and `single_submit_mode` is enabled
- **THEN** selecting an option auto-submits using the current defaults and enforces bounds; when disabled, users can select multiple options up to `max_selections` and must submit explicitly, with the UI blocking submission if counts fall outside `[min_selections, max_selections]`.

#### Scenario: Option and global annotations captured
- **WHEN** a user appends a note to an option or enters a global annotation because provided options are insufficient
- **THEN** the submitted payload returns those annotations alongside selections (or custom input) and the settings persist the annotation toggle state for subsequent invocations.

#### Scenario: Placeholder visibility control
- **WHEN** a text or hybrid prompt exposes the placeholder toggle
- **THEN** enabling it shows the AI-provided placeholder, disabling hides it, and the captured response notes whether a placeholder was used while keeping selection/annotation data intact.

