"""Merge divergent heads: 022_identity_narrative_backfill + 045_story_heat_values.

Revision ID: 046_merge_022_045
Revises: 022_identity_narrative_backfill, 045_story_heat_values
Create Date: 2026-07-24

Context
-------
The migration DAG forked at ``021_character_content``:

    021_character_content
      ├── 022_identity_narrative_backfill   (orphan head — data-only backfill)
      └── 023_user_timezone → … → 045_story_heat_values   (main chain head)

Because 022 was never on the main chain, ``alembic upgrade head`` failed with
"Multiple head revisions" and 022's backfill was only reachable by upgrading to
its explicit revision. This merge migration reunites both heads so a single
``alembic upgrade head`` reaches everything. It carries NO DDL/DML of its own —
it is a pure merge node.
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "046_merge_022_045"
down_revision = ("022_identity_narrative_backfill", "045_story_heat_values")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Pure merge node — no schema or data changes."""
    pass


def downgrade() -> None:
    """Pure merge node — no schema or data changes."""
    pass
