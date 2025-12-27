import asyncio

from server import provide_choice


def test_provide_choice_returns_validation_summary():
    result = asyncio.run(
        provide_choice(
            title="Title",
            prompt="Prompt",
            selection_mode="single",
            options=[{"id": "yes", "description": "desc"}],
        )
    )

    assert result["action_status"] == "cancelled"
    assert "validation_error" in result.get("summary", "")
    assert result.get("validation_error") == result.get("summary")
