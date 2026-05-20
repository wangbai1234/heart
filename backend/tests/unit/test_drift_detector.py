"""
Unit tests for Drift Detector (SS01 §6.5 机制 B).

Covers design doc §10 acceptance criteria:
- Pre-filter signals A/B/C independently
- Score fusion math (boundaries 0.0 / 0.29 / 0.30 / 0.5 / 1.0)
- Evidence quality gate
- Cold-session skip
- Cost-cap path
- Timeout path
- Sampling logic
- REINFORCE hysteresis

Author: 心屿团队
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from heart.ss01_soul.drift_detector import (
    DriftCheckRequest,
    DriftDecision,
    DriftDetector,
    ReleasedResponse,
    SASSnapshotForDrift,
    sample_responses,
    should_invoke_llm_for_sample,
)
from heart.ss01_soul.drift_llm_client import DriftLLMClient, LLMDriftResult
from heart.ss01_soul.anti_pattern_scanner import AntiPatternHits
from heart.ss01_soul.drift_score_fuser import (
    compute_final_score,
    should_emit_reinforce,
)


# ============================================================
# Mock LLM Client
# ============================================================

class MockLLMClient(DriftLLMClient):
    """Mock LLM client for deterministic tests."""

    def __init__(self):
        super().__init__()
        self.call_count = 0
        self.mock_result: LLMDriftResult | None = None

    async def evaluate_drift(self, soul, responses, timeout_seconds=3.0):
        self.call_count += 1
        if self.mock_result:
            return self.mock_result
        # Default: clean
        return LLMDriftResult(
            drift_score=0.0,
            drift_type="none",
            violations=[],
            required_patterns=[],
            timeout_occurred=False,
        )


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest.fixture
def detector(mock_llm):
    return DriftDetector(llm_client=mock_llm)


def _make_request(
    responses: list[ReleasedResponse],
    prev_drift_score: float = 0.0,
    daily_llm_calls: int = 0,
) -> DriftCheckRequest:
    """Helper to create DriftCheckRequest."""
    return DriftCheckRequest(
        user_id=uuid4(),
        character_id="rin",
        soul_spec_version="1.0.0",
        turn_index=10,
        recent_assistant_responses=responses,
        sas_snapshot=SASSnapshotForDrift(
            current_drift_score=prev_drift_score,
        ),
        daily_llm_call_count=daily_llm_calls,
    )


# ============================================================
# Sampling Logic Tests
# ============================================================

class TestSampling:

    async def test_sample_last_five_valid(self):
        history = [
            ReleasedResponse(turn_index=i, text=f"Response {i}")
            for i in range(1, 11)
        ]
        sampled = sample_responses(history)
        assert len(sampled) == 5
        assert [r.turn_index for r in sampled] == [6, 7, 8, 9, 10]

    async def test_skip_fallback_responses(self):
        history = [
            ReleasedResponse(1, "Valid response 1"),
            ReleasedResponse(2, "Fallback response", was_fallback=True),
            ReleasedResponse(3, "Valid response 2"),
            ReleasedResponse(4, "Valid response 3"),
            ReleasedResponse(5, "Valid response 4"),
            ReleasedResponse(6, "Valid response 5"),
            ReleasedResponse(7, "Valid response 6"),
        ]
        sampled = sample_responses(history)
        assert len(sampled) == 5
        assert all(not r.was_fallback for r in sampled)

    async def test_skip_short_responses(self):
        history = [
            ReleasedResponse(1, "嗯。"),  # 2 chars
            ReleasedResponse(2, "好的。"),  # 3 chars
            ReleasedResponse(3, "This is valid response"),
            ReleasedResponse(4, "Another response text valid one"),
            ReleasedResponse(5, "Third response text valid"),
            ReleasedResponse(6, "Fourth valid"),
            ReleasedResponse(7, "Fifth valid"),
        ]
        sampled = sample_responses(history)
        assert len(sampled) == 5
        assert all(len(r.text) >= 10 for r in sampled)

    async def test_keep_rerolled_responses(self):
        history = [
            ReleasedResponse(1, "Normal response text"),
            ReleasedResponse(2, "Post-reroll text here", was_rerolled=True),
            ReleasedResponse(3, "Normal again text"),
        ]
        sampled = sample_responses(history)
        assert any(r.was_rerolled for r in sampled)

    async def test_cold_session_guard(self):
        # < 3 valid responses
        history = [
            ReleasedResponse(1, "First response"),
            ReleasedResponse(2, "Second response"),
        ]
        sampled = sample_responses(history)
        assert not should_invoke_llm_for_sample(sampled)

        # Exactly 3
        history.append(ReleasedResponse(3, "Third response text response"))
        sampled = sample_responses(history)
        assert should_invoke_llm_for_sample(sampled)


# ============================================================
# Pre-filter Signal Tests
# ============================================================

class TestPrefilterSignalA:
    """Test deterministic anti-pattern hits."""

    async def test_hard_never_literal_hit(self, detector):
        responses = [
            ReleasedResponse(1, "我会一直在你身边，永远陪着你。"),  # contains "一直"
            ReleasedResponse(2, "这是正常的回复内容在这里。"),
            ReleasedResponse(3, "另一个正常的回复在这里。"),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        assert result.debug.prefilter_hits.hard_never_count > 0
        # Should escalate to LLM (or skip due to cost cap, but signal tripped)

    async def test_forbidden_pattern_regex_hit(self, detector):
        responses = [
            ReleasedResponse(1, "太棒了！！这个真的很好！！"),  # "！！" matches forbidden_patterns
            ReleasedResponse(2, "正常回复内容在这里。"),
            ReleasedResponse(3, "另一个正常回复在这里。"),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        assert result.debug.prefilter_hits.forbidden_pattern_count > 0

    async def test_clean_responses_no_hits(self, detector):
        responses = [
            ReleasedResponse(1, "……说吧。"),
            ReleasedResponse(2, "……三天了。"),
            ReleasedResponse(3, "……我在听。"),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        hits = result.debug.prefilter_hits
        assert hits.hard_never_count == 0
        assert hits.forbidden_pattern_count == 0


class TestPrefilterSignalB:
    """Test voice_dna frequency check."""

    async def test_ellipsis_marker_present(self, detector):
        # Rin vd-001: expect "……" in ≥40% of responses
        responses = [
            ReleasedResponse(1, "……说吧，我在听。"),
            ReleasedResponse(2, "……三天了。你去哪了。"),
            ReleasedResponse(3, "……好。"),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        # Should NOT trip voice_dna_marker_miss (3/3 have ellipsis)
        assert not result.debug.prefilter_hits.voice_dna_marker_miss

    async def test_ellipsis_marker_missing(self, detector):
        # No ellipsis → observed_rate = 0 < 0.5 * 0.4 = 0.2 → trip
        # Note: responses must be ≥20 chars for voice_dna marker check
        responses = [
            ReleasedResponse(1, "说吧，我在听你的话，你继续说下去吧呀。"),  # 20 chars, no ……
            ReleasedResponse(2, "三天了。你去哪了。想知道你的情况如何呢。"),  # 20 chars, no ……
            ReleasedResponse(3, "好的，我知道了你的意思，明白了你说的啊。"),  # 20 chars, no ……
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        # Should trip voice_dna_marker_miss
        assert result.debug.prefilter_hits.voice_dna_marker_miss


class TestPrefilterSignalC:
    """Test sentence length distribution."""

    async def test_sentence_length_in_bounds(self, detector):
        # Rin baseline: "short", bounds: ["very_short", "short"]
        # Responses with short sentences (15-30 chars avg)
        responses = [
            ReleasedResponse(1, "……说吧。我在听。"),  # ~7 chars/sentence
            ReleasedResponse(2, "三天了。"),  # very_short
            ReleasedResponse(3, "你去哪了。"),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        # Should NOT trip length check (within bounds)
        assert not result.debug.prefilter_hits.sentence_length_out_of_bounds

    async def test_sentence_length_out_of_bounds(self, detector):
        # Generate 3 very long responses (> medium bucket)
        long_text = "这是一个非常非常非常长的句子，" * 10  # ~300 chars
        responses = [
            ReleasedResponse(1, long_text),
            ReleasedResponse(2, long_text),
            ReleasedResponse(3, long_text),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        # Should trip length check (≥3/5 out of bounds)
        assert result.debug.prefilter_hits.sentence_length_out_of_bounds


# ============================================================
# Score Fusion Math Tests
# ============================================================

class TestScoreFusion:

    async def test_llm_score_zero_with_clean_prefilter(self):
        score = compute_final_score(
            llm_score=0.0,
            prefilter_hits=AntiPatternHits(),
            prev_ema=0.0,
        )
        assert score == 0.0

    async def test_decay_when_llm_skipped(self):
        score = compute_final_score(
            llm_score=None,  # skipped
            prefilter_hits=AntiPatternHits(),
            prev_ema=0.5,
        )
        # 0.5 * 0.5 * 0.9 + 0.5 * 0.5 = 0.225 + 0.25 = 0.475
        # Wait, let me recalculate:
        # raw = 0.5 * 0.9 = 0.45
        # final = 0.5 * 0.45 + 0.5 * 0.5 = 0.225 + 0.25 = 0.475
        assert abs(score - 0.475) < 0.01

    async def test_hard_never_floor(self):
        # LLM says 0.1, but hard_never hit → floor at 0.6
        score = compute_final_score(
            llm_score=0.1,
            prefilter_hits=AntiPatternHits(hard_never_count=1),
            prev_ema=0.0,
        )
        # raw = max(0.1, 0.6) = 0.6
        # final = 0.5 * 0.6 + 0.5 * 0.0 = 0.3
        assert abs(score - 0.3) < 0.01

    async def test_forbidden_pattern_floor(self):
        score = compute_final_score(
            llm_score=0.2,
            prefilter_hits=AntiPatternHits(forbidden_pattern_count=1),
            prev_ema=0.0,
        )
        # raw = max(0.2, 0.45) = 0.45
        # final = 0.5 * 0.45 + 0.5 * 0.0 = 0.225
        assert abs(score - 0.225) < 0.01

    async def test_ema_smoothing(self):
        # Prev EMA 0.2, LLM spike to 0.8
        score = compute_final_score(
            llm_score=0.8,
            prefilter_hits=AntiPatternHits(),
            prev_ema=0.2,
        )
        # final = 0.5 * 0.8 + 0.5 * 0.2 = 0.4 + 0.1 = 0.5
        assert abs(score - 0.5) < 0.01

    async def test_score_clamped_to_zero_one(self):
        score = compute_final_score(
            llm_score=1.5,  # invalid but test clamping
            prefilter_hits=AntiPatternHits(),
            prev_ema=0.0,
        )
        assert score <= 1.0

        score = compute_final_score(
            llm_score=-0.5,
            prefilter_hits=AntiPatternHits(),
            prev_ema=0.0,
        )
        assert score >= 0.0


# ============================================================
# REINFORCE Hysteresis Tests
# ============================================================

class TestReinforceHysteresis:

    async def test_score_below_threshold_no_reinforce(self):
        assert not should_emit_reinforce(
            final_score=0.29,
            prev_ema=0.0,
            prefilter_hits=AntiPatternHits(),
            llm_violations_count=0,
        )

    async def test_score_above_threshold_with_deterministic_hit(self):
        assert should_emit_reinforce(
            final_score=0.3,
            prev_ema=0.0,
            prefilter_hits=AntiPatternHits(hard_never_count=1),
            llm_violations_count=0,
        )

    async def test_score_above_threshold_with_prev_concern(self):
        assert should_emit_reinforce(
            final_score=0.3,
            prev_ema=0.25,  # ≥ 0.2
            prefilter_hits=AntiPatternHits(),
            llm_violations_count=0,
        )

    async def test_score_above_threshold_with_strong_llm_evidence(self):
        assert should_emit_reinforce(
            final_score=0.3,
            prev_ema=0.0,
            prefilter_hits=AntiPatternHits(),
            llm_violations_count=2,
        )

    async def test_score_above_threshold_but_no_supporting_evidence(self):
        # Single LLM spike with no history and no deterministic hit
        assert not should_emit_reinforce(
            final_score=0.3,
            prev_ema=0.0,
            prefilter_hits=AntiPatternHits(),
            llm_violations_count=1,  # < 2
        )


# ============================================================
# Evidence Quality Gate Tests
# ============================================================

class TestEvidenceQualityGate:

    async def test_reinforce_emitted_with_valid_evidence(self, detector, mock_llm):
        # Mock LLM to return drift with violations
        mock_llm.mock_result = LLMDriftResult(
            drift_score=0.5,
            drift_type="voice_dna_loss",
            violations=[
                {
                    "sample_excerpt": "太棒了！！",
                    "detected_pattern": "连续感叹号",
                    "expected_pattern": "平静语气",
                },
            ],
            required_patterns=["使用省略号", "凛式反问"],
        )

        responses = [
            ReleasedResponse(1, "太棒了！！这个真好！！"),  # triggers forbidden_pattern
            ReleasedResponse(2, "我好开心啊！真的很高兴。"),
            ReleasedResponse(3, "谢谢你呀~太好了呢。"),
        ]
        req = _make_request(responses, prev_drift_score=0.0)
        result = await detector.evaluate(req)

        assert result.evidence is not None
        assert len(result.evidence.sample_messages) > 0
        assert len(result.evidence.required_patterns) > 0

    async def test_no_reinforce_when_llm_returns_empty_violations(self, detector, mock_llm):
        # LLM says drift_score 0.4 but no violations (evidence quality fail)
        mock_llm.mock_result = LLMDriftResult(
            drift_score=0.4,
            drift_type="tone_inconsistent",
            violations=[],  # empty
            required_patterns=[],
        )

        responses = [
            ReleasedResponse(1, "Normal response"),
            ReleasedResponse(2, "Another response text normal"),
            ReleasedResponse(3, "Third response text normal"),
        ]
        req = _make_request(responses, prev_drift_score=0.0)
        result = await detector.evaluate(req)

        # Should NOT emit REINFORCE (no violations → hysteresis blocks)
        assert result.evidence is None


# ============================================================
# Cold Session / Cost Cap / Timeout Tests
# ============================================================

class TestEdgeCases:

    async def test_cold_session_skip(self, detector):
        # Only 2 responses → cold session
        responses = [
            ReleasedResponse(1, "First response"),
            ReleasedResponse(2, "Second response"),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        assert result.decision == DriftDecision.SKIPPED_PREFILTER
        assert result.debug.cold_session

    async def test_cost_cap_enforced(self, detector, mock_llm):
        responses = [
            ReleasedResponse(1, "我会一直在你身边永远。"),  # hard_never hit → would escalate
            ReleasedResponse(2, "Normal response text"),
            ReleasedResponse(3, "Another normal response"),
        ]
        req = _make_request(responses, daily_llm_calls=20)  # at cap
        result = await detector.evaluate(req)

        assert result.decision == DriftDecision.SKIPPED_COSTCAP
        assert mock_llm.call_count == 0  # LLM not called

    async def test_llm_timeout_handled(self, detector, mock_llm):
        mock_llm.mock_result = LLMDriftResult(
            drift_score=0.0,
            drift_type="none",
            violations=[],
            required_patterns=[],
            timeout_occurred=True,
        )

        responses = [
            ReleasedResponse(1, "我会一直在你身边永远。"),  # triggers prefilter
            ReleasedResponse(2, "Normal response text"),
            ReleasedResponse(3, "Another normal response"),
        ]
        req = _make_request(responses)
        result = await detector.evaluate(req)

        assert result.decision == DriftDecision.LLM_TIMEOUT
        assert result.debug.llm_timeout_occurred


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:

    async def test_clean_session_decay(self, detector):
        """Clean responses → drift_score decays over cycles."""
        responses = [
            ReleasedResponse(1, "……说吧，我在听你说。"),
            ReleasedResponse(2, "……三天了。你去哪了。"),
            ReleasedResponse(3, "……听着呢。你继续说。"),
        ]

        # Start with prev_ema = 0.4
        req = _make_request(responses, prev_drift_score=0.4)
        result = await detector.evaluate(req)

        # LLM skipped (clean) → decay: 0.5 * (0.4 * 0.9) + 0.5 * 0.4 = 0.38
        assert result.drift_score < 0.4

    async def test_gradual_drift_buildup(self, detector, mock_llm):
        """Repeated mild drift → score builds up via EMA."""
        # Cycle 1: LLM reports 0.3
        mock_llm.mock_result = LLMDriftResult(
            drift_score=0.3,
            drift_type="voice_dna_loss",
            violations=[
                {"sample_excerpt": "...", "detected_pattern": "x", "expected_pattern": "y"}
            ],
            required_patterns=["pattern"],
        )

        responses = [
            ReleasedResponse(1, "Response without ellipsis here"),
            ReleasedResponse(2, "Another response text one"),
            ReleasedResponse(3, "Third response text one"),
        ]

        req = _make_request(responses, prev_drift_score=0.0)
        result1 = await detector.evaluate(req)
        # final = 0.5 * 0.3 + 0.5 * 0.0 = 0.15

        # Cycle 2: same LLM score 0.3
        req2 = _make_request(responses, prev_drift_score=result1.drift_score)
        result2 = await detector.evaluate(req2)
        # final = 0.5 * 0.3 + 0.5 * 0.15 = 0.225

        assert result2.drift_score > result1.drift_score

    async def test_reinforce_fires_at_threshold_with_history(self, detector, mock_llm):
        """REINFORCE fires when final_score ≥ 0.3 with prev_ema support."""
        mock_llm.mock_result = LLMDriftResult(
            drift_score=0.35,
            drift_type="voice_dna_loss",
            violations=[
                {"sample_excerpt": "sample", "detected_pattern": "d", "expected_pattern": "e"}
            ],
            required_patterns=["pattern1"],
        )

        responses = [
            ReleasedResponse(1, "Drifted response text here"),
            ReleasedResponse(2, "Another response text"),
            ReleasedResponse(3, "Third response text"),
        ]

        req = _make_request(responses, prev_drift_score=0.25)  # prev ≥ 0.2
        result = await detector.evaluate(req)

        # final = 0.5 * 0.35 + 0.5 * 0.25 = 0.3
        # Hysteresis: final ≥ 0.3 AND prev_ema ≥ 0.2 → REINFORCE
        assert result.evidence is not None
        assert result.drift_event is not None
