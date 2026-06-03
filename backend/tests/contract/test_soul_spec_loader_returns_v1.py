"""
Contract: SoulRegistry.load_all() returns v1 SoulSpec dicts.
per runtime_specs/01_identity_anchor_soul_spec.md §3.2

Verifies SoulSpec v1 schema contract that all downstream subsystems depend on.
"""

import pytest


@pytest.mark.contract
class TestSoulSpecLoaderReturnsV1:
    """SoulRegistry must expose v1 SoulSpec dicts with required sections."""

    REQUIRED_SECTIONS = [
        "character_id",
        "spec_version",
        "identity_anchor",
        "inertia_profile",
        "relational_template",
    ]

    IDENTITY_ANCHOR_FIELDS = [
        "archetype",
        "core_wound",
        "core_desire",
        "core_fear",
        "core_belief",
        "voice_dna",
        "anti_patterns",
    ]

    def test_soul_registry_loads_all_characters(self, make_soul_spec):
        """SoulRegistry can load specs and returns valid dicts."""
        spec = make_soul_spec(character_id="rin")
        for section in self.REQUIRED_SECTIONS:
            assert section in spec, f"Missing required section: {section}"

    def test_soul_spec_identity_anchor_has_required_fields(self, make_soul_spec):
        """Identity anchor must have all required sub-fields."""
        spec = make_soul_spec()
        anchor = spec["identity_anchor"]
        for field in self.IDENTITY_ANCHOR_FIELDS:
            assert field in anchor, f"Missing identity anchor field: {field}"

    def test_soul_spec_voice_dna_is_non_empty(self, make_soul_spec):
        """voice_dna list must be non-empty."""
        spec = make_soul_spec()
        assert len(spec["identity_anchor"]["voice_dna"]) > 0

    def test_soul_spec_has_inertia_profile(self, make_soul_spec):
        """Soul spec must expose inertia_profile for SS03 emotion state machine."""
        spec = make_soul_spec()
        assert "inertia_profile" in spec
        assert "max_valence_change_per_turn" in spec["inertia_profile"]

    def test_soul_spec_has_relational_template(self, make_soul_spec):
        """Soul spec must expose relational_template for SS04 relationship engine."""
        spec = make_soul_spec()
        assert "relational_template" in spec
        assert "intimacy_resistance" in spec["relational_template"]
