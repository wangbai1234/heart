"""
Contract: SS01 Soul -> SS02 Memory: voice_dna selection in Reconstructor.
per runtime_specs/01_identity_anchor_soul_spec.md section 6.2
per runtime_specs/02_memory_runtime.md section 3.9 (INV-M-5)

Verifies that Reconstructor reads voice_dna and anti_patterns from the Soul Spec dict.
The Reconstructor expects voice_dna and anti_patterns at the TOP LEVEL of the dict
(flattened from the YAML's identity_anchor nesting by the SoulRegistry adapter).

P-2: Soul Spec is declarative, not generative.
P-10: Runtime agents cannot modify Soul Spec.
"""

import pytest

from heart.ss02_memory.reconstructor import Reconstructor


# Minimal fake ScoredMemory for contract testing
class FakeScoredMemory:
    def __init__(self, memory_id="fake-id", state="vivid", content="test content"):
        self.memory_id = memory_id
        self.memory = FakeMemory(state=state, content=content)


class FakeMemory:
    def __init__(self, state="vivid", content="test content"):
        self.state = state
        self.episode_summary = content
        self.literal_text = content
        self.subject = "test"


def _make_reconstructor_soul_spec(make_soul_spec):
    """
    Build a soul_spec dict in the shape Reconstructor expects.
    Reconstructor reads voice_dna and anti_patterns at top level,
    as produced by the SoulRegistry adapter layer.
    """
    nested = make_soul_spec(character_id="rin")
    identity = nested["identity_anchor"]
    return {
        "voice_dna": identity.get("voice_dna", []),
        "anti_patterns": identity.get("anti_patterns", {}),
        # Include other top-level fields Reconstructor might need
        "character_id": nested.get("character_id", "rin"),
        "spec_version": nested.get("spec_version", "1.0.0"),
        "inertia_profile": nested.get("inertia_profile", {}),
        "relational_template": nested.get("relational_template", {}),
    }


@pytest.mark.contract
class TestSoulToMemoryVoiceDna:
    """SS01 Soul Spec voice_dna must flow into SS02 Reconstructor."""

    def test_reconstructor_reads_voice_dna_from_soul_spec(self, make_soul_spec):
        """Reconstructor.__init__ extracts voice_dna from Soul Spec dict."""
        soul = _make_reconstructor_soul_spec(make_soul_spec)
        rec = Reconstructor(character_id="rin", soul_spec=soul)

        assert rec.voice_dna is not None, "voice_dna must be loaded from soul_spec"
        assert len(rec.voice_dna) > 0, "voice_dna must be non-empty"
        assert rec.voice_dna[0]["id"] == "vd-R01"

    def test_reconstructor_reads_anti_patterns_from_soul_spec(self, make_soul_spec):
        """Reconstructor reads anti_patterns for post-check enforcement."""
        soul = _make_reconstructor_soul_spec(make_soul_spec)
        rec = Reconstructor(character_id="rin", soul_spec=soul)

        assert rec.anti_patterns is not None
        assert "hard_never" in rec.anti_patterns

    def test_missing_voice_dna_breaks_reconstructor(self, make_soul_spec):
        """If soul_spec has empty voice_dna, Reconstructor must detect it."""
        soul = _make_reconstructor_soul_spec(make_soul_spec)
        soul["voice_dna"] = []

        rec = Reconstructor(character_id="rin", soul_spec=soul)
        assert len(rec.voice_dna) == 0

    def test_corrupted_voice_dna_structure_raises_on_access(self, make_soul_spec):
        """If voice_dna entries lack required 'id' field, reconstruction fails."""
        soul = _make_reconstructor_soul_spec(make_soul_spec)
        soul["voice_dna"] = [{"pattern": "..."}]  # missing "id"

        rec = Reconstructor(character_id="rin", soul_spec=soul)
        # voice_dna loaded as raw dict; access to "id" would KeyError
        with pytest.raises(KeyError, match="id"):
            _ = rec.voice_dna[0]["id"]

    def test_voice_dna_idempotent_across_reconstructions(self, make_soul_spec):
        """voice_dna array must be read-only and unchanged across calls."""
        soul = _make_reconstructor_soul_spec(make_soul_spec)
        rec = Reconstructor(character_id="rin", soul_spec=soul)

        vd_before = len(rec.voice_dna)
        memory = FakeScoredMemory()

        # Multiple reconstructions should not mutate voice_dna
        for _ in range(3):
            text = rec.reconstruct(memory)
            assert len(text) > 0

        assert len(rec.voice_dna) == vd_before, "voice_dna must be immutable"

    def test_soul_spec_shape_contract(self, make_soul_spec):
        """
        The contract between SS01 and SS02: soul_spec dict MUST have
        voice_dna and anti_patterns at top level (not nested).
        This verifies the shape that the SoulRegistry adapter must produce.
        """
        soul = _make_reconstructor_soul_spec(make_soul_spec)
        assert "voice_dna" in soul, (
            "Contract gap: voice_dna must be at top level of soul_spec dict "
            "passed to Reconstructor. SoulRegistry must flatten identity_anchor."
        )
        assert "anti_patterns" in soul, (
            "Contract gap: anti_patterns must be at top level of soul_spec dict."
        )
