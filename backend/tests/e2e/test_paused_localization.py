"""Paused language rollout keeps original prompts and Google authentication."""

import hashlib
import json
import os
import secrets
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
import redis
from websockets.sync.client import connect

from tests.e2e.test_international_release import login

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("INTERNATIONAL_MODE") != "true"
        or os.getenv("INTERNATIONAL_LOCALIZATION") != "false",
        reason="Paused localization only",
    ),
]


def test_original_prompt_ignores_saved_foreign_preferences(api_context, pg_conn, e2e_server):
    uid = str(uuid4())
    token = login(api_context, uid)
    headers = {"Authorization": f"Bearer {token}", "Accept-Language": "ko"}
    assert api_context.get("/api/locale", headers=headers).json() == {"language": "zh"}
    saved = api_context.put(
        "/api/profile/preferences",
        headers=headers,
        data={
            "interface_language": "ko",
            "response_language": "ja",
            "action_style": "fullwidth",
            "response_follows_interface": False,
        },
    )
    assert saved.ok, saved.text()
    with pg_conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET age_verified_at=NOW(), credits_balance=100000 WHERE id=%s", (uid,)
        )
    pg_conn.commit()
    created = api_context.post(
        "/api/characters",
        headers=headers,
        data={
            "display_name": {"zh": "测试作家"},
            "persona": "一位温和细心的成年作家，喜欢倾听故事和安静地陪伴。",
            "locale": "zh-CN",
            "response_language": "ko",
            "visibility": "private",
            "creation_mode": "workshop",
        },
    )
    assert created.ok, created.text()
    cid = created.json()["id"]
    frames = []
    with connect(
        e2e_server.replace("http://", "ws://") + f"/api/chat/ws?token={token}", open_timeout=10
    ) as ws:
        ws.send(json.dumps({"type": "chat", "character_id": cid, "text": "你好，一起聊聊写作吧。"}))
        for _ in range(200):
            frame = json.loads(ws.recv(timeout=30))
            frames.append(frame)
            if frame.get("type") in {
                "error",
                "model_forbidden",
                "insufficient_credits",
                "turn_end",
            }:
                break
    assert any(f["type"] == "turn_end" for f in frames), frames
    assert any("你想聊什么" in f.get("content", f.get("delta", "")) for f in frames), frames
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM chat_messages WHERE user_id=%s AND character_id=%s", (uid, cid)
        )
        assert cur.fetchone()[0] >= 2
    paths = api_context.get("/api/openapi.json").json()["paths"]
    assert not any(
        p.startswith("/api/webhooks")
        for p in paths
    )


def test_google_flow_rejects_wrong_browser_and_replay(api_context):
    assert api_context.get("/api/auth/google/config").json() == {"enabled": True}
    start = api_context.get("/api/auth/google/start", max_redirects=0)
    assert start.status == 303
    location = urlsplit(start.headers["location"])
    assert location.hostname == "accounts.google.com"
    params = parse_qs(location.query)
    assert params["scope"] == ["openid email profile"]
    assert params["code_challenge_method"] == ["S256"]
    assert "HttpOnly" in start.headers["set-cookie"]
    assert "SameSite=lax" in start.headers["set-cookie"]
    state = params["state"][0]
    with redis.from_url(os.environ["REDIS_URL"]) as client:
        flow = json.loads(client.get(f"google:state:{state}"))
        import base64

        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(flow["verifier"].encode()).digest())
            .decode()
            .rstrip("=")
        )
        assert params["code_challenge"] == [challenge]
    wrong = api_context.get(
        f"/api/auth/google/callback?state={state}&code=fake",
        headers={"Cookie": "yuoyuo_google_flow=wrong"},
        max_redirects=0,
    )
    assert wrong.status == 400 and wrong.json()["detail"] == "invalid_google_browser"
    replay = api_context.get(f"/api/auth/google/callback?state={state}&code=fake", max_redirects=0)
    assert replay.status == 400 and replay.json()["detail"] == "invalid_google_state"


def test_google_exchange_creates_one_account_and_preserves_language_pause(api_context, pg_conn):
    subject = str(uuid4())
    email = f"test-{subject}@gmail.com"
    browser = secrets.token_urlsafe(32)
    headers = {"Cookie": f"yuoyuo_google_flow={browser}"}

    def ticket():
        value = secrets.token_urlsafe(32)
        with redis.from_url(os.environ["REDIS_URL"]) as client:
            client.setex(
                f"google:ticket:{value}",
                90,
                json.dumps(
                    {
                        "sub": subject,
                        "email": email,
                        "authoritative_email": True,
                        "browser": browser,
                        "locale": "ko",
                    }
                ),
            )
        return value

    first_ticket = ticket()
    first = api_context.post(
        "/api/auth/google/exchange", headers=headers, data={"ticket": first_ticket}
    )
    assert first.ok, first.text()
    data = first.json()
    assert data["needs_profile"] is True
    assert data["user"]["email"] == email
    assert (
        api_context.post(
            "/api/auth/google/exchange", headers=headers, data={"ticket": first_ticket}
        ).status
        == 400
    )
    again = api_context.post(
        "/api/auth/google/exchange", headers=headers, data={"ticket": ticket()}
    )
    assert again.ok, again.text()
    assert again.json()["user"]["id"] == data["user"]["id"]
    profile = api_context.get(
        "/api/profile", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert profile.ok, profile.text()
    with pg_conn.cursor() as cur:
        uid = data["user"]["id"]
        cur.execute("SELECT count(*) FROM user_language_preferences WHERE user_id=%s", (uid,))
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM oauth_identities WHERE user_id=%s", (uid,))
        assert cur.fetchone()[0] == 1
        cur.execute(
            "SELECT count(*) FROM credit_transactions WHERE user_id=%s AND type='grant'", (uid,)
        )
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT count(*) FROM auth_sessions WHERE user_id=%s", (uid,))
        assert cur.fetchone()[0] == 2
