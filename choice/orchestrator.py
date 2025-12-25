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


class ChoiceOrchestrator:
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

        chosen_transport = self._choose_transport(req.transport)
        if chosen_transport == TRANSPORT_TERMINAL and not is_terminal_available():
            chosen_transport = TRANSPORT_WEB

        if chosen_transport == TRANSPORT_TERMINAL:
            return await run_terminal_choice(req, timeout_seconds=req.timeout_seconds)

        return await run_web_choice(req, timeout_seconds=req.timeout_seconds)

    def _choose_transport(self, explicit: Optional[str]) -> str:
        if explicit == TRANSPORT_TERMINAL:
            return TRANSPORT_TERMINAL
        if explicit == TRANSPORT_WEB:
            return TRANSPORT_WEB
        return TRANSPORT_TERMINAL


async def safe_handle(orchestrator: ChoiceOrchestrator, **kwargs) -> ProvideChoiceResponse:
    try:
        return await orchestrator.handle(**kwargs)
    except ValidationError as exc:
        return cancelled_response(transport=kwargs.get("transport") or TRANSPORT_TERMINAL, url=None)
    except asyncio.CancelledError:
        raise
    except Exception:
        return timeout_response(transport=kwargs.get("transport") or TRANSPORT_TERMINAL, url=None)
