"""Unit tests for _derive_segments_and_cost — segment splitting + zero per-message cost.

Verifies that voice mode never splits into N bubbles (one audio clip = one
bubble) and that the per-message cost is always 0 under the model+provider
billing scheme (a turn is billed per LLM turn + per TTS provider, never per
message bubble — the legacy per-bubble charge caused a voice double-charge).
"""

from __future__ import annotations

from types import SimpleNamespace

from heart.api.routes_chat_ws import _derive_segments_and_cost


def _cfg(text_cost: int = 200, voice_cost: int = 500):
    return SimpleNamespace(
        credits_cost_text_message=text_cost,
        credits_cost_voice_message=voice_cost,
    )


def test_text_mode_splits_semantic_segments():
    segments, cost = _derive_segments_and_cost(
        "（她笑了）你好呀今天。心情还不错吗？", "text", _cfg()
    )
    kinds = [s["kind"] for s in segments]
    assert "action" in kinds
    assert kinds.count("text") >= 2
    assert cost == 0  # per-message cost removed; billed per LLM turn + TTS


def test_voice_mode_never_splits():
    """Voice mode must emit exactly one text bubble carrying the full text."""
    segments, cost = _derive_segments_and_cost(
        "（她笑了）你好呀今天。心情还不错吗？", "voice", _cfg()
    )
    assert len(segments) == 1
    assert segments[0]["kind"] == "text"
    assert "你好呀今天" in segments[0]["content"]
    assert "心情还不错吗" in segments[0]["content"]
    assert cost == 0  # voice no longer per-bubble charged; TTS billed per provider


def test_voice_mode_bills_once_regardless_of_content_length():
    """Even a long response gets one voice charge, not N × voice cost."""
    long_response = "第一句很长的话。" * 10
    segments, cost = _derive_segments_and_cost(long_response, "voice", _cfg())
    assert len(segments) == 1
    assert cost == 0


def test_text_mode_empty_response_returns_single_empty_bubble():
    """Empty response in text mode should return a single (empty text) bubble."""
    segments, cost = _derive_segments_and_cost("", "text", _cfg())
    assert len(segments) == 1
    assert segments[0]["kind"] == "text"
    assert cost == 0
