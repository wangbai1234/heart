"""
Tests for Composer — SS05 §3.3 Step 6

Coverage targets:
- Composer.compose() produces valid PromptBundle
- Layer ordering respects priority + position_constraint
- Anchor layer always first (PC-1)
- User message formatted with "用户：" prefix
- Prompt text assembled with double-newline separators
- Token estimate computed
- LLM params match modality
- CompositionTrace populated correctly
- assemble() convenience works end-to-end

Author: 心屿团队
"""

from __future__ import annotations

import pytest

from heart.ss05_composer.composer import (
    Composer,
    CompositionTrace,
    LayerInclusion,
    PromptBundle,
    _estimate_tokens,
    _format_layer,
    _order_layers,
    assemble,
)
from heart.ss05_composer.layer_aggregator import PromptLayer
from heart.ss05_composer.modality_adapter import (
    LLMCallParams,
    ModalityAwareComposition,
    adapt,
    get_llm_params,
)


# ================================================================
# Helpers — build PromptLayers quickly
# ================================================================


def _layer(
    layer_id: str = "L1",
    layer_type: str = "memory_context",
    content: str = "",
    priority: int = 35,
    position_constraint: str = "anywhere",
    source_subsystem: str = "SS02",
    **kwargs,
) -> PromptLayer:
    return PromptLayer(
        layer_id=layer_id,
        source_subsystem=source_subsystem,
        layer_type=layer_type,
        priority=priority,
        position_constraint=position_constraint,
        content=content,
        **kwargs,
    )


def _anchor(content: str = "") -> PromptLayer:
    return PromptLayer(
        layer_id="anchor_1",
        source_subsystem="SS01",
        layer_type="anchor_full",
        priority=1,
        position_constraint="first",
        content=content or "═" * 80 + "\n[DOROTHY ANCHOR]\n" + "═" * 80,
        min_token_count=400,
        is_compressible=False,
    )


def _resolved_layers() -> list[PromptLayer]:
    """Build a representative post-adapter resolved layer list."""
    return [
        _anchor(),
        _layer(
            layer_id="mod_text", layer_type="modality_adaptation",
            content="[MODE: TEXT-SHORT]",
            priority=10, source_subsystem="SS05",
        ),
        _layer(
            layer_id="rel_1", layer_type="relationship_context",
            content="[RELATIONSHIP: stage=FRIEND, trust=0.72]",
            priority=20, source_subsystem="SS04",
        ),
        _layer(
            layer_id="emo_1", layer_type="emotion_context",
            content="[EMOTION: warmth 0.65, joy 0.40]",
            priority=25, source_subsystem="SS03",
        ),
        _layer(
            layer_id="mem_1", layer_type="memory_context",
            content="[MEMORY: recall 咖啡 episode]",
            priority=35, source_subsystem="SS02",
        ),
        _layer(
            layer_id="msg_1", layer_type="user_message",
            content="今天天气真好！",
            priority=90, source_subsystem="SS05",
        ),
    ]


# ================================================================
# _order_layers
# ================================================================


class TestOrderLayers:
    def test_sorts_by_priority(self):
        layers = [
            _layer("low", priority=90, content="low"),
            _layer("high", priority=1, content="high"),
            _layer("mid", priority=30, content="mid"),
        ]
        ordered = _order_layers(layers)
        priorities = [L.priority for L in ordered]
        assert priorities == [1, 30, 90]

    def test_first_before_anywhere_same_priority(self):
        layers = [
            _layer("any", priority=20, position_constraint="anywhere", content="any"),
            _layer("fst", priority=20, position_constraint="first", content="first"),
        ]
        ordered = _order_layers(layers)
        assert ordered[0].layer_id == "fst"
        assert ordered[1].layer_id == "any"

    def test_last_after_anywhere_same_priority(self):
        layers = [
            _layer("last", priority=50, position_constraint="last", content="last"),
            _layer("any", priority=50, position_constraint="anywhere", content="any"),
        ]
        ordered = _order_layers(layers)
        assert ordered[-1].layer_id == "last"

    def test_stable_sort_preserves_input_order(self):
        """Same priority + constraint → preserve insert order."""
        layers = [
            _layer("a", priority=30, content="a"),
            _layer("b", priority=30, content="b"),
            _layer("c", priority=30, content="c"),
        ]
        ordered = _order_layers(layers)
        assert [L.layer_id for L in ordered] == ["a", "b", "c"]


# ================================================================
# _format_layer
# ================================================================


class TestFormatLayer:
    def test_anchor_passthrough(self):
        anchor = _anchor(content="═══ ANCHOR ═══")
        assert _format_layer(anchor) == "═══ ANCHOR ═══"

    def test_user_message_prefixed(self):
        layer = _layer(layer_type="user_message", content="你好", source_subsystem="SS05")
        assert _format_layer(layer) == "用户：你好"

    def test_response_directive_passthrough(self):
        layer = _layer(layer_type="response_directive", content="凛的回复:", source_subsystem="SS05")
        assert _format_layer(layer) == "凛的回复:"

    def test_modality_adaptation_passthrough(self):
        layer = _layer(layer_type="modality_adaptation", content="[MODE: TEXT]", source_subsystem="SS05")
        assert _format_layer(layer) == "[MODE: TEXT]"

    def test_generic_passthrough(self):
        layer = _layer(layer_type="memory_context", content="[MEMORY]", source_subsystem="SS02")
        assert _format_layer(layer) == "[MEMORY]"


# ================================================================
# _estimate_tokens
# ================================================================


class TestEstimateTokens:
    def test_empty_string(self):
        assert _estimate_tokens("") == 0

    def test_ascii(self):
        assert _estimate_tokens("hello world") == 3

    def test_chinese(self):
        assert _estimate_tokens("你好世界") == 6

    def test_mixed(self):
        t = _estimate_tokens("hello 你好 world")
        assert t == 6  # 12 non-CJK * 0.3 = 3 + 2 CJK * 1.5 = 3 → 6


# ================================================================
# Composer.compose()
# ================================================================


class TestComposerCompose:
    def test_returns_prompt_bundle(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-short")
        assert isinstance(bundle, PromptBundle)
        assert isinstance(bundle.trace_id, type(bundle.trace_id))
        assert isinstance(bundle.llm_params, LLMCallParams)

    def test_anchor_first_in_prompt(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-short")
        # Anchor should be the very first thing in the prompt text
        assert bundle.prompt_text.startswith("═")

    def test_user_message_formatted(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-short")
        assert "用户：" in bundle.prompt_text
        assert "今天天气真好！" in bundle.prompt_text

    def test_layers_joined_with_double_newline(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-short")
        # Should have at least one \n\n separator between non-empty layers
        assert "\n\n" in bundle.prompt_text

    def test_token_count_positive(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-short")
        assert bundle.total_tokens > 0

    def test_layers_included_tracks_offsets(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-short")
        assert len(bundle.layers_included) > 0
        # Each layer in the output should have valid offsets
        for li in bundle.layers_included:
            assert li.start_offset >= 0
            assert li.end_offset > li.start_offset

    def test_first_layer_inclusion_starts_at_zero(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-short")
        assert bundle.layers_included[0].start_offset == 0

    def test_llm_params_match_modality(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "voice-script")
        assert bundle.llm_params.max_tokens == 256
        assert bundle.llm_params.temperature == 0.6

    def test_modality_propagated(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "image-caption")
        assert bundle.modality == "image-caption"

    def test_trace_populated(self):
        composer = Composer()
        bundle = composer.compose(_resolved_layers(), "text-long")
        trace = bundle.composition_trace
        assert isinstance(trace, CompositionTrace)
        assert trace.trace_id == bundle.trace_id
        assert trace.modality == "text-long"
        assert trace.total_tokens > 0
        assert trace.layer_count > 0
        assert len(trace.layers_included) > 0
        assert trace.content_sha256
        assert trace.composition_ms >= 0

    def test_soul_provides_character_id(self):
        composer = Composer()
        soul = {"character_id": "dorothy"}
        bundle = composer.compose(_resolved_layers(), "text-short", soul=soul)
        assert bundle.composition_trace.character_id == "dorothy"

    def test_single_layer_composition(self):
        """Minimal composition with just one layer."""
        composer = Composer()
        single = [_anchor(content="╔══ ANCHOR ══╗")]
        bundle = composer.compose(single, "text-short")
        assert bundle.prompt_text == "╔══ ANCHOR ══╗"
        assert bundle.total_tokens > 0

    def test_empty_layer_skipped(self):
        """Layer with empty content should be skipped."""
        composer = Composer()
        layers = [
            _anchor(content="═══ ANCHOR ═══"),
            _layer("empty", content="", priority=30, layer_type="memory_context"),
        ]
        bundle = composer.compose(layers, "text-short")
        # Only anchor appears (empty layer skipped)
        assert "\n\n" not in bundle.prompt_text


# ================================================================
# assemble() convenience — end-to-end adapter + composer
# ================================================================


class TestAssembleEndToEnd:
    def test_full_pipeline_text_short(self):
        """End-to-end: adapt → assemble for text-short."""
        comp = _resolved_layers()
        adapted = adapt(comp, "text-short")
        bundle = assemble(adapted)
        assert isinstance(bundle, PromptBundle)
        assert bundle.modality == "text-short"
        assert "[MODE: TEXT-SHORT]" in bundle.prompt_text

    def test_full_pipeline_voice_script(self):
        """End-to-end: adapt → assemble for voice-script (markdown stripped)."""
        comp = _resolved_layers()
        adapted = adapt(comp, "voice-script")
        bundle = assemble(adapted)
        assert isinstance(bundle, PromptBundle)
        assert bundle.modality == "voice-script"
        assert "[MODE: VOICE-SCRIPT]" in bundle.prompt_text

    def test_full_pipeline_image_caption(self):
        """End-to-end: adapt → assemble for image-caption."""
        comp = _resolved_layers()
        adapted = adapt(comp, "image-caption")
        bundle = assemble(adapted)
        assert isinstance(bundle, PromptBundle)
        assert bundle.modality == "image-caption"
        assert "[MODE: IMAGE-CAPTION]" in bundle.prompt_text
