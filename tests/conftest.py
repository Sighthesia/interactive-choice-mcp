"""Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests.
The test directory is organized as follows:

    tests/
    ├── conftest.py          # Shared fixtures and configuration
    ├── unit/                 # Unit tests (isolated, fast)
    │   ├── core/            # Core models, validation, response
    │   ├── infra/           # Infrastructure (i18n, logging, storage)
    │   ├── store/           # Session persistence
    │   ├── terminal/        # Terminal client
    │   └── web/             # Web server components
    └── integration/         # Integration tests (full flow)
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so tests can import local packages
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
import asyncio
from src.web.server import WebChoiceServer
from src.core.models import (
    ProvideChoiceRequest,
    ProvideChoiceOption,
    ProvideChoiceConfig,
)


@pytest.fixture
async def web_server():
    """Start a test web server and clean up after the test.
    
    This fixture creates a WebChoiceServer instance, ensures it's running,
    and provides it to tests. After the test completes, it cleans up
    all sessions and shuts down the server.
    
    Yields:
        WebChoiceServer: The running web server instance.
    """
    server = WebChoiceServer()
    await server.ensure_running()
    
    yield server
    
    # Cleanup: remove all sessions and stop the server
    for session_id in list(server.sessions.keys()):
        await server._remove_session(session_id)
    
    # Cancel cleanup task
    if server._cleanup_task and not server._cleanup_task.done():
        server._cleanup_task.cancel()
        try:
            await server._cleanup_task
        except asyncio.CancelledError:
            pass


@pytest.fixture
def sample_single_choice_request():
    """Provide a standard single-choice test request.
    
    Returns:
        ProvideChoiceRequest: A request with two options, first one recommended.
    """
    return ProvideChoiceRequest(
        title="Test Single Choice",
        prompt="Please select one option",
        selection_mode="single",
        options=[
            ProvideChoiceOption(
                id="opt1",
                description="Option 1",
                recommended=True,
            ),
            ProvideChoiceOption(
                id="opt2",
                description="Option 2",
                recommended=False,
            ),
        ],
        timeout_seconds=300,
    )


@pytest.fixture
def sample_multi_choice_request():
    """Provide a standard multi-choice test request.
    
    Returns:
        ProvideChoiceRequest: A request with three options, two recommended.
    """
    return ProvideChoiceRequest(
        title="Test Multi Choice",
        prompt="Please select multiple options",
        selection_mode="multi",
        options=[
            ProvideChoiceOption(
                id="opt1",
                description="Option 1",
                recommended=True,
            ),
            ProvideChoiceOption(
                id="opt2",
                description="Option 2",
                recommended=True,
            ),
            ProvideChoiceOption(
                id="opt3",
                description="Option 3",
                recommended=False,
            ),
        ],
        timeout_seconds=300,
    )


@pytest.fixture
def sample_web_config():
    """Provide a standard web configuration for tests.
    
    Returns:
        ProvideChoiceConfig: A config with web interface and default timeout.
    """
    return ProvideChoiceConfig(
        interface="web",
        timeout_seconds=300,
    )
