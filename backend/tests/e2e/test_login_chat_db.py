"""E2E: login → WebSocket chat → verify DB side-effect.

Real network path through uvicorn → FastAPI WebSocket → Orchestrator → Composer →
(Fake)LLM, then asserts that a `sessions` row was actually written to Postgres.

This is the smallest test that proves the full wiring works end-to-end.
"""

from __future__ import annotations

import json

import pytest
from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.sync.client import connect

from .conftest import DEMO_CHARACTER_ID, DEMO_USER_ID, demo_user_uuid


@pytest.mark.e2e
class TestLoginChatDB:
    def test_login_then_chat_writes_session_row(
        self,
        api_context,
        e2e_server,
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

        # WebSocket chat requires the same adulthood gate as production. The
        # dev login creates the user but intentionally doesn't bypass it.
        with pg_conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET age_verified_at = NOW() WHERE id = %s",
                (str(demo_user_uuid()),),
            )
        pg_conn.commit()

        # 2) Chat — drives the current full orchestrator pipeline over WebSocket.
        ws_url = e2e_server.replace("http://", "ws://") + f"/api/chat/ws?token={token}"
        frames: list[dict] = []
        with connect(ws_url, open_timeout=10, close_timeout=5) as ws:
            ws.send(
                json.dumps(
                    {
                        "type": "chat",
                        "text": "こんにちは、今日はいい天気だね",
                        "character_id": DEMO_CHARACTER_ID,
                    }
                )
            )
            while True:
                frame = json.loads(ws.recv(timeout=30))
                frames.append(frame)
                if frame.get("type") == "turn_end":
                    break

        assert any(frame.get("type") == "turn_start" for frame in frames), frames
        assert any(
            frame.get("type") in {"text_delta", "sentence", "message_bubble"}
            for frame in frames
        ), frames
        assert not any(frame.get("type") == "error" for frame in frames), frames

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

    def test_chat_websocket_without_token_is_rejected(self, e2e_server):
        """The production WebSocket auth guard rejects a missing token."""
        ws_url = e2e_server.replace("http://", "ws://") + "/api/chat/ws"
        with pytest.raises((InvalidStatus, ConnectionClosed)):
            with connect(ws_url, open_timeout=10) as ws:
                ws.recv(timeout=5)
