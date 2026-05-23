"""
Anti-Drift Injector — SS05 Persona Composition Runtime §3.3 Step 3 (§3.6)

Decides anchor injection mode (FULL / LIGHT / REINFORCE) per turn and
injects a REINFORCE anchor layer when drift_score crosses threshold.

Per runtime_specs/05_persona_composition_runtime.md:
- §3.3 Step 3: Anti-Drift Injector (< 1ms)
- §3.6: Anti-Drift Injection Decision
- Decision chain: drift_score ≥ threshold → REINFORCE;
  otherwise delegate to SS01 AnchorModeDecider for cadence-based FULL/LIGHT.

Design contract:
- Deterministic (PC-12: no LLM calls)
- Reads drift_score from SS01 DriftDetector result
- Calls SS01 AnchorModeDecider for cadence-based mode selection
- Injects reinforce-anchor PromptLayer only when drift_score crosses threshold
- For FULL/LIGHT modes, passes through the existing anchor from the Aggregator
- < 1ms target latency (§3.3 Step 3)

Note on interaction with Layer Aggregator (§3.2):
  The Aggregator already injects a cadence-based anchor (FULL or LIGHT) per
  SS01 AnchorModeDecider rules. AntiDriftInjector only intervenes when
  drift_score warrants a REINFORCE override, stripping the existing anchor
  and replacing it with a REINFORCE anchor layer (PC-1: anchor always first).

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from heart.ss01_soul.anchor_injector import (
    AnchorActivationView,
    AnchorInjector,
    AnchorMode,
    DriftEvidence,
    get_anchor_injector,
)
from heart.ss01_soul.anchor_mode_decider import decide_mode as _decide_cadence_mode
from heart.ss05_composer.layer_aggregator import PromptLayer

# ============================================================
# Constants
# ============================================================

# Drift score threshold for REINFORCE injection, per §3.6.
_REINFORCE_DRIFT_THRESHOLD = 0.3

# Anchor layer types — used to identify existing anchor layers.
_ANCHOR_LAYER_TYPES = frozenset({"anchor_full", "anchor_light", "anchor_reinforce"})

# ============================================================
# Output types
# ============================================================


@dataclass(frozen=True)
class InjectionResult:
    """Result of anti-drift injection for a single turn.

    Contains the (possibly mutated) layer list and the decided AnchorMode.
    When mode is FULL or LIGHT, layers may be unchanged (pass-through from
    the Layer Aggregator's cadence-based anchor).
    """

    layers: list[PromptLayer]
    anchor_mode: AnchorMode


# ============================================================
# AntiDriftInjector
# ============================================================


class AntiDriftInjector:
    """Decides anchor mode and injects REINFORCE anchor when needed.

    Step 3 of the per-turn composition pipeline (§3.3):

        1. Read drift_score (from SS01 DriftDetector result).
        2. Call SS01 AnchorModeDecider for cadence-based mode.
        3. If drift_score >= threshold, override to REINFORCE.
        4. For REINFORCE: strip existing anchor, inject REINFORCE anchor.
        5. For FULL/LIGHT: pass-through (Aggregator already injected).

    Thread-safe — all per-request state is parameter-passed.
    """

    def __init__(
        self,
        anchor_injector: Optional[AnchorInjector] = None,
    ):
        """Initialize AntiDriftInjector.

        Args:
            anchor_injector: AnchorInjector instance for generating REINFORCE
                anchor content. Defaults to the SS01 singleton.
        """
        self._anchor_injector = anchor_injector

    @property
    def _injector(self) -> AnchorInjector:
        """Lazy-load the AnchorInjector singleton."""
        if self._anchor_injector is None:
            self._anchor_injector = get_anchor_injector()
        return self._anchor_injector

    # ---- Public API ----

    def decide_mode(
        self,
        turn_index: int,
        activation_state: AnchorActivationView,
        drift_score: float,
    ) -> AnchorMode:
        """Decide anchor mode for the current turn.

        Decision chain (per §3.6):
            1. drift_score >= 0.3  → REINFORCE (override)
            2. Otherwise → delegate to SS01 AnchorModeDecider cadence

        Args:
            turn_index: Current turn number (1-indexed).
            activation_state: Per-(user, character) state projection.
            drift_score: Current drift score in [0, 1] from DriftDetector.

        Returns:
            Decided AnchorMode (FULL, LIGHT, or REINFORCE).
        """
        if drift_score >= _REINFORCE_DRIFT_THRESHOLD:
            return AnchorMode.REINFORCE

        return _decide_cadence_mode(activation_state, turn_index, drift_score)

    def inject(
        self,
        layers: list[PromptLayer],
        turn_index: int,
        activation_state: AnchorActivationView,
        drift_score: float,
        drift_evidence: Optional[DriftEvidence] = None,
    ) -> InjectionResult:
        """Decide mode and inject REINFORCE anchor when drift warrants it.

        For FULL/LIGHT modes, the existing anchor from the Aggregator is
        preserved as-is (pass-through). Only REINFORCE mode mutates the
        layer list by stripping the existing anchor and injecting a
        REINFORCE anchor at position 0 (PC-1).

        Args:
            layers: Current prompt layers from Conflict Resolver
                (already contains cadence-based anchor from Aggregator).
            turn_index: Current turn number (1-indexed).
            activation_state: Per-(user, character) state projection.
            drift_score: Current drift score in [0, 1].
            drift_evidence: DriftEvidence from DriftDetector result.
                Required for rich REINFORCE content; a minimal skeleton
                is used when None.

        Returns:
            InjectionResult with (possibly mutated) layer list and decided mode.
        """
        mode = self.decide_mode(turn_index, activation_state, drift_score)

        if mode != AnchorMode.REINFORCE:
            # Pass-through: Aggregator already injected the correct
            # cadence-based anchor (FULL or LIGHT).
            return InjectionResult(layers=layers, anchor_mode=mode)

        # REINFORCE: strip existing anchor, inject REINFORCE anchor
        filtered = [L for L in layers if L.layer_type not in _ANCHOR_LAYER_TYPES]
        reinforce_layer = self._build_reinforce_layer(drift_evidence)
        filtered.insert(0, reinforce_layer)

        return InjectionResult(layers=filtered, anchor_mode=mode)

    # ---- Internal ----

    def _build_reinforce_layer(
        self, drift_evidence: Optional[DriftEvidence] = None
    ) -> PromptLayer:
        """Build a REINFORCE anchor PromptLayer.

        Uses DriftEvidence for rich content (sample messages, detected
        patterns, required voice_dna patterns). Falls back to a minimal
        skeleton if evidence is unavailable.
        """
        injector = self._injector
        soul = injector._registry.get_soul(
            list(injector._registry.list_characters())[0],
            list(injector._registry.list_versions(
                list(injector._registry.list_characters())[0]
            ))[0],
        )

        if drift_evidence is not None:
            content = injector.generate_reinforce_anchor(
                soul=soul,
                drift_evidence=drift_evidence,
            )
        else:
            evidence = DriftEvidence(
                sample_messages=(),
                detected_patterns=(),
                required_patterns=(
                    "你的标志性说话方式",
                    "你的核心立场",
                ),
            )
            content = injector.generate_reinforce_anchor(
                soul=soul,
                drift_evidence=evidence,
            )

        token_estimate = injector.estimate_tokens(content)

        return PromptLayer(
            layer_id="anchor_reinforce",
            source_subsystem="SS01",
            layer_type="anchor_reinforce",
            priority=1,
            position_constraint="first",
            content=content,
            token_count_estimate=token_estimate,
            min_token_count=300,
            is_compressible=False,
        )


# ============================================================
# Convenience function
# ============================================================


def inject_anchor(
    layers: list[PromptLayer],
    turn_index: int,
    activation_state: AnchorActivationView,
    drift_score: float,
    drift_evidence: Optional[DriftEvidence] = None,
    injector: Optional[AntiDriftInjector] = None,
) -> InjectionResult:
    """Convenience: decide mode and inject anchor in one call.

    Args:
        layers: Current prompt layers (post conflict resolution).
        turn_index: Current turn (1-indexed).
        activation_state: Per-(user, character) state.
        drift_score: Current drift score [0, 1].
        drift_evidence: Optional DriftEvidence for REINFORCE.
        injector: Optional pre-configured AntiDriftInjector instance.

    Returns:
        InjectionResult with layers and decided mode.
    """
    adi = injector or AntiDriftInjector()
    return adi.inject(
        layers=layers,
        turn_index=turn_index,
        activation_state=activation_state,
        drift_score=drift_score,
        drift_evidence=drift_evidence,
    )
