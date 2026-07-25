"""Unit tests for SS09 GM prompt assembly + bubble splitting (PR3)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4


def json_dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)

from heart.ss09_story.models import Run, Scenario, StoryMessage
from heart.ss09_story.prompt import (
    build_gm_messages,
    build_gm_system_prompt,
    build_memory_update_messages,
    parse_memory_update,
    split_gm_text,
)
from heart.ss09_story.prompt import _render_story_memory  # noqa: E402


def _scenario(prompt: str = "这是一个测试剧本原文。") -> Scenario:
    return Scenario(
        id=uuid4(),
        slug="test",
        title="测试剧本",
        genre="悬疑",
        cover_url=None,
        blurb="一段测试",
        maturity="all_ages",
        gm_system_prompt=prompt,
        player_template_json={},
        status="published",
        is_featured=False,
        play_count=0,
    )


def _run(
    summary: str = "",
    identity: dict | None = None,
    story_memory: dict | None = None,
) -> Run:
    now = datetime.now(timezone.utc)
    return Run(
        id=uuid4(),
        user_id=uuid4(),
        scenario_id=uuid4(),
        player_identity_json=identity or {"name": "阿远", "gender": "男"},
        title="测试剧本",
        summary=summary,
        summary_watermark=0,
        turn_count=0,
        status="active",
        model="deepseek",
        created_at=now,
        last_activity_at=now,
        story_memory=story_memory if story_memory is not None else {},
    )


def _msg(role: str, content: str, seq: int, kind: str = "narration", npc: str | None = None):
    return StoryMessage(
        id=uuid4(),
        run_id=uuid4(),
        turn_id=uuid4(),
        seq=seq,
        role=role,
        kind=kind,
        npc_name=npc,
        content=content,
        created_at=datetime.now(timezone.utc),
    )


# ── split_gm_text ───────────────────────────────────────────────────


def test_split_narration_only():
    out = split_gm_text("【旁白】夜色降临，街道空无一人。")
    assert len(out) == 1
    assert out[0]["kind"] == "narration"
    assert "夜色降临" in out[0]["content"]
    assert "【旁白】" not in out[0]["content"]  # prefix stripped


def test_split_npc_dialogue():
    out = split_gm_text("**林深** 你终于来了。")
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["npc_name"] == "林深"
    assert out[0]["content"] == "你终于来了。"


def test_split_action_line():
    out = split_gm_text("（你听见身后传来脚步声）")
    assert len(out) == 1
    assert out[0]["kind"] == "action"
    assert "脚步声" in out[0]["content"]


def test_split_interleaved_order_preserved():
    text = (
        "【旁白】雨下得很大。\n"
        "**林深** 快进来避雨吧。\n"
        "（他递来一把伞）"
    )
    out = split_gm_text(text)
    assert [b["kind"] for b in out] == ["narration", "dialogue", "action"]
    assert out[1]["npc_name"] == "林深"


def test_split_consecutive_prose_merges_into_one_narration():
    out = split_gm_text("第一句描写。\n第二句描写。")
    assert len(out) == 1
    assert out[0]["kind"] == "narration"
    assert "第一句" in out[0]["content"] and "第二句" in out[0]["content"]


def test_split_degrades_to_single_narration_when_unstructured():
    # No markers at all, but there IS prose → one narration bubble.
    out = split_gm_text("完全没有任何格式标记的一段普通文字")
    assert len(out) == 1
    assert out[0]["kind"] == "narration"


def test_split_empty_returns_empty():
    assert split_gm_text("") == []
    assert split_gm_text("   \n  ") == []


# ── pending-speaker: bare `**角色名**` line + 台词 on the next line ────
# Regression for the empty-oval bug: the model sometimes splits name and 台词
# across two lines. The bare speaker must NOT emit an empty dialogue bubble; the
# following prose line becomes that speaker's 台词.


def test_split_bare_speaker_attaches_next_line_as_dialogue():
    out = split_gm_text("**贺听澜**\n贺家不缺摆件，缺的是能扛事的人。")
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["npc_name"] == "贺听澜"
    assert out[0]["content"] == "贺家不缺摆件，缺的是能扛事的人。"
    # No empty-content bubble slipped through.
    assert all((b.get("content") or "").strip() for b in out)


def test_split_bare_speaker_at_eof_drops_silently():
    # A lone `**name**` with nothing after it → no bubble at all (no empty oval).
    assert split_gm_text("**贺听澜**") == []


def test_split_bare_speaker_dropped_when_followed_by_narration():
    out = split_gm_text("**贺听澜**\n【旁白】夜色渐深。")
    assert len(out) == 1
    assert out[0]["kind"] == "narration"
    assert out[0]["npc_name"] is None
    assert "夜色渐深" in out[0]["content"]


def test_split_same_line_speaker_still_works():
    # Same-line `**name** 台词` is the happy path and must be unchanged.
    out = split_gm_text("**贺听澜** 你来了。")
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["npc_name"] == "贺听澜"
    assert out[0]["content"] == "你来了。"


def test_split_bare_speaker_blank_line_before_dialogue_survives():
    out = split_gm_text("**贺听澜**\n\n贺家不缺摆件。")
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["npc_name"] == "贺听澜"
    assert out[0]["content"] == "贺家不缺摆件。"


def test_split_consecutive_bare_speakers_first_dropped():
    out = split_gm_text("**甲**\n**乙** 台词")
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["npc_name"] == "乙"
    assert out[0]["content"] == "台词"


# ── off-contract markup normalisation (pre-clean) ───────────────────


def test_split_unwraps_latex_colorbox_to_dialogue():
    # 笼中鸟 / 雨停 / 为躲雨 / 再见蚊子 style: LaTeX speech bubble → dialogue bubble.
    line = r"\(\colorbox{white}{\textcolor{blue}{\text{你终于回来了}}}\)"
    out = split_gm_text(line)
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["content"] == "你终于回来了"
    # No raw LaTeX leaks into the rendered content.
    assert "colorbox" not in out[0]["content"]
    assert "\\text" not in out[0]["content"]


def test_split_strips_markdown_code_fence_keeps_inner_as_narration():
    # 小姐与狗 / 哥承认爱我 style: ```text 心理活动 code block → plain narration.
    text = "```text\n她其实很紧张。\n心跳得厉害。\n```"
    out = split_gm_text(text)
    assert len(out) == 1
    assert out[0]["kind"] == "narration"
    assert "```" not in out[0]["content"]
    assert "她其实很紧张" in out[0]["content"]


def test_split_strips_danmu_marker_prefix():
    out = split_gm_text("【弹幕】前排围观，主播好帅")
    assert len(out) == 1
    assert out[0]["kind"] == "narration"
    assert "【弹幕】" not in out[0]["content"]
    assert "前排围观" in out[0]["content"]


def test_split_drops_horizontal_rule_lines():
    out = split_gm_text("第一段。\n---\n**林深** 你来了。")
    kinds = [b["kind"] for b in out]
    assert "dialogue" in kinds
    assert all("---" not in b["content"] for b in out)


def test_preclean_leaves_compliant_text_semantically_unchanged():
    # A fully-compliant turn must classify exactly as before the pre-clean.
    text = "【旁白】夜色降临。\n**林深** 你来了。\n（他走近）"
    out = split_gm_text(text)
    assert [b["kind"] for b in out] == ["narration", "dialogue", "action"]
    assert out[1]["npc_name"] == "林深"


# ── build_gm_system_prompt ──────────────────────────────────────────


def test_system_prompt_embeds_scenario_verbatim():
    raw = "★特殊剧本原文★ 保留一切原样"
    sp = build_gm_system_prompt(_scenario(raw), _run())
    assert raw in sp  # raw injection, not paraphrased


def test_system_prompt_renders_player_card_and_summary():
    run = _run(summary="主控已经进入了古宅。", identity={"name": "阿远", "identity": "记者"})
    sp = build_gm_system_prompt(_scenario(), run)
    assert "阿远" in sp
    assert "记者" in sp
    assert "前情提要" in sp
    assert "古宅" in sp


def test_system_prompt_omits_summary_when_empty():
    sp = build_gm_system_prompt(_scenario(), _run(summary=""))
    assert "前情提要" not in sp


# ── build_gm_messages ───────────────────────────────────────────────


def test_build_messages_role_mapping():
    scenario = _scenario()
    run = _run()
    turns = [
        _msg("player", "我推开门。", 1),
        _msg("gm", "门后是一条长廊。", 2, kind="narration"),
        _msg("npc", "别过来。", 3, kind="dialogue", npc="林深"),
    ]
    msgs = build_gm_messages(scenario, run, turns)
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "我推开门。"}
    assert msgs[2]["role"] == "assistant"
    # NPC line re-tagged with speaker for continuity.
    assert msgs[3]["role"] == "assistant"
    assert "**林深**" in msgs[3]["content"]


# ââ Chinese curly-quote dialogue (regression: 2026-07 bubble bug) ââââ
# DeepSeek emits full-width curly quotes ââ¦â (U+201C/U+201D), not ASCII ".
# The old regex only matched U+0022 â dialogue fell through to narration.


def test_split_chinese_curly_quote_dialogue():
    """Dialogue in Chinese curly quotes must parse as a dialogue bubble."""
    out = split_gm_text("“你来了。”")  # âä½ æ¥äºãâ
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["content"] == "你来了。"  # ä½ æ¥äºã (quotes stripped)


def test_split_mixed_action_and_curly_dialogue_same_line():
    """ï¼å¨ä½ï¼âå¯¹è¯â on one line â action bubble + dialogue bubble, in order."""
    # ï¼ä»èµ°è¿ä½ ï¼âä½ æ¥äºãâ
    line = "（他走近你）“你来了。”"
    out = split_gm_text(line)
    assert [b["kind"] for b in out] == ["action", "dialogue"]
    assert out[0]["content"] == "他走近你"  # ä»èµ°è¿ä½ 
    assert out[1]["content"] == "你来了。"  # ä½ æ¥äºã


def test_split_ascii_quote_still_works():
    """ASCII double quotes remain supported (backward compat)."""
    out = split_gm_text('（点头）"好的。"')  # ï¼ç¹å¤´ï¼"å¥½çã"
    assert [b["kind"] for b in out] == ["action", "dialogue"]
    assert out[1]["content"] == "好的。"  # å¥½çã


def test_split_npc_line_strips_curly_quotes():
    """**è§è²å**âå°è¯â â dialogue with curly quotes stripped from content."""
    # **ææ·±**âä½ ç»äºæ¥äºãâ
    line = "**林深**“你终于来了。”"
    out = split_gm_text(line)
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["npc_name"] == "林深"  # ææ·±
    assert out[0]["content"] == "你终于来了。"  # ä½ ç»äºæ¥äºã (no quotes)


# ââ _render_player_card multi-select values (2026-07 form extraction) â
from heart.ss09_story.prompt import _render_player_card  # noqa: E402


def test_render_player_card_joins_list_values():
    """A checkbox multi-select value (list) renders as é¡¿å·-joined, not a repr."""
    card = _render_player_card({
        "name": "小明",           # å°æ
        "preferences": ["办公室恋", "背德感"],  # [åå¬å®¤æ, èå¾·æ]
    })
    assert "办公室恋、背德感" in card  # åå¬å®¤æãèå¾·æ
    assert "[" not in card and "'" not in card  # no python list repr


def test_render_player_card_uses_known_label_for_mode():
    card = _render_player_card({"mode": "18禁模式"})  # 18ç¦æ¨¡å¼
    assert card.startswith("- 模式：")  # - æ¨¡å¼ï¼


def test_render_player_card_skips_empty_list():
    card = _render_player_card({"name": "阿远", "preferences": []})  # é¿è¿, []
    assert "阿远" in card
    assert "设定偏好" not in card  # è®¾å®åå¥½ absent


def test_split_corner_quote_dialogue():
    """Corner quotes 「」 should be recognized as dialogue (2026-07 multi-quote fix)."""
    line = "**纳西缇** 「外面危险。」"
    out = split_gm_text(line)
    assert len(out) == 1
    assert out[0]["kind"] == "dialogue"
    assert out[0]["npc_name"] == "纳西缇"
    assert out[0]["content"] == "外面危险。"


def test_split_mixed_action_and_corner_dialogue():
    """Mixed line: （action）「dialogue」 should split correctly."""
    line = "（他走近你）「你来了。」"
    out = split_gm_text(line)
    assert [b["kind"] for b in out] == ["action", "dialogue"]
    assert out[0]["content"] == "他走近你"
    assert out[1]["content"] == "你来了。"


# ── Tier 2 structured 剧情记忆卡 (story memory card) ─────────────────────


def _sample_memory() -> dict:
    return {
        "npcs": {
            "贺听澜": {
                "relationship": "对主控警惕渐生好感",
                "facts": ["贺家长子", "答应带主控见家人"],
                "last_state": "离开书房",
            }
        },
        "player_facts": ["自称记者", "左手受过伤"],
        "world_facts": ["贺家老宅今夜停电"],
        "open_threads": ["密室钥匙下落不明"],
    }


# ── parse_memory_update ─────────────────────────────────────────────


def test_parse_memory_update_valid_json():
    raw = (
        '{"summary": "主控进入贺家老宅。", '
        '"memory": {"npcs": {"贺听澜": {"relationship": "警惕", '
        '"facts": ["贺家长子"], "last_state": "书房"}}, '
        '"player_facts": ["记者"]}}'
    )
    parsed = parse_memory_update(raw)
    assert parsed is not None
    summary, memory = parsed
    assert summary == "主控进入贺家老宅。"
    assert memory["npcs"]["贺听澜"]["relationship"] == "警惕"
    assert memory["npcs"]["贺听澜"]["facts"] == ["贺家长子"]
    assert memory["player_facts"] == ["记者"]


def test_parse_memory_update_strips_json_fence():
    raw = (
        "```json\n"
        '{"summary": "夜色渐深。", "memory": {"world_facts": ["停电"]}}\n'
        "```"
    )
    parsed = parse_memory_update(raw)
    assert parsed is not None
    summary, memory = parsed
    assert summary == "夜色渐深。"
    assert memory["world_facts"] == ["停电"]


def test_parse_memory_update_bare_fence():
    raw = '```\n{"summary": "abc", "memory": {}}\n```'
    parsed = parse_memory_update(raw)
    assert parsed is not None
    summary, memory = parsed
    assert summary == "abc"
    assert memory == {}  # empty memory sections dropped


def test_parse_memory_update_garbage_returns_none():
    assert parse_memory_update("这不是 JSON，只是一段普通的前情提要。") is None
    assert parse_memory_update("") is None
    assert parse_memory_update("   ") is None
    # A JSON array (not object) is not usable → None.
    assert parse_memory_update("[1, 2, 3]") is None


def test_parse_memory_update_missing_summary_yields_empty_string():
    parsed = parse_memory_update('{"memory": {"player_facts": ["x"]}}')
    assert parsed is not None
    summary, memory = parsed
    assert summary == ""
    assert memory["player_facts"] == ["x"]


def test_parse_memory_update_caps_npcs_at_eight():
    npcs = {f"角色{i}": {"facts": [f"事实{i}"]} for i in range(20)}
    raw = json_dumps({"summary": "s", "memory": {"npcs": npcs}})
    parsed = parse_memory_update(raw)
    assert parsed is not None
    _, memory = parsed
    assert len(memory["npcs"]) == 8  # _MEM_MAX_NPCS


def test_parse_memory_update_caps_facts_per_npc():
    raw = json_dumps(
        {
            "summary": "s",
            "memory": {"npcs": {"甲": {"facts": [f"f{i}" for i in range(20)]}}},
        }
    )
    parsed = parse_memory_update(raw)
    assert parsed is not None
    _, memory = parsed
    assert len(memory["npcs"]["甲"]["facts"]) == 6  # _MEM_MAX_FACTS


def test_parse_memory_update_dedups_and_caps_lists():
    raw = json_dumps(
        {"summary": "s", "memory": {"player_facts": ["同一条", "同一条"] + [f"x{i}" for i in range(20)]}}
    )
    parsed = parse_memory_update(raw)
    assert parsed is not None
    _, memory = parsed
    facts = memory["player_facts"]
    assert facts.count("同一条") == 1  # de-duped
    assert len(facts) == 8  # _MEM_MAX_LIST


def test_parse_memory_update_drops_offshape_npc_entry():
    # A non-dict NPC entry is skipped rather than crashing.
    raw = json_dumps({"summary": "s", "memory": {"npcs": {"坏值": "不是对象", "甲": {"facts": ["ok"]}}}})
    parsed = parse_memory_update(raw)
    assert parsed is not None
    _, memory = parsed
    assert "坏值" not in memory["npcs"]
    assert memory["npcs"]["甲"]["facts"] == ["ok"]


# ── _render_story_memory ────────────────────────────────────────────


def test_render_story_memory_renders_all_sections():
    block = _render_story_memory(_sample_memory())
    assert "【角色记忆 / 剧情档案】" in block
    assert "贺听澜" in block
    assert "对主控警惕渐生好感" in block
    assert "贺家长子" in block
    assert "记者" in block  # player_facts
    assert "停电" in block  # world_facts
    assert "密室钥匙" in block  # open_threads


def test_render_story_memory_empty_returns_empty_string():
    assert _render_story_memory({}) == ""
    assert _render_story_memory(None) == ""  # defensive: off-shape → ""


def test_render_story_memory_skips_empty_sections():
    block = _render_story_memory({"npcs": {"甲": {"facts": ["事实"]}}})
    assert "甲" in block
    assert "主控相关" not in block  # empty player_facts section omitted
    assert "世界设定" not in block
    assert "未解悬念" not in block


def test_render_story_memory_all_empty_npc_yields_empty():
    # NPC with nothing useful + no other sections → whole block empty.
    assert _render_story_memory({"npcs": {"甲": {}}}) == ""


# ── build_gm_system_prompt memory injection ─────────────────────────


def test_system_prompt_includes_memory_block_when_present():
    run = _run(story_memory=_sample_memory())
    sp = build_gm_system_prompt(_scenario(), run)
    assert "【角色记忆 / 剧情档案】" in sp
    assert "贺听澜" in sp
    assert "答应带主控见家人" in sp


def test_system_prompt_omits_memory_block_when_empty():
    sp = build_gm_system_prompt(_scenario(), _run(story_memory={}))
    assert "角色记忆" not in sp


def test_system_prompt_memory_and_summary_coexist():
    run = _run(summary="主控已进入古宅。", story_memory=_sample_memory())
    sp = build_gm_system_prompt(_scenario(), run)
    assert "前情提要" in sp and "古宅" in sp
    assert "角色记忆" in sp and "贺听澜" in sp


# ── build_memory_update_messages ────────────────────────────────────


def test_memory_update_messages_carry_merge_instruction_and_prior():
    prior = _sample_memory()
    turns = [
        _msg("player", "我走进书房。", 1),
        _msg("npc", "你来做什么？", 2, kind="dialogue", npc="贺听澜"),
    ]
    msgs = build_memory_update_messages(_scenario(), "旧的前情提要。", prior, turns)
    assert msgs[0]["role"] == "system"
    assert "增量合并" in msgs[0]["content"]  # MERGE semantics
    assert "JSON" in msgs[0]["content"]
    user = msgs[1]["content"]
    assert "旧的前情提要。" in user  # prior summary in context
    assert "贺听澜" in user  # prior memory serialized into context
    assert "我走进书房。" in user  # new transcript folded in


def test_memory_update_messages_handle_empty_prior():
    turns = [_msg("player", "开场。", 1)]
    msgs = build_memory_update_messages(_scenario(), "", {}, turns)
    user = msgs[1]["content"]
    assert "（无）" in user  # empty prior summary rendered as placeholder
    assert "{}" in user  # empty prior memory serialized as {}


# ── replay isolation: 重新游玩 = 记忆天然清空 ──────────────────────────


def test_fresh_run_has_empty_memory_by_default():
    """A run constructed without story_memory (mirrors create_run's DB default)
    starts with an empty card, so 重新游玩 never inherits the prior run's NPC
    memory."""
    run = _run()
    assert run.story_memory == {}
    sp = build_gm_system_prompt(_scenario(), run)
    assert "角色记忆" not in sp
