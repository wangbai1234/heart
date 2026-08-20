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
from heart.infra.llm_providers.micu import MicuProvider
from heart.infra.llm_providers.pool import ConcurrencyGate, PooledLLMProvider
from heart.infra.model_catalog import LEGACY_MODEL_ALIASES

_CODEX_EXTERNAL_UA = "codex_cli_rs/0.77.0 (Windows 10.0.26100; x86_64) WindowsTerminal"
_BROWSER_EXTERNAL_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0"
)


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


def _env_value(name: str, default: str) -> str:
    """Read a non-empty environment value, otherwise use the declared default."""
    return (os.getenv(name) or default).strip()


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
        # Maps every registered model name (including bare slugs like "deepseek")
        # to the provider's canonical API model name (the first entry in its
        # ``models`` list). The vendor APIs reject slugs — DeepSeek only accepts
        # "deepseek-chat"/"deepseek-reasoner" — so the router must translate the
        # routing slug to this canonical name before building the request body.
        self._model_canonical: Dict[str, str] = {}

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

        # Register model mappings. The first model in the list is the canonical
        # API model name; every alias (incl. bare slugs) resolves to it.
        if models:
            canonical = models[0]
            for model in models:
                self._model_to_provider[model] = provider_name
                self._model_canonical[model] = canonical

    def register_provider_instance(
        self,
        provider_name: str,
        provider: LLMProvider,
        models: Optional[list[str]] = None,
    ) -> None:
        """Register a pre-built provider instance (e.g. a PooledLLMProvider)."""
        self._providers[provider_name] = provider
        if models:
            canonical = models[0]
            for model in models:
                self._model_to_provider[model] = provider_name
                self._model_canonical[model] = canonical

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

    def get_canonical_model(self, model: str) -> str:
        """Resolve a routing slug/alias to the provider's canonical API model.

        Falls back to the input unchanged when no mapping exists (e.g. a real
        model name passed by the legacy stream_main path).
        """
        return self._model_canonical.get(model, model)

    def has_model(self, model: str) -> bool:
        """True if a provider is registered for this model/slug.

        Lets the router pre-filter a failover chain down to attempts that can
        actually run, so empty-response failover knows which candidate is the
        genuinely last usable one.
        """
        return model in self._model_to_provider

    def has_provider(self, provider_name: str) -> bool:
        """True when a named provider instance has been registered."""
        return provider_name in self._providers

    def register_model_alias(self, model: str, provider_name: str, canonical: str) -> None:
        """Route one public model slug to an existing provider and upstream model ID."""
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' not registered")
        self._model_to_provider[model] = provider_name
        self._model_canonical[model] = canonical

    async def close_all(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()


# Global registry instance
_global_registry: Optional[ProviderRegistry] = None


def _register_selectable_models(
    registry: ProviderRegistry,
    circuit_breaker: Optional[CircuitBreakerInterface],
) -> None:
    """Attach product slugs to provider configs and env-defined upstream models.

    DeepSeek, Grok, and Claude reuse the existing provider instances above.
    Gemini and GPT add only the two provider integrations that did not already
    exist. Product labels never double as upstream model IDs.
    """
    if registry.has_provider("deepseek-v4-flash"):
        registry.register_model_alias(
            "deepseek-v4-flash",
            "deepseek-v4-flash",
            _env_value("DEEPSEEK_V4_FLASH_MODEL", "deepseek-chat"),
        )
    if registry.has_provider("deepseek-v4-pro"):
        registry.register_model_alias(
            "deepseek-v4-pro",
            "deepseek-v4-pro",
            _env_value("DEEPSEEK_V4_PRO_MODEL", "deepseek-reasoner"),
        )

    if registry.has_provider("grok"):
        grok_model = _env_value("GROK_MODEL", "grok-3-mini-fast")
        registry.register_model_alias("grok-4.5", "grok", grok_model)
        registry.register_model_alias("grok-4.6", "grok", _env_value("GROK_46_MODEL", "grok-4.6"))

    if registry.has_provider("claude"):
        registry.register_model_alias(
            "claude-haiku-4.5",
            "claude",
            _env_value("CLAUDE_HAIKU_MODEL", "claude-haiku-4-5"),
        )
        registry.register_model_alias(
            "claude-sonnet-4.6",
            "claude",
            _env_value("CLAUDE_MODEL", "claude-sonnet-4-5"),
        )
        registry.register_model_alias(
            "claude-opus-4.6",
            "claude",
            _env_value("CLAUDE_OPUS_46_MODEL", "claude-opus-4-6"),
        )
        registry.register_model_alias(
            "claude-opus-5",
            "claude",
            _env_value("CLAUDE_OPUS_5_MODEL", "claude-opus-5"),
        )

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        gemini_model = _env_value("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
        registry.register_provider_instance(
            provider_name="gemini",
            provider=MicuProvider(
                api_key=gemini_api_key,
                base_url=_env_value("GEMINI_BASE_URL", "https://api-slb.micuapi.ai"),
                protocol="chat_completions",
                provider_id="gemini",
                user_agent=_BROWSER_EXTERNAL_UA,
                circuit_breaker=circuit_breaker,
            ),
            models=[gemini_model, "gemini-3.1"],
        )

    gpt_api_key = os.getenv("GPT_API_KEY")
    if gpt_api_key:
        registry.register_provider_instance(
            provider_name="gpt",
            provider=MicuProvider(
                api_key=gpt_api_key,
                base_url=_env_value("GPT_BASE_URL", "https://api-slb.micuapi.ai"),
                protocol="responses",
                provider_id="gpt",
                user_agent=_CODEX_EXTERNAL_UA,
                circuit_breaker=circuit_breaker,
            ),
        )
        registry.register_model_alias("gpt-5.5", "gpt", _env_value("GPT_MODEL", "gpt-5.5"))
        registry.register_model_alias(
            "gpt-5.6-luna", "gpt", _env_value("GPT_LUNA_MODEL", "gpt-5.6-luna")
        )
        registry.register_model_alias(
            "gpt-5.6-sol", "gpt", _env_value("GPT_SOL_MODEL", "gpt-5.6-sol")
        )


def initialize_registry(
    circuit_breaker: Optional[CircuitBreakerInterface] = None,
) -> ProviderRegistry:
    """
    Initialize global provider registry with environment configuration.

    Reads from environment variables:
    - Existing DeepSeek/Grok/Claude provider settings
    - New Gemini/GPT provider settings
    - One explicit upstream model ID for every selectable product model
    - Legacy MAIN_LLM_MODEL/CHEAP_LLM_MODEL aliases
    - BACKGROUND_LLM_MODEL/BACKGROUND_LLM_FAILOVER are consumed by ModelRouter

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

    if keys:
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
            models=[cheap_model, "deepseek-chat", "deepseek"],
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

    # Attach user-selectable product slugs without replacing the existing
    # DeepSeek/Grok/Claude configs used by legacy and background callers.
    _register_selectable_models(registry, circuit_breaker)

    # Old clients remain functional during rollout, but are normalized to the
    # new public catalog before billing and persistence wherever possible.
    for legacy, target in LEGACY_MODEL_ALIASES.items():
        # Preserve an explicitly configured legacy provider (for example a
        # direct DeepSeek key).  MICU selectable registrations must not
        # silently replace that provider just because they expose the same
        # public alias during the rollout.
        if legacy not in registry._model_to_provider and registry.has_model(target):
            registry._model_to_provider[legacy] = registry._model_to_provider[target]
            registry._model_canonical[legacy] = registry._model_canonical[target]

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
