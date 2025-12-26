import os

import pytest

from choice import models


def test_parse_request_defaults():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "a", "label": "A", "description": "desc"}],
        allow_cancel=True,
    )
    assert req.timeout_seconds == models.DEFAULT_TIMEOUT_SECONDS
    assert req.transport is None


def test_parse_request_env_timeout(monkeypatch):
    monkeypatch.setenv("CHOICE_TIMEOUT_SECONDS", "120")
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="text_input",
        options=[{"id": "a", "label": "A", "description": "desc"}],
        allow_cancel=False,
    )
    assert req.timeout_seconds == 120


def test_parse_request_invalid_type():
    with pytest.raises(models.ValidationError):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="bad",
            options=[{"id": "a", "label": "A", "description": "desc"}],
            allow_cancel=True,
        )


def test_normalize_response_custom_input():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="text_input",
        options=[{"id": "a", "label": "A", "description": "desc"}],
        allow_cancel=True,
    )
    resp = models.normalize_response(req=req, selected_ids=[], custom_input="hi", transport=models.TRANSPORT_WEB, url="http://localhost")
    assert resp.action_status == "custom_input"
    assert resp.selection.custom_input == "hi"
    assert resp.selection.transport == models.TRANSPORT_WEB


def test_timeout_response_helper():
    resp = models.timeout_response(transport=models.TRANSPORT_TERMINAL)
    assert resp.action_status == "timeout"
    assert resp.selection.transport == models.TRANSPORT_TERMINAL


def test_apply_configuration_filters_and_timeout():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[
            {"id": "a", "label": "A", "description": "desc"},
            {"id": "b", "label": "B", "description": "desc"},
        ],
        allow_cancel=True,
    )
    config = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_WEB,
        visible_option_ids=["b"],
        timeout_seconds=42,
        allow_cancel=True,
        placeholder=None,
    )
    adjusted = models.apply_configuration(req, config)
    assert [opt.id for opt in adjusted.options] == ["b"]
    assert adjusted.timeout_seconds == 42
    assert adjusted.transport == models.TRANSPORT_WEB


def test_apply_configuration_empty_visibility_falls_back():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[
            {"id": "a", "label": "A", "description": "desc"},
            {"id": "b", "label": "B", "description": "desc"},
        ],
        allow_cancel=True,
    )
    config = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_TERMINAL,
        visible_option_ids=[],
        timeout_seconds=10,
        allow_cancel=True,
        placeholder=None,
    )
    adjusted = models.apply_configuration(req, config)
    assert [opt.id for opt in adjusted.options] == ["a", "b"]
