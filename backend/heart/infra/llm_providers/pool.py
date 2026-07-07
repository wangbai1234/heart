"""
Pooled LLM provider — outbound concurrency limiting + multi-key rotation + 429 failover.

Wraps N underlying single-key providers (one per API key) behind the LLMProvider
interface. Provides three things the bare providers lack:

1. A process-global concurrency cap (asyncio.Semaphore) so bursts queue instead of
   stampeding the upstream API (which returns 429/503 under load).
2. Least-in-flight key selection across a pool of 1..N keys, so load spreads and a
   cooling key is routed around.
3. 429/5xx failover: a retriable error puts the offending key on a short cooldown and
   retries on another key.

Design notes / honest limits:
- Single key = pool of one → behaves like the bare provider PLUS the limiter + retry.
- The semaphore + per-key state is a *shared* ConcurrencyGate, so main (reasoner) and
  cheap (chat) pools count against ONE budget — matching the fact that the vendor
  concurrency limit is per-account, spanning models.
- Streaming can only fail over BEFORE the first chunk is yielded. Once tokens have been
  emitted to the caller, a mid-stream failure propagates (no silent restart).
- The semaphore is per-process. With multiple app workers/replicas, set
  llm_max_concurrency = total_target / replica_count.

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

import structlog

from heart.infra.llm_providers.base import (
    CostEstimate,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    StreamChunk,
)

logger = structlog.get_logger()


class _KeyState:
    """Per-key runtime state (in-flight count + cooldown deadline)."""

    __slots__ = ("in_flight", "cooldown_until")

    def __init__(self) -> None:
        self.in_flight: int = 0
        self.cooldown_until: float = 0.0


class ConcurrencyGate:
    """
    Shared outbound concurrency limiter + key-cooldown bookkeeping.

    A single gate instance is shared across all pools that talk to the same vendor
    account, so the semaphore caps *total* outbound concurrency and cooldowns are
    tracked per API key regardless of which model pool used the key.
    """

    def __init__(self, max_concurrency: int, cooldown_seconds: float) -> None:
        # Guard against a zero/negative cap disabling all traffic.
        self._sem = asyncio.Semaphore(max(1, max_concurrency))
        self._cooldown_seconds = max(0.0, cooldown_seconds)
        self._states: dict[str, _KeyState] = {}

    def _state(self, key: str) -> _KeyState:
        st = self._states.get(key)
        if st is None:
            st = _KeyState()
            self._states[key] = st
        return st

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        await self._sem.acquire()
        try:
            yield
        finally:
            self._sem.release()

    def pick(self, members: List[LLMProvider]) -> LLMProvider:
        """Pick the least-in-flight member whose key is not cooling.

        Falls back to the member whose cooldown expires soonest if every key is
        currently cooling — better to try (and possibly 429 again) than to fail hard.
        """
        now = time.monotonic()
        available = [m for m in members if self._state(m.api_key).cooldown_until <= now]
        pool = available if available else members
        return min(
            pool,
            key=lambda m: (self._state(m.api_key).in_flight, self._state(m.api_key).cooldown_until),
        )

    def mark_start(self, key: str) -> None:
        self._state(key).in_flight += 1

    def mark_end(self, key: str) -> None:
        st = self._state(key)
        st.in_flight = max(0, st.in_flight - 1)

    def mark_cooldown(self, key: str) -> None:
        if self._cooldown_seconds > 0:
            self._state(key).cooldown_until = time.monotonic() + self._cooldown_seconds


def _redact(key: str) -> str:
    """Short, non-sensitive key fingerprint for logs (never log the full key)."""
    return f"…{key[-4:]}" if key and len(key) >= 4 else "…"


class PooledLLMProvider(LLMProvider):
    """LLMProvider that dispatches across a pool of single-key providers."""

    def __init__(
        self,
        members: List[LLMProvider],
        gate: ConcurrencyGate,
        max_retries: int = 2,
    ) -> None:
        if not members:
            raise ValueError("PooledLLMProvider requires at least one member provider")
        # api_key/base_url are inherited but unused directly; delegate to first member.
        super().__init__(api_key=members[0].api_key, base_url=members[0].base_url)
        self._members = members
        self._gate = gate
        self._max_retries = max(0, max_retries)

    @property
    def provider_name(self) -> str:
        return self._members[0].provider_name

    async def call(self, request: LLMRequest) -> LLMResponse:
        last_err: Optional[ProviderError] = None
        async with self._gate.slot():
            for attempt in range(self._max_retries + 1):
                member = self._gate.pick(self._members)
                self._gate.mark_start(member.api_key)
                try:
                    return await member.call(request)
                except ProviderError as e:
                    last_err = e
                    if not e.retriable or attempt >= self._max_retries:
                        raise
                    self._gate.mark_cooldown(member.api_key)
                    logger.warning(
                        "llm_pool_failover",
                        provider=member.provider_name,
                        key=_redact(member.api_key),
                        status_code=e.status_code,
                        attempt=attempt + 1,
                    )
                finally:
                    self._gate.mark_end(member.api_key)
        # Unreachable in practice (loop either returns or raises), but satisfies typing.
        assert last_err is not None
        raise last_err

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        last_err: Optional[ProviderError] = None
        async with self._gate.slot():
            for attempt in range(self._max_retries + 1):
                member = self._gate.pick(self._members)
                self._gate.mark_start(member.api_key)
                started = False
                try:
                    async for chunk in member.stream(request):  # type: ignore[attr-defined]
                        started = True
                        yield chunk
                    return
                except ProviderError as e:
                    last_err = e
                    # Cannot fail over once tokens have reached the caller.
                    if started or not e.retriable or attempt >= self._max_retries:
                        raise
                    self._gate.mark_cooldown(member.api_key)
                    logger.warning(
                        "llm_pool_stream_failover",
                        provider=member.provider_name,
                        key=_redact(member.api_key),
                        status_code=e.status_code,
                        attempt=attempt + 1,
                    )
                finally:
                    self._gate.mark_end(member.api_key)
            if last_err is not None:
                raise last_err

    def estimate_cost(
        self,
        prompt_tokens: int,
        estimated_completion_tokens: int,
        model: str,
    ) -> CostEstimate:
        return self._members[0].estimate_cost(prompt_tokens, estimated_completion_tokens, model)

    def count_tokens(self, text: str, model: str) -> int:
        return self._members[0].count_tokens(text, model)

    async def close(self) -> None:
        for member in self._members:
            if hasattr(member, "close"):
                await member.close()
