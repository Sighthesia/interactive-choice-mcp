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
    └── test_server.py
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

- MCP server endpoint behavior
- Full session lifecycle
- Transport switching (terminal ↔ web)

## Writing New Tests

1. Place unit tests in the appropriate subdirectory under `unit/`
2. Integration tests go in `integration/`
3. Use descriptive test names: `test_<what>_<when>_<expected>`
4. Add shared fixtures to `conftest.py`

## Fixtures

Common fixtures are defined in `conftest.py`:

- Repository root path is automatically added to `sys.path`
- Additional fixtures can be added as needed
