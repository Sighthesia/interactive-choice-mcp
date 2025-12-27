## MODIFIED Requirements
### Requirement: Provide Choice Tool Contract
The MCP server SHALL expose a `provide_choice` tool with a schema-first request contract including `title`, `prompt`, `type (single_select|multi_select|text_input|hybrid)`, `options[id,label,description]`, `placeholder`, `default_selection_ids`, `min_selections`, `max_selections`, and a `single_submit_mode` flag that controls auto-submit vs batch submission. The server SHALL accept optional annotation fields (per-option appendable note and a global annotation), SHALL treat cancel as always available (ignoring disable attempts), and SHALL validate payloads (including min/max ordering, defaults within the option set, and type compatibility) before prompting.

#### Scenario: Valid tool invocation with extended schema
- **WHEN** `provide_choice` is called with required fields plus any of `default_selection_ids`, `min_selections`, `max_selections`, annotation toggles/values, placeholder visibility, and `single_submit_mode`
- **THEN** the server validates the payload (rejecting inverted limits, invalid defaults, or unsupported flags for the chosen type) and rejects malformed requests before starting any user interaction.

#### Scenario: Deterministic response payload with annotations
- **WHEN** a user completes the interaction across any transport
- **THEN** the tool returns `action_status (selected|custom_input|cancelled|timeout)` with a normalized selection payload that orders option ids, enforces min/max counts, preserves default selections when untouched, and includes any option-level or global annotations alongside optional custom input.

### Requirement: Timeout and Cancel Handling
The system SHALL enforce a bounded wait with a configurable timeout (default 5 minutes) for user input across transports, SHALL honor cancellations with cancel always visible/enabled (no toggle to hide it), and SHALL return `timeout` or `cancelled` action statuses without executing further actions.

#### Scenario: User cancels interaction
- **WHEN** the user cancels during the prompt
- **THEN** the tool returns `action_status: cancelled` immediately and halts the current subtask, regardless of prior configuration.

#### Scenario: No response within timeout
- **WHEN** no user response is received within the configured timeout window (default or user override)
- **THEN** the tool returns `action_status: timeout`, shuts down any transient servers, and signals the caller to re-invoke if needed while keeping cancel available on re-entry.

## ADDED Requirements
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
