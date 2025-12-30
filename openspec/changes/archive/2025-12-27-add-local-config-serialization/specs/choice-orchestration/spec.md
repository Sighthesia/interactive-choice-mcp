# choice-orchestration Specification Delta

## MODIFIED Requirements

### Requirement: Interaction Configuration Surfaces
The system SHALL present a lightweight configuration surface before prompting, allowing users to choose interface (terminal or web), toggle visibility for any options (arbitrary selection), set a timeout override while preserving sensible defaults, and persist the last-used configuration for subsequent prompts. **The configuration SHALL include toggles for placeholder visibility and annotation capture.**

#### Scenario: Expanded configuration persisted
- **WHEN** a user modifies any interaction setting (interface, timeout, option visibility, placeholder visibility, or annotation toggle) in either the Terminal or Web configuration surface
- **THEN** the system SHALL serialize the entire configuration state to a local JSON file and reload it as the default for the next invocation.

### Requirement: Choice Interaction Settings
The system SHALL present interaction settings before prompting that let users switch between single-submit (auto-submit on selection) and batch submission (multi-select with explicit submit), preselect default options provided by the caller, toggle placeholder visibility for text-capable modes, and capture optional annotations (per-option notes and a global note). The settings SHALL enforce `min_selections`/`max_selections` bounds consistently across terminal and web flows and **SHALL persist the state of these settings (including annotation and placeholder toggles) across sessions.**

#### Scenario: Annotation toggle state persisted
- **WHEN** the user disables annotation capture in the configuration surface
- **THEN** subsequent prompts SHALL NOT show annotation input fields until the setting is re-enabled, and this preference SHALL survive server restarts.
