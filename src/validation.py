"""Backward compatibility shim for src.validation.

Moved to src.core.validation. New code should import from src.core.
"""
from .core.validation import *  # noqa: F401, F403
from .core.validation import __all__  # noqa: F401
