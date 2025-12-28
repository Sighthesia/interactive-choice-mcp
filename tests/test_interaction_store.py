"""Tests for the interaction_store module."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.interaction_store import (
    InteractionStore,
    PersistedSession,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_MAX_SESSIONS,
)
from src.models import (
    InteractionStatus,
    ProvideChoiceOption,
    ProvideChoiceRequest,
    ProvideChoiceResponse,
    ProvideChoiceSelection,
)


# Section: Test Fixtures
@pytest.fixture
def temp_store_path(tmp_path: Path) -> Path:
    """Create a temporary directory for testing."""
    return tmp_path / "test_store"


@pytest.fixture
def store(temp_store_path: Path) -> InteractionStore:
    """Create an InteractionStore with a temporary path."""
    return InteractionStore(base_path=temp_store_path)


@pytest.fixture
def sample_request() -> ProvideChoiceRequest:
    """Create a sample ProvideChoiceRequest."""
    return ProvideChoiceRequest(
        title="Test Choice",
        prompt="Please select an option",
        selection_mode="single",
        options=[
            ProvideChoiceOption(id="opt1", description="Option 1", recommended=True),
            ProvideChoiceOption(id="opt2", description="Option 2"),
        ],
        timeout_seconds=300,
    )


@pytest.fixture
def sample_response() -> ProvideChoiceResponse:
    """Create a sample ProvideChoiceResponse."""
    return ProvideChoiceResponse(
        action_status="selected",
        selection=ProvideChoiceSelection(
            selected_indices=["opt1"],
            transport="web",
            summary="ids=['opt1']",
            url="http://localhost:17863/choice/abc123",
            option_annotations={"opt1": "Good choice"},
            global_annotation="Done",
        ),
    )


# Section: PersistedSession Tests
class TestPersistedSession:
    def test_to_interaction_entry_submitted(self) -> None:
        """Test converting a submitted session to InteractionEntry."""
        session = PersistedSession(
            session_id="abc123",
            title="Test",
            prompt="Test prompt",
            transport="web",
            selection_mode="single",
            options=[],
            result={"action_status": "selected"},
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:05:00",
            url="http://localhost/test",
        )
        entry = session.to_interaction_entry()
        assert entry.session_id == "abc123"
        assert entry.status == InteractionStatus.SUBMITTED

    def test_to_interaction_entry_timeout(self) -> None:
        """Test converting a timeout session to InteractionEntry."""
        session = PersistedSession(
            session_id="def456",
            title="Test",
            prompt="Test prompt",
            transport="terminal",
            selection_mode="single",
            options=[],
            result={"action_status": "timeout_auto_submitted"},
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:05:00",
            url=None,
        )
        entry = session.to_interaction_entry()
        assert entry.status == InteractionStatus.AUTO_SUBMITTED

    def test_to_dict_roundtrip(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        original = PersistedSession(
            session_id="abc123",
            title="Test",
            prompt="Test prompt",
            transport="web",
            selection_mode="single",
            options=[{"id": "opt1", "description": "Option 1", "recommended": True}],
            result={"action_status": "selected", "selection": {}},
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:05:00",
            url="http://localhost/test",
        )
        data = original.to_dict()
        restored = PersistedSession.from_dict(data)
        assert restored.session_id == original.session_id
        assert restored.title == original.title
        assert restored.result == original.result


# Section: InteractionStore Tests
class TestInteractionStore:
    def test_load_creates_empty_index_if_missing(self, store: InteractionStore) -> None:
        """Test that load creates an empty index if no file exists."""
        store.load()
        assert len(store._index) == 0

    def test_save_and_load_session(
        self,
        store: InteractionStore,
        sample_request: ProvideChoiceRequest,
        sample_response: ProvideChoiceResponse,
    ) -> None:
        """Test saving and loading a session."""
        store.save_session(
            session_id="test123",
            req=sample_request,
            result=sample_response,
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:05:00",
            url="http://localhost/test",
            transport="web",
        )

        # Create new store and load
        new_store = InteractionStore(base_path=store._base_path)
        new_store.load()
        assert len(new_store._index) == 1
        assert new_store._index[0].session_id == "test123"

    def test_get_recent_returns_completed_only(
        self,
        store: InteractionStore,
        sample_request: ProvideChoiceRequest,
        sample_response: ProvideChoiceResponse,
    ) -> None:
        """Test that get_recent only returns completed sessions."""
        # Save completed session
        store.save_session(
            session_id="completed1",
            req=sample_request,
            result=sample_response,
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:05:00",
            url="http://localhost/test",
            transport="web",
        )

        # Save pending session (no result)
        store.save_session(
            session_id="pending1",
            req=sample_request,
            result=None,
            started_at="2025-01-01T12:10:00",
            completed_at=None,
            url="http://localhost/test2",
            transport="web",
        )

        recent = store.get_recent(limit=10)
        assert len(recent) == 1
        assert recent[0].session_id == "completed1"

    def test_get_recent_respects_limit(
        self,
        store: InteractionStore,
        sample_request: ProvideChoiceRequest,
        sample_response: ProvideChoiceResponse,
    ) -> None:
        """Test that get_recent respects the limit parameter."""
        for i in range(10):
            store.save_session(
                session_id=f"session{i:02d}",
                req=sample_request,
                result=sample_response,
                started_at=f"2025-01-01T12:{i:02d}:00",
                completed_at=f"2025-01-01T12:{i:02d}:30",
                url=f"http://localhost/test{i}",
                transport="web",
            )

        recent = store.get_recent(limit=3)
        assert len(recent) == 3

    def test_cleanup_removes_expired_sessions(
        self,
        store: InteractionStore,
        sample_request: ProvideChoiceRequest,
        sample_response: ProvideChoiceResponse,
    ) -> None:
        """Test that cleanup removes sessions older than retention period."""
        # Save old session (4 days ago)
        old_date = (datetime.now() - timedelta(days=4)).isoformat()
        store.save_session(
            session_id="old_session",
            req=sample_request,
            result=sample_response,
            started_at=old_date,
            completed_at=old_date,
            url="http://localhost/old",
            transport="web",
        )

        # Save recent session
        recent_date = datetime.now().isoformat()
        store.save_session(
            session_id="recent_session",
            req=sample_request,
            result=sample_response,
            started_at=recent_date,
            completed_at=recent_date,
            url="http://localhost/recent",
            transport="web",
        )

        removed = store.cleanup(retention_days=3)
        assert removed == 1
        assert len(store._index) == 1
        assert store._index[0].session_id == "recent_session"

    def test_max_sessions_enforced(
        self,
        temp_store_path: Path,
        sample_request: ProvideChoiceRequest,
        sample_response: ProvideChoiceResponse,
    ) -> None:
        """Test that max_sessions limit is enforced."""
        store = InteractionStore(base_path=temp_store_path, max_sessions=3)

        for i in range(5):
            store.save_session(
                session_id=f"session{i}",
                req=sample_request,
                result=sample_response,
                started_at=f"2025-01-01T12:0{i}:00",
                completed_at=f"2025-01-01T12:0{i}:30",
                url=f"http://localhost/test{i}",
                transport="web",
            )

        assert len(store._index) == 3
        # Should keep the 3 newest
        session_ids = [s.session_id for s in store._index]
        assert "session0" not in session_ids
        assert "session1" not in session_ids

    def test_get_by_id(
        self,
        store: InteractionStore,
        sample_request: ProvideChoiceRequest,
        sample_response: ProvideChoiceResponse,
    ) -> None:
        """Test retrieving a session by ID."""
        store.save_session(
            session_id="find_me",
            req=sample_request,
            result=sample_response,
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:05:00",
            url="http://localhost/test",
            transport="web",
        )

        found = store.get_by_id("find_me")
        assert found is not None
        assert found.session_id == "find_me"

        not_found = store.get_by_id("nonexistent")
        assert not_found is None

    def test_remove_session(
        self,
        store: InteractionStore,
        sample_request: ProvideChoiceRequest,
        sample_response: ProvideChoiceResponse,
    ) -> None:
        """Test removing a session by ID."""
        store.save_session(
            session_id="to_remove",
            req=sample_request,
            result=sample_response,
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:05:00",
            url="http://localhost/test",
            transport="web",
        )

        assert store.remove("to_remove") is True
        assert store.get_by_id("to_remove") is None
        assert store.remove("to_remove") is False  # Already removed
