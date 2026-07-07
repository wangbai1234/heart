"""
Pooled TTS provider — outbound concurrency limiting + multi-key rotation + 429 failover.

Wraps N single-key MiniMax providers behind the TTSProvider Protocol. MiniMax account
concurrency caps are typically single-digit, so a burst of simultaneous voice turns is
the *first* thing to saturate in this system. This pool:

1. Caps total in-flight TTS with an asyncio.Semaphore so bursts queue instead of 429ing.
2. Spreads load across 1..N keys (least-in-flight selection), routing around a cooling key.
3. On 429/5xx, cools the offending key briefly and retries on another key.

Single key = pool of one → the limiter + retry still apply. Non-streaming failover is
transparent; streaming only fails over before the first audio chunk is emitted.

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, List

import structlog

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.provider import TTSProvider
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult

logger = structlog.get_logger(__name__)

_RETRIABLE_STATUS = {429, 500, 502, 503, 504}


class PooledTTSProvider:
    """TTSProvider that dispatches across a pool of single-key TTS providers."""

    def __init__(
        self,
        members: List[TTSProvider],
        max_concurrency: int = 4,
        max_retries: int = 1,
        cooldown_seconds: float = 20.0,
    ) -> None:
        if not members:
            raise ValueError("PooledTTSProvider requires at least one member provider")
        self._members = members
        self._sem = asyncio.Semaphore(max(1, max_concurrency))
        self._max_retries = max(0, max_retries)
        self._cooldown = max(0.0, cooldown_seconds)
        self._in_flight = [0] * len(members)
        self._cooldown_until = [0.0] * len(members)

    @asynccontextmanager
    async def _slot(self) -> AsyncIterator[None]:
        await self._sem.acquire()
        try:
            yield
        finally:
            self._sem.release()

    def _pick(self) -> int:
        now = time.monotonic()
        idxs = [i for i in range(len(self._members)) if self._cooldown_until[i] <= now]
        if not idxs:
            idxs = list(range(len(self._members)))
        return min(idxs, key=lambda i: (self._in_flight[i], self._cooldown_until[i]))

    def _cool(self, i: int) -> None:
        if self._cooldown > 0:
            self._cooldown_until[i] = time.monotonic() + self._cooldown

    @staticmethod
    def _retriable(e: TTSProviderError) -> bool:
        return e.status_code in _RETRIABLE_STATUS

    async def synthesize(self, req: TTSRequest) -> TTSResult:
        last: TTSProviderError | None = None
        async with self._slot():
            for attempt in range(self._max_retries + 1):
                i = self._pick()
                self._in_flight[i] += 1
                try:
                    return await self._members[i].synthesize(req)
                except TTSProviderError as e:
                    last = e
                    if not self._retriable(e) or attempt >= self._max_retries:
                        raise
                    self._cool(i)
                    logger.warning(
                        "tts_pool_failover", index=i, status_code=e.status_code, attempt=attempt + 1
                    )
                finally:
                    self._in_flight[i] = max(0, self._in_flight[i] - 1)
        assert last is not None
        raise last

    async def stream_synthesize(self, req: TTSRequest) -> AsyncIterator[AudioChunk]:
        last: TTSProviderError | None = None
        async with self._slot():
            for attempt in range(self._max_retries + 1):
                i = self._pick()
                self._in_flight[i] += 1
                started = False
                try:
                    async for chunk in self._members[i].stream_synthesize(req):  # type: ignore[attr-defined]
                        started = True
                        yield chunk
                    return
                except TTSProviderError as e:
                    last = e
                    if started or not self._retriable(e) or attempt >= self._max_retries:
                        raise
                    self._cool(i)
                    logger.warning(
                        "tts_pool_stream_failover",
                        index=i,
                        status_code=e.status_code,
                        attempt=attempt + 1,
                    )
                finally:
                    self._in_flight[i] = max(0, self._in_flight[i] - 1)
            if last is not None:
                raise last

    def estimate_cost_cents(self, text: str) -> float:
        return self._members[0].estimate_cost_cents(text)

    @property
    def name(self) -> str:
        return self._members[0].name

    async def close(self) -> None:
        for m in self._members:
            client = getattr(m, "_client", None)
            if client is not None:
                await client.aclose()
