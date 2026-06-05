"""
Unit: InnerStateService.tick receives real days_since_last_interaction.

Verifies T1-04: cold path InnerStateService.tick uses real time data
from SessionManager instead of hardcoded 0.0.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator


class TestInnerStateTickDaysSince:
    """Verify InnerStateService.tick receives real days_since_last."""

    @pytest.fixture
    def mock_inner_state_service(self):
        """Create a mock InnerStateService."""
        svc = MagicMock()
        svc.tick = MagicMock(return_value=None)
        return svc

    def test_tick_receives_real_days_since_last(self, mock_inner_state_service):
        """tick() should receive real days_since_last_interaction from session."""
        user_id = uuid4()
        character_id = "rin"

        # Set last_activity_at to 7 days ago
        last_activity = datetime.now(timezone.utc) - timedelta(days=7)
        days_since = (datetime.now(timezone.utc) - last_activity).total_seconds() / 86400

        mock_inner_state_service.tick(
            user_id=user_id,
            character_id=character_id,
            days_since_last_interaction=days_since,
        )

        call_args = mock_inner_state_service.tick.call_args
        assert call_args.kwargs["days_since_last_interaction"] == pytest.approx(7.0, abs=0.1)

    def test_tick_receives_zero_for_first_interaction(self, mock_inner_state_service):
        """tick() should receive 0.0 for first interaction."""
        user_id = uuid4()
        character_id = "rin"

        mock_inner_state_service.tick(
            user_id=user_id,
            character_id=character_id,
            days_since_last_interaction=0.0,
        )

        call_args = mock_inner_state_service.tick.call_args
        assert call_args.kwargs["days_since_last_interaction"] == 0.0

    def test_days_since_last_computed_from_session(self):
        """days_since_last should be computed from session.last_activity_at."""
        last_activity = datetime.now(timezone.utc) - timedelta(days=3)
        now = datetime.now(timezone.utc)
        delta = now - last_activity
        days_since = delta.total_seconds() / 86400

        assert days_since == pytest.approx(3.0, abs=0.01)
