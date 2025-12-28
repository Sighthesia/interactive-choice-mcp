from pathlib import Path

from src.storage import ConfigStore
from src import models


def test_load_returns_none_when_missing(tmp_path: Path):
    store = ConfigStore(path=tmp_path / "cfg.json")
    assert store.load() is None


def test_save_and_load_roundtrip(tmp_path: Path):
    store = ConfigStore(path=tmp_path / "cfg.json")
    original = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_WEB,
        timeout_seconds=45,
        single_submit_mode=False,
        timeout_default_index=1,
        timeout_default_enabled=True,
        use_default_option=True,
        timeout_action="cancel",
        language="zh",
    )

    store.save(original)
    loaded = store.load()

    assert loaded is not None
    assert loaded.transport == models.TRANSPORT_WEB
    assert loaded.timeout_seconds == 45
    assert loaded.single_submit_mode is False
    assert loaded.timeout_default_index == 1
    assert loaded.timeout_default_enabled is True
    assert loaded.use_default_option is True
    assert loaded.timeout_action == "cancel"
    assert loaded.language == "zh"


def test_load_sanitizes_invalid_values(tmp_path: Path):
    path = tmp_path / "cfg.json"
    path.write_text(
        """
        {
            "transport": "invalid",
            "timeout_seconds": -5
        }
        """
    )

    store = ConfigStore(path=path)
    loaded = store.load()

    assert loaded is not None
    assert loaded.transport == models.TRANSPORT_TERMINAL
    assert loaded.timeout_seconds == models.DEFAULT_TIMEOUT_SECONDS
    assert loaded.language == "en"  # Invalid values fall back to English


def test_language_invalid_fallback(tmp_path: Path):
    """Test that invalid language values fallback to English."""
    path = tmp_path / "cfg.json"
    path.write_text(
        """
        {
            "transport": "terminal",
            "timeout_seconds": 60,
            "language": "invalid"
        }
        """
    )

    store = ConfigStore(path=path)
    loaded = store.load()

    assert loaded is not None
    assert loaded.language == "en"


def test_language_zh_preserved(tmp_path: Path):
    """Test that valid Chinese language setting is preserved."""
    path = tmp_path / "cfg.json"
    path.write_text(
        """
        {
            "transport": "terminal",
            "timeout_seconds": 60,
            "language": "zh"
        }
        """
    )

    store = ConfigStore(path=path)
    loaded = store.load()

    assert loaded is not None
    assert loaded.language == "zh"


def test_save_and_load_preserves_notification_fields(tmp_path: Path):
    store = ConfigStore(path=tmp_path / "cfg.json")
    original = models.ProvideChoiceConfig(
        transport=models.TRANSPORT_WEB,
        timeout_seconds=120,
        notify_new=False,
        notify_upcoming=False,
        upcoming_threshold=42,
        notify_timeout=False,
        notify_if_foreground=False,
        notify_if_focused=False,
        notify_if_background=False,
        notify_sound=False,
    )

    store.save(original)
    loaded = store.load()

    assert loaded is not None
    assert loaded.notify_new is False
    assert loaded.notify_upcoming is False
    assert loaded.upcoming_threshold == 42
    assert loaded.notify_timeout is False
    assert loaded.notify_if_foreground is False
    assert loaded.notify_if_focused is False
    assert loaded.notify_if_background is False
    assert loaded.notify_sound is False
