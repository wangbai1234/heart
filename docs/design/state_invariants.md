# State Invariant Verification Framework

**Status:** Design (not yet implemented)
**Author:** Heart Platform
**Last updated:** 2026-05-24
**Scope:** SS02 Memory, SS03 Emotion, SS04 Relationship, SS06 Initiative, SS07 Safety/Orchestration

---

## 1. Motivation

Heart's runtime is a stack of stateful subsystems whose correctness depends on
invariants that are **not enforceable by static types** — e.g. "L1 ⊂ L2 ⊂ L3 ⊂ L4",
"PURPLE-level user message never reaches Soul composition", "trust_score moves
slower up than down". These rules currently live as prose in `runtime_specs/`
and as ad-hoc asserts inside individual services.

Two failure modes have already shown up in the codebase:

1. **Spec drift** — an AI-authored refactor preserves test pass/fail but breaks
   a structural invariant (e.g. promoted L4 fact missing from L3 after re-encode).
2. **Coverage gaps** — unit tests check one path; the invariant holds on that
   path but not under the random sequencing real traffic produces.

This framework adds two complementary verification layers so that **every code
change is checked against the invariant set the spec author intended**, without
slowing the hot path in production.

### Non-goals

- Replacing the existing unit / integration / contract test pyramid.
- Distributed invariants (cross-service consistency over Kafka). Defer to
  outbox + eventual-consistency tests.
- Performance assertions (covered by SLO tests).

---

## 2. Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Invariant Catalog (this document)                             │
│  - INV-XX-N: subsystem, predicate, severity, source, strategy  │
└────────────────────────────────────────────────────────────────┘
                  │ enumerated by ID
        ┌─────────┴──────────┐
        │                    │
        ▼                    ▼
┌────────────────┐   ┌──────────────────────────────────────────┐
│ Layer 1        │   │ Layer 2                                  │
│ Hypothesis     │   │ Runtime decorators                       │
│ property tests │   │  @invariant("inv-r-4.trust-asymmetry")   │
│                │   │  - DEV: always-on                        │
│ tests/         │   │  - PROD: 1% sampled                      │
│   properties/  │   │  - TEST: always-on                       │
└────────────────┘   │ Violation → log + metric + Sentry        │
                     └──────────────────────────────────────────┘
```

Both layers consult the **same registry** (`backend/heart/infra/invariants.py`)
so that an invariant added once is automatically:

- Available as `@invariant("...")` at runtime.
- Discoverable by a Hypothesis test generator that asserts the same predicate.
- Visible in `/metrics` as `heart_invariant_check_total{id, result}`.

---

## 3. Layer 1 — Property-based tests (Hypothesis)

### 3.1 Location

```
backend/tests/properties/
├── conftest.py                  # shared strategies (turn_seq, user_msg, etc.)
├── strategies.py                # custom Hypothesis strategies per domain object
├── test_memory_invariants.py    # INV-M-*
├── test_emotion_invariants.py   # INV-E-*
├── test_relationship_invariants.py  # INV-R-*
├── test_initiative_invariants.py    # INV-I-*
└── test_safety_invariants.py    # INV-O-*
```

### 3.2 Test shape

Each invariant gets at least **one Hypothesis test** that:

1. Generates a **random valid input sequence** — usually a list of turn events
   or signals, drawn from a domain-specific strategy.
2. Runs the sequence through the **real service** (with in-memory fakes for
   I/O — Postgres replaced by `heart.infra.fakes.MemFakes`, LLM by
   `heart.infra.llm_providers.fake.FakeLLM`).
3. After **each step**, asserts the invariant's predicate on the resulting
   state. Failing the assertion at step *k* is reported with the minimized
   shrunk sequence — Hypothesis's default behaviour.

```
# illustrative, NOT implementation
@given(turn_sequences(min_size=1, max_size=20))
@settings(max_examples=200, deadline=2_000)
def test_inv_m_1_l1_subset_l2(seq):
    svc = MemoryService(MemFakes())
    for turn in seq:
        svc.ingest(turn)
        assert_invariant("inv-m-1.l1-subset-l2", svc.snapshot())
```

### 3.3 Strategies (must be writable)

- `user_message_strategy()` — text + metadata, biased to include edge cases
  (empty, very long, multi-emoji, mixed-language, safety triggers).
- `signal_event_strategy()` — relationship signals with the 8 known types.
- `emotion_trigger_strategy()` — bounded VAD deltas.
- `time_advance_strategy()` — `timedelta` jumps to expose decay / cooldown.

Strategies live in `tests/properties/strategies.py`; the goal is that adding
a new invariant rarely requires writing a new strategy from scratch.

### 3.4 Stateful tests

For invariants that are sequential (e.g. INV-R-1 "highest_stage monotonic"),
use Hypothesis `RuleBasedStateMachine` rather than plain `@given`. The state
machine wraps the service and exposes user actions as rules; Hypothesis then
searches for sequences that violate the invariant.

### 3.5 CI integration

- Properties run in the existing `pytest` job, **separate marker**
  (`-m properties`), so they can be selectively skipped in PR-fast mode and
  always run in the nightly + pre-release jobs.
- `max_examples=200` per invariant in CI; `max_examples=2000` in the weekly
  "deep fuzz" cron job (records artifacts to S3).

---

## 4. Layer 2 — Runtime invariant assertions

### 4.1 Registry — `backend/heart/infra/invariants.py`

The registry holds, for each invariant ID:

- `id` — `inv-xx-n.short-slug`
- `subsystem` — `memory | emotion | relationship | initiative | safety | orchestration`
- `severity` — `FATAL | WARN`
- `predicate` — pure function `(state) -> bool`
- `extract_state` — function the decorator uses to gather the relevant slice
  of state for the predicate (avoids handing the whole world to every check)

```
# illustrative shape, NOT implementation
@registry.register(
    id="inv-r-4.trust-asymmetry",
    subsystem="relationship",
    severity="WARN",
)
def inv_r_4(before, after):
    delta = after.trust - before.trust
    return delta <= 0.05 if delta > 0 else delta >= -0.20
```

### 4.2 Decorator usage

```
# illustrative
@invariant("inv-r-4.trust-asymmetry")
def apply_trust_signals(state, signals):
    ...
    return new_state
```

The decorator:

1. Looks up the invariant in the registry.
2. Captures `before` (return of `extract_state(*args, **kwargs)`).
3. Invokes the wrapped function.
4. Captures `after` (return of `extract_state(result)`).
5. Evaluates `predicate(before, after)`.
6. On failure:
   - **FATAL** → raises `InvariantViolation` (caller decides what to do; in
     test mode this fails the test; in DEV it bubbles; in PROD it is caught
     by the orchestrator one level up and routed to a fallback).
   - **WARN** → logs structured event, increments metric, optionally sends
     Sentry breadcrumb. Does **not** raise.

### 4.3 Sampling and modes

| Mode | Triggered by | Behaviour |
|------|--------------|-----------|
| `always` | `HEART_INVARIANTS=always` or `pytest` | every call checked |
| `dev`    | `HEART_ENV=dev` (default) | every call checked |
| `sampled`| `HEART_ENV=prod` | 1% of turns, sampling decision made by `trace_id` hash to keep determinism within a turn |
| `off`    | `HEART_INVARIANTS=off` | no overhead; the decorator becomes a pass-through |

Sampling rate is per-invariant overridable; safety invariants (INV-O-2,
INV-O-3, INV-O-5) are forced to `always` regardless of env.

### 4.4 Telemetry

- **Metric:** `heart_invariant_check_total{id, result=ok|violation, severity}`
  — Prometheus counter.
- **Metric:** `heart_invariant_check_duration_seconds{id}` — histogram, lets
  us catch a runaway predicate before it impacts the hot path.
- **Log:** structured JSON event `invariant.violation` with
  `{id, severity, before, after, trace_id, user_id, character_id}`. PII is
  scrubbed by the existing logger filter.
- **Sentry:** FATAL-only by default; WARN sends a breadcrumb attached to the
  in-flight span, no new event.

### 4.5 Failure semantics

| Severity | DEV / TEST | PROD |
|----------|------------|------|
| FATAL    | raise, fail the test / abort the turn | route turn to fallback response, emit Sentry, do **not** drop the user's message |
| WARN     | log + continue | log + continue |

Critically, a violation in PROD **must never silently corrupt user state**.
For state-mutating invariants (e.g. INV-M-2 "L4 fact persisted before
emitting reinforcement"), the decorator captures the would-be mutation and,
on FATAL violation, rolls back via the surrounding unit-of-work.

---

## 5. Invariant Catalog

ID format: `INV-{subsystem-letter}-{N}`.
Subsystem letter mirrors the runtime spec convention:
M = Memory, E = Emotion, R = Relationship, I = Initiative, O = Orchestration.

Severity:
- **FATAL** — a violation means user-visible incorrectness (lost sacred
  memory, wrong safety routing, etc.). Block / rollback.
- **WARN** — a violation indicates drift but the turn can complete. Log,
  page on rate spike.

### 5.1 SS02 Memory (`INV-M-*`)

| ID | Predicate (formal) | Severity | Source | Test strategy |
|----|---------------------|----------|--------|----------------|
| **INV-M-1** | `∀ fact f promoted: f ∈ L1 ⇒ f ∈ L2_or_higher` (one-way containment) | FATAL | `02_memory_runtime.md:47-50, 183-204` | `RuleBasedStateMachine` with rules: ingest_turn, end_session, advance_day; after every rule, walk the four layer sets and check inclusion. |
| **INV-M-2** | `∀ promotion p (Lk → Lk+1): p.source_id resolvable ∧ ∃ promotion_record(p)` (no orphan promotions) | FATAL | `02_memory_runtime.md:301-305` | Hypothesis generates promotion candidate sequences; assert post-state has both target row and audit row. |
| **INV-M-3** | `L4.fact_count` strictly non-decreasing across turns (sacred persistence) | FATAL | `02_memory_runtime.md:87 (M-3), 139` | StateMachine: arbitrary `delete`, `decay`, `compact` rules; assert `len(L4)` monotonic. |
| **INV-M-4** | `∀ f ∈ L4: f.decayed_at IS NULL` (L4 never decays) | FATAL | `02_memory_runtime.md:87 (M-3)` | After random decay sweeps, scan L4 for any non-null `decayed_at`. |
| **INV-M-5** | `∀ promotion to L4: ≥2 sacred_signals AND consolidation_round ≥ 1` (multi-signal gate) | FATAL | `02_memory_runtime.md:99 (M-15)` | Hypothesis tries single-signal promotion attempts; assert refused. |
| **INV-M-6** | `total_count(L1)+total_count(L2)+total_count(L3)+total_count(L4) ≥ total_count_{t-1} − decayed_at_t` (no silent loss) | WARN | `02_memory_runtime.md:139-141` | Compare snapshots before/after every consolidation round. |
| **INV-M-7** | `∀ recall request r where r.layer=L4: hallucination_rate(r) == 0` | FATAL | `02_memory_runtime.md:172 (IMM-M-7)` | Property test seeds known L4 facts, then random recall queries; assert recalled IDs are subset of seeded. |
| **INV-M-8** | `∀ disclosure promoted to L4 at t: ∃ echo event at t' < t + 24h` (sacred ack within 24h) | WARN | `02_memory_runtime.md:166 (IMM-M-4)` | Time-advance state machine; on each promotion start a watch, fail if no echo within 24h sim time. |

### 5.2 SS03 Emotion (`INV-E-*`)

| ID | Predicate (formal) | Severity | Source | Test strategy |
|----|---------------------|----------|--------|----------------|
| **INV-E-1** | `∀ transition (v1,a1) → (v2,a2): \|v2−v1\| ≤ inertia.max_valence_change ∧ \|a2−a1\| ≤ inertia.max_arousal_change` | FATAL | `03_emotion_state_machine.md:113, 499-519` | Hypothesis generates trigger sequences with arbitrary deltas; assert post-state honors the cap *per persona's inertia config*. |
| **INV-E-2** | `∀ state s: s.valence ∈ [−1,1] ∧ s.arousal ∈ [0,1] ∧ s.dominance ∈ [−1,1]` | FATAL | `03_emotion_state_machine.md:537-543, 964` | Any state-producing call followed by range check. Trivial property but catches clamp bugs. |
| **INV-E-3** | `∀ emotion e in active_set: e.intensity ∈ [0,1] ∧ e.started_at ≤ NOW()` | FATAL | `03_emotion_state_machine.md:118` | Generate random emotion mutations; range + temporal check after each. |
| **INV-E-4** | `count(turn t: \|v_t\| > 0.85) / count(turn) < 0.05` (extreme rarity, **window=100 turns**) | WARN | `03_emotion_state_machine.md:171 (IMM-E-2)` | Long-form Hypothesis: 500-turn sequence, assert <5% extreme. |
| **INV-E-5** | The emotion graph traversed within a single turn is a DAG (no transition cycles inside one turn) | FATAL | `03_emotion_state_machine.md:283-313` (transition resolution) | StateMachine in single-turn mode; record visited transitions; assert no node repeats. |

### 5.3 SS04 Relationship (`INV-R-*`)

| ID | Predicate (formal) | Severity | Source | Test strategy |
|----|---------------------|----------|--------|----------------|
| **INV-R-1** | `s.current_stage ∈ STAGES_ENUM ∧ s.highest_stage_reached ≥ s.current_stage` (monotone high-water mark) | FATAL | `04_relationship_phase_engine.md:118` | StateMachine with promote/regress rules; assert high-water never decreases. |
| **INV-R-2** | `∀ transition T(s1→s2): if rank(s2) > rank(s1) then T.criteria_all_satisfied; if rank(s2) < rank(s1) then T.reason ∈ {regression, reset, cold_war_long}` (no unjustified jumps) | FATAL | `04_relationship_phase_engine.md:120-128` | Hypothesis generates signal sequences; intercept all transitions; assert each carries a valid reason record. |
| **INV-R-3** | `∀ d ∈ {intimacy, trust, attachment, conflict_debt}: d ∈ [0,1]` | FATAL | `04_relationship_phase_engine.md:126-129` | Range check after every mutation. |
| **INV-R-4** | `Δtrust per turn ≤ 0.05 if positive, ≥ −0.20 if negative` (asymmetric speed) | FATAL | `04_relationship_phase_engine.md:130-131, 737-758` | Random signal sequences; per-turn delta assertion. |
| **INV-R-5** | `∀ user-character pair (u,c): \|{r ∈ reunions : r.user=u ∧ r.char=c ∧ r.status='active'}\| ≤ 1` | FATAL | `04_relationship_phase_engine.md:848-895, 1032-1042` | StateMachine: arbitrary trigger_reunion / advance_reunion / end_reunion; assert query returns at most 1 active row. |
| **INV-R-6** | `∀ cold_war c: c.entered_at → c.cleared_at duration ≤ COLD_WAR_MAX (configurable, default 30d)` and `c.cleared_reason ∈ {repair, decay, timeout}` | FATAL | `04_relationship_phase_engine.md:133-134, 897-, 2344` | Time-advance state machine simulating up to 60d; assert no cold_war exceeds cap without a clear reason. |
| **INV-R-7** | `∀ pending conflict p: cold_war cannot clear unless repair_complete OR natural_decay_done` | FATAL | `04_relationship_phase_engine.md:133-135` | Generate conflict→clear sequences; assert clear requires one of the two preconditions. |
| **INV-R-8** | All queries within RelationshipService filter by `(user_id, character_id)` — no cross-pair leakage | FATAL | `04_relationship_phase_engine.md:139 (INV-R-7), 1262-1278` | Property test: seed two pairs; run arbitrary ops on one; assert the other is bit-identical before/after. |
| **INV-R-9** | After a major conflict + repair, `trust_score < pre_conflict_baseline` for 180 days | WARN | `04_relationship_phase_engine.md:164 (C-R-3)` | Time-advance scenario test (probably integration, not pure property). |

### 5.4 SS06 Initiative (`INV-I-*`)

| ID | Predicate (formal) | Severity | Source | Test strategy |
|----|---------------------|----------|--------|----------------|
| **INV-I-1** | `∀ proactive message P: P.composer_modality == 'proactive' ∧ P.anti_pattern_filter_passed ∧ P.within_stage_envelope` | FATAL | `06_inner_state_behavior_runtime.md:133-136` | Hypothesis spawns initiatives; intercept emit path; assert all three flags. |
| **INV-I-2** | `∀ scheduled trigger T: T.scheduled_at ∉ user.quiet_hours ∧ (T.scheduled_at − last_proactive_at) ≥ MIN_GAP ∧ proactive_today_count < DAILY_QUOTA` — **must hold across simulated restart** | FATAL | `06_inner_state_behavior_runtime.md:138-141`, task brief | StateMachine includes a `restart()` rule that drops in-memory caches but keeps DB; assert quotas/gaps survive. |
| **INV-I-3** | `∀ inner-state update U: U.path != 'user_turn' ∧ U.duration_ms < 200` | WARN | `06_inner_state_behavior_runtime.md:143-145` | Instrument timer in property test; assert. |
| **INV-I-4** | `∀ activity A: A.id ∈ soul.activity_pool[A.character_id]` | FATAL | `06_inner_state_behavior_runtime.md:147-148` | Hypothesis pulls characters with known pools; assert membership. |
| **INV-I-5** | `∀ anniversary trigger T: T.source_l4_id resolves ∧ payload.snapshot matches L4 row` | FATAL | `06_inner_state_behavior_runtime.md:150-152` | Seed L4; advance to anniversary; assert fields match. |
| **INV-I-6** | `∀ inner_state: each thought has expiry_at ∧ len(unfinished_thoughts) ≤ MAX_UNFINISHED (10)` | FATAL | `06_inner_state_behavior_runtime.md:153-155` | Generate arbitrary thought-additions; assert pruning. |
| **INV-I-7** | Cross-pair isolation, mirrors INV-R-8 for initiative tables | FATAL | `06_inner_state_behavior_runtime.md:156` | Same shape as INV-R-8 but on initiative + inner_state tables. |
| **INV-I-8** | `cold_war.active == true ⇒ no new initiative scheduled with type ∈ {check_in, playful_poke, break_the_ice}` | FATAL | `06_inner_state_behavior_runtime.md:163 (anti-pattern row)` | Compose cold_war state with initiative scheduler; assert scheduler returns null. |

### 5.5 SS07 Safety + Orchestration (`INV-O-*`)

| ID | Predicate (formal) | Severity | Source | Test strategy |
|----|---------------------|----------|--------|----------------|
| **INV-O-1** | `∀ turn t: ∃! trace_id appearing in every subsystem span of t` | WARN | `07_agent_orchestration.md:111` | Property test wraps the orchestrator; assert spans all share trace_id. |
| **INV-O-2** | `∀ user_message m: m → Safety.pre_filter precedes any SS05 compose call` (call-order) | FATAL | `07_agent_orchestration.md:113` | Hypothesis composes turn pipelines with arbitrary safety classifier responses; assert order via call-log. |
| **INV-O-3** | `safety.level == PURPLE ⇒ response.path == 'wellbeing_care' ∧ response.author != 'soul_composer'` (no Soul voice on PURPLE) | **FATAL** | `07_agent_orchestration.md:98 (O-4), 273, 385-390, 926-969` | Property test: seed turns Hypothesis-marked as PURPLE (via stub classifier); assert outgoing message metadata path. **Always-on**, never sampled out. |
| **INV-O-4** | `safety.level == RED ⇒ response.path == 'soul_flavored_rejection'` | FATAL | `07_agent_orchestration.md:383-384` | As INV-O-3 with RED stub. |
| **INV-O-5** | `safety.level ∈ {GREEN, YELLOW, ORANGE, RED, PURPLE}` (enum closed) | FATAL | `07_agent_orchestration.md:119, 448` | Trivial enum check, exhaustive. |
| **INV-O-6** | All LLM calls go through `ModelRouter.call(...)`, never via raw SDK | FATAL | `07_agent_orchestration.md:115` | Static check (grep + import-linter rule) + runtime decorator on SDK adapter that asserts caller stack contains `ModelRouter`. |
| **INV-O-7** | `∀ subsystem call S: S.deadline ≤ S.hard_timeout` | WARN | `07_agent_orchestration.md:126` | Wrap subsystem clients with assertion. |
| **INV-O-8** | Circuit breaker open ⇒ subsystem result.source ∈ {cache, default} (no live call) | FATAL | `07_agent_orchestration.md:134` | Force breaker open via Hypothesis-controlled failure injection; assert result metadata. |
| **INV-O-9** | `∀ event e: e.user_id is set ∧ all repo queries filter by user_id` | FATAL | `07_agent_orchestration.md:117 (INV-O-4)` | Cross-pair leak test, mirrors INV-R-8 at the orchestrator boundary. |

---

## 6. Coverage requirements

For each invariant the design **requires**:

1. **One catalog entry** (this document, must stay in sync).
2. **One registry entry** in `backend/heart/infra/invariants.py` with
   matching `id` slug.
3. **At least one Hypothesis property test** in `backend/tests/properties/`.
4. **At least one usage site** of the decorator on a production code path,
   if the invariant is checkable at runtime. (Some invariants — like INV-O-6
   "no raw SDK" — are purely static/architectural and won't have a runtime
   decorator site; the catalog marks these explicitly under
   `verification_kind: static`.)

A CI check (added in the implementation PR) will fail when any of these
four artifacts is missing for any ID listed here.

---

## 7. Implementation roadmap

Once this design is approved, the implementation lands in three PRs:

1. **PR 1 — registry + decorator + telemetry**
   - `backend/heart/infra/invariants.py` skeleton
   - decorator, sampling, env-mode switch
   - Prometheus metrics + structured log + Sentry hook
   - one canary invariant (INV-E-2 range check) wired end-to-end
   - unit tests for the framework itself

2. **PR 2 — property test scaffold + first 6 invariants**
   - `backend/tests/properties/` with strategies, conftest
   - INV-M-1, INV-M-3, INV-R-1, INV-R-4, INV-E-1, INV-O-3
   - new pytest marker `properties`, CI job (PR-required, fast settings)

3. **PR 3 — fill remaining invariants + CI completeness check**
   - all remaining IDs from this catalog
   - CI check that scans this doc, the registry, and the test files for
     ID parity; fails on drift
   - weekly deep-fuzz nightly cron with `max_examples=2000`

---

## 8. Open questions

- **Q1:** Do we want a way to **temporarily downgrade** a FATAL invariant to
  WARN during incident response? Proposal: yes, via env var
  `HEART_INVARIANT_DOWNGRADE=inv-r-6,inv-o-7`, audited in startup logs.
- **Q2:** For INV-R-9 (180-day trust ceiling), property testing is awkward
  at that timescale. Should this stay in the catalog as "verification_kind:
  integration-only", or move to an LTS scenario test? Default to the
  former — keep one catalog, mark the verification kind.
- **Q3:** Sampling at 1% in PROD — do we sample uniformly per-turn or
  weighted by user-cohort? Start uniform; revisit if we see hot users
  generating noisy violations.

---

## 9. References

- `runtime_specs/02_memory_runtime.md` §2.2, §3 (encoder/consolidator)
- `runtime_specs/03_emotion_state_machine.md` §2.2, §4 (inertia + VAD math)
- `runtime_specs/04_relationship_phase_engine.md` §2.2, §5 (stages, reunion, cold_war)
- `runtime_specs/06_inner_state_behavior_runtime.md` §2.2
- `runtime_specs/07_agent_orchestration.md` §2.2, §3.9 (PURPLE care path)
- `docs/design/integration_test_pyramid.md` — existing test-tier strategy this
  framework slots beneath.
