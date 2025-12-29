import os

import pytest

from src.core import models
from src.core import validation as v
from src.core import response as r


def test_parse_request_defaults():
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="single",
        options=[{"id": "A", "description": "desc", "recommended": True}],
    )
    assert req.timeout_seconds == models.DEFAULT_TIMEOUT_SECONDS
    assert req.transport is None
    assert req.single_submit_mode is True


def test_parse_request_env_timeout(monkeypatch):
    monkeypatch.setenv("CHOICE_TIMEOUT_SECONDS", "120")
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="single",
        options=[{"id": "A", "description": "desc", "recommended": True}],
    )
    assert req.timeout_seconds == 120


def test_parse_request_invalid_type():
    with pytest.raises(models.ValidationError):
        v.parse_request(
            title="Title",
            prompt="Prompt",
            selection_mode="bad",
            options=[{"id": "A", "description": "desc", "recommended": True}],
        )


def test_option_recommended_must_be_boolean():
    with pytest.raises(models.ValidationError):
        v.parse_request(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "A", "description": "desc", "recommended": "yes"}],
        )


def test_options_require_recommended_present():
    with pytest.raises(models.ValidationError):
        v.parse_request(
            title="Title",
            prompt="Prompt",
            selection_mode="multi",
            options=[{"id": "A", "description": "desc"}],
        )


def test_selection_mode_alias_rejected():
    with pytest.raises(models.ValidationError):
        v.parse_request(
            title="Title",
            prompt="Prompt",
            selection_mode="single_select",
            options=[{"id": "A", "description": "desc", "recommended": True}],
        )


def test_single_select_multiple_recommended_rejected():
    with pytest.raises(models.ValidationError):
        v.parse_request(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[
                {"id": "A", "description": "desc", "recommended": True},
                {"id": "B", "description": "desc", "recommended": True},
            ],
        )


def test_parse_request_extended_fields():
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="multi",
        options=[
            {"id": "A", "description": "desc", "recommended": True},
            {"id": "B", "description": "desc"},
        ],
        single_submit_mode=False,
    )
    assert req.single_submit_mode is False


def test_normalize_response_selection():
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="single",
        options=[{"id": "A", "description": "desc", "recommended": True}],
    )
    resp = r.normalize_response(
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
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="single",
        options=[{"id": "A", "description": "desc", "recommended": True}],
    )
    with pytest.raises(models.ValidationError):
        r.normalize_response(
            req=req,
            selected_indices=["A"],
            transport=models.TRANSPORT_TERMINAL,
            action_status="bad_status",
        )


def test_timeout_response_auto_select():
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="single",
        options=[
            {"id": "A", "description": "desc", "recommended": True},
            {"id": "B", "description": "desc"},
        ],
        timeout_default_enabled=True,
        timeout_default_index=1,
    )
    resp = r.timeout_response(req=req, transport=models.TRANSPORT_TERMINAL)
    assert resp.action_status == "timeout_auto_submitted"
    assert resp.selection.selected_indices == ["B"]


def test_timeout_response_cancelled_when_no_default():
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="single",
        options=[{"id": "A", "description": "desc", "recommended": True}],
        timeout_default_enabled=False,
    )
    resp = r.timeout_response(req=req, transport=models.TRANSPORT_TERMINAL)
    assert resp.action_status == "timeout_cancelled"
    assert resp.selection.selected_indices == []


def test_timeout_default_index_out_of_range():
    with pytest.raises(models.ValidationError):
        v.parse_request(
            title="Title",
            prompt="Prompt",
            selection_mode="multi",
            options=[{"id": "A", "description": "desc", "recommended": True}],
            timeout_default_index=2,
        )


def test_apply_configuration():
    req = v.parse_request(
        title="Title",
        prompt="Prompt",
        selection_mode="single",
        options=[
            {"id": "A", "description": "desc", "recommended": True},
            {"id": "B", "description": "desc"},
        ],
    )
    config = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_WEB,
        timeout_seconds=42,
    )
    adjusted = v.apply_configuration(req, config)
    assert adjusted.timeout_seconds == 42
    assert adjusted.transport == models.TRANSPORT_WEB
    assert [opt.id for opt in adjusted.options] == ["A", "B"]
