"""Model Router - 所有 LLM 调用的统一入口

遵循原则 E-5: 所有 LLM 调用必须经 Model Router（不直连 SDK）
遵循原则 O-6: Model Router 必须支持 failover

V1 Future: Multi-provider failover (Anthropic → DeepSeek → OpenAI)
"""

from typing import Any, AsyncGenerator, Callable, Optional
import structlog

from .config import ModelTier, LLMProviderConfig
from .provider import DeepSeekProvider

logger = structlog.get_logger()

# ============================================================
# Failover hooks — V1 multi-provider fallback per O-6
# ============================================================


# Type alias for failover hook callbacks
FailoverHook = Callable[[list[dict], Optional[float], Optional[int]], Any]
StreamFailoverHook = Callable[[list[dict], Optional[float], Optional[int]], AsyncGenerator[str, None]]


class ModelRouter:
    """LLM 模型路由器 - 所有 LLM 调用的统一入口.

    Supports:
      - Primary provider (DeepSeek today, multi-provider in V1)
      - Failover hooks for future V1 fallback (O-6)
      - Circuit breaker integration (via heart.infra.circuit_breaker)
    """

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self.deepseek_provider = DeepSeekProvider(config.deepseek)

        # Failover hooks — injectable for V1 multi-provider
        self._failover_call: Optional[FailoverHook] = None
        self._failover_stream: Optional[StreamFailoverHook] = None
        self._circuit_breaker = None  # Set via inject_circuit_breaker()

    # --- Failover Configuration ---

    def inject_circuit_breaker(
        self,
        breaker,  # heart.infra.circuit_breaker.CircuitBreaker
    ) -> None:
        """Wire a circuit breaker around this router for failover protection.

        The breaker is checked before every call. When the circuit is open,
        calls are rejected immediately — the caller handles fallback.

        Args:
            breaker: A CircuitBreaker instance (e.g. for "main_llm" service).
        """
        self._circuit_breaker = breaker
        logger.info(f"ModelRouter: circuit breaker wired (name={breaker.name})")

    def inject_failover_hooks(
        self,
        *,
        call_hook: Optional[FailoverHook] = None,
        stream_hook: Optional[StreamFailoverHook] = None,
    ) -> None:
        """Register failover hooks for V1 multi-provider fallback.

        When the primary provider fails and no circuit breaker is open,
        these hooks are tried in order.

        Args:
            call_hook: Sync failover hook for call_main/call_cheap.
            stream_hook: Async generator failover hook for stream_main.
        """
        self._failover_call = call_hook
        self._failover_stream = stream_hook
        logger.info("ModelRouter: failover hooks injected")

    # --- Primary API ---

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
        """
        model = self.config.get_main_model()
        logger.info(f"[{agent_name}] Calling main model: {model.name}")

        # Circuit breaker check
        if self._circuit_breaker and self._circuit_breaker.is_open():
            logger.warning(
                f"[{agent_name}] Circuit OPEN for main model — "
                f"attempting failover"
            )
            return await self._try_failover_call(
                messages, temperature, max_tokens, agent_name
            )

        try:
            result = await self.deepseek_provider.call(
                model, messages, temperature, max_tokens
            )
            if self._circuit_breaker:
                self._circuit_breaker.record_success()
            return result
        except Exception as e:
            if self._circuit_breaker:
                self._circuit_breaker.record_failure()
            logger.error(f"[{agent_name}] Main model call failed: {e}")
            return await self._try_failover_call(
                messages, temperature, max_tokens, agent_name
            )

    async def stream_main(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: str = "unknown",
    ) -> AsyncGenerator[str, None]:
        """流式调用主模型 (高质量响应)"""
        model = self.config.get_main_model()
        logger.info(f"[{agent_name}] Streaming main model: {model.name}")

        # Circuit breaker check
        if self._circuit_breaker and self._circuit_breaker.is_open():
            logger.warning(
                f"[{agent_name}] Circuit OPEN for main model — "
                f"attempting failover stream"
            )
            async for chunk in self._try_failover_stream(
                messages, temperature, max_tokens, agent_name
            ):
                yield chunk
            return

        try:
            async for chunk in self.deepseek_provider.stream(
                model, messages, temperature, max_tokens
            ):
                yield chunk
            if self._circuit_breaker:
                self._circuit_breaker.record_success()
        except Exception as e:
            if self._circuit_breaker:
                self._circuit_breaker.record_failure()
            logger.error(f"[{agent_name}] Main model stream failed: {e}")
            async for chunk in self._try_failover_stream(
                messages, temperature, max_tokens, agent_name
            ):
                yield chunk

    async def call_cheap(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        agent_name: str = "unknown",
    ) -> str:
        """调用便宜模型 (快速低成本)"""
        model = self.config.get_cheap_model()
        logger.info(f"[{agent_name}] Calling cheap model: {model.name}")

        try:
            result = await self.deepseek_provider.call(
                model, messages, temperature, max_tokens, json_mode=json_mode
            )
            return result
        except Exception as e:
            logger.error(f"[{agent_name}] Cheap model call failed: {e}")
            raise

    async def estimate_cost(
        self,
        model_tier: ModelTier,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """估算调用成本 (用于监控和告警)"""
        if model_tier == ModelTier.MAIN:
            model = self.config.get_main_model()
        else:
            model = self.config.get_cheap_model()
        return await self.deepseek_provider.estimate_cost(model, input_tokens, output_tokens)

    async def close(self):
        """关闭所有连接"""
        await self.deepseek_provider.close()

    # --- Failover internals ---

    async def _try_failover_call(
        self,
        messages: list[dict],
        temperature: Optional[float],
        max_tokens: Optional[int],
        agent_name: str,
    ) -> str:
        """Attempt V1 failover call hook, then raise."""
        if self._failover_call is not None:
            logger.info(f"[{agent_name}] Trying V1 failover call hook")
            try:
                result = await self._failover_call(messages, temperature, max_tokens)
                return result
            except Exception as e:
                logger.error(f"[{agent_name}] Failover call hook also failed: {e}")

        raise RuntimeError(
            f"[{agent_name}] Primary model failed and no failover hook available"
        )

    async def _try_failover_stream(
        self,
        messages: list[dict],
        temperature: Optional[float],
        max_tokens: Optional[int],
        agent_name: str,
    ) -> AsyncGenerator[str, None]:
        """Attempt V1 failover stream hook, then raise."""
        if self._failover_stream is not None:
            logger.info(f"[{agent_name}] Trying V1 failover stream hook")
            try:
                async for chunk in self._failover_stream(
                    messages, temperature, max_tokens
                ):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"[{agent_name}] Failover stream hook also failed: {e}")

        raise RuntimeError(
            f"[{agent_name}] Primary model stream failed and no failover hook available"
        )


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
