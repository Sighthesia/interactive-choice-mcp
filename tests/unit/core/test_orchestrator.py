import asyncio
import pytest
from src.core.orchestrator import ChoiceOrchestrator, safe_handle
from src.core import models
from src.core import response as r


# Section: Terminal Hand-off Tests
def test_orchestrator_terminal_handoff_returns_pending(monkeypatch, tmp_path):
    """When terminal interface is configured, orchestrator returns pending_terminal_launch."""
    # Pre-set config to terminal interface
    from src.infra.storage import ConfigStore
    store = ConfigStore(path=tmp_path / "cfg.json")
    store.save(models.ProvideChoiceConfig(
        interface=models.TRANSPORT_TERMINAL,
        timeout_seconds=300,
    ))

    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    async def fake_handoff(req, config):
        return r.pending_terminal_launch_response(
            session_id="test123",
            url="http://127.0.0.1:17863/terminal/test123",
            launch_command="uv run python -m src.terminal.client --session test123 --url http://127.0.0.1:17863",
        )

    monkeypatch.setattr("src.core.orchestrator.create_terminal_handoff_session", fake_handoff)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "A", "description": "desc", "recommended": True}],
        )
    )

    assert result.action_status == "pending_terminal_launch"
    assert "test123" in result.selection.url


def test_orchestrator_session_polling_returns_result(monkeypatch, tmp_path):
    """When session_id is provided and result is ready, returns the result."""
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    async def fake_poll(session_id, wait_seconds=30):
        return r.normalize_response(
            req=models.ProvideChoiceRequest(
                title="T", prompt="P", selection_mode="single",
                options=[models.ProvideChoiceOption(id="A", description="d", recommended=True)],
                timeout_seconds=300,
            ),
            selected_indices=["A"],
            interface=models.TRANSPORT_WEB,
        )

    monkeypatch.setattr("src.core.orchestrator.poll_terminal_session_result", fake_poll)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "A", "description": "desc", "recommended": True}],
            session_id="existing123",
        )
    )

    assert result.action_status == "selected"
    assert result.selection.selected_indices == ["A"]


def test_orchestrator_session_polling_pending(monkeypatch, tmp_path):
    """When session_id is provided but result is not ready (expired), returns cancelled status."""
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    async def fake_poll(session_id, wait_seconds=30):
        # Return None to simulate session not found or expired
        return None

    monkeypatch.setattr("src.core.orchestrator.poll_terminal_session_result", fake_poll)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "A", "description": "desc", "recommended": True}],
            session_id="pending123",
        )
    )

    # Now returns cancelled instead of pending when session not found
    assert result.action_status == "cancelled"
    assert "not found" in result.selection.summary.lower() or "expired" in result.selection.summary.lower()


# Section: Web Transport Tests
def test_orchestrator_falls_back_to_web(monkeypatch, tmp_path):
    """When web interface is configured, uses web portal."""
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")
    
    # Pre-set config to web interface
    from src.infra.storage import ConfigStore
    store = ConfigStore(path=tmp_path / "cfg.json")
    store.save(models.ProvideChoiceConfig(
        interface=models.TRANSPORT_WEB,
        timeout_seconds=300,
    ))
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    async def fake_web(req, defaults, allow_terminal):
        return (
            r.normalize_response(
                req=req,
                selected_indices=["B"],
                interface=models.TRANSPORT_WEB,
            ),
            defaults,
        )

    monkeypatch.setattr("src.core.orchestrator.run_web_choice", fake_web)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "B", "description": "desc", "recommended": True}],
        )
    )

    assert result.selection.interface == models.TRANSPORT_WEB
    assert result.selection.selected_indices == ["B"]


# Section: Error Handling Tests
def test_safe_handle_reports_validation_error(tmp_path):
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    result = asyncio.run(
        safe_handle(
            orch,
            title="Title",
            prompt="Prompt",
            selection_mode="invalid",
            options=[{"id": "A", "description": "desc", "recommended": True}],
        )
    )

    assert result.action_status == "cancelled"
    assert "validation_error" in result.selection.summary
