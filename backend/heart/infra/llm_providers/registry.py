"""
Provider registry for managing and looking up LLM providers.

Supports:
- Provider registration
- Model-to-provider mapping
- Provider initialization
- Failover configuration
"""

import os
from typing import Dict, Optional, Type

from heart.infra.llm_providers.base import CircuitBreakerInterface, LLMProvider
from heart.infra.llm_providers.claude import ClaudeProvider
from heart.infra.llm_providers.deepseek import DeepSeekV4FlashProvider
from heart.infra.llm_providers.deepseek_pro import DeepSeekV4ProProvider
from heart.infra.llm_providers.grok import GrokProvider
from heart.infra.llm_providers.pool import ConcurrencyGate, PooledLLMProvider


def _parse_keys(primary: Optional[str], extra: Optional[str]) -> list[str]:
    """Merge a primary key with an optional comma-separated extra list, de-duped."""
    keys: list[str] = []
    if primary:
        keys.append(primary.strip())
    if extra:
        keys.extend(k.strip() for k in extra.split(",") if k.strip())
    # Preserve order, drop duplicates and empties.
    seen: set[str] = set()
    result: list[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            result.append(k)
    return result


class ProviderRegistry:
    """
    Registry for LLM providers.

    Manages provider instances and model routing.
    """

    def __init__(self, circuit_breaker: Optional[CircuitBreakerInterface] = None):
        """
        Initialize provider registry.

        Args:
            circuit_breaker: Optional circuit breaker for all providers
        """
        self.circuit_breaker = circuit_breaker
        self._providers: Dict[str, LLMProvider] = {}
        self._model_to_provider: Dict[str, str] = {}

    def register_provider(
        self,
        provider_name: str,
        provider_class: Type[LLMProvider],
        api_key: str,
        base_url: Optional[str] = None,
        models: Optional[list[str]] = None,
    ) -> None:
        """
        Register a provider.

        Args:
            provider_name: Unique provider name
            provider_class: Provider class to instantiate
            api_key: API key for provider
            base_url: Optional custom base URL
            models: List of models this provider handles
        """
        provider = provider_class(
            api_key=api_key,
            base_url=base_url,
            circuit_breaker=self.circuit_breaker,
        )
        self._providers[provider_name] = provider

        # Register model mappings
        if models:
            for model in models:
                self._model_to_provider[model] = provider_name

    def register_provider_instance(
        self,
        provider_name: str,
        provider: LLMProvider,
        models: Optional[list[str]] = None,
    ) -> None:
        """Register a pre-built provider instance (e.g. a PooledLLMProvider)."""
        self._providers[provider_name] = provider
        if models:
            for model in models:
                self._model_to_provider[model] = provider_name

    def get_provider(self, provider_name: str) -> LLMProvider:
        """
        Get provider by name.

        Args:
            provider_name: Provider name

        Returns:
            Provider instance

        Raises:
            KeyError: If provider not found
        """
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' not registered")
        return self._providers[provider_name]

    def get_provider_for_model(self, model: str) -> LLMProvider:
        """
        Get provider for a specific model.

        Args:
            model: Model name

        Returns:
            Provider instance that handles this model

        Raises:
            KeyError: If no provider registered for model
        """
        if model not in self._model_to_provider:
            raise KeyError(f"No provider registered for model '{model}'")

        provider_name = self._model_to_provider[model]
        return self.get_provider(provider_name)

    async def close_all(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()


# Global registry instance
_global_registry: Optional[ProviderRegistry] = None


def initialize_registry(
    circuit_breaker: Optional[CircuitBreakerInterface] = None,
) -> ProviderRegistry:
    """
    Initialize global provider registry with environment configuration.

    Reads from environment variables:
    - DEEPSEEK_API_KEY
    - DEEPSEEK_BASE_URL (optional)
    - MAIN_LLM_MODEL (default: deepseek-reasoner)
    - CHEAP_LLM_MODEL (default: deepseek-chat)

    Args:
        circuit_breaker: Optional circuit breaker

    Returns:
        Initialized registry
    """
    global _global_registry

    registry = ProviderRegistry(circuit_breaker=circuit_breaker)

    # Get configuration from environment
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    deepseek_api_keys = os.getenv("DEEPSEEK_API_KEYS")  # optional comma-separated extras
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")
    main_model = os.getenv("MAIN_LLM_MODEL", "deepseek-chat")
    cheap_model = os.getenv("CHEAP_LLM_MODEL", "deepseek-chat")

    keys = _parse_keys(deepseek_api_key, deepseek_api_keys)
    if not keys:
        raise ValueError(
            "DEEPSEEK_API_KEY environment variable not set. Please check your .env file."
        )

    # Shared gate: one semaphore + per-key cooldown across BOTH model pools, because the
    # vendor concurrency limit is per-account (per-key), spanning models.
    try:
        max_concurrency = int(os.getenv("LLM_MAX_CONCURRENCY", "8"))
    except ValueError:
        max_concurrency = 8
    try:
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
    except ValueError:
        max_retries = 2
    try:
        cooldown = float(os.getenv("LLM_KEY_COOLDOWN_SECONDS", "15"))
    except ValueError:
        cooldown = 15.0
    gate = ConcurrencyGate(max_concurrency=max_concurrency, cooldown_seconds=cooldown)

    # DeepSeek V4-pro (main model) — one underlying provider per key, wrapped in a pool.
    pro_members: list[LLMProvider] = [
        DeepSeekV4ProProvider(
            api_key=k, base_url=deepseek_base_url, circuit_breaker=circuit_breaker
        )
        for k in keys
    ]
    registry.register_provider_instance(
        provider_name="deepseek-v4-pro",
        provider=PooledLLMProvider(pro_members, gate=gate, max_retries=max_retries),
        models=[main_model, "deepseek-reasoner"],
    )

    # DeepSeek V4-flash (cheap model)
    flash_members: list[LLMProvider] = [
        DeepSeekV4FlashProvider(
            api_key=k, base_url=deepseek_base_url, circuit_breaker=circuit_breaker
        )
        for k in keys
    ]
    registry.register_provider_instance(
        provider_name="deepseek-v4-flash",
        provider=PooledLLMProvider(flash_members, gate=gate, max_retries=max_retries),
        models=[cheap_model, "deepseek-chat"],
    )

    # Grok (xAI) — optional; registered only when GROK_API_KEY is configured
    grok_api_key = os.getenv("GROK_API_KEY")
    grok_base_url = os.getenv("GROK_BASE_URL")
    grok_model = os.getenv("GROK_MODEL", "grok-3-mini-fast")
    if grok_api_key:
        registry.register_provider_instance(
            provider_name="grok",
            provider=GrokProvider(
                api_key=grok_api_key,
                base_url=grok_base_url,
                circuit_breaker=circuit_breaker,
            ),
            models=[grok_model, "grok"],
        )

    # Claude (Anthropic) — optional; registered only when CLAUDE_API_KEY is configured
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    claude_base_url = os.getenv("CLAUDE_BASE_URL")
    claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
    claude_api_style = os.getenv("CLAUDE_API_STYLE", "anthropic")
    if claude_api_key:
        registry.register_provider_instance(
            provider_name="claude",
            provider=ClaudeProvider(
                api_key=claude_api_key,
                base_url=claude_base_url,
                circuit_breaker=circuit_breaker,
                api_style=claude_api_style,
            ),
            models=[claude_model, "claude"],
        )

    _global_registry = registry
    return registry


def get_registry() -> ProviderRegistry:
    """
    Get global provider registry.

    Returns:
        Global registry instance

    Raises:
        RuntimeError: If registry not initialized
    """
    if _global_registry is None:
        raise RuntimeError("Provider registry not initialized. Call initialize_registry() first.")
    return _global_registry


def get_provider(provider_name: str) -> LLMProvider:
    """
    Get provider from global registry.

    Args:
        provider_name: Provider name

    Returns:
        Provider instance
    """
    return get_registry().get_provider(provider_name)


def get_provider_for_model(model: str) -> LLMProvider:
    """
    Get provider for model from global registry.

    Args:
        model: Model name

    Returns:
        Provider instance
    """
    return get_registry().get_provider_for_model(model)
