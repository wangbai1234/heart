"""Unit tests for SS10 opening prompt building + splitting.

Covers the diversity-axis sampling (anti mode-collapse), the format contract
the splitter depends on, and the split_opening parser itself.
"""

from __future__ import annotations

import random

from heart.ss10_opening.prompt import ENTRY_ANGLES, PACING, TIME_TONES
from heart.ss10_opening.prompt_builder import build_opening_prompt
from heart.ss10_opening.splitter import split_opening


def _prompt(**kw) -> str:
    msgs = build_opening_prompt(
        display_name="测试角色",
        persona="一个沉默寡言的旧书店老板",
        **kw,
    )
    assert len(msgs) == 1 and msgs[0]["role"] == "system"
    return msgs[0]["content"]


def test_samples_one_from_each_axis():
    """A seeded rng must inject exactly the chosen axis lines."""
    rng = random.Random(42)
    entry = rng.choice(ENTRY_ANGLES)
    time = rng.choice(TIME_TONES)
    pace = rng.choice(PACING)

    content = _prompt(greeting_style="reserved", rng=random.Random(42))
    assert entry in content
    assert time in content
    assert pace in content


def test_different_seeds_produce_different_prompts():
    """Randomness must actually vary output across generations."""
    seen = {_prompt(rng=random.Random(s)) for s in range(20)}
    # 7 x 6 x 5 = 210 combos; 20 seeds should yield many distinct prompts.
    assert len(seen) > 5


def test_no_hardcoded_location_pool():
    """Scene must be character-driven — no fixed venue leaking from a pool."""
    content = _prompt()
    # The old template hardcoded these; they must not be prescribed anymore.
    for banned in ("咖啡厅", "便利店", "图书馆", "天台"):
        assert f"【场景氛围】{banned}" not in content


def test_format_contract_present():
    """Splitter relies on （）=action / plain=text; prompt must instruct it."""
    content = _prompt()
    assert "（）" in content
    assert "不加引号" in content


def test_forbids_cliches():
    content = _prompt()
    assert "下雨" in content  # appears inside the 禁止 clause


def test_split_opening_preserves_order_and_kind():
    raw = "（黄昏，旧书店的光斜进来）\n你来得正好。（他抬眼，指尖还夹着一页纸）"
    bubbles = split_opening(raw)
    kinds = [b.kind for b in bubbles]
    assert kinds == ["action", "text", "action"]
    assert bubbles[0].content == "黄昏，旧书店的光斜进来"
    assert bubbles[1].content == "你来得正好。"


def test_split_opening_plain_text_only():
    bubbles = split_opening("你终于来了。")
    assert len(bubbles) == 1
    assert bubbles[0].kind == "text"


def test_split_opening_empty():
    assert split_opening("   ") == []


def test_split_opening_strips_wrapping_curly_quotes():
    # 用户习惯把整段对白用中文双引号包裹 —— 气泡本身已表示"这是说话"，剥掉冗余外层。
    bubbles = split_opening("“你终于来了。”")
    assert len(bubbles) == 1
    assert bubbles[0].kind == "text"
    assert bubbles[0].content == "你终于来了。"


def test_split_opening_strips_wrapping_straight_quotes():
    bubbles = split_opening('"坐吧，我等你很久了。"')
    assert bubbles[0].content == "坐吧，我等你很久了。"


def test_split_opening_strips_quotes_per_dialogue_segment():
    raw = "（他倚在门框上）“来得比我想的早。”"
    bubbles = split_opening(raw)
    assert [b.kind for b in bubbles] == ["action", "text"]
    assert bubbles[0].content == "他倚在门框上"
    assert bubbles[1].content == "来得比我想的早。"


def test_split_opening_keeps_inner_quotation():
    # 段落中间真正引用别人的话 —— 不是整段包裹，保持原样不误伤。
    raw = "他说“别走”，然后转身离开。"
    bubbles = split_opening(raw)
    assert bubbles[0].content == raw


def test_split_opening_leaves_unbalanced_quote():
    # 只有开引号、没有闭引号 —— 保守不动。
    bubbles = split_opening("“你来了")
    assert bubbles[0].content == "“你来了"
