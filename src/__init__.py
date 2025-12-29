"""Interactive Choice MCP Server - Core package.

This package provides the core functionality for the interactive-choice-mcp server.

Package Structure:
    src/
    ├── core/          - Core business logic (models, orchestrator, validation, response)
    ├── infra/         - Infrastructure (logging, storage, i18n)
    ├── store/         - Session persistence
    ├── terminal/      - Terminal transport implementation
    └── web/           - Web transport implementation

Logging Configuration:
    Set the following environment variables to configure logging:
    - CHOICE_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR). Default: INFO
        - CHOICE_LOG_FILE: Path to log file. Default: .mcp-data/server.log in the
            current working directory. Set this to override the default.
    - CHOICE_LOG_FORMAT: Custom log format string.

Example:
    export CHOICE_LOG_LEVEL=DEBUG
    # To override default (.mcp-data/server.log), set CHOICE_LOG_FILE explicitly
    export CHOICE_LOG_FILE=~/.local/share/interactive-choice-mcp/server.log
"""
# Re-export from subpackages for convenience and backward compatibility
from .infra import configure_logging, get_logger

# Initialize logging when the package is imported
configure_logging()

__all__ = [
    "configure_logging",
    "get_logger",
]