from pathlib import Path

from choice.storage import ConfigStore
from choice import models


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
