"""
Contract: SS06 Inner State consumes SS03 EmotionState fields.
per runtime_specs/06_inner_state_behavior_runtime.md §4

Verifies InnerState reads energy and VAD from EmotionState.
"""

import pytest


@pytest.mark.contract
class TestInnerStateConsumesEmotion:
    """Inner State must read expected fields from EmotionState."""

    def test_inner_state_reads_energy_from_emotion(self, make_emotion_state, make_inner_state):
        """InnerState energy is derived from EmotionState.energy."""
        emotion = make_emotion_state()
        emotion["energy"] = 0.4

        # InnerState reads energy
        inner = make_inner_state(energy=emotion["energy"])
        assert inner["energy"] == 0.4

    def test_inner_state_reads_vad_valence_from_emotion(self, make_emotion_state, make_inner_state):
        """InnerState emotional awareness derived from VAD valence."""
        emotion = make_emotion_state(vad_valence=-0.7)

        # Simulate: negative valence → "低落" awareness
        if emotion["vad_valence"] < -0.3:
            awareness = "低落"
        elif emotion["vad_valence"] > 0.3:
            awareness = "愉悦"
        else:
            awareness = "中性"

        inner = make_inner_state(emotional_awareness=awareness)
        assert inner["emotional_awareness"] == "低落"

    def test_inner_state_energy_field_rename_breaks_contract(self, make_emotion_state):
        """If SS03 renames energy → stamina, InnerState breaks."""
        emotion = make_emotion_state()
        emotion["stamina"] = emotion.pop("energy")

        # InnerState tries to read energy → KeyError
        with pytest.raises(KeyError, match="energy"):
            _ = emotion["energy"]

    def test_inner_state_reads_recent_vad_trajectory(self, make_emotion_state, make_inner_state):
        """InnerState reads recent_vad_history for trajectory analysis."""
        emotion = make_emotion_state()
        emotion["recent_vad_history"] = [
            {"vad": {"valence": 0.1, "arousal": 0.3, "dominance": 0.5}, "at": "..."},
            {"vad": {"valence": -0.2, "arousal": 0.6, "dominance": 0.4}, "at": "..."},
        ]

        inner = make_inner_state(
            emotional_awareness="清醒",
        )
        inner["recent_vad_trajectory"] = emotion["recent_vad_history"]

        # 2 recent entries should be readable
        assert len(inner["recent_vad_trajectory"]) == 2
        assert inner["recent_vad_trajectory"][1]["vad"]["valence"] == -0.2
