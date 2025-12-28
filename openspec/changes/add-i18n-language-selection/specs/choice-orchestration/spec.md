## ADDED Requirements
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
