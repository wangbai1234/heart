"""
Claude provider — Anthropic /v1/messages API.

Request/response format differs from OpenAI:
- system prompt is a top-level field, not a message
- content is block-based (list of {type, text} dicts)
- streaming uses named SSE events (content_block_delta, etc.)

Supports two styles via `claude_api_style`:
- "anthropic" (default): native /v1/messages with x-api-key + anthropic-version headers
- "openai-compat": /v1/chat/completions with Bearer auth (for Claude via proxy)
"""

import json
from typing import AsyncIterator, Dict, List, Optional

import httpx

from heart.infra.llm_providers.base import (
    CircuitBreakerInterface,
    CostEstimate,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ProviderError,
    StreamChunk,
)


class ClaudeProvider(LLMProvider):
    """
    Anthropic Claude provider.

    Uses native /v1/messages endpoint by default.
    Switch to OpenAI-compat mode by passing claude_api_style="openai-compat".
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com"
    DEFAULT_MODEL = "claude-sonnet-4-5"
    ANTHROPIC_VERSION = "2023-06-01"

    PRICING = {
        "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
        "claude-opus-4-8": {"input": 15.0, "output": 75.0},
        "claude-sonnet-5": {"input": 3.0, "output": 15.0},
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        circuit_breaker: Optional[CircuitBreakerInterface] = None,
        timeout: float = 60.0,
        api_style: str = "anthropic",
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            circuit_breaker=circuit_breaker,
        )
        self.timeout = timeout
        self.api_style = api_style  # "anthropic" | "openai-compat"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_name(self) -> str:
        return "claude"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            if self.api_style == "openai-compat":
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            else:
                # Use Bearer auth to match Anthropic SDK behavior (ANTHROPIC_AUTH_TOKEN),
                # which is required by proxies like micuapi. Real Anthropic API also accepts Bearer.
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "x-api-key": self.api_key,
                    "anthropic-version": self.ANTHROPIC_VERSION,
                    "Content-Type": "application/json",
                }
            self._client = httpx.AsyncClient(
                base_url=self.base_url or "",
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _split_messages(self, messages: List[Message]) -> tuple[str, List[Dict]]:
        """Extract system prompt and split into (system_text, chat_messages)."""
        system_parts: list[str] = []
        chat: list[Dict] = []
        for m in messages:
            if m.role == MessageRole.SYSTEM:
                system_parts.append(m.content)
            else:
                # Use block array format to match Anthropic SDK behavior — proxies expect this
                chat.append(
                    {
                        "role": m.role.value,
                        "content": [{"type": "text", "text": m.content}],
                    }
                )
        return "\n\n".join(system_parts), chat

    def _prepare_anthropic_body(self, request: LLMRequest, stream: bool) -> Dict:
        system_text, chat_messages = self._split_messages(request.messages)
        body: Dict = {
            "model": request.model or self.DEFAULT_MODEL,
            "messages": chat_messages,
            "max_tokens": request.max_tokens or 1024,
            "stream": stream,
        }
        if system_text:
            body["system"] = system_text
        if request.temperature is not None:
            body["temperature"] = request.temperature
        return body

    def _prepare_openai_body(self, request: LLMRequest, stream: bool) -> Dict:
        messages = [{"role": m.role.value, "content": m.content} for m in request.messages]
        body: Dict = {
            "model": request.model or self.DEFAULT_MODEL,
            "messages": messages,
            "stream": stream,
        }
        if request.max_tokens:
            body["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            body["temperature"] = request.temperature
        return body

    async def call(self, request: LLMRequest) -> LLMResponse:
        if self.circuit_breaker.is_open(self.provider_name, request.model):
            raise ProviderError(
                f"Circuit breaker open for {self.provider_name}/{request.model}",
                provider=self.provider_name,
                model=request.model,
                retriable=True,
            )

        client = await self._get_client()

        if self.api_style == "openai-compat":
            return await self._call_openai_compat(client, request)
        return await self._call_anthropic(client, request)

    async def _call_anthropic(self, client: httpx.AsyncClient, request: LLMRequest) -> LLMResponse:
        body = self._prepare_anthropic_body(request, stream=False)
        try:
            response = await client.post("/v1/messages", json=body)
            response.raise_for_status()
            data = response.json()
            self.circuit_breaker.record_success(self.provider_name, request.model)

            # content is a list of blocks: [{"type":"text","text":"..."}]
            text = "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
            usage = data.get("usage", {})
            return LLMResponse(
                content=text,
                model=data.get("model", request.model),
                finish_reason=data.get("stop_reason", "end_turn"),
                usage={
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                },
                provider=self.provider_name,
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
                f"Unexpected error: {e}",
                provider=self.provider_name,
                model=request.model,
                retriable=False,
            ) from e

    async def _call_openai_compat(
        self, client: httpx.AsyncClient, request: LLMRequest
    ) -> LLMResponse:
        body = self._prepare_openai_body(request, stream=False)
        try:
            response = await client.post("/v1/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()
            self.circuit_breaker.record_success(self.provider_name, request.model)
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
                f"Unexpected error: {e}",
                provider=self.provider_name,
                model=request.model,
                retriable=False,
            ) from e

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        if self.circuit_breaker.is_open(self.provider_name, request.model):
            raise ProviderError(
                f"Circuit breaker open for {self.provider_name}/{request.model}",
                provider=self.provider_name,
                model=request.model,
                retriable=True,
            )

        client = await self._get_client()

        if self.api_style == "openai-compat":
            async for chunk in self._stream_openai_compat(client, request):
                yield chunk
            return

        async for chunk in self._stream_anthropic(client, request):
            yield chunk

    @staticmethod
    def _parse_anthropic_sse_line(line: str) -> "StreamChunk | None":
        """Parse one SSE data: line into a StreamChunk, or None to skip."""
        if not line or line.startswith("event:") or not line.startswith("data:"):
            return None
        data_str = line[5:].strip()
        if not data_str or data_str == "[DONE]":
            return None
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return None
        ev_type = data.get("type", "")
        if ev_type == "content_block_delta":
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                if text:
                    return StreamChunk(content=text)
        elif ev_type == "message_delta":
            stop_reason = data.get("delta", {}).get("stop_reason")
            usage = data.get("usage", {})
            if stop_reason:
                return StreamChunk(
                    content="",
                    finish_reason=stop_reason,
                    usage={
                        "prompt_tokens": 0,
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("output_tokens", 0),
                    }
                    if usage
                    else None,
                )
        return None

    async def _stream_anthropic(
        self, client: httpx.AsyncClient, request: LLMRequest
    ) -> AsyncIterator[StreamChunk]:
        body = self._prepare_anthropic_body(request, stream=True)
        try:
            async with client.stream("POST", "/v1/messages", json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    chunk = self._parse_anthropic_sse_line(line)
                    if chunk is not None:
                        yield chunk
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
                f"Unexpected error: {e}",
                provider=self.provider_name,
                model=request.model,
                retriable=False,
            ) from e

    async def _stream_openai_compat(
        self, client: httpx.AsyncClient, request: LLMRequest
    ) -> AsyncIterator[StreamChunk]:
        body = self._prepare_openai_body(request, stream=True)
        try:
            async with client.stream("POST", "/v1/chat/completions", json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choice = data["choices"][0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield StreamChunk(content=content)
                        if choice.get("finish_reason"):
                            yield StreamChunk(content="", finish_reason=choice["finish_reason"])
                    except json.JSONDecodeError:
                        continue
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
                f"Unexpected error: {e}",
                provider=self.provider_name,
                model=request.model,
                retriable=False,
            ) from e

    def estimate_cost(
        self, prompt_tokens: int, estimated_completion_tokens: int, model: str
    ) -> CostEstimate:
        pricing = self.PRICING.get(model, self.PRICING["claude-sonnet-4-5"])
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
        return len(text) // 4
