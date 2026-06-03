"""
Emotion Service per SS03 §10.2 and §7.2.

Main orchestrator for emotion state management.
Single source of truth writer per RULE-W-E-1.

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

import yaml

from heart.ss03_emotion.contagion import apply_contagion
from heart.ss03_emotion.decay import DecayEngine, apply_decay_to_stack
from heart.ss03_emotion.repair import RepairEngine
from heart.ss03_emotion.state_machine import EmotionStateMachine
from heart.ss03_emotion.trigger_detector import TriggerDetector


class EmotionService:
    """
    Emotion Service - single source of truth for emotion state.

    RULE-W-E-1: All writes go through this service.
    RULE-W-E-2: Every write produces emotion_event audit log.
    RULE-W-E-3: Writes must apply inertia + Soul constraints.
    RULE-W-E-4: Cross user/character isolation strict.
    RULE-W-E-5: VAD writes go through stack/mood recomputation.

    Target latency: process_turn P95 < 30ms
    """

    def __init__(self, config_path: str = None):
        """
        Initialize EmotionService with lexicon and profiles.

        Args:
            config_path: Path to emotion_lexicon.yaml
                         Defaults to project config/emotion_lexicon.yaml
        """
        if config_path is None:
            # Default to project config directory
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "emotion_lexicon.yaml"

        # Load lexicon configuration
        with open(config_path, "r", encoding="utf-8") as f:
            self.lexicon = yaml.safe_load(f)

        # Initialize engines
        self.decay_engine = DecayEngine(self.lexicon.get("decay_profiles", {}))
        self.state_machine = EmotionStateMachine(self.lexicon.get("emotion_vad_map", {}))
        self.trigger_detector = TriggerDetector(self.lexicon)
        # RepairEngine will be initialized per-turn with soul config
        self.repair_engine: RepairEngine | None = None

        # TODO: Initialize database connections (Redis + PostgreSQL)
        # For now, use in-memory storage for development
        self._state_cache: Dict[tuple, Dict[str, Any]] = {}

    def get_current_state(
        self,
        user_id: UUID,
        character_id: str,
    ) -> Dict[str, Any]:
        """
        Get current emotion state for user × character.

        RULE-W-E-4: user_id filter enforced.

        Returns:
            EmotionState dict (matches models.EmotionState schema)
        """
        key = (str(user_id), character_id)

        if key not in self._state_cache:
            # Initialize default state
            self._state_cache[key] = self._create_default_state(user_id, character_id)

        return self._state_cache[key].copy()

    async def process_turn(
        self,
        user_id: UUID,
        character_id: str,
        user_message: str,
        turn_id: UUID,
        context: Dict[str, Any],
        soul_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a turn and update emotion state.

        This is the main entry point per §3.4 Runtime Flow.

        Args:
            user_id: User UUID
            character_id: Character identifier
            user_message: User's text input
            turn_id: Current turn UUID
            context: Turn context with:
                - days_since_last: float
                - hours_since_last: float
                - relationship_phase: str
                - user_emotion_vad: Dict (from fast encoder)
            soul_config: Soul spec configuration

        Returns:
            Updated EmotionState

        Flow per §3.4:
        1. Load current state
        2. Detect triggers + repair signals (< 20ms)
        3. Apply decay (< 5ms)
        4. Apply contagion (< 5ms)
        5. Apply triggers → state machine (< 10ms)
        6. Apply repair (< 5ms)
        7. Persist (Redis sync + PG async)
        """
        # 1. Load current state
        current_state = self.get_current_state(user_id, character_id)

        # 2a. Detect triggers
        trigger_context = {
            "turn_id": turn_id,
            "days_since_last": context.get("days_since_last", 0),
            "hours_since_last": context.get("hours_since_last", 0),
            "relationship_phase": context.get("relationship_phase", "stranger"),
            "prev_messages": context.get("prev_messages", []),
        }

        # Update trigger detector with soul config
        self.trigger_detector.soul = soul_config

        detected_triggers = self.trigger_detector.detect(user_message, trigger_context)

        # 2b. Detect repair signals (§3.4 step 2: Repair Mechanic Detector)
        # Initialize repair engine with soul config if not already done
        if self.repair_engine is None or self.repair_engine.soul_config != soul_config:
            self.repair_engine = RepairEngine(self.lexicon, soul_config)

        # Build repair detection context
        user_emotional_charge = context.get("user_emotion_vad", {}).get("valence", 0.0)
        repair_context = {
            "pending_repairs": current_state.get("pending_repairs", []),
            "recent_triggers": current_state.get("recent_triggers", []),
            "user_emotional_charge": user_emotional_charge,
            "relationship_phase": context.get("relationship_phase", "stranger"),
        }

        # Detect repair signal (async)
        repair_signal = await self.repair_engine.detect_repair_signal(
            user_message=user_message,
            user_id=user_id,
            character_id=character_id,
            turn_id=turn_id,
            context=repair_context,
        )

        # 3. Apply decay to active_stack
        hours_since_last = context.get("hours_since_last", 0)
        if hours_since_last > 0:
            current_state["active_stack"] = apply_decay_to_stack(
                active_stack=current_state["active_stack"],
                delta_t_hours=hours_since_last,
                decay_engine=self.decay_engine,
                current_local_time=datetime.now(timezone.utc),
            )

        # 4. Compute contagion delta
        user_emotion_vad = context.get(
            "user_emotion_vad", {"valence": 0, "arousal": 0.3, "dominance": 0.5}
        )
        relationship_phase = context.get("relationship_phase", "stranger")

        contagion_delta = apply_contagion(
            user_emotion_vad=user_emotion_vad,
            current_state=current_state,
            soul=soul_config,
            relationship_phase=relationship_phase,
        )

        # 5. Apply state machine transition
        inertia_profile = soul_config.get(
            "inertia_profile",
            {
                "max_valence_change_per_turn": 0.15,
                "max_arousal_change_per_turn": 0.15,
                "max_dominance_change_per_turn": 0.15,
            },
        )

        new_state = self.state_machine.transition(
            current_state=current_state,
            triggers=detected_triggers,
            contagion_delta=contagion_delta,
            inertia_profile=inertia_profile,
        )

        # 6. Apply repair (§3.4 step 7: Apply Repair)
        # Must happen BEFORE updating pending_repairs
        repair_outcome = self.repair_engine.apply_repair(
            signal=repair_signal,
            user_id=user_id,
            character_id=character_id,
            current_state=new_state,
            context=repair_context,
        )

        # Store repair outcome for downstream layers (Persona Composition)
        new_state["_last_repair_outcome"] = repair_outcome

        # Update metadata
        new_state["last_turn_processed_at"] = datetime.now(timezone.utc)
        new_state["updated_at"] = datetime.now(timezone.utc)

        # Add to VAD history
        new_state["recent_vad_history"].append(
            {
                "vad": {
                    "valence": new_state["vad_valence"],
                    "arousal": new_state["vad_arousal"],
                    "dominance": new_state["vad_dominance"],
                },
                "at": datetime.now(timezone.utc).isoformat(),
                "triggered_by": [t["trigger_type"] for t in detected_triggers],
            }
        )

        # Keep only recent 50 entries
        if len(new_state["recent_vad_history"]) > 50:
            new_state["recent_vad_history"] = new_state["recent_vad_history"][-50:]

        # Update recent_triggers
        new_state["recent_triggers"].extend(detected_triggers)
        # Keep only last 24h (simplified: keep last 20)
        if len(new_state["recent_triggers"]) > 20:
            new_state["recent_triggers"] = new_state["recent_triggers"][-20:]

        # Update pending_repairs for repair_required emotions
        self._update_pending_repairs(new_state)

        # 6. Persist (TODO: Redis + PostgreSQL)
        key = (str(user_id), character_id)
        self._state_cache[key] = new_state

        # TODO: Emit emotion_event audit log (RULE-W-E-2)

        return new_state

    def get_context_block(
        self,
        user_id: UUID,
        character_id: str,
    ) -> Dict[str, Any]:
        """
        Generate EmotionContextBlock for Persona Composer.

        Per §5.2 and §6.2.

        Target latency: P95 < 10ms

        Returns:
            EmotionContextBlock dict
        """
        state = self.get_current_state(user_id, character_id)

        # Sort emotions by intensity
        top_emotions = sorted(
            state["active_stack"],
            key=lambda e: e["intensity"],
            reverse=True,
        )[:3]

        # Generate emotion summary (template-based)
        emotion_summary = self._generate_emotion_summary(top_emotions, character_id)

        # Generate mood descriptor
        mood_descriptor = self._generate_mood_descriptor(state["mood"])

        # Generate energy descriptor
        energy_descriptor = self._generate_energy_descriptor(state["energy"])

        # Pending repairs summary
        pending_repairs_summary = None
        if state["pending_repairs"]:
            pending_repairs_summary = self._generate_repairs_summary(state["pending_repairs"])

        # Expression guidelines
        expression_guidelines = self._derive_expression_guidelines(state)

        return {
            "emotion_summary": emotion_summary,
            "vad": {
                "valence": state["vad_valence"],
                "arousal": state["vad_arousal"],
                "dominance": state["vad_dominance"],
            },
            "active_emotions": [
                {
                    "emotion": e["emotion"],
                    "intensity": e["intensity"],
                    "source_brief": e.get("triggered_by", "unknown"),
                }
                for e in top_emotions
            ],
            "mood_descriptor": mood_descriptor,
            "energy_descriptor": energy_descriptor,
            "pending_repairs_summary": pending_repairs_summary,
            "expression_guidelines": expression_guidelines,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "state_version": state.get("version", 1),
        }

    def apply_repair(
        self,
        user_id: UUID,
        character_id: str,
        repair_type: str,
        repair_impact: float,
    ) -> None:
        """
        Apply repair to repair_required emotions.

        Per §4.5 Repair Mechanic.

        Args:
            user_id: User UUID
            character_id: Character identifier
            repair_type: "apology" | "vulnerability" | "sustained_attention"
            repair_impact: Impact amount [0, 1]
        """
        state = self.get_current_state(user_id, character_id)

        for pending in state["pending_repairs"]:
            emotion_name = pending["emotion"]

            # Get repair impact for this emotion
            profile = self.decay_engine.profiles.get(emotion_name, {})
            if profile.get("decay_type") == "repair_required":
                impact_map = profile.get("repair_impact", {})
                base_impact = impact_map.get(repair_type, 0)

                # Update repair progress
                pending["repair_progress"] = min(
                    1.0,
                    pending["repair_progress"] + base_impact * repair_impact,
                )

        # Update in cache
        key = (str(user_id), character_id)
        self._state_cache[key] = state

    def _create_default_state(self, user_id: UUID, character_id: str) -> Dict[str, Any]:
        """Create default emotion state for new user × character pair."""
        return {
            "user_id": user_id,
            "character_id": character_id,
            "vad_valence": 0.0,
            "vad_arousal": 0.3,
            "vad_dominance": 0.5,
            "vad_target_valence": 0.0,
            "vad_target_arousal": 0.3,
            "vad_target_dominance": 0.5,
            "active_stack": [],
            "mood": {
                "valence_baseline": 0.0,
                "arousal_baseline": 0.3,
                "dominance_baseline": 0.5,
                "background_emotions": [],
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "energy": 0.6,
            "energy_baseline": 0.6,
            "recent_vad_history": [],
            "recent_triggers": [],
            "pending_repairs": [],
            "loaded_from_previous": False,
            "session_id": None,
            "last_turn_processed_at": None,
            "last_mood_drift_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "version": 1,
        }

    def _update_pending_repairs(self, state: Dict[str, Any]) -> None:
        """
        Update pending_repairs list based on active_stack.

        Preserves existing repair_progress from current pending_repairs.
        """
        # Build map of existing repair progress
        existing_repairs = {r["emotion"]: r for r in state.get("pending_repairs", [])}

        # Find repair_required emotions
        repair_required_emotions = []
        for emotion in state["active_stack"]:
            emotion_name = emotion["emotion"]
            profile = self.decay_engine.profiles.get(emotion_name, {})
            if profile.get("decay_type") == "repair_required":
                repair_required_emotions.append(emotion)

        # Update pending_repairs, preserving existing progress
        new_pending_repairs = []
        for e in repair_required_emotions:
            emotion_name = e["emotion"]
            existing = existing_repairs.get(emotion_name)

            new_pending_repairs.append(
                {
                    "emotion": emotion_name,
                    "intensity": e["intensity"],
                    "started_at": e.get("started_at"),
                    "cause": e.get("triggered_by", "unknown"),
                    # Preserve existing repair_progress and history
                    "repair_progress": existing["repair_progress"] if existing else 0.0,
                    "repair_history": existing.get("repair_history", []) if existing else [],
                }
            )

        state["pending_repairs"] = new_pending_repairs

    def _generate_emotion_summary(
        self,
        top_emotions: List[Dict[str, Any]],
        character_id: str,
    ) -> str:
        """Generate natural language emotion summary per §6.3."""
        if not top_emotions or all(e["intensity"] < 0.2 for e in top_emotions):
            return "你的情绪相对平静。"

        primary = top_emotions[0]
        primary_name = primary["emotion"]

        # Template-based phrases (simplified)
        phrases = {
            "aggrieved": "你心里有些不舒服。是那种说不出口的，'你怎么可以这样'的感觉。",
            "longing": "你最近常常在不经意时想到他。但你不会承认。",
            "fluttered": "你心里有一下小小的、不熟悉的颤动。你不愿承认这是什么。",
            "coldness": "你现在不太想说话。有一种安静的距离感。",
            "tenderness": "你感到一种温柔的关心。想靠近，但不会说出口。",
            "worry": "你有点担心。这种不安让你保持警觉。",
            "joy": "你心里有一点轻快的感觉。虽然不会表现得太明显。",
            "sadness": "你感到一种低落。不是激烈的悲伤，是安静的沉重。",
        }

        primary_phrase = phrases.get(primary_name, f"你感到{primary_name}。")

        if len(top_emotions) > 1 and top_emotions[1]["intensity"] > 0.2:
            secondary = top_emotions[1]
            secondary_name = secondary["emotion"]
            secondary_phrase = phrases.get(secondary_name, secondary_name)
            return f"{primary_phrase} 同时混合着{secondary_phrase}"

        return primary_phrase

    def _generate_mood_descriptor(self, mood: Dict[str, Any]) -> str:
        """Generate mood descriptor text."""
        v_baseline = mood["valence_baseline"]

        if v_baseline < -0.3:
            return "今天本来心情就不太好。"
        elif v_baseline > 0.3:
            return "今天心情还不错。"
        else:
            return "心情还算平静。"

    def _generate_energy_descriptor(self, energy: float) -> str:
        """Generate energy descriptor text."""
        if energy < 0.3:
            return "无精打采"
        elif energy < 0.5:
            return "微疲惫"
        elif energy < 0.7:
            return "状态正常"
        else:
            return "状态不错"

    def _generate_repairs_summary(self, pending_repairs: List[Dict[str, Any]]) -> str:
        """Generate pending repairs summary text."""
        if not pending_repairs:
            return None

        repair = pending_repairs[0]  # Focus on most significant
        emotion_name = repair["emotion"]

        if emotion_name == "aggrieved":
            return "她还有些没消化的委屈。今天如果他主动提起，她会接，但不会主动开口。"
        elif emotion_name == "coldness":
            return "她还保持着一点距离。需要时间慢慢靠近。"
        else:
            return f"她的{emotion_name}还在，需要修复。"

    def _derive_expression_guidelines(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Derive expression guidelines per §6.4."""
        active_stack = state["active_stack"]

        # Sentence length modifier
        modifiers_map = {
            "sadness": -1,
            "weariness": -1,
            "aggrieved": -1,
            "coldness": -2,
            "joy": 1,
            "excitement": 1,
            "fluttered": -1,
        }

        length_mod = sum(modifiers_map.get(e["emotion"], 0) * e["intensity"] for e in active_stack)

        # Use ellipsis for certain emotions
        use_ellipsis = any(
            e["emotion"] in ["aggrieved", "weariness", "fluttered", "longing"]
            and e["intensity"] > 0.3
            for e in active_stack
        )

        return {
            "sentence_length_modifier": length_mod,
            "use_ellipsis": use_ellipsis,
            "avoid_topics": [],
            "favor_topics": [],
        }
