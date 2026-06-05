"""
Integration: Relationship progression in orchestrator hot path.

Verifies T1-02: RelationshipService.process_turn_raw is wired into orchestrator
and updates relationship state on each turn.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator


@pytest.mark.integration
class TestRelationshipProgression:
    """Verify relationship state updates through orchestrator hot path."""

    @pytest.fixture
    def mock_relationship_service(self):
        """Create a mock RelationshipService."""
        service = MagicMock()
        service.process_turn_raw = AsyncMock(
            return_value=MagicMock(
                current_stage="stranger",
                trust_score=0.05,
                attachment_strength=0.02,
                intimacy_level=0.01,
            )
        )
        return service

    @pytest.fixture
    def orchestrator(self, mock_relationship_service):
        """Create orchestrator with relationship service wired."""
        from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
        from heart.ss07_orchestration.session_manager import SessionManager

        # Create a builder that returns the mock service
        async def relationship_service_builder(db_session=None):
            return mock_relationship_service

        return Orchestrator(
            safety_agent=MagicMock(),
            composer_builder=AsyncMock(),
            session_manager=MagicMock(spec=SessionManager),
            breakers=BreakerRegistry(),
            safety_event_writer=AsyncMock(),
            emotion_service=None,
            relationship_service_builder=relationship_service_builder,
        )

    @pytest.mark.asyncio
    async def test_relationship_process_turn_called(self, orchestrator, mock_relationship_service):
        """RelationshipService.process_turn_raw should be called on each turn."""
        user_id = uuid4()
        character_id = "rin"
        turn_id = uuid4()

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
            user_id=user_id,
            character_id=character_id,
            user_message="你好",
            trace_id=turn_id,
            history=[],
        )

        # Process the turn
        response = await orchestrator.handle_turn(req, db_session=MagicMock())

        # Verify relationship service was called
        mock_relationship_service.process_turn_raw.assert_called_once()
        call_args = mock_relationship_service.process_turn_raw.call_args
        assert call_args.kwargs["user_id"] == user_id
        assert call_args.kwargs["character_id"] == character_id
        assert call_args.kwargs["turn_id"] == turn_id
        assert call_args.kwargs["message_text"] == "你好"

    @pytest.mark.asyncio
    async def test_relationship_skipped_when_no_builder(self):
        """Orchestrator should work without relationship service (graceful degradation)."""
        from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
        from heart.ss07_orchestration.session_manager import SessionManager

        orchestrator = Orchestrator(
            safety_agent=MagicMock(),
            composer_builder=AsyncMock(),
            session_manager=MagicMock(spec=SessionManager),
            breakers=BreakerRegistry(),
            safety_event_writer=AsyncMock(),
            emotion_service=None,
            relationship_service_builder=None,  # No relationship service
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

    @pytest.mark.asyncio
    async def test_relationship_state_updates_on_multiple_turns(self, orchestrator, mock_relationship_service):
        """Multiple turns should call relationship service multiple times."""
        user_id = uuid4()
        character_id = "rin"

        # Mock session manager
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_mock.turn_count = 0
        orchestrator._session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        orchestrator._session_manager.record_turn = AsyncMock()

        # Mock safety and composer
        orchestrator._safety_agent.classify = AsyncMock(return_value=None)
        composer_mock = MagicMock()
        composer_mock.compose = AsyncMock(return_value=MagicMock(response="I see."))
        orchestrator._composer_builder = AsyncMock(return_value=composer_mock)

        # Process two turns
        for i in range(2):
            req = TurnRequest(
                user_id=user_id,
                character_id=character_id,
                user_message=f"Message {i}",
                trace_id=uuid4(),
                history=[],
            )
            await orchestrator.handle_turn(req, db_session=MagicMock())

        # Verify relationship service was called twice
        assert mock_relationship_service.process_turn_raw.call_count == 2
