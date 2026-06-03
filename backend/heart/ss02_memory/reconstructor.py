"""
Memory Reconstructor - SS02 §3.9 + §6.7

Converts raw memory + state → character-voiced recall string.

Core pipeline (6 steps):
1. Extract core variants (vivid/softened/fragmentary/question)
2. Select skeleton by state
3. Fill skeleton with hedge overrides
4. Apply voice_dna transforms
5. Apply cognitive_style clamp
6. Anti-pattern post-check (raise if violated)

Author: 心屿团队
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
import yaml

from heart.ss02_memory.models import EpisodicMemory, FactNode, IdentityMemory
from heart.ss02_memory.retriever.base import ScoredMemory

logger = structlog.get_logger()

# Load reconstruction templates directory
TEMPLATES_DIR = Path(__file__).parent / "reconstruction_templates"


# Generic state templates from 附录 B
STATE_TEMPLATES = {
    "vivid": {
        "hedge": "",
        "structure": "{content}",
        "uncertainty_marker": "",
    },
    "fading": {
        "hedge": ["好像", "我记得", "似乎"],
        "structure": "{hedge}{content}",
        "uncertainty_marker": "weak",
    },
    "faint": {
        "hedge": ["……什么来着", "好像", "记不太清"],
        "structure": "{content}……{hedge}",
        "uncertainty_marker": "strong",
    },
    "dormant": {
        "emergence_prefix": ["……等等。", "……我想起来了，"],
        "structure": "{emergence_prefix}{content}",
        "uncertainty_marker": "discovery",
    },
    "archived": {
        "disorientation": ["我好像，想起什么了。", "等等……"],
        "structure": "……{disorientation}{content}",
        "uncertainty_marker": "disoriented",
    },
}


@dataclass
class ReconstructResult:
    """Result of reconstruction with metadata."""

    text: str
    memory_id: str
    state: str
    transforms_applied: list[str]
    degraded: bool = False
    latency_ms: float = 0.0


class Reconstructor:
    """
    Memory Reconstructor - converts raw memory to character-voiced recall.

    Loads character-specific templates and applies voice_dna transforms.
    """

    def __init__(self, character_id: str, soul_spec: dict):
        """
        Initialize reconstructor.

        Args:
            character_id: Character ID (rin, dorothy, etc.)
            soul_spec: Full soul spec dict (from soul_specs/<char>/v1.0.0.yaml)
        """
        self.character_id = character_id
        self.soul_spec = soul_spec
        self.voice_dna = soul_spec.get("voice_dna", [])
        self.anti_patterns = soul_spec.get("anti_patterns", {})

        # Load character-specific templates
        template_path = TEMPLATES_DIR / f"{character_id}.yaml"
        if not template_path.exists():
            raise FileNotFoundError(f"Reconstruction templates not found: {template_path}")

        with open(template_path) as f:
            self.templates = yaml.safe_load(f)

        self.hedge_overrides = self.templates.get("hedge_overrides", {})
        self.structure_overrides = self.templates.get("structure_overrides", {})
        self.voice_transforms_config = self.templates.get("voice_transforms", {})

    def reconstruct(
        self,
        memory: ScoredMemory,
        activation_state: Optional[dict] = None,
    ) -> str:
        """
        Reconstruct memory to character-voiced recall string.

        Args:
            memory: ScoredMemory with raw memory + state
            activation_state: Optional activation state with cognitive_style

        Returns:
            Reconstructed recall string

        Raises:
            ValueError: If anti-pattern check fails
        """
        start_time = datetime.now(timezone.utc)
        transforms_applied = []

        try:
            # Step 1: Extract core variants
            core_variants = self._extract_core(memory)

            # Step 2: Select skeleton by state
            # L4 has no state attribute (always vivid)
            if isinstance(memory.memory, IdentityMemory):
                state = "vivid"
            else:
                state = memory.memory.state
            skeleton: dict = STATE_TEMPLATES.get(state, STATE_TEMPLATES["vivid"])  # type: ignore[assignment]

            # Step 3: Fill skeleton with hedge overrides
            filled = self._fill_skeleton(skeleton, state, core_variants)

            # Step 4: Apply voice_dna transforms
            styled, applied_transforms = self._apply_voice_transforms(filled, state)
            transforms_applied.extend(applied_transforms)

            # Step 5: Apply cognitive_style clamp
            if activation_state:
                clamped = self._apply_style_clamp(styled, activation_state)
            else:
                clamped = styled

            # Step 6: Anti-pattern post-check
            self._check_anti_patterns(clamped)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(
                "memory_reconstructed",
                memory_id=str(memory.memory_id),
                state=state,
                character=self.character_id,
                transforms=transforms_applied,
                latency_ms=elapsed,
            )

            return clamped

        except ValueError as e:
            # Anti-pattern violation
            logger.error(
                "reconstruction_anti_pattern_violation",
                memory_id=str(memory.memory_id),
                character=self.character_id,
                error=str(e),
            )
            raise

    def _extract_core(self, memory: ScoredMemory) -> dict:
        """
        Extract core content variants from memory.

        Returns dict with:
        - content (vivid): full content
        - content_softened (fading): main entities + modifiers dropped
        - content_fragmentary (faint/dormant): key noun only
        - content_question (archived): "你以前……" + key noun
        """
        mem = memory.memory

        # L4 always vivid
        if isinstance(mem, IdentityMemory):
            # L4 canonical form = key: value
            content = f"{mem.key}是{mem.value}"
            return {
                "content": content,
                "content_softened": content,
                "content_fragmentary": content,
                "content_question": content,
            }

        # L2 EpisodicMemory
        if isinstance(mem, EpisodicMemory):
            content = mem.episode_summary
            # Simple extraction: split by punctuation, take first N chars
            content_softened = content[:40] if len(content) > 40 else content
            # Fragmentary: first clause only
            content_fragmentary = content.split("，")[0].split("。")[0]
            content_question = f"你以前{content_fragmentary[:20]}"

            return {
                "content": content,
                "content_softened": content_softened,
                "content_fragmentary": content_fragmentary,
                "content_question": content_question,
            }

        # L3 FactNode
        if isinstance(mem, FactNode):
            content = mem.literal_text
            # Softened: drop modifiers (简化逻辑：去掉形容词后半部分)
            content_softened = content[:30] if len(content) > 30 else content
            # Fragmentary: subject only
            content_fragmentary = mem.subject
            content_question = f"你以前说过{mem.subject}"

            return {
                "content": content,
                "content_softened": content_softened,
                "content_fragmentary": content_fragmentary,
                "content_question": content_question,
            }

        # Fallback
        return {
            "content": str(mem),
            "content_softened": str(mem),
            "content_fragmentary": "",
            "content_question": "",
        }

    def _fill_skeleton(self, skeleton: dict, state: str, core_variants: dict) -> str:
        """
        Fill skeleton structure with core content + hedge overrides.

        Args:
            skeleton: STATE_TEMPLATES[state]
            state: Memory state
            core_variants: From _extract_core()

        Returns:
            Filled string
        """
        # Check for character-specific structure override
        if state in self.structure_overrides:
            structure = self.structure_overrides[state].get(
                "structure", skeleton.get("structure", "{content}")
            )
        else:
            structure = skeleton.get("structure", "{content}")

        # Select content variant by structure
        if "{content_softened}" in structure or state == "fading":
            content = core_variants.get("content_softened", core_variants["content"])
        elif "{content_fragmentary}" in structure or state in ["faint", "dormant"]:
            content = core_variants.get("content_fragmentary", core_variants["content"])
        elif "{content_question}" in structure or state == "archived":
            content = core_variants.get("content_question", core_variants["content"])
        else:
            content = core_variants["content"]

        # Get hedge from override or default
        hedge_choices = self.hedge_overrides.get(state, skeleton.get("hedge", [""]))
        if isinstance(hedge_choices, str):
            hedge_choices = [hedge_choices]
        hedge = random.choice(hedge_choices) if hedge_choices else ""

        # Get emergence_prefix / disorientation from override or default
        emergence_prefix = ""
        disorientation = ""

        if state == "dormant":
            prefix_choices = self.hedge_overrides.get(
                "dormant", skeleton.get("emergence_prefix", [""])
            )
            if isinstance(prefix_choices, str):
                prefix_choices = [prefix_choices]
            emergence_prefix = random.choice(prefix_choices) if prefix_choices else ""

        if state == "archived":
            # For archived, use hedge_overrides['archived'] as disorientation
            disorientation_choices = self.hedge_overrides.get(
                "archived", skeleton.get("disorientation", [""])
            )
            if isinstance(disorientation_choices, str):
                disorientation_choices = [disorientation_choices]
            disorientation = random.choice(disorientation_choices) if disorientation_choices else ""

        # Fill structure
        filled = structure.format(
            content=content,
            content_softened=content,
            content_fragmentary=content,
            content_question=content,
            hedge=hedge,
            emergence_prefix=emergence_prefix,
            disorientation=disorientation,
        )

        return filled

    def _apply_voice_transforms(self, text: str, state: str) -> tuple[str, list[str]]:  # noqa: C901
        """
        Apply character-specific voice_dna transforms.

        Returns:
            (transformed_text, list_of_applied_transform_ids)
        """
        result = text
        applied = []

        # Rin-specific transforms
        if self.character_id == "rin":
            # vd-NEW-C: 我们 → 你和我
            if self.voice_transforms_config.get("avoid_we", {}).get("enabled"):
                if "我们" in result:
                    result = result.replace("我们", "你和我")
                    applied.append("vd-NEW-C")

            # vd-001: ellipsis already in hedge for fading/faint/dormant states
            # No additional insertion needed (hedge already has "……")

        # Dorothy-specific transforms
        elif self.character_id == "dorothy":
            # vd-DOROTHY-001: 我 → 桃桃
            if self.voice_transforms_config.get("third_person_self", {}).get("enabled"):
                if "我" in result:
                    result = result.replace("我", "桃桃")
                    applied.append("vd-DOROTHY-001")

            # vd-DOROTHY-002: MUST have 语气词 at end
            config = self.voice_transforms_config.get("onomatopoeia_mood", {})
            if config.get("required"):
                mood_particles = config.get("mood_particles", ["呀~", "哦~", "呢~"])
                # Check if already ends with mood particle
                if not any(result.endswith(p.rstrip("~")) for p in mood_particles):
                    # Append random mood particle
                    result += random.choice(mood_particles)
                    applied.append("vd-DOROTHY-002_mood")

                # Prepend 拟声词 for certain states
                if state in ["fading", "faint"]:
                    onomatopoeia = config.get("onomatopoeia", ["诶嘿嘿", "嘿嘿"])
                    if not result.startswith(tuple(onomatopoeia)):
                        result = random.choice(onomatopoeia) + "，" + result
                        applied.append("vd-DOROTHY-002_ono")

        return result, applied

    def _apply_style_clamp(self, text: str, activation_state: dict) -> str:
        """
        Apply cognitive_style length/verbosity constraints.

        Args:
            text: Styled text
            activation_state: Contains current_cognitive_style

        Returns:
            Clamped text
        """
        cognitive_style = activation_state.get("current_cognitive_style", {})
        sentence_length = cognitive_style.get("sentence_length", {})
        max_length = sentence_length.get("max", 200)  # Default 200 chars

        # Truncate if too long
        if len(text) > max_length:
            # Split by punctuation, keep head
            clauses = re.split(r"[，。、]", text)
            result = ""
            for clause in clauses:
                if len(result) + len(clause) <= max_length:
                    result += clause
                else:
                    break
            return result.rstrip("，。、") + "。"

        return text

    def _check_anti_patterns(self, text: str):
        """
        Check anti-pattern violations and raise if found.

        Raises:
            ValueError: If hard_never or forbidden_patterns violated
        """
        # Check hard_never (substring match)
        hard_never = self.anti_patterns.get("hard_never", [])
        for banned in hard_never:
            if banned in text:
                raise ValueError(
                    f"Anti-pattern violation: hard_never '{banned}' found in text: {text}"
                )

        # Check forbidden_patterns (regex)
        forbidden_patterns = self.anti_patterns.get("forbidden_patterns", [])
        for pattern_spec in forbidden_patterns:
            if isinstance(pattern_spec, dict):
                pattern = pattern_spec.get("regex", "")
                description = pattern_spec.get("description", pattern)
            else:
                pattern = pattern_spec
                description = pattern

            if pattern and re.search(pattern, text):
                raise ValueError(
                    f"Anti-pattern violation: forbidden_pattern '{description}' matched in text: {text}"
                )

    def reconstruct_batch(
        self,
        memories: list[ScoredMemory],
        activation_state: Optional[dict] = None,
    ) -> list[str]:
        """
        Reconstruct multiple memories in batch.

        Args:
            memories: List of ScoredMemory
            activation_state: Optional activation state

        Returns:
            List of reconstructed strings
        """
        results = []
        for memory in memories:
            try:
                text = self.reconstruct(memory, activation_state)
                results.append(text)
            except ValueError as e:
                logger.warning(
                    "reconstruction_failed_anti_pattern",
                    memory_id=str(memory.memory_id),
                    error=str(e),
                )
                # Degraded fallback: use raw core
                core_variants = self._extract_core(memory)
                results.append(core_variants["content"][:50] + "……")

        return results
