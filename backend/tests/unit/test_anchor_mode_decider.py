"""
Unit tests for Anchor Mode Decider (SS01 §3.4).

Covers all cadence rules and the drift override.

Author: 心屿团队
"""

from __future__ import annotations

import pytest

from heart.ss01_soul.anchor_injector import AnchorActivationView, AnchorMode
from heart.ss01_soul.anchor_mode_decider import decide_mode


def _state(last_full_anchor_turn: int = 0) -> AnchorActivationView:
    return AnchorActivationView(
        resonance_score=0.5,
        unlocked_facet_ids=(),
        last_full_anchor_turn=last_full_anchor_turn,
    )


class TestFirstTurn:
    def test_turn_one_returns_full(self):
        assert decide_mode(_state(), turn_index=1, drift_score=0.0) == AnchorMode.FULL

    def test_turn_zero_also_returns_full(self):
        """Edge case: turn_index 0 should still be treated as first-contact."""
        assert decide_mode(_state(), turn_index=0, drift_score=0.0) == AnchorMode.FULL


class TestCadence:
    """Per §3.4 table: turn 1 FULL → turns 2-7 LIGHT → turn 8 FULL → ..."""

    @pytest.mark.parametrize("turn_index", [2, 3, 4, 5, 6, 7])
    def test_turns_two_through_seven_after_full_at_one(self, turn_index):
        result = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=turn_index,
            drift_score=0.0,
        )
        assert result == AnchorMode.LIGHT

    def test_turn_eight_after_full_at_one_returns_full(self):
        """Periodic re-injection per §3.4: gap of 7 → FULL."""
        result = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=8,
            drift_score=0.0,
        )
        assert result == AnchorMode.FULL

    @pytest.mark.parametrize("turn_index", [9, 10, 11, 12, 13, 14])
    def test_turns_after_second_full_are_light(self, turn_index):
        result = decide_mode(
            _state(last_full_anchor_turn=8),
            turn_index=turn_index,
            drift_score=0.0,
        )
        assert result == AnchorMode.LIGHT

    def test_third_full_after_gap_of_seven(self):
        result = decide_mode(
            _state(last_full_anchor_turn=8),
            turn_index=15,
            drift_score=0.0,
        )
        assert result == AnchorMode.FULL


class TestDriftOverride:
    """Per §3.4: drift_score > 0.3 → early FULL injection."""

    def test_high_drift_overrides_light_cadence(self):
        result = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=3,  # would normally be LIGHT
            drift_score=0.5,
        )
        assert result == AnchorMode.FULL

    def test_drift_threshold_boundary_just_above(self):
        result = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=3,
            drift_score=0.31,
        )
        assert result == AnchorMode.FULL

    def test_drift_threshold_exact_does_not_override(self):
        """drift_score > 0.3 means strictly greater."""
        result = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=3,
            drift_score=0.3,
        )
        assert result == AnchorMode.LIGHT

    def test_drift_just_below_threshold_does_not_override(self):
        result = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=3,
            drift_score=0.29,
        )
        assert result == AnchorMode.LIGHT


class TestNeverReturnsReinforce:
    """REINFORCE is selected by orchestrator with DriftEvidence, not here."""

    @pytest.mark.parametrize("drift_score", [0.0, 0.3, 0.5, 0.9, 1.0])
    @pytest.mark.parametrize("turn_index", [1, 2, 7, 8, 100])
    def test_never_returns_reinforce(self, drift_score, turn_index):
        result = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=turn_index,
            drift_score=drift_score,
        )
        assert result != AnchorMode.REINFORCE


class TestBoundaryConditions:
    def test_long_session_periodic_pattern(self):
        """Simulate a 30-turn session and check FULL re-injection rhythm."""
        last_full = 1
        full_turns = [1]
        for turn in range(2, 31):
            mode = decide_mode(
                _state(last_full_anchor_turn=last_full),
                turn_index=turn,
                drift_score=0.0,
            )
            if mode == AnchorMode.FULL:
                full_turns.append(turn)
                last_full = turn
        # Expect FULLs at turns 1, 8, 15, 22, 29 (every 7 turns)
        assert full_turns == [1, 8, 15, 22, 29]

    def test_drift_recovery_does_not_double_trigger(self):
        """If drift triggers FULL at turn 3, the cadence resets from there."""
        # Turn 3 with drift → FULL
        mode = decide_mode(
            _state(last_full_anchor_turn=1),
            turn_index=3,
            drift_score=0.5,
        )
        assert mode == AnchorMode.FULL

        # Now last_full = 3. Turn 4 with low drift should be LIGHT.
        mode = decide_mode(
            _state(last_full_anchor_turn=3),
            turn_index=4,
            drift_score=0.0,
        )
        assert mode == AnchorMode.LIGHT

        # Turn 10 should be FULL again (10 - 3 = 7).
        mode = decide_mode(
            _state(last_full_anchor_turn=3),
            turn_index=10,
            drift_score=0.0,
        )
        assert mode == AnchorMode.FULL
