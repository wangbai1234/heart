#!/usr/bin/env python3
"""
Anchor Block Generation Demo

演示如何使用 Anchor Block Generator 生成不同模式的 Anchor。

Usage:
    python3 scripts/demo_anchor_block.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from heart.ss01_soul.anchor_block import get_anchor_generator, AnchorMode
import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),
)


def demo_full_anchor():
    """Demo FULL Anchor generation."""
    print("=" * 80)
    print("FULL Anchor Block - 完整版 (首次对话 / 长时间未见)")
    print("=" * 80)
    print()

    generator = get_anchor_generator()
    anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)

    print(f"Character: {anchor.character_id}")
    print(f"Mode: {anchor.mode}")
    print(f"Spec Version: {anchor.spec_version}")
    print(f"Token Estimate: {anchor.token_count_estimate}")
    print()
    print("Content Preview (first 500 chars):")
    print("-" * 80)
    print(anchor.content[:500])
    print("...")
    print()


def demo_light_anchor():
    """Demo LIGHT Anchor generation."""
    print("=" * 80)
    print("LIGHT Anchor Block - 精简版 (正常对话，drift_score 低)")
    print("=" * 80)
    print()

    generator = get_anchor_generator()
    anchor = generator.generate_anchor_block("rin", AnchorMode.LIGHT)

    print(f"Token Estimate: {anchor.token_count_estimate} (vs FULL: ~2000)")
    print()
    print("Full Content:")
    print("-" * 80)
    print(anchor.content)
    print("-" * 80)
    print()


def demo_reinforce_anchor():
    """Demo REINFORCE Anchor generation."""
    print("=" * 80)
    print("REINFORCE Anchor Block - 强化版 (drift_score > 0.3)")
    print("=" * 80)
    print()

    generator = get_anchor_generator()
    anchor = generator.generate_anchor_block("rin", AnchorMode.REINFORCE)

    print(f"Token Estimate: {anchor.token_count_estimate} (FULL + reinforcement)")
    print()
    print("Reinforcement Section (last 300 chars):")
    print("-" * 80)
    print(anchor.content[-300:])
    print("-" * 80)
    print()


def demo_prompt_layer_conversion():
    """Demo converting AnchorBlock to PromptLayer."""
    print("=" * 80)
    print("PromptLayer Conversion (用于 SS05 Composition)")
    print("=" * 80)
    print()

    generator = get_anchor_generator()
    anchor = generator.generate_anchor_block("rin", AnchorMode.FULL)
    layer = anchor.to_prompt_layer()

    print("PromptLayer Structure:")
    print(f"  layer_id: {layer['layer_id']}")
    print(f"  source_subsystem: {layer['source_subsystem']}")
    print(f"  layer_type: {layer['layer_type']}")
    print(f"  priority: {layer['priority']} (highest)")
    print(f"  position_constraint: {layer['position_constraint']}")
    print(f"  token_count_estimate: {layer['token_count_estimate']}")
    print(f"  min_token_count: {layer['min_token_count']}")
    print(f"  is_compressible: {layer['is_compressible']}")
    print(f"  cache_key: {layer['cache_key']}")
    print()


def demo_both_characters():
    """Demo anchor generation for both characters."""
    print("=" * 80)
    print("Character Comparison - Rin vs Dorothy")
    print("=" * 80)
    print()

    generator = get_anchor_generator()

    rin_full = generator.generate_anchor_block("rin", AnchorMode.FULL)
    dorothy_full = generator.generate_anchor_block("dorothy", AnchorMode.FULL)

    print(f"Rin FULL Anchor:")
    print(f"  Tokens: {rin_full.token_count_estimate}")
    print(f"  Preview: {rin_full.content[:200]}...")
    print()

    print(f"Dorothy FULL Anchor:")
    print(f"  Tokens: {dorothy_full.token_count_estimate}")
    print(f"  Preview: {dorothy_full.content[:200]}...")
    print()


def demo_cache_performance():
    """Demo cache performance."""
    print("=" * 80)
    print("Cache Performance")
    print("=" * 80)
    print()

    generator = get_anchor_generator()

    # First call - cache miss
    print("First call (cache miss)...")
    anchor1 = generator.generate_anchor_block("rin", AnchorMode.FULL)
    print(f"  Generated: {anchor1.token_count_estimate} tokens")

    # Second call - cache hit
    print("Second call (cache hit)...")
    anchor2 = generator.generate_anchor_block("rin", AnchorMode.FULL)
    print(f"  Cached: {anchor2.token_count_estimate} tokens")
    print(f"  Same instance: {anchor1 is anchor2}")
    print()

    # Cache invalidation
    print("Invalidating cache for 'rin'...")
    generator.invalidate_cache(character_id="rin")

    # Third call - cache miss again
    print("Third call (cache miss after invalidation)...")
    anchor3 = generator.generate_anchor_block("rin", AnchorMode.FULL)
    print(f"  Generated: {anchor3.token_count_estimate} tokens")
    print(f"  New instance: {anchor1 is not anchor3}")
    print()


def main():
    """Run all demos."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "Anchor Block Generator Demo" + " " * 31 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    demo_full_anchor()
    demo_light_anchor()
    demo_reinforce_anchor()
    demo_prompt_layer_conversion()
    demo_both_characters()
    demo_cache_performance()

    print("=" * 80)
    print("✅ Demo Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
