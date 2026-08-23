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


def test_seeded_builtin_uses_authored_tagline():
    rows = [
        CharacterRow(id="rin", owner_user_id=None, visibility="public", status="active")
    ]
    entries = build_catalog_entries(rows, VIEWER, taglines={"rin": "一条数据库里的剧情钩子"})
    assert entries[0].tagline == "一条数据库里的剧情钩子"


# ── Boundary validation ─────────────────────────────────────────────────────


def test_is_known_character_true_for_builtins():
    assert is_known_character("rin") is True
    assert is_known_character("dorothy") is True


def test_is_known_character_false_for_unknown():
    assert is_known_character("not_a_real_character") is False
    assert is_known_character("") is False


# ── ensure_character_loaded (multi-worker lazy hydration) ────────────────────

import pytest  # noqa: E402
import yaml  # noqa: E402
from pathlib import Path  # noqa: E402

from heart.ss01_soul.character_catalog import ensure_character_loaded  # noqa: E402
from heart.ss01_soul.schema_validator import SoulSpec  # noqa: E402

_SOUL_SPECS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "soul_specs"


def _make_ugc_row(character_id: str) -> dict:
    """A soul_specs DB row (as fetch_active_spec returns) for a fake UGC id,
    cloned off the rin builtin so it validates."""
    with open(_SOUL_SPECS_DIR / "rin" / "v1.0.0.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    spec = SoulSpec.model_validate(data)
    d = spec.model_dump()
    d["character_id"] = character_id
    d["meta"]["author"] = "user:test"
    return {"character_id": character_id, "spec_version": "1.0.0", "source": "ugc", "spec": d}


@pytest.mark.asyncio
async def test_ensure_loaded_short_circuits_for_known_without_db(monkeypatch):
    """A builtin already in the registry is confirmed without any DB round-trip."""
    import heart.ss01_soul.spec_store as spec_store

    async def _boom(*a, **k):
        raise AssertionError("DB should not be touched for a known id")

    monkeypatch.setattr(spec_store, "fetch_active_spec", _boom)
    assert await ensure_character_loaded("rin", object()) is True


@pytest.mark.asyncio
async def test_ensure_loaded_hydrates_from_db_on_miss(monkeypatch):
    """An id absent from this worker's registry but present in the DB is
    hydrated on the hot path and then reported known (the --workers 2 skew fix)."""
    import heart.ss01_soul.spec_store as spec_store
    from heart.ss01_soul.character_catalog import is_known_character

    cid = "ugc_ensure_hydrate"
    assert is_known_character(cid) is False  # not loaded yet

    async def _fetch(db, character_id):
        assert character_id == cid
        return _make_ugc_row(cid)

    monkeypatch.setattr(spec_store, "fetch_active_spec", _fetch)
    assert await ensure_character_loaded(cid, object()) is True
    # And it stays known for subsequent (same-process) requests.
    assert is_known_character(cid) is True


@pytest.mark.asyncio
async def test_ensure_loaded_false_when_db_miss(monkeypatch):
    import heart.ss01_soul.spec_store as spec_store

    async def _fetch(db, character_id):
        return None

    monkeypatch.setattr(spec_store, "fetch_active_spec", _fetch)
    assert await ensure_character_loaded("ugc_never_existed", object()) is False


@pytest.mark.asyncio
async def test_ensure_loaded_fails_closed_on_db_error(monkeypatch):
    """A DB error must fail closed (return False), never wave an unknown id through."""
    import heart.ss01_soul.spec_store as spec_store

    async def _fetch(db, character_id):
        raise RuntimeError("db down")

    monkeypatch.setattr(spec_store, "fetch_active_spec", _fetch)
    assert await ensure_character_loaded("ugc_db_error", object()) is False
