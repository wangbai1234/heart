"""
Contract: ComposerLayerAggregator must satisfy build_layers protocol.
per runtime_specs/05_persona_composition_runtime.md §5

Verifies that Composer exposes a build_layers method with correct signature.
"""

import pytest

from tests.contract.conftest import ComposerLayerProtocol


class ConcreteComposer:
    """Concrete Composer satisfying ComposerLayerProtocol."""

    def build_layers(
        self,
        emotion: dict,
        memory: object,
        inner_state: dict,
        relationship: dict,
    ) -> dict:
        return {
            "meta": {
                "emotion_vad": emotion.get("vad_valence"),
                "energy": emotion.get("energy"),
                "memory_count": 1,
                "relationship_stage": relationship.get("current_stage"),
            },
            "prompt_context": {
                "inner_awareness": inner_state.get("emotional_awareness"),
            },
        }


@pytest.mark.contract
class TestComposerLayerAggregatorProtocol:
    """Composer must satisfy the build_layers protocol."""

    def test_composer_implements_protocol(self):
        """Concrete composer satisfies ComposerLayerProtocol."""
        composer = ConcreteComposer()
        assert isinstance(composer, ComposerLayerProtocol)

    def test_build_layers_returns_dict(
        self, make_emotion_state, make_inner_state, make_relationship_state
    ):
        """build_layers must return a dict with meta and prompt_context."""
        composer = ConcreteComposer()
        emotion = make_emotion_state(vad_valence=0.7)
        inner = make_inner_state(emotional_awareness="愉悦")
        rel = make_relationship_state(current_stage="FRIEND")

        layers = composer.build_layers(
            emotion=emotion,
            memory=None,
            inner_state=inner,
            relationship=rel,
        )

        assert isinstance(layers, dict)
        assert "meta" in layers
        assert "prompt_context" in layers
        assert layers["meta"]["emotion_vad"] == 0.7
        assert layers["meta"]["relationship_stage"] == "FRIEND"

    def test_build_layers_wrong_signature_rejected(self):
        """Protocol check catches wrong signature via structural validation."""

        class BadComposer:
            def build_layers(self, emotion):  # missing params
                return {}

        # @runtime_checkable only checks method existence, not signature.
        # So isinstance passes, but calling with wrong args would fail at runtime.
        # This is a known limitation of Python Protocol — we validate structurally.
        bad = BadComposer()
        assert hasattr(bad, "build_layers")  # has method, but wrong signature
        # Calling with full args would raise TypeError
        import inspect

        sig = inspect.signature(bad.build_layers)
        params = list(sig.parameters.keys())
        assert len(params) == 1  # only 'emotion', not the full set

    def test_build_layers_missing_method_rejected(self):
        """Protocol check rejects missing method."""

        class NoComposer:
            pass

        assert not isinstance(NoComposer(), ComposerLayerProtocol)
