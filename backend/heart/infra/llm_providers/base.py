"""
Abstract base class for LLM providers.

Defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """A message in the conversation."""
    role: MessageRole
    content: str


@dataclass
class LLMRequest:
    """Request to LLM provider."""
    messages: List[Message]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stream: bool = False
    json_mode: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Non-streaming response from LLM provider."""
    content: str
    model: str
    finish_reason: str
    usage: Dict[str, int]  # {prompt_tokens, completion_tokens, total_tokens}
    created_at: datetime = field(default_factory=datetime.utcnow)
    provider: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """A chunk from streaming response."""
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


@dataclass
class CostEstimate:
    """Cost estimation for LLM call."""
    prompt_tokens: int
    estimated_completion_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    model: str
    provider: str


class CircuitBreakerInterface:
    """
    Interface for circuit breaker integration.

    LLM providers can hook into circuit breaker for:
    - Recording failures
    - Checking if provider is available
    - Automatic failover triggering

    This is just an interface - actual implementation provided by SS07.
    """

    def record_success(self, provider: str, model: str) -> None:
        """Record successful call."""
        pass

    def record_failure(self, provider: str, model: str, error: Exception) -> None:
        """Record failed call."""
        pass

    def is_open(self, provider: str, model: str) -> bool:
        """Check if circuit breaker is open (unavailable)."""
        return False


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers must implement this interface to ensure
    consistent behavior across different providers (DeepSeek, Claude, GPT, etc.)
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        circuit_breaker: Optional[CircuitBreakerInterface] = None,
    ):
        """
        Initialize provider.

        Args:
            api_key: API key for the provider
            base_url: Optional custom base URL
            circuit_breaker: Optional circuit breaker for failure handling
        """
        self.api_key = api_key
        self.base_url = base_url
        self.circuit_breaker = circuit_breaker or CircuitBreakerInterface()

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name (e.g., 'deepseek', 'anthropic', 'openai')."""
        pass

    @abstractmethod
    async def call(self, request: LLMRequest) -> LLMResponse:
        """
        Non-streaming call to LLM.

        Args:
            request: LLM request with messages and parameters

        Returns:
            Complete LLM response

        Raises:
            ProviderError: On API failure
            ValidationError: On invalid request
        """
        pass

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """
        Streaming call to LLM.

        Args:
            request: LLM request with messages and parameters

        Yields:
            StreamChunk: Individual chunks of response

        Raises:
            ProviderError: On API failure
            ValidationError: On invalid request
        """
        pass

    @abstractmethod
    def estimate_cost(
        self,
        prompt_tokens: int,
        estimated_completion_tokens: int,
        model: str,
    ) -> CostEstimate:
        """
        Estimate cost for a given request.

        Args:
            prompt_tokens: Number of tokens in prompt
            estimated_completion_tokens: Estimated completion tokens
            model: Model name

        Returns:
            Cost estimation with breakdown
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens in text for given model.

        Args:
            text: Text to count tokens for
            model: Model name (affects tokenization)

        Returns:
            Number of tokens
        """
        pass


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        model: str,
        status_code: Optional[int] = None,
        retriable: bool = False,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retriable = retriable


class ValidationError(Exception):
    """Exception for invalid requests."""
    pass
