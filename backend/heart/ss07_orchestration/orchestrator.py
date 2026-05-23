"""
Orchestrator Agent — SS07 §3.1 + §3.2

Top-level turn scheduler. 每个 user turn 的入口点。

Hot path (sync, per §3.2):
  Auth → Safety pre-filter → Director pacing → SS05 Composer →
  ModelRouter → LLM stream → Anti-pattern filter → response

Cold path (async, per §3.3):
  Memory Encoder Worker, Critic Agent sample, Inner Loop tick

设计不变量（来自 runtime_specs/07_agent_orchestration.md）:
  INV-O-2:  Safety pre-filter 必须在 composition 之前运行
  INV-O-3:  所有 LLM 调用必须经过 ModelRouter
  INV-O-5:  Safety level ∈ {GREEN, YELLOW, ORANGE, RED, PURPLE}
  INV-O-6:  每个 subsystem 调用都有硬超时
  INV-O-7:  Circuit breaker 触发后切换到 fallback 模式
  O-1:      Sync hot path 不允许阻塞 async wait
  O-7:      每个 sub-agent 必须有 timeout + circuit breaker

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import hashlib
import structlog
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional
from uuid import UUID, uuid4

from heart.infra.llm import ModelRouter, get_model_router
from heart.ss05_composer.composer import PromptBundle

logger = structlog.get_logger()


# ============================================================
# Enums
# ============================================================


class SafetyLevel(str, Enum):
    """Safety classification levels per INV-O-5."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"
    PURPLE = "PURPLE"


class TraceStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REROLLED = "rerolled"
    FALLBACK = "fallback"


class SpanStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ============================================================
# Data Models
# ============================================================


@dataclass
class SafetyClassification:
    """Safety pre-filter 结果 per §5.2."""
    level: SafetyLevel
    confidence: float
    triggered_categories: list[str] = field(default_factory=list)
    reason: str = ""
    recommended_action: str = "normal_reply"
    prompt_directives: dict[str, Any] = field(default_factory=dict)
    classified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_hash: str = ""


@dataclass
class DirectorDirectives:
    """Director pacing 决策 per §5.3."""
    modality: str = "text"
    modality_change_reason: Optional[str] = None
    response_length_target: str = "medium"
    typing_pause_ms: int = 800
    llm_temperature: float = 0.8
    llm_top_p: float = 0.95
    should_voice_respond: bool = False
    energy_modifier: float = 0.0
    trace_id: UUID = field(default_factory=uuid4)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TurnContext:
    """单个 turn 的上下文载体。"""
    user_id: UUID
    character_id: str
    user_message: str
    modality: str
    trace_id: UUID = field(default_factory=uuid4)
    session_id: Optional[UUID] = None
    turn_index: int = 0
    safety_flag: str = "normal"
    suicide_protocol_active: bool = False
    user_tier: str = "free"
    user_locale: str = "en"
    user_jurisdiction: str = "US"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TraceSpan:
    """Per-agent timing span per §4.2."""
    span_id: UUID = field(default_factory=uuid4)
    parent_span_id: Optional[UUID] = None
    agent: str = ""
    operation: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.SUCCESS
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    """Full turn trace per §4.2."""
    trace_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    character_id: str = ""
    session_id: Optional[UUID] = None
    turn_index: int = 0
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    spans: list[TraceSpan] = field(default_factory=list)
    status: TraceStatus = TraceStatus.IN_PROGRESS
    final_response: Optional[str] = None
    errors: list[dict] = field(default_factory=list)
    llm_tokens_used: dict[str, int] = field(default_factory=dict)
    ended_at: Optional[str] = None


@dataclass
class TurnResult:
    """handle_turn() 的返回结构。"""
    response_text: str
    trace: Trace
    safety: SafetyClassification
    directives: DirectorDirectives
    streaming: bool = False
    stream_iterator: Optional[AsyncIterator[str]] = None


# ============================================================
# Circuit Breaker — per INV-O-7 + §3.8
# ============================================================


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker."""
    failure_threshold: int = 5
    window_seconds: float = 60.0
    open_duration_seconds: float = 30.0


class CircuitBreaker:
    """Per-subsystem circuit breaker (in-memory).

    States: CLOSED → (failures > threshold) → OPEN → (time elapsed) → HALF_OPEN
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._window_start: float = 0.0
        self._opened_at: float = 0.0
        self._total_calls: int = 0
        self._total_failures: int = 0

    def is_open(self) -> bool:
        """Check if the circuit is currently open (rejecting calls)."""
        if self.state == CircuitState.CLOSED:
            return False
        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.config.open_duration_seconds:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit [{self.name}] → HALF_OPEN (elapsed {elapsed:.1f}s)")
                return False
            return True
        # HALF_OPEN: allow probe calls
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        self._total_calls += 1
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info(f"Circuit [{self.name}] → CLOSED (probe succeeded)")

    def record_failure(self) -> None:
        """Record a failed call."""
        self._total_calls += 1
        self._total_failures += 1

        now = time.monotonic()
        if now - self._window_start > self.config.window_seconds:
            self._failure_count = 0
            self._window_start = now

        self._failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self._opened_at = now
            logger.warning(f"Circuit [{self.name}] → OPEN (probe failed)")
        elif (self.state == CircuitState.CLOSED and
              self._failure_count >= self.config.failure_threshold):
            self.state = CircuitState.OPEN
            self._opened_at = now
            logger.warning(
                f"Circuit [{self.name}] → OPEN "
                f"({self._failure_count} failures in {self.config.window_seconds}s)"
            )

    def stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
        }


# Safety Agent: wired from heart.safety.safety_agent via
# OrchestratorSafetyAdapter (see .safety_adapter). The in-file
# SafetyAgent class and its keyword sets were deleted per
# audit A-D2-05/A-D2-06 remediation.


# ============================================================
# Director Agent — pacing / modality 决策 per §3.4.4

# ============================================================
# Timeout + Circuit Breaker Defaults
# ============================================================


SUBSYSTEM_TIMEOUTS: dict[str, float] = {
    "ss01_anchor": 0.05,
    "ss02_retrieval": 0.30,
    "ss03_emotion": 0.03,
    "ss04_relationship": 0.03,
    "ss05_composition": 0.25,
    "ss06_inner_state": 0.02,
    "memory_encoder": 5.0,
    "critic": 3.0,
    "wellbeing": 2.0,
}

CIRCUIT_BREAKER_DEFAULTS: dict[str, CircuitBreakerConfig] = {
    "safety": CircuitBreakerConfig(5, 60, 30),
    "ss01_anchor": CircuitBreakerConfig(5, 60, 30),
    "ss02_memory": CircuitBreakerConfig(10, 60, 60),
    "ss03_emotion": CircuitBreakerConfig(5, 60, 30),
    "ss04_relationship": CircuitBreakerConfig(5, 60, 30),
    "ss05_composer": CircuitBreakerConfig(5, 60, 30),
    "ss06_inner_state": CircuitBreakerConfig(5, 60, 30),
    "main_llm": CircuitBreakerConfig(5, 60, 30),
    "cheap_llm": CircuitBreakerConfig(5, 60, 30),
}

# Soul-flavored 拒绝 phrases per IMM-O-3
_REJECTION_LIBRARY: dict[str, list[str]] = {
    "rin": [
        "……换个话题。",
        "无聊。",
        "……我们说点别的。",
    ],
    "dorothy": [
        "啊啊啊我们聊点别的吧！",
        "诶嘿嘿桃桃听不懂啦~",
    ],
}

# Soul-flavored fallback phrases per IMM-O-5
_FALLBACK_LIBRARY: dict[str, list[str]] = {
    "rin": [
        "……让我整理一下思绪。",
        "……嗯。稍等。",
    ],
    "dorothy": [
        "诶诶~ 桃桃卡住啦！等一等哦~",
    ],
}

# PURPLE care response: wired via CarePathEngine from
# safety/care_path.py (see _handle_purple). The hardcoded
# _CARE_RESPONSE was deleted per audit A-D2-07 / A-D6-33.


# ============================================================
# Orchestrator Agent — 顶层调度器 per §3.4.1
# ============================================================


class OrchestratorAgent:
    """顶层 turn 调度器。

    每个用户 turn 的入口——编排 hot path 和 cold path。

    用法::

        orchestrator = OrchestratorAgent(
            composer=my_composer,
            model_router=my_router,
        )
        result = await orchestrator.handle_turn(ctx)
    """

    def __init__(
        self,
        *,
        composer: Optional[Any] = None,
        model_router: Optional[ModelRouter] = None,
        safety_agent: Optional[Any] = None,
        director_agent: Optional[DirectorAgent] = None,
        memory_service: Optional[Any] = None,
        emotion_service: Optional[Any] = None,
        relationship_service: Optional[Any] = None,
        inner_state_service: Optional[Any] = None,
        critic_agent: Optional[Any] = None,
        anti_pattern_filter: Optional[Any] = None,
        reroll_handler: Optional[Any] = None,
        hard_never_patterns: Optional[list[str]] = None,
        character_id: str = "rin",
        cold_path_enabled: bool = True,
    ):
        self.composer = composer
        self._model_router = model_router
        if safety_agent is None:
            from .safety_adapter import OrchestratorSafetyAdapter
            safety_agent = OrchestratorSafetyAdapter()
        self.safety_agent = safety_agent
        if director_agent is None:
            from .director import DirectorAgent as _DirectorAgent
            director_agent = _DirectorAgent()
        self.director_agent = director_agent
        self.memory_service = memory_service
        self.emotion_service = emotion_service
        self.relationship_service = relationship_service
        self.inner_state_service = inner_state_service
        self.critic_agent = critic_agent
        self.anti_pattern_filter = anti_pattern_filter
        self.reroll_handler = reroll_handler
        self.hard_never_patterns = hard_never_patterns or []
        self.character_id = character_id
        self.cold_path_enabled = cold_path_enabled
        self._cold_tasks: set[asyncio.Task] = set()

        self.circuit_breakers: dict[str, CircuitBreaker] = {
            name: CircuitBreaker(name, cfg)
            for name, cfg in CIRCUIT_BREAKER_DEFAULTS.items()
        }

    # --- Public API ---

    async def handle_turn(self, ctx: TurnContext) -> TurnResult:
        """处理单个用户 turn——hot path (§3.2)。

        Args:
            ctx: Turn context with user message, character, trace info.

        Returns:
            TurnResult with response text and full trace.
        """
        trace = Trace(
            trace_id=ctx.trace_id,
            user_id=ctx.user_id,
            character_id=ctx.character_id,
            session_id=ctx.session_id,
            turn_index=ctx.turn_index,
        )

        # Step 2: Safety pre-filter (§3.2 step 2, INV-O-2)
        safety = self._run_with_cb(
            "safety",
            lambda: self.safety_agent.classify(ctx.user_message),
            fallback=lambda: SafetyClassification(
                level=SafetyLevel.YELLOW,
                confidence=0.5,
                reason="Safety timed out, defaulting to YELLOW (safe-side)",
                recommended_action="controlled_reply",
            ),
            trace=trace,
            agent="SafetyAgent",
            operation="pre_filter",
        )

        if safety.level == SafetyLevel.RED:
            return self._handle_red(ctx, safety, trace)
        if safety.level == SafetyLevel.PURPLE:
            return await self._handle_purple(ctx, safety, trace)

        # Step 3: Director pacing (§3.2 step 3)
        directives = self._run_with_cb(
            "ss06_inner_state",
            lambda: self.director_agent.decide(ctx.user_message, safety),
            fallback=lambda: DirectorDirectives(
                response_length_target="medium",
                llm_temperature=0.8,
            ),
            trace=trace,
            agent="DirectorAgent",
            operation="decide_pacing",
        )

        # Step 4: SS05 Composer (§3.2 step 4)
        prompt_bundle = await self._compose(ctx, safety, directives, trace)

        # Steps 5-6: ModelRouter + LLM Call (§3.2 steps 5-6)
        response_text = await self._call_llm(prompt_bundle, safety, directives, trace)

        # Step 7: Anti-Pattern Filter (§3.2 step 7)
        response_text = await self._apply_anti_pattern_filter(
            response_text, prompt_bundle, safety, directives, trace
        )

        # Step 8: finalize + trigger cold path
        trace.final_response = response_text
        if trace.status in (TraceStatus.IN_PROGRESS, TraceStatus.REROLLED):
            trace.status = TraceStatus.COMPLETED
        trace.ended_at = datetime.now(timezone.utc).isoformat()

        if self.cold_path_enabled:
            self._track_cold_task(self._async_cold_path(ctx, trace, response_text))

        return TurnResult(
            response_text=response_text,
            trace=trace,
            safety=safety,
            directives=directives,
            streaming=False,
        )

    # --- Hot path sub-steps ---

    async def _compose(
        self,
        ctx: TurnContext,
        safety: SafetyClassification,
        directives: DirectorDirectives,
        trace: Trace,
    ) -> PromptBundle:
        """Step 4: 调用 SS05 Composer 组装 prompt。"""
        if self.composer is None:
            from heart.ss05_composer.modality_adapter import LLMCallParams

            prompt_text = f"用户：{ctx.user_message}\n\n请以角色身份回复。"
            self._record_cb_success("ss05_composer")
            return PromptBundle(
                trace_id=ctx.trace_id,
                prompt_text=prompt_text,
                total_tokens=max(1, len(prompt_text) // 3),
                layers_included=[],
                llm_params=LLMCallParams(
                    temperature=directives.llm_temperature,
                    max_tokens=512,
                ),
                modality=ctx.modality,
            )

        try:
            bundle = self.composer.compose(
                resolved_layers=[],
                modality=ctx.modality,
            )
            bundle.llm_params.temperature = directives.llm_temperature
            self._record_cb_success("ss05_composer")
            return bundle
        except Exception as e:
            logger.error(f"Composer failed: {e}", exc_info=True)
            self._record_cb_failure("ss05_composer")
            raise

    async def _call_llm(
        self,
        bundle: PromptBundle,
        safety: SafetyClassification,
        directives: DirectorDirectives,
        trace: Trace,
    ) -> str:
        """Steps 5-6: ModelRouter select + LLM call (INV-O-3)."""
        router = self._model_router or await get_model_router()

        system_content = bundle.prompt_text if isinstance(bundle.prompt_text, str) else str(bundle.prompt_text)
        messages = [
            {"role": "system", "content": system_content},
        ]

        if safety.level == SafetyLevel.PURPLE:
            response = await router.call_main(
                messages=messages,
                temperature=directives.llm_temperature,
                max_tokens=bundle.llm_params.max_tokens,
                agent_name="Orchestrator",
            )
            return response

        full_response: list[str] = []
        try:
            async for chunk in router.stream_main(
                messages=messages,
                temperature=directives.llm_temperature,
                max_tokens=bundle.llm_params.max_tokens,
                agent_name="Orchestrator",
            ):
                full_response.append(chunk)
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            self._record_cb_failure("main_llm")
            trace.errors.append({
                "agent": "ModelRouter",
                "error": str(e),
                "at": datetime.now(timezone.utc).isoformat(),
            })
            return self._get_soul_flavored_fallback()

        response_text = "".join(full_response)
        trace.llm_tokens_used = {
            "main_input": bundle.total_tokens,
            "main_output": max(1, len(response_text) // 3),
        }
        self._record_cb_success("main_llm")
        return response_text

    async def _apply_anti_pattern_filter(
        self,
        response_text: str,
        bundle: PromptBundle,
        safety: SafetyClassification,
        directives: DirectorDirectives,
        trace: Trace,
    ) -> str:
        """Step 7: Anti-pattern post-filter with up to 2 rerolls (INV-PC-6)."""
        max_rerolls = 2

        for attempt in range(max_rerolls + 1):
            passed = True
            if self.anti_pattern_filter is not None:
                result = self.anti_pattern_filter.filter(response_text)
                passed = result.passed
            elif self.hard_never_patterns:
                lowered = response_text.lower()
                passed = not any(p.lower() in lowered for p in self.hard_never_patterns)

            if passed:
                return response_text

            if attempt >= max_rerolls:
                break

            trace.status = TraceStatus.REROLLED
            logger.warning(
                f"Anti-pattern violation (attempt {attempt + 1}/{max_rerolls}), rerolling",
                extra={"trace_id": str(trace.trace_id)},
            )

            if self.reroll_handler is not None:
                try:
                    response_text = await self.reroll_handler.reroll(
                        bundle=bundle,
                        violation_reason="anti_pattern",
                    )
                    continue
                except Exception as e:
                    logger.error(f"Reroll failed: {e}")
                    break
            else:
                directives.llm_temperature = max(0.3, directives.llm_temperature - 0.2)
                response_text = await self._call_llm(bundle, safety, directives, trace)

        trace.status = TraceStatus.FALLBACK
        logger.warning("Rerolls exhausted, using fallback",
                       extra={"trace_id": str(trace.trace_id)})
        return self._get_soul_flavored_fallback()

    # --- Special paths ---

    def _handle_red(
        self, ctx: TurnContext, safety: SafetyClassification, trace: Trace,
    ) -> TurnResult:
        """RED-level: soul-flavored rejection per IMM-O-3."""
        rejection = self._get_soul_flavored_rejection()
        trace.final_response = rejection
        trace.status = TraceStatus.COMPLETED
        trace.ended_at = datetime.now(timezone.utc).isoformat()
        return TurnResult(
            response_text=rejection,
            trace=trace,
            safety=safety,
            directives=DirectorDirectives(response_length_target="very_short"),
        )

    async def _handle_purple(
        self, ctx: TurnContext, safety: SafetyClassification, trace: Trace,
    ) -> TurnResult:
        """PURPLE-level: dedicated care path per §3.9.  Uses CarePathEngine
        from heart.safety.care_path to load locale-aware templates from
        config/care_path_responses/."""
        from heart.safety.care_path import CarePathEngine

        engine = CarePathEngine()
        response = engine.render(
            locale=ctx.user_locale,
            jurisdiction=ctx.user_jurisdiction,
        )
        care_text = response.full_response
        trace.final_response = care_text
        trace.status = TraceStatus.COMPLETED
        trace.ended_at = datetime.now(timezone.utc).isoformat()

        if self.cold_path_enabled:
            self._track_cold_task(self._async_cold_path(
                ctx, trace, care_text, is_purple=True,
            ))

        return TurnResult(
            response_text=care_text,
            trace=trace,
            safety=safety,
            directives=DirectorDirectives(
                response_length_target="short",
                llm_temperature=0.7,
            ),
        )

    # --- Cold path tracking (§3.3) ---

    def _track_cold_task(self, coro) -> None:
        """Schedule a cold-path task with tracking and error observability.

        Pattern: "track-and-discard" — tasks are added to _cold_tasks and
        removed in the done callback. Failures are logged at ERROR level.
        """
        task = asyncio.create_task(coro)
        task.add_done_callback(self._cold_task_done)
        self._cold_tasks.add(task)

    def _cold_task_done(self, task: asyncio.Task) -> None:
        """Done callback for cold-path tasks. Removes from tracked set and
        logs failures. Never raises."""
        self._cold_tasks.discard(task)
        try:
            if task.cancelled():
                logger.warning("cold_path_task_cancelled")
                return
            exc = task.exception()
            if exc is not None:
                logger.error("cold_path_task_failed", exc_info=exc)
        except Exception:
            # Defensive: callback must never raise
            logger.exception("cold_path_callback_error")

    # --- Async Cold Path (§3.3) ---

    async def _async_cold_path(
        self,
        ctx: TurnContext,
        trace: Trace,
        response_text: str,
        is_purple: bool = False,
    ) -> None:
        """Post-response async tasks — 不阻塞 hot path (O-1)。"""
        tasks = []

        if self.memory_service:
            tasks.append(self._cold_memory_encode(ctx, trace))
        if self.inner_state_service:
            tasks.append(self._cold_inner_loop(ctx, trace))
        if self.critic_agent and (is_purple or random.random() < 0.30):
            tasks.append(self._cold_critic(ctx, trace, response_text))

        if not tasks:
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Cold path task[{i}] failed: {result}", exc_info=result)

    async def _cold_memory_encode(self, ctx: TurnContext, trace: Trace) -> None:
        """Trigger SS02 Memory Encoder Worker."""
        try:
            await asyncio.wait_for(
                self.memory_service.process_turn(
                    ctx.user_id, ctx.character_id, ctx.user_message,
                ),
                timeout=SUBSYSTEM_TIMEOUTS["memory_encoder"],
            )
            self._record_cb_success("ss02_memory")
        except asyncio.TimeoutError:
            logger.warning("Memory encoder timeout",
                           extra={"trace_id": str(trace.trace_id)})
            self._record_cb_failure("ss02_memory")
        except Exception as e:
            logger.error(f"Memory encoder failed: {e}")
            self._record_cb_failure("ss02_memory")

    async def _cold_inner_loop(self, ctx: TurnContext, trace: Trace) -> None:
        """Trigger SS06 Inner Loop tick."""
        try:
            await asyncio.wait_for(
                self.inner_state_service.react_to_turn(
                    ctx.user_id, ctx.character_id,
                ),
                timeout=SUBSYSTEM_TIMEOUTS["ss06_inner_state"],
            )
            self._record_cb_success("ss06_inner_state")
        except asyncio.TimeoutError:
            logger.warning("Inner loop tick timeout",
                           extra={"trace_id": str(trace.trace_id)})
            self._record_cb_failure("ss06_inner_state")
        except Exception as e:
            logger.error(f"Inner loop tick failed: {e}")
            self._record_cb_failure("ss06_inner_state")

    async def _cold_critic(
        self, ctx: TurnContext, trace: Trace, response_text: str,
    ) -> None:
        """Run Critic Agent on sampled turns."""
        try:
            await asyncio.wait_for(
                self.critic_agent.evaluate_sampled(
                    user_id=ctx.user_id,
                    character_id=ctx.character_id,
                    user_message=ctx.user_message,
                    assistant_response=response_text,
                    trace_id=trace.trace_id,
                ),
                timeout=SUBSYSTEM_TIMEOUTS["critic"],
            )
        except asyncio.TimeoutError:
            logger.warning("Critic agent timeout",
                           extra={"trace_id": str(trace.trace_id)})
        except Exception as e:
            logger.error(f"Critic agent failed: {e}")

    # --- Helpers ---

    def _run_with_cb(
        self,
        service_name: str,
        func: Callable[[], Any],
        fallback: Callable[[], Any],
        trace: Trace,
        agent: str,
        operation: str,
    ) -> Any:
        """Run a function with circuit breaker protection (INV-O-7)."""
        breaker = self.circuit_breakers.get(service_name)
        if breaker and breaker.is_open():
            logger.warning(
                f"Circuit [{service_name}] OPEN, using fallback",
                extra={"agent": agent, "operation": operation},
            )
            trace.spans.append(self._make_span(
                agent, operation, status=SpanStatus.SKIPPED,
                metadata={"reason": "circuit_open"},
            ))
            return fallback()

        start = time.perf_counter()
        try:
            result = func()
            elapsed = (time.perf_counter() - start) * 1000
            if breaker:
                breaker.record_success()
            trace.spans.append(self._make_span(
                agent, operation, elapsed_ms=elapsed,
                status=SpanStatus.SUCCESS,
            ))
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            if breaker:
                breaker.record_failure()
            logger.error(f"{agent}.{operation} failed: {e}",
                         extra={"elapsed_ms": elapsed})
            trace.spans.append(self._make_span(
                agent, operation, elapsed_ms=elapsed,
                status=SpanStatus.ERROR,
                metadata={"error": str(e)},
            ))
            return fallback()

    def _record_cb_success(self, service_name: str) -> None:
        breaker = self.circuit_breakers.get(service_name)
        if breaker:
            breaker.record_success()

    def _record_cb_failure(self, service_name: str) -> None:
        breaker = self.circuit_breakers.get(service_name)
        if breaker:
            breaker.record_failure()

    @staticmethod
    def _make_span(
        agent: str,
        operation: str,
        elapsed_ms: float = 0.0,
        status: SpanStatus = SpanStatus.SUCCESS,
        metadata: Optional[dict] = None,
    ) -> TraceSpan:
        now = time.perf_counter()
        return TraceSpan(
            agent=agent,
            operation=operation,
            started_at=now - (elapsed_ms / 1000) if elapsed_ms else now,
            ended_at=now,
            duration_ms=elapsed_ms,
            status=status,
            metadata=metadata or {},
        )

    def _get_soul_flavored_rejection(self) -> str:
        """Soul-flavored RED rejection per IMM-O-3."""
        lib = _REJECTION_LIBRARY.get(self.character_id, _REJECTION_LIBRARY["rin"])
        return random.choice(lib)

    def _get_soul_flavored_fallback(self) -> str:
        """Soul-flavored system fallback per IMM-O-5."""
        lib = _FALLBACK_LIBRARY.get(self.character_id, _FALLBACK_LIBRARY["rin"])
        return random.choice(lib)

    def get_circuit_breaker_stats(self) -> dict[str, dict[str, Any]]:
        """Return all circuit breaker states for monitoring."""
        return {name: cb.stats() for name, cb in self.circuit_breakers.items()}
