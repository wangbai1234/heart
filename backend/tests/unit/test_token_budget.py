"""
Tests for Token Budget Allocator — SS05 §3.3 Step 4 + §10.5-10.6

Coverage targets per runtime_specs/05_persona_composition_runtime.md §10.11:
- Token Budget Allocator (various overflow scenarios)
- Compression preserves min_token_count
- Anchor + Care Path non-compressible
- Loose budget → no compression
- Tight budget → low-priority layers dropped

Author: 心屿团队
"""

from __future__ import annotations

import pytest

from heart.ss05_composer.layer_aggregator import PromptLayer
from heart.ss05_composer.token_budget import (
    AllocatedLayer,
    AllocatedLayers,
    LayerCompressor,
    TokenCounter,
    _is_non_compressible,
    allocate,
)


# ================================================================
# Helpers — build PromptLayers quickly
# ================================================================


def _layer(
    layer_id: str = "L1",
    layer_type: str = "memory_context",
    content: str = "",
    priority: int = 35,
    min_token_count: int = 300,
    is_compressible: bool = True,
    **kwargs,
) -> PromptLayer:
    return PromptLayer(
        layer_id=layer_id,
        source_subsystem="SS02",
        layer_type=layer_type,
        priority=priority,
        content=content,
        min_token_count=min_token_count,
        is_compressible=is_compressible,
        **kwargs,
    )


def _anchor(layer_id: str = "A1", mode: str = "full", content: str = "") -> PromptLayer:
    return PromptLayer(
        layer_id=layer_id,
        source_subsystem="SS01",
        layer_type=f"anchor_{mode}",
        priority=1,
        content=content or ("═" * 80 + "\n[DOROTHY ANCHOR]\n" + "═" * 80),
        min_token_count=400 if mode == "full" else 80,
        is_compressible=False,
    )


def _safety(layer_id: str = "S1", level: str = "GREEN", content: str = "") -> PromptLayer:
    return PromptLayer(
        layer_id=layer_id,
        source_subsystem="SS07",
        layer_type="safety",
        priority=5,
        content=content or "[SAFETY: level={}]".format(level),
        min_token_count=50,
        is_compressible=False,
        metadata={"level": level},
    )


# ================================================================
# TokenCounter
# ================================================================


class TestTokenCounter:
    def test_empty_string(self):
        assert TokenCounter().estimate("") == 0

    def test_ascii_only(self):
        c = TokenCounter()
        # "hello world" = 11 chars * 0.3 ≈ 3 tokens
        assert c.estimate("hello world") == 3

    def test_chinese_only(self):
        c = TokenCounter()
        # 你好世界 = 4 chars * 1.5 = 6 tokens
        assert c.estimate("你好世界") == 6

    def test_mixed_text(self):
        c = TokenCounter()
        # "你好 world" = 2 chinese * 1.5 + 6 non-chinese * 0.3 = 3 + 1 = 4
        assert c.estimate("你好 world") == 4

    def test_exact_falls_back_to_estimate(self):
        c = TokenCounter()
        assert c.exact("你好") == c.estimate("你好")


# ================================================================
# _is_non_compressible
# ================================================================


class TestNonCompressible:
    def test_anchor_full(self):
        assert _is_non_compressible(_anchor(mode="full"))
        assert _is_non_compressible(_anchor(mode="light"))
        assert _is_non_compressible(_anchor(mode="reinforce"))

    def test_care_path_safety(self):
        assert _is_non_compressible(_safety(level="PURPLE"))
        assert not _is_non_compressible(_safety(level="GREEN"))
        assert not _is_non_compressible(_safety(level="YELLOW"))

    def test_compressible_layer(self):
        L = _layer(layer_type="memory_context")
        assert not _is_non_compressible(L)


# ================================================================
# LayerCompressor — basic behaviour
# ================================================================


class TestLayerCompressor:
    def test_no_compression_when_already_fits(self):
        comp = LayerCompressor()
        L = _layer(content="short text")
        result = comp.compress(L, 1000)
        assert result.content == "short text"

    def test_truncation_reduces_content(self):
        comp = LayerCompressor()
        long_text = "x" * 500  # ~150 tokens
        L = _layer(content=long_text)
        result = comp.compress(L, 10)  # target far below current
        assert len(result.content) < len(long_text)
        assert comp._counter.estimate(result.content) <= 10

    def test_truncation_preserves_layer_identity(self):
        comp = LayerCompressor()
        L = _layer(layer_id="L42", content="hello world " * 20)
        result = comp.compress(L, 10)
        assert result.layer_id == "L42"
        assert result.layer_type == "memory_context"
        assert result.priority == 35

    def test_memory_compression_preserves_l4(self):
        comp = LayerCompressor()
        content = (
            "[L4_IDENTITY]\nname: Dorothy\ncore: gentle librarian\n[/L4_IDENTITY]\n\n"
            + "Episode 1: first meeting details " * 10
        )
        L = _layer(layer_type="memory_context", content=content)
        target = comp._counter.estimate("[L4_IDENTITY]\nname: Dorothy\ncore: gentle librarian\n[/L4_IDENTITY]") + 20
        result = comp.compress(L, target)
        assert "[L4_IDENTITY]" in result.content
        assert "name: Dorothy" in result.content

    def test_history_compression_keeps_first_turn(self):
        comp = LayerCompressor()
        turns = [
            "用户：你好，初次见面。",
            "助手：你好，我是 Dorothy。",
            "用户：今天天气真好。",
            "助手：是啊，很适合散步。",
            "用户：你最近读了什么书？",
            "助手：我最近在读《百年孤独》。",
            "用户：你有什么推荐吗？",
        ]
        content = "\n".join(turns)
        L = _layer(layer_type="conversation_history", content=content)
        # Budget only enough for ~2 turns
        first_tokens = comp._counter.estimate(turns[0])
        result = comp.compress(L, first_tokens + 20)
        # First turn should be preserved
        assert "你好，初次见面" in result.content


# ================================================================
# allocate — integration scenarios
# ================================================================


class TestAllocateLooseBudget:
    """Loose budget → no compression, all layers pass through."""

    def test_all_layers_fit(self):
        layers = [
            _anchor(content="DOROTHY ANCHOR " * 20),  # ~ 500 tokens
            _safety(content="SAFETY LAYER " * 10),     # ~ 150 tokens
            _layer(
                layer_id="M1", layer_type="memory_context",
                content="MEMORY CONTEXT " * 30, priority=35,
            ),  # ~ 450 tokens
        ]
        result = allocate(layers, total_budget=5000)
        assert result.compression_applied is False
        assert len(result.layers) == 3
        assert result.total_tokens <= 5000
        assert len(result.dropped_layer_ids) == 0

    def test_no_allocations_show_compression(self):
        layers = [_anchor(), _layer(layer_id="M1", content="short")]
        result = allocate(layers, total_budget=5000)
        for a in result.allocations:
            assert a.compression_applied is None


class TestAllocateTightBudget:
    """Tight budget → low-priority layers compressed/dropped, anchor preserved."""

    def test_anchor_preserved_when_tight(self):
        anchor_content = "DOROTHY ANCHOR FULL " * 30  # ~800 tokens
        anchor = _anchor(content=anchor_content)
        memory = _layer(
            layer_id="M1", layer_type="memory_context",
            content="LONG MEMORY " * 500, priority=35, min_token_count=50,
        )
        history = _layer(
            layer_id="H1", layer_type="conversation_history",
            content="HISTORY TURNS " * 500, priority=50, min_token_count=50,
        )

        # Budget = anchor + just a bit more → compression needed
        anchor_tokens = TokenCounter().estimate(anchor_content)
        result = allocate([anchor, memory, history], total_budget=anchor_tokens + 100)

        # Anchor MUST be in result unchanged
        anchor_in_result = [L for L in result.layers if L.layer_id == "A1"]
        assert len(anchor_in_result) == 1
        assert anchor_in_result[0].content == anchor_content

        # Total must respect budget
        assert result.total_tokens <= anchor_tokens + 100
        assert result.compression_applied is True

    def test_low_priority_dropped_before_high_priority(self):
        anchor = _anchor()
        # High-priority compressible (safety, p=5)
        safety = _safety(level="GREEN")
        # Low-priority compressible (memory, p=35)
        big_memory = _layer(
            layer_id="M1", layer_type="memory_context",
            content="BIG MEMORY BLOCK " * 500, priority=35, min_token_count=30,
        )
        # Very-low-priority (history, p=50)
        big_history = _layer(
            layer_id="H1", layer_type="conversation_history",
            content="BIG HISTORY BLOCK " * 500, priority=50, min_token_count=30,
        )

        # Budget = anchor + safety only
        counter = TokenCounter()
        budget = counter.estimate(anchor.content) + counter.estimate(safety.content) + 10
        result = allocate([anchor, safety, big_memory, big_history], total_budget=budget)

        # Anchor and safety must survive
        kept_ids = {L.layer_id for L in result.layers}
        assert "A1" in kept_ids
        assert "S1" in kept_ids

        # Low-priority layers should be dropped or heavily compressed
        assert result.compression_applied is True

        # Token count ≤ budget
        assert result.total_tokens <= budget

    def test_min_token_count_respected(self):
        anchor = _anchor()
        memory = _layer(
            layer_id="M1", layer_type="memory_context",
            content="M" * 2000, priority=35, min_token_count=300,
        )
        history = _layer(
            layer_id="H1", layer_type="conversation_history",
            content="H" * 2000, priority=50, min_token_count=100,
        )

        counter = TokenCounter()
        anchor_tokens = counter.estimate(anchor.content)
        # Budget = anchor + memory_min + history_min - 50 → forcing drop of history
        budget = anchor_tokens + 300 + 50
        result = allocate([anchor, memory, history], total_budget=budget)

        # Memory should survive (maybe compressed) because its min=300 fits
        kept_ids = {L.layer_id for L in result.layers}
        assert "A1" in kept_ids
        # Memory at min=300 should be kept (budget allows)
        if "M1" in kept_ids:
            m_tokens = counter.estimate(
                [L for L in result.layers if L.layer_id == "M1"][0].content
            )
            assert m_tokens >= 300 or m_tokens == 0  # either kept at min or dropped

    def test_extreme_budget_only_anchor_survives(self):
        anchor = _anchor()
        memory = _layer(
            layer_id="M1", layer_type="memory_context",
            content="MEMORY " * 1000, priority=35, min_token_count=100,
        )
        history = _layer(
            layer_id="H1", layer_type="conversation_history",
            content="HISTORY " * 1000, priority=50, min_token_count=100,
        )

        counter = TokenCounter()
        anchor_tokens = counter.estimate(anchor.content)
        # Budget = anchor only → everything else dropped
        result = allocate([anchor, memory, history], total_budget=anchor_tokens)

        kept_ids = {L.layer_id for L in result.layers}
        assert kept_ids == {"A1"}
        assert result.compression_applied is True
        assert len(result.dropped_layer_ids) == 2

    def test_care_path_preserved_when_purple(self):
        """Care Path (safety level=PURPLE) must never be compressed or dropped."""
        anchor = _anchor()
        safety = _safety(
            level="PURPLE",
            content="CRITICAL SAFETY GUIDELINES " * 30,  # ~450 tokens
        )
        memory = _layer(
            layer_id="M1", layer_type="memory_context",
            content="LARGE MEMORY " * 300, priority=35, min_token_count=30,
        )

        counter = TokenCounter()
        anchor_tokens = counter.estimate(anchor.content)
        safety_tokens = counter.estimate(safety.content)
        # Budget = anchor + safety + tiny margin
        budget = anchor_tokens + safety_tokens + 5
        result = allocate([anchor, safety, memory], total_budget=budget)

        kept_ids = {L.layer_id for L in result.layers}
        # Anchor + PURPLE safety must survive
        assert "A1" in kept_ids
        assert "S1" in kept_ids

        # safety content must be intact
        safety_result = [L for L in result.layers if L.layer_id == "S1"][0]
        assert safety_result.content == safety.content


class TestAllocateEdgeCases:
    def test_empty_layers(self):
        result = allocate([], total_budget=1000)
        assert len(result.layers) == 0
        assert result.total_tokens == 0
        assert result.compression_applied is False

    def test_budget_zero(self):
        anchor = _anchor()
        result = allocate([anchor], total_budget=0)
        # Anchor must survive even at zero budget
        assert len(result.layers) >= 1
        assert "A1" in {L.layer_id for L in result.layers}

    def test_single_compressible_layer(self):
        L = _layer(content="short content")
        result = allocate([L], total_budget=1000)
        assert len(result.layers) == 1
        assert result.compression_applied is False

    def test_allocation_metadata_complete(self):
        layers = [_anchor(), _layer(layer_id="M1", content="test")]
        result = allocate(layers, total_budget=5000)
        # One AllocatedLayer per input layer
        assert len(result.allocations) == 2
        ids = {a.layer_id for a in result.allocations}
        assert ids == {"A1", "M1"}

    def test_allocation_preserves_priority_order(self):
        """Higher priority layers should appear before lower priority ones."""
        anchor = _anchor(layer_id="A1")
        safety = _safety(layer_id="S1", level="GREEN")
        memory = _layer(layer_id="M1", content="mem", priority=35)
        history = _layer(layer_id="H1", content="hist", priority=50)

        result = allocate([history, memory, safety, anchor], total_budget=5000)
        # Order should be: anchor(1) → safety(5) → memory(35) → history(50)
        types = [L.layer_id for L in result.layers]
        expected_order = ["A1", "S1", "M1", "H1"]
        assert types == expected_order


class TestAllocatedLayersProperties:
    def test_dropped_layer_ids(self):
        a = AllocatedLayers(
            layers=[],
            total_tokens=0,
            budget=1000,
            compression_applied=True,
            allocations=[
                AllocatedLayer("L1", "memory_context", 35, 500, 0, "drop"),
                AllocatedLayer("L2", "anchor_full", 1, 400, 400, None),
                AllocatedLayer("L3", "conversation_history", 50, 300, 150, "truncation"),
            ],
        )
        assert a.dropped_layer_ids == ["L1"]
        assert a.compressed_layer_ids == ["L3"]

    def test_no_drops(self):
        a = AllocatedLayers(
            layers=[], total_tokens=0, budget=1000, compression_applied=False
        )
        assert a.dropped_layer_ids == []
        assert a.compressed_layer_ids == []
