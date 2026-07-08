"""Soul Spec storage table for DB-backed UGC character specs.

Revision ID: 020_soul_specs
Revises: 019_characters_directory
Create Date: 2026-07-08

Stores the fully-expanded SoulSpec JSONB for UGC characters so they can be
loaded into the registry at startup and hot-reloaded without a restart.

Built-in characters (rin / dorothy) continue to be loaded from soul_specs/
YAML files; this table is purely additive for UGC specs.  The complete
expanded spec is stored (not just the draft) so future changes to the
deterministic expander cannot silently mutate an existing character's identity.
"""

from alembic import op

revision = "020_soul_specs"
down_revision = "019_characters_directory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE soul_specs (
            character_id  TEXT        NOT NULL,
            spec_version  TEXT        NOT NULL,
            source        TEXT        NOT NULL DEFAULT 'ugc',
            status        TEXT        NOT NULL DEFAULT 'active',
            spec          JSONB       NOT NULL,
            draft         JSONB,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (character_id, spec_version),
            CONSTRAINT chk_soul_spec_source CHECK (source IN ('builtin', 'ugc')),
            CONSTRAINT chk_soul_spec_status CHECK (status IN ('active', 'superseded', 'disabled'))
        )
    """)
    op.execute("""
        CREATE INDEX ix_soul_specs_active
            ON soul_specs (character_id)
            WHERE status = 'active'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS soul_specs")
