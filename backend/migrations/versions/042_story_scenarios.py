"""042 — Story/剧情 mode: scenarios, runs, and message transcripts.

Why
---
Heart is upgrading from an "AI chat tool" to an "AI companion + interactive
story platform". The first-stage feature is **Story mode**: the AI acts as a
GM (game master) that runs a turn-based interactive plot, with the user as the
"主控" (player). See docs / the story-mode plan for product context.

Three new tables, deliberately independent of the existing chat pipeline:

- ``story_scenarios`` — the imported script catalog. ``gm_system_prompt`` holds
  the (verbatim) source .txt used as the GM system prompt. ``maturity`` gates
  adult scenarios behind the existing age-gate (users.age_verified_at).
- ``story_runs`` — one row per playthrough. A user can start MANY runs of the
  same scenario, so this deliberately has **no** UNIQUE(user_id, scenario_id)
  constraint (contrast the ``sessions`` table's UNIQUE(user_id, character_id)).
- ``story_messages`` — the turn-by-turn transcript. Its own role/kind CHECKs
  (player/gm/npc/system) — it does NOT reuse ``chat_messages`` (whose role is
  CHECK IN ('user','assistant') and which is hash-partitioned + coupled to the
  inbox / memory cold-path / read-state).

Idempotent: all DDL uses IF NOT EXISTS; seed rows use ON CONFLICT DO NOTHING.
The two seed scenarios let the read API return data before the bulk importer
(scripts/import_scenarios.py) runs; they are all-ages and marked published.

Revision ID: 042_story_scenarios
Revises: 041_rin_mp3_reference
Create Date: 2026-07-22
"""

from __future__ import annotations

from alembic import op

revision = "042_story_scenarios"
down_revision = "041_rin_mp3_reference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- story_scenarios: imported script catalog ---------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS story_scenarios (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug                TEXT NOT NULL UNIQUE,
            title               TEXT NOT NULL,
            genre               TEXT NOT NULL DEFAULT '其他',
            cover_url           TEXT,
            blurb               TEXT NOT NULL DEFAULT '',
            maturity            TEXT NOT NULL DEFAULT 'all_ages'
                                    CHECK (maturity IN ('all_ages', 'adult')),
            gm_system_prompt    TEXT NOT NULL,
            player_template_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            status              TEXT NOT NULL DEFAULT 'draft'
                                    CHECK (status IN ('draft', 'published', 'archived')),
            is_featured         BOOLEAN NOT NULL DEFAULT false,
            play_count          BIGINT NOT NULL DEFAULT 0,
            source_hash         TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_story_scenarios_browse "
        "ON story_scenarios (status, is_featured, genre)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_story_scenarios_genre ON story_scenarios (genre)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_story_scenarios_maturity ON story_scenarios (maturity)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_story_scenarios_play_count "
        "ON story_scenarios (play_count DESC)"
    )

    # --- story_runs: one row per playthrough (many per user) ----------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS story_runs (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL,
            scenario_id         UUID NOT NULL REFERENCES story_scenarios(id),
            player_identity_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            title               TEXT NOT NULL DEFAULT '',
            summary             TEXT NOT NULL DEFAULT '',
            summary_watermark   INTEGER NOT NULL DEFAULT 0,
            turn_count          INTEGER NOT NULL DEFAULT 0,
            status              TEXT NOT NULL DEFAULT 'active'
                                    CHECK (status IN ('active', 'ended', 'deleted')),
            model               TEXT NOT NULL DEFAULT 'deepseek',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_activity_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_story_runs_user "
        "ON story_runs (user_id, status, last_activity_at DESC)"
    )

    # --- story_messages: turn-by-turn transcript ----------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS story_messages (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id      UUID NOT NULL REFERENCES story_runs(id) ON DELETE CASCADE,
            user_id     UUID NOT NULL,
            turn_id     UUID NOT NULL,
            seq         BIGINT NOT NULL,
            role        TEXT NOT NULL
                            CHECK (role IN ('player', 'gm', 'npc', 'system')),
            kind        TEXT NOT NULL DEFAULT 'narration'
                            CHECK (kind IN ('narration', 'dialogue', 'action')),
            npc_name    TEXT,
            content     TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_story_messages_run_seq ON story_messages (run_id, seq)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_story_messages_run_turn ON story_messages (run_id, turn_id)")

    # --- seed: two all-ages demo scenarios (separate from DDL) --------------
    # Kept minimal; the real 45-file catalog is loaded by the importer. These
    # exist so the read API returns data pre-importer. ON CONFLICT keeps re-run
    # idempotent and never clobbers an importer-updated row.
    op.execute(
        """
        INSERT INTO story_scenarios
            (slug, title, genre, blurb, maturity, gm_system_prompt,
             player_template_json, status, is_featured, play_count)
        VALUES
        (
            'seed-yuting-tianqing',
            '雨停，天晴',
            '校园恋爱',
            '两个把真实自己藏起来的人，在彼此面前卸下铠甲，完成双向救赎。',
            'all_ages',
            $prompt$你正在主持一个回合制剧情互动游戏，扮演男主，不允许 OOC。

【背景】两个把真实自己藏起来的人，在彼此面前卸下铠甲，因外力分离而受伤，最终在各自成长后完成双向救赎。校园暗恋、暧昧感为主，唯美青春基调。

【男主·程砚】身高 180cm；桃花眼微微下垂，眼下小痣勾人；年级前三，数学英语极优，体育好；表面骄傲臭屁、张扬明媚，实则因家庭管束极严而内心脆弱；面对感情别扭、爱说反话，怕被看穿，喜欢主控。

【输出格式】
- 用 `【旁白】` 标注场景、动作、环境描写。
- 用 `**角色名**` + 对话内容标注 NPC 说话。
- 用 `（动作/语气提示）` 穿插在对话或旁白中。
- 每次输出后必须停下，等待主控输入，绝不替主控行动。$prompt$,
            '{}'::jsonb,
            'published',
            true,
            0
        ),
        (
            'seed-lianyin',
            '联姻对象？好难选啊',
            '现代豪门',
            '开学季偶遇三位性格迥异的男主，上流宴会上你要选出联姻对象。',
            'all_ages',
            $prompt$你正在主持一个回合制剧情互动游戏，扮演所有 NPC。先婚后爱 / 欢喜冤家基调，感情循序渐进，保留每个人的骄傲与特色。贴近现代大学生活与豪门题材（社团、欢送会、研究所、酒吧、上流宴会）。

【男主1·纳兰辞】188cm，温柔淡漠，白天大学教授、晚上酒吧老板；爱好调酒、下棋、射击。
【男主2·梁琼】183cm，爱人面前傲娇、生人面前毒舌高冷，华清研究生、梁家少爷；爱好钢琴。
【男主3·沈汣】191cm，冷血无情、冷面心热，沈氏小儿子、表面华清拳击老师。

【输出格式】
- 用 `【旁白】` 标注场景、动作、环境描写。
- 用 `**角色名**` + 对话内容标注 NPC 说话。
- 用 `（动作/语气提示）` 穿插在对话或旁白中。
- 到上流宴会环节时，让主控在三位男主中选择联姻对象。
- 每次输出后必须停下，等待主控输入，绝不替主控行动。$prompt$,
            '{}'::jsonb,
            'published',
            false,
            0
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS story_messages")
    op.execute("DROP TABLE IF EXISTS story_runs")
    op.execute("DROP TABLE IF EXISTS story_scenarios")
