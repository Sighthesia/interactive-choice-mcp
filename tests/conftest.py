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

from dataclasses import replace
import asyncio
import webbrowser

import pytest
from src.web.server import WebChoiceServer
from src.core.models import (
    ProvideChoiceRequest,
    ProvideChoiceOption,
    ProvideChoiceConfig,
    TRANSPORT_TERMINAL,
    TRANSPORT_WEB,
    NotificationTriggerMode,
)
from src.infra import ConfigStore


def pytest_addoption(parser):
    """Register CLI options to toggle interactive testing."""
    parser.addoption(
        "--interactive",
        action="store_true",
        default=False,
        help="Enable manual interactive tests (off by default).",
    )
    parser.addoption(
        "--selection-mode",
        action="store",
        default="single",
        choices=["single", "multi"],
        help="Selection mode for interactive tests: single or multi (default: single).",
    )


def _build_default_config(interface: str) -> ProvideChoiceConfig:
    """Construct a config payload matching config.json defaults."""
    return ProvideChoiceConfig(
        interface=interface,
        timeout_seconds=600,
        single_submit_mode=True,
        use_default_option=False,
        timeout_action="submit",
        language="zh",
        notify_new=True,
        notify_upcoming=True,
        upcoming_threshold=60,
        notify_timeout=True,
        notify_trigger_mode=NotificationTriggerMode.default(),
    )


@pytest.fixture
def interactive(request) -> bool:
    """Flag to enable manual interactive tests."""
    return bool(request.config.getoption("--interactive"))


@pytest.fixture
def selection_mode(request) -> str:
    """Selection mode for interactive tests: single or multi."""
    return str(request.config.getoption("selection_mode"))


@pytest.fixture
def persisted_config() -> ProvideChoiceConfig:
    """Load config.json (creates one if missing) for shared test settings."""
    store = ConfigStore()
    config = store.load()
    if config is None:
        config = _build_default_config(TRANSPORT_WEB)
        store.save(config)
    return config


@pytest.fixture
def sample_web_config(persisted_config: ProvideChoiceConfig) -> ProvideChoiceConfig:
    """Provide web config derived from persisted config.json data."""
    return replace(persisted_config, interface=TRANSPORT_WEB)


@pytest.fixture
def sample_terminal_config(persisted_config: ProvideChoiceConfig) -> ProvideChoiceConfig:
    """Provide terminal config derived from persisted config.json data."""
    return replace(persisted_config, interface=TRANSPORT_TERMINAL)


@pytest.fixture
async def web_server(interactive: bool, monkeypatch):
    """Start a test web server and clean up after the test.
    
    Ensures global server helpers reuse this instance. Browser opening
    is suppressed for automated test runs but allowed in interactive mode.
    """
    from src.web import server as server_module

    # Only suppress browser opening for automated tests
    if not interactive:
        monkeypatch.setattr(webbrowser, "open", lambda url: False)

    server = WebChoiceServer()
    server_module._WEB_SERVER = server
    await server.ensure_running()
    
    yield server
    
    for session_id in list(server.sessions.keys()):
        await server._remove_session(session_id)
    
    await server.shutdown()
    server_module._WEB_SERVER = None


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
def sample_request(selection_mode: str, sample_single_choice_request, sample_multi_choice_request):
    """Provide a test request based on selection_mode parameter.
    
    Args:
        selection_mode: Either "single" or "multi"
        sample_single_choice_request: Single choice request fixture
        sample_multi_choice_request: Multi choice request fixture
    
    Returns:
        ProvideChoiceRequest: Single or multi choice request based on selection_mode.
    """
    if selection_mode == "multi":
        return sample_multi_choice_request
    return sample_single_choice_request
