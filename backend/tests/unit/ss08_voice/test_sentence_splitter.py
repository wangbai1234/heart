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


def test_first_clause_splits_early_on_comma():
    """The FIRST sentence breaks on a comma once past FIRST_MIN_LEN, so the
    opening audio reaches TTS a beat sooner than waiting for a terminator."""
    splitter = SentenceSplitter()
    # 9 chars then a comma (>= FIRST_MIN_LEN=8) → early clause split.
    out = splitter.feed("其实我今天有点累，")
    assert out == ["其实我今天有点累，"]


def test_only_first_clause_splits_on_comma():
    """After the first sentence emits, later commas no longer split — cadence
    returns to terminator/MAX_LEN so mid-reply isn't chopped at every comma."""
    splitter = SentenceSplitter()
    assert splitter.feed("其实我今天有点累，") == ["其实我今天有点累，"]
    # A second comma clause of the same length must NOT split now.
    assert splitter.feed("然后又下了雨，") == []
    out = splitter.feed("心情更差了。")
    assert out == ["然后又下了雨，心情更差了。"]


def test_first_clause_not_split_below_min_len():
    """A very short leading clause (< FIRST_MIN_LEN) is not worth splitting."""
    splitter = SentenceSplitter()
    assert splitter.feed("你好，") == []  # only 3 chars before the comma


def test_first_clause_comma_inside_instruction_bracket_kept():
    """A comma inside a [中文指令] span must not bisect the instruction."""
    splitter = SentenceSplitter()
    # The comma sits inside [温柔，轻声] — splitting there would send half an
    # instruction to Fish as speech. Held until a real boundary.
    out = splitter.feed("[温柔，轻声]我在这儿。")
    assert out == ["[温柔，轻声]我在这儿。"]


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
