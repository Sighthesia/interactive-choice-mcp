"""Sanity tests to ensure modules import cleanly with proper __all__ exports."""
from __future__ import annotations


def test_core_validation_module_importable():
    import src.core.validation as v

    assert hasattr(v, "__all__")


def test_core_response_module_importable():
    import src.core.response as r

    assert hasattr(r, "__all__")


def test_core_models_module_importable():
    import src.core.models as m

    assert hasattr(m, "__all__")


def test_core_orchestrator_module_importable():
    import src.core.orchestrator as o

    assert hasattr(o, "__all__")


def test_infra_logging_module_importable():
    import src.infra.logging as l

    assert hasattr(l, "__all__")


def test_infra_storage_module_importable():
    import src.infra.storage as s

    assert hasattr(s, "__all__")


def test_infra_i18n_module_importable():
    import src.infra.i18n as i

    assert hasattr(i, "__all__")


def test_store_interaction_store_module_importable():
    import src.store.interaction_store as store

    assert hasattr(store, "__all__")


def test_terminal_package_importable():
    import src.terminal as t

    assert hasattr(t, "__all__")


def test_web_package_importable():
    import src.web as w

    assert hasattr(w, "__all__")
