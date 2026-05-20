"""
Unit tests for Multi-Strategy Retriever (SS02 §3.5 + §10.3).

Tests:
- Individual strategy functionality
- Orchestrator score combination
- L4 force-inclusion
- User isolation (INV-M-13)
- Parallel execution
- Deduplication

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from heart.ss02_memory.models import EpisodicMemory, FactNode, IdentityMemory
from heart.ss02_memory.retriever import (
    QueryContext,
    ScoredMemory,
    RetrievalOrchestrator,
    VectorRetriever,
    RecencyRetriever,
    EmotionalRetriever,
    IdentityLookup,
    combine_scores,
    select_top_k,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def another_user_id():
    """Another user UUID (for isolation tests)."""
    return uuid4()


@pytest.fixture
def character_id():
    """Test character ID."""
    return "rin"


@pytest.fixture
def query_context(user_id, character_id):
    """Sample query context."""
    return QueryContext(
        query_text="我的猫叫什么名字？",
        query_embedding=[0.1] * 768,  # 768-dim embedding
        keywords=["猫", "名字"],
        current_emotion={"valence": 0.3, "arousal": 0.4},
        current_time=datetime.now(timezone.utc),
        user_id=user_id,
        character_id=character_id,
    )


@pytest.fixture
def l2_memory(user_id, character_id):
    """Sample L2 episodic memory."""
    memory = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        episode_summary="用户养了一只叫老铁的黑猫",
        episode_raw_turn_ids=[uuid4()],
        episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
        episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
        emotional_peak={"valence": 0.4, "arousal": 0.5, "label": "fond"},
        emotional_end={"valence": 0.3, "arousal": 0.4, "label": "calm"},
        emotional_significance=0.6,
        importance_score=0.7,
        initial_importance=0.7,
        recall_count=0,
        state="vivid",
        created_at=datetime.now(timezone.utc) - timedelta(hours=24),
        updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
    )
    # Add semantic_vector as attribute (not in constructor)
    memory.semantic_vector = [0.1] * 768
    return memory


@pytest.fixture
def l3_fact(user_id, character_id):
    """Sample L3 fact."""
    fact = FactNode(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        predicate="has_pet",
        subject="user",
        object="一只叫老铁的黑猫",
        literal_text="user has_pet 一只叫老铁的黑猫",
        raw_evidence="我养了一只叫老铁的黑猫",
        source_turn_ids=[uuid4()],
        confidence=0.95,
        emotional_charge=0.4,
        importance=0.7,
        state="active",
        confirmation_count=1,
        last_confirmed_at=datetime.now(timezone.utc),
    )
    # Add semantic_vector as attribute
    fact.semantic_vector = [0.1] * 768
    return fact


@pytest.fixture
def l4_memory(user_id, character_id):
    """Sample L4 identity memory."""
    return IdentityMemory(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        category="foundational",
        content={"type": "name", "value": "王小明"},
        promoted_from_fact_id=uuid4(),
        sacred_reason="foundational_fact",
        created_at=datetime.now(timezone.utc),
        last_accessed_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_db_session():
    """Mock database session with proper async and sync mock support."""
    session = MagicMock()

    # Create a default result mock that supports both .all() (sync) and .scalars() methods
    # Tests can override this by setting mock_db_session.execute.return_value
    result_mock = MagicMock()
    result_mock.all = MagicMock(return_value=[])
    result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    # AsyncMock with default return value
    session.execute = AsyncMock(return_value=result_mock)
    session.commit = AsyncMock()
    return session


# ============================================================
# Score Combination Tests
# ============================================================


class TestScoreCombination:
    """Tests for score combination logic."""

    def test_combine_scores_default_weights(self):
        """Should combine scores using default weights."""
        candidates = [
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L2",
                score_breakdown={
                    "semantic": 0.9,
                    "importance": 0.7,
                    "emotional": 0.6,
                    "recency": 0.8,
                    "associative": 0.5,
                    "confidence": 1.0,
                },
            )
        ]

        combine_scores(candidates)

        expected = (
            0.30 * 0.9
            + 0.20 * 0.7
            + 0.15 * 0.6
            + 0.15 * 0.8
            + 0.10 * 0.5
            + 0.10 * 1.0
        )

        assert abs(candidates[0].score - expected) < 0.01

    def test_combine_scores_custom_weights(self):
        """Should use custom weights if provided."""
        candidates = [
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L2",
                score_breakdown={
                    "semantic": 0.9,
                    "importance": 0.7,
                },
            )
        ]

        custom_weights = {"semantic": 0.5, "importance": 0.5}
        combine_scores(candidates, custom_weights)

        expected = 0.5 * 0.9 + 0.5 * 0.7
        assert abs(candidates[0].score - expected) < 0.01

    def test_combine_scores_missing_keys(self):
        """Should handle missing score keys gracefully."""
        candidates = [
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L2",
                score_breakdown={
                    "semantic": 0.9,
                    # Missing other keys
                },
            )
        ]

        combine_scores(candidates)

        # Should only use semantic (0.30 * 0.9)
        expected = 0.30 * 0.9
        assert abs(candidates[0].score - expected) < 0.01


# ============================================================
# Top-K Selection Tests
# ============================================================


class TestTopKSelection:
    """Tests for Top-K selection with L4 force-inclusion."""

    def test_select_top_k_basic(self):
        """Should select top 5 by score."""
        candidates = [
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L2",
                score=0.9 - i * 0.1,
            )
            for i in range(10)
        ]

        top_k = select_top_k(candidates, k=5)

        assert len(top_k) == 5
        assert all(top_k[i].score >= top_k[i + 1].score for i in range(4))

    def test_select_top_k_l4_force_inclusion(self):
        """Should force-include L4 memories if relevant."""
        candidates = [
            # L4 with high score
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L4",
                score=0.8,
            ),
            # L4 with low score (but > 0.1 threshold)
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L4",
                score=0.2,
            ),
            # L2 with very high score
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L2",
                score=0.95,
            ),
            # Other L2 memories
            *[
                ScoredMemory(
                    memory=MagicMock(),
                    memory_id=uuid4(),
                    memory_type="L2",
                    score=0.5,
                )
                for _ in range(5)
            ],
        ]

        top_k = select_top_k(candidates, k=5, must_include_l4=True)

        # Should include both L4 memories (max 2)
        l4_in_top_k = [m for m in top_k if m.memory_type == "L4"]
        assert len(l4_in_top_k) == 2

        # Should be at most 5 total
        assert len(top_k) <= 5

    def test_select_top_k_l4_below_threshold(self):
        """Should NOT include L4 if score < 0.1."""
        candidates = [
            # L4 with very low score
            ScoredMemory(
                memory=MagicMock(),
                memory_id=uuid4(),
                memory_type="L4",
                score=0.05,  # Below threshold
            ),
            # L2 with high score
            *[
                ScoredMemory(
                    memory=MagicMock(),
                    memory_id=uuid4(),
                    memory_type="L2",
                    score=0.8 - i * 0.1,
                )
                for i in range(5)
            ],
        ]

        top_k = select_top_k(candidates, k=5, must_include_l4=True)

        # Should NOT include L4 (below threshold)
        l4_in_top_k = [m for m in top_k if m.memory_type == "L4"]
        assert len(l4_in_top_k) == 0


# ============================================================
# User Isolation Tests (INV-M-13)
# ============================================================


class TestUserIsolation:
    """Tests for user isolation (INV-M-13)."""

    @pytest.mark.asyncio
    async def test_orchestrator_requires_user_id(self, mock_db_session, character_id):
        """Should raise error if user_id missing."""
        orchestrator = RetrievalOrchestrator(mock_db_session)

        query_context = QueryContext(
            query_text="test",
            user_id=None,  # Missing
            character_id=character_id,
        )

        with pytest.raises(ValueError, match="user_id.*required"):
            await orchestrator.retrieve(query_context)

    @pytest.mark.asyncio
    async def test_orchestrator_requires_character_id(self, mock_db_session, user_id):
        """Should raise error if character_id missing."""
        orchestrator = RetrievalOrchestrator(mock_db_session)

        query_context = QueryContext(
            query_text="test",
            user_id=user_id,
            character_id=None,  # Missing
        )

        with pytest.raises(ValueError, match="character_id.*required"):
            await orchestrator.retrieve(query_context)


# ============================================================
# Orchestrator Integration Tests
# ============================================================


class TestRetrievalOrchestrator:
    """Tests for RetrievalOrchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_runs_strategies_in_parallel(
        self, mock_db_session, query_context
    ):
        """Should run all strategies in parallel."""
        orchestrator = RetrievalOrchestrator(mock_db_session)

        # Mock strategies to return empty results
        with patch.object(VectorRetriever, "retrieve", new_callable=AsyncMock) as mock_vector, \
             patch.object(RecencyRetriever, "retrieve", new_callable=AsyncMock) as mock_recency, \
             patch.object(EmotionalRetriever, "retrieve", new_callable=AsyncMock) as mock_emotional, \
             patch.object(IdentityLookup, "retrieve", new_callable=AsyncMock) as mock_identity:

            mock_vector.return_value = []
            mock_recency.return_value = []
            mock_emotional.return_value = []
            mock_identity.return_value = []

            result = await orchestrator.retrieve(query_context)

            # All strategies should be called
            mock_vector.assert_called_once()
            mock_recency.assert_called_once()
            mock_emotional.assert_called_once()
            mock_identity.assert_called_once()

            assert result.total_candidates == 0

    @pytest.mark.asyncio
    async def test_orchestrator_merges_candidates(
        self, mock_db_session, query_context, l2_memory
    ):
        """Should merge candidates from different strategies."""
        orchestrator = RetrievalOrchestrator(mock_db_session)

        # Mock strategies returning same memory
        scored_memory_1 = ScoredMemory(
            memory=l2_memory,
            memory_id=l2_memory.id,
            memory_type="L2",
            score_breakdown={"semantic": 0.9},
            retrieved_by=["vector"],
        )

        scored_memory_2 = ScoredMemory(
            memory=l2_memory,
            memory_id=l2_memory.id,
            memory_type="L2",
            score_breakdown={"recency": 0.8},
            retrieved_by=["recency"],
        )

        with patch.object(VectorRetriever, "retrieve", new_callable=AsyncMock) as mock_vector, \
             patch.object(RecencyRetriever, "retrieve", new_callable=AsyncMock) as mock_recency, \
             patch.object(EmotionalRetriever, "retrieve", new_callable=AsyncMock) as mock_emotional, \
             patch.object(IdentityLookup, "retrieve", new_callable=AsyncMock) as mock_identity:

            mock_vector.return_value = [scored_memory_1]
            mock_recency.return_value = [scored_memory_2]
            mock_emotional.return_value = []
            mock_identity.return_value = []

            result = await orchestrator.retrieve(query_context)

            # Should merge into 1 candidate
            assert result.total_candidates == 1

            # Merged memory should have both scores
            merged = result.memories[0]
            assert "semantic" in merged.score_breakdown
            assert "recency" in merged.score_breakdown

            # Should have both strategies in retrieved_by
            assert set(merged.retrieved_by) == {"vector", "recency"}

    @pytest.mark.asyncio
    async def test_orchestrator_handles_strategy_failure(
        self, mock_db_session, query_context
    ):
        """Should continue if one strategy fails."""
        orchestrator = RetrievalOrchestrator(mock_db_session)

        with patch.object(VectorRetriever, "retrieve", new_callable=AsyncMock) as mock_vector, \
             patch.object(RecencyRetriever, "retrieve", new_callable=AsyncMock) as mock_recency:

            # Vector fails
            mock_vector.side_effect = Exception("Vector search error")

            # Recency succeeds
            mock_recency.return_value = [
                ScoredMemory(
                    memory=MagicMock(),
                    memory_id=uuid4(),
                    memory_type="L2",
                    score_breakdown={"recency": 0.8},
                )
            ]

            result = await orchestrator.retrieve(query_context)

            # Should still return recency results
            assert result.total_candidates == 1


# ============================================================
# Individual Strategy Tests
# ============================================================


class TestRecencyRetriever:
    """Tests for RecencyRetriever."""

    @pytest.mark.asyncio
    async def test_recency_retriever_filters_by_time_window(
        self, mock_db_session, query_context, l2_memory
    ):
        """Should only retrieve memories within time window."""
        retriever = RecencyRetriever(mock_db_session, window_hours=72)

        # Mock recent memory
        recent_memory = l2_memory
        recent_memory.created_at = datetime.now(timezone.utc) - timedelta(hours=24)

        # Mock DB result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [recent_memory]
        mock_db_session.execute.return_value = mock_result

        candidates = await retriever.retrieve(query_context)

        assert len(candidates) == 1
        assert "recency" in candidates[0].score_breakdown

    @pytest.mark.asyncio
    async def test_recency_score_decay(self, mock_db_session, query_context, user_id, character_id):
        """Recency score should decay exponentially."""
        retriever = RecencyRetriever(mock_db_session, tau_hours=24.0)

        # Memory 12 hours ago
        memory_12h = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            episode_summary="测试记忆 12h",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(hours=12),
            episode_end_at=datetime.now(timezone.utc) - timedelta(hours=12),
            emotional_peak={"valence": 0.4, "arousal": 0.5},
            emotional_end={"valence": 0.3, "arousal": 0.4},
            emotional_significance=0.6,
            importance_score=0.7,
            initial_importance=0.7,
            recall_count=0,
            state="vivid",
            created_at=datetime.now(timezone.utc) - timedelta(hours=12),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=12),
        )

        # Memory 24 hours ago
        memory_24h = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            episode_summary="测试记忆 24h",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
            episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
            emotional_peak={"valence": 0.4, "arousal": 0.5},
            emotional_end={"valence": 0.3, "arousal": 0.4},
            emotional_significance=0.6,
            importance_score=0.7,
            initial_importance=0.7,
            recall_count=0,
            state="vivid",
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [memory_12h, memory_24h]
        mock_db_session.execute.return_value = mock_result

        candidates = await retriever.retrieve(query_context)

        assert len(candidates) == 2

        # Newer memory should have higher recency score
        scores = {str(c.memory_id): c.score_breakdown["recency"] for c in candidates}
        assert scores[str(memory_12h.id)] > scores[str(memory_24h.id)]


class TestEmotionalRetriever:
    """Tests for EmotionalRetriever."""

    @pytest.mark.asyncio
    async def test_emotional_retriever_skips_low_arousal(
        self, mock_db_session, query_context
    ):
        """Should skip query if arousal too low."""
        retriever = EmotionalRetriever(mock_db_session, min_arousal=0.3)

        # Low arousal query
        query_context.current_emotion = {"valence": 0.1, "arousal": 0.1}

        candidates = await retriever.retrieve(query_context)

        # Should skip (no DB query)
        assert len(candidates) == 0
        mock_db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_emotional_similarity(self, mock_db_session, query_context, user_id, character_id):
        """Should score by emotional distance."""
        retriever = EmotionalRetriever(mock_db_session)

        # Query emotion: valence=0.3, arousal=0.4
        query_context.current_emotion = {"valence": 0.3, "arousal": 0.4}

        # Similar memory
        similar_memory = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            episode_summary="类似情绪的记忆",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
            episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
            emotional_peak={"valence": 0.4, "arousal": 0.5},
            emotional_end={"valence": 0.3, "arousal": 0.4},
            emotional_significance=0.6,
            importance_score=0.7,
            initial_importance=0.7,
            recall_count=0,
            state="vivid",
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )

        # Different memory
        different_memory = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            episode_summary="不同情绪的记忆",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(hours=24),
            episode_end_at=datetime.now(timezone.utc) - timedelta(hours=24),
            emotional_peak={"valence": -0.8, "arousal": 0.8},
            emotional_end={"valence": -0.7, "arousal": 0.7},
            emotional_significance=0.8,
            importance_score=0.7,
            initial_importance=0.7,
            recall_count=0,
            state="vivid",
            created_at=datetime.now(timezone.utc) - timedelta(hours=24),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=24),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            similar_memory,
            different_memory,
        ]
        mock_db_session.execute.return_value = mock_result

        candidates = await retriever.retrieve(query_context, top_n=2)

        # Similar memory should score higher
        scores = {str(c.memory_id): c.score_breakdown["emotional"] for c in candidates}
        assert scores[str(similar_memory.id)] > scores[str(different_memory.id)]


# ============================================================
# Performance Tests
# ============================================================


class TestPerformance:
    """Performance tests for retriever."""

    @pytest.mark.asyncio
    async def test_parallel_execution_is_faster(
        self, mock_db_session, query_context
    ):
        """Parallel execution should be faster than sequential."""
        orchestrator = RetrievalOrchestrator(mock_db_session)

        # Mock slow strategies (50ms each)
        async def slow_retrieve(*args, **kwargs):
            await asyncio.sleep(0.05)
            return []

        with patch.object(VectorRetriever, "retrieve", slow_retrieve), \
             patch.object(RecencyRetriever, "retrieve", slow_retrieve), \
             patch.object(EmotionalRetriever, "retrieve", slow_retrieve), \
             patch.object(IdentityLookup, "retrieve", slow_retrieve):

            result = await orchestrator.retrieve(query_context)

            # 4 strategies × 50ms = 200ms if sequential
            # Should be ~50ms if parallel
            assert result.retrieval_time_ms < 150  # Allow some overhead
