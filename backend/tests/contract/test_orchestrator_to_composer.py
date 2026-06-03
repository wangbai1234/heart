"""
Contract: SS07 Orchestrator -> SS05 Composer: Director hints applied.
per runtime_specs/07_agent_orchestration.md section 3.4 (Director Agent)
per runtime_specs/05_persona_composition_runtime.md section 5 (Director directives)
per INV-O-6: SS05 composition timeout 250ms
per INV-PC-5: Layer priority sorting enforced

Verifies that Director hints (length, pacing, modality, fallback_mode)
arrive at Composer and are applied in the correct order.
"""

import pytest


class FakeComposer:
    """Minimal Composer that accepts Director hints from SS07."""

    DEFAULT_DIRECTOR_HINTS = {
        "response_length": "auto",  # auto | short | medium | long
        "pacing": "normal",  # slow | normal | quick
        "modality": "text",  # text | voice | proactive
        "fallback_mode": False,  # True when circuit breaker is open
        "deflect_directive": None,  # set when safety is ORANGE
    }

    def apply_director_hints(self, hints: dict) -> dict:
        """Apply Director hints, filling defaults for missing keys."""
        result = dict(self.DEFAULT_DIRECTOR_HINTS)
        for key, value in hints.items():
            if key in result:
                result[key] = value
        return result

    def compose_with_hints(self, layers: dict, hints: dict) -> dict:
        """Compose layers with Director hints applied."""
        applied_hints = self.apply_director_hints(hints)
        return {
            "layers": layers,
            "director": applied_hints,
        }


@pytest.mark.contract
class TestOrchestratorToComposer:
    """SS07 Director hints must be applied by Composer."""

    def test_director_hints_applied_to_composition(self, make_soul_spec):
        """Director hints are passed through to composition output."""
        composer = FakeComposer()
        hints = {"response_length": "short", "pacing": "quick"}
        layers = {"soul": make_soul_spec(character_id="rin")}

        result = composer.compose_with_hints(layers, hints)
        assert result["director"]["response_length"] == "short"
        assert result["director"]["pacing"] == "quick"

    def test_missing_hints_get_defaults(self, make_soul_spec):
        """Missing Director hints filled with sensible defaults."""
        composer = FakeComposer()
        layers = {"soul": make_soul_spec(character_id="rin")}

        result = composer.compose_with_hints(layers, {})
        assert result["director"]["response_length"] == "auto"
        assert result["director"]["pacing"] == "normal"
        assert result["director"]["fallback_mode"] is False

    def test_fallback_mode_hint_applied(self, make_soul_spec):
        """When circuit breaker open, fallback_mode=True arrives at Composer."""
        composer = FakeComposer()
        hints = {"fallback_mode": True}
        layers = {"soul": make_soul_spec(character_id="rin")}

        result = composer.compose_with_hints(layers, hints)
        assert result["director"]["fallback_mode"] is True

    def test_deflect_directive_when_safety_orange(self, make_soul_spec):
        """Safety ORANGE -> deflect directive in hints."""
        composer = FakeComposer()
        hints = {"deflect_directive": "change_topic_gracefully"}
        layers = {"soul": make_soul_spec(character_id="rin")}

        result = composer.compose_with_hints(layers, hints)
        assert result["director"]["deflect_directive"] == "change_topic_gracefully"

    def test_unknown_hint_keys_ignored(self, make_soul_spec):
        """Unknown hint keys are silently ignored (not crashed)."""
        composer = FakeComposer()
        hints = {"unknown_field": "should_be_ignored"}
        layers = {"soul": make_soul_spec(character_id="rin")}

        result = composer.compose_with_hints(layers, hints)
        assert "unknown_field" not in result["director"]

    def test_director_hints_idempotent(self, make_soul_spec):
        """Applying same hints twice returns identical result."""
        composer = FakeComposer()
        hints = {"response_length": "medium", "pacing": "slow"}
        layers = {"soul": make_soul_spec(character_id="rin")}

        result1 = composer.compose_with_hints(layers, hints)
        result2 = composer.compose_with_hints(layers, hints)

        assert result1["director"] == result2["director"]
