"""Unit tests for voice-clone audio-source dispatch.

The clone endpoint now supports two audio-delivery paths:
- ``minimax_file://<file_id>`` — audio hosted at MiniMax (dev / no-S3 path)
- anything else — a public URL for MiniMax to fetch (S3-configured path)

Dispatch happens in ``_call_tts_clone_api``. These tests lock in the
routing so a future refactor doesn't silently regress into "always URL".
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from heart.api import routes_voice


@pytest.mark.asyncio
async def test_local_scheme_is_rejected():
    """Legacy 'local://' placeholder must never succeed — that was the 假成功 bug."""
    result = await routes_voice._call_tts_clone_api("local://tmp/x.wav", "abc")
    assert result is None


@pytest.mark.asyncio
async def test_minimax_file_scheme_routes_to_file_id_path():
    """`minimax_file://123` should call the file_id clone helper, not URL."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "minimax"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_file_id",
            new=AsyncMock(return_value="VOICE_OK"),
        ) as mock_file,
        patch.object(
            routes_voice,
            "_minimax_clone_by_url",
            new=AsyncMock(return_value="WRONG"),
        ) as mock_url,
    ):
        got = await routes_voice._call_tts_clone_api("minimax_file://12345", "char_abc")

    assert got == "VOICE_OK"
    mock_file.assert_awaited_once_with(12345, "char_abc")
    mock_url.assert_not_called()


@pytest.mark.asyncio
async def test_https_scheme_routes_to_url_path():
    """A regular https URL should call the file_url clone helper."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "minimax"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_file_id",
            new=AsyncMock(return_value="WRONG"),
        ) as mock_file,
        patch.object(
            routes_voice,
            "_minimax_clone_by_url",
            new=AsyncMock(return_value="VOICE_OK"),
        ) as mock_url,
    ):
        got = await routes_voice._call_tts_clone_api(
            "https://cdn.example.com/sample.wav", "char_abc"
        )

    assert got == "VOICE_OK"
    mock_url.assert_awaited_once_with("https://cdn.example.com/sample.wav", "char_abc")
    mock_file.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_returns_none_on_missing_provider():
    with (
        patch.object(routes_voice.settings, "voice_provider", "unset"),
        patch.object(routes_voice.settings, "minimax_api_key", ""),
    ):
        got = await routes_voice._call_tts_clone_api("minimax_file://1", "x")
    assert got is None


@pytest.mark.asyncio
async def test_dispatch_allows_clone_when_primary_provider_is_mimo():
    """Clone must proceed as long as MiniMax key is set — the primary TTS
    provider being MiMo (voice_provider="mimo") is not a reason to refuse
    clone. Regression from 2026-07-12 real-device report."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "mimo"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_file_id",
            new=AsyncMock(return_value="VOICE_OK"),
        ) as mock_file,
    ):
        got = await routes_voice._call_tts_clone_api("minimax_file://42", "char_abc")

    assert got == "VOICE_OK"
    mock_file.assert_awaited_once_with(42, "char_abc")


@pytest.mark.asyncio
async def test_dispatch_swallows_exceptions():
    """A raised inner helper turns into ``None`` — job marks failed, no crash."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "minimax"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_url",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
    ):
        got = await routes_voice._call_tts_clone_api("https://x/y.wav", "z")
    assert got is None


def test_clone_voice_id_for_starts_with_letter_and_contains_char_id():
    """MiniMax voice_id needs to be a stable-ish identifier — sanity-check shape."""
    got = routes_voice._clone_voice_id_for("char_abc123")
    assert got.startswith("UGC_")
    assert "char" in got or "abc" in got  # segment survived alnum filter
    assert len(got) <= 64


def test_clone_voice_id_for_handles_ugly_ids():
    """Even a pure-symbol character_id shouldn't produce an empty middle segment."""
    got = routes_voice._clone_voice_id_for("---")
    assert got.startswith("UGC_clone_")
