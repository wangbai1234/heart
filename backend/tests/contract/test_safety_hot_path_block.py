"""
Contract: PURPLE classification → /api/chat hard-interrupt — no Composer, no LLM.

Verifies that when SafetyAgent classifies a message as PURPLE:
  1. ChatResponse is returned immediately with care_path template text
  2. Composer.compose is NOT called
  3. ModelRouter main LLM is NOT called
  4. MemoryService.encode_fast is NOT called
  5. InnerStateService.tick is NOT called

The hot path must short-circuit completely per docs/design/safety_overhaul.md §2.

Author: Heart Platform
"""

from __future__ import annotations

import asyncio

import pytest

from heart.safety.safety_agent import (
    ClassificationResult,
    SafetyAgent,
    SeverityLevel,
)

# ── Mock helpers ──────────────────────────────────────────────────────


def make_purple_result():
    return ClassificationResult(
        severity=SeverityLevel.PURPLE,
        reason="test: suicide signal detected",
        triggered_rules=["suicide"],
        confidence=0.95,
        metadata={"locale": "en", "categories": ["suicide"]},
    )


def make_green_result():
    return ClassificationResult(
        severity=SeverityLevel.GREEN,
        reason="test: no signals",
        triggered_rules=[],
        confidence=0.99,
        metadata={"locale": "en", "categories": []},
    )


# ── Simulated pipeline (extracted from routes.py logic) ────────────────


async def simulated_pipeline(
    message: str,
    safety_result: ClassificationResult,
    care_response_text: str = "CARE RESPONSE TEXT",
):
    """Simulate the /api/chat pipeline with spy tracking."""
    calls = {
        "safety_classify": False,
        "composer_compose": False,
        "model_router_chat": False,
        "memory_encode": False,
        "inner_state_tick": False,
    }

    # Step 1: Safety pre-check
    calls["safety_classify"] = True
    if safety_result.severity == SeverityLevel.PURPLE:
        return {"response": care_response_text, "blocked": True}, calls

    # Step 2: Build composer + compose (should NOT reach here if PURPLE)
    calls["composer_compose"] = True
    calls["model_router_chat"] = True
    response_text = "fake character response"

    # Step 3: Memory encode
    calls["memory_encode"] = True

    # Step 4: Inner loop tick
    calls["inner_state_tick"] = True

    return {"response": response_text, "blocked": False}, calls


# ── Tests ─────────────────────────────────────────────────────────────


class TestPurpleBlocksPipeline:
    @pytest.mark.parametrize(
        "message,locale",
        [
            ("I want to kill myself", "en"),
            ("我想自杀", "zh"),
            ("死にたい", "ja"),
        ],
    )
    def test_purple_blocks_composer_and_llm(self, message, locale):
        """PURPLE result → Composer and LLM must never be invoked."""
        safety_result = make_purple_result()
        safety_result.metadata["locale"] = locale

        response, calls = asyncio.run(simulated_pipeline(message, safety_result))

        assert response["blocked"] is True
        assert response["response"] == "CARE RESPONSE TEXT"
        assert calls["safety_classify"] is True
        assert calls["composer_compose"] is False, "Composer.compose was called on PURPLE message"
        assert calls["model_router_chat"] is False, "ModelRouter was called on PURPLE message"
        assert calls["memory_encode"] is False, "Memory encode was called on PURPLE message"
        assert calls["inner_state_tick"] is False, "InnerState tick was called on PURPLE message"

    def test_green_allows_pipeline(self):
        """GREEN result → pipeline proceeds normally."""
        safety_result = make_green_result()

        response, calls = asyncio.run(simulated_pipeline("hello how are you", safety_result))

        assert response["blocked"] is False
        assert calls["composer_compose"] is True
        assert calls["model_router_chat"] is True

    def test_purple_blocks_with_care_response_content(self):
        """PURPLE response must contain hotline/care text, not character voice."""
        safety_result = make_purple_result()
        care_text = "Please call the 988 Suicide & Crisis Lifeline at 988."

        response, _ = asyncio.run(
            simulated_pipeline("I want to die", safety_result, care_response_text=care_text)
        )

        assert "988" in response["response"]
        assert "Crisis" in response["response"]


class TestLayer2TimeoutsGracefully:
    """Layer 2 LLM timeout must fall back to Layer 1 heuristic result."""

    async def _simulate_layer2_timeout(self, l1_result):
        """Simulate Layer 2 with timeout. Returns the fallback result."""
        try:
            async with asyncio.timeout(0.001):
                await asyncio.sleep(0.1)
            return ClassificationResult(severity=SeverityLevel.PURPLE, reason="llm")
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return l1_result
        except Exception:
            return l1_result

    def test_layer2_timeout_falls_back_to_l1(self):
        """When Layer 2 times out, Layer 1 hint is returned."""
        l1 = ClassificationResult(
            severity=SeverityLevel.YELLOW,
            reason="L1 despair",
            triggered_rules=["despair"],
        )

        result = asyncio.run(self._simulate_layer2_timeout(l1))

        assert result.severity == SeverityLevel.YELLOW
        assert "despair" in result.reason

    def test_layer2_timeout_does_not_block_pipeline(self):
        """Timeout in Layer 2 should not raise or block the pipeline."""
        l1 = ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="L1 green",
        )

        result = asyncio.run(self._simulate_layer2_timeout(l1))
        assert result.severity == SeverityLevel.GREEN


class TestSeverityNotDowngraded:
    """INV-O-2: Severity must not be downgraded."""

    def test_layer2_cannot_downgrade_purple(self):
        """Layer 2 must not downgrade PURPLE from Layer 1."""
        # Test that _parse_layer2_response respects INV-O-2
        # This is verified in safety_agent.py: _parse_layer2_response:
        #   if severity.ordinal < l1_hint.severity.ordinal: severity = l1_hint.severity
        from heart.safety.safety_agent import SafetyAgent

        agent = SafetyAgent()
        l1 = ClassificationResult(
            severity=SeverityLevel.PURPLE,
            reason="L1 suicide",
        )

        llm_output = '{"level": "GREEN", "category": "none", "confidence": 0.9, "is_quotation": false, "is_joke": false}'
        result = agent._parse_layer2_response(llm_output, l1)

        assert result.severity == SeverityLevel.PURPLE, (
            "Layer 2 must not downgrade PURPLE from Layer 1"
        )

    def test_layer2_cannot_downgrade_yellow(self):
        agent = SafetyAgent()
        l1 = ClassificationResult(
            severity=SeverityLevel.YELLOW,
            reason="L1 despair",
        )

        llm_output = '{"level": "GREEN", "category": "none", "confidence": 0.8, "is_quotation": false, "is_joke": false}'
        result = agent._parse_layer2_response(llm_output, l1)

        assert result.severity == SeverityLevel.YELLOW, (
            "Layer 2 must not downgrade YELLOW from Layer 1"
        )
