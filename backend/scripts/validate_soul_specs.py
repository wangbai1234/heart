#!/usr/bin/env python3
"""
Soul Spec Validation Script

验证所有 Soul Spec YAML 文件的完整性。

Usage:
    python3 scripts/validate_soul_specs.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from heart.ss01_soul.registry import SoulRegistry
import structlog
import logging

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger()


def main():
    """Validate all Soul Specs and print summary."""

    print("=" * 60)
    print("Soul Spec Validation Report")
    print("=" * 60)
    print()

    # Find soul_specs directory
    repo_root = Path(__file__).parent.parent.parent
    soul_specs_dir = repo_root / "soul_specs"

    print(f"📂 Soul Specs Directory: {soul_specs_dir}")
    print()

    # Create registry and load
    try:
        registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
        registry.load_all()
        print("✅ All Soul Specs loaded successfully!")
        print()

    except Exception as e:
        print(f"❌ Failed to load Soul Specs:")
        print(f"   {e}")
        return 1

    # Print summary
    characters = registry.list_characters()
    print(f"📊 Summary:")
    print(f"   Total characters: {len(characters)}")
    print()

    # Print details for each character
    for character_id in sorted(characters):
        print(f"🎭 Character: {character_id}")

        versions = registry.list_versions(character_id)
        print(f"   Versions: {', '.join(versions)}")

        # Get latest version
        spec = registry.get_soul(character_id)

        # Display name
        display_name = spec.display_name.zh or spec.display_name.en or character_id
        print(f"   Display Name: {display_name}")

        # Archetype (first line)
        archetype_line = spec.identity_anchor.archetype.split('\n')[0].strip()
        print(f"   Archetype: {archetype_line}")

        # Voice DNA count
        voice_dna_count = len(spec.identity_anchor.voice_dna)
        print(f"   Voice DNA patterns: {voice_dna_count}")

        # Hard Never count
        hard_never_count = len(spec.identity_anchor.anti_patterns.hard_never)
        print(f"   Hard Never rules: {hard_never_count}")

        # Hidden Facets count
        facets = spec.identity_anchor.hidden_facets or []
        facets_count = len(facets)
        print(f"   Hidden Facets: {facets_count}")

        # Golden Dialogues count
        gd_count = len(spec.test_fixtures.golden_dialogues)
        print(f"   Golden Dialogues: {gd_count}")

        # Regression Tests count
        rt_count = len(spec.test_fixtures.regression_tests)
        print(f"   Regression Tests: {rt_count}")

        print()

    # Validation checks
    print("🔍 Validation Checks:")
    all_passed = True

    for character_id in characters:
        spec = registry.get_soul(character_id)

        # Check 1: At least 3 voice_dna patterns
        voice_dna_count = len(spec.identity_anchor.voice_dna)
        if voice_dna_count < 3:
            print(f"   ⚠️  {character_id}: Only {voice_dna_count} voice DNA patterns (recommend ≥ 3)")
            all_passed = False

        # Check 2: At least 5 golden_dialogues
        gd_count = len(spec.test_fixtures.golden_dialogues)
        if gd_count < 5:
            print(f"   ⚠️  {character_id}: Only {gd_count} golden dialogues (recommend ≥ 5)")
            all_passed = False

        # Check 3: At least 3 hard_never rules
        hard_never_count = len(spec.identity_anchor.anti_patterns.hard_never)
        if hard_never_count < 3:
            print(f"   ⚠️  {character_id}: Only {hard_never_count} hard_never rules (recommend ≥ 3)")
            all_passed = False

        # Check 4: Cognitive style bounds valid
        verbosity = spec.cognitive_style.expression.verbosity
        if not (verbosity.evolution_bound[0] <= verbosity.baseline <= verbosity.evolution_bound[1]):
            print(f"   ❌ {character_id}: verbosity baseline not within evolution_bound")
            all_passed = False

    if all_passed:
        print("   ✅ All validation checks passed!")

    print()
    print("=" * 60)
    print("✅ Validation Complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
