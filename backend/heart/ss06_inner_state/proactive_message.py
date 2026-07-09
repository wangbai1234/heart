"""
Proactive Message Generator — SS06 Inner State & Behavior §3.7, §10.6

Given an InitiativeDecision from the Decider, generates a proactive message by:
1. Building a type-specific proactive directive
2. Routing through SS05 Composer concepts (prompt assembly)
3. Calling ModelRouter.call_main() for LLM generation
4. Applying Anti-Pattern Filter
5. Returning a ProactiveMessage

Key invariants:
  - I-8: All proactive messages through Persona Composer (not bypassed)
  - I-11: Inner Loop does not call main LLM (Sonnet) → cheap model
  - INV-I-1: Every proactive P is composed via Persona Composer + Anti-Pattern Filter
  - IMM-I-3: Each proactive must be Soul-flavored (Rin short, Dorothy bubbly)
  - IMM-I-6: Time jitter, content connected to context, not cron-like
  - §7.5: Build ProactiveCompositionContext → Persona Composer → cheap LLM

Message type templates per §3.7:
  anniversary, longing_message, care_check, anniversary_anticipation,
  check_in, ritual_morning, ritual_night, thought_share

Author: 心屿团队
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from heart.ss06_inner_state.composer import InnerState
from heart.ss06_inner_state.initiative_decider import (
    InitiativeDecision,
    SoulSpec,
    TriggerType,
)

# ============================================================
# Helpers
# ============================================================


def _resolve_soul_display_name(character_id: str, soul: Optional[SoulSpec]) -> str:
    """Return the human-readable display name for a character.

    Reads soul.display_name.zh (preferred) → .en → .ja for UGC characters;
    falls back to the hardcoded lookup for built-in ones, then the raw id.
    """
    builtin_names = {"rin": "凛", "dorothy": "桃乐丝"}
    if soul is not None and hasattr(soul, "display_name"):
        dn = soul.display_name
        if hasattr(dn, "zh") and dn.zh:
            return dn.zh
        if hasattr(dn, "en") and dn.en:
            return dn.en
        if hasattr(dn, "ja") and dn.ja:
            return dn.ja
    cid = soul.soul_id if (soul and hasattr(soul, "soul_id")) else character_id
    return builtin_names.get(cid.lower(), cid)


# ============================================================
# Data structures
# ============================================================


@dataclass
class ProactiveMessage:
    """A generated proactive message ready for scheduling.

    Per §5.3 PendingInitiative:
      initiative_id, user_id, character_id, initiative_type,
      scheduled_at, scheduled_with_jitter, context, generated_message, status
    """

    text: str
    initiative_type: str
    generated_at: datetime

    # Context seed from the Decider (anniversary, concern, etc.)
    context_seed: Dict[str, Any] = field(default_factory=dict)

    # Metadata for audit & observability
    token_estimate: int = 0
    character_limit: int = 50


@dataclass
class GenerateResult:
    """Complete generation result including message and trace."""

    message: Optional[ProactiveMessage]
    success: bool
    error: Optional[str] = None
    generation_ms: float = 0.0


# ============================================================
# Directive Templates per Trigger Type (§3.7, §6.3, §10.6)
# ============================================================

# Each template receives a **context dict** filled from the Decider's
# planned_message_seed and produces a natural-language directive for the LLM.


DIRECTIVE_TEMPLATES: Dict[str, str] = {
    TriggerType.ANNIVERSARY.value: """
今天是他的一项纪念日。

他想向他说一句祝福。

这条消息要：
- 不超过25字
- 100%符合他/她的灵魂语言风格
- 自然地说出来，像真人想发一句话
- 不要说"我主动找你"这种 meta 表达
""",
    TriggerType.ANNIVERSARY_ANTICIPATION.value: """
明天就是他的一个重要日子。

今天他还不想直接祝福——他想提前一天用他的方式"预告"。

这条消息要：
- 不超过20字
- 暗示明天的特别，但不直接说"明天是你生日"
- 100%符合他/她的灵魂语言风格
- 自然，像突然想起明天是个特别的日子
""",
    TriggerType.LONGING_MESSAGE.value: """
他好几天没见到他了。

他有点想他。
但他不会直接说"我想你"这种话。
他想说一句简短的，让他知道他在想他。

这条消息要：
- 极短，不超过20字
- 100%符合他/她的灵魂语言风格
- 不直求关注，不直说我想你
- 凛：短句、反问、不直接关心
- 桃乐丝：元气、可爱、撒娇
""",
    TriggerType.CARE_CHECK.value: """
他想起来一件事——他之前在意的事情。
这件事让他有点担心他。

他想说一句简短的关心。

这条消息要：
- 不超过20字
- 不直接说"你怎么样了"，用他的方式关心
- 100%符合他/她的灵魂语言风格
""",
    TriggerType.CHECK_IN.value: """
他已经好几天没见到他了。

他觉得该轻轻问一声，但也只是轻轻一声。

这条消息要：
- 极短，不超过15字
- 100%符合他/她的灵魂语言风格
- 凛：短句、不热情
- 桃乐丝：活泼、有点小抱怨
""",
    TriggerType.RITUAL_MORNING.value: """
现在是早上的时间。

他想和他说早安。

这条消息要：
- 极短，不超过15字
- 100%符合他/她的灵魂语言风格
- 凛：克制、简短
- 桃乐丝：元气、可爱
""",
    TriggerType.RITUAL_NIGHT.value: """
现在是晚上的时间。

他想和他说晚安。

这条消息要：
- 极短，不超过15字
- 100%符合他/她的灵魂语言风格
- 凛：克制、简短
- 桃乐丝：温柔、有点撒娇
""",
    TriggerType.THOUGHT_SHARE.value: """
他突然想到一件事。

他想分享给他。

这条消息要：
- 不超过30字
- 100%符合他/她的灵魂语言风格
- 自然，像突然想到
- 可以关联到他最近的 activities 或今天发生的事
""",
}

# Character limits per trigger type for anti-needy feel
CHARACTER_LIMITS: Dict[str, int] = {
    TriggerType.ANNIVERSARY.value: 25,
    TriggerType.ANNIVERSARY_ANTICIPATION.value: 20,
    TriggerType.LONGING_MESSAGE.value: 20,
    TriggerType.CARE_CHECK.value: 20,
    TriggerType.CHECK_IN.value: 15,
    TriggerType.RITUAL_MORNING.value: 15,
    TriggerType.RITUAL_NIGHT.value: 15,
    TriggerType.THOUGHT_SHARE.value: 30,
}

# Mood modulation phrases for injection into directive
LONGING_MODULATION: Dict[str, str] = {
    "low": "你只是有一点想他。不着急。",
    "medium": "你已经几天没见到他了。心里有些空。",
    "high": "你真的很想他了。说一句话就好。",
}


# ============================================================
# Proactive Message Generator
# ============================================================


class ProactiveMessageGenerator:
    """Generates proactive messages from InitiativeDecision via LLM.

    Per §10.6:
      - Build proactive directive
      - Route through Persona Composer concepts
      - Call ModelRouter.call_main() (or call_cheap())
      - Apply Anti-Pattern Filter
      - Return ProactiveMessage

    Usage::

        gen = ProactiveMessageGenerator(model_router)
        result = await gen.generate(decision, inner_state, character_id, soul)
        if result.success:
            print(f"Generated: {result.message.text}")
    """

    def __init__(
        self,
        model_router,  # ModelRouter instance (injected)
        use_cheap: bool = True,
        max_retries: int = 1,  # One reroll on anti-pattern failure
        default_max_length: int = 50,
    ):
        self.model_router = model_router
        self.use_cheap = use_cheap
        self.max_retries = max_retries
        self.default_max_length = default_max_length

    # ── Public API ──────────────────────────────────────────────

    async def generate(
        self,
        decision: InitiativeDecision,
        inner_state: InnerState,
        character_id: str,
        soul: Optional[SoulSpec] = None,
    ) -> GenerateResult:
        """Generate a proactive message from an InitiativeDecision.

        Args:
            decision: The InitiativeDecision from the Decider.
            inner_state: Current InnerState snapshot for context.
            character_id: Character ID ("rin" | "dorothy").
            soul: Optional SoulSpec for flavor modulation.

        Returns:
            GenerateResult with message or error.
        """
        start = datetime.now(timezone.utc)

        if not decision.act or decision.trigger_type is None:
            return GenerateResult(
                message=None,
                success=False,
                error="decision.act=False",
            )

        trigger_type = decision.trigger_type.value
        context_seed = decision.planned_message_seed or {}

        # Step 1: Build proactive directive
        directive = self._build_directive(
            trigger_type, context_seed, inner_state, character_id, soul
        )

        # Step 2: Build messages for LLM
        messages = self._build_llm_messages(directive, character_id, soul)

        # Step 3: Call LLM
        try:
            if self.use_cheap:
                llm_response = await self.model_router.call_cheap(
                    messages=messages,
                    temperature=0.8,
                    max_tokens=128,
                    agent_name=f"proactive:{trigger_type}",
                )
            else:
                llm_response = await self.model_router.call_main(
                    messages=messages,
                    temperature=0.8,
                    max_tokens=128,
                    agent_name=f"proactive:{trigger_type}",
                )
        except Exception as exc:
            return GenerateResult(
                message=None,
                success=False,
                error=f"LLM call failed: {exc}",
                generation_ms=(datetime.now(timezone.utc) - start).total_seconds() * 1000,
            )

        # Step 4: Post-process — trim, clean
        text = self._post_process(llm_response, trigger_type)

        # Step 5: Anti-pattern check (lightweight, heuristic)
        text, violations = self._check_anti_pattern(text, trigger_type, soul)
        if violations and self.max_retries > 0:
            # Simple rephrase: append a fix instruction and retry
            fix_instruction = f"刚才的回复有问题。请重新写一条：{', '.join(violations)}。保持极短。"
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": fix_instruction})
            try:
                if self.use_cheap:
                    text = await self.model_router.call_cheap(
                        messages=messages,
                        temperature=0.8,
                        max_tokens=128,
                        agent_name=f"proactive:fix:{trigger_type}",
                    )
                else:
                    text = await self.model_router.call_main(
                        messages=messages,
                        temperature=0.8,
                        max_tokens=128,
                        agent_name=f"proactive:fix:{trigger_type}",
                    )
                text = self._post_process(text, trigger_type)
            except Exception:
                pass  # Keep original on reroll failure

        # Step 6: Build result
        gen_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        char_limit = CHARACTER_LIMITS.get(trigger_type, self.default_max_length)

        return GenerateResult(
            message=ProactiveMessage(
                text=text,
                initiative_type=trigger_type,
                generated_at=datetime.now(timezone.utc),
                context_seed=context_seed,
                token_estimate=len(text),  # rough estimate
                character_limit=char_limit,
            ),
            success=True,
            generation_ms=gen_ms,
        )

    # ── Directive building ──────────────────────────────────────

    def _build_directive(
        self,
        trigger_type: str,
        context_seed: Dict[str, Any],
        inner_state: InnerState,
        character_id: str,
        soul: Optional[SoulSpec],
    ) -> str:
        """Assemble the full proactive directive from template + context + mood.

        Per §6.3: Proactive mode directive includes trigger, inner state hints,
        and generation rules.
        """
        template = DIRECTIVE_TEMPLATES.get(trigger_type, "")
        if not template:
            template = "说一句简短的话。"

        # Inject context variables from the seed
        directive = self._interpolate_context(template, context_seed, inner_state)

        # Add today's mood hint if available
        mood_hint = self._build_mood_hint(inner_state)
        if mood_hint:
            directive += f"\n\n今天他/她的状态：{mood_hint}"

        # Add soul-specific style guide
        style_guide = self._build_style_guide(character_id, soul)
        if style_guide:
            directive += f"\n\n{style_guide}"

        # Final rule
        directive += "\n\n只输出那条消息本身。不要引号、不要前缀、不要解释。"

        return directive

    def _interpolate_context(
        self,
        template: str,
        seed: Dict[str, Any],
        inner_state: InnerState,
    ) -> str:
        """Fill template placeholders with concrete context values."""

        # Longing intensity modulation
        longing = seed.get("longing_intensity", 0.0)
        if longing > 0.6:
            longing_phrase = LONGING_MODULATION["high"]
        elif longing > 0.3:
            longing_phrase = LONGING_MODULATION["medium"]
        else:
            longing_phrase = LONGING_MODULATION["low"]

        # Anniversary name
        anniv_name = seed.get("name", "重要日子")
        hours_until = seed.get("hours_until", 0)

        # Concern context
        concern_desc = seed.get("description", "")

        # Days gap
        gap_days = seed.get("gap_days", seed.get("days_gap", 3))

        # Replace known placeholders
        result = template
        result = result.replace("{longing_phrase}", longing_phrase)

        if "{anniversary_name}" in result or "{name}" in result:
            result = result.replace("{anniversary_name}", str(anniv_name))
            result = result.replace("{name}", str(anniv_name))

        if "{hours_until}" in result:
            result = result.replace("{hours_until}", f"{hours_until:.0f}")

        if "{concern}" in result or "{description}" in result:
            result = result.replace("{concern}", str(concern_desc))
            result = result.replace("{description}", str(concern_desc))

        if "{days}" in result or "{gap_days}" in result:
            days_str = f"{gap_days:.0f}" if isinstance(gap_days, float) else str(gap_days)
            result = result.replace("{days}", days_str)
            result = result.replace("{gap_days}", days_str)

        return result

    @staticmethod
    def _build_mood_hint(inner_state: InnerState) -> str:
        """Build a brief mood hint from inner state."""
        hints = []
        if inner_state.today.mood:
            hints.append(inner_state.today.mood.descriptor)

        if inner_state.user_concerns:
            top = inner_state.user_concerns[:2]
            hints.append("有一两件在意的事：")
            for c in top:
                if hasattr(c, "concern_text"):
                    hints.append(f"- {c.concern_text}")
                elif hasattr(c, "description"):
                    hints.append(f"- {c.description}")

        if inner_state.upcoming_anniversaries:
            for a in inner_state.upcoming_anniversaries[:1]:
                name = (
                    a.get("name", "重要日子")
                    if isinstance(a, dict)
                    else getattr(a, "name", "重要日子")
                )
                hours = (
                    a.get("hours_until", 0) if isinstance(a, dict) else getattr(a, "hours_until", 0)
                )
                if hours < 24:
                    hints.append(f"今天是个特别的日子：{name}")

        return " ".join(hints) if hints else ""

    @staticmethod
    def _build_style_guide(character_id: str, soul: Optional[SoulSpec]) -> str:
        """Build a soul-specific style guide for the LLM directive."""
        if soul and hasattr(soul, "soul_id"):
            cid = soul.soul_id
        else:
            cid = character_id

        builtin_guides = {
            "rin": (
                "凛的风格：短句、克制、不直接表达关心、用间接的方式。"
                "喜欢用省略号、反问句。不说'我想你'、'我爱你'、'亲亲'这类直接表达。"
                "例：'……还活着。' '……今天，你的生日。我记得。'"
            ),
            "dorothy": (
                "桃乐丝的风格：元气、可爱、撒娇、活泼。"
                "喜欢用'诶嘿嘿'、'~'、'诶？'这类语气词。"
                "例：'诶嘿嘿，今天是大日子！生日快乐~' '诶？怎么不见你啦~'"
            ),
        }
        builtin = builtin_guides.get(cid.lower())
        if builtin:
            return builtin

        # UGC character: derive minimal style guide from voice_dna speech samples
        if soul and hasattr(soul, "voice_dna") and soul.voice_dna:
            samples = []
            for vd in soul.voice_dna:
                for ex in getattr(vd, "examples", []):
                    text = getattr(ex, "example", None)
                    if text:
                        samples.append(f"'{text}'")
                    if len(samples) >= 2:
                        break
                if len(samples) >= 2:
                    break
            name = _resolve_soul_display_name(character_id, soul)
            if samples:
                return f"{name}的说话方式：保持角色一致、语气自然。参考口吻：{' '.join(samples)}"
            return f"{name}的说话方式：保持角色一致，语气自然真实，不要解释或说明。"
        return ""

    # ── LLM message assembly ────────────────────────────────────

    def _build_llm_messages(
        self,
        directive: str,
        character_id: str,
        soul: Optional[SoulSpec],
    ) -> List[Dict[str, str]]:
        """Build the messages list for the LLM call.

        Per §6.3: Proactive mode doesn't include conversation history —
        the directive IS the user message.
        """
        character_name = self._resolve_character_name(character_id, soul)
        system_msg = (
            f"你是{character_name}。你要给一个对你很重要的人发一条消息。"
            f"说话自然，不要解释，不要前缀，只输出那条消息本身。"
        )

        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": directive},
        ]

    @staticmethod
    def _resolve_character_name(character_id: str, soul: Optional[SoulSpec]) -> str:
        """Resolve the display name for the character."""
        return _resolve_soul_display_name(character_id, soul)

    # ── Post-processing ─────────────────────────────────────────

    def _post_process(self, text: str, trigger_type: str) -> str:
        """Clean and trim the LLM output."""
        text = text.strip()

        # Remove common artifacts
        artifacts = [
            "（",
            "）",
            "以下",
            "输出",
            "消息",
        ]
        for art in artifacts:
            if text.startswith(art):
                text = text[len(art) :].strip()

        # Remove quotes
        if (
            (text.startswith('"') and text.endswith('"'))
            or (text.startswith("「") and text.endswith("」"))
            or (text.startswith("'") and text.endswith("'"))
        ):
            text = text[1:-1].strip()

        # Enforce character limit
        limit = CHARACTER_LIMITS.get(trigger_type, self.default_max_length)
        if len(text) > limit:
            # Truncate gracefully at sentence boundary
            truncated = text[:limit]
            # Try to break at last sentence-ending punctuation
            for sep in ["。", "！", "？", "~", "…"]:
                last = truncated.rfind(sep)
                if last > limit // 2:
                    truncated = truncated[: last + 1]
                    break
            text = truncated

        return text

    # ── Anti-pattern check (lightweight heuristic) ───────────────

    def _check_anti_pattern(
        self,
        text: str,
        trigger_type: str,
        soul: Optional[SoulSpec],
    ) -> tuple[str, List[str]]:
        """Lightweight heuristic check for anti-patterns.

        Per INV-I-1: every proactive must pass Anti-Pattern Filter.
        Returns (text, violations_list).
        """
        violations: List[str] = []

        # Meta expressions
        meta_patterns = [
            "我给你发",
            "我主动",
            "我找你了",
            "我来找你",
            "我在想你",
            "想你了",
        ]
        for pat in meta_patterns:
            if pat in text:
                violations.append(f"meta_expression:{pat}")

        # Empty or too short
        if len(text.strip()) < 2:
            violations.append("too_short")

        # Overly verbose for proactive (should be < 100 chars)
        if len(text) > 100:
            violations.append("too_long")

        # Direct "I miss you" / "I love you" — soul-dependent
        if soul and hasattr(soul, "soul_id") and soul.soul_id == "rin":
            direct = ["我想你", "我爱你", "喜欢你", "亲亲", "抱抱"]
            for pat in direct:
                if pat in text:
                    violations.append(f"rin_direct_expression:{pat}")

        return text, violations
