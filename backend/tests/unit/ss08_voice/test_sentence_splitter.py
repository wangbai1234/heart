"""Tests for SentenceSplitter."""

import pytest

from heart.ss08_voice.sentence_splitter import SentenceSplitter


def test_feed_no_terminator():
    """Test feeding text without terminator returns empty list."""
    splitter = SentenceSplitter()
    result = splitter.feed("你好")
    assert result == []


def test_feed_short_sentence_not_split():
    """Test short sentence with terminator is not split (below MIN_LEN)."""
    splitter = SentenceSplitter()
    result = splitter.feed("嗯。")
    assert result == []


def test_feed_sentence_split():
    """Test sentence is split at terminator when long enough."""
    splitter = SentenceSplitter()
    # Feed enough characters to exceed MIN_LEN
    result = splitter.feed("你好，今天")
    assert result == []
    result = splitter.feed("好累。")
    assert len(result) == 1
    assert result[0] == "你好，今天好累。"


def test_feed_long_sentence_force_split():
    """Test long sentence is force split at MAX_LEN."""
    splitter = SentenceSplitter()
    # Feed 50+ characters without terminator
    text = "这是一段很长的文本" * 6  # 48 chars
    result = splitter.feed(text)
    assert len(result) == 1
    assert len(result[0]) == 50


def test_terminator_inside_bracket_does_not_split():
    """A （）span with an inner terminator stays whole (brackets kept paired)."""
    splitter = SentenceSplitter()
    # Inner 。 must NOT trigger a split — that would orphan the brackets and the
    # TTS strip regex (paired-only) would then read them aloud.
    out = splitter.feed("（她停顿了一下。目光落向别处）你还好吗？")
    # One clean sentence with the bracket span intact + the real question.
    assert out == ["（她停顿了一下。目光落向别处）你还好吗？"]


def test_bracket_span_kept_balanced_across_feeds():
    """Bracket depth carries across feed() calls (streamed token boundaries)."""
    splitter = SentenceSplitter()
    assert splitter.feed("（轻声说，") == []
    assert splitter.feed("像怕惊扰谁。") == []  # inner terminator, still inside （
    out = splitter.feed("）好久不见。")
    assert out == ["（轻声说，像怕惊扰谁。）好久不见。"]


def test_hard_max_forces_split_when_bracket_never_closes():
    """A never-closed bracket can't buffer forever — HARD_MAX forces a cut."""
    splitter = SentenceSplitter()
    text = "（" + "啊" * 200  # opener then no closer, well past HARD_MAX
    out = splitter.feed(text)
    assert len(out) >= 1
    assert len(out[0]) == SentenceSplitter.HARD_MAX


def test_flush_remaining():
    """Test flush returns remaining buffer."""
    splitter = SentenceSplitter()
    splitter.feed("你好")
    result = splitter.flush()
    assert result == "你好"


def test_flush_empty():
    """Test flush returns None when buffer is empty."""
    splitter = SentenceSplitter()
    result = splitter.flush()
    assert result is None
