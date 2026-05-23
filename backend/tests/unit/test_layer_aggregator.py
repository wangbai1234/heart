
"""
Tests for LayerAggregator — SS05 §3.2 + §10.3

Covers:
- Happy path: all 5 layers succeed
- Partial failure: 1 layer fails → fallback used + warning logged
- Timing: end-to-end < 200ms with mocked upstreams
- Empty placeholder correctness (per-layer priorities, constraints, min tokens)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

import pytest

from heart.ss05_composer.layer_aggregator import (
    DEFAULT_LAYER_TIMEOUTS,
    LAYER_AGGREGATION_TIMEOUT,
    LAYER_MIN_TOKENS,
    LAYER_PRIORITIES,
    LayerAggregator,
    PromptLayer,
)


# ============================================================
# Helpers
# ============================================================


@dataclass
class FakeContext:
    """Minimal CompositionContext for testing."""

    trace_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    character_id: str = "dorothy"
    turn_index: int = 1


class FakeSubsystem:
    """Fake upstream subsystem that returns a configurable PromptLayer.

    Supports all 5 layer methods.  delay_ms controls the simulated
    async latency.  Set fail=True to raise an exception.
    """

    def __init__(
        self,
        *,
        delay_ms: float = 1.0,
        fail: bool = False,
        anchor_layer: Optional[PromptLayer] = None,
        memory_layer: Optional[PromptLayer] = None,
        emotion_layer: Optional[PromptLayer] = None,
        relationship_layer: Optional[PromptLayer] = None,
        inner_state_layer: Optional[PromptLayer] = None,
    ):
        self._delay_ms = delay_ms
        self._fail = fail
        self.call_count = 0

        # Per-layer response overrides
        self._anchor = anchor_layer
        self._memory = memory_layer
        self._emotion = emotion_layer
        self._relationship = relationship_layer
        self._inner_state = inner_state_layer

    async def _simulate(self) -> None:
        self.call_count += 1
        if self._fail:
            raise RuntimeError("SS simulated failure")
        await asyncio.sleep(self._delay_ms / 1000.0)

    async def get_anchor_block(self, ctx: FakeContext) -> PromptLayer:
        await self._simulate()
        if self._anchor:
            return self._anchor
        return PromptLayer(
            layer_id="anchor-001",
            source_subsystem="SS01",
            layer_type="anchor_full",
            priority=LAYER_PRIORITIES["anchor_full"],
            position_constraint="first",
            content=f"[FULL ANCHOR] {ctx.character_id} soul block",
            token_count_estimate=800,
            min_token_count=LAYER_MIN_TOKENS["anchor_full"],
            is_compressible=False,
        )

    async def get_memory_context_block(self, ctx: FakeContext) -> PromptLayer:
        await self._simulate()
        if self._memory:
            return self._memory
        return PromptLayer(
            layer_id="memory-001",
            source_subsystem="SS02",
            layer_type="memory_context",
            priority=LAYER_PRIORITIES["memory_context"],
            position_constraint="anywhere",
            content="[MEMORY] Last remembered: ...",
            token_count_estimate=300,
            min_token_count=LAYER_MIN_TOKENS["memory_context"],
            is_compressible=True,
        )

    async def get_emotion_context_block(self, ctx: FakeContext) -> PromptLayer:
        await self._simulate()
        if self._emotion:
            return self._emotion
        return PromptLayer(
            layer_id="emotion-001",
            source_subsystem="SS03",
            layer_type="emotion_context",
            priority=LAYER_PRIORITIES["emotion_context"],
            position_constraint="anywhere",
            content="[EMOTION] VAD: (0.4, 0.6, 0.3)",
            token_count_estimate=200,
            min_token_count=LAYER_MIN_TOKENS["emotion_context"],
            is_compressible=True,
        )

    async def get_relationship_context_block(self, ctx: FakeContext) -> PromptLayer:
        await self._simulate()
        if self._relationship:
            return self._relationship
        return PromptLayer(
            layer_id="rel-001",
            source_subsystem="SS04",
            layer_type="relationship_context",
            priority=LAYER_PRIORITIES["relationship_context"],
            position_constraint="anywhere",
            content="[REL] Stage: FAMILIAR, Trust: 0.72",
            token_count_estimate=250,
            min_token_count=LAYER_MIN_TOKENS["relationship_context"],
            is_compressible=True,
        )

    async def get_inner_state_block(self, ctx: FakeContext) -> PromptLayer:
        await self._simulate()
        if self._inner_state:
            return self._inner_state
        return PromptLayer(
            layer_id="inner-001",
            source_subsystem="SS06",
            layer_type="inner_state",
            priority=LAYER_PRIORITIES["inner_state"],
            position_constraint="anywhere",
            content="[INNER] Energy: 0.8, Initiative: moderate",
            token_count_estimate=150,
            min_token_count=LAYER_MIN_TOKENS["inner_state"],
            is_compressible=True,
        )


def _make_subsystem(delay_ms: float = 1.0, fail: bool = False) -> FakeSubsystem:
    return FakeSubsystem(delay_ms=delay_ms, fail=fail)


def make_aggregator(
    *,
    ss01_delay: float = 1.0,
    ss02_delay: float = 1.0,
    ss03_delay: float = 1.0,
    ss04_delay: float = 1.0,
    ss06_delay: float = 1.0,
    ss01_fail: bool = False,
    ss02_fail: bool = False,
    ss03_fail: bool = False,
    ss04_fail: bool = False,
    ss06_fail: bool = False,
    timeouts: Optional[dict[str, float]] = None,
) -> LayerAggregator:
    """Build a LayerAggregator with fake upstreams for testing."""

    fake_timeouts = {"SS01": 0.100, "SS02": 0.100, "SS03": 0.100, "SS04": 0.100, "SS06": 0.100}
    if timeouts:
        fake_timeouts.update(timeouts)

    return LayerAggregator(
        ss01=_make_subsystem(delay_ms=ss01_delay, fail=ss01_fail),
        ss02=_make_subsystem(delay_ms=ss02_delay, fail=ss02_fail),
        ss03=_make_subsystem(delay_ms=ss03_delay, fail=ss03_fail),
        ss04=_make_subsystem(delay_ms=ss04_delay, fail=ss04_fail),
        ss06=_make_subsystem(delay_ms=ss06_delay, fail=ss06_fail),
        timeouts=fake_timeouts,
    )


# ============================================================
# Test: All 5 layers succeed
# ============================================================


@pytest.mark.asyncio
async def test_all_layers_succeed():
    """All 5 upstream layers return successfully → all included in result."""
    agg = make_aggregator()
    ctx = FakeContext()

    layers = await agg.aggregate(ctx, "Hello!")

    # 5 upstream + user_message + response_directive = 7 layers
    assert len(layers) == 7, f"Expected 7 layers, got {len(layers)}"

    # Verify each upstream layer is present and non-empty
    layer_ids = {L.layer_id for L in layers}
    assert "anchor-001" in layer_ids, "Anchor layer missing"
    assert "memory-001" in layer_ids, "Memory layer missing"
    assert "emotion-001" in layer_ids, "Emotion layer missing"
    assert "rel-001" in layer_ids, "Relationship layer missing"
    assert "inner-001" in layer_ids, "Inner state layer missing"

    # Verify user_message and response_directive are present
    layer_types = {L.layer_type for L in layers}
    assert "user_message" in layer_types, "user_message layer missing"
    assert "response_directive" in layer_types, "response_directive layer missing"

    # Verify no empty layers
    for L in layers:
        if L.layer_type not in ("user_message", "response_directive"):
            assert not L.is_empty, f"Layer {L.layer_id} should not be empty"

    # Verify priorities
    for L in layers:
        expected_priority = LAYER_PRIORITIES.get(L.layer_type)
        if expected_priority is not None:
            assert L.priority == expected_priority, (
                f"Layer {L.layer_id} priority {L.priority} != expected {expected_priority}"
            )


# ============================================================
# Test: 1 layer fails → fallback used + warning logged
# ============================================================


@pytest.mark.asyncio
async def test_one_layer_fails_fallback_used(capsys):
    """When SS02 fails, cached fallback is used, and a warning is logged."""
    # First run: succeed → populate cache
    agg1 = make_aggregator()
    ctx = FakeContext()
    await agg1.aggregate(ctx, "Hello!")

    # Second run: fail SS02, use cache from first run
    agg2 = make_aggregator(ss02_fail=True)
    agg2._result_cache = agg1._result_cache  # transfer cache

    layers = await agg2.aggregate(ctx, "Hello again!")

    # SS02 should have used fallback (cached)
    memory_layer = next((L for L in layers if L.layer_type == "memory_context"), None)
    assert memory_layer is not None, "Memory context layer missing"
    assert not memory_layer.is_empty, "Memory layer should have used cached fallback"

    # Check that the failure was logged (structlog goes to stdout)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "layer_fetch_failed" in output, f"No failure log in: {output[:500]}"
    assert "SS02" in output, f"No SS02 mention in: {output[:500]}"


@pytest.mark.asyncio
async def test_layer_fails_no_cache_uses_empty(capsys):
    """When a layer fails and there is no cache → empty placeholder used."""
    agg = make_aggregator(ss03_fail=True)

    layers = await agg.aggregate(FakeContext(), "Hello!")

    # SS03 should be empty (no cache)
    emotion_layer = next((L for L in layers if L.layer_type == "emotion_context"), None)
    assert emotion_layer is not None, "Emotion layer missing"
    assert emotion_layer.is_empty, "Emotion layer should be empty (no cache)"

    # Verify warning logged (structlog → stdout)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "layer_fetch_failed" in output, f"No failure log in: {output[:500]}"
    assert "source=empty" in output or "empty" in output.lower(), (
        f"No empty fallback log in: {output[:500]}"
    )


# ============================================================
# Test: Timing — end-to-end < 200ms with mocked upstreams
# ============================================================


@pytest.mark.asyncio
async def test_aggregation_timing_under_200ms():
    """With mocked upstreams (each ~1ms delay), aggregation completes < 200ms."""
    agg = make_aggregator(
        ss01_delay=1.0,
        ss02_delay=1.0,
        ss03_delay=1.0,
        ss04_delay=1.0,
        ss06_delay=1.0,
    )
    ctx = FakeContext()

    start = time.monotonic()
    layers = await agg.aggregate(ctx, "Timing test")
    elapsed_ms = (time.monotonic() - start) * 1000

    assert len(layers) == 7
    assert elapsed_ms < 200, (
        f"Aggregation took {elapsed_ms:.1f}ms, expected < 200ms"
    )


@pytest.mark.asyncio
async def test_aggregation_timing_with_slow_layer():
    """When one layer is slow but within its timeout, aggregation still works.

    The slow layer (simulated SS02 at 50ms) is within its 100ms timeout.
    Total time should be bounded by the slowest layer (parallel: ~50ms),
    so well under 200ms.
    """
    agg = make_aggregator(ss02_delay=50.0)
    ctx = FakeContext()

    start = time.monotonic()
    layers = await agg.aggregate(ctx, "Slow layer test")
    elapsed_ms = (time.monotonic() - start) * 1000

    assert len(layers) == 7
    # The slowest layer is 50ms, so total should be < 150ms (some overhead)
    assert elapsed_ms < 200, (
        f"Aggregation with slow layer took {elapsed_ms:.1f}ms, expected < 200ms"
    )


# ============================================================
# Test: Independent timeouts
# ============================================================


@pytest.mark.asyncio
async def test_independent_timeout_per_layer(capsys):
    """Each layer has an independent timeout; a slow layer doesn't block others."""
    # SS02 is very slow (500ms), but timeout is 50ms → should timeout
    # Other layers are fast (1ms)
    agg = make_aggregator(
        ss02_delay=500.0,
        timeouts={"SS02": 0.050},  # 50ms timeout for SS02
    )

    start = time.monotonic()
    layers = await agg.aggregate(FakeContext(), "Timeout test")
    elapsed_ms = (time.monotonic() - start) * 1000

    # SS02 should have timed out, used fallback
    memory_layer = next((L for L in layers if L.layer_type == "memory_context"), None)
    assert memory_layer is not None
    assert memory_layer.is_empty, "SS02 should have timed out and used empty fallback"

    # Other layers should still be present
    layer_types = {L.layer_type for L in layers}
    assert "anchor_full" in layer_types
    assert "emotion_context" in layer_types
    assert "relationship_context" in layer_types
    assert "inner_state" in layer_types

    # Total time should be bounded by timeout (~50ms), not SS02's 500ms
    assert elapsed_ms < 200, (
        f"With SS02 timeout, aggregation took {elapsed_ms:.1f}ms (should be < 200ms)"
    )

    # Timeout warning logged (structlog → stdout)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "layer_fetch_timeout" in output, f"No timeout log in: {output[:500]}"
    assert "SS02" in output, f"No SS02 mention in: {output[:500]}"


# ============================================================
# Test: Empty placeholder properties
# ============================================================


@pytest.mark.asyncio
async def test_empty_anchor_has_first_constraint():
    """Empty anchor placeholder must have position_constraint='first' per PC-1."""
    agg = LayerAggregator()
    empty = agg._empty_anchor()
    assert empty.position_constraint == "first", (
        f"Anchor position_constraint '{empty.position_constraint}' != 'first'"
    )
    assert empty.priority == 1, f"Anchor priority {empty.priority} != 1"


def test_empty_layer_priorities_correct():
    """All empty placeholder priorities match LAYER_PRIORITIES."""
    agg = LayerAggregator()
    empty_layers = [
        ("anchor_light", agg._empty_anchor()),
        ("memory_context", agg._empty_memory()),
        ("emotion_context", agg._empty_emotion()),
        ("relationship_context", agg._empty_relationship()),
        ("inner_state", agg._empty_inner_state()),
    ]
    for layer_type, layer in empty_layers:
        expected = LAYER_PRIORITIES.get(layer_type)
        assert layer.priority == expected, (
            f"{layer_type} priority {layer.priority} != expected {expected}"
        )


# ============================================================
# Test: Cache behavior
# ============================================================


@pytest.mark.asyncio
async def test_cache_population_and_retrieval():
    """Successful layer fetch populates cache; subsequent failure uses cache."""
    agg = make_aggregator()

    # First run populates cache
    await agg.aggregate(FakeContext(), "msg1")

    # Verify cache has entries
    assert "SS01" in agg._result_cache
    assert "SS02" in agg._result_cache

    # Second run with all failures → should use cache
    agg_fail = make_aggregator(
        ss01_fail=True, ss02_fail=True, ss03_fail=True,
        ss04_fail=True, ss06_fail=True,
    )
    agg_fail._result_cache = agg._result_cache  # transfer cache

    layers = await agg_fail.aggregate(FakeContext(), "msg2")

    # All layers should still be non-empty (from cache)
    for L in layers:
        if L.layer_type in ("user_message", "response_directive"):
            continue
        assert not L.is_empty, f"Layer {L.layer_type} is empty, expected cached fallback"


@pytest.mark.asyncio
async def test_cache_invalidation():
    """invalidate_cache removes entries."""
    agg = make_aggregator()
    await agg.aggregate(FakeContext(), "msg")

    assert "SS01" in agg._result_cache
    agg.invalidate_cache("SS01")
    assert "SS01" not in agg._result_cache
    assert "SS02" in agg._result_cache  # other layers unaffected

    agg.invalidate_cache()  # all
    assert len(agg._result_cache) == 0


# ============================================================
# Test: User message and response directive
# ============================================================


@pytest.mark.asyncio
async def test_user_message_layer_content():
    """User message layer contains the actual user message."""
    agg = make_aggregator()
    ctx = FakeContext()
    layers = await agg.aggregate(ctx, "こんにちは、凛。")

    user_msg = next((L for L in layers if L.layer_type == "user_message"), None)
    assert user_msg is not None
    assert user_msg.content == "こんにちは、凛。"
    assert user_msg.priority == LAYER_PRIORITIES["user_message"]
    assert user_msg.position_constraint == "last"


@pytest.mark.asyncio
async def test_response_directive_contains_character():
    """Response directive layer includes the character_id."""
    agg = make_aggregator()
    ctx = FakeContext(character_id="rin")
    layers = await agg.aggregate(ctx, "Hi")

    directive = next((L for L in layers if L.layer_type == "response_directive"), None)
    assert directive is not None
    assert "rin" in directive.content.lower()
    assert directive.priority == LAYER_PRIORITIES["response_directive"]
    assert directive.position_constraint == "last"
