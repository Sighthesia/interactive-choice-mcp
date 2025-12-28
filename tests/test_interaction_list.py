"""Tests for the interaction list functionality."""
import pytest

from choice.models import InteractionEntry, InteractionStatus, TRANSPORT_WEB, TRANSPORT_TERMINAL


# Section: InteractionStatus Tests
class TestInteractionStatus:
    """Tests for InteractionStatus enum and conversion."""

    def test_from_action_status_selected(self):
        assert InteractionStatus.from_action_status("selected") == InteractionStatus.SUBMITTED

    def test_from_action_status_cancelled(self):
        assert InteractionStatus.from_action_status("cancelled") == InteractionStatus.CANCELLED

    def test_from_action_status_timeout(self):
        assert InteractionStatus.from_action_status("timeout") == InteractionStatus.TIMEOUT

    def test_from_action_status_timeout_auto_submitted(self):
        assert InteractionStatus.from_action_status("timeout_auto_submitted") == InteractionStatus.AUTO_SUBMITTED

    def test_from_action_status_timeout_cancelled(self):
        assert InteractionStatus.from_action_status("timeout_cancelled") == InteractionStatus.TIMEOUT

    def test_from_action_status_pending_terminal_launch(self):
        # pending_terminal_launch should be treated as pending
        assert InteractionStatus.from_action_status("pending_terminal_launch") == InteractionStatus.PENDING

    def test_from_action_status_unknown(self):
        # Unknown status should default to pending
        assert InteractionStatus.from_action_status("unknown") == InteractionStatus.PENDING


# Section: InteractionEntry Tests
class TestInteractionEntry:
    """Tests for InteractionEntry dataclass."""

    def test_to_dict_web_session(self):
        entry = InteractionEntry(
            session_id="abc123",
            title="Test Choice",
            transport=TRANSPORT_WEB,
            status=InteractionStatus.PENDING,
            started_at="2025-12-28 10:00:00",
            url="http://localhost:17863/choice/abc123",
        )
        result = entry.to_dict()
        assert result == {
            "session_id": "abc123",
            "title": "Test Choice",
            "transport": "web",
            "status": "pending",
            "started_at": "2025-12-28 10:00:00",
            "url": "http://localhost:17863/choice/abc123",
        }

    def test_to_dict_terminal_session(self):
        entry = InteractionEntry(
            session_id="def456",
            title="Terminal Choice",
            transport=TRANSPORT_TERMINAL,
            status=InteractionStatus.SUBMITTED,
            started_at="2025-12-28 11:00:00",
            url=None,
        )
        result = entry.to_dict()
        assert result == {
            "session_id": "def456",
            "title": "Terminal Choice",
            "transport": "terminal",
            "status": "submitted",
            "started_at": "2025-12-28 11:00:00",
            "url": None,
        }

    def test_to_dict_completed_statuses(self):
        for status in [InteractionStatus.SUBMITTED, InteractionStatus.AUTO_SUBMITTED,
                       InteractionStatus.CANCELLED, InteractionStatus.TIMEOUT]:
            entry = InteractionEntry(
                session_id="test",
                title="Test",
                transport=TRANSPORT_WEB,
                status=status,
                started_at="2025-12-28 12:00:00",
            )
            result = entry.to_dict()
            assert result["status"] == status.value


# Section: Session to InteractionEntry Conversion Tests
class TestSessionToInteractionEntry:
    """Tests for session conversion to InteractionEntry."""

    def test_web_session_to_interaction_entry_pending(self):
        """Test ChoiceSession.to_interaction_entry for pending session."""
        # Import here to avoid circular imports in test collection
        import asyncio
        from choice.web.session import ChoiceSession
        from choice.models import ProvideChoiceRequest, ProvideChoiceConfig, ProvideChoiceOption

        req = ProvideChoiceRequest(
            title="Web Test",
            prompt="Choose an option",
            selection_mode="single",
            options=[ProvideChoiceOption(id="A", description="Option A", recommended=True)],
            timeout_seconds=300,
        )
        config = ProvideChoiceConfig(transport=TRANSPORT_WEB, timeout_seconds=300)
        loop = asyncio.new_event_loop()
        result_future = loop.create_future()

        session = ChoiceSession(
            choice_id="web123",
            req=req,
            defaults=config,
            allow_terminal=False,
            url="http://localhost:17863/choice/web123",
            deadline=100.0,
            result_future=result_future,
            connections=set(),
            config_used=config,
            created_at=0.0,
            invocation_time="2025-12-28 10:00:00",
        )

        entry = session.to_interaction_entry()
        assert entry.session_id == "web123"
        assert entry.title == "Web Test"
        assert entry.transport == TRANSPORT_WEB
        assert entry.status == InteractionStatus.PENDING
        assert entry.url == "http://localhost:17863/choice/web123"

        loop.close()

    def test_terminal_session_to_interaction_entry(self):
        """Test TerminalSession.to_interaction_entry."""
        from choice.terminal.session import TerminalSession
        from choice.models import ProvideChoiceRequest, ProvideChoiceConfig, ProvideChoiceOption

        req = ProvideChoiceRequest(
            title="Terminal Test",
            prompt="Choose",
            selection_mode="single",
            options=[ProvideChoiceOption(id="B", description="Option B", recommended=False)],
            timeout_seconds=60,
        )
        config = ProvideChoiceConfig(transport=TRANSPORT_TERMINAL, timeout_seconds=60)

        session = TerminalSession(
            session_id="term456",
            req=req,
            config=config,
            deadline=100.0,
        )

        entry = session.to_interaction_entry()
        assert entry.session_id == "term456"
        assert entry.title == "Terminal Test"
        assert entry.transport == TRANSPORT_TERMINAL
        assert entry.status == InteractionStatus.PENDING
        assert entry.url is None
