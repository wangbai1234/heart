"""Tests for the embedding service (PR4a).

Covers the Fake backend (shape/determinism), the hosted OpenAI-compatible
client (batching, ordering, dim validation, error mapping), and the
build-from-settings graceful-disable path.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from heart.infra.embeddings import (
    EmbeddingError,
    FakeEmbeddingService,
    HostedEmbeddingService,
    build_embedding_service,
)

# ── Fake backend ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fake_embeddings_shape_and_determinism():
    svc = FakeEmbeddingService(dimensions=1024)
    a = await svc.embed_texts(["猫叫年糕", "你好"])
    assert len(a) == 2
    assert all(len(v) == 1024 for v in a)
    assert all(-1.0 <= x <= 1.0 for x in a[0])
    # Deterministic per input.
    b = await svc.embed_texts(["猫叫年糕"])
    assert b[0] == a[0]
    # Different inputs → different vectors.
    assert a[0] != a[1]


@pytest.mark.asyncio
async def test_fake_embed_query_and_empty():
    svc = FakeEmbeddingService(dimensions=8)
    q = await svc.embed_query("hi")
    assert len(q) == 8
    assert await svc.embed_texts([]) == []


# ── Hosted backend ────────────────────────────────────────────


def _make_hosted(dim: int = 4) -> HostedEmbeddingService:
    return HostedEmbeddingService(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="BAAI/bge-m3",
        dimensions=dim,
        batch_size=2,
    )


def _resp(vectors: list[list[float]]) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json = MagicMock(
        return_value={"data": [{"index": i, "embedding": v} for i, v in enumerate(vectors)]}
    )
    return r


@pytest.mark.asyncio
async def test_hosted_batches_and_preserves_order():
    svc = _make_hosted(dim=4)
    await svc._get_client()
    # batch_size=2 over 3 inputs → two POSTs.
    responses = [
        _resp([[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]),
        _resp([[0.9, 1.0, 1.1, 1.2]]),
    ]
    with patch.object(svc._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = responses
        out = await svc.embed_texts(["a", "b", "c"])

    assert mock_post.await_count == 2
    assert len(out) == 3
    assert out[0] == [0.1, 0.2, 0.3, 0.4]
    assert out[2] == [0.9, 1.0, 1.1, 1.2]


@pytest.mark.asyncio
async def test_hosted_reorders_by_index():
    svc = _make_hosted(dim=2)
    await svc._get_client()
    # Provider returns out-of-order; service must sort by index.
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(
        return_value={
            "data": [
                {"index": 1, "embedding": [9.0, 9.0]},
                {"index": 0, "embedding": [1.0, 1.0]},
            ]
        }
    )
    with patch.object(svc._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp
        out = await svc.embed_texts(["first", "second"])
    assert out[0] == [1.0, 1.0]
    assert out[1] == [9.0, 9.0]


@pytest.mark.asyncio
async def test_hosted_rejects_wrong_dimension():
    svc = _make_hosted(dim=4)
    await svc._get_client()
    with patch.object(svc._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _resp([[0.1, 0.2]])  # dim 2, expected 4
        with pytest.raises(EmbeddingError, match="dim"):
            await svc.embed_texts(["x"])


@pytest.mark.asyncio
async def test_hosted_maps_http_error():
    svc = _make_hosted(dim=4)
    await svc._get_client()
    with patch.object(svc._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("boom")
        with pytest.raises(EmbeddingError, match="failed"):
            await svc.embed_texts(["x"])


# ── build_embedding_service ───────────────────────────────────


def test_build_returns_none_without_key():
    settings = SimpleNamespace(
        embedding_api_key="",
        embedding_base_url="https://api.siliconflow.cn/v1",
        embedding_model="BAAI/bge-m3",
        embedding_dimensions=1024,
        embedding_batch_size=32,
    )
    assert build_embedding_service(settings) is None


def test_build_returns_hosted_with_key():
    settings = SimpleNamespace(
        embedding_api_key="sk-abc",
        embedding_base_url="https://api.siliconflow.cn/v1",
        embedding_model="BAAI/bge-m3",
        embedding_dimensions=1024,
        embedding_batch_size=32,
    )
    svc = build_embedding_service(settings)
    assert isinstance(svc, HostedEmbeddingService)
    assert svc.dimensions == 1024
