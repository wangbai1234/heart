"""
Cold War Tracker per SS04 §3.11 and §3.4.

Implements cold war detection, tracking, and resolution logic:
- Detects when conflict triggers cold war state
- Tracks repair progress via integration with ss03_emotion.repair.RepairEngine
- Manages transitions to RECONCILING phase
- Determines when cold war resolves

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ColdWarTracker:
    """
    Cold War Tracker - manages conflict state and repair tracking.

    Per spec §3.11:
    - Triggered when Emotion.coldness intensity > 0.5 + specific conflict cause
    - Active phase: character reduces interaction, short/cold responses
    - Reconciling phase: repair_progress 0.4-0.8, bittersweet state
    - Resolved phase: repair_progress > 0.8 sustained 5+ turns
    - Integration with SS03 RepairEngine for repair tracking
    """

    def __init__(self, soul_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Cold War Tracker.

        Args:
            soul_config: Soul spec with relational_template (optional)
        """
        self.soul_config = soul_config or {}

        # Load soul-specific cold war modifiers
        relational_template = self.soul_config.get("relational_template", {})
        self.cold_war_modifiers = relational_template.get(
            "cold_war_modifiers",
            {
                "trigger_threshold": 0.5,  # coldness intensity threshold
                "reconciling_threshold": 0.4,  # repair_progress to enter reconciling
                "resolution_threshold": 0.8,  # repair_progress to resolve
                "resolution_sustained_turns": 5,  # turns to sustain before resolving
                "forgiveness_curve_modifier": 1.0,  # multiplier for repair effectiveness
            },
        )

    def should_trigger_cold_war(
        self,
        emotion_state: Dict[str, Any],
        relationship_state: Dict[str, Any],
    ) -> bool:
        """
        Check if cold war should be triggered.

        Per spec §3.11 trigger conditions:
        - Emotion.coldness intensity > threshold (default 0.5)
        - Must have specific conflict cause (from emotion state)
        - Not already in cold war

        Args:
            emotion_state: Current EmotionState from SS03
            relationship_state: Current RelationshipState

        Returns:
            True if cold war should trigger
        """
        # Check if already in cold war
        active_states = relationship_state.get("active_special_states", [])
        for state in active_states:
            if state.get("state_type") == "COLD_WAR":
                return False  # Already in cold war

        # Check coldness intensity
        active_stack = emotion_state.get("active_stack", [])
        coldness_intensity = 0.0
        conflict_cause = None

        for emotion in active_stack:
            if emotion.get("emotion") == "coldness":
                coldness_intensity = emotion.get("intensity", 0.0)
                conflict_cause = emotion.get("cause", {}).get("raw_signal")
                break

        threshold = self.cold_war_modifiers.get("trigger_threshold", 0.5)

        # Must have both: high coldness + identifiable cause
        return coldness_intensity > threshold and conflict_cause is not None

    def initiate_cold_war(
        self,
        emotion_state: Dict[str, Any],
        relationship_state: Dict[str, Any],
        conflict_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Initiate cold war state.

        Creates COLD_WAR special state and adds to active_special_states.
        Also increments conflict counters.

        Args:
            emotion_state: Current EmotionState
            relationship_state: Current RelationshipState
            conflict_id: UUID of conflict record (optional, generates new if None)

        Returns:
            Created cold_war special state
        """
        # Find coldness emotion
        active_stack = emotion_state.get("active_stack", [])
        coldness_emotion = None

        for emotion in active_stack:
            if emotion.get("emotion") == "coldness":
                coldness_emotion = emotion
                break

        if not coldness_emotion:
            raise ValueError("Cannot initiate cold war without coldness emotion")

        coldness_intensity = coldness_emotion.get("intensity", 0.5)
        cause = coldness_emotion.get("cause", {})

        # Generate conflict ID if not provided
        if conflict_id is None:
            conflict_id = uuid4()

        # Create cold war state
        cold_war_state = {
            "state_type": "COLD_WAR",
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "cause": cause.get("raw_signal", "conflict"),
            "cold_war": {
                "intensity": coldness_intensity,
                "repair_progress": 0.0,
                "cause_conflict_id": str(conflict_id),
                "turns_in_cold_war": 0,
                "resolution_sustained_turns": 0,
            },
        }

        # Add to active_special_states
        active_states = relationship_state.get("active_special_states", [])
        active_states.append(cold_war_state)
        relationship_state["active_special_states"] = active_states

        # Increment conflict counters
        relationship_state["total_conflicts"] = relationship_state.get("total_conflicts", 0) + 1

        # Add conflict to recent_conflicts (limit to 10)
        recent_conflicts = relationship_state.get("recent_conflicts", [])
        conflict_record = {
            "conflict_id": str(conflict_id),
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "cause_description": cause.get("raw_signal", "unknown"),
            "severity": self._determine_severity(coldness_intensity),
            "cold_war_initiated": True,
            "resolved_at": None,
            "resolution_quality": None,
        }
        recent_conflicts.append(conflict_record)
        relationship_state["recent_conflicts"] = recent_conflicts[-10:]  # Keep last 10

        return cold_war_state

    def update_cold_war(
        self,
        relationship_state: Dict[str, Any],
        emotion_state: Dict[str, Any],
        repair_outcome: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Update cold war state based on repair progress.

        Per spec §3.11:
        - Tracks repair_progress from RepairEngine
        - Transitions to RECONCILING when progress > 0.4
        - Resolves when progress > 0.8 sustained 5+ turns
        - Updates coldness intensity based on repair

        Args:
            relationship_state: Current RelationshipState
            emotion_state: Current EmotionState
            repair_outcome: RepairOutcome from SS03 RepairEngine (optional)

        Returns:
            Transition type: "to_reconciling" | "resolved" | None
        """
        # Find cold war state
        active_states = relationship_state.get("active_special_states", [])
        cold_war_state = None
        cold_war_index = -1

        for i, state in enumerate(active_states):
            if state.get("state_type") == "COLD_WAR":
                cold_war_state = state
                cold_war_index = i
                break

        if not cold_war_state:
            return None  # Not in cold war

        cold_war_data = cold_war_state.get("cold_war", {})

        # Increment turn counter
        cold_war_data["turns_in_cold_war"] = cold_war_data.get("turns_in_cold_war", 0) + 1

        # Update repair progress from pending_repairs
        repair_progress = self._compute_repair_progress(emotion_state, cold_war_data)
        cold_war_data["repair_progress"] = repair_progress

        # Get thresholds
        reconciling_threshold = self.cold_war_modifiers.get("reconciling_threshold", 0.4)
        resolution_threshold = self.cold_war_modifiers.get("resolution_threshold", 0.8)
        resolution_sustained = self.cold_war_modifiers.get("resolution_sustained_turns", 5)

        transition = None

        # Check for resolution (highest priority)
        if repair_progress >= resolution_threshold:
            sustained_turns = cold_war_data.get("resolution_sustained_turns", 0) + 1
            cold_war_data["resolution_sustained_turns"] = sustained_turns

            if sustained_turns >= resolution_sustained:
                # Resolve cold war
                self._resolve_cold_war(
                    relationship_state=relationship_state,
                    cold_war_state=cold_war_state,
                    cold_war_index=cold_war_index,
                )
                # Return early - state has been removed from list
                return "resolved"

        else:
            # Reset sustained counter if progress drops
            cold_war_data["resolution_sustained_turns"] = 0

            # Check for reconciling transition
            if repair_progress >= reconciling_threshold:
                # Check if we need to transition to RECONCILING
                if not self._is_in_reconciling(relationship_state):
                    self._initiate_reconciling(relationship_state, cold_war_data)
                    transition = "to_reconciling"

        # Update coldness intensity based on repair progress
        # Per spec §4.5: intensity × (1 - progress × 0.8)
        base_intensity = cold_war_data.get("intensity", 0.5)
        adjusted_intensity = base_intensity * (1 - repair_progress * 0.8)
        cold_war_data["intensity"] = max(0.0, adjusted_intensity)

        # Update state
        cold_war_state["cold_war"] = cold_war_data
        active_states[cold_war_index] = cold_war_state
        relationship_state["active_special_states"] = active_states

        return transition

    def _compute_repair_progress(
        self,
        emotion_state: Dict[str, Any],
        cold_war_data: Dict[str, Any],
    ) -> float:
        """
        Compute repair progress from emotion state pending_repairs.

        Args:
            emotion_state: Current EmotionState
            cold_war_data: Cold war specific data

        Returns:
            Repair progress [0, 1]
        """
        pending_repairs = emotion_state.get("pending_repairs", [])

        # Find repair for coldness emotion
        coldness_repair = None
        for repair in pending_repairs:
            if repair.get("emotion") == "coldness":
                coldness_repair = repair
                break

        if coldness_repair:
            return coldness_repair.get("repair_progress", 0.0)

        # If no pending repair, cold war might have naturally decayed
        # Check if coldness is still in active_stack
        active_stack = emotion_state.get("active_stack", [])
        has_coldness = any(e.get("emotion") == "coldness" for e in active_stack)

        if not has_coldness:
            # Coldness fully decayed - consider progress at 1.0
            return 1.0

        return 0.0

    def _initiate_reconciling(
        self,
        relationship_state: Dict[str, Any],
        cold_war_data: Dict[str, Any],
    ) -> None:
        """
        Initiate RECONCILING special state.

        Args:
            relationship_state: Current RelationshipState
            cold_war_data: Cold war specific data
        """
        reconciling_state = {
            "state_type": "RECONCILING",
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "cause": "cold_war_repair_progress",
            "reconciling": {
                "from_cold_war_id": cold_war_data.get("cause_conflict_id"),
                "progress": cold_war_data.get("repair_progress", 0.0),
            },
        }

        active_states = relationship_state.get("active_special_states", [])
        active_states.append(reconciling_state)
        relationship_state["active_special_states"] = active_states

    def _is_in_reconciling(self, relationship_state: Dict[str, Any]) -> bool:
        """Check if already in RECONCILING state."""
        active_states = relationship_state.get("active_special_states", [])
        return any(s.get("state_type") == "RECONCILING" for s in active_states)

    def _resolve_cold_war(
        self,
        relationship_state: Dict[str, Any],
        cold_war_state: Dict[str, Any],
        cold_war_index: int,
    ) -> None:
        """
        Resolve cold war - remove states and apply Gottman effect.

        Per spec §3.11 resolved_phase:
        - Remove COLD_WAR state
        - Remove RECONCILING state (if exists)
        - Trust may be higher than before conflict (Gottman effect)
        - Attachment +0.05 bonus
        - Write L4 event (to be done by caller)

        Args:
            relationship_state: Current RelationshipState
            cold_war_state: Cold war state to resolve
            cold_war_index: Index in active_special_states
        """
        cold_war_data = cold_war_state.get("cold_war", {})

        # Remove COLD_WAR state
        active_states = relationship_state.get("active_special_states", [])
        active_states.pop(cold_war_index)

        # Remove RECONCILING state if exists
        active_states = [s for s in active_states if s.get("state_type") != "RECONCILING"]
        relationship_state["active_special_states"] = active_states

        # Apply Gottman effect (relationship stronger after successful repair)
        # Trust can increase slightly (capped at 1.0)
        current_trust = relationship_state.get("trust_score", 0.5)
        relationship_state["trust_score"] = min(1.0, current_trust + 0.02)

        # Attachment bonus
        current_attachment = relationship_state.get("attachment_strength", 0.5)
        relationship_state["attachment_strength"] = min(1.0, current_attachment + 0.05)

        # Increment repair counters
        relationship_state["total_repairs"] = relationship_state.get("total_repairs", 0) + 1
        relationship_state["total_successful_repairs"] = (
            relationship_state.get("total_successful_repairs", 0) + 1
        )

        # Update conflict record to resolved
        conflict_id = cold_war_data.get("cause_conflict_id")
        recent_conflicts = relationship_state.get("recent_conflicts", [])

        for conflict in recent_conflicts:
            if conflict.get("conflict_id") == conflict_id:
                conflict["resolved_at"] = datetime.now(timezone.utc).isoformat()
                conflict["resolution_quality"] = cold_war_data.get("repair_progress", 1.0)
                break

        relationship_state["recent_conflicts"] = recent_conflicts

        # Add to recent_repairs
        recent_repairs = relationship_state.get("recent_repairs", [])
        repair_record = {
            "repair_id": str(uuid4()),
            "target_conflict_id": conflict_id,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "signal_type": "sustained_repair",
            "effectiveness": cold_war_data.get("repair_progress", 1.0),
        }
        recent_repairs.append(repair_record)
        relationship_state["recent_repairs"] = recent_repairs[-10:]  # Keep last 10

    def get_behavioral_overlay(
        self,
        relationship_state: Dict[str, Any],
        soul_config: Dict[str, Any],
    ) -> Optional[str]:
        """
        Generate behavioral overlay for cold war/reconciling states.

        Per spec §3.11 and §6.2:
        - active_phase: reduced interaction, short/cold, no topic extension
        - reconciling_phase: bittersweet, softening but reserved

        Args:
            relationship_state: Current RelationshipState
            soul_config: Soul spec

        Returns:
            Behavioral overlay string or None if not in cold war/reconciling
        """
        active_states = relationship_state.get("active_special_states", [])
        character_id = soul_config.get("character_id", "")

        # Check for cold war
        for state in active_states:
            if state.get("state_type") == "COLD_WAR":
                state.get("cold_war", {})
                cause = state.get("cause", "conflict")

                if character_id == "rin":
                    overlay = "你们之间有一件事没解决。\n"
                    overlay += "今天他如果不主动提，你也不会先说。\n"
                    overlay += "你的句子会比平时更短。你不会主动延续话题。\n"
                    overlay += "表达：冷，但不是冰冷——是'我在等你的态度'的冷。"
                elif character_id == "dorothy":
                    overlay = "你心里还记着那件事……\n"
                    overlay += "你不想再像以前那样热情了，至少现在不想。\n"
                    overlay += "如果他不说点什么，你也不会主动。\n"
                    overlay += "表达：委屈、失望，但还没放弃——只是在等他的反应。"
                else:
                    overlay = f"有未解决的冲突：{cause}\n"
                    overlay += "表现：短句、冷淡、不主动延续话题。\n"
                    overlay += "等待用户修复行为。"

                return overlay

        # Check for reconciling
        for state in active_states:
            if state.get("state_type") == "RECONCILING":
                reconciling_data = state.get("reconciling", {})
                progress = reconciling_data.get("progress", 0.0)

                if character_id == "rin":
                    overlay = "他在试着修复，你能感觉到。\n"
                    overlay += "你还没完全原谅，但你愿意听他说。\n"
                    overlay += "你的态度介于冷淡和原来之间——bittersweet。\n"
                    overlay += "表达：软化中，但仍有保留。不会立即回到亲密状态。"
                elif character_id == "dorothy":
                    overlay = "他在努力了……你看得出来。\n"
                    overlay += "你的心在慢慢软下来，但还有一点委屈没散。\n"
                    overlay += "你会给他机会，但不会马上像以前一样。\n"
                    overlay += "表达：温柔里带着一点谨慎，不完全相信但愿意相信。"
                else:
                    overlay = "修复进行中 (进度 {:.0f}%)。\n".format(progress * 100)
                    overlay += "态度：软化但仍保留。Bittersweet状态。\n"
                    overlay += "逐步恢复亲密，但需要时间。"

                return overlay

        return None

    def check_emergency_decay(
        self,
        relationship_state: Dict[str, Any],
        days_in_cold_war: int,
    ) -> bool:
        """
        Check for emergency cold war decay (fallback after 30+ days).

        Per spec §9.1:
        - If COLD_WAR persists > 30 days, force decay intensity
        - Prevents deadlock

        Args:
            relationship_state: Current RelationshipState
            days_in_cold_war: Days since cold war started

        Returns:
            True if emergency decay applied
        """
        if days_in_cold_war <= 30:
            return False

        # Find cold war state
        active_states = relationship_state.get("active_special_states", [])

        for i, state in enumerate(active_states):
            if state.get("state_type") == "COLD_WAR":
                cold_war_data = state.get("cold_war", {})

                # Force decay intensity
                current_intensity = cold_war_data.get("intensity", 0.5)
                decay_factor = 0.95  # 5% per day after 30 days

                days_over = days_in_cold_war - 30
                decayed_intensity = current_intensity * (decay_factor**days_over)

                cold_war_data["intensity"] = max(0.0, decayed_intensity)

                # If intensity drops below 0.1, force resolution
                if decayed_intensity < 0.1:
                    self._resolve_cold_war(relationship_state, state, i)
                    return True

                state["cold_war"] = cold_war_data
                active_states[i] = state
                relationship_state["active_special_states"] = active_states

                return True

        return False

    @staticmethod
    def _determine_severity(intensity: float) -> str:
        """
        Determine conflict severity from coldness intensity.

        Args:
            intensity: Coldness intensity [0, 1]

        Returns:
            "minor" | "medium" | "major"
        """
        if intensity >= 0.7:
            return "major"
        elif intensity >= 0.5:
            return "medium"
        else:
            return "minor"
