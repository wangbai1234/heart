"""Cache-header / ETag / 304 behavior for the image proxy endpoints.

These endpoints (avatar-file, story covers) proxy bytes out of MinIO/S3. Without
cache headers the browser re-downloads every image on every refresh and each hit
re-reads the whole object from MinIO — the root cause of slow image loads. These
tests lock in the immutable Cache-Control + ETag + If-None-Match→304 behavior.

No DB or auth is required for these routes, so they run without DATABASE_URL.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from heart.api.main import create_app

_IMMUTABLE = "public, max-age=31536000, immutable"


@pytest.fixture
def client():
    return TestClient(create_app())


# ── avatar-file endpoint ────────────────────────────────────────────────────


def test_avatar_full_fetch_sets_immutable_cache_and_etag(client):
    with patch(
        "heart.infra.storage.get_s3_object",
        new=AsyncMock(return_value=(b"\x89PNG-bytes", "image/webp", "etag-avatar")),
    ):
        resp = client.get("/api/profile/avatar-file/user-1/abc.webp")

    assert resp.status_code == 200
    assert resp.content == b"\x89PNG-bytes"
    assert resp.headers["Cache-Control"] == _IMMUTABLE
    assert resp.headers["ETag"] == '"etag-avatar"'


def test_avatar_if_none_match_returns_304_without_body(client):
    head = AsyncMock(return_value=("etag-avatar", "image/webp"))
    get = AsyncMock(return_value=(b"should-not-be-read", "image/webp", "etag-avatar"))
    with (
        patch("heart.infra.storage.head_s3_object", new=head),
        patch("heart.infra.storage.get_s3_object", new=get),
    ):
        resp = client.get(
            "/api/profile/avatar-file/user-1/abc.webp",
            headers={"If-None-Match": '"etag-avatar"'},
        )

    assert resp.status_code == 304
    assert resp.content == b""
    assert resp.headers["Cache-Control"] == _IMMUTABLE
    # 304 must short-circuit on the cheap head, never read the full body.
    get.assert_not_awaited()


def test_avatar_if_none_match_mismatch_returns_full_200(client):
    head = AsyncMock(return_value=("etag-new", "image/webp"))
    get = AsyncMock(return_value=(b"new-bytes", "image/webp", "etag-new"))
    with (
        patch("heart.infra.storage.head_s3_object", new=head),
        patch("heart.infra.storage.get_s3_object", new=get),
    ):
        resp = client.get(
            "/api/profile/avatar-file/user-1/abc.webp",
            headers={"If-None-Match": '"stale-etag"'},
        )

    assert resp.status_code == 200
    assert resp.content == b"new-bytes"
    assert resp.headers["ETag"] == '"etag-new"'


def test_avatar_missing_object_404(client):
    with patch(
        "heart.infra.storage.get_s3_object",
        new=AsyncMock(side_effect=RuntimeError("NoSuchKey")),
    ):
        resp = client.get("/api/profile/avatar-file/user-1/missing.webp")
    assert resp.status_code == 404


# ── story cover endpoint ────────────────────────────────────────────────────


def test_cover_full_fetch_sets_immutable_cache_and_etag(client):
    with patch(
        "heart.infra.storage.get_s3_object",
        new=AsyncMock(return_value=(b"cover-bytes", "image/png", "etag-cover")),
    ):
        resp = client.get("/api/story/covers/my-scenario")

    assert resp.status_code == 200
    assert resp.content == b"cover-bytes"
    assert resp.headers["Cache-Control"] == _IMMUTABLE
    assert resp.headers["ETag"] == '"etag-cover"'


def test_cover_if_none_match_returns_304(client):
    head = AsyncMock(return_value=("etag-cover", "image/png"))
    get = AsyncMock(return_value=(b"unused", "image/png", "etag-cover"))
    with (
        patch("heart.infra.storage.head_s3_object", new=head),
        patch("heart.infra.storage.get_s3_object", new=get),
    ):
        resp = client.get(
            "/api/story/covers/my-scenario",
            headers={"If-None-Match": '"etag-cover"'},
        )

    assert resp.status_code == 304
    assert resp.headers["Cache-Control"] == _IMMUTABLE
    get.assert_not_awaited()


def test_cover_missing_object_404(client):
    with patch(
        "heart.infra.storage.get_s3_object",
        new=AsyncMock(side_effect=RuntimeError("NoSuchKey")),
    ):
        resp = client.get("/api/story/covers/nope")
    assert resp.status_code == 404
