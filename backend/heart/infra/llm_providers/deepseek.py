"""
DeepSeek V4-flash provider implementation.

Fast and cheap model for auxiliary tasks (classification, encoding, etc.)
"""

import json
from typing import AsyncIterator, Dict, Optional

import httpx

from heart.infra.llm_providers.base import (
    CircuitBreakerInterface,
    CostEstimate,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    StreamChunk,
)


class DeepSeekV4FlashProvider(LLMProvider):
    """
    DeepSeek V4-flash (deepseek-chat) provider.

    Fast and cheap model for:
    - Memory encoding
    - Safety classification
    - Emotion detection
    - Other auxiliary tasks

    Pricing (per 1M tokens):
    - Input: $0.14
    - Output: $0.28
    - Cache read: $0.014
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"

    # Pricing per 1M tokens (USD)
    PRICING = {
        "deepseek-chat": {
            "input": 0.14,
            "output": 0.28,
            "cache_read": 0.014,
        },
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        circuit_breaker: Optional[CircuitBreakerInterface] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize DeepSeek V4-flash provider.

        Args:
            api_key: DeepSeek API key
            base_url: Custom base URL (defaults to api.deepseek.com)
            circuit_breaker: Optional circuit breaker
            timeout: Request timeout in seconds
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            circuit_breaker=circuit_breaker,
        )
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_name(self) -> str:
        return "deepseek-v4-flash"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _prepare_request_body(self, request: LLMRequest) -> Dict:
        """Prepare request body for DeepSeek API."""
        messages = [{"role": msg.role.value, "content": msg.content} for msg in request.messages]

        body = {
            "model": request.model or self.DEFAULT_MODEL,
            "messages": messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": request.stream,
        }

        if request.max_tokens:
            body["max_tokens"] = request.max_tokens

        if request.json_mode:
            body["response_format"] = {"type": "json_object"}

        return body

    async def call(self, request: LLMRequest) -> LLMResponse:
        """
        Non-streaming call to DeepSeek V4-flash.

        Args:
            request: LLM request

        Returns:
            Complete response
        """
        if self.circuit_breaker.is_open(self.provider_name, request.model):
            raise ProviderError(
                f"Circuit breaker open for {self.provider_name}/{request.model}",
                provider=self.provider_name,
                model=request.model,
                retriable=True,
            )

        client = await self._get_client()
        body = self._prepare_request_body(request)
        body["stream"] = False

        try:
            response = await client.post("/v1/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()

            # Record success
            self.circuit_breaker.record_success(self.provider_name, request.model)

            # Extract response
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", request.model),
                finish_reason=choice.get("finish_reason", "stop"),
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                provider=self.provider_name,
                metadata={"raw_response": data},
            )

        except httpx.HTTPStatusError as e:
            self.circuit_breaker.record_failure(self.provider_name, request.model, e)
            raise ProviderError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                provider=self.provider_name,
                model=request.model,
                status_code=e.response.status_code,
                retriable=e.response.status_code in [429, 500, 502, 503, 504],
            ) from e
        except Exception as e:
            self.circuit_breaker.record_failure(self.provider_name, request.model, e)
            raise ProviderError(
                f"Unexpected error: {str(e)}",
                provider=self.provider_name,
                model=request.model,
                retriable=False,
            ) from e

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """
        Streaming call to DeepSeek V4-flash.

        Args:
            request: LLM request

        Yields:
            StreamChunk: Individual response chunks
        """
        if self.circuit_breaker.is_open(self.provider_name, request.model):
            raise ProviderError(
                f"Circuit breaker open for {self.provider_name}/{request.model}",
                provider=self.provider_name,
                model=request.model,
                retriable=True,
            )

        client = await self._get_client()
        body = self._prepare_request_body(request)
        body["stream"] = True

        try:
            async with client.stream("POST", "/v1/chat/completions", json=body) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Remove "data: " prefix

                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        choice = data["choices"][0]

                        # Yield content chunk
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield StreamChunk(content=content)

                        # Final chunk with finish reason and usage
                        if choice.get("finish_reason"):
                            usage = data.get("usage")
                            yield StreamChunk(
                                content="",
                                finish_reason=choice["finish_reason"],
                                usage={
                                    "prompt_tokens": usage.get("prompt_tokens", 0) if usage else 0,
                                    "completion_tokens": usage.get("completion_tokens", 0)
                                    if usage
                                    else 0,
                                    "total_tokens": usage.get("total_tokens", 0) if usage else 0,
                                }
                                if usage
                                else None,
                            )
                    except json.JSONDecodeError:
                        continue

            # Record success
            self.circuit_breaker.record_success(self.provider_name, request.model)

        except httpx.HTTPStatusError as e:
            self.circuit_breaker.record_failure(self.provider_name, request.model, e)
            raise ProviderError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                provider=self.provider_name,
                model=request.model,
                status_code=e.response.status_code,
                retriable=e.response.status_code in [429, 500, 502, 503, 504],
            ) from e
        except Exception as e:
            self.circuit_breaker.record_failure(self.provider_name, request.model, e)
            raise ProviderError(
                f"Unexpected error: {str(e)}",
                provider=self.provider_name,
                model=request.model,
                retriable=False,
            ) from e

    def estimate_cost(
        self,
        prompt_tokens: int,
        estimated_completion_tokens: int,
        model: str,
    ) -> CostEstimate:
        """
        Estimate cost for DeepSeek V4-flash call.

        Args:
            prompt_tokens: Number of prompt tokens
            estimated_completion_tokens: Estimated completion tokens
            model: Model name

        Returns:
            Cost estimate
        """
        pricing = self.PRICING.get(model, self.PRICING["deepseek-chat"])

        # Calculate costs (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (estimated_completion_tokens / 1_000_000) * pricing["output"]

        return CostEstimate(
            prompt_tokens=prompt_tokens,
            estimated_completion_tokens=estimated_completion_tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=input_cost + output_cost,
            model=model,
            provider=self.provider_name,
        )

    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens in text.

        Note: Uses simple approximation (1 token ≈ 4 chars for English).
        For production, use tiktoken or model-specific tokenizer.

        Args:
            text: Text to count
            model: Model name

        Returns:
            Approximate token count
        """
        # Simple approximation: ~4 chars per token
        return len(text) // 4
