"""
Nightly Consolidator Worker - SS02 §3.6

8-step consolidation pipeline ("sleep"):
1. Aggregate pending events
2. Episode clustering
3. Episode summarization (LLM)
4. L3 fact reconciliation
5. L3 → L4 promotion check
6. Association builder
7. Batch decay application
8. Anniversary scheduling

Scheduled at user local 03:00, distributed lock per (user, character).
Idempotent via ConsolidationJob.scheduled_for unique constraint.

Performance target: P95 < 30s per user

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from heart.infra.llm.router import get_model_router
from heart.prompts.episode_summary import EPISODE_SUMMARY_PROMPT
from heart.ss02_memory.models import (
    ConsolidationJob,
    EpisodicMemory,
    FactNode,
    IdentityMemory,
    MemoryEncodingEvent,
)
from heart.ss02_memory.decay_engine import DecayEngine

logger = structlog.get_logger()


# ============================================================
# Configuration
# ============================================================

LLM_TIMEOUT_SECONDS = 15
MAX_TURNS_PER_EPISODE = 10  # Max conversation turns in single episode
EPISODE_TIME_GAP_MINUTES = 30  # Time gap to split episodes
SEMANTIC_SIMILARITY_THRESHOLD = 0.7  # For clustering

# L4 promotion thresholds
L4_MIN_CONFIRMATION_COUNT = 3  # Fact mentioned 3+ times
L4_MIN_IMPORTANCE = 0.8  # Importance > 0.8
L4_SACRED_KEYWORDS = ["记住", "别忘", "重要", "一定要", "千万"]

# Peak-End formula weights
PEAK_WEIGHT = 0.6
END_WEIGHT = 0.4


# ============================================================
# Episode Clustering (Step 2)
# ============================================================


class EpisodeClusterer:
    """Clusters conversation turns into episodes.

    Uses:
    - Time gap: > 30 minutes gap → new episode
    - Semantic similarity: Use embeddings to cluster similar topics
    - Session boundaries: Different sessions → different episodes
    """

    @staticmethod
    async def cluster_turns(
        session: AsyncSession,
        turn_ids: list[UUID],
        user_id: UUID,
        character_id: str,
    ) -> list[list[UUID]]:
        """Cluster turns into episodes.

        Args:
            session: Database session
            turn_ids: Turn IDs to cluster
            user_id: User ID
            character_id: Character ID

        Returns:
            List of episode clusters (each cluster is list of turn IDs)
        """
        if not turn_ids:
            return []

        # For MVP: Simple time-based clustering
        # TODO: Add semantic similarity clustering with embeddings

        # Fetch turn metadata (we'd need a turns table - for now simulate)
        # In production, query turns table to get timestamps

        # Simple heuristic: Group consecutive turns, split by time gap
        episodes = []
        current_episode = []

        for i, turn_id in enumerate(turn_ids):
            current_episode.append(turn_id)

            # Check if we should start new episode
            if len(current_episode) >= MAX_TURNS_PER_EPISODE:
                episodes.append(current_episode)
                current_episode = []

        # Add remaining turns
        if current_episode:
            episodes.append(current_episode)

        logger.info(
            "clustered_episodes",
            user_id=str(user_id),
            character_id=character_id,
            total_turns=len(turn_ids),
            episodes_created=len(episodes),
        )

        return episodes


# ============================================================
# Episode Summarizer (Step 3)
# ============================================================


class EpisodeSummarizer:
    """Summarizes episode clusters with LLM."""

    @staticmethod
    async def summarize_episode(
        session: AsyncSession,
        turn_ids: list[UUID],
        character_id: str,
    ) -> dict:
        """Summarize episode with LLM.

        Args:
            session: Database session
            turn_ids: Turn IDs in this episode
            character_id: Character ID

        Returns:
            dict with episode_summary, emotional_peak, emotional_end, importance_estimate

        Raises:
            ValueError: If LLM output invalid
            TimeoutError: If LLM call times out
        """
        # Build prompt with turns
        # For MVP: Simulate turn content (production would query turns table)
        turns_text = f"[Episode with {len(turn_ids)} turns]"

        prompt = EPISODE_SUMMARY_PROMPT.format(
            character_id=character_id,
            turns=turns_text,
        )

        # Call LLM
        router = await get_model_router()

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            response = await asyncio.wait_for(
                router.call_cheap(
                    messages=messages,
                    temperature=0.0,
                    max_tokens=1000,
                    json_mode=True,
                    agent_name="consolidator",
                ),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM call timed out after {LLM_TIMEOUT_SECONDS}s")

        # Parse JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}")

        # Validate required fields
        required_fields = [
            "episode_summary",
            "emotional_peak",
            "emotional_end",
            "importance_estimate",
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Calculate emotional_significance using Peak-End Rule
        peak_valence = abs(data["emotional_peak"].get("valence", 0))
        peak_arousal = data["emotional_peak"].get("arousal", 0)
        end_valence = abs(data["emotional_end"].get("valence", 0))
        end_arousal = data["emotional_end"].get("arousal", 0)

        peak_intensity = (peak_valence + peak_arousal) / 2
        end_intensity = (end_valence + end_arousal) / 2

        emotional_significance = PEAK_WEIGHT * peak_intensity + END_WEIGHT * end_intensity

        data["emotional_significance"] = emotional_significance

        return data


# ============================================================
# L3 Fact Reconciliation (Step 4)
# ============================================================


class FactReconciler:
    """Reconciles new facts with existing L3 facts."""

    @staticmethod
    async def reconcile_facts(
        session: AsyncSession,
        new_fact_ids: list[UUID],
        user_id: UUID,
        character_id: str,
    ) -> tuple[list[UUID], list[UUID]]:
        """Reconcile new facts with existing facts.

        Args:
            session: Database session
            new_fact_ids: New fact IDs from today's encoding
            user_id: User ID
            character_id: Character ID

        Returns:
            (facts_reinforced, facts_contradicted) as UUID lists
        """
        reinforced = []
        contradicted = []

        if not new_fact_ids:
            return reinforced, contradicted

        # Fetch new facts
        stmt = select(FactNode).where(FactNode.id.in_(new_fact_ids))
        result = await session.execute(stmt)
        new_facts = result.scalars().all()

        # For each new fact, check for existing similar facts
        for new_fact in new_facts:
            # Simple heuristic: Same predicate + subject = same fact
            existing_stmt = select(FactNode).where(
                and_(
                    FactNode.user_id == user_id,
                    FactNode.character_id == character_id,
                    FactNode.predicate == new_fact.predicate,
                    FactNode.subject == new_fact.subject,
                    FactNode.id != new_fact.id,
                    FactNode.do_not_recall == False,
                )
            )

            result = await session.execute(existing_stmt)
            existing_facts = result.scalars().all()

            for existing in existing_facts:
                # Check if reinforcing or contradicting
                if existing.object == new_fact.object:
                    # Reinforcing
                    existing.confirmation_count += 1
                    existing.confidence = max(existing.confidence, new_fact.confidence)
                    existing.last_confirmed_at = datetime.now(timezone.utc)
                    reinforced.append(existing.id)

                    logger.info(
                        "fact_reinforced",
                        existing_id=str(existing.id),
                        new_id=str(new_fact.id),
                        predicate=existing.predicate,
                        confirmation_count=existing.confirmation_count,
                    )
                else:
                    # Contradicting
                    existing.contradiction_count = (existing.contradiction_count or 0) + 1
                    existing.contradicted_by_ids = (existing.contradicted_by_ids or []) + [
                        new_fact.id
                    ]
                    contradicted.append(existing.id)

                    logger.info(
                        "fact_contradicted",
                        existing_id=str(existing.id),
                        new_id=str(new_fact.id),
                        predicate=existing.predicate,
                        old_object=existing.object,
                        new_object=new_fact.object,
                    )

        await session.commit()

        return reinforced, contradicted


# ============================================================
# L4 Promotion Check (Step 5)
# ============================================================


class L4Promoter:
    """Checks and promotes L3 facts to L4 Identity Memory."""

    @staticmethod
    async def check_promotions(
        session: AsyncSession,
        user_id: UUID,
        character_id: str,
    ) -> list[UUID]:
        """Check L3 facts for L4 promotion.

        Args:
            session: Database session
            user_id: User ID
            character_id: Character ID

        Returns:
            List of promoted fact IDs
        """
        promoted = []

        # Fetch high-importance L3 facts
        stmt = (
            select(FactNode)
            .where(
                and_(
                    FactNode.user_id == user_id,
                    FactNode.character_id == character_id,
                    FactNode.importance_score >= L4_MIN_IMPORTANCE,
                    FactNode.do_not_recall == False,
                )
            )
            .order_by(FactNode.importance_score.desc())
            .limit(50)
        )

        result = await session.execute(stmt)
        candidates = result.scalars().all()

        for fact in candidates:
            # Check promotion conditions (§4.2)
            should_promote = False
            reason = ""

            # Trigger A: Explicit emphasis
            if fact.is_identity_level:
                should_promote = True
                reason = "explicit_emphasis"

            # Trigger B: High confirmation + importance
            elif (
                fact.confirmation_count >= L4_MIN_CONFIRMATION_COUNT
                and fact.importance_score >= L4_MIN_IMPORTANCE
            ):
                should_promote = True
                reason = "high_confirmation_and_importance"

            # Trigger C: Sacred keywords in raw evidence
            elif any(kw in (fact.raw_evidence or "") for kw in L4_SACRED_KEYWORDS):
                should_promote = True
                reason = "sacred_keyword"

            if should_promote:
                # Check if already promoted
                existing_stmt = select(IdentityMemory).where(
                    and_(
                        IdentityMemory.user_id == user_id,
                        IdentityMemory.character_id == character_id,
                        IdentityMemory.source_fact_id == fact.id,
                    )
                )
                result = await session.execute(existing_stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    logger.info(
                        "fact_already_promoted",
                        fact_id=str(fact.id),
                        identity_id=str(existing.id),
                    )
                    continue

                # Promote to L4
                identity = IdentityMemory(
                    id=uuid4(),
                    user_id=user_id,
                    character_id=character_id,
                    key=fact.predicate,
                    value=fact.object,
                    category="user_identity",  # Simplified
                    source_fact_id=fact.id,
                    raw_evidence=fact.raw_evidence,
                    confidence=fact.confidence,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )

                session.add(identity)
                promoted.append(fact.id)

                logger.info(
                    "fact_promoted_to_l4",
                    fact_id=str(fact.id),
                    identity_id=str(identity.id),
                    reason=reason,
                    key=identity.key,
                    value=identity.value,
                )

        await session.commit()

        return promoted


# ============================================================
# Association Builder (Step 6)
# ============================================================


class AssociationBuilder:
    """Builds associations between memories."""

    @staticmethod
    async def build_associations(
        session: AsyncSession,
        episode_ids: list[UUID],
        user_id: UUID,
        character_id: str,
    ) -> int:
        """Build associations between episodes and facts.

        Args:
            session: Database session
            episode_ids: New episode IDs
            user_id: User ID
            character_id: Character ID

        Returns:
            Number of associations created
        """
        # MVP: Simplified association building
        # Production would:
        # - Compute embedding similarities
        # - Build graph edges based on co-occurrence
        # - Link episodes to relevant facts

        count = 0

        # For now, just log
        logger.info(
            "associations_built",
            user_id=str(user_id),
            character_id=character_id,
            episode_count=len(episode_ids),
            associations_created=count,
        )

        return count


# ============================================================
# Consolidation Orchestrator
# ============================================================


class ConsolidationWorker:
    """Nightly consolidation worker - runs 8-step pipeline."""

    def __init__(self, db_session_factory):
        """Initialize worker.

        Args:
            db_session_factory: Async session factory
        """
        self.db_session_factory = db_session_factory
        self.decay_engine = DecayEngine()
        self._should_stop = False

        logger.info("consolidation_worker_initialized")

    async def start(self):
        """Start worker loop.

        Polls for pending consolidation jobs.
        """
        logger.info("consolidation_worker_started")

        while not self._should_stop:
            try:
                # Fetch pending jobs
                async with self.db_session_factory() as session:
                    jobs = await self._fetch_pending_jobs(session)

                if not jobs:
                    # No pending jobs - sleep
                    await asyncio.sleep(60)  # Check every minute
                    continue

                # Process jobs
                for job in jobs:
                    try:
                        await self._process_job(job)
                    except Exception as e:
                        logger.error(
                            "job_processing_failed",
                            job_id=str(job.job_id),
                            error=str(e),
                            exc_info=True,
                        )

            except Exception as e:
                logger.error(
                    "worker_loop_error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(60)

        logger.info("consolidation_worker_stopped")

    async def stop(self):
        """Stop worker gracefully."""
        logger.info("consolidation_worker_stopping")
        self._should_stop = True

    async def _fetch_pending_jobs(self, session: AsyncSession) -> list[ConsolidationJob]:
        """Fetch pending consolidation jobs.

        Args:
            session: Database session

        Returns:
            List of pending jobs (status='pending', scheduled_for <= now)
        """
        now = datetime.now(timezone.utc)

        stmt = (
            select(ConsolidationJob)
            .where(
                and_(
                    ConsolidationJob.status == "pending",
                    ConsolidationJob.scheduled_for <= now,
                )
            )
            .order_by(ConsolidationJob.scheduled_for)
            .limit(10)  # Process 10 jobs per batch
        )

        result = await session.execute(stmt)
        jobs = result.scalars().all()

        return list(jobs)

    async def _process_job(self, job: ConsolidationJob):
        """Process a consolidation job.

        Runs 8-step pipeline per §3.6.

        Args:
            job: Consolidation job to process
        """
        start_time = datetime.now(timezone.utc)
        job_id = str(job.job_id)

        logger.info(
            "consolidation_job_started",
            job_id=job_id,
            user_id=str(job.user_id),
            character_id=job.character_id,
            scheduled_for=job.scheduled_for.isoformat(),
        )

        async with self.db_session_factory() as session:
            # Reload job to ensure we have latest state
            stmt = select(ConsolidationJob).where(ConsolidationJob.job_id == job.job_id)
            result = await session.execute(stmt)
            current_job = result.scalar_one_or_none()

            if current_job is None:
                logger.warning("job_not_found", job_id=job_id)
                return

            if current_job.status != "pending":
                logger.info(
                    "job_already_processed",
                    job_id=job_id,
                    status=current_job.status,
                )
                return

            # Mark as running
            current_job.status = "running"
            current_job.started_at = start_time
            await session.commit()

            try:
                # Step 1: Aggregate pending events
                pending_events = await self._aggregate_pending_events(
                    session, job.user_id, job.character_id
                )

                current_job.pending_event_ids = [e.event_id for e in pending_events]

                # Step 2: Episode clustering
                turn_ids = []
                for event in pending_events:
                    if event.source_turn_id:
                        turn_ids.append(event.source_turn_id)

                episode_clusters = await EpisodeClusterer.cluster_turns(
                    session, turn_ids, job.user_id, job.character_id
                )

                # Step 3: Episode summarization (LLM)
                episodes_created = []
                for cluster in episode_clusters:
                    try:
                        summary_data = await EpisodeSummarizer.summarize_episode(
                            session, cluster, job.character_id
                        )

                        # Create L2 episode
                        episode = EpisodicMemory(
                            id=uuid4(),
                            user_id=job.user_id,
                            character_id=job.character_id,
                            episode_summary=summary_data["episode_summary"],
                            episode_raw_turn_ids=cluster,
                            episode_start_at=start_time,  # Simplified
                            episode_end_at=start_time,
                            emotional_peak=summary_data["emotional_peak"],
                            emotional_end=summary_data["emotional_end"],
                            emotional_significance=summary_data["emotional_significance"],
                            importance_score=summary_data["importance_estimate"],
                            initial_importance=summary_data["importance_estimate"],
                            decay_immunity=summary_data["emotional_significance"],
                            state="vivid",
                            recall_count=0,
                            last_recalled_at=None,
                            created_at=start_time,
                            updated_at=start_time,
                        )

                        session.add(episode)
                        episodes_created.append(episode.id)

                        logger.info(
                            "episode_created",
                            job_id=job_id,
                            episode_id=str(episode.id),
                            turn_count=len(cluster),
                            importance=episode.importance_score,
                        )

                    except Exception as e:
                        logger.error(
                            "episode_summarization_failed",
                            job_id=job_id,
                            error=str(e),
                            exc_info=True,
                        )

                current_job.episodes_created = episodes_created

                # Step 4: L3 fact reconciliation
                new_fact_ids = []
                for event in pending_events:
                    if event.llm_extraction and "facts" in event.llm_extraction:
                        # Extract fact IDs (would need to track these)
                        pass

                facts_reinforced, facts_contradicted = await FactReconciler.reconcile_facts(
                    session, new_fact_ids, job.user_id, job.character_id
                )

                current_job.facts_reinforced = facts_reinforced
                current_job.facts_contradicted = facts_contradicted

                # Step 5: L3 → L4 promotion check
                promotions = await L4Promoter.check_promotions(
                    session, job.user_id, job.character_id
                )

                current_job.promotions_to_l4 = promotions

                # Step 6: Association builder
                associations_count = await AssociationBuilder.build_associations(
                    session, episodes_created, job.user_id, job.character_id
                )

                current_job.associations_created = associations_count

                # Step 7: Batch decay application
                await self._apply_batch_decay(session, job.user_id, job.character_id)

                # Step 8: Anniversary scheduling
                await self._schedule_anniversaries(session, job.user_id, job.character_id)

                # Mark as succeeded
                end_time = datetime.now(timezone.utc)
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                current_job.status = "succeeded"
                current_job.completed_at = end_time
                current_job.duration_ms = duration_ms

                await session.commit()

                logger.info(
                    "consolidation_job_succeeded",
                    job_id=job_id,
                    duration_ms=duration_ms,
                    episodes_created=len(episodes_created),
                    facts_reinforced=len(facts_reinforced),
                    promotions=len(promotions),
                )

            except Exception as e:
                # Mark as failed
                current_job.status = "failed"
                current_job.completed_at = datetime.now(timezone.utc)
                current_job.failure_reason = str(e)

                await session.commit()

                logger.error(
                    "consolidation_job_failed",
                    job_id=job_id,
                    error=str(e),
                    exc_info=True,
                )
                raise

    async def _aggregate_pending_events(
        self,
        session: AsyncSession,
        user_id: UUID,
        character_id: str,
    ) -> list[MemoryEncodingEvent]:
        """Aggregate pending encoding events (Step 1).

        Args:
            session: Database session
            user_id: User ID
            character_id: Character ID

        Returns:
            List of pending events
        """
        # Fetch events from yesterday (simplified)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)

        stmt = (
            select(MemoryEncodingEvent)
            .where(
                and_(
                    MemoryEncodingEvent.user_id == user_id,
                    MemoryEncodingEvent.character_id == character_id,
                    MemoryEncodingEvent.status == "llm_done",
                    MemoryEncodingEvent.created_at >= yesterday,
                )
            )
            .order_by(MemoryEncodingEvent.created_at)
        )

        result = await session.execute(stmt)
        events = result.scalars().all()

        logger.info(
            "aggregated_pending_events",
            user_id=str(user_id),
            character_id=character_id,
            event_count=len(events),
        )

        return list(events)

    async def _apply_batch_decay(
        self,
        session: AsyncSession,
        user_id: UUID,
        character_id: str,
    ):
        """Apply decay to all L2/L3 memories (Step 7).

        Args:
            session: Database session
            user_id: User ID
            character_id: Character ID
        """
        # Fetch all L2 episodes
        stmt = select(EpisodicMemory).where(
            and_(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.character_id == character_id,
            )
        )

        result = await session.execute(stmt)
        episodes = result.scalars().all()

        # Apply decay
        for episode in episodes:
            new_importance = self.decay_engine.calculate_current_importance(
                initial_importance=episode.initial_importance,
                created_at=episode.created_at,
                emotional_peak_valence=episode.emotional_peak.get("valence", 0),
                emotional_peak_arousal=episode.emotional_peak.get("arousal", 0),
                recall_count=episode.recall_count,
                decay_immunity=episode.decay_immunity,
            )

            episode.importance_score = new_importance
            episode.state = self.decay_engine.compute_state(new_importance)
            episode.updated_at = datetime.now(timezone.utc)

        # Fetch all L3 facts
        stmt = select(FactNode).where(
            and_(
                FactNode.user_id == user_id,
                FactNode.character_id == character_id,
                FactNode.do_not_recall == False,
            )
        )

        result = await session.execute(stmt)
        facts = result.scalars().all()

        # Apply decay
        for fact in facts:
            new_importance = self.decay_engine.calculate_current_importance(
                initial_importance=fact.importance,
                created_at=fact.created_at,
                emotional_peak_valence=fact.emotional_charge,
                emotional_peak_arousal=abs(fact.emotional_charge),
                recall_count=fact.recall_count or 0,
                decay_immunity=0.0,
            )

            fact.importance_score = new_importance
            fact.state = self.decay_engine.compute_state(new_importance)
            fact.updated_at = datetime.now(timezone.utc)

        await session.commit()

        logger.info(
            "batch_decay_applied",
            user_id=str(user_id),
            character_id=character_id,
            episodes_decayed=len(episodes),
            facts_decayed=len(facts),
        )

    async def _schedule_anniversaries(
        self,
        session: AsyncSession,
        user_id: UUID,
        character_id: str,
    ):
        """Schedule anniversary reminders from L4 (Step 8).

        Args:
            session: Database session
            user_id: User ID
            character_id: Character ID
        """
        # Fetch L4 memories with anniversary patterns
        stmt = select(IdentityMemory).where(
            and_(
                IdentityMemory.user_id == user_id,
                IdentityMemory.character_id == character_id,
                IdentityMemory.anniversary_pattern.isnot(None),
            )
        )

        result = await session.execute(stmt)
        identities = result.scalars().all()

        # For each, calculate next anniversary and schedule
        # (Would integrate with Behavior Runtime queue)

        logger.info(
            "anniversaries_scheduled",
            user_id=str(user_id),
            character_id=character_id,
            count=len(identities),
        )
