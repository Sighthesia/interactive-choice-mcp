from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from .logging import get_logger
from .models import (
    ProvideChoiceConfig,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    ValidationError,
    TRANSPORT_TERMINAL,
    TRANSPORT_WEB,
)
from .storage import ConfigStore
from .terminal import is_terminal_available, run_terminal_choice
from .terminal import prompt_configuration as prompt_terminal_configuration
from .validation import apply_configuration, parse_request
from .response import cancelled_response, timeout_response
from .web import run_web_choice, create_terminal_handoff_session, poll_terminal_session_result

_logger = get_logger(__name__)


# Section: Orchestrator Logic
class ChoiceOrchestrator:
    """
    Central coordinator for user interaction.

    This class is responsible for:
    1. Validating the incoming request.
    2. Determining the best available transport (Terminal vs Web).
    3. Executing the interaction on the chosen transport.
    4. Supporting terminal hand-off for non-blocking MCP invocations.
    """
    def __init__(self, *, config_path: Optional[Path] = None) -> None:
        self._store = ConfigStore(path=config_path)
        self._last_config: Optional[ProvideChoiceConfig] = self._store.load()

    async def handle(
        self,
        *,
        title: str,
        prompt: str,
        selection_mode: str,
        options: List[Dict[str, object]],
        transport: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        # Extended schema fields
        single_submit_mode: Optional[bool] = None,
        timeout_default_index: Optional[int] = None,
        timeout_default_enabled: Optional[bool] = None,
        use_default_option: Optional[bool] = None,
        timeout_action: Optional[str] = None,
        # Terminal hand-off support
        session_id: Optional[str] = None,
    ) -> ProvideChoiceResponse:
        """
        Process a choice request from start to finish.
        
        Validates inputs, selects transport, and awaits user action.
        
        When `session_id` is provided, polls for the result of an existing
        terminal hand-off session instead of creating a new interaction.
        """
        _logger.info(f"Handling choice request: title='{title}', mode={selection_mode}, options={len(options)}")

        # Section: Session Polling
        # If session_id is provided, poll for result of existing terminal session.
        # The poll function blocks for up to 30s waiting for the result,
        # reducing the need for frequent polling by the AI agent.
        if session_id is not None:
            result = await poll_terminal_session_result(session_id, wait_seconds=30)
            if result is not None:
                return result
            # Session not found (expired or invalid)
            from .models import ProvideChoiceSelection
            return ProvideChoiceResponse(
                action_status="cancelled",
                selection=ProvideChoiceSelection(
                    selected_indices=[],
                    transport=TRANSPORT_TERMINAL,
                    summary=f"Session {session_id} not found or expired. Please create a new session.",
                ),
            )

        # Section: Request Validation
        # Step 1: Validate and parse the request payload.
        req: ProvideChoiceRequest = parse_request(
            title=title,
            prompt=prompt,
            selection_mode=selection_mode,
            options=options,
            transport=transport,
            timeout_seconds=timeout_seconds,
            single_submit_mode=single_submit_mode,
            timeout_default_index=timeout_default_index,
            timeout_default_enabled=timeout_default_enabled,
            use_default_option=use_default_option,
            timeout_action=timeout_action,
        )
        _logger.debug(f"Request parsed successfully")

        config_defaults = self._build_default_config(req)

        # If the caller prefers terminal transport and a local terminal is available,
        # use the in-process interactive configuration flow (preserves previous behaviour).
        if config_defaults.transport == TRANSPORT_TERMINAL and is_terminal_available():
            _logger.debug("Using terminal transport")
            config = await prompt_terminal_configuration(req, defaults=config_defaults, allow_web=True)
            if config is None:
                # User aborted terminal configuration — fall back to web portal when possible
                _logger.info("Terminal config aborted, falling back to web")
                response, final_config = await run_web_choice(req, defaults=config_defaults, allow_terminal=False)
                self._store.save(final_config)
                self._last_config = final_config
                _logger.info(f"Choice completed via web: action={response.action_status}")
                return response
            if config.transport == TRANSPORT_WEB:
                _logger.info("User selected web transport from terminal config")
                response, final_config = await run_web_choice(req, defaults=config, allow_terminal=False)
                self._store.save(final_config)
                self._last_config = final_config
                _logger.info(f"Choice completed via web: action={response.action_status}")
                return response
            filtered_req = apply_configuration(req, config)
            response = await run_terminal_choice(filtered_req, timeout_seconds=config.timeout_seconds, config=config)
            self._store.save(config)
            self._last_config = config
            _logger.info(f"Choice completed via terminal: action={response.action_status}")
            return response

        # If terminal transport is requested but a local terminal isn't available,
        # create a terminal hand-off session so the agent can launch the terminal UI externally.
        if config_defaults.transport == TRANSPORT_TERMINAL:
            self._store.save(config_defaults)
            self._last_config = config_defaults
            return await create_terminal_handoff_session(req, config_defaults)

        _logger.debug("Using web transport")
        response, final_config = await run_web_choice(req, defaults=config_defaults, allow_terminal=False)
        self._store.save(final_config)
        self._last_config = final_config
        _logger.info(f"Choice completed via web: action={response.action_status}")
        return response

    def _build_default_config(self, req: ProvideChoiceRequest) -> ProvideChoiceConfig:
        saved = self._last_config
        transport_pref = saved.transport if saved else req.transport or TRANSPORT_TERMINAL
        timeout_pref = saved.timeout_seconds if saved else req.timeout_seconds

        # Extended settings: inherit from saved config or request defaults
        single_submit_pref = saved.single_submit_mode if saved else req.single_submit_mode
        timeout_default_index_pref = saved.timeout_default_index if saved else req.timeout_default_index
        timeout_default_enabled_pref = saved.timeout_default_enabled if saved else req.timeout_default_enabled
        use_default_option_pref = saved.use_default_option if saved else req.use_default_option
        timeout_action_pref = saved.timeout_action if saved else req.timeout_action
        return ProvideChoiceConfig(
            transport=transport_pref,
            timeout_seconds=timeout_pref,
            single_submit_mode=single_submit_pref,
            timeout_default_index=timeout_default_index_pref,
            timeout_default_enabled=timeout_default_enabled_pref,
            use_default_option=use_default_option_pref,
            timeout_action=timeout_action_pref,
        )



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
        # Return a cancelled response if validation fails, including the validation detail.
        _logger.warning(f"Validation error: {exc}")
        return cancelled_response(
            transport=kwargs.get("transport") or TRANSPORT_TERMINAL,
            url=None,
            summary=f"validation_error: {exc}",
        )
    except asyncio.CancelledError:
        _logger.debug("Request cancelled")
        raise
    except Exception as exc:
        # Catch-all for other errors, treating them as timeouts/failures.
        _logger.exception(f"Unexpected error during orchestration: {exc}")
        # We try to parse the request to get the req object for timeout_response
        try:
            # Filter out session_id as it's not part of parse_request
            parse_kwargs = {k: v for k, v in kwargs.items() if k != "session_id"}
            req = parse_request(**parse_kwargs)
            return timeout_response(req=req, transport=kwargs.get("transport") or TRANSPORT_TERMINAL, url=None)
        except Exception:
            # If even parsing fails, we can't use timeout_response properly, return cancelled
            return cancelled_response(transport=kwargs.get("transport") or TRANSPORT_TERMINAL, url=None)
