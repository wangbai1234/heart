"""Unit tests for SS04 Special States (DRIFTING, COLD_WAR, RECONCILING, REUNION)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from heart.ss04_relationship.special_states import (
    SpecialState,
    advance_reunion_turn,
    evaluate_special_state,
    _get_current_special,
    _get_coldness_intensity,
)


def _make_signals(**kwargs):
    """Create a mock signals object."""
    signals = MagicMock()
    signals.warmth_signal_count = kwargs.get("warmth_signal_count", 0)
    signals.total_interactions = kwargs.get("total_interactions", 1)
    return signals


def _make_emotion_state(coldness=0.0, repair_progress=0.0):
    """Create a mock emotion state."""
    active_stack = []
    if coldness > 0:
        active_stack.append({"emotion": "coldness", "intensity": coldness})
    return {
        "active_stack": active_stack,
        "repair_progress": repair_progress,
    }


class TestColdWar:
    """Tests for COLD_WAR state."""

    def test_enter_cold_war_on_high_coldness(self):
        """Should enter COLD_WAR when coldness > 0.5."""
        emotion = _make_emotion_state(coldness=0.7)
        result = evaluate_special_state(
            current_states=[{"state": "none"}],
            signals=_make_signals(),
            days_since_last=0,
            emotion_state=emotion,
        )
        assert result == SpecialState.COLD_WAR

    def test_no_cold_war_on_low_coldness(self):
        """Should NOT enter COLD_WAR when coldness < 0.5."""
        emotion = _make_emotion_state(coldness=0.3)
        result = evaluate_special_state(
            current_states=[{"state": "none"}],
            signals=_make_signals(),
            days_since_last=0,
            emotion_state=emotion,
        )
        assert result is None

    def test_exit_cold_war_to_reconciling(self):
        """Should exit COLD_WAR → RECONCILING when repair_progress > 0.6."""
        emotion = _make_emotion_state(coldness=0.7, repair_progress=0.8)
        result = evaluate_special_state(
            current_states=[{"state": "cold_war"}],
            signals=_make_signals(),
            days_since_last=0,
            emotion_state=emotion,
        )
        assert result == SpecialState.RECONCILING

    def test_exit_cold_war_to_none_on_low_coldness(self):
        """Should exit COLD_WAR → NONE when coldness drops."""
        emotion = _make_emotion_state(coldness=0.1)
        result = evaluate_special_state(
            current_states=[{"state": "cold_war"}],
            signals=_make_signals(),
            days_since_last=0,
            emotion_state=emotion,
        )
        assert result == SpecialState.NONE

    def test_stay_in_cold_war(self):
        """Should stay in COLD_WAR when coldness still high."""
        emotion = _make_emotion_state(coldness=0.6, repair_progress=0.2)
        result = evaluate_special_state(
            current_states=[{"state": "cold_war"}],
            signals=_make_signals(),
            days_since_last=0,
            emotion_state=emotion,
        )
        assert result is None


class TestDrifting:
    """Tests for DRIFTING state."""

    def test_enter_drifting_on_long_absence(self):
        """Should enter DRIFTING when absence > 14 days."""
        result = evaluate_special_state(
            current_states=[{"state": "none"}],
            signals=_make_signals(),
            days_since_last=20,
            emotion_state=None,
        )
        assert result == SpecialState.DRIFTING

    def test_no_drifting_on_short_absence(self):
        """Should NOT enter DRIFTING when absence < 14 days."""
        result = evaluate_special_state(
            current_states=[{"state": "none"}],
            signals=_make_signals(),
            days_since_last=5,
            emotion_state=None,
        )
        assert result is None

    def test_exit_drifting_to_reunion(self):
        """Should exit DRIFTING → REUNION when user returns."""
        signals = _make_signals(total_interactions=5)
        result = evaluate_special_state(
            current_states=[{"state": "drifting"}],
            signals=signals,
            days_since_last=0.5,
            emotion_state=None,
        )
        assert result == SpecialState.REUNION

    def test_stay_in_drifting(self):
        """Should stay in DRIFTING when user hasn't returned."""
        result = evaluate_special_state(
            current_states=[{"state": "drifting"}],
            signals=_make_signals(),
            days_since_last=20,
            emotion_state=None,
        )
        assert result is None


class TestReconciling:
    """Tests for RECONCILING state."""

    def test_exit_reconciling_on_warmth(self):
        """Should exit RECONCILING → NONE on warmth signals."""
        signals = _make_signals(warmth_signal_count=3)
        result = evaluate_special_state(
            current_states=[{"state": "reconciling"}],
            signals=signals,
            days_since_last=0,
            emotion_state=None,
        )
        assert result == SpecialState.NONE

    def test_stay_in_reconciling(self):
        """Should stay in RECONCILING without enough warmth."""
        signals = _make_signals(warmth_signal_count=0)
        result = evaluate_special_state(
            current_states=[{"state": "reconciling"}],
            signals=signals,
            days_since_last=0,
            emotion_state=_make_emotion_state(repair_progress=0.3),
        )
        assert result is None


class TestReunion:
    """Tests for REUNION state."""

    def test_exit_reunion_after_10_turns(self):
        """Should exit REUNION → NONE after 10 turns."""
        result = evaluate_special_state(
            current_states=[{"state": "reunion", "turns_in_state": 10}],
            signals=_make_signals(),
            days_since_last=0,
            emotion_state=None,
        )
        assert result == SpecialState.NONE

    def test_stay_in_reunion(self):
        """Should stay in REUNION before 10 turns."""
        result = evaluate_special_state(
            current_states=[{"state": "reunion", "turns_in_state": 3}],
            signals=_make_signals(),
            days_since_last=0,
            emotion_state=None,
        )
        assert result is None


class TestAdvanceReunionTurn:
    """Tests for advance_reunion_turn."""

    def test_increments_turn(self):
        """Should increment turns_in_state for REUNION."""
        states = [{"state": "reunion", "turns_in_state": 3}]
        result = advance_reunion_turn(states)
        assert result[0]["turns_in_state"] == 4

    def test_no_change_for_non_reunion(self):
        """Should not change non-REUNION states."""
        states = [{"state": "cold_war", "turns_in_state": 0}]
        result = advance_reunion_turn(states)
        assert result[0]["turns_in_state"] == 0


class TestGetCurrentSpecial:
    """Tests for _get_current_special."""

    def test_returns_none_for_empty(self):
        assert _get_current_special([]) == SpecialState.NONE

    def test_returns_none_for_none_state(self):
        assert _get_current_special([{"state": "none"}]) == SpecialState.NONE

    def test_returns_cold_war(self):
        assert _get_current_special([{"state": "cold_war"}]) == SpecialState.COLD_WAR

    def test_returns_drifting(self):
        assert _get_current_special([{"state": "drifting"}]) == SpecialState.DRIFTING
