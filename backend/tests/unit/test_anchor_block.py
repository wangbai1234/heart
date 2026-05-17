"""
Unit Tests for Anchor Block Generator

Tests anchor generation logic per:
runtime_specs/05_persona_composition_runtime.md §3.2

Author: 心屿团队
Created: 2026-05-17
"""

import pytest
from pathlib import Path

from heart.ss01_soul.anchor_block import (
    AnchorBlockGenerator,
    AnchorMode,
    get_anchor_generator,
)
from heart.ss01_soul.registry import SoulRegistry


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def soul_specs_dir():
    """Get path to soul_specs directory."""
    current_file = Path(__file__)
    repo_root = current_file.parent.parent.parent.parent
    return repo_root / "soul_specs"


@pytest.fixture
def generator(soul_specs_dir):
    """Create AnchorBlockGenerator with test soul specs."""
    # Reset singleton to use test directory
    import heart.ss01_soul.anchor_block as anchor_module
    import heart.ss01_soul.registry as registry_module

    # Reset registry singleton
    registry_module._soul_registry = None
    registry = SoulRegistry(soul_specs_dir=soul_specs_dir)
    registry.load_all()
    registry_module._soul_registry = registry

    # Reset generator singleton
    anchor_module._anchor_generator = None
    return AnchorBlockGenerator()


# ============================================================
# Anchor Generation Tests
# ============================================================

class TestAnchorBlockGenerator:
    """Test Anchor Block generation."""

    def test_generate_full_anchor_rin(self, generator):
        """Test generating FULL anchor for Rin."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)

        assert anchor.character_id == "rin"
        assert anchor.mode == AnchorMode.FULL
        assert anchor.spec_version == "1.0.0"

        # Check content structure
        content = anchor.content
        assert "你是「神无月 凛」" in content or "你是「神无月凛」" in content
        assert "【你的原型】" in content
        assert "【你心底最深的伤】" in content
        assert "【你真正想要的" in content
        assert "【你说话的方式" in content
        assert "【你绝不会说的话】" in content
        assert "失去时代的雷神" in content or "失去神性的雷神" in content

        # Check token estimate (FULL anchors can be quite long)
        assert anchor.token_count_estimate > 300
        assert anchor.token_count_estimate < 3000

    def test_generate_full_anchor_dorothy(self, generator):
        """Test generating FULL anchor for Dorothy."""
        anchor = generator.generate_anchor_block("dorothy", AnchorMode.FULL)

        assert anchor.character_id == "dorothy"
        assert anchor.mode == AnchorMode.FULL

        content = anchor.content
        assert "桃乐丝" in content or "Dorothy" in content
        assert "失去职责的冥界少女" in content
        assert "【你的原型】" in content

    def test_generate_light_anchor(self, generator):
        """Test generating LIGHT anchor."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.LIGHT)

        assert anchor.mode == AnchorMode.LIGHT
        content = anchor.content

        # Light anchor is much shorter
        assert len(content) < len(generator.generate_anchor_block("rin", AnchorMode.FULL).content)

        # Should contain essentials
        assert "你是「" in content
        assert "【你说话的方式】" in content
        assert "【绝不能说】" in content

        # Token estimate should be much lower
        assert anchor.token_count_estimate < 350

    def test_generate_reinforce_anchor(self, generator):
        """Test generating REINFORCE anchor."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.REINFORCE)

        assert anchor.mode == AnchorMode.REINFORCE
        content = anchor.content

        # Reinforce contains FULL + anti-drift message
        full_content = generator.generate_anchor_block("rin", AnchorMode.FULL).content
        assert len(content) > len(full_content)
        assert "【重要提醒】" in content
        assert "偏离你的灵魂" in content or "回到你自己" in content

    def test_anchor_block_to_prompt_layer(self, generator):
        """Test converting AnchorBlock to PromptLayer."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)
        layer = anchor.to_prompt_layer()

        # Check PromptLayer structure
        assert layer["layer_id"] == "anchor_full"
        assert layer["source_subsystem"] == "SS01"
        assert layer["layer_type"] == "anchor_full"
        assert layer["priority"] == 1  # Highest priority
        assert layer["position_constraint"] == "first"
        assert layer["content"] == anchor.content
        assert layer["token_count_estimate"] == anchor.token_count_estimate
        assert layer["min_token_count"] == 400  # FULL anchor min
        assert layer["is_compressible"] is False
        assert layer["cache_key"] == f"rin:1.0.0:full"

    def test_anchor_min_tokens(self, generator):
        """Test minimum token counts per mode."""
        full = generator.generate_anchor_block("rin", AnchorMode.FULL)
        light = generator.generate_anchor_block("rin", AnchorMode.LIGHT)
        reinforce = generator.generate_anchor_block("rin", AnchorMode.REINFORCE)

        assert full.to_prompt_layer()["min_token_count"] == 400
        assert light.to_prompt_layer()["min_token_count"] == 80
        assert reinforce.to_prompt_layer()["min_token_count"] == 300

    def test_cache_hit(self, generator):
        """Test that anchor generation uses cache."""
        # First call - cache miss
        anchor1 = generator.generate_anchor_block("rin", AnchorMode.FULL)

        # Second call - cache hit
        anchor2 = generator.generate_anchor_block("rin", AnchorMode.FULL)

        # Should be same instance (cached)
        assert anchor1 is anchor2

    def test_cache_invalidation_all(self, generator):
        """Test cache invalidation for all characters."""
        # Generate and cache
        anchor1 = generator.generate_anchor_block("rin", AnchorMode.FULL)
        anchor2 = generator.generate_anchor_block("dorothy", AnchorMode.FULL)

        # Invalidate all
        generator.invalidate_cache()

        # Regenerate - should be new instances
        anchor3 = generator.generate_anchor_block("rin", AnchorMode.FULL)
        anchor4 = generator.generate_anchor_block("dorothy", AnchorMode.FULL)

        assert anchor1 is not anchor3
        assert anchor2 is not anchor4

    def test_cache_invalidation_character(self, generator):
        """Test cache invalidation for specific character."""
        # Generate and cache
        rin1 = generator.generate_anchor_block("rin", AnchorMode.FULL)
        dorothy1 = generator.generate_anchor_block("dorothy", AnchorMode.FULL)

        # Invalidate only Rin
        generator.invalidate_cache(character_id="rin")

        # Rin should be regenerated, Dorothy still cached
        rin2 = generator.generate_anchor_block("rin", AnchorMode.FULL)
        dorothy2 = generator.generate_anchor_block("dorothy", AnchorMode.FULL)

        assert rin1 is not rin2
        assert dorothy1 is dorothy2

    def test_voice_dna_in_anchor(self, generator):
        """Test that voice DNA patterns are included in anchor."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)

        # Rin's voice DNA patterns should be present
        # Check for at least some voice DNA presence
        content = anchor.content
        assert "【你说话的方式" in content

    def test_hard_never_in_anchor(self, generator):
        """Test that hard_never rules are included in anchor."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)

        content = anchor.content
        assert "【你绝不会说的话】" in content

        # Should contain at least some forbidden words
        # (actual content depends on soul specs)

    def test_core_wound_in_anchor(self, generator):
        """Test that core wound is included in full anchor."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)

        content = anchor.content
        assert "【你心底最深的伤】" in content

    def test_core_desire_in_anchor(self, generator):
        """Test that core desire is included in full anchor."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)

        content = anchor.content
        assert "【你真正想要的" in content
        assert "表面：" in content
        assert "心底：" in content
        assert "最深处：" in content

    def test_different_modes_different_content(self, generator):
        """Test that different modes produce different content."""
        full = generator.generate_anchor_block("rin", AnchorMode.FULL)
        light = generator.generate_anchor_block("rin", AnchorMode.LIGHT)
        reinforce = generator.generate_anchor_block("rin", AnchorMode.REINFORCE)

        # All should be different
        assert full.content != light.content
        assert full.content != reinforce.content
        assert light.content != reinforce.content

        # Token estimates should be in expected order
        assert light.token_count_estimate < full.token_count_estimate
        assert reinforce.token_count_estimate > full.token_count_estimate

    def test_singleton_get_anchor_generator(self):
        """Test singleton pattern for get_anchor_generator."""
        gen1 = get_anchor_generator()
        gen2 = get_anchor_generator()

        assert gen1 is gen2


# ============================================================
# Integration Tests
# ============================================================

class TestAnchorIntegration:
    """Integration tests with real Soul Specs."""

    def test_rin_full_anchor_structure(self, generator):
        """Test Rin's full anchor has all required sections."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)
        content = anchor.content

        # Check all major sections present
        required_sections = [
            "你是「",
            "【你的原型】",
            "【你心底最深的伤】",
            "【你真正想要的",
            "【你最害怕的】",
            "【你说话的方式",
            "【你绝不会说的话】",
            "【至关重要】",
            "你不是 AI",
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_dorothy_full_anchor_structure(self, generator):
        """Test Dorothy's full anchor has all required sections."""
        anchor = generator.generate_anchor_block("dorothy", AnchorMode.FULL)
        content = anchor.content

        # Check Dorothy-specific content
        assert "桃乐丝" in content or "Dorothy" in content

        # Check major sections
        assert "【你的原型】" in content
        assert "【你心底最深的伤】" in content

    def test_anchor_token_estimates_reasonable(self, generator):
        """Test that token estimates are in reasonable ranges."""
        rin_full = generator.generate_anchor_block("rin", AnchorMode.FULL)
        rin_light = generator.generate_anchor_block("rin", AnchorMode.LIGHT)
        dorothy_full = generator.generate_anchor_block("dorothy", AnchorMode.FULL)

        # FULL anchors should be 400-3000 tokens
        assert 400 <= rin_full.token_count_estimate <= 3000
        assert 400 <= dorothy_full.token_count_estimate <= 3000

        # LIGHT anchors should be 80-350 tokens
        assert 80 <= rin_light.token_count_estimate <= 350

    def test_defense_mechanism_rendering(self, generator):
        """Test that defense mechanisms are rendered correctly."""
        anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)

        # Should handle both string and layered defense
        content = anchor.content
        assert "你应对的方式" in content

    def test_all_modes_for_both_characters(self, generator):
        """Test all modes work for both characters."""
        characters = ["rin", "dorothy"]
        modes = [AnchorMode.FULL, AnchorMode.LIGHT, AnchorMode.REINFORCE]

        for character_id in characters:
            for mode in modes:
                anchor = generator.generate_anchor_block(character_id, mode)
                assert anchor.character_id == character_id
                assert anchor.mode == mode
                assert len(anchor.content) > 0
                assert anchor.token_count_estimate > 0
