"""
Integration: Memory encoding persistence in orchestrator cold path.

Verifies T1-03: MemoryService.encode_fast actually persists to DB
and queues LLM encoding for L3 fact extraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator


@pytest.mark.integration
class TestMemoryEncodePersists:
    """Verify memory encoding persists to DB in cold path."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock DB session."""
        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def orchestrator(self, mock_db_session):
        """Create orchestrator with memory service wired."""
        from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
        from heart.ss07_orchestration.session_manager import SessionManager

        return Orchestrator(
            safety_agent=MagicMock(),
            composer_builder=AsyncMock(),
            session_manager=MagicMock(spec=SessionManager),
            breakers=BreakerRegistry(),
            safety_event_writer=AsyncMock(),
            emotion_service=None,
            relationship_service_builder=None,
        )

    @pytest.mark.asyncio
    async def test_memory_encode_persists_to_db(self, orchestrator, mock_db_session):
        """Memory encoding should persist to DB when db_session is provided."""
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
            user_message="我妈妈叫王梅",
            trace_id=turn_id,
            history=[],
        )

        # Process the turn with mock DB session
        response = await orchestrator.handle_turn(req, db_session=mock_db_session)

        # Wait for cold path tasks to complete
        import asyncio
        await asyncio.sleep(0.1)

        # Verify DB session was used for memory encoding
        assert mock_db_session.add.called, "DB session add should have been called"
        assert mock_db_session.flush.called, "DB session flush should have been called"

    @pytest.mark.asyncio
    async def test_memory_encode_works_without_db(self, orchestrator):
        """Memory encoding should work without DB (in-memory only)."""
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
            user_message="测试消息",
            trace_id=turn_id,
            history=[],
        )

        # Process the turn without DB session
        response = await orchestrator.handle_turn(req, db_session=None)

        # Should not raise
        assert response.response == "Hello."

    @pytest.mark.asyncio
    async def test_memory_encoding_event_queued(self, orchestrator, mock_db_session):
        """MemoryEncodingEvent should be queued with correct status."""
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
            user_message="我妈妈叫王梅",
            trace_id=turn_id,
            history=[],
        )

        # Process the turn
        response = await orchestrator.handle_turn(req, db_session=mock_db_session)

        # Wait for cold path tasks to complete
        import asyncio
        await asyncio.sleep(0.1)

        # Verify MemoryEncodingEvent was added to DB
        from heart.ss02_memory.models import MemoryEncodingEvent

        added_events = [
            call.args[0]
            for call in mock_db_session.add.call_args_list
            if isinstance(call.args[0], MemoryEncodingEvent)
        ]
        assert len(added_events) == 1, f"Should have added one MemoryEncodingEvent, got {len(added_events)}: {mock_db_session.add.call_args_list}"
        event = added_events[0]
        assert event.user_id == user_id
        assert event.character_id == character_id
        assert event.status == "llm_pending"
        assert event.source_user_text == "我妈妈叫王梅"
