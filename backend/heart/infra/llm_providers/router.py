"""ModelRouter — facade over ProviderRegistry.

Provides call_main(), call_cheap(), stream_main() for legacy callers, and
stream_for() / call_for() for multi-model failover.
"""

from typing import AsyncGenerator, Optional

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
        last_error: Optional[Exception] = None

        for candidate in chain:
            try:
                provider = self._registry.get_provider_for_model(candidate)
            except KeyError:
                logger.debug("call_for_no_provider", model=candidate)
                continue

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

        Failover only triggers on connection/status errors (ProviderError raised
        before any chunks are yielded). Mid-stream errors propagate as-is.
        """
        chain = self._get_failover_chain(model, failover or DEFAULT_FAILOVER)
        last_error: Optional[Exception] = None

        for i, candidate in enumerate(chain):
            try:
                provider = self._registry.get_provider_for_model(candidate)
            except KeyError:
                logger.debug("stream_for_no_provider", model=candidate)
                continue

            # candidate is a routing slug (e.g. "deepseek"); the vendor API needs
            # the canonical model name (e.g. "deepseek-chat"). served_model stays
            # the slug for billing/label purposes.
            api_model = self._registry.get_canonical_model(candidate)
            request = self._build_request(messages, api_model, temperature, max_tokens, stream=True)
            try:
                logger.info(
                    "stream_for_attempt",
                    agent_name=agent_name,
                    model=candidate,
                    requested=model,
                )
                first_chunk = True
                async for chunk in provider.stream(request):  # type: ignore[attr-defined]
                    if first_chunk:
                        # Record which model actually responded
                        if meta is not None:
                            meta["served_model"] = candidate
                            meta["degraded_to"] = candidate if i > 0 else None
                        first_chunk = False
                    if chunk.content:
                        yield chunk.content
                # Stream completed successfully
                if first_chunk:
                    # Empty response — still record served_model
                    if meta is not None:
                        meta["served_model"] = candidate
                        meta["degraded_to"] = candidate if i > 0 else None
                return
            except ProviderError as e:
                logger.warning(
                    "stream_for_failover",
                    from_model=candidate,
                    error=str(e),
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
