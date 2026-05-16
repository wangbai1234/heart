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
from heart.infra.llm_providers.base import LLMProvider, CircuitBreakerInterface
from heart.infra.llm_providers.anthropic import DeepSeekV4ProProvider
from heart.infra.llm_providers.deepseek import DeepSeekV4FlashProvider


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
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")
    main_model = os.getenv("MAIN_LLM_MODEL", "deepseek-reasoner")
    cheap_model = os.getenv("CHEAP_LLM_MODEL", "deepseek-chat")

    if not deepseek_api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY environment variable not set. "
            "Please check your .env file."
        )

    # Register DeepSeek V4-pro (main model)
    registry.register_provider(
        provider_name="deepseek-v4-pro",
        provider_class=DeepSeekV4ProProvider,
        api_key=deepseek_api_key,
        base_url=deepseek_base_url,
        models=[main_model, "deepseek-reasoner"],
    )

    # Register DeepSeek V4-flash (cheap model)
    registry.register_provider(
        provider_name="deepseek-v4-flash",
        provider_class=DeepSeekV4FlashProvider,
        api_key=deepseek_api_key,
        base_url=deepseek_base_url,
        models=[cheap_model, "deepseek-chat"],
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
        raise RuntimeError(
            "Provider registry not initialized. "
            "Call initialize_registry() first."
        )
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
