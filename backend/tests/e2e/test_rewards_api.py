"""E2E: authenticated lottery status and draw persist exactly one reward."""

from __future__ import annotations

import uuid

import pytest

from .conftest import DEMO_USER_ID


@pytest.mark.e2e
def test_lottery_status_then_draw_persists_reward(api_context, pg_conn):
    login_response = api_context.post(
        "/api/auth/login",
        data={"user_id": DEMO_USER_ID, "email": "e2e@example.com"},
    )
    assert login_response.ok, login_response.text()
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    idem_key = f"e2e-lottery:{uuid.uuid4()}"

    chance_id: int | None = None
    draw_id: int | None = None
    with pg_conn.cursor() as cursor:
        cursor.execute(
            "SELECT credits_balance FROM users WHERE id = %s",
            (DEMO_USER_ID,),
        )
        original_balance = int(cursor.fetchone()[0])
        cursor.execute(
            """
            INSERT INTO invite_draw_chances
              (user_id, source, grant_day, daily_ordinal, expires_at, idem_key, pool_id)
            SELECT %s, 'e2e-api', CURRENT_DATE,
                   COALESCE((SELECT MAX(daily_ordinal) + 1 FROM invite_draw_chances
                             WHERE user_id = %s AND grant_day = CURRENT_DATE), 1),
                   NOW() + INTERVAL '1 day', %s, id
            FROM lottery_pool_versions WHERE status = 'active'
            RETURNING id
            """,
            (DEMO_USER_ID, DEMO_USER_ID, idem_key),
        )
        chance_id = int(cursor.fetchone()[0])
    pg_conn.commit()

    try:
        status_response = api_context.get("/api/lottery/status", headers=headers)
        assert status_response.ok, status_response.text()
        status_payload = status_response.json()
        assert any(item["id"] == chance_id for item in status_payload["chances"])

        draw_response = api_context.post(
            "/api/lottery/draw",
            headers=headers,
            data={"chance_id": chance_id},
        )
        assert draw_response.ok, draw_response.text()
        draw_payload = draw_response.json()
        draw_id = int(draw_payload["id"])
        assert int(draw_payload["chance_id"]) == chance_id

        with pg_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT d.id, c.consumed_at,
                       (SELECT COUNT(*) FROM credit_transactions
                        WHERE idempotency_key = %s) +
                       (SELECT COUNT(*) FROM membership_reward_coupons
                        WHERE idem_key = %s) AS reward_count
                FROM lottery_draws d
                JOIN invite_draw_chances c ON c.id = d.chance_id
                WHERE d.chance_id = %s
                """,
                (f"draw_reward:{draw_id}", f"coupon:lottery:{draw_id}", chance_id),
            )
            persisted = cursor.fetchone()

        assert persisted is not None
        assert int(persisted[0]) == draw_id
        assert persisted[1] is not None
        assert int(persisted[2]) == 1
    finally:
        with pg_conn.cursor() as cursor:
            if draw_id is not None:
                cursor.execute(
                    "DELETE FROM credit_transactions WHERE idempotency_key = %s",
                    (f"draw_reward:{draw_id}",),
                )
                cursor.execute(
                    "DELETE FROM membership_reward_coupons WHERE idem_key = %s",
                    (f"coupon:lottery:{draw_id}",),
                )
                cursor.execute("DELETE FROM lottery_draws WHERE id = %s", (draw_id,))
            if chance_id is not None:
                cursor.execute("DELETE FROM invite_draw_chances WHERE id = %s", (chance_id,))
            cursor.execute(
                "UPDATE users SET credits_balance = %s WHERE id = %s",
                (original_balance, DEMO_USER_ID),
            )
        pg_conn.commit()
