"""Add privacy-preserving referral risk signals and admin audit log.

Revision ID: 070_referral_risk
Revises: 069_commission
"""

from alembic import op

revision = "070_referral_risk"
down_revision = "069_commission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE user_invite_uses
          ADD COLUMN IF NOT EXISTS device_hash VARCHAR(64),
          ADD COLUMN IF NOT EXISTS ip_hash VARCHAR(64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_invite_uses_device_recent
        ON user_invite_uses (device_hash, created_at) WHERE device_hash IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS referral_risk_events (
          id BIGSERIAL PRIMARY KEY,
          event_type VARCHAR(32) NOT NULL,
          subject_id VARCHAR(64) NOT NULL,
          signals JSONB NOT NULL DEFAULT '{}'::jsonb,
          score INT NOT NULL,
          risk_level VARCHAR(8) NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_referral_risk_subject
        ON referral_risk_events (subject_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
          id BIGSERIAL PRIMARY KEY,
          action VARCHAR(48) NOT NULL,
          subject_type VARCHAR(32) NOT NULL,
          subject_id VARCHAR(64) NOT NULL,
          detail JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS growth_rule_settings (
          namespace VARCHAR(24) PRIMARY KEY,
          config JSONB NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        INSERT INTO growth_rule_settings (namespace, config) VALUES
          ('invite', jsonb_build_object(
            'qualification_days', 7, 'binding_hours', 24, 'min_messages', 3,
            'min_ai_replies', 2, 'min_valid_chars', 15, 'min_span_seconds', 120,
            'chance_expiry_days', 30, 'daily_limit_free', 5, 'daily_limit_plus', 10,
            'daily_limit_immersive', 20
          )),
          ('commission', jsonb_build_object(
            'rate_percent', 10, 'attribution_days', 30,
            'settlement_days', 15, 'risk_settlement_days', 30
          ))
        ON CONFLICT (namespace) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS growth_rule_settings")
    op.execute("DROP TABLE IF EXISTS admin_audit_logs")
    op.execute("DROP TABLE IF EXISTS referral_risk_events")
    op.execute("DROP INDEX IF EXISTS idx_invite_uses_device_recent")
    op.execute(
        "ALTER TABLE user_invite_uses DROP COLUMN IF EXISTS ip_hash, "
        "DROP COLUMN IF EXISTS device_hash"
    )
