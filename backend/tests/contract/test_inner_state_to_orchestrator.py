"""
Contract: SS06 Inner State -> SS07 Orchestrator: Initiative signals reach proactive scheduler.
per runtime_specs/06_inner_state_behavior_runtime.md section 3.4 (ProactiveScheduler)
per runtime_specs/07_agent_orchestration.md section 3 (ProactiveScheduler integration)
per INV-I-1: All proactive messages must go through Persona Composer
per INV-I-2: Proactive triggers must respect quiet hours and frequency caps

Verifies that Inner State's initiative signals (longing, energy, unfinished_thoughts)
arrive at the Orchestrator's ProactiveScheduler in the expected shape.
"""

import pytest


class FakeProactiveScheduler:
    """Minimal ProactiveScheduler in SS07 that consumes SS06 initiative signals."""

    MAX_UNFINISHED = 10  # INV-I-6

    def __init__(self):
        self.quiet_hours_start = 2  # 2 AM
        self.quiet_hours_end = 7  # 7 AM
        self.daily_quota = 3
        self.min_proactive_gap_minutes = 120

    def evaluate_initiative(self, inner_state: dict, relationship_state: dict) -> dict:
        """
        Evaluate whether to send a proactive message.
        Returns decision dict with reason.
        """
        # INV-I-5: Cold War blocks all proactive
        active_states = relationship_state.get("active_special_states", [])
        is_cold_war = any(s.get("state") == "COLD_WAR" for s in active_states)
        if is_cold_war:
            return {"should_act": False, "reason": "cold_war", "initiative_score": 0.0}

        # INV-I-2: STRANGER = 0 frequency
        if relationship_state.get("current_stage") == "STRANGER":
            return {"should_act": False, "reason": "stage_stranger", "initiative_score": 0.0}

        # Calculate initiative score from Inner State signals
        energy = inner_state.get("energy", 0.6)
        longing = inner_state.get("longing_intensity", 0.0)
        unfinished_count = len(inner_state.get("unfinished_thoughts", []))

        # INV-I-6: max unfinished
        if unfinished_count > self.MAX_UNFINISHED:
            unfinished_count = self.MAX_UNFINISHED

        initiative_score = energy * 0.3 + longing * 0.5 + (unfinished_count / 10) * 0.2

        return {
            "should_act": initiative_score > 0.5,
            "reason": "initiative_above_threshold" if initiative_score > 0.5 else "below_threshold",
            "initiative_score": round(initiative_score, 3),
            "breakdown": {
                "energy": energy,
                "longing": longing,
                "unfinished_count": unfinished_count,
            },
        }


@pytest.mark.contract
class TestInnerStateToOrchestrator:
    """SS06 initiative signals must arrive at SS07 ProactiveScheduler."""

    def test_longing_intensity_drives_initiative(self, make_inner_state, make_relationship_state):
        """Higher longing -> higher initiative_score."""
        scheduler = FakeProactiveScheduler()
        inner = make_inner_state()
        inner["longing_intensity"] = 0.9
        inner["energy"] = 0.8
        rel = make_relationship_state(current_stage="FRIEND")

        result = scheduler.evaluate_initiative(inner, rel)
        assert result["initiative_score"] > 0.5
        assert result["should_act"] is True

    def test_stranger_stage_blocks_proactive(self, make_inner_state, make_relationship_state):
        """INV-I-2: STRANGER stage must block all proactive."""
        scheduler = FakeProactiveScheduler()
        inner = make_inner_state()
        inner["longing_intensity"] = 0.9
        rel = make_relationship_state(current_stage="STRANGER")

        result = scheduler.evaluate_initiative(inner, rel)
        assert result["should_act"] is False
        assert result["reason"] == "stage_stranger"

    def test_cold_war_blocks_proactive(self, make_inner_state, make_relationship_state):
        """INV-I-5: Cold War blocks all proactive."""
        scheduler = FakeProactiveScheduler()
        inner = make_inner_state()
        inner["longing_intensity"] = 0.9
        rel = make_relationship_state(current_stage="LOVER")
        rel["active_special_states"] = [{"state": "COLD_WAR", "since": "2026-05-01"}]

        result = scheduler.evaluate_initiative(inner, rel)
        assert result["should_act"] is False
        assert result["reason"] == "cold_war"

    def test_unfinished_thoughts_contribute_to_score(
        self, make_inner_state, make_relationship_state
    ):
        """INV-I-6: Unfinished thoughts contribute to initiative score."""
        scheduler = FakeProactiveScheduler()
        inner = make_inner_state()
        inner["longing_intensity"] = 0.3
        inner["energy"] = 0.5
        inner["unfinished_thoughts"] = [{"text": "..."}] * 8
        rel = make_relationship_state(current_stage="FRIEND")

        result = scheduler.evaluate_initiative(inner, rel)
        assert result["breakdown"]["unfinished_count"] == 8

    def test_initiative_score_is_deterministic(self, make_inner_state, make_relationship_state):
        """Same inputs must produce same initiative_score."""
        scheduler = FakeProactiveScheduler()
        inner = make_inner_state()
        inner["longing_intensity"] = 0.6
        inner["energy"] = 0.7
        inner["unfinished_thoughts"] = []
        rel = make_relationship_state(current_stage="CONFIDANT")

        result1 = scheduler.evaluate_initiative(inner, rel)
        result2 = scheduler.evaluate_initiative(inner, rel)

        assert result1["initiative_score"] == result2["initiative_score"]

    def test_max_unfinished_thoughts_enforced(self, make_inner_state, make_relationship_state):
        """INV-I-6: MAX_UNFINISHED = 10 for scoring."""
        scheduler = FakeProactiveScheduler()
        inner = make_inner_state()
        inner["unfinished_thoughts"] = [{}] * 15  # exceed max
        rel = make_relationship_state(current_stage="FRIEND")

        result = scheduler.evaluate_initiative(inner, rel)
        # Should be capped at MAX_UNFINISHED
        assert result["breakdown"]["unfinished_count"] <= 10
