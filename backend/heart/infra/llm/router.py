"""Model Router - facade over ProviderRegistry.

Keeps the same public API (call_main, call_cheap, stream_main) so all
production callers need zero changes. Internally delegates to
infra/llm_providers/ProviderRegistry.
"""

from typing import AsyncGenerator, AsyncIterator, Optional

import structlog

from heart.infra.llm_providers.base import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    StreamChunk,
)
from heart.infra.llm_providers.registry import ProviderRegistry, get_registry, initialize_registry
from heart.observability.turn_profiler import TurnProfiler

logger = structlog.get_logger()

# Default model names (env-configurable via llm_providers/registry.py)
_DEFAULT_MAIN_MODEL = "deepseek-reasoner"
_DEFAULT_CHEAP_MODEL = "deepseek-chat"


class ModelRouter:
    """LLM facade — delegates to ProviderRegistry internally."""

    def __init__(self, registry: ProviderRegistry, main_model: str, cheap_model: str):
        self._registry = registry
        self._main_model = main_model
        self._cheap_model = cheap_model

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
        self._annotate_profiler(response)
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
        self._annotate_profiler(response)
        return response.content

    async def estimate_cost(self, model_tier: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a call (USD)."""
        model = self._main_model if model_tier == "main" else self._cheap_model
        provider = self._registry.get_provider_for_model(model)
        estimate = provider.estimate_cost(input_tokens, output_tokens, model)
        return estimate.total_cost_usd

    async def close(self):
        """Close all provider connections."""
        await self._registry.close_all()

    # ── helpers ───────────────────────────────────────────────────

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

    @staticmethod
    def _annotate_profiler(response: LLMResponse) -> None:
        p = TurnProfiler.current()
        if p.enabled and p.current_span_name() == "model_router":
            p.annotate(
                model_name=response.model,
                input_tokens=response.usage.get("prompt_tokens", 0),
                output_tokens=response.usage.get("completion_tokens", 0),
                cost_usd=0.0,  # cost tracked via provider estimate_cost if needed
            )


# ── Global lifecycle ──────────────────────────────────────────────

_global_router: Optional[ModelRouter] = None


async def get_model_router() -> ModelRouter:
    """Get global ModelRouter instance."""
    if _global_router is None:
        raise RuntimeError("ModelRouter not initialized. Call initialize_router() first.")
    return _global_router


async def initialize_router(config=None) -> None:
    """Initialize global ModelRouter from LLMProviderConfig or env defaults."""
    global _global_router
    registry = initialize_registry()
    if config is not None and hasattr(config, "get_main_model"):
        main_model = config.get_main_model().name
        cheap_model = config.get_cheap_model().name
    else:
        import os

        main_model = os.getenv("MAIN_LLM_MODEL", _DEFAULT_MAIN_MODEL)
        cheap_model = os.getenv("CHEAP_LLM_MODEL", _DEFAULT_CHEAP_MODEL)
    _global_router = ModelRouter(registry, main_model, cheap_model)
    logger.info(f"ModelRouter initialized: main={main_model}, cheap={cheap_model}")


async def shutdown_router():
    """Shutdown global ModelRouter."""
    global _global_router
    if _global_router:
        await _global_router.close()
        _global_router = None
