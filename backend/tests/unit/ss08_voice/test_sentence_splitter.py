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
