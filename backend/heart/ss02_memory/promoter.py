"""SS02 Memory — L3→L4 Promoter (INV-M-15)

Promotes L3 semantic facts to L4 identity memory when multiple conditions
are jointly satisfied. No single signal can trigger promotion alone.

Promotion predicate (§1):
    ELIGIBLE(f, t) ≡
        P1: f.is_active = TRUE
      ∧ P2: f.promoted_to_l4_at IS NULL
      ∧ P3: f.is_corrected = FALSE
      ∧ P4: f.do_not_recall = FALSE
      ∧ P5: f.mention_count ≥ K1
      ∧ P6: f.confidence_ewma ≥ K2
      ∧ P7: age_days(f, t) ≥ K3
      ∧ P8: cross_session_count(f) ≥ K4
      ∧ P9: contradiction_clear(f, t, K5)
      ∧ P10: f.predicate ∉ BLOCKLIST

Demotion predicate (§2):
    DEMOTE(im, t) ≡
        D1: contradicting_disclosures_in_window(im, 14d) ≥ 2
      ∧ D2: ¬im.user_initiated_forget
      ∧ D3: ¬contradictions_are_self_correcting(im)

Author: 心屿团队
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import structlog
import yaml
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings
from heart.ss02_memory.models import (
    FactNode,
    IdentityMemory,
    MemoryAuditLog,
)

logger = structlog.get_logger()

# ── Config loading ─────────────────────────────────────────────

_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "memory_promoter.yaml"
)


@dataclass(frozen=True)
class PromoterConfig:
    """Immutable promoter configuration loaded from YAML + settings."""

    K1_min_mentions: int = 3
    K2_min_confidence_ewma: float = 0.80
    K3_min_age_days: int = 1
    K4_min_cross_sessions: int = 2
    K5_contradiction_clear_days: int = 7
    batch_size: int = 200
    per_user_l4_cap: int = 50
    blocklist_exact: tuple[str, ...] = ()
    blocklist_glob: tuple[str, ...] = ()
    demotion_window_days: int = 14
    demotion_min_count: int = 2


def load_config() -> PromoterConfig:
    """Load promoter config from YAML file, falling back to settings defaults."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {}

    t = raw.get("thresholds", {})
    lim = raw.get("limits", {})
    b = raw.get("blocklist", {})
    d = raw.get("demotion", {})

    return PromoterConfig(
        K1_min_mentions=t.get("K1_min_mentions", settings.memory_promoter_min_mentions),
        K2_min_confidence_ewma=t.get(
            "K2_min_confidence_ewma", settings.memory_promoter_min_confidence
        ),
        K3_min_age_days=t.get("K3_min_age_days", settings.memory_promoter_min_age_days),
        K4_min_cross_sessions=t.get(
            "K4_min_cross_sessions", settings.memory_promoter_min_cross_sessions
        ),
        K5_contradiction_clear_days=t.get(
            "K5_contradiction_clear_days",
            settings.memory_promoter_contradiction_clear_days,
        ),
        batch_size=lim.get("batch_size", settings.memory_promoter_batch_size),
        per_user_l4_cap=lim.get("per_user_l4_cap", settings.memory_promoter_l4_cap),
        blocklist_exact=tuple(b.get("exact_predicates", [])),
        blocklist_glob=tuple(b.get("glob_patterns", [])),
        demotion_window_days=d.get(
            "contradiction_window_days",
            settings.memory_promoter_demotion_window_days,
        ),
        demotion_min_count=d.get("min_contradictions", settings.memory_promoter_demotion_min_count),
    )


# ── Result types ───────────────────────────────────────────────


@dataclass
class PromoterRunResult:
    """Result of a single promoter batch run."""

    promoted: list[UUID] = field(default_factory=list)
    demoted: list[UUID] = field(default_factory=list)
    skipped_blocklist: int = 0
    skipped_l4_cap: int = 0
    candidates_found: int = 0
    reconciliation_fixed: int = 0
    errors: list[str] = field(default_factory=list)


# ── Blocklist matcher ──────────────────────────────────────────


def _is_blocked(predicate: str, cfg: PromoterConfig) -> bool:
    """Check if predicate matches blocklist (exact or glob)."""
    if predicate in cfg.blocklist_exact:
        return True
    for pattern in cfg.blocklist_glob:
        if fnmatch.fnmatch(predicate, pattern):
            return True
    return False


# ── Category derivation ────────────────────────────────────────


_CATEGORY_MAP = {
    "name": "identity",
    "nickname": "identity",
    "age": "personal",
    "birthday": "personal",
    "occupation": "occupation",
    "hobby": "interest",
    "location_residence": "location",
    "location_origin": "location",
    "relation": "relationship",
    "color": "pet",
    "breed": "pet",
}


def _derive_category(predicate: str, subject: str) -> str:
    """Derive L4 category from predicate/subject."""
    if predicate in _CATEGORY_MAP:
        return _CATEGORY_MAP[predicate]
    if "pet" in subject.lower() or "pet" in predicate.lower():
        return "pet"
    if any(k in predicate for k in ("favorite", "love", "hate", "afraid")):
        return "preference"
    if any(k in predicate for k in ("trauma", "loss", "promise")):
        return "sacred"
    return "user_identity"


# ── Promoter ───────────────────────────────────────────────────


class Promoter:
    """L3→L4 Promoter — scans eligible L3 facts and promotes to L4.

    Strictly additive on L4, strictly read-only on L3 except for
    metadata fields (is_identity_level, promoted_to_l4_at, promotion_reason).

    INV-M-15: No single signal can trigger promotion.
    """

    def __init__(self, session: AsyncSession, config: PromoterConfig | None = None) -> None:
        self._session = session
        self._cfg = config or load_config()

    async def run_batch(self, user_ids: list[UUID] | None = None) -> PromoterRunResult:
        """Run one promotion batch + demotion pass + crash reconciliation.

        Args:
            user_ids: Optional filter to specific users. None = all users.

        Returns:
            PromoterRunResult with promoted/demoted IDs and stats.
        """
        result = PromoterRunResult()

        # Step 0: Crash-recovery reconciliation (§5.4)
        result.reconciliation_fixed = await self._reconcile_crash_recovery()

        # Step 1: Promotion pass
        candidates = await self._find_candidates(user_ids)
        result.candidates_found = len(candidates)

        for fact_row in candidates:
            try:
                promoted = await self._promote_one(fact_row)
                if promoted is not None:
                    result.promoted.append(promoted)
            except Exception as e:
                result.errors.append(f"promote {fact_row.id}: {e}")
                logger.error("promote_failed", fact_id=str(fact_row.id), error=str(e))

        # Step 2: Demotion pass
        demoted_ids = await self._run_demotion_pass()
        result.demoted = demoted_ids

        # Log summary
        logger.info(
            "promoter_batch_complete",
            candidates=result.candidates_found,
            promoted=len(result.promoted),
            demoted=len(result.demoted),
            reconciliation_fixed=result.reconciliation_fixed,
            errors=len(result.errors),
        )

        # Prometheus metrics (best-effort)
        try:
            from prometheus_client import Counter, Gauge

            promoted_counter = Counter(
                "heart_memory_promoter_promoted_total", "Facts promoted to L4"
            )
            demoted_counter = Counter("heart_memory_promoter_demoted_total", "L4 facts demoted")
            candidates_gauge = Gauge("heart_memory_promoter_candidates", "Candidates in last batch")
            candidates_gauge.set(result.candidates_found)
            for _ in result.promoted:
                promoted_counter.inc()
            for _ in result.demoted:
                demoted_counter.inc()
        except Exception:
            pass  # prometheus_client not available

        return result

    # ── Candidate query (§1.3) ─────────────────────────────────

    async def _find_candidates(self, user_ids: list[UUID] | None) -> list[FactNode]:
        """Query L3 facts eligible for promotion using the §1.3 SQL shape."""
        cfg = self._cfg
        now = datetime.now(timezone.utc)

        # Build the cross-session count subquery
        session_counts_sq = (
            select(
                MemoryAuditLog.entity_ref.label("fact_id_str"),
                func.count(func.distinct(MemoryAuditLog.session_id)).label("distinct_sessions"),
            )
            .where(
                MemoryAuditLog.tier == "L3",
                MemoryAuditLog.actor.in_(["extractor", "resolver"]),
                MemoryAuditLog.operation.in_(["create", "update"]),
                MemoryAuditLog.created_at >= now - timedelta(days=90),
            )
            .group_by(MemoryAuditLog.entity_ref)
            .subquery()
        )

        # Main candidate query
        stmt = (
            select(FactNode, session_counts_sq.c.distinct_sessions)
            .join(
                session_counts_sq,
                session_counts_sq.c.fact_id_str == text("fact_nodes.id::text"),
            )
            .where(
                FactNode.is_active.is_(True),
                FactNode.promoted_to_l4_at.is_(None),
                FactNode.is_corrected.is_(False),
                FactNode.do_not_recall.is_(False),
                FactNode.mention_count >= cfg.K1_min_mentions,
                FactNode.confidence_ewma >= cfg.K2_min_confidence_ewma,
                FactNode.created_at <= now - timedelta(days=cfg.K3_min_age_days),
                session_counts_sq.c.distinct_sessions >= cfg.K4_min_cross_sessions,
                # Contradiction clear (P9)
                (
                    FactNode.last_contradicted_at.is_(None)
                    | (
                        FactNode.last_contradicted_at
                        <= now - timedelta(days=cfg.K5_contradiction_clear_days)
                    )
                ),
            )
            .order_by(FactNode.user_id, FactNode.id)
            .limit(cfg.batch_size)
        )

        # Per-user filter
        if user_ids:
            stmt = stmt.where(FactNode.user_id.in_(user_ids))

        result = await self._session.execute(stmt)
        rows = result.all()

        # Filter blocklist in Python (avoids complex SQL LIKE ALL)
        candidates = []
        for fact, _sessions in rows:
            if _is_blocked(fact.predicate, cfg):
                logger.debug("skipped_blocklist", fact_id=str(fact.id), predicate=fact.predicate)
                continue
            candidates.append(fact)

        return candidates

    # ── Single promotion (§5.3) ────────────────────────────────

    async def _promote_one(self, fact: FactNode) -> UUID | None:
        """Promote a single L3 fact to L4 within a transaction.

        Steps:
        1. SELECT ... FOR UPDATE the L3 fact
        2. Check per-user L4 cap
        3. INSERT INTO identity_memories
        4. UPDATE fact_nodes SET promoted_to_l4_at, is_identity_level, promotion_reason
        5. INSERT INTO memory_audit_log (tier='L4', operation='promote')
        """
        cfg = self._cfg
        now = datetime.now(timezone.utc)

        # Re-lock and re-check (the batch query used SKIP LOCKED semantics
        # via the session_counts subquery; here we do a fresh FOR UPDATE)
        stmt = select(FactNode).where(FactNode.id == fact.id).with_for_update()
        result = await self._session.execute(stmt)
        locked_fact = result.scalar_one_or_none()

        if locked_fact is None:
            return None

        # Re-check P2 (might have been promoted by another worker)
        if locked_fact.promoted_to_l4_at is not None:
            logger.debug("already_promoted", fact_id=str(fact.id))
            return None

        # Per-user L4 cap (§4)
        l4_count_stmt = select(IdentityMemory).where(
            IdentityMemory.user_id == locked_fact.user_id,
            IdentityMemory.character_id == locked_fact.character_id,
            IdentityMemory.demoted_at.is_(None),
            IdentityMemory.user_initiated_forget.is_(False),
        )
        l4_result = await self._session.execute(l4_count_stmt)
        active_l4_count = len(l4_result.scalars().all())

        if active_l4_count >= cfg.per_user_l4_cap:
            logger.warning(
                "l4_cap_reached",
                user_id=str(locked_fact.user_id),
                fact_id=str(locked_fact.id),
                active_l4=active_l4_count,
                cap=cfg.per_user_l4_cap,
            )
            try:
                from prometheus_client import Counter

                Counter(
                    "heart_memory_promoter_skipped_l4_cap_total",
                    "Promotions skipped due to L4 cap",
                ).inc()
            except Exception:
                pass
            return None

        # Idempotency: check if L4 already exists for this fact
        existing_l4 = select(IdentityMemory).where(
            IdentityMemory.promoted_from_fact_id == locked_fact.id,
            IdentityMemory.demoted_at.is_(None),
        )
        existing_result = await self._session.execute(existing_l4)
        if existing_result.scalar_one_or_none() is not None:
            logger.info("l4_already_exists", fact_id=str(locked_fact.id))
            return None

        # Derive L4 fields
        category = _derive_category(locked_fact.predicate, locked_fact.subject)
        key = locked_fact.predicate
        value = locked_fact.object

        # Build promotion reason
        reason_parts = [
            f"mention_count={locked_fact.mention_count}",
            f"confidence_ewma={locked_fact.confidence_ewma:.2f}",
            f"age_days={_age_days(locked_fact.created_at, now):.1f}",
        ]
        promotion_reason = "promoter: " + ", ".join(reason_parts)

        # 3. INSERT L4
        l4_id = uuid4()
        identity = IdentityMemory(
            id=l4_id,
            user_id=locked_fact.user_id,
            character_id=locked_fact.character_id,
            category=category,
            key=key,
            value=value,
            disclosed_at=now,
            disclosure_context=locked_fact.raw_evidence,
            source_turn_ids=locked_fact.source_turn_ids or [],
            sacred_reason=promotion_reason,
            significance_score=max(locked_fact.confidence_ewma, 0.85),
            promotion_trigger="promoter_batch",
            promoted_from_fact_id=locked_fact.id,
            reconstruction_hints={
                "original_literal": locked_fact.literal_text,
                "confidence_ewma": locked_fact.confidence_ewma,
                "mention_count": locked_fact.mention_count,
            },
            created_at=now,
        )
        self._session.add(identity)

        # 4. UPDATE L3 metadata
        locked_fact.is_identity_level = True
        locked_fact.promoted_to_l4_at = now
        locked_fact.promotion_reason = promotion_reason

        # 5. INSERT audit log
        audit = MemoryAuditLog(
            id=uuid4(),
            user_id=locked_fact.user_id,
            session_id=uuid4(),  # promoter has no session context
            tier="L4",
            operation="promote",
            entity_type="identity",
            entity_ref=str(l4_id),
            attribute=locked_fact.predicate,
            old_value=None,
            new_value={
                "fact_id": str(locked_fact.id),
                "key": key,
                "value": value,
                "category": category,
                "promotion_reason": promotion_reason,
            },
            source_turns=locked_fact.source_turns or [],
            actor="promoter",
            reasoning=promotion_reason,
        )
        self._session.add(audit)

        await self._session.flush()

        logger.info(
            "fact_promoted",
            fact_id=str(locked_fact.id),
            l4_id=str(l4_id),
            predicate=key,
            value=value,
            user_id=str(locked_fact.user_id),
        )

        return l4_id

    # ── Demotion pass (§2) ─────────────────────────────────────

    async def _run_demotion_pass(self) -> list[UUID]:
        """Check all active L4 facts for demotion conditions.

        DEMOTE(im, t) ≡
            D1: contradicting_disclosures_in_window(im, 14d) ≥ 2
          ∧ D2: ¬im.user_initiated_forget
          ∧ D3: ¬contradictions_are_self_correcting(im)
        """
        cfg = self._cfg
        now = datetime.now(timezone.utc)
        demoted_ids: list[UUID] = []

        # Find active L4 facts
        stmt = select(IdentityMemory).where(
            IdentityMemory.demoted_at.is_(None),
            IdentityMemory.user_initiated_forget.is_(False),
        )
        result = await self._session.execute(stmt)
        active_l4s = result.scalars().all()

        for l4 in active_l4s:
            try:
                should_demote = await self._check_demotion(l4, cfg, now)
                if should_demote:
                    demoted_id = await self._demote_one(l4, now)
                    if demoted_id is not None:
                        demoted_ids.append(demoted_id)
            except Exception as e:
                logger.error("demotion_check_failed", l4_id=str(l4.id), error=str(e))

        return demoted_ids

    async def _check_demotion(self, l4: IdentityMemory, cfg: PromoterConfig, now: datetime) -> bool:
        """Check if an L4 fact should be demoted.

        Counts contradicting disclosures in the audit log within the demotion window.
        A disclosure contradicts L4 iff:
        - audit.operation='create' AND new_value has same predicate/subject but different object
        - OR audit.operation='update' AND new_value.is_corrected='true'
        Excludes self-corrections (reasoning='self_correction').
        """
        window_start = now - timedelta(days=cfg.demotion_window_days)

        # Find the promoted_from_fact_id to get the original L3
        if l4.promoted_from_fact_id is None:
            return False

        fact_stmt = select(FactNode).where(FactNode.id == l4.promoted_from_fact_id)
        fact_result = await self._session.execute(fact_stmt)
        source_fact = fact_result.scalar_one_or_none()

        if source_fact is None:
            return False

        # Count contradicting audit entries
        # A contradiction: same predicate+subject, different object, within window
        stmt = select(MemoryAuditLog).where(
            MemoryAuditLog.user_id == l4.user_id,
            MemoryAuditLog.tier == "L3",
            MemoryAuditLog.created_at >= window_start,
            MemoryAuditLog.operation.in_(["create", "update"]),
            # Exclude self-corrections
            (MemoryAuditLog.reasoning.is_(None) | (MemoryAuditLog.reasoning != "self_correction")),
        )
        result = await self._session.execute(stmt)
        audit_rows = result.scalars().all()

        contradiction_count = 0
        for audit in audit_rows:
            if audit.operation == "create" and audit.new_value:
                if (
                    audit.new_value.get("predicate") == source_fact.predicate
                    and audit.new_value.get("subject") == source_fact.subject
                    and audit.new_value.get("object") != source_fact.object
                ):
                    contradiction_count += 1
            elif audit.operation == "update" and audit.new_value:
                if audit.new_value.get("is_corrected") in (True, "true"):
                    # Check if this is for the same fact
                    if audit.entity_ref == str(l4.promoted_from_fact_id):
                        contradiction_count += 1

        return contradiction_count >= cfg.demotion_min_count

    async def _demote_one(self, l4: IdentityMemory, now: datetime) -> UUID | None:
        """Demote a single L4 fact.

        1. Set l4.demoted_at, l4.demotion_reason
        2. Clear L3 promoted_to_l4_at, set was_l4=True, previously_l4_id
        3. Write audit log with operation='demote'
        """
        demotion_reason = f"contradiction_threshold_met_at_{now.isoformat()}"

        # 1. Shadow L4 (not deleted, just hidden)
        l4.demoted_at = now
        l4.demotion_reason = demotion_reason

        # 2. Update L3 source fact
        if l4.promoted_from_fact_id is not None:
            fact_stmt = select(FactNode).where(FactNode.id == l4.promoted_from_fact_id)
            fact_result = await self._session.execute(fact_stmt)
            source_fact = fact_result.scalar_one_or_none()

            if source_fact is not None:
                source_fact.was_l4 = True
                source_fact.previously_l4_id = l4.id
                source_fact.promoted_to_l4_at = None  # Clear so it can re-enter candidate pool

        # 3. Audit log
        audit = MemoryAuditLog(
            id=uuid4(),
            user_id=l4.user_id,
            session_id=uuid4(),
            tier="L4",
            operation="demote",
            entity_type="identity",
            entity_ref=str(l4.id),
            attribute=l4.key,
            old_value={
                "key": l4.key,
                "value": l4.value,
                "category": l4.category,
            },
            new_value={
                "demoted_at": now.isoformat(),
                "demotion_reason": demotion_reason,
            },
            source_turns=[],
            actor="promoter",
            reasoning=demotion_reason,
        )
        self._session.add(audit)

        await self._session.flush()

        logger.info(
            "l4_demoted",
            l4_id=str(l4.id),
            key=l4.key,
            user_id=str(l4.user_id),
            reason=demotion_reason,
        )

        return l4.id

    # ── Crash recovery (§5.4) ──────────────────────────────────

    async def _reconcile_crash_recovery(self) -> int:
        """Find L4 rows whose L3 source isn't marked as promoted.

        This closes the gap if the promoter crashed between INSERT L4 and
        UPDATE L3 (§5.3 steps 2–3).
        """
        stmt = (
            select(IdentityMemory)
            .join(FactNode, FactNode.id == IdentityMemory.promoted_from_fact_id)
            .where(
                IdentityMemory.demoted_at.is_(None),
                FactNode.promoted_to_l4_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        orphans = result.scalars().all()

        fixed = 0
        for im in orphans:
            if im.promoted_from_fact_id is not None:
                fact_stmt = select(FactNode).where(FactNode.id == im.promoted_from_fact_id)
                fact_result = await self._session.execute(fact_stmt)
                fact = fact_result.scalar_one_or_none()
                if fact is not None:
                    fact.promoted_to_l4_at = im.created_at
                    fact.is_identity_level = True
                    fixed += 1
                    logger.info(
                        "reconciled_l3_marker",
                        fact_id=str(fact.id),
                        l4_id=str(im.id),
                    )

        if fixed > 0:
            await self._session.flush()

        return fixed


# ── Utility ────────────────────────────────────────────────────


def _age_days(created_at: datetime, now: datetime) -> float:
    """Compute age in days from created_at to now."""
    delta = now - created_at
    return delta.total_seconds() / 86400
