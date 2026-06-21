# SS02 Memory — L3 → L4 Promoter Rules

> **Status**: Design (not yet implemented)
> **Subsystem**: SS02 Memory
> **Invariant being formalized**: INV-M-15 — "L4 晋升必须满足多重条件，单一信号不晋升"
> **Spec parent**: `runtime_specs/02_memory_runtime.md` §4.2
> **Schema parent**: `backend/heart/ss02_memory/models.py` (`FactNode`, `IdentityMemory`, `MemoryAuditLog`)
> **Last updated**: 2026-06-19

## 0. Scope & terminology

| Term | Meaning |
|---|---|
| **L3 fact** | a row in `fact_nodes` with `is_active=True`, `promoted_to_l4_at IS NULL` |
| **L4 identity fact** | a row in `identity_memories` |
| **Promoter** | the worker that scans L3 candidates and writes L4 rows |
| **disclosure** | a single new write or reinforce against an L3 fact (one Resolver decision = one disclosure) |
| **session** | the conversation session that produced a disclosure (`memory_audit_log.session_id`) |
| **EWMA** | exponentially weighted moving average; the Writer maintains `confidence_ewma` per fact (`writer.py` `_handle_reinforce`) |

A fact is identified by `(user_id, character_id, predicate, subject)`. Object value variation is handled by SUPERSEDE — the Promoter only sees the **currently active** L3 row per identity.

The Promoter is **strictly additive on L4** and **strictly read-only on L3** except for two metadata fields (`is_identity_level`, `promoted_to_l4_at`, `promotion_reason`). It never deletes L3, never edits L3 content (M-1, M-14).

---

## 1. Promotion predicate

A fact `f` is promoted at run-time `t` **iff every clause holds**:

```text
ELIGIBLE(f, t) ≡
    (P1)  f.is_active = TRUE
  ∧ (P2)  f.promoted_to_l4_at IS NULL
  ∧ (P3)  f.is_corrected = FALSE
  ∧ (P4)  f.do_not_recall = FALSE
  ∧ (P5)  f.mention_count                ≥ K1   -- repetition
  ∧ (P6)  f.confidence_ewma              ≥ K2   -- model agreement
  ∧ (P7)  age_days(f, t)                 ≥ K3   -- temporal soak
  ∧ (P8)  cross_session_count(f)         ≥ K4   -- spanning sessions
  ∧ (P9)  contradiction_clear(f, t, K5)         -- no recent dispute
  ∧ (P10) f.predicate ∉ BLOCKLIST                -- §3
```

All clauses are AND-ed. **Single-signal escape hatches are explicitly forbidden** (no "sacred_signal=true alone promotes") — that is exactly the over-promotion failure mode that motivates INV-M-15.

### 1.1 Threshold defaults and justification

| Const | Default | Predicate guarded | Rationale |
|---|---|---|---|
| **K1** | `3` | mention_count ≥ K1 | Two mentions is "user said it twice" — common after a typo or re-confirmation in the same breath. Three forces the fact to survive one full conversational arc plus one re-entry. Choosing 3 (not 2) matches the Composer's existing "≥3 confirmations" rule for elevating fact prominence and keeps L4 promotion strictly stricter than fact prominence. |
| **K2** | `0.80` | confidence_ewma ≥ K2 | Writer initializes `confidence_ewma = candidate.confidence` and updates it on each REINFORCE. The Extractor refuses to emit candidates with `confidence < 0.70` (`memory_extractor_prompt.md` 严格规则), so 0.80 means the model has converged *above* its own emission floor — i.e., later reinforcements confirmed an already-confident initial extraction. 0.85 would over-reject legitimate facts the model is reasonably sure of; 0.75 would let through one-shot high-confidence extractions that never got cross-validated. |
| **K3** | `1 day` | age_days(f, t) ≥ K3 | Guards against single-session over-promotion. Within a single session, a user can re-state the same fact many times (driving `mention_count` up) without it being a genuinely stable belief. Requiring ≥1 day forces at least one consolidation cycle + one calendar day boundary between first disclosure and promotion. 1 day is the minimum that still preserves the "she remembers from the start" feel — anything longer (3d, 7d) makes the Companion seem cold on early days. |
| **K4** | `2` | cross_session_count(f) ≥ K4 | The most important predicate. Re-stating something inside the *same* session is cheap (the user is editing their own assertion in real time); re-stating across sessions is the signal that the fact is part of the user's stable self-model. Two distinct sessions is the minimum non-trivial count; three would be ideal for safety but pushes L4 onset to ~Day 3–4 of usage, which is too late for the "she remembers your name" experience. K4=2 + K3=1d + K1=3 jointly guarantee multi-session, multi-day, multi-mention — strictly stricter than any single condition. |
| **K5** | `7 days` | contradiction_clear(f, t, K5) | If a fact was contradicted, we require a full week of silence on it before treating the contradiction as stale. Shorter (1d, 3d) lets recent disputes promote during a calm-down window; longer (14d, 30d) lets stale disputes block promotion forever even after the user has moved on. 7d aligns with the demotion window in §2. |

All defaults live in `config/memory_promoter.yaml` (to be created); the Promoter reads them at startup. No magic numbers in code.

### 1.2 Computing each signal

| Signal | Source | Formula |
|---|---|---|
| `mention_count` | `fact_nodes.mention_count` | Writer maintains it: +1 per REINFORCE, =1 on CREATE/SUPERSEDE. |
| `confidence_ewma` | `fact_nodes.confidence_ewma` | Writer maintains it: initialized to `candidate.confidence`, updated by Resolver on REINFORCE. |
| `age_days(f, t)` | `fact_nodes.created_at` | `EXTRACT(EPOCH FROM (t - created_at)) / 86400`. Note: this is the age of the *current* row; if a fact was SUPERSEDED, its age resets — that's intentional (a freshly-superseded value should re-prove itself before going sacred). |
| `cross_session_count(f)` | `memory_audit_log` | `COUNT(DISTINCT session_id)` over audit rows where `entity_ref = f.id::text` and `actor IN ('extractor','resolver')` and `operation IN ('create','update')`. **Computed at query time**, not stored — keeps the predicate truth-aligned to the audit log of record. |
| `contradiction_clear(f, t, K5)` | `fact_nodes` | `f.last_contradicted_at IS NULL OR (t - f.last_contradicted_at) > INTERVAL 'K5 days'` |

### 1.3 SQL query shape

The Promoter runs **one cursor-based query per batch** to find candidates. It is a single SELECT joining `fact_nodes` with an audit-log subquery; no per-row Python loops over the DB.

```sql
WITH session_counts AS (
    SELECT
        entity_ref AS fact_id_str,
        COUNT(DISTINCT session_id) AS distinct_sessions
    FROM memory_audit_log
    WHERE tier = 'L3'
      AND actor IN ('extractor', 'resolver')
      AND operation IN ('create', 'update')
      AND created_at >= NOW() - INTERVAL '90 days'   -- bound the scan
    GROUP BY entity_ref
)
SELECT
    f.id,
    f.user_id,
    f.character_id,
    f.predicate,
    f.subject,
    f.object,
    f.confidence_ewma,
    f.mention_count,
    f.created_at,
    f.last_contradicted_at,
    sc.distinct_sessions
FROM fact_nodes f
JOIN session_counts sc ON sc.fact_id_str = f.id::text
WHERE f.is_active = TRUE
  AND f.promoted_to_l4_at IS NULL
  AND f.is_corrected      = FALSE
  AND f.do_not_recall     = FALSE
  AND f.mention_count    >= :K1
  AND f.confidence_ewma  >= :K2
  AND f.created_at       <= NOW() - INTERVAL ':K3 days'
  AND sc.distinct_sessions >= :K4
  AND (
        f.last_contradicted_at IS NULL
        OR f.last_contradicted_at <= NOW() - INTERVAL ':K5 days'
      )
  AND f.predicate NOT IN (:blocklist_predicates)
  AND f.predicate NOT LIKE ALL (:blocklist_patterns)   -- glob matches, §3
ORDER BY f.user_id, f.id
LIMIT :batch_size
FOR UPDATE SKIP LOCKED;                                -- §6
```

`FOR UPDATE SKIP LOCKED` lets multiple Promoter workers run concurrently without stepping on each other (each batch grabs a disjoint set of L3 rows).

---

## 2. Demotion predicate (L4 → L3)

L4 facts are sacred (INV-M-2), so demotion is rare and **only triggered by contradiction**, never by simple decay. Per the user's spec ("contradicted by ≥2 disclosures within 14 days"):

```text
DEMOTE(im, t) ≡
    (D1)  contradicting_disclosures_in_window(im, 14d) ≥ 2
  ∧ (D2)  ¬im.user_initiated_forget                       -- different path
  ∧ (D3)  ¬contradictions_are_self_correcting(im)         -- §2.1
```

When `DEMOTE(im) = TRUE`:

1. **L4 row is NOT deleted.** A new audit row is written with `operation='demote'`, `actor='promoter'`, `old_value=L4 snapshot`, `new_value={demoted_at, demoted_reason}`.
2. **L4 row gets `user_initiated_forget=FALSE` (unchanged) but a flag-only update**: set `audit_log.append({event:'demoted',...})` (the existing `audit_log JSONB` column on `identity_memories`).
3. **The L3 fact stays in `fact_nodes`** with `was_l4=True`, `previously_l4_id=<demoted L4 id>`, `promoted_to_l4_at=NULL` (cleared). This requires a tiny schema addition (see §2.2).
4. **The L4 row is hidden from Reconstructor reads** via a `WHERE demoted_at IS NULL` clause everywhere L4 is read — *not deleted, just shadowed*, so it remains in audit for forensics (M-1: "记忆内容永不物理删除").

### 2.1 What "contradicting disclosure" means

A disclosure contradicts an L4 fact `im` iff:

- A new L3 candidate has `predicate=im.predicate, subject=im.subject` but `object ≠ im.value`, **OR**
- The user explicitly negates (`is_corrected=TRUE` set on the matched L3 fact) within the window.

`contradictions_are_self_correcting(im)` — exclude the case where the *user themselves* immediately retracts the contradiction in the next turn (e.g., "no wait, I meant…"). This is detected by the Resolver tagging the disclosure `reasoning="self_correction"`. We trust the Resolver here — it's the cheapest correct place to make the call.

### 2.2 Required schema change (one column)

`fact_nodes` needs:

```python
was_l4: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
previously_l4_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID, nullable=True)
```

(Two columns; tiny migration. The "was_l4 flag" the user asked for is `was_l4`; `previously_l4_id` lets us trace back to the demoted L4 audit trail.)

`identity_memories` needs:

```python
demoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
demotion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

Reads of `identity_memories` from Reconstructor / Retriever / Composer must filter `WHERE demoted_at IS NULL` (one-line addition in each callsite).

### 2.3 Demotion SQL shape

```sql
-- run on each L4 row after a contradiction event hits
WITH contradiction_count AS (
    SELECT
        target.fact_id,
        COUNT(*) AS n
    FROM memory_audit_log al
    JOIN identity_memories im ON im.promoted_from_fact_id::text = al.entity_ref
    WHERE im.id = :l4_id
      AND al.created_at >= NOW() - INTERVAL '14 days'
      AND (
            (al.operation = 'create' AND al.new_value->>'predicate' = im.predicate
                                     AND al.new_value->>'subject'   = im.subject
                                     AND al.new_value->>'object'   != im.value)
         OR (al.operation = 'update' AND al.new_value->>'is_corrected' = 'true')
      )
      AND COALESCE(al.reasoning, '') != 'self_correction'
)
SELECT n FROM contradiction_count;
-- DEMOTE if n >= 2
```

---

## 3. Attribute blocklist

The blocklist names **predicates that must never promote**, regardless of how often they're confirmed. Each entry has an explicit reason. Two forms: exact predicate names and glob patterns.

### 3.1 Exact predicates (never promote)

| Predicate | Reason for blocking |
|---|---|
| `current_mood` | Transient by definition — promoting "user is sad" makes the Companion permanently treat the user as sad. |
| `current_emotion` | Same as above. |
| `current_location_temporary` | "I'm at the coffee shop" is not identity. Distinct from `home_city`, which *is* identity. |
| `currently_doing` | "I'm working right now" — a turn-scoped activity. |
| `today_plan` / `tomorrow_plan` | Plan facts decay naturally; promoting them to sacred makes them permanent. |
| `recent_purchase` | Shopping is not self. |
| `current_weather_in_location` | The user's report of weather where they are. Pure context. |
| `last_meal` / `recent_meal` | Eating is not identity. |
| `body_state_temporary` | "I'm tired" / "I have a headache" — these are passing states, not selfhood. |
| `wants_now` | "I want pizza right now" vs. `favorite_food` (which *can* promote). |
| `arguing_with` | Active relational state — "I'm fighting with my mom this week" should fade. Distinct from `relationship_with` which can promote. |

### 3.2 Glob patterns (never promote)

Patterns matched via SQL `LIKE` / `NOT LIKE ALL`. Captures families of transient predicates the Extractor may invent.

| Pattern | Reason |
|---|---|
| `current_*` | Anything starting with `current_` is by convention turn-scoped. |
| `today_*` / `tonight_*` / `this_week_*` | Calendar-bounded → not identity. |
| `temp_*` / `temporary_*` | Self-labeled transient. |
| `*_in_progress` | Activity in progress, not stable. |
| `feeling_*` | All feeling states are L2 territory (episodic), not L4. |
| `recent_*` | "Recent" is a recency claim, not a stable attribute. |

### 3.3 Predicates that *can* promote (whitelist for documentation, not enforcement)

For reviewer reference — promotion is gated by §1 predicates, not whitelist; this is *which kinds of facts* §1 was designed to let through:

- Identity: `has_name`, `birthday`, `age`, `gender`, `occupation`, `hometown`, `home_city`, `lives_with`
- Stable preferences: `favorite_food`, `favorite_color`, `loves`, `hates`, `afraid_of`, `allergic_to`
- Relationships: `relationship_with`, `has_pet`, `has_sibling`, `parent_status`
- Sacred disclosures: `core_trauma`, `core_loss`, `first_event_*`, `made_promise`

These are documented in `config/memory_promoter.yaml` but **the code path enforces only the blocklist**. Whitelist would couple Promoter to the Extractor's predicate vocabulary, which is owned by SS02 prompt evolution, not by the Promoter.

---

## 4. Scheduling

| Property | Value | Rationale |
|---|---|---|
| **Trigger** | Reuse the existing Consolidator nightly run (per-user local 03:00, `consolidation_jobs` table). Add `promotions_to_l4: UUID[]` output step at the end of the existing pipeline. | Already in the spec (`02_memory_runtime.md` §3.6 step 5: "L3 → L4 Promotion Check"). Don't add a second scheduler. |
| **Frequency** | Once per user per day. | INV-M-8 guarantees ≤1 consolidation/day, which inherits to Promoter. Aligns with K3 ≥ 1 day: there's no value in running promoter more often than the minimum age requirement. |
| **Out-of-band trigger** | None for promotion. **Demotion is event-driven**: it runs synchronously whenever the Resolver writes a contradictory disclosure (`memory_audit_log` insert with `operation='update'`, `new_value->>'is_corrected'='true'` and an existing L4 sibling). | Promotion is patient (low risk of waiting one more day). Demotion is urgent — leaving a contradicted L4 fact live for up to 24h means the Companion can confidently repeat a now-false sacred fact to the user, which is the worst failure mode. |
| **Batch size** | 200 candidate L3 rows per cursor cycle, with `FOR UPDATE SKIP LOCKED`. | Bounded memory; multi-worker safe. |
| **Per-user L4 cap** | 50 (matches §9.2 "数量 cap 50 个 L4 最多"). | Promoter refuses to insert if the user already has 50 active (non-demoted) L4 rows, even if the candidate is eligible. Logs `promotion_skipped_l4_cap_reached`. The cap exists to keep the Identity Layer prompt-block small and to prevent "everything is sacred → nothing is". |

---

## 5. Idempotency

A single fact must never produce two L4 rows. Three independent layers enforce this:

### 5.1 Database-level (hard guarantee)

`identity_memories` has `UNIQUE (user_id, character_id, key)` (already in `models.py:352`). A double-insert with the same derived `key` is rejected by Postgres with a uniqueness violation. The Promoter catches `UniqueViolation`, logs `promotion_duplicate_key`, and treats it as success (the L4 already exists).

### 5.2 L3-level marker (soft guarantee, fast)

After successful promotion the Promoter atomically writes:

```python
fact.is_identity_level     = True
fact.promoted_to_l4_at     = NOW()
fact.promotion_reason      = "<which predicates passed; threshold values used>"
```

`P2: f.promoted_to_l4_at IS NULL` in §1 then excludes the fact from the next batch. The L3 row never re-enters the candidate set.

### 5.3 Atomic transaction boundary

For each candidate the Promoter does:

```
BEGIN;
  -- 1. SELECT ... FOR UPDATE the L3 fact row (already locked by §1.3 SKIP LOCKED)
  -- 2. INSERT INTO identity_memories (...) RETURNING id;
  -- 3. UPDATE fact_nodes SET promoted_to_l4_at=NOW(), is_identity_level=TRUE,
  --                          promotion_reason=:reason WHERE id=:fact_id;
  -- 4. INSERT INTO memory_audit_log (
  --        tier='L4', operation='promote', actor='promoter',
  --        entity_ref=:l4_id::text, ...);
COMMIT;
```

All three writes commit or none. A crash between INSERT (step 2) and UPDATE (step 3) is recovered by §5.4.

### 5.4 Crash-recovery reconciliation (§6 detail)

On Promoter startup it runs a reconciliation query:

```sql
-- Find L4 rows whose L3 source isn't marked as promoted.
SELECT im.id, im.promoted_from_fact_id
FROM identity_memories im
JOIN fact_nodes f ON f.id = im.promoted_from_fact_id
WHERE im.demoted_at IS NULL
  AND f.promoted_to_l4_at IS NULL;
```

For each row found, UPDATE the L3 fact to set `promoted_to_l4_at = im.created_at, is_identity_level = TRUE`. This closes the §6.1 partial-commit window.

---

## 6. Failure modes

### 6.1 Mid-batch crash

**Symptom**: Promoter crashes between INSERT into `identity_memories` and UPDATE on `fact_nodes` (no transaction wrapper bug) **OR** Postgres goes down mid-transaction.

**Recovery**: On next startup, §5.4 reconciliation closes the gap. The transaction boundary in §5.3 makes within-Postgres crashes safe by default; reconciliation handles the scenarios where the worker died after COMMIT but before logging.

**Test**: §7 scenario T-6.

### 6.2 Duplicate promotion under concurrent workers

**Symptom**: Two Promoter pods process the same user simultaneously, both pick the same L3 fact.

**Mitigation**: `FOR UPDATE SKIP LOCKED` on the candidate query (§1.3) means at most one pod holds the row. The other pod's query returns a smaller batch. Worst case (no row lock, e.g., misconfig): the unique constraint on `identity_memories(user_id, character_id, key)` rejects the duplicate insert. Both paths converge on "exactly one L4 row".

### 6.3 Audit-log write fails but L4 write succeeds

**Symptom**: Step 4 of §5.3 fails (e.g., disk full on append-only table).

**Mitigation**: All four writes are in one transaction; step 4 failing aborts the whole transaction. L4 row is never created without its audit row.

### 6.4 Predicate not in blocklist but should be

**Symptom**: A new Extractor prompt version starts emitting `current_mood_extended` (not in blocklist). It promotes incorrectly.

**Mitigation**:
- Glob pattern `current_*` in §3.2 catches this — that's why globs exist.
- New predicate categories the globs miss → caught by review: a metric `promoter.promoted.predicate_distribution` is exposed; a sudden spike in a new predicate name triggers an alert. The blocklist is then updated in `config/memory_promoter.yaml` and the offending L4 row is demoted via an admin-tooling path (out of scope here).

### 6.5 `cross_session_count` over-counts because of session_id reuse

**Symptom**: A buggy upstream reuses a `session_id` across two real user sessions, inflating the count.

**Mitigation**: Defense in depth — K3 ≥ 1 day forces calendar-time spread regardless of session_id correctness. Also: the auth/session layer guarantees `session_id` is a fresh UUID per login (`backend/heart/api/...`); reuse would be a bug there, not here.

### 6.6 Promoter never runs (scheduler dead)

**Symptom**: Consolidator daemon dies; promotions stop.

**Mitigation**: Out of scope for this design; addressed by SS08 (Consolidator runs under a supervised service with Prometheus alert on `memory.consolidation.last_run_seconds_ago > 86400`). The Promoter itself has no separate watchdog — it's a step in Consolidator.

### 6.7 Promoter promotes during a contradiction race

**Symptom**: Promoter selects fact `f`, then before COMMIT, Resolver writes a contradiction.

**Mitigation**: `SELECT ... FOR UPDATE` on `f` blocks the Resolver's UPDATE until promotion commits or aborts. After promotion, the L4 row exists; the contradiction then flows through the demotion path (§2). This is the *correct* sequence — a brief moment of L4-then-demote is auditable and recoverable, whereas a never-promoted L4 because of a race window is silent loss.

---

## 7. Test scenarios

Tests live in `backend/tests/unit/ss02_memory/test_promoter.py` (to be created) and `backend/tests/integration/test_promoter_pipeline.py`. Each scenario seeds the DB, runs Promoter, asserts L4/L3/audit state.

### T-1 — Happy path: all conditions met

**Setup**: Seed L3 `has_pet/user/老铁的猫` with `mention_count=4, confidence_ewma=0.88, created_at=now-2d`, with audit rows from 3 distinct session_ids spread across 2 days, no `last_contradicted_at`, predicate not in blocklist.

**Assert**: After Promoter run, exactly one new `identity_memories` row exists with `promoted_from_fact_id=f.id`; `f.is_identity_level=True`; `f.promoted_to_l4_at IS NOT NULL`; an audit row with `tier='L4', operation='promote', actor='promoter'`.

### T-2 — Reject: mention_count just below threshold

**Setup**: Same as T-1 but `mention_count=2` (with K1=3).

**Assert**: No L4 row created. `f` unchanged. No new audit rows for `f`. The query in §1.3 returns zero candidates.

### T-3 — Reject: single-session over-mention

**Setup**: `mention_count=10, confidence_ewma=0.95, created_at=now-2d`, but **all 10 mentions in 1 session_id**.

**Assert**: No L4 row created. This is the exact INV-M-15 failure mode: a user re-asserting a fact ten times in one venting session should not produce an L4 row. The K4 ≥ 2 distinct sessions clause must block this.

### T-4 — Reject: too young

**Setup**: `mention_count=5, confidence_ewma=0.90, distinct_sessions=3, created_at=now-12h` (with K3=1d).

**Assert**: No L4 row. After 24h passes and the fact is unchanged, a re-run promotes it.

### T-5 — Reject: contradicted within K5 window

**Setup**: All other conditions met; `last_contradicted_at=now-3d` (with K5=7d).

**Assert**: No L4 row. After K5+1 more days with no further contradiction, re-run promotes.

### T-6 — Crash recovery: L4 written, L3 marker missing

**Setup**: Insert an `identity_memories` row whose `promoted_from_fact_id` points to an L3 fact with `promoted_to_l4_at IS NULL` (simulates a crash between §5.3 step 2 and step 3).

**Assert**: Run Promoter startup reconciliation (§5.4). The L3 fact is updated to `promoted_to_l4_at = im.created_at, is_identity_level=TRUE`. No duplicate L4 row is created on the same fact in a subsequent normal batch run.

### T-7 — Demotion: two contradictory disclosures within 14 days

**Setup**: A live L4 row `key=has_pet, value="老铁的猫"`. Within 14 days, write two L3 audit rows with operation='create', `new_value.object="一只狗"` (distinct sessions, not flagged self-correction).

**Assert**: Demoter runs (event-driven via the second contradiction). `identity_memories.demoted_at IS NOT NULL`, `demotion_reason` populated. The originally-promoted L3 fact has `was_l4=TRUE`, `previously_l4_id=<demoted L4 id>`, `promoted_to_l4_at=NULL`, but the row itself remains in `fact_nodes`. Reconstructor reads exclude the demoted L4 row.

### T-8 — Blocklist: transient mood never promotes

**Setup**: L3 fact `predicate=current_mood, mention_count=20, confidence_ewma=1.0, distinct_sessions=15, age=30d`. Every numeric threshold blown out.

**Assert**: No L4 row. The `predicate NOT IN (blocklist)` clause in §1.3 short-circuits. Audit log shows `promoter.skipped.blocklist` counter incremented but no fact-specific audit row (we don't log per-skip to avoid log spam).

### T-9 — Blocklist glob: `current_*` pattern

**Setup**: L3 fact `predicate=current_location_in_city`. Conditions otherwise met.

**Assert**: No L4 row. The `NOT LIKE ALL (:blocklist_patterns)` clause catches `current_*`.

### T-10 — Idempotency: re-running Promoter on same data is a no-op

**Setup**: T-1, then run Promoter, then **run Promoter again** without any new disclosures.

**Assert**: Exactly one L4 row in total. Second run logs `promoter.batch.candidates=0`. No new audit rows. (Confirms P2: `f.promoted_to_l4_at IS NULL` excludes already-promoted facts.)

### T-11 — Per-user L4 cap

**Setup**: User has 50 active (non-demoted) L4 rows. A 51st L3 candidate is fully eligible.

**Assert**: No L4 row inserted. Metric `promoter.skipped.l4_cap_reached` incremented; structured log entry includes `user_id` and the skipped `fact_id` so HUMAN can review whether to demote a less-important existing L4 instead.

### T-12 — Concurrent workers: no duplicate

**Setup**: Spawn two Promoter workers against the same eligible L3 fact (use `psycopg` directly to race the SELECT FOR UPDATE).

**Assert**: Exactly one L4 row. The losing worker either sees the row already locked (`SKIP LOCKED` → empty batch) or hits `UniqueViolation` on the L4 insert and logs `promotion_duplicate_key` without failing the batch.

---

## Open questions for review

1. **K3 = 1 day** is the minimum that preserves the "she remembers from the start" UX. Is there appetite for a per-predicate K3 (e.g., `has_name` promotes faster than `core_trauma`)? Current design says no — keep one K3 to keep the promoter simple. Revisit only if user testing shows L4 onset feels wrong.
2. **Blocklist owner**: kept in `config/memory_promoter.yaml`, owned by SS02 maintainers. Updates do not require code deploy; the Promoter reloads at startup. Should a hot-reload signal be added? Defer until we've operated the system for ≥1 quarter.
3. **Demotion ≥ 2 within 14 days** is conservative. Should a single high-confidence contradiction (e.g., user explicitly says "I lied about that, sorry") trigger immediate demotion? Yes — but route it through the existing `user_request_forget` path in `MemoryService`, not through Promoter. Promoter handles statistical demotion only.

---

## Approval

| Date | Reviewer | Role | Version reviewed | Notes |
|---|---|---|---|---|
| 2026-06-20 | HUMAN | Project Lead | 1.0.0 | approved as-is |
