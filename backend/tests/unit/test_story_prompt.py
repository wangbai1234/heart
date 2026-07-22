"""Unit tests for SS09 GM prompt assembly + bubble splitting (PR3)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from heart.ss09_story.models import Run, Scenario, StoryMessage
from heart.ss09_story.prompt import (
    build_gm_messages,
    build_gm_system_prompt,
    split_gm_text,
)


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


def _run(summary: str = "", identity: dict | None = None) -> Run:
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
