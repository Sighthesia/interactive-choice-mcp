"""Backward compatibility shim for src.logging.

All logging utilities have moved to src.infra.logging. This module re-exports
them for backward compatibility. New code should import from src.infra.
"""
# Re-export everything from the new location
from .infra.logging import *  # noqa: F401, F403
from .infra.logging import __all__  # noqa: F401
