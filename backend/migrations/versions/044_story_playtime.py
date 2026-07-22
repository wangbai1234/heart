"""044 — Story/剧情 mode: per-minute playtime billing counters.

Why
---
After the one-time unlock (migration 043), story playtime is billed **per full
minute** (1 悠悠币 = 100 fen/min). Billing is driven by a client heartbeat sent
every 60s while the player page is foregrounded; the server charges one minute
per heartbeat, idempotent on ``story_time:{run}:{minute_index}``.

To make each minute globally unique per run (so charging survives disconnects /
resume and never double-charges), the run owns the minute counter:

- ``story_runs.billed_minutes`` — how many minutes have already been billed for
  this run. The next charge uses this value as its idempotency-key index, then
  the counter advances.
- ``story_runs.last_billed_at`` — timestamp of the last successful minute charge;
  the WS uses it to throttle out rapid-fire / duplicate heartbeats.

Idempotent: ADD COLUMN uses IF NOT EXISTS. No backfill needed (default 0 / NULL
is correct for existing runs). No business-code imports (raw SQL only).

Revision ID: 044_story_playtime
Revises: 043_story_unlock
Create Date: 2026-07-22
"""

from __future__ import annotations

from alembic import op

revision = "044_story_playtime"
down_revision = "043_story_unlock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE story_runs "
        "ADD COLUMN IF NOT EXISTS billed_minutes INTEGER NOT NULL DEFAULT 0"
    )
    op.execute("ALTER TABLE story_runs ADD COLUMN IF NOT EXISTS last_billed_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE story_runs DROP COLUMN IF EXISTS last_billed_at")
    op.execute("ALTER TABLE story_runs DROP COLUMN IF EXISTS billed_minutes")
