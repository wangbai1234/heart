"""
Anti-Gaming Module for SS04 Relationship Phase Engine.

Implements §8.4 anti-gaming rules and §3.2 Change 3 tuning additions:
1. Distinct-session counter: all ≥N form events count once per session
2. Cooldown between same-type signals: 60 min window, repeat weight ×0.3
3. Empty-message filter: < 5 chars and no emotional keywords → excluded

Author: 心屿团队
Tuning: v1.1 (2026-05-21)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# ============================================================
# Configuration
# ============================================================


# Event types subject to distinct-session counting
DISTINCT_SESSION_EVENT_TYPES = {
    "vulnerability_disclosure",
    "emotional_resonance",
    "romantic_gesture",
    "character_reciprocation",
    "heart_flutter",
    "meaningful_disclosure",
}

# Session boundary in minutes (same session if within this window)
SESSION_BOUNDARY_MINUTES = 60

# Cooldown window for same-type signals
COOLDOWN_WINDOW_MINUTES = 60

# Weight multiplier for repeated signals within cooldown window
COOLDOWN_REPEAT_WEIGHT = 0.3

# Maximum cooldown violations before anti-gaming blocks
MAX_COOLDOWN_VIOLATIONS = 3

# Empty-message filter
EMPTY_MESSAGE_MIN_CHARS = 5

EMOTIONAL_KEYWORDS = [
    "想",
    "爱",
    "怕",
    "担心",
    "开心",
    "难过",
    "生气",
    "感动",
    "寂寞",
    "孤单",
    "喜欢",
    "讨厌",
    "希望",
    "害怕",
    "谢谢",
    "对不起",
    "❤",
    "😊",
    "😢",
    "🥺",
    "💕",
    "😭",
    "🥰",
    "😡",
]


# ============================================================
# Distinct-Session Tracker
# ============================================================


@dataclass
class SessionRecord:
    """Record of event occurrences within sessions."""

    # event_type → set of session IDs where this event occurred
    event_sessions: dict[str, set[str]] = field(default_factory=dict)
    # session_id → timestamp of first event in session
    session_starts: dict[str, datetime] = field(default_factory=dict)
    # Current session tracking
    current_session_id: Optional[str] = None
    session_start_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None


class DistinctSessionTracker:
    """
    Tracks distinct sessions for anti-gaming (v1.1 Change 3.1).

    Ensures that ≥N form event counts only increment once per session.
    A new session starts when there is a gap > SESSION_BOUNDARY_MINUTES
    since the last event.
    """

    def __init__(self, boundary_minutes: int = SESSION_BOUNDARY_MINUTES):
        self.boundary = timedelta(minutes=boundary_minutes)
        self.records: dict[str, SessionRecord] = {}  # keyed by (user_id, character_id)

    def _get_key(self, user_id: str, character_id: str) -> str:
        return f"{user_id}:{character_id}"

    def get_or_create_record(self, user_id: str, character_id: str) -> SessionRecord:
        """Get or create session record for user×character."""
        key = self._get_key(user_id, character_id)
        if key not in self.records:
            self.records[key] = SessionRecord()
        return self.records[key]

    def record_event(
        self,
        user_id: str,
        character_id: str,
        event_type: str,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Record an event and return whether it counts for this session.

        Returns:
            True if this is the first occurrence of event_type in current session
            (should increment counter), False if already counted.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        record = self.get_or_create_record(user_id, character_id)

        # Determine session — use session_start_at as reference
        if record.session_start_at is None:
            # First event ever
            session_id = f"session_{timestamp.timestamp():.0f}"
            record.current_session_id = session_id
            record.session_start_at = timestamp
            record.session_starts[session_id] = timestamp
        elif (timestamp - record.session_start_at) > self.boundary:
            # Session window expired → new session
            session_id = f"session_{timestamp.timestamp():.0f}"
            record.current_session_id = session_id
            record.session_start_at = timestamp
            record.session_starts[session_id] = timestamp
        else:
            # Still within same session window
            session_id = record.current_session_id

        record.last_event_at = timestamp

        # Initialize event_sessions for this type
        if event_type not in record.event_sessions:
            record.event_sessions[event_type] = set()

        # Check if already counted in this session
        is_first_in_session = session_id not in record.event_sessions[event_type]

        if is_first_in_session:
            record.event_sessions[event_type].add(session_id)

        return is_first_in_session

    def count_distinct_sessions(
        self,
        user_id: str,
        character_id: str,
        event_type: str,
    ) -> int:
        """
        Count distinct sessions where event_type occurred.

        Args:
            user_id: User identifier
            character_id: Character identifier
            event_type: Type of event to count

        Returns:
            Number of distinct sessions with this event type
        """
        record = self.get_or_create_record(user_id, character_id)
        sessions = record.event_sessions.get(event_type, set())
        return len(sessions)

    def count_distinct_across_types(
        self,
        user_id: str,
        character_id: str,
        event_types: list[str],
    ) -> dict[str, int]:
        """
        Count distinct sessions for multiple event types.

        Returns:
            Dict mapping event_type → distinct session count
        """
        record = self.get_or_create_record(user_id, character_id)
        return {et: len(record.event_sessions.get(et, set())) for et in event_types}

    def reset(self, user_id: str, character_id: str) -> None:
        """Reset tracking for a user×character pair."""
        key = self._get_key(user_id, character_id)
        self.records.pop(key, None)


# ============================================================
# Signal Cooldown Tracker
# ============================================================


class SignalCooldownTracker:
    """
    Tracks cooldown between same-type signals (v1.1 Change 3.2).

    Same signal_type within COOLDOWN_WINDOW_MINUTES → 2nd+ weight × 0.3.
    """

    def __init__(self, window_minutes: int = COOLDOWN_WINDOW_MINUTES):
        self.window = timedelta(minutes=window_minutes)
        self._last_triggered: dict[str, dict[str, datetime]] = defaultdict(dict)
        # keyed by (user_id, character_id) → signal_type → last_triggered_at

    def check_and_record(
        self,
        user_id: str,
        character_id: str,
        signal_type: str,
        timestamp: Optional[datetime] = None,
    ) -> tuple[bool, float]:
        """
        Check if signal is within cooldown and record it.

        Args:
            user_id: User identifier
            character_id: Character identifier
            signal_type: Type of signal
            timestamp: When the signal occurred

        Returns:
            (is_within_cooldown, effective_weight_multiplier)
            - is_within_cooldown: True if this is a repeat within window
            - effective_weight_multiplier: 1.0 for first, COOLDOWN_REPEAT_WEIGHT for repeats
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        key = f"{user_id}:{character_id}"
        last_time = self._last_triggered.get(key, {}).get(signal_type)

        if last_time is not None and (timestamp - last_time) < self.window:
            # Within cooldown — repeat signal
            self._last_triggered[key][signal_type] = timestamp
            return True, COOLDOWN_REPEAT_WEIGHT

        # First occurrence or outside window
        self._last_triggered[key][signal_type] = timestamp
        return False, 1.0

    def count_violations(
        self,
        user_id: str,
        character_id: str,
        signal_types: list[str],
        timestamp: Optional[datetime] = None,
    ) -> int:
        """
        Count how many of the given signal types are within cooldown.

        Useful for batch anti-gaming checks.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        key = f"{user_id}:{character_id}"
        violations = 0
        for st in signal_types:
            last_time = self._last_triggered.get(key, {}).get(st)
            if last_time is not None and (timestamp - last_time) < self.window:
                violations += 1
        return violations

    def reset(self, user_id: str, character_id: str) -> None:
        """Reset cooldown tracking."""
        key = f"{user_id}:{character_id}"
        self._last_triggered.pop(key, None)


# ============================================================
# Empty-Message Filter
# ============================================================


def is_empty_message(
    text: str,
    min_chars: int = EMPTY_MESSAGE_MIN_CHARS,
    keywords: Optional[list[str]] = None,
) -> bool:
    """
    Check if a message is below quality threshold (v1.1 Change 3.3).

    A message is "empty" if:
    - < min_chars characters (after stripping whitespace)
    - AND contains no emotional keywords

    Args:
        text: Message text to evaluate
        min_chars: Minimum character count (default 5)
        keywords: Optional custom keyword list

    Returns:
        True if message should be filtered out
    """
    if keywords is None:
        keywords = EMOTIONAL_KEYWORDS

    stripped = text.strip() if text else ""
    if len(stripped) >= min_chars:
        return False

    for kw in keywords:
        if kw in stripped:
            return False

    return True


def filter_empty_messages(messages: list[str]) -> list[str]:
    """
    Filter out empty/meaningless messages from a batch.

    Args:
        messages: List of message texts

    Returns:
        Filtered list with empty messages removed
    """
    return [m for m in messages if not is_empty_message(m)]


def count_empty_messages(messages: list[str]) -> int:
    """
    Count how many messages are empty.

    Args:
        messages: List of message texts

    Returns:
        Count of empty messages
    """
    return sum(1 for m in messages if is_empty_message(m))


# ============================================================
# Anti-Gaming Result
# ============================================================


@dataclass
class AntiGamingResult:
    """Result of anti-gaming check."""

    passed: bool
    reason: str = ""
    # Detailed metrics for observability
    distinct_session_counts: dict[str, int] = field(default_factory=dict)
    cooldown_violations: int = 0
    empty_messages_filtered: int = 0
    blocked_by: Optional[str] = None
