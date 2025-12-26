# choice-orchestration Specification

## Purpose
TBD - created by archiving change add-provide-choice-capability. Update Purpose after archive.
## Requirements
### Requirement: Provide Choice Tool Contract
The MCP server SHALL expose a `provide_choice` tool with a schema-first request contract including `title`, `prompt`, `type (single_select|multi_select)`, `options[label,description]`, and `allow_cancel`, and SHALL validate payloads before prompting.

#### Scenario: Valid tool invocation
- **WHEN** `provide_choice` is called with all required fields according to the schema
- **THEN** the server validates the payload and rejects malformed requests before starting any user interaction.

#### Scenario: Deterministic response payload
- **WHEN** a user completes the interaction across any transport
- **THEN** the tool returns `action_status (selected|cancelled|timeout)` with a normalized selection payload, capturing selected indices and optional annotations.

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
The system SHALL enforce a bounded wait with a configurable timeout (default 5 minutes) for user input across transports and honor cancellations, returning `timeout` or `cancelled` action statuses without executing further actions.

#### Scenario: User cancels interaction
- **WHEN** the user cancels during the prompt
- **THEN** the tool returns `action_status: cancelled` immediately and halts the current subtask.

#### Scenario: No response within timeout
- **WHEN** no user response is received within the configured timeout window (default 5 minutes)
- **THEN** the tool returns `action_status: timeout`, shuts down any transient servers, and signals the caller to re-invoke if needed.

### Requirement: Decision Policy and Prompt Context
The orchestration layer SHALL require callers to include current task context and the reason a choice is needed in the `prompt`, and SHALL invoke `provide_choice` whenever branching options exceed two, an action is destructive, or required configuration is missing, avoiding speculative defaults.

#### Scenario: Branching decision requires user choice
- **WHEN** the system detects more than two viable paths, a destructive action, or missing configuration
- **THEN** it triggers `provide_choice` with contextual prompting instead of selecting a default, ensuring the subsequent action follows the returned selection.

