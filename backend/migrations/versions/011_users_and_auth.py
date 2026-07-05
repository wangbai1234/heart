"""Users, OTP codes, and auth sessions for commercial auth system.

Revision ID: 011_users_and_auth
Revises: 010_memory_regex_shadow
Create Date: 2026-07-04 00:00:00.000000

Tables:
  - users: real user entity with email, profile fields, credits balance
  - email_otp_codes: hashed OTP codes for email login
  - auth_sessions: refresh token sessions (revocable)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import CITEXT, INET, UUID

revision = "011_users_and_auth"
down_revision = "010_memory_regex_shadow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure CITEXT extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ── users (must be first — FK holders depend on it) ──
    op.execute(
        """
    CREATE TABLE users (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email           CITEXT NOT NULL,
        display_name    TEXT,
        avatar_url      TEXT,
        gender          TEXT,
        birthdate       DATE,
        age_verified_at TIMESTAMPTZ,
        credits_balance BIGINT NOT NULL DEFAULT 0
                        CHECK (credits_balance >= 0),
        status          TEXT NOT NULL DEFAULT 'active',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_login_at   TIMESTAMPTZ,
        deleted_at      TIMESTAMPTZ,

        CONSTRAINT uq_users_email UNIQUE (email),
        CONSTRAINT chk_users_status CHECK (status IN ('active', 'deleted')),
        CONSTRAINT chk_users_gender CHECK (
            gender IS NULL OR gender IN ('female', 'male', 'nonbinary', 'undisclosed')
        )
    )
    """
    )
    op.execute("CREATE INDEX ix_users_status ON users (status)")

    # ── email_otp_codes ──
    op.execute(
        """
    CREATE TABLE email_otp_codes (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email       CITEXT NOT NULL,
        code_hash   TEXT NOT NULL,
        purpose     TEXT NOT NULL DEFAULT 'login',
        expires_at  TIMESTAMPTZ NOT NULL,
        consumed_at TIMESTAMPTZ,
        attempts    SMALLINT NOT NULL DEFAULT 0,
        request_ip  INET,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
    )
    op.execute(
        "CREATE INDEX ix_email_otp_codes_email_created "
        "ON email_otp_codes (email, created_at DESC)"
    )

    # ── credit_transactions (minimal for signup grant; Module 3 extends) ──
    op.execute(
        """
    CREATE TABLE credit_transactions (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL,
        delta           BIGINT NOT NULL,
        balance_after   BIGINT NOT NULL,
        type            TEXT NOT NULL,
        ref_type        TEXT,
        ref_id          TEXT,
        idempotency_key TEXT NOT NULL,
        metadata        JSONB,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        CONSTRAINT uq_credit_tx_idempotency UNIQUE (idempotency_key),
        CONSTRAINT fk_credit_tx_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
    )
    op.execute(
        "CREATE INDEX ix_credit_tx_user_created "
        "ON credit_transactions (user_id, created_at DESC)"
    )

    # ── auth_sessions (refresh tokens) ──
    op.execute(
        """
    CREATE TABLE auth_sessions (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id             UUID NOT NULL,
        refresh_token_hash  TEXT NOT NULL,
        issued_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at          TIMESTAMPTZ NOT NULL,
        revoked_at          TIMESTAMPTZ,
        user_agent          TEXT,
        ip                  INET,

        CONSTRAINT fk_auth_sessions_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
    )
    op.execute("CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id)")
    op.execute(
        "CREATE INDEX ix_auth_sessions_refresh_hash ON auth_sessions (refresh_token_hash)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_sessions")
    op.execute("DROP TABLE IF EXISTS credit_transactions")
    op.execute("DROP TABLE IF EXISTS email_otp_codes")
    op.execute("DROP TABLE IF EXISTS users")
