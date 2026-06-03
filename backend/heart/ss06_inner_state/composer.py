"""
Inner State Composer — Aggregates all SS06 components into InnerState.

Per runtime_specs/06_inner_state_behavior_runtime.md:
  - §3.4: 整合所有部件 → InnerState (In: components / Out: InnerState)
  - §3.5: Inner Loop Flow Step 2 (mood + activities + concerns + energy + cleanup)
  - §4.1: InnerState complete schema

Key invariants:
  - INV-I-3: Update completes < 200ms (no LLM calls)
  - I-2: Inner State is the cross-modal single point of truth
  - I-6: Inner State update → Emotion injection must go through Soul.inertia calibration

Aggregates:
  - current_activity (from ActivityGenerator)
  - concerns (from ConcernsTracker: user_concerns + unfinished_thoughts)
  - mood_drift (delta from last mood state)
  - since-last-talk delta (time since last user interaction)

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

# ============================================================
# InnerState — per §4.1
# ============================================================


@dataclass
class TodayMood:
    """Today's mood snapshot (§4.1 TodayMood)."""

    label: str  # "tired but cozy"
    primary_emotion: str  # from EmotionState
    valence: float  # [-1, 1]
    arousal: float  # [0, 1]
    descriptor: str  # natural language, soul-flavored

    # Mood drift since last inner loop update
    delta_valence: float = 0.0  # [-2, 2]
    delta_arousal: float = 0.0  # [-1, 1]
    drift_direction: str = "stable"  # "rising" | "falling" | "stable"


@dataclass
class EnergyPoint:
    """Hourly energy snapshot (§4.1 EnergyPoint)."""

    hour: int  # 0-23
    energy: float  # [0, 1]
    source: str  # "circadian" | "recent_activity" | "emotional"


@dataclass
class ProactiveState:
    """Initiative tracking state (§4.1 proactive_state)."""

    last_proactive_at: Optional[str] = None  # ISO8601
    proactive_today_count: int = 0
    last_proactive_type: Optional[str] = None
    pending_initiatives: List[dict] = field(default_factory=list)


@dataclass
class DailyRitualState:
    """Daily ritual tracking (§4.1 rituals.daily_check_in)."""

    morning_streak: int = 0
    night_streak: int = 0
    longest_streak: int = 0
    last_morning_at: Optional[str] = None
    last_night_at: Optional[str] = None


@dataclass
class RitualState:
    """Ritual state container (§4.1 rituals)."""

    daily_check_in: DailyRitualState = field(default_factory=DailyRitualState)


@dataclass
class TodayState:
    """Today-reset block (§4.1 today). Resets daily at local 06:00."""

    date: str = ""  # ISO date "2026-05-15"
    mood: Optional[TodayMood] = None
    activities: List[object] = field(default_factory=list)  # Activity[]
    energy_trajectory: List[EnergyPoint] = field(default_factory=list)
    morning_check_in_done: bool = False
    night_check_in_done: bool = False


@dataclass
class InnerState:
    """Complete inner state for a (user, character) pair (§4.1 InnerState).

    This is the cross-modal single point of truth (I-2).
    Never exposed directly to users (I-10); only used for prompt construction.
    """

    # ─── Identity ───
    user_id: UUID
    character_id: str

    # ─── Today (resets daily at local 06:00) ───
    today: TodayState = field(default_factory=TodayState)

    # ─── Current Energy ───
    current_energy: float = 0.5  # [0, 1]
    energy_baseline: float = 0.5  # from Soul

    # ─── Since last talk ───
    last_user_interaction_at: Optional[str] = None  # ISO8601
    since_last_talk_seconds: float = 0.0
    since_last_talk_label: str = "刚刚"  # human-readable: "刚刚" | "几小时前" | "一天前" | ...

    # ─── Concerns about User ───
    user_concerns: List[object] = field(default_factory=list)  # UserConcern[]

    # ─── Unfinished Thoughts ───
    unfinished_thoughts: List[object] = field(default_factory=list)  # UnfinishedThought[]

    # ─── Initiative tracking ───
    proactive_state: ProactiveState = field(default_factory=ProactiveState)

    # ─── Anniversary upcoming ───
    upcoming_anniversaries: List[dict] = field(default_factory=list)
    # [{anniversary_id, name, due_at, hours_until, soft_mention_sent, actual_sent}]

    # ─── Ritual State ───
    rituals: RitualState = field(default_factory=RitualState)

    # ─── Dream (V2) ───
    recent_dream: Optional[dict] = None  # Dream | null

    # ─── Meta ───
    next_inner_loop_at: str = ""  # ISO8601
    loop_iteration_count: int = 0
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================
# Inner State Composer
# ============================================================


class InnerStateComposer:
    """Aggregates all SS06 components into a coherent InnerState.

    Per §3.4: 整合所有部件 → InnerState.
    Per §3.5 Step 2: mood + activities + concerns + energy + cleanup.

    Usage::

        composer = InnerStateComposer()
        inner_state = composer.compose(
            user_id=uuid4(),
            character_id="rin",
            activities=[activity],
            user_concerns=concerns,
            unfinished_thoughts=thoughts,
            mood_label="平静",
            mood_valence=0.3,
            mood_arousal=0.4,
            mood_descriptor="你今天有些静。",
            prev_mood_valence=0.5,
            prev_mood_arousal=0.3,
            current_energy=0.65,
            energy_baseline=0.5,
            last_user_interaction_at=None,
            upcoming_anniversaries=[],
        )
    """

    # ── Mood drift thresholds ──

    DRIFT_RISING_THRESHOLD = 0.15  # valence increase > this → "rising"
    DRIFT_FALLING_THRESHOLD = -0.15  # valence decrease < this → "falling"

    # ── Since-last-talk labels ──

    TALK_LABEL_THRESHOLDS: List[tuple[float, str]] = [
        (0, "刚刚"),
        (60, "1 分钟前"),
        (300, "几分钟前"),
        (1800, "半小时前"),
        (3600, "1 小时前"),
        (7200, "几小时前"),
        (21600, "半天前"),
        (43200, "半天多前"),
        (86400, "一天前"),
        (172800, "两天前"),
        (259200, "几天前"),
        (604800, "一周前"),
    ]

    # ── Public API ──────────────────────────────────────────────

    def compose(
        self,
        *,
        user_id: UUID,
        character_id: str,
        # Activity
        activities: Optional[List[object]] = None,
        # Concerns
        user_concerns: Optional[List[object]] = None,
        unfinished_thoughts: Optional[List[object]] = None,
        # Mood
        mood_label: str = "平静",
        mood_valence: float = 0.0,
        mood_arousal: float = 0.5,
        mood_descriptor: str = "",
        prev_mood_valence: float = 0.0,
        prev_mood_arousal: float = 0.5,
        # Energy
        current_energy: float = 0.5,
        energy_baseline: float = 0.5,
        energy_trajectory: Optional[List[EnergyPoint]] = None,
        # Since last talk
        last_user_interaction_at: Optional[str] = None,
        # Anniversaries
        upcoming_anniversaries: Optional[List[dict]] = None,
        # Ritual state
        morning_streak: int = 0,
        night_streak: int = 0,
        longest_streak: int = 0,
        last_morning_at: Optional[str] = None,
        last_night_at: Optional[str] = None,
        # Proactive state
        proactive_state: Optional[ProactiveState] = None,
        # Dream (V2)
        recent_dream: Optional[dict] = None,
        # Meta
        loop_iteration_count: int = 0,
        next_inner_loop_at: Optional[str] = None,
        # Today checks
        morning_check_in_done: bool = False,
        night_check_in_done: bool = False,
    ) -> InnerState:
        """Aggregate all components into InnerState.

        Args:
            user_id: User UUID.
            character_id: Character identifier.
            activities: Today's selected activities.
            user_concerns: Concerns about the user.
            unfinished_thoughts: Lingering unfinished thoughts.
            mood_label: Current mood label (e.g. "平静", "疲惫但安心").
            mood_valence: Current mood valence [-1, 1].
            mood_arousal: Current mood arousal [0, 1].
            mood_descriptor: Soul-flavored natural language mood description.
            prev_mood_valence: Previous mood valence for drift calculation.
            prev_mood_arousal: Previous mood arousal for drift calculation.
            current_energy: Current energy level [0, 1].
            energy_baseline: Baseline energy from Soul.
            energy_trajectory: Hourly energy snapshots.
            last_user_interaction_at: ISO8601 of last user interaction.
            upcoming_anniversaries: Upcoming anniversary entries.
            morning_streak: Morning ritual streak.
            night_streak: Night ritual streak.
            longest_streak: Longest ritual streak.
            last_morning_at: ISO8601 of last morning ritual.
            last_night_at: ISO8601 of last night ritual.
            proactive_state: Existing proactive state (or fresh).
            recent_dream: Recent dream data (V2).
            loop_iteration_count: Number of inner loop iterations so far.
            next_inner_loop_at: ISO8601 for next scheduled loop.
            morning_check_in_done: Whether morning check-in completed today.
            night_check_in_done: Whether night check-in completed today.

        Returns:
            Populated InnerState.
        """
        now = datetime.now(timezone.utc).isoformat()

        # ── Mood drift ──
        delta_valence = mood_valence - prev_mood_valence
        delta_arousal = mood_arousal - prev_mood_arousal
        drift_direction = self._classify_drift(delta_valence)

        today_mood = TodayMood(
            label=mood_label,
            primary_emotion=self._derive_emotion_name(mood_valence, mood_arousal),
            valence=mood_valence,
            arousal=mood_arousal,
            descriptor=mood_descriptor,
            delta_valence=delta_valence,
            delta_arousal=delta_arousal,
            drift_direction=drift_direction,
        )

        # ── Since-last-talk ──
        since_seconds, since_label = self._compute_since_last_talk(last_user_interaction_at)

        # ── Assemble today ──
        today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        today = TodayState(
            date=today_date,
            mood=today_mood,
            activities=list(activities) if activities else [],
            energy_trajectory=list(energy_trajectory) if energy_trajectory else [],
            morning_check_in_done=morning_check_in_done,
            night_check_in_done=night_check_in_done,
        )

        # ── Assemble rituals ──
        rituals = RitualState(
            daily_check_in=DailyRitualState(
                morning_streak=morning_streak,
                night_streak=night_streak,
                longest_streak=longest_streak,
                last_morning_at=last_morning_at,
                last_night_at=last_night_at,
            )
        )

        # ── Proactive state ──
        if proactive_state is None:
            proactive_state = ProactiveState()

        # ── Next inner loop ──
        if next_inner_loop_at is None:
            next_loop = datetime.now(timezone.utc) + timedelta(hours=1)
            next_inner_loop_at = next_loop.isoformat()

        return InnerState(
            user_id=user_id,
            character_id=character_id,
            today=today,
            current_energy=current_energy,
            energy_baseline=energy_baseline,
            last_user_interaction_at=last_user_interaction_at,
            since_last_talk_seconds=since_seconds,
            since_last_talk_label=since_label,
            user_concerns=list(user_concerns) if user_concerns else [],
            unfinished_thoughts=list(unfinished_thoughts) if unfinished_thoughts else [],
            proactive_state=proactive_state,
            upcoming_anniversaries=list(upcoming_anniversaries) if upcoming_anniversaries else [],
            rituals=rituals,
            recent_dream=recent_dream,
            next_inner_loop_at=next_inner_loop_at,
            loop_iteration_count=loop_iteration_count,
            updated_at=now,
        )

    # ── Helpers ─────────────────────────────────────────────────

    def _classify_drift(self, delta_valence: float) -> str:
        """Classify mood drift direction from valence delta.

        Uses rounding to 4 decimal places to avoid floating-point
        precision issues (e.g. 0.45 - 0.3 = 0.15000000000000002).
        """
        delta = round(delta_valence, 4)
        if delta > self.DRIFT_RISING_THRESHOLD:
            return "rising"
        elif delta < self.DRIFT_FALLING_THRESHOLD:
            return "falling"
        return "stable"

    @staticmethod
    def _derive_emotion_name(valence: float, arousal: float) -> str:
        """Derive a primary emotion name from valence × arousal quadrant."""
        if valence >= 0.3:
            if arousal >= 0.6:
                return "excited"
            elif arousal >= 0.3:
                return "content"
            else:
                return "serene"
        elif valence >= -0.3:
            if arousal >= 0.6:
                return "restless"
            elif arousal >= 0.3:
                return "neutral"
            else:
                return "lethargic"
        else:
            if arousal >= 0.6:
                return "distressed"
            elif arousal >= 0.3:
                return "sad"
            else:
                return "depressed"

    def _compute_since_last_talk(self, last_interaction_at: Optional[str]) -> tuple[float, str]:
        """Compute seconds since last user interaction and a human label.

        Returns:
            (seconds, label) tuple.
        """
        if last_interaction_at is None:
            return 0.0, "刚刚"

        try:
            last_dt = datetime.fromisoformat(last_interaction_at.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            delta = (now_dt - last_dt).total_seconds()
            delta = max(0.0, delta)
        except (ValueError, TypeError):
            return 0.0, "刚刚"

        label = self._quantize_since_label(delta)
        return delta, label

    def _quantize_since_label(self, seconds: float) -> str:
        """Map seconds to a human-readable label."""
        for threshold, label in reversed(self.TALK_LABEL_THRESHOLDS):
            if seconds >= threshold:
                return label
        return "刚刚"


# ============================================================
# Convenience function
# ============================================================


def compose_inner_state(
    user_id: UUID,
    character_id: str,
    *,
    activities: Optional[List[object]] = None,
    user_concerns: Optional[List[object]] = None,
    unfinished_thoughts: Optional[List[object]] = None,
    mood_label: str = "平静",
    mood_valence: float = 0.0,
    mood_arousal: float = 0.5,
    mood_descriptor: str = "",
    prev_mood_valence: float = 0.0,
    prev_mood_arousal: float = 0.5,
    current_energy: float = 0.5,
    energy_baseline: float = 0.5,
    energy_trajectory: Optional[List[EnergyPoint]] = None,
    last_user_interaction_at: Optional[str] = None,
    upcoming_anniversaries: Optional[List[dict]] = None,
    **kwargs,
) -> InnerState:
    """Quick compose without constructing the class."""
    composer = InnerStateComposer()
    return composer.compose(
        user_id=user_id,
        character_id=character_id,
        activities=activities,
        user_concerns=user_concerns,
        unfinished_thoughts=unfinished_thoughts,
        mood_label=mood_label,
        mood_valence=mood_valence,
        mood_arousal=mood_arousal,
        mood_descriptor=mood_descriptor,
        prev_mood_valence=prev_mood_valence,
        prev_mood_arousal=prev_mood_arousal,
        current_energy=current_energy,
        energy_baseline=energy_baseline,
        energy_trajectory=energy_trajectory,
        last_user_interaction_at=last_user_interaction_at,
        upcoming_anniversaries=upcoming_anniversaries,
        **kwargs,
    )
