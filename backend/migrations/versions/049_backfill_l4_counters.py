"""049 — Backfill L4 promotion counters on existing fact_nodes.

Why
---
L4 identity memory was permanently empty in production (0 rows) despite 214
active L3 facts and a promoter worker running every 5 minutes with 0 errors.
Root cause: the active encoder (``heart/workers/memory_encoder.py``) reinforced
facts by bumping ``confirmation_count`` and never touched the two fields the
promoter actually gates on —

  - P5: ``mention_count >= K1`` (3)          → frozen at creation default 1
  - P6: ``confidence_ewma >= K2`` (0.8)      → frozen at column default 0.5

so ``candidates_found`` was always 0. The code fix (same PR) makes the encoder
increment ``mention_count`` and roll ``confidence_ewma`` on every reinforce, and
seed ``confidence_ewma`` from the fact's own confidence at creation.

This migration retro-corrects the rows that already exist so they are not
stranded forever waiting for the (now-fixed) code to touch them:

  - ``confidence_ewma`` → GREATEST(current, confidence). Existing facts average
    confidence ~0.91, so this lifts them from the 0.5 default over the 0.8 gate.
  - ``mention_count``  → GREATEST(current, confirmation_count + 1). This credits
    the reinforces we DID track (in confirmation_count) but forgot to mirror
    into mention_count. A fact confirmed N times becomes mention_count N+1.

Only touches active, recallable facts. Never lowers a value (GREATEST), so it is
safe to re-run and safe against the fixed code path writing higher values first.

Idempotent: pure UPDATE with GREATEST guards, no DDL. Raw SQL only, no
business-code imports.

Revision ID: 049_backfill_l4_counters
Revises: 048_story_memory
Create Date: 2026-07-25
"""

from __future__ import annotations

from alembic import op

revision = "049_backfill_l4_counters"
down_revision = "048_story_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Data backfill only — columns already exist (migration 007). Kept as a
    # standalone UPDATE (no DDL in this statement) per the repo's migration
    # rules so rollback granularity stays clean.
    op.execute(
        """
        UPDATE fact_nodes
        SET
            confidence_ewma = GREATEST(COALESCE(confidence_ewma, 0.5), confidence),
            mention_count = GREATEST(COALESCE(mention_count, 1), COALESCE(confirmation_count, 0) + 1)
        WHERE is_active = TRUE
          AND do_not_recall = FALSE
        """
    )


def downgrade() -> None:
    # Non-reversible data backfill: the pre-backfill values (mention_count=1,
    # confidence_ewma=0.5 defaults) are not recoverable and re-deriving them
    # would corrupt facts the fixed code has since legitimately reinforced.
    # No-op downgrade — the forward migration only ever raised values via
    # GREATEST, so leaving them in place is safe.
    pass
