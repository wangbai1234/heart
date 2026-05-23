"""
Activity Generator — Soul-curated daily activity selection.

Per runtime_specs/06_inner_state_behavior_runtime.md:
  - §3.2 (Inner Loop 调度, Step 2b)
  - §3.3 (9 大组件, Activity Generator)
  - §3.4 (组件职责)
  - §10.4 (Activity Generator implementation spec)

Key invariants:
  - INV-I-4: ∀ activity A: A ∈ soul.activity_pool[character_id]
  - I-7: Activity Generation 必须 Soul-curated，不随机生成
  - INV-I-7: 跨 user/character 隔离严格
  - 机制 D: 同一 activity 不在 3 天内被选两次

Deterministic: seeded by (user_id, character_id, hour) → same seed → same output.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set
from uuid import UUID, uuid4

import yaml


# ============================================================
# Types
# ============================================================

TimeOfDay = Literal["morning", "afternoon", "evening", "night"]
DayType = Literal["weekday", "weekend"]


@dataclass
class Activity:
    """A single activity selected from Soul.activity_pool.

    Per spec §4.1 Activity interface.
    """

    activity_id: UUID
    description: str
    time_of_day: TimeOfDay
    scheduled_at: datetime
    associated_mood: str
    share_eligible: bool
    already_shared: bool = False

    # YAML pool entry id for repeat-avoidance tracking
    pool_id: str = ""


# ============================================================
# YAML pool entry shape (internal)
# ============================================================

@dataclass
class _PoolEntry:
    """Parsed activity pool entry from YAML."""

    id: str
    description: str
    duration: str
    interruptible: bool
    mood_modifier: dict
    allowed_stages: List[str]
    share_eligible: bool
    share_template: str = ""


# ============================================================
# Activity Generator
# ============================================================


class ActivityGenerator:
    """Soul-curated activity selection.

    Loads activity pools from config/activity_pools/<character_id>.yaml.
    Provides deterministic per-(user, character, hour) selection.

    Usage:
        gen = ActivityGenerator()
        activity = gen.select(soul, user_id, current_time, recent_activity_ids)
    """

    # Time-of-day window mapping (§3.8: 4 periods)
    TIME_WINDOWS: Dict[TimeOfDay, range] = {
        "morning": range(6, 12),     # 06:00–11:59
        "afternoon": range(12, 18),   # 12:00–17:59
        "evening": range(18, 22),    # 18:00–21:59
        "night": range(22, 24),      # 22:00–23:59
    }

    # Night also covers 00:00–05:59
    NIGHT_EARLY = range(0, 6)

    # Days to avoid repeat (§10.4: 3 days, 机制 D)
    REPEAT_AVOIDANCE_DAYS = 3

    def __init__(self, activity_pool_dir: Optional[str] = None):
        """Initialize the generator.

        Args:
            activity_pool_dir: Path to activity pool YAML files.
                Defaults to config/activity_pools/ relative to project root.
        """
        if activity_pool_dir is None:
            repo_root = Path(__file__).resolve().parents[3]
            activity_pool_dir = str(repo_root / "config" / "activity_pools")

        self._pool_dir = Path(activity_pool_dir)
        self._pools: Dict[str, Dict[str, Dict[str, List[_PoolEntry]]]] = {}
        # _pools[character_id][day_type][time_of_day] = List[_PoolEntry]

    # ── Public API ──────────────────────────────────────────────

    def select(
        self,
        soul: object,
        user_id: UUID,
        current_time: datetime,
        recent_activity_ids: Optional[Set[str]] = None,
    ) -> Activity:
        """Select one activity for the current time window.

        Deterministic: seeded by (user_id, character_id, hour).
        Avoids activities already used in recent_activity_ids (last 3 days).

        Args:
            soul: SoulSpec object with character_id attribute.
            user_id: The user UUID.
            current_time: Current datetime (used for hour → time_of_day).
            recent_activity_ids: Set of pool_ids used in the last 3 days.

        Returns:
            A single Activity for the current time window.

        Raises:
            ValueError: If no activity pool exists for the character.
        """
        character_id = getattr(soul, "character_id", None)
        if not character_id:
            raise ValueError("Soul spec missing character_id")

        tod = self._determine_time_of_day(current_time)
        day_type = self._determine_day_type(current_time)
        seed = self._make_seed(user_id, character_id, current_time)
        rng = random.Random(seed)

        pool = self._load_pool(character_id)
        candidates = pool.get(day_type, {}).get(tod, [])

        if not candidates:
            raise ValueError(
                f"No activities found for character_id={character_id} "
                f"day_type={day_type} time_of_day={tod}"
            )

        # Filter out recently used (3-day avoidance, 机制 D)
        if recent_activity_ids:
            filtered = [e for e in candidates if e.id not in recent_activity_ids]
            if filtered:
                candidates = filtered
            # If ALL candidates are recent, allow repeats (pool too small)

        chosen = rng.choice(candidates)

        # Pick a mood label from the mood_modifier keys
        mood_keys = list(chosen.mood_modifier.keys())
        mood = rng.choice(mood_keys) if mood_keys else "neutral"

        # Scheduled time: start of the time window
        scheduled_hour = (
            self.TIME_WINDOWS[tod].start if tod in self.TIME_WINDOWS else 0
        )
        scheduled_at = current_time.replace(
            hour=scheduled_hour, minute=0, second=0, microsecond=0
        )

        return Activity(
            activity_id=uuid4(),
            description=chosen.description,
            time_of_day=tod,
            scheduled_at=scheduled_at,
            associated_mood=mood,
            share_eligible=chosen.share_eligible,
            already_shared=False,
            pool_id=chosen.id,
        )

    def generate_today_activities(
        self,
        soul: object,
        user_id: UUID,
        target_date: date,
        recent_activity_ids: Optional[Set[str]] = None,
    ) -> List[Activity]:
        """Generate all 4 time-of-day activities for a date.

        Per spec §10.4: pre-compute at 06:00 for the whole day.
        Deterministic per (date, character_id).

        Args:
            soul: SoulSpec object with character_id attribute.
            user_id: The user UUID.
            target_date: The date to generate activities for.
            recent_activity_ids: Pool IDs used in the last 3 days.

        Returns:
            List of 4 Activity objects (one per time_of_day).
        """
        character_id = getattr(soul, "character_id", None)
        if not character_id:
            raise ValueError("Soul spec missing character_id")

        activities: List[Activity] = []
        used_in_batch: Set[str] = set(recent_activity_ids or [])

        for tod in ["morning", "afternoon", "evening", "night"]:
            hour = (
                self.TIME_WINDOWS[tod].start
                if tod in self.TIME_WINDOWS
                else 0
            )
            base_time = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour=hour,
            )
            activity = self.select(
                soul=soul,
                user_id=user_id,
                current_time=base_time,
                recent_activity_ids=used_in_batch,
            )
            activities.append(activity)
            used_in_batch.add(activity.pool_id)

        return activities

    def get_pool_size(self, character_id: str) -> Dict[str, int]:
        """Return pool sizes indexed by 'day_type:time_of_day' for debugging.

        Args:
            character_id: Character identifier.

        Returns:
            Dict mapping "weekday:morning" → count, etc.
        """
        pool = self._load_pool(character_id)
        sizes: Dict[str, int] = {}
        for day_type in ["weekday", "weekend"]:
            for tod in ["morning", "afternoon", "evening", "night"]:
                entries = pool.get(day_type, {}).get(tod, [])
                sizes[f"{day_type}:{tod}"] = len(entries)
        return sizes

    # ── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _determine_time_of_day(dt: datetime) -> TimeOfDay:
        """Map an hour to a time_of_day slot.

        morning   (06–11)
        afternoon (12–17)
        evening   (18–21)
        night     (22–05)
        """
        hour = dt.hour
        if hour in ActivityGenerator.NIGHT_EARLY or hour >= 22:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:  # 18–21
            return "evening"

    @staticmethod
    def _determine_day_type(dt: datetime) -> DayType:
        """Map a datetime to weekday/weekend."""
        return "weekend" if dt.weekday() >= 5 else "weekday"

    @staticmethod
    def _make_seed(user_id: UUID, character_id: str, dt: datetime) -> int:
        """Create a deterministic seed from (user_id, character_id, hour)."""
        key = f"{user_id}:{character_id}:{dt.strftime('%Y-%m-%d-%H')}"
        digest = hashlib.sha256(key.encode()).digest()
        return int.from_bytes(digest[:8], "big")

    def _load_pool(self, character_id: str) -> Dict[str, Dict[str, List[_PoolEntry]]]:
        """Load and cache a character's activity pool from YAML.

        Returns:
            Nested dict: {day_type: {time_of_day: [PoolEntry, ...]}}
        """
        if character_id in self._pools:
            return self._pools[character_id]

        yaml_path = self._pool_dir / f"{character_id}.yaml"
        if not yaml_path.exists():
            raise ValueError(
                f"Activity pool not found for character_id={character_id} "
                f"at {yaml_path}"
            )

        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        pool: Dict[str, Dict[str, List[_PoolEntry]]] = {}

        for day_type in ("weekday", "weekend"):
            day_data = raw.get(day_type, {})
            pool[day_type] = {}
            for tod in ("morning", "afternoon", "evening", "night"):
                entries = day_data.get(tod, [])
                parsed = []
                for entry in entries:
                    parsed.append(_PoolEntry(
                        id=entry.get("id", ""),
                        description=entry.get("description", ""),
                        duration=entry.get("duration", "short"),
                        interruptible=entry.get("interruptible", True),
                        mood_modifier=entry.get("mood_modifier", {}),
                        allowed_stages=entry.get("allowed_stages", []),
                        share_eligible=entry.get("share_eligible", False),
                        share_template=entry.get("share_template", ""),
                    ))
                pool[day_type][tod] = parsed

        self._pools[character_id] = pool
        return pool
