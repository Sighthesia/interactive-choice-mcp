"""Backward compatibility shim for src.response.

Moved to src.core.response. New code should import from src.core.
"""
from .core.response import *  # noqa: F401, F403
from .core.response import __all__  # noqa: F401
