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
from heart.infra.llm_providers.router import (
    DEFAULT_BACKGROUND_ATTEMPT_TIMEOUT_S,
    DEFAULT_BACKGROUND_FAILOVER,
    DEFAULT_BACKGROUND_MODEL,
    ModelRouter,
)

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
    background_model = os.getenv("BACKGROUND_LLM_MODEL", DEFAULT_BACKGROUND_MODEL)
    background_failover = [
        model.strip()
        for model in os.getenv(
            "BACKGROUND_LLM_FAILOVER", ",".join(DEFAULT_BACKGROUND_FAILOVER)
        ).split(",")
        if model.strip()
    ]
    try:
        background_attempt_timeout_s = float(
            os.getenv(
                "BACKGROUND_LLM_ATTEMPT_TIMEOUT_SECONDS",
                str(DEFAULT_BACKGROUND_ATTEMPT_TIMEOUT_S),
            )
        )
    except ValueError:
        background_attempt_timeout_s = DEFAULT_BACKGROUND_ATTEMPT_TIMEOUT_S
    return ModelRouter(
        registry,
        main_model,
        cheap_model,
        background_model=background_model,
        background_failover=background_failover,
        background_attempt_timeout_s=background_attempt_timeout_s,
    )
