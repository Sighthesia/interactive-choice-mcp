"""Core business logic for interactive choice.

This package contains the fundamental data models, request validation,
response building, and the main orchestrator that coordinates choice sessions.

Modules:
    models: Data structures (ProvideChoiceRequest, ProvideChoiceConfig, etc.)
    validation: Request parsing and configuration application
    response: Response normalization and helper factories
    orchestrator: Central coordinator for choice session lifecycle

Example:
    from src.core import ChoiceOrchestrator, ProvideChoiceConfig

    orchestrator = ChoiceOrchestrator()
    response = await orchestrator.handle_provide_choice(params)
"""
from .models import (
    # Constants
    DEFAULT_TIMEOUT_SECONDS,
    TRANSPORT_TERMINAL,
    TRANSPORT_WEB,
    LANG_EN,
    LANG_ZH,
    VALID_LANGUAGES,
    VALID_SELECTION_MODES,
    VALID_ACTIONS,
    VALID_TRANSPORTS,
    # Exceptions
    ValidationError,
    # Enums
    InteractionStatus,
    # Data classes
    ProvideChoiceOption,
    ProvideChoiceRequest,
    ProvideChoiceConfig,
    ProvideChoiceSelection,
    ProvideChoiceResponse,
    InteractionEntry,
)

from .validation import (
    parse_request,
    apply_configuration,
)

from .response import (
    normalize_response,
    cancelled_response,
    timeout_response,
    pending_terminal_launch_response,
)

# Note: ChoiceOrchestrator is NOT imported here to avoid circular imports.
# Import it directly from src.core.orchestrator when needed.

__all__ = [
    # Constants
    "DEFAULT_TIMEOUT_SECONDS",
    "TRANSPORT_TERMINAL",
    "TRANSPORT_WEB",
    "LANG_EN",
    "LANG_ZH",
    "VALID_LANGUAGES",
    "VALID_SELECTION_MODES",
    "VALID_ACTIONS",
    "VALID_TRANSPORTS",
    # Exceptions
    "ValidationError",
    # Enums
    "InteractionStatus",
    # Data classes
    "ProvideChoiceOption",
    "ProvideChoiceRequest",
    "ProvideChoiceConfig",
    "ProvideChoiceSelection",
    "ProvideChoiceResponse",
    "InteractionEntry",
    # Validation
    "parse_request",
    "apply_configuration",
    # Response
    "normalize_response",
    "cancelled_response",
    "timeout_response",
    "pending_terminal_launch_response",
]
