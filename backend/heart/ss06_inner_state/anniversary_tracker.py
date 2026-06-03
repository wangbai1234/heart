"""
Anniversary Tracker — SS06 Inner State & Behavior §3.7, §6.6 机制 E

Reads L4 (Identity Memory) from SS02 for anniversary candidates and surfaces
upcoming anniversaries to the Initiative Decider for proactive message scheduling.

Key invariants:
  - I-9: Anniversary triggers 100% grounded in L4 — no missed days
  - INV-I-5: Every trigger.source_l4_id exists ∧ l4_data is accurate
  - C-I-4: 24h before → anticipation ("她在为明天做小准备"), day-of → active send
  - IMM-I-4: Birthday → 1x active; 7-day → soft mention, not grand
  - Anti-pattern: ❌ Anniversary计算依赖 client-side 时间

Design:
  - Pure function: accepts L4 memory rows as input, outputs candidates
  - No I/O, no LLM, deterministic
  - Handles yearly/monthly/weekly recurrence patterns
  - 7-day lookahead window for upcoming_anniversaries

Schema per §4.1 upcoming_anniversaries:
  [{anniversary_id, name, due_at, hours_until, soft_mention_sent, actual_sent}]

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

# ============================================================
# Enums
# ============================================================


class AnniversaryPattern(str, Enum):
    """Recurrence patterns for L4 anniversary memories (§2.0 §11.3)."""

    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    ONCE = "once"


class AnniversaryCategory(str, Enum):
    """Semantic category of an anniversary."""

    BIRTHDAY = "birthday"
    RELATIONSHIP = "relationship"
    MILESTONE = "milestone"
    SACRED_PROMISE = "sacred_promise"
    OTHER = "other"


# ============================================================
# Data structures
# ============================================================


@dataclass
class L4AnniversarySource:
    """Minimal L4 identity memory row needed by the tracker.

    This is a read-only projection of SS02 IdentityMemory fields relevant
    to anniversary computation. The actual SS02 service hydrates this.
    """

    l4_id: UUID
    user_id: UUID
    character_id: str
    key: str  # e.g., "user_birthday"
    category: str  # "anniversary" | "sacred_promise"
    value: dict  # the raw identity value blob
    anniversary_pattern: Optional[str]  # "yearly" | "monthly" | "weekly" | "once"
    next_anniversary_at: Optional[datetime]
    created_at: datetime


@dataclass
class AnniversaryCandidate:
    """A single upcoming anniversary detected by the tracker.

    This feeds into InnerState.upcoming_anniversaries and is consumed by
    the Initiative Decider's T1 (anniversary_due) and T4 (anticipation) triggers.
    """

    # ─── Identity (grounded in L4) ───
    anniversary_id: UUID  # = source l4_id
    source_l4_id: UUID  # INV-I-5: must exist and be accurate
    name: str  # "他的生日", "100 天连续"
    category: AnniversaryCategory

    # ─── Timing ───
    due_at: datetime  # next occurrence (server-time, UTC)
    hours_until: float  # hours until due_at from now

    # ─── Pattern for recurrence ───
    pattern: AnniversaryPattern
    original_date: Optional[datetime] = None  # the canonical date (e.g., Jan 15)

    # ─── Celebration guard (单次 per 年) ───
    soft_mention_sent: bool = False  # 24h anticipation sent?
    actual_sent: bool = False  # day-of celebration sent?

    # ─── Soul modulation ───
    celebration_intensity: str = "normal"  # "subtle" | "normal" | "grand"

    # ─── Raw L4 data for audit ───
    l4_data_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnniversaryTrackResult:
    """Complete tracker output for one (user, character) pair."""

    user_id: UUID
    character_id: str
    upcoming: List[AnniversaryCandidate] = field(default_factory=list)
    total_l4_checked: int = 0
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_due_today(self) -> bool:
        """True if any candidate has hours_until ≤ 0 (due now)."""
        return any(c.hours_until <= 0 for c in self.upcoming)

    @property
    def has_within_24h(self) -> bool:
        """True if any candidate within 24h (anticipation window)."""
        return any(0 < c.hours_until <= 24 for c in self.upcoming)


# ============================================================
# Anniversary Tracker
# ============================================================


class AnniversaryTracker:
    """Reads L4 identity memories and surfaces upcoming anniversaries.

    Pure function: no I/O, no LLM calls, deterministic given same inputs.
    Called during Inner Loop Step 2f (or Step 1 context load).

    Usage::

        tracker = AnniversaryTracker()
        result = tracker.track(l4_sources, user_id, character_id, now=now)
        for c in result.upcoming:
            print(f"{c.name} in {c.hours_until:.1f}h — pattern={c.pattern.value}")
    """

    LOOKAHEAD_DAYS = 7
    MAX_CANDIDATES = 10

    INTENSITY_MAP: Dict[AnniversaryCategory, str] = {
        AnniversaryCategory.BIRTHDAY: "grand",
        AnniversaryCategory.RELATIONSHIP: "normal",
        AnniversaryCategory.MILESTONE: "normal",
        AnniversaryCategory.SACRED_PROMISE: "subtle",
        AnniversaryCategory.OTHER: "subtle",
    }

    def __init__(
        self,
        lookahead_days: int = LOOKAHEAD_DAYS,
        max_candidates: int = MAX_CANDIDATES,
    ):
        self.lookahead_days = lookahead_days
        self.max_candidates = max_candidates

    # ── Public API ──────────────────────────────────────────────

    def track(
        self,
        l4_sources: List[L4AnniversarySource],
        user_id: UUID,
        character_id: str,
        now: Optional[datetime] = None,
    ) -> AnniversaryTrackResult:
        """Scan L4 identity memories and produce anniversary candidates.

        Args:
            l4_sources: L4 IdentityMemory rows with anniversary_pattern set.
            user_id / character_id: For result identity.
            now: Reference time (injectable for testing). Defaults to UTC now.

        Returns:
            AnniversaryTrackResult with sorted upcoming candidates.
        """
        now = now or datetime.now(timezone.utc)
        lookahead = now + timedelta(days=self.lookahead_days)

        candidates: List[AnniversaryCandidate] = []
        for src in l4_sources:
            candidate = self._evaluate_source(src, now, lookahead)
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(key=lambda c: c.hours_until)
        candidates = candidates[: self.max_candidates]

        return AnniversaryTrackResult(
            user_id=user_id,
            character_id=character_id,
            upcoming=candidates,
            total_l4_checked=len(l4_sources),
        )

    def compute_next_occurrence(
        self,
        original_date: datetime,
        pattern: AnniversaryPattern,
        now: datetime,
    ) -> Optional[datetime]:
        """Compute the next occurrence of a recurring anniversary.

        Args:
            original_date: The canonical date.
            pattern: Recurrence pattern.
            now: Reference time.

        Returns:
            Next occurrence datetime or None for ONCE past events.
        """
        if pattern == AnniversaryPattern.ONCE:
            return original_date if original_date > now else None
        if pattern == AnniversaryPattern.YEARLY:
            return self._next_yearly(original_date, now)
        if pattern == AnniversaryPattern.MONTHLY:
            return self._next_monthly(original_date, now)
        if pattern == AnniversaryPattern.WEEKLY:
            return self._next_weekly(original_date, now)
        return None

    # ── Internal: source evaluation ──────────────────────────────

    def _evaluate_source(
        self,
        src: L4AnniversarySource,
        now: datetime,
        lookahead: datetime,
    ) -> Optional[AnniversaryCandidate]:
        """Evaluate a single L4 source and produce a candidate if relevant."""

        due_at = self._resolve_due_at(src, now)
        if due_at is None:
            return None

        hours_until = (due_at - now).total_seconds() / 3600.0
        if hours_until > self.lookahead_days * 24:
            return None
        if hours_until < -24:
            return None

        category = self._infer_category(src)
        original_date = self._extract_original_date(src)

        return AnniversaryCandidate(
            anniversary_id=src.l4_id,
            source_l4_id=src.l4_id,
            name=self._build_display_name(src, category),
            category=category,
            due_at=due_at,
            hours_until=hours_until,
            pattern=AnniversaryPattern(src.anniversary_pattern or "once"),
            original_date=original_date,
            soft_mention_sent=False,
            actual_sent=False,
            celebration_intensity=self.INTENSITY_MAP.get(category, "normal"),
            l4_data_snapshot={
                "key": src.key,
                "category": src.category,
                "pattern": src.anniversary_pattern,
                "created_at": src.created_at.isoformat(),
            },
        )

    def _resolve_due_at(self, src: L4AnniversarySource, now: datetime) -> Optional[datetime]:
        """Resolve due_at: prefer next_anniversary_at, fallback to computed."""
        if src.next_anniversary_at is not None:
            return src.next_anniversary_at

        original = self._extract_original_date(src)
        if original is None:
            return None

        pattern = AnniversaryPattern(src.anniversary_pattern or "once")
        return self.compute_next_occurrence(original, pattern, now)

    # ── Recurrence helpers ──────────────────────────────────────

    @staticmethod
    def _next_yearly(original: datetime, now: datetime) -> Optional[datetime]:
        """Next yearly occurrence (same month+day, current or next year).

        For Feb 29 on non-leap years, skips to the next leap year to keep
        the exact date intact (anniversary accuracy, IMM-I-4).
        """
        import calendar

        # Feb 29 special case: find next actual leap year
        if original.month == 2 and original.day == 29:
            year = now.year
            while year <= now.year + 8:
                if calendar.isleap(year):
                    candidate = datetime(year, 2, 29, tzinfo=original.tzinfo)
                    if candidate > now:
                        return candidate
                year += 1
            return None

        # Normal yearly: same month+day, current or next year
        try:
            candidate = original.replace(year=now.year)
        except ValueError:
            return None

        if candidate <= now:
            try:
                candidate = original.replace(year=now.year + 1)
            except ValueError:
                return None
        return candidate

    @staticmethod
    def _next_monthly(original: datetime, now: datetime) -> Optional[datetime]:
        """Next monthly occurrence (same day-of-month, rolling forward)."""
        candidate = original
        while candidate <= now:
            month = candidate.month + 1
            year = candidate.year
            if month > 12:
                month = 1
                year += 1
            try:
                candidate = candidate.replace(year=year, month=month)
            except ValueError:
                import calendar

                last_day = calendar.monthrange(year, month)[1]
                candidate = candidate.replace(year=year, month=month, day=last_day)
        return candidate

    @staticmethod
    def _next_weekly(original: datetime, now: datetime) -> Optional[datetime]:
        """Next weekly occurrence (add 7 days until after now)."""
        candidate = original
        while candidate <= now:
            candidate = candidate + timedelta(days=7)
        return candidate

    # ── L4 value extraction ─────────────────────────────────────

    @staticmethod
    def _extract_original_date(src: L4AnniversarySource) -> Optional[datetime]:
        """Extract canonical date from L4 value blob."""
        value = src.value
        if not isinstance(value, dict):
            return None

        date_keys = [
            "date",
            "datetime",
            "birthday",
            "original_date",
            "canonical_date",
            "occurred_at",
            "first_at",
        ]
        for key in date_keys:
            raw = value.get(key)
            if raw is not None:
                dt = AnniversaryTracker._parse_datetime(raw)
                if dt is not None:
                    return dt
        return src.created_at

    @staticmethod
    def _parse_datetime(raw: Any) -> Optional[datetime]:
        """Parse a datetime from various input formats."""
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, str):
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            ]:
                try:
                    dt = datetime.strptime(raw, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        return None

    # ── Category & display name ──────────────────────────────────

    @staticmethod
    def _infer_category(src: L4AnniversarySource) -> AnniversaryCategory:
        """Infer the anniversary category from L4 metadata."""
        key_lower = src.key.lower()
        category_lower = src.category.lower()

        if "birthday" in key_lower or "birthday" in category_lower:
            return AnniversaryCategory.BIRTHDAY
        if "relationship" in category_lower or "first" in key_lower:
            return AnniversaryCategory.RELATIONSHIP
        if "milestone" in key_lower or "streak" in key_lower:
            return AnniversaryCategory.MILESTONE
        if "sacred_promise" in category_lower or "promise" in key_lower:
            return AnniversaryCategory.SACRED_PROMISE
        return AnniversaryCategory.OTHER

    @staticmethod
    def _build_display_name(src: L4AnniversarySource, category: AnniversaryCategory) -> str:
        """Build a human-readable display name."""
        friendly: Dict[str, str] = {
            "user_birthday": "他的生日",
            "user_birthday_solar": "他的生日",
            "user_birthday_lunar": "他的农历生日",
            "first_meeting": "第一次见面",
            "first_talked": "第一次说话",
            "became_friends": "成为朋友的日子",
            "became_lovers": "在一起的日子",
            "100_day_streak": "100 天连续",
            "30_day_streak": "30 天连续",
        }
        key = src.key
        if key in friendly:
            return friendly[key]
        return key.replace("_", " ").title()

    # ── Format conversion ───────────────────────────────────────

    def to_inner_state_format(
        self,
        candidates: List[AnniversaryCandidate],
    ) -> List[Dict[str, Any]]:
        """Convert candidates to InnerState.upcoming_anniversaries format (§4.1)."""
        return [
            {
                "anniversary_id": str(c.anniversary_id),
                "name": c.name,
                "due_at": c.due_at.isoformat(),
                "hours_until": c.hours_until,
                "soft_mention_sent": c.soft_mention_sent,
                "actual_sent": c.actual_sent,
                "category": c.category.value,
                "pattern": c.pattern.value,
                "celebration_intensity": c.celebration_intensity,
            }
            for c in candidates
        ]
