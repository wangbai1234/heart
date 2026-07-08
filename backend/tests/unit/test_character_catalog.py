"""Unit tests for the character catalog logic (UGC refactor C2).

Covers the pure shaping / visibility / validation layer over the ``characters``
table — no database required. The endpoint itself (SQL + auth) is exercised in
the integration tier; here we pin the rules that decide *what* a viewer sees and
*which* ids are accepted at the boundary.
"""

from __future__ import annotations

from uuid import uuid4

from heart.ss01_soul.character_catalog import (
    CharacterRow,
    build_catalog_entries,
    is_known_character,
    visible_to,
)

VIEWER = uuid4()
OTHER = uuid4()


# ── Visibility rules ────────────────────────────────────────────────────────


def test_public_active_visible_to_anyone():
    row = CharacterRow(id="rin", owner_user_id=None, visibility="public", status="active")
    assert visible_to(row, VIEWER) is True
    assert visible_to(row, OTHER) is True


def test_disabled_never_visible():
    row = CharacterRow(id="rin", owner_user_id=None, visibility="public", status="disabled")
    assert visible_to(row, VIEWER) is False


def test_private_visible_only_to_owner():
    row = CharacterRow(id="ugc1", owner_user_id=VIEWER, visibility="private", status="active")
    assert visible_to(row, VIEWER) is True
    assert visible_to(row, OTHER) is False


def test_unlisted_visible_only_to_owner():
    row = CharacterRow(id="ugc2", owner_user_id=VIEWER, visibility="unlisted", status="active")
    assert visible_to(row, VIEWER) is True
    assert visible_to(row, OTHER) is False


# ── Catalog shaping ─────────────────────────────────────────────────────────


def test_builtins_come_first_then_by_id():
    rows = [
        CharacterRow(id="zeta", owner_user_id=VIEWER, visibility="private", status="active"),
        CharacterRow(id="rin", owner_user_id=None, visibility="public", status="active"),
        CharacterRow(id="dorothy", owner_user_id=None, visibility="public", status="active"),
    ]
    entries = build_catalog_entries(rows, VIEWER)
    assert [e.id for e in entries] == ["dorothy", "rin", "zeta"]
    assert entries[0].is_builtin is True
    assert entries[-1].is_builtin is False
    assert entries[-1].is_owner is True


def test_other_users_private_row_filtered_out():
    rows = [
        CharacterRow(id="rin", owner_user_id=None, visibility="public", status="active"),
        CharacterRow(id="secret", owner_user_id=OTHER, visibility="private", status="active"),
    ]
    entries = build_catalog_entries(rows, VIEWER)
    assert [e.id for e in entries] == ["rin"]


def test_builtin_display_name_derived_from_soul_spec():
    rows = [CharacterRow(id="rin", owner_user_id=None, visibility="public", status="active")]
    entries = build_catalog_entries(rows, VIEWER)
    # Derived from the Soul Spec, not stored on the row (note the space).
    assert entries[0].display_name == "神无月 凛"
    assert entries[0].is_owner is False


# ── Boundary validation ─────────────────────────────────────────────────────


def test_is_known_character_true_for_builtins():
    assert is_known_character("rin") is True
    assert is_known_character("dorothy") is True


def test_is_known_character_false_for_unknown():
    assert is_known_character("not_a_real_character") is False
    assert is_known_character("") is False
