# Tasks: Add Local Configuration Serialization

- [ ] **Infrastructure**
    - [ ] Create `choice/storage.py` and implement `ConfigStore` class.
    - [ ] Add unit tests for `ConfigStore` in `tests/test_storage.py`.
- [ ] **Model Updates**
    - [ ] Update `ProvideChoiceConfig` in `choice/models.py` with new fields (`option_visibility`, `placeholder_visibility`, `annotation_enabled`).
    - [ ] Update `parse_request` and `apply_configuration` if necessary to handle new fields.
- [ ] **Orchestrator Refactoring**
    - [ ] Update `ChoiceOrchestrator` in `choice/orchestrator.py` to use `ConfigStore`.
    - [ ] Remove legacy `_load_config` and `_persist_config` methods.
    - [ ] Update `_build_default_config` to handle new fields.
- [ ] **UI Integration**
    - [ ] **Terminal**: Update `prompt_configuration` in `choice/terminal.py` to include toggles for the new fields.
    - [ ] **Web**: Update `_render_html` and `_parse_config_payload` in `choice/web.py` to handle the new fields.
    - [ ] **Web**: Update `choice/templates/choice.html` to include UI elements for the new configuration options.
- [ ] **Validation**
    - [ ] Run `uv run pytest` to ensure all tests pass.
    - [ ] Perform manual smoke tests for both Terminal and Web flows.
    - [ ] Run `openspec validate add-local-config-serialization --strict`.
