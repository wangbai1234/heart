"""MICU relay provider for OpenAI chat-completions and Responses protocols."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from heart.infra.llm_providers._http import make_async_client
from heart.infra.llm_providers.base import (
    CostEstimate,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    StreamChunk,
)


class MicuProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        protocol: str,
        provider_id: str,
        user_agent: str,
        **kwargs,
    ):
        super().__init__(
            api_key=api_key, base_url=base_url, circuit_breaker=kwargs.get("circuit_breaker")
        )
        self.protocol = protocol
        self._provider_id = provider_id
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return self._provider_id

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = make_async_client(
                base_url=(self.base_url or "https://www.micuapi.ai").rstrip("/"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": self._user_agent,
                },
                timeout=60.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _messages(request: LLMRequest) -> list[dict]:
        return [
            {"role": message.role.value, "content": message.content} for message in request.messages
        ]

    def _body(self, request: LLMRequest, *, stream: bool) -> dict:
        body = {"model": request.model, "stream": stream}
        if self.protocol == "responses":
            body["input"] = self._messages(request)
            if request.max_tokens:
                body["max_output_tokens"] = request.max_tokens
        else:
            body["messages"] = self._messages(request)
            body["temperature"] = request.temperature
            if request.max_tokens:
                body["max_tokens"] = request.max_tokens
        return body

    def _path(self) -> str:
        return "/v1/responses" if self.protocol == "responses" else "/v1/chat/completions"

    @staticmethod
    def _response_text(data: dict, protocol: str) -> str:
        if protocol != "responses":
            return data["choices"][0]["message"]["content"]
        content = data.get("output_text", "")
        if content:
            return content
        return "".join(
            part.get("text", "")
            for item in data.get("output", [])
            for part in item.get("content", [])
            if part.get("type") in {"output_text", "text"}
        )

    @staticmethod
    def _stream_chunks(data: dict, protocol: str) -> list[StreamChunk]:
        if protocol == "responses":
            event_type = data.get("type")
            if event_type in {"response.output_text.delta", "response.content_part.delta"}:
                delta = data.get("delta", "")
                if isinstance(delta, dict):
                    delta = delta.get("text", "")
                return [StreamChunk(content=delta)] if delta else []
            if event_type in {"response.completed", "response.output_text.done"}:
                return [StreamChunk(content="", finish_reason="stop")]
            return []
        choices = data.get("choices") or []
        if not choices:
            return []
        choice = choices[0]
        delta = choice.get("delta", {}).get("content", "")
        chunks = [StreamChunk(content=delta)] if delta else []
        if choice.get("finish_reason"):
            chunks.append(StreamChunk(content="", finish_reason=choice["finish_reason"]))
        return chunks

    async def call(self, request: LLMRequest) -> LLMResponse:
        client = await self._get_client()
        try:
            response = await client.post(self._path(), json=self._body(request, stream=False))
            response.raise_for_status()
            data = response.json()
            content = self._response_text(data, self.protocol)
            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                model=data.get("model", request.model),
                finish_reason="stop",
                usage={
                    "prompt_tokens": usage.get("input_tokens", usage.get("prompt_tokens", 0)),
                    "completion_tokens": usage.get(
                        "output_tokens", usage.get("completion_tokens", 0)
                    ),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                provider=self.provider_name,
            )
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"MICU HTTP {exc.response.status_code}",
                self.provider_name,
                request.model,
                status_code=exc.response.status_code,
                retriable=exc.response.status_code in {429, 500, 502, 503, 504},
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                str(exc), self.provider_name, request.model, retriable=True
            ) from exc

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        client = await self._get_client()
        try:
            async with client.stream(
                "POST", self._path(), json=self._body(request, stream=True)
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    for chunk in self._stream_chunks(data, self.protocol):
                        yield chunk
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"MICU HTTP {exc.response.status_code}",
                self.provider_name,
                request.model,
                status_code=exc.response.status_code,
                retriable=exc.response.status_code in {429, 500, 502, 503, 504},
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                str(exc), self.provider_name, request.model, retriable=True
            ) from exc

    def estimate_cost(
        self, prompt_tokens: int, estimated_completion_tokens: int, model: str
    ) -> CostEstimate:
        return CostEstimate(
            prompt_tokens, estimated_completion_tokens, 0, 0, 0, model, self.provider_name
        )

    def count_tokens(self, text: str, model: str) -> int:
        return max(1, len(text) // 4)
