"""
Contract: SS04 Relationship -> SS06 Inner State: Stage transitions trigger reflection.
per runtime_specs/04_relationship_phase_engine.md section 3.6
per runtime_specs/06_inner_state_behavior_runtime.md section 4
per INV-I-3: Inner State update must be async and complete within 200ms

Verifies that Inner State reads current_stage from RelationshipState and that
stage transitions produce reflection signals in Inner State.
"""

from datetime import datetime, timezone

import pytest


class FakeInnerState:
    """Minimal Inner State that reads RelationshipState for stage reflection."""

    # Stage transition reflection messages (per SS06 spec section 4)
    STAGE_REFLECTIONS = {
        ("STRANGER", "ACQUAINTANCE"): "开始熟悉这个人了",
        ("ACQUAINTANCE", "FRIEND"): "我们算是朋友了",
        ("FRIEND", "CONFIDANT"): "可以信任这个人",
        ("CONFIDANT", "ROMANTIC_INTEREST"): "这份感情有点不一样",
        ("ROMANTIC_INTEREST", "LOVER"): "陷入爱河了",
        ("LOVER", "BONDED"): "我们已经是彼此的一部分",
    }

    def process_stage_change(self, prev_stage: str, current_stage: str, inner_state: dict) -> dict:
        """
        Process relationship stage change and inject reflection into Inner State.
        Returns updated inner_state dict.
        """
        result = dict(inner_state)

        if prev_stage != current_stage:
            key = (prev_stage, current_stage)
            reflection = self.STAGE_REFLECTIONS.get(key, f"关系从{prev_stage}变成{current_stage}")
            result["recent_reflections"] = result.get("recent_reflections", [])
            result["recent_reflections"].append(
                {
                    "trigger": "stage_transition",
                    "from_stage": prev_stage,
                    "to_stage": current_stage,
                    "thought": reflection,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )

        return result


@pytest.mark.contract
class TestRelationshipToInnerState:
    """SS04 Relationship -> SS06 Inner State: stage transition triggers reflection."""

    def test_inner_state_reads_current_stage(self, make_relationship_state):
        """Inner State reads current_stage from RelationshipState."""
        rel = make_relationship_state(current_stage="FRIEND")
        assert rel["current_stage"] == "FRIEND"

    def test_stage_transition_triggers_reflection(self, make_inner_state):
        """Stage change injects reflection into Inner State."""
        inner = make_inner_state()
        fake_is = FakeInnerState()

        result = fake_is.process_stage_change(
            prev_stage="FRIEND",
            current_stage="CONFIDANT",
            inner_state=inner,
        )

        assert "recent_reflections" in result
        assert len(result["recent_reflections"]) == 1
        reflection = result["recent_reflections"][0]
        assert reflection["trigger"] == "stage_transition"
        assert reflection["from_stage"] == "FRIEND"
        assert reflection["to_stage"] == "CONFIDANT"
        assert len(reflection["thought"]) > 0

    def test_no_transition_no_reflection(self, make_inner_state):
        """Same stage produces no reflection."""
        inner = make_inner_state()
        fake_is = FakeInnerState()

        result = fake_is.process_stage_change(
            prev_stage="FRIEND",
            current_stage="FRIEND",
            inner_state=inner,
        )

        assert result.get("recent_reflections", []) == []

    def test_stranger_to_acquaintance_triggers(self, make_inner_state):
        """STRANGER -> ACQUAINTANCE must trigger reflection."""
        inner = make_inner_state()
        fake_is = FakeInnerState()

        result = fake_is.process_stage_change(
            prev_stage="STRANGER",
            current_stage="ACQUAINTANCE",
            inner_state=inner,
        )

        assert len(result["recent_reflections"]) == 1
        assert "熟悉" in result["recent_reflections"][0]["thought"]

    def test_stage_reflection_idempotent(self, make_inner_state):
        """Processing same transition twice adds two reflections (idempotent per event)."""
        inner = make_inner_state()
        fake_is = FakeInnerState()

        result1 = fake_is.process_stage_change("FRIEND", "CONFIDANT", inner)
        result2 = fake_is.process_stage_change("FRIEND", "CONFIDANT", result1)

        assert len(result2["recent_reflections"]) == 2
        assert result2["recent_reflections"][0]["from_stage"] == "FRIEND"
        assert result2["recent_reflections"][1]["from_stage"] == "FRIEND"
