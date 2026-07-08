"""
Unit tests for the character content registry (UGC refactor C1).

The registry is the single source for per-character operational copy that used
to be scattered as inline ``{"rin": ..., "dorothy": ...}`` dicts across SS06.
These tests pin the exact content (a regression anchor proving the C1 move is
byte-identical) and the fallback semantics the accessors must preserve.
"""

from __future__ import annotations

from heart.ss01_soul.character_content import (
    CHARACTER_CONTENT,
    get_display_name,
    get_proactive_persona,
    get_proactive_templates,
    get_ritual_greeting,
)

# ── Behavior preservation: exact content anchors ────────────────────────────


def test_rin_persona_unchanged():
    assert get_proactive_persona("rin") == (
        "神无月凛：清冷、话少、口是心非的傲娇，关心藏在简短的话里，绝不肉麻。"
    )


def test_dorothy_persona_unchanged():
    assert get_proactive_persona("dorothy") == (
        "桃桃：活泼、元气、粘人，用感叹号和叠词，热情直接地表达想念。"
    )


def test_rin_templates_unchanged():
    templates = get_proactive_templates("rin")
    assert len(templates) == 8
    assert "……突然想你了。没什么事，就是想告诉你。" in templates
    assert "下雨了。记得带伞。" in templates


def test_dorothy_templates_unchanged():
    templates = get_proactive_templates("dorothy")
    assert len(templates) == 8
    assert "你今天怎么样呀？桃桃突然好想你！" in templates


def test_ritual_greetings_unchanged():
    assert get_ritual_greeting("rin", "morning") == "早安。"
    assert get_ritual_greeting("rin", "night") == "晚安。明天见。"
    assert get_ritual_greeting("dorothy", "morning") == "早安早安！新的一天开始啦！"
    assert get_ritual_greeting("dorothy", "night") == "晚安晚安！做个好梦哦！"


# ── Fallback semantics (must match the code the accessors replaced) ─────────


def test_unknown_persona_falls_back_to_id():
    # Previously: PROACTIVE_PERSONA.get(cid, cid)
    assert get_proactive_persona("unknown_char") == "unknown_char"


def test_unknown_templates_fall_back_to_fallback_character():
    # Previously: PROACTIVE_TEMPLATES.get(cid, PROACTIVE_TEMPLATES["rin"])
    assert get_proactive_templates("unknown_char") == get_proactive_templates("rin")


def test_unknown_ritual_falls_back_to_fallback_character():
    # Previously: templates.get(cid, templates.get("rin", "早安。"))
    assert get_ritual_greeting("unknown_char", "morning") == "早安。"
    assert get_ritual_greeting("unknown_char", "night") == "晚安。明天见。"


def test_templates_accessor_returns_a_copy():
    """Callers must not be able to mutate the single source of truth."""
    first = get_proactive_templates("rin")
    first.append("mutated")
    assert "mutated" not in get_proactive_templates("rin")
    assert "mutated" not in CHARACTER_CONTENT["rin"]["proactive_templates"]


# ── Display name derived from the Soul Spec ─────────────────────────────────


def test_display_name_derived_from_soul_spec():
    # Rin's Soul Spec declares display_name.zh = "神无月 凛" (note the space) —
    # the accessor must return the spec value verbatim, not a hardcoded name.
    assert get_display_name("rin") == "神无月 凛"


def test_display_name_unknown_falls_back_to_id():
    assert get_display_name("not_a_registered_character") == "not_a_registered_character"
