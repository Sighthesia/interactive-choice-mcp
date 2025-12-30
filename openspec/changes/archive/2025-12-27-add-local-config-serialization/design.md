# Design: Local Configuration Serialization

## Architecture
The serialization feature will be implemented as a standalone service to decouple storage concerns from orchestration logic.

### Components
1.  **`ConfigStore` (New)**:
    - Responsibility: Reading from and writing to the local configuration file (default: `~/.interactive_choice_config.json`).
    - Methods: `load() -> ProvideChoiceConfig`, `save(config: ProvideChoiceConfig) -> None`.
    - Logic: Handles JSON parsing, default value injection for missing fields, and atomic writes to prevent file corruption.

2.  **`ProvideChoiceConfig` (Modified)**:
    - Add `option_visibility: Dict[str, bool]`
    - Add `placeholder_visibility: bool`
    - Add `annotation_enabled: bool`

3.  **`ChoiceOrchestrator` (Modified)**:
    - Replace internal `_load_config` and `_persist_config` with a `ConfigStore` instance.
    - Ensure the store is initialized with a configurable path for testing.

## Data Flow
1.  **Initialization**: `ChoiceOrchestrator` creates a `ConfigStore`.
2.  **Request Handling**:
    - `Orchestrator` calls `ConfigStore.load()` to get the last-used settings.
    - These settings are merged with the incoming `ProvideChoiceRequest` to form the defaults for the configuration surface.
3.  **Interaction**:
    - The user adjusts settings in the Terminal or Web UI.
    - The UI returns the updated `ProvideChoiceConfig`.
4.  **Persistence**:
    - After the interaction completes (or cancels, if settings were changed), `Orchestrator` calls `ConfigStore.save(config)`.

## Storage Format
```json
{
  "interface": "terminal",
  "timeout_seconds": 300,
  "single_submit_mode": true,
  "timeout_default_index": 0,
  "timeout_default_enabled": false,
  "use_default_option": false,
  "timeout_action": "submit",
  "option_visibility": {},
  "placeholder_visibility": true,
  "annotation_enabled": true
}
```

## Trade-offs
- **JSON vs. Other Formats**: JSON is chosen for its simplicity and native support in Python. While YAML is more human-readable, it requires an external dependency.
- **Global vs. Per-Project Config**: For now, we stick to a global config in the home directory as per the current implementation, but `ConfigStore` will support a custom path to allow for future per-project overrides.
