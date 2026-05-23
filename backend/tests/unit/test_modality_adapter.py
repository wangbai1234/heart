"""
Tests for Modality Adapter — SS05 §3.3 Step 5

Coverage targets:
- All four modalities produce valid ModalityAwareComposition
- Voice-script strips markdown (§3.5 voice-script modality)
- Each modality injects expected structural elements (header)
- Invalid modality raises ValueError
- LLM params vary per modality
- Directives are modality-appropriate

Author: 心屿团队
"""

from __future__ import annotations

import pytest

from heart.ss05_composer.layer_aggregator import PromptLayer
from heart.ss05_composer.modality_adapter import (
    LLMCallParams,
    ModalityAwareComposition,
    ModalityDirectives,
    VALID_MODALITIES,
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
    source_subsystem: str = "SS02",
    **kwargs,
) -> PromptLayer:
    return PromptLayer(
        layer_id=layer_id,
        source_subsystem=source_subsystem,
        layer_type=layer_type,
        priority=priority,
        content=content,
        **kwargs,
    )


def _anchor(content: str = "═" * 80 + "\n[DOROTHY ANCHOR]\n" + "═" * 80) -> PromptLayer:
    return PromptLayer(
        layer_id="anchor_1",
        source_subsystem="SS01",
        layer_type="anchor_full",
        priority=1,
        content=content,
        min_token_count=400,
        is_compressible=False,
    )


def _make_composition() -> list[PromptLayer]:
    """Build a representative resolved layer list for testing."""
    return [
        _anchor(),
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
            content="[L4_IDENTITY] 核心记忆：你喜欢喝咖啡。[/L4_IDENTITY]\n[EPISODE] 上次聊天提到星巴克。",
            priority=35, source_subsystem="SS02",
        ),
        _layer(
            layer_id="msg_1", layer_type="user_message",
            content="今天天气真好！",
            priority=90, source_subsystem="SS05",
        ),
    ]


# ================================================================
# adapt() — modality validation
# ================================================================


class TestAdaptValidation:
    def test_invalid_modality_raises(self):
        with pytest.raises(ValueError, match="Unknown modality"):
            adapt(_make_composition(), "invalid-mode")

    def test_all_valid_modalities_accepted(self):
        for modality in sorted(VALID_MODALITIES):
            result = adapt(_make_composition(), modality)
            assert isinstance(result, ModalityAwareComposition)
            assert result.modality == modality

    def test_empty_composition_still_works(self):
        """Empty layer list should still produce valid composition + header."""
        result = adapt([], "text-short")
        assert len(result.layers) == 1  # only modality header
        assert result.layers[0].layer_type == "modality_adaptation"


# ================================================================
# Structural elements — each modality has a header
# ================================================================


class TestStructuralElements:
    def test_text_short_header_present(self):
        result = adapt(_make_composition(), "text-short")
        header = result.layers[0]
        assert header.layer_type == "modality_adaptation"
        assert "TEXT-SHORT" in header.content
        assert "concise" in header.content.lower()

    def test_text_long_header_present(self):
        result = adapt(_make_composition(), "text-long")
        header = result.layers[0]
        assert header.layer_type == "modality_adaptation"
        assert "TEXT-LONG" in header.content
        assert "detailed" in header.content.lower()

    def test_voice_script_header_present(self):
        result = adapt(_make_composition(), "voice-script")
        header = result.layers[0]
        assert header.layer_type == "modality_adaptation"
        assert "VOICE-SCRIPT" in header.content
        assert "speakable" in header.content.lower()
        assert "TTS" in header.content

    def test_image_caption_header_present(self):
        result = adapt(_make_composition(), "image-caption")
        header = result.layers[0]
        assert header.layer_type == "modality_adaptation"
        assert "IMAGE-CAPTION" in header.content
        assert "visual" in header.content.lower()

    def test_all_layers_preserved_count(self):
        """Adapt must not drop layers; it only adds the modality header."""
        original = _make_composition()
        for modality in sorted(VALID_MODALITIES):
            result = adapt(original, modality)
            assert len(result.layers) == len(original) + 1


# ================================================================
# Voice-script markdown stripping
# ================================================================


class TestVoiceMarkdownStripping:
    def test_bold_stripped(self):
        comp = [
            _layer(
                layer_id="test_1", layer_type="memory_context",
                content="This is **bold** text with *italic* emphasis.",
                priority=35, source_subsystem="SS02",
            ),
        ]
        result = adapt(comp, "voice-script")
        adapted_content = result.layers[1].content  # skip header
        assert "**" not in adapted_content
        assert "bold" in adapted_content
        assert "*" not in adapted_content

    def test_code_block_stripped(self):
        comp = [
            _layer(
                layer_id="test_1", layer_type="memory_context",
                content="Here is `code` and ```\nblock\n```.",
                priority=35, source_subsystem="SS02",
            ),
        ]
        result = adapt(comp, "voice-script")
        adapted_content = result.layers[1].content
        assert "`" not in adapted_content
        assert "code" not in adapted_content  # inline code removed entirely

    def test_headings_stripped(self):
        comp = [
            _layer(
                layer_id="test_1", layer_type="memory_context",
                content="# Heading 1\n## Heading 2\nNormal text.",
                priority=35, source_subsystem="SS02",
            ),
        ]
        result = adapt(comp, "voice-script")
        adapted_content = result.layers[1].content
        assert "#" not in adapted_content
        assert "Heading 1" in adapted_content
        assert "Normal text" in adapted_content

    def test_links_stripped_to_text(self):
        comp = [
            _layer(
                layer_id="test_1", layer_type="memory_context",
                content="Check [this link](https://example.com) out.",
                priority=35, source_subsystem="SS02",
            ),
        ]
        result = adapt(comp, "voice-script")
        adapted_content = result.layers[1].content
        assert "https://example.com" not in adapted_content
        assert "this link" in adapted_content

    def test_markdown_not_stripped_in_text_modes(self):
        """Text modalities should NOT strip markdown."""
        content = "This is **bold** and *italic* and `code`."
        comp = [_layer(layer_id="t1", layer_type="memory_context", content=content)]
        for modality in ("text-short", "text-long"):
            result = adapt(comp, modality)
            assert "**" in result.layers[1].content

    def test_complex_voice_strip(self):
        """Integration: multiple markdown constructs in one content block."""
        content = (
            "# Title\n\n"
            "This is **bold** and *italic*.\n\n"
            "> A quote block\n\n"
            "```python\nprint('hello')\n```\n\n"
            "[Click here](https://example.com)\n\n"
            "| col1 | col2 |\n|------|------|\n| a | b |\n\n"
            "~~strikethrough~~ text."
        )
        comp = [_layer(layer_id="rich", layer_type="memory_context", content=content)]
        result = adapt(comp, "voice-script")
        stripped = result.layers[1].content

        # Verify nothing un-speakable remains
        assert "#" not in stripped
        assert "**" not in stripped
        assert "`" not in stripped
        assert ">" not in stripped
        assert "|" not in stripped
        assert "https" not in stripped
        assert "~~" not in stripped

        # Content survived
        assert "Title" in stripped
        assert "bold" in stripped
        assert "italic" in stripped
        assert "quote block" in stripped
        assert "Click here" in stripped
        assert "strikethrough" in stripped


# ================================================================
# Modality directives
# ================================================================


class TestModalityDirectives:
    def test_text_short_has_text_directive(self):
        result = adapt(_make_composition(), "text-short")
        assert result.directives.text is not None
        assert result.directives.text.target_response_length == "short"
        assert result.directives.voice is None

    def test_text_long_has_text_directive(self):
        result = adapt(_make_composition(), "text-long")
        assert result.directives.text is not None
        assert result.directives.text.target_response_length == "long"

    def test_voice_has_voice_directive(self):
        result = adapt(_make_composition(), "voice-script")
        assert result.directives.voice is not None
        assert result.directives.voice.must_be_speakable is True
        assert result.directives.text is None

    def test_image_caption_has_caption_directive(self):
        result = adapt(_make_composition(), "image-caption")
        assert result.directives.image_caption is not None
        assert result.directives.image_caption.require_visual_description is True
        assert result.directives.text is None


# ================================================================
# ModalityAwareComposition properties
# ================================================================


class TestCompositionProperties:
    def test_is_text(self):
        assert adapt(_make_composition(), "text-short").is_text
        assert adapt(_make_composition(), "text-long").is_text
        assert not adapt(_make_composition(), "voice-script").is_text
        assert not adapt(_make_composition(), "image-caption").is_text

    def test_is_voice(self):
        assert adapt(_make_composition(), "voice-script").is_voice
        assert not adapt(_make_composition(), "text-short").is_voice

    def test_is_image_caption(self):
        assert adapt(_make_composition(), "image-caption").is_image_caption
        assert not adapt(_make_composition(), "text-short").is_image_caption


# ================================================================
# LLM params
# ================================================================


class TestLLMParams:
    def test_text_short_params(self):
        params = get_llm_params("text-short")
        assert params.max_tokens == 512
        assert params.temperature == 0.7

    def test_text_long_params(self):
        params = get_llm_params("text-long")
        assert params.max_tokens == 4096
        assert params.temperature == 0.8

    def test_voice_params(self):
        params = get_llm_params("voice-script")
        assert params.max_tokens == 256
        assert params.temperature == 0.6
        assert "\n\n\n" in params.stop_sequences

    def test_caption_params(self):
        params = get_llm_params("image-caption")
        assert params.max_tokens == 128
        assert params.temperature == 0.3

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            get_llm_params("bogus")
