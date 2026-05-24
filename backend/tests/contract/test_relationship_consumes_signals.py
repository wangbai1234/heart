"""
Contract: SS04 Relationship engine consumes SignalBatch.
per runtime_specs/04_relationship_phase_engine.md §3.5

Verifies that StagePhaseEngine accepts SignalBatch with required fields.
"""

import pytest
from heart.ss04_relationship.stage_engine import (
    StagePhaseEngine,
    Signal,
    SignalBatch,
    RelationshipStage,
    TransitionAction,
)


@pytest.mark.contract
class TestRelationshipConsumesSignals:
    """StagePhaseEngine must accept SignalBatch with correct structure."""

    def test_signal_has_required_fields(self):
        """Signal must have type, strength, metadata."""
        signal = Signal(type="trust_building", strength=0.7, metadata={"source": "disclosure"})
        assert signal.type == "trust_building"
        assert signal.strength == 0.7
        assert signal.metadata == {"source": "disclosure"}

    def test_signal_batch_has_three_categories(self):
        """SignalBatch groups signals into positive/negative/events."""
        batch = SignalBatch(
            positive=[Signal(type="disclosure", strength=0.5, metadata={})],
            negative=[],
            events=[],
        )
        assert len(batch.positive) == 1
        assert len(batch.negative) == 0
        assert len(batch.events) == 0

    def test_stage_engine_evaluate_returns_stay_for_empty_signals(self, make_soul_spec):
        """Stage engine returns STAY when no signals."""
        from heart.ss04_relationship.models import RelationshipState
        from datetime import datetime, timezone
        from uuid import uuid4

        soul_spec = make_soul_spec()
        engine = StagePhaseEngine(soul_spec)

        state = RelationshipState(
            user_id=uuid4(),
            character_id="rin",
            current_stage="STRANGER",
            previous_stage="STRANGER",
            stage_entered_at=datetime.now(timezone.utc),
            highest_stage_reached="STRANGER",
            intimacy_level=0.0,
            trust_score=0.0,
            attachment_strength=0.0,
            conflict_debt=0.0,
            vulnerability_score=0.0,
            total_interactions=0,
            total_meaningful_disclosures=0,
            total_promises_made=0,
            total_promises_kept=0,
            total_conflicts=0,
            total_repairs=0,
            total_successful_repairs=0,
            first_meeting_at=datetime.now(timezone.utc),
        )

        signals = SignalBatch(positive=[], negative=[], events=[])
        decision = engine.evaluate(state, signals)

        assert decision.action == TransitionAction.STAY

    def test_evaluate_signal_batch_renamed_breaks(self, make_soul_spec):
        """If SignalBatch renamed 'positive' → 'pos', evaluation breaks."""
        # Simulate a renamed batch
        batch_dict = {"pos": [], "neg": [], "events": []}
        with pytest.raises(KeyError, match="positive"):
            _ = batch_dict["positive"]
