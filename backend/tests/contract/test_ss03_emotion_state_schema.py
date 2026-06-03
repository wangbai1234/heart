"""
Contract: SS03 EmotionState schema fields.
per runtime_specs/03_emotion_state_machine.md §5

Verifies that the EmotionState dict has the required fields
that downstream subsystems (SS05, SS06, SS07) depend on.
"""

import pytest


@pytest.mark.contract
class TestEmotionStateSchemaV1:
    """SS03 EmotionState must expose v1 contract fields."""

    REQUIRED_FIELDS = [
        "user_id",
        "character_id",
        "vad_valence",
        "vad_arousal",
        "vad_dominance",
        "vad_target_valence",
        "vad_target_arousal",
        "vad_target_dominance",
        "active_stack",
        "mood",
        "energy",
        "energy_baseline",
        "recent_vad_history",
        "recent_triggers",
        "pending_repairs",
        "version",
    ]

    def test_emotion_state_has_required_fields(self, make_emotion_state):
        """All required fields must be present in EmotionState dict."""
        state = make_emotion_state()
        for field in self.REQUIRED_FIELDS:
            assert field in state, f"Missing required field: {field}"

    def test_vad_fields_are_floats_in_range(self, make_emotion_state):
        """VAD fields must be floats in valid ranges."""
        state = make_emotion_state(vad_valence=0.5, vad_arousal=0.7, vad_dominance=0.6)
        assert -1.0 <= state["vad_valence"] <= 1.0
        assert 0.0 <= state["vad_arousal"] <= 1.0
        assert 0.0 <= state["vad_dominance"] <= 1.0

    def test_active_stack_is_list_of_dicts(self, make_emotion_state):
        """active_stack must be a list of emotion dicts."""
        state = make_emotion_state(
            active_stack=[{"emotion": "joy", "intensity": 0.5, "source": "user_trigger"}]
        )
        assert isinstance(state["active_stack"], list)
        assert len(state["active_stack"]) > 0
        assert "emotion" in state["active_stack"][0]
        assert "intensity" in state["active_stack"][0]

    def test_mood_has_required_subfields(self, make_emotion_state):
        """Mood dict must have baseline fields for Persona Composer."""
        state = make_emotion_state()
        mood = state["mood"]
        assert "valence_baseline" in mood
        assert "arousal_baseline" in mood
        assert "dominance_baseline" in mood
        assert "background_emotions" in mood

    def test_pending_repairs_is_list(self, make_emotion_state):
        """pending_repairs must be a list (even if empty)."""
        state = make_emotion_state(pending_repairs=[])
        assert isinstance(state["pending_repairs"], list)

    def test_version_is_present(self, make_emotion_state):
        """version field must be present for schema evolution."""
        state = make_emotion_state(version=1)
        assert state["version"] == 1
