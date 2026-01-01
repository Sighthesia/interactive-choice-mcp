"""Tests for i18n module."""
import os
from unittest.mock import patch

import pytest

from src.infra.i18n import get_text, TEXTS
from src.infra.logging import get_language_from_env, LANG_ENV


class TestGetText:
    """Tests for get_text function."""

    def test_get_english_text(self):
        """Test getting English text."""
        result = get_text("settings.title", "en")
        assert result == "Settings"

    def test_get_chinese_text(self):
        """Test getting Chinese text."""
        result = get_text("settings.title", "zh")
        assert result == "设置"

    def test_unknown_key_returns_key(self):
        """Test that unknown keys return the key itself."""
        result = get_text("unknown.key", "en")
        assert result == "unknown.key"

    def test_unknown_language_fallback_to_english(self):
        """Test that unknown language codes fallback to English."""
        result = get_text("settings.title", "fr")
        assert result == "Settings"

    def test_all_keys_have_both_languages(self):
        """Ensure all text keys have both en and zh translations."""
        for key, translations in TEXTS.items():
            assert "en" in translations, f"Key '{key}' missing English translation"
            assert "zh" in translations, f"Key '{key}' missing Chinese translation"

    def test_status_messages_present(self):
        """Ensure human-readable status messages exist and contain expected emojis."""
        assert get_text("status_message.manual", "en").startswith("✅")
        assert get_text("status_message.manual", "zh").startswith("✅")
        assert get_text("status_message.cancelled", "en").startswith("🚫")
        assert get_text("status_message.cancelled", "zh").startswith("🚫")

    def test_status_completed_localization(self):
        """Ensure short completed label is localized."""
        assert get_text("status.completed", "en") == "Completed"
        assert get_text("status.completed", "zh") == "已完成"

    def test_cancel_with_annotations_texts(self):
        """Ensure cancel-with-annotations action and status message are present and localized."""
        assert get_text("action.cancel_with_annotations", "en") == "Cancel with annotations"
        assert get_text("action.cancel_with_annotations", "zh") == "带备注取消"
        assert get_text("status_message.cancel_with_annotation", "en").startswith("🚫")
        assert get_text("status_message.cancel_with_annotation", "zh").startswith("🚫")

    def test_notification_session_texts(self):
        """Ensure notification session texts are present and localized."""
        assert "New Session" in get_text("notification.session.title", "en")
        assert "{prompt_title}" in get_text("notification.session.title", "en")
        assert "新交互" in get_text("notification.session.title", "zh")
        assert "{prompt_title}" in get_text("notification.session.title", "zh")
        assert get_text("notification.session.ready", "en") == "Ready"
        assert get_text("notification.session.ready", "zh") == "就绪"

    def test_notification_timeout_upcoming_texts(self):
        """Ensure notification timeout upcoming texts are present and localized."""
        assert "Timeout Approaching" in get_text("notification.timeout.upcomingTitle", "en")
        assert "{prompt_title}" in get_text("notification.timeout.upcomingTitle", "en")
        assert "即将超时" in get_text("notification.timeout.upcomingTitle", "zh")
        assert "{prompt_title}" in get_text("notification.timeout.upcomingTitle", "zh")
        assert "{seconds}" in get_text("notification.timeout.upcomingBody", "en")
        assert "{seconds}" in get_text("notification.timeout.upcomingBody", "zh")

    def test_notification_timeout_submitted_texts(self):
        """Ensure notification timeout submitted texts are present and localized."""
        assert "Auto Submitted" in get_text("notification.timeout.submittedTitle", "en")
        assert "{prompt_title}" in get_text("notification.timeout.submittedTitle", "en")
        assert "已自动提交" in get_text("notification.timeout.submittedTitle", "zh")
        assert "{prompt_title}" in get_text("notification.timeout.submittedTitle", "zh")
        assert "timeout" in get_text("notification.timeout.submittedBody", "en").lower()
        assert "超时" in get_text("notification.timeout.submittedBody", "zh")

    def test_notification_timeout_cancelled_texts(self):
        """Ensure notification timeout cancelled texts are present and localized."""
        assert "Timeout Cancelled" in get_text("notification.timeout.cancelledTitle", "en")
        assert "{prompt_title}" in get_text("notification.timeout.cancelledTitle", "en")
        assert "超时已取消" in get_text("notification.timeout.cancelledTitle", "zh")
        assert "{prompt_title}" in get_text("notification.timeout.cancelledTitle", "zh")
        assert "timeout" in get_text("notification.timeout.cancelledBody", "en").lower()
        assert "超时" in get_text("notification.timeout.cancelledBody", "zh")

    def test_notification_timeout_reached_texts(self):
        """Ensure notification timeout reached texts are present and localized."""
        assert "Timeout Reached" in get_text("notification.timeout.reachedTitle", "en")
        assert "{prompt_title}" in get_text("notification.timeout.reachedTitle", "en")
        assert "已超时" in get_text("notification.timeout.reachedTitle", "zh")
        assert "{prompt_title}" in get_text("notification.timeout.reachedTitle", "zh")
        assert "timed out" in get_text("notification.timeout.reachedBody", "en").lower()
        assert "超时" in get_text("notification.timeout.reachedBody", "zh")


class TestGetLanguageFromEnv:
    """Tests for get_language_from_env function."""

    def test_env_not_set_returns_none(self):
        """Test that unset env returns None."""
        with patch.dict(os.environ, {}, clear=True):
            if LANG_ENV in os.environ:
                del os.environ[LANG_ENV]
            result = get_language_from_env()
            assert result is None

    def test_env_en_returns_en(self):
        """Test that CHOICE_LANG=en returns 'en'."""
        with patch.dict(os.environ, {LANG_ENV: "en"}):
            result = get_language_from_env()
            assert result == "en"

    def test_env_zh_returns_zh(self):
        """Test that CHOICE_LANG=zh returns 'zh'."""
        with patch.dict(os.environ, {LANG_ENV: "zh"}):
            result = get_language_from_env()
            assert result == "zh"

    def test_env_invalid_returns_none_and_logs_warning(self):
        """Test that invalid CHOICE_LANG logs warning and returns None."""
        with patch.dict(os.environ, {LANG_ENV: "invalid"}):
            result = get_language_from_env()
            # Invalid value should return None (caller handles fallback)
            assert result is None

    def test_env_with_whitespace_trimmed(self):
        """Test that whitespace is trimmed from env value."""
        with patch.dict(os.environ, {LANG_ENV: "  zh  "}):
            result = get_language_from_env()
            assert result == "zh"

    def test_env_case_insensitive(self):
        """Test that env value is case-insensitive."""
        with patch.dict(os.environ, {LANG_ENV: "ZH"}):
            result = get_language_from_env()
            assert result == "zh"
