"""LLM infrastructure module — re-exports from infra/llm_providers/.

All actual implementation lives in infra/llm_providers/.
This package exists for backward compatibility of import paths.
"""

from heart.infra.llm_providers import (
    ModelRouter,
    get_model_router,
    get_registry,
    initialize_registry,
)

__all__ = [
    "ModelRouter",
    "get_model_router",
    "get_registry",
    "initialize_registry",
]


async def initialize_router(config=None) -> None:
    """Initialize global LLM router. Delegates to ProviderRegistry."""
    initialize_registry()


async def shutdown_router() -> None:
    """Shutdown global LLM router. No-op (providers clean up on GC)."""
    pass
