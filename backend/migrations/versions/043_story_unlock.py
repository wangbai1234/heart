"""043 — Story/剧情 mode: per-scenario unlock + free-tier flag.

Why
---
Story mode moves to a paid model (product directive):

- Text dialogue defaults to DeepSeek (free per-turn).
- A scenario is **permanently unlocked** by a one-time 80-悠悠币 (8000 fen)
  charge; playtime is then billed per minute (PR C2).
- **Tier gating**: free (普通) users may only unlock the 4 ``free_tier`` demo
  scenarios; plus/immersive members may unlock ALL scenarios. Membership does
  NOT waive the unlock fee — it only grants *eligibility* to unlock the full
  catalog.

This migration:

- Adds ``story_scenarios.free_tier`` (BOOLEAN) — the free-tier eligibility flag.
- Creates ``story_scenario_unlocks`` — one row per (user, scenario) unlock,
  ``UNIQUE(user_id, scenario_id)`` so a repeat unlock is a no-op (idempotent
  with the billing idempotency key).
- Backfills ``free_tier = true`` for the 4 designated demo slugs. This is a
  no-op until the bulk importer inserts those rows; the importer also writes
  ``free_tier`` from ``settings.story_free_tier_slugs`` so the flag is correct
  regardless of import/migration order.

Idempotent: ADD COLUMN / CREATE TABLE use IF NOT EXISTS; the backfill is a
plain UPDATE (safe to re-run). No business-code imports (raw SQL only).

Revision ID: 043_story_unlock
Revises: 042_story_scenarios
Create Date: 2026-07-22
"""

from __future__ import annotations

from alembic import op

revision = "043_story_unlock"
down_revision = "042_story_scenarios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- free-tier eligibility flag on the catalog --------------------------
    op.execute(
        "ALTER TABLE story_scenarios "
        "ADD COLUMN IF NOT EXISTS free_tier BOOLEAN NOT NULL DEFAULT false"
    )

    # --- per-user permanent unlocks -----------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS story_scenario_unlocks (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL,
            scenario_id UUID NOT NULL REFERENCES story_scenarios(id) ON DELETE CASCADE,
            unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, scenario_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_story_unlocks_user "
        "ON story_scenario_unlocks (user_id, scenario_id)"
    )

    # --- backfill: the 4 free-tier demo slugs (separate from DDL) -----------
    # No-op until the importer inserts these rows; kept here so an environment
    # that imported before this migration still gets the flag set.
    op.execute(
        """
        UPDATE story_scenarios SET free_tier = true
        WHERE slug IN (
            '当我暗恋的哥哥朋友成为我的顶头上司',
            '轮到我演校园偶像剧了吗？',
            '我在后宫开后宫',
            '无限流？好玩的恐怖游戏而已'
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS story_scenario_unlocks")
    op.execute("ALTER TABLE story_scenarios DROP COLUMN IF EXISTS free_tier")
