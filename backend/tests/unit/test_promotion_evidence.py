"""Promotion evidence proxy and retention behavior."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.api.routes_promotions import admin_promotion_image
from heart.core.config import settings
from heart.infra.storage import object_key_from_storage_url
from heart.workers.promotion_cleanup_worker import _purge_expired_promotions


def test_object_key_from_internal_minio_url(monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket_name", "yuoyuo-media-prod")
    value = "http://minio:9000/yuoyuo-media-prod/promotion-evidence/user/image.png"
    assert object_key_from_storage_url(value) == "promotion-evidence/user/image.png"


def test_object_key_from_private_handle():
    assert (
        object_key_from_storage_url("s3://promotion-evidence/user/image.webp")
        == "promotion-evidence/user/image.webp"
    )


@pytest.mark.asyncio
async def test_admin_image_proxy_reads_legacy_storage_url(monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket_name", "yuoyuo-media-prod")
    submission_id = uuid.uuid4()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = (
        "http://minio:9000/yuoyuo-media-prod/promotion-evidence/user/image.png"
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=scalar_result)

    with patch(
        "heart.infra.storage.get_s3_object",
        new=AsyncMock(return_value=(b"image-bytes", "image/png", "etag")),
    ) as fetch:
        response = await admin_promotion_image(str(submission_id), None, db)

    assert response.body == b"image-bytes"
    assert response.media_type == "image/png"
    assert response.headers["cache-control"] == "private, max-age=300"
    fetch.assert_awaited_once_with("promotion-evidence/user/image.png")


@pytest.mark.asyncio
async def test_cleanup_deletes_s3_object_before_approved_record():
    submission_id = uuid.uuid4()
    rows_result = MagicMock()
    rows_result.mappings.return_value.all.return_value = [
        {"id": submission_id, "screenshot_url": "s3://promotion-evidence/user/image.webp"}
    ]
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[rows_result, MagicMock()])
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=session)

    with (
        patch("heart.workers.promotion_cleanup_worker.is_s3_configured", return_value=True),
        patch(
            "heart.workers.promotion_cleanup_worker.delete_s3_object", new=AsyncMock()
        ) as delete_object,
    ):
        await _purge_expired_promotions(factory)

    delete_object.assert_awaited_once_with("promotion-evidence/user/image.webp")
    assert "reviewed_at < NOW() - INTERVAL '3 days'" in str(
        session.execute.await_args_list[0].args[0]
    )
    assert "DELETE FROM promotion_submissions" in str(session.execute.await_args_list[1].args[0])
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_defers_record_when_storage_is_unavailable():
    rows_result = MagicMock()
    rows_result.mappings.return_value.all.return_value = [
        {"id": uuid.uuid4(), "screenshot_url": "s3://promotion-evidence/user/image.jpg"}
    ]
    session = MagicMock()
    session.execute = AsyncMock(return_value=rows_result)
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=session)

    with patch("heart.workers.promotion_cleanup_worker.is_s3_configured", return_value=False):
        await _purge_expired_promotions(factory)

    assert session.execute.await_count == 1
    session.commit.assert_awaited_once()
