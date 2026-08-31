"""E2E: profile entry updates real views and cover heat on every visit."""

from __future__ import annotations

import pytest

from .conftest import DEMO_CHARACTER_ID, DEMO_USER_ID


@pytest.mark.e2e
def test_profile_entries_each_increment_real_view_and_random_heat(api_context, pg_conn):
    login = api_context.post(
        "/api/auth/login",
        data={"user_id": DEMO_USER_ID, "email": "e2e@example.com"},
    )
    assert login.ok, login.text()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with pg_conn.cursor() as cursor:
        cursor.execute(
            "SELECT display_heat, real_view_count FROM characters WHERE id = %s",
            (DEMO_CHARACTER_ID,),
        )
        before_heat, before_views = cursor.fetchone()

    first = api_context.post(f"/api/characters/{DEMO_CHARACTER_ID}/view", headers=headers)
    second = api_context.post(f"/api/characters/{DEMO_CHARACTER_ID}/view", headers=headers)
    assert first.ok, first.text()
    assert second.ok, second.text()

    with pg_conn.cursor() as cursor:
        cursor.execute(
            "SELECT display_heat, real_view_count FROM characters WHERE id = %s",
            (DEMO_CHARACTER_ID,),
        )
        after_heat, after_views = cursor.fetchone()

    assert after_views == before_views + 2
    assert before_heat + 200 <= after_heat <= before_heat + 800

    catalog = api_context.get("/api/characters", headers=headers)
    assert catalog.ok, catalog.text()
    rin = next(item for item in catalog.json()["characters"] if item["id"] == DEMO_CHARACTER_ID)
    assert rin["display_heat"] == after_heat
    assert rin["real_view_count"] == after_views
