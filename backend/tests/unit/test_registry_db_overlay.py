"""Unit tests for SoulRegistry DB overlay additions (C3a).

Covers:
- load_db_overlay: file-loaded builtins always win over same-id DB rows
- load_db_overlay: bad DB row is skipped; other rows succeed
- register_spec: upserts a new UGC spec and bumps generation
- register_spec: builtin ids are protected
- invalidate: removes a UGC spec and bumps generation
- invalidate: builtin ids are protected
- generation counter advances on mutations
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from heart.ss01_soul.registry import SoulRegistry, LoadReport
from heart.ss01_soul.schema_validator import SoulSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SOUL_SPECS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "soul_specs"


def _load_rin_spec() -> SoulSpec:
    with open(SOUL_SPECS_DIR / "rin" / "v1.0.0.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SoulSpec.model_validate(data)


def _make_ugc_spec(character_id: str = "test_ugc", spec_version: str = "1.0.0") -> SoulSpec:
    """Clone rin and override character_id / spec_version to make a fake UGC spec."""
    rin = _load_rin_spec()
    data = rin.model_dump()
    data["character_id"] = character_id
    data["spec_version"] = spec_version
    data["meta"]["author"] = f"user:test"
    return SoulSpec.model_validate(data)


def _fresh_registry() -> SoulRegistry:
    registry = SoulRegistry()
    registry.load_all()
    return registry


# ---------------------------------------------------------------------------
# load_db_overlay
# ---------------------------------------------------------------------------

class TestLoadDbOverlay:
    def test_valid_ugc_row_loaded(self):
        registry = _fresh_registry()
        ugc = _make_ugc_spec("ugc_alpha")
        gen_before = registry.generation

        row = {"character_id": "ugc_alpha", "spec": ugc.model_dump()}
        report = registry.load_db_overlay([row])

        assert "ugc_alpha" in report.loaded
        assert not report.skipped
        assert registry.generation > gen_before
        # Can be retrieved
        retrieved = registry.get_soul("ugc_alpha")
        assert retrieved.character_id == "ugc_alpha"

    def test_builtin_db_row_skipped(self):
        """A DB row with the same id as a file-loaded builtin must NOT overwrite it."""
        registry = _fresh_registry()
        rin = _load_rin_spec()
        rin_data = rin.model_dump()
        # Tamper with something to prove the file version wins
        rin_data["display_name"]["zh"] = "TAMPERED"

        row = {"character_id": "rin", "spec": rin_data}
        report = registry.load_db_overlay([row])

        assert "rin" not in report.loaded
        assert not report.skipped  # silently skipped, not an error
        assert registry.get_soul("rin").display_name.zh != "TAMPERED"

    def test_bad_db_row_skipped_others_succeed(self):
        registry = _fresh_registry()
        ugc_good = _make_ugc_spec("ugc_good")
        bad_row = {"character_id": "ugc_bad", "spec": {"totally": "invalid"}}
        good_row = {"character_id": "ugc_good", "spec": ugc_good.model_dump()}

        report = registry.load_db_overlay([bad_row, good_row])

        assert "ugc_good" in report.loaded
        assert len(report.skipped) == 1
        assert report.skipped[0]["character_id"] == "ugc_bad"
        # ugc_good is accessible
        assert registry.get_soul("ugc_good").character_id == "ugc_good"

    def test_returns_load_report_instance(self):
        registry = _fresh_registry()
        report = registry.load_db_overlay([])
        assert isinstance(report, LoadReport)
        assert report.loaded == []
        assert report.skipped == []

    def test_generation_unchanged_on_empty_overlay(self):
        registry = _fresh_registry()
        gen = registry.generation
        registry.load_db_overlay([])
        assert registry.generation == gen

    def test_spec_as_json_string_accepted(self):
        """asyncpg may sometimes return JSONB as a string."""
        registry = _fresh_registry()
        ugc = _make_ugc_spec("ugc_str")
        row = {"character_id": "ugc_str", "spec": json.dumps(ugc.model_dump())}
        report = registry.load_db_overlay([row])
        assert "ugc_str" in report.loaded


# ---------------------------------------------------------------------------
# register_spec
# ---------------------------------------------------------------------------

class TestRegisterSpec:
    def test_register_new_ugc_spec(self):
        registry = _fresh_registry()
        ugc = _make_ugc_spec("ugc_beta")
        gen_before = registry.generation

        registry.register_spec(ugc)

        assert "ugc_beta" in registry.list_characters()
        assert registry.generation == gen_before + 1

    def test_register_updates_existing_ugc(self):
        registry = _fresh_registry()
        ugc_v1 = _make_ugc_spec("ugc_upd", "1.0.0")
        ugc_v2 = _make_ugc_spec("ugc_upd", "1.1.0")
        registry.register_spec(ugc_v1)
        registry.register_spec(ugc_v2)
        assert "1.1.0" in registry.list_versions("ugc_upd")

    def test_register_builtin_id_protected(self):
        registry = _fresh_registry()
        rin = _load_rin_spec()
        gen_before = registry.generation

        registry.register_spec(rin, source="ugc")

        assert registry.generation == gen_before  # no change


# ---------------------------------------------------------------------------
# invalidate
# ---------------------------------------------------------------------------

class TestInvalidate:
    def test_invalidate_removes_ugc(self):
        registry = _fresh_registry()
        ugc = _make_ugc_spec("ugc_rm")
        registry.register_spec(ugc)
        gen_after_add = registry.generation

        registry.invalidate("ugc_rm")

        assert "ugc_rm" not in registry.list_characters()
        assert registry.generation > gen_after_add

    def test_invalidate_builtin_protected(self):
        registry = _fresh_registry()
        gen_before = registry.generation

        registry.invalidate("rin")

        assert "rin" in registry.list_characters()
        assert registry.generation == gen_before

    def test_invalidate_nonexistent_noop(self):
        registry = _fresh_registry()
        gen_before = registry.generation
        registry.invalidate("no_such_id")
        assert registry.generation == gen_before


# ---------------------------------------------------------------------------
# generation counter
# ---------------------------------------------------------------------------

class TestGeneration:
    def test_load_all_bumps_generation(self):
        registry = SoulRegistry()
        assert registry.generation == 0
        registry.load_all()
        assert registry.generation >= 1

    def test_each_register_bumps_by_one(self):
        registry = _fresh_registry()
        ugc_a = _make_ugc_spec("ugc_gen_a")
        ugc_b = _make_ugc_spec("ugc_gen_b")
        g0 = registry.generation
        registry.register_spec(ugc_a)
        assert registry.generation == g0 + 1
        registry.register_spec(ugc_b)
        assert registry.generation == g0 + 2
