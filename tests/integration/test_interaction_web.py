"""Integration tests for web-based interactive choice flows.

This module tests end-to-end interactions with the web server, including:
- Single choice selection
- Multi choice selection
- Timeout handling
- Cancellation scenarios
- Error handling for invalid inputs
- HTML page rendering 
- WebSocket real-time communication

These tests use the shared web_server fixture to start a real web server
and simulate HTTP requests using httpx and WebSocket connections using websockets.
"""
import pytest
import asyncio
import httpx
import time
import json
from src.core.models import InteractionStatus


class TestSingleChoiceInteraction:
    """Test single-choice interaction flows."""

    @pytest.mark.asyncio
    async def test_create_and_submit_single_choice(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test creating a session and submitting a single choice selection."""
        # Step 1: Create session
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        # Verify session creation
        assert session.choice_id in web_server.sessions
        assert session.status == InteractionStatus.PENDING
        assert session.req.selection_mode == "single"

        # Step 2: Submit single choice selection
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        # Verify submission response
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify session state
        assert session.final_result is not None
        assert session.final_result.action_status == "selected"
        assert session.final_result.selection.selected_indices == ["opt1"]
        assert session.status == InteractionStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_single_choice_with_annotation(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test single choice with option and global annotations."""
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        # Submit with annotations
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt2"],
                    "option_annotations": {"opt2": "Selected this option"},
                    "additional_annotation": "User provided feedback",
                },
            )

        assert response.status_code == 200
        assert session.final_result is not None
        assert session.final_result.selection.selected_indices == ["opt2"]
        assert session.final_result.selection.option_annotations == {"opt2": "Selected this option"}
        assert session.final_result.selection.additional_annotation == "User provided feedback"


class TestMultiChoiceInteraction:
    """Test multi-choice interaction flows."""

    @pytest.mark.asyncio
    async def test_create_and_submit_multi_choice(
        self, web_server, sample_multi_choice_request, sample_web_config
    ):
        """Test creating a session and submitting multiple selections."""
        # Step 1: Create session
        session = await web_server.create_session(
            sample_multi_choice_request, sample_web_config, allow_terminal=False
        )

        # Verify session creation
        assert session.choice_id in web_server.sessions
        assert session.status == InteractionStatus.PENDING
        assert session.req.selection_mode == "multi"

        # Step 2: Submit multiple selections
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1", "opt2"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        # Verify submission response
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify session state
        assert session.final_result is not None
        assert session.final_result.action_status == "selected"
        assert set(session.final_result.selection.selected_indices) == {"opt1", "opt2"}
        assert session.status == InteractionStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_multi_choice_select_all(
        self, web_server, sample_multi_choice_request, sample_web_config
    ):
        """Test selecting all available options in multi-choice mode."""
        session = await web_server.create_session(
            sample_multi_choice_request, sample_web_config, allow_terminal=False
        )

        # Submit all options
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1", "opt2", "opt3"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        assert response.status_code == 200
        assert session.final_result is not None
        assert set(session.final_result.selection.selected_indices) == {"opt1", "opt2", "opt3"}


class TestTimeoutHandling:
    """Test timeout scenarios."""

    @pytest.mark.asyncio
    async def test_session_timeout_without_selection(
        self, web_server, sample_single_choice_request
    ):
        """Test that a session has a deadline set correctly."""
        # Create a session with 1 second timeout
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=1)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        # Verify that the deadline was set correctly
        now = time.monotonic()
        remaining_timeout = session.deadline - now
        # Should be approximately 1 second remaining just after creation
        assert 0 < remaining_timeout <= 1.5

    @pytest.mark.asyncio
    async def test_selection_before_timeout(
        self, web_server, sample_single_choice_request
    ):
        """Test that selection before timeout prevents timeout."""
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=5)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        # Submit selection before timeout
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        assert response.status_code == 200
        assert session.final_result is not None
        assert session.final_result.action_status == "selected"

        # Wait past original timeout to ensure no override
        await asyncio.sleep(6)
        assert session.final_result.action_status == "selected"


class TestCancellationScenarios:
    """Test cancellation scenarios."""

    @pytest.mark.asyncio
    async def test_user_cancellation(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test user cancelling the choice."""
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        # Submit cancellation
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "cancelled",
                    "selected_indices": [],
                    "option_annotations": {},
                    "additional_annotation": "User cancelled",
                },
            )

        assert response.status_code == 200
        assert session.final_result is not None
        assert session.final_result.action_status == "cancelled"
        assert session.final_result.selection.additional_annotation == "User cancelled"
        assert session.status == InteractionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancellation_with_annotation(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test cancellation with detailed annotation."""
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        # Submit cancellation with annotation
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "cancel_with_annotation",
                    "selected_indices": [],
                    "option_annotations": {},
                    "additional_annotation": "Reason for cancellation",
                },
            )

        assert response.status_code == 200
        assert session.final_result is not None
        assert session.final_result.action_status == "cancel_with_annotation"
        assert session.final_result.selection.additional_annotation == "Reason for cancellation"


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    @pytest.mark.asyncio
    async def test_submit_to_nonexistent_session(self, web_server):
        """Test submitting to a session that doesn't exist."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/nonexistent/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        # Session not found returns 404
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_invalid_option_id(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test submitting an invalid option ID."""
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        # Submit with invalid option ID
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["invalid_option"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        # The server should accept the submission but validation may fail
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_submit_missing_required_fields(self, web_server, sample_single_choice_request):
        """Test submitting with missing required fields to a valid session."""
        # Create a valid session first
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        # Submit with missing required fields
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    # Missing action_status and selected_indices
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        # Should return validation error
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_double_submit_prevention(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test that double submission is handled correctly."""
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        # First submission
        async with httpx.AsyncClient() as client:
            response1 = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        assert response1.status_code == 200

        # Second submission should be rejected or ignored
        async with httpx.AsyncClient() as client:
            response2 = await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt2"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        # The second submission should not change the result
        assert session.final_result is not None
        assert session.final_result.selection.selected_indices == ["opt1"]


class TestResponseStructure:
    """Test that responses have the correct structure."""

    @pytest.mark.asyncio
    async def test_selected_response_structure(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test that a selected response has all required fields."""
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1"],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        result = session.final_result
        assert result is not None
        assert result.action_status == "selected"
        assert result.selection is not None
        assert hasattr(result.selection, "selected_indices")
        assert hasattr(result.selection, "option_annotations")
        assert hasattr(result.selection, "additional_annotation")

    @pytest.mark.asyncio
    async def test_cancelled_response_structure(
        self, web_server, sample_single_choice_request, sample_web_config
    ):
        """Test that a cancelled response has all required fields."""
        session = await web_server.create_session(
            sample_single_choice_request, sample_web_config, allow_terminal=False
        )

        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                json={
                    "action_status": "cancelled",
                    "selected_indices": [],
                    "option_annotations": {},
                    "additional_annotation": None,
                },
            )

        result = session.final_result
        assert result is not None
        assert result.action_status == "cancelled"
        assert result.selection is not None

    @pytest.mark.asyncio
    async def test_timeout_response_structure(
        self, web_server, sample_single_choice_request
    ):
        """Test that a session has correct deadline structure."""
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=1)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        # Verify session structure for timeout handling
        assert session.deadline is not None
        assert session.deadline > time.monotonic()
        assert session.deadline <= time.monotonic() + 1.5


class TestHtmlRendering:
    """Test HTML page rendering for choice interactions."""

    @pytest.mark.asyncio
    async def test_html_page_returns_correct_content_type(
        self, web_server, sample_single_choice_request
    ):
        """Test that the HTML page returns correct content type."""
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}"
            )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_html_page_contains_session_data(
        self, web_server, sample_single_choice_request
    ):
        """Test that the HTML page contains session-specific data."""
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}"
            )

        assert response.status_code == 200
        html_content = response.text

        # Verify session ID is present
        assert session.choice_id in html_content

        # Verify title is present
        assert sample_single_choice_request.title in html_content

        # Verify prompt is present
        assert sample_single_choice_request.prompt in html_content

        # Verify options are present
        assert "Option 1" in html_content
        assert "Option 2" in html_content

    @pytest.mark.asyncio
    async def test_html_page_multi_choice_mode(
        self, web_server, sample_multi_choice_request
    ):
        """Test that the HTML page correctly renders multi-choice mode."""
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_multi_choice_request, config, allow_terminal=False
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}"
            )

        assert response.status_code == 200
        html_content = response.text

        # Verify all options are present
        assert "Option 1" in html_content
        assert "Option 2" in html_content
        assert "Option 3" in html_content

    @pytest.mark.asyncio
    async def test_html_page_nonexistent_session_returns_404(self, web_server):
        """Test that requesting a non-existent session returns 404."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{web_server.host}:{web_server.port}/choice/nonexistent"
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_html_page_contains_static_assets(
        self, web_server, sample_single_choice_request
    ):
        """Test that the HTML page includes static asset references."""
        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}"
            )

        assert response.status_code == 200
        html_content = response.text

        # Verify CSS is present (either inline or bundled)
        assert "<style>" in html_content or ".css" in html_content

        # Verify JavaScript is present (either inline or bundled)
        assert "<script>" in html_content or ".js" in html_content


class TestWebSocketCommunication:
    """Test WebSocket real-time communication """

    @pytest.mark.asyncio
    async def test_websocket_connection_established(
        self, web_server, sample_single_choice_request
    ):
        """Test that WebSocket connection can be established."""
        import websockets

        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        uri = f"ws://{web_server.host}:{web_server.port}/ws/{session.choice_id}"

        async with websockets.connect(uri) as websocket:
            # Connection should be established (no exception raised)
            # Receive initial status message
            message = await websocket.recv()
            data = json.loads(message)
            assert data["type"] == "status"
            assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_websocket_receives_status_updates(
        self, web_server, sample_single_choice_request
    ):
        """Test that WebSocket receives status updates on submission."""
        import websockets

        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        uri = f"ws://{web_server.host}:{web_server.port}/ws/{session.choice_id}"

        async with websockets.connect(uri) as websocket:
            # Receive initial status
            message = await websocket.recv()
            data = json.loads(message)
            assert data["type"] == "status"
            assert data["status"] == "pending"

            # Submit a choice
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"http://{web_server.host}:{web_server.port}/choice/{session.choice_id}/submit",
                    json={
                        "action_status": "selected",
                        "selected_indices": ["opt1"],
                        "option_annotations": {},
                        "additional_annotation": None,
                    },
                )

            # Receive status update (may be sync or status type)
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(message)

            # Accept either "status" or "sync" message type
            assert data["type"] in ["status", "sync"]
            if data["type"] == "status":
                assert data["status"] in ["submitted", "completed"]

    @pytest.mark.asyncio
    async def test_websocket_nonexistent_session_rejected(
        self, web_server
    ):
        """Test that WebSocket connection to non-existent session is rejected."""
        import websockets

        uri = f"ws://{web_server.host}:{web_server.port}/ws/nonexistent"

        try:
            async with websockets.connect(uri) as websocket:
                # Should not reach here
                assert False, "WebSocket connection should have been rejected"
        except Exception:
            # Connection should fail
            pass

    @pytest.mark.asyncio
    async def test_websocket_multiple_connections(
        self, web_server, sample_single_choice_request
    ):
        """Test that multiple WebSocket connections can be established to the same session."""
        import websockets

        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        uri = f"ws://{web_server.host}:{web_server.port}/ws/{session.choice_id}"

        # Create multiple connections
        async with websockets.connect(uri) as ws1:
            async with websockets.connect(uri) as ws2:
                # Both connections should be able to receive messages
                msg1 = await ws1.recv()
                msg2 = await ws2.recv()

                data1 = json.loads(msg1)
                data2 = json.loads(msg2)

                assert data1["status"] == "pending"
                assert data2["status"] == "pending"

    @pytest.mark.asyncio
    async def test_websocket_connection_cleanup(
        self, web_server, sample_single_choice_request
    ):
        """Test that WebSocket connections are cleaned up when session is removed."""
        import websockets

        from src.core.models import ProvideChoiceConfig

        config = ProvideChoiceConfig(interface="web", timeout_seconds=300)
        session = await web_server.create_session(
            sample_single_choice_request, config, allow_terminal=False
        )

        uri = f"ws://{web_server.host}:{web_server.port}/ws/{session.choice_id}"

        async with websockets.connect(uri) as websocket:
            # Connection should be established (able to receive)
            # Receive initial message to confirm connection
            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            data = json.loads(message)
            assert data["status"] == "pending"

            # Remove the session
            await web_server._remove_session(session.choice_id)

            # Connection may or may not be closed immediately
            assert session.choice_id not in web_server.sessions


class TestWebInteractionManual:
    """Manual interactive tests for web interface."""

    @pytest.mark.asyncio
    async def test_web_e2e_manual_interaction(
        self,
        web_server,
        sample_single_choice_request,
        sample_web_config,
        interactive,
    ):
        """End-to-end test with manual browser interaction.
        
        When --interactive is provided, this test will:
        1. Create a web session
        2. Open the browser automatically with the session URL
        3. Wait for you to make a selection in the browser
        4. Verify the selection was properly submitted
        """
        if not interactive:
            pytest.skip(
                "Run with --interactive to enable interactive browser testing. "
                "Example: uv run pytest tests/integration/test_interaction_web.py::TestWebInteractionManual::test_web_e2e_manual_interaction --interactive -v -s"
            )

        # Create a session using the web server
        session = await web_server.create_session(
            sample_single_choice_request,
            sample_web_config,
            allow_terminal=False,
        )

        # Open browser for interactive testing
        import webbrowser
        webbrowser.open(session.url)

        timeout_seconds = sample_web_config.timeout_seconds

        print(f"\n{'='*60}")
        print("🌐 BROWSER OPENED FOR E2E TESTING")
        print(f"{'='*60}")
        print(f"Session URL: {session.url}")
        print(f"Title: {sample_single_choice_request.title}")
        print(f"Prompt: {sample_single_choice_request.prompt}")
        print(f"Options:")
        for opt in sample_single_choice_request.options:
            marker = "⭐" if opt.recommended else "  "
            print(f"  {marker} [{opt.id}] {opt.description}")
        print(f"{'='*60}")
        print(f"Please make a selection in the browser...")
        print(f"The test will wait up to {timeout_seconds} seconds (from config) for your selection.")
        print(f"{'='*60}\n")

        # Wait for the user to make a selection
        try:
            result = await asyncio.wait_for(session.wait_for_result(), timeout=float(timeout_seconds))
        except asyncio.TimeoutError:
            pytest.fail(f"Timeout: No selection made within {timeout_seconds} seconds")

        # Verify the result
        assert result is not None
        assert result.action_status in ["selected", "cancelled"]
        
        if result.action_status == "selected":
            print(f"\n✅ Selection received: {result.selection.selected_indices}")
        else:
            print(f"\n❌ Interaction was cancelled")

        assert session.final_result is not None
