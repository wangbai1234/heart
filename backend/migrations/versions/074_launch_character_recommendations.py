"""Seed launch heat and editorial recommendation priority for character batches.

Revision ID: 074_launch_character_recommendations
Revises: 073_character_heat_metrics
"""

from alembic import op

revision = "074_launch_character_recommendations"
down_revision = "073_character_heat_metrics"
branch_labels = None
depends_on = None

_LAUNCH_IDS = (
    "'qin_jingzhou','ye_jingheng','luo_zhiye','han_jingmo','xu_yanzhi',"
    "'shang_yanli','shen_li','fu_yichen','xu_changye','su_chen',"
    "'pei_jinchuan','bai_yao','ye_linchuan','shen_fengchuan','huo_yanshen'"
)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE characters
           SET display_heat = 30000 + MOD(hashtextextended(id, 9041) & 9223372036854775807, 20001),
               heat_initialized_at = COALESCE(heat_initialized_at, NOW())
         WHERE id IN ({_LAUNCH_IDS})
        """
    )
    # Give the two product-fixed leaders a temporary editorial score. The
    # daily metrics worker adds real-view and return behaviour, while this
    # launch bonus decays as real profile entries accumulate.
    op.execute(
        f"""
        UPDATE characters
           SET recommendation_score = CASE id
             WHEN 'fu_yichen' THEN 1.30
             WHEN 'shen_li' THEN 1.29
             ELSE 1.10
           END
         WHERE id IN ({_LAUNCH_IDS})
           AND COALESCE(real_view_count, 0) = 0
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE characters
           SET recommendation_score = 0
         WHERE id IN ({_LAUNCH_IDS})
           AND COALESCE(real_view_count, 0) = 0
        """
    )
