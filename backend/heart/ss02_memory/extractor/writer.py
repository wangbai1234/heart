"""
SS02 Memory LLM Extractor — Writer

Transactional writer for Resolver decisions. All decisions for one envelope
are committed in a single DB transaction.

Writes:
- L2 episodic record (audit log tier=L2) for every decision including REJECT
- L3 FactNode changes for CREATE/SUPERSEDE/REINFORCE/SOFT_DELETE
- memory_audit_log rows for every state change with old_value/new_value
- Updates extraction_queue.status = "done"
- On exception: tx rollback, mark queue status="failed", retry_count++
- Failed envelopes go to memory_extraction_dlq for HUMAN inspection

INV-M-NEW-A: every L3 write cites source_turns
INV-M-NEW-B: ≤1 active row per (user_id, entity_type, entity_ref, attribute)
INV-M-NEW-C: negation never physically deletes

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import (
    FactNode,
    MemoryAuditLog,
    MemoryExtractionDLQ,
    MemoryExtractionQueue,
)

from .resolver import DecisionType, ResolverDecision
from .types import ExtractionCandidate, ExtractionEnvelope

logger = structlog.get_logger()


class WriterError(Exception):
    """Raised when Writer encounters an unrecoverable error."""


class Writer:
    """Transactional writer for Resolver decisions.

    All decisions for one envelope are committed in one DB transaction.
    On exception: rollback, mark queue status="failed", enqueue to DLQ.
    """

    def __init__(
        self,
        session: AsyncSession,
        user_id: UUID,
        session_id: UUID,
        embedding_service=None,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._session_id = session_id
        self._embedding = embedding_service

    async def _embed_literal(self, literal_text: str):
        """Embed an L3 fact's literal text, or None when unavailable.

        Best-effort: None if no embedding service (no API key) or on failure,
        leaving semantic_vector NULL (pre-semantic-recall behaviour).
        """
        if self._embedding is None:
            return None
        try:
            return await self._embedding.embed_query(literal_text)
        except Exception as e:
            logger.warning("l3_embedding_failed", error=str(e))
            return None

    async def commit(
        self,
        decisions: list[ResolverDecision],
        envelope: ExtractionEnvelope,
    ) -> None:
        """Commit all decisions in a single transaction.

        Args:
            decisions: List of ResolverDecision from the Resolver.
            envelope: The original ExtractionEnvelope.

        Raises:
            WriterError: If the commit fails after rollback.
        """
        run_id = envelope.extractor_run_id

        # ── Idempotency check ──
        if await self._already_processed(run_id):
            logger.warning(
                "writer_idempotent_skip",
                extractor_run_id=str(run_id),
            )
            return

        try:
            # ── Write L2 + L3 + audit for each decision ──
            for decision in decisions:
                self._write_l2_episodic_audit(decision, envelope)
                await self._write_l3_and_audit(decision, envelope)

            # ── Mark queue done ──
            await self._mark_queue_done(run_id)

            await self._session.commit()

            logger.info(
                "writer_commit_success",
                extractor_run_id=str(run_id),
                decisions_count=len(decisions),
            )

        except Exception as e:
            logger.error(
                "writer_commit_failed",
                extractor_run_id=str(run_id),
                error=str(e),
            )
            await self._session.rollback()

            # Mark queue failed + enqueue to DLQ
            await self._mark_queue_failed(run_id, str(e))
            await self._enqueue_dlq(envelope, str(e))

            raise WriterError(f"Writer commit failed for {run_id}: {e}") from e

    # ── Idempotency ──────────────────────────────────────────────

    async def _already_processed(self, run_id: UUID) -> bool:
        """Check if this extractor_run_id was already committed successfully."""
        stmt = (
            select(MemoryAuditLog.id)
            .where(
                MemoryAuditLog.extractor_run_id == run_id,
                MemoryAuditLog.actor == "resolver",
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ── L2 Episodic Audit ────────────────────────────────────────

    def _write_l2_episodic_audit(
        self,
        decision: ResolverDecision,
        envelope: ExtractionEnvelope,
    ) -> None:
        """Write L2-tier audit log entry for every decision (including REJECT).

        This records the raw candidate + reasoning for auditability.
        """
        cand = decision.candidate
        audit = MemoryAuditLog(
            id=uuid4(),
            user_id=self._user_id,
            session_id=self._session_id,
            tier="L2",
            operation=decision.decision.value,
            entity_type=cand.entity_type.value,
            entity_ref=cand.entity_ref,
            attribute=cand.attribute.value,
            old_value=None,
            new_value={
                "value": cand.value,
                "confidence": cand.confidence,
                "kind": cand.kind.value,
                "reasoning": cand.reasoning,
                "decision_reason": decision.reason,
            },
            source_turns=cand.source_turns,
            extractor_run_id=envelope.extractor_run_id,
            actor="resolver",
            reasoning=cand.reasoning,
        )
        self._session.add(audit)

    # ── L3 Writes + Audit ────────────────────────────────────────

    async def _write_l3_and_audit(
        self,
        decision: ResolverDecision,
        envelope: ExtractionEnvelope,
    ) -> None:
        """Write L3 FactNode changes and L3-tier audit log entries.

        Only writes for CREATE/SUPERSEDE/REINFORCE/SOFT_DELETE.
        REJECT and CONFLICT_DEFER have no L3 side-effects.
        """
        handler = {
            DecisionType.CREATE: self._handle_create,
            DecisionType.REINFORCE: self._handle_reinforce,
            DecisionType.SUPERSEDE: self._handle_supersede,
            DecisionType.SOFT_DELETE: self._handle_soft_delete,
        }.get(decision.decision)

        if handler is not None:
            await handler(decision, envelope)

    async def _handle_create(
        self,
        decision: ResolverDecision,
        envelope: ExtractionEnvelope,
    ) -> None:
        """CREATE: insert new L3 FactNode + audit."""
        cand = decision.candidate
        now = datetime.now(timezone.utc)
        fact_id = uuid4()

        subject = cand.entity_ref or cand.entity_type.value
        predicate = cand.attribute.value
        literal_text = f"{subject}: {predicate} = {cand.value}"
        semantic_vector = await self._embed_literal(literal_text)

        fact = FactNode(
            id=fact_id,
            user_id=self._user_id,
            character_id="default",
            predicate=predicate,
            subject=subject,
            object=cand.value,
            literal_text=literal_text,
            raw_evidence=cand.reasoning,
            source_episode_ids=[],
            source_turn_ids=[],
            source_turns=cand.source_turns,
            confidence=cand.confidence,
            emotional_charge=0.0,
            importance=0.5,
            is_identity_level=False,
            confirmation_count=0,
            contradiction_count=0,
            contradicting_fact_ids=[],
            is_corrected=False,
            do_not_recall=False,
            last_confirmed_at=now,
            state="vivid",
            mention_count=1,
            confidence_ewma=cand.confidence,
            last_extractor_run_id=envelope.extractor_run_id,
            is_active=True,
            semantic_vector=semantic_vector,
        )
        self._session.add(fact)

        audit = self._make_l3_audit(
            decision=decision,
            envelope=envelope,
            operation="create",
            old_value=None,
            new_value=self._fact_snapshot(fact),
        )
        self._session.add(audit)

    async def _handle_reinforce(
        self,
        decision: ResolverDecision,
        envelope: ExtractionEnvelope,
    ) -> None:
        """REINFORCE: update mention_count, confidence_ewma, last_seen + audit."""
        fact = decision.matched_fact
        assert fact is not None

        old_snapshot = self._fact_snapshot(fact)

        fact.mention_count = (fact.mention_count or 1) + 1
        fact.confidence_ewma = decision.new_confidence_ewma  # type: ignore[arg-type]
        fact.last_extractor_run_id = envelope.extractor_run_id
        fact.last_confirmed_at = datetime.now(timezone.utc)
        fact.confirmation_count = (fact.confirmation_count or 0) + 1
        fact.updated_at = datetime.now(timezone.utc)

        # Merge source_turns (INV-M-NEW-A)
        existing = set(fact.source_turns or [])
        existing.update(decision.candidate.source_turns)
        fact.source_turns = sorted(existing)

        audit = self._make_l3_audit(
            decision=decision,
            envelope=envelope,
            operation="update",
            old_value=old_snapshot,
            new_value=self._fact_snapshot(fact),
        )
        self._session.add(audit)

    async def _handle_supersede(
        self,
        decision: ResolverDecision,
        envelope: ExtractionEnvelope,
    ) -> None:
        """SUPERSEDE: mark old is_active=False, insert new fact + audit."""
        old_fact = decision.matched_fact
        assert old_fact is not None
        cand = decision.candidate
        now = datetime.now(timezone.utc)

        # ── Mark old fact inactive ──
        old_snapshot = self._fact_snapshot(old_fact)
        old_fact.is_active = False
        old_fact.updated_at = now

        # ── Insert new fact ──
        new_fact_id = uuid4()
        subject = cand.entity_ref or cand.entity_type.value
        predicate = cand.attribute.value
        literal_text = f"{subject}: {predicate} = {cand.value}"
        semantic_vector = await self._embed_literal(literal_text)

        new_fact = FactNode(
            id=new_fact_id,
            user_id=self._user_id,
            character_id="default",
            predicate=predicate,
            subject=subject,
            object=cand.value,
            literal_text=literal_text,
            raw_evidence=cand.reasoning,
            source_episode_ids=[],
            source_turn_ids=[],
            source_turns=cand.source_turns,
            confidence=cand.confidence,
            emotional_charge=0.0,
            importance=0.5,
            is_identity_level=False,
            confirmation_count=0,
            contradiction_count=0,
            contradicting_fact_ids=[old_fact.id],
            is_corrected=False,
            do_not_recall=False,
            last_confirmed_at=now,
            state="vivid",
            mention_count=1,
            confidence_ewma=cand.confidence,
            last_extractor_run_id=envelope.extractor_run_id,
            is_active=True,
            semantic_vector=semantic_vector,
        )
        self._session.add(new_fact)

        # Link old → new
        old_fact.superseded_by_id = new_fact_id

        # ── Audit for old fact (superseded) ──
        audit_old = self._make_l3_audit(
            decision=decision,
            envelope=envelope,
            operation="supersede",
            old_value=old_snapshot,
            new_value={
                **self._fact_snapshot(new_fact),
                "superseded_by": str(new_fact_id),
            },
        )
        self._session.add(audit_old)

    async def _handle_soft_delete(
        self,
        decision: ResolverDecision,
        envelope: ExtractionEnvelope,
    ) -> None:
        """SOFT_DELETE: mark do_not_recall=True + audit (INV-M-NEW-C: never physical delete)."""
        fact = decision.matched_fact
        assert fact is not None

        old_snapshot = self._fact_snapshot(fact)
        fact.do_not_recall = True
        fact.updated_at = datetime.now(timezone.utc)

        audit = self._make_l3_audit(
            decision=decision,
            envelope=envelope,
            operation="soft_delete",
            old_value=old_snapshot,
            new_value=self._fact_snapshot(fact),
        )
        self._session.add(audit)

    # ── Helpers ──────────────────────────────────────────────────

    def _make_l3_audit(
        self,
        decision: ResolverDecision,
        envelope: ExtractionEnvelope,
        operation: str,
        old_value: Optional[dict],
        new_value: Optional[dict],
    ) -> MemoryAuditLog:
        """Create an L3-tier MemoryAuditLog entry."""
        cand = decision.candidate
        return MemoryAuditLog(
            id=uuid4(),
            user_id=self._user_id,
            session_id=self._session_id,
            tier="L3",
            operation=operation,
            entity_type=cand.entity_type.value,
            entity_ref=cand.entity_ref,
            attribute=cand.attribute.value,
            old_value=old_value,
            new_value=new_value,
            source_turns=cand.source_turns,
            extractor_run_id=envelope.extractor_run_id,
            actor="resolver",
            reasoning=cand.reasoning,
        )

    @staticmethod
    def _fact_snapshot(fact: FactNode) -> dict:
        """Create a JSON-serialisable snapshot of a FactNode."""
        return {
            "id": str(fact.id),
            "subject": fact.subject,
            "predicate": fact.predicate,
            "object": fact.object,
            "confidence": fact.confidence,
            "confidence_ewma": fact.confidence_ewma,
            "mention_count": fact.mention_count,
            "is_active": fact.is_active,
            "do_not_recall": fact.do_not_recall,
            "source_turns": fact.source_turns,
        }

    # ── Queue status management ──────────────────────────────────

    async def _mark_queue_done(self, run_id: UUID) -> None:
        """Mark extraction queue items as done for this run."""
        now = datetime.now(timezone.utc)
        stmt = select(MemoryExtractionQueue).where(MemoryExtractionQueue.extractor_run_id == run_id)
        result = await self._session.execute(stmt)
        for row in result.scalars().all():
            row.status = "done"
            row.finished_at = now

    async def _mark_queue_failed(self, run_id: UUID, error: str) -> None:
        """Mark extraction queue items as failed, increment retry_count."""
        try:
            now = datetime.now(timezone.utc)
            stmt = select(MemoryExtractionQueue).where(
                MemoryExtractionQueue.extractor_run_id == run_id
            )
            result = await self._session.execute(stmt)
            for row in result.scalars().all():
                row.status = "failed"
                row.finished_at = now
                row.error_message = error[:1000]
                row.retry_count = (row.retry_count or 0) + 1
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.error("writer_mark_queue_failed_error", run_id=str(run_id))

    async def _enqueue_dlq(self, envelope: ExtractionEnvelope, error: str) -> None:
        """Push failed envelope to DLQ for HUMAN inspection."""
        try:
            dlq_entry = MemoryExtractionDLQ(
                id=uuid4(),
                extractor_run_id=envelope.extractor_run_id,
                user_id=self._user_id,
                session_id=self._session_id,
                envelope_json=envelope.model_dump(mode="json"),
                error_message=error[:2000],
                candidates_count=len(envelope.candidates),
                model=envelope.model,
                prompt_version=envelope.prompt_version,
            )
            self._session.add(dlq_entry)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.error(
                "writer_dlq_enqueue_failed",
                run_id=str(envelope.extractor_run_id),
            )
