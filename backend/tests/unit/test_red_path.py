"""
Unit: Orchestrator RED path — rejection on high-risk content.

Verifies T4-02: RED severity in safety classification
short-circuits to rejection without writing to memory.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator
from heart.ss07_orchestration.session_manager import SessionManager


class TestRedPath:
    """Verify RED path rejection behavior."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked services."""
        from heart.ss07_orchestration.circuit_breaker import BreakerRegistry

        breakers = BreakerRegistry()
        # Reset any open breakers from other tests
        breakers._breakers.clear()

        return Orchestrator(
            safety_agent=MagicMock(),
            composer_builder=AsyncMock(),
            session_manager=MagicMock(spec=SessionManager),
            breakers=breakers,
            safety_event_writer=AsyncMock(),
            emotion_service=None,
            relationship_service_builder=None,
        )

    @pytest.fixture
    def mock_classification_red(self):
        """Create a RED classification."""
        classification = MagicMock()
        classification.severity.value = "RED"
        classification.reason = "High-risk content detected"
        classification.metadata = {"categories": ["violence"]}
        classification.layer = "heuristic"
        classification.triggered_rules = ["rule_1"]
        classification.confidence = 0.95
        return classification

    @pytest.mark.asyncio
    async def test_red_path_returns_reject(self, orchestrator, mock_classification_red):
        """RED severity should return rejection response."""
        user_id = uuid4()
        character_id = "rin"

        # Mock session manager
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_mock.turn_count = 0
        orchestrator._session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        orchestrator._session_manager.record_turn = AsyncMock()

        # Mock safety to return RED
        orchestrator._safety_agent.classify = AsyncMock(return_value=mock_classification_red)

        req = TurnRequest(
            user_id=user_id,
            character_id=character_id,
            user_message="dangerous content",
            trace_id=uuid4(),
            history=[],
        )

        # Process the turn
        response = await orchestrator.handle_turn(req, db_session=MagicMock())

        # Verify rejection
        assert response.path == "reject"
        assert response.safety_severity == "RED"
        assert "not able to help" in response.response.lower()

    @pytest.mark.asyncio
    async def test_red_path_does_not_call_compose(self, orchestrator, mock_classification_red):
        """RED severity should NOT call composer."""
        user_id = uuid4()

        # Mock session manager
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_mock.turn_count = 0
        orchestrator._session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        orchestrator._session_manager.record_turn = AsyncMock()

        # Mock safety to return RED
        orchestrator._safety_agent.classify = AsyncMock(return_value=mock_classification_red)

        # Mock composer (should NOT be called)
        composer_mock = MagicMock()
        composer_mock.compose = AsyncMock()
        orchestrator._composer_builder = AsyncMock(return_value=composer_mock)

        req = TurnRequest(
            user_id=user_id,
            character_id="rin",
            user_message="dangerous content",
            trace_id=uuid4(),
            history=[],
        )

        # Process the turn
        await orchestrator.handle_turn(req, db_session=MagicMock())

        # Composer should NOT have been called
        composer_mock.compose.assert_not_called()

    @pytest.mark.asyncio
    async def test_red_path_writes_safety_event(self, orchestrator, mock_classification_red):
        """RED severity should write safety event for audit."""
        user_id = uuid4()

        # Mock session manager
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_mock.turn_count = 0
        orchestrator._session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        orchestrator._session_manager.record_turn = AsyncMock()

        # Mock safety to return RED
        orchestrator._safety_agent.classify = AsyncMock(return_value=mock_classification_red)

        req = TurnRequest(
            user_id=user_id,
            character_id="rin",
            user_message="dangerous content",
            trace_id=uuid4(),
            history=[],
        )

        # Process the turn
        await orchestrator.handle_turn(req, db_session=MagicMock())

        # Safety event writer should have been called
        orchestrator._write_safety_event.assert_called_once()
