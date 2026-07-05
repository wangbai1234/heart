"""Embedding service — turns text into dense vectors for semantic memory recall.

DeepSeek (the project's LLM provider) has no embeddings endpoint, so this talks
to an OpenAI-compatible hosted embeddings API (default: SiliconFlow serving
BAAI/bge-m3, 1024-dim). The interface is deliberately small:

    vecs = await service.embed_texts(["我家猫叫年糕", ...])   # write path (batched)
    q    = await service.embed_query("你还记得我的猫吗")       # query path (single)

Graceful degradation: `build_embedding_service()` returns None when no API key
is configured, so callers (MemoryService, cold path, composer) simply skip
embedding and fall back to recency/identity retrieval — never crash.

Author: 心屿团队
"""

from __future__ import annotations

import abc
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()


class EmbeddingError(RuntimeError):
    """Raised when the embedding backend fails. Callers should degrade gracefully."""


class EmbeddingService(abc.ABC):
    """Abstract embedding backend. All vectors have `dimensions` length."""

    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @abc.abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per input, same order."""

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        vecs = await self.embed_texts([text])
        return vecs[0]


class HostedEmbeddingService(EmbeddingService):
    """OpenAI-compatible `/embeddings` client (SiliconFlow / OpenAI / 通义 …)."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        dimensions: int,
        batch_size: int = 32,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(dimensions)
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._batch_size = max(1, batch_size)
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = await self._get_client()
        out: list[list[float]] = []
        # Chunk into batches to respect provider input limits.
        for start in range(0, len(texts), self._batch_size):
            chunk = texts[start : start + self._batch_size]
            try:
                resp = await client.post(
                    "/embeddings",
                    json={"model": self._model, "input": chunk},
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                raise EmbeddingError(f"embedding request failed: {e}") from e
            # OpenAI-compatible: {"data": [{"index": i, "embedding": [...]}, ...]}
            items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
            if len(items) != len(chunk):
                raise EmbeddingError(
                    f"embedding count mismatch: got {len(items)} for {len(chunk)} inputs"
                )
            for item in items:
                vec = item.get("embedding")
                if not isinstance(vec, list) or len(vec) != self._dimensions:
                    raise EmbeddingError(
                        f"unexpected embedding dim: got {len(vec) if isinstance(vec, list) else '?'}, "
                        f"expected {self._dimensions}"
                    )
                out.append([float(x) for x in vec])
        return out


class FakeEmbeddingService(EmbeddingService):
    """Deterministic, dependency-free embeddings for tests/offline dev.

    Not semantically meaningful, but stable per input and correctly shaped, so
    write/query wiring and pgvector round-trips can be exercised without a key.
    """

    def __init__(self, dimensions: int = 1024) -> None:
        super().__init__(dimensions)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(t) for t in texts]

    def _vector_for(self, text: str) -> list[float]:
        # Simple, stable hashing to floats in [-1, 1]; no external deps, no RNG.
        vec: list[float] = []
        for i in range(self._dimensions):
            h = hash((text, i)) % 2000
            vec.append((h - 1000) / 1000.0)
        return vec


def build_embedding_service(settings=None) -> Optional[EmbeddingService]:
    """Build the hosted service from settings, or None when no API key is set.

    Returning None is the disabled path: memory keeps working via recency/identity
    retrieval, exactly as before semantic recall existed.
    """
    if settings is None:
        from heart.core.config import Settings

        settings = Settings()

    api_key = getattr(settings, "embedding_api_key", "") or ""
    if not api_key:
        logger.info("embedding_service_disabled_no_api_key")
        return None

    svc = HostedEmbeddingService(
        api_key=api_key,
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
    )
    logger.info(
        "embedding_service_initialized",
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        base_url=settings.embedding_base_url,
    )
    return svc
