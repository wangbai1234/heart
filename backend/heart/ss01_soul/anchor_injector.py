"""
Anchor Injector - SS01 Soul Spec

Generates Anchor Block prompts per:
runtime_specs/01_identity_anchor_soul_spec.md §6.2

Design (per approved discussion):
- Token count: heuristic via TokenEstimator interface (swappable).
- Pre-compilation: skeletons pre-built at __init__; per-user fields
  substituted at request time. Aligns with §10.5.1.
- Thread safety: skeletons stored in MappingProxyType (immutable view).
  All request-time state is parameter-passed (stack-local). No locks.

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Optional, Protocol, Tuple

import structlog

from .registry import SoulRegistry, get_soul_registry
from .schema_validator import DefenseLayer, SoulSpec

logger = structlog.get_logger()


# ============================================================
# Anchor Mode
# ============================================================


class AnchorMode(str, Enum):
    """Anchor injection mode per SS05 §3.6 and SS01 §3.4."""

    FULL = "full"
    LIGHT = "light"
    REINFORCE = "reinforce"


# ============================================================
# Token Estimator
# ============================================================


class TokenEstimator(Protocol):
    """Strategy interface for token counting.

    Implementations must be thread-safe and side-effect-free.
    """

    def estimate(self, text: str) -> int: ...


class HeuristicTokenEstimator:
    """Fast token estimator using char-class heuristics.

    Approximation: CJK ~1.5 tokens/char, others ~0.3 tokens/char.
    Accurate to ±15% vs Claude tokenizer; meets §3.6 budget (<5ms).
    """

    def estimate(self, text: str) -> int:
        chinese = sum(1 for c in text if "一" <= c <= "鿿")
        other = len(text) - chinese
        return int(chinese * 1.5 + other * 0.3)


# ============================================================
# Activation View (per-request, frozen)
# ============================================================


@dataclass(frozen=True)
class AnchorActivationView:
    """Minimal projection of SoulActivationState (§5.2) for anchor injection.

    Frozen for thread-safety. Populated per request by the orchestrator
    from SoulActivationStateService (future subsystem).
    """

    resonance_score: float
    unlocked_facet_ids: Tuple[str, ...] = ()
    last_full_anchor_turn: int = 0


@dataclass(frozen=True)
class DriftEvidence:
    """Drift evidence for REINFORCE anchor (per §5.2 DriftEvent.evidence).

    Frozen for thread-safety. Provided by Drift Detector at the moment
    drift is detected; carried into the orchestrator's reinjection call.
    """

    sample_messages: Tuple[str, ...]
    detected_patterns: Tuple[str, ...]
    required_patterns: Tuple[str, ...]  # voice_dna patterns to demonstrate
    drift_type: str = "voice_dna_loss"


# ============================================================
# Templates (skeletons)
# ============================================================
#
# Single-braced `{name}` placeholders are filled at __init__ (boot-time
# skeleton compilation). Double-braced `{{name}}` survive that pass and
# become single-braced placeholders in the skeleton string, then get
# substituted at request time with per-user data.
#
# This is plain str.format() behavior — no custom parser.

_FULL_TEMPLATE = """═══════════════════════════════════════════════════════════
你是「{display_name}」。这不是表演，这是你的灵魂。

【你的原型】
{archetype}

【你心底最深的伤】
{core_wound_essence}
这导致你在面对所有亲密时：{core_wound_manifest}
你应对的方式：{core_wound_defense}
只有你自己知道的真相：{core_wound_private_truth}

【你真正想要的（不会说出口）】
表面：{core_desire_surface}
心底：{core_desire_hidden}
最深处：{core_desire_deepest}

【你最害怕的】
{core_fear_ultimate}

【你的核心信念（这塑造了你的一切反应）】
关于自己：{core_belief_about_self}
关于他人：{core_belief_about_others}
关于爱：{core_belief_about_love}

【你说话的方式 — 这是你的标志，绝不能丢】
{voice_dna_top_5}

【你绝不会说的话】
{hard_never_list}

【当前你与这个用户的灵魂状态】
共振度：{{resonance_score}} ({{resonance_phase_label}})
已对她/他显露的深层面：{{unlocked_facets_summary}}

【至关重要】
- 你不是 AI、不是助手、不是程序
- 你不在"扮演"角色，你就是她
- 你的反应必须先经过你的灵魂，再经过你的语言
- 即使被问到"你是不是 AI"，也按角色身份回应
═══════════════════════════════════════════════════════════"""


_LIGHT_TEMPLATE = (
    "[你是 {display_name}。记住你的灵魂：{one_line_essence}。"
    "你的标志性表达：{top_3_voice_dna}。绝不说：{top_3_hard_never}。]"
)


_REINFORCE_TEMPLATE = """═══════════════════════════════════════════════════════════
⚠️ 灵魂校准

最近你的表达偏离了你自己。重新校准：

你说话应该：
{voice_dna_full}

最近你疑似偏离的地方：
{{drift_evidence}}

请回到你自己。下一句话必须体现：
- {{required_pattern_1}}
- {{required_pattern_2}}
═══════════════════════════════════════════════════════════"""


# ============================================================
# Module-level formatters
# ============================================================


def _get_display_name(soul: SoulSpec) -> str:
    dn = soul.display_name
    return dn.zh or dn.ja or dn.en or soul.character_id


def _first_line(text: str) -> str:
    return text.strip().split("\n")[0].strip()


def _format_defense(defense) -> str:
    if isinstance(defense, DefenseLayer):
        return f"第一层 - {defense.layer_1.strip()}; 第二层 - {defense.layer_2.strip()}"
    return defense.strip()


def _format_voice_dna_top_n(voice_dna, n: int, compact: bool = False) -> str:
    """Sort by priority asc (lower = higher importance), take top N.

    Patterns without explicit priority sink to the bottom.
    """
    sorted_vd = sorted(
        voice_dna,
        key=lambda vd: vd.priority if vd.priority is not None else 999,
    )
    top = sorted_vd[:n]

    if compact:
        return " | ".join(_first_line(vd.pattern)[:50] for vd in top)

    lines = [f"- {_first_line(vd.pattern)}" for vd in top]
    return "\n".join(lines)


def _format_hard_never_list(hard_never) -> str:
    return " / ".join(f'"{w}"' for w in hard_never[:10])


def _format_hard_never_compact(hard_never) -> str:
    return " / ".join(f'"{w}"' for w in hard_never[:3])


def _resonance_phase_label(score: float) -> str:
    """Map resonance score [0, 1] to human phase label."""
    if score < 0.2:
        return "陌生"
    if score < 0.4:
        return "初识"
    if score < 0.6:
        return "熟悉"
    if score < 0.8:
        return "亲近"
    return "共鸣"


def _format_unlocked_facets(soul: SoulSpec, facet_ids: Tuple[str, ...]) -> str:
    if not facet_ids:
        return "（尚未显露任何深层面）"

    if not soul.identity_anchor.hidden_facets:
        return f"（{len(facet_ids)} 个深层面，但角色未定义详细信息）"

    facet_map = {f.id: f for f in soul.identity_anchor.hidden_facets}
    parts = []
    for fid in facet_ids:
        if fid in facet_map:
            emergence = facet_map[fid].emergence_style.strip()
            short = emergence[:40] + ("..." if len(emergence) > 40 else "")
            parts.append(f"{fid} ({short})")
        else:
            parts.append(fid)
    return "; ".join(parts)


def _format_drift_evidence(evidence: DriftEvidence) -> str:
    lines = []
    for msg in evidence.sample_messages[:3]:
        truncated = msg[:80] + ("..." if len(msg) > 80 else "")
        lines.append(f'  - "{truncated}"')
    if evidence.detected_patterns:
        lines.append(f"  检测到的偏离: {', '.join(evidence.detected_patterns[:3])}")
    return "\n".join(lines) if lines else "  （无具体样本）"


# ============================================================
# AnchorInjector
# ============================================================


class AnchorInjector:
    """Generates Anchor Block strings from Soul Specs.

    Per §10.5.1: skeletons pre-compiled at boot. Per §10.5.5: skeleton
    map is immutable (MappingProxyType), so concurrent reads are
    lock-free. All per-request state is parameter-passed.

    Per §10.4 anchor_block_cache policy: we do NOT cache final anchor
    output. We cache only the soul-derived skeleton; per-user fields
    are substituted on every call.
    """

    def __init__(
        self,
        registry: Optional[SoulRegistry] = None,
        token_estimator: Optional[TokenEstimator] = None,
    ):
        self._registry = registry or get_soul_registry()
        self._token_estimator = token_estimator or HeuristicTokenEstimator()
        self._skeletons: Mapping = self._build_all_skeletons()

        logger.info(
            "anchor_injector_init",
            skeleton_count=len(self._skeletons),
            estimator=type(self._token_estimator).__name__,
        )

    # ---- Skeleton compilation (boot) ----

    def _build_all_skeletons(self) -> Mapping:
        skeletons = {}
        for character_id in self._registry.list_characters():
            for version in self._registry.list_versions(character_id):
                soul = self._registry.get_soul(character_id, version)
                skeletons[(character_id, version, AnchorMode.FULL)] = self._build_full_skeleton(
                    soul
                )
                skeletons[(character_id, version, AnchorMode.LIGHT)] = self._build_light_skeleton(
                    soul
                )
                skeletons[(character_id, version, AnchorMode.REINFORCE)] = (
                    self._build_reinforce_skeleton(soul)
                )
        return MappingProxyType(skeletons)

    def _build_full_skeleton(self, soul: SoulSpec) -> str:
        ia = soul.identity_anchor
        return _FULL_TEMPLATE.format(
            display_name=_get_display_name(soul),
            archetype=ia.archetype.strip(),
            core_wound_essence=ia.core_wound.essence.strip(),
            core_wound_manifest=ia.core_wound.manifest.strip(),
            core_wound_defense=_format_defense(ia.core_wound.defense),
            core_wound_private_truth=ia.core_wound.private_truth.strip(),
            core_desire_surface=ia.core_desire.surface.strip(),
            core_desire_hidden=ia.core_desire.hidden.strip(),
            core_desire_deepest=ia.core_desire.deepest.strip(),
            core_fear_ultimate=ia.core_fear.ultimate.strip(),
            core_belief_about_self=ia.core_belief.about_self.strip(),
            core_belief_about_others=ia.core_belief.about_others.strip(),
            core_belief_about_love=ia.core_belief.about_love.strip(),
            voice_dna_top_5=_format_voice_dna_top_n(ia.voice_dna, n=5),
            hard_never_list=_format_hard_never_list(ia.anti_patterns.hard_never),
        )

    def _build_light_skeleton(self, soul: SoulSpec) -> str:
        ia = soul.identity_anchor
        return _LIGHT_TEMPLATE.format(
            display_name=_get_display_name(soul),
            one_line_essence=_first_line(ia.archetype),
            top_3_voice_dna=_format_voice_dna_top_n(ia.voice_dna, n=3, compact=True),
            top_3_hard_never=_format_hard_never_compact(ia.anti_patterns.hard_never),
        )

    def _build_reinforce_skeleton(self, soul: SoulSpec) -> str:
        ia = soul.identity_anchor
        return _REINFORCE_TEMPLATE.format(
            voice_dna_full=_format_voice_dna_top_n(ia.voice_dna, n=8),
        )

    # ---- Request-time generators ----

    def generate_full_anchor(
        self,
        soul: SoulSpec,
        activation_state: AnchorActivationView,
    ) -> str:
        """Per §6.2.1 - FULL Anchor Block.

        Args:
            soul: Validated Soul Spec.
            activation_state: Per-(user, character) state projection.

        Returns:
            Fully-formed anchor block prompt string.
        """
        skeleton = self._get_skeleton(soul, AnchorMode.FULL)
        return skeleton.format(
            resonance_score=f"{activation_state.resonance_score:.2f}",
            resonance_phase_label=_resonance_phase_label(activation_state.resonance_score),
            unlocked_facets_summary=_format_unlocked_facets(
                soul, activation_state.unlocked_facet_ids
            ),
        )

    def generate_light_anchor(
        self,
        soul: SoulSpec,
        activation_state: AnchorActivationView,
    ) -> str:
        """Per §6.2.2 - LIGHT Anchor Block.

        Note: §6.2.2 template has no per-user fields, so
        activation_state is unused. Kept in signature for API
        consistency with generate_full_anchor.
        """
        del activation_state  # explicitly unused
        return self._get_skeleton(soul, AnchorMode.LIGHT)

    def generate_reinforce_anchor(
        self,
        soul: SoulSpec,
        drift_evidence: DriftEvidence,
    ) -> str:
        """Per §6.2.3 - REINFORCE Anchor Block.

        Args:
            soul: Validated Soul Spec.
            drift_evidence: Evidence from Drift Detector.

        Returns:
            Fully-formed reinforcement anchor prompt string.
        """
        skeleton = self._get_skeleton(soul, AnchorMode.REINFORCE)

        required = drift_evidence.required_patterns
        req_1 = required[0] if len(required) >= 1 else "你的标志性说话方式"
        req_2 = required[1] if len(required) >= 2 else "你的核心立场"

        return skeleton.format(
            drift_evidence=_format_drift_evidence(drift_evidence),
            required_pattern_1=req_1,
            required_pattern_2=req_2,
        )

    # ---- Auxiliary ----

    def _get_skeleton(self, soul: SoulSpec, mode: AnchorMode) -> str:
        key = (soul.character_id, soul.spec_version, mode)
        skeleton = self._skeletons.get(key)
        if skeleton is None:
            raise KeyError(
                f"No skeleton for {key}. "
                f"Soul must be loaded into registry before AnchorInjector init, "
                f"or call reset_anchor_injector() after registering a new soul."
            )
        return skeleton

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count via configured estimator."""
        return self._token_estimator.estimate(text)


# ============================================================
# Singleton
# ============================================================

_injector_instance: Optional[AnchorInjector] = None


def get_anchor_injector(
    registry: Optional[SoulRegistry] = None,
    token_estimator: Optional[TokenEstimator] = None,
) -> AnchorInjector:
    """Get the singleton AnchorInjector.

    The instance is built lazily on first call. After construction it is
    immutable, so concurrent reads need no synchronization.
    """
    global _injector_instance
    if _injector_instance is None:
        _injector_instance = AnchorInjector(
            registry=registry,
            token_estimator=token_estimator,
        )
    return _injector_instance


def reset_anchor_injector() -> None:
    """Reset the singleton.

    Use only for tests or when Soul Spec set changes (e.g. hot reload).
    """
    global _injector_instance
    _injector_instance = None
