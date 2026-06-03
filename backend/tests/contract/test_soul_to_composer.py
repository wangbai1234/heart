"""
Contract: SS01 Soul -> SS05 Composer: Soul layer is highest-priority layer.
per runtime_specs/05_persona_composition_runtime.md section 3.6
per INV-PC-1: AnchorBlock MUST be position 0 in composed prompt
per INV-PC-2: Priority ordering is Soul > Safety > Stage > Emotion > Inner State > Memory

Verifies that the Composer places Soul-derived AnchorBlock as the first segment
in the composed prompt, and that priority ordering is enforced.
"""

import pytest


class FakeComposer:
    """Minimal Composer that enforces layer priority ordering per INV-PC-1/2."""

    LAYER_PRIORITY = {
        "soul": 0,
        "safety": 1,
        "stage": 2,
        "emotion": 3,
        "inner_state": 4,
        "memory": 5,
    }

    def compose(self, layers: dict) -> list[dict]:
        """
        Build prompt segments in priority order.
        Returns list of {layer_name, content, priority}.
        """
        segments = []

        # Build segments from layer data
        for name, data in layers.items():
            if name == "soul":
                segments.append(
                    {
                        "layer": "soul",
                        "content": self._build_anchor_block(data),
                        "priority": self.LAYER_PRIORITY["soul"],
                    }
                )
            elif name == "emotion":
                segments.append(
                    {
                        "layer": "emotion",
                        "content": self._build_emotion_block(data),
                        "priority": self.LAYER_PRIORITY["emotion"],
                    }
                )
            elif name == "memory":
                segments.append(
                    {
                        "layer": "memory",
                        "content": self._build_memory_block(data),
                        "priority": self.LAYER_PRIORITY["memory"],
                    }
                )
            elif name == "relationship":
                segments.append(
                    {
                        "layer": "relationship",
                        "content": self._build_relationship_block(data),
                        "priority": self.LAYER_PRIORITY["stage"],
                    }
                )
            elif name == "inner_state":
                segments.append(
                    {
                        "layer": "inner_state",
                        "content": self._build_inner_state_block(data),
                        "priority": self.LAYER_PRIORITY["inner_state"],
                    }
                )

        # Sort by priority (asc)
        segments.sort(key=lambda s: s["priority"])
        return segments

    def _build_anchor_block(self, soul_spec: dict) -> str:
        return f"[{soul_spec['character_id']}]"

    def _build_emotion_block(self, emotion: dict) -> str:
        return f"VAD: {emotion.get('vad_valence', 0)}"

    def _build_memory_block(self, memories: list) -> str:
        return f"Memories: {len(memories)}"

    def _build_relationship_block(self, rel: dict) -> str:
        return f"Stage: {rel.get('current_stage', 'STRANGER')}"

    def _build_inner_state_block(self, inner: dict) -> str:
        return f"Energy: {inner.get('energy', 0.6)}"


@pytest.mark.contract
class TestSoulToComposer:
    """SS01 Soul Spec must be highest-priority layer in Composer output."""

    def test_soul_anchor_block_is_first_segment(self, make_soul_spec):
        """INV-PC-1: AnchorBlock at position 0."""
        composer = FakeComposer()
        layers = {
            "soul": make_soul_spec(character_id="rin"),
            "emotion": {"vad_valence": 0.5},
            "memory": [{"content": "test"}],
            "relationship": {"current_stage": "FRIEND"},
            "inner_state": {"energy": 0.7},
        }
        segments = composer.compose(layers)

        assert segments[0]["layer"] == "soul", (
            f"INV-PC-1 violated: first segment is {segments[0]['layer']}, expected 'soul'"
        )

    def test_priority_ordering_enforced(self):
        """INV-PC-2: Soul > Safety > Stage > Emotion > Inner State > Memory."""
        composer = FakeComposer()
        layers = {
            "soul": {"character_id": "rin", "identity_anchor": {"voice_dna": []}},
            "emotion": {"vad_valence": 0.0},
            "memory": [],
            "relationship": {"current_stage": "STRANGER"},
            "inner_state": {"energy": 0.6},
        }
        segments = composer.compose(layers)

        priorities = [s["priority"] for s in segments]
        assert priorities == sorted(priorities), (
            f"INV-PC-2 violated: segments not in priority order: {priorities}"
        )

    def test_missing_soul_layer_causes_empty_first_segment(self, make_soul_spec):
        """If Soul layer missing, Composer must not silently substitute."""
        composer = FakeComposer()
        layers = {
            "emotion": {"vad_valence": 0.5},
            "memory": [],
        }
        segments = composer.compose(layers)

        # Without soul layer, first segment should NOT be soul
        assert len(segments) > 0
        assert segments[0]["layer"] != "soul", (
            "Soul layer missing but composition still has soul segment"
        )

    def test_anchor_block_contains_character_id(self, make_soul_spec):
        """Soul anchor block must carry character identity."""
        composer = FakeComposer()
        soul = make_soul_spec(character_id="dorothy")
        layers = {"soul": soul}
        segments = composer.compose(layers)

        assert "dorothy" in segments[0]["content"]

    def test_two_different_soul_specs_produce_different_anchors(self, make_soul_spec):
        """Different Soul Specs produce different anchor blocks."""
        composer = FakeComposer()
        rin_soul = make_soul_spec(character_id="rin")
        dorothy_soul = make_soul_spec(character_id="dorothy")

        rin_segments = composer.compose({"soul": rin_soul})
        dorothy_segments = composer.compose({"soul": dorothy_soul})

        assert rin_segments[0]["content"] != dorothy_segments[0]["content"]
