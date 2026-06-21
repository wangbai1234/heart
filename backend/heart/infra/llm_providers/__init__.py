"""
LLM Provider abstraction layer.

Supports multiple LLM providers with unified interface for:
- Streaming and non-streaming calls
- Cost estimation
- Circuit breaker integration
- Provider registry and failover
"""

from heart.infra.llm_providers.base import (
    CostEstimate,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    MessageRole,
    StreamChunk,
)
from heart.infra.llm_providers.registry import (
    ProviderRegistry,
    get_provider,
    get_registry,
    initialize_registry,
)
from heart.infra.llm_providers.router import ModelRouter

__all__ = [
    "CostEstimate",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "MessageRole",
    "ModelRouter",
    "ProviderRegistry",
    "StreamChunk",
    "get_provider",
    "get_registry",
    "initialize_registry",
]


async def get_model_router() -> ModelRouter:
    """Get ModelRouter from global registry. Raises RuntimeError if not initialized."""
    registry = get_registry()
    import os

    main_model = os.getenv("MAIN_LLM_MODEL", "deepseek-reasoner")
    cheap_model = os.getenv("CHEAP_LLM_MODEL", "deepseek-chat")
    return ModelRouter(registry, main_model, cheap_model)
