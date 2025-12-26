from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    DEFAULT_TIMEOUT_SECONDS,
    ProvideChoiceConfig,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    ValidationError,
    apply_configuration,
    cancelled_response,
    parse_request,
    timeout_response,
    TRANSPORT_TERMINAL,
    TRANSPORT_WEB,
)
from .terminal import is_terminal_available, run_terminal_choice
from .terminal import prompt_configuration as prompt_terminal_configuration
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
    def __init__(self, *, config_path: Optional[Path] = None) -> None:
        self._config_path = config_path or Path.home() / ".interactive_choice_config.json"
        self._last_config: Optional[ProvideChoiceConfig] = self._load_config()

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
        config_defaults = self._build_default_config(req)
        # If terminal is unavailable, force web transport.
        if config_defaults.transport == TRANSPORT_TERMINAL and not is_terminal_available():
            config_defaults.transport = TRANSPORT_WEB

        # Step 2: Collect configuration surface based on transport availability.
        if config_defaults.transport == TRANSPORT_TERMINAL and is_terminal_available():
            config = await prompt_terminal_configuration(req, defaults=config_defaults, allow_web=True)
            if config is None:
                return cancelled_response(transport=TRANSPORT_TERMINAL)
            if config.transport == TRANSPORT_WEB:
                response, final_config = await run_web_choice(req, defaults=config, allow_terminal=False)
                self._persist_config(final_config)
                return response
            filtered_req = apply_configuration(req, config)
            response = await run_terminal_choice(filtered_req, timeout_seconds=config.timeout_seconds)
            self._persist_config(config)
            return response

        response, final_config = await run_web_choice(req, defaults=config_defaults, allow_terminal=False)
        self._persist_config(final_config)
        return response

    def _build_default_config(self, req: ProvideChoiceRequest) -> ProvideChoiceConfig:
        visible_ids = [opt.id for opt in req.options]
        saved = self._last_config
        transport_pref = saved.transport if saved else req.transport or TRANSPORT_TERMINAL
        timeout_pref = saved.timeout_seconds if saved else req.timeout_seconds
        visible_pref = [vid for vid in (saved.visible_option_ids if saved else visible_ids) if vid in visible_ids]
        if not visible_pref:
            visible_pref = list(visible_ids)
        return ProvideChoiceConfig(
            transport=transport_pref,
            visible_option_ids=visible_pref,
            timeout_seconds=timeout_pref,
        )

    def _load_config(self) -> Optional[ProvideChoiceConfig]:
        try:
            if not self._config_path.exists():
                return None
            payload = json.loads(self._config_path.read_text())
            transport = payload.get("transport")
            visible_option_ids = payload.get("visible_option_ids") or []
            timeout_seconds = int(payload.get("timeout_seconds", 0))
            config = ProvideChoiceConfig(
                transport=transport or TRANSPORT_TERMINAL,
                visible_option_ids=list(map(str, visible_option_ids)),
                timeout_seconds=timeout_seconds if timeout_seconds > 0 else DEFAULT_TIMEOUT_SECONDS,
            )
            return config
        except Exception:
            return None

    def _persist_config(self, config: ProvideChoiceConfig) -> None:
        try:
            data = {
                "transport": config.transport,
                "visible_option_ids": config.visible_option_ids,
                "timeout_seconds": config.timeout_seconds,
            }
            self._config_path.write_text(json.dumps(data))
            self._last_config = config
        except Exception:
            # Persistence failures should not break the interaction flow.
            pass


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
