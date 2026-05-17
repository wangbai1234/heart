"""
Decay Engine - SS02 §10.4.1

Implements importance decay algorithm with emotional and Hebbian modulation.

Formula:
    I(t) = max(I_floor, I_0 × T(t) × E × R)

Where:
    T(t) = exp(-Δt_days / τ)      # Exponential decay
    E = 1 + |v| × 0.5 + a × 0.3   # Emotional multiplier [1, 1.8]
    R = min(1 + ln(1+r) × 0.2, 2.0)  # Recall multiplier (capped)
    I_floor = max(|v|×0.1, min(0.20, ln(1+r)×0.03))  # Recall-aware floor

Constraints:
- L4 never decays (importance immutable)
- L2 τ = 14 days, L3 τ = 60 days
- Importance capped at 0.95
- State updated based on new importance

Bug fixes applied:
1. Continuous time (no integer day truncation)
2. Bounded emotional multiplier (clamps inputs)
3. Recall multiplier saturation (cap at 2.0)
4. Recall-aware floor (neutral facts don't decay to archive)
5. Reinforcement bumps initial_importance (not current score)
6. NULL handling for optional fields
7. Clock skew protection (elapsed ≥ 0)

Author: 心屿团队
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional, Protocol, Union
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import EpisodicMemory, FactNode, IdentityMemory

logger = structlog.get_logger()


# ============================================================
# Configuration
# ============================================================

# Time constants (days)
TAU_L2 = 14.0
TAU_L3 = 60.0

# Importance bounds
MIN_IMPORTANCE = 0.0
MAX_IMPORTANCE = 0.95  # Reserve [0.95, 1.0] for L4 promotion threshold

# Emotional multiplier coefficients
VALENCE_WEIGHT = 0.5
AROUSAL_WEIGHT = 0.3

# Recall multiplier coefficients
RECALL_LOG_WEIGHT = 0.2
MAX_RECALL_MULTIPLIER = 2.0  # Cap at ~150 recalls

# Floor coefficients
EMOTIONAL_FLOOR_WEIGHT = 0.1
RECALL_FLOOR_LOG_WEIGHT = 0.03
MAX_RECALL_FLOOR = 0.20

# State thresholds
STATE_THRESHOLDS = {
    "vivid": 0.7,
    "fading": 0.5,
    "faint": 0.3,
    "dormant": 0.1,
    "archived": 0.0,
}


# ============================================================
# Memory Protocol (Duck Typing)
# ============================================================


class DecayableMemory(Protocol):
    """Protocol for memories that can decay (L2/L3).

    Both EpisodicMemory and FactNode implement this interface.
    """

    id: UUID
    user_id: UUID
    character_id: str

    importance_score: float
    initial_importance: float
    recall_count: int
    state: str

    updated_at: datetime
    last_recalled_at: Optional[datetime]

    # L2 has emotional_peak (dict), L3 has emotional_charge (float)
    # Handled in _extract_emotional_values()


@dataclass
class EmotionalValues:
    """Extracted emotional values from memory."""
    valence: float  # [-1, 1]
    arousal: float  # [0, 1]


# ============================================================
# Decay Engine
# ============================================================


class DecayEngine:
    """
    Decay Engine for L2/L3 memories.

    Provides:
    - apply_decay_lazy: In-memory decay calculation (no DB write)
    - apply_decay_batch: Batch decay for all user memories (with DB write)
    """

    def __init__(self):
        """Initialize decay engine."""
        logger.info("decay_engine_initialized")

    def apply_decay_lazy(
        self,
        memory: Union[EpisodicMemory, FactNode],
        now: Optional[datetime] = None,
    ) -> Union[EpisodicMemory, FactNode]:
        """
        Apply decay to a single memory (lazy, in-memory only).

        This is called at retrieval time to compute current importance
        without writing to DB. Batch decay writes back nightly.

        Args:
            memory: L2 or L3 memory to decay
            now: Current timestamp (defaults to UTC now)

        Returns:
            Memory with updated importance_score and state

        Raises:
            ValueError: If memory has invalid data
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # L4 never decays (should not reach here, but guard anyway)
        if isinstance(memory, IdentityMemory):
            logger.warning("decay_skipped_l4", memory_id=str(memory.id))
            return memory

        # Extract layer
        layer = self._get_layer(memory)

        # L4 facts promoted but not yet migrated have layer="L4" marker
        # (not applicable in current schema, but future-proof)
        if layer == "L4":
            logger.info("decay_skipped_l4_promoted", memory_id=str(memory.id))
            return memory

        # Extract and validate emotional values
        emotional = self._extract_emotional_values(memory)
        valence = self._clamp(emotional.valence, -1.0, 1.0)
        arousal = self._clamp(emotional.arousal, 0.0, 1.0)

        # Extract and validate recall count
        recalls = max(0, memory.recall_count or 0)

        # Compute elapsed time (continuous, not integer days)
        elapsed_days = self._compute_elapsed_days(memory.updated_at, now)

        # Skip if too recent (< 1 day)
        if elapsed_days < 1.0:
            logger.debug(
                "decay_skipped_too_recent",
                memory_id=str(memory.id),
                elapsed_days=elapsed_days,
            )
            return memory

        # Time decay factor
        tau = TAU_L2 if layer == "L2" else TAU_L3
        time_factor = math.exp(-elapsed_days / tau)

        # Emotional multiplier E ∈ [1, 1.8]
        valence_abs = abs(valence)
        emotional_factor = 1.0 + valence_abs * VALENCE_WEIGHT + arousal * AROUSAL_WEIGHT

        # Recall multiplier R (Hebbian, capped at 2.0)
        recall_factor = min(
            1.0 + math.log(1.0 + recalls) * RECALL_LOG_WEIGHT,
            MAX_RECALL_MULTIPLIER,
        )

        # Compute raw importance
        raw_importance = (
            memory.initial_importance * time_factor * emotional_factor * recall_factor
        )

        # Compute floor (recall-aware)
        emotional_floor = valence_abs * EMOTIONAL_FLOOR_WEIGHT
        recall_floor = min(
            MAX_RECALL_FLOOR,
            math.log(1.0 + recalls) * RECALL_FLOOR_LOG_WEIGHT,
        )
        floor = max(emotional_floor, recall_floor)

        # Apply floor and cap
        new_importance = max(floor, raw_importance)
        new_importance = self._clamp(new_importance, MIN_IMPORTANCE, MAX_IMPORTANCE)

        # Update memory
        memory.importance_score = new_importance
        memory.state = self._compute_state(new_importance)

        logger.debug(
            "decay_applied_lazy",
            memory_id=str(memory.id),
            layer=layer,
            elapsed_days=round(elapsed_days, 2),
            time_factor=round(time_factor, 3),
            emotional_factor=round(emotional_factor, 3),
            recall_factor=round(recall_factor, 3),
            old_importance=round(memory.initial_importance, 3),
            new_importance=round(new_importance, 3),
            state=memory.state,
        )

        return memory

    async def apply_decay_batch(
        self,
        session: AsyncSession,
        user_id: UUID,
        character_id: str,
        now: Optional[datetime] = None,
    ) -> dict:
        """
        Apply decay to all L2/L3 memories for a user (batch, with DB write).

        This is called nightly by the consolidation job to update importance
        scores in the database.

        Args:
            session: Database session
            user_id: User UUID
            character_id: Character ID
            now: Current timestamp (defaults to UTC now)

        Returns:
            Statistics dict with counts
        """
        if now is None:
            now = datetime.now(timezone.utc)

        stats = {
            "l2_processed": 0,
            "l3_processed": 0,
            "l2_archived": 0,
            "l3_archived": 0,
            "l2_errors": 0,
            "l3_errors": 0,
        }

        # Process L2 (EpisodicMemory)
        l2_stmt = select(EpisodicMemory).where(
            EpisodicMemory.user_id == user_id,
            EpisodicMemory.character_id == character_id,
            EpisodicMemory.do_not_recall == False,
        )

        result = await session.execute(l2_stmt)
        l2_memories = result.scalars().all()

        for memory in l2_memories:
            try:
                self.apply_decay_lazy(memory, now)
                stats["l2_processed"] += 1

                if memory.state == "archived":
                    stats["l2_archived"] += 1
                    memory.archived_at = now
            except Exception as e:
                logger.error(
                    "decay_batch_error_l2",
                    memory_id=str(memory.id),
                    error=str(e),
                    exc_info=True,
                )
                stats["l2_errors"] += 1

        # Process L3 (FactNode)
        l3_stmt = select(FactNode).where(
            FactNode.user_id == user_id,
            FactNode.character_id == character_id,
            FactNode.do_not_recall == False,
            FactNode.promoted_to_l4_at.is_(None),  # Skip L4-promoted facts
        )

        result = await session.execute(l3_stmt)
        l3_facts = result.scalars().all()

        for fact in l3_facts:
            try:
                # L3 facts don't have "archived" state, but we track if they hit floor
                old_state = fact.state
                self.apply_decay_lazy(fact, now)
                stats["l3_processed"] += 1

                # Count as "archived" if importance hit floor and state degraded
                if fact.importance < 0.15 and old_state != "dormant":
                    stats["l3_archived"] += 1
            except Exception as e:
                logger.error(
                    "decay_batch_error_l3",
                    fact_id=str(fact.id),
                    error=str(e),
                    exc_info=True,
                )
                stats["l3_errors"] += 1

        # Commit changes
        await session.commit()

        logger.info(
            "decay_batch_completed",
            user_id=str(user_id),
            character_id=character_id,
            stats=stats,
        )

        return stats

    # ============================================================
    # Helpers
    # ============================================================

    def _get_layer(self, memory: Union[EpisodicMemory, FactNode]) -> Literal["L2", "L3"]:
        """Determine memory layer from type."""
        if isinstance(memory, EpisodicMemory):
            return "L2"
        elif isinstance(memory, FactNode):
            return "L3"
        else:
            raise ValueError(f"Unknown memory type: {type(memory)}")

    def _extract_emotional_values(
        self, memory: Union[EpisodicMemory, FactNode]
    ) -> EmotionalValues:
        """
        Extract emotional values from memory.

        L2 (EpisodicMemory) has emotional_peak: {valence, arousal, label}
        L3 (FactNode) has emotional_charge (scalar) - we use it as arousal proxy
        """
        if isinstance(memory, EpisodicMemory):
            emotional_peak = memory.emotional_peak or {}
            valence = emotional_peak.get("valence", 0.0)
            arousal = emotional_peak.get("arousal", 0.0)
        elif isinstance(memory, FactNode):
            # FactNode has emotional_charge (scalar)
            # Use it as arousal proxy, assume valence = 0
            valence = 0.0
            arousal = memory.emotional_charge or 0.0
        else:
            valence = 0.0
            arousal = 0.0

        return EmotionalValues(valence=valence, arousal=arousal)

    def _compute_elapsed_days(self, last_updated: datetime, now: datetime) -> float:
        """
        Compute elapsed time in days (continuous).

        Bug fix: Use total_seconds() to avoid integer day truncation.
        Clock skew protection: elapsed ≥ 0.
        """
        elapsed_seconds = (now - last_updated).total_seconds()
        elapsed_days = max(0.0, elapsed_seconds / 86400.0)
        return elapsed_days

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp value to [min_val, max_val]."""
        return max(min_val, min(max_val, value))

    def _compute_state(self, importance: float) -> str:
        """
        Compute memory state from importance score.

        States (from spec §10.2.5):
        - vivid: importance ≥ 0.7
        - fading: importance ≥ 0.5
        - faint: importance ≥ 0.3
        - dormant: importance ≥ 0.1
        - archived: importance < 0.1
        """
        if importance >= STATE_THRESHOLDS["vivid"]:
            return "vivid"
        elif importance >= STATE_THRESHOLDS["fading"]:
            return "fading"
        elif importance >= STATE_THRESHOLDS["faint"]:
            return "faint"
        elif importance >= STATE_THRESHOLDS["dormant"]:
            return "dormant"
        else:
            return "archived"


# ============================================================
# Reinforcement
# ============================================================


class ReinforcementTrigger:
    """Reinforcement trigger types (from spec §10.4.3)."""

    USER_RE_MENTIONED = "user_re_mentioned"
    CHARACTER_RECALLED_CONFIRMED = "character_recalled_user_confirmed"
    RECALL_NO_OBJECTION = "recall_no_objection"
    PEAK_END_AMPLIFICATION = "peak_end_amplification"
    USER_EXPLICIT_INQUIRY = "user_explicit_inquiry"


# Reinforcement boost deltas (from spec §10.4.3)
REINFORCEMENT_DELTAS = {
    ReinforcementTrigger.USER_RE_MENTIONED: 0.15,
    ReinforcementTrigger.CHARACTER_RECALLED_CONFIRMED: 0.20,
    ReinforcementTrigger.RECALL_NO_OBJECTION: 0.02,
    ReinforcementTrigger.PEAK_END_AMPLIFICATION: 0.10,
    ReinforcementTrigger.USER_EXPLICIT_INQUIRY: 0.05,
}


async def reinforce_memory(
    session: AsyncSession,
    memory_id: UUID,
    trigger: str,
    now: Optional[datetime] = None,
) -> None:
    """
    Reinforce a memory via Hebbian boost.

    Bug fix: Boosts initial_importance (not importance_score) so it persists
    through decay calculations.

    Args:
        session: Database session
        memory_id: Memory UUID (L2 or L3)
        trigger: Reinforcement trigger type
        now: Current timestamp (defaults to UTC now)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    boost = REINFORCEMENT_DELTAS.get(trigger, 0.0)
    if boost == 0.0:
        logger.warning("unknown_reinforcement_trigger", trigger=trigger)
        return

    # Try L2 first
    l2_stmt = select(EpisodicMemory).where(EpisodicMemory.id == memory_id)
    result = await session.execute(l2_stmt)
    memory = result.scalar_one_or_none()

    # If not L2, try L3
    if memory is None:
        l3_stmt = select(FactNode).where(FactNode.id == memory_id)
        result = await session.execute(l3_stmt)
        memory = result.scalar_one_or_none()

    if memory is None:
        logger.warning("reinforcement_memory_not_found", memory_id=str(memory_id))
        return

    # Boost initial_importance (capped at MAX_IMPORTANCE)
    old_importance = memory.initial_importance
    new_importance = min(MAX_IMPORTANCE, old_importance + boost)

    memory.initial_importance = new_importance
    memory.recall_count += 1
    memory.last_recalled_at = now

    # Add to reinforcement history (if field exists)
    if hasattr(memory, "reinforcement_history"):
        memory.reinforcement_history.append({
            "triggered_by": trigger,
            "boost": boost,
            "at": now.isoformat(),
        })

    await session.commit()

    logger.info(
        "memory_reinforced",
        memory_id=str(memory_id),
        trigger=trigger,
        boost=boost,
        old_importance=round(old_importance, 3),
        new_importance=round(new_importance, 3),
        recall_count=memory.recall_count,
    )
