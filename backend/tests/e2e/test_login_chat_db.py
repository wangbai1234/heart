"""E2E: login → chat → verify DB side-effect.

Real HTTP path through uvicorn → FastAPI → Orchestrator → Composer → (Fake)LLM,
then asserts that a `sessions` row was actually written to Postgres.

This is the smallest test that proves the full wiring works end-to-end.
"""

from __future__ import annotations

import pytest

from .conftest import DEMO_CHARACTER_ID, DEMO_USER_ID, demo_user_uuid


@pytest.mark.e2e
class TestLoginChatDB:
    def test_login_then_chat_writes_session_row(
        self,
        api_context,
        pg_conn,
        clean_demo_user,
    ):
        # 1) Login → bearer token
        login_resp = api_context.post(
            "/api/auth/login",
            data={"user_id": DEMO_USER_ID, "email": "e2e@example.com"},
        )
        assert login_resp.ok, f"login failed: {login_resp.status} {login_resp.text()}"
        token_payload = login_resp.json()
        token = token_payload.get("access_token")
        assert token, f"no access_token in payload: {token_payload}"

        # 2) Chat — drives the full orchestrator pipeline
        chat_resp = api_context.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "messages": [{"role": "user", "content": "こんにちは、今日はいい天気だね"}],
                "character_id": DEMO_CHARACTER_ID,
            },
        )
        assert chat_resp.ok, f"chat failed: {chat_resp.status} {chat_resp.text()}"
        body = chat_resp.json()
        assert body["character_id"] == DEMO_CHARACTER_ID
        assert isinstance(body["response"], str) and len(body["response"]) > 0
        assert body["message_id"]

        # 3) DB side-effect — a session row exists with turn_count >= 1
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT turn_count, suicide_protocol_active
                FROM sessions
                WHERE user_id = %s AND character_id = %s
                """,
                (str(demo_user_uuid()), DEMO_CHARACTER_ID),
            )
            row = cur.fetchone()

        assert row is not None, "no sessions row was written — orchestrator did not reach DB"
        turn_count, suicide_active = row
        assert turn_count >= 1, f"expected turn_count >= 1, got {turn_count}"
        assert suicide_active is False, "GREEN message should not flip suicide_protocol_active"

    def test_chat_without_token_is_403(self, api_context):
        """Auth guard is wired — no bearer → 403."""
        r = api_context.post(
            "/api/chat",
            data={"messages": [{"role": "user", "content": "hi"}], "character_id": "rin"},
        )
        assert r.status == 403, f"expected 403, got {r.status}: {r.text()}"
