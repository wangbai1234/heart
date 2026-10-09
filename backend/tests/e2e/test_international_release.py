"""Real HTTP/WS + PostgreSQL release checks (run with INTERNATIONAL_MODE=true)."""

import json
import os
from uuid import uuid4

import pytest
from websockets.sync.client import connect

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("INTERNATIONAL_MODE") != "true", reason="International release only"
    ),
]


def login(api, uid):
    response = api.post(
        "/api/auth/login",
        data={
            "user_id": uid,
            "email": f"intl-{uid}@example.com",
        },
    )
    assert response.ok, response.text()
    return response.json()["access_token"]


def test_preferences_private_characters_and_chat(api_context, pg_conn, e2e_server):
    first, second = str(uuid4()), str(uuid4())
    token = login(api_context, first)
    other_token = login(api_context, second)
    headers = {"Authorization": f"Bearer {token}", "Accept-Language": "ko"}
    other = {"Authorization": f"Bearer {other_token}"}
    preferences = {
        "interface_language": "ko",
        "response_language": "ja",
        "action_style": "fullwidth",
        "response_follows_interface": False,
    }
    saved = api_context.put("/api/profile/preferences", headers=headers, data=preferences)
    assert saved.ok, saved.text()
    assert api_context.get("/api/profile/preferences", headers=headers).json() == preferences
    exported = api_context.post("/api/account/export", headers=headers)
    assert exported.ok, exported.text()
    assert exported.json()["language_preferences"] == preferences
    assert (
        api_context.get("/api/profile/preferences", headers=other).json()["response_language"]
        == "en"
    )
    assert (
        api_context.put(
            "/api/profile/preferences",
            headers=headers,
            data={**preferences, "response_language": "zh"},
        ).status
        == 422
    )
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT response_language, action_style FROM user_language_preferences WHERE user_id=%s",
            (first,),
        )
        assert cur.fetchone() == ("ja", "fullwidth")
        cur.execute(
            "UPDATE users SET age_verified_at=NOW(), credits_balance=100000 WHERE id=%s", (first,)
        )
    pg_conn.commit()
    created = api_context.post(
        "/api/characters",
        headers=headers,
        data={
            "display_name": {"ko": "테스트 작가"},
            "persona": "A thoughtful adult writer who listens carefully and invites quiet conversation.",
            "tagline": "작은 이야기의 시작",
            "locale": "ko",
            "visibility": "private",
            "creation_mode": "workshop",
        },
    )
    assert created.ok, created.text()
    cid = created.json()["id"]
    assert api_context.get(f"/api/characters/{cid}/profile", headers=headers).ok
    assert api_context.get(f"/api/characters/{cid}/profile", headers=other).status == 404
    assert api_context.get(f"/api/characters/{cid}/profile").status == 404
    frames = []
    with connect(
        e2e_server.replace("http://", "ws://") + f"/api/chat/ws?token={token}", open_timeout=10
    ) as ws:
        ws.send(
            json.dumps(
                {"type": "chat", "character_id": cid, "text": "Hello, tell me about your writing."}
            )
        )
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
        # Save while the same WebSocket is still open; the next turn must load it.
        followed = api_context.put(
            "/api/profile/preferences",
            headers=headers,
            data={**preferences, "interface_language": "ko", "response_follows_interface": True},
        )
        assert followed.ok, followed.text()
        assert followed.json()["response_language"] == "ko"
        ws.send(json.dumps({"type": "chat", "character_id": cid, "text": "Please continue."}))
        switched_frames = []
        for _ in range(200):
            frame = json.loads(ws.recv(timeout=30))
            switched_frames.append(frame)
            if frame.get("type") in {"error", "turn_end"}:
                break
        assert any(f["type"] == "turn_end" for f in switched_frames), switched_frames
        assert any(
            "어떤 이야기" in f.get("content", f.get("delta", "")) for f in switched_frames
        ), switched_frames
    assert any(f["type"] == "turn_end" for f in frames), frames
    assert not any(f["type"] == "error" for f in frames), frames
    assert any("どんな物語" in f.get("content", f.get("delta", "")) for f in frames), frames
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM chat_messages WHERE user_id=%s AND character_id=%s", (first, cid)
        )
        assert cur.fetchone()[0] >= 2
    disabled = api_context.post(f"/api/characters/{cid}/disable", headers=headers)
    assert disabled.ok, disabled.text()
    assert api_context.get(f"/api/characters/{cid}/profile", headers=headers).status == 404


def test_international_catalog_and_no_commerce(api_context):
    catalog = api_context.get("/api/characters", headers={"Accept-Language": "ko"}).json()[
        "characters"
    ]
    assert any(c["id"] == "intl_haru" and c["display_name"] == "하루" for c in catalog)
    assert not any(c["id"] == "rin" for c in catalog)
    profile = api_context.get(
        "/api/characters/intl_haru/profile", headers={"Accept-Language": "ja"}
    )
    assert profile.ok, profile.text()
    assert "古書店" in profile.json()["intro"]
    schema = api_context.get("/api/openapi.json").json()["paths"]
    assert not any(
        p.startswith(("/api/webhooks", "/api/commission", "/api/lottery", "/api/promotions"))
        for p in schema
    )


@pytest.mark.parametrize("locale", ["ja", "ko"])
def test_signup_initializes_selected_language(api_context, pg_conn, locale):
    from heart.api.routes_auth import _hash_code

    email = f"signup-{uuid4()}@example.com"
    with pg_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO email_otp_codes (id, email, code_hash, purpose, expires_at) "
            "VALUES (%s, %s, %s, 'register', NOW() + interval '10 minutes')",
            (str(uuid4()), email, _hash_code("123456")),
        )
    pg_conn.commit()
    response = api_context.post(
        "/api/auth/register",
        headers={"Accept-Language": locale},
        data={"email": email, "otp_code": "123456", "password": "Signup-test-password1"},
    )
    assert response.ok, response.text()
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    preferences = api_context.get("/api/profile/preferences", headers=headers).json()
    assert preferences == {
        "interface_language": locale,
        "response_language": locale,
        "action_style": "fullwidth",
        "response_follows_interface": True,
    }
    # Subsequent login in a different browser language must not reset the choice.
    login_response = api_context.post(
        "/api/auth/login/password",
        headers={"Accept-Language": "en"},
        data={"email": email, "password": "Signup-test-password1"},
    )
    assert login_response.ok, login_response.text()
    assert api_context.get("/api/profile/preferences", headers=headers).json() == preferences


def test_shared_memory_corrections_are_private_audited_and_conflict_safe(api_context, pg_conn):
    first, second = str(uuid4()), str(uuid4())
    token, other = login(api_context, first), login(api_context, second)
    headers = {"Authorization": f"Bearer {token}"}
    cid, mid = 'intl_haru', str(uuid4())
    with pg_conn.cursor() as cur:
        cur.execute("INSERT INTO identity_memories (id,user_id,character_id,category,key,value,disclosed_at,sacred_reason,significance_score,promotion_trigger) VALUES (%s,%s,%s,'identity','favorite_place','Old library',NOW(),'User shared',0.9,'test')", (mid,first,cid))
    pg_conn.commit()
    bond = api_context.get(f'/api/companions/{cid}/bond', headers=headers)
    assert bond.ok, bond.text()
    assert any(m['id'] == mid for m in bond.json()['memories'])
    payload = {'content':'New library', 'expected_content':'Old library', 'confirm_identity':True}
    url = f'/api/companions/{cid}/memories/L4/{mid}'
    denied = api_context.patch(url, headers={'Authorization':f'Bearer {other}'}, data=payload)
    assert denied.status == 404
    changed = api_context.patch(url, headers=headers, data=payload)
    assert changed.ok, changed.text()
    assert api_context.patch(url, headers=headers, data=payload).status == 409
    with pg_conn.cursor() as cur:
        cur.execute('SELECT value FROM identity_memories WHERE id=%s', (mid,))
        assert cur.fetchone()[0] == 'New library'
        cur.execute('SELECT old_value,new_value,actor FROM memory_audit_log WHERE entity_ref=%s', (mid,))
        old,new,actor = cur.fetchone()
        assert old['content'] == 'Old library' and new['content'] == 'New library' and actor == 'user'


def test_l3_correction_clears_stale_recall_and_requires_ownership(api_context, pg_conn):
    uid, mid = str(uuid4()), str(uuid4())
    token = login(api_context, uid)
    headers = {'Authorization': f'Bearer {token}'}
    with pg_conn.cursor() as cur:
        cur.execute("""INSERT INTO fact_nodes (id,user_id,character_id,predicate,subject,object,literal_text,raw_evidence,confidence,emotional_charge,importance,state,semantic_vector,reconstruction_hints)
            VALUES (%s,%s,'intl_haru','likes','user','coffee','Likes coffee','Original message',0.9,0.2,0.8,'vivid',%s::vector,'{"detail":"coffee"}')""", (mid,uid,'['+','.join(['0.1']*1024)+']'))
    pg_conn.commit()
    changed = api_context.patch(f'/api/companions/intl_haru/memories/L3/{mid}',headers=headers,data={'content':'Likes tea','expected_content':'Likes coffee'})
    assert changed.ok, changed.text()
    with pg_conn.cursor() as cur:
        cur.execute('SELECT object,literal_text,semantic_vector,reconstruction_hints,is_corrected FROM fact_nodes WHERE id=%s AND user_id=%s',(mid,uid))
        assert cur.fetchone() == ('Likes tea','Likes tea',None,{},True)


def test_catalog_filters_do_not_expose_private_characters(api_context):
    japanese = api_context.get('/api/characters?content_language=ja').json()['characters']
    assert japanese and all(c['content_language']=='ja' for c in japanese)
    assert api_context.get('/api/characters?q=not_a_real_plot_983241').json()['characters'] == []
    assert api_context.get('/api/auth/google/config').json() == {'enabled':False}
    assert api_context.get('/api/auth/google/start').status == 503
