<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->
# Interactive Choice MCP – Guide

## Priority Guidelines

When generating code for this repository:

1. **Version Compatibility**: Always detect and respect the exact versions of languages, frameworks, and libraries used in this project
2. **Context Files**: Prioritize patterns and standards defined in AGENTS.md at the repository root
3. **Codebase Patterns**: When context files don't provide specific guidance, scan the codebase for established patterns
4. **Architectural Consistency**: Maintain our layered architectural style with clear module boundaries
5. **Code Quality**: Prioritize maintainability, testability, and robustness in all generated code

## Technology Version Detection

Before generating code, scan the codebase to identify:

1. **Language Versions**: Python 3.12 or higher (as specified in pyproject.toml: `requires-python = ">=3.12"`)
   - Use Python 3.12+ features (match statements, type parameter defaults, etc.)
   - Never use features incompatible with Python 3.12

2. **Framework Versions**: Exact versions from pyproject.toml
   - FastAPI >= 0.127.0
   - FastMCP >= 2.14.1
   - Uvicorn >= 0.40.0
   - WebSockets >= 13.0
   - Questionary >= 2.1.1
   - Pytest >= 7.4, pytest-asyncio >= 0.23.0
   - Respect version constraints when generating code

3. **Library Versions**: Note the exact versions of key libraries
   - Generate code compatible with these specific versions
   - Never use APIs or features not available in the detected versions

## Context Files

Prioritize the following files in the repository root:

- **AGENTS.md**: Project overview, architecture guidelines, code style, testing instructions, and workflow documentation
- **openspec/AGENTS.md**: OpenSpec instructions for planning and proposals
- **README.md**: Project description and setup instructions

## Codebase Scanning Instructions

When context files don't provide specific guidance:

1. Identify similar files to the one being modified or created
2. Analyze patterns for:
   - Naming conventions (complete English words, no non-standard abbreviations)
   - Code organization (layered architecture: core, mcp, infra, store, terminal, web)
   - Error handling (custom ValidationError, try-except wrapping)
   - Logging approaches (get_logger factory function)
   - Documentation style (module docstrings, public API docs with parameter lists)
   - Testing patterns (pytest fixtures, async tests, test naming: test_<what>_<when>_<expected>)

3. Follow the most consistent patterns found in the codebase
4. When conflicting patterns exist, prioritize patterns in newer files or files with higher test coverage
5. Never introduce patterns not found in the existing codebase

## Code Quality Standards

### Maintainability
- Write self-documenting code with clear naming using complete English words
- Follow the naming and organization conventions evident in the codebase
- Follow established patterns for consistency
- Keep functions focused on single responsibilities
- Limit function complexity and length to match existing patterns
- Use `__all__` to explicitly define public API exports

### Testability
- Follow established patterns for testable code
- Use dependency injection for orchestrator and store classes
- Apply the same patterns for managing dependencies
- Follow established mocking and test double patterns in tests
- Match the testing style used in existing tests (pytest with fixtures)
- Keep test code strictly separated from source files

### Robustness
- Use custom ValidationError for validation failures with descriptive messages
- Apply the same error handling patterns used in the codebase
- Use try-except blocks to wrap exceptions and provide context
- Handle edge cases explicitly (e.g., duplicate IDs, empty strings)
- Use type hints consistently throughout the codebase

## Documentation Requirements

### Standard
- Follow the exact documentation format found in the codebase
- Module-level docstrings explain purpose and contents
- Public APIs must include standard documentation comments with parameter lists
- Document parameters, returns, and exceptions in the same style
- Follow existing patterns for usage examples
- Match class-level documentation style and content

### Code Comments
- Add one-line comments before independent logic blocks
- Use `# Section: Section Name` to separate code blocks
- Use `# FIXME:` for hardcoded values, architecture flaws, or known bugs
- Use `# TODO:` for skipped robustness or future features
- Written for open source contributors, explaining the **intent** and **design**.

## Testing Approach

Use `uv run pytest` to run tests.

### Unit Testing
- Match the exact structure and style of existing unit tests
- Follow the same naming conventions for test classes and methods
- Use the same assertion patterns found in existing tests (pytest-style)
- Apply the same mocking approach used in the codebase
- Follow existing patterns for test isolation
- Place unit tests in `tests/unit/` with subdirectories matching source structure

### Integration Testing
- Follow the same integration test patterns found in the codebase
- Match existing patterns for test data setup and teardown
- Use the same approach for testing component interactions
- Follow existing patterns for verifying system behavior
- Place integration tests in `tests/integration/`

### Test Configuration
- Use pytest with asyncio_mode="auto" (as configured in pyproject.toml)
- Use shared fixtures in `tests/conftest.py`
- Follow existing fixture patterns for web server, config, and test data

## Python-Specific Guidelines

### Python Version and Features
- Use Python 3.12+ features when appropriate (match statements, type parameter defaults, etc.)
- Follow `from __future__ import annotations` pattern in all modules to allow forward references
- Use type hints consistently for all function parameters and return values
- Use `|` union syntax (PEP 604) instead of `typing.Optional` for simple unions

### Data Structures
- Prefer `dataclass` or `TypedDict` for request/response envelopes
- Use `dataclass` with field() for complex models
- Use `enum.Enum` for constants and status values
- Use `__all__` to explicitly define public API exports

### Imports
- Organize imports in the following order: standard library, third-party, local imports
- Use `from __future__ import annotations` as the first import
- Use TYPE_CHECKING for type-only imports to avoid circular dependencies
- Group imports by category with blank lines between groups

### Asynchronous Programming
- Use `async/await` for all I/O operations
- Use `asyncio` for concurrent operations
- Follow existing patterns for WebSocket communication
- Use pytest-asyncio for async tests

### Error Handling
- Use custom `ValidationError` for validation failures
- Wrap exceptions with try-except to provide context
- Use `raise ... from exc` for exception chaining
- Log errors and warnings using get_logger factory

### Logging
- Use `get_logger(__name__)` to create module-specific loggers
- Use get_session_logger for session-specific logging
- Follow existing log level patterns (DEBUG, INFO, WARNING, ERROR)
- Configure logging via environment variables (CHOICE_LOG_LEVEL, CHOICE_LOG_FILE)

### Configuration
- Use environment variables for configuration (e.g., CHOICE_WEB_HOST, CHOICE_WEB_PORT)
- Use ConfigStore for persistent configuration
- Follow existing patterns for resolving configuration values
- Provide sensible defaults when environment variables are not set

## Architecture Guidelines

### Layered Architecture
The project follows a layered architecture with clear separation of concerns:

- **core/**: Core orchestration, models, validation, response logic
- **mcp/**: MCP tool bindings and response formatting
- **infra/**: Infrastructure (logging, i18n, storage, paths)
- **store/**: Session persistence and interaction history
- **terminal/**: Terminal UI (questionary-based)
- **web/**: Web server, bundling, templates

### Module Organization
- Keep modules small and single-purpose
- Avoid global state beyond configuration wiring
- Use clear module boundaries with well-defined interfaces
- Follow the Single Responsibility Principle (SRP)

### Schema-First Design
- Define data models in `src/core/models.py`
- Use validation in `src/core/validation.py` to parse requests
- Response generation in `src/core/response.py`
- Orchestrator in `src/core/orchestrator.py` coordinates all operations

### Transport Modes
- Terminal mode: Uses questionary for ANSI-based prompts
- Web mode: Uses FastAPI with WebSocket support
- Support terminal hand-off for non-blocking MCP invocations
- Respect user's persisted interface preference

## Code Style Guidelines

### Naming Conventions
- Use complete English words (no non-standard abbreviations)
- Constants: UPPER_CASE (e.g., DEFAULT_TIMEOUT_SECONDS, TRANSPORT_WEB)
- Classes: PascalCase (e.g., ChoiceOrchestrator, ProvideChoiceRequest)
- Functions and variables: snake_case (e.g., parse_request, get_logger)
- Private methods: _single_leading_underscore
- Module names: lowercase with underscores

### Type Hints
- Required for all function parameters and return values
- Use `|` for simple unions (e.g., `str | None`)
- Use `typing.List`, `typing.Dict`, etc. for complex types
- Use `TYPE_CHECKING` for type-only imports
- Use forward references when needed (enabled by `from __future__ import annotations`)

### Code Organization
- Use `# Section: Section Name` to separate code blocks
- Keep functions focused on single responsibilities
- Limit function length to match existing patterns
- Use docstrings for all modules, classes, and public functions

### Exception Handling
- Use custom ValidationError for validation failures
- Wrap exceptions with try-except to provide context
- Use `raise ... from exc` for exception chaining
- Log errors appropriately

## Internationalization

- Language settings from CHOICE_LANG or persisted config
- Supported languages: English (en), Chinese (zh)
- Use i18n texts from src/infra/i18n.py
- Follow existing patterns for adding new languages
- Extensible support for additional languages

## Web Server Guidelines

### FastAPI Patterns
- Use FastAPI for web server (>=0.127.0)
- Use WebSocket for real-time communication
- Use HTMLResponse and JSONResponse for responses
- Follow existing route patterns in src/web/server.py

### Asset Management
- Web assets are bundled from src/web/frontend/manifest.json
- Restart server after asset edits to refresh cached bundles
- Use bundler.py for asset assembly

### Port Management
- Resolve port from CHOICE_WEB_PORT environment variable or use default (9999)
- Find free port if requested port is occupied
- Use _resolve_host() and _resolve_port() for configuration

## Terminal UI Guidelines

### Questionary Integration
- Use questionary >=2.1.1 for ANSI-based terminal prompts
- Follow existing patterns in src/terminal/ui.py
- Support terminal hand-off with command execution

### Terminal Hand-Off
- Return pending_terminal_launch action status for terminal mode
- Agent must run the returned command to continue
- Emit markers for parsing: [SELECTION_COMPLETE], [CANCELLED], [SWITCH_TO_WEB]

## Session Management

### Session Persistence
- Use InteractionStore for session history
- Default retention: 3 days
- Default max sessions: 100 sessions
- Store sessions in .mcp-data/sessions/ (respects MCP_DATA_DIR env var)

### Session Lifecycle
- Create session with unique ID (UUID)
- Track session status (pending, selected, cancelled, etc.)
- Support timeout handling with configurable actions
- Poll for results in both web and terminal modes

## Testing Patterns

### Test Structure
```
tests/
├── conftest.py          # Shared fixtures and pytest configuration
├── unit/                # Unit tests (isolated, fast)
│   ├── core/           # Core models, validation, response
│   ├── infra/          # Infrastructure components
│   ├── store/          # Session persistence
│   ├── terminal/       # Terminal UI components
│   └── web/            # Web server components
└── integration/        # Integration tests (full system flow)
```

### Test Naming
- Use descriptive test names: `test_<what>_<when>_<expected>`
- Example: `test_parse_request_defaults`, `test_option_recommended_must_be_boolean`

### Fixtures
- Use pytest fixtures for shared test setup
- Place shared fixtures in tests/conftest.py
- Follow existing fixture patterns (web_server, config, etc.)

### Async Tests
- Use pytest-asyncio for async tests
- Configure asyncio_mode="auto" in pyproject.toml
- Follow existing async test patterns

## General Best Practices

- Follow naming conventions exactly as they appear in existing code
- Match code organization patterns from similar files
- Apply error handling consistent with existing patterns
- Follow the same approach to testing as seen in the codebase
- Match logging patterns from existing code
- Use the same approach to configuration as seen in the codebase
- Use complete English words for naming (no non-standard abbreviations)
- Add module-level docstrings explaining purpose and contents
- Use `__all__` to explicitly define public API exports
- Keep test code strictly separated from source files

## Project-Specific Guidance

- Scan the codebase thoroughly before generating any code
- Respect existing architectural boundaries without exception
- Match the style and patterns of surrounding code
- When in doubt, prioritize consistency with existing code over external best practices
- Follow the layered architecture: core → mcp/terminal/web → infra/store
- Use dataclasses for models with validation helpers
- Support both terminal and web transport modes
- Maintain session persistence with configurable retention
- Handle timeouts gracefully with configurable actions
- Support internationalization (i18n) with extensible language support