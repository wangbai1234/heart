"""Unit tests for ss02_memory.mode — MEMORY_EXTRACTOR_MODE feature flag."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from heart.ss02_memory.mode import get_mode, is_llm_enabled, is_regex_active


class TestGetMode:
    """Tests for get_mode()."""

    def test_default_is_llm(self):
        """Default config should return 'llm'."""
        with patch("heart.ss02_memory.mode.settings") as mock_settings:
            mock_settings.memory_extractor_mode = "llm"
            assert get_mode() == "llm"

    def test_regex_mode_returns_regex(self):
        """Explicit 'regex' mode still works (deprecated)."""
        with patch("heart.ss02_memory.mode.settings") as mock_settings:
            mock_settings.memory_extractor_mode = "regex"
            assert get_mode() == "regex"

    def test_dual_mode_returns_dual(self):
        """Explicit 'dual' mode still works (deprecated)."""
        with patch("heart.ss02_memory.mode.settings") as mock_settings:
            mock_settings.memory_extractor_mode = "dual"
            assert get_mode() == "dual"

    def test_case_insensitive(self):
        """Mode should be case-insensitive."""
        with patch("heart.ss02_memory.mode.settings") as mock_settings:
            mock_settings.memory_extractor_mode = "LLM"
            assert get_mode() == "llm"

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace should be stripped."""
        with patch("heart.ss02_memory.mode.settings") as mock_settings:
            mock_settings.memory_extractor_mode = "  llm  "
            assert get_mode() == "llm"

    def test_invalid_mode_raises(self):
        """Invalid mode should raise ValueError."""
        with patch("heart.ss02_memory.mode.settings") as mock_settings:
            mock_settings.memory_extractor_mode = "invalid"
            with pytest.raises(ValueError, match="Invalid MEMORY_EXTRACTOR_MODE"):
                get_mode()


class TestDeprecationWarnings:
    """Deprecated modes should emit structlog warnings."""

    def test_regex_mode_logs_deprecation_warning(self):
        """Explicit 'regex' mode should log a deprecation warning."""
        with (
            patch("heart.ss02_memory.mode.settings") as mock_settings,
            patch("heart.ss02_memory.mode.logger") as mock_logger,
        ):
            mock_settings.memory_extractor_mode = "regex"
            result = get_mode()
            assert result == "regex"
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args.kwargs
            assert call_kwargs["mode"] == "regex"
            assert "deprecated" in call_kwargs["message"]

    def test_dual_mode_logs_deprecation_warning(self):
        """Explicit 'dual' mode should log a deprecation warning."""
        with (
            patch("heart.ss02_memory.mode.settings") as mock_settings,
            patch("heart.ss02_memory.mode.logger") as mock_logger,
        ):
            mock_settings.memory_extractor_mode = "dual"
            result = get_mode()
            assert result == "dual"
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args.kwargs
            assert call_kwargs["mode"] == "dual"

    def test_llm_mode_does_not_log_warning(self):
        """Default 'llm' mode should NOT log a warning."""
        with (
            patch("heart.ss02_memory.mode.settings") as mock_settings,
            patch("heart.ss02_memory.mode.logger") as mock_logger,
        ):
            mock_settings.memory_extractor_mode = "llm"
            result = get_mode()
            assert result == "llm"
            mock_logger.warning.assert_not_called()


class TestIsLlmEnabled:
    """Tests for is_llm_enabled()."""

    def test_regex_disables_llm(self):
        """regex mode: is_llm_enabled() == False."""
        with patch("heart.ss02_memory.mode.get_mode", return_value="regex"):
            assert is_llm_enabled() is False

    def test_llm_enables_llm(self):
        """llm mode: is_llm_enabled() == True."""
        with patch("heart.ss02_memory.mode.get_mode", return_value="llm"):
            assert is_llm_enabled() is True

    def test_dual_enables_llm(self):
        """dual mode: is_llm_enabled() == True."""
        with patch("heart.ss02_memory.mode.get_mode", return_value="dual"):
            assert is_llm_enabled() is True


class TestIsRegexActive:
    """Tests for is_regex_active()."""

    def test_regex_active_in_regex_mode(self):
        """regex mode: is_regex_active() == True (deprecated)."""
        with patch("heart.ss02_memory.mode.get_mode", return_value="regex"):
            assert is_regex_active() is True

    def test_regex_inactive_in_llm_mode(self):
        """llm mode: is_regex_active() == False."""
        with patch("heart.ss02_memory.mode.get_mode", return_value="llm"):
            assert is_regex_active() is False

    def test_regex_active_in_dual_mode(self):
        """dual mode: is_regex_active() == True (deprecated)."""
        with patch("heart.ss02_memory.mode.get_mode", return_value="dual"):
            assert is_regex_active() is True
