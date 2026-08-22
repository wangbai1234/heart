"""ModelRouter — facade over ProviderRegistry.

Provides call_main(), call_cheap(), stream_main() for legacy callers,
call_background() for internal tasks, and stream_for() / call_for() for
explicit per-model routing with failover.
"""

import asyncio
import json
import re
import time
from typing import AsyncGenerator, Optional, cast

import structlog

from heart.infra.llm_providers.base import (
    CostEstimate,
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ProviderError,
    StreamChunk,
)
from heart.infra.llm_providers.registry import ProviderRegistry
from heart.infra.model_catalog import get_model_spec
from heart.infra.model_health import record_model_result

logger = structlog.get_logger()

# Legacy fallback for unknown model slugs. Catalog models define their own chain.
DEFAULT_FAILOVER = ["grok", "deepseek"]
DEFAULT_BACKGROUND_MODEL = "background-gpt-5.6-luna"
DEFAULT_BACKGROUND_FAILOVER = [
    "background-gpt-5.4-mini",
    "background-gemini-2.5-flash-lite",
    "background-gemini-3.1-flash-lite-preview",
    "background-claude-haiku-4.5",
]

# Time-to-first-token deadline for the streaming path. If a candidate model does
# not produce its first *content* byte within this window, we abort it and fail
# over to the next model in the chain. This is the "卡住的气泡" guard: a relay
# that accepts the connection but stalls on prefill (observed grok TTFT of 19.5s)
# would otherwise leave the user staring at an empty bubble until the 45s
# whole-turn timeout. 6s is chosen so a healthy HK→relay cold prefill (usually
# <6s) still succeeds, while a genuine stall degrades fast. Only applied before
# the first byte — once content flows we never interrupt a live stream.
TTFT_FAILOVER_S = 6.0

_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
    re.IGNORECASE | re.DOTALL,
)


class ModelRouter:
    """LLM facade — delegates to ProviderRegistry internally.

    Legacy methods (call_main, stream_main, call_cheap) remain unchanged.
    call_background uses an independent low-cost model chain for internal
    tasks. stream_for / call_for support explicit per-request model selection.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        main_model: str,
        cheap_model: str,
        background_model: str = DEFAULT_BACKGROUND_MODEL,
        background_failover: Optional[list[str]] = None,
    ):
        self._registry = registry
        self._main_model = main_model
        self._cheap_model = cheap_model
        self._background_model = background_model
        self._background_failover = (
            list(background_failover)
            if background_failover is not None
            else list(DEFAULT_BACKGROUND_FAILOVER)
        )

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

    async def call_background(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        agent_name: str = "unknown",
        meta: Optional[dict] = None,
    ) -> str:
        """Call the independent low-cost chain used by internal tasks."""
        content, _served_model = await self.call_for(
            self._background_model,
            messages,
            failover=self._background_failover,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            agent_name=agent_name,
            meta=meta,
        )
        return content

    def estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> CostEstimate:
        """Estimate cost using the provider that served a routed response."""
        provider = self._registry.get_provider_for_model(model)
        api_model = self._registry.get_canonical_model(model)
        return provider.estimate_cost(prompt_tokens, completion_tokens, api_model)

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

    @staticmethod
    def _normalize_json_content(content: str, model: str) -> str:
        """Return parseable JSON, unwrapping a standard Markdown fence.

        Some native providers ignore ``response_format`` and wrap otherwise
        valid JSON in a Markdown code fence. Structured background callers expect
        raw JSON, so normalize that provider-level formatting here. A response
        that is still not valid JSON is a routing failure and must reach the
        next model in the configured chain.
        """
        stripped = content.strip()
        candidates = [stripped]
        fence_match = _JSON_FENCE_RE.fullmatch(stripped)
        if fence_match:
            candidates.append(fence_match.group(1).strip())

        for candidate in candidates:
            try:
                json.loads(candidate)
            except (json.JSONDecodeError, TypeError):
                continue
            if candidate != stripped:
                logger.info("call_for_json_fence_normalized", model=model)
            return candidate

        raise ProviderError(
            f"invalid JSON response from {model}",
            provider=model,
            model=model,
            retriable=True,
        )

    async def call_for(
        self,
        model: str,
        messages: list[dict],
        failover: Optional[list[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        agent_name: str = "unknown",
        meta: Optional[dict] = None,
    ) -> tuple[str, str]:
        """Call the specified model with automatic failover.

        Returns (content, served_model) where served_model is the model that
        actually produced the response (may differ from requested model if failover occurred).
        When ``meta`` is provided, it also receives ``served_model``,
        ``degraded_to``, and the provider's token ``usage``.
        """
        spec = get_model_spec(model)
        fallback = list(spec.failover) if spec else DEFAULT_FAILOVER
        chain = self._get_failover_chain(model, failover if failover is not None else fallback)
        # Narrow to candidates with a registered provider so we know which
        # attempt is genuinely last (empty-response failover must not "continue"
        # past the final usable provider).
        usable = [c for c in chain if self._registry.has_model(c)]
        last_error: Optional[Exception] = None

        for i, candidate in enumerate(usable):
            provider = self._registry.get_provider_for_model(candidate)
            is_last = i == len(usable) - 1
            candidate_started = time.perf_counter()

            # candidate is a routing slug (e.g. "deepseek"); the vendor API needs
            # the canonical model name (e.g. "deepseek-chat"). served_model stays
            # the slug for billing/label purposes.
            api_model = self._registry.get_canonical_model(candidate)
            request = self._build_request(
                messages,
                api_model,
                temperature,
                max_tokens,
                json_mode=json_mode,
            )
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
                content = response.content
                if json_mode:
                    content = self._normalize_json_content(content, candidate)
                if candidate != model:
                    logger.info(
                        "call_for_degraded",
                        from_model=model,
                        to_model=candidate,
                        agent_name=agent_name,
                    )
                duration_ms = (time.perf_counter() - candidate_started) * 1000
                record_model_result(candidate, success=True, duration_ms=duration_ms)
                if meta is not None:
                    meta["served_model"] = candidate
                    meta["degraded_to"] = candidate if candidate != model else None
                    meta["usage"] = dict(response.usage)
                return content, candidate
            except Exception as e:
                record_model_result(
                    candidate,
                    success=False,
                    duration_ms=(time.perf_counter() - candidate_started) * 1000,
                )
                logger.warning(
                    "call_for_failover",
                    from_model=candidate,
                    error=str(e),
                    retriable=getattr(e, "retriable", True),
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
        saw_finish = False
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
                except Exception:
                    # A relay/transport error AFTER the model already signalled
                    # completion (finish_reason chunk) is teardown noise on a
                    # WHOLE reply — some relays (micu) close the SSE stream with a
                    # spurious error frame once the answer is done. The content is
                    # complete, so end cleanly instead of re-raising, which would
                    # otherwise make the WS route show a bogus STREAM_INTERRUPTED
                    # "宇宙偏离轨道" toast on a perfectly good reply. A genuine
                    # mid-reply drop (no finish_reason yet) still re-raises below.
                    if saw_finish:
                        logger.debug(
                            "stream_post_finish_error", from_model=candidate, requested=requested
                        )
                        break
                    raise
                if chunk.finish_reason:
                    saw_finish = True
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

    def _failover_error_or_raise(
        self, exc: Exception, *, got_content: bool, candidate: str, requested: str
    ) -> Exception:
        """Classify an exception raised while streaming a candidate.

        Returns the error to record as ``last_error`` and continue the failover
        loop, or re-raises when the failure happened mid-stream (content already
        on the wire) and cannot be recovered.

        Covers three cases collapsed into one caller ``except``:
          - ``asyncio.TimeoutError``: first token missed ``TTFT_FAILOVER_S``.
            Only reachable before any content, so always safe to fail over.
          - ``ProviderError``: a provider-wrapped connection/status failure.
          - any other ``Exception``: a raw relay/transport/parse error that the
            provider did not wrap (the claude "生成失败无兜底" report — such an
            error must not skip grok→deepseek). ``asyncio.CancelledError`` is a
            ``BaseException`` and never reaches here, so turn cancellation is
            preserved.
        """
        if isinstance(exc, asyncio.TimeoutError):
            logger.warning(
                "stream_for_ttft_timeout",
                from_model=candidate,
                requested=requested,
                ttft_budget_s=TTFT_FAILOVER_S,
            )
            return ProviderError(
                f"first-token timeout (>{TTFT_FAILOVER_S}s) from {candidate}",
                provider=candidate,
                model=candidate,
                retriable=True,
            )
        if got_content:
            # Bytes are already on the wire to the client — re-streaming a second
            # model would concatenate a whole new answer onto the partial one
            # (garbled output). We cannot un-send, so surface the failure.
            logger.warning(
                "stream_for_midstream_error",
                from_model=candidate,
                requested=requested,
                error=str(exc),
                provider_error=isinstance(exc, ProviderError),
            )
            raise exc
        logger.warning(
            "stream_for_failover",
            from_model=candidate,
            requested=requested,
            error=str(exc),
            provider_error=isinstance(exc, ProviderError),
        )
        return exc

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
        spec = get_model_spec(model)
        fallback = list(spec.failover) if spec else DEFAULT_FAILOVER
        chain = self._get_failover_chain(model, failover if failover is not None else fallback)
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
            candidate_started = time.perf_counter()
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
                    record_model_result(
                        candidate,
                        success=True,
                        duration_ms=(time.perf_counter() - candidate_started) * 1000,
                        ttft_ms=(meta or {}).get("ttft_ms"),
                    )
                    return
                # Stream finished without any content.
                if not is_last:
                    record_model_result(
                        candidate,
                        success=False,
                        duration_ms=(time.perf_counter() - candidate_started) * 1000,
                    )
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
                record_model_result(
                    candidate,
                    success=False,
                    duration_ms=(time.perf_counter() - candidate_started) * 1000,
                )
                return
            except Exception as exc:
                record_model_result(
                    candidate,
                    success=False,
                    duration_ms=(time.perf_counter() - candidate_started) * 1000,
                )
                # One handler for TTFT timeout, ProviderError, and any raw
                # (unwrapped) relay/transport error. _failover_error_or_raise
                # decides: record-and-continue before the first byte, re-raise
                # mid-stream. CancelledError is a BaseException → not caught here.
                last_error = self._failover_error_or_raise(
                    exc, got_content=got_content, candidate=candidate, requested=model
                )
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
