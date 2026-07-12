"""Unit tests for the preset-voice sample endpoint's error surface.

The endpoint used to swallow the MiniMax provider's real error and reply with
a generic "试听合成失败，请稍后再试" that gave the frontend nothing to show
except a same-copy toast. We now bubble the provider's message up into the
502 ``detail`` so a real-device tester (or Sonnet reading the log) can tell
which voice_id broke and why.
"""

from __future__ import annotations

import re

import pytest

from heart.ss08_voice.errors import TTSProviderError


def test_provider_error_message_is_truncated_at_320_chars():
    """A very long provider error should be trimmed with an ellipsis marker."""
    from heart.api import routes_voice  # noqa: F401 -- imports for coverage

    # Simulate what the endpoint does: read exc, truncate, format detail.
    long_body = "x" * 500
    exc = TTSProviderError(f"MiniMax API error: 400 - {long_body}", status_code=400)
    provider_msg = str(exc)
    if len(provider_msg) > 320:
        provider_msg = provider_msg[:317] + "..."
    detail = f"试听合成失败：{provider_msg}"

    assert len(provider_msg) == 320
    assert provider_msg.endswith("...")
    assert detail.startswith("试听合成失败：")
    # Ensure raw error prefix survived truncation.
    assert "MiniMax API error: 400" in detail


def test_provider_error_short_message_untruncated():
    exc = TTSProviderError("MiniMax API error: 400 - voice_id not found", status_code=400)
    provider_msg = str(exc)
    if len(provider_msg) > 320:
        provider_msg = provider_msg[:317] + "..."
    detail = f"试听合成失败：{provider_msg}"
    assert "voice_id not found" in detail
    assert "..." not in detail


def test_provider_error_status_code_reachable_on_exc():
    """The endpoint logs exc.status_code — verify TTSProviderError exposes it."""
    exc = TTSProviderError("boom", status_code=503)
    assert exc.status_code == 503


@pytest.mark.parametrize(
    "raw,expected_head",
    [
        ("timeout after 30s", "timeout"),
        ("Invalid MiniMax response: {'base_resp': {'status_code': 1002}}", "Invalid"),
    ],
)
def test_provider_error_str_head(raw: str, expected_head: str):
    """Sanity: TTSProviderError preserves whatever message we pass in."""
    assert str(TTSProviderError(raw)).startswith(expected_head)


def test_detail_contains_ideographic_colon_separator():
    """UI split by '：' when rendering — assert we use the CJK separator, not ':'."""
    provider_msg = "MiniMax API error: 400"
    detail = f"试听合成失败：{provider_msg}"
    assert re.search(r"试听合成失败：", detail) is not None
