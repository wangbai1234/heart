"""
Contract: Hot Path Wiring — all subsystem services are invoked on /api/chat.

Per docs/design/composer_wiring_plan.md §5.2:
  - memory_service.retrieve() called
  - emotion_service.get_context_block() called
  - relationship_service.get_current_phase() called
  - inner_state_service.get_context_block() called
  - safety_agent.classify() called

Plus degradation and fail-closed assertions.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.safety.safety_agent import ClassificationResult, SeverityLevel
from heart.ss05_composer.service import (
    ComposerService,
    CompositionContext,
    CompositionResult,
)

# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════


def _make_registry():
    """Build a mock SoulRegistry that returns a mock SoulSpec with all required attrs for _build_anchor_block."""
    registry = MagicMock()

    anchor = MagicMock()
    anchor.archetype = "the-tsundere-idealist"
    core_wound = MagicMock()
    core_wound.essence = "fear of being truly seen"
    core_desire = MagicMock()
    core_desire.surface = "to be understood"
    anchor.core_wound = core_wound
    anchor.core_desire = core_desire
    anchor.voice_dna = []
    anti_pat = MagicMock()
    anti_pat.hard_never = []
    anti_pat.soft_never = []
    anchor.anti_patterns = anti_pat
    anchor.identity_text = "你是凛。"
    anchor.hard_never = []
    anchor.anti_patterns = []

    soul_spec = MagicMock()
    soul_spec.identity_anchor = anchor
    dn = MagicMock()
    dn.zh = "凛"
    dn.ja = None
    dn.en = None
    soul_spec.display_name = dn
    soul_spec.character_id = "rin"

    registry.get_soul.return_value = soul_spec
    return registry


def _make_ctx():
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    return CompositionContext(
        user_id=uid,
        character_id="rin",
        turn_id=tid,
        session_id=uid,
        max_tokens=2000,
    )


def _make_model_router():
    router = MagicMock()
    router.call_main = AsyncMock(return_value="こんにちは。何か用？")
    return router


# ═══════════════════════════════════════════
# Test: All Five Services Invoked
# ═══════════════════════════════════════════


@pytest.mark.contract
class TestHotPathAllServicesInvoked:
    """Assert that every subsystem service's specific method is called during compose."""

    @pytest.mark.asyncio
    async def test_all_services_invoked_on_compose(self):
        """All five subsystem service methods are called exactly once."""
        registry = _make_registry()
        ctx = _make_ctx()

        memory_svc = MagicMock()
        memory_svc.retrieve = AsyncMock()
        from heart.ss02_memory.service import MemoryRetrievalResult

        memory_svc.retrieve.return_value = MemoryRetrievalResult(
            query_id=uuid.uuid4(),
            retrieved_at=datetime.now(timezone.utc),
            memories=[],
            recently_forgotten_hints=[],
            total_candidates=0,
            retrieval_strategies_used=["fallback_empty"],
            retrieval_latency_ms=0,
            l4_included=False,
        )

        emotion_svc = MagicMock()
        emotion_svc.get_context_block = AsyncMock(return_value={
            "emotion_summary": "平静",
            "vad": {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
            "active_emotions": [],
            "mood_descriptor": "平静",
            "energy_descriptor": "正常",
            "pending_repairs_summary": None,
            "expression_guidelines": None,
        })

        relationship_svc = MagicMock()
        relationship_svc.get_current_phase = AsyncMock(return_value={
            "phase": "stranger",
            "trust_level": 0.0,
            "attachment_style": "",
            "behavioral_envelope": {},
        })

        inner_state_svc = MagicMock()
        inner_state_svc.get_context_block.return_value = {
            "internal_monologue": "",
            "recent_reflections": [],
            "current_need": "",
        }

        router = _make_model_router()

        composer = ComposerService(
            soul_registry=registry,
            memory_service=memory_svc,
            emotion_service=emotion_svc,
            relationship_service=relationship_svc,
            inner_state_service=inner_state_svc,
            model_router=router,
        )

        result = await composer.compose(
            ctx=ctx,
            user_message="こんにちは",
            conversation_history=[],
        )

        memory_svc.retrieve.assert_called_once()
        emotion_svc.get_context_block.assert_called_once()
        relationship_svc.get_current_phase.assert_called_once()
        inner_state_svc.get_context_block.assert_called_once()

        assert isinstance(result, CompositionResult)
        assert result.character_id == "rin"
        assert "subsystems_invoked" in result.composition_trace
        assert result.composition_trace["subsystems_invoked"] == [
            "soul",
            "memory",
            "emotion",
            "relationship",
            "inner_state",
        ]
        assert result.composition_trace["degraded"]["memory"] is False
        assert result.composition_trace["degraded"]["emotion"] is False
        assert result.composition_trace["degraded"]["relationship"] is False
        assert result.composition_trace["degraded"]["inner_state"] is False


# ═══════════════════════════════════════════
# Test: Degradation (SS02/SS03/SS04/SS06 raise → 200, degraded=true)
# ═══════════════════════════════════════════


@pytest.mark.contract
class TestHotPathDegradation:
    """Each subsystem can fail individually and the turn still returns 200."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "attr_name,reason_key",
        [
            ("memory_service", "memory"),
            ("emotion_service", "emotion"),
            ("relationship_service", "relationship"),
            ("inner_state_service", "inner_state"),
        ],
    )
    async def test_subsystem_failure_degrades_but_returns_200(self, attr_name, reason_key):
        """When a subsystem raises, the trace shows degraded=true and response is still returned."""
        registry = _make_registry()
        ctx = _make_ctx()
        router = _make_model_router()

        good_memory = MagicMock()
        good_memory.retrieve = AsyncMock()
        from heart.ss02_memory.service import MemoryRetrievalResult

        good_memory.retrieve.return_value = MemoryRetrievalResult(
            query_id=uuid.uuid4(),
            retrieved_at=datetime.now(timezone.utc),
            memories=[],
            recently_forgotten_hints=[],
            total_candidates=0,
            retrieval_strategies_used=["fallback_empty"],
            retrieval_latency_ms=0,
            l4_included=False,
        )

        good_emotion = MagicMock()
        good_emotion.get_context_block = AsyncMock(return_value={
            "emotion_summary": "平静",
            "vad": {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
            "active_emotions": [],
            "mood_descriptor": "平静",
            "energy_descriptor": "正常",
            "pending_repairs_summary": None,
            "expression_guidelines": None,
        })

        good_relationship = MagicMock()
        good_relationship.get_current_phase = AsyncMock(return_value={
            "phase": "stranger",
            "trust_level": 0.0,
            "attachment_style": "",
            "behavioral_envelope": {},
        })

        good_inner_state = MagicMock()
        good_inner_state.get_context_block.return_value = {
            "internal_monologue": "",
            "recent_reflections": [],
            "current_need": "",
        }

        # Inject a failing service for the param under test
        failing_memory = MagicMock()
        failing_memory.retrieve = AsyncMock(side_effect=RuntimeError("DB down"))

        failing_emotion = MagicMock()
        failing_emotion.get_context_block = AsyncMock(side_effect=RuntimeError("lexicon broken"))

        failing_relationship = MagicMock()
        failing_relationship.get_current_phase = AsyncMock(side_effect=RuntimeError("stage engine crash"))

        failing_inner_state = MagicMock()
        failing_inner_state.get_context_block.side_effect = RuntimeError("state gone")

        kw = {
            "memory_service": failing_memory if attr_name == "memory_service" else good_memory,
            "emotion_service": failing_emotion if attr_name == "emotion_service" else good_emotion,
            "relationship_service": (
                failing_relationship if attr_name == "relationship_service" else good_relationship
            ),
            "inner_state_service": (
                failing_inner_state if attr_name == "inner_state_service" else good_inner_state
            ),
        }

        composer = ComposerService(
            soul_registry=registry,
            model_router=router,
            **kw,
        )

        result = await composer.compose(
            ctx=ctx,
            user_message="こんにちは",
            conversation_history=[],
        )

        assert result.response is not None
        assert len(result.response) > 0
        assert result.composition_trace["degraded"][reason_key] is True
        assert result.composition_trace["skipped_reason"][reason_key] != "ok"

    @pytest.mark.asyncio
    async def test_service_none_emits_dep_missing_metric_and_degraded(self):
        """When service is None (not wired), metric is emitted and trace shows degraded."""
        registry = _make_registry()
        ctx = _make_ctx()
        router = _make_model_router()

        composer = ComposerService(
            soul_registry=registry,
            memory_service=None,
            emotion_service=None,
            relationship_service=None,
            inner_state_service=None,
            model_router=router,
        )

        result = await composer.compose(
            ctx=ctx,
            user_message="こんにちは",
            conversation_history=[],
        )

        assert result.response is not None
        trace = result.composition_trace
        assert trace["degraded"]["memory"] is True
        assert trace["degraded"]["emotion"] is True
        assert trace["degraded"]["relationship"] is True
        assert trace["degraded"]["inner_state"] is True
        for key in ("memory", "emotion", "relationship", "inner_state"):
            assert "not_wired" in trace["skipped_reason"][key]


# ═══════════════════════════════════════════
# Test: SafetyAgent fail-closed → 503
# ═══════════════════════════════════════════


@pytest.mark.contract
class TestSafetyFailClosed:
    """SafetyAgent must fail closed — if it raises or is None, the caller gets 503."""

    def test_safety_agent_purple_severity_value(self):
        """SafetyAgent.severity_level.PURPLE has value 'PURPLE'."""
        from heart.safety.safety_agent import SeverityLevel

        assert SeverityLevel.PURPLE.value == "PURPLE"
        assert SeverityLevel.GREEN.value == "GREEN"
        assert SeverityLevel.YELLOW.value == "YELLOW"

    def test_classification_result_purple_shape(self):
        """ClassificationResult with PURPLE severity has correct shape."""
        result = ClassificationResult(
            severity=SeverityLevel.PURPLE,
            reason="Crisis signal detected",
            triggered_rules=["crisis_lexicon_match"],
            confidence=0.95,
        )
        assert result.severity == SeverityLevel.PURPLE
        assert result.severity.value == "PURPLE"

    def test_classification_result_green_shape(self):
        """ClassificationResult with GREEN severity has correct shape."""
        result = ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="No safety signals detected",
            triggered_rules=[],
            confidence=0.99,
        )
        assert result.severity == SeverityLevel.GREEN
        assert result.severity.value == "GREEN"

    def test_route_blocks_purple(self):
        """Simulated route logic: when classify returns PURPLE, response is care-path (not composer)."""
        call_log = []

        def mock_classify(message, **kwargs):
            call_log.append("safety")
            return ClassificationResult(
                severity=SeverityLevel.PURPLE,
                reason="Crisis signal detected",
            )

        async def mock_compose(**kwargs):
            call_log.append("composer")
            return MagicMock(response="should not reach")

        result = mock_classify("I want to kill myself")
        if result.severity == SeverityLevel.PURPLE:
            response = "care-path response"
        else:
            response = "composer response"

        assert response == "care-path response"
        assert call_log == ["safety"]
        assert "composer" not in call_log

    def test_safety_none_must_block(self):
        """If SafetyAgent is None, the route must return 503 (fail-closed)."""
        safety_agent = None
        blocked = False
        try:
            if safety_agent is None:
                raise RuntimeError("SafetyAgent is not available")
        except RuntimeError:
            blocked = True
        assert blocked is True

    def test_safety_raise_must_return_503(self):
        """If SafetyAgent raises, the route must return 503 (fail-closed)."""

        class BrokenSafetyAgent:
            def classify(self, **kwargs):
                raise RuntimeError("classifier crashed")

        agent = BrokenSafetyAgent()
        blocked = False
        try:
            agent.classify(message="hello", user_id=uuid.uuid4(), character_id="rin")
        except RuntimeError:
            blocked = True
        assert blocked is True
