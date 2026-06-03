"""
Emotion State Machine per SS03 §3 and §4.

Handles:
- State transitions based on triggers
- Inertia application (INV-E-1)
- VAD recomputation from active_stack + mood
- Stack management (INV-E-2: max 5 concurrent)
- Contagion from user emotion

Author: 心屿团队
"""

from __future__ import annotations

from typing import Any, Dict, List

from heart.infra.invariants import invariant

# Ensure invariant predicates are registered before decorator evaluation.
import heart.infra.invariant_predicates  # noqa: F401, E402 isort:skip


# Constants per §2.2
MAX_CONCURRENT_EMOTIONS = 5


class EmotionStateMachine:
    """
    Core state transition logic for emotion state.

    INV-E-1: ∀ emotion transition, |Δvalence| ≤ inertia_cap × Δt
    INV-E-2: ∀ active_emotion_stack S, |S| ≤ MAX_CONCURRENT_EMOTIONS
    INV-E-3: ∀ emotion e, e.intensity ∈ [0, 1]
    """

    def __init__(self, emotion_vad_map: Dict[str, Dict[str, float]]):
        """
        Args:
            emotion_vad_map: Mapping from emotion name to VAD values
                             (from emotion_lexicon.yaml)
        """
        self.emotion_vad = emotion_vad_map

    @invariant("inv-e-3.vad-range")
    @invariant("inv-e-2.stack-limit")
    def transition(
        self,
        current_state: Dict[str, Any],
        triggers: List[Dict[str, Any]],
        contagion_delta: Dict[str, float],
        inertia_profile: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Apply state transition given triggers and contagion.

        Args:
            current_state: Current EmotionState (dict representation)
            triggers: List of detected triggers from TriggerDetector
            contagion_delta: VAD delta from user emotion contagion
            inertia_profile: Inertia constraints from Soul
                {
                    "max_valence_change_per_turn": float,
                    "max_arousal_change_per_turn": float,
                    "max_dominance_change_per_turn": float,
                }

        Returns:
            Updated EmotionState (dict)

        Flow per §3.4:
        1. Apply triggers → update active_stack
        2. Compute target VAD from stack
        3. Apply contagion delta
        4. Apply inertia constraints
        5. Blend with mood baseline
        """
        # Copy current state
        new_state = current_state.copy()

        # 1. Apply triggers to active_stack
        self._apply_triggers_to_stack(new_state, triggers)

        # 2. Compute target VAD from active_stack
        stack_vad = self._compute_stack_vad(new_state["active_stack"])

        # 3. Add contagion delta
        target_vad = {
            "valence": stack_vad["valence"] + contagion_delta.get("valence", 0),
            "arousal": stack_vad["arousal"] + contagion_delta.get("arousal", 0),
            "dominance": stack_vad["dominance"] + contagion_delta.get("dominance", 0),
        }

        # 4. Apply inertia constraints
        current_vad = {
            "valence": new_state["vad_valence"],
            "arousal": new_state["vad_arousal"],
            "dominance": new_state["vad_dominance"],
        }

        new_vad = self._apply_inertia(current_vad, target_vad, inertia_profile)

        # 5. Blend with mood baseline (per §10.3 formula)
        mood = new_state["mood"]
        alpha, beta, gamma = 0.5, 0.3, 0.2  # stack, mood, prev weights

        final_vad = {
            "valence": (
                alpha * new_vad["valence"]
                + beta * mood["valence_baseline"]
                + gamma * current_vad["valence"]
            ),
            "arousal": (
                alpha * new_vad["arousal"]
                + beta * mood["arousal_baseline"]
                + gamma * current_vad["arousal"]
            ),
            "dominance": (
                alpha * new_vad["dominance"]
                + beta * mood["dominance_baseline"]
                + gamma * current_vad["dominance"]
            ),
        }

        # Clamp to valid ranges
        final_vad["valence"] = max(-1.0, min(1.0, final_vad["valence"]))
        final_vad["arousal"] = max(0.0, min(1.0, final_vad["arousal"]))
        final_vad["dominance"] = max(0.0, min(1.0, final_vad["dominance"]))

        # Update state
        new_state["vad_valence"] = final_vad["valence"]
        new_state["vad_arousal"] = final_vad["arousal"]
        new_state["vad_dominance"] = final_vad["dominance"]

        new_state["vad_target_valence"] = target_vad["valence"]
        new_state["vad_target_arousal"] = target_vad["arousal"]
        new_state["vad_target_dominance"] = target_vad["dominance"]

        return new_state

    def _apply_triggers_to_stack(
        self,
        state: Dict[str, Any],
        triggers: List[Dict[str, Any]],
    ) -> None:
        """
        Apply detected triggers to active_stack.

        Modifies state["active_stack"] in place.

        Each trigger contains suggested_emotions with intensity_delta.
        If "is_new_or_reinforce" == "new", add to stack.
        If "reinforce", modify existing intensity.

        INV-E-2: Enforce max 5 concurrent emotions.
        """
        active_stack = state["active_stack"]

        for trigger in triggers:
            for suggestion in trigger.get("suggested_emotions", []):
                emotion_name = suggestion["emotion"]
                intensity_delta = suggestion["intensity_delta"]
                is_new = suggestion["is_new_or_reinforce"] == "new"

                # Find existing emotion in stack
                existing = None
                for entry in active_stack:
                    if entry["emotion"] == emotion_name:
                        existing = entry
                        break

                if existing:
                    # Reinforce existing
                    new_intensity = existing["intensity"] + intensity_delta
                    existing["intensity"] = max(0.0, min(1.0, new_intensity))
                elif is_new:
                    # Add new emotion
                    if len(active_stack) >= MAX_CONCURRENT_EMOTIONS:
                        # Evict weakest emotion
                        active_stack.sort(key=lambda e: e["intensity"])
                        active_stack.pop(0)

                    # Get VAD for this emotion
                    vad = self.emotion_vad.get(emotion_name, {"v": 0, "a": 0.3, "d": 0.5})

                    active_stack.append(
                        {
                            "emotion": emotion_name,
                            "intensity": max(0.0, min(1.0, abs(intensity_delta))),
                            "source": "user_trigger",
                            "triggered_by": trigger["trigger_type"],
                            "started_at": None,  # Will be set by service
                            "vad_contribution": {
                                "valence": vad["v"],
                                "arousal": vad["a"],
                                "dominance": vad["d"],
                            },
                            "decay_state": "natural",
                            "repair_progress": 0.0,
                        }
                    )

        # Remove emotions with intensity < 0.05
        state["active_stack"] = [e for e in active_stack if e["intensity"] >= 0.05]

    def _compute_stack_vad(self, active_stack: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute aggregate VAD from active_stack.

        Formula per §10.3:
        VAD = Σ (emotion.vad × emotion.intensity) / Σ intensity
        """
        if not active_stack:
            return {"valence": 0.0, "arousal": 0.3, "dominance": 0.5}

        total_intensity = sum(e["intensity"] for e in active_stack) + 0.01
        weighted_vad = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0}

        for emotion in active_stack:
            weight = emotion["intensity"] / total_intensity
            vad = emotion["vad_contribution"]

            weighted_vad["valence"] += vad["valence"] * weight
            weighted_vad["arousal"] += vad["arousal"] * weight
            weighted_vad["dominance"] += vad["dominance"] * weight

        return weighted_vad

    def _apply_inertia(
        self,
        current_vad: Dict[str, float],
        target_vad: Dict[str, float],
        inertia_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Apply inertia constraints to VAD transition.

        INV-E-1: |Δvalence| ≤ inertia_cap × Δt (Δt=1 per turn)

        Formula per §10.3:
        new_vad = current_vad + clamp(target_vad - current_vad, -cap, +cap)
        """

        def clamp_delta(delta: float, cap: float) -> float:
            return max(-cap, min(cap, delta))

        max_v_change = inertia_profile.get("max_valence_change_per_turn", 0.15)
        max_a_change = inertia_profile.get("max_arousal_change_per_turn", 0.15)
        max_d_change = inertia_profile.get("max_dominance_change_per_turn", 0.15)

        return {
            "valence": current_vad["valence"]
            + clamp_delta(target_vad["valence"] - current_vad["valence"], max_v_change),
            "arousal": current_vad["arousal"]
            + clamp_delta(target_vad["arousal"] - current_vad["arousal"], max_a_change),
            "dominance": current_vad["dominance"]
            + clamp_delta(target_vad["dominance"] - current_vad["dominance"], max_d_change),
        }


# apply_contagion moved to contagion.py (Soul-aware version)
# Import it from there if needed:
# from heart.ss03_emotion.contagion import apply_contagion
