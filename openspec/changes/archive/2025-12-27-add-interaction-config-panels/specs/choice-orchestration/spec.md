## ADDED Requirements
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

## MODIFIED Requirements
### Requirement: Timeout and Cancel Handling
The system SHALL enforce a bounded wait with a configurable timeout (default 5 minutes) for user input across transports, accept user-provided timeout overrides from the configuration surface (including persisted defaults), and honor cancellations, returning `timeout` or `cancelled` action statuses without executing further actions.

#### Scenario: User cancels interaction
- **WHEN** the user cancels during the prompt
- **THEN** the tool returns `action_status: cancelled` immediately and halts the current subtask.

#### Scenario: No response within timeout
- **WHEN** no user response is received within the configured timeout window (default or user override)
- **THEN** the tool returns `action_status: timeout`, shuts down any transient servers, and signals the caller to re-invoke if needed.
