from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from .models import (
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    ValidationError,
    cancelled_response,
    parse_request,
    timeout_response,
    TRANSPORT_TERMINAL,
    TRANSPORT_WEB,
)
from .terminal import is_terminal_available, run_terminal_choice
from .web import run_web_choice


# Section: Orchestrator Logic
class ChoiceOrchestrator:
    """
    Central coordinator for user interaction.

    This class is responsible for:
    1. Validating the incoming request.
    2. Determining the best available transport (Terminal vs Web).
    3. Executing the interaction on the chosen transport.
    """
    def __init__(self) -> None:
        pass

    async def handle(
        self,
        *,
        title: str,
        prompt: str,
        type: str,
        options: List[Dict[str, object]],
        allow_cancel: bool,
        placeholder: Optional[str] = None,
        transport: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> ProvideChoiceResponse:
        """
        Process a choice request from start to finish.
        
        Validates inputs, selects transport, and awaits user action.
        """
        # Step 1: Validate and parse the request payload.
        req: ProvideChoiceRequest = parse_request(
            title=title,
            prompt=prompt,
            type=type,
            options=options,
            allow_cancel=allow_cancel,
            placeholder=placeholder,
            transport=transport,
            timeout_seconds=timeout_seconds,
        )

        # Step 2: Select the transport mechanism.
        # We prefer the terminal if explicitly requested or if no preference is given
        # AND the terminal is interactive. Otherwise, we fall back to the web bridge.
        chosen_transport = self._choose_transport(req.transport)
        if chosen_transport == TRANSPORT_TERMINAL and not is_terminal_available():
            chosen_transport = TRANSPORT_WEB

        # Step 3: Execute the interaction.
        if chosen_transport == TRANSPORT_TERMINAL:
            return await run_terminal_choice(req, timeout_seconds=req.timeout_seconds)

        return await run_web_choice(req, timeout_seconds=req.timeout_seconds)

    def _choose_transport(self, explicit: Optional[str]) -> str:
        """Determine the preferred transport based on explicit request."""
        if explicit == TRANSPORT_TERMINAL:
            return TRANSPORT_TERMINAL
        if explicit == TRANSPORT_WEB:
            return TRANSPORT_WEB
        # Default to terminal if not specified
        return TRANSPORT_TERMINAL


# Section: Safety Wrapper
async def safe_handle(orchestrator: ChoiceOrchestrator, **kwargs) -> ProvideChoiceResponse:
    """
    Wrapper to catch unexpected errors during orchestration.
    
    Ensures that the MCP tool always returns a valid JSON response,
    even if validation fails or an unhandled exception occurs.
    """
    try:
        return await orchestrator.handle(**kwargs)
    except ValidationError as exc:
        # Return a cancelled response if validation fails, rather than crashing.
        return cancelled_response(transport=kwargs.get("transport") or TRANSPORT_TERMINAL, url=None)
    except asyncio.CancelledError:
        raise
    except Exception:
        # Catch-all for other errors, treating them as timeouts/failures.
        return timeout_response(transport=kwargs.get("transport") or TRANSPORT_TERMINAL, url=None)
