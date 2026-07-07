"""Unit tests for PooledTTSProvider — concurrency cap + 429 failover."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.pooled_provider import PooledTTSProvider
from heart.ss08_voice.types import AudioChunk, TTSRequest, TTSResult


class _StubTTS:
    def __init__(self, key: str, *, fail_times: int = 0, status: int = 429):
        self._key = key
        self.fail_times = fail_times
        self.status = status
        self.calls = 0
        self.active = 0
        self.max_active = 0

    async def synthesize(self, req: TTSRequest) -> TTSResult:
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.fail_times > 0:
                self.fail_times -= 1
                raise TTSProviderError("boom", status_code=self.status)
            await asyncio.sleep(0.01)
            return TTSResult(audio=self._key.encode(), format=req.format, duration_ms=1, request_id=self._key)
        finally:
            self.active -= 1

    async def stream_synthesize(self, req: TTSRequest) -> AsyncIterator[AudioChunk]:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise TTSProviderError("boom", status_code=self.status)
        yield AudioChunk(seq=0, data=self._key.encode(), format=req.format, is_last=True)

    def estimate_cost_cents(self, text: str) -> float:
        return 0.0

    @property
    def name(self) -> str:
        return "minimax"


def _req() -> TTSRequest:
    return TTSRequest(text="你好", voice_id="v1")


@pytest.mark.asyncio
async def test_single_key_passthrough():
    m = _StubTTS("k1")
    pool = PooledTTSProvider([m], max_concurrency=4, max_retries=1)
    res = await pool.synthesize(_req())
    assert res.request_id == "k1"
    assert pool.name == "minimax"


@pytest.mark.asyncio
async def test_429_failover():
    bad = _StubTTS("bad", fail_times=1, status=429)
    good = _StubTTS("good")
    pool = PooledTTSProvider([bad, good], max_concurrency=4, max_retries=1)
    res = await pool.synthesize(_req())
    assert res.request_id == "good"


@pytest.mark.asyncio
async def test_non_retriable_propagates():
    bad = _StubTTS("bad", fail_times=1, status=400)
    good = _StubTTS("good")
    pool = PooledTTSProvider([bad, good], max_concurrency=4, max_retries=1)
    with pytest.raises(TTSProviderError):
        await pool.synthesize(_req())
    assert good.calls == 0


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    members = [_StubTTS(f"k{i}") for i in range(3)]
    pool = PooledTTSProvider(members, max_concurrency=2, max_retries=0)
    await asyncio.gather(*(pool.synthesize(_req()) for _ in range(9)))
    assert max(m.max_active for m in members) <= 2
    assert sum(m.calls for m in members) == 9
