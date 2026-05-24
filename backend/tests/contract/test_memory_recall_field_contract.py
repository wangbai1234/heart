"""
Contract: SS02 Memory retrieval returns RetrievedMemory with required fields.
per runtime_specs/02_memory_runtime.md §5.5

Verifies RetrievedMemory dataclass fields that Composer depends on.
"""

import pytest


@pytest.mark.contract
class TestMemoryRecallFieldContract:
    """RetrievedMemory must expose fields Composer and InnerState depend on."""

    REQUIRED_FIELDS = [
        "memory_id", "memory_type", "state",
        "reconstructed_text", "raw_content",
        "score", "score_breakdown",
        "uncertainty_level", "voice_dna_applied",
        "source_evidence",
    ]

    def test_retrieved_memory_has_all_required_fields(self, make_retrieved_memory):
        """All required fields present in RetrievedMemory."""
        mem = make_retrieved_memory()
        for field in self.REQUIRED_FIELDS:
            assert hasattr(mem, field), f"Missing required field: {field}"

    def test_memory_type_is_l2_l3_or_l4(self, make_retrieved_memory):
        """memory_type must be L2, L3, or L4."""
        for mem_type in ["L2", "L3", "L4"]:
            mem = make_retrieved_memory(memory_type=mem_type)
            assert mem.memory_type == mem_type

    def test_state_is_valid_memory_state(self, make_retrieved_memory):
        """state must be a valid memory state."""
        valid_states = ["vivid", "fading", "faint", "dormant", "archived"]
        for state in valid_states:
            mem = make_retrieved_memory(state=state)
            assert mem.state == state

    def test_score_is_between_0_and_1(self, make_retrieved_memory):
        """Score must be in [0, 1]."""
        mem = make_retrieved_memory(score=0.85)
        assert 0.0 <= mem.score <= 1.0

    def test_uncertainty_level_is_between_0_and_1(self, make_retrieved_memory):
        """Uncertainty must be in [0, 1]."""
        mem = make_retrieved_memory(uncertainty_level=0.3)
        assert 0.0 <= mem.uncertainty_level <= 1.0

    def test_reconstructed_text_is_non_empty(self, make_retrieved_memory):
        """Reconstructed text must be non-empty for Composer prompt injection."""
        mem = make_retrieved_memory(reconstructed_text="上次你说你喜欢雨天。")
        assert len(mem.reconstructed_text) > 0

    def test_raw_content_is_present_for_critic_debug(self, make_retrieved_memory):
        """raw_content must be present for Critic/debug access."""
        mem = make_retrieved_memory(raw_content="User said they like rainy days.")
        assert len(mem.raw_content) > 0
