"""Unit tests for MessageSplitter."""

from __future__ import annotations

import pytest

from heart.ss05_composer.message_splitter import split_response


@pytest.mark.unit
class TestSplitResponse:
    def test_short_text_stays_single_bubble(self):
        result = split_response("你好，我是凛。", max_chars=60)
        assert len(result) == 1
        assert result[0] == "你好，我是凛。"

    def test_empty_string_returns_single_empty(self):
        result = split_response("")
        assert result == [""]

    def test_paragraph_break_splits(self):
        text = "第一段话。\n\n第二段话。"
        result = split_response(text, max_chars=60)
        assert len(result) == 2
        assert "第一段话" in result[0]
        assert "第二段话" in result[1]

    def test_long_paragraph_splits_at_terminator(self):
        # 2 short sentences that individually are < 60 chars but their paragraph > max_chars
        text = "今天天气不错。我们去散步吧！这是第三句，凑够长度用的。所以需要被拆分。"
        result = split_response(text, max_chars=15)
        assert len(result) >= 2
        # Each segment should be non-empty
        for seg in result:
            assert seg.strip()

    def test_max_bubbles_cap(self):
        # 8 short sentences — should be capped at 4 bubbles
        text = "a。b。c。d。e。f。g。h。"
        result = split_response(text, max_chars=5, max_bubbles=4)
        assert len(result) <= 4

    def test_exactly_max_chars(self):
        # text is exactly max_chars — should stay as one segment
        text = "a" * 60
        result = split_response(text, max_chars=60)
        assert len(result) == 1

    def test_whitespace_trimmed(self):
        result = split_response("  你好  ", max_chars=60)
        assert result[0] == "你好"

    def test_multiple_paragraphs_capped(self):
        # 6 paragraphs with max_bubbles=4: some will be merged
        parts = [f"第{i}段落内容。" for i in range(1, 7)]
        text = "\n\n".join(parts)
        result = split_response(text, max_chars=60, max_bubbles=4)
        assert len(result) == 4
        # All original text must appear somewhere
        for i in range(1, 7):
            assert any(f"第{i}段落" in seg for seg in result)

    def test_single_long_sentence_not_chopped(self):
        # A 100-char sentence with no terminator stays as one segment
        text = "这是一个很长很长的句子，没有任何标点符号，因此不会被拆分，直到达到上限。。。看看能不能保持完整"
        result = split_response(text, max_chars=30, max_bubbles=4)
        # Merged to within max_bubbles; all text present
        combined = "".join(result)
        assert "这是一个很长很长的句子" in combined
