"""Centralized logging configuration for the interactive-choice-mcp server.

This module provides a unified logging infrastructure with:
- Configurable log levels via environment variables
- Optional file output with rotation
- Structured log format with timestamps and session context
- Consistent logging across all modules
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

__all__ = [
    "get_logger",
    "configure_logging",
    "LOG_LEVEL_ENV",
    "LOG_FILE_ENV",
    "LOG_FORMAT_ENV",
    "LANG_ENV",
    "get_language_from_env",
]

# Section: Environment Variable Names
LOG_LEVEL_ENV = "CHOICE_LOG_LEVEL"
LOG_FILE_ENV = "CHOICE_LOG_FILE"
LOG_FORMAT_ENV = "CHOICE_LOG_FORMAT"
LANG_ENV = "CHOICE_LANG"

# Section: Default Configuration
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_LOG_FILE_BACKUP_COUNT = 5

# Section: Logger Registry
_configured = False
_root_logger_name = "choice"


def _get_log_level() -> int:
    """Resolve log level from environment variable."""
    level_str = os.environ.get(LOG_LEVEL_ENV, _DEFAULT_LOG_LEVEL).upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str, logging.INFO)


def _get_log_file() -> Optional[Path]:
    """Resolve log file path from environment variable."""
    path_str = os.environ.get(LOG_FILE_ENV)
    if not path_str:
        return None
    return Path(path_str).expanduser().resolve()


def _get_log_format() -> str:
    """Resolve log format from environment variable."""
    return os.environ.get(LOG_FORMAT_ENV, _DEFAULT_LOG_FORMAT)


def configure_logging(*, force: bool = False) -> None:
    """Configure the logging system for the application.

    This function sets up handlers and formatters for the root 'choice' logger.
    It should be called once at application startup.

    Args:
        force: If True, reconfigure even if already configured.

    Environment Variables:
        CHOICE_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                          Default: INFO
        CHOICE_LOG_FILE: Path to log file. If not set, file logging is disabled.
        CHOICE_LOG_FORMAT: Custom log format string. Uses Python logging format.
    """
    global _configured

    if _configured and not force:
        return

    log_level = _get_log_level()
    log_file = _get_log_file()
    log_format = _get_log_format()

    # Get the root logger for our application
    root_logger = logging.getLogger(_root_logger_name)
    root_logger.setLevel(log_level)

    # Clear existing handlers on reconfiguration
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=_DEFAULT_DATE_FORMAT)

    # Console handler (always enabled, outputs to stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if log file is specified)
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=_LOG_FILE_MAX_BYTES,
                backupCount=_LOG_FILE_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Failed to configure file logging to {log_file}: {e}")

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified module.

    Args:
        name: Module name, typically __name__. Will be prefixed with 'choice.'
              if not already.

    Returns:
        A configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Server started")
    """
    # Ensure logging is configured
    configure_logging()

    # Normalize the logger name
    if name.startswith(_root_logger_name + "."):
        full_name = name
    elif name == _root_logger_name:
        full_name = name
    else:
        # Extract the last component for cleaner names
        short_name = name.split(".")[-1] if "." in name else name
        full_name = f"{_root_logger_name}.{short_name}"

    return logging.getLogger(full_name)


# Section: Convenience Functions for Structured Logging
class SessionLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes session context."""

    def __init__(self, logger: logging.Logger, session_id: str) -> None:
        super().__init__(logger, {"session_id": session_id})
        self._session_id = session_id

    def process(self, msg: object, kwargs: dict) -> tuple[str, dict]:  # type: ignore[override]
        return f"[{self._session_id[:8]}] {msg}", kwargs


def get_session_logger(name: str, session_id: str) -> SessionLoggerAdapter:
    """Get a logger that includes session ID in all messages.

    Args:
        name: Module name for the logger.
        session_id: Session identifier to include in log messages.

    Returns:
        A logger adapter that prefixes messages with the session ID.

    Example:
        >>> logger = get_session_logger(__name__, "abc123def456")
        >>> logger.info("User submitted selection")
        # Output: 2024-01-01 12:00:00 | INFO     | choice.server       | [abc123de] User submitted selection
    """
    base_logger = get_logger(name)
    return SessionLoggerAdapter(base_logger, session_id)


# Section: Language Environment Helper
def get_language_from_env() -> str | None:
    """Read language preference from CHOICE_LANG environment variable.

    Returns:
        'en' or 'zh' if valid, None if not set or invalid (logs warning).
    """
    from .models import LANG_EN, VALID_LANGUAGES

    lang_env = os.environ.get(LANG_ENV)
    if lang_env is None:
        return None
    lang_env = lang_env.strip().lower()
    if lang_env in VALID_LANGUAGES:
        return lang_env
    # Invalid value: log warning and return None (caller should fallback)
    logger = get_logger(__name__)
    logger.warning(f"Invalid CHOICE_LANG value '{lang_env}', falling back to English")
    return None
