"""
SS02 Memory LLM Extractor — Resolver

For each candidate in an ExtractionEnvelope, determines the write action
against the current L3 state. Implements the decision table from
docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md §3.4.

Decision table:
  - kind in {rhetoric, question, hypothetical} → REJECT
  - kind == negation + match exists → SOFT_DELETE
  - kind == disclosure:
      no match → CREATE
      match + same value → REINFORCE
      match + different value + confidence >= 0.7 → SUPERSEDE
      match + different value + confidence < 0.7 → CONFLICT_DEFER

INV-M-NEW-A: every L3 write cites source_turns
INV-M-NEW-B: ≤1 active row per (user_id, entity_type, entity_ref, attribute)
INV-M-NEW-C: negation never physically deletes

Author: 心屿团队
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import FactNode

from .types import ExtractionCandidate, ExtractionEnvelope

logger = structlog.get_logger()

# EWMA smoothing factor
_EWMA_ALPHA = 0.7
_EWMA_BETA = 0.3


class DecisionType(str, enum.Enum):
    """Resolver decision types."""

    CREATE = "create"
    REINFORCE = "reinforce"
    SUPERSEDE = "supersede"
    SOFT_DELETE = "soft_delete"
    REJECT = "reject"
    CONFLICT_DEFER = "conflict_defer"


@dataclass
class ResolverDecision:
    """Outcome of resolving a single ExtractionCandidate against L3 state."""

    decision: DecisionType
    candidate: ExtractionCandidate
    matched_fact: Optional[FactNode] = None
    new_confidence_ewma: Optional[float] = None
    reason: str = ""


class Resolver:
    """Resolves ExtractionEnvelope candidates against current L3 FactNode state.

    For each candidate, looks up matching active L3 row by
    (user_id, entity_type, entity_ref, attribute) and applies the decision table.
    """

    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self._session = session
        self._user_id = user_id

    async def resolve(self, envelope: ExtractionEnvelope) -> list[ResolverDecision]:
        """Resolve all candidates in the envelope against L3 state.

        Args:
            envelope: The extraction envelope from the LLM.

        Returns:
            List of ResolverDecision, one per candidate.
        """
        decisions: list[ResolverDecision] = []
        for candidate in envelope.candidates:
            decision = await self._resolve_one(candidate)
            decisions.append(decision)

        logger.info(
            "resolver_decisions_complete",
            extractor_run_id=str(envelope.extractor_run_id),
            total=len(decisions),
            create=sum(1 for d in decisions if d.decision == DecisionType.CREATE),
            reinforce=sum(1 for d in decisions if d.decision == DecisionType.REINFORCE),
            supersede=sum(1 for d in decisions if d.decision == DecisionType.SUPERSEDE),
            soft_delete=sum(1 for d in decisions if d.decision == DecisionType.SOFT_DELETE),
            reject=sum(1 for d in decisions if d.decision == DecisionType.REJECT),
            conflict_defer=sum(1 for d in decisions if d.decision == DecisionType.CONFLICT_DEFER),
        )
        return decisions

    async def _resolve_one(self, candidate: ExtractionCandidate) -> ResolverDecision:
        """Resolve a single candidate against L3 state."""
        # ── Non-disclosure kinds → REJECT ──
        if candidate.kind in {
            "rhetoric",
            "question",
            "hypothetical",
        }:
            return ResolverDecision(
                decision=DecisionType.REJECT,
                candidate=candidate,
                reason=f"kind={candidate.kind.value}, not a real disclosure",
            )

        # ── Look up matching active L3 row ──
        matched = await self._find_matching_l3(candidate)

        # ── Negation ──
        if candidate.kind == "negation":
            if matched is not None:
                return ResolverDecision(
                    decision=DecisionType.SOFT_DELETE,
                    candidate=candidate,
                    matched_fact=matched,
                    reason="negation of existing fact, soft-deleting",
                )
            return ResolverDecision(
                decision=DecisionType.REJECT,
                candidate=candidate,
                reason="negation but no matching active L3 fact to delete",
            )

        # ── Disclosure ──
        if matched is None:
            return ResolverDecision(
                decision=DecisionType.CREATE,
                candidate=candidate,
                reason="no matching L3 fact, creating new",
            )

        # Match exists — compare values
        if _values_match(candidate.value, matched.object):
            new_ewma = _compute_ewma(matched.confidence_ewma, candidate.confidence)
            return ResolverDecision(
                decision=DecisionType.REINFORCE,
                candidate=candidate,
                matched_fact=matched,
                new_confidence_ewma=new_ewma,
                reason="matching L3 fact with same value, reinforcing",
            )

        # Different value
        if candidate.confidence >= 0.7:
            return ResolverDecision(
                decision=DecisionType.SUPERSEDE,
                candidate=candidate,
                matched_fact=matched,
                reason="matching L3 fact with different value, high confidence → supersede",
            )

        return ResolverDecision(
            decision=DecisionType.CONFLICT_DEFER,
            candidate=candidate,
            matched_fact=matched,
            reason=(
                f"matching L3 fact with different value, "
                f"confidence {candidate.confidence:.2f} < 0.7 → deferring"
            ),
        )

    async def _find_matching_l3(self, candidate: ExtractionCandidate) -> Optional[FactNode]:
        """Find matching active L3 FactNode by (user_id, subject, predicate).

        subject = entity_ref if set, else entity_type
        predicate = attribute
        Only matches is_active=True and do_not_recall=False rows.
        """
        subject = candidate.entity_ref or candidate.entity_type.value
        predicate = candidate.attribute.value

        stmt = (
            select(FactNode)
            .where(
                FactNode.user_id == self._user_id,
                FactNode.subject == subject,
                FactNode.predicate == predicate,
                FactNode.is_active.is_(True),
                FactNode.do_not_recall.is_(False),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


def _values_match(candidate_value: str, l3_object: str) -> bool:
    """Check if candidate value matches L3 object (case-insensitive, trimmed)."""
    return candidate_value.strip().lower() == l3_object.strip().lower()


def _compute_ewma(old_ewma: float, new_confidence: float) -> float:
    """Compute updated confidence EWMA.

    ewma_new = 0.7 * ewma_old + 0.3 * candidate.confidence
    """
    return _EWMA_ALPHA * old_ewma + _EWMA_BETA * new_confidence
