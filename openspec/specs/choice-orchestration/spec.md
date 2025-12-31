# choice-orchestration Specification

## Purpose
TBD - created by archiving change add-provide-choice-capability. Update Purpose after archive.
## Requirements
### Requirement: Provide Choice Tool Contract
The terminal hand-off response SHALL return structured fields: `terminal_command` (copy-paste ready), `session_id`, and an `instructions` string that explicitly directs the agent to run the command and then poll with the same session id. A `url` MAY be included for diagnostics or client connectivity, but agents MUST NOT depend on parsing it when `terminal_command` is present. Polling a session_id SHALL block up to a bounded interval (e.g., 30s) before returning pending/timeout to reduce missed executions.

#### Scenario: Structured hand-off response
- **WHEN** terminal interface is requested and hand-off is used
- **THEN** the response includes `terminal_command`, `session_id`, optional `url`, and `instructions` that tell the agent to execute the command and poll; no freeform parsing of `summary` is required.

#### Scenario: Blocking poll reduces missed execution
- **WHEN** `provide_choice` is called with `session_id`
- **THEN** the server waits up to the configured blocking window for a terminal submission before replying, returning the final result if ready, otherwise pending/timeout, minimizing repeated agent calls.

### Requirement: Terminal Choice Flow
The terminal UI SHALL display invocation time and timeout countdown, support `j`/`k` as aliases for down/up navigation, allow `Tab` to focus annotation input, and keep per-option/global annotations always available (empty input yields no annotation). Selecting cancel SHALL prompt for global annotation before completing cancel. The terminal UI SHALL provide a settings entry that lets the user adjust global and terminal UI settings and trigger a switch of the current session to the web interface.

#### Scenario: Ergonomic navigation and annotations
- **WHEN** the terminal prompt is shown
- **THEN** the header shows invocation time and remaining timeout, navigation accepts arrows or `j`/`k`, `Tab` focuses annotation fields, and annotations are offered by default; empty submissions are treated as no annotation.

#### Scenario: Cancel with global annotation
- **WHEN** the user chooses cancel
- **THEN** the UI requests a global annotation (optional text) before emitting the `cancelled` action.

#### Scenario: Settings and interface switch
- **WHEN** the user enters the settings entry from the terminal UI
- **THEN** they can update persisted global/terminal UI settings and choose to switch this interaction to the web interface, which cancels the terminal session and starts a web session with the same request/options.

### Requirement: Web Bridge Flow
The system SHALL provide a transient FastAPI-based web portal as a fallback or when explicitly requested, exposing a local URL (e.g., `http://localhost:<port>/choice/<id>`), opening the browser when possible, collecting the choice via WebSocket or long-poll, and shutting down after completion. **The system SHALL use WebSocket to synchronize the remaining timeout duration between the server and the client in real-time, SHALL support browser notifications for timeout alerts, and SHALL render a left-side interaction list (temporarily replacing the standalone dashboard) that surfaces active interactions plus the five most recent completed ones with their status (pending, submitted, auto-submitted, cancelled, timeout) and interface type (web, terminal), supports filters such as active vs completed, and supports multiple concurrent agent-triggered interactions without cross-contamination.**

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
- **THEN** the left-side list displays each active interaction and the five most recent completed interactions with badges for status (pending, submitted, auto-submitted, cancelled, timeout) and interface type (web or terminal), including started time or relative age so users can pick the correct session.

#### Scenario: Filtering interactions
- **WHEN** a user switches the interaction list filter (e.g., active vs completed)
- **THEN** the list updates without page reload, remains bounded to the five most recent completed interactions for the selected filter, and continues to include terminal sessions alongside web sessions.

#### Scenario: Concurrent web sessions are isolated
- **WHEN** multiple agents or tool calls create more than one web interaction concurrently
- **THEN** each session appears as a distinct entry in the left-side list, status updates for one session do not overwrite others, and selecting an entry routes to that session while preserving its timeout and state without leaking data across sessions.

### Requirement: REQ-INTERACTION-LIST Interaction List Includes History
The interaction list endpoint MUST include persisted historical sessions.

#### Scenario: Historical sessions in list
- **Given**: Persisted sessions exist in storage
- **When**: Client requests interaction list
- **Then**: Response includes both active and historical sessions (limited to configured count)

### Requirement: Timeout and Cancel Handling
The system SHALL enforce a bounded wait with a configurable timeout (default 5 minutes) for user input across transports, SHALL honor cancellations with cancel always visible/enabled (no toggle to hide it), and SHALL return `timeout` or `cancelled` action statuses without executing further actions. **In the web interface, the timeout deadline SHALL be dynamically adjustable, and the server SHALL maintain the authoritative expiration time.**

#### Scenario: Dynamic timeout update in web portal
- **WHEN** a user adjusts the timeout value in the web portal configuration panel
- **THEN** the client notifies the server of the new timeout duration, the server updates its internal deadline, and the updated remaining time is synchronized back to the client via WebSocket.

### Requirement: Decision Policy and Prompt Context
The orchestration layer SHALL require callers to include current task context and the reason a choice is needed in the `prompt`, and SHALL invoke `provide_choice` whenever branching options exceed two, an action is destructive, or required configuration is missing, avoiding speculative defaults.

#### Scenario: Branching decision requires user choice
- **WHEN** the system detects more than two viable paths, a destructive action, or missing configuration
- **THEN** it triggers `provide_choice` with contextual prompting instead of selecting a default, ensuring the subsequent action follows the returned selection.

### Requirement: Interaction Configuration Surfaces
The configuration surface SHALL be reachable from the terminal UI, persist updates to the configuration store, and apply immediately to the current session when switching interface (terminal→web). Settings include interface selection, timeout override, annotation availability (default on), and terminal UI controls (navigation hints, annotation focus behavior).

#### Scenario: Terminal-accessible configuration persistence
- **WHEN** a user opens settings from the terminal UI and modifies interface, timeout, or annotation/navigation toggles
- **THEN** the changes are saved to the config store, affect the current interaction (including when switching to web), and become defaults for subsequent sessions.

### Requirement: Choice Interaction Settings
The system SHALL present interaction settings before prompting that let users switch between single-submit (auto-submit on selection) and batch submission (multi-select with explicit submit), preselect default options provided by the caller, toggle placeholder visibility for text-capable modes, and capture optional annotations (per-option notes and a global note). The settings SHALL enforce `min_selections`/`max_selections` bounds consistently across terminal and web flows and **SHALL persist the state of these settings (including annotation and placeholder toggles) across sessions.**

#### Scenario: Annotation toggle state persisted
- **WHEN** the user disables annotation capture in the configuration surface
- **THEN** subsequent prompts SHALL NOT show annotation input fields until the setting is re-enabled, and this preference SHALL survive server restarts.

### Requirement: Reduce large file size and enforce single-responsibility
- Description: The `choice` package MUST be organized so that individual source files are small and focused. Files that implement more than one high-level concern (data modeling, validation, interface runtime, template rendering, UI prompts) MUST be split into separate modules. The web portal SHALL source its styles and scripts from concern-specific modules assembled via an explicit manifest into the delivered page, keeping i18n/config wiring centralized, and SHALL expose a versioned static bundle route (with inline fallback) so the assembled assets can be cached and smoke-tested.

#### Scenario: Adding a new web feature (e.g., dashboard filter)
- **Given** an engineer needs to add a UI-only change to the web dashboard,
- **When** they implement it,
- **Then** they should only need to modify files under `choice/web/` (including the modular frontend asset sources) and not change `models`/`validation`/`response` logic.

#### Scenario: Extending validation rules
- **Given** a change to request validation,
- **When** the engineer updates validation logic,
- **Then** they should only need to modify `choice/validation.py` and update tests focused on validation, without touching `web` or `terminal` modules.

#### Scenario: Unit testing
- **Given** the code is split by responsibilities,
- **When** running unit tests,
- **Then** developers can run focused tests (example: `pytest tests/test_validation.py`) that do not require spinning up web servers or prompts.

#### Scenario: Web assets assembled from modules
- **WHEN** the web portal page is rendered,
- **THEN** styles and scripts originate from manifest-ordered modules grouped by concern (layout, rendering, config/i18n, sockets/timeout, interaction list), are assembled into the delivered HTML (inline or versioned bundle), and i18n/config payload handling lives in the dedicated modules without duplicating logic across files.

#### Scenario: Static bundle served and smoke-tested
- **WHEN** the hashed static bundle route is requested,
- **THEN** it responds 200 with content matching the manifest order/hash, emits cache-friendly headers, and a smoke test verifies the bundle is reachable alongside the inline fallback remaining functional.

### Requirement: Maintain backward compatibility during migration
- Description: During the migration period, existing public imports and function signatures MUST remain usable. Short-term proxy exports are permitted so that importers don't break; proxies MUST include deprecation notes and be removed in a future breaking release.

#### Scenario: Import stability
- Given a consuming module imports `choice.models.parse_request`,
- When the implementation is moved to `choice/validation.py` and `choice/models.py` exposes a proxy,
- Then the existing import path continues to work and tests verify identical behavior.

### Requirement: REQ-PERSIST-01 Session Persistence
The system MUST persist completed sessions to local storage.

#### Scenario: Session saved after completion
- **Given**: A web or terminal session is completed
- **When**: The session result is finalized
- **Then**: The session data is written to disk

### Requirement: REQ-PERSIST-02 Historical Session Loading
The system MUST load historical sessions on server startup.

#### Scenario: Server restart preserves history
- **Given**: Completed sessions exist in storage
- **When**: The server starts
- **Then**: Historical sessions appear in the interaction list

### Requirement: REQ-PERSIST-03 Retention Policy
The system MUST automatically clean up sessions based on retention policy.

#### Scenario: Expired sessions removed
- **Given**: Sessions older than retention period exist
- **When**: Cleanup runs (on startup or periodically)
- **Then**: Expired sessions are removed from storage

### Requirement: REQ-PERSIST-04 Session Count Limit
The system MUST enforce a maximum session count limit.

#### Scenario: Oldest sessions removed when limit exceeded
- **Given**: Number of stored sessions equals max limit
- **When**: A new session is saved
- **Then**: The oldest session is removed to make room

### Requirement: Interface language selection
The system SHALL allow users to choose the interaction interface language (English or Simplified Chinese) before the prompt is shown and persist this preference across terminal and web sessions. The selected language SHALL be applied to user-facing text (labels, settings, actions) for the active session.

#### Scenario: Language selectable before prompt
- **WHEN** a user opens the configuration UI (terminal settings entry or web settings panel) before the choice prompt renders
- **THEN** they can pick English or Chinese, the UI text updates immediately for the current session, and the preference is saved for subsequent sessions.

#### Scenario: Persisted language applied on restart
- **WHEN** the server restarts and a stored language preference exists
- **THEN** the system loads that preference and uses it as the default language for both terminal and web transports until changed.

### Requirement: Environment language default
The system SHALL read an MCP environment variable `CHOICE_LANG` (values `en` or `zh`) to determine the default interface language when a session starts. Invalid or unsupported values SHALL fall back to English and log a warning. The environment default SHALL be applied before stored configuration or other overrides.

#### Scenario: Environment variable sets default
- **WHEN** `CHOICE_LANG=zh` is set in the environment and a new session starts
- **THEN** the terminal or web UI renders using Chinese text without manual selection, while still allowing users to switch languages in settings.

#### Scenario: Invalid environment value falls back
- **WHEN** `CHOICE_LANG` is set to an unsupported value
- **THEN** the system logs a warning, defaults to English, and allows users to change language via settings.

