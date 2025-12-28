from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .models import (
    DEFAULT_TIMEOUT_SECONDS,
    ProvideChoiceConfig,
    TRANSPORT_TERMINAL,
    VALID_TRANSPORTS,
    LANG_EN,
    VALID_LANGUAGES,
)


class ConfigStore:
    """Lightweight JSON-backed store for user configuration.

    Responsible for reading/writing the persisted interaction settings while
    tolerating missing or partially corrupted files.
    """

    def __init__(self, *, path: Optional[Path] = None) -> None:
        self._path = Path(path) if path is not None else Path.home() / ".interactive_choice_config.json"

    def load(self) -> Optional[ProvideChoiceConfig]:
        """Load configuration from disk if present.

        Returns None when the file is missing or cannot be parsed.
        """
        try:
            if not self._path.exists():
                return None
            raw = json.loads(self._path.read_text())
            if not isinstance(raw, dict):
                return None
        except Exception:
            return None

        try:
            transport = raw.get("transport")
            if transport not in VALID_TRANSPORTS:
                transport = TRANSPORT_TERMINAL

            timeout_seconds = DEFAULT_TIMEOUT_SECONDS
            raw_timeout = raw.get("timeout_seconds")
            if isinstance(raw_timeout, (int, float, str)):
                try:
                    timeout_seconds = int(raw_timeout)
                except Exception:
                    timeout_seconds = DEFAULT_TIMEOUT_SECONDS
            timeout_seconds = timeout_seconds if timeout_seconds > 0 else DEFAULT_TIMEOUT_SECONDS

            single_submit_mode = bool(raw.get("single_submit_mode", True))
            timeout_default_index = raw.get("timeout_default_index")
            if timeout_default_index is not None:
                try:
                    timeout_default_index = int(timeout_default_index)
                except Exception:
                    timeout_default_index = None

            timeout_default_enabled = bool(raw.get("timeout_default_enabled", False))
            use_default_option = bool(raw.get("use_default_option", False))
            timeout_action = raw.get("timeout_action", "submit") or "submit"

            # Persistence settings
            persistence_enabled = bool(raw.get("persistence_enabled", True))
            retention_days = 3
            raw_retention = raw.get("retention_days")
            if isinstance(raw_retention, (int, float, str)):
                try:
                    retention_days = max(1, int(raw_retention))
                except Exception:
                    retention_days = 3
            max_sessions = 100
            raw_max = raw.get("max_sessions")
            if isinstance(raw_max, (int, float, str)):
                try:
                    max_sessions = max(1, int(raw_max))
                except Exception:
                    max_sessions = 100

            # Language setting
            language = raw.get("language")
            if language not in VALID_LANGUAGES:
                language = LANG_EN

            return ProvideChoiceConfig(
                transport=transport,
                timeout_seconds=timeout_seconds,
                single_submit_mode=single_submit_mode,
                timeout_default_index=timeout_default_index,
                timeout_default_enabled=timeout_default_enabled,
                use_default_option=use_default_option,
                timeout_action=timeout_action,
                persistence_enabled=persistence_enabled,
                retention_days=retention_days,
                max_sessions=max_sessions,
                language=language,
            )
        except Exception:
            return None

    def save(self, config: ProvideChoiceConfig) -> None:
        """Persist configuration to disk using atomic replacement."""
        payload = {
            "transport": config.transport,
            "timeout_seconds": config.timeout_seconds,
            "single_submit_mode": config.single_submit_mode,
            "timeout_default_index": config.timeout_default_index,
            "timeout_default_enabled": config.timeout_default_enabled,
            "use_default_option": config.use_default_option,
            "timeout_action": config.timeout_action,
            "persistence_enabled": config.persistence_enabled,
            "retention_days": config.retention_days,
            "max_sessions": config.max_sessions,
            "language": config.language,
        }

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload))
            tmp_path.replace(self._path)
        except Exception:
            # Persistence failures should not crash the interaction flow.
            pass
