# Decay Engine Implementation Summary

**Date**: 2026-05-17  
**Author**: 心屿团队  
**Status**: ✅ Implemented and Tested

---

## Overview

Implemented the **Decay Engine** per `/runtime_specs/02_memory_runtime.md` §10.4.1 with all 7 bug fixes from design review.

## Files Created

### 1. `backend/heart/ss02_memory/decay_engine.py`
Core implementation:
- `DecayEngine` class with `apply_decay_lazy()` and `apply_decay_batch()`
- `reinforce_memory()` async function
- `ReinforcementTrigger` enum

### 2. `backend/tests/unit/test_decay_engine.py`
Comprehensive test suite:
- **28 tests** covering all 12 invariants (I1-I12)
- Edge cases (NULL handling, extreme values, clock skew)
- Performance benchmark (0.023ms per memory, well under 1ms target)
- Batch decay with DB writes
- Reinforcement persistence

---

## Algorithm

```
I(t) = max(I_floor, I_0 × T(t) × E × R)

Where:
  T(t) = exp(-Δt_days / τ)           # L2: τ=14, L3: τ=60, L4: τ=∞
  E = 1 + |v| × 0.5 + a × 0.3        # Emotional [1, 1.8]
  R = min(1 + ln(1+r) × 0.2, 2.0)    # Recall (capped)
  I_floor = max(|v|×0.1, min(0.20, ln(1+r)×0.03))  # Recall-aware
```

---

## Bug Fixes Applied

| # | Bug | Fix | Impact |
|---|-----|-----|--------|
| 1 | Integer day truncation | Use `total_seconds() / 86400.0` | No step jumps |
| 2 | Unbounded emotional multiplier | Clamp inputs at function boundary | No importance explosion |
| 3 | Recall multiplier grows forever | Hard cap R at 2.0 (~150 recalls) | Prevents bot spam abuse |
| 4 | Floor ignores recall | `floor = max(emotional, recall_floor)` | Neutral facts don't vanish |
| 5 | **CRITICAL**: Reinforcement wiped by decay | Bump `initial_importance` not `importance_score` | Hebbian persists |
| 6 | NULL handling crashes | Default to 0 for NULL fields | No AttributeError |
| 7 | Clock skew inflates importance | `elapsed = max(0, elapsed)` | Distributed robustness |

---

## Test Results

```
============================== 28 passed in 0.24s ==============================
Average decay time: 0.023ms per memory (target: < 1ms)
```

### Invariants Tested (I1-I12)

- ✅ **I1**: Decay non-increasing without reinforcement
- ✅ **I2**: L4 immutable (never decays)
- ✅ **I3**: Floor enforced (emotional + recall-aware)
- ✅ **I4**: Cap enforced at 0.95
- ✅ **I5**: L2 decays faster than L3 (τ_L2 < τ_L3)
- ✅ **I6**: Monotone in recall_count
- ✅ **I7**: Monotone in |valence|
- ✅ **I8**: Idempotent at same timestamp
- ✅ **I9**: Reinforcement persists after decay (bug fix test)
- ✅ **I10**: State function monotone in importance
- ✅ **I11**: Finite output (no NaN/Inf)
- ✅ **I12**: Clock skew safety

### Edge Cases Tested

- NULL emotional_peak → default {valence:0, arousal:0}
- NULL recall_count → default 0
- Importance starts at 0
- Very recent memory (< 1 hour) → skip decay
- Very old memory (3 years) → decay to floor
- Out-of-bounds emotion values → clamped
- Clock skew (future timestamp) → elapsed = 0
- Extreme values (no NaN/Inf)

---

## Performance

**Benchmark**: 1000 iterations, warm cache

```
Average: 0.023ms per memory
Target:  < 1ms per memory
Margin:  43x faster than requirement
```

**Throughput estimate**:
- 1 memory = 0.023ms
- 1000 memories/sec (single-threaded)
- Batch mode can process 10K+ memories/minute

---

## Integration Points

### Used By
- **Consolidation Job** (nightly): calls `apply_decay_batch()`
- **Retrieval Service**: calls `apply_decay_lazy()` on-the-fly
- **Reinforcement Triggers**: call `reinforce_memory()` on user interactions

### Dependencies
- `heart.ss02_memory.models`: EpisodicMemory, FactNode, IdentityMemory
- `sqlalchemy.ext.asyncio`: AsyncSession for DB writes
- `structlog`: Structured logging
- Python stdlib: `math`, `datetime`

---

## Usage Examples

### Lazy Decay (No DB Write)
```python
from heart.ss02_memory import DecayEngine

engine = DecayEngine()
memory = await fetch_memory(memory_id)
decayed = engine.apply_decay_lazy(memory, now=datetime.now(timezone.utc))
# Use decayed.importance_score for ranking
```

### Batch Decay (Nightly Job)
```python
from heart.ss02_memory import DecayEngine

engine = DecayEngine()
stats = await engine.apply_decay_batch(
    session,
    user_id=user_id,
    character_id="rin",
)
# stats = {"l2_processed": 150, "l3_processed": 320, ...}
```

### Reinforcement
```python
from heart.ss02_memory import reinforce_memory, ReinforcementTrigger

await reinforce_memory(
    session,
    memory_id=memory_id,
    trigger=ReinforcementTrigger.USER_RE_MENTIONED,
)
# Boosts initial_importance by 0.15
```

---

## Design Decisions

### 1. R cap at 2.0
Prevents bot/spam abuse while preserving Hebbian semantics up to ~150 recalls. After that, L4 promotion is the path forward.

### 2. Recall-aware floor
Essential for M-8 compliance. Without it, neutral but important memories (like "user lives in Beijing") could fade to archived despite being referenced constantly.

### 3. Reinforcement model
Bump `initial_importance` directly (not `importance_score`). This is cleaner than maintaining a separate boost field with its own decay curve, and semantically accurate ("this memory became more important").

### 4. L2/L3 ceiling at 0.95
Let L4 promotion criteria (M-15) enforce sacred memory gates, not the decay formula. A memory can stay vivid without being sacred.

---

## Next Steps

- [ ] Integrate with Consolidation Job (§3.5 阶段 3)
- [ ] Add Prometheus metrics for decay timing
- [ ] Implement L4 promotion logic (M-15)
- [ ] Add decay visualization in admin dashboard

---

## References

- **Spec**: `/runtime_specs/02_memory_runtime.md` §10.4.1
- **Tests**: `tests/unit/test_decay_engine.py`
- **Implementation**: `heart/ss02_memory/decay_engine.py`
