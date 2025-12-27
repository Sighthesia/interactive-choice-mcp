## MODIFIED Requirements
### Requirement: Provide Choice Tool Contract
The terminal hand-off response SHALL return structured fields: `terminal_command` (copy-paste ready), `session_id`, and an `instructions` string that explicitly directs the agent to run the command and then poll with the same session id. A `url` MAY be included for diagnostics or client connectivity, but agents MUST NOT depend on parsing it when `terminal_command` is present. Polling a session_id SHALL block up to a bounded interval (e.g., 30s) before returning pending/timeout to reduce missed executions.

#### Scenario: Structured hand-off response
- **WHEN** terminal transport is requested and hand-off is used
- **THEN** the response includes `terminal_command`, `session_id`, optional `url`, and `instructions` that tell the agent to execute the command and poll; no freeform parsing of `summary` is required.

#### Scenario: Blocking poll reduces missed execution
- **WHEN** `provide_choice` is called with `session_id`
- **THEN** the server waits up to the configured blocking window for a terminal submission before replying, returning the final result if ready, otherwise pending/timeout, minimizing repeated agent calls.

### Requirement: Terminal Choice Flow
The terminal UI SHALL display invocation time and timeout countdown, support `j`/`k` as aliases for down/up navigation, allow `Tab` to focus annotation input, and keep per-option/global annotations always available (empty input yields no annotation). Selecting cancel SHALL prompt for global annotation before completing cancel. The terminal UI SHALL provide a settings entry that lets the user adjust global and terminal UI settings and trigger a switch of the current session to the web transport.

#### Scenario: Ergonomic navigation and annotations
- **WHEN** the terminal prompt is shown
- **THEN** the header shows invocation time and remaining timeout, navigation accepts arrows or `j`/`k`, `Tab` focuses annotation fields, and annotations are offered by default; empty submissions are treated as no annotation.

#### Scenario: Cancel with global annotation
- **WHEN** the user chooses cancel
- **THEN** the UI requests a global annotation (optional text) before emitting the `cancelled` action.

#### Scenario: Settings and transport switch
- **WHEN** the user enters the settings entry from the terminal UI
- **THEN** they can update persisted global/terminal UI settings and choose to switch this interaction to the web transport, which cancels the terminal session and starts a web session with the same request/options.

### Requirement: Interaction Configuration Surfaces
The configuration surface SHALL be reachable from the terminal UI, persist updates to the configuration store, and apply immediately to the current session when switching transport (terminal→web). Settings include transport selection, timeout override, annotation availability (default on), and terminal UI controls (navigation hints, annotation focus behavior).

#### Scenario: Terminal-accessible configuration persistence
- **WHEN** a user opens settings from the terminal UI and modifies transport, timeout, or annotation/navigation toggles
- **THEN** the changes are saved to the config store, affect the current interaction (including when switching to web), and become defaults for subsequent sessions.
