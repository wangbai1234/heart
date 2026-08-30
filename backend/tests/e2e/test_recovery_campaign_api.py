"""E2E: normal signup grant after recovery campaign retirement."""

from __future__ import annotations

import uuid

import pytest

from heart.api.routes_auth import _hash_code
from heart.core.config import settings


@pytest.mark.e2e
def test_registration_uses_configured_signup_grant_once(api_context, pg_conn):
    email = f"e2e-recovery-{uuid.uuid4()}@example.com"
    otp_code = "482731"
    otp_id = uuid.uuid4()
    user_id = None

    with pg_conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO email_otp_codes (id, email, code_hash, purpose, expires_at)
            VALUES (%s, %s, %s, 'register', NOW() + INTERVAL '10 minutes')
            """,
            (str(otp_id), email, _hash_code(otp_code)),
        )
    pg_conn.commit()

    expected_fen = settings.signup_grant_credits
    try:
        response = api_context.post(
            "/api/auth/register",
            data={"email": email, "otp_code": otp_code, "password": "recovery-test-password"},
        )
        assert response.ok, response.text()
        payload = response.json()
        user_id = payload["user"]["id"]
        assert payload["user"]["credits_balance"] == expected_fen / 100

        with pg_conn.cursor() as cursor:
            cursor.execute(
                "SELECT credits_balance FROM users WHERE id = %s",
                (user_id,),
            )
            assert cursor.fetchone()[0] == expected_fen
            cursor.execute(
                "SELECT delta, balance_after, COUNT(*) OVER () "
                "FROM credit_transactions WHERE idempotency_key = %s",
                (f"signup_grant:{user_id}",),
            )
            transaction = cursor.fetchone()
            assert transaction == (expected_fen, expected_fen, 1)

        duplicate = api_context.post(
            "/api/auth/register",
            data={"email": email, "otp_code": otp_code, "password": "recovery-test-password"},
        )
        assert duplicate.status == 409
    finally:
        with pg_conn.cursor() as cursor:
            if user_id is not None:
                cursor.execute("DELETE FROM auth_sessions WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM credit_transactions WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            cursor.execute("DELETE FROM email_otp_codes WHERE email = %s", (email,))
        pg_conn.commit()
