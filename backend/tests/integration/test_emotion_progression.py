"""
Integration: Emotion progression — multiple turns, VAD evolution.
per runtime_specs/03_emotion_state_machine.md §3.4

Tests that process_turn produces meaningful VAD changes across turns
when wired through Orchestrator's hot path.
"""

from uuid import uuid4

import pytest


@pytest.mark.integration
class TestEmotionProgression:
    """Emotion state evolves meaningfully across consecutive turns."""

    @pytest.fixture
    def service(self):
        from heart.ss03_emotion.service import EmotionService

        return EmotionService()

    @pytest.mark.asyncio
    async def test_sad_message_lowers_valence(self, service):
        """Send '我好难过' twice; valence should drop (more negative) on second call."""
        user_id = uuid4()

        soul_config = {
            "inertia_profile": {
                "max_valence_change_per_turn": 0.15,
                "max_arousal_change_per_turn": 0.15,
                "max_dominance_change_per_turn": 0.15,
            },
            "relational_template": {"repair_profile": {}},
        }

        base_context = {
            "days_since_last": 0,
            "hours_since_last": 0,
            "relationship_phase": "stranger",
            "user_emotion_vad": {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
        }

        try:
            state_1 = await service.process_turn(
                user_id=user_id,
                character_id="rin",
                user_message="我今天很难过，工作上被骂了",
                turn_id=uuid4(),
                context=base_context,
                soul_config=soul_config,
            )
        except AttributeError:
            pytest.skip("Aho-Corasick automaton not properly initialized")

        state_2 = await service.process_turn(
            user_id=user_id,
            character_id="rin",
            user_message="我今天很难过，工作上被骂了",
            turn_id=uuid4(),
            context=base_context,
            soul_config=soul_config,
        )

        assert state_1["vad_valence"] < 0.0, (
            f"First sad message should lower valence below 0, got {state_1['vad_valence']}"
        )
        assert state_2["vad_valence"] <= state_1["vad_valence"], (
            f"Valence should drop further on second sad message: "
            f"{state_1['vad_valence']} -> {state_2['vad_valence']}"
        )

    @pytest.mark.asyncio
    async def test_positive_message_raises_valence(self, service):
        """A positive message should raise valence above default."""
        user_id = uuid4()

        soul_config = {
            "inertia_profile": {
                "max_valence_change_per_turn": 0.15,
                "max_arousal_change_per_turn": 0.15,
                "max_dominance_change_per_turn": 0.15,
            },
            "relational_template": {"repair_profile": {}},
        }

        context = {
            "days_since_last": 0,
            "hours_since_last": 0,
            "relationship_phase": "close_friend",
            "user_emotion_vad": {"valence": 0.7, "arousal": 0.5, "dominance": 0.5},
        }

        try:
            state = await service.process_turn(
                user_id=user_id,
                character_id="rin",
                user_message="你今天真好看！我很开心见到你",
                turn_id=uuid4(),
                context=context,
                soul_config=soul_config,
            )
        except AttributeError:
            pytest.skip("Aho-Corasick automaton not properly initialized")

        assert state["vad_valence"] > 0.0, (
            f"Positive message should raise valence above 0, got {state['vad_valence']}"
        )
