# Proposal: Add Local Configuration Serialization

## Problem
The current configuration persistence is tightly coupled with the `ChoiceOrchestrator` and only covers a subset of the interaction settings. As the system grows, we need a more robust and extensible way to serialize user preferences to local storage, ensuring that all relevant settings (including option visibility and annotation toggles) are preserved across sessions.

## Proposed Change
1.  **Dedicated Storage Layer**: Introduce a `ConfigStore` class in `choice/storage.py` to handle JSON-based serialization of user configurations.
2.  **Expanded Configuration Model**: Update `ProvideChoiceConfig` to include missing fields from the specification:
    - `option_visibility`: Map of option IDs to visibility state.
    - `placeholder_visibility`: Toggle for showing/hiding AI-provided placeholders.
    - `annotation_enabled`: Toggle for capturing per-option and global notes.
3.  **Orchestration Integration**: Refactor `ChoiceOrchestrator` to delegate persistence to `ConfigStore`.
4.  **UI Synchronization**: Ensure both Terminal and Web transports correctly load, display, and update the expanded configuration.

## Impact
- **User Experience**: Users will have their full interaction preferences (not just transport and timeout) remembered between prompts.
- **Maintainability**: Serialization logic is isolated, making it easier to add new settings or change the storage format (e.g., to YAML or a database) in the future.
- **Robustness**: Centralized error handling for file I/O operations.

## Verification Plan
- **Unit Tests**: Test `ConfigStore` for correct serialization/deserialization, handling of missing files, and migration of old formats.
- **Integration Tests**: Verify that `ChoiceOrchestrator` correctly uses `ConfigStore` to persist settings after a successful interaction.
- **Manual Smoke Tests**:
    - Change a setting in the Terminal config panel and verify it's preserved in the next prompt.
    - Change a setting in the Web portal and verify it's preserved.
