"""Persistent storage for completed interaction sessions.

This module provides the InteractionStore class which manages:
- Persisting completed sessions to local JSON files
- Loading historical sessions on startup
- Automatic cleanup based on retention policies
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..infra import get_logger
from ..infra.paths import get_sessions_dir
from ..core.models import InteractionEntry, InteractionStatus

if TYPE_CHECKING:
    from ..core.models import ProvideChoiceRequest, ProvideChoiceResponse

__all__ = [
    "InteractionStore",
    "PersistedSession",
    "DEFAULT_RETENTION_DAYS",
    "DEFAULT_MAX_SESSIONS",
]

_logger = get_logger(__name__)

# Section: Constants
DEFAULT_RETENTION_DAYS = 3
DEFAULT_MAX_SESSIONS = 100


# Section: Persisted Session Model
@dataclass
class PersistedSession:
    """Complete session data for persistence.

    Contains all information needed to reconstruct a session's history,
    including the original request, final result, and timing information.
    """
    session_id: str
    title: str
    prompt: str
    interface: str
    selection_mode: str
    options: list[dict]  # List of option dicts
    result: Optional[dict]  # ProvideChoiceResponse as dict
    started_at: str  # ISO 8601
    completed_at: Optional[str]  # ISO 8601
    timeout_seconds: Optional[int] = None
    url: Optional[str] = None

    def to_interaction_entry(self) -> InteractionEntry:
        """Convert to an InteractionEntry for the sidebar list."""
        if self.result:
            status = InteractionStatus.from_action_status(
                self.result.get("action_status", "pending")
            )
        else:
            status = InteractionStatus.PENDING
        return InteractionEntry(
            session_id=self.session_id,
            title=self.title,
            interface=self.interface,
            status=status,
            started_at=self.started_at,
            url=self.url,
        )

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary."""
        return {
            "version": 1,
            "session_id": self.session_id,
            "title": self.title,
            "prompt": self.prompt,
            "interface": self.interface,
            "selection_mode": self.selection_mode,
            "options": self.options,
            "result": self.result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "timeout_seconds": self.timeout_seconds,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersistedSession":
        """Create a PersistedSession from a dictionary."""
        return cls(
            session_id=data["session_id"],
            title=data["title"],
            prompt=data["prompt"],
            interface=data["interface"],
            selection_mode=data["selection_mode"],
            options=data.get("options", []),
            result=data.get("result"),
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            timeout_seconds=data.get("timeout_seconds"),
            url=data.get("url"),
        )


# Section: Interaction Store
class InteractionStore:
    """Persistent storage for completed interaction sessions.

    Stores sessions as individual JSON files with an index file for quick lookup.
    Supports automatic cleanup based on retention days and maximum session count.
    """

    def __init__(
        self,
        *,
        base_path: Optional[Path] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        self._base_path = base_path or get_sessions_dir()
        self._sessions_path = self._base_path
        self._index_path = self._sessions_path / "index.json"
        self._retention_days = retention_days
        self._max_sessions = max_sessions
        self._index: list[PersistedSession] = []
        self._loaded = False

    def _ensure_dirs(self) -> None:
        """Ensure storage directories exist."""
        self._sessions_path.mkdir(parents=True, exist_ok=True)

    def load(self) -> None:
        """Load session index from disk.

        Should be called once at startup. If the index file doesn't exist
        or is corrupted, starts with an empty index.
        """
        self._index = []
        self._loaded = True

        if not self._index_path.exists():
            _logger.debug("No session index found, starting fresh")
            return

        try:
            data = json.loads(self._index_path.read_text())
            if not isinstance(data, dict) or "sessions" not in data:
                _logger.warning("Invalid index format, starting fresh")
                return

            for entry in data.get("sessions", []):
                try:
                    session = PersistedSession.from_dict(entry)
                    self._index.append(session)
                except Exception as e:
                    _logger.warning(f"Skipping invalid session entry: {e}")

            _logger.info(f"Loaded {len(self._index)} persisted sessions")
        except Exception as e:
            _logger.warning(f"Failed to load session index: {e}")

    def _save_index(self) -> None:
        """Save the session index to disk."""
        self._ensure_dirs()
        payload = {
            "version": 1,
            "sessions": [s.to_dict() for s in self._index],
        }
        temp_path = self._index_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, indent=2))
        temp_path.replace(self._index_path)

    def save_session(
        self,
        *,
        session_id: str,
        req: "ProvideChoiceRequest",
        result: Optional["ProvideChoiceResponse"],
        started_at: str,
        completed_at: Optional[str],
        url: Optional[str],
        interface: str,
    ) -> None:
        """Persist a completed session.

        Args:
            session_id: Unique session identifier
            req: The original choice request
            result: The final response (if completed)
            started_at: ISO 8601 start time
            completed_at: ISO 8601 completion time (if completed)
            url: Web URL for the session (if applicable)
            interface: "web" or "terminal"
        """
        if not self._loaded:
            self.load()

        # Convert request to serializable format
        options = [
            {"id": o.id, "description": o.description, "recommended": o.recommended}
            for o in req.options
        ]

        # Convert result to serializable format
        result_dict = None
        if result:
            result_dict = {
                "action_status": result.action_status,
                "selection": {
                    "selected_indices": result.selection.selected_indices,
                    "interface": result.selection.interface,
                    "summary": result.selection.summary,
                    "url": result.selection.url,
                    "option_annotations": result.selection.option_annotations,
                    "additional_annotation": result.selection.additional_annotation,
                },
            }

        # Use relative URL to avoid stale host/port when rendering historical entries
        stored_url = None
        stored_timeout = req.timeout_seconds if hasattr(req, "timeout_seconds") else None
        if interface == "web":
            stored_url = f"/choice/{session_id}"
        elif url:
            stored_url = url

        session = PersistedSession(
            session_id=session_id,
            title=req.title,
            prompt=req.prompt,
            interface=interface,
            selection_mode=req.selection_mode,
            options=options,
            result=result_dict,
            started_at=started_at,
            completed_at=completed_at,
            timeout_seconds=stored_timeout,
            url=stored_url,
        )

        # Remove existing entry with same ID (update case)
        self._index = [s for s in self._index if s.session_id != session_id]
        self._index.append(session)

        # Enforce max sessions limit
        self._enforce_max_sessions()

        self._save_index()
        _logger.debug(f"Saved session {session_id[:8]}")

    def _enforce_max_sessions(self) -> None:
        """Remove oldest sessions if over max limit."""
        if len(self._index) <= self._max_sessions:
            return

        # Sort by completed_at (oldest first), then by started_at
        def sort_key(s: PersistedSession) -> str:
            return s.completed_at or s.started_at

        self._index.sort(key=sort_key)
        excess = len(self._index) - self._max_sessions
        removed = self._index[:excess]
        self._index = self._index[excess:]
        _logger.info(f"Removed {len(removed)} oldest sessions to enforce limit")

    def get_recent(self, limit: int = 5) -> list[InteractionEntry]:
        """Get most recent completed sessions for the sidebar.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of InteractionEntry objects, newest first
        """
        if not self._loaded:
            self.load()

        # Filter to completed sessions only
        completed = [s for s in self._index if s.result is not None]

        # Sort by completed_at descending
        def sort_key(s: PersistedSession) -> str:
            return s.completed_at or s.started_at

        completed.sort(key=sort_key, reverse=True)

        return [s.to_interaction_entry() for s in completed[:limit]]

    def cleanup(self, retention_days: Optional[int] = None) -> int:
        """Remove expired sessions.

        Args:
            retention_days: Override default retention period

        Returns:
            Number of sessions removed
        """
        if not self._loaded:
            self.load()

        days = retention_days if retention_days is not None else self._retention_days
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        original_count = len(self._index)
        self._index = [
            s for s in self._index
            if (s.completed_at or s.started_at) >= cutoff_str
        ]
        removed = original_count - len(self._index)

        if removed > 0:
            self._save_index()
            _logger.info(f"Cleaned up {removed} expired sessions (>{days} days old)")

        return removed

    def get_by_id(self, session_id: str) -> Optional[PersistedSession]:
        """Get a specific session by ID.

        Args:
            session_id: The session ID to look up

        Returns:
            PersistedSession if found, None otherwise
        """
        if not self._loaded:
            self.load()

        for s in self._index:
            if s.session_id == session_id:
                return s
        return None

    def remove(self, session_id: str) -> bool:
        """Remove a session by ID.

        Args:
            session_id: The session ID to remove

        Returns:
            True if removed, False if not found
        """
        if not self._loaded:
            self.load()

        original_count = len(self._index)
        self._index = [s for s in self._index if s.session_id != session_id]

        if len(self._index) < original_count:
            self._save_index()
            return True
        return False


# Section: Singleton Instance
_STORE: Optional[InteractionStore] = None


def get_interaction_store() -> InteractionStore:
    """Get the singleton InteractionStore instance."""
    global _STORE
    if _STORE is None:
        _STORE = InteractionStore()
    return _STORE
