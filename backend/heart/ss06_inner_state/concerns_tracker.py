"""
Concerns Tracker — lingering thoughts from SS02 memory + SS03 emotion.

Per runtime_specs/06_inner_state_behavior_runtime.md:
  - §3.2 (Inner Loop 调度, Step 2c)
  - §3.3 (9 大组件, Concerns Tracker)
  - §3.4 (组件职责): 从 Memory 提取她目前"在意"的事
  - §5.5 (Concerns Tracker 数据源): 5 concern source types
  - §4.1 (UserConcern, UnfinishedThought interfaces)
  - §6.6 (长期一致性): 机制 B (expiry), 机制 C (lifecycle)

Key invariants:
  - INV-I-6: |unfinished_thoughts| ≤ MAX_UNFINISHED (=10)
  - 机制 B: default expiry 7 days; high-emotional (|valence| > 0.7) → 30 days
  - 机制 C: has_been_addressed=True → 24h no surfacing
  - Urgency: |valence_peak| × recency_decay × (1 - days_since_addressed / 7)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Union
from uuid import UUID, uuid4

# ============================================================
# Data types (§4.1)
# ============================================================


@dataclass
class UserConcern:
    """A concern the character has about the user (§4.1 UserConcern).

    Sources (§5.5):
      - Unresolved user distress (L2, valence < -0.5)
      - Upcoming user event (L3, predicate: has_upcoming_event)
      - User health mentions (L3, feels_unwell/tired)
      - Promise pending (L4, sacred_promise)
      - Anniversary imminent (L4, anniversary)
    """

    concern_id: UUID
    concern_text: str
    urgency: float  # [0, 1]
    source_memory_ids: List[UUID] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    expiry_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))

    has_been_addressed: bool = False
    last_referenced_at: Optional[datetime] = None


@dataclass
class UnfinishedThought:
    """A thought the character didn't finish expressing (§4.1 UnfinishedThought).

    机制 B: default expiry 7 days; high-emotional → 30 days.
    """

    thought_id: UUID
    content: str
    from_turn_id: UUID

    created_at: datetime = field(default_factory=datetime.utcnow)
    expiry_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))

    reference_count: int = 0


# ============================================================
# Source descriptors for concern extraction (§5.5)
# ============================================================


@dataclass
class ConcernSource:
    """Input data for concern extraction from a single source."""

    source_type: str  # "unresolved_distress", "upcoming_event", ...
    concern_text: str
    valence_peak: float  # emotional intensity (absolute)
    source_memory_ids: List[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    days_since_addressed: float = 0.0  # for urgency decay


# ============================================================
# Concerns Tracker
# ============================================================


class ConcernsTracker:
    """Tracks lingering thoughts from SS02 memory + SS03 emotion.

    Surfaces top-3 concerns/thoughts for current turn composition.

    Usage:
        tracker = ConcernsTracker()
        tracker.extract_concerns(sources, now)
        tracker.extract_unfinished_thoughts(recent_turns, now)
        top = tracker.surface_top_concerns(concerns, thoughts, n=3)
    """

    # Default expiry windows (§6.6)
    DEFAULT_CONCERN_EXPIRY_DAYS = 7
    DEFAULT_THOUGHT_EXPIRY_DAYS = 7
    HIGH_EMOTIONAL_THOUGHT_EXPIRY_DAYS = 30  # |valence| > 0.7

    # Surfacing rules (§6.6 机制 C)
    ADDRESSED_COOLDOWN_HOURS = 24  # has_been_addressed=True → 24h no surfacing

    # Limits (INV-I-6)
    MAX_UNFINISHED_THOUGHTS = 10
    MAX_USER_CONCERNS = 10

    # High emotional threshold for extended expiry (§6.6 机制 B)
    HIGH_EMOTIONAL_THRESHOLD = 0.7

    def __init__(
        self,
        max_concerns: int = MAX_USER_CONCERNS,
        max_unfinished: int = MAX_UNFINISHED_THOUGHTS,
    ):
        self.max_concerns = max_concerns
        self.max_unfinished = max_unfinished

    # ── Concern Extraction ─────────────────────────────────────

    def extract_concerns(
        self,
        sources: List[ConcernSource],
        now: Optional[datetime] = None,
    ) -> List[UserConcern]:
        """Extract UserConcern objects from raw concern sources.

        Each source is mapped to a UserConcern with computed urgency.

        Args:
            sources: List of ConcernSource from SS02 Memory / SS03 Emotion.
            now: Current time for expiry calculation.

        Returns:
            List of UserConcern objects, sorted by urgency descending.
        """
        now = now or datetime.utcnow()
        concerns: List[UserConcern] = []

        for src in sources:
            urgency = self._compute_urgency(
                valence_peak=src.valence_peak,
                created_at=src.created_at,
                days_since_addressed=src.days_since_addressed,
                now=now,
            )

            # Expiry: default 7 days from creation
            expiry = src.created_at + timedelta(days=self.DEFAULT_CONCERN_EXPIRY_DAYS)

            concern = UserConcern(
                concern_id=uuid4(),
                concern_text=src.concern_text,
                urgency=urgency,
                source_memory_ids=list(src.source_memory_ids),
                created_at=src.created_at,
                expiry_at=expiry,
                has_been_addressed=False,
                last_referenced_at=None,
            )
            concerns.append(concern)

        # Sort by urgency descending
        concerns.sort(key=lambda c: c.urgency, reverse=True)

        # Cap at max
        return concerns[: self.max_concerns]

    # ── Unfinished Thought Extraction ──────────────────────────

    def extract_unfinished_thoughts(
        self,
        recent_turns: List[dict],
        emotional_intensity: float = 0.0,
        now: Optional[datetime] = None,
    ) -> List[UnfinishedThought]:
        """Extract unfinished thoughts from recent conversation turns.

        A turn is "unfinished" if the character was interrupted or the
        conversation ended before a thought was fully expressed (§6.6 机制 B).

        Args:
            recent_turns: List of dicts with keys: turn_id (UUID), content (str),
                was_interrupted (bool).
            emotional_intensity: Peak |valence| for the associated episode.
                Values > HIGH_EMOTIONAL_THRESHOLD extend expiry to 30 days.
            now: Current time for expiry calculation.

        Returns:
            List of UnfinishedThought objects.
        """
        now = now or datetime.utcnow()

        # Determine expiry window based on emotional intensity
        if abs(emotional_intensity) > self.HIGH_EMOTIONAL_THRESHOLD:
            expiry_days = self.HIGH_EMOTIONAL_THOUGHT_EXPIRY_DAYS
        else:
            expiry_days = self.DEFAULT_THOUGHT_EXPIRY_DAYS

        thoughts: List[UnfinishedThought] = []
        for turn in recent_turns:
            was_interrupted = turn.get("was_interrupted", False)
            if not was_interrupted:
                continue

            thought = UnfinishedThought(
                thought_id=uuid4(),
                content=turn.get("content", ""),
                from_turn_id=turn.get("turn_id", uuid4()),
                created_at=now,
                expiry_at=now + timedelta(days=expiry_days),
                reference_count=0,
            )
            thoughts.append(thought)

        # Cap at max (INV-I-6)
        return thoughts[: self.max_unfinished]

    def add_unfinished_thought(
        self,
        existing: List[UnfinishedThought],
        content: str,
        turn_id: UUID,
        emotional_intensity: float = 0.0,
        now: Optional[datetime] = None,
    ) -> List[UnfinishedThought]:
        """Add a single unfinished thought to the list, maintaining cap.

        Args:
            existing: Current list of unfinished thoughts.
            content: The thought content.
            turn_id: The turn this thought originates from.
            emotional_intensity: Peak |valence| (affects expiry).
            now: Current time.

        Returns:
            Updated list of UnfinishedThought objects (capped at max).
        """
        now = now or datetime.utcnow()

        if abs(emotional_intensity) > self.HIGH_EMOTIONAL_THRESHOLD:
            expiry_days = self.HIGH_EMOTIONAL_THOUGHT_EXPIRY_DAYS
        else:
            expiry_days = self.DEFAULT_THOUGHT_EXPIRY_DAYS

        thought = UnfinishedThought(
            thought_id=uuid4(),
            content=content,
            from_turn_id=turn_id,
            created_at=now,
            expiry_at=now + timedelta(days=expiry_days),
        )

        updated = list(existing) + [thought]
        # Keep most recent (by created_at), cap at max
        updated.sort(key=lambda t: t.created_at, reverse=True)
        return updated[: self.max_unfinished]

    # ── Surfacing ──────────────────────────────────────────────

    def surface_top_concerns(
        self,
        concerns: List[UserConcern],
        unfinished_thoughts: Optional[List[UnfinishedThought]] = None,
        n: int = 3,
        now: Optional[datetime] = None,
    ) -> List[Union[UserConcern, UnfinishedThought]]:
        """Surface top-N concerns + unfinished thoughts for current turn.

        Selection rules (spec §6.6):
          - Only non-expired items
          - has_been_addressed → 24h cooldown
          - Sort by urgency (concerns) and recency (thoughts)
          - If multiple concerns have same urgency, prefer most recent

        Args:
            concerns: Current user concerns.
            unfinished_thoughts: Current unfinished thoughts.
            n: Number of items to surface (default 3).
            now: Current time for expiry/cooldown checks.

        Returns:
            Top-N surfaced items (mix of UserConcern and UnfinishedThought).
        """
        now = now or datetime.utcnow()
        candidates: List[Tuple[float, Union[UserConcern, UnfinishedThought]]] = []

        # Filter concerns
        for c in concerns:
            if c.expiry_at <= now:
                continue
            if c.has_been_addressed:
                cooldown_end = (
                    c.last_referenced_at + timedelta(hours=self.ADDRESSED_COOLDOWN_HOURS)
                    if c.last_referenced_at
                    else now
                )
                if now < cooldown_end:
                    continue
            # Weight: urgency + recency bonus
            score = c.urgency + self._recency_weight(c.created_at, now)
            candidates.append((score, c))

        # Filter unfinished thoughts
        if unfinished_thoughts:
            for t in unfinished_thoughts:
                if t.expiry_at <= now:
                    continue
                # Thoughts scored by recency (newer = higher)
                score = self._recency_weight(t.created_at, now) * 2.0
                candidates.append((score, t))

        # Sort by score descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        return [item for _, item in candidates[:n]]

    # ── Cleanup ────────────────────────────────────────────────

    def cleanup_expired(
        self,
        concerns: List[UserConcern],
        unfinished_thoughts: Optional[List[UnfinishedThought]] = None,
        now: Optional[datetime] = None,
    ) -> Tuple[List[UserConcern], List[UnfinishedThought]]:
        """Remove expired concerns and unfinished thoughts.

        Per spec §6.6 机制 B + 机制 C.

        Args:
            concerns: Current user concerns.
            unfinished_thoughts: Current unfinished thoughts.
            now: Current time.

        Returns:
            Tuple of (cleaned_concerns, cleaned_thoughts).
        """
        now = now or datetime.utcnow()

        cleaned_concerns = [c for c in concerns if c.expiry_at > now]
        cleaned_thoughts = [t for t in (unfinished_thoughts or []) if t.expiry_at > now]

        return cleaned_concerns, cleaned_thoughts

    # ── Mutation ───────────────────────────────────────────────

    def mark_addressed(
        self,
        concern: UserConcern,
        now: Optional[datetime] = None,
    ) -> UserConcern:
        """Mark a concern as having been addressed by the character.

        Per 机制 C: has_been_addressed=True → 24h cooldown before re-surfacing.

        Args:
            concern: The concern to mark.
            now: Current time.

        Returns:
            Updated concern with addressed flags set.
        """
        now = now or datetime.utcnow()
        concern.has_been_addressed = True
        concern.last_referenced_at = now
        return concern

    def reference_thought(
        self,
        thought: UnfinishedThought,
    ) -> UnfinishedThought:
        """Increment the reference count on an unfinished thought.

        Args:
            thought: The thought being referenced.

        Returns:
            Updated thought with incremented reference_count.
        """
        thought.reference_count += 1
        return thought

    # ── Urgency Computation ────────────────────────────────────

    def _compute_urgency(
        self,
        valence_peak: float,
        created_at: datetime,
        days_since_addressed: float,
        now: datetime,
    ) -> float:
        """Compute concern urgency from emotional intensity and recency.

        Formula (§5.5 source_1):
          urgency = |valence_peak| × recency_decay × (1 - days_since_addressed / 7)

        Clamped to [0, 1].

        Args:
            valence_peak: Peak emotional valence (may be negative for distress).
            created_at: When the concern was first created.
            days_since_addressed: Days since last addressed (0 if never).
            now: Current time.

        Returns:
            Urgency value in [0, 1].
        """
        # Emotional intensity
        intensity = min(abs(valence_peak), 1.0)

        # Recency decay: exponential decay with half-life ~3 days
        age_days = (now - created_at).total_seconds() / 86400.0
        recency_decay = math.exp(-age_days * math.log(2) / 3.0)

        # Addressed decay: urgency reduced as time since addressing increases
        addressed_factor = max(0.0, 1.0 - days_since_addressed / 7.0)

        urgency = intensity * recency_decay * addressed_factor
        return max(0.0, min(1.0, urgency))

    @staticmethod
    def _recency_weight(created_at: datetime, now: datetime) -> float:
        """Compute a recency weight for sorting.

        Newer items get higher scores. Exponential decay with ~1 day half-life.

        Args:
            created_at: When the item was created.
            now: Current time.

        Returns:
            Recency weight in [0, 1].
        """
        age_days = (now - created_at).total_seconds() / 86400.0
        return math.exp(-age_days * math.log(2))
