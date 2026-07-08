"""UGC character operational content table.

Revision ID: 021_character_content
Revises: 020_soul_specs
Create Date: 2026-07-08

Stores per-character operational copy (proactive persona hints, fallback
templates, ritual greetings) for UGC characters.  Built-in rin / dorothy
continue to read from the static CHARACTER_CONTENT dict in character_content.py.

This table is the DB-backed overlay that character_content.py will consult
before falling back to its static map (C5a).
"""

from alembic import op

revision = "021_character_content"
down_revision = "020_soul_specs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE character_content (
            character_id        TEXT        NOT NULL PRIMARY KEY,
            proactive_persona   TEXT        NOT NULL DEFAULT '',
            proactive_templates JSONB       NOT NULL DEFAULT '[]'::jsonb,
            ritual_morning      TEXT        NOT NULL DEFAULT '',
            ritual_night        TEXT        NOT NULL DEFAULT '',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS character_content")
