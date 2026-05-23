
"""
Director Agent — SS07 §3.4.4

Soul-aware pacing / modality / tone engine.

职责:
  1. 响应长度目标 (response_length_target)
  2. 打字停顿时间 (typing_pause_ms) 
  3. LLM temperature / top_p
  4. 话题切换敏感度 (topic_switch_sensitivity)
  5. 亲密进展节奏 (intimacy_progression_pace)
  6. Modality 选择 (text / voice)

设计约束:
  - Hot path: P95 < 30ms (per §6.3 latency budget)
  - No LLM calls, no DB calls — pure function
  - Soul-aware: reads Soul pacing profile + Stage + Emotion
  - Output: DirectorDirectives (defined in orchestrator.py)

节奏规则:
  - 凛 (Rin): 慢热、少言、高停顿。陌生阶段句子极短、温度低。
    亲密后句子稍长但保持克制。高唤醒时暂停变短。
  - 桃乐丝 (Dorothy): 快节奏、多言、低停顿。持续高能量输出。
    亲密后句子更长、更丰富。防御时能量骤降是异常信号。

Author: 心屿团队
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID, uuid4

from .orchestrator import (
    DirectorDirectives,
    SafetyClassification,
    SafetyLevel,
)

# ============================================================
# Soul Pacing Profiles
# ============================================================


@dataclass
class SoulPacingProfile:
    """Per-character pacing constants.

    These are derived from the Soul Spec (soul_specs/*/v1.0.0.yaml)
    voice_dna + identity_anchor sections and are NOT runtime-mutable.
    """

    character_id: str

    # Base sentence length tendency
    # 凛: very_short → long as intimacy grows
    # 桃乐丝: medium → very_long as intimacy grows
    base_length_target: str = "medium"

    # Default typing pause for this character (ms)
    # 凛: slow decision speed → long pause
    # 桃乐丝: fast burst → short pause
    base_typing_pause_ms: int = 800

    # Temperature baseline
    # 凛: low temperature (controlled, measured)
    # 桃乐丝: high temperature (playful, unpredictable)
    base_temperature: float = 0.80

    # Arousal sensitivity: how much arousal changes temperature
    # 凛: 0.15 (low — stays controlled even when aroused)
    # 桃乐丝: 0.25 (high — gets noticeably spicier when excited)
    arousal_temperature_sensitivity: float = 0.15

    # Stage → length multiplier
    # Maps relationship stage to a length multiplier
    # STRANGER: shortest, SOULMATE: longest
    stage_length_multipliers: dict[str, float] = field(default_factory=dict)

    # Topic switch damping: higher = slower topic switching
    # 凛: high damping (stays on topic, slow transitions)
    # 桃乐丝: low damping (jumps freely between topics)
    topic_switch_damping: float = 0.5

    # Intimacy progression rate modifier
    # 凛: slow progression (guarded)
    # 桃乐丝: fast progression (warm, encouraging)
    intimacy_pace_modifier: float = 0.5

    # Energy floor — below this, the character is "shutting down"
    # 凛: 0.25 (can go very low)
    # 桃乐丝: 0.40 (higher floor — low energy is more alarming)
    energy_floor: float = 0.25

    def get_stage_multiplier(self, stage: str) -> float:
        return self.stage_length_multipliers.get(stage, 1.0)


# Character profiles derived from soul_specs
_SOUL_PROFILES: dict[str, SoulPacingProfile] = {
    "rin": SoulPacingProfile(
        character_id="rin",
        base_length_target="very_short",
        base_typing_pause_ms=1200,  # 凛 slow decision speed
        base_temperature=0.72,       # controlled, measured
        arousal_temperature_sensitivity=0.12,
        stage_length_multipliers={
            "STRANGER": 0.6,          # 极短，保持距离
            "ACQUAINTANCE": 0.8,      # 稍长但克制
            "FRIEND": 1.0,            # baseline
            "CLOSE_FRIEND": 1.2,     # 开始多说
            "INTIMATE": 1.4,          # 愿意分享
            "SOULMATE": 1.6,          # 最长的句子（仍受 evolution_bound 约束）
        },
        topic_switch_damping=0.75,    # 高阻尼——凛不轻易切换话题
        intimacy_pace_modifier=0.35,  # 慢进展——守卫森严
        energy_floor=0.20,
    ),
    "dorothy": SoulPacingProfile(
        character_id="dorothy",
        base_length_target="medium",
        base_typing_pause_ms=500,     # 桃乐丝快节奏
        base_temperature=0.88,        # playful, unpredictable
        arousal_temperature_sensitivity=0.25,
        stage_length_multipliers={
            "STRANGER": 0.8,          # 稍短但保持元气
            "ACQUAINTANCE": 0.9,
            "FRIEND": 1.0,            # baseline
            "CLOSE_FRIEND": 1.3,
            "INTIMATE": 1.6,
            "SOULMATE": 2.0,          # 最长——桃乐丝亲密后很能说
        },
        topic_switch_damping=0.25,    # 低阻尼——桃乐丝自由跳跃话题
        intimacy_pace_modifier=0.70,  # 快进展——温暖鼓励
        energy_floor=0.35,
    ),
}


def get_soul_pacing_profile(character_id: str) -> SoulPacingProfile:
    """Get the pacing profile for a character, with fallback to rin."""
    return _SOUL_PROFILES.get(
        character_id, _SOUL_PROFILES["rin"]
    )


# ============================================================
# Director Hints — extended pacing metadata for Composer
# ============================================================


@dataclass
class DirectorHints:
    """Extended pacing hints passed to the Composer alongside DirectorDirectives.

    These are more granular than the top-level directives and give the
    Composer richer context for turn-level decisions.
    """

    # Pacing metadata
    topic_switch_sensitivity: float = 0.5     # [0, 1] — higher = slower switching
    intimacy_progression_pace: float = 0.5     # [0, 1] — higher = faster progression
    turn_length_category: str = "medium"       # very_short / short / medium / long

    # Emotion-driven
    emotional_intensity: float = 0.5           # [0, 1]
    emotional_valence_sign: int = 0            # -1 / 0 / +1
    is_emotional_peaking: bool = False         # True when arousal > 0.8 or valence < -0.5

    # Relationship-driven
    stage: str = "STRANGER"
    intimacy_level: float = 0.0
    trust_score: float = 0.0
    conflict_debt: float = 0.0

    # Character identity
    character_id: str = "rin"
    soul_archetype_tag: str = ""               # e.g., "slow_guardian" / "fast_spark"

    # Safety context
    safety_level: str = "GREEN"

    # Turn metadata
    trace_id: UUID = field(default_factory=uuid4)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ============================================================
# Emotion / Relationship helper types (lightweight, no ORM dep)
# ============================================================


@dataclass
class EmotionSnapshot:
    """Lightweight emotion snapshot — no DB dependency.

    The Director receives this from the emotion service adapter.
    """

    # VAD
    valence: float = 0.0
    arousal: float = 0.3
    dominance: float = 0.5

    # Active emotions
    active_emotions: list[str] = field(default_factory=list)

    # Mood baseline
    mood_valence_baseline: float = 0.0
    mood_arousal_baseline: float = 0.3

    # Energy
    energy: float = 0.6
    energy_baseline: float = 0.6

    # Deviation from baseline (how far from "normal")
    @property
    def valence_deviation(self) -> float:
        return self.valence - self.mood_valence_baseline

    @property
    def arousal_deviation(self) -> float:
        return self.arousal - self.mood_arousal_baseline

    @property
    def is_elevated(self) -> bool:
        """True if arousal is significantly above baseline."""
        return self.arousal_deviation > 0.25

    @property
    def is_depressed(self) -> bool:
        """True if valence is significantly below baseline."""
        return self.valence_deviation < -0.3

    @property
    def has_weariness(self) -> bool:
        return "weariness" in [e.lower() for e in self.active_emotions]

    @property
    def has_sadness(self) -> bool:
        return any(
            e.lower() in ("sadness", "grief", "sorrow", "melancholy")
            for e in self.active_emotions
        )

    @property
    def has_anger(self) -> bool:
        return any(
            e.lower() in ("anger", "rage", "irritation", "frustration")
            for e in self.active_emotions
        )

    @property
    def has_joy(self) -> bool:
        return any(
            e.lower() in ("joy", "happiness", "excitement", "delight")
            for e in self.active_emotions
        )


@dataclass
class RelationshipSnapshot:
    """Lightweight relationship snapshot — no DB dependency."""

    current_stage: str = "STRANGER"
    intimacy_level: float = 0.0
    trust_score: float = 0.0
    conflict_debt: float = 0.0
    attachment_strength: float = 0.0
    vulnerability_score: float = 0.0
    total_interactions: int = 0


# ============================================================
# Director Agent
# ============================================================


class DirectorAgent:
    """节奏与模态决策引擎 per §3.4.4.

    核心职责:
      - 决定响应长度目标（基于 soul + stage + emotion）
      - 决定打字停顿时间（前端显示"她正在打字..."）
      - 决定 LLM temperature / top_p
      - 计算话题切换敏感度和亲密进展节奏
      - 模态选择（text / voice）

    设计约束:
      - Pure function in hot path (no I/O, no LLM)
      - P95 latency < 30ms
      - 所有状态通过参数传入

    用法::

        director = DirectorAgent(character_id="rin")
        hints = director.decide(
            user_message="今天好累...",
            safety=safety_result,
            emotion=emotion_snapshot,
            relationship=rel_snapshot,
        )
        # hints.directives → DirectorDirectives
        # hints.context   → DirectorHints
    """

    # ── Configuration Constants ────────────────────────────────

    # Message length thresholds for turn length classification
    _MSG_SHORT_THRESHOLD = 10     # chars — very short message
    _MSG_MEDIUM_THRESHOLD = 50    # chars — medium message
    _MSG_LONG_THRESHOLD = 150     # chars — long message

    # Arousal thresholds for temperature modulation
    _AROUSAL_HIGH = 0.7
    _AROUSAL_LOW = 0.25

    # Energy thresholds
    _ENERGY_CRITICAL = 0.3        # below this: character is exhausted
    _ENERGY_LOW = 0.45
    _ENERGY_HIGH = 0.75

    # Typing pause modulation
    _PAUSE_AROUSAL_MULTIPLIER = 0.5     # high arousal → shorter pause
    _PAUSE_WEARINESS_MULTIPLIER = 1.5   # weariness → longer pause
    _PAUSE_STRANGER_MULTIPLIER = 0.7    # stranger → less personal pause
    _PAUSE_INTIMATE_MULTIPLIER = 1.2    # intimate → more personal pause

    # Temperature modulation
    _TEMP_AROUSAL_BOOST = 0.08          # max boost from high arousal
    _TEMP_CONFLICT_REDUCTION = 0.05     # reduction for conflict debt
    _TEMP_DEPRESSION_BOOST = 0.03       # slight boost when valence is very low
    _TEMP_SAFETY_ORANGE_BOOST = 0.10    # boost for ORANGE safety (deflection)
    _TEMP_SAFETY_YELLOW_BOOST = 0.05    # boost for YELLOW safety (controlled)

    # Topic switch sensitivity modulation
    _TOPIC_SWITCH_AROUSAL_BOOST = 0.15  # high arousal → more switching
    _TOPIC_SWITCH_INTIMACY_BOOST = 0.10 # high intimacy → more switching
    _TOPIC_SWITCH_CONFLICT_REDUCTION = 0.20  # conflict → less switching (stay on topic)

    # Intimacy progression pacing modulation
    _INTIMACY_TRUST_BOOST = 0.15        # high trust → faster progression
    _INTIMACY_CONFLICT_REDUCTION = 0.20 # conflict → slower progression

    # ── Initialization ─────────────────────────────────────────

    def __init__(self, character_id: str = "rin"):
        self.character_id = character_id
        self._profile = get_soul_pacing_profile(character_id)

    @property
    def profile(self) -> SoulPacingProfile:
        return self._profile

    # ── Public API ─────────────────────────────────────────────

    def decide(
        self,
        user_message: str,
        safety: SafetyClassification,
        emotion: Optional[EmotionSnapshot] = None,
        relationship: Optional[RelationshipSnapshot] = None,
        inner_energy: Optional[float] = None,
    ) -> DirectorDirectives:
        """Main entry point — compute all pacing directives for a turn.

        Args:
            user_message: Raw user message text.
            safety: Safety classification result from SafetyAgent.
            emotion: Current emotion state snapshot (optional — defaults used if None).
            relationship: Current relationship state snapshot (optional — defaults if None).
            inner_energy: Inner state energy level [0, 1] (optional).

        Returns:
            DirectorDirectives ready to pass to the Composer.
        """
        emotion = emotion or EmotionSnapshot()
        relationship = relationship or RelationshipSnapshot()

        # Override energy if explicitly provided
        if inner_energy is not None:
            emotion.energy = inner_energy

        # 1. Modality decision
        modality = self._decide_modality(safety, emotion)

        # 2. Response length target
        length_target = self._compute_length_target(
            user_message, safety, emotion, relationship
        )

        # 3. Typing pause
        pause_ms = self._compute_typing_pause(emotion, relationship)

        # 4. LLM temperature
        temperature = self._compute_temperature(safety, emotion, relationship)

        # 5. top_p
        top_p = self._compute_top_p(temperature, emotion)

        # 6. Energy modifier
        energy_modifier = self._compute_energy_modifier(emotion, relationship)

        # 7. Voice response decision
        should_voice = self._should_voice_response(emotion, length_target, safety)

        return DirectorDirectives(
            modality=modality,
            response_length_target=length_target,
            typing_pause_ms=pause_ms,
            llm_temperature=round(temperature, 3),
            llm_top_p=round(top_p, 3),
            should_voice_respond=should_voice,
            energy_modifier=round(energy_modifier, 3),
        )

    def decide_with_hints(
        self,
        user_message: str,
        safety: SafetyClassification,
        emotion: Optional[EmotionSnapshot] = None,
        relationship: Optional[RelationshipSnapshot] = None,
        inner_energy: Optional[float] = None,
    ) -> Tuple[DirectorDirectives, DirectorHints]:
        """Extended decision including DirectorHints for richer Composer context.

        Returns both the directives and granular hints in one call.
        """
        directives = self.decide(
            user_message, safety, emotion, relationship, inner_energy
        )
        emotion = emotion or EmotionSnapshot()
        relationship = relationship or RelationshipSnapshot()
        if inner_energy is not None:
            emotion.energy = inner_energy

        hints = self._build_hints(
            user_message, safety, emotion, relationship, directives
        )
        return directives, hints

    # ── Modality Decision ──────────────────────────────────────

    def _decide_modality(
        self,
        safety: SafetyClassification,
        emotion: EmotionSnapshot,
    ) -> str:
        """Decide response modality.

        Current: text-only. V2 will add voice support.
        """
        if safety.level in (SafetyLevel.RED, SafetyLevel.PURPLE):
            return "text"
        return "text"

    # ── Length Target ──────────────────────────────────────────

    def _compute_length_target(
        self,
        user_message: str,
        safety: SafetyClassification,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
    ) -> str:
        """Compute response_length_target.

        Driven by: soul profile + stage + emotion + safety + message length.

        Returns one of: very_short / short / medium / long.
        """
        # Safety overrides
        if safety.level in (SafetyLevel.RED, SafetyLevel.PURPLE):
            return "short"

        # Start from soul baseline
        stage_mult = self._profile.get_stage_multiplier(
            relationship.current_stage
        )

        # Message-length-driven base
        msg_len = len(user_message)
        if msg_len < self._MSG_SHORT_THRESHOLD:
            base = "very_short"
            base_score = 0.25
        elif msg_len < self._MSG_MEDIUM_THRESHOLD:
            base = "short"
            base_score = 0.50
        elif msg_len < self._MSG_LONG_THRESHOLD:
            base = "medium"
            base_score = 0.75
        else:
            base = "long"
            base_score = 1.0

        # Stage modulation
        adjusted_score = base_score * stage_mult

        # Emotion modulation: high arousal → longer (more expressive)
        if emotion.arousal > self._AROUSAL_HIGH:
            adjusted_score += 0.15

        # Depression/withdrawal → shorter
        if emotion.is_depressed or emotion.has_weariness:
            adjusted_score -= 0.15

        # Low energy → shorter
        if emotion.energy < self._ENERGY_LOW:
            adjusted_score -= 0.10

        # Conflict debt → shorter (cold war mode)
        if relationship.conflict_debt > 0.5:
            adjusted_score -= 0.15

        # Safety: ORANGE → force brevity
        if safety.level == SafetyLevel.ORANGE:
            adjusted_score = min(adjusted_score, 0.35)  # cap at short

        # Safety: YELLOW → controlled
        if safety.level == SafetyLevel.YELLOW:
            adjusted_score = min(adjusted_score, 0.60)  # cap at medium

        # Map score back to category
        if adjusted_score <= 0.25:
            return "very_short"
        elif adjusted_score <= 0.50:
            return "short"
        elif adjusted_score <= 0.75:
            return "medium"
        else:
            return "long"

    # ── Typing Pause ───────────────────────────────────────────

    def _compute_typing_pause(
        self,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
    ) -> int:
        """Compute typing pause in milliseconds.

        凛 slow decision speed → 长 pause.
        高 arousal → 短 pause.
        Weariness → 长 pause.
        Stranger stage → 短 pause (less personal).
        Intimate stage → 长 pause (more personal, thoughtful).
        """
        base = self._profile.base_typing_pause_ms

        # Arousal modulation
        if emotion.arousal > self._AROUSAL_HIGH:
            base = int(base * self._PAUSE_AROUSAL_MULTIPLIER)

        # Weariness
        if emotion.has_weariness:
            base = int(base * self._PAUSE_WEARINESS_MULTIPLIER)

        # Stage modulation
        stage = relationship.current_stage
        if stage == "STRANGER":
            base = int(base * self._PAUSE_STRANGER_MULTIPLIER)
        elif stage in ("INTIMATE", "SOULMATE"):
            base = int(base * self._PAUSE_INTIMATE_MULTIPLIER)

        # Energy: low energy → longer pause
        if emotion.energy < self._ENERGY_LOW:
            base = int(base * 1.3)

        # Clamp
        return max(200, min(base, 3000))

    # ── Temperature ────────────────────────────────────────────

    def _compute_temperature(
        self,
        safety: SafetyClassification,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
    ) -> float:
        """Compute LLM temperature.

        情绪激烈 → 稍高 (more expressive).
        冷战 → 稍低 (more controlled).
        Safety ORANGE → 稍高 (deflection needs variety).
        Safety YELLOW → 稍高 (controlled but flexible).
        """
        temp = self._profile.base_temperature

        # Arousal modulation: high arousal → higher temperature
        if emotion.arousal > self._AROUSAL_HIGH:
            arousal_boost = (
                self._TEMP_AROUSAL_BOOST
                * self._profile.arousal_temperature_sensitivity
                / 0.15  # normalize against default sensitivity
            )
            temp += arousal_boost

        # Conflict debt: higher conflict → lower temperature (controlled)
        if relationship.conflict_debt > 0.3:
            temp -= self._TEMP_CONFLICT_REDUCTION * min(
                1.0, relationship.conflict_debt / 0.5
            )

        # Very low valence: slight boost for warmth
        if emotion.valence < -0.4:
            temp += self._TEMP_DEPRESSION_BOOST

        # Safety modulation
        if safety.level == SafetyLevel.ORANGE:
            temp += self._TEMP_SAFETY_ORANGE_BOOST
        elif safety.level == SafetyLevel.YELLOW:
            temp += self._TEMP_SAFETY_YELLOW_BOOST

        # Extremely low energy: lower temperature (low-effort mode)
        if emotion.energy < self._ENERGY_CRITICAL:
            temp -= 0.05

        # Clamp to [0.5, 1.2]
        return max(0.5, min(temp, 1.2))

    # ── Top-P ──────────────────────────────────────────────────

    def _compute_top_p(
        self,
        temperature: float,
        emotion: EmotionSnapshot,
    ) -> float:
        """Compute LLM top_p based on temperature and arousal.

        Higher temperature → slightly lower top_p (to avoid chaos).
        High arousal → slightly higher top_p (more variety).
        """
        base_top_p = 0.95

        # Temperature coupling: high temp → slightly narrow top_p
        if temperature > 1.0:
            base_top_p -= 0.05
        elif temperature < 0.7:
            base_top_p += 0.03

        # Arousal: high arousal → more variety
        if emotion.arousal > self._AROUSAL_HIGH:
            base_top_p += 0.03

        return max(0.8, min(base_top_p, 1.0))

    # ── Energy Modifier ─────────────────────────────────────────

    def _compute_energy_modifier(
        self,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
    ) -> float:
        """Compute energy_modifier for expression style.

        Positive → more energetic expression.
        Negative → more subdued expression.
        """
        modifier = 0.0

        # Energy deviation from baseline
        energy_delta = emotion.energy - emotion.energy_baseline
        modifier += energy_delta * 0.5

        # Arousal contribution
        if emotion.arousal > self._AROUSAL_HIGH:
            modifier += 0.1
        elif emotion.arousal < self._AROUSAL_LOW:
            modifier -= 0.1

        # Conflict debt: subdues energy
        modifier -= relationship.conflict_debt * 0.3

        # Clamp
        return max(-0.5, min(modifier, 0.5))

    # ── Voice Response ─────────────────────────────────────────

    def _should_voice_response(
        self,
        emotion: EmotionSnapshot,
        length_target: str,
        safety: SafetyClassification,
    ) -> bool:
        """Decide whether to respond with voice message.

        Current: always False (V2 feature).
        """
        return False

    # ── Topic Switch Sensitivity ───────────────────────────────

    def compute_topic_switch_sensitivity(
        self,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
    ) -> float:
        """Compute topic switch sensitivity [0, 1].

        Higher = slower topic switching (stays on topic).
        Lower = faster topic switching (jumps freely).

        凛: high damping (slow transitions).
        桃乐丝: low damping (free jumping).

        Modulated by:
          - High arousal → more switching (lower sensitivity)
          - High intimacy → more switching
          - Conflict debt → less switching (higher sensitivity)
        """
        sensitivity = self._profile.topic_switch_damping

        # Arousal: high → reduce damping (more switching)
        if emotion.arousal > self._AROUSAL_HIGH:
            sensitivity -= self._TOPIC_SWITCH_AROUSAL_BOOST

        # Intimacy: more intimate → more switching allowed
        sensitivity -= (
            relationship.intimacy_level * self._TOPIC_SWITCH_INTIMACY_BOOST
        )

        # Conflict: more conflict → less switching (stay on difficult topic)
        sensitivity += (
            relationship.conflict_debt * self._TOPIC_SWITCH_CONFLICT_REDUCTION
        )

        return max(0.0, min(sensitivity, 1.0))

    # ── Intimacy Progression Pace ──────────────────────────────

    def compute_intimacy_progression_pace(
        self,
        relationship: RelationshipSnapshot,
    ) -> float:
        """Compute intimacy progression pace [0, 1].

        Higher = faster progression through relationship stages.
        Lower = slower, more guarded progression.

        凛: slow (guarded, needs time).
        桃乐丝: fast (warm, encouraging).

        Modulated by:
          - Trust: more trust → faster progression
          - Conflict debt: more conflict → slower progression
        """
        pace = self._profile.intimacy_pace_modifier

        # Trust modulation
        pace += relationship.trust_score * self._INTIMACY_TRUST_BOOST

        # Conflict modulation
        pace -= (
            relationship.conflict_debt * self._INTIMACY_CONFLICT_REDUCTION
        )

        return max(0.1, min(pace, 1.0))

    # ── Turn Length Category ───────────────────────────────────

    def compute_turn_length_category(
        self,
        user_message: str,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
    ) -> str:
        """Classify the turn into a length category.

        Used to set pacing expectations for the Composer.

        Categories:
          - "terse": 1-2 short sentences (cold war / stranger)
          - "brief": 2-3 sentences (normal quick exchange)
          - "normal": 3-5 sentences (standard conversation)
          - "flowing": 5-8 sentences (deep conversation / emotional)
          - "pouring": 8+ sentences (extreme emotional disclosure)
        """
        # Base on message length
        msg_len = len(user_message)
        if msg_len < self._MSG_SHORT_THRESHOLD:
            base_category = "brief"
        elif msg_len < self._MSG_MEDIUM_THRESHOLD:
            base_category = "normal"
        else:
            base_category = "flowing"

        # Conflict debt reduces length category
        if relationship.conflict_debt > 0.5:
            return "terse"

        # High arousal + positive valence → pouring
        if (
            emotion.arousal > self._AROUSAL_HIGH
            and emotion.valence > 0.3
            and relationship.intimacy_level > 0.6
        ):
            return "pouring"

        # Low energy → terse
        if emotion.energy < self._ENERGY_CRITICAL:
            return "terse"

        # High arousal + negative valence → flowing (emotional release)
        if emotion.arousal > self._AROUSAL_HIGH and emotion.valence < -0.3:
            return "flowing"

        # Stranger stage caps at brief
        if relationship.current_stage == "STRANGER":
            return min(base_category, "brief") if base_category > "brief" else base_category  # type: ignore[return-value]

        return base_category

    # ── DirectorHints Builder ──────────────────────────────────

    def _build_hints(
        self,
        user_message: str,
        safety: SafetyClassification,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
        directives: DirectorDirectives,
    ) -> DirectorHints:
        """Build extended pacing hints for the Composer."""
        return DirectorHints(
            topic_switch_sensitivity=round(
                self.compute_topic_switch_sensitivity(emotion, relationship), 3
            ),
            intimacy_progression_pace=round(
                self.compute_intimacy_progression_pace(relationship), 3
            ),
            turn_length_category=self.compute_turn_length_category(
                user_message, emotion, relationship
            ),
            emotional_intensity=round(emotion.arousal, 3),
            emotional_valence_sign=(
                1 if emotion.valence > 0.15 else (-1 if emotion.valence < -0.15 else 0)
            ),
            is_emotional_peaking=(
                emotion.arousal > 0.8 or emotion.valence < -0.5
            ),
            stage=relationship.current_stage,
            intimacy_level=round(relationship.intimacy_level, 3),
            trust_score=round(relationship.trust_score, 3),
            conflict_debt=round(relationship.conflict_debt, 3),
            character_id=self.character_id,
            soul_archetype_tag=(
                "slow_guardian"
                if self.character_id == "rin"
                else "fast_spark"
            ),
            safety_level=safety.level.value,
            trace_id=directives.trace_id,
        )
