"""Tests for novel-style narration stripping in composer post-filter."""

from heart.ss05_composer.service import ComposerService


def test_strip_full_width_parens():
    text = "（抬眼看了你一眼，语气平淡）七月的梅雨季节还要持续七天。"
    cleaned, count = ComposerService._strip_narration(text)
    assert cleaned == "七月的梅雨季节还要持续七天。"
    assert count == 1


def test_strip_multiple_parens():
    text = "（轻声叹气）嗯。（沉默了一下）你过得还好吗？"
    cleaned, _ = ComposerService._strip_narration(text)
    assert "（" not in cleaned and "）" not in cleaned
    assert "嗯" in cleaned and "你过得还好吗" in cleaned


def test_strip_ascii_parens_with_stage_direction():
    text = "Hello. (softly) How are you?"
    cleaned, _ = ComposerService._strip_narration(text)
    assert "(softly)" not in cleaned


def test_strip_markdown_italic_action():
    text = "*耸耸肩* 随便吧。"
    cleaned, _ = ComposerService._strip_narration(text)
    assert "*" not in cleaned
    assert "随便吧" in cleaned


def test_preserve_short_placeholder():
    """`（略）`(单字内容) 是 post-filter 占位符，不能误删。"""
    text = "前面（略）后面"
    cleaned, count = ComposerService._strip_narration(text)
    assert "（略）" in cleaned
    assert count == 0


def test_preserve_pure_dialogue():
    text = "今天天气真好，你想去哪里走走？"
    cleaned, count = ComposerService._strip_narration(text)
    assert cleaned == text
    assert count == 0
