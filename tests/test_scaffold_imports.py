"""Sanity tests to ensure newly added scaffold modules import cleanly."""
from __future__ import annotations

def test_validation_module_importable():
    import choice.validation as v

    assert hasattr(v, "__all__")


def test_response_module_importable():
    import choice.response as r

    assert hasattr(r, "__all__")


def test_terminal_package_importable():
    import choice.terminal as t

    assert hasattr(t, "__all__")


def test_web_package_importable():
    import choice.web as w

    assert hasattr(w, "__all__")
