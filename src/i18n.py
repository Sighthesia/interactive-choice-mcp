"""Backward compatibility shim for src.i18n.

Moved to src.infra.i18n. New code should import from src.infra.
"""
from .infra.i18n import *  # noqa: F401, F403
from .infra.i18n import __all__  # noqa: F401
