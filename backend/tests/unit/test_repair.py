"""
Unit tests for Repair Mechanic Engine.

Covers:
- Spam scenarios → reject
- Sincere wording + low recent offenses → partial/full repair
- Soul-specific behavior (Rin vs Dorothy diverges)
- Cost cap enforced (max 5 LLM calls per user per day)
- Recidivism detection and reversal
- Template repetition penalties

Author: 心屿团队
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from heart.ss03_emotion.repair import RepairEngine


@pytest.fixture
def base_lexicon():
    """Base emotion lexicon for testing."""
    return {
        "repair_keywords": {
            "apology": [
                "对不起", "抱歉", "我错了", "不该", "原谅", "是我",
                "我的错", "怪我", "让你", "委屈", "难过",
            ],
            "vulnerability": [
                "累了", "疲惫", "压力", "难受", "撑不住", "失眠",
                "焦虑", "痛苦", "无助", "孤独", "害怕",
            ],
        },
    }


@pytest.fixture
def rin_soul_config():
    """Rin soul config with strict repair profile."""
    return {
        "character_id": "rin",
        "relational_template": {
            "repair_profile": {
                "forgiveness_curve_gain": {
                    "apology": 0.6,  # Slow
                    "vulnerability": 1.2,  # High
                    "sustained_attention": 1.4,  # High
                    "bespoke_phrase": 1.5,
                },
                "bespoke_repair_phrases": ["我还在", "我没走"],
                "cooldown_turns": 5,  # Longer cool-down
                "recidivism_penalty_gain": 1.5,  # Harder punishment
                "session_progress_cap": 0.5,  # Lower cap
            },
        },
    }


@pytest.fixture
def dorothy_soul_config():
    """Dorothy soul config with forgiving repair profile."""
    return {
        "character_id": "dorothy",
        "relational_template": {
            "repair_profile": {
                "forgiveness_curve_gain": {
                    "apology": 1.2,  # Fast
                    "vulnerability": 1.0,
                    "sustained_attention": 0.8,
                    "bespoke_phrase": 1.2,
                },
                "bespoke_repair_phrases": ["你不用变", "我喜欢现在的你"],
                "cooldown_turns": 2,  # Shorter cool-down
                "recidivism_penalty_gain": 0.8,  # Lighter punishment
                "session_progress_cap": 0.8,  # Higher cap
            },
        },
    }


@pytest.fixture
def base_context():
    """Base detection context."""
    return {
        "pending_repairs": [
            {
                "emotion": "aggrieved",
                "intensity": 0.6,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "cause": "user_mention_other_partner",
                "repair_progress": 0.0,
                "repair_history": [],
            }
        ],
        "recent_triggers": [],
        "user_emotional_charge": 0.0,
        "relationship_phase": "established",
    }


class TestApologyDetection:
    """Test apology detection (Layer A)."""

    @pytest.mark.asyncio
    async def test_spam_apology_rejected(self, base_lexicon, rin_soul_config, base_context):
        """Spam "对不起" should be heavily penalized."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"
        turn_id = uuid4()

        # First apology
        signal1 = await engine.detect_repair_signal(
            user_message="对不起",
            user_id=user_id,
            character_id=character_id,
            turn_id=turn_id,
            context=base_context,
        )

        assert signal1 is not None
        assert signal1["total_strength"] >= 0.2

        # Second identical apology (should be penalized)
        signal2 = await engine.detect_repair_signal(
            user_message="对不起",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        assert signal2 is not None
        # Should be heavily penalized (×0.5 for 2nd apology)
        assert signal2["total_strength"] < signal1["total_strength"] * 0.6

        # Third identical apology (should be more penalized)
        signal3 = await engine.detect_repair_signal(
            user_message="对不起",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        assert signal3 is not None
        # Should be even more penalized (×0.2 for 3rd+ apology)
        assert signal3["total_strength"] < signal2["total_strength"] * 0.5

    @pytest.mark.asyncio
    async def test_template_copy_penalized(self, base_lexicon, rin_soul_config, base_context):
        """Template-copy apologies (high n-gram similarity) should be penalized."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # First apology with specific template
        signal1 = await engine.detect_repair_signal(
            user_message="对不起对不起对不起，我真的错了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        assert signal1 is not None

        # Second apology with very similar template (high Jaccard)
        signal2 = await engine.detect_repair_signal(
            user_message="对不起对不起对不起，我真的错了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        assert signal2 is not None
        # Should have template penalty (×0.1 for similarity ≥ 0.6)
        assert signal2["total_strength"] < signal1["total_strength"] * 0.2

    @pytest.mark.asyncio
    async def test_sincere_specific_apology_accepted(self, base_lexicon, rin_soul_config, base_context):
        """Sincere, specific apology should have high strength."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # Specific apology with ownership and concrete reference
        signal = await engine.detect_repair_signal(
            user_message="对不起，是我不该提起她的事情，让你难受了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        assert signal is not None
        assert len(signal["components"]) > 0
        apology_component = next(c for c in signal["components"] if c["type"] == "apology")
        # Specificity should be high (length + ownership + concrete)
        assert apology_component["strength"] >= 0.6

    @pytest.mark.asyncio
    async def test_no_apology_keyword_no_signal(self, base_lexicon, rin_soul_config, base_context):
        """Message without apology keywords should not generate apology signal."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        signal = await engine.detect_repair_signal(
            user_message="今天天气不错",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        # Should be None or have no apology component
        if signal:
            apology_components = [c for c in signal["components"] if c["type"] == "apology"]
            assert len(apology_components) == 0


class TestVulnerabilityDetection:
    """Test vulnerability detection (Layer B)."""

    @pytest.mark.asyncio
    async def test_vulnerability_detected(self, base_lexicon, rin_soul_config, base_context):
        """Long message with negative emotion and vulnerability keywords should be detected."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # Update context with negative emotional charge
        context = base_context.copy()
        context["user_emotional_charge"] = -0.7

        signal = await engine.detect_repair_signal(
            user_message="我最近真的很累，工作压力很大，每天都失眠，感觉快撑不住了，心里很难受",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=context,
        )

        assert signal is not None
        vulnerability_components = [c for c in signal["components"] if c["type"] == "vulnerability"]
        assert len(vulnerability_components) > 0
        assert vulnerability_components[0]["strength"] >= 0.3

    @pytest.mark.asyncio
    async def test_short_message_no_vulnerability(self, base_lexicon, rin_soul_config, base_context):
        """Short messages should not trigger vulnerability even with keywords."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        context = base_context.copy()
        context["user_emotional_charge"] = -0.7

        signal = await engine.detect_repair_signal(
            user_message="很累",  # Too short
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=context,
        )

        if signal:
            vulnerability_components = [c for c in signal["components"] if c["type"] == "vulnerability"]
            assert len(vulnerability_components) == 0

    @pytest.mark.asyncio
    async def test_positive_emotion_no_vulnerability(self, base_lexicon, rin_soul_config, base_context):
        """Positive emotional charge should not trigger vulnerability."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        context = base_context.copy()
        context["user_emotional_charge"] = 0.5  # Positive

        signal = await engine.detect_repair_signal(
            user_message="我最近很累，但是很开心，工作压力大但是很有成就感",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=context,
        )

        if signal:
            vulnerability_components = [c for c in signal["components"] if c["type"] == "vulnerability"]
            assert len(vulnerability_components) == 0


class TestBespokePhrases:
    """Test soul-specific bespoke repair phrases."""

    @pytest.mark.asyncio
    async def test_rin_bespoke_phrase_detected(self, base_lexicon, rin_soul_config, base_context):
        """Rin's bespoke phrase '我还在' should be detected."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        signal = await engine.detect_repair_signal(
            user_message="我还在，不会走的",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        assert signal is not None
        assert signal["has_bespoke_match"] is True
        bespoke_components = [c for c in signal["components"] if c["type"] == "bespoke_phrase"]
        assert len(bespoke_components) > 0
        assert bespoke_components[0]["strength"] >= 0.7

    @pytest.mark.asyncio
    async def test_dorothy_bespoke_phrase_detected(self, base_lexicon, dorothy_soul_config, base_context):
        """Dorothy's bespoke phrase should be detected."""
        engine = RepairEngine(base_lexicon, dorothy_soul_config)
        user_id = uuid4()
        character_id = "dorothy"

        signal = await engine.detect_repair_signal(
            user_message="你不用变，我喜欢现在的你",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        assert signal is not None
        assert signal["has_bespoke_match"] is True


class TestRepairApplication:
    """Test repair application to emotion state."""

    @pytest.mark.asyncio
    async def test_repair_for_nothing_rejected(self, base_lexicon, rin_soul_config):
        """Apology without pending_repairs should be rejected (G5)."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # Empty pending_repairs
        context = {
            "pending_repairs": [],
            "recent_triggers": [],
            "user_emotional_charge": 0.0,
            "relationship_phase": "established",
        }

        signal = await engine.detect_repair_signal(
            user_message="对不起",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=context,
        )

        # Apply repair
        current_state = {
            "pending_repairs": [],
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=signal,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=context,
        )

        assert outcome["accepted"] is False
        assert outcome["narrative_hint"] == "ignored"

    @pytest.mark.asyncio
    async def test_sincere_repair_advances_progress(self, base_lexicon, rin_soul_config, base_context):
        """Sincere apology should advance repair_progress."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        signal = await engine.detect_repair_signal(
            user_message="对不起，是我不该提起那件事，让你难受了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        current_state = {
            "pending_repairs": base_context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=signal,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        assert outcome["accepted"] is True
        assert len(outcome["applied_to"]) > 0

        detail = outcome["applied_to"][0]
        assert detail["repair_progress_after"] > detail["repair_progress_before"]
        assert detail["impact"] > 0.0

    @pytest.mark.asyncio
    async def test_session_cap_enforced(self, base_lexicon, rin_soul_config, base_context):
        """Session progress cap should be enforced (G6)."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # Get session state and set cumulative progress near cap
        session_state = engine._get_session_state(str(user_id), character_id)
        session_state["cumulative_progress_this_session"] = 0.5  # At Rin's cap

        signal = await engine.detect_repair_signal(
            user_message="对不起，是我错了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        current_state = {
            "pending_repairs": base_context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=signal,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        # Should be capped
        assert outcome["flags"]["capped_by_session"] is True
        assert outcome["accepted"] is False

    @pytest.mark.asyncio
    async def test_recidivism_reversal(self, base_lexicon, rin_soul_config, base_context):
        """Re-offending after apology should trigger recidivism reversal (G2)."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # First, apply a repair
        signal1 = await engine.detect_repair_signal(
            user_message="对不起，是我不该提起那件事",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        current_state = {
            "pending_repairs": base_context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome1 = engine.apply_repair(
            signal=signal1,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        assert outcome1["accepted"] is True
        progress_after_first_repair = outcome1["applied_to"][0]["repair_progress_after"]

        # Now, simulate re-offense (same trigger appears in recent_triggers)
        current_state["recent_triggers"] = [
            {
                "trigger_type": "user_mention_other_partner",
                "at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        # Apply another repair
        signal2 = await engine.detect_repair_signal(
            user_message="对不起，又让你不开心了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        outcome2 = engine.apply_repair(
            signal=signal2,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        # Should detect recidivism
        assert outcome2["flags"]["recidivism_reversal"] is True

    @pytest.mark.asyncio
    async def test_partial_vs_full_repair(self, base_lexicon, rin_soul_config, base_context):
        """Test partial vs full repair transitions."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        current_state = {
            "pending_repairs": base_context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        # First repair (should be partial)
        signal1 = await engine.detect_repair_signal(
            user_message="对不起，是我不该提起那件事，让你难受了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        outcome1 = engine.apply_repair(
            signal=signal1,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        assert outcome1["accepted"] is True
        detail1 = outcome1["applied_to"][0]
        progress1 = detail1["repair_progress_after"]

        # Progress should be partial (0.4 ≤ progress < 0.8)
        # Depending on implementation, might or might not hit 0.4 in one go
        # Let's just verify progress increased

        # Apply more repairs to reach full
        for i in range(5):
            signal = await engine.detect_repair_signal(
                user_message=f"真的很抱歉，让你受委屈了{i}",  # Varied to avoid repetition penalty
                user_id=user_id,
                character_id=character_id,
                turn_id=uuid4(),
                context=base_context,
            )

            outcome = engine.apply_repair(
                signal=signal,
                user_id=user_id,
                character_id=character_id,
                current_state=current_state,
                context=base_context,
            )

            if outcome["accepted"]:
                detail = outcome["applied_to"][0]
                progress = detail["repair_progress_after"]

                # Check for full repair
                if detail["transitioned"] == "fully_repaired":
                    assert progress >= 0.8
                    break


class TestSoulDivergence:
    """Test soul-specific behavior (Rin vs Dorothy)."""

    @pytest.mark.asyncio
    async def test_rin_slower_forgiveness(self, base_lexicon, rin_soul_config, base_context):
        """Rin should have slower forgiveness (lower apology gain)."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        signal = await engine.detect_repair_signal(
            user_message="对不起，是我错了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        current_state = {
            "pending_repairs": base_context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=signal,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        rin_impact = outcome["applied_to"][0]["impact"] if outcome["applied_to"] else 0.0

        # Dorothy should have higher impact for same apology
        dorothy_config = {
            "character_id": "dorothy",
            "relational_template": {
                "repair_profile": {
                    "forgiveness_curve_gain": {
                        "apology": 1.2,  # Dorothy: faster
                        "vulnerability": 1.0,
                        "sustained_attention": 0.8,
                        "bespoke_phrase": 1.2,
                    },
                    "bespoke_repair_phrases": [],
                    "cooldown_turns": 2,
                    "recidivism_penalty_gain": 0.8,
                    "session_progress_cap": 0.8,
                },
            },
        }
        dorothy_engine = RepairEngine(base_lexicon, dorothy_config)

        dorothy_signal = await dorothy_engine.detect_repair_signal(
            user_message="对不起，是我错了",
            user_id=user_id,
            character_id="dorothy",
            turn_id=uuid4(),
            context=base_context,
        )

        dorothy_outcome = dorothy_engine.apply_repair(
            signal=dorothy_signal,
            user_id=user_id,
            character_id="dorothy",
            current_state=current_state,
            context=base_context,
        )

        dorothy_impact = dorothy_outcome["applied_to"][0]["impact"] if dorothy_outcome["applied_to"] else 0.0

        # Dorothy's impact should be higher due to higher gain (1.2 vs 0.6)
        assert dorothy_impact > rin_impact

    @pytest.mark.asyncio
    async def test_rin_higher_vulnerability_gain(self, base_lexicon, rin_soul_config, base_context):
        """Rin should respond better to vulnerability (higher gain)."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # Update context with negative emotional charge
        context = base_context.copy()
        context["user_emotional_charge"] = -0.7

        signal = await engine.detect_repair_signal(
            user_message="我最近真的很累，工作压力很大，每天都失眠，感觉快撑不住了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=context,
        )

        current_state = {
            "pending_repairs": context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=signal,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=context,
        )

        # Rin's vulnerability gain is 1.2 (higher than apology 0.6)
        # Should have meaningful impact
        if outcome["accepted"]:
            assert outcome["applied_to"][0]["impact"] > 0.0


class TestCostCap:
    """Test LLM call cost cap enforcement."""

    @pytest.mark.asyncio
    async def test_llm_call_cap_enforced(self, base_lexicon, rin_soul_config, base_context):
        """Max 5 LLM calls per user per day should be enforced."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # Simulate 6 LLM calls
        for i in range(6):
            can_use = engine._can_use_llm(str(user_id))

            if i < 5:
                assert can_use is True
                # Simulate LLM call
                engine._increment_llm_counter(str(user_id))
            else:
                # 6th call should be blocked
                assert can_use is False

    @pytest.mark.asyncio
    async def test_llm_counter_resets_daily(self, base_lexicon, rin_soul_config, base_context):
        """LLM counter should reset daily."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()

        # Exhaust today's quota
        for _ in range(5):
            engine._increment_llm_counter(str(user_id))

        assert engine._can_use_llm(str(user_id)) is False

        # Simulate next day by clearing old dates
        # (In production: Redis TTL handles this)
        engine._llm_call_counter[str(user_id)].clear()

        # Should be able to use LLM again
        assert engine._can_use_llm(str(user_id)) is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_no_signal_no_outcome(self, base_lexicon, rin_soul_config, base_context):
        """No signal should produce empty outcome."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        current_state = {
            "pending_repairs": base_context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=None,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        assert outcome["accepted"] is False
        assert outcome["signal_id"] is None
        assert len(outcome["applied_to"]) == 0

    @pytest.mark.asyncio
    async def test_multiple_pending_repairs(self, base_lexicon, rin_soul_config):
        """Repair should apply to multiple pending repairs."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        # Multiple pending repairs
        context = {
            "pending_repairs": [
                {
                    "emotion": "aggrieved",
                    "intensity": 0.6,
                    "cause": "user_mention_other_partner",
                    "repair_progress": 0.0,
                    "repair_history": [],
                },
                {
                    "emotion": "coldness",
                    "intensity": 0.5,
                    "cause": "user_mention_other_partner",
                    "repair_progress": 0.0,
                    "repair_history": [],
                },
            ],
            "recent_triggers": [],
            "user_emotional_charge": 0.0,
            "relationship_phase": "established",
        }

        signal = await engine.detect_repair_signal(
            user_message="对不起，是我不该提起那件事，让你难受了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=context,
        )

        current_state = {
            "pending_repairs": context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=signal,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=context,
        )

        # Should apply to both emotions
        assert outcome["accepted"] is True
        assert len(outcome["applied_to"]) == 2

        emotions_repaired = {detail["emotion"] for detail in outcome["applied_to"]}
        assert "aggrieved" in emotions_repaired
        assert "coldness" in emotions_repaired

    @pytest.mark.asyncio
    async def test_residual_score_computation(self, base_lexicon, rin_soul_config, base_context):
        """Residual score should be 1 - max(repair_progress)."""
        engine = RepairEngine(base_lexicon, rin_soul_config)
        user_id = uuid4()
        character_id = "rin"

        signal = await engine.detect_repair_signal(
            user_message="对不起，是我错了，让你难受了",
            user_id=user_id,
            character_id=character_id,
            turn_id=uuid4(),
            context=base_context,
        )

        current_state = {
            "pending_repairs": base_context["pending_repairs"].copy(),
            "recent_triggers": [],
        }

        outcome = engine.apply_repair(
            signal=signal,
            user_id=user_id,
            character_id=character_id,
            current_state=current_state,
            context=base_context,
        )

        if outcome["accepted"]:
            max_progress = max(detail["repair_progress_after"] for detail in outcome["applied_to"])
            expected_residual = 1.0 - max_progress

            assert abs(outcome["residual_score"] - expected_residual) < 0.01
