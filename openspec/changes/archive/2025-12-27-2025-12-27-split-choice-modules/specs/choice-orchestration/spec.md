## MODIFIED Requirements

### Requirement: Reduce large file size and enforce single-responsibility
- Description: The `choice` package MUST be organized so that individual source files are small and focused. Files that implement more than one high-level concern (data modeling, validation, transport runtime, template rendering, UI prompts) MUST be split into separate modules.

#### Scenario: Adding a new web feature (e.g., dashboard filter)
- Given an engineer needs to add a UI-only change to the web dashboard,
- When they implement it,
- Then they should only need to modify files under `choice/web/` and not change `models`/`validation`/`response` logic.

#### Scenario: Extending validation rules
- Given a change to request validation,
- When the engineer updates validation logic,
- Then they should only need to modify `choice/validation.py` and update tests focused on validation, without touching `web` or `terminal` modules.

#### Scenario: Unit testing
- Given the code is split by responsibilities,
- When running unit tests,
- Then developers can run focused tests (example: `pytest tests/test_validation.py`) that do not require spinning up web servers or prompts.

### Requirement: Maintain backward compatibility during migration
- Description: During the migration period, existing public imports and function signatures MUST remain usable. Short-term proxy exports are permitted so that importers don't break; proxies MUST include deprecation notes and be removed in a future breaking release.

#### Scenario: Import stability
- Given a consuming module imports `choice.models.parse_request`,
- When the implementation is moved to `choice/validation.py` and `choice/models.py` exposes a proxy,
- Then the existing import path continues to work and tests verify identical behavior.

