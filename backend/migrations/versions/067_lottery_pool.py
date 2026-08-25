"""Add versioned lottery pools, prizes, and draw results.

Revision ID: 067_lottery_pool
Revises: 066_invite_lottery_chances
"""

from alembic import op

revision = "067_lottery_pool"
down_revision = "066_invite_lottery_chances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS lottery_pool_versions (
          id BIGSERIAL PRIMARY KEY,
          name VARCHAR(64) NOT NULL UNIQUE,
          status VARCHAR(12) NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'active', 'closed')),
          total_chances INT NOT NULL CHECK (total_chances > 0),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          activated_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_lottery_one_active_pool
        ON lottery_pool_versions (status) WHERE status = 'active'
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS lottery_prizes (
          id BIGSERIAL PRIMARY KEY,
          pool_id BIGINT NOT NULL REFERENCES lottery_pool_versions(id),
          code VARCHAR(32) NOT NULL,
          kind VARCHAR(16) NOT NULL CHECK (kind IN ('coins', 'membership')),
          payload JSONB NOT NULL,
          weight INT NOT NULL CHECK (weight > 0),
          face_value_fen INT NOT NULL CHECK (face_value_fen >= 0),
          total_stock INT,
          daily_stock INT,
          per_user_limit_json JSONB,
          fallback_prize_code VARCHAR(32),
          enabled BOOLEAN NOT NULL DEFAULT TRUE,
          CONSTRAINT uq_lottery_prize_code UNIQUE (pool_id, code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS lottery_draws (
          id BIGSERIAL PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          pool_id BIGINT NOT NULL REFERENCES lottery_pool_versions(id),
          chance_id BIGINT NOT NULL UNIQUE REFERENCES invite_draw_chances(id),
          prize_code VARCHAR(32) NOT NULL,
          prize_kind VARCHAR(16) NOT NULL,
          payload JSONB NOT NULL,
          face_value_fen INT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          idem_key VARCHAR(64) NOT NULL UNIQUE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_lottery_draws_user ON lottery_draws (user_id, created_at)"
    )
    op.execute("ALTER TABLE invite_draw_chances ADD COLUMN IF NOT EXISTS pool_id BIGINT")
    op.execute(
        """
        DO $$ BEGIN
          ALTER TABLE invite_draw_chances
            ADD CONSTRAINT fk_draw_chance_pool
            FOREIGN KEY (pool_id) REFERENCES lottery_pool_versions(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """
    )

    op.execute(
        """
        INSERT INTO lottery_pool_versions
            (name, status, total_chances, activated_at)
        VALUES ('invite-v1-2026-08-25', 'active', 10000, NOW())
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        WITH pool AS (
          SELECT id FROM lottery_pool_versions WHERE name = 'invite-v1-2026-08-25'
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
            5000, 200, 5000, NULL::jsonb, NULL),
          ('coin_40', 'coins', jsonb_build_object('coins', 40),
            2800, 400, 2800, NULL::jsonb, 'coin_20'),
          ('coin_60', 'coins', jsonb_build_object('coins', 60),
            1000, 600, 1000, NULL::jsonb, 'coin_20'),
          ('coin_80', 'coins', jsonb_build_object('coins', 80),
            500, 800, 500, NULL::jsonb, 'coin_20'),
          ('coin_100', 'coins', jsonb_build_object('coins', 100),
            300, 1000, 300,
            jsonb_build_object('days', 30, 'max', 2, 'group', 'coin_100'), 'coin_20'),
          ('coin_200', 'coins', jsonb_build_object('coins', 200),
            100, 2000, 100,
            jsonb_build_object('days', 30, 'max', 1, 'group', 'coin_200'), 'coin_20'),
          ('vip_plus_3d', 'membership',
            jsonb_build_object('tier', 'plus', 'days', 3), 150, 290, 150,
            jsonb_build_object('days', 30, 'max', 4, 'group', 'vip_3d'), 'coin_20'),
          ('vip_immersive_3d', 'membership',
            jsonb_build_object('tier', 'immersive', 'days', 3), 100, 690, 100,
            jsonb_build_object('days', 30, 'max', 4, 'group', 'vip_3d'), 'coin_20'),
          ('vip_plus_30d', 'membership',
            jsonb_build_object('tier', 'plus', 'days', 30), 35, 2900, 35,
            jsonb_build_object('days', 180, 'max', 2, 'group', 'vip_30d'), 'coin_20'),
          ('vip_immersive_30d', 'membership',
            jsonb_build_object('tier', 'immersive', 'days', 30), 15, 6900, 15,
            jsonb_build_object('days', 180, 'max', 2, 'group', 'vip_30d'), 'coin_20')
        ) AS seed(code, kind, payload, weight, face_value_fen, total_stock, user_limit, fallback)
        ON CONFLICT (pool_id, code) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE invite_draw_chances
        SET pool_id = (
          SELECT id FROM lottery_pool_versions WHERE name = 'invite-v1-2026-08-25'
        )
        WHERE pool_id IS NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE invite_draw_chances DROP CONSTRAINT IF EXISTS fk_draw_chance_pool")
    op.execute("ALTER TABLE invite_draw_chances DROP COLUMN IF EXISTS pool_id")
    op.execute("DROP TABLE IF EXISTS lottery_draws")
    op.execute("DROP TABLE IF EXISTS lottery_prizes")
    op.execute("DROP TABLE IF EXISTS lottery_pool_versions")
