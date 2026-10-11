"""Local-only review must not expose restored private content through a tunnel."""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from heart.api.local_review import LocalReviewOnlyMiddleware
from heart.core.config import Settings


def test_review_config_rejects_production_and_remote_database():
    base = dict(
        _env_file=None,
        local_character_review=True,
        heart_dev_mode="true",
        database_url="postgresql+asyncpg://heart:test@127.0.0.1/heart_review",
        jwt_algorithm="HS256",
        jwt_secret_key="test-only-secret-at-least-32-characters",
    )
    assert Settings(**base).local_character_review
    for changes in (
        {"environment": "production"},
        {"heart_dev_mode": "false"},
        {"database_url": "postgresql+asyncpg://heart:test@db.example.com/heart"},
    ):
        with pytest.raises(ValueError):
            Settings(**{**base, **changes})


@pytest.mark.parametrize(
    "headers,allowed",
    [
        ({}, True),
        ({"Host": "public.example.com"}, False),
        ({"CF-Connecting-IP": "192.0.2.1"}, False),
        ({"X-Forwarded-Host": "public.example.com"}, False),
    ],
)
def test_review_rejects_external_hosts_and_tunnels(headers, allowed):
    async def endpoint(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api/test", endpoint)])
    app.add_middleware(LocalReviewOnlyMiddleware)
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 12000)) as client:
        assert client.get("/api/test", headers=headers).status_code == (200 if allowed else 403)


@pytest.mark.parametrize("as_owner", [False, True])
def test_review_catalog_only_lists_active_approved_public_or_unlisted(as_owner):
    from uuid import uuid4

    from heart.ss01_soul.character_catalog import CharacterRow, build_catalog_entries

    owner = uuid4()
    rows = [
        CharacterRow(f"{visibility}-{status}-{review}", owner, visibility, status, review)
        for visibility in ("public", "unlisted", "private")
        for status in ("active", "disabled")
        for review in ("approved", "pending", "rejected", "not_required")
    ]
    entries = build_catalog_entries(
        rows,
        owner if as_owner else None,
        display_names={row.id: row.id for row in rows},
        local_review=True,
    )
    assert {e.id for e in entries} == {"public-active-approved", "unlisted-active-approved"}
    assert {e.visibility for e in entries} == {"public", "unlisted"}
    ordinary = build_catalog_entries(rows, None, display_names={r.id: r.id for r in rows})
    assert {e.id for e in ordinary} == {"public-active-approved"}
