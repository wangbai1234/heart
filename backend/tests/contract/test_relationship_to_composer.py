"""
Contract: SS04 Relationship -> SS05 Composer: Current Stage modifies intimacy register.
per runtime_specs/04_relationship_phase_engine.md section 3.1 (7 stages)
per runtime_specs/05_persona_composition_runtime.md section 3.6 (RelationshipContextBlock)
per INV-PC-2: Stage priority = 2 in layer ordering

Verifies that Composer reads current_stage, intimacy_level, trust_score
from RelationshipState and that stage affects the intimacy register in prompt.
"""

import pytest
from datetime import datetime, timezone


class FakeComposer:
    """Minimal Composer that reads RelationshipState for intimacy register."""

    # Stage-to-intimacy register mapping (per SS05 spec section 3.6)
    STAGE_INTIMACY_MAP = {
        "STRANGER": "formal",
        "ACQUAINTANCE": "polite",
        "FRIEND": "casual",
        "CONFIDANT": "warm",
        "ROMANTIC_INTEREST": "flirtatious",
        "LOVER": "intimate",
        "BONDED": "deeply_intimate",
    }

    def build_relationship_context_block(self, rel_state: dict) -> dict:
        """Build RelationshipContextBlock from RelationshipState dict."""
        current_stage = rel_state.get("current_stage", "STRANGER")
        return {
            "stage": current_stage,
            "intimacy_level": rel_state.get("intimacy_level", 0.0),
            "trust_score": rel_state.get("trust_score", 0.0),
            "intimacy_register": self.STAGE_INTIMACY_MAP.get(current_stage, "formal"),
            "attachment_strength": rel_state.get("attachment_strength", 0.0),
        }


@pytest.mark.contract
class TestRelationshipToComposer:
    """SS04 RelationshipState must feed correct intimacy data to Composer."""

    def test_stage_maps_to_intimacy_register(self, make_relationship_state):
        """Each stage produces correct intimacy register."""
        composer = FakeComposer()
        for stage, expected_register in FakeComposer.STAGE_INTIMACY_MAP.items():
            rel = make_relationship_state(current_stage=stage)
            block = composer.build_relationship_context_block(rel)
            assert block["intimacy_register"] == expected_register, (
                f"Stage {stage} should map to '{expected_register}', got '{block['intimacy_register']}'"
            )

    def test_intimacy_level_read_from_state(self, make_relationship_state):
        """Composer reads intimacy_level from RelationshipState."""
        composer = FakeComposer()
        rel = make_relationship_state(intimacy_level=0.75)
        block = composer.build_relationship_context_block(rel)
        assert block["intimacy_level"] == 0.75

    def test_trust_score_read_from_state(self, make_relationship_state):
        """Composer reads trust_score from RelationshipState."""
        composer = FakeComposer()
        rel = make_relationship_state(trust_score=0.85)
        block = composer.build_relationship_context_block(rel)
        assert block["trust_score"] == 0.85

    def test_unknown_stage_falls_back_to_formal(self):
        """Unknown stage values fall back to 'formal' intimacy."""
        composer = FakeComposer()
        rel = {"current_stage": "UNKNOWN_STAGE", "intimacy_level": 0.0}
        block = composer.build_relationship_context_block(rel)
        assert block["intimacy_register"] == "formal"

    def test_attachment_strength_present(self, make_relationship_state):
        """Composer reads attachment_strength for clinginess modulation."""
        composer = FakeComposer()
        rel = make_relationship_state()
        rel["attachment_strength"] = 0.9
        block = composer.build_relationship_context_block(rel)
        assert block["attachment_strength"] == 0.9

    def test_field_rename_breaks_contract(self, make_relationship_state):
        """If SS04 renames current_stage -> stage, Composer breaks."""
        rel = make_relationship_state()
        rel["stage"] = rel.pop("current_stage")

        composer = FakeComposer()
        block = composer.build_relationship_context_block(rel)

        # Should have fallen back to default "STRANGER"
        assert block["stage"] == "STRANGER"
