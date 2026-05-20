"""Model Router - 所有 LLM 调用的统一入口

遵循原则 E-5: 所有 LLM 调用必须经 Model Router（不直连 SDK）
"""

from typing import AsyncGenerator, Optional
import logging

from .config import ModelTier, LLMProviderConfig
from .provider import DeepSeekProvider

logger = logging.getLogger(__name__)


class ModelRouter:
    """LLM 模型路由器 - 所有 LLM 调用的统一入口"""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self.deepseek_provider = DeepSeekProvider(config.deepseek)

    async def call_main(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: str = "unknown",
    ) -> str:
        """
        调用主模型 (高质量响应)
        用于: SS05 Composer (主角色响应)

        Args:
            messages: 对话历史
            temperature: 温度 (默认使用模型配置)
            max_tokens: 最大输出 token
            agent_name: 调用的 agent 名称（用于日志）

        Returns:
            完整的模型响应
        """
        model = self.config.get_main_model()
        logger.info(f"[{agent_name}] Calling main model: {model.name}")
        return await self.deepseek_provider.call(model, messages, temperature, max_tokens)

    async def stream_main(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: str = "unknown",
    ) -> AsyncGenerator[str, None]:
        """
        流式调用主模型 (高质量响应)
        用于: SS05 Composer (实时流式返回)

        Yields:
            模型响应的文本片段
        """
        model = self.config.get_main_model()
        logger.info(f"[{agent_name}] Streaming main model: {model.name}")
        async for chunk in self.deepseek_provider.stream(model, messages, temperature, max_tokens):
            yield chunk

    async def call_cheap(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        agent_name: str = "unknown",
    ) -> str:
        """
        调用便宜模型 (快速低成本)
        用于: SS02 Memory (编码、记忆处理)
             SS03 Emotion (情感分类)
             SS07 Safety (安全检查、分类)

        Args:
            messages: 对话历史
            temperature: 温度
            max_tokens: 最大输出 token
            json_mode: 是否强制 JSON 输出
            agent_name: 调用的 agent 名称

        Returns:
            完整的模型响应
        """
        model = self.config.get_cheap_model()
        logger.info(f"[{agent_name}] Calling cheap model: {model.name}")
        return await self.deepseek_provider.call(
            model, messages, temperature, max_tokens, json_mode=json_mode
        )

    async def estimate_cost(
        self,
        model_tier: ModelTier,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        估算调用成本 (用于监控和告警)
        """
        if model_tier == ModelTier.MAIN:
            model = self.config.get_main_model()
        else:
            model = self.config.get_cheap_model()

        return await self.deepseek_provider.estimate_cost(model, input_tokens, output_tokens)

    async def close(self):
        """关闭所有连接"""
        await self.deepseek_provider.close()


# 全局 Model Router 实例（会在应用启动时初始化）
_global_router: Optional[ModelRouter] = None


async def get_model_router() -> ModelRouter:
    """获取全局 Model Router 实例"""
    global _global_router
    if _global_router is None:
        raise RuntimeError("ModelRouter not initialized. Call initialize_router() first.")
    return _global_router


async def initialize_router(config: LLMProviderConfig):
    """初始化全局 Model Router"""
    global _global_router
    _global_router = ModelRouter(config)
    logger.info(
        f"ModelRouter initialized with main={config.get_main_model().name}, "
        f"cheap={config.get_cheap_model().name}"
    )


async def shutdown_router():
    """关闭全局 Model Router"""
    global _global_router
    if _global_router:
        await _global_router.close()
        _global_router = None
