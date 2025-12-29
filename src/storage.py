"""Backward compatibility shim for src.storage.

Moved to src.infra.storage. New code should import from src.infra.
"""
from .infra.storage import *  # noqa: F401, F403
from .infra.storage import __all__  # noqa: F401
