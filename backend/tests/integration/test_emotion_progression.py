"""
Integration: Emotion progression in orchestrator hot path.

Verifies T1-01: EmotionService.process_turn is wired into orchestrator
and updates emotion state on each turn.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss03_emotion.service import EmotionService
from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator


@pytest.mark.integration
class TestEmotionProgression:
    """Verify emotion state updates through orchestrator hot path."""

    @pytest.fixture
    def emotion_service(self):
        """Create a real EmotionService with in-memory cache."""
        from pathlib import Path

        config_path = Path("/Users/wanglixun/heart/config/emotion_lexicon.yaml")
        if not config_path.exists():
            config_path = (
                Path(__file__).parent.parent.parent.parent / "config" / "emotion_lexicon.yaml"
            )
        if not config_path.exists():
            pytest.skip("emotion_lexicon.yaml not found")
        return EmotionService(config_path=str(config_path))

    @pytest.fixture
    def orchestrator(self, emotion_service):
        """Create orchestrator with emotion service wired."""
        from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
        from heart.ss07_orchestration.session_manager import SessionManager

        return Orchestrator(
            safety_agent=MagicMock(),
            composer_builder=AsyncMock(),
            session_manager=MagicMock(spec=SessionManager),
            breakers=BreakerRegistry(),
            safety_event_writer=AsyncMock(),
            emotion_service=emotion_service,
        )

    @pytest.mark.asyncio
    async def test_emotion_valence_changes_on_vulnerability_message(
        self, orchestrator, emotion_service
    ):
        """Sending a vulnerability message should update emotion state.

        This verifies the hot path calls emotion_service.process_turn.
        Uses vulnerability_keywords: 压力, 撑不住, 难受, 痛苦
        """
        user_id = uuid4()
        character_id = "rin"
        turn_id = uuid4()

        # Get initial state
        initial_state = await emotion_service.get_current_state(user_id, character_id)
        initial_valence = initial_state["vad_valence"]
        assert initial_state["active_stack"] == [], "Initial active_stack should be empty"

        # Mock session manager to return session info
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_mock.turn_count = 0
        orchestrator._session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        orchestrator._session_manager.get_session_info = AsyncMock(
            return_value={
                "session_id": session_mock.session_id,
                "last_turn_at": None,
                "turn_count": 0,
                "current_stage": "stranger",
            }
        )
        orchestrator._session_manager.record_turn = AsyncMock()

        # Mock safety to pass through
        orchestrator._safety_agent.classify = AsyncMock(return_value=None)

        # Mock composer to return a simple response
        composer_mock = MagicMock()
        composer_mock.compose = AsyncMock(return_value=MagicMock(response="I understand."))
        orchestrator._composer_builder = AsyncMock(return_value=composer_mock)

        # Create a vulnerability message (uses keywords: 压力, 撑不住)
        req = TurnRequest(
            user_id=user_id,
            character_id=character_id,
            user_message="我压力好大，真的撑不住了",
            trace_id=turn_id,
            history=[],
        )

        # Process the turn
        response = await orchestrator.handle_turn(req, db_session=MagicMock())

        # Get updated state
        updated_state = await emotion_service.get_current_state(user_id, character_id)

        # Should have detected vulnerability trigger and updated active_stack
        assert updated_state["last_turn_processed_at"] is not None
        assert len(updated_state["active_stack"]) > 0, (
            "active_stack should have emotions after vulnerability message"
        )

        # Check that vulnerability-related emotions were added
        emotion_names = [e["emotion"] for e in updated_state["active_stack"]]
        assert any(e in ["tenderness", "worry", "attachment"] for e in emotion_names), (
            f"Expected vulnerability-related emotions, got {emotion_names}"
        )

    @pytest.mark.asyncio
    async def test_emotion_state_accumulates_on_multiple_turns(self, orchestrator, emotion_service):
        """Multiple turns should accumulate emotion state changes."""
        user_id = uuid4()
        character_id = "rin"

        # Mock session manager
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_mock.turn_count = 0
        orchestrator._session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        orchestrator._session_manager.get_session_info = AsyncMock(
            return_value={
                "session_id": session_mock.session_id,
                "last_turn_at": None,
                "turn_count": 0,
                "current_stage": "stranger",
            }
        )
        orchestrator._session_manager.record_turn = AsyncMock()

        # Mock safety and composer
        orchestrator._safety_agent.classify = AsyncMock(return_value=None)
        composer_mock = MagicMock()
        composer_mock.compose = AsyncMock(return_value=MagicMock(response="I see."))
        orchestrator._composer_builder = AsyncMock(return_value=composer_mock)

        # Process two vulnerability messages
        for i in range(2):
            req = TurnRequest(
                user_id=user_id,
                character_id=character_id,
                user_message="我压力好大，撑不住了",
                trace_id=uuid4(),
                history=[],
            )
            await orchestrator.handle_turn(req, db_session=MagicMock())

        # Check final state
        final_state = await emotion_service.get_current_state(user_id, character_id)
        assert len(final_state["active_stack"]) > 0, (
            "Should have emotions after vulnerability messages"
        )
        assert len(final_state["recent_vad_history"]) >= 2

        # Verify emotion intensities accumulated
        for emotion in final_state["active_stack"]:
            assert emotion["intensity"] > 0, (
                f"Emotion {emotion['emotion']} should have positive intensity"
            )

    @pytest.mark.asyncio
    async def test_emotion_skipped_when_no_service(self):
        """Orchestrator should work without emotion service (graceful degradation)."""
        from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
        from heart.ss07_orchestration.session_manager import SessionManager

        orchestrator = Orchestrator(
            safety_agent=MagicMock(),
            composer_builder=AsyncMock(),
            session_manager=MagicMock(spec=SessionManager),
            breakers=BreakerRegistry(),
            safety_event_writer=AsyncMock(),
            emotion_service=None,  # No emotion service
        )

        # Mock session manager
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_mock.turn_count = 0
        orchestrator._session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        orchestrator._session_manager.record_turn = AsyncMock()

        # Mock safety and composer
        orchestrator._safety_agent.classify = AsyncMock(return_value=None)
        composer_mock = MagicMock()
        composer_mock.compose = AsyncMock(return_value=MagicMock(response="Hello."))
        orchestrator._composer_builder = AsyncMock(return_value=composer_mock)

        req = TurnRequest(
            user_id=uuid4(),
            character_id="rin",
            user_message="你好",
            trace_id=uuid4(),
            history=[],
        )

        # Should not raise
        response = await orchestrator.handle_turn(req, db_session=MagicMock())
        assert response.response == "Hello."
