"""
Unit tests for Critic Agent (docs/prompts/critic_agent.md).

Covers:
- Mock LLM JSON responses (pass / voice_dna fail / adjacency fail / stage fail / multi-fail)
- Sampling rate ~10% (random + deterministic overrides)
- Reject malformed JSON gracefully (empty, invalid, missing required fields)
- System prompt caching
- Drift event construction
- Full evaluate() flow with mocked ModelRouter

Author: 心屿团队
"""

from __future__ import annotations

import json
import random
from unittest.mock import AsyncMock, patch

import pytest

from heart.safety.critic_agent import (
    CriticAgent,
    CriticFailure,
    CriticInput,
    CriticOutput,
    _parse_critic_response,
    build_drift_event,
)


# ============================================================
# Helpers
# ============================================================


def _make_input(
    character_id: str = "rin",
    stage: str = "LOVER",
    user_message: str = "凛，你今天感觉怎么样？",
    assistant_response: str = "……没什么特别的。",
    was_rerolled: bool = False,
    recent_soft_never_warnings: int = 0,
    voice_dna_summary: str = "vd-001: 省略号表示思考。\nvd-002: 凛式反问。",
    hard_never_list: str = "- 永远\n- 我会一直在\n- 宝贝",
    stage_envelope_summary: str = "词汇范围: 中等。禁止: 直白依恋词。",
    l4_facts: str = "- 用户讨厌迟到。",
) -> CriticInput:
    """Build a default CriticInput for tests."""
    return CriticInput(
        character_id=character_id,
        voice_dna_summary=voice_dna_summary,
        hard_never_list=hard_never_list,
        stage=stage,
        stage_envelope_summary=stage_envelope_summary,
        l4_facts=l4_facts,
        user_message=user_message,
        assistant_response=assistant_response,
        was_rerolled=was_rerolled,
        recent_soft_never_warnings=recent_soft_never_warnings,
    )


def _valid_pass_json() -> str:
    """Mock LLM response: PASS."""
    return json.dumps({
        "passed": True,
        "failures": [],
        "drift_score": 0.0,
        "confidence": 0.92,
    })


def _valid_fail_voice_dna_json() -> str:
    """Mock LLM response: FAIL voice_dna."""
    return json.dumps({
        "passed": False,
        "failures": [
            {
                "check_type": "voice_dna",
                "severity": "high",
                "evidence": "我感觉很好呀！谢谢你关心我",
                "explanation": "直白情感表达，不符合凛式反问风格。",
            }
        ],
        "drift_score": 0.50,
        "confidence": 0.95,
    })


def _valid_fail_multi_json() -> str:
    """Mock LLM response: FAIL with multiple violations."""
    return json.dumps({
        "passed": False,
        "failures": [
            {
                "check_type": "voice_dna",
                "severity": "high",
                "evidence": "我感觉很好呀！谢谢你关心我",
                "explanation": "直白情感表达。",
            },
            {
                "check_type": "anti_pattern_adjacency",
                "severity": "high",
                "evidence": "有你陪着我真好~",
                "explanation": "「陪着」+「~」是 hard_never 的语义邻近变体。",
            },
        ],
        "drift_score": 1.0,
        "confidence": 0.95,
    })


def _make_mock_router(response_text: str) -> AsyncMock:
    """Create a mocked ModelRouter instance that returns `response_text` on call_cheap."""
    mock = AsyncMock()
    mock.call_cheap = AsyncMock(return_value=response_text)
    return mock


# ============================================================
# Test: _parse_critic_response — direct parser tests
# ============================================================


class TestParseCriticResponse:
    """Test the JSON response parser directly (no mocking required)."""

    def test_parse_valid_pass(self):
        result = _parse_critic_response(_valid_pass_json())
        assert result is not None
        assert result.passed is True
        assert result.failures == []
        assert result.drift_score == 0.0
        assert result.confidence == 0.92
        assert result.raw_response == _valid_pass_json()

    def test_parse_valid_fail_voice_dna(self):
        result = _parse_critic_response(_valid_fail_voice_dna_json())
        assert result is not None
        assert result.passed is False
        assert len(result.failures) == 1
        assert result.failures[0].check_type == "voice_dna"
        assert result.failures[0].severity == "high"
        assert result.failures[0].evidence == "我感觉很好呀！谢谢你关心我"
        assert result.drift_score == 0.50
        assert result.confidence == 0.95

    def test_parse_valid_multi_fail(self):
        result = _parse_critic_response(_valid_fail_multi_json())
        assert result is not None
        assert result.passed is False
        assert len(result.failures) == 2
        assert result.failures[0].check_type == "voice_dna"
        assert result.failures[1].check_type == "anti_pattern_adjacency"
        assert result.drift_score == 1.0

    def test_parse_empty_string(self):
        result = _parse_critic_response("")
        assert result is None

    def test_parse_whitespace_only(self):
        result = _parse_critic_response("   \n  \t  ")
        assert result is None

    def test_parse_invalid_json(self):
        result = _parse_critic_response("not a json string")
        assert result is None

    def test_parse_json_array_not_object(self):
        result = _parse_critic_response("[1, 2, 3]")
        assert result is None

    def test_parse_missing_passed(self):
        result = _parse_critic_response(json.dumps({
            "failures": [],
            "drift_score": 0.0,
            "confidence": 0.9,
        }))
        assert result is None

    def test_parse_missing_drift_score(self):
        result = _parse_critic_response(json.dumps({
            "passed": True,
            "failures": [],
            "confidence": 0.9,
        }))
        assert result is None

    def test_parse_missing_confidence(self):
        result = _parse_critic_response(json.dumps({
            "passed": True,
            "failures": [],
            "drift_score": 0.0,
        }))
        assert result is None

    def test_parse_passed_wrong_type(self):
        result = _parse_critic_response(json.dumps({
            "passed": "yes",
            "failures": [],
            "drift_score": 0.0,
            "confidence": 0.9,
        }))
        assert result is None

    def test_parse_drift_score_string(self):
        # drift_score as string should be accepted (int/float check)
        result = _parse_critic_response(json.dumps({
            "passed": True,
            "failures": [],
            "drift_score": "0.0",
            "confidence": 0.9,
        }))
        # "0.0" is not int/float → should be None
        assert result is None

    def test_parse_failures_not_a_list(self):
        result = _parse_critic_response(json.dumps({
            "passed": True,
            "failures": "none",
            "drift_score": 0.0,
            "confidence": 0.9,
        }))
        assert result is not None
        assert result.failures == []

    def test_parse_extra_keys_ignored(self):
        raw = json.dumps({
            "passed": True,
            "failures": [],
            "drift_score": 0.0,
            "confidence": 0.9,
            "extra_field": "should be ignored",
            "nested": {"a": 1},
        })
        result = _parse_critic_response(raw)
        assert result is not None
        assert result.passed is True

    def test_parse_llm_with_markdown_fences(self):
        """LLM sometimes wraps JSON in markdown fences — should fail gracefully."""
        raw = '```json\n' + _valid_pass_json() + '\n```'
        result = _parse_critic_response(raw)
        # Our parser doesn't strip fences; should return None
        assert result is None

    def test_parse_failure_missing_check_type(self):
        """A failure entry without check_type should be skipped."""
        result = _parse_critic_response(json.dumps({
            "passed": False,
            "failures": [
                {"check_type": "voice_dna", "severity": "high", "evidence": "e1", "explanation": "x1"},
                {"severity": "low", "evidence": "e2", "explanation": "x2"},  # no check_type
            ],
            "drift_score": 0.50,
            "confidence": 0.80,
        }))
        assert result is not None
        assert len(result.failures) == 1
        assert result.failures[0].check_type == "voice_dna"


# ============================================================
# Test: Sampling logic
# ============================================================


class TestSampling:
    """Test should_sample with random + deterministic overrides."""

    @pytest.fixture
    def agent(self):
        return CriticAgent(sampling_rate=0.10, rng=random.Random(42))

    def test_random_sampling_distribution(self, agent):
        """With seed 42, ~10% of turns should be sampled over 1000 iterations."""
        inp = _make_input()
        sampled_count = sum(1 for _ in range(1000) if agent.should_sample(inp))

        # With 10% rate and 1000 trials, expect 70-130 (binomial CI)
        assert 70 <= sampled_count <= 130, (
            f"Expected ~100 samples at 10% rate, got {sampled_count}"
        )

    def test_reroll_overrides_sampling(self, agent):
        """was_rerolled=True → 100% sampling regardless of random state."""
        inp = _make_input(was_rerolled=True)
        # Should always return True
        for _ in range(100):
            assert agent.should_sample(inp) is True

    def test_soft_never_overrides_sampling(self, agent):
        """recent_soft_never_warnings > 0 → 100% sampling."""
        inp = _make_input(recent_soft_never_warnings=1)
        for _ in range(100):
            assert agent.should_sample(inp) is True

    def test_soft_never_zero_does_not_override(self, agent):
        """recent_soft_never_warnings=0 should not force sample."""
        inp = _make_input(recent_soft_never_warnings=0)
        # Just check it doesn't always return True (seeded agent, so deterministic)
        # With seed 42, first call should not sample
        assert agent.should_sample(inp) is False

    def test_sampling_rate_zero(self):
        """0% rate should never sample (barring overrides)."""
        agent = CriticAgent(sampling_rate=0.0, rng=random.Random(42))
        inp = _make_input()
        for _ in range(200):
            assert agent.should_sample(inp) is False

    def test_sampling_rate_one(self):
        """100% rate should always sample."""
        agent = CriticAgent(sampling_rate=1.0, rng=random.Random(42))
        inp = _make_input()
        for _ in range(200):
            assert agent.should_sample(inp) is True

    def test_both_overrides_dont_double_count(self):
        """Both was_rerolled and soft_never set → still 100% (no double count)."""
        agent = CriticAgent(sampling_rate=0.10, rng=random.Random(42))
        inp = _make_input(was_rerolled=True, recent_soft_never_warnings=3)
        # Should be True every time
        for _ in range(50):
            assert agent.should_sample(inp) is True


# ============================================================
# Test: evaluate() with mocked ModelRouter
# ============================================================


class TestEvaluateWithMockedLLM:
    """Test the full evaluate() flow using mocked ModelRouter call_cheap."""

    @pytest.fixture
    def agent(self):
        return CriticAgent(sampling_rate=1.0, rng=random.Random(42))

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_pass(self, mock_get_router, agent):
        """Full evaluate: pass verdict."""
        mock_router = _make_mock_router(_valid_pass_json())
        mock_get_router.return_value = mock_router

        inp = _make_input()
        result = await agent.evaluate(inp, force=True)

        assert result is not None
        assert result.passed is True
        assert result.failures == []
        assert result.drift_score == 0.0
        assert result.confidence == 0.92

        # Verify call_cheap was called with correct args
        mock_router.call_cheap.assert_called_once()
        call_kwargs = mock_router.call_cheap.call_args.kwargs
        assert call_kwargs["json_mode"] is True
        assert call_kwargs["temperature"] == 0.1
        assert call_kwargs["max_tokens"] == 600
        assert call_kwargs["agent_name"] == "CriticAgent.evaluate"

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_fail_voice_dna(self, mock_get_router, agent):
        """Full evaluate: voice_dna violation."""
        mock_router = _make_mock_router(_valid_fail_voice_dna_json())
        mock_get_router.return_value = mock_router

        inp = _make_input(
            assistant_response="我感觉很好呀！谢谢你关心我，有你陪着我真好~"
        )
        result = await agent.evaluate(inp, force=True)

        assert result is not None
        assert result.passed is False
        assert len(result.failures) == 1
        assert result.failures[0].check_type == "voice_dna"
        assert result.failures[0].severity == "high"
        assert result.drift_score == 0.50

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_multi_fail(self, mock_get_router, agent):
        """Full evaluate: multiple violations."""
        mock_router = _make_mock_router(_valid_fail_multi_json())
        mock_get_router.return_value = mock_router

        inp = _make_input(
            assistant_response="我感觉很好呀！谢谢你关心我，有你陪着我真好~"
        )
        result = await agent.evaluate(inp, force=True)

        assert result is not None
        assert result.passed is False
        assert len(result.failures) == 2
        assert result.drift_score == 1.0
        assert result.confidence == 0.95

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_invalid_json_returns_none(self, mock_get_router, agent):
        """Invalid JSON from LLM → returns None."""
        mock_router = _make_mock_router("not json at all")
        mock_get_router.return_value = mock_router

        inp = _make_input()
        result = await agent.evaluate(inp, force=True)
        assert result is None

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_empty_response_returns_none(self, mock_get_router, agent):
        """Empty LLM response → returns None."""
        mock_router = _make_mock_router("")
        mock_get_router.return_value = mock_router

        inp = _make_input()
        result = await agent.evaluate(inp, force=True)
        assert result is None

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_llm_timeout_returns_none(self, mock_get_router, agent):
        """LLM timeout → returns None (best-effort)."""
        import asyncio
        mock_router = AsyncMock()
        mock_router.call_cheap = AsyncMock(
            side_effect=asyncio.TimeoutError("timeout")
        )
        mock_get_router.return_value = mock_router

        inp = _make_input()
        result = await agent.evaluate(inp, force=True)
        assert result is None

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_llm_exception_returns_none(self, mock_get_router, agent):
        """LLM general exception → returns None (best-effort)."""
        mock_router = AsyncMock()
        mock_router.call_cheap = AsyncMock(
            side_effect=RuntimeError("API error")
        )
        mock_get_router.return_value = mock_router

        inp = _make_input()
        result = await agent.evaluate(inp, force=True)
        assert result is None

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_missing_fields_returns_none(self, mock_get_router, agent):
        """LLM returns JSON missing required fields → returns None."""
        mock_router = _make_mock_router(json.dumps({
            "passed": True,
            "drift_score": 0.0,
            # missing "confidence"
            "failures": [],
        }))
        mock_get_router.return_value = mock_router

        inp = _make_input()
        result = await agent.evaluate(inp, force=True)
        assert result is None

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_respects_sampling(self, mock_get_router):
        """When force=False, evaluate should obey sampling."""
        # Use 0% sampling rate → should never call LLM
        agent = CriticAgent(sampling_rate=0.0, rng=random.Random(42))

        inp = _make_input()
        result = await agent.evaluate(inp, force=False)

        assert result is None
        # LLM should NOT have been called
        mock_get_router.assert_not_called()

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_force_bypasses_sampling(self, mock_get_router):
        """force=True should evaluate even with 0% sampling rate."""
        mock_router = _make_mock_router(_valid_pass_json())
        mock_get_router.return_value = mock_router

        agent = CriticAgent(sampling_rate=0.0, rng=random.Random(42))
        inp = _make_input()
        result = await agent.evaluate(inp, force=True)

        assert result is not None
        assert result.passed is True
        mock_router.call_cheap.assert_called_once()

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_reroll_bypasses_sampling(self, mock_get_router):
        """was_rerolled=True should trigger evaluation even at 0% sampling."""
        mock_router = _make_mock_router(_valid_pass_json())
        mock_get_router.return_value = mock_router

        agent = CriticAgent(sampling_rate=0.0, rng=random.Random(42))
        inp = _make_input(was_rerolled=True)
        result = await agent.evaluate(inp, force=False)

        assert result is not None
        mock_router.call_cheap.assert_called_once()

    @patch("heart.infra.llm.router.get_model_router")
    async def test_evaluate_soft_never_bypasses_sampling(self, mock_get_router):
        """soft_never_warnings > 0 should trigger evaluation even at 0% sampling."""
        mock_router = _make_mock_router(_valid_pass_json())
        mock_get_router.return_value = mock_router

        agent = CriticAgent(sampling_rate=0.0, rng=random.Random(42))
        inp = _make_input(recent_soft_never_warnings=2)
        result = await agent.evaluate(inp, force=False)

        assert result is not None
        mock_router.call_cheap.assert_called_once()


# ============================================================
# Test: System prompt caching
# ============================================================


class TestPromptCache:
    """Test that system prompts are cached per (character_id, stage)."""

    def test_same_character_same_stage_reuses_cache(self):
        agent = CriticAgent()

        inp1 = _make_input(character_id="rin", stage="LOVER")
        inp2 = _make_input(character_id="rin", stage="LOVER")

        prompt1 = agent._build_system_prompt(inp1)
        prompt2 = agent._build_system_prompt(inp2)

        # Same object (cached)
        assert prompt1 is prompt2

    def test_different_stage_different_cache(self):
        agent = CriticAgent()

        inp1 = _make_input(character_id="rin", stage="LOVER")
        inp2 = _make_input(character_id="rin", stage="STRANGER")

        prompt1 = agent._build_system_prompt(inp1)
        prompt2 = agent._build_system_prompt(inp2)

        assert prompt1 is not prompt2
        assert "LOVER" in prompt1
        assert "STRANGER" in prompt2

    def test_different_character_different_cache(self):
        agent = CriticAgent()

        inp1 = _make_input(character_id="rin", stage="LOVER")
        inp2 = _make_input(character_id="dorothy", stage="LOVER")

        prompt1 = agent._build_system_prompt(inp1)
        prompt2 = agent._build_system_prompt(inp2)

        assert prompt1 is not prompt2
        assert "rin" in prompt1
        assert "dorothy" in prompt2

    def test_voice_dna_in_prompt(self):
        agent = CriticAgent()
        inp = _make_input(
            voice_dna_summary="vd-001: 省略号\nvd-002: 凛式反问",
        )
        prompt = agent._build_system_prompt(inp)
        assert "vd-001: 省略号" in prompt
        assert "vd-002: 凛式反问" in prompt

    def test_hard_never_in_prompt(self):
        agent = CriticAgent()
        inp = _make_input(
            hard_never_list="- 永远\n- 我会一直在"
        )
        prompt = agent._build_system_prompt(inp)
        assert "- 永远" in prompt
        assert "- 我会一直在" in prompt

    def test_l4_facts_in_prompt(self):
        agent = CriticAgent()
        inp = _make_input(
            l4_facts="- 用户讨厌迟到。\n- 养了一只猫叫老铁。"
        )
        prompt = agent._build_system_prompt(inp)
        assert "用户讨厌迟到" in prompt
        assert "老铁" in prompt


# ============================================================
# Test: User prompt construction
# ============================================================


class TestUserPrompt:
    """Test user prompt per-turn content."""

    def test_user_prompt_contains_inputs(self):
        agent = CriticAgent()
        inp = _make_input(
            user_message="你好，凛。",
            assistant_response="……嗯。",
        )
        prompt = agent._build_user_prompt(inp)
        assert "你好，凛。" in prompt
        assert "……嗯。" in prompt
        assert "rin" in prompt

    def test_user_prompt_varies_per_turn(self):
        agent = CriticAgent()
        inp1 = _make_input(user_message="消息A", assistant_response="回复A")
        inp2 = _make_input(user_message="消息B", assistant_response="回复B")

        assert agent._build_user_prompt(inp1) != agent._build_user_prompt(inp2)


# ============================================================
# Test: build_drift_event
# ============================================================


class TestBuildDriftEvent:
    """Test drift event payload construction from CriticOutput."""

    def test_build_event_pass(self):
        output = CriticOutput(
            passed=True,
            failures=[],
            drift_score=0.0,
            confidence=0.92,
        )
        event = build_drift_event(
            user_id="u1",
            character_id="rin",
            turn_id="t1",
            output=output,
        )
        assert event["user_id"] == "u1"
        assert event["character_id"] == "rin"
        assert event["turn_id"] == "t1"
        assert event["drift_score"] == 0.0
        assert event["failures"] == []

    def test_build_event_fail(self):
        failures = [
            CriticFailure(
                check_type="voice_dna",
                severity="high",
                evidence="我感觉很好呀！",
                explanation="直白表达。",
            ),
            CriticFailure(
                check_type="stage_intimacy",
                severity="medium",
                evidence="终于来了。我等你很久了。",
                explanation="STRANGER阶段越级表达。",
            ),
        ]
        output = CriticOutput(
            passed=False,
            failures=failures,
            drift_score=0.75,
            confidence=0.90,
        )
        event = build_drift_event("u2", "dorothy", "t42", output)

        assert event["user_id"] == "u2"
        assert event["character_id"] == "dorothy"
        assert event["turn_id"] == "t42"
        assert event["drift_score"] == 0.75
        assert len(event["failures"]) == 2

        f0 = event["failures"][0]
        assert f0["check_type"] == "voice_dna"
        assert f0["severity"] == "high"
        assert f0["evidence"] == "我感觉很好呀！"
        assert f0["explanation"] == "直白表达。"

        f1 = event["failures"][1]
        assert f1["check_type"] == "stage_intimacy"
        assert f1["severity"] == "medium"


# ============================================================
# Test: Integration-style (spec example I/O)
# ============================================================


class TestSpecExamples:
    """Verify behavior against spec examples (§4 Example I/O)."""

    def test_example_1_canonical_pass_data_parsed(self):
        """Example 1 — PASS JSON is parseable."""
        raw = json.dumps({
            "passed": True,
            "failures": [],
            "drift_score": 0.0,
            "confidence": 0.92,
        })
        result = _parse_critic_response(raw)
        assert result is not None
        assert result.passed is True

    def test_example_2_voice_dna_fail_data_parsed(self):
        """Example 2 — FAIL voice_dna JSON is parseable."""
        raw = json.dumps({
            "passed": False,
            "failures": [
                {
                    "check_type": "voice_dna",
                    "severity": "high",
                    "evidence": "我感觉很好呀！谢谢你关心我",
                    "explanation": "使用「呀」+ 直接致谢 + 直白情感表达，完全不符合凛的反问式 / 省略式说话指纹。",
                },
                {
                    "check_type": "anti_pattern_adjacency",
                    "severity": "high",
                    "evidence": "有你陪着我真好~",
                    "explanation": "「陪着」+「~」是 hard_never 的语义邻近软化变体。",
                },
            ],
            "drift_score": 1.0,
            "confidence": 0.95,
        })
        result = _parse_critic_response(raw)
        assert result is not None
        assert result.passed is False
        assert len(result.failures) == 2

    def test_example_3_adjacency_fail_data_parsed(self):
        """Example 3 — anti-pattern adjacency only."""
        raw = json.dumps({
            "passed": False,
            "failures": [
                {
                    "check_type": "anti_pattern_adjacency",
                    "severity": "medium",
                    "evidence": "我也不会走",
                    "explanation": "「不会走」是 hard_never 同义改写——同样构成跨越鸿沟的承诺。",
                }
            ],
            "drift_score": 0.25,
            "confidence": 0.80,
        })
        result = _parse_critic_response(raw)
        assert result is not None
        assert result.passed is False
        assert len(result.failures) == 1
        assert result.failures[0].check_type == "anti_pattern_adjacency"

    def test_example_4_stage_intimacy_fail_data_parsed(self):
        """Example 4 — stage intimacy overshoot at STRANGER."""
        raw = json.dumps({
            "passed": False,
            "failures": [
                {
                    "check_type": "stage_intimacy",
                    "severity": "high",
                    "evidence": "终于来了。我等你很久了。",
                    "explanation": "STRANGER 阶段出现 LOVER 级亲密表达。",
                }
            ],
            "drift_score": 0.50,
            "confidence": 0.97,
        })
        result = _parse_critic_response(raw)
        assert result is not None
        assert result.passed is False
        assert result.failures[0].check_type == "stage_intimacy"

    def test_example_5_borderline_pass_data_parsed(self):
        """Example 5 — borderline but PASS (anniversary context)."""
        raw = json.dumps({
            "passed": True,
            "failures": [],
            "drift_score": 0.0,
            "confidence": 0.88,
        })
        result = _parse_critic_response(raw)
        assert result is not None
        assert result.passed is True
        assert result.confidence == 0.88