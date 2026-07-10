"""Backfill identity_narrative into existing UGC soul_specs.

Revision ID: 022_identity_narrative_backfill
Revises: 021_character_content
Create Date: 2026-07-09

No DDL change — SoulSpec is stored as JSONB, so schema_version 1.0→1.1
and the new identity_narrative field are purely data changes.

For each active UGC soul_spec row that lacks identity_narrative, copy
draft->>'persona' into spec->'identity_narrative'.  Built-in characters
(rin, dorothy) have no draft row in soul_specs; they are skipped.
"""

from alembic import op

revision = "022_identity_narrative_backfill"
down_revision = "021_character_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE soul_specs
        SET spec = jsonb_set(
                       jsonb_set(
                           spec,
                           '{identity_narrative}',
                           to_jsonb(COALESCE(draft->>'persona', '')),
                           true
                       ),
                       '{schema_version}',
                       '"1.1"',
                       true
                   )
        WHERE source = 'ugc'
          AND status = 'active'
          AND (spec->>'identity_narrative') IS NULL
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE soul_specs
        SET spec = spec
                   - 'identity_narrative'
                   || jsonb_build_object('schema_version', '1.0')
        WHERE source = 'ugc'
          AND status = 'active'
    """)
