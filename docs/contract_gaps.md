# Cross-Subsystem Contract Gap Report

> Generated: 2026-05-24 | Audit scope: all 13 cross-subsystem edges

---

## GAP-001: SS03 Emotion -> SS04 Relationship - No Emotion-Delta-to-Signal Adapter

**Edge**: SS03 Emotion -> SS04 Relationship
**Expected per architecture**: Emotion deltas feed into Stage signal aggregator
**Status**: Contract gap - no defined adapter interface

### What Exists

| Artifact | Location | Description |
|----------|----------|-------------|
| EmotionState (SS03) | heart/ss03_emotion/models.py | Full VAD vector, active_stack, mood, energy |
| EmotionService.process_turn() | heart/ss03_emotion/service.py | Produces updated EmotionState with VAD deltas |
| StagePhaseEngine.evaluate() (SS04) | heart/ss04_relationship/stage_engine.py | Accepts RelationshipState + SignalBatch |
| SignalBatch | heart/ss04_relationship/stage_engine.py | Groups positive, negative, events signals |
| Signal | heart/ss04_relationship/stage_engine.py | type: str, strength: float [0,1], metadata: dict |

### What Is Missing

There is no code path or adapter interface that converts SS03 emotion deltas into SS04 Signal objects:

1. No emotion-to-signal mapping: The VAD delta produced by EmotionStateMachine.transition() (valence/arousal/dominance changes) has no defined mapping to relationship signal types (trust_building, disclosure, conflict, etc.).

2. No signal aggregation entry point: StagePhaseEngine.evaluate() takes a SignalBatch, but there is no function build_signals_from_emotion(emotion_state, prev_emotion_state) in the codebase.

3. Spec ambiguity: runtime_specs/04_relationship_phase_engine.md section 3.5 mentions signal aggregation but does not specify how SS03 feeds into it. runtime_specs/03_emotion_state_machine.md does not mention feeding deltas to SS04.

### Why This Matters

Without this interface, relationship stage transitions cannot react to emotional changes:
- A sudden drop in valence (user said something hurtful) should generate a negative relationship signal
- A sustained high-arousal positive emotion should contribute to trust-building signals
- Pending repairs in emotion should feed into relationship repair tracking

### Recommended Resolution

Define an emotion_to_relationship_signals() adapter in either heart/ss03_emotion/ or a new heart/core/bridges/ module:

```python
def emotion_to_relationship_signals(
    prev_emotion: dict,
    new_emotion: dict,
    context: dict,
) -> SignalBatch:
    # Convert emotion delta to relationship signals
    # Mapping: abs(delta_valence) > 0.3 -> signal based on direction
    #          delta_arousal > 0.3 + valence > 0 -> trust_building
    #          energy < 0.2 -> withdrawal signal (negative)
    #          pending_repairs non-empty -> repair signal (event)
    ...
```

### Related Invariants

- INV-R-2 (SS04): Every stage transition must pass all gates
- INV-E-1 (SS03): abs(delta_valence) <= inertia_cap * delta_t

---

## Summary

| # | Edge | Status | Action |
|---|------|--------|--------|
| 1 | SS01 -> SS02 | OK | Contract test exists |
| 2 | SS01 -> SS05 | OK | Contract test created |
| 3 | SS02 -> SS05 | OK | Contract test created |
| 4 | SS03 -> SS04 | GAP | Define adapter, then contract test |
| 5 | SS03 -> SS05 | OK | Existing test_ss05_consumes_ss03.py |
| 6 | SS04 -> SS05 | OK | Contract test created |
| 7 | SS04 -> SS06 | OK | Contract test created |
| 8 | SS06 -> SS05 | OK | Contract test created |
| 9 | SS06 -> SS07 | OK | Contract test created |
| 10 | SS07 -> SS05 | OK | Contract test created |
| 11 | Safety -> ALL | OK | Existing test_safety_short_circuits_composer.py |
| 12 | ModelRouter -> Providers | OK | Existing test_router_provider_protocol.py |
| 13 | CB -> ModelRouter | OK | Contract test created |

Total edges: 13 | Covered: 12 | Gaps: 1 (SS03->SS04)