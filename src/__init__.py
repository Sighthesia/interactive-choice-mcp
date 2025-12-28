"""Interactive Choice MCP Server - Core package.

This package provides the core functionality for the interactive-choice-mcp server.

Logging Configuration:
    Set the following environment variables to configure logging:
    - CHOICE_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR). Default: INFO
    - CHOICE_LOG_FILE: Path to log file. If not set, logs go to stderr only.
    - CHOICE_LOG_FORMAT: Custom log format string.

Example:
    export CHOICE_LOG_LEVEL=DEBUG
    export CHOICE_LOG_FILE=~/.local/share/interactive-choice-mcp/server.log
"""
from .logging import configure_logging, get_logger

# Initialize logging when the package is imported
configure_logging()

__all__ = [
    "configure_logging",
    "get_logger",
]