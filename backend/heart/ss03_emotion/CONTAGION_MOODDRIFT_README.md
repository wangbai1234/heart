# SS03 Contagion Engine + Mood Drift Engine

Implementation of Contagion and Mood Drift engines per runtime spec `03_emotion_state_machine.md` §3.5, §3.7, and §10.3.

## Components Added

### 1. Contagion Engine (`contagion.py`)
Soul-aware user emotion transmission to character.

**Key Features:**
- Reads `soul.cognitive_style.emotional_inertia.shock_resistance` directly
- Per-character empathy curves (Rin: 0.75 resistance, Dorothy: 0.2 resistance)
- Relationship phase modulation (stranger → bonded)
- Dominance never transfers (per spec)
- Target latency: < 5ms per turn

**API:**
```python
from heart.ss03_emotion.contagion import apply_contagion, compute_empathy_curve

# Apply contagion
delta_vad = apply_contagion(
    user_emotion_vad={"valence": 0.8, "arousal": 0.7, "dominance": 0.6},
    current_state=emotion_state,
    soul=soul_config,  # Now takes full Soul dict
    relationship_phase="close_friend",
)

# Compute empathy strength
empathy = compute_empathy_curve(soul_config, "romantic")
# Rin as romantic: ~0.24 (still guarded)
# Dorothy as romantic: ~0.76 (very empathetic)
```

**Formula:**
```
strength = (1 - shock_resistance) × phase_modifier
Δvalence = (user.valence - current.valence) × strength × 0.15
Δarousal = (user.arousal - current.arousal) × strength × 0.10
Δdominance = 0  # Never transfers
```

### 2. Mood Drift Engine (`mood_drift.py`)
Hourly mood baseline drift based on recent emotion history and Soul volatility.

**Key Features:**
- 24h moving average + EWMA (Exponentially Weighted Moving Average)
- Soul.mood_volatility modulation (Rin: 0.2 stable, Dorothy: 0.75 volatile)
- Environmental factors (time of day, weekday)
- Longing gradient (grows with user absence, capped at 7 days)
- Floor/ceiling bounds: |valence| ≤ 0.5 (mood is backdrop, not peak)
- Target latency: P95 < 200ms per user

**API:**
```python
from heart.ss03_emotion.mood_drift import drift_mood

# Apply hourly drift
new_mood = drift_mood(
    current_state=emotion_state,
    soul=soul_config,
    hours_since_last=1.0,
    days_since_last_interaction=3.0,
    current_local_time=datetime.now(timezone.utc),
)

# Returns updated mood dict:
# {
#     "valence_baseline": float,
#     "arousal_baseline": float,
#     "dominance_baseline": float,
#     "background_emotions": ["weariness", "longing", ...],
#     "last_updated_at": str,
#     "drift_history": [...],
# }
```

**Algorithm:**
1. Compute 24h simple moving average from `recent_vad_history`
2. Compute EWMA (alpha=0.3) for smoother transitions
3. Blend: 60% EWMA + 40% average
4. Apply Soul volatility:
   - High volatility: mood follows blended_vad quickly
   - Low volatility: mood drifts slowly toward Soul baseline
5. Apply environmental factors (late night → arousal -0.05, weekend → valence +0.02)
6. Apply longing gradient (absence → valence -0.01/day, arousal +0.005/day)
7. Enforce bounds: valence ∈ [-0.5, 0.5], arousal/dominance ∈ [0, 1]
8. Derive background emotions (weariness, longing, contentment, calmness)

**Drift Formula:**
```
target_vad = current_mood 
           + volatility × (blended_vad - current_mood)
           + (1 - volatility) × drift_rate × (soul_baseline - current_mood)

where:
  drift_rate = 0.05  # Slow drift toward Soul baseline per hour
  volatility ∈ [0, 1]  # Soul.mood_volatility
```

## Testing

### Contagion Tests (`test_contagion.py`)
**16 tests, all passing**

Test coverage:
- ✅ Shock resistance modulation (Rin vs Dorothy)
- ✅ Relationship phase modulation (stranger → romantic → bonded)
- ✅ Empathy curve computation
- ✅ Contagion direction (positive/negative)
- ✅ Dominance non-contagion
- ✅ Float shock_resistance values
- ✅ Missing Soul fields (graceful fallback)

**Key Tests:**
```python
def test_rin_contagion_weaker_than_dorothy():
    """Rin's contagion delta should be significantly smaller than Dorothy's."""
    # Dorothy > 2.5x more affected than Rin
    assert abs(delta_dorothy["valence"]) > abs(delta_rin["valence"]) * 2.5

def test_contagion_increases_with_intimacy():
    """Contagion should monotonically increase with intimacy."""
    # stranger < acquaintance < friend < close_friend < romantic < bonded
    for i in range(len(deltas) - 1):
        assert deltas[i + 1] >= deltas[i]
```

### Mood Drift Tests (`test_mood_drift.py`)
**23 tests, all passing**

Test coverage:
- ✅ Drift convergence to baseline over time (property test)
- ✅ Volatility modulation (Rin stable, Dorothy fluctuates)
- ✅ Floor/ceiling bounds enforcement
- ✅ Environmental factors (late night, weekday/weekend)
- ✅ Longing gradient (grows with absence, capped at 7 days)
- ✅ Moving average computation
- ✅ EWMA dampening of sudden spikes
- ✅ Drift history tracking
- ✅ Background emotion derivation

**Key Tests:**
```python
def test_property_convergence_to_baseline():
    """Property test: repeated drift without input converges to Soul baseline."""
    # Simulate 100 hours of drift without new input
    for _ in range(100):
        new_mood = drift_mood(state, soul_rin, hours_since_last=1.0)
    # Should converge toward Soul baseline (0.0, 0.3, 0.5)
    assert abs(new_mood["valence_baseline"] - 0.0) < 0.15

def test_valence_capped_at_0_5():
    """Mood valence should be capped at ±0.5 (mood is backdrop, not peak)."""
    # Even with extremely positive recent VAD
    assert new_mood["valence_baseline"] <= 0.5
```

## Run Tests

```bash
cd backend

# Run all emotion + contagion + mood drift tests
python3 -m pytest tests/unit/test_emotion*.py tests/unit/test_contagion.py tests/unit/test_mood_drift.py -v

# Results: 73 passed in 0.09s
# - 34 existing emotion tests (state machine + triggers)
# - 16 contagion tests
# - 23 mood drift tests
```

## Architecture Changes

### Before:
```python
# state_machine.py
def apply_contagion(
    user_emotion_vad: Dict,
    current_state: Dict,
    soul_shock_resistance: float,  # Just a float
    relationship_phase: str,
) -> Dict:
    ...
```

### After:
```python
# contagion.py (new file)
def apply_contagion(
    user_emotion_vad: Dict,
    current_state: Dict,
    soul: Dict,  # Full Soul dict, reads shock_resistance internally
    relationship_phase: str,
) -> Dict:
    shock_resistance = _get_shock_resistance(soul)
    # Maps "high"/"medium"/"low" → 0.75/0.5/0.2
    ...
```

### Integration with Service:

**Updated:**
- `service.py`: Now imports from `contagion` module, passes full `soul_config` dict
- `state_machine.py`: Removed `apply_contagion`, added comment directing to `contagion.py`
- `__init__.py`: Exports `apply_contagion`, `compute_empathy_curve`, `drift_mood`

**Backward Compatibility:**
Old tests updated to pass Soul dict instead of float. All existing functionality preserved.

## Performance

| Component | Target Latency | Achieved |
|-----------|---------------|----------|
| Contagion | < 5ms | < 1ms (pure calc) |
| Mood Drift | P95 < 200ms | ~2ms (no DB calls yet) |

Both engines are pure computation (no LLM, no DB in current implementation).

## Next Steps

1. **Database Integration**
   - Call `drift_mood()` from hourly cron job
   - Persist new mood baseline to PostgreSQL
   - Add observability metrics

2. **Service Integration**
   - Add `EmotionService.drift_mood_scheduled()` method
   - Connect to Inner Loop Scheduler
   - Add per-user drift job scheduling

3. **Mood Drift Enhancements**
   - Character-specific environmental sensitivity (from Soul)
   - Seasonal patterns (optional)
   - More sophisticated background emotion derivation

4. **Validation**
   - Benchmark actual latency in production
   - Validate convergence behavior over 30 days
   - A/B test Rin vs Dorothy mood stability

## References

- Spec: `/runtime_specs/03_emotion_state_machine.md`
- Soul Specs: `/soul_specs/{rin,dorothy}/v1.0.0.yaml`
- Models: `backend/heart/ss03_emotion/models.py`

---

**Status**: ✅ Implementation complete, all tests passing  
**Author**: 心屿团队  
**Last Updated**: 2026-05-20
