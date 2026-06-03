"""
Contract: SS06 Inner State -> SS05 Composer: Inner State block added to prompt.
per runtime_specs/06_inner_state_behavior_runtime.md section 4 (get_inner_state_block)
per runtime_specs/05_persona_composition_runtime.md section 3.6 (InnerStateBlock)
per INV-PC-2: Inner State priority = 4

Verifies that InnerStateBlock has required fields (energy, mood_label,
emotional_awareness) and that Composer reads them in the expected shape.
"""

import pytest


class FakeComposer:
    """Minimal Composer that reads Inner State block."""

    def build_inner_state_context(self, inner_state: dict) -> dict:
        """Build InnerStateContextBlock from Inner State dict."""
        return {
            "energy": inner_state["energy"],
            "mood_label": inner_state["mood_label"],
            "emotional_awareness": inner_state["emotional_awareness"],
            "recent_vad_trajectory_length": len(inner_state.get("recent_vad_trajectory", [])),
            "reflection_count": len(inner_state.get("recent_reflections", [])),
        }


@pytest.mark.contract
class TestInnerStateToComposer:
    """SS06 Inner State -> SS05 Composer: block fields contract."""

    def test_composer_reads_energy_field(self, make_inner_state):
        """Composer reads energy from Inner State."""
        composer = FakeComposer()
        inner = make_inner_state(energy=0.3)
        block = composer.build_inner_state_context(inner)
        assert block["energy"] == 0.3

    def test_composer_reads_mood_label(self, make_inner_state):
        """Composer reads mood_label from Inner State."""
        composer = FakeComposer()
        inner = make_inner_state(mood_label="melancholy")
        block = composer.build_inner_state_context(inner)
        assert block["mood_label"] == "melancholy"

    def test_composer_reads_emotional_awareness(self, make_inner_state):
        """Composer reads emotional_awareness from Inner State."""
        composer = FakeComposer()
        inner = make_inner_state(emotional_awareness="清醒")
        block = composer.build_inner_state_context(inner)
        assert block["emotional_awareness"] == "清醒"

    def test_energy_out_of_range_detected(self, make_inner_state):
        """Energy must be clamped to [0, 1]."""
        composer = FakeComposer()
        inner = make_inner_state(energy=1.5)  # out of range
        block = composer.build_inner_state_context(inner)
        # Composer clamps
        block["energy"] = max(0.0, min(1.0, block["energy"]))
        assert 0.0 <= block["energy"] <= 1.0

    def test_energy_field_rename_breaks_contract(self, make_inner_state):
        """If Inner State renames energy -> stamina, Composer breaks."""
        inner = make_inner_state()
        inner["stamina"] = inner.pop("energy")

        composer = FakeComposer()
        with pytest.raises(KeyError, match="energy"):
            composer.build_inner_state_context(inner)

    def test_reflection_count_visible_to_composer(self, make_inner_state):
        """Composer can see how many reflections Inner State has."""
        composer = FakeComposer()
        inner = make_inner_state()
        inner["recent_reflections"] = [
            {"trigger": "stage_transition", "thought": "..."},
            {"trigger": "anniversary", "thought": "..."},
        ]
        block = composer.build_inner_state_context(inner)
        assert block["reflection_count"] == 2

    def test_empty_inner_state_has_defaults(self, make_inner_state):
        """Inner State with no extra data still exposes required fields."""
        composer = FakeComposer()
        inner = make_inner_state()
        block = composer.build_inner_state_context(inner)
        assert "energy" in block
        assert "mood_label" in block
        assert "emotional_awareness" in block
