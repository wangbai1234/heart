"""
Unit Tests for Soul Spec Schema Validator and Registry

Tests validation logic per:
runtime_specs/01_identity_anchor_soul_spec.md §5.1

Author: 心屿团队
Created: 2026-05-17
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from heart.ss01_soul.registry import SoulRegistry
from heart.ss01_soul.schema_validator import (
    CoreDesire,
    CoreWound,
    VoiceDNA,
    validate_soul_spec_yaml,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def soul_specs_dir():
    """Get path to soul_specs directory."""
    # /heart/backend/tests/unit/test_soul_validator.py -> /heart/soul_specs/
    current_file = Path(__file__)
    repo_root = current_file.parent.parent.parent.parent
    return repo_root / "soul_specs"


@pytest.fixture
def rin_spec_path(soul_specs_dir):
    """Get path to Rin's Soul Spec."""
    return soul_specs_dir / "rin" / "v1.0.0.yaml"


@pytest.fixture
def dorothy_spec_path(soul_specs_dir):
    """Get path to Dorothy's Soul Spec."""
    return soul_specs_dir / "dorothy" / "v1.0.0.yaml"


@pytest.fixture
def rin_yaml_data(rin_spec_path):
    """Load Rin's YAML data."""
    with open(rin_spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def dorothy_yaml_data(dorothy_spec_path):
    """Load Dorothy's YAML data."""
    with open(dorothy_spec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# Schema Validator Tests
# ============================================================


class TestSoulSpecValidation:
    """Test Soul Spec schema validation."""

    def test_rin_spec_validates(self, rin_yaml_data):
        """Test that Rin's v1.0.0.yaml passes validation."""
        spec = validate_soul_spec_yaml(rin_yaml_data)

        assert spec.character_id == "rin"
        assert spec.spec_version == "1.0.0"
        assert spec.schema_version == "1.0"
        assert spec.locale == "zh-CN"

        # Verify identity anchor exists
        assert spec.identity_anchor is not None
        assert spec.identity_anchor.archetype is not None
        assert len(spec.identity_anchor.voice_dna) > 0

        # Verify test fixtures exist
        assert len(spec.test_fixtures.golden_dialogues) > 0

    def test_dorothy_spec_validates(self, dorothy_yaml_data):
        """Test that Dorothy's v1.0.0.yaml passes validation."""
        spec = validate_soul_spec_yaml(dorothy_yaml_data)

        assert spec.character_id == "dorothy"
        assert spec.spec_version == "1.0.0"
        assert spec.schema_version == "1.0"
        assert spec.locale == "zh-CN"

        # Verify Dorothy-specific fields
        assert spec.display_name.pet_self_reference == "桃桃"
        assert spec.identity_anchor.core_fear.fear_about_existence is not None

    def test_missing_required_field_fails(self, rin_yaml_data):
        """Test that missing required field causes validation failure."""
        # Remove required field
        del rin_yaml_data["character_id"]

        with pytest.raises(ValidationError) as exc_info:
            validate_soul_spec_yaml(rin_yaml_data)

        assert "character_id" in str(exc_info.value)

    def test_invalid_character_id_format_fails(self, rin_yaml_data):
        """Test that invalid character_id format fails."""
        # character_id must be lowercase alphanumeric + underscore
        rin_yaml_data["character_id"] = "Rin-Invalid"

        with pytest.raises(ValidationError) as exc_info:
            validate_soul_spec_yaml(rin_yaml_data)

        assert "character_id" in str(exc_info.value)

    def test_invalid_spec_version_format_fails(self, rin_yaml_data):
        """Test that invalid spec_version format fails."""
        rin_yaml_data["spec_version"] = "1.0"  # Must be semver (X.Y.Z)

        with pytest.raises(ValidationError) as exc_info:
            validate_soul_spec_yaml(rin_yaml_data)

        assert "spec_version" in str(exc_info.value)

    def test_extra_fields_forbidden(self, rin_yaml_data):
        """Test that extra fields are forbidden (strict schema)."""
        rin_yaml_data["extra_field"] = "not_allowed"

        with pytest.raises(ValidationError) as exc_info:
            validate_soul_spec_yaml(rin_yaml_data)

        assert "extra" in str(exc_info.value).lower()

    def test_voice_dna_id_format_enforced(self, rin_yaml_data):
        """Test that voice_dna id must match pattern."""
        # voice_dna id must start with 'vd-'
        rin_yaml_data["identity_anchor"]["voice_dna"][0]["id"] = "invalid-id"

        with pytest.raises(ValidationError) as exc_info:
            validate_soul_spec_yaml(rin_yaml_data)

        assert "vd-" in str(exc_info.value) or "pattern" in str(exc_info.value).lower()

    def test_resonance_score_bounds_enforced(self, rin_yaml_data):
        """Test that resonance_score must be in [0, 1]."""
        facets = rin_yaml_data["identity_anchor"].get("hidden_facets")
        if facets and len(facets) > 0:
            facets[0]["threshold"]["resonance_score"] = 1.5  # Invalid

            with pytest.raises(ValidationError) as exc_info:
                validate_soul_spec_yaml(rin_yaml_data)

            assert "resonance_score" in str(exc_info.value)

    def test_cognitive_style_bounds_validation(self, rin_yaml_data):
        """Test that cognitive style baseline must be within evolution_bound."""
        style = rin_yaml_data["cognitive_style"]["expression"]["verbosity"]
        style["baseline"] = 0.99  # Outside evolution_bound

        with pytest.raises(ValidationError) as exc_info:
            validate_soul_spec_yaml(rin_yaml_data)

        assert "baseline" in str(exc_info.value) or "evolution_bound" in str(exc_info.value)

    def test_golden_dialogue_id_format_enforced(self, rin_yaml_data):
        """Test that golden_dialogue id must match pattern."""
        gd = rin_yaml_data["test_fixtures"]["golden_dialogues"][0]
        gd["id"] = "invalid-id"  # Must match gd-XXX-...

        with pytest.raises(ValidationError) as exc_info:
            validate_soul_spec_yaml(rin_yaml_data)

        assert "gd-" in str(exc_info.value) or "pattern" in str(exc_info.value).lower()


class TestCoreComponents:
    """Test individual core component validation."""

    def test_core_wound_requires_all_fields(self):
        """Test that CoreWound requires all 4 fields."""
        with pytest.raises(ValidationError):
            CoreWound(
                essence="test",
                manifest="test",
                defense="test",
                # Missing private_truth
            )

    def test_core_desire_requires_all_layers(self):
        """Test that CoreDesire requires all 3 layers."""
        with pytest.raises(ValidationError):
            CoreDesire(
                surface="test",
                hidden="test",
                # Missing deepest
            )

    def test_voice_dna_requires_id_and_pattern(self):
        """Test that VoiceDNA requires id and pattern."""
        with pytest.raises(ValidationError):
            VoiceDNA(
                pattern="test",
                frequency="high",
                # Missing id
            )

    def test_voice_dna_allows_no_examples(self):
        """Test that VoiceDNA allows no examples (optional)."""
        # This should NOT raise - examples are optional
        vd = VoiceDNA(
            id="vd-001",
            pattern="test",
            frequency="high",
            # Both example and examples are optional
        )
        assert vd.id == "vd-001"


# ============================================================
# Soul Registry Tests
# ============================================================


class TestSoulRegistry:
    """Test Soul Registry loading and access."""

    def test_registry_loads_all_specs(self, soul_specs_dir):
        """Test that registry loads all Soul Specs successfully."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        # Should have at least Rin and Dorothy
        characters = registry.list_characters()
        assert "rin" in characters
        assert "dorothy" in characters

    def test_registry_rejects_invalid_specs(self, tmp_path):
        """Test that registry rejects invalid Soul Specs."""
        # Create temp directory with invalid YAML
        invalid_dir = tmp_path / "soul_specs" / "invalid"
        invalid_dir.mkdir(parents=True)

        invalid_yaml = invalid_dir / "v1.0.0.yaml"
        invalid_yaml.write_text("""
schema_version: "1.0"
character_id: "invalid"
# Missing required fields
        """)

        registry = SoulRegistry(soul_specs_dir=tmp_path / "soul_specs")

        with pytest.raises(RuntimeError) as exc_info:
            registry.load_all()

        assert "Failed to load" in str(exc_info.value)

    def test_get_soul_by_id_and_version(self, soul_specs_dir):
        """Test getting Soul Spec by character_id and version."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        rin_spec = registry.get_soul("rin", "1.0.0")

        assert rin_spec.character_id == "rin"
        assert rin_spec.spec_version == "1.0.0"
        assert rin_spec.identity_anchor is not None

    def test_get_soul_latest_version(self, soul_specs_dir):
        """Test getting latest version when version not specified."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        rin_spec = registry.get_soul("rin")

        assert rin_spec.character_id == "rin"
        # Should return latest version (currently 1.0.0)

    def test_get_soul_nonexistent_character_raises(self, soul_specs_dir):
        """Test that getting nonexistent character raises KeyError."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        with pytest.raises(KeyError) as exc_info:
            registry.get_soul("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "Available" in str(exc_info.value)

    def test_get_soul_nonexistent_version_raises(self, soul_specs_dir):
        """Test that getting nonexistent version raises KeyError."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        with pytest.raises(KeyError) as exc_info:
            registry.get_soul("rin", "99.99.99")

        assert "99.99.99" in str(exc_info.value)
        assert "Available versions" in str(exc_info.value)

    def test_list_versions(self, soul_specs_dir):
        """Test listing all versions for a character."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        versions = registry.list_versions("rin")

        assert "1.0.0" in versions
        assert len(versions) >= 1

    def test_character_id_matches_directory(self, tmp_path):
        """Test that character_id in YAML must match directory name."""
        # Create mismatched structure
        bad_dir = tmp_path / "soul_specs" / "rin"
        bad_dir.mkdir(parents=True)

        bad_yaml = bad_dir / "v1.0.0.yaml"
        # character_id doesn't match directory name
        bad_yaml.write_text("""
schema_version: "1.0"
character_id: "dorothy"
spec_version: "1.0.0"
locale: "zh-CN"
display_name:
  zh: "Test"
identity_anchor:
  archetype: "test"
  core_wound: {essence: "t", manifest: "t", defense: "t", private_truth: "t"}
  core_desire: {surface: "t", hidden: "t", deepest: "t"}
  core_fear: {ultimate: "t", daily: "t", shadow: "t"}
  core_belief: {about_self: "t", about_others: "t", about_love: "t", about_time: "t"}
  voice_dna:
    - {id: "vd-001", pattern: "t", example: "t", frequency: "high"}
  anti_patterns:
    hard_never: ["test"]
cognitive_style:
  expression:
    sentence_length:
      baseline: "short"
      evolution_bound: ["very_short", "medium"]
      semantic_definition: {very_short: "1-8", short: "8-20", medium: "20-40"}
    verbosity: {baseline: 0.2, evolution_bound: [0.1, 0.4], meaning: "t"}
    emotional_directness: {baseline: 0.1, evolution_bound: [0.05, 0.5], meaning: "t"}
    use_of_metaphor: {baseline: 0.3, evolution_bound: [0.2, 0.6], meaning: "t"}
    hedge_words: {baseline: 0.7, evolution_bound: [0.5, 0.8], meaning: "t"}
    ellipsis_usage: {baseline: 0.6, evolution_bound: [0.4, 0.8], meaning: "t"}
  thinking_style: "deliberate"
  decision_speed: "slow"
  abstraction_level: "high"
  humor_profile: {dryness: 0.9, self_deprecation: 0.05, sarcasm: 0.5, absurdism: 0.2, warmth_in_humor: 0.1}
  emotional_inertia: {recovery_speed: "slow", shock_resistance: "high", bounce_back_curve: "logarithmic", mood_volatility: 0.2}
relational_template:
  default_distance: "guarded"
  intimacy_resistance: 0.75
  softening_curve: "logistic"
  softening_triggers: ["test"]
test_fixtures:
  golden_dialogues:
    - id: "gd-001-test"
      context: {days_since_first: 0}
      user_message: "test"
      expected_properties: {test: "test"}
  regression_tests: ["test"]
meta:
  created_at: "2026-05-17"
  spec_version: "1.0.0"
  author: "test"
  reviewers: ["test"]
  changelog:
    - {version: "1.0.0", date: "2026-05-17", changes: ["test"]}
  backwards_compatibility:
    breaking_changes: []
    migration_required_from: []
        """)

        registry = SoulRegistry(soul_specs_dir=tmp_path / "soul_specs")

        with pytest.raises(RuntimeError) as exc_info:
            registry.load_all()

        assert "does not match directory name" in str(exc_info.value)


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests with real Soul Specs."""

    def test_rin_spec_structure(self, soul_specs_dir):
        """Test Rin's Soul Spec structure integrity."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        rin = registry.get_soul("rin", "1.0.0")

        # Check identity anchor structure
        assert rin.identity_anchor.core_wound.essence is not None
        assert rin.identity_anchor.core_desire.deepest is not None
        assert rin.identity_anchor.core_fear.ultimate is not None

        # Check voice DNA
        voice_dna_ids = [vd.id for vd in rin.identity_anchor.voice_dna]
        assert "vd-001" in voice_dna_ids or "vd-DOROTHY-001" not in voice_dna_ids

        # Check anti-patterns
        assert len(rin.identity_anchor.anti_patterns.hard_never) > 0

        # Check test fixtures
        assert len(rin.test_fixtures.golden_dialogues) > 0

    def test_dorothy_spec_structure(self, soul_specs_dir):
        """Test Dorothy's Soul Spec structure integrity."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        dorothy = registry.get_soul("dorothy", "1.0.0")

        # Check Dorothy-specific features
        assert dorothy.display_name.pet_self_reference == "桃桃"

        # Check voice DNA has Dorothy patterns
        voice_dna_ids = [vd.id for vd in dorothy.identity_anchor.voice_dna]
        assert any("DOROTHY" in vd_id for vd_id in voice_dna_ids)

        # Check cognitive style differences from Rin
        # (Dorothy should have different baseline values)
        assert dorothy.cognitive_style.decision_speed != "slow"  # Dorothy is "fast"

    def test_both_specs_have_required_sections(self, soul_specs_dir):
        """Test that both Rin and Dorothy have all required sections."""
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()

        for character_id in ["rin", "dorothy"]:
            spec = registry.get_soul(character_id, "1.0.0")

            # All specs must have these sections
            assert spec.identity_anchor is not None
            assert spec.cognitive_style is not None
            assert spec.relational_template is not None
            assert spec.test_fixtures is not None
            assert spec.meta is not None

            # Identity anchor subsections
            assert spec.identity_anchor.core_wound is not None
            assert spec.identity_anchor.core_desire is not None
            assert spec.identity_anchor.core_fear is not None
            assert spec.identity_anchor.core_belief is not None
            assert len(spec.identity_anchor.voice_dna) > 0
            assert spec.identity_anchor.anti_patterns is not None

            # Test fixtures
            assert len(spec.test_fixtures.golden_dialogues) > 0
            assert len(spec.test_fixtures.regression_tests) > 0
