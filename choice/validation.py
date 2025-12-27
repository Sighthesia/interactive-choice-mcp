"""Validation helpers extracted from `models.py`.

Contains the request parsing logic and configuration application helpers.
Kept intentionally side-effect free to avoid import cycles and simplify
unit testing.
"""
from __future__ import annotations

import os
from typing import List, Optional, Sequence

__all__ = [
    "parse_request",
    "apply_configuration",
]


# Section: Validation Helpers
def _ensure_non_empty(value: str, field_name: str) -> None:
    from .models import ValidationError

    if not value or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


def _validate_options(options: Sequence[dict | "ProvideChoiceOption"]) -> List["ProvideChoiceOption"]:
    from .models import ProvideChoiceOption, ValidationError

    if not options:
        raise ValidationError("options must contain at least one entry")
    parsed: List[ProvideChoiceOption] = []
    seen_ids: set[str] = set()
    for raw in options:
        if isinstance(raw, ProvideChoiceOption):
            opt = raw
        else:
            try:
                raw_id = raw.get("id") if isinstance(raw, dict) else None
                if raw_id is None:
                    raise ValidationError("options entries must include an 'id' and description")
                opt_recommended_raw = raw.get("recommended", False)
                if isinstance(opt_recommended_raw, bool):
                    opt_recommended = opt_recommended_raw
                else:
                    raise ValidationError("option.recommended must be a boolean when provided")
                opt = ProvideChoiceOption(
                    id=str(raw_id),
                    description=str(raw.get("description", "")),
                    recommended=opt_recommended,
                )
            except ValidationError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise ValidationError("options entries must include an 'id' and description") from exc
        _ensure_non_empty(opt.id, "option.id")
        if not isinstance(opt.recommended, bool):
            raise ValidationError("option.recommended must be a boolean when provided")
        if opt.id in seen_ids:
            raise ValidationError(f"duplicate option id: {opt.id}")
        seen_ids.add(opt.id)
        parsed.append(opt)

    if not any(opt.recommended for opt in parsed):
        raise ValidationError("at least one option must be marked as recommended")

    return parsed


def _normalize_selection_mode(value: str) -> str:
    from .models import ValidationError, VALID_SELECTION_MODES

    normalized = value.strip().lower().replace("-", "_")
    if normalized not in VALID_SELECTION_MODES:
        raise ValidationError(f"selection_mode must be one of {sorted(VALID_SELECTION_MODES)}")
    return normalized


def _validate_transport(value: Optional[str]) -> Optional[str]:
    from .models import VALID_TRANSPORTS, ValidationError

    if value is None:
        return None
    if value not in VALID_TRANSPORTS:
        raise ValidationError(f"transport must be one of {sorted(VALID_TRANSPORTS)} when provided")
    return value


# Section: Public API
def parse_request(
    *,
    title: str,
    prompt: str,
    selection_mode: str,
    options: Sequence[dict | "ProvideChoiceOption"],
    transport: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    # Extended schema fields
    single_submit_mode: Optional[bool] = None,
    timeout_default_index: Optional[int] = None,
    timeout_default_enabled: Optional[bool] = None,
    use_default_option: Optional[bool] = None,
    timeout_action: Optional[str] = None,
) -> "ProvideChoiceRequest":
    """Validate and normalize tool inputs into a request model."""

    from .models import (
        DEFAULT_TIMEOUT_SECONDS,
        ProvideChoiceOption,
        ProvideChoiceRequest,
        ValidationError,
    )

    _ensure_non_empty(title, "title")
    _ensure_non_empty(prompt, "prompt")
    normalized_selection_mode = _normalize_selection_mode(selection_mode)
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

    if timeout_default_index is not None:
        if timeout_default_index < 0 or timeout_default_index >= len(parsed_options):
            raise ValidationError(f"timeout_default_index {timeout_default_index} out of range")

    recommended_count = sum(1 for opt in parsed_options if opt.recommended)
    if normalized_selection_mode == "single" and recommended_count > 1:
        raise ValidationError("single requests may only mark one recommended option")

    return ProvideChoiceRequest(
        title=title.strip(),
        prompt=prompt.strip(),
        selection_mode=normalized_selection_mode,
        options=parsed_options,
        transport=validated_transport,
        timeout_seconds=normalized_timeout,
        single_submit_mode=single_submit_mode if single_submit_mode is not None else True,
        timeout_default_index=timeout_default_index,
        timeout_default_enabled=bool(timeout_default_enabled),
        use_default_option=bool(use_default_option),
        timeout_action=timeout_action or "submit",
    )


def apply_configuration(
    req: "ProvideChoiceRequest",
    config: "ProvideChoiceConfig",
) -> "ProvideChoiceRequest":
    """Apply user configuration to the request (transport, timeout, extended settings)."""

    from .models import ProvideChoiceConfig, ProvideChoiceRequest, VALID_TRANSPORTS, ValidationError

    if config.transport not in VALID_TRANSPORTS:
        raise ValidationError(f"transport must be one of {sorted(VALID_TRANSPORTS)}")
    if config.timeout_seconds <= 0:
        raise ValidationError("timeout_seconds must be positive")

    timeout_default_index = config.timeout_default_index
    if timeout_default_index is not None:
        if timeout_default_index < 0 or timeout_default_index >= len(req.options):
            timeout_default_index = None

    return ProvideChoiceRequest(
        title=req.title,
        prompt=req.prompt,
        selection_mode=req.selection_mode,
        options=req.options,
        transport=config.transport,
        timeout_seconds=config.timeout_seconds,
        single_submit_mode=config.single_submit_mode,
        timeout_default_index=timeout_default_index,
        timeout_default_enabled=config.timeout_default_enabled,
        use_default_option=config.use_default_option,
        timeout_action=config.timeout_action,
    )
