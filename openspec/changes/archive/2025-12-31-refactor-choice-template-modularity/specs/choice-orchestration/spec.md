## MODIFIED Requirements
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
