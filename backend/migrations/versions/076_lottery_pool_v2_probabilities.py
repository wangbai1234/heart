"""Lower lottery odds while preserving every prize value.

Revision ID: 076_lottery_pool_v2_probabilities
Revises: 075_promotion_tasks
"""

from alembic import op

revision = "076_lottery_pool_v2_probabilities"
down_revision = "075_promotion_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO lottery_pool_versions
            (name, status, total_chances, activated_at)
        VALUES ('invite-v2-2026-09-10', 'draft', 10000, NULL)
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        WITH pool AS (
          SELECT id FROM lottery_pool_versions WHERE name = 'invite-v2-2026-09-10'
        )
        INSERT INTO lottery_prizes
          (pool_id, code, kind, payload, weight, face_value_fen, total_stock,
           per_user_limit_json, fallback_prize_code)
        SELECT pool.id, seed.code, seed.kind, seed.payload, seed.weight,
               seed.face_value_fen, seed.total_stock, seed.user_limit,
               seed.fallback
        FROM pool
        CROSS JOIN (VALUES
          ('coin_20', 'coins', jsonb_build_object('coins', 20),
            8000, 200, 8000, NULL::jsonb, NULL),
          ('coin_40', 'coins', jsonb_build_object('coins', 40),
            1200, 400, 1200, NULL::jsonb, 'coin_20'),
          ('coin_60', 'coins', jsonb_build_object('coins', 60),
            400, 600, 400, NULL::jsonb, 'coin_20'),
          ('coin_80', 'coins', jsonb_build_object('coins', 80),
            180, 800, 180, NULL::jsonb, 'coin_20'),
          ('coin_100', 'coins', jsonb_build_object('coins', 100),
            100, 1000, 100,
            jsonb_build_object('days', 30, 'max', 2, 'group', 'coin_100'), 'coin_20'),
          ('coin_200', 'coins', jsonb_build_object('coins', 200),
            20, 2000, 20,
            jsonb_build_object('days', 30, 'max', 1, 'group', 'coin_200'), 'coin_20'),
          ('vip_plus_3d', 'membership',
            jsonb_build_object('tier', 'plus', 'days', 3), 50, 290, 50,
            jsonb_build_object('days', 30, 'max', 4, 'group', 'vip_3d'), 'coin_20'),
          ('vip_immersive_3d', 'membership',
            jsonb_build_object('tier', 'immersive', 'days', 3), 30, 690, 30,
            jsonb_build_object('days', 30, 'max', 4, 'group', 'vip_3d'), 'coin_20'),
          ('vip_plus_30d', 'membership',
            jsonb_build_object('tier', 'plus', 'days', 30), 15, 2900, 15,
            jsonb_build_object('days', 180, 'max', 2, 'group', 'vip_30d'), 'coin_20'),
          ('vip_immersive_30d', 'membership',
            jsonb_build_object('tier', 'immersive', 'days', 30), 5, 6900, 5,
            jsonb_build_object('days', 180, 'max', 2, 'group', 'vip_30d'), 'coin_20')
        ) AS seed(code, kind, payload, weight, face_value_fen, total_stock, user_limit, fallback)
        ON CONFLICT (pool_id, code) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE lottery_pool_versions
        SET status = 'closed'
        WHERE status = 'active' AND name <> 'invite-v2-2026-09-10'
        """
    )
    op.execute(
        """
        UPDATE lottery_pool_versions
        SET status = 'active', activated_at = NOW()
        WHERE name = 'invite-v2-2026-09-10'
        """
    )


def downgrade() -> None:
    op.execute(
        "UPDATE lottery_pool_versions SET status = 'closed' "
        "WHERE name = 'invite-v2-2026-09-10'"
    )
    op.execute(
        "UPDATE lottery_pool_versions SET status = 'active' "
        "WHERE name = 'invite-v1-2026-08-25'"
    )
