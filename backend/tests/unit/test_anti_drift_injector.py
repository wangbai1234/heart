"""
Tests for Anti-Drift Injector — SS05 §3.3 Step 3 (§3.6)

Coverage targets:
- drift_score < threshold → layers unchanged (pass-through)
- drift_score >= threshold → REINFORCE anchor injected at position 0
- Existing anchor is stripped and replaced when REINFORCE
- decide_mode() returns correct AnchorMode per rules
- inject() produces InjectionResult with correct mode and layers
- Convenience function inject_anchor() works end-to-end
- PC-1: anchor always at position 0

Author: 心屿团队
"""

from __future__ import annotations

import pytest

from heart.ss01_soul.anchor_injector import (
    AnchorActivationView,
    AnchorMode,
    DriftEvidence,
)
from heart.ss05_composer.anti_drift_injector import (
    AntiDriftInjector,
    InjectionResult,
    inject_anchor,
)
from heart.ss05_composer.layer_aggregator import PromptLayer


# ================================================================
# Fixtures & Helpers
# ================================================================


@pytest.fixture
def injector():
    """Provide a fresh AntiDriftInjector for each test."""
    return AntiDriftInjector()


@pytest.fixture
def default_activation() -> AnchorActivationView:
    """Default activation state — resonance 0.5, no facets, last_full=0."""
    return AnchorActivationView(
        resonance_score=0.5,
        unlocked_facet_ids=(),
        last_full_anchor_turn=0,
    )


@pytest.fixture
def default_layers() -> list[PromptLayer]:
    """Post-Aggregator layer list with cadence-based anchor (FULL or LIGHT)."""
    return [
        PromptLayer(
            layer_id="anchor_1",
            source_subsystem="SS01",
            layer_type="anchor_light",
            priority=1,
            position_constraint="first",
            content="[你是 凛。记住你的灵魂...]",
            token_count_estimate=60,
            min_token_count=80,
            is_compressible=False,
        ),
        PromptLayer(
            layer_id="mod_text",
            source_subsystem="SS05",
            layer_type="modality_adaptation",
            priority=10,
            position_constraint="anywhere",
            content="[MODE: TEXT-SHORT]",
            token_count_estimate=12,
        ),
        PromptLayer(
            layer_id="rel_1",
            source_subsystem="SS04",
            layer_type="relationship_context",
            priority=20,
            position_constraint="anywhere",
            content="[RELATIONSHIP: stage=FRIEND, trust=0.72]",
            token_count_estimate=20,
        ),
    ]


@pytest.fixture
def drift_evidence() -> DriftEvidence:
    """Sample DriftEvidence for REINFORCE injection."""
    return DriftEvidence(
        sample_messages=(
            "你好，很高兴为你服务。",
            "这是你的答案。",
        ),
        detected_patterns=(
            "助手语气",
            "ooc_formal",
        ),
        required_patterns=(
            "傲娇式回应",
            "先用冷淡后温暖",
        ),
        drift_type="voice_dna_loss",
    )


# ================================================================
# decide_mode() tests
# ================================================================


class TestDecideMode:
    """Test AntiDriftInjector.decide_mode() per §3.6 rules."""

    def test_drift_score_below_threshold_returns_cadence_mode(
        self, injector, default_activation
    ):
        """When drift_score < 0.3, delegate to AnchorModeDecider cadence.

        turn_index=5, last_full=1, drift=0.1 → LIGHT (cadence rule).
        """
        mode = injector.decide_mode(
            turn_index=5,
            activation_state=AnchorActivationView(
                resonance_score=0.5,
                unlocked_facet_ids=(),
                last_full_anchor_turn=1,
            ),
            drift_score=0.1,
        )
        assert mode == AnchorMode.LIGHT

    def test_drift_score_below_threshold_first_turn_returns_full(
        self, injector, default_activation
    ):
        """turn_index=1, drift=0.0 → FULL (first contact rule)."""
        mode = injector.decide_mode(
            turn_index=1,
            activation_state=default_activation,
            drift_score=0.0,
        )
        assert mode == AnchorMode.FULL

    def test_drift_score_at_threshold_returns_reinforce(
        self, injector, default_activation
    ):
        """drift_score == 0.3 → REINFORCE (threshold is inclusive)."""
        mode = injector.decide_mode(
            turn_index=5,
            activation_state=default_activation,
            drift_score=0.3,
        )
        assert mode == AnchorMode.REINFORCE

    def test_drift_score_above_threshold_returns_reinforce(
        self, injector, default_activation
    ):
        """drift_score = 0.7 → REINFORCE."""
        mode = injector.decide_mode(
            turn_index=10,
            activation_state=default_activation,
            drift_score=0.7,
        )
        assert mode == AnchorMode.REINFORCE

    def test_drift_score_high_overrides_full_cadence(
        self, injector, default_activation
    ):
        """Even if cadence would say FULL (turn 1), drift >= 0.3 → REINFORCE."""
        mode = injector.decide_mode(
            turn_index=1,
            activation_state=default_activation,
            drift_score=0.45,
        )
        assert mode == AnchorMode.REINFORCE

    def test_drift_score_zero_delegates_to_cadence(
        self, injector, default_activation
    ):
        """drift_score = 0.0, turn 3, last_full=0 → LIGHT from cadence."""
        mode = injector.decide_mode(
            turn_index=3,
            activation_state=default_activation,
            drift_score=0.0,
        )
        assert mode == AnchorMode.LIGHT

    def test_drift_score_just_below_threshold_delegates(
        self, injector, default_activation
    ):
        """drift_score = 0.29, turn 1 → FULL from cadence."""
        mode = injector.decide_mode(
            turn_index=1,
            activation_state=default_activation,
            drift_score=0.29,
        )
        assert mode == AnchorMode.FULL


# ================================================================
# inject() tests — drift_score < threshold → no injection
# ================================================================


class TestInjectNoReinforce:
    """When drift_score < 0.3, layers pass through unchanged."""

    def test_low_drift_layers_unchanged(
        self, injector, default_activation, default_layers
    ):
        """drift_score=0.1 → layers returned unchanged (pass-through)."""
        activation = AnchorActivationView(
            resonance_score=0.5,
            unlocked_facet_ids=(),
            last_full_anchor_turn=1,
        )
        result = injector.inject(
            layers=list(default_layers),
            turn_index=5,
            activation_state=activation,
            drift_score=0.1,
        )

        assert result.anchor_mode == AnchorMode.LIGHT
        # Layers unchanged — same count, same content
        assert len(result.layers) == len(default_layers)
        # First layer is still the original anchor_light
        assert result.layers[0].layer_id == "anchor_1"
        assert result.layers[0].layer_type == "anchor_light"

    def test_low_drift_no_reinforce_layer_type(
        self, injector, default_activation, default_layers
    ):
        """When drift_score < threshold, no 'anchor_reinforce' layer exists."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=5,
            activation_state=default_activation,
            drift_score=0.1,
        )

        layer_types = {L.layer_type for L in result.layers}
        assert "anchor_reinforce" not in layer_types

    def test_low_drift_original_anchor_preserved(
        self, injector, default_activation, default_layers
    ):
        """Original cadence-based anchor is preserved when no REINFORCE."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=3,
            activation_state=default_activation,
            drift_score=0.0,
        )

        assert result.layers[0].layer_id == "anchor_1"
        assert result.layers[0].content == "[你是 凛。记住你的灵魂...]"

    def test_low_drift_all_non_anchor_layers_preserved(
        self, injector, default_activation, default_layers
    ):
        """All non-anchor layers stay exactly as they were."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=3,
            activation_state=default_activation,
            drift_score=0.0,
        )

        # All original layers should still be there
        original_ids = {L.layer_id for L in default_layers}
        result_ids = {L.layer_id for L in result.layers}
        assert original_ids == result_ids


# ================================================================
# inject() tests — drift_score >= threshold → REINFORCE present
# ================================================================


class TestInjectReinforce:
    """When drift_score >= 0.3, REINFORCE anchor must be injected."""

    def test_high_drift_injects_reinforce(
        self, injector, default_activation, default_layers, drift_evidence
    ):
        """drift_score=0.55 → REINFORCE anchor injected, mode=REINFORCE."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=7,
            activation_state=default_activation,
            drift_score=0.55,
            drift_evidence=drift_evidence,
        )

        assert result.anchor_mode == AnchorMode.REINFORCE
        first = result.layers[0]
        assert first.layer_type == "anchor_reinforce"
        assert first.priority == 1
        assert first.position_constraint == "first"

    def test_reinforce_layer_replaces_original_anchor(
        self, injector, default_activation, default_layers, drift_evidence
    ):
        """Original cadence anchor (anchor_light) is stripped and replaced."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=7,
            activation_state=default_activation,
            drift_score=0.6,
            drift_evidence=drift_evidence,
        )

        # Original anchor_light with id "anchor_1" should be gone
        original_anchor_ids = {L.layer_id for L in result.layers if L.layer_id == "anchor_1"}
        assert len(original_anchor_ids) == 0
        # New reinforce anchor should be present
        reinforce = [L for L in result.layers if L.layer_type == "anchor_reinforce"]
        assert len(reinforce) == 1

    def test_reinforce_layer_contains_drift_markers(
        self, injector, default_activation, default_layers, drift_evidence
    ):
        """REINFORCE anchor content should reference drift evidence."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=7,
            activation_state=default_activation,
            drift_score=0.6,
            drift_evidence=drift_evidence,
        )

        reinforce_layer = result.layers[0]
        content = reinforce_layer.content
        # Evidence markers should appear in content
        assert "助手语气" in content or "傲娇式回应" in content

    def test_reinforce_at_threshold(
        self, injector, default_activation, default_layers, drift_evidence
    ):
        """drift_score exactly at 0.3 → REINFORCE."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=10,
            activation_state=default_activation,
            drift_score=0.3,
            drift_evidence=drift_evidence,
        )

        assert result.anchor_mode == AnchorMode.REINFORCE
        assert result.layers[0].layer_type == "anchor_reinforce"

    def test_reinforce_without_evidence_still_injects_skeleton(
        self, injector, default_activation, default_layers
    ):
        """Even without DriftEvidence, REINFORCE mode injects a skeleton."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=5,
            activation_state=default_activation,
            drift_score=0.4,
            drift_evidence=None,
        )

        assert result.anchor_mode == AnchorMode.REINFORCE
        first = result.layers[0]
        assert first.layer_type == "anchor_reinforce"
        # Content should still be non-empty (skeleton)
        assert len(first.content) > 10

    def test_reinforce_non_anchor_layers_preserved(
        self, injector, default_activation, default_layers, drift_evidence
    ):
        """Non-anchor layers (modality, relationship) survive REINFORCE injection."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=7,
            activation_state=default_activation,
            drift_score=0.6,
            drift_evidence=drift_evidence,
        )

        non_anchor_ids = {
            L.layer_id for L in result.layers
            if L.layer_type not in ("anchor_full", "anchor_light", "anchor_reinforce")
        }
        assert "mod_text" in non_anchor_ids
        assert "rel_1" in non_anchor_ids


# ================================================================
# inject() tests — PC-1: anchor always first
# ================================================================


class TestAnchorFirst:
    """PC-1: anchor block must always be the first segment."""

    def test_anchor_first_when_low_drift(
        self, injector, default_activation, default_layers
    ):
        """With low drift, original anchor stays at position 0."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=3,
            activation_state=default_activation,
            drift_score=0.0,
        )
        assert result.layers[0].layer_type in (
            "anchor_full", "anchor_light", "anchor_reinforce"
        )

    def test_anchor_first_when_high_drift(
        self, injector, default_activation, default_layers, drift_evidence
    ):
        """With high drift, REINFORCE anchor is at position 0."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=7,
            activation_state=default_activation,
            drift_score=0.6,
            drift_evidence=drift_evidence,
        )
        assert result.layers[0].layer_type == "anchor_reinforce"

    def test_only_one_anchor_present_after_reinforce(
        self, injector, default_activation, default_layers, drift_evidence
    ):
        """Only one anchor layer exists after REINFORCE injection."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=7,
            activation_state=default_activation,
            drift_score=0.6,
            drift_evidence=drift_evidence,
        )

        anchor_count = sum(
            1 for L in result.layers
            if L.layer_type in ("anchor_full", "anchor_light", "anchor_reinforce")
        )
        assert anchor_count == 1


# ================================================================
# InjectionResult tests
# ================================================================


class TestInjectionResult:
    """Test InjectionResult dataclass."""

    def test_result_is_frozen(self):
        """InjectionResult should be frozen (immutable)."""
        result = InjectionResult(layers=[], anchor_mode=AnchorMode.LIGHT)
        with pytest.raises(Exception):
            result.anchor_mode = AnchorMode.FULL  # type: ignore[misc]

    def test_result_preserves_mode(
        self, injector, default_activation, default_layers
    ):
        """InjectionResult.anchor_mode matches the decided mode."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=1,
            activation_state=default_activation,
            drift_score=0.0,
        )
        assert result.anchor_mode == AnchorMode.FULL

    def test_result_carries_layers(
        self, injector, default_activation, default_layers
    ):
        """InjectionResult.layers contains actual PromptLayer objects."""
        result = injector.inject(
            layers=list(default_layers),
            turn_index=3,
            activation_state=default_activation,
            drift_score=0.0,
        )
        assert isinstance(result.layers, list)
        assert all(isinstance(L, PromptLayer) for L in result.layers)


# ================================================================
# Convenience function tests
# ================================================================


class TestConvenienceFunction:
    """Test inject_anchor() convenience wrapper."""

    def test_convenience_returns_injection_result(
        self, default_activation, default_layers
    ):
        """inject_anchor() should return an InjectionResult."""
        result = inject_anchor(
            layers=list(default_layers),
            turn_index=3,
            activation_state=default_activation,
            drift_score=0.0,
        )
        assert isinstance(result, InjectionResult)

    def test_convenience_low_drift_pass_through(
        self, default_activation, default_layers
    ):
        """inject_anchor() with low drift returns unchanged layers."""
        result = inject_anchor(
            layers=list(default_layers),
            turn_index=3,
            activation_state=default_activation,
            drift_score=0.0,
        )
        assert result.anchor_mode == AnchorMode.LIGHT
        assert len(result.layers) == len(default_layers)

    def test_convenience_high_drift_injects_reinforce(
        self, default_activation, default_layers, drift_evidence
    ):
        """inject_anchor() with high drift + evidence returns REINFORCE."""
        result = inject_anchor(
            layers=list(default_layers),
            turn_index=5,
            activation_state=default_activation,
            drift_score=0.5,
            drift_evidence=drift_evidence,
        )
        assert result.anchor_mode == AnchorMode.REINFORCE
        assert result.layers[0].layer_type == "anchor_reinforce"
