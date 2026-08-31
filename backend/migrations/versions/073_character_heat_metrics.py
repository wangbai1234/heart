"""Persist character cover heat and real recommendation metrics.

Revision ID: 073_character_heat_metrics
Revises: 072_targeted_user_notices
"""

from alembic import op

revision = "073_character_heat_metrics"
down_revision = "072_targeted_user_notices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE characters
          ADD COLUMN IF NOT EXISTS display_heat BIGINT NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS real_view_count BIGINT NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS real_play_uv INTEGER NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS return_user_uv INTEGER NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS smoothed_return_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS recommendation_score DOUBLE PRECISION NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS heat_initialized_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS last_heat_support_date DATE,
          ADD COLUMN IF NOT EXISTS metrics_calculated_at TIMESTAMPTZ
        """
    )

    # First-party characters retain an editorial-looking launch baseline, but
    # every subsequent change is persisted. hashtextextended makes the one-time
    # seed deterministic across environments instead of changing on re-run.
    op.execute(
        """
        UPDATE characters
           SET display_heat = CASE id
                 WHEN 'char_b8ed4c9b' THEN 6388
                 WHEN 'char_ae43cbad' THEN 6216
                 WHEN 'zhou_jin' THEN 5867
                 WHEN 'song_ye' THEN 4218
                 WHEN 'pei_tinglan' THEN 5732
                 WHEN 'vito_rosetti' THEN 3976
                 WHEN 'xie_ci' THEN 5421
                 WHEN 'fu_mingxiu' THEN 5894
                 WHEN 'shen_liao' THEN 4685
                 WHEN 'xize' THEN 3512
                 WHEN 'lu_wenjing' THEN 5238
                 WHEN 'luo_fei' THEN 4879
                 WHEN 'jiang_ran' THEN 4356
                 WHEN 'gu_yanli' THEN 5608
                 WHEN 'xu_zhihan' THEN 3167
                 ELSE 500 + MOD(hashtextextended(id, 7301) & 9223372036854775807, 4501)
               END,
               heat_initialized_at = COALESCE(heat_initialized_at, NOW())
         WHERE owner_user_id IS NULL
           AND heat_initialized_at IS NULL
        """
    )

    # Existing public+approved UGC must receive the same one-time cold-start
    # heat as characters approved after this migration.
    op.execute(
        """
        UPDATE characters
           SET display_heat = display_heat
                              + 100 + MOD(hashtextextended(id, 7302) & 9223372036854775807, 301),
               heat_initialized_at = NOW()
         WHERE owner_user_id IS NOT NULL
           AND status = 'active'
           AND visibility = 'public'
           AND review_status = 'approved'
           AND heat_initialized_at IS NULL
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_characters_recommendation_score "
        "ON characters (recommendation_score DESC, real_view_count DESC) "
        "WHERE status = 'active' AND visibility = 'public'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_msg_character_metrics "
        "ON chat_messages (created_at, character_id, user_id) "
        "WHERE role = 'user' AND rewound_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_msg_character_metrics")
    op.execute("DROP INDEX IF EXISTS ix_characters_recommendation_score")
    op.execute(
        """
        ALTER TABLE characters
          DROP COLUMN IF EXISTS metrics_calculated_at,
          DROP COLUMN IF EXISTS last_heat_support_date,
          DROP COLUMN IF EXISTS heat_initialized_at,
          DROP COLUMN IF EXISTS recommendation_score,
          DROP COLUMN IF EXISTS smoothed_return_rate,
          DROP COLUMN IF EXISTS return_user_uv,
          DROP COLUMN IF EXISTS real_play_uv,
          DROP COLUMN IF EXISTS real_view_count,
          DROP COLUMN IF EXISTS display_heat
        """
    )
