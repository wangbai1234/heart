"""ModelRouter — facade over ProviderRegistry.

Provides call_main(), call_cheap(), stream_main() convenience methods.
"""

from typing import AsyncGenerator, Optional

import structlog

from heart.infra.llm_providers.base import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    StreamChunk,
)
from heart.infra.llm_providers.registry import ProviderRegistry

logger = structlog.get_logger()


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
