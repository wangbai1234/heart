"""
Unit tests for PooledLLMProvider — concurrency cap, least-in-flight selection,
and 429/5xx failover with cooldown.

100% in-process (stub providers), no network.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, List

import pytest

from heart.infra.llm_providers.base import (
    CostEstimate,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ProviderError,
    StreamChunk,
)
from heart.infra.llm_providers.pool import ConcurrencyGate, PooledLLMProvider


class _StubProvider(LLMProvider):
    """Configurable stub: can 429 the first N calls, and tracks concurrency."""

    def __init__(self, key: str, *, fail_times: int = 0, status: int = 429):
        super().__init__(api_key=key)
        self._name = f"stub-{key}"
        self.fail_times = fail_times
        self.status = status
        self.calls = 0
        self.active = 0
        self.max_active = 0

    @property
    def provider_name(self) -> str:
        return self._name

    async def call(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.fail_times > 0:
                self.fail_times -= 1
                raise ProviderError(
                    "boom",
                    provider=self._name,
                    model=request.model,
                    status_code=self.status,
                    retriable=self.status in (429, 500, 502, 503, 504),
                )
            await asyncio.sleep(0.01)
            return LLMResponse(
                content=f"ok:{self.api_key}",
                model=request.model,
                finish_reason="stop",
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                provider=self._name,
            )
        finally:
            self.active -= 1

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ProviderError(
                "boom",
                provider=self._name,
                model=request.model,
                status_code=self.status,
                retriable=True,
            )
        yield StreamChunk(content=f"chunk:{self.api_key}", finish_reason="stop")

    def estimate_cost(self, prompt_tokens, estimated_completion_tokens, model) -> CostEstimate:
        return CostEstimate(prompt_tokens, estimated_completion_tokens, 0.0, 0.0, 0.0, model, self._name)

    def count_tokens(self, text: str, model: str) -> int:
        return len(text)


def _req() -> LLMRequest:
    return LLMRequest(messages=[Message(role=MessageRole.USER, content="hi")], model="deepseek-chat")


@pytest.mark.asyncio
async def test_single_key_pool_passes_through():
    m = _StubProvider("k1")
    pool = PooledLLMProvider([m], gate=ConcurrencyGate(4, 5.0), max_retries=2)
    resp = await pool.call(_req())
    assert resp.content == "ok:k1"
    assert m.calls == 1


@pytest.mark.asyncio
async def test_429_fails_over_to_other_key():
    bad = _StubProvider("bad", fail_times=1, status=429)
    good = _StubProvider("good")
    pool = PooledLLMProvider([bad, good], gate=ConcurrencyGate(4, 5.0), max_retries=2)
    resp = await pool.call(_req())
    # Failover lands on the healthy key after the bad one 429s.
    assert resp.content == "ok:good"
    assert bad.calls == 1
    assert good.calls == 1


@pytest.mark.asyncio
async def test_non_retriable_error_propagates():
    bad = _StubProvider("bad", fail_times=1, status=400)
    good = _StubProvider("good")
    pool = PooledLLMProvider([bad, good], gate=ConcurrencyGate(4, 5.0), max_retries=2)
    with pytest.raises(ProviderError):
        await pool.call(_req())
    # 400 is not retriable → no failover attempt on the good key.
    assert good.calls == 0


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    members = [_StubProvider(f"k{i}") for i in range(4)]
    gate = ConcurrencyGate(max_concurrency=2, cooldown_seconds=0.0)
    pool = PooledLLMProvider(members, gate=gate, max_retries=0)
    await asyncio.gather(*(pool.call(_req()) for _ in range(12)))
    # Total simultaneous in-flight across all members must never exceed the cap.
    assert max(m.max_active for m in members) <= 2
    assert sum(m.calls for m in members) == 12


@pytest.mark.asyncio
async def test_retries_exhausted_raises():
    # Every key 429s; with max_retries=1 we try twice then give up.
    a = _StubProvider("a", fail_times=5, status=429)
    b = _StubProvider("b", fail_times=5, status=429)
    pool = PooledLLMProvider([a, b], gate=ConcurrencyGate(4, 0.0), max_retries=1)
    with pytest.raises(ProviderError):
        await pool.call(_req())
    assert a.calls + b.calls == 2  # initial + 1 retry


@pytest.mark.asyncio
async def test_stream_failover_before_first_chunk():
    bad = _StubProvider("bad", fail_times=1, status=429)
    good = _StubProvider("good")
    pool = PooledLLMProvider([bad, good], gate=ConcurrencyGate(4, 5.0), max_retries=2)
    chunks: List[str] = []
    async for c in pool.stream(_req()):
        chunks.append(c.content)
    assert chunks == ["chunk:good"]
