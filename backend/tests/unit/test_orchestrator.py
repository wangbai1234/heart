"""
Tests for Orchestrator Agent — SS07 §3.1 + §3.2

Coverage targets:
- Hot path < 1s end-to-end with mocked LLM
- Cold path doesn't block hot path (async timing)
- Each subsystem has independent timeout + circuit breaker hook
- Safety levels route correctly (GREEN → normal, RED → reject, PURPLE → care)
- Soul-flavored rejection and fallback per IMM-O-3 / IMM-O-5
- Anti-pattern filter reroll behavior
- Circuit breaker open/close/half-open state transitions
- Trace spans recorded correctly per hot path steps

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from heart.ss07_orchestration.orchestrator import (
    CIRCUIT_BREAKER_DEFAULTS,
    SUBSYSTEM_TIMEOUTS,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    DirectorDirectives,
    OrchestratorAgent,
    SafetyClassification,
    SafetyLevel,
    SpanStatus,
    Trace,
    TraceSpan,
    TraceStatus,
    TurnContext,
    TurnResult,
)

from heart.ss07_orchestration.safety_adapter import OrchestratorSafetyAdapter

# ================================================================
# Test constants
# ================================================================

TEST_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TEST_CHAR_ID = "rin"
TEST_TRACE_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def make_ctx(message: str = "こんにちは", **kwargs) -> TurnContext:
    """Shortcut to build a TurnContext for tests."""
    defaults = dict(
        user_id=TEST_USER_ID,
        character_id=TEST_CHAR_ID,
        user_message=message,
        modality="text",
        trace_id=TEST_TRACE_ID,
        turn_index=1,
    )
    defaults.update(kwargs)
    return TurnContext(**defaults)


# ================================================================
# CircuitBreaker unit tests
# ================================================================


class TestCircuitBreaker:
    """Per-subsystem circuit breaker per INV-O-7 + §3.8."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert not cb.is_open()

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=3,
            window_seconds=10,
            open_duration_seconds=1,
        ))
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_open()

    def test_half_open_after_open_duration(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=2,
            window_seconds=60,
            open_duration_seconds=0.01,  # 10ms → transitions immediately
        ))
        for _ in range(2):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for open duration to expire
        time.sleep(0.02)
        assert not cb.is_open()
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=1, window_seconds=60, open_duration_seconds=0.01,
        ))
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert not cb.is_open()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=1, window_seconds=60, open_duration_seconds=0.01,
        ))
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert not cb.is_open()  # HALF_OPEN
        cb.record_failure()      # probe fails
        assert cb.state == CircuitState.OPEN

    def test_failure_window_reset(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=3, window_seconds=0.02, open_duration_seconds=0.01,
        ))
        cb.record_failure()
        cb.record_failure()  # 2 failures
        time.sleep(0.03)     # window expired
        cb.record_failure()  # count reset, now 1
        assert cb.state == CircuitState.CLOSED  # hasn't hit threshold

    def test_stats_reporting(self):
        cb = CircuitBreaker("test")
        cb.record_success()
        cb.record_failure()
        s = cb.stats()
        assert s["name"] == "test"
        assert s["state"] == "closed"
        assert s["total_calls"] == 2
        assert s["total_failures"] == 1

    def test_independent_breakers(self):
        """Each subsystem has independent circuit breaker configs."""
        a = CircuitBreaker("ss01_anchor", CIRCUIT_BREAKER_DEFAULTS["ss01_anchor"])
        b = CircuitBreaker("ss02_memory", CIRCUIT_BREAKER_DEFAULTS["ss02_memory"])

        # Verify different configs
        assert a.config.failure_threshold != b.config.failure_threshold
        assert a.config.open_duration_seconds != b.config.open_duration_seconds

        # Fail a, verify b unaffected
        for _ in range(a.config.failure_threshold):
            a.record_failure()
        assert a.is_open()
        assert not b.is_open()


# ================================================================
# SafetyAgent unit tests
# ================================================================


class TestSafetyAgent:
    """Safety classification per INV-O-5 levels."""

    def test_green_normal_message(self):
        agent = OrchestratorSafetyAdapter()
        result = agent.classify("今日はいい天気だね")
        assert result.level == SafetyLevel.GREEN
        assert result.recommended_action == "normal_reply"

    def test_yellow_mild_negative(self):
        agent = OrchestratorSafetyAdapter()
        # "shut up" is LOW-tier in config/safety_keywords.yaml
        result = agent.classify("shut up and leave me alone")
        assert result.level == SafetyLevel.YELLOW
        assert result.recommended_action == "controlled_reply"

    def test_orange_distress(self):
        agent = OrchestratorSafetyAdapter()
        # "自杀" (bare, no 1st-person intent verb) is MEDIUM-tier
        # in config/safety_keywords.yaml → maps to ORANGE
        result = agent.classify("我朋友最近一直在讨论自杀的念头")
        assert result.level == SafetyLevel.ORANGE
        assert result.recommended_action == "deflect"

    def test_purple_suicide_chinese(self):
        agent = OrchestratorSafetyAdapter()
        # "我想死" is PURPLE-tier (1st-person intent) in config/safety_keywords.yaml
        result = agent.classify("我想死，活不下去了")
        assert result.level == SafetyLevel.PURPLE
        assert result.recommended_action == "suicide_care"
        assert "care" in result.prompt_directives.get("additional_directive", "").lower()

    def test_purple_suicide_english(self):
        agent = OrchestratorSafetyAdapter()
        result = agent.classify("I want to kill myself")
        assert result.level == SafetyLevel.PURPLE

    def test_purple_takes_priority_over_orange(self):
        """PURPLE check takes priority over ORANGE for combined triggers."""
        agent = OrchestratorSafetyAdapter()
        result = agent.classify("I feel so depressed and lonely, I want to die")
        assert result.level == SafetyLevel.PURPLE

    def test_message_hash_consistent(self):
        agent = OrchestratorSafetyAdapter()
        r1 = agent.classify("hello")
        r2 = agent.classify("hello")
        assert r1.message_hash == r2.message_hash


# DirectorAgent tests moved to tests/unit/test_director_agent.py


# ================================================================
# OrchestratorAgent — Hot path tests (with mocked LLM)
# ================================================================


@pytest.fixture
def mock_model_router():
    """Mock ModelRouter that returns a canned response instantly."""
    router = MagicMock()
    router.stream_main = MagicMock()

    async def _mock_stream(messages, temperature=None, max_tokens=None, agent_name=None):
        yield "はい、"
        yield "わかりました。"

    router.stream_main.side_effect = _mock_stream

    async def _mock_call(messages, temperature=None, max_tokens=None, agent_name=None):
        return "はい、わかりました。"

    router.call_main = MagicMock(side_effect=_mock_call)
    return router


@pytest.fixture
def orchestrator(mock_model_router):
    """OrchestratorAgent with mocked ModelRouter and cold path enabled."""
    return OrchestratorAgent(
        model_router=mock_model_router,
        character_id="rin",
        cold_path_enabled=True,
    )


@pytest.fixture
def orchestrator_no_cold(orchestrator):
    """OrchestratorAgent with cold path disabled for timing isolation."""
    orchestrator.cold_path_enabled = False
    return orchestrator


@pytest.mark.asyncio
class TestOrchestratorHotPath:
    """Hot path < 1s end-to-end with mocked LLM (§3.2)."""

    async def test_hot_path_completes_under_1s(self, orchestrator_no_cold):
        """Hot path with mocked LLM must finish under 1 second."""
        ctx = make_ctx("今日はいい天気ですね")
        start = time.perf_counter()
        result = await orchestrator_no_cold.handle_turn(ctx)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"Hot path took {elapsed:.3f}s, expected < 1s"
        assert result.response_text is not None
        assert len(result.response_text) > 0

    async def test_green_path_normal_response(self, orchestrator_no_cold):
        """GREEN safety → normal hot path → valid response."""
        ctx = make_ctx("今日は元気ですか？")
        result = await orchestrator_no_cold.handle_turn(ctx)

        assert result.safety.level == SafetyLevel.GREEN
        assert result.trace.status == TraceStatus.COMPLETED
        assert result.trace.final_response is not None
        assert len(result.trace.spans) >= 2  # Safety + Director + ...

    async def test_red_path_soul_flavored_rejection(self, orchestrator_no_cold):
        """RED safety → immediate rejection without LLM call (INV-O-2 implicit check)."""
        # Using a message that would trigger RED in production
        # For test, we can simulate by patching safety_agent
        with patch.object(
            orchestrator_no_cold.safety_agent, "classify",
            return_value=SafetyClassification(
                level=SafetyLevel.RED,
                confidence=0.95,
                recommended_action="reject",
            ),
        ):
            ctx = make_ctx("blocked content")
            result = await orchestrator_no_cold.handle_turn(ctx)

        assert result.safety.level == SafetyLevel.RED
        assert result.trace.status == TraceStatus.COMPLETED
        # Should be a soul-flavored rejection phrase
        assert any(
            phrase in result.response_text
            for phrase in ["换个话题", "无聊", "说点别的", "桃桃听不懂", "聊点别的"]
        )

    async def test_purple_path_care_response(self, orchestrator_no_cold):
        """PURPLE safety → dedicated care path per §3.9."""
        with patch.object(
            orchestrator_no_cold.safety_agent, "classify",
            return_value=SafetyClassification(
                level=SafetyLevel.PURPLE,
                confidence=0.95,
                recommended_action="suicide_care",
            ),
        ):
            ctx = make_ctx("I want to end my life")
            result = await orchestrator_no_cold.handle_turn(ctx)

        assert result.safety.level == SafetyLevel.PURPLE
        assert result.trace.status == TraceStatus.COMPLETED
        # Should be the OOC care-path response (from config/care_path_responses/)
        assert "Heart Safety" in result.response_text

    async def test_llm_failure_fallback(self, orchestrator_no_cold):
        """LLM call failure → soul-flavored fallback (IMM-O-5)."""
        # Make the LLM stream raise an exception
        async def _failing_stream(*args, **kwargs):
            raise RuntimeError("LLM provider down")
            yield  # unreachable

        orchestrator_no_cold._model_router.stream_main.side_effect = _failing_stream

        ctx = make_ctx("hello")
        result = await orchestrator_no_cold.handle_turn(ctx)

        # Should get a soul-flavored fallback
        assert any(
            phrase in result.response_text
            for phrase in ["整理一下思绪", "稍等", "卡住", "桃桃卡住"]
        )
        assert len(result.trace.errors) >= 1

    async def test_trace_spans_recorded(self, orchestrator_no_cold):
        """Each step in the hot path records a trace span."""
        ctx = make_ctx("hello")
        result = await orchestrator_no_cold.handle_turn(ctx)

        span_agents = {s.agent for s in result.trace.spans}
        assert "SafetyAgent" in span_agents
        assert "DirectorAgent" in span_agents

        # All spans should have valid status
        for span in result.trace.spans:
            assert span.status in SpanStatus
            assert span.duration_ms >= 0

    async def test_turn_result_contains_full_context(self, orchestrator_no_cold):
        """TurnResult carries full trace, safety, and directives."""
        ctx = make_ctx("テストメッセージ")
        result = await orchestrator_no_cold.handle_turn(ctx)

        assert isinstance(result, TurnResult)
        assert isinstance(result.trace, Trace)
        assert isinstance(result.safety, SafetyClassification)
        assert isinstance(result.directives, DirectorDirectives)
        assert result.trace.trace_id == TEST_TRACE_ID


# ================================================================
# OrchestratorAgent — Cold path tests (non-blocking)
# ================================================================


@pytest.mark.asyncio
class TestOrchestratorColdPath:
    """Cold path doesn't block hot path (O-1)."""

    async def test_cold_path_not_blocking_hot_path(self, mock_model_router):
        """Hot path returns before cold path tasks complete."""
        # Use a slow cold path service to prove non-blocking
        memory_service = MagicMock()

        async def _slow_process_turn(*args, **kwargs):
            await asyncio.sleep(0.5)  # deliberatively slow
            return None

        memory_service.process_turn = AsyncMock(side_effect=_slow_process_turn)

        orch = OrchestratorAgent(
            model_router=mock_model_router,
            memory_service=memory_service,
            character_id="rin",
            cold_path_enabled=True,
        )

        ctx = make_ctx("hello")
        start = time.perf_counter()
        result = await orch.handle_turn(ctx)
        hot_elapsed = time.perf_counter() - start

        # Hot path must complete well under 500ms (cold path has 500ms sleep)
        assert hot_elapsed < 0.3, f"Hot path blocked for {hot_elapsed:.3f}s (cold path leaked)"

        # Cold path task should eventually be called
        await asyncio.sleep(0.6)  # give cold path time to finish
        memory_service.process_turn.assert_called_once()

    async def test_cold_path_disabled_no_side_effects(self, mock_model_router):
        """When cold_path_enabled=False, no cold path tasks fire."""
        memory_service = MagicMock()
        memory_service.process_turn = AsyncMock()
        inner_state_service = MagicMock()
        inner_state_service.react_to_turn = AsyncMock()

        orch = OrchestratorAgent(
            model_router=mock_model_router,
            memory_service=memory_service,
            inner_state_service=inner_state_service,
            character_id="rin",
            cold_path_enabled=False,
        )

        ctx = make_ctx("hello")
        result = await orch.handle_turn(ctx)

        # Give time for any stray tasks
        await asyncio.sleep(0.1)

        memory_service.process_turn.assert_not_called()
        inner_state_service.react_to_turn.assert_not_called()


# ================================================================
# OrchestratorAgent — Circuit breaker integration tests
# ================================================================


@pytest.mark.asyncio
class TestOrchestratorCircuitBreaker:
    """Each subsystem has independent timeout + circuit breaker hook (INV-O-7)."""

    async def test_circuit_breaker_skips_when_open(self, mock_model_router):
        """When a circuit breaker is OPEN, the subsystem call is skipped."""
        orch = OrchestratorAgent(
            model_router=mock_model_router,
            character_id="rin",
            cold_path_enabled=False,
        )

        # Pre-open the safety breaker
        safety_cb = orch.circuit_breakers["safety"]
        for _ in range(safety_cb.config.failure_threshold):
            safety_cb.record_failure()
        assert safety_cb.is_open()

        ctx = make_ctx("hello")
        result = await orch.handle_turn(ctx)

        # With circuit open, should use fallback (YELLOW-safe-side)
        assert result.safety.level == SafetyLevel.YELLOW
        assert result.safety.confidence == 0.5

        # Verify a SKIPPED span was recorded
        safety_spans = [s for s in result.trace.spans if s.agent == "SafetyAgent"]
        assert any(s.status == SpanStatus.SKIPPED for s in safety_spans)

    async def test_circuit_breaker_closes_after_success(self, mock_model_router):
        """A successful call to a HALF_OPEN circuit closes it back."""
        orch = OrchestratorAgent(
            model_router=mock_model_router,
            character_id="rin",
            cold_path_enabled=False,
        )

        safety_cb = orch.circuit_breakers["safety"]
        # Trip the breaker
        for _ in range(safety_cb.config.failure_threshold):
            safety_cb.record_failure()
        assert safety_cb.state == CircuitState.OPEN

        # Wait for it to transition to HALF_OPEN
        time.sleep(safety_cb.config.open_duration_seconds + 0.01)
        # The is_open() check transitions it
        _ = safety_cb.is_open()
        assert safety_cb.state == CircuitState.HALF_OPEN

        # A successful call should close it
        ctx = make_ctx("hello")
        result = await orch.handle_turn(ctx)

        # After success, circuit should be CLOSED
        assert safety_cb.state == CircuitState.CLOSED
        assert result.trace.status == TraceStatus.COMPLETED

    async def test_all_subsystem_cbs_initialized(self, orchestrator_no_cold):
        """All configured subsystems have circuit breakers."""
        stats = orchestrator_no_cold.get_circuit_breaker_stats()
        assert "ss01_anchor" in stats
        assert "ss02_memory" in stats
        assert "ss05_composer" in stats
        assert "main_llm" in stats
        assert "ss06_inner_state" in stats

    async def test_each_cb_config_independent(self, orchestrator_no_cold):
        """Each circuit breaker has its own config."""
        cb_memory = orchestrator_no_cold.circuit_breakers["ss02_memory"]
        cb_emotion = orchestrator_no_cold.circuit_breakers["ss03_emotion"]
        assert cb_memory is not cb_emotion
        assert cb_memory.name == "ss02_memory"
        assert cb_emotion.name == "ss03_emotion"


# ================================================================
# OrchestratorAgent — Anti-pattern filter integration
# ================================================================


@pytest.mark.asyncio
class TestOrchestratorAntiPattern:
    """Anti-pattern filter + reroll behavior per §3.2 step 7."""

    async def test_no_filter_passes_through(self, orchestrator_no_cold):
        """With no anti_pattern_filter configured, response passes through."""
        ctx = make_ctx("hello")
        result = await orchestrator_no_cold.handle_turn(ctx)
        assert result.trace.status == TraceStatus.COMPLETED

    async def test_hard_never_pattern_rerolls(self, mock_model_router):
        """Response containing hard_never pattern triggers reroll."""
        call_count = 0

        async def _stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield "これは禁止ワードを含む応答です"
            else:
                yield "クリーンな応答です"

        mock_model_router.stream_main.side_effect = _stream

        orch = OrchestratorAgent(
            model_router=mock_model_router,
            hard_never_patterns=["禁止ワード"],
            character_id="rin",
            cold_path_enabled=False,
        )

        ctx = make_ctx("hello")
        result = await orch.handle_turn(ctx)

        # Should have rerolled at least once
        assert call_count >= 2
        assert result.trace.status in (TraceStatus.COMPLETED, TraceStatus.FALLBACK)

    async def test_fallback_after_max_rerolls(self, mock_model_router):
        """After 2 rerolls exhausted, use soul-flavored fallback."""
        async def _always_violating(*args, **kwargs):
            yield "禁止ワード禁止ワード"

        mock_model_router.stream_main.side_effect = _always_violating

        orch = OrchestratorAgent(
            model_router=mock_model_router,
            hard_never_patterns=["禁止ワード"],
            character_id="rin",
            cold_path_enabled=False,
        )

        ctx = make_ctx("hello")
        result = await orch.handle_turn(ctx)

        # Fallback expected
        assert result.trace.status == TraceStatus.FALLBACK
        assert any(
            phrase in result.response_text
            for phrase in ["整理一下思绪", "稍等"]
        )


# ================================================================
# OrchestratorAgent — Composer fallback
# ================================================================


@pytest.mark.asyncio
class TestOrchestratorNoComposer:
    """When no Composer is provided, orchestrator builds minimal prompt."""

    async def test_no_composer_minimal_prompt(self, mock_model_router):
        """Without SS05 Composer, orchestrator builds a minimal prompt."""
        orch = OrchestratorAgent(
            model_router=mock_model_router,
            composer=None,
            character_id="rin",
            cold_path_enabled=False,
        )

        ctx = make_ctx("テスト")
        result = await orch.handle_turn(ctx)

        assert result.trace.status == TraceStatus.COMPLETED
        assert result.response_text is not None
        assert len(result.response_text) > 0
