"""
Forgetting Affect Engine - SS02 §4.5 + §6.6

Decides whether to inject "she's forgetting" hints into Memory Context Block.

Core algorithm:
1. Base frequency: 3% of turns
2. Multipliers based on days_since_last_interaction:
   - ×3 if > 30 days
   - ×5 if > 90 days
3. Cap at 15% (avoid "dementia" feeling)
4. Mode selection based on current memory state distribution

Author: 心屿团队
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import structlog

logger = structlog.get_logger()


class InjectionMode(Enum):
    """Forgetting hint injection modes from §4.5."""

    MISSING_HINT = "missing_hint"  # "我好像漏了什么……"
    TIP_OF_TONGUE = "tip_of_tongue"  # "那个，什么来着……"
    APOLOGETIC = "apologetic"  # "……抱歉，我记不太清楚了。"
    DISCOVERY = "discovery"  # "等等……我想起来了。" (dormant/archived only)
    COMPLETE_AMNESIA = "complete_amnesia"  # Rare, archived only, max 1/30 days


@dataclass
class ForgettingAffectConfig:
    """Configuration for Forgetting Affect Engine from §4.5."""

    base_frequency: float = 0.03  # 3% of turns
    multiplier_30_days: float = 3.0  # ×3 if days_since_last > 30
    multiplier_90_days: float = 5.0  # ×5 if days_since_last > 90
    upper_bound: float = 0.15  # Never exceed 15%

    # complete_amnesia rate limit
    complete_amnesia_max_per_month: int = 1  # Max 1 per 30 days


@dataclass
class MemoryStateDistribution:
    """Current distribution of memory states (from Retriever)."""

    vivid_count: int = 0
    fading_count: int = 0
    faint_count: int = 0
    dormant_count: int = 0
    archived_count: int = 0

    @property
    def total(self) -> int:
        return (
            self.vivid_count
            + self.fading_count
            + self.faint_count
            + self.dormant_count
            + self.archived_count
        )

    @property
    def has_weak_memories(self) -> bool:
        """Returns True if there are faint/dormant/archived memories."""
        return (self.faint_count + self.dormant_count + self.archived_count) > 0


@dataclass
class ForgettingAffectDecision:
    """Result of forgetting affect decision."""

    should_inject: bool
    mode: Optional[InjectionMode]
    frequency_used: float  # Actual frequency after multipliers
    hint_text: Optional[str] = None  # Character-voiced hint


class ForgettingAffectEngine:
    """
    Forgetting Affect Engine - decides when to inject forgetting hints.

    Per §4.5, §6.6, and INV-IMM-M-6 (max 5% turns, but spec §4.5 says 15% cap).
    """

    def __init__(
        self,
        character_id: str,
        soul_spec: dict,
        config: Optional[ForgettingAffectConfig] = None,
    ):
        """
        Initialize Forgetting Affect Engine.

        Args:
            character_id: Character ID (rin, dorothy, etc.)
            soul_spec: Full soul spec (for voice_dna phrasing)
            config: Optional config override
        """
        self.character_id = character_id
        self.soul_spec = soul_spec
        self.config = config or ForgettingAffectConfig()

        # Track complete_amnesia usage (session-level, reset daily)
        # In production, this should be stored in Redis/DB per user
        self._last_complete_amnesia_date: Optional[datetime] = None

    def should_inject_forgetting_hint(
        self,
        days_since_last_interaction: int,
        memory_state_distribution: MemoryStateDistribution,
        user_mentioned_forgotten_fact: bool = False,
    ) -> ForgettingAffectDecision:
        """
        Decide whether to inject forgetting hint this turn.

        Args:
            days_since_last_interaction: Days since last conversation
            memory_state_distribution: Current memory state counts
            user_mentioned_forgotten_fact: True if user mentioned something we should remember but don't

        Returns:
            ForgettingAffectDecision with should_inject + mode
        """
        # Calculate current frequency with multipliers
        frequency = self.config.base_frequency

        # Apply days_since_last multipliers (§4.5)
        if days_since_last_interaction > 90:
            frequency *= self.config.multiplier_90_days
        elif days_since_last_interaction > 30:
            frequency *= self.config.multiplier_30_days

        # Cap at upper_bound (§4.5)
        frequency = min(frequency, self.config.upper_bound)

        # Forced injection if user mentioned forgotten fact (§6.6)
        if user_mentioned_forgotten_fact:
            mode = self._select_injection_mode(
                memory_state_distribution,
                days_since_last_interaction,
            )
            hint_text = self._generate_hint_text(mode)
            logger.info(
                "forgetting_affect_forced_injection",
                character=self.character_id,
                mode=mode.value if mode else None,
                reason="user_mentioned_forgotten_fact",
            )
            return ForgettingAffectDecision(
                should_inject=True,
                mode=mode,
                frequency_used=1.0,  # Forced
                hint_text=hint_text,
            )

        # Random injection based on frequency
        should_inject = random.random() < frequency

        if should_inject:
            mode = self._select_injection_mode(
                memory_state_distribution,
                days_since_last_interaction,
            )
            hint_text = self._generate_hint_text(mode)

            logger.info(
                "forgetting_affect_injection",
                character=self.character_id,
                mode=mode.value if mode else None,
                frequency=frequency,
                days_since_last=days_since_last_interaction,
            )

            return ForgettingAffectDecision(
                should_inject=True,
                mode=mode,
                frequency_used=frequency,
                hint_text=hint_text,
            )

        return ForgettingAffectDecision(
            should_inject=False,
            mode=None,
            frequency_used=frequency,
        )

    def _select_injection_mode(
        self,
        distribution: MemoryStateDistribution,
        days_since_last: int,
    ) -> InjectionMode:
        """
        Select injection mode based on memory state distribution.

        Logic:
        - If mostly archived → discovery or complete_amnesia (rare)
        - If mostly dormant → discovery
        - If mostly faint → tip_of_tongue or apologetic
        - Default → missing_hint

        Args:
            distribution: Current memory state distribution
            days_since_last: Days since last interaction

        Returns:
            Selected InjectionMode
        """
        if distribution.total == 0:
            # No memories to recall → missing_hint
            return InjectionMode.MISSING_HINT

        # Calculate proportions
        archived_ratio = distribution.archived_count / distribution.total
        dormant_ratio = distribution.dormant_count / distribution.total
        faint_ratio = distribution.faint_count / distribution.total

        # Archived-dominant: discovery or complete_amnesia (rare)
        if archived_ratio > 0.5:
            # Check if complete_amnesia allowed (max 1 per 30 days)
            if self._can_use_complete_amnesia():
                # Very rare (10% chance even when allowed)
                if random.random() < 0.1:
                    self._last_complete_amnesia_date = datetime.now(timezone.utc)
                    return InjectionMode.COMPLETE_AMNESIA
            # Default to discovery for archived
            return InjectionMode.DISCOVERY

        # Dormant-dominant: discovery
        if dormant_ratio > 0.3:
            return InjectionMode.DISCOVERY

        # Faint-dominant: tip_of_tongue or apologetic
        if faint_ratio > 0.3:
            return random.choice([InjectionMode.TIP_OF_TONGUE, InjectionMode.APOLOGETIC])

        # Default: missing_hint
        return InjectionMode.MISSING_HINT

    def _can_use_complete_amnesia(self) -> bool:
        """
        Check if complete_amnesia mode is allowed (max 1 per 30 days).

        Returns:
            True if allowed
        """
        if self._last_complete_amnesia_date is None:
            return True

        now = datetime.now(timezone.utc)
        days_since_last = (now - self._last_complete_amnesia_date).days

        return days_since_last >= 30

    def _generate_hint_text(self, mode: InjectionMode) -> str:
        """
        Generate character-voiced hint text for the injection mode.

        Uses Soul.voice_dna for character-specific phrasing.
        Per user requirements:
        - Rin: "……忘了。"
        - Dorothy: "诶嘿嘿忘啦~"

        Args:
            mode: Injection mode

        Returns:
            Character-voiced hint string
        """
        # Character-specific base phrases
        if self.character_id == "rin":
            phrases = {
                InjectionMode.MISSING_HINT: "……我好像漏了什么。算了。",
                InjectionMode.TIP_OF_TONGUE: "那个，什么来着……",
                InjectionMode.APOLOGETIC: "……抱歉，我记不太清楚了。",
                InjectionMode.DISCOVERY: "……等等。我想起来了。",
                InjectionMode.COMPLETE_AMNESIA: "……忘了。",
            }
        elif self.character_id == "dorothy":
            phrases = {
                InjectionMode.MISSING_HINT: "诶嘿嘿，桃桃好像忘了什么呀~",
                InjectionMode.TIP_OF_TONGUE: "那个那个，什么来着呀~",
                InjectionMode.APOLOGETIC: "呜哇，桃桃记不清楚了呢~",
                InjectionMode.DISCOVERY: "啊！桃桃想起来了！",
                InjectionMode.COMPLETE_AMNESIA: "诶嘿嘿忘啦~",
            }
        else:
            # Fallback generic phrases
            phrases = {
                InjectionMode.MISSING_HINT: "我好像漏了什么……算了。",
                InjectionMode.TIP_OF_TONGUE: "那个，什么来着……",
                InjectionMode.APOLOGETIC: "抱歉，我记不太清楚了。",
                InjectionMode.DISCOVERY: "等等……我想起来了。",
                InjectionMode.COMPLETE_AMNESIA: "……忘了。",
            }

        return phrases.get(mode, phrases[InjectionMode.MISSING_HINT])
