"""Terminal hand-off session management.

Provides session storage and lifecycle management for the terminal hand-off flow.
The MCP tool creates a session and returns a launch command immediately, then
the external terminal client attaches to the session to render the UI and
submit the result.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.models import ProvideChoiceConfig, ProvideChoiceRequest, ProvideChoiceResponse

__all__ = [
    "TerminalSession",
    "TerminalSessionStore",
    "get_terminal_session_store",
]


# Section: Session Model
@dataclass
class TerminalSession:
    """Represents a pending terminal hand-off session.
    
    The session is created when the MCP tool is invoked with terminal transport,
    and the tool returns immediately with a launch command. The external terminal
    client then attaches to this session, renders the questionary UI, and posts
    the result back.
    """
    session_id: str
    req: "ProvideChoiceRequest"
    config: "ProvideChoiceConfig"
    deadline: float
    # created_at uses monotonic for deadline math; started_at is wall clock for display
    created_at: float = field(default_factory=time.monotonic)
    started_at: float = field(default_factory=time.time)
    result: Optional["ProvideChoiceResponse"] = None
    result_event: asyncio.Event = field(default_factory=asyncio.Event)
    attached: bool = False

    @property
    def is_expired(self) -> bool:
        """Check if the session has timed out."""
        return time.monotonic() > self.deadline

    @property
    def remaining_seconds(self) -> float:
        """Return seconds remaining until deadline."""
        return max(0.0, self.deadline - time.monotonic())

    @property
    def started_at_iso(self) -> str:
        """Return started_at as an ISO formatted datetime string."""
        return datetime.fromtimestamp(self.started_at).strftime("%Y-%m-%d %H:%M:%S")

    def set_result(self, response: "ProvideChoiceResponse") -> bool:
        """Set the session result. Returns False if already set."""
        if self.result is not None:
            return False
        self.result = response
        self.result_event.set()
        return True

    def to_interaction_entry(self) -> "InteractionEntry":
        """Convert this session to an InteractionEntry for the sidebar list."""
        from ..models import InteractionEntry, InteractionStatus, TRANSPORT_TERMINAL
        if self.result:
            status = InteractionStatus.from_action_status(self.result.action_status)
        else:
            status = InteractionStatus.PENDING
        remaining = self.remaining_seconds if status == InteractionStatus.PENDING else None
        timeout_total = self.config.timeout_seconds if status == InteractionStatus.PENDING else None
        return InteractionEntry(
            session_id=self.session_id,
            title=self.req.title,
            transport=TRANSPORT_TERMINAL,
            status=status,
            started_at=self.started_at_iso,
            url=None,
            remaining_seconds=remaining,
            timeout_seconds=timeout_total,
        )

    async def wait_for_result(self, timeout: Optional[float] = None) -> Optional["ProvideChoiceResponse"]:
        """Wait for the result to be set, with optional timeout."""
        effective_timeout = timeout if timeout is not None else self.remaining_seconds
        try:
            await asyncio.wait_for(self.result_event.wait(), timeout=effective_timeout)
            return self.result
        except asyncio.TimeoutError:
            return None


# Section: Session Store
class TerminalSessionStore:
    """Thread-safe storage for terminal hand-off sessions.
    
    Manages the lifecycle of sessions including creation, retrieval, result
    submission, and cleanup of expired sessions.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, TerminalSession] = {}
        self._cleanup_task: Optional[asyncio.Task[None]] = None

    def create_session(
        self,
        req: "ProvideChoiceRequest",
        config: "ProvideChoiceConfig",
        timeout_seconds: int,
    ) -> TerminalSession:
        """Create a new terminal session and return it."""
        session_id = uuid.uuid4().hex[:12]
        deadline = time.monotonic() + max(1, timeout_seconds)
        session = TerminalSession(
            session_id=session_id,
            req=req,
            config=config,
            deadline=deadline,
        )
        self._sessions[session_id] = session
        self._ensure_cleanup_running()
        return session

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Retrieve a session by ID, or None if not found or expired."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired and session.result is None:
            # Expired without result - clean it up
            self._sessions.pop(session_id, None)
            return None
        return session

    def remove_session(self, session_id: str) -> None:
        """Remove a session from the store."""
        self._sessions.pop(session_id, None)

    def _ensure_cleanup_running(self) -> None:
        """Ensure the background cleanup task is running."""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_loop())
            except RuntimeError:
                # No running loop - cleanup will happen on next access
                pass

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired sessions."""
        while True:
            await asyncio.sleep(30)
            now = time.monotonic()
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired and session.result is not None
            ]
            # Keep sessions with results for a grace period (60s) for polling
            for sid in list(self._sessions.keys()):
                session = self._sessions.get(sid)
                if session is None:
                    continue
                if session.result is not None:
                    # Result set - keep for 60s after completion
                    if now - session.created_at > session.config.timeout_seconds + 60:
                        self._sessions.pop(sid, None)
                elif session.is_expired:
                    # No result and expired - remove
                    self._sessions.pop(sid, None)


# Section: Global Instance
_TERMINAL_SESSION_STORE: Optional[TerminalSessionStore] = None


def get_terminal_session_store() -> TerminalSessionStore:
    """Get or create the global terminal session store."""
    global _TERMINAL_SESSION_STORE
    if _TERMINAL_SESSION_STORE is None:
        _TERMINAL_SESSION_STORE = TerminalSessionStore()
    return _TERMINAL_SESSION_STORE
