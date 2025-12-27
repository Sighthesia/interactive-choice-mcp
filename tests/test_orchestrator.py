import asyncio
import pytest
from choice.orchestrator import ChoiceOrchestrator, safe_handle
from choice import models

def test_orchestrator_prefers_terminal_when_available(monkeypatch, tmp_path):
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    monkeypatch.setattr("choice.orchestrator.is_terminal_available", lambda: True)

    async def fake_prompt(req, defaults, allow_web):
        return models.ProvideChoiceConfig(
            transport=models.TRANSPORT_TERMINAL,
            timeout_seconds=defaults.timeout_seconds,
            timeout_default_enabled=False,
            timeout_default_index=0,
        )

    monkeypatch.setattr("choice.orchestrator.prompt_terminal_configuration", fake_prompt)

    async def fake_run(req, timeout_seconds, config=None):
        return models.normalize_response(
            req=req,
            selected_indices=["A"],
            transport=models.TRANSPORT_TERMINAL,
        )

    monkeypatch.setattr("choice.orchestrator.run_terminal_choice", fake_run)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "A", "description": "desc", "recommended": True}],
        )
    )

    assert result.selection.transport == models.TRANSPORT_TERMINAL
    assert result.selection.selected_indices == ["A"]

def test_orchestrator_terminal_config_abort_falls_back_to_web(monkeypatch, tmp_path):
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    monkeypatch.setattr("choice.orchestrator.is_terminal_available", lambda: True)

    async def fake_prompt_abort(req, defaults, allow_web):
        return None

    monkeypatch.setattr("choice.orchestrator.prompt_terminal_configuration", fake_prompt_abort)

    async def fake_web(req, defaults, allow_terminal):
        return (
            models.normalize_response(
                req=req,
                selected_indices=["A"],
                transport=models.TRANSPORT_WEB,
            ),
            defaults,
        )

    monkeypatch.setattr("choice.orchestrator.run_web_choice", fake_web)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "A", "description": "desc", "recommended": True}],
        )
    )

    assert result.selection.transport == models.TRANSPORT_WEB
    assert result.selection.selected_indices == ["A"]

def test_orchestrator_falls_back_to_web(monkeypatch, tmp_path):
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")
    monkeypatch.setattr("choice.orchestrator.is_terminal_available", lambda: False)

    async def fake_web(req, defaults, allow_terminal):
        return (
            models.normalize_response(
                req=req,
                selected_indices=["B"],
                transport=models.TRANSPORT_WEB,
            ),
            defaults,
        )

    monkeypatch.setattr("choice.orchestrator.run_web_choice", fake_web)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "B", "description": "desc", "recommended": True}],
        )
    )

    assert result.selection.transport == models.TRANSPORT_WEB
    assert result.selection.selected_indices == ["B"]


def test_safe_handle_reports_validation_error(monkeypatch, tmp_path):
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")
    monkeypatch.setattr("choice.orchestrator.is_terminal_available", lambda: False)

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
