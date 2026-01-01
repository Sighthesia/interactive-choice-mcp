"""Configuration storage for interactive choice settings.

Provides a JSON-backed store for persisting user preferences like
interface preference, timeout settings, and notification options.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import get_config_path
from ..core.models import (
    DEFAULT_TIMEOUT_SECONDS,
    ProvideChoiceConfig,
    TRANSPORT_TERMINAL,
    VALID_TRANSPORTS,
    LANG_EN,
    VALID_LANGUAGES,
    NotificationTriggerMode,
)

__all__ = ["ConfigStore"]


class ConfigStore:
    """Lightweight JSON-backed store for user configuration.

    Responsible for reading/writing the persisted interaction settings while
    tolerating missing or partially corrupted files.
    """

    def __init__(self, *, path: Optional[Path] = None) -> None:
        self._path = Path(path) if path is not None else get_config_path()

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
            interface = raw.get("interface")
            if interface not in VALID_TRANSPORTS:
                interface = TRANSPORT_TERMINAL

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

            # Notification settings
            notify_new = bool(raw.get("notify_new", True))
            notify_upcoming = bool(raw.get("notify_upcoming", True))
            upcoming_threshold = 60
            raw_threshold = raw.get("upcoming_threshold")
            if isinstance(raw_threshold, (int, float, str)):
                try:
                    upcoming_threshold = max(1, int(raw_threshold))
                except Exception:
                    upcoming_threshold = 60
            notify_timeout = bool(raw.get("notify_timeout", True))
            
            # Migrate from old three-state settings to new trigger mode
            # If old settings exist, derive trigger mode from them
            notify_trigger_mode = NotificationTriggerMode.default()
            raw_trigger_mode = raw.get("notify_trigger_mode")
            if raw_trigger_mode in NotificationTriggerMode.__members__.values():
                notify_trigger_mode = NotificationTriggerMode(raw_trigger_mode)
            else:
                # Migration: check for old three-state settings
                old_foreground = raw.get("notify_if_foreground", True)
                old_focused = raw.get("notify_if_focused", True)
                old_background = raw.get("notify_if_background", True)
                
                # Derive trigger mode from old settings
                # Only background selected -> BACKGROUND mode (browser lost focus)
                # Only foreground and focused selected -> TAB_SWITCH mode (only page lost focus)
                # All selected -> ALWAYS mode
                # Otherwise -> TAB_SWITCH mode (most common use case)
                if old_background and not old_foreground and not old_focused:
                    notify_trigger_mode = NotificationTriggerMode.BACKGROUND
                elif old_foreground and old_focused and old_background:
                    notify_trigger_mode = NotificationTriggerMode.ALWAYS
                else:
                    # Default to TAB_SWITCH for other combinations
                    notify_trigger_mode = NotificationTriggerMode.TAB_SWITCH
            
            notify_sound = bool(raw.get("notify_sound", True))
            notify_sound_path = raw.get("notify_sound_path")
            if notify_sound_path is not None and not isinstance(notify_sound_path, str):
                notify_sound_path = None

            return ProvideChoiceConfig(
                interface=interface,
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
                notify_new=notify_new,
                notify_upcoming=notify_upcoming,
                upcoming_threshold=upcoming_threshold,
                notify_timeout=notify_timeout,
                notify_trigger_mode=notify_trigger_mode,
                notify_sound=notify_sound,
                notify_sound_path=notify_sound_path,
            )
        except Exception:
            return None

    def save(self, config: ProvideChoiceConfig, *, exclude_transport: bool = False) -> None:
        """Persist configuration to disk using atomic replacement.
        
        Args:
            config: The configuration to save.
            exclude_transport: If True, preserve the existing interface setting in the file
                              instead of overwriting it with config.interface. Useful for
                              operations like terminal->web switch that shouldn't change
                              the user's interface preference.
        """
        payload: Dict[str, Any] = {
            "interface": config.interface,
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
            "notify_new": config.notify_new,
            "notify_upcoming": config.notify_upcoming,
            "upcoming_threshold": config.upcoming_threshold,
            "notify_timeout": config.notify_timeout,
            "notify_trigger_mode": config.notify_trigger_mode.value,
            "notify_sound": config.notify_sound,
            "notify_sound_path": config.notify_sound_path,
        }

        # If excluding interface, preserve the existing value from disk
        if exclude_transport:
            existing = self.load()
            if existing is not None:
                payload["interface"] = existing.interface

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload))
            tmp_path.replace(self._path)
        except Exception:
            # Persistence failures should not crash the interaction flow.
            pass
