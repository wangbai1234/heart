"""
Subsystem 07: Agent Orchestration

Components:
  - OrchestratorAgent: 顶层 turn 调度器（hot path + cold path）
  - OrchestratorSafetyAdapter: bridges heart.safety.safety_agent → SafetyLevel
  - DirectorAgent: 节奏 / 模态决策引擎（soul-aware per §3.4.4）
  - DirectorHints: 扩展 pacing 元数据（传递给 Composer）
  - SoulPacingProfile: 每角色 pacing 常量（不可变）
  - CircuitBreaker: 每子系统熔断器 per §3.8
  - TurnContext, TurnResult, Trace, TraceSpan: 数据模型 per §4

Author: 心屿团队
"""

from .director import (
    DirectorAgent,
    DirectorHints,
    SoulPacingProfile,
    EmotionSnapshot,
    RelationshipSnapshot,
    get_soul_pacing_profile,
)

from .orchestrator import (
    # Agent classes
    OrchestratorAgent,
    # Circuit breaker
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    # Data models
    TurnContext,
    TurnResult,
    Trace,
    TraceSpan,
    TraceStatus,
    SpanStatus,
    SafetyClassification,
    SafetyLevel,
    DirectorDirectives,
    # Configuration
    SUBSYSTEM_TIMEOUTS,
    CIRCUIT_BREAKER_DEFAULTS,
)

from .safety_adapter import OrchestratorSafetyAdapter

__all__ = [
    # Agent classes
    "OrchestratorAgent",
    "OrchestratorSafetyAdapter",
    "DirectorAgent",
    # Director types
    "DirectorHints",
    "SoulPacingProfile",
    "EmotionSnapshot",
    "RelationshipSnapshot",
    "get_soul_pacing_profile",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    # Data models
    "TurnContext",
    "TurnResult",
    "Trace",
    "TraceSpan",
    "TraceStatus",
    "SpanStatus",
    "SafetyClassification",
    "SafetyLevel",
    "DirectorDirectives",
    # Configuration
    "SUBSYSTEM_TIMEOUTS",
    "CIRCUIT_BREAKER_DEFAULTS",
]
