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
