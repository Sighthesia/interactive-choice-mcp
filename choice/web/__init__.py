"""Web package entrypoint exposing the web interaction flow."""

from .server import run_web_choice, WebChoiceServer
from .session import ChoiceSession, _deadline_from_seconds, _remaining_seconds

__all__ = [
    "run_web_choice",
    "WebChoiceServer",
    "ChoiceSession",
    "_deadline_from_seconds",
    "_remaining_seconds",
]
