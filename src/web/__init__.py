"""Web package entrypoint exposing the web interaction flow."""

from .server import (
    run_web_choice,
    WebChoiceServer,
    create_terminal_handoff_session,
    poll_terminal_session_result,
)
from .session import ChoiceSession, _deadline_from_seconds, _remaining_seconds

__all__ = [
    "run_web_choice",
    "WebChoiceServer",
    "create_terminal_handoff_session",
    "poll_terminal_session_result",
    "ChoiceSession",
    "_deadline_from_seconds",
    "_remaining_seconds",
]
