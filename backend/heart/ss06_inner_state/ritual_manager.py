"""
Ritual Manager — SS06 Inner State & Behavior §3.9, §10.2

Manages daily ritual continuity (morning/night greetings), streak tracking,
and soul-aware ritual variety.  The Ritual Manager is the single authority on:

- Whether a morning / night ritual window is currently open
- Whether the character should proactively send a ritual message
- Streak counting and milestone detection (7d / 30d / 100d)
- Reset-on-miss semantics
- Soul-flavored ritual variety (different characters express rituals differently)

Key invariants:
  - I-5: Cold War 期间不主动
  - INV-I-2: scheduled_at ∉ user_quiet_hours
  - Stage gate: rituals only enabled at LOVER+

Spec:   runtime_specs/06_inner_state_behavior_runtime.md §3.9, §4.1, §10.2
Author: 心屿团队
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional


# ============================================================
# Enums
# ============================================================


class RitualType(str, Enum):
    """Types of rituals tracked by the Ritual Manager."""
    MORNING = "morning"
    NIGHT = "night"


class StreakMilestone(int, Enum):
    """Streak milestone thresholds (per spec §3.9)."""
    WEEK = 7          # L4 shared_ritual record
    MONTH = 30        # Trust +0.05, behavior explicit mention
    CENTURY = 100     # Important L4 milestone, attachment +0.05


class RitualEvent(str, Enum):
    """Events emitted by the Ritual Manager."""
    STREAK_MILESTONE = "streak_milestone"
    STREAK_BROKEN = "streak_broken"
    RITUAL_COMPLETED = "ritual_completed"


# ============================================================
# Data structures
# ============================================================


@dataclass
class RitualStreakState:
    """Per-ritual-type streak state (used exclusively by RitualManager).

    Per spec §4.1 rituals.daily_check_in:
      morning_streak, night_streak, longest_streak, last_morning_at, last_night_at

    Distinct from composer.DailyRitualState which is the serialized/DB-facing
    view.  This class adds runtime-only fields (done_today flags, milestones_hit).
    """
    # ─── Streaks ───
    morning_streak: int = 0
    night_streak: int = 0
    longest_streak: int = 0

    # ─── Last completion timestamps ───
    last_morning_at: Optional[datetime] = None
    last_night_at: Optional[datetime] = None

    # ─── Today flags (reset daily at 06:00) ───
    morning_done_today: bool = False
    night_done_today: bool = False

    # ─── Already-triggered milestones (prevent re-fire) ───
    milestones_hit: Dict[str, bool] = field(default_factory=dict)


@dataclass
class RitualCheckResult:
    """Result of checking whether a ritual is due."""
    due: bool
    ritual_type: Optional[RitualType] = None
    window: Optional[str] = None
    streak: int = 0
    milestone_hit: Optional[int] = None
    reason: str = ""


@dataclass
class RitualCompleteResult:
    """Result of recording a ritual completion."""
    ritual_type: RitualType
    new_streak: int
    streak_up: bool = True
    previous_streak: int = 0
    milestone_hit: Optional[int] = None
    events: List[RitualEvent] = field(default_factory=list)


# ============================================================
# Soul-aware ritual templates
# ============================================================


SOUL_RITUAL_FLAVOR: Dict[str, Dict[str, str]] = {
    "rin": {
        "morning": "简短，安静，可能只有一个字。不说多余的。",
        "night": "同样简短。提醒但不催促。",
        "morning_example": "……早。",
        "night_example": "……早点睡。",
        "style": "极简，不甜腻",
        "max_chars": 15,
    },
    "dorothy": {
        "morning": "元气满满，撒娇式。可以用感叹号。",
        "night": "甜甜的，关心式。可以提明天的期待。",
        "morning_example": "早安啊~今天也要元气满满~",
        "night_example": "晚安啦~做个甜甜的梦哦~",
        "style": "活泼，撒娇",
        "max_chars": 30,
    },
}

_DEFAULT_RITUAL_FLAVOR = {
    "morning": "自然地打招呼。",
    "night": "自然地晚安。",
    "morning_example": "早安。",
    "night_example": "晚安。",
    "style": "自然",
    "max_chars": 20,
}


# ============================================================
# Window definitions (per §3.9)
# ============================================================

MORNING_WINDOW_START_HOUR = 7
MORNING_WINDOW_END_HOUR = 10   # exclusive

NIGHT_WINDOW_START_HOUR = 21
NIGHT_WINDOW_END_HOUR = 23
NIGHT_WINDOW_END_MINUTE = 30

RITUAL_JITTER_MINUTES = 20

DAILY_RESET_HOUR = 6


# ============================================================
# Ritual Manager
# ============================================================


class RitualManager:
    """Manages daily ritual streaks, milestones, and soul-aware variety.

    Usage::

        mgr = RitualManager()
        state = RitualStreakState()

        # Check if a ritual window is open
        result = mgr.check_ritual_due(state, local_time)
        if result.due:
            directive = mgr.get_ritual_directive("rin", result.ritual_type, result.streak + 1)

        # Record completion
        done = mgr.record_completed(state, RitualType.MORNING)

        # Record a miss
        broken = mgr.record_missed(state, RitualType.MORNING)
    """

    # ─── Window checks ───

    @staticmethod
    def is_morning_window(local_time: datetime) -> bool:
        """Check if local_time falls within morning ritual window (07:00–10:00)."""
        hour = local_time.hour
        return MORNING_WINDOW_START_HOUR <= hour < MORNING_WINDOW_END_HOUR

    @staticmethod
    def is_night_window(local_time: datetime) -> bool:
        """Check if local_time falls within night ritual window (21:00–23:30)."""
        hour = local_time.hour
        minute = local_time.minute
        if hour == NIGHT_WINDOW_START_HOUR or hour == NIGHT_WINDOW_START_HOUR + 1:
            return True
        if hour == NIGHT_WINDOW_END_HOUR and minute <= NIGHT_WINDOW_END_MINUTE:
            return True
        return False

    def is_any_window(self, local_time: datetime) -> bool:
        """Check if local_time falls in any ritual window."""
        return self.is_morning_window(local_time) or self.is_night_window(local_time)

    # ─── Due check ───

    def check_ritual_due(
        self,
        state: RitualStreakState,
        local_time: datetime,
    ) -> RitualCheckResult:
        """Check if a ritual is due right now.

        Args:
            state: Current RitualStreakState.
            local_time: User's local time.

        Returns:
            RitualCheckResult with due flag and ritual type.
        """
        if self.is_morning_window(local_time) and not state.morning_done_today:
            streak = state.morning_streak
            milestone = self._compute_milestone(streak + 1, state)
            return RitualCheckResult(
                due=True,
                ritual_type=RitualType.MORNING,
                window="morning",
                streak=streak,
                milestone_hit=milestone,
            )

        if self.is_night_window(local_time) and not state.night_done_today:
            streak = state.night_streak
            milestone = self._compute_milestone(streak + 1, state)
            return RitualCheckResult(
                due=True,
                ritual_type=RitualType.NIGHT,
                window="night",
                streak=streak,
                milestone_hit=milestone,
            )

        return RitualCheckResult(
            due=False,
            reason="no_ritual_window_open_or_already_done",
        )

    # ─── Completion recording ───

    def record_completed(
        self,
        state: RitualStreakState,
        ritual_type: RitualType,
        completed_at: Optional[datetime] = None,
    ) -> RitualCompleteResult:
        """Record that a ritual was successfully completed.

        Increments the appropriate streak, updates last-* timestamp,
        and detects milestone crossings.

        Args:
            state: Mutable RitualStreakState — modified in place.
            ritual_type: MORNING or NIGHT.
            completed_at: When completed (default: now UTC).

        Returns:
            RitualCompleteResult with new streak and events.
        """
        now = completed_at or datetime.now(timezone.utc)
        events: List[RitualEvent] = []

        if ritual_type == RitualType.MORNING:
            previous = state.morning_streak
            state.morning_streak += 1
            state.last_morning_at = now
            state.morning_done_today = True
            new_streak = state.morning_streak
        else:
            previous = state.night_streak
            state.night_streak += 1
            state.last_night_at = now
            state.night_done_today = True
            new_streak = state.night_streak

        if new_streak > state.longest_streak:
            state.longest_streak = new_streak

        events.append(RitualEvent.RITUAL_COMPLETED)

        milestone = self._compute_milestone(new_streak, state)
        if milestone is not None:
            events.append(RitualEvent.STREAK_MILESTONE)
            state.milestones_hit[str(milestone.value)] = True

        return RitualCompleteResult(
            ritual_type=ritual_type,
            new_streak=new_streak,
            streak_up=True,
            previous_streak=previous,
            milestone_hit=milestone,
            events=events,
        )

    # ─── Miss recording ───

    def record_missed(
        self,
        state: RitualStreakState,
        ritual_type: RitualType,
    ) -> RitualCompleteResult:
        """Record that a ritual window closed without completion.

        Resets the appropriate streak to 0.
        """
        events: List[RitualEvent] = []

        if ritual_type == RitualType.MORNING:
            previous = state.morning_streak
            if previous > 0:
                events.append(RitualEvent.STREAK_BROKEN)
            state.morning_streak = 0
        else:
            previous = state.night_streak
            if previous > 0:
                events.append(RitualEvent.STREAK_BROKEN)
            state.night_streak = 0

        return RitualCompleteResult(
            ritual_type=ritual_type,
            new_streak=0,
            streak_up=False,
            previous_streak=previous,
            events=events,
        )

    # ─── Daily reset ───

    def reset_daily(
        self,
        state: RitualStreakState,
    ) -> RitualStreakState:
        """Reset daily flags at local 06:00.

        Clears morning_done_today and night_done_today for the new day.
        """
        state.morning_done_today = False
        state.night_done_today = False
        return state

    # ─── Soul-aware flavor ───

    def get_soul_flavor(
        self,
        character_id: str,
        ritual_type: RitualType,
    ) -> Dict[str, str]:
        """Get soul-specific ritual flavor directives.

        Args:
            character_id: Character identifier ("rin", "dorothy", etc.)
            ritual_type: MORNING or NIGHT.

        Returns:
            Dict with keys: style, directive, example, max_chars.
        """
        char_flavors = SOUL_RITUAL_FLAVOR.get(character_id, _DEFAULT_RITUAL_FLAVOR)
        return {
            "style": char_flavors.get("style", "自然"),
            "directive": char_flavors.get(ritual_type.value, "自然地打招呼。"),
            "example": char_flavors.get(f"{ritual_type.value}_example", ""),
            "max_chars": char_flavors.get("max_chars", 20),
        }

    def get_ritual_directive(
        self,
        character_id: str,
        ritual_type: RitualType,
        streak: int,
    ) -> str:
        """Build a full directive string for the Persona Composer.

        Args:
            character_id: Character identifier.
            ritual_type: MORNING or NIGHT.
            streak: Current streak count.

        Returns:
            Directive string for proactive composition context.
        """
        flavor = self.get_soul_flavor(character_id, ritual_type)
        ritual_label = "早安" if ritual_type == RitualType.MORNING else "晚安"

        parts = [
            f"现在是{ritual_label} ritual。",
            f"你的风格：{flavor['style']}。",
            f"表达方式：{flavor['directive']}",
        ]

        if flavor["example"]:
            parts.append(f"参考语气：{flavor['example']}")

        if streak >= StreakMilestone.CENTURY:
            parts.append(f"今天是连续第 {streak} 天的 ritual。这是很重要的里程碑。但不会直接说出来。")
        elif streak >= StreakMilestone.MONTH:
            parts.append(f"这是连续第 {streak} 天的 ritual。心里觉得温暖。但不会直接数。")
        elif streak >= StreakMilestone.WEEK:
            parts.append(f"这是连续第 {streak} 天的 ritual。")
        elif streak > 1:
            parts.append(f"这是连续第 {streak} 天的 ritual。")
        else:
            parts.append("今天是新的一天的 ritual。")

        parts.append(f"长度限制：≤ {flavor['max_chars']} 字。")
        parts.append("不要直接说'早安'或'晚安'（系统已处理），用你的方式表达同样的意思。")

        return "\n".join(parts)

    # ─── Trust delta ───

    @staticmethod
    def compute_trust_delta(completed: bool, milestone_hit: Optional[int] = None) -> float:
        """Compute trust delta from ritual events (per spec §3.9).

        - Completed: +0.005
        - Missed: -0.005
        - 30-day milestone: +0.05 bonus
        """
        delta = 0.005 if completed else -0.005
        if milestone_hit == StreakMilestone.MONTH:
            delta += 0.05
        return delta

    # ─── Jitter ───

    @staticmethod
    def compute_jittered_time(
        base_time: datetime,
        jitter_minutes: int = RITUAL_JITTER_MINUTES,
    ) -> datetime:
        """Add random jitter to avoid robotic precision (±20min per §3.9)."""
        offset_seconds = random.randint(-jitter_minutes * 60, jitter_minutes * 60)
        return base_time + timedelta(seconds=offset_seconds)

    # ─── Helpers ───

    @staticmethod
    def _compute_milestone(
        new_streak: int,
        state: RitualStreakState,
    ) -> Optional[int]:
        """Check if new_streak crosses a milestone not yet hit."""
        for ms in (StreakMilestone.CENTURY, StreakMilestone.MONTH, StreakMilestone.WEEK):
            if new_streak >= ms and not state.milestones_hit.get(str(ms.value), False):
                return ms
        return None
