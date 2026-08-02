"""Add review columns to characters + milestone reward table

Revision ID: 056_character_review
Revises: 055_afdian_custom_order_id
Create Date: 2026-08-02

review_status values:
  not_required  — private; skips review pipeline entirely
  pending       — submitted for human review
  approved      — approved; character is visible in catalog
  rejected      — rejected; owner sees reason, can resubmit
"""

from alembic import op

revision = "056_character_review"
down_revision = "055_afdian_custom_order_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Review columns on characters ─────────────────────────────────────────
    op.execute(
        """
        ALTER TABLE characters
            ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'not_required',
            ADD COLUMN IF NOT EXISTS review_reason TEXT,
            ADD COLUMN IF NOT EXISTS submitted_at  TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS reviewed_at   TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS result_ack_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_characters_review_status'
            ) THEN
                ALTER TABLE characters
                    ADD CONSTRAINT chk_characters_review_status
                    CHECK (review_status IN ('not_required','pending','approved','rejected'));
            END IF;
        END $$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_characters_review_status "
        "ON characters (review_status) WHERE review_status = 'pending'"
    )
    # Backfill: built-ins (no owner) → approved
    op.execute(
        """
        UPDATE characters
           SET review_status = 'approved'
         WHERE owner_user_id IS NULL
           AND review_status = 'not_required'
        """
    )
    # Existing UGC that is public/unlisted → pending (should be reviewed)
    op.execute(
        """
        UPDATE characters
           SET review_status = 'pending',
               submitted_at  = NOW()
         WHERE owner_user_id IS NOT NULL
           AND visibility IN ('public','unlisted')
           AND review_status = 'not_required'
        """
    )

    # ── Milestone reward guard table ─────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_reward_milestones (
            user_id    UUID   NOT NULL,
            milestone  TEXT   NOT NULL,
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT pk_user_reward_milestones PRIMARY KEY (user_id, milestone),
            CONSTRAINT fk_urm_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_reward_milestones")
    op.execute(
        "DROP INDEX IF EXISTS ix_characters_review_status"
    )
    op.execute(
        "ALTER TABLE characters DROP CONSTRAINT IF EXISTS chk_characters_review_status"
    )
    op.execute(
        """
        ALTER TABLE characters
            DROP COLUMN IF EXISTS result_ack_at,
            DROP COLUMN IF EXISTS reviewed_at,
            DROP COLUMN IF EXISTS submitted_at,
            DROP COLUMN IF EXISTS review_reason,
            DROP COLUMN IF EXISTS review_status
        """
    )
