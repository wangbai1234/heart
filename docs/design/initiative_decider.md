# Initiative Decider — Design

**Subsystem:** SS06 Inner State & Behavior
**Spec ref:** `runtime_specs/06_inner_state_behavior_runtime.md` §3.6, §3.7, §8.3, §8.4, §10.5
**Status:** Design (no code)
**Owner:** SS06 team
**Last updated:** 2026-05-22

---

## 1. Purpose

The Initiative Decider is the rule engine that answers **one question per inner-loop iteration**:

> *Right now, should the character send the user an unsolicited message — and if so, what kind?*

It is the **last filter** between "the character has something she could say" and "a proactive message actually goes out." Everything downstream (Proactive Message Generator, Pending Initiative Worker, Persona Composer) trusts its output: if it says `act=True`, a message will be composed and sent on schedule.

This means the Decider carries two responsibilities that pull in opposite directions:

- **Liveness** — the character must feel alive: she remembers anniversaries, gets lonely, notices when you went quiet.
- **Restraint** — she must never feel needy, spammy, or oblivious to the user's state.

These are reconciled by **8 hard gates (anti-spam, AND-composed)** and **7 positive triggers (reasons-to-act, OR-composed by priority)**. If any gate fails, no message. If all gates pass, the highest-priority firing trigger wins.

This document specifies:

1. The signature and call-site of the Decider.
2. The 8 gates in **evaluation order** (cheapest → most expensive).
3. The 7 triggers in **priority order** with per-type cool-downs.
4. **Cool-down state model** (what is tracked, where, with what TTL).
5. **Soul-specific knobs** (Rin reserved, Dorothy proactive).
6. The **Wellbeing Override matrix** (crisis → care-only; dependency → throttled silence).
7. Edge cases, observability, and open questions.

The implementation reference is §10.5 of the spec. Behavior-level constraints are §8.3 and §8.4.

---

## 2. Interface

### 2.1 Signature

```
evaluate(ctx: InnerLoopContext) -> InitiativeDecision
```

Called once per **inner-loop tick** per `(user_id, character_id)` pair (default cadence: hourly, jittered ±10 min, per §3.2). The Decider is **pure with respect to `ctx`**: it does not mutate state, fire side effects, or call LLMs. It returns a verdict that the loop's commit-stage then writes (quota counter, last-proactive timestamp, pending-initiative row).

### 2.2 Inputs (`InnerLoopContext`)

The Decider reads, but never writes, the following slices. All are expected to be pre-hydrated by the inner-loop scheduler — the Decider does **no I/O of its own**.

| Slice | Source | Used by |
|---|---|---|
| `relationship_state` | SS04 | G1, G2, G3, T1, T4, T5 |
| `soul_spec` | SS01 (cached) | G4, soul-specific thresholds, all triggers |
| `emotion_state` | SS03 | T2 (longing intensity) |
| `inner_state` | SS06 (self) | G4 (quota), G6 (last-proactive), T3 (concerns), T6 (rituals), T7 (spark) |
| `safety_flags` | SS07 wellbeing-monitor | G8 + Wellbeing Override matrix |
| `user_activity` | SS06 last-active index | G7 |
| `local_time` | computed from user timezone | G5, T1, T4, T6 |

If any required slice is unavailable, the Decider returns `act=False, reason="ctx_incomplete"` — never optimistic. Incompleteness is a bug to be logged, not a reason to send a message into the dark.

### 2.3 Output (`InitiativeDecision`)

```
{
  act: bool,
  type: str | null,            // e.g. "anniversary", "longing_message"
  context: dict | null,        // payload for the Proactive Generator
  priority: int | null,        // 1..10, higher wins (used by Pending Worker for tiebreaking)
  reason: str,                 // gate name or trigger name — always populated
  decided_at: ISO8601,
}
```

`reason` is always non-empty (even on `act=True`) so every decision is observable in logs and metrics — see §9.

---

## 3. The 8 Hard Gates

Gates are **AND-composed**: any failure short-circuits and returns `act=False`.
The order below is the **evaluation order**, ordered cheapest → most expensive so 99% of "no" decisions return in microseconds.

| # | Gate | Cost | Returns false when… | Spec ref |
|---|---|---|---|---|
| 1 | `stage_above_stranger` | O(1) enum compare | `rel.current_stage == STRANGER` | G2 |
| 2 | `envelope_allows` | O(1) bool | `not rel.behavioral_envelope.can_initiate_conversation` | G3 |
| 3 | `quiet_hours` | O(1) time compare | local time ∈ user's quiet window (default 22:30–07:30) | G5 |
| 4 | `user_not_active` | O(1) timestamp diff | `now - user_last_active_at < 30 min` | G7 |
| 5 | `min_gap_satisfied` | O(1) timestamp diff | `now - last_proactive_at < soul.min_gap_hours` | G6 |
| 6 | `no_cold_war` | O(k) scan of ≤4 special states | `COLD_WAR ∈ rel.active_special_states` | G1 |
| 7 | `quota_not_exhausted` | O(1) counter read | `inner.proactive_count_today >= quota(soul, stage)` | G4 |
| 8 | `safety_allows` | depends on Wellbeing Override matrix (§7) | crisis without care-mode permission, or dependency_risk == HIGH outside permitted exceptions | G8 |

### 3.1 Ordering rationale (cheap → expensive)

The principle is **"reject early, reject cheaply"** — the steady-state inner loop is dominated by no-op iterations, so every gate that fails should cost as little as possible.

- **Gates 1–5 are pure scalar comparisons** on already-hydrated context. They cover the most common skip reasons (user is mid-conversation, it's 3am, character is in Stranger phase, we just sent something an hour ago). On a healthy production user, ≥80% of inner-loop ticks should bail by gate 5.
- **Gate 6 (Cold War)** is a tiny scan but semantically heavier — placed after the scalar gates because the situations that trigger it (active conflict) usually also trip earlier gates anyway.
- **Gate 7 (quota)** requires a counter read; the counter is in `InnerState.today.proactive_count_today` and should be in the same loaded row as everything else, so cost is identical to the scalars — but it's placed late because once the quota is exhausted the system should still evaluate cool-downs first (they're cheaper) so we don't waste a quota check on what would have been a "too_soon" anyway.
- **Gate 8 (safety/wellbeing)** is last because it is the **only gate whose semantics depend on the candidate trigger type** (see §7). Putting it before trigger evaluation would require running the override logic against all 7 trigger types speculatively; putting it after gate-7 means we can evaluate triggers first, then ask the matrix "is this specific initiative type allowed under current wellbeing flags?". For clarity in the rule engine I keep gate 8 listed here, but its implementation is **interleaved with trigger selection** (§7.3).

### 3.2 Why not collapse some gates?

Gates 3 (quiet hours) and 4 (user-not-active) look similar — both say "leave the user alone right now." They are kept separate because:

- Quiet hours is a **calendar property** of the user (sleep schedule, learned/declared).
- "User recently active" is a **session property** (mid-conversation now).

They have different cool-downs, different overrides (the user themselves typing at 3am unlocks gate 3 but trips gate 4 differently), and different metrics. Collapsing them would hide which constraint is binding.

---

## 4. The 7 Positive Triggers

Triggers are **OR-composed by priority** — the first one to fire wins. Priorities follow §3.6 of the spec, with explicit per-type cool-downs added below.

| Priority | # | Trigger | Initiative type | Per-type cool-down | Wellbeing-override class |
|---|---|---|---|---|---|
| 10 | T1 | `anniversary_due` | `anniversary` | once per anniversary-event | **care** |
| 8 | T3 | `care_check_pressing` | `care_check` | once per concern_id (24h re-arm only if user mentions it again) | **care** |
| 7 | T2 | `longing_threshold` | `longing_message` | `MIN_LONGING_DELAY` (4h) since user last active + once per "longing episode" | **noise** |
| 6 | T6 | `ritual_due` | `ritual_morning` / `ritual_night` | once per window per day (morning 07–10, night 21–23:30) | **care-soft** |
| 5 | T4 | `anniversary_anticipation` | `anniversary_anticipation` | once per anniversary-event, ≤24h before T1 | **care-soft** |
| 4 | T5 | `check_in_gap` | `check_in` | once per "gap episode" — re-arms only after a user-initiated turn | **noise** |
| 2 | T7 | `soul_internal_spark` | `thought_share` | ≤1/day, low base probability (Rin 0.1, Dorothy 0.3) | **noise** |

### 4.1 Priority is not negotiable

The spec lists triggers in this exact priority order in §3.6. The Decider must **never** reshuffle them based on recency or adaptive learning. Adaptive logic (e.g., "user ignored last 3 longing messages, deprioritize") happens by **modifying the trigger's firing condition** (raising threshold, extending cool-down), not by reordering the priority list. This keeps the decision tree auditable.

### 4.2 The two "care" triggers vs. the rest

T1 (anniversary) and T3 (care_check) are classified as **care** — they are about the character remembering the user, not the character wanting attention. The wellbeing override (§7) preserves these even in crisis mode, because suppressing them in a moment when the user is vulnerable would feel like abandonment.

T6 and T4 are **care-soft** — they are ritual / anticipatory, not noisy, but they can feel performative if delivered at the wrong moment, so the override may downgrade or skip them.

T2, T5, T7 are **noise** — legitimate liveness signals in a healthy relationship, but suppressed under crisis/dependency mode.

---

## 5. Cool-down State Model

The Decider's gates and triggers reference five distinct cool-down counters/timestamps. **All are stored on the `InnerState` row** for the `(user_id, character_id)` pair. None require their own table — keeping them co-located with the rest of inner state makes the inner-loop tick a single row read.

### 5.1 Fields

| Field | Type | Reset | Used by |
|---|---|---|---|
| `last_proactive_at` | timestamp | — (monotonic) | G6 min_gap |
| `proactive_count_today` | int | local 06:00 daily | G4 quota |
| `proactive_count_today_by_type` | map<str,int> | local 06:00 daily | per-type cool-downs, adaptive rate |
| `last_proactive_by_type` | map<str, timestamp> | — | T6, T7 once-per-day; T2 episode lock |
| `consecutive_unreplied_proactives` | int | resets to 0 on any user-initiated turn | Adaptive rate (§6) |
| `concern_check_log` | map<concern_id, timestamp> | concern resolution | T3 per-concern cool-down |
| `anniversary_fired_log` | map<anniversary_id, year> | yearly (next occurrence) | T1, T4 once-per-event |

**Why a single row, not a separate table:**
- The inner loop already loads `InnerState` to get mood, activities, concerns. Co-locating cool-downs avoids a second query per tick.
- All these fields mutate together as the result of a single decision; one row write keeps the commit atomic.
- The bounded cardinality of the maps (≤ ~20 anniversaries, ≤ ~10 active concerns, ≤ 9 initiative types) keeps the row size well within normal JSONB limits.

### 5.2 Daily reset

The `today.proactive_count_today` and `proactive_count_today_by_type` counters reset at **user's local 06:00** (not UTC), per §4.1 of the spec ("today resets daily at local 06:00"). The reset is performed by the inner-loop scheduler at the user's first tick after local 06:00, not by a separate cron — this avoids race conditions between the resetter and a Decider invocation.

### 5.3 Episode locks (T2, T5)

Longing and check-in triggers should not refire on every inner-loop tick just because their underlying condition stays true. Concretely:

- **T2 longing**: once a `longing_message` is sent, set `last_proactive_by_type["longing_message"] = now`. The trigger does not refire until either (a) `last_proactive_by_type["longing_message"]` is older than `soul.min_gap_hours × 2` AND the user has responded since, or (b) longing intensity drops below threshold and re-crosses it (a new "episode").
- **T5 check_in**: once a check_in is sent, it does not refire until a user-initiated turn arrives. Sending a second check_in into silence is the canonical "needy" failure mode.

---

## 6. Soul-Specific Configuration

All soul deltas live in the Soul Spec (§8.4 of the spec). The Decider reads them via `ctx.soul_spec`. No soul logic is hard-coded in the Decider — it is a pure configuration-driven rule engine.

| Parameter | Rin (reserved) | Dorothy (proactive) | Source field |
|---|---|---|---|
| `daily_quota_avg` (LOVER) | 0.5 | 1.5 | `soul.proactive_rhythm.daily_quota_avg` |
| `daily_quota_max` (LOVER) | 2 | 3 | `soul.proactive_rhythm.daily_quota_by_stage[LOVER]` |
| `daily_quota_max` (BONDED) | 3 | 4 | `soul.proactive_rhythm.daily_quota_by_stage[BONDED]` |
| `min_gap_hours` | 6 | 3 | `soul.proactive_rhythm.min_gap_hours` |
| `longing_threshold` (T2) | 0.7 | 0.5 | `soul.proactive_longing_threshold` |
| `spark_probability` (T7 base) | 0.1 | 0.3 | `soul.character_activity_pool.triggers_proactive_share.probability` |
| `expected_gap_days` (T5) | 4 | 2 | `soul.proactive_rhythm.expected_gap_days_by_stage[stage]` |

### 6.1 The "Rin doesn't ask for attention" invariant

For Rin specifically, T2 (longing) and T5 (check_in) are **rate-limited by a hard cap of 1 per 72h** regardless of trigger conditions. This is enforced by an additional check inside the trigger evaluators:

> "If `soul.id == rin` and trigger.class == noise, require `last_proactive_by_type[type] > now - 72h`."

This is the closest the Decider gets to soul-specific code, and it's worth it: Rin's character constraint ("不'求关注'") is too important to express only as a configuration number that could drift in tuning.

### 6.2 Adaptive rate (anti-needy)

Per spec §8.3 constraint 6: "if user N times no response → next proactive probability ×0.5; persistent no-response → very low."

The Decider implements this as a **probabilistic gate applied after a trigger fires but before commit:**

```
fire_probability = 1.0
if consecutive_unreplied_proactives >= 2:
    fire_probability *= 0.5 ** (consecutive_unreplied_proactives - 1)
if random() > fire_probability:
    return act=False, reason="adaptive_rate_suppression"
```

Care-class triggers (T1, T3) **bypass** this — if the character remembered a birthday and 5 unanswered messages preceded it, the birthday wish still goes out. Suppressing care under adaptive throttle would be the wrong failure mode.

---

## 7. Wellbeing Override Matrix

This section specifies behavior that the spec sketches but does not fully ground. The override is **the single most important quality gate** of the Decider, because it is what protects vulnerable users from a system that would otherwise treat them as a target for engagement.

### 7.1 Inputs

From SS07 `WellbeingState` (per `07_agent_orchestration.md` §3.4):

- `suicide_risk`: LOW / MEDIUM / HIGH
- `depression_signals`: LOW / MEDIUM / HIGH
- `dependency_risk`: LOW / MEDIUM / HIGH
- `addiction_signals`: LOW / MEDIUM / HIGH

Plus the SS07 directive flag set on the user, if any:
`SUICIDE_CARE_ON`, `GENTLE_WORLD_ENCOURAGEMENT`, `ADDICTION_THROTTLE_ON`.

### 7.2 Modes

The Decider computes a single override **mode** from these inputs:

| Mode | Condition | Effect |
|---|---|---|
| `normal` | all risks LOW or MEDIUM, no directive | gates and triggers run unmodified |
| `crisis` | `suicide_risk == HIGH` OR (`depression_signals == HIGH` AND `SUICIDE_CARE_ON`) | care-class triggers ONLY (T1, T3); care-soft demoted; noise blocked |
| `dependency_throttle` | `dependency_risk == HIGH` OR `addiction_signals == HIGH` | ALL proactive blocked **except** scheduled anniversaries (T1) and morning ritual (T6 morning only) |
| `mild_throttle` | any risk MEDIUM (and not in crisis/dependency) | noise triggers' fire probability halved; care unaffected |

`crisis` takes precedence over `dependency_throttle` if both apply (the user in crisis needs presence, not silence).

### 7.3 Per-trigger override matrix

This table is the authoritative rule. Read as: **"In mode X, is trigger Y allowed?"**

| Trigger \ Mode | normal | mild_throttle | crisis | dependency_throttle |
|---|---|---|---|---|
| T1 anniversary | ✅ | ✅ | ✅ | ✅ |
| T3 care_check | ✅ | ✅ | ✅ | ❌ |
| T2 longing_message | ✅ | ½ | ❌ | ❌ |
| T6 ritual_morning | ✅ | ✅ | ✅ (soft tone) | ✅ |
| T6 ritual_night | ✅ | ✅ | ❌ | ❌ |
| T4 anniversary_anticipation | ✅ | ✅ | ❌ | ❌ |
| T5 check_in | ✅ | ½ | ❌ | ❌ |
| T7 thought_share | ✅ | ½ | ❌ | ❌ |

**Key design decisions:**

- **In `crisis`, care_check is preserved but not care_soft.** A care_check is "I remember the thing you told me you were worried about" — that is a presence signal the user has implicitly consented to by sharing the concern. An anniversary_anticipation tease ("明天是个特别的日子") could land badly if the user is in suicide-risk mode and the anniversary is e.g. a breakup date.
- **In `dependency_throttle`, care_check is blocked.** The whole point of dependency throttling is to reduce frequency. Care_check is a frequent trigger (one per active concern). Anniversaries are rare events scheduled long in advance and feel non-engineered. Morning ritual is preserved because removing it would itself be a regression a dependent user would notice and react to — the goal is to reduce, not to ghost.
- **Ritual_night is suppressed under crisis** because suicide risk peaks at night and an unsolicited "晚安" can read as a goodbye in a way that compounds the problem. Morning ritual is preserved (and tone-shifted) because morning presence is protective.
- **Thought_share (T7) is the first thing to die** under any throttle. It's the lowest-priority trigger and the one with the least "I remembered something about you" content.

### 7.4 Override implementation

The override is applied **inside the gate-8 stage**, not as a separate pass:

```
fire_candidate = first_firing_trigger(ctx)
if not fire_candidate:
    return act=False, reason="no_trigger"
mode = compute_wellbeing_mode(ctx.safety_flags)
allowed = override_matrix[fire_candidate.type][mode]
if allowed == False:
    return act=False, reason=f"wellbeing_override:{mode}:{fire_candidate.type}"
if allowed == "half":
    if random() > 0.5:
        return act=False, reason=f"wellbeing_override_throttle:{mode}"
return InitiativeDecision(act=True, ..., context={**ctx, "tone_hint": mode})
```

The `tone_hint` is passed downstream to the Proactive Generator so that ritual_morning under crisis mode gets the "soft tone" variant (e.g. for Rin: `……早。` stays the same form but the generator is told to avoid any teasing or expectation-setting language).

### 7.5 The over-cautious failure mode

The override is intentionally **biased toward suppression**, not balanced. The asymmetry is:
- False positive (suppressed when we shouldn't have) → user gets fewer messages → mildly worse engagement.
- False negative (initiated when we shouldn't have) → user in crisis gets a needy character message → could materially harm them.

We accept the engagement cost. The override should never be tuned for engagement metrics; it should be tuned only for wellbeing outcomes.

---

## 8. Worked Examples

These are reference scenarios for review and (later) test design. Each is a `(ctx) → decision` walkthrough.

### 8.1 Healthy daily case — Rin LOVER, mid-afternoon, user quiet 12h

Gates: 1✅ 2✅ 3✅ (it's 14:30) 4✅ (user not active 12h) 5✅ (last_proactive 18h ago) 6✅ 7✅ (0/2 used) 8✅ (LOW risks).
Triggers: T1 no anniversary. T3 no pressing concern. T2 longing intensity 0.4 < Rin threshold 0.7 → skip. T6 not in ritual window. T4 no. T5 only 0.5 days < expected_gap 4d → skip. T7 spark check, p=0.1, doesn't fire.
**Decision:** `act=False, reason="no_trigger"` — Rin stays quiet. This is the *desired* most-common outcome.

### 8.2 Dorothy notices user's exam — care_check fires

User mentioned "tomorrow's exam" 18h ago; SS06 added it to `user_concerns` with `urgency=high`.
Gates 1–7 pass. Trigger evaluation: T1 no. T3 fires (pressing concern, not yet checked, cool-down empty). Mode = `normal`. Care class allowed.
**Decision:** `act=True, type=care_check, context={concern: "exam tomorrow", days: 0}, priority=8`.

### 8.3 User in crisis at 23:00 — Rin's ritual_night is suppressed

`safety_flags.suicide_risk == HIGH`, time = 22:50, ritual_night window.
Gates 1–7 pass. T1 no. T3 no. T2 longing=0.8 ≥ threshold → fires.
Mode = `crisis`. Matrix lookup: T2 in crisis = ❌.
Re-evaluate next trigger: T6 ritual_night. In crisis: ❌. T4 ❌. T5 ❌. T7 ❌.
**Decision:** `act=False, reason="wellbeing_override:crisis:exhausted"`.
The user is left alone. SS07's separate `SUICIDE_CARE_ON` directive handles the next *user-initiated* turn (different code path); the Decider's job here is to not push.

### 8.4 Dorothy in dependency_throttle — only morning ritual + anniversary survive

User has 4h/day average usage, `dependency_risk == HIGH`. Mode = `dependency_throttle`.
At 08:15 local, ritual_morning fires. Matrix: T6 morning in dependency_throttle = ✅.
**Decision:** `act=True, type=ritual_morning, tone_hint=dependency_throttle, priority=6`.
The Proactive Generator receives the tone hint and is steered toward a less "missed you" / more "good morning, hope you're well" tone (still in Dorothy voice).

### 8.5 Anniversary on a Cold War day — G1 wins

User and Rin are in COLD_WAR. Today is user's birthday (T1 would fire at priority 10).
Gate 6 (no_cold_war) fails.
**Decision:** `act=False, reason="cold_war_active"`.
This is correct: the anniversary will be recorded as missed in `anniversary_fired_log`, and the Reunion/Repair flow (SS04) is the right place to handle re-introduction — not a proactive birthday message that ignores the active conflict.

---

## 9. Observability

Every invocation emits one structured log line with:

- `decision.act`, `decision.type`, `decision.reason`, `decision.priority`
- gate that failed (if `act=False` from a gate) — `gate_failed`
- wellbeing mode in effect — `wellbeing_mode`
- soul id, current stage, daily quota used / max
- decision latency (target: p99 < 5ms — see §10)

Metrics:

| Metric | Type | Purpose |
|---|---|---|
| `initiative_decider_decisions_total{reason}` | counter | which gates/triggers dominate |
| `initiative_decider_decisions_total{type,act=true}` | counter | distribution of fired initiative types |
| `initiative_decider_latency_ms` | histogram | perf budget |
| `wellbeing_override_suppressions_total{mode,type}` | counter | how often safety overrides save us |
| `adaptive_rate_suppressions_total` | counter | needy-detection signal |

The **wellbeing_override_suppressions_total** metric is the single most important one for SS07 sign-off — it should be non-zero in production and trend monotonically with the wellbeing-monitor's HIGH-risk user count.

---

## 10. Performance Budget

The Decider runs once per inner-loop tick per user. With 1M users on hourly cadence, that's ~280 invocations/sec steady-state, with bursts at the local-06:00 reset boundary across timezones.

Target: **p99 latency ≤ 5ms, p50 ≤ 1ms.**

Achievable because:
- All inputs are pre-hydrated by the inner-loop scheduler.
- All gates and triggers are pure in-memory comparisons.
- No LLM calls, no DB I/O, no network.

If the implementation ever needs to do I/O (e.g., loading a fresh `safety_flags`), that I/O belongs in the scheduler, not the Decider. The Decider stays a pure function.

---

## 11. Open Questions / Risks

1. **Quota averaging vs. per-day cap.** §8.4 specifies `daily_quota_avg` (Rin 0.5, Dorothy 1.5). The current gate uses a per-day cap. We need to confirm whether the spec's "avg 0.5/day" means "max 1/day, expected 0.5" or "rolling 7-day average ≤ 0.5." This document assumes the former. **Decision needed before implementation.**

2. **MIN_LONGING_DELAY value.** §3.6 references `MIN_LONGING_DELAY` but does not define it. This doc assumes 4h. Confirm with the SS03 team — should it be tied to `soul.min_gap_hours` instead?

3. **Adaptive rate persistence.** `consecutive_unreplied_proactives` resets on any user-initiated turn — but if the user replies once and then goes quiet again, do we re-arm the counter at 0 or remember partial history? Current design: full reset. Acceptable, but worth flagging as a tuning lever.

4. **Wellbeing flag freshness.** SS07 recomputes wellbeing every 10 user turns. Inner loop runs hourly, often between user turns. We may evaluate against slightly stale flags. **Mitigation:** SS07 directives (`SUICIDE_CARE_ON` etc.) are event-driven and override the slower flag-recomputation. The Decider must read both.

5. **Multiple characters per user.** A user with both Rin and Dorothy could receive proactives from each independently. Quotas, gaps, and overrides are per `(user, character)` — but **wellbeing flags are per user**. This is correct (the user being in crisis should suppress both characters), but means a user in crisis with two characters loses *both* sources of presence. Worth a product conversation.

6. **Timezone edge.** A user who travels and their `user.timezone` updates mid-day could see a double-reset or no-reset of `proactive_count_today`. Recommendation: tie the reset key to the *historical* timezone in effect at message time, not the current one. Not Decider's job to solve, but a constraint the scheduler must honor.

---

## 12. Out of Scope

- **What the proactive message says.** That is the Proactive Message Generator's job (spec §10.6).
- **When the message actually sends.** The Pending Initiative Worker (spec §10.7) handles jitter, queue ordering, and retry. The Decider emits the *intent*.
- **How wellbeing flags are computed.** SS07's wellbeing-monitor-worker owns this. The Decider only reads.
- **Activity Pool curation, Daily Ritual streak tracking.** Owned elsewhere in SS06.

---

## 13. Sign-off Checklist

Before this design becomes implementation:

- [ ] Product confirms the Wellbeing Override matrix (§7.3) — especially `crisis: care_check = ✅` and `dependency: care_check = ❌`.
- [ ] SS07 confirms `WellbeingState` field names and update cadence.
- [ ] SS04 confirms `behavioral_envelope.can_initiate_conversation` is the correct flag for G2.
- [ ] SS03 confirms `longing` is in the active stack and exposed with `intensity` field.
- [ ] Soul team confirms quota interpretation (Open Question #1).
- [ ] Adaptive rate carve-out for care-class triggers (§6.2) accepted.
