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
    label: str
    description: str


@dataclass
class ProvideChoiceRequest:
    """Internal representation of a validated choice request."""
    title: str
    prompt: str
    type: str
    options: List[ProvideChoiceOption]
    timeout_seconds: int
    transport: Optional[str] = None
    # Extended schema fields
    single_submit_mode: bool = True
    timeout_default_index: Optional[int] = None
    timeout_default_enabled: bool = False


@dataclass
class ProvideChoiceConfig:
    """Represents user-configurable interaction settings."""

    transport: str
    timeout_seconds: int
    # Extended settings
    single_submit_mode: bool = True
    timeout_default_index: Optional[int] = None
    timeout_default_enabled: bool = False


@dataclass
class ProvideChoiceSelection:
    """The actual data selected or entered by the user."""
    selected_indices: List[int] = field(default_factory=list)
    transport: str = TRANSPORT_TERMINAL
    summary: str = ""
    url: Optional[str] = None
    # Annotation fields
    option_annotations: dict[int, str] = field(default_factory=dict)
    global_annotation: Optional[str] = None


@dataclass
class ProvideChoiceResponse:
    """The final response envelope returned to the MCP client."""
    action_status: str
    selection: ProvideChoiceSelection


VALID_TYPES = {"single_select", "multi_select"}
VALID_ACTIONS = {"selected", "cancelled", "timeout"}
VALID_TRANSPORTS = {TRANSPORT_TERMINAL, TRANSPORT_WEB}


# Section: Validation Logic
def _ensure_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


def _validate_options(options: Sequence[dict | ProvideChoiceOption]) -> List[ProvideChoiceOption]:
    """
    Validate and normalize the list of options.
    Ensures all options have required fields.
    """
    if not options:
        raise ValidationError("options must contain at least one entry")
    parsed: List[ProvideChoiceOption] = []
    for raw in options:
        if isinstance(raw, ProvideChoiceOption):
            opt = raw
        else:
            try:
                opt = ProvideChoiceOption(
                    label=str(raw["label"]),
                    description=str(raw.get("description", "")),
                )
            except Exception as exc:  # noqa: BLE001
                raise ValidationError("options entries must include label, description") from exc
        _ensure_non_empty(opt.label, "option.label")
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
    transport: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    # Extended schema fields
    single_submit_mode: Optional[bool] = None,
    timeout_default_index: Optional[int] = None,
    timeout_default_enabled: Optional[bool] = None,
    # Legacy: allow_cancel is ignored, cancel always enabled
    allow_cancel: bool = True,  # noqa: ARG001
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

    # Validate timeout_default_index
    if timeout_default_index is not None:
        if timeout_default_index < 0 or timeout_default_index >= len(parsed_options):
            raise ValidationError(f"timeout_default_index {timeout_default_index} out of range")

    return ProvideChoiceRequest(
        title=title.strip(),
        prompt=prompt.strip(),
        type=type,
        options=parsed_options,
        transport=validated_transport,
        timeout_seconds=normalized_timeout,
        single_submit_mode=single_submit_mode if single_submit_mode is not None else True,
        timeout_default_index=timeout_default_index,
        timeout_default_enabled=bool(timeout_default_enabled),
    )


def apply_configuration(
    req: ProvideChoiceRequest,
    config: ProvideChoiceConfig,
) -> ProvideChoiceRequest:
    """Apply user configuration to the request (transport, timeout, extended settings)."""

    if config.transport not in VALID_TRANSPORTS:
        raise ValidationError(f"transport must be one of {sorted(VALID_TRANSPORTS)}")
    if config.timeout_seconds <= 0:
        raise ValidationError("timeout_seconds must be positive")

    return ProvideChoiceRequest(
        title=req.title,
        prompt=req.prompt,
        type=req.type,
        options=req.options,
        transport=config.transport,
        timeout_seconds=config.timeout_seconds,
        single_submit_mode=config.single_submit_mode,
        timeout_default_index=config.timeout_default_index,
        timeout_default_enabled=config.timeout_default_enabled,
    )


def normalize_response(
    *,
    req: ProvideChoiceRequest,
    selected_indices: Sequence[int] | None,
    transport: str,
    url: Optional[str] = None,
    option_annotations: Optional[dict[int, str]] = None,
    global_annotation: Optional[str] = None,
    action_status: str = "selected",
) -> ProvideChoiceResponse:
    """
    Normalize response, enforcing min/max selection counts.
    """
    if transport not in VALID_TRANSPORTS:
        raise ValidationError("invalid transport for response")

    if selected_indices is None:
        selected_indices = []
    ordered_indices = list(selected_indices)



    summary_parts: list[str] = []
    if ordered_indices:
        summary_parts.append(f"indices={ordered_indices}")
    if option_annotations:
        summary_parts.append(f"option_annotations={option_annotations}")
    if global_annotation:
        summary_parts.append(f"global_annotation={global_annotation}")
    summary = ", ".join(summary_parts) if summary_parts else "no selection"

    selection = ProvideChoiceSelection(
        selected_indices=ordered_indices,
        transport=transport,
        summary=summary,
        url=url,
        option_annotations=option_annotations or {},
        global_annotation=global_annotation,
    )

    return ProvideChoiceResponse(action_status=action_status, selection=selection)


def cancelled_response(
    *,
    transport: str,
    url: Optional[str] = None,
    option_annotations: Optional[dict[int, str]] = None,
    global_annotation: Optional[str] = None,
) -> ProvideChoiceResponse:
    selection = ProvideChoiceSelection(
        selected_indices=[],
        transport=transport,
        summary="cancelled",
        url=url,
        option_annotations=option_annotations or {},
        global_annotation=global_annotation,
    )
    return ProvideChoiceResponse(action_status="cancelled", selection=selection)


def timeout_response(*, req: ProvideChoiceRequest, transport: str, url: Optional[str] = None) -> ProvideChoiceResponse:
    """Generate a timeout response, potentially with a default selection."""
    indices = []
    if req.timeout_default_enabled and req.timeout_default_index is not None:
        indices = [req.timeout_default_index]

    return normalize_response(
        req=req,
        selected_indices=indices,
        transport=transport,
        url=url,
        action_status="timeout"
    )
