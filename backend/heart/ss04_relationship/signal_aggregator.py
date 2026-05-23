"""
Signal Aggregator for SS04 Relationship Phase Engine.

Handles signal aggregation per turn with anti-gaming deduplication.
Implements §3.5 signal aggregation + §3.2 Change 3 distinct-session logic.

Author: 心屿团队
Tuning: v1.1 (2026-05-21)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ..ss04_relationship.anti_gaming import (
    DistinctSessionTracker,
    SignalCooldownTracker,
    is_empty_message,
    DISTINCT_SESSION_EVENT_TYPES,
    COOLDOWN_WINDOW_MINUTES,
)
from ..ss04_relationship.stage_engine import Signal, SignalBatch


# ============================================================
# Session-Aware Signal Collector
# ============================================================


@dataclass
class SessionContext:
    """Context for a user session."""

    user_id: str
    character_id: str
    session_id: str
    started_at: datetime
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SignalAggregator:
    """
    Aggregates signals for a turn with distinct-session deduplication.

    Integrates with DistinctSessionTracker to ensure:
    - Events that require ≥N count only increment once per session
    - Cooldown weights applied to rapid repeated signals
    - Empty messages are filtered before counting

    Instance per user×character pair; stateful across turns within a session.
    """

    def __init__(
        self,
        user_id: str,
        character_id: str,
        session_tracker: DistinctSessionTracker,
        cooldown_tracker: SignalCooldownTracker,
    ):
        self.user_id = user_id
        self.character_id = character_id
        self.session_tracker = session_tracker
        self.cooldown_tracker = cooldown_tracker
        # Aggregation state per turn
        self._current_session_id: Optional[str] = None
        self._last_turn_at: Optional[datetime] = None

    def aggregate(
        self,
        raw_signals: list[dict[str, Any]],
        turn_timestamp: Optional[datetime] = None,
    ) -> SignalBatch:
        """
        Aggregate raw signals into a SignalBatch for stage evaluation.

        Steps:
        1. Filter empty messages
        2. Map raw signals to Signal objects
        3. Apply distinct-session dedup for count-type events
        4. Apply cooldown weight penalties
        5. Return SignalBatch

        Args:
            raw_signals: List of raw signal dicts, each with at least:
                - type: str
                - strength: float [0, 1]
                - metadata: dict (optional)
            turn_timestamp: When this turn occurred

        Returns:
            SignalBatch ready for stage engine evaluation
        """
        if turn_timestamp is None:
            turn_timestamp = datetime.now(timezone.utc)

        # Determine session boundary
        is_new_session = False
        if self._last_turn_at is None:
            is_new_session = True
        elif (turn_timestamp - self._last_turn_at) > timedelta(minutes=60):
            is_new_session = True

        self._last_turn_at = turn_timestamp

        # 1. Filter empty messages
        filtered = self._filter_signals(raw_signals)

        # 2. Convert to Signal objects
        all_signals = []
        for s in filtered:
            sig = Signal(
                type=s.get("type", "unknown"),
                strength=float(s.get("strength", 1.0)),
                metadata=s.get("metadata", {}),
            )
            all_signals.append(sig)

        # 3. Separate into positive/negative/events
        positive = []
        negative = []
        events = []

        for sig in all_signals:
            # Apply cooldown check
            is_repeat, weight_mult = self.cooldown_tracker.check_and_record(
                self.user_id, self.character_id, sig.type, turn_timestamp
            )
            if is_repeat:
                sig.strength *= weight_mult
                # Tag as dampened for observability
                sig.metadata["cooldown_dampened"] = True

            # Categorize by signal valence
            if sig.type.startswith("neg_") or sig.type in {
                "promise_broken", "vulnerability_mocked", "deception_detected",
                "pattern_neglect", "user_disappear_long",
            }:
                negative.append(sig)
            elif sig.type in DISTINCT_SESSION_EVENT_TYPES:
                # Check distinct-session
                is_first = self.session_tracker.record_event(
                    self.user_id, self.character_id, sig.type, turn_timestamp
                )
                if is_first:
                    events.append(sig)
                else:
                    # Already counted this session — skip or add as weak echo
                    weak_sig = Signal(
                        type=sig.type + "_echo",
                        strength=sig.strength * 0.1,
                        metadata={"original_type": sig.type, "duplicate_in_session": True},
                    )
                    events.append(weak_sig)
            elif sig.type in {
                "promise_kept", "vulnerability_honored", "consistent_presence_milestone",
                "sacred_disclosure_acknowledged", "memory_recall_confirmed",
                "repair_completed", "user_remembers_detail",
                "shared_vulnerability", "anniversary_acknowledged",
                "successful_repair", "user_honors_vulnerability",
                "compliment_received", "daily_check_in_completed",
                "first_iloveyou",
            }:
                positive.append(sig)
            else:
                # Unknown type — default to neutral/events
                sig.metadata["uncategorized"] = True
                events.append(sig)

        return SignalBatch(positive=positive, negative=negative, events=events)

    def get_session_counts(self) -> dict[str, int]:
        """Get current distinct-session counters for observability."""
        return self.session_tracker.count_distinct_across_types(
            self.user_id,
            self.character_id,
            list(DISTINCT_SESSION_EVENT_TYPES),
        )

    def get_cooldown_violations(self, signal_types: list[str]) -> int:
        """Get current cooldown violation count."""
        return self.cooldown_tracker.count_violations(
            self.user_id, self.character_id, signal_types
        )

    def reset(self) -> None:
        """Reset aggregation state (e.g., after stage transition)."""
        self.session_tracker.reset(self.user_id, self.character_id)
        self.cooldown_tracker.reset(self.user_id, self.character_id)
        self._current_session_id = None
        self._last_turn_at = None

    # ─── Internal helpers ────────────────────────────────────

    @staticmethod
    def _filter_signals(raw_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Filter out empty messages from raw signals.

        A signal is filtered if its message text meets empty-message criteria.
        """
        filtered = []
        for s in raw_signals:
            text = s.get("metadata", {}).get("text", "")
            if text and is_empty_message(str(text)):
                # Skip empty messages — they don't count
                continue
            filtered.append(s)
        return filtered


# ============================================================
# Factory function
# ============================================================


def create_signal_aggregator(
    user_id: str,
    character_id: str,
    session_tracker: Optional[DistinctSessionTracker] = None,
    cooldown_tracker: Optional[SignalCooldownTracker] = None,
) -> SignalAggregator:
    """
    Create a SignalAggregator with default or provided trackers.

    Args:
        user_id: User identifier
        character_id: Character identifier
        session_tracker: Optional shared DistinctSessionTracker
        cooldown_tracker: Optional shared SignalCooldownTracker

    Returns:
        Configured SignalAggregator
    """
    if session_tracker is None:
        session_tracker = DistinctSessionTracker()
    if cooldown_tracker is None:
        cooldown_tracker = SignalCooldownTracker()
    return SignalAggregator(user_id, character_id, session_tracker, cooldown_tracker)
