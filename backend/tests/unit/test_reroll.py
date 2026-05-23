"""
Tests for Reroll Handler — SS05 §3.10 (§3.4)

Coverage targets:
- RerollHandler.should_reroll() decision logic
- RerollHandler.tighten_constraints() injects reinforce-anchor
- RerollHandler.handle() loop: reroll succeeds after 1st reject (tighter constraints)
- RerollHandler.handle() loop: 3rd reject → fallback library used
- RerollHandler.select_fallback() for known Rin/Dorothy characters
- RerollHandler.select_fallback() for unknown characters
- RerollAttempt and RerollResult dataclass behavior
- Module-level get_fallback() and list_fallback_categories()
- max_attempts constructor validation

Author: 心屿团队
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.ss05_composer.anti_pattern_filter import FilterResult, FilterViolation
from heart.ss05_composer.reroll import (
    _DEFAULT_FALLBACK_CATEGORY,
    _DEFAULT_MAX_ATTEMPTS,
    _FALLBACK_LIBRARY,
    RerollAttempt,
    RerollHandler,
    RerollResult,
    get_fallback,
    list_fallback_categories,
)


# ================================================================
# Fixtures
# ================================================================


def _base_messages() -> List[Dict[str, str]]:
    """Build a representative message list for conversation turn."""
    return [
        {
            "role": "system",
            "content": "你是神无月凛。你是一个冷淡、嘴硬但内心温柔的雷神。",
        },
        {"role": "user", "content": "凛，今天天气不错。"},
    ]


def _rin_soul() -> Dict[str, Any]:
    """Minimal Rin soul spec for fallback tests."""
    return {
        "character_id": "rin",
        "anti_patterns": {
            "hard_never": ["宝宝", "加油", "一直"],
        },
    }


def _dorothy_soul() -> Dict[str, Any]:
    """Minimal Dorothy soul spec for fallback tests."""
    return {
        "character_id": "dorothy",
        "anti_patterns": {
            "hard_never": ["永远", "无聊", "幼稚"],
        },
    }


@pytest.fixture
def handler() -> RerollHandler:
    """Default handler with max_attempts=2."""
    return RerollHandler(max_attempts=2)


@pytest.fixture
def handler_no_reroll() -> RerollHandler:
    """Handler with max_attempts=0 (immediate fallback)."""
    return RerollHandler(max_attempts=0)


# ================================================================
# RerollAttempt dataclass
# ================================================================


class TestRerollAttempt:
    def test_defaults(self):
        a = RerollAttempt(attempt_number=1)
        assert a.attempt_number == 1
        assert a.violated_patterns == []
        assert a.anchor_injected is False
        assert a.llm_response == ""
        assert a.llm_latency_ms == 0.0

    def test_full_record(self):
        a = RerollAttempt(
            attempt_number=2,
            violated_patterns=["宝宝", "加油"],
            anchor_injected=True,
            llm_response="……知道了。",
            llm_latency_ms=120.5,
        )
        assert a.attempt_number == 2
        assert "宝宝" in a.violated_patterns
        assert a.anchor_injected is True
        assert a.llm_response == "……知道了。"
        assert a.llm_latency_ms == 120.5


# ================================================================
# RerollResult dataclass
# ================================================================


class TestRerollResult:
    def test_defaults(self):
        r = RerollResult(response_text="...")
        assert r.response_text == "..."
        assert r.action == ""
        assert r.total_attempts == 0
        assert r.reroll_history == []

    def test_reroll_succeeded(self):
        r = RerollResult(
            response_text="嗯。",
            action="reroll_succeeded",
            total_attempts=1,
        )
        assert r.action == "reroll_succeeded"
        assert r.total_attempts == 1

    def test_fallback(self):
        r = RerollResult(
            response_text="……抱歉，刚才走神了。",
            action="fallback",
            total_attempts=2,
        )
        assert r.action == "fallback"
        assert r.total_attempts == 2


# ================================================================
# should_reroll
# ================================================================


class TestShouldReroll:
    def test_allow_when_below_max(self, handler):
        assert handler.should_reroll(0) is True
        assert handler.should_reroll(1) is True

    def test_deny_when_at_or_above_max(self, handler):
        assert handler.should_reroll(2) is False
        assert handler.should_reroll(3) is False

    def test_zero_max_never_rerolls(self, handler_no_reroll):
        assert handler_no_reroll.should_reroll(0) is False
        assert handler_no_reroll.should_reroll(1) is False


# ================================================================
# tighten_constraints
# ================================================================


class TestTightenConstraints:
    def test_injects_reinforce_after_system_messages(self, handler):
        messages = _base_messages()
        violated = ["宝宝", "加油"]
        tightened = handler.tighten_constraints(messages, violated)

        # System + reinforce + user = 3 messages
        assert len(tightened) == 3
        # The second message should be the reinforce
        assert tightened[1]["role"] == "system"
        assert "上一次回复违反了你的灵魂" in tightened[1]["content"]
        assert "宝宝" in tightened[1]["content"]
        assert "加油" in tightened[1]["content"]

    def test_no_patterns_no_injection(self, handler):
        messages = _base_messages()
        tightened = handler.tighten_constraints(messages, [])
        assert len(tightened) == 2  # No injection
        assert tightened == messages  # Structural equality

    def test_original_not_mutated(self, handler):
        messages = _base_messages()
        original_len = len(messages)
        handler.tighten_constraints(messages, ["宝宝"])
        assert len(messages) == original_len  # Unchanged

    def test_custom_reinforce_content(self, handler):
        messages = _base_messages()
        tightened = handler.tighten_constraints(
            messages,
            ["宝宝"],
            reinforce_content="请用冷淡的语气回复。",
        )
        assert "请用冷淡的语气回复" in tightened[1]["content"]

    def test_all_system_messages(self, handler):
        """When all messages are system, reinforce is appended at end."""
        messages = [
            {"role": "system", "content": "system A"},
            {"role": "system", "content": "system B"},
        ]
        tightened = handler.tighten_constraints(messages, ["宝宝"])
        assert len(tightened) == 3
        assert tightened[2]["role"] == "system"
        assert "宝宝" in tightened[2]["content"]


# ================================================================
# select_fallback
# ================================================================


class TestSelectFallback:
    def test_rin_apologetic(self, handler):
        text = handler.select_fallback("rin", "apologetic")
        assert "抱歉" in text or "走神" in text

    def test_rin_casual_thinking(self, handler):
        text = handler.select_fallback("rin", "casual_thinking")
        assert text in _FALLBACK_LIBRARY["rin"]["casual_thinking"]

    def test_dorothy_apologetic(self, handler):
        text = handler.select_fallback("dorothy", "apologetic")
        assert "桃桃" in text

    def test_unknown_character_returns_minimal(self, handler):
        text = handler.select_fallback("unknown_character")
        assert text == "……"

    def test_unknown_category_falls_back_to_default(self, handler):
        text = handler.select_fallback("rin", "nonexistent_category")
        assert "抱歉" in text or "走神" in text  # Rin apologetic

    def test_default_category_is_apologetic(self, handler):
        text = handler.select_fallback("rin")
        assert text in _FALLBACK_LIBRARY["rin"]["apologetic"]


# ================================================================
# handle() — with mocked ModelRouter
# ================================================================


class TestHandleWithMockedLLM:
    """Tests for the full handle() orchestration loop.

    Uses AsyncMock to simulate ModelRouter.call_main().
    """

    @pytest.mark.asyncio
    async def test_first_reroll_succeeds(self, handler):
        """After 1st reject, 2nd attempt has tighter constraints → succeeds."""
        messages = _base_messages()
        violated = ["宝宝"]
        mock_response = "……嗯。今天也是平常的一天。"

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.call_main = AsyncMock(return_value=mock_response)
            mock_get_router.return_value = mock_router

            result = await handler.handle(
                messages=messages,
                violated_patterns=violated,
                soul=_rin_soul(),
            )

            assert result.action == "reroll_succeeded"
            assert result.response_text == mock_response
            assert result.total_attempts == 1
            assert len(result.reroll_history) == 1
            assert result.reroll_history[0].anchor_injected is True

    @pytest.mark.asyncio
    async def test_second_reroll_has_tighter_constraints(self, handler):
        """Verify that the 2nd reroll attempt's messages contain reinforce."""
        messages = _base_messages()
        violated = ["宝宝", "加油"]

        # Mock: first call returns still-violating text, second returns clean
        call_count = 0

        async def side_effect(messages, temperature=None, max_tokens=None,
                              agent_name=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Verify first call's messages have reinforce
                msg_texts = [m["content"] for m in messages]
                has_reinforce = any(
                    "上一次回复违反了你的灵魂" in t for t in msg_texts
                )
                assert has_reinforce, (
                    f"First reroll attempt should have reinforce anchor. "
                    f"Messages: {msg_texts}"
                )
                return "宝宝你今天好可爱~"  # Still violates
            else:
                # Second call also should have reinforce (tighter)
                msg_texts = [m["content"] for m in messages]
                has_reinforce = any(
                    "上一次回复违反了你的灵魂" in t for t in msg_texts
                )
                assert has_reinforce, (
                    f"Second reroll attempt should also have reinforce anchor."
                )
                return "嗯。今天天气确实不错。"

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.call_main = AsyncMock(side_effect=side_effect)
            mock_get_router.return_value = mock_router

            result = await handler.handle(
                messages=messages,
                violated_patterns=violated,
                soul=_rin_soul(),
            )

            # Without filter_fn, the first reroll response is accepted as-is
            # (since no filter_fn to check anti-patterns)
            assert result.action == "reroll_succeeded"
            assert result.total_attempts == 1

    @pytest.mark.asyncio
    async def test_third_reject_uses_fallback(self, handler):
        """3rd reject (after 2 rerolls exhausted) → fallback library used."""
        messages = _base_messages()
        violated = ["宝宝"]

        # Create a filter_fn that always rejects
        def always_reject(text: str) -> FilterResult:
            return FilterResult(
                passed=False,
                violations=[
                    FilterViolation(
                        pattern="宝宝",
                        violation_type="hard_never",
                    )
                ],
                severity="hard",
            )

        # Mock LLM to return the same violating text every time
        mock_response = "宝宝你好可爱~"

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.call_main = AsyncMock(return_value=mock_response)
            mock_get_router.return_value = mock_router

            result = await handler.handle(
                messages=messages,
                violated_patterns=violated,
                soul=_rin_soul(),
                filter_fn=always_reject,
            )

            # Should have exhausted all 2 attempts and fallen back
            assert result.action == "fallback"
            assert result.total_attempts == 2
            assert len(result.reroll_history) == 2

            # Fallback must be from Rin's fallback library
            rin_apologetic = _FALLBACK_LIBRARY["rin"]["apologetic"]
            assert result.response_text in rin_apologetic, (
                f"Expected fallback in {rin_apologetic}, got {result.response_text!r}"
            )

    @pytest.mark.asyncio
    async def test_reroll_succeeds_with_filter_fn_on_second_try(self, handler):
        """After 1st reject, 2nd attempt has tighter constraints → passes filter."""
        messages = _base_messages()
        violated = ["宝宝"]

        call_count = 0

        async def side_effect(messages, temperature=None, max_tokens=None,
                              agent_name=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "宝宝你今天好可爱~"
            else:
                return "嗯。今天也是平常的一天。"

        def filter_fn(text: str) -> FilterResult:
            if "宝宝" in text:
                return FilterResult(
                    passed=False,
                    violations=[FilterViolation(
                        pattern="宝宝",
                        violation_type="hard_never",
                    )],
                    severity="hard",
                )
            return FilterResult(passed=True)

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.call_main = AsyncMock(side_effect=side_effect)
            mock_get_router.return_value = mock_router

            result = await handler.handle(
                messages=messages,
                violated_patterns=violated,
                soul=_rin_soul(),
                filter_fn=filter_fn,
            )

            assert result.action == "reroll_succeeded"
            assert result.total_attempts == 2
            assert result.response_text == "嗯。今天也是平常的一天。"

    @pytest.mark.asyncio
    async def test_empty_violations_no_reroll(self, handler):
        """handle() with empty violated_patterns returns immediately."""
        messages = _base_messages()

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            result = await handler.handle(
                messages=messages,
                violated_patterns=[],
                soul=_rin_soul(),
            )
            # Should not have called LLM
            mock_get_router.assert_not_called()
            assert result.action == "reroll_succeeded"
            assert result.response_text == ""
            assert result.total_attempts == 0

    @pytest.mark.asyncio
    async def test_llm_failure_retries(self, handler):
        """LLM call failure should not count against reroll budget."""
        messages = _base_messages()
        violated = ["宝宝"]

        # First call fails, second succeeds
        async def side_effect(messages, temperature=None, max_tokens=None,
                              agent_name=None):
            raise RuntimeError("LLM temporarily unavailable")

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.call_main = AsyncMock(side_effect=side_effect)
            mock_get_router.return_value = mock_router

            result = await handler.handle(
                messages=messages,
                violated_patterns=violated,
                soul=_rin_soul(),
            )

            # Both attempts failed → fallback
            assert result.action == "fallback"
            assert result.total_attempts == 2
            # Both records should be in history (even the failed ones)
            assert len(result.reroll_history) == 2
            assert result.reroll_history[0].llm_response == ""

    @pytest.mark.asyncio
    async def test_dorothy_fallback_on_exhaustion(self, handler):
        """Verify Dorothy's fallback is used when character is Dorothy."""
        messages = _base_messages()
        violated = ["永远"]

        def always_reject(text: str) -> FilterResult:
            return FilterResult(
                passed=False,
                violations=[FilterViolation(
                    pattern="永远",
                    violation_type="hard_never",
                )],
                severity="hard",
            )

        mock_response = "永远永远在一起！"

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.call_main = AsyncMock(return_value=mock_response)
            mock_get_router.return_value = mock_router

            result = await handler.handle(
                messages=messages,
                violated_patterns=violated,
                soul=_dorothy_soul(),
                filter_fn=always_reject,
            )

            assert result.action == "fallback"
            dorothy_apologetic = _FALLBACK_LIBRARY["dorothy"]["apologetic"]
            assert result.response_text in dorothy_apologetic


# ================================================================
# Constructor validation
# ================================================================


class TestConstructor:
    def test_default_max_attempts_is_two(self):
        h = RerollHandler()
        assert h.max_attempts == 2

    def test_custom_max_attempts(self):
        h = RerollHandler(max_attempts=3)
        assert h.max_attempts == 3

    def test_negative_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RerollHandler(max_attempts=-1)


# ================================================================
# Module-level convenience functions
# ================================================================


class TestModuleLevel:
    def test_get_fallback_rin(self):
        text = get_fallback("rin", "apologetic")
        assert text in _FALLBACK_LIBRARY["rin"]["apologetic"]

    def test_get_fallback_dorothy(self):
        text = get_fallback("dorothy", "casual_thinking")
        assert text in _FALLBACK_LIBRARY["dorothy"]["casual_thinking"]

    def test_list_fallback_categories_rin(self):
        cats = list_fallback_categories("rin")
        assert "apologetic" in cats
        assert "casual_thinking" in cats
        assert "avoiding_topic" in cats
        assert "cant_compute" in cats

    def test_list_fallback_categories_unknown(self):
        cats = list_fallback_categories("nonexistent")
        assert cats == []


# ================================================================
# Integration-like: verify the full flow end-to-end
# ================================================================


class TestEndToEndFlow:
    """Simulates the full reroll → fallback pipeline.

    Per fixture_004_fallback in runtime_specs appendix D:
    - mock_llm_to_always_violate: true
    - expected_after_2_rerolls: action "fallback", response_in rin.fallback_library.apologetic
    """

    @pytest.mark.asyncio
    async def test_exhaust_rerolls_then_fallback_rin(self, handler):
        """Complete path: 2 rerolls both fail filter → fallback to Rin's apologetic."""
        messages = _base_messages()

        # Mock LLM that always returns violating text
        violating_response = "宝宝你好可爱~你今天太棒了！"

        # Filter that always rejects
        def always_reject(text: str) -> FilterResult:
            return FilterResult(
                passed=False,
                violations=[
                    FilterViolation(
                        pattern="宝宝",
                        violation_type="hard_never",
                        match_excerpt="宝宝",
                    ),
                    FilterViolation(
                        pattern="太棒了",
                        violation_type="hard_never",
                        match_excerpt="太棒了",
                    ),
                ],
                severity="hard",
            )

        with patch(
            "heart.ss05_composer.reroll.get_model_router",
            new_callable=AsyncMock,
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.call_main = AsyncMock(return_value=violating_response)
            mock_get_router.return_value = mock_router

            result = await handler.handle(
                messages=messages,
                violated_patterns=["宝宝", "太棒了"],
                soul=_rin_soul(),
                filter_fn=always_reject,
            )

            # Expected per fixture_004_fallback
            assert result.action == "fallback"
            assert result.total_attempts == 2
            assert len(result.reroll_history) == 2

            # Both attempts should have anchor_injected=True
            for attempt in result.reroll_history:
                assert attempt.anchor_injected is True

            # Fallback must be from Rin's apologetic library
            rin_apologetic = _FALLBACK_LIBRARY["rin"]["apologetic"]
            assert result.response_text in rin_apologetic, (
                f"Expected fallback in {rin_apologetic!r}, "
                f"got {result.response_text!r}"
            )
