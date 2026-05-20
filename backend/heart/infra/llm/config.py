"""LLM 配置和模型定义"""

from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    """模型层级"""

    MAIN = "main"  # 主响应 - deepseek-reasoner (高质量)
    CHEAP = "cheap"  # 便宜操作 - deepseek-chat (快速)


@dataclass
class ModelConfig:
    """单个模型配置"""

    name: str
    provider: str
    max_tokens: int
    temperature: float = 0.7
    top_p: float = 1.0
    timeout_seconds: int = 30


class LLMModels:
    """所有模型配置"""

    # Main model - 用于主响应 (SS05 Composer)
    # deepseek-reasoner: 更强的推理能力，适合需要深度思考的场景
    MAIN_STRONG = ModelConfig(
        name="deepseek-reasoner",
        provider="deepseek",
        max_tokens=8000,
        temperature=0.7,
        timeout_seconds=30,
    )

    # Cheap model - 用于低成本操作 (SS02/03/07)
    # deepseek-chat: 更快更便宜，用于编码、分类、安全检查
    CHEAP = ModelConfig(
        name="deepseek-chat",
        provider="deepseek",
        max_tokens=4000,
        temperature=0.7,
        timeout_seconds=10,
    )


@dataclass
class DeepSeekConfig:
    """DeepSeek API 配置"""

    api_key: str
    base_url: str = "https://api.deepseek.com"
    api_version: str = "v1"

    @property
    def full_base_url(self) -> str:
        """返回完整的 API 基础 URL"""
        return f"{self.base_url}/{self.api_version}"


@dataclass
class LLMProviderConfig:
    """全局 LLM 提供商配置"""

    deepseek: DeepSeekConfig
    main_model: ModelTier = ModelTier.MAIN
    cheap_model: ModelTier = ModelTier.CHEAP

    def get_main_model(self) -> ModelConfig:
        """获取主模型配置"""
        if self.main_model == ModelTier.MAIN:
            return LLMModels.MAIN_STRONG
        return LLMModels.MAIN_STRONG

    def get_cheap_model(self) -> ModelConfig:
        """获取便宜模型配置"""
        if self.cheap_model == ModelTier.CHEAP:
            return LLMModels.CHEAP
        return LLMModels.CHEAP
