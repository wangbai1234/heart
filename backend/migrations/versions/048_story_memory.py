"""048 — Story run structured memory card (剧情记忆卡).

Why
---
Players report that NPC "memory" in SS09 story mode is too weak. The engine
carries context as (a) the last N message rows replayed verbatim and (b) one
short rolling prose ``summary`` (≤200 chars). In a multi-NPC playthrough that
flat blob can't retain who-relates-to-whom, player promises, items, or open
plot threads — anything that scrolls past the window is lost.

This adds ``story_runs.story_memory`` JSONB: a compact, structured "memory card"
maintained inline by the same rolling-summary pass (no new workers, no
embeddings). Shape (all sections optional, hard-capped for token budget):

    {
      "npcs": {"<name>": {"relationship": str, "facts": [str], "last_state": str}},
      "player_facts": [str],
      "world_facts": [str],
      "open_threads": [str]
    }

It is rendered into the GM system prompt every turn so each NPC's durable facts
are always in context regardless of the verbatim window. Multiple characters are
just multiple keys under ``npcs`` — the multi-NPC case falls out naturally.

Scope isolation: a fresh 重新游玩 creates a brand-new run (see start_run →
create_run), which gets the DEFAULT ``{}`` here, so replay starts with an empty
memory card. No per-user backfill is needed — existing runs default to ``{}``
and fill in as play continues.

Idempotent: ADD COLUMN IF NOT EXISTS. Raw SQL only, no business-code imports.

Revision ID: 048_story_memory
Revises: 047_character_story_hooks
Create Date: 2026-07-25
"""

from __future__ import annotations

from alembic import op

revision = "048_story_memory"
down_revision = "047_character_story_hooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE story_runs "
        "ADD COLUMN IF NOT EXISTS story_memory JSONB NOT NULL DEFAULT '{}'::jsonb"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE story_runs DROP COLUMN IF EXISTS story_memory")
