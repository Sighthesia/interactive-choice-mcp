"""Integration tests for terminal-based interactive choice flows.

This module tests terminal hand-off launch flow and end-to-end selection.
"""
import pytest
import asyncio
import httpx
from src.web.server import create_terminal_handoff_session, poll_session_result


class TestTerminalHandOff:
    """Test terminal hand-off launch flow and end-to-end selection."""

    @pytest.mark.asyncio
    async def test_terminal_handoff_launch_command(
        self,
        web_server,
        sample_single_choice_request,
        sample_terminal_config,
    ):
        response = await create_terminal_handoff_session(
            sample_single_choice_request,
            sample_terminal_config,
        )

        assert response.action_status == "pending_terminal_launch"
        selection_url = response.selection.url or ""
        session_id = selection_url.rstrip("/").split("/")[-1]
        assert session_id
        assert f"/terminal/{session_id}" in selection_url
        assert "uv run python -m src.terminal.client" in response.selection.summary
        assert str(web_server.port) in response.selection.summary

    @pytest.mark.asyncio
    async def test_terminal_handoff_end_to_end(
        self,
        web_server,
        sample_single_choice_request,
        sample_terminal_config,
    ):

        # Use a longer timeout for this test to avoid timeout during submission
        from src.core.models import ProvideChoiceConfig
        test_config = ProvideChoiceConfig(
            interface=sample_terminal_config.interface,
            timeout_seconds=60,  # Use fixed 60s timeout for this test
            single_submit_mode=sample_terminal_config.single_submit_mode,
            timeout_default_index=sample_terminal_config.timeout_default_index,
            timeout_default_enabled=sample_terminal_config.timeout_default_enabled,
            use_default_option=sample_terminal_config.use_default_option,
            timeout_action=sample_terminal_config.timeout_action,
            language=sample_terminal_config.language,
            notify_new=sample_terminal_config.notify_new,
            notify_upcoming=sample_terminal_config.notify_upcoming,
            upcoming_threshold=sample_terminal_config.upcoming_threshold,
            notify_timeout=sample_terminal_config.notify_timeout,
            notify_trigger_mode=sample_terminal_config.notify_trigger_mode,
            notify_sound=sample_terminal_config.notify_sound,
            notify_sound_path=sample_terminal_config.notify_sound_path,
        )

        response = await create_terminal_handoff_session(
            sample_single_choice_request,
            test_config,
        )
        selection_url = response.selection.url or ""
        session_id = selection_url.rstrip("/").split("/")[-1]

        async with httpx.AsyncClient(timeout=30.0) as client:
            submit_response = await client.post(
                f"http://{web_server.host}:{web_server.port}/terminal/{session_id}/submit",
                json={
                    "action_status": "selected",
                    "selected_indices": ["opt1"],
                    "option_annotations": {"opt1": "terminal selection"},
                    "additional_annotation": "terminal user",
                    "config": {
                        "interface": test_config.interface,
                        "timeout_seconds": test_config.timeout_seconds,
                        "single_submit_mode": test_config.single_submit_mode,
                    },
                },
            )

        assert submit_response.status_code == 200

        final_result = await poll_session_result(session_id)
        if final_result is None:
            await asyncio.sleep(0.1)
            final_result = await poll_session_result(session_id)

        assert final_result is not None
        assert final_result.action_status == "selected"
        assert final_result.selection.selected_indices == ["opt1"]


class TestTerminalInteractionManual:
    """Manual interactive tests for terminal interface."""

    @pytest.mark.asyncio
    async def test_terminal_e2e_manual_interaction(
        self,
        web_server,
        sample_single_choice_request,
        sample_terminal_config,
        interactive,
    ):
        """End-to-end test with manual terminal interaction.
        
        When --interactive is provided, this test will:
        1. Create a terminal hand-off session
        2. Display the terminal command to run
        3. Wait for you to execute the command and make a selection
        4. Verify the selection was properly submitted
        """
        if not interactive:
            pytest.skip(
                "Run with --interactive to enable interactive terminal testing. "
                "Example: uv run pytest tests/integration/test_interaction_terminal.py::TestTerminalInteractionManual::test_terminal_e2e_manual_interaction --interactive -v -s"
            )

        # Create a terminal hand-off session
        response = await create_terminal_handoff_session(
            sample_single_choice_request,
            sample_terminal_config,
        )

        selection_url = response.selection.url or ""
        session_id = selection_url.rstrip("/").split("/")[-1]
        launch_command = response.selection.summary
        timeout_seconds = sample_terminal_config.timeout_seconds

        print(f"\n{'='*60}")
        print("💻 TERMINAL COMMAND FOR E2E TESTING")
        print(f"{'='*60}")
        print(f"Session ID: {session_id}")
        print(f"Title: {sample_single_choice_request.title}")
        print(f"Prompt: {sample_single_choice_request.prompt}")
        print(f"Options:")
        for opt in sample_single_choice_request.options:
            marker = "⭐" if opt.recommended else "  "
            print(f"  {marker} [{opt.id}] {opt.description}")
        print(f"{'='*60}")
        print("Run this command in a separate terminal:")
        print(f"  {launch_command}")
        print(f"{'='*60}")
        print(f"The test will wait up to {timeout_seconds} seconds (from config) for your selection.")
        print(f"{'='*60}\n")

        # Wait for the user to make a selection via terminal
        # Use polling to handle the case where poll_session_result returns None
        max_attempts = 60
        result = None
        for attempt in range(max_attempts):
            result = await poll_session_result(session_id)
            if result is not None:
                break
            if attempt < max_attempts - 1:
                await asyncio.sleep(1)

        if result is None:
            pytest.fail(f"Timeout: No selection made within {timeout_seconds} seconds")

        # Verify the result
        assert result is not None
        assert result.action_status in ["selected", "cancelled"]
        
        if result.action_status == "selected":
            print(f"\n✅ Selection received: {result.selection.selected_indices}")
        else:
            print(f"\n❌ Interaction was cancelled")
