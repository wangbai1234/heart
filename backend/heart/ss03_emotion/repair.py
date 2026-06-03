"""
Repair Mechanic Engine per SS03 §4.5 and design doc.

Implements three-layer cascade:
- Layer A: Heuristic gate (fast, anti-gaming)
- Layer B: Vulnerability detector (heuristic + optional LLM)
- Layer C: Cheap LLM sincerity check (boundary cases only)

All LLM calls via heart.infra.llm.get_model_router().call_cheap()
Cost cap: max 5 repair-LLM calls per user per day

Author: 心屿团队
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from heart.ss03_emotion.models import (
    RepairApplicationDetail,
    RepairOutcome,
    RepairOutcomeFlags,
    RepairSignal,
    RepairSignalComponent,
)


class RepairEngine:
    """
    Repair Mechanic Engine.

    Detects repair signals (apology, vulnerability, sustained_attention)
    and computes repair impact with anti-gaming enforcement.

    Per design doc:
    - G1: Spam "对不起" → repetition penalty + session cap
    - G2: Recidivism (re-offense after apology) → reversal
    - G3: Template-copy → n-gram similarity penalty
    - G4: Soul-mismatched repair → bespoke phrase matching
    - G5: Repair for nothing → return accepted=false
    - G6: Stacking multiple types → per-turn cap
    """

    def __init__(
        self,
        lexicon: Dict[str, Any],
        soul_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize RepairEngine.

        Args:
            lexicon: Emotion lexicon with apology keywords
            soul_config: Soul spec with repair_profile (optional)
        """
        self.lexicon = lexicon
        self.soul_config = soul_config or {}

        # Load repair keywords from lexicon
        self.apology_keywords = lexicon.get("repair_keywords", {}).get(
            "apology",
            [
                "对不起",
                "抱歉",
                "我错了",
                "不该",
                "原谅",
                "是我",
                "我的错",
                "怪我",
                "让你",
                "委屈",
                "难过",
            ],
        )

        self.vulnerability_keywords = lexicon.get("repair_keywords", {}).get(
            "vulnerability",
            [
                "累了",
                "疲惫",
                "压力",
                "难受",
                "撑不住",
                "失眠",
                "焦虑",
                "痛苦",
                "无助",
                "孤独",
                "害怕",
            ],
        )

        # Load soul repair profile (if available)
        self.soul_repair_profile = self._load_soul_repair_profile()

        # Session state cache (in production: Redis)
        # For now: in-memory Dict[user_id, SessionRepairState]
        self._session_cache: Dict[str, Dict[str, Any]] = {}

        # LLM call counter (per user per day)
        # In production: Redis with TTL
        self._llm_call_counter: Dict[str, Dict[str, int]] = {}

    def _load_soul_repair_profile(self) -> Dict[str, Any]:
        """
        Load soul-specific repair profile.

        Returns default if not present in soul_config.
        Per design doc §6.
        """
        relational_template = self.soul_config.get("relational_template", {})
        repair_profile = relational_template.get("repair_profile", {})

        # Default profile (balanced)
        default_profile = {
            "forgiveness_curve_gain": {
                "apology": 1.0,
                "vulnerability": 1.0,
                "sustained_attention": 1.0,
                "grand_gesture": 1.0,
            },
            "bespoke_repair_phrases": [],
            "cooldown_turns": 3,
            "recidivism_penalty_gain": 1.0,
            "session_progress_cap": 0.6,
        }

        # Merge with soul-specific overrides
        for key, value in default_profile.items():
            if key not in repair_profile:
                repair_profile[key] = value

        return repair_profile

    async def detect_repair_signal(
        self,
        user_message: str,
        user_id: UUID,
        character_id: str,
        turn_id: UUID,
        context: Dict[str, Any],
    ) -> Optional[RepairSignal]:
        """
        Detect repair signal from user message.

        Three-layer cascade per design doc §3:
        - Layer A: Heuristic (always on, <5ms)
        - Layer B: Vulnerability (heuristic gate + optional LLM)
        - Layer C: LLM sincerity (boundary cases only)

        Args:
            user_message: User's message
            user_id: User UUID
            character_id: Character ID
            turn_id: Current turn UUID
            context: Detection context with:
                - pending_repairs: List of pending repair emotions
                - recent_triggers: Recent trigger events
                - user_emotional_charge: User VAD score
                - relationship_phase: Current phase

        Returns:
            RepairSignal or None
        """
        components: List[RepairSignalComponent] = []

        # Get session state
        session_state = self._get_session_state(str(user_id), character_id)

        # Layer A: Apology detection (heuristic)
        apology_component = self._detect_apology_heuristic(
            user_message=user_message,
            session_state=session_state,
            context=context,
        )
        if apology_component:
            components.append(apology_component)

        # Layer B: Vulnerability detection
        vulnerability_component = await self._detect_vulnerability(
            user_message=user_message,
            user_id=user_id,
            context=context,
        )
        if vulnerability_component:
            components.append(vulnerability_component)

        # Layer C: LLM refinement for ambiguous cases
        # Only when:
        # 1. There's an apology component with strength in [0.2, 0.7]
        # 2. There's an active pending_repair
        # 3. Haven't hit LLM call cap
        if apology_component and 0.2 <= apology_component["strength"] < 0.7:
            pending_repairs = context.get("pending_repairs", [])
            if pending_repairs and self._can_use_llm(str(user_id)):
                llm_refined_strength = await self._llm_sincerity_check(
                    user_message=user_message,
                    user_id=user_id,
                    pending_repairs=pending_repairs,
                    base_strength=apology_component["strength"],
                )
                if llm_refined_strength is not None:
                    # Update strength with LLM refinement
                    apology_component["strength"] = llm_refined_strength
                    apology_component["reason_code"] += "_llm_refined"

        # Check for bespoke phrases (soul-specific)
        bespoke_component = self._detect_bespoke_phrases(user_message)
        if bespoke_component:
            components.append(bespoke_component)

        # No signals detected
        if not components:
            return None

        # Compute total strength (capped)
        total_strength = sum(c["strength"] for c in components)
        total_strength = min(total_strength, 1.0)

        has_bespoke = bespoke_component is not None

        # Update session state
        session_state["last_signal_at"] = datetime.now(timezone.utc).isoformat()
        session_state["signal_count_this_session"] += 1

        # Record apology in history for repetition tracking
        for component in components:
            if component["type"] == "apology":
                session_state["apology_history"].append(component["raw_signal"])
                # Keep only last 5
                session_state["apology_history"] = session_state["apology_history"][-5:]

        signal: RepairSignal = {
            "signal_id": str(uuid4()),
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "source_turn_id": str(turn_id),
            "components": components,
            "total_strength": total_strength,
            "has_bespoke_match": has_bespoke,
        }

        return signal

    def _detect_apology_heuristic(
        self,
        user_message: str,
        session_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[RepairSignalComponent]:
        """
        Layer A: Heuristic apology detection.

        Per design doc §3 Layer A:
        - Keyword match
        - Specificity score
        - Repetition penalty (anti-G1, G3)

        Returns:
            RepairSignalComponent or None
        """
        # 1. Keyword match
        has_keyword = any(kw in user_message for kw in self.apology_keywords)
        if not has_keyword:
            return None

        # 2. Specificity score
        specificity = 0.2  # Base score

        # Length check
        if len(user_message) >= 10:
            specificity += 0.2

        # Ownership markers
        ownership_markers = ["因为", "是我", "不该", "我的错", "怪我"]
        if any(marker in user_message for marker in ownership_markers):
            specificity += 0.3

        # Reference to concrete cause (cheap check: overlap with recent triggers)
        recent_triggers = context.get("recent_triggers", [])
        if recent_triggers:
            # Simple token overlap check
            trigger_tokens = set()
            for trigger in recent_triggers[-3:]:  # Last 3 triggers
                raw_signal = trigger.get("raw_signal", "")
                trigger_tokens.update(raw_signal)

            message_tokens = set(user_message)
            overlap = len(trigger_tokens & message_tokens)
            if overlap > 2:
                specificity += 0.3

        specificity = min(specificity, 1.0)

        # 3. Repetition penalty (anti-G1, G3)
        repetition_penalty = self._compute_repetition_penalty(
            user_message=user_message,
            session_state=session_state,
        )

        # Apply penalty
        final_strength = specificity * repetition_penalty

        # Determine reason code
        reason_code = "apology_detected"
        if repetition_penalty < 0.5:
            reason_code = "apology_repetition_penalty"
        elif specificity >= 0.7:
            reason_code = "specific_apology"
        else:
            reason_code = "generic_apology"

        component: RepairSignalComponent = {
            "type": "apology",
            "raw_signal": user_message[:80],
            "strength": final_strength,
            "reason_code": reason_code,
        }

        return component

    def _compute_repetition_penalty(
        self,
        user_message: str,
        session_state: Dict[str, Any],
    ) -> float:
        """
        Compute repetition penalty for apology.

        Anti-gaming rules per design doc §5.5:
        - 3-gram Jaccard similarity ≥ 0.6 vs last 3 apologies → ×0.1
        - Count of apologies in session: 2nd → ×0.5, 3rd+ → ×0.2

        Returns:
            Penalty multiplier [0.1, 1.0]
        """
        apology_history = session_state.get("apology_history", [])

        # Template similarity check (3-gram Jaccard)
        penalty = 1.0

        if apology_history:
            # Compute 3-grams
            current_trigrams = self._compute_trigrams(user_message)

            for past_apology in apology_history[-3:]:
                past_trigrams = self._compute_trigrams(past_apology)
                similarity = self._jaccard_similarity(current_trigrams, past_trigrams)

                if similarity >= 0.6:
                    penalty = min(penalty, 0.1)
                    break

        # Session count penalty
        apology_count = len(apology_history)
        if apology_count == 1:
            penalty *= 0.5
        elif apology_count >= 2:
            penalty *= 0.2

        return penalty

    @staticmethod
    def _compute_trigrams(text: str) -> set:
        """Compute 3-gram set from text."""
        text = text.lower()
        return {text[i : i + 3] for i in range(len(text) - 2)}

    @staticmethod
    def _jaccard_similarity(set1: set, set2: set) -> float:
        """Compute Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    async def _detect_vulnerability(
        self,
        user_message: str,
        user_id: UUID,
        context: Dict[str, Any],
    ) -> Optional[RepairSignalComponent]:
        """
        Layer B: Vulnerability detection.

        Per design doc §3 Layer B:
        - Heuristic gate (emotional_charge, length, topic)
        - Optional LLM Critic (only if gate passes)

        Returns:
            RepairSignalComponent or None
        """
        # Heuristic gate
        user_emotional_charge = context.get("user_emotional_charge", 0.0)

        # Gate 1: Negative emotional charge
        if user_emotional_charge >= -0.5:
            return None

        # Gate 2: Length and not pure apology
        if len(user_message) < 30:
            return None

        # Gate 3: Not pure apology topic
        apology_ratio = sum(1 for kw in self.apology_keywords if kw in user_message) / max(
            len(user_message), 1
        )
        if apology_ratio > 0.3:  # Too apology-heavy
            return None

        # Passed heuristic gates → could be vulnerability
        # For now: use heuristic strength based on vulnerability keywords
        # TODO: Optional LLM Critic call (when implemented)

        vulnerability_score = 0.0
        for kw in self.vulnerability_keywords:
            if kw in user_message:
                vulnerability_score += 0.2

        vulnerability_score = min(vulnerability_score, 1.0)

        if vulnerability_score < 0.3:
            return None

        component: RepairSignalComponent = {
            "type": "vulnerability",
            "raw_signal": user_message[:80],
            "strength": vulnerability_score,
            "reason_code": "vulnerability_heuristic",
        }

        return component

    def _detect_bespoke_phrases(
        self,
        user_message: str,
    ) -> Optional[RepairSignalComponent]:
        """
        Detect soul-specific bespoke repair phrases.

        Per design doc §6:
        - Rin: "我还在" / "我没走"
        - Dorothy: "你不用变" / "我喜欢现在的你"

        Returns:
            RepairSignalComponent or None
        """
        bespoke_phrases = self.soul_repair_profile.get("bespoke_repair_phrases", [])

        for phrase in bespoke_phrases:
            if phrase in user_message:
                component: RepairSignalComponent = {
                    "type": "bespoke_phrase",
                    "raw_signal": user_message[:80],
                    "strength": 0.8,  # High strength for soul-specific phrases
                    "reason_code": f"bespoke_{phrase}",
                }
                return component

        return None

    async def _llm_sincerity_check(
        self,
        user_message: str,
        user_id: UUID,
        pending_repairs: List[Dict[str, Any]],
        base_strength: float,
    ) -> Optional[float]:
        """
        Layer C: LLM-based sincerity refinement.

        Per design doc §3 Layer C:
        - Use critic-tier model (cheap)
        - One-shot prompt
        - Hard timeout 150ms
        - Cache-friendly (hash-based)

        Returns:
            Refined strength [0, 1] or None on failure/timeout
        """
        # Check LLM call cap
        if not self._can_use_llm(str(user_id)):
            return None

        # Prepare prompt
        repair = pending_repairs[0]  # Focus on primary
        emotion = repair["emotion"]
        intensity = repair["intensity"]
        cause = repair.get("cause", "unknown")

        messages = [
            {
                "role": "user",
                "content": f"""角色当前情绪：{emotion}（强度 {intensity:.2f}），起因："{cause}"

用户刚说："{user_message}"

评价道歉真诚度 0-1：
- 真诚 = 具体承担责任，非套话
- 不真诚 = 公式化 / 回避 / 无关话题

仅返回 JSON：{{"sincerity": <float>, "reason": "<简短理由>"}}""",
            }
        ]

        try:
            # Import here to avoid circular dependency
            from heart.infra.llm import get_model_router

            router = await get_model_router()

            # Make LLM call with timeout
            response = await router.call_cheap(
                messages=messages,
                temperature=0.0,
                max_tokens=100,
                json_mode=True,
                agent_name="repair_sincerity_check",
            )

            # Increment counter
            self._increment_llm_counter(str(user_id))

            # Parse response
            result = json.loads(response)
            sincerity = float(result.get("sincerity", base_strength))
            sincerity = max(0.0, min(1.0, sincerity))

            return sincerity

        except Exception:
            # On timeout or error, fall back to heuristic
            return None

    def _can_use_llm(self, user_id: str) -> bool:
        """
        Check if user can use LLM for repair (cost cap).

        Max 5 LLM calls per user per day.

        Args:
            user_id: User ID string

        Returns:
            True if under cap
        """
        today = datetime.now(timezone.utc).date().isoformat()

        if user_id not in self._llm_call_counter:
            self._llm_call_counter[user_id] = {}

        user_counter = self._llm_call_counter[user_id]

        # Clean old dates
        old_dates = [date for date in user_counter if date != today]
        for date in old_dates:
            del user_counter[date]

        # Check today's count
        today_count = user_counter.get(today, 0)
        return today_count < 5

    def _increment_llm_counter(self, user_id: str) -> None:
        """Increment LLM call counter for user."""
        today = datetime.now(timezone.utc).date().isoformat()

        if user_id not in self._llm_call_counter:
            self._llm_call_counter[user_id] = {}

        user_counter = self._llm_call_counter[user_id]
        user_counter[today] = user_counter.get(today, 0) + 1

    def _get_session_state(self, user_id: str, character_id: str) -> Dict[str, Any]:
        """
        Get session repair state for user × character.

        In production: Redis cache.
        For now: in-memory dict.
        """
        key = f"{user_id}:{character_id}"

        if key not in self._session_cache:
            self._session_cache[key] = {
                "signal_count_this_session": 0,
                "apology_history": [],
                "last_signal_at": None,
                "cumulative_progress_this_session": 0.0,
            }

        return self._session_cache[key]

    def apply_repair(
        self,
        signal: Optional[RepairSignal],
        user_id: UUID,
        character_id: str,
        current_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> RepairOutcome:
        """
        Apply repair signal to emotion state.

        Per design doc §7.2 and §5:
        - Check for pending_repairs
        - Apply impact with soul-specific gain
        - Check for recidivism (G2)
        - Enforce session caps (G6)
        - Update repair_progress

        Args:
            signal: RepairSignal (can be None)
            user_id: User UUID
            character_id: Character ID
            current_state: Current EmotionState
            context: Application context

        Returns:
            RepairOutcome
        """
        # Default outcome (no signal)
        if signal is None:
            return self._empty_outcome()

        pending_repairs = current_state.get("pending_repairs", [])

        # G5: No pending repairs → reject
        if not pending_repairs:
            return self._empty_outcome(
                signal_id=signal["signal_id"],
                narrative_hint="ignored",
            )

        # Get session state
        session_state = self._get_session_state(str(user_id), character_id)

        # Initialize flags
        flags: RepairOutcomeFlags = {
            "repetition_detected": False,
            "recidivism_reversal": False,
            "capped_by_session": False,
            "bespoke_match": signal["has_bespoke_match"],
        }

        # Compute total impact (before caps)
        total_impact = self._compute_total_impact(signal, flags)

        # Check session cap (G6, §5.2)
        session_cap = self.soul_repair_profile.get("session_progress_cap", 0.6)
        cumulative_progress = session_state.get("cumulative_progress_this_session", 0.0)

        if cumulative_progress >= session_cap:
            flags["capped_by_session"] = True
            return self._capped_outcome(signal["signal_id"], flags)

        # Apply to each pending repair
        applied_to: List[RepairApplicationDetail] = []

        for pending in pending_repairs:
            emotion = pending["emotion"]

            # Check for recidivism (G2)
            if self._check_recidivism(emotion, current_state, context):
                flags["recidivism_reversal"] = True
                # Roll back previous repair
                pending["repair_progress"] = max(0.0, pending["repair_progress"] - 0.2)
                continue

            # Compute impact for this emotion
            impact = self._compute_emotion_impact(
                emotion=emotion,
                signal=signal,
                total_impact=total_impact,
            )

            # Apply impact
            repair_progress_before = pending.get("repair_progress", 0.0)
            repair_progress_after = min(1.0, repair_progress_before + impact)

            # Update pending repair
            pending["repair_progress"] = repair_progress_after

            # Append to repair_history
            if "repair_history" not in pending:
                pending["repair_history"] = []

            pending["repair_history"].append(
                {
                    "turn_id": signal["source_turn_id"],
                    "signal_components": signal["components"],
                    "impact": impact,
                    "post_progress": repair_progress_after,
                    "at": signal["detected_at"],
                }
            )

            # Compute new intensity (per §4.5: intensity × (1 - progress × 0.8))
            initial_intensity = pending.get("intensity", 0.5)
            intensity_after = max(0.0, initial_intensity * (1 - repair_progress_after * 0.8))

            # Determine transition
            transitioned = None
            if repair_progress_after >= 0.8:
                transitioned = "fully_repaired"
            elif 0.4 <= repair_progress_after < 0.8:
                transitioned = "semi_repaired"

            applied_to.append(
                {
                    "emotion": emotion,
                    "impact": impact,
                    "repair_progress_before": repair_progress_before,
                    "repair_progress_after": repair_progress_after,
                    "intensity_after": intensity_after,
                    "transitioned": transitioned,
                }
            )

            # Update cumulative session progress
            session_state["cumulative_progress_this_session"] += impact

        # Compute residual score
        residual_score = 1.0
        if applied_to:
            max_progress = max(detail["repair_progress_after"] for detail in applied_to)
            residual_score = 1.0 - max_progress

        # Determine narrative hint
        narrative_hint = self._determine_narrative_hint(applied_to, flags)

        outcome: RepairOutcome = {
            "signal_id": signal["signal_id"],
            "accepted": len(applied_to) > 0,
            "partial": any(detail["transitioned"] == "semi_repaired" for detail in applied_to),
            "applied_to": applied_to,
            "residual_score": residual_score,
            "flags": flags,
            "narrative_hint": narrative_hint,
        }

        return outcome

    def _compute_total_impact(
        self,
        signal: RepairSignal,
        flags: RepairOutcomeFlags,
    ) -> float:
        """
        Compute total impact from signal components.

        Per design doc §5.1: per-turn cap = 0.5
        """
        total = 0.0

        for component in signal["components"]:
            component_type = component["type"]
            strength = component["strength"]

            # Apply soul-specific gain
            gain_map = self.soul_repair_profile.get("forgiveness_curve_gain", {})
            gain = gain_map.get(component_type, 1.0)

            total += strength * gain

        # Per-turn cap
        total = min(total, 0.5)

        # Check for repetition flag
        if any(c["reason_code"].startswith("apology_repetition") for c in signal["components"]):
            flags["repetition_detected"] = True

        return total

    def _compute_emotion_impact(
        self,
        emotion: str,
        signal: RepairSignal,
        total_impact: float,
    ) -> float:
        """
        Compute repair impact for specific emotion.

        Different repair types have different efficacy per emotion.
        Per SS03 §4.5 repair impact table.
        """
        # Impact map per emotion
        impact_map = {
            "aggrieved": {
                "apology": 0.3,
                "vulnerability": 0.2,
                "sustained_attention": 0.25,
                "bespoke_phrase": 0.4,
            },
            "coldness": {
                "apology": 0.3,
                "vulnerability": 0.2,
                "sustained_attention": 0.25,
                "bespoke_phrase": 0.4,
            },
            "jealousy": {
                "apology": 0.15,
                "vulnerability": 0.15,
                "sustained_attention": 0.2,
                "bespoke_phrase": 0.3,
            },
            "guilt": {
                "apology": 0.1,
                "vulnerability": 0.25,
                "sustained_attention": 0.2,
                "bespoke_phrase": 0.2,
            },
        }

        emotion_impacts = impact_map.get(emotion, {})

        # Get soul-specific gain
        gain_map = self.soul_repair_profile.get("forgiveness_curve_gain", {})

        # Sum component impacts with soul gain
        impact = 0.0
        for component in signal["components"]:
            component_type = component["type"]
            strength = component["strength"]

            base_impact = emotion_impacts.get(component_type, 0.1)
            soul_gain = gain_map.get(component_type, 1.0)

            impact += base_impact * strength * soul_gain

        # Cap impact to total_impact (prevents over-repair)
        impact = min(impact, total_impact)

        return impact

    def _check_recidivism(
        self,
        emotion: str,
        current_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        Check for recidivism (G2).

        If the offense that caused this pending_repair fired again
        within recidivism_window_turns (default 5) of last apology,
        treat as recidivism.

        Returns:
            True if recidivism detected
        """
        # Get recent triggers
        recent_triggers = current_state.get("recent_triggers", [])

        # Get pending repair for this emotion
        pending_repairs = current_state.get("pending_repairs", [])
        matching_repair = next((r for r in pending_repairs if r["emotion"] == emotion), None)

        if not matching_repair:
            return False

        # Get repair history
        repair_history = matching_repair.get("repair_history", [])
        if not repair_history:
            return False

        # Get last apology time
        last_apology = repair_history[-1]
        datetime.fromisoformat(last_apology["at"])

        # Check if offense re-occurred after last apology
        recidivism_window = 5  # turns

        # Get triggers after last apology (simplified: last N triggers)
        recent_trigger_types = [t.get("trigger_type") for t in recent_triggers[-recidivism_window:]]

        # Check if the original cause trigger re-occurred
        original_cause = matching_repair.get("cause", "")

        # Simple check: if original_cause trigger type appears in recent
        if original_cause in recent_trigger_types:
            return True

        return False

    def _determine_narrative_hint(
        self,
        applied_to: List[RepairApplicationDetail],
        flags: RepairOutcomeFlags,
    ) -> str:
        """
        Determine narrative hint for Persona Composition.

        Returns:
            "advanced" | "stalled" | "rejected" | "reversed" | "completed" | "ignored"
        """
        if flags["recidivism_reversal"]:
            return "reversed"

        if not applied_to:
            return "ignored"

        # Check for completion
        if any(detail["transitioned"] == "fully_repaired" for detail in applied_to):
            return "completed"

        # Check for advancement
        total_impact = sum(detail["impact"] for detail in applied_to)
        if total_impact >= 0.3:
            return "advanced"
        elif total_impact >= 0.1:
            return "advanced"
        else:
            return "stalled"

    def _empty_outcome(
        self,
        signal_id: Optional[str] = None,
        narrative_hint: str = "ignored",
    ) -> RepairOutcome:
        """Create empty repair outcome (no repair applied)."""
        return {
            "signal_id": signal_id,
            "accepted": False,
            "partial": False,
            "applied_to": [],
            "residual_score": 1.0,
            "flags": {
                "repetition_detected": False,
                "recidivism_reversal": False,
                "capped_by_session": False,
                "bespoke_match": False,
            },
            "narrative_hint": narrative_hint,
        }

    def _capped_outcome(
        self,
        signal_id: str,
        flags: RepairOutcomeFlags,
    ) -> RepairOutcome:
        """Create capped outcome (session cap hit)."""
        return {
            "signal_id": signal_id,
            "accepted": False,
            "partial": False,
            "applied_to": [],
            "residual_score": 1.0,
            "flags": flags,
            "narrative_hint": "stalled",
        }
