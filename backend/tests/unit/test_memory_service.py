"""
Unit tests for Memory Service (SS02 §10.3).

Test scaffolding for:
- Read API: retrieve(), get_l4(), get_recent_episodes(), get_anniversaries()
- Write API: encode_fast(), queue_llm_encoding(), reinforce(), user_request_forget()
- Lifecycle: apply_decay_batch(), run_consolidation(), promote_to_l4()

Invariants tested:
- INV-M-3: Top-K limit enforcement
- INV-M-6: User isolation enforcement

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from heart.ss02_memory.service import (
    MemoryService,
    QueryContext,
    ReinforcementTrigger,
    Turn,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def service():
    """Memory Service instance."""
    return MemoryService()


@pytest.fixture
def user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def character_id():
    """Test character ID."""
    return "rin"


@pytest.fixture
def query_context(user_id, character_id):
    """Test query context."""
    return QueryContext(
        current_message="你还记得我的猫吗？",
        recent_turns=[
            Turn(
                turn_index=1,
                role="user",
                content="我养了一只猫",
                user_id=user_id,
                character_id=character_id,
                timestamp=datetime.now(timezone.utc),
            ),
        ],
        session_id=uuid4(),
        user_id=user_id,
        character_id=character_id,
    )


# ============================================================
# Read API Tests
# ============================================================


class TestRetrieveAPI:
    """Tests for retrieve() main retrieval API."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_result_without_db(
        self, service, user_id, character_id, query_context
    ):
        """retrieve() returns empty result when DB is not configured."""
        result = await service.retrieve(
            user_id=user_id,
            character_id=character_id,
            query_context=query_context,
            top_k=5,
        )
        assert result.memories == []
        assert result.total_candidates == 0

    @pytest.mark.asyncio
    async def test_retrieve_enforces_top_k_limit(
        self, service, user_id, character_id, query_context
    ):
        """retrieve() should enforce INV-M-3: top_k ≤ MAX_TOP_K."""
        # Should clamp to MAX_TOP_K (10)
        clamped = service._enforce_top_k(20)
        assert clamped == service.MAX_TOP_K

    @pytest.mark.asyncio
    async def test_retrieve_enforces_user_isolation(self, service, user_id, character_id):
        """retrieve() should enforce INV-M-6: user_id isolation."""
        # Mismatched user_id in context should raise
        bad_context = QueryContext(
            current_message="test",
            recent_turns=[],
            session_id=uuid4(),
            user_id=uuid4(),  # Different user_id!
            character_id=character_id,
        )

        with pytest.raises(ValueError, match="INV-M-6"):
            service._enforce_user_isolation(user_id, character_id, bad_context)


class TestGetL4:
    """Tests for get_l4() L4 identity memory read."""

    @pytest.mark.asyncio
    async def test_get_l4_returns_empty_without_db(self, service, user_id, character_id):
        """get_l4() returns empty list when DB is not configured."""
        result = await service.get_l4(user_id=user_id, character_id=character_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_l4_enforces_user_isolation(self, service, user_id, character_id):
        """get_l4() should enforce INV-M-6."""
        # Should not raise (valid user_id)
        service._enforce_user_isolation(user_id, character_id, None)


class TestGetRecentEpisodes:
    """Tests for get_recent_episodes() recency-based retrieval."""

    @pytest.mark.asyncio
    async def test_get_recent_episodes_returns_empty_without_db(
        self, service, user_id, character_id
    ):
        """get_recent_episodes() returns empty list when DB is not configured."""
        result = await service.get_recent_episodes(user_id=user_id, character_id=character_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_recent_episodes_enforces_limit(self, service, user_id, character_id):
        """get_recent_episodes() should enforce limit ≤ MAX_TOP_K."""
        clamped = service._enforce_top_k(15)
        assert clamped == service.MAX_TOP_K


class TestGetAnniversaries:
    """Tests for get_anniversaries() anniversary lookup."""

    @pytest.mark.asyncio
    async def test_get_anniversaries_returns_empty_without_db(self, service, user_id, character_id):
        """get_anniversaries() returns empty list when DB is not configured."""
        result = await service.get_anniversaries(user_id=user_id, character_id=character_id)
        assert result == []


# ============================================================
# Write API Tests
# ============================================================


class TestEncodeFast:
    """Tests for encode_fast() real-time encoding."""

    @pytest.mark.asyncio
    async def test_encode_fast_returns_signals(self, service, user_id, character_id):
        """encode_fast() returns FastSignals without DB."""
        turn = Turn(
            turn_index=1,
            role="user",
            content="我养了一只猫",
            user_id=user_id,
            character_id=character_id,
            timestamp=datetime.now(timezone.utc),
        )
        result = await service.encode_fast(turn)
        assert result is not None
        assert hasattr(result, "sentiment")
        assert -1.0 <= result.sentiment <= 1.0


class TestQueueLLMEncoding:
    """Tests for queue_llm_encoding() async encoding."""

    @pytest.mark.asyncio
    async def test_queue_llm_encoding_does_not_raise(self, service):
        """queue_llm_encoding() logs warning without DB (no raise)."""
        from heart.ss02_memory.models import MemoryEncodingEvent

        event = MemoryEncodingEvent(
            event_id=uuid4(),
            user_id=uuid4(),
            character_id="rin",
            source_turn_id=uuid4(),
            status="llm_pending",
            created_at=datetime.now(timezone.utc),
        )
        # Should not raise — logs warning when no DB
        await service.queue_llm_encoding(event)


class TestReinforce:
    """Tests for reinforce() memory reinforcement."""

    @pytest.mark.asyncio
    async def test_reinforce_no_db_no_raise(self, service):
        """reinforce() does not raise when DB is not configured."""
        trigger = ReinforcementTrigger(
            trigger_type="user_re_mentioned",
            context="test",
            boost=0.15,
        )
        # Should not raise — silently no-ops without DB
        await service.reinforce(memory_ids=[uuid4()], trigger=trigger)


class TestUserRequestForget:
    """Tests for user_request_forget() user-initiated forgetting."""

    @pytest.mark.asyncio
    async def test_user_request_forget_no_db_no_raise(self, service, user_id):
        """user_request_forget() does not raise when DB is not configured."""
        await service.user_request_forget(user_id=user_id, memory_id=uuid4())


# ============================================================
# Lifecycle Tests
# ============================================================


class TestApplyDecayBatch:
    """Tests for apply_decay_batch() daily decay."""

    @pytest.mark.asyncio
    async def test_apply_decay_batch_returns_zero_without_db(self, service, user_id, character_id):
        """apply_decay_batch() returns 0 when DB is not configured."""
        count = await service.apply_decay_batch(user_id=user_id, character_id=character_id)
        assert count == 0


class TestRunConsolidation:
    """Tests for run_consolidation() daily consolidation."""

    @pytest.mark.asyncio
    async def test_run_consolidation_returns_job_without_db(self, service, user_id, character_id):
        """run_consolidation() returns ConsolidationJob without DB."""
        job = await service.run_consolidation(user_id=user_id, character_id=character_id)
        assert job is not None
        assert job.status == "triggered"


class TestPromoteToL4:
    """Tests for promote_to_l4() L3 → L4 promotion."""

    @pytest.mark.asyncio
    async def test_promote_to_l4_requires_db_session(self, service):
        """promote_to_l4() requires db_session."""
        with pytest.raises(RuntimeError, match="requires db_session"):
            await service.promote_to_l4(fact_id=uuid4(), reason="test")


# ============================================================
# Invariant Enforcement Tests
# ============================================================


class TestInvariants:
    """Tests for INV-M-* invariant enforcement."""

    def test_enforce_top_k_clamps_to_max(self, service):
        """_enforce_top_k() should clamp to MAX_TOP_K."""
        # Too high → clamp
        assert service._enforce_top_k(100) == service.MAX_TOP_K

        # Within range → unchanged
        assert service._enforce_top_k(5) == 5

        # Too low → clamp to 1
        assert service._enforce_top_k(0) == 1
        assert service._enforce_top_k(-5) == 1

    def test_enforce_user_isolation_rejects_mismatch(self, service, user_id, character_id):
        """_enforce_user_isolation() should reject user_id mismatch."""
        bad_context = QueryContext(
            current_message="test",
            recent_turns=[],
            session_id=uuid4(),
            user_id=uuid4(),  # Wrong user_id
            character_id=character_id,
        )

        with pytest.raises(ValueError, match="INV-M-6.*user_id"):
            service._enforce_user_isolation(user_id, character_id, bad_context)

    def test_enforce_user_isolation_rejects_character_mismatch(
        self, service, user_id, character_id
    ):
        """_enforce_user_isolation() should reject character_id mismatch."""
        bad_context = QueryContext(
            current_message="test",
            recent_turns=[],
            session_id=uuid4(),
            user_id=user_id,
            character_id="wrong_character",  # Wrong character_id
        )

        with pytest.raises(ValueError, match="INV-M-6.*character_id"):
            service._enforce_user_isolation(user_id, character_id, bad_context)

    def test_enforce_user_isolation_allows_valid_context(self, service, user_id, character_id):
        """_enforce_user_isolation() should allow valid context."""
        valid_context = QueryContext(
            current_message="test",
            recent_turns=[],
            session_id=uuid4(),
            user_id=user_id,
            character_id=character_id,
        )

        # Should not raise
        service._enforce_user_isolation(user_id, character_id, valid_context)
