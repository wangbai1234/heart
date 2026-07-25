"""050 — Character catalog tags + portrait cover_url (Nimoo-style discovery).

Why
---
The character page is being reworked from a "羁绊中心" (bond center that only
lists already-chatted companions) into a browsable **discovery catalog** modeled
on chat.nimoo.ai: a 2-column grid of tall portrait cover cards with a top row of
style-filter chips, and a per-character profile page.

Two things the ``characters`` table cannot express today:
  1. **Style tags** — the filter chips (御姐 / 元气 / 治愈 / …) need a
     data-driven taxonomy per character, not a frontend-only hardcode.
  2. **Portrait cover art** — the grid cards and the chat background use a
     dedicated 竖版封面, distinct from the small round avatar.

Columns
-------
- ``characters.tags``      JSONB DEFAULT '[]'  — list[str] of style/category tags.
  JSONB (not text[]) mirrors how soul_specs stores structured JSON and keeps the
  API passthrough a plain list; empty list default so existing rows read cleanly.
- ``characters.cover_url`` TEXT (nullable)     — proxied URL to the portrait
  cover object in S3/R2 (``/api/profile/cover-file/...``). NULL → frontend derives
  a blurred cover from the avatar. **Never a base64 data URL** — covers are stored
  as compressed WebP objects and only their short proxy URL lives here (the
  探索页 OOM incident, commit d3922fb, was full-res images proxied through memory;
  inlining base64 into a row would repeat that mistake at the DB layer).

Idempotent: ADD COLUMN IF NOT EXISTS. Raw SQL only, no business-code imports.
No data backfill needed — defaults cover every existing row.

Revision ID: 050_character_tags_cover
Revises: 049_backfill_l4_counters
Create Date: 2026-07-25
"""

from __future__ import annotations

from alembic import op

revision = "050_character_tags_cover"
down_revision = "049_backfill_l4_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE characters ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb"
    )
    op.execute("ALTER TABLE characters ADD COLUMN IF NOT EXISTS cover_url TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE characters DROP COLUMN IF EXISTS cover_url")
    op.execute("ALTER TABLE characters DROP COLUMN IF EXISTS tags")
