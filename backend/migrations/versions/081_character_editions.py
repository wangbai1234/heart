"""Persist source/edition relationships without publishing editorial drafts."""
from alembic import op

revision = "081_character_editions"
down_revision = "080_extensible_locales"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS character_editions (
        character_id VARCHAR(64) PRIMARY KEY REFERENCES characters(id),
        source_id VARCHAR(64) NOT NULL REFERENCES characters(id),
        locale VARCHAR(64) NOT NULL,
        source_sha256 TEXT NOT NULL,
        candidate_sha256 TEXT NOT NULL,
        batch_id TEXT NOT NULL,
        local_preview BOOLEAN NOT NULL DEFAULT FALSE,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(source_id, locale),
        CHECK(character_id <> source_id)
    )""")


def downgrade() -> None:
    # Keep provenance when rolling application code back; never delete editions.
    pass
