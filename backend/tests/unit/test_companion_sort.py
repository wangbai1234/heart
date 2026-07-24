"""Unit tests for the bond-center companion ordering (Wave 1).

The /api/companions endpoint is DB-heavy (raw SQL across four tables), so the
SQL join is covered in the integration tier. Here we pin the *pure* ordering
rule — which is where a subtle regression would actually hide — with no DB.
"""

from __future__ import annotations

from heart.api.routes_companions import _pick_story_hook, sort_companions


def _c(cid, *, unread=0, proactive=False, last_at=None, intimacy=0.0):
    return {
        "character_id": cid,
        "unread_count": unread,
        "has_proactive": proactive,
        "last_message_at": last_at,
        "intimacy": intimacy,
    }


def _order(companions):
    return [c["character_id"] for c in sort_companions(companions)]


def test_unread_floats_to_top():
    out = _order(
        [
            _c("a", last_at="2026-07-24T10:00:00+00:00", intimacy=0.9),
            _c("b", unread=2, last_at="2026-07-20T10:00:00+00:00", intimacy=0.1),
        ]
    )
    assert out == ["b", "a"]


def test_proactive_counts_as_active():
    out = _order(
        [
            _c("a", last_at="2026-07-24T10:00:00+00:00", intimacy=0.9),
            _c("b", proactive=True, last_at="2026-07-01T10:00:00+00:00", intimacy=0.0),
        ]
    )
    assert out == ["b", "a"]


def test_recency_orders_within_active_rank():
    out = _order(
        [
            _c("older", unread=1, last_at="2026-07-20T10:00:00+00:00"),
            _c("newer", unread=1, last_at="2026-07-24T10:00:00+00:00"),
        ]
    )
    assert out == ["newer", "older"]


def test_intimacy_is_final_tiebreak():
    # Same active rank, same recency (both None) → higher intimacy wins.
    out = _order(
        [
            _c("low", intimacy=0.2),
            _c("high", intimacy=0.8),
        ]
    )
    assert out == ["high", "low"]


def test_missing_recency_sinks_within_rank():
    out = _order(
        [
            _c("has_msg", last_at="2026-07-24T10:00:00+00:00"),
            _c("never_messaged", last_at=None, intimacy=0.5),
        ]
    )
    assert out == ["has_msg", "never_messaged"]


def test_full_priority_chain():
    companions = [
        _c("idle_high_intimacy", last_at=None, intimacy=0.95),
        _c("active_old", unread=1, last_at="2026-07-10T00:00:00+00:00"),
        _c("active_new", proactive=True, last_at="2026-07-24T00:00:00+00:00"),
        _c("idle_recent", last_at="2026-07-23T00:00:00+00:00", intimacy=0.1),
    ]
    # active first (new before old), then idle by recency, idle-no-msg last.
    assert _order(companions) == [
        "active_new",
        "active_old",
        "idle_recent",
        "idle_high_intimacy",
    ]


# ── Wave 3: story-hook eligibility (_pick_story_hook) ──────────────────────


def _hook(scenario_id="s1", *, stage_min="CONFIDANT", intimacy_min=0.0, title="t"):
    return {
        "scenario_id": scenario_id,
        "trigger_stage_min": stage_min,
        "trigger_intimacy_min": intimacy_min,
        "cooldown_hours": 72,
        "invite_title": title,
        "invite_copy": "copy",
        "cta_label": "进入剧情",
    }


def test_hook_none_when_no_hooks():
    assert _pick_story_hook([], "LOVER", 0.9) is None


def test_hook_eligible_when_stage_and_intimacy_met():
    got = _pick_story_hook([_hook(stage_min="CONFIDANT", intimacy_min=0.4)], "CONFIDANT", 0.4)
    assert got is not None
    assert got["scenario_id"] == "s1"
    # only frontend-facing keys are surfaced (no trigger_* internals)
    assert set(got) == {"scenario_id", "invite_title", "invite_copy", "cta_label", "cooldown_hours"}


def test_hook_higher_stage_qualifies_for_lower_threshold():
    # LOVER (rank 5) easily clears a CONFIDANT (rank 3) gate.
    assert _pick_story_hook([_hook(stage_min="CONFIDANT")], "LOVER", 0.9) is not None


def test_hook_blocked_when_stage_too_low():
    assert _pick_story_hook([_hook(stage_min="LOVER")], "FRIEND", 0.99) is None


def test_hook_blocked_when_intimacy_too_low():
    assert _pick_story_hook([_hook(stage_min="STRANGER", intimacy_min=0.8)], "BONDED", 0.5) is None


def test_hook_cold_war_never_eligible():
    # cold_war ranks -1 → hook_rank>=0 gate fails even at max intimacy.
    assert (
        _pick_story_hook([_hook(stage_min="STRANGER", intimacy_min=0.0)], "cold_war", 1.0) is None
    )


def test_hook_picks_highest_threshold_among_eligible():
    hooks = [
        _hook("low", stage_min="ACQUAINTANCE", intimacy_min=0.1, title="low"),
        _hook("high", stage_min="ROMANTIC_INTEREST", intimacy_min=0.5, title="high"),
    ]
    got = _pick_story_hook(hooks, "LOVER", 0.9)
    assert got is not None and got["scenario_id"] == "high"


def test_hook_unknown_stage_string_is_ineligible():
    assert _pick_story_hook([_hook(stage_min="CONFIDANT")], "NOT_A_STAGE", 0.9) is None
