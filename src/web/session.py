"""Session lifecycle and timeout helpers for web interactions."""
from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, Set, TYPE_CHECKING

from ..core.models import (
    InteractionEntry,
    InteractionStatus,
    ProvideChoiceConfig,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    TRANSPORT_WEB,
)
from ..core.response import timeout_response

if TYPE_CHECKING:
    from fastapi import WebSocket

__all__ = [
    "ChoiceSession",
    "_deadline_from_seconds",
    "_remaining_seconds",
    "_status_label",
]


def _deadline_from_seconds(seconds: int, *, now: Optional[float] = None) -> float:
    base = now if now is not None else time.monotonic()
    return base + max(1, int(seconds))


def _remaining_seconds(deadline: float, *, now: Optional[float] = None) -> float:
    base = now if now is not None else time.monotonic()
    return max(0.0, deadline - base)


def _status_label(action_status: str) -> str:
    if action_status.startswith("timeout"):
        return "timeout"
    if action_status == "cancelled":
        return "cancelled"
    return "submitted"


@dataclass
class ChoiceSession:
    choice_id: str
    req: ProvideChoiceRequest
    defaults: ProvideChoiceConfig
    allow_terminal: bool
    url: str
    deadline: float
    result_future: asyncio.Future[ProvideChoiceResponse]
    connections: Set["WebSocket"]
    config_used: ProvideChoiceConfig
    created_at: float  # monotonic time when session was created
    invocation_time: str  # formatted datetime string when session was created
    transport: str = TRANSPORT_WEB  # "web" or "terminal" - the interface used
    status: str = "pending"
    final_result: Optional[ProvideChoiceResponse] = None
    completed_at: Optional[float] = None
    monitor_task: Optional[asyncio.Task[None]] = None

    def effective_defaults(self) -> ProvideChoiceConfig:
        return self.config_used if self.final_result else self.defaults

    def update_deadline(self, seconds: int) -> None:
        self.deadline = _deadline_from_seconds(seconds)
        self.config_used.timeout_seconds = seconds

    def set_result(self, response: ProvideChoiceResponse) -> bool:
        """Set the final result for this session.
        
        Note: Even if the future is already done (e.g., from timeout), we still
        update final_result so that interaction list displays correct status.
        """
        # Always update final_result for consistent status display
        self.final_result = response
        self.status = _status_label(response.action_status)
        self.completed_at = time.monotonic()
        
        # Try to set future result if not already done
        if self.result_future.done():
            return False
        self.result_future.set_result(response)
        return True

    async def wait_for_result(self) -> ProvideChoiceResponse:
        return await self.result_future

    async def broadcast_sync(self) -> None:
        if not self.connections:
            return
        payload = {
            "type": "sync",
            "remaining_seconds": _remaining_seconds(self.deadline),
            "timeout_seconds": self.config_used.timeout_seconds,
        }
        stale: set["WebSocket"] = set()
        for ws in list(self.connections):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.add(ws)
        for ws in stale:
            self.connections.discard(ws)

    async def broadcast_status(self, status: str, action_status: Optional[str] = None) -> None:
        if not self.connections:
            return
        payload = {"type": "status", "status": status}
        if action_status:
            payload["action_status"] = action_status
        stale: set["WebSocket"] = set()
        for ws in list(self.connections):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.add(ws)
        for ws in stale:
            self.connections.discard(ws)

    def to_template_state(self) -> dict[str, object]:
        if not self.final_result:
            return {
                "status": "pending",
                "action_status": None,
                "selected_indices": [],
                "option_annotations": {},
                "global_annotation": None,
            }
        selection = self.final_result.selection
        return {
            "status": self.status,
            "action_status": self.final_result.action_status,
            "selected_indices": selection.selected_indices,
            "option_annotations": selection.option_annotations,
            "global_annotation": selection.global_annotation,
        }

    def to_interaction_entry(self) -> InteractionEntry:
        """Convert this session to an InteractionEntry for the sidebar list."""
        if self.final_result:
            status = InteractionStatus.from_action_status(self.final_result.action_status)
        else:
            status = InteractionStatus.PENDING
        remaining = _remaining_seconds(self.deadline) if status == InteractionStatus.PENDING else None
        timeout_total = self.config_used.timeout_seconds if status == InteractionStatus.PENDING else None
        return InteractionEntry(
            session_id=self.choice_id,
            title=self.req.title,
            transport=self.transport,
            status=status,
            started_at=self.invocation_time,
            url=self.url,
            remaining_seconds=remaining,
            timeout_seconds=timeout_total,
        )

    def is_expired(self, now: float) -> bool:
        return (
            self.final_result is not None
            and self.completed_at is not None
            and now - self.completed_at >= 600
        )

    async def close(self) -> None:
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitor_task
        for ws in list(self.connections):
            with contextlib.suppress(Exception):
                await ws.close()
        self.connections.clear()

    async def monitor_deadline(self) -> None:
        from ..infra.logging import get_session_logger

        logger = get_session_logger(__name__, self.choice_id)
        try:
            while not self.result_future.done():
                remaining = _remaining_seconds(self.deadline)
                await self.broadcast_sync()
                if remaining <= 0:
                    from ..validation import apply_configuration

                    logger.info("Timeout reached, applying timeout action")
                    adjusted_req = apply_configuration(self.req, self.config_used)
                    response = timeout_response(req=adjusted_req, transport=TRANSPORT_WEB, url=self.url)
                    self.set_result(response)
                    await self.broadcast_status("timeout", action_status=response.action_status)
                    logger.info(f"Timeout action completed: {response.action_status}")
                    break
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.debug("Deadline monitor cancelled")
            raise
        finally:
            await self.broadcast_sync()
