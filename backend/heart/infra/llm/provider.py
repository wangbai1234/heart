"""LLM 提供商抽象和 DeepSeek 实现"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
import httpx
import json
import structlog

from .config import DeepSeekConfig, ModelConfig
from heart.observability.turn_profiler import TurnProfiler

logger = structlog.get_logger()


class LLMProvider(ABC):
    """LLM 提供商基类"""

    @abstractmethod
    async def call(
        self,
        model: ModelConfig,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """同步调用 LLM，返回完整响应"""
        pass

    @abstractmethod
    async def stream(
        self,
        model: ModelConfig,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM，逐字节返回"""
        pass

    @abstractmethod
    async def estimate_cost(
        self,
        model: ModelConfig,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """估算调用成本（USD）"""
        pass


class DeepSeekProvider(LLMProvider):
    """DeepSeek 提供商实现"""

    # DeepSeek 官方定价 (per 1M tokens)
    PRICING = {
        "deepseek-reasoner": {
            "input": 0.55,  # $0.55 per 1M input tokens
            "output": 2.19,  # $2.19 per 1M output tokens
        },
        "deepseek-chat": {
            "input": 0.14,  # $0.14 per 1M input tokens
            "output": 0.28,  # $0.28 per 1M output tokens
        },
    }

    def __init__(self, config: DeepSeekConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.full_base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=60.0,
        )

    async def call(
        self,
        model: ModelConfig,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """同步调用 DeepSeek API"""
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": model.name,
                    "messages": messages,
                    "temperature": temperature or model.temperature,
                    "max_tokens": max_tokens or model.max_tokens,
                    "response_format": {"type": "json_object"} if json_mode else None,
                },
            )
            response.raise_for_status()
            data = response.json()

            # 记录 token 使用量用于成本计算
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            cost = await self._record_usage(model.name, prompt_tokens, completion_tokens)

            # Annotate active profiler span with usage data
            p = TurnProfiler.current()
            if p.enabled and p.current_span_name() == "model_router":
                p.annotate(
                    model_name=model.name,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    cost_usd=cost,
                )

            return data["choices"][0]["message"]["content"]

        except httpx.HTTPError as e:
            logger.error(f"DeepSeek API error: {e}")
            raise

    async def stream(
        self,
        model: ModelConfig,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """流式调用 DeepSeek API"""
        try:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": model.name,
                    "messages": messages,
                    "temperature": temperature or model.temperature,
                    "max_tokens": max_tokens or model.max_tokens,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # 去掉 "data: " 前缀
                            if data.get("choices"):
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPError as e:
            logger.error(f"DeepSeek streaming error: {e}")
            raise

    async def estimate_cost(
        self,
        model: ModelConfig,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """计算调用成本"""
        pricing = self.PRICING.get(model.name, {})
        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
        return input_cost + output_cost

    async def _record_usage(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """记录 token 使用量（用于监控和计费）"""
        cost = await self.estimate_cost(
            ModelConfig(name=model_name, provider="deepseek", max_tokens=4000),
            input_tokens,
            output_tokens,
        )
        logger.info(
            f"LLM usage: model={model_name}, input={input_tokens}, "
            f"output={output_tokens}, cost=${cost:.4f}"
        )
        return cost

    async def close(self):
        """关闭连接"""
        await self.client.aclose()
