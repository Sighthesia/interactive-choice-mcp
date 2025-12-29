"""Backward compatibility shim for src.interaction_store.

Moved to src.store.interaction_store. New code should import from src.store.
"""
from .store.interaction_store import *  # noqa: F401, F403
from .store.interaction_store import __all__  # noqa: F401
