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
    timeout_seconds: int
    placeholder: Optional[str] = None
    transport: Optional[str] = None
    # Extended schema fields
    default_selection_ids: List[str] = field(default_factory=list)
    min_selections: int = 0
    max_selections: Optional[int] = None
    single_submit_mode: bool = True
    placeholder_enabled: bool = True


@dataclass
class ProvideChoiceConfig:
    """Represents user-configurable interaction settings."""

    transport: str
    visible_option_ids: List[str]
    timeout_seconds: int
    placeholder: Optional[str] = None
    # Extended settings
    default_selection_ids: List[str] = field(default_factory=list)
    min_selections: int = 0
    max_selections: Optional[int] = None
    single_submit_mode: bool = True
    placeholder_enabled: bool = True
    annotations_enabled: bool = False


@dataclass
class ProvideChoiceSelection:
    """The actual data selected or entered by the user."""
    selected_ids: List[str] = field(default_factory=list)
    custom_input: Optional[str] = None
    transport: str = TRANSPORT_TERMINAL
    summary: str = ""
    url: Optional[str] = None
    # Annotation fields
    option_annotations: dict[str, str] = field(default_factory=dict)
    global_annotation: Optional[str] = None


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
    placeholder: Optional[str] = None,
    transport: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    # Extended schema fields
    default_selection_ids: Optional[List[str]] = None,
    min_selections: Optional[int] = None,
    max_selections: Optional[int] = None,
    single_submit_mode: Optional[bool] = None,
    placeholder_enabled: Optional[bool] = None,
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

    # Validate min/max selection bounds
    valid_option_ids = {opt.id for opt in parsed_options}
    norm_min = min_selections if min_selections is not None else 0
    norm_max = max_selections
    if norm_min < 0:
        raise ValidationError("min_selections must be non-negative")
    if norm_max is not None and norm_max < 1:
        raise ValidationError("max_selections must be at least 1")
    if norm_max is not None and norm_min > norm_max:
        raise ValidationError("min_selections must not exceed max_selections")

    # Validate default_selection_ids against options
    norm_defaults: List[str] = []
    if default_selection_ids:
        for did in default_selection_ids:
            if did not in valid_option_ids:
                raise ValidationError(f"default_selection_ids contains invalid option: {did}")
            norm_defaults.append(did)

    return ProvideChoiceRequest(
        title=title.strip(),
        prompt=prompt.strip(),
        type=type,
        options=parsed_options,
        placeholder=placeholder.strip() if placeholder else None,
        transport=validated_transport,
        timeout_seconds=normalized_timeout,
        default_selection_ids=norm_defaults,
        min_selections=norm_min,
        max_selections=norm_max,
        single_submit_mode=single_submit_mode if single_submit_mode is not None else True,
        placeholder_enabled=placeholder_enabled if placeholder_enabled is not None else True,
    )


def apply_configuration(
    req: ProvideChoiceRequest,
    config: ProvideChoiceConfig,
) -> ProvideChoiceRequest:
    """Apply user configuration to the request (transport, visible options, timeout, extended settings)."""

    if config.transport not in VALID_TRANSPORTS:
        raise ValidationError(f"transport must be one of {sorted(VALID_TRANSPORTS)}")
    if config.timeout_seconds <= 0:
        raise ValidationError("timeout_seconds must be positive")

    # Filter options by visibility; fall back to all if none remain.
    visible_ids = set(config.visible_option_ids)
    filtered_options = [opt for opt in req.options if opt.id in visible_ids]
    if not filtered_options:
        filtered_options = list(req.options)

    # Validate min/max from config
    norm_min = config.min_selections
    norm_max = config.max_selections
    if norm_min < 0:
        norm_min = 0
    if norm_max is not None and norm_max < 1:
        norm_max = None
    if norm_max is not None and norm_min > norm_max:
        norm_min = 0  # fall back to safe default

    # Filter defaults against visible options
    visible_set = {opt.id for opt in filtered_options}
    filtered_defaults = [d for d in config.default_selection_ids if d in visible_set]

    return ProvideChoiceRequest(
        title=req.title,
        prompt=req.prompt,
        type=req.type,
        options=filtered_options,
        placeholder=config.placeholder if config.placeholder is not None else req.placeholder,
        transport=config.transport,
        timeout_seconds=config.timeout_seconds,
        default_selection_ids=filtered_defaults,
        min_selections=norm_min,
        max_selections=norm_max,
        single_submit_mode=config.single_submit_mode,
        placeholder_enabled=config.placeholder_enabled,
    )


def normalize_response(
    *,
    req: ProvideChoiceRequest,
    selected_ids: Sequence[str] | None,
    custom_input: Optional[str],
    transport: str,
    url: Optional[str] = None,
    option_annotations: Optional[dict[str, str]] = None,
    global_annotation: Optional[str] = None,
) -> ProvideChoiceResponse:
    """
    Normalize response, enforcing min/max selection counts (except for custom_input).
    """
    if transport not in VALID_TRANSPORTS:
        raise ValidationError("invalid transport for response")

    action_status = "selected"
    if custom_input is not None:
        action_status = "custom_input"
    if selected_ids is None:
        selected_ids = []
    ordered_ids = list(selected_ids)

    # Enforce min/max constraints on selections (custom input bypasses)
    if action_status == "selected":
        count = len(ordered_ids)
        if count < req.min_selections:
            raise ValidationError(f"selection count {count} below minimum {req.min_selections}")
        if req.max_selections is not None and count > req.max_selections:
            raise ValidationError(f"selection count {count} exceeds maximum {req.max_selections}")

    summary_parts: list[str] = []
    if ordered_ids:
        summary_parts.append(f"options={ordered_ids}")
    if custom_input:
        summary_parts.append(f"custom_input={custom_input}")
    if option_annotations:
        summary_parts.append(f"option_annotations={option_annotations}")
    if global_annotation:
        summary_parts.append(f"global_annotation={global_annotation}")
    summary = ", ".join(summary_parts) if summary_parts else "no selection"

    selection = ProvideChoiceSelection(
        selected_ids=ordered_ids,
        custom_input=custom_input,
        transport=transport,
        summary=summary,
        url=url,
        option_annotations=option_annotations or {},
        global_annotation=global_annotation,
    )

    return ProvideChoiceResponse(action_status=action_status, selection=selection)


def cancelled_response(*, transport: str, url: Optional[str] = None) -> ProvideChoiceResponse:
    selection = ProvideChoiceSelection(selected_ids=[], custom_input=None, transport=transport, summary="cancelled", url=url)
    return ProvideChoiceResponse(action_status="cancelled", selection=selection)


def timeout_response(*, transport: str, url: Optional[str] = None) -> ProvideChoiceResponse:
    selection = ProvideChoiceSelection(selected_ids=[], custom_input=None, transport=transport, summary="timeout", url=url)
    return ProvideChoiceResponse(action_status="timeout", selection=selection)
