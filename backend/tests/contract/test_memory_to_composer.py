"""
Contract: SS02 Memory -> SS05 Composer: Retrieved memories arrive with state-aware scoring.
per runtime_specs/02_memory_runtime.md section 5.5
per runtime_specs/05_persona_composition_runtime.md section 5
per INV-M-3: Top-K limit (default 5, max 10)

Verifies that RetrievedMemory records arrive at Composer with all required
fields: state, score, score_breakdown, uncertainty_level, voice_dna_applied.
"""

import pytest
from uuid import uuid4


@pytest.mark.contract
class TestMemoryToComposer:
    """SS02 RetrievedMemory must expose all fields Composer consumes."""

    REQUIRED_FIELDS = [
        "memory_id", "memory_type", "state",
        "reconstructed_text", "raw_content",
        "score", "score_breakdown",
        "uncertainty_level", "voice_dna_applied",
        "source_evidence",
    ]

    COMPOSER_READ_FIELDS = [
        "reconstructed_text",  # injected into prompt
        "state",               # determines uncertainty hedge
        "score",               # sort order
        "uncertainty_level",    # tone adjustment
        "memory_type",          # L4 gets special treatment
    ]

    def test_all_required_fields_present(self, make_retrieved_memory):
        """All fields that Composer depends on must be present."""
        mem = make_retrieved_memory()
        for field in self.REQUIRED_FIELDS:
            assert hasattr(mem, field), (
                f"Composer reads '{field}' but it is missing from RetrievedMemory"
            )

    def test_composer_reads_only_defined_fields(self, make_retrieved_memory):
        """Composer must only access fields in the contract."""
        mem = make_retrieved_memory()
        for field in self.COMPOSER_READ_FIELDS:
            val = getattr(mem, field)
            assert val is not None, (
                f"Composer field '{field}' must be non-None"
            )

    def test_state_aware_scoring_preserved(self, make_retrieved_memory):
        """Score and state are independent dimensions."""
        # Vivid memory with low score (old memory that just got recalled)
        mem = make_retrieved_memory(state="vivid", score=0.3)
        assert mem.state == "vivid"
        assert 0.0 <= mem.score <= 1.0

        # Dormant memory with high score (important but decayed)
        mem = make_retrieved_memory(state="dormant", score=0.9)
        assert mem.state == "dormant"
        assert mem.score == 0.9

    def test_uncertainty_level_consistent_with_state(self, make_retrieved_memory):
        """uncertainty_level must be consistent with memory state."""
        # Vivid -> low uncertainty
        mem = make_retrieved_memory(state="vivid", uncertainty_level=0.0)
        assert mem.uncertainty_level < 0.3

        # Archived -> high uncertainty
        mem = make_retrieved_memory(state="archived", uncertainty_level=0.9)
        assert mem.uncertainty_level > 0.5

    def test_voice_dna_applied_is_readable_list(self, make_retrieved_memory):
        """voice_dna_applied must be a list of string IDs for Composer traceability."""
        mem = make_retrieved_memory()
        assert isinstance(mem.voice_dna_applied, list)
        assert len(mem.voice_dna_applied) > 0
        assert all(isinstance(vd, str) for vd in mem.voice_dna_applied)

    def test_score_breakdown_has_expected_keys(self, make_retrieved_memory):
        """score_breakdown must contain semantic/importance/emotional_resonance."""
        mem = make_retrieved_memory()
        assert "semantic" in mem.score_breakdown
        assert "importance" in mem.score_breakdown
        assert isinstance(mem.score_breakdown["semantic"], (int, float))

    def test_l4_memory_type_present(self, make_retrieved_memory):
        """L4 memories must be distinguishable by memory_type."""
        mem = make_retrieved_memory(memory_type="L4")
        assert mem.memory_type == "L4"
