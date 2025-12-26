import os

import pytest

from choice import models


def test_parse_request_defaults():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "a", "label": "A", "description": "desc"}],
    )
    assert req.timeout_seconds == models.DEFAULT_TIMEOUT_SECONDS
    assert req.transport is None
    assert req.min_selections == 0
    assert req.max_selections is None
    assert req.single_submit_mode is True
    assert req.placeholder_enabled is True
    assert req.default_selection_ids == []


def test_parse_request_env_timeout(monkeypatch):
    monkeypatch.setenv("CHOICE_TIMEOUT_SECONDS", "120")
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="text_input",
        options=[{"id": "a", "label": "A", "description": "desc"}],
    )
    assert req.timeout_seconds == 120


def test_parse_request_invalid_type():
    with pytest.raises(models.ValidationError):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="bad",
            options=[{"id": "a", "label": "A", "description": "desc"}],
        )


def test_parse_request_extended_fields():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="multi_select",
        options=[
            {"id": "a", "label": "A", "description": "desc"},
            {"id": "b", "label": "B", "description": "desc"},
        ],
        default_selection_ids=["a"],
        min_selections=1,
        max_selections=2,
        single_submit_mode=False,
        placeholder_enabled=False,
    )
    assert req.default_selection_ids == ["a"]
    assert req.min_selections == 1
    assert req.max_selections == 2
    assert req.single_submit_mode is False
    assert req.placeholder_enabled is False


def test_parse_request_invalid_min_max():
    with pytest.raises(models.ValidationError, match="min_selections must not exceed max_selections"):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="multi_select",
            options=[{"id": "a", "label": "A", "description": "desc"}],
            min_selections=5,
            max_selections=2,
        )


def test_parse_request_invalid_default_selection():
    with pytest.raises(models.ValidationError, match="invalid option"):
        models.parse_request(
            title="Title",
            prompt="Prompt",
            type="single_select",
            options=[{"id": "a", "label": "A", "description": "desc"}],
            default_selection_ids=["nonexistent"],
        )


def test_normalize_response_custom_input():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="text_input",
        options=[{"id": "a", "label": "A", "description": "desc"}],
    )
    resp = models.normalize_response(req=req, selected_ids=[], custom_input="hi", transport=models.TRANSPORT_WEB, url="http://localhost")
    assert resp.action_status == "custom_input"
    assert resp.selection.custom_input == "hi"
    assert resp.selection.transport == models.TRANSPORT_WEB


def test_normalize_response_with_annotations():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="single_select",
        options=[{"id": "a", "label": "A", "description": "desc"}],
    )
    resp = models.normalize_response(
        req=req,
        selected_ids=["a"],
        custom_input=None,
        transport=models.TRANSPORT_TERMINAL,
        option_annotations={"a": "my note"},
        global_annotation="global note",
    )
    assert resp.selection.option_annotations == {"a": "my note"}
    assert resp.selection.global_annotation == "global note"


def test_normalize_response_min_max_enforcement():
    req = models.parse_request(
        title="Title",
        prompt="Prompt",
        type="multi_select",
        options=[
            {"id": "a", "label": "A", "description": "desc"},
            {"id": "b", "label": "B", "description": "desc"},
        ],
        min_selections=1,
        max_selections=1,
    )
    # Too few selections
    with pytest.raises(models.ValidationError, match="below minimum"):
        models.normalize_response(req=req, selected_ids=[], custom_input=None, transport=models.TRANSPORT_TERMINAL)

    # Too many selections
    with pytest.raises(models.ValidationError, match="exceeds maximum"):
        models.normalize_response(req=req, selected_ids=["a", "b"], custom_input=None, transport=models.TRANSPORT_TERMINAL)

    # Valid selection
    resp = models.normalize_response(req=req, selected_ids=["a"], custom_input=None, transport=models.TRANSPORT_TERMINAL)
    assert resp.action_status == "selected"


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
    )
    config = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_WEB,
        visible_option_ids=["b"],
        timeout_seconds=42,
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
    )
    config = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_TERMINAL,
        visible_option_ids=[],
        timeout_seconds=10,
        placeholder=None,
    )
    adjusted = models.apply_configuration(req, config)
    assert [opt.id for opt in adjusted.options] == ["a", "b"]
