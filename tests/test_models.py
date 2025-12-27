import os

import pytest

from choice import models


def test_parse_request_defaults():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "A", "description": "desc"}],
    )
    assert req.timeout_seconds == models.DEFAULT_TIMEOUT_SECONDS
    assert req.transport is None
    assert req.single_submit_mode is True


def test_parse_request_env_timeout(monkeypatch):
    monkeypatch.setenv("CHOICE_TIMEOUT_SECONDS", "120")
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "A", "description": "desc"}],
    )
    assert req.timeout_seconds == 120


def test_parse_request_invalid_type():
    with pytest.raises(models.ValidationError):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="bad",
            options=[{"id": "A", "description": "desc"}],
        )


def test_option_default_must_be_boolean():
    with pytest.raises(models.ValidationError):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="single_select",
            options=[{"id": "A", "description": "desc", "default": "yes"}],
        )


def test_single_select_multiple_defaults_rejected():
    with pytest.raises(models.ValidationError):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="single_select",
            options=[
                {"id": "A", "description": "desc", "default": True},
                {"id": "B", "description": "desc", "default": True},
            ],
        )


def test_parse_request_extended_fields():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="multi_select",
        options=[
            {"id": "A", "description": "desc"},
            {"id": "B", "description": "desc"},
        ],
        single_submit_mode=False,
    )
    assert req.single_submit_mode is False


def test_normalize_response_selection():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "A", "description": "desc"}],
    )
    resp = models.normalize_response(
        req=req,
        selected_indices=["A"],
        transport=models.TRANSPORT_WEB,
        url="http://localhost",
        global_annotation="some note",
    )
    assert resp.action_status == "selected"
    assert resp.selection.selected_indices == ["A"]
    assert resp.selection.transport == models.TRANSPORT_WEB
    assert resp.selection.global_annotation == "some note"


def test_normalize_response_rejects_invalid_action_status():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "A", "description": "desc"}],
    )
    with pytest.raises(models.ValidationError):
        models.normalize_response(
            req=req,
            selected_indices=["A"],
            transport=models.TRANSPORT_TERMINAL,
            action_status="bad_status",
        )


def test_timeout_response_auto_select():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "A", "description": "desc"}, {"id": "B", "description": "desc"}],
        timeout_default_enabled=True,
        timeout_default_index=1,
    )
    resp = models.timeout_response(req=req, transport=models.TRANSPORT_TERMINAL)
    assert resp.action_status == "timeout_auto_submitted"
    assert resp.selection.selected_indices == ["B"]


def test_timeout_response_cancelled_when_no_default():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "A", "description": "desc"}],
        timeout_default_enabled=False,
    )
    resp = models.timeout_response(req=req, transport=models.TRANSPORT_TERMINAL)
    assert resp.action_status == "timeout_cancelled"
    assert resp.selection.selected_indices == []


def test_timeout_default_index_out_of_range():
    with pytest.raises(models.ValidationError):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="multi_select",
            options=[{"id": "A", "description": "desc"}],
            timeout_default_index=2,
        )


def test_apply_configuration():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[
            {"id": "A", "description": "desc"},
            {"id": "B", "description": "desc"},
        ],
    )
    config = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_WEB,
        timeout_seconds=42,
    )
    adjusted = models.apply_configuration(req, config)
    assert adjusted.timeout_seconds == 42
    assert adjusted.transport == models.TRANSPORT_WEB
