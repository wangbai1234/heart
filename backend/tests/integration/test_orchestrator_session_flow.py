"""
Integration: Orchestrator with SessionManager — session lifecycle and turn flow.

Tests:
- SessionManager creates sessions (mock DB)
- get_or_create_session is idempotent
- Orchestrator normal path flow (mocked deps)
- Orchestrator PURPLE care path (mocked safety agent)
- Orchestrator composer fallback (mocked failure)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.integration
class TestSessionManagerFlow:
    """SessionManager creates and retrieves sessions."""

    @pytest.mark.asyncio
    async def test_get_or_create_session_returns_session(self):
        """SessionManager returns a new session when none exists."""
        from heart.ss07_orchestration.session_manager import SessionManager

        mgr = SessionManager()
        user_id = uuid4()
        character_id = "rin"

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        session = await mgr.get_or_create_session(mock_db, user_id, character_id)
        assert session.user_id == user_id
        assert session.character_id == character_id
        assert session.turn_count == 0

    @pytest.mark.asyncio
    async def test_get_or_create_session_cache_hit(self):
        """Second call returns cached session without DB query."""
        from heart.ss07_orchestration.session_manager import SessionManager

        mgr = SessionManager()
        user_id = uuid4()
        character_id = "dorothy"

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        s1 = await mgr.get_or_create_session(mock_db, user_id, character_id)
        s2 = await mgr.get_or_create_session(mock_db, user_id, character_id)

        assert s1.session_id == s2.session_id
        assert s1 is s2

    @pytest.mark.asyncio
    async def test_record_turn_increments_count(self):
        """record_turn increments turn_count and updates last_activity_at."""
        from heart.ss07_orchestration.models import Session
        from heart.ss07_orchestration.session_manager import SessionManager

        mgr = SessionManager()
        now_value = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

        session = Session(
            session_id=uuid4(),
            user_id=uuid4(),
            character_id="rin",
            started_at=now_value,
            last_activity_at=now_value,
            turn_count=3,
        )

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        await mgr.record_turn(mock_db, session)
        assert session.turn_count == 4

    def test_invalidate_cache_removes_entry(self):
        """invalidate_cache clears the in-process cache entry."""
        from heart.ss07_orchestration.session_manager import SessionManager

        mgr = SessionManager()
        user_id = uuid4()
        mgr._cache[(str(user_id), "rin")] = MagicMock()

        mgr.invalidate_cache(user_id, "rin")
        assert (str(user_id), "rin") not in mgr._cache


@pytest.mark.integration
class TestOrchestratorTurnFlow:
    """Orchestrator.handle_turn wires safety, composer, and memory."""

    def _make_breakers(self):
        """Create a fresh BreakerRegistry (bypasses singleton)."""
        from heart.ss07_orchestration.circuit_breaker import BreakerRegistry

        BreakerRegistry._instance = None  # reset singleton
        return BreakerRegistry()

    @pytest.fixture
    def mock_deps(self):
        """Create mock dependencies with fresh breakers per test."""
        safety_agent = MagicMock()
        safety_agent.classify = AsyncMock()
        safety_agent.resolve_care_response = MagicMock(return_value="Crisis helpline: 988")

        composer_builder = AsyncMock()
        compose_result = MagicMock()
        compose_result.response = "Hello from Rin."
        composer = MagicMock()
        composer.compose = AsyncMock(return_value=compose_result)
        composer_builder.return_value = composer

        session_manager = MagicMock()
        session_mock = MagicMock()
        session_mock.session_id = uuid4()
        session_manager.get_or_create_session = AsyncMock(return_value=session_mock)
        session_manager.record_turn = AsyncMock()

        breakers = self._make_breakers()

        safety_event_writer = AsyncMock()

        return {
            "safety_agent": safety_agent,
            "composer_builder": composer_builder,
            "session_manager": session_manager,
            "breakers": breakers,
            "safety_event_writer": safety_event_writer,
        }

    @pytest.mark.asyncio
    async def test_normal_path_returns_response(self, mock_deps):
        """Normal (GREEN) path: safety pass → compose → return."""
        from heart.safety.safety_agent import ClassificationResult, SeverityLevel
        from heart.ss07_orchestration.models import TurnRequest
        from heart.ss07_orchestration.orchestrator import Orchestrator

        mock_deps["safety_agent"].classify.return_value = ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="No safety signals",
            layer="heuristic",
            metadata={"locale": "en"},
        )

        orchestrator = Orchestrator(**mock_deps)
        req = TurnRequest(
            user_id=uuid4(),
            character_id="rin",
            user_message="Hello",
            history=[],
            trace_id=uuid4(),
        )

        db_mock = AsyncMock()
        resp = await orchestrator.handle_turn(req, db_mock)

        assert resp.response == "Hello from Rin."
        assert resp.path == "normal"
        assert resp.character_id == "rin"

    @pytest.mark.asyncio
    async def test_purple_path_short_circuits(self, mock_deps):
        """PURPLE severity: safety blocks → care path, composer never called."""
        from heart.safety.safety_agent import ClassificationResult, SeverityLevel
        from heart.ss07_orchestration.models import TurnRequest
        from heart.ss07_orchestration.orchestrator import Orchestrator

        mock_deps["safety_agent"].classify.return_value = ClassificationResult(
            severity=SeverityLevel.PURPLE,
            reason="Suicide risk detected",
            triggered_rules=["suicide_risk"],
            layer="heuristic",
            metadata={"locale": "en"},
        )

        orchestrator = Orchestrator(**mock_deps)
        req = TurnRequest(
            user_id=uuid4(),
            character_id="rin",
            user_message="harmful message",
            history=[],
            trace_id=uuid4(),
        )

        db_mock = AsyncMock()
        resp = await orchestrator.handle_turn(req, db_mock)

        assert resp.path == "care"
        assert resp.safety_severity == "PURPLE"
        assert "988" in resp.response
        mock_deps["composer_builder"].assert_not_called()
        mock_deps["safety_event_writer"].assert_called_once()

    @pytest.mark.asyncio
    async def test_safety_breaker_open_skips_classify(self, mock_deps):
        """When safety breaker is open, classification is skipped."""
        from heart.ss07_orchestration.models import TurnRequest
        from heart.ss07_orchestration.orchestrator import Orchestrator

        safety_breaker = mock_deps["breakers"].get("safety")
        for _ in range(5):
            safety_breaker.record_failure()
        assert safety_breaker.is_open()

        orchestrator = Orchestrator(**mock_deps)
        req = TurnRequest(
            user_id=uuid4(),
            character_id="rin",
            user_message="Hello",
            history=[],
            trace_id=uuid4(),
        )

        db_mock = AsyncMock()
        resp = await orchestrator.handle_turn(req, db_mock)

        assert resp.path == "normal"
        mock_deps["safety_agent"].classify.assert_not_called()

    @pytest.mark.asyncio
    async def test_composer_failure_returns_fallback(self, mock_deps):
        """When composer raises, fallback message is returned."""
        from heart.safety.safety_agent import ClassificationResult, SeverityLevel
        from heart.ss07_orchestration.models import TurnRequest
        from heart.ss07_orchestration.orchestrator import Orchestrator

        mock_deps["safety_agent"].classify.return_value = ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="No signals",
            layer="heuristic",
            metadata={"locale": "en"},
        )
        mock_deps["composer_builder"].side_effect = RuntimeError("Composer crash")

        orchestrator = Orchestrator(**mock_deps)
        req = TurnRequest(
            user_id=uuid4(),
            character_id="rin",
            user_message="Hello",
            history=[],
            trace_id=uuid4(),
        )

        db_mock = AsyncMock()
        resp = await orchestrator.handle_turn(req, db_mock)

        assert resp.path == "normal"
        assert "凛" in resp.response

    @pytest.mark.asyncio
    async def test_composer_breaker_open_returns_fallback(self, mock_deps):
        """When composer breaker is open, fallback without calling builder."""
        from heart.safety.safety_agent import ClassificationResult, SeverityLevel
        from heart.ss07_orchestration.models import TurnRequest
        from heart.ss07_orchestration.orchestrator import Orchestrator

        mock_deps["safety_agent"].classify.return_value = ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="No signals",
            layer="heuristic",
            metadata={"locale": "en"},
        )

        composer_breaker = mock_deps["breakers"].get("composer")
        for _ in range(3):
            composer_breaker.record_failure()
        assert composer_breaker.is_open()

        orchestrator = Orchestrator(**mock_deps)
        req = TurnRequest(
            user_id=uuid4(),
            character_id="dorothy",
            user_message="Hi",
            history=[],
            trace_id=uuid4(),
        )

        db_mock = AsyncMock()
        resp = await orchestrator.handle_turn(req, db_mock)

        assert "Dorothy" in resp.response
        mock_deps["composer_builder"].assert_not_called()

    @pytest.mark.asyncio
    async def test_safety_agent_unavailable_raises(self, mock_deps):
        """When safety_agent is None, RuntimeError is raised (fail-closed)."""
        from heart.ss07_orchestration.models import TurnRequest
        from heart.ss07_orchestration.orchestrator import Orchestrator

        mock_deps["safety_agent"] = None

        orchestrator = Orchestrator(**mock_deps)
        req = TurnRequest(
            user_id=uuid4(),
            character_id="rin",
            user_message="Hello",
            history=[],
            trace_id=uuid4(),
        )

        db_mock = AsyncMock()
        with pytest.raises(RuntimeError, match="SafetyAgent is not available"):
            await orchestrator.handle_turn(req, db_mock)

    @pytest.mark.asyncio
    async def test_cold_path_does_not_block_response(self, mock_deps):
        """Cold path errors do not affect the response."""
        from heart.safety.safety_agent import ClassificationResult, SeverityLevel
        from heart.ss07_orchestration.models import TurnRequest
        from heart.ss07_orchestration.orchestrator import Orchestrator

        mock_deps["safety_agent"].classify.return_value = ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="No signals",
            layer="heuristic",
            metadata={"locale": "en"},
        )

        orchestrator = Orchestrator(**mock_deps)
        req = TurnRequest(
            user_id=uuid4(),
            character_id="rin",
            user_message="Hello",
            history=[],
            trace_id=uuid4(),
        )

        db_mock = AsyncMock()

        with patch(
            "heart.ss07_orchestration.orchestrator.asyncio.create_task",
            side_effect=Exception("event loop closed"),
        ):
            resp = await orchestrator.handle_turn(req, db_mock)

        assert resp.path == "normal"
        assert resp.response == "Hello from Rin."
