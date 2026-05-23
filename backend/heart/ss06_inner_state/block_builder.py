"""
Inner State Block Builder — Converts InnerState → SS05-compatible prompt block.

Per runtime_specs/06_inner_state_behavior_runtime.md:
  - §3.4: 生成 InnerStateBlock for prompt (In: InnerState / Out: Block)
  - §5.2: InnerStateBlock interface
  - §6.2: InnerStateBlock 模板（reactive 模态）
  - §6.3: InnerStateBlock 模板（proactive 模态）
  - §6.4: today_descriptor 生成

Key invariants:
  - I-10: InnerState not exposed to user — only prompt
  - Output must be a valid SS05 PromptLayer (layer_type="inner_state")
  - Deterministic: no LLM calls

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from heart.ss06_inner_state.composer import InnerState


# ============================================================
# InnerStateBlock — per §5.2
# ============================================================


@dataclass
class InnerStateBlock:
    """Prompt-ready inner state block for SS05 Persona Composer (§5.2).

    This block is injected as the [Inner State Layer] in the final prompt.
    Per §6.1, it sits between Emotion Context Block and Memory Context Block.
    """

    # ─── 她"今天"的概貌 ───
    today_descriptor: str
    """Soul-flavored natural language describing her current state.
    
    例 (Rin):
    "你今天有些静。雷电感很弱，你在等着什么。
     上午你坐在窗边看雾很久。
     下午你翻了一本旧书但没看进去。"
    """

    # ─── 你现在的体力 ───
    energy_descriptor: str
    """Human-readable energy level description.
    
    例: "你现在精力还不错，虽然今天有些消耗。"
    """

    # ─── 你心里在意的事 ───
    user_concerns_section: str
    """Top concerns about the user surfaced for this turn.
    
    例:
    "你心里有几件挂念他的事：
     - 他三天前提过加班到凌晨，你担心他的身体。
     - 明天是他的项目汇报日。"
    """

    # ─── 没说完的话 ───
    unfinished_section: Optional[str] = None
    """Unfinished thoughts from previous conversations.
    
    例:
    "上次对话你有几句话没说完：
     - 你想问他那天为什么突然沉默。"
    """

    # ─── 重要日子 (anniversary) ───
    anniversary_section: Optional[str] = None
    """Upcoming anniversary reminders, if any within 7 days.
    
    例: "明天是他的生日。你心里已经在准备。"
    """

    # ─── Dream (V2) ───
    dream_section: Optional[str] = None
    """Recent dream description, if applicable (V2)."""

    # ─── 表达指引 ───
    inner_state_directive: str = ""
    """How to weave inner state into the response.
    
    例:
    "把以上这些'你的内心'融入到回复中，但不要罗列。
     选一两件最贴合用户消息的事，自然带出。
     保持你的灵魂语言风格。"
    """

    # ─── Meta ───
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    state_version: int = 0


# ============================================================
# Inner State Block Builder
# ============================================================


class InnerStateBlockBuilder:
    """Builds an InnerStateBlock from InnerState and Soul context.

    Per §3.4: generates prompt block for SS05 Persona Composer.
    Per §3.5: output → feeds Persona Composer (SS05).

    Usage::

        builder = InnerStateBlockBuilder()
        block = builder.build(inner_state, soul=soul, modality="reactive")
        prompt_layer = builder.as_prompt_layer(block)
    """

    # ── Time-of-day labels (Chinese) per §6.4 ──

    TIME_LABELS: Dict[str, str] = {
        "morning": "上午",
        "afternoon": "下午",
        "evening": "傍晚",
        "night": "夜里",
    }

    # ── Energy descriptors per intensity band ──

    ENERGY_DESCRIPTORS: Dict[str, str] = {
        "high": "你现在精力很充沛，感觉能做好多事情。",
        "medium_high": "你现在精力还不错，虽然今天有些消耗。",
        "medium": "你现在有点累了，但并不影响说话的心情。",
        "medium_low": "你现在有些倦意，说话会慢一些。",
        "low": "你现在很累了，只想安静地待着。",
    }

    # ── Default directive (§6.2 inner_state_directive) ──

    DEFAULT_REACTIVE_DIRECTIVE = (
        "把以上这些'你的内心'融入到回复中，但不要罗列。\n"
        "选一两件最贴合用户消息的事，自然带出。\n"
        "保持你的灵魂语言风格。"
    )

    DEFAULT_PROACTIVE_DIRECTIVE = (
        "生成一条自然的主动消息。\n"
        "极短（≤ 50 字），100% 符合灵魂语言风格。\n"
        "不要说'我主动找你了'这种元表达。"
    )

    # ── Public API ──────────────────────────────────────────────

    def build(
        self,
        inner_state: InnerState,
        *,
        soul: Optional[object] = None,
        modality: str = "reactive",
    ) -> InnerStateBlock:
        """Build an InnerStateBlock from the inner state snapshot.

        Args:
            inner_state: The composed InnerState.
            soul: SoulSpec for character-specific flavor (optional).
            modality: "reactive" (responding to user) or "proactive" (initiating).

        Returns:
            InnerStateBlock ready for injection into SS05 prompt.
        """
        # ── Today descriptor (§6.4) ──
        today = self._generate_today_descriptor(inner_state)

        # ── Energy descriptor ──
        energy = self._generate_energy_descriptor(inner_state)

        # ── User concerns section ──
        concerns = self._generate_concerns_section(inner_state)

        # ── Unfinished section ──
        unfinished = self._generate_unfinished_section(inner_state)

        # ── Anniversary section ──
        anniversary = self._generate_anniversary_section(inner_state)

        # ── Dream section ──
        dream = self._generate_dream_section(inner_state)

        # ── Directive ──
        directive = self._generate_directive(modality, soul)

        return InnerStateBlock(
            today_descriptor=today,
            energy_descriptor=energy,
            user_concerns_section=concerns,
            unfinished_section=unfinished,
            anniversary_section=anniversary,
            dream_section=dream,
            inner_state_directive=directive,
        )

    def as_prompt_layer(
        self,
        block: InnerStateBlock,
        modality: str = "reactive",
    ) -> "PromptLayer":
        """Convert InnerStateBlock to a PromptLayer for SS05 Composer.

        Per §6.1: inner_state layer sits between emotion_context and memory_context.
        Uses the PromptLayer type defined in ss05_composer.layer_aggregator.
        The layer_type is "inner_state".

        Args:
            block: Built InnerStateBlock.
            modality: "reactive" or "proactive".

        Returns:
            PromptLayer compatible with SS05 Composer assembly.
        """
        from heart.ss05_composer.layer_aggregator import PromptLayer

        # Render the full block text based on modality
        content = self._render_block_text(block, modality)

        return PromptLayer(
            layer_id=f"inner_state_{block.generated_at}",
            source_subsystem="SS06",
            layer_type="inner_state",
            priority=30,  # per LAYER_PRIORITIES: inner_state = 30
            position_constraint="anywhere",
            content=content,
            token_count_estimate=self._estimate_block_tokens(block),
            min_token_count=100,  # per LAYER_MIN_TOKENS
            is_compressible=True,
            metadata={
                "availability": "cache",
                "sub_suggestions": self._extract_sub_suggestions(block),
                "intensity": "medium",
            },
        )

    def as_content_string(
        self,
        block: "InnerStateBlock | InnerState",
        modality: str = "reactive",
    ) -> str:
        """Render the full InnerStateBlock as a single string for prompt injection.

        This is the text that gets placed in the final prompt between
        [Emotion Context Block] and [Memory Context Block] per §6.1.

        Accepts either a pre-built InnerStateBlock or a raw InnerState
        (which will be built automatically).

        Args:
            block: Built InnerStateBlock or raw InnerState.
            modality: "reactive" or "proactive".

        Returns:
            Complete inner state section text.
        """
        if not isinstance(block, InnerStateBlock):
            # Auto-build from raw InnerState
            block = self.build(block, modality=modality)
        return self._render_block_text(block, modality)

    # ── Descriptor generators ──────────────────────────────────

    def _generate_today_descriptor(self, inner_state: InnerState) -> str:
        """Generate today's mood + activity descriptor per §6.4.

        Structure:
          - First line: mood descriptor
          - Then: activities by time of day
        """
        parts: List[str] = []
        today = inner_state.today

        # Mood
        if today.mood and today.mood.descriptor:
            parts.append(f"你今天{today.mood.descriptor}")
        elif today.mood:
            parts.append(f"你今天{today.mood.label}。")
        else:
            parts.append("你今天还好。")

        # Mood drift hint (internal only — affects phrasing but not exposed)
        if today.mood and today.mood.drift_direction == "falling":
            parts[-1] = parts[-1].rstrip("。") + "，比早上低落了一点。"

        # Activities by time of day
        if today.activities:
            time_parts: Dict[str, List[str]] = {}
            for a in today.activities:
                tod = getattr(a, "time_of_day", None)
                if not tod:
                    continue
                desc = getattr(a, "description", str(a))
                if tod not in time_parts:
                    time_parts[tod] = []
                time_parts[tod].append(desc)

            for tod in ("morning", "afternoon", "evening", "night"):
                if tod in time_parts:
                    label = self.TIME_LABELS.get(tod, tod)
                    joined = "，".join(time_parts[tod])
                    parts.append(f"{label}你{joined}。")

        return "\n".join(parts)

    def _generate_energy_descriptor(self, inner_state: InnerState) -> str:
        """Generate a human-readable energy level descriptor.

        Uses current_energy relative to baseline for nuanced description.
        """
        energy = inner_state.current_energy
        baseline = inner_state.energy_baseline

        # Classify energy band
        if energy >= 0.8:
            desc = self.ENERGY_DESCRIPTORS["high"]
        elif energy >= 0.6:
            desc = self.ENERGY_DESCRIPTORS["medium_high"]
        elif energy >= 0.4:
            desc = self.ENERGY_DESCRIPTORS["medium"]
        elif energy >= 0.2:
            desc = self.ENERGY_DESCRIPTORS["medium_low"]
        else:
            desc = self.ENERGY_DESCRIPTORS["low"]

        # Add relative-to-baseline nuance
        if energy < baseline - 0.2:
            desc += " 你今天比平时更累。"
        elif energy > baseline + 0.2:
            desc += " 你今天比平时精神好。"

        return desc

    def _generate_concerns_section(self, inner_state: InnerState) -> str:
        """Generate the user concerns section.

        Only surfaces concerns that haven't been addressed (or past the 24h cooldown).
        """
        concerns = inner_state.user_concerns
        if not concerns:
            return "你今天没有什么特别挂念他的事。"

        # Filter: only non-addressed (or past cooldown) concerns
        active_concerns: List[object] = []
        now = datetime.now(timezone.utc)
        for c in concerns:
            has_been_addressed = getattr(c, "has_been_addressed", False)
            last_referenced = getattr(c, "last_referenced_at", None)

            if not has_been_addressed:
                active_concerns.append(c)
            elif last_referenced:
                try:
                    ref_dt = datetime.fromisoformat(
                        str(last_referenced).replace("Z", "+00:00")
                    )
                    hours_since = (now - ref_dt).total_seconds() / 3600
                    if hours_since > 24:  # Past cooldown
                        active_concerns.append(c)
                except (ValueError, TypeError):
                    pass

        if not active_concerns:
            return "你今天没有什么特别挂念他的事。"

        # Sort by urgency
        active_concerns.sort(
            key=lambda c: getattr(c, "urgency", 0.0), reverse=True
        )

        # Build bullet list (top 3)
        lines = ["你心里有几件挂念他的事："]
        for c in active_concerns[:3]:
            text = getattr(c, "concern_text", str(c))
            lines.append(f" - {text}")

        return "\n".join(lines)

    def _generate_unfinished_section(self, inner_state: InnerState) -> Optional[str]:
        """Generate the unfinished thoughts section.

        Only includes active (non-expired) thoughts.
        Returns None if no unfinished thoughts.
        """
        thoughts = inner_state.unfinished_thoughts
        if not thoughts:
            return None

        # Filter out expired thoughts
        active = []
        now = datetime.now(timezone.utc)
        for t in thoughts:
            expiry = getattr(t, "expiry_at", None)
            if expiry:
                try:
                    exp_dt = datetime.fromisoformat(
                        str(expiry).replace("Z", "+00:00")
                    )
                    if exp_dt < now:
                        continue
                except (ValueError, TypeError):
                    pass
            active.append(t)

        if not active:
            return None

        lines = ["上次对话你有几句话没说完："]
        for t in active[:3]:  # Top 3 per INV-I-6
            content = getattr(t, "content", str(t))
            lines.append(f" - {content}")

        return "\n".join(lines)

    def _generate_anniversary_section(
        self, inner_state: InnerState
    ) -> Optional[str]:
        """Generate anniversary section for upcoming important dates.

        Returns None if no imminent anniversaries.
        """
        anniversaries = inner_state.upcoming_anniversaries
        if not anniversaries:
            return None

        # Only surface if within 7 days and not yet sent
        relevant = []
        for a in anniversaries:
            hours = a.get("hours_until", float("inf"))
            actual_sent = a.get("actual_sent", False)

            if hours <= 168 and not actual_sent:  # Within 7 days
                relevant.append(a)

        if not relevant:
            return None

        lines: List[str] = []
        for a in relevant:
            name = a.get("name", "重要日子")
            hours = a.get("hours_until", 0)
            if hours <= 24:
                lines.append(f"今天是{name}。你觉得很重要。")
            else:
                days = int(hours / 24)
                lines.append(f"还有{days}天是{name}。你心里已经在准备了。")

        return "\n".join(lines)

    def _generate_dream_section(self, inner_state: InnerState) -> Optional[str]:
        """Generate dream section (V2). Returns None if no recent dream."""
        dream = inner_state.recent_dream
        if not dream:
            return None

        has_been_shared = dream.get("has_been_shared", False)
        if has_been_shared:
            return None

        content = dream.get("dream_content", "")
        emot = dream.get("associated_emotion", "")
        if not content:
            return None

        if emot:
            return f"你最近做了一个{emot}的梦：{content}。"
        return f"你最近做了一个梦：{content}。"

    def _generate_directive(
        self,
        modality: str,
        soul: Optional[object] = None,
    ) -> str:
        """Generate the inner state usage directive.

        Reactive: per §6.2 directive block.
        Proactive: per §6.3 message generation rules.
        """
        if modality == "proactive":
            directive = self.DEFAULT_PROACTIVE_DIRECTIVE
            # Add character-specific guidance if soul is available
            if soul is not None:
                character_id = getattr(soul, "character_id", "")
                if character_id == "rin":
                    directive += "\n凛: 短句、反问、不直接关心。用自然意象。"
                elif character_id == "dorothy":
                    directive += "\n桃乐丝: 元气、可爱、撒娇。用颜色和蝴蝶。"
            return directive

        directive = self.DEFAULT_REACTIVE_DIRECTIVE

        # Append drift-specific guidance
        # (handled elsewhere — here just return the default)
        return directive

    # ── Block rendering ─────────────────────────────────────────

    def _render_block_text(
        self, block: InnerStateBlock, modality: str
    ) -> str:
        """Render the complete block text per §6.2 (reactive) or §6.3 (proactive).

        Returns the full text that sits inside the prompt at the inner state position.
        """
        if modality == "proactive":
            return self._render_proactive_block(block)

        return self._render_reactive_block(block)

    def _render_reactive_block(self, block: InnerStateBlock) -> str:
        """Render per §6.2 InnerStateBlock 模板（reactive 模态）."""
        segments: List[str] = []

        segments.append("═══════════════════════════════════════════════════════════")
        segments.append("【你今天的内心】")
        segments.append("")

        # Today
        segments.append("▾ 你今天的概貌")
        segments.append(block.today_descriptor)
        segments.append("")

        # Energy
        segments.append("▾ 你现在的体力 / 状态")
        segments.append(block.energy_descriptor)
        segments.append("")

        # Concerns
        segments.append("▾ 你心里在意的事 (关于他)")
        segments.append(block.user_concerns_section)
        segments.append("")

        # Unfinished
        if block.unfinished_section:
            segments.append(block.unfinished_section)
            segments.append("")

        # Anniversary
        if block.anniversary_section:
            segments.append(block.anniversary_section)
            segments.append("")

        # Dream
        if block.dream_section:
            segments.append(block.dream_section)
            segments.append("")

        # Directive
        segments.append("【内心运用指引】")
        segments.append(block.inner_state_directive)
        segments.append("═══════════════════════════════════════════════════════════")

        return "\n".join(segments)

    def _render_proactive_block(self, block: InnerStateBlock) -> str:
        """Render per §6.3 InnerStateBlock 模板（proactive 模态）."""
        segments: List[str] = []

        segments.append("═══════════════════════════════════════════════════════════")
        segments.append("【你主动想发一句话给他】")
        segments.append("")

        # Today brief
        segments.append("▾ 你今天的内心 (供参考)")
        segments.append(block.today_descriptor)
        if block.user_concerns_section:
            segments.append(block.user_concerns_section)
        if block.unfinished_section:
            segments.append(block.unfinished_section)
        segments.append("")

        # Directive
        segments.append("【生成规则】")
        segments.append(block.inner_state_directive)
        segments.append("═══════════════════════════════════════════════════════════")

        return "\n".join(segments)

    # ── Metadata extraction ─────────────────────────────────────

    @staticmethod
    def _extract_sub_suggestions(block: InnerStateBlock) -> List[str]:
        """Extract implicit suggestions from block content for Conflict Resolver."""
        suggestions: List[str] = []
        if block.unfinished_section:
            suggestions.append("unfinished_thought_present")
        if block.anniversary_section:
            suggestions.append("anniversary_reminder")
        if block.dream_section:
            suggestions.append("dream_available")
        if "没有什么特别挂念" in block.user_concerns_section:
            suggestions.append("no_concerns")
        else:
            suggestions.append("user_concerns_present")
        return suggestions

    @staticmethod
    def _estimate_block_tokens(block: InnerStateBlock) -> int:
        """Fast CJK-aware token count on the combined block text."""
        text = (
            block.today_descriptor
            + block.energy_descriptor
            + block.user_concerns_section
            + (block.unfinished_section or "")
            + (block.anniversary_section or "")
            + (block.dream_section or "")
            + block.inner_state_directive
        )
        chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other = len(text) - chinese
        return max(1, int(chinese * 1.5 + other * 0.3))
