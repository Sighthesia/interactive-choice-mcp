import asyncio

from src.core.orchestrator import ChoiceOrchestrator
from src.mcp.tools import provide_choice, set_orchestrator_for_testing


def test_provide_choice_returns_validation_summary():
    # Initialize orchestrator for testing
    orchestrator = ChoiceOrchestrator()
    set_orchestrator_for_testing(orchestrator)

    result = asyncio.run(
        provide_choice(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "yes", "description": "desc"}],
        )
    )

    assert result["action_status"] == "cancelled"
    assert "validation_error" in result.get("validation_error", "")
