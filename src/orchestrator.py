"""Backward compatibility shim for src.orchestrator.

Moved to src.core.orchestrator. New code should import from src.core.
"""
from .core.orchestrator import *  # noqa: F401, F403
from .core.orchestrator import __all__  # noqa: F401

# Re-export web functions that the orchestrator module previously exposed
from .web import (  # noqa: F401
    create_terminal_handoff_session,
    poll_terminal_session_result,
)
