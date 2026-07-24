"""047 — Character↔Scenario story hooks (剧情邀约 / story-invitation cards).

Why
---
Wave 3 of the 羁绊中心 (bond center) adds a "剧情邀约卡": when a user's
relationship with a companion character reaches a configured threshold, the
companions view surfaces an invitation to play a linked 剧情 (SS09 scenario).

Until now there was **no link at all** between the ``characters`` catalog
(SS01) and ``story_scenarios`` (SS09) — scenarios are GM-driven multi-NPC
playthroughs whose "characters" live only as free text inside the GM prompt.
``character_story_hooks`` is that first, explicit, config-driven association.
It is deliberately a thin config table (no per-user state): eligibility is
computed at read time from the user's live relationship stage/intimacy, and the
per-user "don't nag me again" cooldown is enforced client-side (localStorage)
in V1 — see docs/execution/COMPANION_CENTER_FRONTEND_SPEC.md.

Table
-----
- ``character_story_hooks`` — one row per (character, scenario) invitation.
  - ``trigger_stage_min``  RAW SS04 stage enum (e.g. ``CONFIDANT``); the user's
    stage must rank >= this in STAGE_ORDER for the hook to be eligible.
  - ``trigger_intimacy_min`` FLOAT 0..1; user intimacy must be >= this.
  - ``cooldown_hours``     advisory; passed to the frontend for localStorage
    dismissal windows (no server-side per-user tracking in V1).
  - ``invite_title`` / ``invite_copy`` / ``cta_label`` — card copy.
  - ``enabled``            soft on/off without deleting the row.

Seed
----
One demo hook pairing the built-in character ``rin`` with ``seed-yuting-tianqing``
(《雨停，天晴》), resolved by slug so it works regardless of the scenario's
runtime-generated UUID. That scenario is a DDL-time ``published`` all-ages seed
in migration 042 — present on *every* environment (not importer-dependent) — so
the invitation card actually renders end-to-end (the /api/companions query
filters ``status='published'``). ON CONFLICT DO NOTHING and a slug-lookup that
no-ops when the scenario is absent keep this idempotent and safe. This is
placeholder content for a testable card; real hook curation happens in ops later.

Idempotent: CREATE TABLE IF NOT EXISTS; seed uses INSERT ... SELECT with
ON CONFLICT DO NOTHING. Raw SQL only, no business-code imports.

Revision ID: 047_character_story_hooks
Revises: 046_merge_022_045
Create Date: 2026-07-24
"""

from __future__ import annotations

from alembic import op

revision = "047_character_story_hooks"
down_revision = "046_merge_022_045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- character_story_hooks: config-driven character↔scenario invitations --
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS character_story_hooks (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            character_id         TEXT NOT NULL,
            scenario_id          UUID NOT NULL REFERENCES story_scenarios(id) ON DELETE CASCADE,
            trigger_stage_min    TEXT NOT NULL DEFAULT 'CONFIDANT',
            trigger_intimacy_min FLOAT NOT NULL DEFAULT 0.0
                                    CHECK (trigger_intimacy_min BETWEEN 0 AND 1),
            cooldown_hours       INTEGER NOT NULL DEFAULT 72,
            invite_title         TEXT NOT NULL DEFAULT '',
            invite_copy          TEXT NOT NULL DEFAULT '',
            cta_label            TEXT NOT NULL DEFAULT '进入剧情',
            enabled              BOOLEAN NOT NULL DEFAULT true,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (character_id, scenario_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_character_story_hooks_char "
        "ON character_story_hooks (character_id, enabled)"
    )

    # --- seed: demo hook rin ↔ 人外＊饲养指南 (slug-resolved, no-op if absent) ---
    # Separate from DDL. INSERT ... SELECT resolves the runtime scenario UUID by
    # slug; if the scenario isn't loaded yet the SELECT returns 0 rows (no insert).
    op.execute(
        """
        INSERT INTO character_story_hooks
            (character_id, scenario_id, trigger_stage_min, trigger_intimacy_min,
             cooldown_hours, invite_title, invite_copy, cta_label)
        SELECT
            'rin',
            s.id,
            'CONFIDANT',
            0.4,
            72,
            '她想带你回到那个夜晚',
            '从这一刻起，凛的故事线与你相连。她似乎想带你走进《雨停，天晴》的某个夜晚。',
            '进入剧情'
        FROM story_scenarios s
        WHERE s.slug = 'seed-yuting-tianqing'
        ON CONFLICT (character_id, scenario_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS character_story_hooks")
