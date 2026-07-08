"""Unit tests for reload.py (C3a) — authoritative character reload / invalidation.

Verifies that reload_character:
- registers a new spec into the module registry when spec is provided
- makes the character visible via is_known_character after reload
- invalidates (evicts) a UGC character when spec=None
- does not crash when the wiring cache_clear / reset_anchor_injector fail
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from heart.ss01_soul.registry import SoulSpec, _soul_registry
from heart.ss01_soul.reload import reload_character


SOUL_SPECS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "soul_specs"


def _make_ugc_spec(character_id: str = "ugc_reload_test") -> SoulSpec:
    with open(SOUL_SPECS_DIR / "rin" / "v1.0.0.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["character_id"] = character_id
    data["meta"]["author"] = "user:test"
    return SoulSpec.model_validate(data)


@pytest.fixture(autouse=True)
def _reset_module_registry():
    """Reset the module-level registry singleton between tests."""
    import heart.ss01_soul.registry as _reg_mod
    original = _reg_mod._soul_registry
    _reg_mod._soul_registry = None
    yield
    _reg_mod._soul_registry = original


def test_reload_with_spec_registers_character():
    ugc = _make_ugc_spec("ugc_reload_new")
    reload_character("ugc_reload_new", spec=ugc)

    from heart.ss01_soul.character_catalog import is_known_character
    assert is_known_character("ugc_reload_new")


def test_reload_without_spec_invalidates_character():
    from heart.ss01_soul.registry import get_soul_registry
    ugc = _make_ugc_spec("ugc_to_remove")
    registry = get_soul_registry()
    registry.register_spec(ugc)
    assert "ugc_to_remove" in registry.list_characters()

    reload_character("ugc_to_remove", spec=None)

    assert "ugc_to_remove" not in registry.list_characters()


def test_reload_tolerates_missing_wiring_module():
    """reload_character must not raise if wiring is unavailable (e.g. tests)."""
    ugc = _make_ugc_spec("ugc_no_wiring")
    with patch.dict("sys.modules", {"heart.api.wiring": None}):
        # Should not raise even if import fails
        reload_character("ugc_no_wiring", spec=ugc)


def test_reload_tolerates_anchor_injector_failure():
    """A broken AnchorInjector reset must not abort the reload."""
    ugc = _make_ugc_spec("ugc_anchor_fail")
    with patch("heart.ss01_soul.anchor_injector.reset_anchor_injector", side_effect=RuntimeError("boom")):
        reload_character("ugc_anchor_fail", spec=ugc)  # must not raise

    from heart.ss01_soul.character_catalog import is_known_character
    assert is_known_character("ugc_anchor_fail")
