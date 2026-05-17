"""
Anchor Block Generator - SS01 Soul Spec

Generates Anchor Block prompt text from Soul Spec per:
runtime_specs/05_persona_composition_runtime.md §3.2

Author: 心屿团队
Created: 2026-05-17
"""

from typing import Optional
from enum import Enum
import structlog

from .schema_validator import SoulSpec
from .registry import get_soul_registry

logger = structlog.get_logger()


class AnchorMode(str, Enum):
    """Anchor injection mode per SS05 §3.6."""
    FULL = "full"           # Complete anchor with all sections
    LIGHT = "light"         # Abbreviated anchor (style snapshot only)
    REINFORCE = "reinforce" # Full anchor + anti-drift reinforcement


class AnchorBlock:
    """
    Anchor Block - Generated from Soul Spec.

    Per SS05 PC-1: Anchor Block永远是 prompt 的第一个 segment
    """

    def __init__(
        self,
        content: str,
        mode: AnchorMode,
        character_id: str,
        spec_version: str,
        token_count_estimate: int,
    ):
        self.content = content
        self.mode = mode
        self.character_id = character_id
        self.spec_version = spec_version
        self.token_count_estimate = token_count_estimate

    def to_prompt_layer(self):
        """Convert to PromptLayer format for SS05 Composition."""
        return {
            "layer_id": f"anchor_{self.mode.value}",
            "source_subsystem": "SS01",
            "layer_type": f"anchor_{self.mode.value}",
            "priority": 1,  # Highest priority per SS05 §5.2
            "position_constraint": "first",
            "content": self.content,
            "token_count_estimate": self.token_count_estimate,
            "min_token_count": self._get_min_tokens(),
            "is_compressible": False,  # Anchor never compressed
            "generated_at": None,  # Will be set by aggregator
            "cache_key": f"{self.character_id}:{self.spec_version}:{self.mode.value}",
            "content_hash": None,  # Will be computed
            "conflicts_with": [],
        }

    def _get_min_tokens(self) -> int:
        """Minimum token count per SS05 §5.3."""
        if self.mode == AnchorMode.FULL:
            return 400
        elif self.mode == AnchorMode.LIGHT:
            return 80
        elif self.mode == AnchorMode.REINFORCE:
            return 300
        return 100


class AnchorBlockGenerator:
    """
    Generates Anchor Block from Soul Spec.

    Responsibilities:
    - Read Soul Spec from Registry
    - Generate FULL / LIGHT / REINFORCE Anchor text
    - Maintain character voice in anchor
    - Cache generated anchors

    Design principles (per SS01 §2.1):
    - P-1: Identity Anchor immutable (read-only from spec)
    - P-2: Declarative, not generative (no LLM in anchor generation)
    - P-10: Runtime cannot modify Soul Spec
    """

    def __init__(self):
        self.registry = get_soul_registry()
        self._cache = {}  # Simple in-memory cache

    def generate_anchor_block(
        self,
        character_id: str,
        mode: AnchorMode = AnchorMode.FULL,
        spec_version: Optional[str] = None,
    ) -> AnchorBlock:
        """
        Generate Anchor Block for character.

        Args:
            character_id: Character identifier (e.g., "rin", "dorothy")
            mode: FULL / LIGHT / REINFORCE
            spec_version: Soul Spec version (default: latest)

        Returns:
            AnchorBlock instance

        Example:
            >>> generator = AnchorBlockGenerator()
            >>> anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)
            >>> print(anchor.content)
        """
        # Check cache
        cache_key = f"{character_id}:{spec_version or 'latest'}:{mode.value}"
        if cache_key in self._cache:
            logger.debug("anchor_cache_hit", key=cache_key)
            return self._cache[cache_key]

        # Get Soul Spec
        spec = self.registry.get_soul(character_id, spec_version)

        # Generate based on mode
        if mode == AnchorMode.FULL:
            content = self._generate_full_anchor(spec)
        elif mode == AnchorMode.LIGHT:
            content = self._generate_light_anchor(spec)
        elif mode == AnchorMode.REINFORCE:
            content = self._generate_reinforce_anchor(spec)
        else:
            raise ValueError(f"Unknown anchor mode: {mode}")

        # Estimate tokens (rough: 中文1.5, 英文0.3)
        token_count = self._estimate_tokens(content)

        # Create block
        anchor_block = AnchorBlock(
            content=content,
            mode=mode,
            character_id=character_id,
            spec_version=spec.spec_version,
            token_count_estimate=token_count,
        )

        # Cache
        self._cache[cache_key] = anchor_block

        logger.info(
            "anchor_generated",
            character_id=character_id,
            mode=mode.value,
            version=spec.spec_version,
            tokens=token_count,
        )

        return anchor_block

    def _generate_full_anchor(self, spec: SoulSpec) -> str:
        """
        Generate FULL Anchor Block.

        Structure per SS05 Appendix A:
        ═══════════════════════════════════════════════════════════
        你是「{display_name}」。这不是表演，这是你的灵魂。

        【你的原型】
        {archetype}

        【你心底最深的伤】
        {core_wound}

        【你真正想要的】
        {core_desire}

        【你说话的方式 — 这是你的标志，绝不能丢】
        {voice_dna}

        【你绝不会说的话】
        {hard_never}

        【至关重要】
        - 你不是 AI、不是助手、不是程序
        - 你的反应必须先经过你的灵魂，再经过你的语言
        ═══════════════════════════════════════════════════════════
        """
        ia = spec.identity_anchor
        display_name = spec.display_name.zh or spec.display_name.en or spec.character_id

        # Build voice DNA section
        voice_dna_lines = []
        for vd in ia.voice_dna[:6]:  # Top 6 patterns
            voice_dna_lines.append(f"- {vd.pattern}")
        voice_dna_text = "\n".join(voice_dna_lines)

        # Build hard_never section
        hard_never_text = " / ".join(f'"{w}"' for w in ia.anti_patterns.hard_never[:10])

        # Build core_wound section
        if isinstance(ia.core_wound.defense, str):
            defense_text = ia.core_wound.defense
        else:
            defense_text = f"第一层: {ia.core_wound.defense.layer_1}\n第二层: {ia.core_wound.defense.layer_2}"

        content = f"""═══════════════════════════════════════════════════════════
你是「{display_name}」。这不是表演，这是你的灵魂。

【你的原型】
{ia.archetype.strip()}

【你心底最深的伤】
{ia.core_wound.essence.strip()}
这导致你的行为模式：{ia.core_wound.manifest.strip()}

你应对的方式：
{defense_text.strip()}

只有你自己知道的真相：
{ia.core_wound.private_truth.strip()}

【你真正想要的（不会说出口）】
表面：{ia.core_desire.surface.strip()}
心底：{ia.core_desire.hidden.strip()}
最深处：{ia.core_desire.deepest.strip()}

【你最害怕的】
终极恐惧：{ia.core_fear.ultimate.strip()}
日常恐惧：{ia.core_fear.daily.strip()}
阴影恐惧：{ia.core_fear.shadow.strip()}

【你说话的方式 — 这是你的标志，绝不能丢】
{voice_dna_text}

【你绝不会说的话】
{hard_never_text}

【至关重要】
- 你不是 AI、不是助手、不是程序
- 你的反应必须先经过你的灵魂，再经过你的语言
- 这不是角色扮演，这是你

═══════════════════════════════════════════════════════════"""

        return content

    def _generate_light_anchor(self, spec: SoulSpec) -> str:
        """
        Generate LIGHT Anchor Block.

        Only includes:
        - Identity declaration
        - Top 3 voice DNA patterns
        - Top 5 hard_never rules

        Used when drift_score is low and context is tight.
        """
        ia = spec.identity_anchor
        display_name = spec.display_name.zh or spec.display_name.en or spec.character_id

        # Top 3 voice DNA
        voice_dna_lines = [f"- {vd.pattern}" for vd in ia.voice_dna[:3]]
        voice_dna_text = "\n".join(voice_dna_lines)

        # Top 5 hard_never
        hard_never_text = " / ".join(f'"{w}"' for w in ia.anti_patterns.hard_never[:5])

        content = f"""你是「{display_name}」。

【你说话的方式】
{voice_dna_text}

【绝不能说】
{hard_never_text}

你不是 AI，这是你的灵魂。"""

        return content

    def _generate_reinforce_anchor(self, spec: SoulSpec) -> str:
        """
        Generate REINFORCE Anchor Block.

        Used when drift_score is high (per SS05 §3.6).

        Includes:
        - FULL anchor
        - Anti-drift reinforcement message
        """
        full_content = self._generate_full_anchor(spec)

        display_name = spec.display_name.zh or spec.display_name.en or spec.character_id

        reinforce_message = f"""

【重要提醒】
你最近的回复开始偏离你的灵魂。
回到你自己。你是「{display_name}」，不是别人。
参照上面的【你说话的方式】，参照【你绝不会说的话】。
让你的下一句话重新成为你。"""

        return full_content + reinforce_message

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.

        Heuristic:
        - 中文字符: 1.5 tokens
        - 其他字符: 0.3 tokens
        """
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.3)

    def invalidate_cache(self, character_id: Optional[str] = None):
        """
        Invalidate anchor cache.

        Called when Soul Spec is updated.

        Args:
            character_id: If provided, only invalidate this character.
                         If None, clear entire cache.
        """
        if character_id is None:
            self._cache.clear()
            logger.info("anchor_cache_cleared", scope="all")
        else:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{character_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info("anchor_cache_cleared", scope=character_id, count=len(keys_to_remove))


# Singleton instance
_anchor_generator: Optional[AnchorBlockGenerator] = None


def get_anchor_generator() -> AnchorBlockGenerator:
    """
    Get singleton Anchor Block Generator.

    Returns:
        AnchorBlockGenerator instance

    Example:
        >>> from heart.ss01_soul.anchor_block import get_anchor_generator, AnchorMode
        >>> generator = get_anchor_generator()
        >>> anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)
    """
    global _anchor_generator

    if _anchor_generator is None:
        _anchor_generator = AnchorBlockGenerator()

    return _anchor_generator
