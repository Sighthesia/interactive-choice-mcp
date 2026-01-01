# Tests Directory

This directory contains all automated tests for the Interactive Choice MCP project.

## Directory Structure

```
tests/
├── conftest.py          # Shared fixtures and pytest configuration
├── unit/                # Unit tests (isolated, fast)
│   ├── core/           # Core models, validation, response logic
│   │   ├── test_models.py
│   │   └── test_orchestrator.py
│   ├── infra/          # Infrastructure components
│   │   ├── test_i18n.py
│   │   ├── test_logging.py
│   │   └── test_storage.py
│   ├── store/          # Session persistence
│   │   ├── test_interaction_list.py
│   │   └── test_interaction_store.py
│   ├── terminal/       # Terminal UI components
│   │   └── test_terminal_client.py
│   └── web/            # Web server components
│       ├── test_bundler.py
│       ├── test_static_bundle.py
│       └── test_web_timeout.py
└── integration/        # Integration tests (full system flow)
    ├── test_server.py
    ├── test_interaction_web.py
    └── test_interaction_terminal.py
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test category
uv run pytest tests/unit/core/
uv run pytest tests/integration/

# Run with coverage report
uv run pytest --cov=src --cov-report=html

# Run end-to-end interactive test with single choice (default)
uv run pytest tests/integration/test_interaction_web.py::TestWebInteractionManual::test_web_e2e_manual_interaction --interactive -v -s

# Run end-to-end interactive test with multi choice
uv run pytest tests/integration/test_interaction_web.py::TestWebInteractionManual::test_web_e2e_manual_interaction --interactive --selection-mode multi -v -s

# Run end-to-end terminal test with single choice (default)
uv run pytest tests/integration/test_interaction_terminal.py::TestTerminalInteractionManual::test_terminal_e2e_manual_interaction --interactive -v -s

# Run end-to-end terminal test with multi choice
uv run pytest tests/integration/test_interaction_terminal.py::TestTerminalInteractionManual::test_terminal_e2e_manual_interaction --interactive --selection-mode multi -v -s
```

## Test Categories

### Unit Tests (`unit/`)

Fast, isolated tests that mock external dependencies:

- **core/**: Data models, validation logic, response generation
- **infra/**: I18n texts, logging configuration, config storage
- **store/**: Session persistence and retrieval
- **terminal/**: Terminal client functionality
- **web/**: Web bundling, static assets, timeout handling

### Integration Tests (`integration/`)

Tests that verify complete interaction flows:

- **test_server.py**: Web server basic functionality
- **test_interaction_web.py**: Web-based interactive flows
  - Single/multi choice selection
  - Timeout handling
  - Cancellation scenarios
  - Error handling
  - HTML rendering
  - WebSocket communication
- **test_interaction_terminal.py**: Terminal-based interactive flows
  - Terminal hand-off launch
  - End-to-end terminal selection

**Interactive Testing**:

Integration tests include manual interactive tests that require human interaction:
- Use `--interactive` flag to enable manual testing
- Use `--selection-mode single` (default) for single-choice interactions
- Use `--selection-mode multi` for multi-choice interactions
- Without `--interactive`, manual tests are skipped
- Web tests automatically open the browser with the session URL
- Terminal tests display the command to run in a separate terminal

## Writing New Tests

1. Place unit tests in the appropriate subdirectory under `unit/`
2. Integration tests go in `integration/`
3. Use descriptive test names: `test_<what>_<when>_<expected>`
4. Add shared fixtures to `conftest.py`

## Fixtures

Common fixtures are defined in `conftest.py`:

- `web_server`: Provides a running web server instance for integration tests
- `sample_single_choice_request`: Provides a sample single-choice request
- `sample_multi_choice_request`: Provides a sample multi-choice request
- `sample_request`: Provides a sample request based on `--selection-mode` option
- `sample_web_config`: Provides a sample web configuration
- `sample_terminal_config`: Provides a sample terminal configuration
- `interactive`: Returns True if `--interactive` flag is set
- `selection_mode`: Returns the selection mode from `--selection-mode` option (single or multi)
- `persisted_config`: Loads config.json (creates one if missing) for shared test settings

Repository root path is automatically added to `sys.path`. Interactive tests share settings loaded from `.mcp-data/config.json`; if the file is missing a default payload (600s timeout, zh language, single-submit) is created and reused for both web and terminal flows.
