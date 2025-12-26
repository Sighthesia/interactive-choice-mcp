import asyncio

from choice.orchestrator import ChoiceOrchestrator
from choice import models


def test_orchestrator_prefers_terminal_when_available(monkeypatch, tmp_path):
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")

    monkeypatch.setattr("choice.orchestrator.is_terminal_available", lambda: True)

    async def fake_prompt(req, defaults, allow_web):
        return models.ProvideChoiceConfig(
            transport=models.TRANSPORT_TERMINAL,
            visible_option_ids=["a"],
            timeout_seconds=defaults.timeout_seconds,
        )

    monkeypatch.setattr("choice.orchestrator.prompt_terminal_configuration", fake_prompt)

    async def fake_run(req, timeout_seconds):
        return models.normalize_response(
            req=req,
            selected_ids=["a"],
            custom_input=None,
            transport=models.TRANSPORT_TERMINAL,
        )

    monkeypatch.setattr("choice.orchestrator.run_terminal_choice", fake_run)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            type="single_select",
            options=[{"id": "a", "label": "A", "description": "desc"}],
            allow_cancel=True,
        )
    )

    assert result.selection.transport == models.TRANSPORT_TERMINAL
    assert result.selection.selected_ids == ["a"]


def test_orchestrator_falls_back_to_web(monkeypatch, tmp_path):
    orch = ChoiceOrchestrator(config_path=tmp_path / "cfg.json")
    monkeypatch.setattr("choice.orchestrator.is_terminal_available", lambda: False)

    async def fake_web(req, defaults, allow_terminal):
        return (
            models.normalize_response(
                req=req,
                selected_ids=["b"],
                custom_input=None,
                transport=models.TRANSPORT_WEB,
            ),
            defaults,
        )

    monkeypatch.setattr("choice.orchestrator.run_web_choice", fake_web)

    result = asyncio.run(
        orch.handle(
            title="Title",
            prompt="Prompt",
            type="single_select",
            options=[{"id": "b", "label": "B", "description": "desc"}],
            allow_cancel=False,
        )
    )

    assert result.selection.transport == models.TRANSPORT_WEB
    assert result.selection.selected_ids == ["b"]
