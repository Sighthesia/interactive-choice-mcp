"""Backward compatibility shim for src.models.

All models have moved to src.core.models. This module re-exports
them for backward compatibility. New code should import from src.core.
"""
# Re-export everything from the new location
from .core.models import *  # noqa: F401, F403
from .core.models import __all__  # noqa: F401
