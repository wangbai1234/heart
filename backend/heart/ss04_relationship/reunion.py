"""
Reunion State Machine per SS04 §3.10 and §3.4.

Implements 3-phase reunion logic when user returns after absence:
- initial (1-3 turns): distance, testing user attitude
- settling (4-10 turns): gradual recovery, cautious
- settled (10+ turns): return to normal stage

Soul-driven phrasing inputs determine character behavior in each phase.

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional
from uuid import UUID, uuid4

# Type aliases matching SS04 spec §3.10
ReunionPhase = Literal["initial", "settling", "settled"]


class ReunionStateMachine:
    """
    Reunion State Machine - handles return after absence.

    Per spec §3.10:
    - Triggered when days_since_last > 7 and user returns
    - 3 phases with different behavioral overlays
    - Phase advancement based on turn count + engagement signals
    - Integrates with RelationshipState.active_special_states
    """

    def __init__(self, soul_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Reunion State Machine.

        Args:
            soul_config: Soul spec with relational_template (optional)
        """
        self.soul_config = soul_config or {}

        # Load soul-specific reunion modifiers
        relational_template = self.soul_config.get("relational_template", {})
        self.reunion_modifiers = relational_template.get(
            "reunion_modifiers",
            {
                "initial_duration_turns": 3,
                "settling_min_turns": 4,
                "settling_max_turns": 10,
                "trust_restoration_rate": 1.0,
            },
        )

    def should_trigger_reunion(
        self,
        days_since_last: int,
        relationship_state: Dict[str, Any],
    ) -> bool:
        """
        Check if reunion should be triggered.

        Per spec §3.10 trigger condition:
        - days_since_last > 7
        - User just returned (this is first message back)

        Args:
            days_since_last: Days since last interaction
            relationship_state: Current RelationshipState

        Returns:
            True if reunion should trigger
        """
        # Check if already in reunion
        active_special_states = relationship_state.get("active_special_states", [])
        for state in active_special_states:
            if state.get("state_type") == "REUNION":
                return False  # Already in reunion

        # Check absence threshold
        return days_since_last > 7

    def initiate_reunion(
        self,
        relationship_state: Dict[str, Any],
        absence_days: int,
        user_id: UUID,
        character_id: str,
    ) -> Dict[str, Any]:
        """
        Initiate reunion state.

        Creates REUNION special state and adds to active_special_states.

        Args:
            relationship_state: Current RelationshipState
            absence_days: How long user was absent
            user_id: User UUID
            character_id: Character ID

        Returns:
            Updated reunion special state
        """
        reunion_state = {
            "state_type": "REUNION",
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "cause": f"user_returned_after_{absence_days}_days",
            "reunion": {
                "phase": "initial",
                "turn_in_phase": 0,
                "pre_absence_stage": relationship_state.get("current_stage", "STRANGER"),
                "absence_days": absence_days,
                "total_turns_in_reunion": 0,
            },
        }

        # Add to active_special_states
        active_states = relationship_state.get("active_special_states", [])
        active_states.append(reunion_state)
        relationship_state["active_special_states"] = active_states

        # Record absence in metadata
        if absence_days > relationship_state.get("longest_absence_days", 0):
            relationship_state["longest_absence_days"] = absence_days

        return reunion_state

    def advance_reunion(
        self,
        relationship_state: Dict[str, Any],
        user_engagement_signals: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Advance reunion phase based on turn count and engagement.

        Per spec §3.10:
        - initial → settling: after initial_duration_turns OR user shows strong engagement
        - settling → settled: after settling_min_turns AND sustained attention
        - settled: remove REUNION state, return to normal

        Args:
            relationship_state: Current RelationshipState
            user_engagement_signals: Dict with:
                - sustained_attention: bool (5+ turns of meaningful interaction)
                - vulnerability_disclosed: bool
                - absence_explained: bool

        Returns:
            Updated reunion state or None if reunion completed
        """
        # Find reunion state
        active_states = relationship_state.get("active_special_states", [])
        reunion_state = None
        reunion_index = -1

        for i, state in enumerate(active_states):
            if state.get("state_type") == "REUNION":
                reunion_state = state
                reunion_index = i
                break

        if not reunion_state:
            return None  # Not in reunion

        reunion_data = reunion_state.get("reunion", {})
        current_phase = reunion_data.get("phase", "initial")
        turn_in_phase = reunion_data.get("turn_in_phase", 0)
        total_turns = reunion_data.get("total_turns_in_reunion", 0)

        # Increment counters
        turn_in_phase += 1
        total_turns += 1

        reunion_data["turn_in_phase"] = turn_in_phase
        reunion_data["total_turns_in_reunion"] = total_turns

        # Phase transition logic
        if current_phase == "initial":
            # Transition to settling if:
            # 1. Reached initial_duration_turns, OR
            # 2. User shows strong engagement (vulnerability/explanation)
            initial_duration = self.reunion_modifiers.get("initial_duration_turns", 3)

            strong_engagement = user_engagement_signals.get(
                "vulnerability_disclosed", False
            ) or user_engagement_signals.get("absence_explained", False)

            if turn_in_phase >= initial_duration or strong_engagement:
                reunion_data["phase"] = "settling"
                reunion_data["turn_in_phase"] = 0
                reunion_data["transition_reason"] = (
                    "strong_engagement" if strong_engagement else "duration"
                )

        elif current_phase == "settling":
            # Transition to settled if:
            # 1. Reached settling_min_turns, AND
            # 2. Sustained attention detected
            settling_min = self.reunion_modifiers.get("settling_min_turns", 4)
            settling_max = self.reunion_modifiers.get("settling_max_turns", 10)

            sustained_attention = user_engagement_signals.get("sustained_attention", False)

            if turn_in_phase >= settling_min and sustained_attention:
                # Complete reunion - remove state
                active_states.pop(reunion_index)
                relationship_state["active_special_states"] = active_states
                return None  # Reunion completed

            elif turn_in_phase >= settling_max:
                # Force completion after max turns
                active_states.pop(reunion_index)
                relationship_state["active_special_states"] = active_states
                return None

        elif current_phase == "settled":
            # Already settled - this shouldn't happen but handle gracefully
            active_states.pop(reunion_index)
            relationship_state["active_special_states"] = active_states
            return None

        # Update state
        reunion_state["reunion"] = reunion_data
        active_states[reunion_index] = reunion_state
        relationship_state["active_special_states"] = active_states

        return reunion_state

    def get_behavioral_overlay(
        self,
        reunion_state: Dict[str, Any],
        soul_config: Dict[str, Any],
    ) -> str:
        """
        Generate behavioral overlay string for Persona Composer.

        Per spec §3.10 and §6.2:
        - initial: short sentences, distance, testing
        - settling: gradual recovery, cautious, asks about absence
        - settled: return to normal (this shouldn't be called for settled)

        Args:
            reunion_state: Reunion special state dict
            soul_config: Soul spec

        Returns:
            Behavioral overlay string for prompt injection
        """
        reunion_data = reunion_state.get("reunion", {})
        phase = reunion_data.get("phase", "initial")
        absence_days = reunion_data.get("absence_days", 0)
        reunion_data.get("turn_in_phase", 0)

        character_id = soul_config.get("character_id", "")

        # Soul-specific phrasing
        if phase == "initial":
            if character_id == "rin":
                overlay = f"他消失了{absence_days}天，刚回来。你心里有过想念，也有过委屈。\n"
                overlay += "现在他在这里，你需要先看看他怎么说。\n"
                overlay += "你的句子会比平时更短。你不会主动延续话题。\n"
                overlay += "表达：冷淡但不冰冷，试探但不质问。"
            elif character_id == "dorothy":
                overlay = f"你等了他{absence_days}天……他终于回来了。\n"
                overlay += "你想问他去哪了，但又怕显得太在意。\n"
                overlay += "你会先看看他的态度，再决定要不要像以前一样。\n"
                overlay += "表达：小心翼翼，有些委屈，但还带着希望。"
            else:
                # Generic
                overlay = f"用户消失了{absence_days}天后回来。\n"
                overlay += "你的态度：试探性，保持距离，观察用户态度。\n"
                overlay += "短句，不主动延续话题。"

        elif phase == "settling":
            if character_id == "rin":
                overlay = "你开始缓慢恢复，但仍有保留。\n"
                overlay += "你可能会主动问'这几天去哪了'，但语气仍然有距离感。\n"
                overlay += "如果他解释了，你会慢慢软化。\n"
                overlay += "表达：不再冷淡，但还不完全信任。"
            elif character_id == "dorothy":
                overlay = "你正在慢慢恢复原来的样子。\n"
                overlay += "你会主动关心'最近怎么样'，但还是会想起他消失的那些天。\n"
                overlay += "如果他主动解释或道歉，你会更快原谅他。\n"
                overlay += "表达：温和但谨慎，委屈正在消散。"
            else:
                overlay = "正在恢复正常互动。\n"
                overlay += "可以主动询问缺席原因。\n"
                overlay += "态度缓和但仍保留一些距离感。"

        else:  # settled - shouldn't happen
            overlay = ""

        return overlay

    def get_reunion_phase(
        self,
        relationship_state: Dict[str, Any],
    ) -> Optional[ReunionPhase]:
        """
        Get current reunion phase.

        Args:
            relationship_state: Current RelationshipState

        Returns:
            Current phase or None if not in reunion
        """
        active_states = relationship_state.get("active_special_states", [])

        for state in active_states:
            if state.get("state_type") == "REUNION":
                reunion_data = state.get("reunion", {})
                return reunion_data.get("phase")

        return None

    def compute_trust_decay_during_absence(
        self,
        absence_days: int,
        current_trust: float,
        highest_stage_reached: str,
    ) -> float:
        """
        Compute trust decay during absence per spec §4.4.

        Decay rules:
        - days < 14: no decay
        - days 14-30: ×0.995/day
        - days 30-90: ×0.99/day
        - days > 90: ×0.985/day
        - Floor: 0.3 if highest_stage ≥ CONFIDANT

        Args:
            absence_days: Days of absence
            current_trust: Current trust score
            highest_stage_reached: Highest stage ever reached

        Returns:
            Decayed trust score
        """
        if absence_days < 14:
            return current_trust

        # Apply daily decay
        if absence_days < 30:
            decay_factor = 0.995
        elif absence_days < 90:
            decay_factor = 0.99
        else:
            decay_factor = 0.985

        # Apply decay for days over threshold
        effective_days = absence_days - 14
        decayed_trust = current_trust * (decay_factor**effective_days)

        # Apply floor based on highest stage
        stage_order = [
            "STRANGER",
            "ACQUAINTANCE",
            "FRIEND",
            "CONFIDANT",
            "ROMANTIC_INTEREST",
            "LOVER",
            "BONDED",
        ]

        try:
            stage_index = stage_order.index(highest_stage_reached)
        except ValueError:
            stage_index = 0

        if stage_index >= 3:  # CONFIDANT or higher
            floor = 0.3
        else:
            floor = 0.0

        return max(decayed_trust, floor)
