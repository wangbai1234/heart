"""Unit tests for the action/text semantic message splitter."""

from __future__ import annotations

from heart.ss05_composer.message_splitter import split_response


def test_empty_input_returns_empty_list():
    assert split_response("") == []
    assert split_response("   ") == []


def test_plain_dialog_one_sentence():
    result = split_response("你好啊。")
    assert result == [{"kind": "text", "content": "你好啊。"}]


def test_two_sentences_split():
    """Two long-enough sentences (≥6 chars each) should stay separate."""
    result = split_response("你好呀今天。心情还不错吗？")
    assert len(result) == 2
    assert result[0] == {"kind": "text", "content": "你好呀今天。"}
    assert result[1] == {"kind": "text", "content": "心情还不错吗？"}


def test_chinese_paren_action_extracted():
    result = split_response("（她轻轻笑了笑）好啊，今天想去哪里？")
    assert result[0] == {"kind": "action", "content": "她轻轻笑了笑"}
    assert result[1] == {"kind": "text", "content": "好啊，今天想去哪里？"}


def test_english_paren_action():
    result = split_response("(she smiles) Hello there.")
    assert result[0] == {"kind": "action", "content": "she smiles"}
    assert result[1]["kind"] == "text"


def test_brackets_ooc_treated_as_action():
    result = split_response("[回到主题] 我们说到哪里了？")
    assert result[0] == {"kind": "action", "content": "回到主题"}
    assert result[1]["kind"] == "text"


def test_chinese_full_width_brackets():
    result = split_response("【叹气】好吧，我明白了。")
    assert result[0] == {"kind": "action", "content": "叹气"}
    assert result[1]["kind"] == "text"


def test_interleaved_actions_and_dialog():
    result = split_response("（歪头）真的吗？（笑了）我不太相信。")
    kinds = [s["kind"] for s in result]
    assert kinds == ["action", "text", "action", "text"]
    assert result[0]["content"] == "歪头"
    assert result[1]["content"] == "真的吗？"
    assert result[2]["content"] == "笑了"
    assert result[3]["content"] == "我不太相信。"


def test_short_text_merged_with_next():
    """一个字'嗯。'应该合并到下一句"""
    result = split_response("嗯。我明白你的意思了。")
    text_segments = [s for s in result if s["kind"] == "text"]
    assert len(text_segments) == 1
    assert text_segments[0]["content"].startswith("嗯")


def test_short_text_at_end_stays():
    """如果短句在最后且没有后续文本，只能保留"""
    result = split_response("我明白你的意思了。嗯。")
    text_segments = [s for s in result if s["kind"] == "text"]
    # Either merged or kept; both are acceptable — verify no data loss
    total = "".join(s["content"] for s in text_segments)
    assert "嗯" in total and "明白" in total


def test_short_text_before_action_does_not_swallow_action():
    """短句 + 动作 + 长句 → 短句应合并到长句，动作保留独立"""
    result = split_response("嗯。（点头）我明白你的意思了。")
    kinds = [s["kind"] for s in result]
    assert "action" in kinds
    action = next(s for s in result if s["kind"] == "action")
    assert action["content"] == "点头"


def test_cap_at_six_text_bubbles():
    """超过 6 条 text 时，最小相邻对合并"""
    long_text = "。".join(f"这是第{i}句话内容" for i in range(1, 11)) + "。"
    result = split_response(long_text)
    text_count = sum(1 for s in result if s["kind"] == "text")
    assert text_count <= 6


def test_actions_dont_count_towards_text_cap():
    """3 个 action + 6 个 text 应全部保留"""
    result = split_response(
        "（笑）这是第一句话啊。（点头）这是第二句话啊。（歪头）这是第三句话啊。"
        "这是第四句话啊。这是第五句话啊。这是第六句话啊。"
    )
    text_count = sum(1 for s in result if s["kind"] == "text")
    action_count = sum(1 for s in result if s["kind"] == "action")
    assert text_count == 6
    assert action_count == 3


def test_order_preserved():
    """交错的 action 和 text 顺序必须保留"""
    result = split_response("A句话很长哦。（动作一）B句话也很长哦。（动作二）C句话也一样长哦。")
    kinds = [s["kind"] for s in result]
    assert kinds == ["text", "action", "text", "action", "text"]


def test_multiple_terminators_grouped():
    """连续问号/感叹号视为一个终止符"""
    result = split_response("真的吗好意外呀？！我不敢相信这件事！")
    text = [s for s in result if s["kind"] == "text"]
    assert len(text) == 2
    assert text[0]["content"] == "真的吗好意外呀？！"


def test_action_without_dialog():
    """整段全是动作"""
    result = split_response("（她转身离开）")
    assert result == [{"kind": "action", "content": "她转身离开"}]


def test_no_terminator_single_segment():
    """一句没标点的对白不拆"""
    result = split_response("你今天真的很好看")
    assert result == [{"kind": "text", "content": "你今天真的很好看"}]


def test_corner_quote_wraps_terminator_stays_atomic():
    """`「今晚别走。」` — 终止符在角引号内，不切分，不留孤儿 `」`。"""
    result = split_response("「今晚别走。」")
    assert result == [{"kind": "text", "content": "「今晚别走。」"}]


def test_corner_quote_ellipsis_stays_atomic():
    """`「……不说了。」` — 省略号+句号在角引号内也不拆。"""
    result = split_response("「……不说了。」")
    assert result == [{"kind": "text", "content": "「……不说了。」"}]


def test_corner_quote_then_outside_terminator_splits():
    """引号闭合后外面的终止符仍触发正常切分。"""
    result = split_response("「你说什么。」我听不清。她小声说。")
    texts = [s["content"] for s in result if s["kind"] == "text"]
    assert texts == ["「你说什么。」我听不清。", "她小声说。"]


def test_corner_quote_after_normal_sentence():
    """引号前面正常句子先切，引号自身保持完整。"""
    result = split_response("嗯。「我在。」")
    assert result == [{"kind": "text", "content": "嗯。「我在。」"}]


def test_action_paren_then_corner_quote():
    """动作括号与角引号并存 — 动作归 action，引号归 text 且不拆。"""
    result = split_response("（凛低头）「不说了。」")
    assert result[0] == {"kind": "action", "content": "凛低头"}
    assert result[1] == {"kind": "text", "content": "「不说了。」"}


def test_unmatched_close_corner_quote_is_defensive():
    """孤立 `」` 不导致负深度或异常，仍走正常终止符切分。"""
    result = split_response("」孤儿。你好呀。")
    texts = [s["content"] for s in result if s["kind"] == "text"]
    assert texts == ["」孤儿。你好呀。"]


# ── Post-hoc bracket wrapping (rin turn-2 regression, Plan B) ─────────────────


def test_bare_action_prose_before_dialog_is_wrapped():
    """`目光微微闪动，随即移开视线 不。` → action bubble + dialog bubble."""
    result = split_response("目光微微闪动，随即移开视线 不。")
    kinds = [s["kind"] for s in result]
    assert "action" in kinds
    action = next(s for s in result if s["kind"] == "action")
    assert "目光微微闪动" in action["content"]
    text = next(s for s in result if s["kind"] == "text")
    assert text["content"].startswith("不")


def test_bare_action_mid_stream_wraps_between_dialog():
    """`你叫对了。声音轻了几分…疲惫 只是…` — dialog + action + dialog."""
    result = split_response(
        "你叫对了。声音轻了几分，带着一丝难以察觉的疲惫 只是…被太久没人叫过的名字突然喊住，有点不习惯罢了。"
    )
    # Must include the action span; the exact bubble count may vary due to the
    # short-text merger, so verify the action was extracted.
    actions = [s["content"] for s in result if s["kind"] == "action"]
    assert any("声音轻了几分" in a for a in actions)
    joined_text = "".join(s["content"] for s in result if s["kind"] == "text")
    assert "你叫对了" in joined_text
    assert "只是" in joined_text


def test_bare_action_no_dialog_wraps_whole_piece():
    """`目光微微闪动。` — action-only piece wrapped as an action bubble."""
    result = split_response("目光微微闪动。")
    kinds = [s["kind"] for s in result]
    assert kinds == ["action"]
    assert "目光微微闪动" in result[0]["content"]


def test_explicit_brackets_still_win_over_wrapper():
    """If the LLM already brackets, the heuristic must not double-wrap."""
    result = split_response("（目光微垂）好的。")
    action = next(s for s in result if s["kind"] == "action")
    # Must be the LLM's original content, not '目光微垂）好的' or similar.
    assert action["content"] == "目光微垂"
    text = next(s for s in result if s["kind"] == "text")
    assert text["content"] == "好的。"


def test_plain_dialog_without_action_subject_is_untouched():
    """Regular replies with no body-part noun stay pure text."""
    result = split_response("你今天怎么样，还好吗？我有点担心你。")
    kinds = [s["kind"] for s in result]
    assert kinds == ["text", "text"]


def test_long_action_bracket_with_internal_newline_stays_atomic():
    """`（...嘲讽\n急着走？） 俯身...` — regression from live-chat report.

    The LLM sometimes drops a newline inside a long action bracket. The old
    `_ACTION_RE` character class excluded `\\n`, so the closing `）` leaked
    into a text bubble that started with `）`. Content must stay one action
    bubble; interior newline collapses to a space.
    """
    raw = (
        "（指尖轻抬，一缕暗紫色魔力缠绕上你的手腕，语气带着淡淡的嘲讽\n"
        "急着走？）俯身在你耳边，声音压得极低 你以为惹怒我，还能全身而退吗？"
    )
    result = split_response(raw)
    # First segment must be a single action bubble containing the full span.
    assert result[0]["kind"] == "action"
    assert "指尖轻抬" in result[0]["content"]
    assert "急着走？" in result[0]["content"]
    # No orphan `）` sitting alone in a text bubble.
    text_contents = [s["content"] for s in result if s["kind"] == "text"]
    assert all(not tc.lstrip().startswith("）") for tc in text_contents)
    # Interior newline is collapsed — grey pill renders as a single line.
    assert "\n" not in result[0]["content"]
