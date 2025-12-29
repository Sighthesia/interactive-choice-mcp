"""Infrastructure components for interactive choice.

This package provides foundational services that support the core business logic:
logging, configuration persistence, and internationalization.

Modules:
    logging: Structured logging with session context support
    storage: JSON-based configuration persistence
    i18n: Internationalization text resources (en/zh)

Example:
    from src.infra import get_logger, ConfigStore, get_text

    logger = get_logger(__name__)
    config = ConfigStore().load()
    label = get_text("action.submit", "en")
"""
from .logging import (
    configure_logging,
    get_logger,
    get_session_logger,
    get_language_from_env,
)

from .storage import ConfigStore

from .i18n import (
    get_text,
    TEXTS,
)

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    "get_session_logger",
    "get_language_from_env",
    # Storage
    "ConfigStore",
    # I18n
    "get_text",
    "TEXTS",
]
