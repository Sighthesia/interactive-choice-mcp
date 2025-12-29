from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

DEFAULT_TIMEOUT_SECONDS = 300
TRANSPORT_TERMINAL = "terminal"
TRANSPORT_WEB = "web"

# Language constants
LANG_EN = "en"
LANG_ZH = "zh"
VALID_LANGUAGES = {LANG_EN, LANG_ZH}


class ValidationError(ValueError):
    """Raised when incoming tool payloads are invalid."""


# Section: Interaction Status
class InteractionStatus(str, Enum):
    """Status states for an interaction session."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    AUTO_SUBMITTED = "auto_submitted"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    @classmethod
    def from_action_status(cls, action_status: str) -> "InteractionStatus":
        """Convert an action_status string to an InteractionStatus."""
        if action_status.startswith("timeout"):
            if "auto_submitted" in action_status:
                return cls.AUTO_SUBMITTED
            return cls.TIMEOUT
        if action_status in ("cancelled", "cancel_with_annotation"):
            return cls.CANCELLED
        if action_status == "selected":
            return cls.SUBMITTED
        return cls.PENDING


# Section: Data Models
@dataclass
class ProvideChoiceOption:
    """Represents a single selectable option. The option has an `id` which is
    used as its canonical identifier and also displayed to the user as the
    visible label (per new schema semantics).
    """
    id: str
    description: str
    recommended: bool = False

    @property
    def label(self) -> str:
        # Backwards-compatible accessor for templates and existing code
        return self.id


@dataclass
class ProvideChoiceRequest:
    """Internal representation of a validated choice request."""
    title: str
    prompt: str
    selection_mode: str
    options: List[ProvideChoiceOption]
    timeout_seconds: int
    transport: Optional[str] = None
    # Extended schema fields
    single_submit_mode: bool = True
    timeout_default_index: Optional[int] = None
    timeout_default_enabled: bool = False
    use_default_option: bool = False
    timeout_action: str = "submit"


@dataclass
class ProvideChoiceConfig:
    """Represents user-configurable interaction settings."""

    transport: str
    timeout_seconds: int
    # Extended settings
    single_submit_mode: bool = True
    timeout_default_index: Optional[int] = None
    timeout_default_enabled: bool = False
    use_default_option: bool = False
    timeout_action: str = "submit"
    # Persistence settings
    persistence_enabled: bool = True
    retention_days: int = 3
    max_sessions: int = 100
    # Language setting (en/zh)
    language: str = "en"

    # Notification settings
    notify_new: bool = True
    notify_upcoming: bool = True
    upcoming_threshold: int = 60
    notify_timeout: bool = True
    notify_if_foreground: bool = True
    notify_if_focused: bool = True
    notify_if_background: bool = True
    notify_sound: bool = True


@dataclass
class ProvideChoiceSelection:
    """The actual data selected or entered by the user."""
    # Note: selected_indices now holds option IDs (strings) instead of numeric indices.
    selected_indices: List[str] = field(default_factory=list)
    transport: str = TRANSPORT_TERMINAL
    summary: str = ""
    url: Optional[str] = None
    # Annotation fields (keys are option IDs)
    option_annotations: dict[str, str] = field(default_factory=dict)
    global_annotation: Optional[str] = None


@dataclass
class ProvideChoiceResponse:
    """The final response envelope returned to the MCP client."""
    action_status: str
    selection: ProvideChoiceSelection


# Section: Interaction List Entry
@dataclass
class InteractionEntry:
    """Represents an entry in the interaction list shown in the sidebar.

    This is a lightweight view model used for rendering the interaction list
    in the web UI. It captures essential metadata for both web and terminal
    interactions.
    """
    session_id: str
    title: str
    transport: str  # "web" or "terminal"
    status: InteractionStatus
    started_at: str  # ISO 8601 formatted datetime string
    url: Optional[str] = None
    remaining_seconds: Optional[float] = None
    timeout_seconds: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        payload = {
            "session_id": self.session_id,
            "title": self.title,
            "transport": self.transport,
            "status": self.status.value,
            "started_at": self.started_at,
            "url": self.url,
        }
        if self.remaining_seconds is not None:
            payload["remaining_seconds"] = self.remaining_seconds
        if self.timeout_seconds is not None:
            payload["timeout_seconds"] = self.timeout_seconds
        return payload


VALID_SELECTION_MODES = {"single", "multi"}
VALID_ACTIONS = {
    "selected",
    "cancelled",
    "cancel_with_annotation",
    # Timeout variants differentiate auto submission vs. cancelled with no default
    "timeout",
    "timeout_auto_submitted",
    "timeout_cancelled",
    "timeout_reinvoke_requested",
    # Terminal hand-off: returned immediately when launching external terminal UI
    "pending_terminal_launch",
}
VALID_TRANSPORTS = {TRANSPORT_TERMINAL, TRANSPORT_WEB}
