"""
Contract: SS05 Composer consumes SS03 EmotionState correctly.
per runtime_specs/05_persona_composition_runtime.md §6

Verifies that Composer reads EmotionState fields in the expected shape.
Any field rename in SS03 must break this test.
"""

import pytest
from datetime import datetime, timezone


class FakeComposer:
    """Minimal Composer that reads EmotionState for contract validation."""

    def build_emotion_context_block(self, emotion_state: dict) -> dict:
        """Build EmotionContextBlock from EmotionState — mirrors SS03.get_context_block()."""
        # Sort emotions by intensity
        active_stack = emotion_state.get("active_stack", [])
        top_emotions = sorted(
            active_stack, key=lambda e: e.get("intensity", 0), reverse=True
        )[:3]

        return {
            "vad": {
                "valence": emotion_state["vad_valence"],
                "arousal": emotion_state["vad_arousal"],
                "dominance": emotion_state["vad_dominance"],
            },
            "active_emotions": [
                {
                    "emotion": e["emotion"],
                    "intensity": e["intensity"],
                }
                for e in top_emotions
            ],
            "energy": emotion_state["energy"],
            "pending_repairs_summary": (
                emotion_state["pending_repairs"][0]["emotion"]
                if emotion_state.get("pending_repairs")
                else None
            ),
        }


@pytest.mark.contract
class TestComposerConsumesSS03:
    """SS05 must consume SS03 EmotionState v1 contract correctly."""

    def test_reads_vad_fields_from_emotion_state(self, make_emotion_state):
        """Composer reads vad_valence/arousal/dominance from EmotionState."""
        state = make_emotion_state(vad_valence=0.6, vad_arousal=0.4, vad_dominance=0.8)
        composer = FakeComposer()
        block = composer.build_emotion_context_block(state)

        assert block["vad"]["valence"] == 0.6
        assert block["vad"]["arousal"] == 0.4
        assert block["vad"]["dominance"] == 0.8

    def test_reads_active_emotions_sorted_by_intensity(self, make_emotion_state):
        """Composer sorts active emotions by intensity descending."""
        state = make_emotion_state(active_stack=[
            {"emotion": "joy", "intensity": 0.3, "source": "test"},
            {"emotion": "sadness", "intensity": 0.8, "source": "test"},
            {"emotion": "anger", "intensity": 0.2, "source": "test"},
        ])
        composer = FakeComposer()
        block = composer.build_emotion_context_block(state)

        assert block["active_emotions"][0]["emotion"] == "sadness"
        assert block["active_emotions"][0]["intensity"] == 0.8

    def test_reads_energy_field(self, make_emotion_state):
        """Composer reads energy from EmotionState."""
        state = make_emotion_state()
        state["energy"] = 0.9
        composer = FakeComposer()
        block = composer.build_emotion_context_block(state)

        assert block["energy"] == 0.9

    def test_renamed_field_breaks_contract(self, make_emotion_state):
        """If SS03 renames vad_valence → valence, Composer MUST see failure."""
        state = make_emotion_state(vad_valence=0.5)
        # Simulate a rename that would happen in SS03
        state["valence"] = state.pop("vad_valence")

        composer = FakeComposer()
        with pytest.raises(KeyError, match="vad_valence"):
            composer.build_emotion_context_block(state)

    def test_reads_pending_repairs(self, make_emotion_state):
        """Composer reads pending_repairs from EmotionState."""
        state = make_emotion_state(pending_repairs=[
            {"emotion": "aggrieved", "repair_progress": 0.0}
        ])
        composer = FakeComposer()
        block = composer.build_emotion_context_block(state)

        assert block["pending_repairs_summary"] == "aggrieved"
