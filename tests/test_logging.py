"""Tests for the logging module."""
import logging
import os
import tempfile
from pathlib import Path

import pytest

from choice.logging import (
    LOG_LEVEL_ENV,
    LOG_FILE_ENV,
    configure_logging,
    get_logger,
    get_session_logger,
)


def test_get_logger_returns_logger():
    """Test that get_logger returns a valid logger instance."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert "choice" in logger.name


def test_get_session_logger_prefixes_messages():
    """Test that session logger includes session ID prefix."""
    session_id = "abc123def456ghi789"
    logger = get_session_logger("test_module", session_id)
    # Check that the adapter was created with the correct session ID
    assert logger._session_id == session_id


def test_configure_logging_respects_env_level(monkeypatch):
    """Test that log level can be configured via environment variable."""
    monkeypatch.setenv(LOG_LEVEL_ENV, "DEBUG")
    configure_logging(force=True)
    
    logger = get_logger("test_level")
    # The root logger should be set to DEBUG
    root = logging.getLogger("choice")
    assert root.level == logging.DEBUG


def test_configure_logging_with_file(monkeypatch, tmp_path):
    """Test that file logging can be enabled via environment variable."""
    log_file = tmp_path / "test.log"
    monkeypatch.setenv(LOG_FILE_ENV, str(log_file))
    configure_logging(force=True)
    
    logger = get_logger("test_file")
    logger.info("Test message")
    
    # Force flush handlers
    for handler in logging.getLogger("choice").handlers:
        handler.flush()
    
    # Check that the file was created and contains the message
    assert log_file.exists()
    content = log_file.read_text()
    assert "Test message" in content
