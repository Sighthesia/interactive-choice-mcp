"""Session lifecycle and timeout helpers for web interactions."""
from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, Set, TYPE_CHECKING

from ..models import (
    ProvideChoiceConfig,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    TRANSPORT_WEB,
)
from ..response import timeout_response

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
        if self.result_future.done():
            return False
        self.final_result = response
        self.status = _status_label(response.action_status)
        self.result_future.set_result(response)
        self.completed_at = time.monotonic()
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
        from ..logging import get_session_logger

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
