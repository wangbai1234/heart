"""ModelRouter — facade over ProviderRegistry.

Provides call_main(), call_cheap(), stream_main() for legacy callers, and
stream_for() / call_for() for multi-model failover.
"""

import asyncio
import time
from typing import AsyncGenerator, Optional, cast

import structlog

from heart.infra.llm_providers.base import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ProviderError,
    StreamChunk,
)
from heart.infra.llm_providers.registry import ProviderRegistry

logger = structlog.get_logger()

# Default failover chain: highest quality → cheapest (DeepSeek is free).
DEFAULT_FAILOVER = ["claude", "grok", "deepseek"]

# Time-to-first-token deadline for the streaming path. If a candidate model does
# not produce its first *content* byte within this window, we abort it and fail
# over to the next model in the chain. This is the "卡住的气泡" guard: a relay
# that accepts the connection but stalls on prefill (observed grok TTFT of 19.5s)
# would otherwise leave the user staring at an empty bubble until the 45s
# whole-turn timeout. 6s is chosen so a healthy HK→relay cold prefill (usually
# <6s) still succeeds, while a genuine stall degrades fast. Only applied before
# the first byte — once content flows we never interrupt a live stream.
TTFT_FAILOVER_S = 6.0


class ModelRouter:
    """LLM facade — delegates to ProviderRegistry internally.

    Legacy methods (call_main, stream_main, call_cheap) remain unchanged.
    New methods stream_for / call_for support per-request model selection
    with automatic failover.
    """

    def __init__(self, registry: ProviderRegistry, main_model: str, cheap_model: str):
        self._registry = registry
        self._main_model = main_model
        self._cheap_model = cheap_model

    # ------------------------------------------------------------------
    # Legacy helpers (unchanged)
    # ------------------------------------------------------------------

    async def call_main(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: str = "unknown",
    ) -> str:
        """Call main (high-quality) model. Returns content string."""
        logger.info(f"[{agent_name}] Calling main model: {self._main_model}")
        request = self._build_request(messages, self._main_model, temperature, max_tokens)
        provider = self._registry.get_provider_for_model(self._main_model)
        response = await provider.call(request)
        return response.content

    async def stream_main(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: str = "unknown",
    ) -> AsyncGenerator[str, None]:
        """Stream main model. Yields content strings."""
        logger.info(f"[{agent_name}] Streaming main model: {self._main_model}")
        request = self._build_request(
            messages, self._main_model, temperature, max_tokens, stream=True
        )
        provider = self._registry.get_provider_for_model(self._main_model)
        async for chunk in provider.stream(request):  # type: ignore[attr-defined]
            if chunk.content:
                yield chunk.content

    async def call_cheap(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        agent_name: str = "unknown",
    ) -> str:
        """Call cheap (fast/low-cost) model. Returns content string."""
        logger.info(f"[{agent_name}] Calling cheap model: {self._cheap_model}")
        request = self._build_request(
            messages, self._cheap_model, temperature, max_tokens, json_mode=json_mode
        )
        provider = self._registry.get_provider_for_model(self._cheap_model)
        response = await provider.call(request)
        return response.content

    # ------------------------------------------------------------------
    # Per-request model selection with failover
    # ------------------------------------------------------------------

    def _get_failover_chain(self, model: str, failover: list[str]) -> list[str]:
        """Return ordered list of models to try: [model] + filtered failover (no dups)."""
        seen = {model}
        chain = [model]
        for m in failover:
            if m not in seen:
                seen.add(m)
                chain.append(m)
        return chain

    async def call_for(
        self,
        model: str,
        messages: list[dict],
        failover: Optional[list[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: str = "unknown",
    ) -> tuple[str, str]:
        """Call the specified model with automatic failover.

        Returns (content, served_model) where served_model is the model that
        actually produced the response (may differ from requested model if failover occurred).
        """
        chain = self._get_failover_chain(model, failover or DEFAULT_FAILOVER)
        # Narrow to candidates with a registered provider so we know which
        # attempt is genuinely last (empty-response failover must not "continue"
        # past the final usable provider).
        usable = [c for c in chain if self._registry.has_model(c)]
        last_error: Optional[Exception] = None

        for i, candidate in enumerate(usable):
            provider = self._registry.get_provider_for_model(candidate)
            is_last = i == len(usable) - 1

            # candidate is a routing slug (e.g. "deepseek"); the vendor API needs
            # the canonical model name (e.g. "deepseek-chat"). served_model stays
            # the slug for billing/label purposes.
            api_model = self._registry.get_canonical_model(candidate)
            request = self._build_request(messages, api_model, temperature, max_tokens)
            try:
                logger.info(
                    "call_for_attempt",
                    agent_name=agent_name,
                    model=candidate,
                    requested=model,
                )
                response = await provider.call(request)
                # An error-free but empty response is useless to the user — treat
                # it as a soft failure and fail over to the next model (the
                # "deepseek 兜底"). Only the last usable candidate is allowed to
                # return empty, so the caller can surface a clean error.
                if not (response.content and response.content.strip()) and not is_last:
                    logger.warning(
                        "call_for_empty_failover",
                        from_model=candidate,
                        requested=model,
                    )
                    last_error = ProviderError(
                        f"empty response from {candidate}",
                        provider=candidate,
                        model=candidate,
                        retriable=True,
                    )
                    continue
                if candidate != model:
                    logger.info(
                        "call_for_degraded",
                        from_model=model,
                        to_model=candidate,
                        agent_name=agent_name,
                    )
                return response.content, candidate
            except ProviderError as e:
                logger.warning(
                    "call_for_failover",
                    from_model=candidate,
                    error=str(e),
                    retriable=e.retriable if hasattr(e, "retriable") else True,
                )
                last_error = e
                continue

        msg = f"All models in failover chain exhausted: {chain}"
        raise ProviderError(
            msg,
            provider="router",
            model=model,
            retriable=False,
        ) from last_error

    @staticmethod
    async def _anext_with_ttft(
        agen: "AsyncGenerator[StreamChunk, None]", *, budget_s: Optional[float]
    ) -> StreamChunk:
        """Await the next chunk.

        ``budget_s`` bounds the wait for the *first* content byte (TTFT guard): a
        non-positive budget or a slow first token raises ``asyncio.TimeoutError``
        so the caller can fail over. Once content is flowing the caller passes
        ``None`` → we wait unbounded and never interrupt a live stream.
        """
        if budget_s is None:
            return await agen.__anext__()
        if budget_s <= 0:
            raise asyncio.TimeoutError()
        return await asyncio.wait_for(agen.__anext__(), timeout=budget_s)

    async def _stream_candidate(
        self,
        provider,
        request: LLMRequest,
        *,
        candidate: str,
        requested: str,
        agent_name: str,
        attempt_idx: int,
        t_start: float,
        meta: Optional[dict],
    ) -> AsyncGenerator[str, None]:
        """Drive one provider's stream with a first-token watchdog.

        Yields content strings. Completing without yielding = an empty response
        (the caller decides whether to fail over). Raises ``asyncio.TimeoutError``
        if the first content byte exceeds ``TTFT_FAILOVER_S``, or ``ProviderError``
        on a provider failure. Sets ``meta`` on the first content chunk. Always
        closes the upstream connection in ``finally``.
        """
        # `t_candidate` resets per attempt so each model gets its own fresh TTFT
        # budget. Cast: the abstract `stream` is declared `async def -> Iterator`
        # but every concrete provider is an async *generator*, so the runtime
        # object has __anext__/aclose.
        t_candidate = time.perf_counter()
        yielded_content = False
        agen = cast("AsyncGenerator[StreamChunk, None]", provider.stream(request))
        try:
            while True:
                budget = (
                    None
                    if yielded_content
                    else TTFT_FAILOVER_S - (time.perf_counter() - t_candidate)
                )
                try:
                    chunk = await self._anext_with_ttft(agen, budget_s=budget)
                except StopAsyncIteration:
                    break
                if not chunk.content:
                    continue
                if not yielded_content:
                    # Lock in served_model on the first *content* chunk (not the
                    # first raw frame) so a stream that emits only a finish-reason
                    # frame still counts as empty and can fail over.
                    yielded_content = True
                    ttft_ms = round((time.perf_counter() - t_start) * 1000.0, 1)
                    if meta is not None:
                        meta["served_model"] = candidate
                        meta["degraded_to"] = candidate if attempt_idx > 0 else None
                        meta["ttft_ms"] = ttft_ms
                    logger.info(
                        "stream_ttft",
                        agent_name=agent_name,
                        model=candidate,
                        requested=requested,
                        attempt=attempt_idx + 1,
                        ttft_ms=ttft_ms,
                    )
                yield chunk.content
        finally:
            # Release the upstream connection whether we exhausted, failed over,
            # or aborted on timeout. aclose() throws GeneratorExit into the
            # provider's `async with client.stream(...)`, closing the HTTP
            # response cleanly. Best-effort: a cancelled __anext__ can leave the
            # generator in a state where aclose() itself errors, and that must not
            # mask the real failover/return path.
            try:
                await agen.aclose()
            except Exception:
                logger.debug("stream_for_aclose_failed", from_model=candidate)

    async def stream_for(
        self,
        model: str,
        messages: list[dict],
        failover: Optional[list[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: str = "unknown",
        meta: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from the specified model with automatic failover.

        Yields content strings. When ``meta`` dict is provided, sets:
          meta["served_model"] = actual model that produced the response
          meta["degraded_to"]  = served_model if failover occurred, else None

        Failover triggers on (a) connection/status errors (ProviderError raised
        before any chunk is yielded), (b) an error-free stream that produces no
        content — an empty response is useless, so we fall through to the next
        model (the "deepseek 兜底") — and (c) a stalled prefill that misses the
        TTFT_FAILOVER_S first-token deadline. Once real content has been yielded,
        a mid-stream error propagates as-is (we cannot un-send bytes).
        """
        chain = self._get_failover_chain(model, failover or DEFAULT_FAILOVER)
        # Narrow to candidates with a registered provider so we know which
        # attempt is genuinely last (empty-response failover must not "continue"
        # past the final usable provider).
        usable = [c for c in chain if self._registry.has_model(c)]
        last_error: Optional[Exception] = None

        # Measured from the router call to the first *content* byte reaching the
        # caller — i.e. the user-facing TTFT, spanning any failover hops. This is
        # the number to watch when diagnosing "转很久才出字": network to the
        # upstream/relay + model prefill, isolated from token throughput.
        t_start = time.perf_counter()

        for i, candidate in enumerate(usable):
            provider = self._registry.get_provider_for_model(candidate)
            is_last = i == len(usable) - 1
            # candidate is a routing slug (e.g. "deepseek"); the vendor API needs
            # the canonical model name (e.g. "deepseek-chat"). served_model stays
            # the slug for billing/label purposes.
            api_model = self._registry.get_canonical_model(candidate)
            request = self._build_request(messages, api_model, temperature, max_tokens, stream=True)
            logger.info(
                "stream_for_attempt", agent_name=agent_name, model=candidate, requested=model
            )

            got_content = False
            try:
                async for content in self._stream_candidate(
                    provider,
                    request,
                    candidate=candidate,
                    requested=model,
                    agent_name=agent_name,
                    attempt_idx=i,
                    t_start=t_start,
                    meta=meta,
                ):
                    got_content = True
                    yield content
                if got_content:
                    return
                # Stream finished without any content.
                if not is_last:
                    logger.warning(
                        "stream_for_empty_failover", from_model=candidate, requested=model
                    )
                    last_error = ProviderError(
                        f"empty response from {candidate}",
                        provider=candidate,
                        model=candidate,
                        retriable=True,
                    )
                    continue
                # Last usable candidate also empty — record it and return so the
                # caller surfaces the graceful "生成失败，请重试" path.
                if meta is not None:
                    meta["served_model"] = candidate
                    meta["degraded_to"] = candidate if i > 0 else None
                return
            except asyncio.TimeoutError:
                # First token missed TTFT_FAILOVER_S. Only reachable before any
                # content was yielded, so failing over is safe.
                logger.warning(
                    "stream_for_ttft_timeout",
                    from_model=candidate,
                    requested=model,
                    ttft_budget_s=TTFT_FAILOVER_S,
                )
                last_error = ProviderError(
                    f"first-token timeout (>{TTFT_FAILOVER_S}s) from {candidate}",
                    provider=candidate,
                    model=candidate,
                    retriable=True,
                )
                continue
            except ProviderError as e:
                if got_content:
                    # Bytes are already on the wire to the client — re-streaming a
                    # second model would concatenate a whole new answer onto the
                    # partial one (garbled output). We cannot un-send, so surface
                    # the mid-stream failure instead of failing over.
                    logger.warning(
                        "stream_for_midstream_error",
                        from_model=candidate,
                        requested=model,
                        error=str(e),
                    )
                    raise
                logger.warning("stream_for_failover", from_model=candidate, error=str(e))
                last_error = e
                continue

        msg = f"All models in failover chain exhausted: {chain}"
        raise ProviderError(
            msg,
            provider="router",
            model=model,
            retriable=False,
        ) from last_error

    async def close(self):
        """Close all provider connections."""
        await self._registry.close_all()

    @staticmethod
    def _build_request(
        messages: list[dict],
        model: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        json_mode: bool = False,
        stream: bool = False,
    ) -> LLMRequest:
        typed_messages = [
            Message(role=MessageRole(m["role"]), content=m["content"]) for m in messages
        ]
        return LLMRequest(
            messages=typed_messages,
            model=model,
            temperature=temperature or 0.7,
            max_tokens=max_tokens,
            json_mode=json_mode,
            stream=stream,
        )
