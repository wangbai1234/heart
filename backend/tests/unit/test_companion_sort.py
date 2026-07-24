"""Unit tests for the bond-center companion ordering (Wave 1).

The /api/companions endpoint is DB-heavy (raw SQL across four tables), so the
SQL join is covered in the integration tier. Here we pin the *pure* ordering
rule — which is where a subtle regression would actually hide — with no DB.
"""

from __future__ import annotations

from heart.api.routes_companions import sort_companions


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
