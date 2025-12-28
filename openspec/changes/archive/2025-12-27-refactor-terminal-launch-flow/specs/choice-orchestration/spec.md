## MODIFIED Requirements
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
