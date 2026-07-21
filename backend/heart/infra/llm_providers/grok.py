"""
Grok provider implementation (xAI).

OpenAI-compatible /v1/chat/completions endpoint — mirrors deepseek.py structure.
"""

import json
import re
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


class GrokProvider(LLMProvider):
    """
    xAI Grok provider (OpenAI-compatible API).

    Used for mid-tier chat responses (plus-tier users).

    Default model: grok-3-mini-fast (cost-effective)
    """

    DEFAULT_BASE_URL = "https://api.x.ai"
    DEFAULT_MODEL = "grok-3-mini-fast"

    PRICING = {
        "grok-3-mini-fast": {"input": 0.3, "output": 0.5},
        "grok-3": {"input": 3.0, "output": 15.0},
        "grok-3-fast": {"input": 5.0, "output": 25.0},
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        circuit_breaker: Optional[CircuitBreakerInterface] = None,
        timeout: float = 30.0,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            circuit_breaker=circuit_breaker,
        )
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_name(self) -> str:
        return "grok"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url or "",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _strip_think_tags(text: str) -> str:
        """Remove <think>...</think> blocks from non-streaming response."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).lstrip("\n")

    @staticmethod
    async def _raw_chunks(response: httpx.Response) -> AsyncIterator[StreamChunk]:
        """Parse SSE lines and yield raw StreamChunks without filtering."""
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
                    usage = data.get("usage")
                    yield StreamChunk(
                        content="",
                        finish_reason=choice["finish_reason"],
                        usage={
                            "prompt_tokens": usage.get("prompt_tokens", 0) if usage else 0,
                            "completion_tokens": (
                                usage.get("completion_tokens", 0) if usage else 0
                            ),
                            "total_tokens": usage.get("total_tokens", 0) if usage else 0,
                        }
                        if usage
                        else None,
                    )
            except json.JSONDecodeError:
                continue

    @staticmethod
    def _scan_outside_think(text: str, i: int) -> tuple[str, str, bool, int]:
        """Scan text while outside a <think> block. Returns (result, pending, in_think, i)."""
        start = text.find("<think>", i)
        if start == -1:
            tail_start = max(i, len(text) - 6)
            for j in range(tail_start, len(text)):
                if "<think>".startswith(text[j:]):
                    return text[i:j], text[j:], False, len(text)
            return text[i:], "", False, len(text)
        return text[i:start], "", True, start + len("<think>")

    @staticmethod
    def _scan_inside_think(text: str, i: int) -> tuple[str, bool, int]:
        """Scan text while inside a <think> block. Returns (pending, in_think, i)."""
        end = text.find("</think>", i)
        if end == -1:
            tail_start = max(i, len(text) - 7)
            for j in range(tail_start, len(text)):
                if "</think>".startswith(text[j:]):
                    return text[j:], True, len(text)
            return "", True, len(text)
        new_i = end + len("</think>")
        # Drop one leading newline right after closing tag
        if new_i < len(text) and text[new_i] == "\n":
            new_i += 1
        return "", False, new_i

    @staticmethod
    async def _filter_think_tags_stream(
        chunks: AsyncIterator[StreamChunk],
    ) -> AsyncIterator[StreamChunk]:
        """
        Strip <think>...</think> blocks from a streaming sequence of chunks.

        Handles tags split across chunk boundaries via a small pending buffer
        (max 7 chars = len("</think>") - 1). Fully streaming — yields each
        non-think chunk immediately with no batching.
        """
        in_think = False
        pending = ""

        async for chunk in chunks:
            if not chunk.content:
                yield chunk
                continue

            text = pending + chunk.content
            pending = ""
            result = ""
            i = 0

            while i < len(text):
                if in_think:
                    seg_pending, in_think, i = GrokProvider._scan_inside_think(text, i)
                    pending = seg_pending
                    if i >= len(text):
                        break
                else:
                    seg, seg_pending, in_think, i = GrokProvider._scan_outside_think(text, i)
                    result += seg
                    pending = seg_pending
                    if i >= len(text):
                        break

            if result:
                yield StreamChunk(content=result)

        if pending and not in_think:
            yield StreamChunk(content=pending)

    def _prepare_request_body(self, request: LLMRequest) -> Dict:
        messages = [{"role": msg.role.value, "content": msg.content} for msg in request.messages]
        body: Dict = {
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
            self.circuit_breaker.record_success(self.provider_name, request.model)
            choice = data["choices"][0]
            usage = data.get("usage", {})
            return LLMResponse(
                content=self._strip_think_tags(choice["message"]["content"]),
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
        body = self._prepare_request_body(request)
        body["stream"] = True

        try:
            async with client.stream("POST", "/v1/chat/completions", json=body) as response:
                response.raise_for_status()
                async for chunk in self._filter_think_tags_stream(self._raw_chunks(response)):
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

    def estimate_cost(
        self, prompt_tokens: int, estimated_completion_tokens: int, model: str
    ) -> CostEstimate:
        pricing = self.PRICING.get(model, self.PRICING["grok-3-mini-fast"])
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
