from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

DEFAULT_TIMEOUT_SECONDS = 300
TRANSPORT_TERMINAL = "terminal"
TRANSPORT_WEB = "web"


class ValidationError(ValueError):
    """Raised when incoming tool payloads are invalid."""


# Section: Data Models
@dataclass
class ProvideChoiceOption:
    """Represents a single selectable option."""
    id: str
    label: str
    description: str


@dataclass
class ProvideChoiceRequest:
    """Internal representation of a validated choice request."""
    title: str
    prompt: str
    type: str
    options: List[ProvideChoiceOption]
    allow_cancel: bool
    timeout_seconds: int
    placeholder: Optional[str] = None
    transport: Optional[str] = None


@dataclass
class ProvideChoiceSelection:
    """The actual data selected or entered by the user."""
    selected_ids: List[str] = field(default_factory=list)
    custom_input: Optional[str] = None
    transport: str = TRANSPORT_TERMINAL
    summary: str = ""
    url: Optional[str] = None


@dataclass
class ProvideChoiceResponse:
    """The final response envelope returned to the MCP client."""
    action_status: str
    selection: ProvideChoiceSelection


VALID_TYPES = {"single_select", "multi_select", "text_input", "hybrid"}
VALID_ACTIONS = {"selected", "custom_input", "cancelled", "timeout"}
VALID_TRANSPORTS = {TRANSPORT_TERMINAL, TRANSPORT_WEB}


# Section: Validation Logic
def _ensure_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


def _validate_options(options: Sequence[dict | ProvideChoiceOption]) -> List[ProvideChoiceOption]:
    """
    Validate and normalize the list of options.
    Ensures all options have required fields and unique IDs.
    """
    if not options:
        raise ValidationError("options must contain at least one entry")
    parsed: List[ProvideChoiceOption] = []
    seen_ids: set[str] = set()
    for raw in options:
        if isinstance(raw, ProvideChoiceOption):
            opt = raw
        else:
            try:
                opt = ProvideChoiceOption(
                    id=str(raw["id"]),
                    label=str(raw["label"]),
                    description=str(raw.get("description", "")),
                )
            except Exception as exc:  # noqa: BLE001
                raise ValidationError("options entries must include id, label, description") from exc
        _ensure_non_empty(opt.id, "option.id")
        _ensure_non_empty(opt.label, "option.label")
        if opt.id in seen_ids:
            raise ValidationError(f"duplicate option id: {opt.id}")
        seen_ids.add(opt.id)
        parsed.append(opt)
    return parsed


def _validate_transport(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value not in VALID_TRANSPORTS:
        raise ValidationError(f"transport must be one of {sorted(VALID_TRANSPORTS)} when provided")
    return value


def parse_request(
    *,
    title: str,
    prompt: str,
    type: str,
    options: Sequence[dict | ProvideChoiceOption],
    allow_cancel: bool,
    placeholder: Optional[str] = None,
    transport: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> ProvideChoiceRequest:
    """Validate and normalize tool inputs into a request model."""

    _ensure_non_empty(title, "title")
    _ensure_non_empty(prompt, "prompt")
    if type not in VALID_TYPES:
        raise ValidationError(f"type must be one of {sorted(VALID_TYPES)}")
    parsed_options = _validate_options(options)
    validated_transport = _validate_transport(transport)

    normalized_timeout = timeout_seconds
    if normalized_timeout is None:
        env_timeout = os.environ.get("CHOICE_TIMEOUT_SECONDS")
        if env_timeout:
            try:
                normalized_timeout = int(env_timeout)
            except ValueError as exc:  # noqa: BLE001
                raise ValidationError("CHOICE_TIMEOUT_SECONDS must be an integer") from exc
    if normalized_timeout is None:
        normalized_timeout = DEFAULT_TIMEOUT_SECONDS
    if normalized_timeout <= 0:
        raise ValidationError("timeout_seconds must be positive")

    return ProvideChoiceRequest(
        title=title.strip(),
        prompt=prompt.strip(),
        type=type,
        options=parsed_options,
        allow_cancel=bool(allow_cancel),
        placeholder=placeholder.strip() if placeholder else None,
        transport=validated_transport,
        timeout_seconds=normalized_timeout,
    )


def normalize_response(
    *,
    req: ProvideChoiceRequest,
    selected_ids: Sequence[str] | None,
    custom_input: Optional[str],
    transport: str,
    url: Optional[str] = None,
) -> ProvideChoiceResponse:
    if transport not in VALID_TRANSPORTS:
        raise ValidationError("invalid transport for response")

    action_status = "selected"
    if custom_input is not None:
        action_status = "custom_input"
    if selected_ids is None:
        selected_ids = []
    ordered_ids = list(selected_ids)

    summary_parts: list[str] = []
    if ordered_ids:
        summary_parts.append(f"options={ordered_ids}")
    if custom_input:
        summary_parts.append(f"custom_input={custom_input}")
    summary = ", ".join(summary_parts) if summary_parts else "no selection"

    selection = ProvideChoiceSelection(
        selected_ids=ordered_ids,
        custom_input=custom_input,
        transport=transport,
        summary=summary,
        url=url,
    )

    return ProvideChoiceResponse(action_status=action_status, selection=selection)


def cancelled_response(*, transport: str, url: Optional[str] = None) -> ProvideChoiceResponse:
    selection = ProvideChoiceSelection(selected_ids=[], custom_input=None, transport=transport, summary="cancelled", url=url)
    return ProvideChoiceResponse(action_status="cancelled", selection=selection)


def timeout_response(*, transport: str, url: Optional[str] = None) -> ProvideChoiceResponse:
    selection = ProvideChoiceSelection(selected_ids=[], custom_input=None, transport=transport, summary="timeout", url=url)
    return ProvideChoiceResponse(action_status="timeout", selection=selection)
