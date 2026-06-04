"""LLM config — backward-compatible types used by app.py and wiring.py.

The real provider logic lives in infra/llm_providers/. These types exist
solely so that app.py / wiring.py can construct a config object and pass
it to initialize_router() without changing their call sites.
"""

from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    """Model tier — kept for backward compatibility."""

    MAIN = "main"
    CHEAP = "cheap"


@dataclass
class DeepSeekConfig:
    """DeepSeek API configuration."""

    api_key: str
    base_url: str = "https://api.deepseek.com"


@dataclass
class ModelConfig:
    """Single model configuration."""

    name: str
    provider: str = "deepseek"
    max_tokens: int = 4000
    temperature: float = 0.7


# Default model configs (names match llm_providers/registry.py env defaults)
_MAIN_MODEL = ModelConfig(name="deepseek-reasoner", max_tokens=8000)
_CHEAP_MODEL = ModelConfig(name="deepseek-chat", max_tokens=4000)


@dataclass
class LLMProviderConfig:
    """Global LLM provider configuration — passed to initialize_router()."""

    deepseek: DeepSeekConfig
    main_model: ModelTier = ModelTier.MAIN
    cheap_model: ModelTier = ModelTier.CHEAP

    def get_main_model(self) -> ModelConfig:
        return _MAIN_MODEL

    def get_cheap_model(self) -> ModelConfig:
        return _CHEAP_MODEL
