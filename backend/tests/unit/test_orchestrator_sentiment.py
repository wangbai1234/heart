"""Tests for the orchestrator's lexicon sentiment helper.

Guards that emotion contagion / L2 episodes are fed a *real* message
sentiment instead of the old hardcoded neutral value.
"""

from __future__ import annotations

from uuid import uuid4

from heart.ss07_orchestration.orchestrator import _message_sentiment


def test_message_sentiment_negative_for_dislike():
    s = _message_sentiment(uuid4(), "rin", "我讨厌香菜")
    assert s < 0.0


def test_message_sentiment_neutral_and_safe_on_empty():
    # Empty / whitespace → no sentiment words → 0.0, never raises.
    assert _message_sentiment(uuid4(), "rin", "") == 0.0
    assert _message_sentiment(uuid4(), "rin", "   ") == 0.0


def test_message_sentiment_in_range():
    for text in ["我今天很开心", "我讨厌香菜", "我在苏州工作"]:
        s = _message_sentiment(uuid4(), "rin", text)
        assert -1.0 <= s <= 1.0
