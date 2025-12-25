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
