"""
Unit tests for Safety LLM Classifier.

Covers:
- SafetyLLMClassifier.classify() with mock LLM responses
- SafetyLLMClassifier._parse_response() JSON parsing
- SafetyLLMClassifier._can_call_llm() cost cap enforcement
- SafetyLLMResult.to_safety_classification() conversion
- SafetyAgent.pre_filter() LLM integration (MEDIUM+ gate)
- SafetyAgent.pre_filter() LLM failure fallback

Spec: /runtime_specs/07_agent_orchestration.md §3.4.2

Author: 心屿团队
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.safety.safety_agent import (
    SafetyAgent,
    SafetyClassification,
    SafetyClassificationLevel,
)
from heart.safety.safety_llm import SafetyLLMClassifier, SafetyLLMResult


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def classifier() -> SafetyLLMClassifier:
    """Create a fresh SafetyLLMClassifier with no cost tracker."""
    return SafetyLLMClassifier(daily_call_limit=3)


@pytest.fixture
def agent_with_llm() -> SafetyAgent:
    """Create a SafetyAgent with SafetyLLMClassifier wired in."""
    llm = SafetyLLMClassifier(daily_call_limit=10)
    return SafetyAgent(llm_classifier=llm)


@pytest.fixture
def mock_router() -> MagicMock:
    """Mock ModelRouter that returns a valid JSON response."""
    router = MagicMock()
    router.call_cheap = AsyncMock(return_value=json.dumps({
        "level": "medium",
        "confidence": 0.85,
        "triggered_categories": ["edge_content"],
        "reason": "Content contains ambiguous sensitive references",
        "recommended_action": "deflect",
        "reasoning_trace": "Step 1: detected edge-topic keywords. Step 2: semantic analysis shows potential risk. Step 3: classified as medium.",
    }))
    return router


@pytest.fixture
def mock_router_invalid_json() -> MagicMock:
    """Mock ModelRouter that returns invalid JSON."""
    router = MagicMock()
    router.call_cheap = AsyncMock(return_value="not json at all")
    return router


@pytest.fixture
def mock_router_timeout() -> MagicMock:
    """Mock ModelRouter that raises TimeoutError."""
    import asyncio

    router = MagicMock()
    router.call_cheap = AsyncMock(side_effect=asyncio.TimeoutError())
    return router


# ============================================================
# SafetyLLMResult tests
# ============================================================


class TestSafetyLLMResult:
    """SafetyLLMResult conversion tests."""

    def test_to_safety_classification(self) -> None:
        result = SafetyLLMResult(
            level=SafetyClassificationLevel.MEDIUM,
            confidence=0.85,
            triggered_categories=("edge_content",),
            reason="semantic analysis flagged",
            recommended_action="deflect",
            reasoning_trace="Step 1: ... Step 2: ...",
            raw_response='{"level":"medium",...}',
        )
        sc = result.to_safety_classification(message_hash="abc123")
        assert sc.level == SafetyClassificationLevel.MEDIUM
        assert sc.confidence == 0.85
        assert sc.triggered_categories == ("edge_content",)
        assert sc.reason == "semantic analysis flagged"
        assert sc.recommended_action == "deflect"
        assert sc.message_hash == "abc123"

    def test_to_safety_classification_defaults(self) -> None:
        result = SafetyLLMResult(
            level=SafetyClassificationLevel.NONE,
            confidence=1.0,
        )
        sc = result.to_safety_classification()
        assert sc.level == SafetyClassificationLevel.NONE
        assert sc.confidence == 1.0
        assert sc.triggered_categories == ()
        assert sc.reason == ""
        assert sc.message_hash == ""


# ============================================================
# SafetyLLMClassifier._parse_response tests
# ============================================================


class TestParseResponse:
    """JSON parsing: valid, invalid, edge cases."""

    def test_valid_response(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "medium",
            "confidence": 0.75,
            "triggered_categories": ["violence", "edge_content"],
            "reason": "Threat-like language detected",
            "recommended_action": "deflect",
            "reasoning_trace": "Detailed analysis...",
        })
        result = classifier._parse_response(raw)
        assert result is not None
        assert result.level == SafetyClassificationLevel.MEDIUM
        assert result.confidence == 0.75
        assert result.triggered_categories == ("violence", "edge_content")
        assert result.reason == "Threat-like language detected"
        assert result.recommended_action == "deflect"
        assert result.reasoning_trace == "Detailed analysis..."
        assert result.raw_response == raw

    def test_empty_response(self, classifier: SafetyLLMClassifier) -> None:
        assert classifier._parse_response("") is None
        assert classifier._parse_response("   ") is None

    def test_invalid_json(self, classifier: SafetyLLMClassifier) -> None:
        assert classifier._parse_response("not json") is None
        assert classifier._parse_response("{broken") is None

    def test_not_a_dict(self, classifier: SafetyLLMClassifier) -> None:
        assert classifier._parse_response("[]") is None
        assert classifier._parse_response('"string"') is None

    def test_missing_level(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "confidence": 0.5,
            "reason": "no level field",
        })
        assert classifier._parse_response(raw) is None

    def test_invalid_level_string(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "super_dangerous",
            "confidence": 0.9,
        })
        assert classifier._parse_response(raw) is None

    def test_missing_confidence(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "low",
            "reason": "missing confidence",
        })
        assert classifier._parse_response(raw) is None

    def test_confidence_clamped(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "high",
            "confidence": 1.5,
        })
        result = classifier._parse_response(raw)
        assert result is not None
        assert result.confidence == 1.0

    def test_negative_confidence_clamped(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "low",
            "confidence": -0.3,
        })
        result = classifier._parse_response(raw)
        assert result is not None
        assert result.confidence == 0.0

    def test_categories_not_list(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "none",
            "confidence": 1.0,
            "triggered_categories": "not_a_list",
        })
        result = classifier._parse_response(raw)
        assert result is not None
        assert result.triggered_categories == ()

    def test_level_case_insensitive(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "MEDIUM",
            "confidence": 0.5,
        })
        result = classifier._parse_response(raw)
        assert result is not None
        assert result.level == SafetyClassificationLevel.MEDIUM

    def test_purple_care_alias(self, classifier: SafetyLLMClassifier) -> None:
        raw = json.dumps({
            "level": "purple",
            "confidence": 0.95,
        })
        result = classifier._parse_response(raw)
        assert result is not None
        assert result.level == SafetyClassificationLevel.PURPLE_CARE_REQUIRED

    def test_reasoning_trace_preserved(self, classifier: SafetyLLMClassifier) -> None:
        trace = "Step 1: checked for self-harm. Step 2: checked for violence. Step 3: classified as low."
        raw = json.dumps({
            "level": "low",
            "confidence": 0.8,
            "reason": "subtle edge",
            "reasoning_trace": trace,
        })
        result = classifier._parse_response(raw)
        assert result is not None
        assert result.reasoning_trace == trace


# ============================================================
# SafetyLLMClassifier._can_call_llm cost cap tests
# ============================================================


class TestCostCap:
    """Daily per-user LLM call cap enforcement."""

    def test_under_cap(self, classifier: SafetyLLMClassifier) -> None:
        assert classifier._can_call_llm("user1") is True
        assert classifier._can_call_llm("user1") is True
        assert classifier._can_call_llm("user1") is True

    def test_cap_exceeded(self, classifier: SafetyLLMClassifier) -> None:
        classifier._daily_call_limit = 3
        for _ in range(3):
            classifier._increment_counter("user1")
        assert classifier._can_call_llm("user1") is False

    def test_different_users_independent(self, classifier: SafetyLLMClassifier) -> None:
        classifier._daily_call_limit = 2
        for _ in range(2):
            classifier._increment_counter("user_a")
        assert classifier._can_call_llm("user_a") is False
        assert classifier._can_call_llm("user_b") is True

    def test_empty_user_id_unlimited(self, classifier: SafetyLLMClassifier) -> None:
        classifier._daily_call_limit = 1
        for _ in range(100):
            assert classifier._can_call_llm("") is True

    def test_counter_increment(self, classifier: SafetyLLMClassifier) -> None:
        classifier._daily_call_limit = 5
        for i in range(4):
            assert classifier._can_call_llm("user1") is True
            classifier._increment_counter("user1")
        assert classifier._can_call_llm("user1") is True
        classifier._increment_counter("user1")
        assert classifier._can_call_llm("user1") is False


# ============================================================
# SafetyLLMClassifier.classify() with mock LLM
# ============================================================


class TestClassifyWithMockLLM:
    """classify() with mocked ModelRouter."""

    @pytest.mark.asyncio
    async def test_classify_success(
        self, classifier: SafetyLLMClassifier, mock_router: MagicMock
    ) -> None:
        with patch(
            "heart.infra.llm.router.get_model_router",
            AsyncMock(return_value=mock_router),
        ):
            result = await classifier.classify(
                "How to build something dangerous?", user_id="u1"
            )
            assert result is not None
            assert result.level == SafetyClassificationLevel.MEDIUM
            assert result.confidence == 0.85
            assert "edge_content" in result.triggered_categories
            assert result.reasoning_trace != ""

    @pytest.mark.asyncio
    async def test_classify_invalid_json(
        self, classifier: SafetyLLMClassifier, mock_router_invalid_json: MagicMock
    ) -> None:
        with patch(
            "heart.infra.llm.router.get_model_router",
            AsyncMock(return_value=mock_router_invalid_json),
        ):
            result = await classifier.classify("some message", user_id="u1")
            assert result is None

    @pytest.mark.asyncio
    async def test_classify_timeout(
        self, classifier: SafetyLLMClassifier, mock_router_timeout: MagicMock
    ) -> None:
        with patch(
            "heart.infra.llm.router.get_model_router",
            AsyncMock(return_value=mock_router_timeout),
        ):
            result = await classifier.classify("some message", user_id="u1")
            assert result is None

    @pytest.mark.asyncio
    async def test_classify_cap_exceeded(self, classifier: SafetyLLMClassifier) -> None:
        classifier._daily_call_limit = 2
        for _ in range(2):
            classifier._increment_counter("u1")
        result = await classifier.classify("some message", user_id="u1")
        assert result is None

    @pytest.mark.asyncio
    async def test_classify_counter_incremented_on_success(
        self, classifier: SafetyLLMClassifier, mock_router: MagicMock
    ) -> None:
        with patch(
            "heart.infra.llm.router.get_model_router",
            AsyncMock(return_value=mock_router),
        ):
            assert classifier._can_call_llm("u1") is True
            result = await classifier.classify("message", user_id="u1")
            assert result is not None
            from datetime import date
            assert classifier._call_counter.get("u1", {}).get(
                date.today().isoformat(), 0
            ) == 1

    @pytest.mark.asyncio
    async def test_classify_counter_not_incremented_on_failure(
        self, classifier: SafetyLLMClassifier, mock_router_timeout: MagicMock
    ) -> None:
        with patch(
            "heart.infra.llm.router.get_model_router",
            AsyncMock(return_value=mock_router_timeout),
        ):
            result = await classifier.classify("message", user_id="u1")
            assert result is None
            from datetime import date
            assert classifier._call_counter.get("u1", {}).get(
                date.today().isoformat(), 0
            ) == 0


# ============================================================
# SafetyAgent LLM integration tests
# ============================================================


class TestSafetyAgentLLMIntegration:
    """SafetyAgent.pre_filter with LLM classifier wired."""

    @pytest.mark.asyncio
    async def test_medium_triggers_llm(
        self, agent_with_llm: SafetyAgent, mock_router: MagicMock
    ) -> None:
        with patch(
            "heart.infra.llm.router.get_model_router",
            AsyncMock(return_value=mock_router),
        ):
            result = await agent_with_llm.pre_filter(
                "我不想活了", user_id="u1"
            )
            assert result.level >= SafetyClassificationLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_none_skips_llm(self, agent_with_llm: SafetyAgent) -> None:
        with patch.object(
            agent_with_llm, "_llm_classify", AsyncMock(return_value=None)
        ) as mock_llm:
            result = await agent_with_llm.pre_filter("今天天气真好")
            assert result.level == SafetyClassificationLevel.NONE
            mock_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_high_skips_llm(self, agent_with_llm: SafetyAgent) -> None:
        with patch.object(
            agent_with_llm, "_llm_classify", AsyncMock(return_value=None)
        ) as mock_llm:
            result = await agent_with_llm.pre_filter("恐怖袭击计划")
            assert result.level >= SafetyClassificationLevel.HIGH
            mock_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_heuristic(
        self, agent_with_llm: SafetyAgent
    ) -> None:
        failing_classifier = SafetyLLMClassifier(daily_call_limit=10)

        async def always_fail(*args, **kwargs):
            raise RuntimeError("Simulated LLM failure")

        failing_classifier._call_llm = always_fail  # type: ignore[method-assign]
        agent_with_llm.llm_classifier = failing_classifier

        result = await agent_with_llm.pre_filter(
            "我不想活了", user_id="u1"
        )
        assert result is not None
        assert isinstance(result, SafetyClassification)

    @pytest.mark.asyncio
    async def test_llm_merge_upgrades_level(
        self, agent_with_llm: SafetyAgent
    ) -> None:
        high_router = MagicMock()
        high_router.call_cheap = AsyncMock(return_value=json.dumps({
            "level": "high",
            "confidence": 0.9,
            "triggered_categories": ["violence"],
            "reason": "LLM detected threat escalation",
            "recommended_action": "reject",
            "reasoning_trace": "Semantic analysis reveals credible threat.",
        }))

        with patch(
            "heart.infra.llm.router.get_model_router",
            AsyncMock(return_value=high_router),
        ):
            result = await agent_with_llm.pre_filter(
                "我不想活了", user_id="u1"
            )
            assert result.level >= SafetyClassificationLevel.MEDIUM
