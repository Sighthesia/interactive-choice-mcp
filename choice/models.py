from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_TIMEOUT_SECONDS = 300
TRANSPORT_TERMINAL = "terminal"
TRANSPORT_WEB = "web"


class ValidationError(ValueError):
    """Raised when incoming tool payloads are invalid."""


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


VALID_SELECTION_MODES = {"single", "multi"}
VALID_ACTIONS = {
    "selected",
    "cancelled",
    # Timeout variants differentiate auto submission vs. cancelled with no default
    "timeout",
    "timeout_auto_submitted",
    "timeout_cancelled",
    "timeout_reinvoke_requested",
    # Terminal hand-off: returned immediately when launching external terminal UI
    "pending_terminal_launch",
}
VALID_TRANSPORTS = {TRANSPORT_TERMINAL, TRANSPORT_WEB}
