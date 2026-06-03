"""
Tests for Consolidation Worker - SS02 §3.6

Test coverage:
1. Job idempotency (unique constraint)
2. 8-step pipeline execution
3. Episode clustering
4. Episode summarization (mocked LLM)
5. Fact reconciliation
6. L4 promotion logic
7. Batch decay application
8. Cross-user isolation

Author: 心屿团队
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

# Consolidator tests require Postgres (ARRAY/JSONB/vector columns).
# Skip in unit runs; the suite is exercised by tests/integration/.
pytestmark = pytest.mark.requires_postgres

from heart.ss02_memory.models import (
    ConsolidationJob,
    EpisodicMemory,
    FactNode,
    IdentityMemory,
    MemoryEncodingEvent,
)
from heart.workers.memory_consolidator import (
    ConsolidationWorker,
    EpisodeClusterer,
    EpisodeSummarizer,
    FactReconciler,
    L4Promoter,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def user_id():
    """Sample user ID."""
    return uuid4()


@pytest.fixture
def character_id():
    """Sample character ID."""
    return "rin"


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for episode summarization."""
    return json.dumps(
        {
            "episode_summary": "User discussed their cat named Laotie who is afraid of thunder.",
            "emotional_peak": {
                "valence": 0.6,
                "arousal": 0.4,
                "label": "joy",
            },
            "emotional_end": {
                "valence": 0.5,
                "arousal": 0.3,
                "label": "contentment",
            },
            "importance_estimate": 0.7,
        }
    )


@pytest.fixture
async def consolidation_job(async_session, user_id, character_id):
    """Create a pending consolidation job."""
    job = ConsolidationJob(
        job_id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        scheduled_for=datetime.now(timezone.utc),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )

    async_session.add(job)
    await async_session.commit()

    return job


@pytest.fixture
async def encoding_events(async_session, user_id, character_id):
    """Create sample encoding events."""
    events = []

    for i in range(3):
        event = MemoryEncodingEvent(
            event_id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            source_turn_id=uuid4(),
            source_user_text=f"User message {i}",
            source_assistant_text=f"Assistant response {i}",
            status="llm_done",
            llm_extraction={
                "facts": [],
                "emotion_peak": {"valence": 0.5, "arousal": 0.3},
                "importance_estimate": 0.6,
            },
            created_at=datetime.now(timezone.utc) - timedelta(hours=i),
        )

        async_session.add(event)
        events.append(event)

    await async_session.commit()

    return events


@pytest.fixture
async def fact_nodes(async_session, user_id, character_id):
    """Create sample L3 facts."""
    facts = []

    # Fact 1: High importance, high confirmation (L4 candidate)
    fact1 = FactNode(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        predicate="owns",
        subject="user",
        object="cat named Laotie",
        literal_text="user owns cat named Laotie",
        raw_evidence="I have a cat named Laotie",
        source_turn_ids=[uuid4()],
        confidence=0.9,
        emotional_charge=0.5,
        importance=0.85,
        importance_score=0.85,
        confirmation_count=5,
        is_identity_level=False,
        state="vivid",
        do_not_recall=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        updated_at=datetime.now(timezone.utc),
    )

    # Fact 2: Low importance (should not promote)
    fact2 = FactNode(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        predicate="likes",
        subject="user",
        object="coffee",
        literal_text="user likes coffee",
        raw_evidence="I like coffee",
        source_turn_ids=[uuid4()],
        confidence=0.7,
        emotional_charge=0.2,
        importance=0.4,
        importance_score=0.4,
        confirmation_count=1,
        is_identity_level=False,
        state="vivid",
        do_not_recall=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
        updated_at=datetime.now(timezone.utc),
    )

    async_session.add(fact1)
    async_session.add(fact2)
    facts.extend([fact1, fact2])

    await async_session.commit()

    return facts


# ============================================================
# Test: Idempotency
# ============================================================


class TestIdempotency:
    """Test consolidation job idempotency."""

    async def test_unique_constraint_enforced(self, async_session, user_id, character_id):
        """Cannot create duplicate job for same (user, character, scheduled_for)."""
        scheduled_for = datetime.now(timezone.utc)

        # Create first job
        job1 = ConsolidationJob(
            job_id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            scheduled_for=scheduled_for,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

        async_session.add(job1)
        await async_session.commit()

        # Try to create duplicate job
        job2 = ConsolidationJob(
            job_id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            scheduled_for=scheduled_for,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

        async_session.add(job2)

        # Should raise unique constraint violation
        with pytest.raises(Exception):  # IntegrityError
            await async_session.commit()

    async def test_already_processed_job_skipped(self, async_session, consolidation_job):
        """Worker should skip jobs that are already processed."""
        # Mark job as succeeded
        consolidation_job.status = "succeeded"
        consolidation_job.completed_at = datetime.now(timezone.utc)
        await async_session.commit()

        # Create worker
        worker = ConsolidationWorker(lambda: async_session)

        # Process job - should skip
        await worker._process_job(consolidation_job)

        # Reload job
        stmt = select(ConsolidationJob).where(ConsolidationJob.job_id == consolidation_job.job_id)
        result = await async_session.execute(stmt)
        job = result.scalar_one()

        # Status should still be succeeded (not changed)
        assert job.status == "succeeded"


# ============================================================
# Test: Episode Clustering
# ============================================================


class TestEpisodeClustering:
    """Test episode clustering logic."""

    async def test_cluster_turns_by_max_size(self, async_session, user_id, character_id):
        """Turns should be split into episodes when max size reached."""
        turn_ids = [uuid4() for _ in range(25)]

        clusters = await EpisodeClusterer.cluster_turns(
            async_session, turn_ids, user_id, character_id
        )

        # With MAX_TURNS_PER_EPISODE=10, should have 3 clusters (10, 10, 5)
        assert len(clusters) == 3
        assert len(clusters[0]) == 10
        assert len(clusters[1]) == 10
        assert len(clusters[2]) == 5

    async def test_empty_turns_returns_empty_clusters(self, async_session, user_id, character_id):
        """Empty turn list should return empty clusters."""
        clusters = await EpisodeClusterer.cluster_turns(async_session, [], user_id, character_id)

        assert clusters == []


# ============================================================
# Test: Episode Summarization
# ============================================================


class TestEpisodeSummarization:
    """Test episode summarization with LLM."""

    @patch("heart.workers.memory_consolidator.get_model_router")
    async def test_summarize_episode_success(
        self, mock_router, async_session, character_id, mock_llm_response
    ):
        """Episode summarization should parse LLM response correctly."""
        # Mock LLM call
        mock_router_instance = AsyncMock()
        mock_router_instance.call_cheap = AsyncMock(return_value=mock_llm_response)
        mock_router.return_value = mock_router_instance

        turn_ids = [uuid4(), uuid4(), uuid4()]

        result = await EpisodeSummarizer.summarize_episode(async_session, turn_ids, character_id)

        # Check result structure
        assert "episode_summary" in result
        assert "emotional_peak" in result
        assert "emotional_end" in result
        assert "importance_estimate" in result
        assert "emotional_significance" in result

        # Check emotional_significance calculated with Peak-End Rule
        # peak_intensity = (0.6 + 0.4) / 2 = 0.5
        # end_intensity = (0.5 + 0.3) / 2 = 0.4
        # significance = 0.6 * 0.5 + 0.4 * 0.4 = 0.46
        assert abs(result["emotional_significance"] - 0.46) < 0.01

    @patch("heart.workers.memory_consolidator.get_model_router")
    async def test_summarize_episode_invalid_json(self, mock_router, async_session, character_id):
        """Invalid JSON from LLM should raise ValueError."""
        # Mock LLM call with invalid JSON
        mock_router_instance = AsyncMock()
        mock_router_instance.call_cheap = AsyncMock(return_value="not json")
        mock_router.return_value = mock_router_instance

        turn_ids = [uuid4()]

        with pytest.raises(ValueError, match="Invalid JSON"):
            await EpisodeSummarizer.summarize_episode(async_session, turn_ids, character_id)

    @patch("heart.workers.memory_consolidator.get_model_router")
    async def test_summarize_episode_missing_fields(self, mock_router, async_session, character_id):
        """Missing required fields should raise ValueError."""
        # Mock LLM call with incomplete response
        mock_router_instance = AsyncMock()
        mock_router_instance.call_cheap = AsyncMock(
            return_value=json.dumps({"episode_summary": "test"})
        )
        mock_router.return_value = mock_router_instance

        turn_ids = [uuid4()]

        with pytest.raises(ValueError, match="Missing required field"):
            await EpisodeSummarizer.summarize_episode(async_session, turn_ids, character_id)


# ============================================================
# Test: Fact Reconciliation
# ============================================================


class TestFactReconciliation:
    """Test L3 fact reconciliation."""

    async def test_fact_reinforcement(self, async_session, user_id, character_id):
        """Duplicate facts should reinforce existing fact."""
        # Create existing fact
        existing = FactNode(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            predicate="owns",
            subject="user",
            object="cat",
            literal_text="user owns cat",
            raw_evidence="I have a cat",
            source_turn_ids=[uuid4()],
            confidence=0.8,
            emotional_charge=0.5,
            importance=0.6,
            importance_score=0.6,
            confirmation_count=1,
            state="vivid",
            do_not_recall=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        async_session.add(existing)
        await async_session.commit()

        # Create new fact (same predicate + subject + object)
        new = FactNode(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            predicate="owns",
            subject="user",
            object="cat",
            literal_text="user owns cat",
            raw_evidence="I own a cat",
            source_turn_ids=[uuid4()],
            confidence=0.9,
            emotional_charge=0.5,
            importance=0.7,
            importance_score=0.7,
            confirmation_count=0,
            state="vivid",
            do_not_recall=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        async_session.add(new)
        await async_session.commit()

        # Reconcile
        reinforced, contradicted = await FactReconciler.reconcile_facts(
            async_session, [new.id], user_id, character_id
        )

        # Check reinforcement
        assert existing.id in reinforced
        assert len(contradicted) == 0

        # Reload existing fact
        stmt = select(FactNode).where(FactNode.id == existing.id)
        result = await async_session.execute(stmt)
        updated = result.scalar_one()

        # Confirmation count should increase
        assert updated.confirmation_count == 2
        # Confidence should be max of both
        assert updated.confidence == 0.9

    async def test_fact_contradiction(self, async_session, user_id, character_id):
        """Contradicting facts should mark existing as contradicted."""
        # Create existing fact
        existing = FactNode(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            predicate="owns",
            subject="user",
            object="cat",
            literal_text="user owns cat",
            raw_evidence="I have a cat",
            source_turn_ids=[uuid4()],
            confidence=0.8,
            emotional_charge=0.5,
            importance=0.6,
            importance_score=0.6,
            confirmation_count=1,
            contradiction_count=0,
            contradicted_by_ids=[],
            state="vivid",
            do_not_recall=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        async_session.add(existing)
        await async_session.commit()

        # Create contradicting fact (same predicate + subject, different object)
        new = FactNode(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            predicate="owns",
            subject="user",
            object="dog",  # Different!
            literal_text="user owns dog",
            raw_evidence="I own a dog",
            source_turn_ids=[uuid4()],
            confidence=0.9,
            emotional_charge=0.5,
            importance=0.7,
            importance_score=0.7,
            confirmation_count=0,
            state="vivid",
            do_not_recall=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        async_session.add(new)
        await async_session.commit()

        # Reconcile
        reinforced, contradicted = await FactReconciler.reconcile_facts(
            async_session, [new.id], user_id, character_id
        )

        # Check contradiction
        assert existing.id in contradicted
        assert len(reinforced) == 0

        # Reload existing fact
        stmt = select(FactNode).where(FactNode.id == existing.id)
        result = await async_session.execute(stmt)
        updated = result.scalar_one()

        # Contradiction count should increase
        assert updated.contradiction_count == 1
        assert new.id in updated.contradicted_by_ids


# ============================================================
# Test: L4 Promotion
# ============================================================


class TestL4Promotion:
    """Test L3 → L4 promotion logic."""

    async def test_promote_high_importance_high_confirmation(
        self, async_session, user_id, character_id, fact_nodes
    ):
        """High importance + high confirmation should promote to L4."""
        # fact_nodes[0] has importance=0.85, confirmation=5
        promoted = await L4Promoter.check_promotions(async_session, user_id, character_id)

        # Should have promoted 1 fact
        assert len(promoted) == 1
        assert fact_nodes[0].id in promoted

        # Check L4 created
        stmt = select(IdentityMemory).where(IdentityMemory.source_fact_id == fact_nodes[0].id)
        result = await async_session.execute(stmt)
        identity = result.scalar_one()

        assert identity.user_id == user_id
        assert identity.character_id == character_id
        assert identity.key == "owns"
        assert identity.value == "cat named Laotie"

    async def test_no_promotion_low_importance(
        self, async_session, user_id, character_id, fact_nodes
    ):
        """Low importance facts should not promote."""
        # fact_nodes[1] has importance=0.4
        # Before promotion, check count
        stmt = select(IdentityMemory).where(IdentityMemory.user_id == user_id)
        result = await async_session.execute(stmt)
        len(result.scalars().all())

        promoted = await L4Promoter.check_promotions(async_session, user_id, character_id)

        # fact_nodes[1] should not be in promoted
        assert fact_nodes[1].id not in promoted

    async def test_already_promoted_skipped(self, async_session, user_id, character_id, fact_nodes):
        """Facts already promoted should be skipped."""
        # Promote fact_nodes[0] first time
        promoted1 = await L4Promoter.check_promotions(async_session, user_id, character_id)

        assert len(promoted1) == 1

        # Try to promote again
        await L4Promoter.check_promotions(async_session, user_id, character_id)

        # Should not promote again (already exists)
        # But promoted2 might be empty or contain it - implementation dependent
        # The key is no duplicate L4 entries

        stmt = select(IdentityMemory).where(IdentityMemory.source_fact_id == fact_nodes[0].id)
        result = await async_session.execute(stmt)
        identities = result.scalars().all()

        # Should only have 1 L4 entry
        assert len(identities) == 1


# ============================================================
# Test: Cross-User Isolation
# ============================================================


class TestCrossUserIsolation:
    """Test that consolidation doesn't leak across users."""

    async def test_no_cross_user_fact_reconciliation(self, async_session, character_id):
        """Fact reconciliation should not match facts from different users."""
        user1 = uuid4()
        user2 = uuid4()

        # Create fact for user1
        fact1 = FactNode(
            id=uuid4(),
            user_id=user1,
            character_id=character_id,
            predicate="owns",
            subject="user",
            object="cat",
            literal_text="user owns cat",
            raw_evidence="I have a cat",
            source_turn_ids=[uuid4()],
            confidence=0.8,
            emotional_charge=0.5,
            importance=0.6,
            importance_score=0.6,
            confirmation_count=1,
            state="vivid",
            do_not_recall=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Create same fact for user2
        fact2 = FactNode(
            id=uuid4(),
            user_id=user2,
            character_id=character_id,
            predicate="owns",
            subject="user",
            object="cat",
            literal_text="user owns cat",
            raw_evidence="I have a cat",
            source_turn_ids=[uuid4()],
            confidence=0.9,
            emotional_charge=0.5,
            importance=0.7,
            importance_score=0.7,
            confirmation_count=0,
            state="vivid",
            do_not_recall=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        async_session.add(fact1)
        async_session.add(fact2)
        await async_session.commit()

        # Reconcile for user2
        reinforced, contradicted = await FactReconciler.reconcile_facts(
            async_session, [fact2.id], user2, character_id
        )

        # Should NOT reinforce user1's fact
        assert fact1.id not in reinforced
        assert len(reinforced) == 0

        # Reload fact1 - should be unchanged
        stmt = select(FactNode).where(FactNode.id == fact1.id)
        result = await async_session.execute(stmt)
        unchanged = result.scalar_one()

        assert unchanged.confirmation_count == 1  # Still 1, not 2


# ============================================================
# Test: Batch Decay
# ============================================================


class TestBatchDecay:
    """Test batch decay application."""

    async def test_decay_applied_to_episodes(self, async_session, user_id, character_id):
        """Decay should be applied to all episodes."""
        # Create old episode
        old_episode = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            episode_summary="Old episode",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=datetime.now(timezone.utc) - timedelta(days=30),
            episode_end_at=datetime.now(timezone.utc) - timedelta(days=30),
            emotional_peak={"valence": 0.5, "arousal": 0.3},
            emotional_end={"valence": 0.4, "arousal": 0.2},
            emotional_significance=0.4,
            importance_score=0.8,
            initial_importance=0.8,
            decay_immunity=0.0,
            state="vivid",
            recall_count=0,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            updated_at=datetime.now(timezone.utc) - timedelta(days=30),
        )

        async_session.add(old_episode)
        await async_session.commit()

        # Apply decay
        worker = ConsolidationWorker(lambda: async_session)
        await worker._apply_batch_decay(async_session, user_id, character_id)

        # Reload episode
        stmt = select(EpisodicMemory).where(EpisodicMemory.id == old_episode.id)
        result = await async_session.execute(stmt)
        updated = result.scalar_one()

        # Importance should have decayed
        assert updated.importance_score < 0.8
        # State might have changed from vivid
        assert updated.state in ["vivid", "fading", "faint"]


# ============================================================
# Test: Full Pipeline Integration
# ============================================================


class TestFullPipeline:
    """Test full 8-step consolidation pipeline."""

    @patch("heart.workers.memory_consolidator.get_model_router")
    async def test_full_consolidation_pipeline(
        self,
        mock_router,
        async_session,
        consolidation_job,
        encoding_events,
        mock_llm_response,
    ):
        """Full consolidation should complete all 8 steps."""
        # Mock LLM
        mock_router_instance = AsyncMock()
        mock_router_instance.call_cheap = AsyncMock(return_value=mock_llm_response)
        mock_router.return_value = mock_router_instance

        # Run consolidation
        worker = ConsolidationWorker(lambda: async_session)
        await worker._process_job(consolidation_job)

        # Reload job
        stmt = select(ConsolidationJob).where(ConsolidationJob.job_id == consolidation_job.job_id)
        result = await async_session.execute(stmt)
        job = result.scalar_one()

        # Job should be succeeded
        assert job.status == "succeeded"
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.duration_ms is not None

        # Should have created episodes
        assert job.episodes_created is not None
        assert len(job.episodes_created) > 0

        # Duration should be reasonable (< 30s target)
        assert job.duration_ms < 30000
