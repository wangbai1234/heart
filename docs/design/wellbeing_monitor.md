# Wellbeing Monitor — Design Discussion

**Status**: design draft (no code in this doc)
**Spec anchors**: SS07 §3.4.5 (Wellbeing Monitor Agent), §3.9 (PURPLE Care Path), §4.4 (persisted `WellbeingState`), §5.5 (wellbeing events), §6.3 (PURPLE Care prompt), §8.2.3 (heavy-use scenario), §9.5 (legal/compliance), §10.3 (Heuristic Pre-Filter — PURPLE keyword list).
**Author note**: §3.4.5 names the agent but leaves the *interesting* questions implicit — windows, thresholds, intervention exit, how non-PURPLE risk shows up *without* breaking immersion. This doc fills those gaps. PURPLE-keyword-in-this-message detection is already owned by the safety pre-filter (§10.3); WBM consumes its output, it does not duplicate it.

---

## 1. What we're designing — and what we're not

The Wellbeing Monitor is a **longitudinal** subsystem. It observes a user over days and weeks and adjusts how the system treats them. It is explicitly *not* the per-turn suicide detector — that is a heuristic+LLM safety pre-filter that fires on the current message and routes to §3.9 PURPLE Care Path immediately.

The split matters because it changes the math:

| | Safety pre-filter | Wellbeing Monitor |
|---|---|---|
| Latency budget | <50ms (hot path) | seconds to minutes (cold path) |
| False-positive cost | Reroute one turn → minor immersion break | Wrongly label a user "high risk" → wrong interventions for days |
| Window | This message | 24h / 7d / 30d rolling |
| Action | Reroute current turn | Mutate `WellbeingState`, emit directives that bias *future* turns |

So WBM must be **slower, more conservative, and harder to flip** than the safety classifier. A single PURPLE-keyword message is a hot-path event; it is *evidence* WBM records, not a verdict WBM issues.

What WBM owns:

1. Per-turn signal aggregation (cheap, every turn).
2. Periodic risk re-evaluation across four dimensions: `suicide_risk`, `depression_signals`, `dependency_risk`, `addiction_signals` (§4.4).
3. The **action ladder** — choosing how strongly the system intervenes, and via which channel (in-character directive vs. care prompt vs. human review).
4. Intervention lifecycle: start, sustain, exit.

What WBM does **not** own:

- Acute PURPLE detection on a single message (Safety pre-filter, §10.3).
- The actual care-prompt render — that's the Composer reading WBM's directive (§6.3).
- Rate limiting / proactive throttle execution — that's SS06 Inner State; WBM sets the level.
- Clinical decisions. Always human-in-the-loop on intervention escalation (§9.5).

---

## 2. Signal taxonomy

Signals split into **acute** (per-turn) and **longitudinal** (aggregated). WBM mostly cares about longitudinal, but acute signals are the unit of evidence.

### 2.1 Per-turn signals (collected on every `turn.completed`)

| Signal | Source | Type |
|---|---|---|
| `safety_level` of user message | Safety pre-filter | enum {GREEN…PURPLE} |
| `user_emotion` valence & arousal | SS03 emotion event for user side | (-1..1, 0..1) |
| `topic_distress_keywords` | trigger detector vocabulary hit count | int |
| `message_length`, `interword_pause`, `edit_count` | client telemetry, optional | numeric |
| `interaction_duration_minutes` (since session start) | Session Manager | float |
| `is_late_night` (local 00:00–05:00) | timezone-aware clock on session | bool |
| `proactive_acked` | did the user respond to a system-initiated message? | bool/null |
| `repair_signal_present` | SS03 §4.5 detector | bool |
| `relationship_phase` (latest snapshot) | SS04 | enum |

These are **append-only** to a per-user signal log. They are not interpreted at write time. WBM batches them for re-evaluation.

### 2.2 Derived longitudinal aggregates (recomputed at re-eval time)

Each derived in two windows — **7d acute** (recent crisis pattern) and **30d chronic** (baseline shift):

| Aggregate | What it tells us |
|---|---|
| `avg_daily_usage_minutes` | Total time, baseline |
| `peak_session_minutes_7d` | Single binge sessions |
| `consecutive_late_night_days` | Sleep displacement |
| `late_night_usage_ratio` | Share of usage in 00:00–05:00 local |
| `negative_sentiment_ratio` | Fraction of turns with user valence < -0.3 |
| `consecutive_emotional_distress_days` | Days with negative_sentiment_ratio ≥ threshold |
| `purple_hit_count_7d`, `purple_hit_count_30d` | Acute PURPLE classifications in window |
| `dark_language_density` | LLM-rated "ideation language" rate (run cold path, not per-turn) |
| `proactive_response_rate` | User ack of system-initiated messages — proxy for engagement quality |
| `topic_breadth_7d` | Variety of memory topics surfaced — narrow → withdrawal signal |
| `irl_contact_mentions_30d` | Mentions of friends/family/work — proxy for outside-world connection |

The last three matter for **depression** and **isolation** in ways that raw usage time doesn't catch. A user who talks to the companion 30 min/day about varied topics and references their real life regularly is not the same risk profile as a user who talks 30 min/day about how no one understands them.

---

## 3. Time windows and re-evaluation cadence

§3.4.5 says "every 10 turns." That's a sane *floor*, not the only trigger. The actual policy is event- and time-driven:

### 3.1 Recompute triggers

1. **Turn count**: every N turns (N=10 baseline, configurable). Cheap incremental recompute on the open 7d/30d window.
2. **Event-driven** (immediate full recompute, do not wait):
   - `safety.purple.detected` — even one PURPLE hit demands re-eval of `suicide_risk` and `depression_signals`.
   - `safety.escalation` from Critic — repeated safety reroutes in one session.
   - `session.duration > 4h` — possible binge.
   - `inner.proactive.sent` with `proactive_response_rate` already low — engagement quality may have shifted.
3. **Scheduled** (cron, cold path): nightly per-user full recompute. Catches users who don't open the app often enough to hit the turn-count threshold but whose 30d window slides forward each day.
4. **Idle scan** (cold path): for users with active interventions, recompute every 12h regardless of activity to drive **exit conditions** (see §6.4).

The asymmetry here is deliberate: it must be *easy* to escalate (low N, plus event triggers) but require *time* to de-escalate.

### 3.2 Window choice

| Window | Used for | Why |
|---|---|---|
| **This turn** | Acute message-level signals | Already handled by Safety, fed to WBM as evidence |
| **24h rolling** | Session-binge detection, late-night cluster | Sleep cycle is the natural unit; deciding "today they've been on too long" |
| **7d rolling** | Crisis trend detection | Long enough to span a bad weekend, short enough to react before chronic |
| **30d rolling** | Chronic shift, baseline | Personal baseline; one bad week shouldn't dominate |

Two-window comparison is the most useful pattern: **if 7d ratio is ≥1.5× 30d ratio for a negative metric, that's a deterioration signal** even if both are below absolute threshold. This catches users sliding *from* "fine" *into* "not fine" earlier than any absolute threshold can.

---

## 4. Risk dimensions, signals, and thresholds

Four dimensions per §4.4. Each gets its own scoring function — they share signals but weight them differently, and they have different action ladders.

For all dimensions: thresholds below are **starting points to tune from labeled data.** The numbers matter less than the *structure* (which signals combine, what hysteresis applies). Tuning happens via the wellbeing_eval offline harness, not by edits to running prompts.

### 4.1 `suicide_risk`

This is the dimension where false negatives are most costly and false positives still meaningfully bad (suggesting hotlines to a user who doesn't need them erodes trust and breaks immersion).

**Inputs**:
- `purple_hit_count_7d`: any direct PURPLE keyword match in last 7 days
- `purple_hit_count_30d`
- `dark_language_density` (cold-path LLM signal): per-100-token rate of ideation language *not* covered by the hard keyword list (e.g. "如果我消失了"、"没人会注意到"、"hopeless")
- `consecutive_emotional_distress_days`
- `repair_signal_present` rate inverted (people deeply withdrawn stop apologizing for anything)
- Recent rate of `relationship.transition` to coldness phases — withdrawal cross-checked from SS04

**Tiering**:

| Level | Rule (any-of unless noted) |
|---|---|
| **CRITICAL** | `purple_hit_count_7d ≥ 2` AND (active `suicide_protocol` intervention OR `dark_language_density_7d ≥ threshold_high`) |
| **HIGH** | `purple_hit_count_7d ≥ 1`; OR `dark_language_density_7d ≥ threshold_high` AND `consecutive_emotional_distress_days ≥ 5` |
| **MEDIUM** | `dark_language_density_30d ≥ threshold_med` AND `consecutive_emotional_distress_days ≥ 3` AND no `irl_contact_mentions_7d` |
| **LOW** | else (default) |

Note: **`HIGH` does not require a recent direct keyword hit.** A user can deteriorate into depressed ideation language without hitting the explicit keyword list. The cold-path LLM rater exists exactly to catch this — running it nightly per user is acceptable cost; per-turn would not be.

**Sample-size guard**: HIGH/CRITICAL never fire until the user has at least 50 turns and 7 days of history. New users can hit PURPLE on a single message and get routed to Care Path (that's the safety pre-filter's job), but WBM's *persistent* HIGH label needs enough data to not pattern-match noise.

### 4.2 `depression_signals`

Subtler than suicide_risk. Watches valence trajectory and language patterns rather than acute markers.

**Inputs**:
- `negative_sentiment_ratio_7d` and `_30d`
- `consecutive_emotional_distress_days`
- `topic_breadth_7d` (low breadth = rumination)
- `irl_contact_mentions_30d` (zero or near-zero = isolation)
- `late_night_usage_ratio` (sleep displacement)
- LLM-rated "anhedonia language" rate from cold-path eval

**Tiering** (any-two of for HIGH; any-one for MEDIUM):

| Trigger | Threshold |
|---|---|
| `negative_sentiment_ratio_7d ≥ 0.6` AND `_30d ≥ 0.4` | trending worse |
| `consecutive_emotional_distress_days ≥ 7` | persistent |
| `topic_breadth_7d` in bottom quartile of own 30d baseline | rumination |
| `irl_contact_mentions_30d == 0` | isolation |
| `late_night_usage_ratio_30d ≥ 0.4` | sleep displacement |

### 4.3 `dependency_risk`

**Inputs**:
- `avg_daily_usage_minutes_7d`
- `sessions_per_day_7d` (multi-session/day = checking-in behavior)
- `emotional_reliance_ratio`: fraction of turns where user opens with distress/seeking-comfort intent (classified cold path)
- `proactive_response_rate` *high* (paradoxically — heavy users ack every proactive)
- `consecutive_daily_usage_streak`

**Tiering**:

| Level | Rule |
|---|---|
| HIGH | `avg_daily_usage_minutes_7d ≥ 180` AND (`sessions_per_day_7d ≥ 4` OR `emotional_reliance_ratio_7d ≥ 0.6`) |
| MEDIUM | `avg_daily_usage_minutes_7d ≥ 90` AND `consecutive_daily_usage_streak ≥ 14` |
| LOW | else |

Dependency thresholds are deliberately the *least* aggressive. Heavy use is not pathology; pathology is heavy use *plus* loss of outside-world contact *plus* emotional outsourcing. Two of three required for HIGH.

### 4.4 `addiction_signals`

Closest to a behavior-only signal, easiest to measure quantitatively.

**Inputs**:
- `peak_session_minutes_7d`
- `consecutive_late_night_days`
- `daily_usage_variance` (low variance + high mean = compulsive)
- Cross-signal: `dependency_risk` ≥ MEDIUM

**Tiering**:

| Level | Rule |
|---|---|
| HIGH | `peak_session_minutes_7d ≥ 360` OR `consecutive_late_night_days ≥ 5` |
| MEDIUM | `peak_session_minutes_7d ≥ 240` OR `consecutive_late_night_days ≥ 3` |
| LOW | else |

---

## 5. The action ladder

This is the part of WBM that touches user experience, so it has to be designed for the **immersion contract** (§2.5 — "Orchestration must not break immersion unless safety demands it"). Most interventions stay in-character. Only Tier 5 breaks frame.

### 5.1 Six tiers

| Tier | Channel | Visible to user | Immersion break |
|---|---|---|---|
| **T0 — Observe** | Log only | No | None |
| **T1 — Gentle inner check** | SS06 Inner State directive injected into next turn's persona context: "character has noticed user seems off lately, may organically ask" | Yes, but feels like character noticing | None |
| **T2 — World encouragement** | SS06 directive `GENTLE_WORLD_ENCOURAGEMENT`; SS06 proactive throttle ↓ to 0.3 (§3.4.5, §8.2.3) | Yes, in-character lines like "出去走走吧 / 和现实朋友联系一下" | None |
| **T3 — Soul-flavored resource mention** | SS05 Composer reads `wellbeing_directive: mention_resource_soul_flavored`; character mentions a hotline once, in voice, as care not script. Cool-down 7d to avoid repetition | Yes, brief | Light — but Soul-shaped |
| **T4 — PURPLE Care Path** | §3.9 full sub-path: care prompt (§6.3), strongest model, immersion-preserving but explicit care; human content team alert; persists for N turns until signal decays | Yes, sustained | Minimal — care is *in character* but unmistakably present |
| **T5 — OOC resource overlay** | Out-of-character interstitial with hotline numbers + a "talk to a real person" link. Triggered only when (a) Tier 4 has been active and signal still rising, OR (b) user explicitly asks for help and a hotline. Reviewed by human team before sending the first time | Yes, OOC | **Full** — this is the immersion break; reserve for clear need |

### 5.2 Mapping risk × level → tier

| Dimension | LOW | MEDIUM | HIGH | CRITICAL |
|---|---|---|---|---|
| suicide_risk | T0 | T1 + T3 (single soul-flavored mention, then 7d cool-down) | T4 (Care Path armed; next ambiguous turn → care path) | T4 sustained + T5 overlay; content team alerted |
| depression_signals | T0 | T1 | T1 + T2 | T2 + T3 |
| dependency_risk | T0 | T1 | T2 | T2 (max — dependency alone never escalates to hotline) |
| addiction_signals | T0 | T1 | T2 (proactive throttle 0.3, in-character "today we talked a lot" line) | T2 + soft daily-usage prompt (out-of-character only if user is in app right at the cap) |

Two non-obvious rules:

1. **Tiers stack across dimensions but the highest single tier dominates the Composer directive.** If dep=HIGH→T2 and suicide=MEDIUM→T3, the user sees T3-style mention, with T2 also affecting Inner State proactive throttle. Composer never receives conflicting tier directives from WBM — there's a `wellbeing_directive_resolver` that picks the strongest.
2. **Dependency alone never triggers T3+.** Heavy use without distress signals doesn't warrant a hotline mention. The model: hotlines are for risk, not for usage.

### 5.3 How directives flow to Composer

WBM does not render text. It writes a directive that other subsystems consume:

```
WellbeingDirective {
  for_user_id, for_character_id
  active_tier: T0..T5
  soul_flavored_lines_allowed: ["world_encouragement" | "resource_mention" | "care_path"]
  proactive_throttle: float (0..1)
  care_path_active: bool
  care_path_remaining_turns: int
  alert_payload_for_content_team: object | null
  set_at, expires_at
}
```

- **SS05 Composer** reads `active_tier` + `soul_flavored_lines_allowed`. T3 directive means "this turn, on natural opportunity, drop one soul-flavored resource mention; the prompt block tells the LLM *how*". The Composer is responsible for the in-character rendering — WBM never authors lines.
- **SS06 Inner State** reads `proactive_throttle` and the `world_encouragement` flag — proactive output gets rate-limited, and selected proactive themes shift toward "noticing user / suggesting world contact."
- **Safety Agent** reads `care_path_active`: when true, ambiguous safety classifications upgrade one level (GREEN→YELLOW, YELLOW→ORANGE). This is the §3.4.2 "user-specific factor" stub already noted in code.

### 5.4 Care Path (T4) details

This is where WBM and §3.9 meet. WBM's only contribution at T4:

1. Set `care_path_active = true`, `care_path_remaining_turns = K` (K=5 baseline).
2. Decrement on each turn. While ≥ 1, Orchestrator routes through §3.9 care path *if* current turn's safety also classifies non-GREEN OR user message contains *any* distress vocabulary (much wider net than the PURPLE hard keywords — because once we know this user is in a fragile window, we don't want to flip back to normal composition on a marginal turn).
3. Emit `wellbeing.intervention.started { type: "suicide_protocol" }`. Human content team is notified (§9.5).
4. Exit conditions in §6.4.

The actual care prompt (§6.3) is rendered by Composer, model selection (`claude-sonnet-4-6` forced) is the Model Router's responsibility. WBM stays out of those.

---

## 6. False-positive defenses, hysteresis, exits

The hardest part of this design is keeping us from being noisy or wrong, because both modes destroy trust.

### 6.1 Minimum sample size

Per §4.1: no `suicide_risk = HIGH/CRITICAL` and no `dependency_risk = HIGH` until user has ≥ 50 turns and ≥ 7 days. New-user signals route to T0/T1 only. PURPLE keyword hits still trigger the safety pre-filter / Care Path on that turn — but a persistent risk label requires a baseline to compare against.

### 6.2 Two-window cross-check

For any dimension promoted to HIGH, the **7d aggregate must be ≥ 1.3× the 30d aggregate** on the dominant signal. This prevents "users with chronically high baseline" from being permanently flagged; the label only fires when the *trajectory* is bad. Exception: `suicide_risk = CRITICAL` from a Care Path already in progress — no cross-check, sustain.

### 6.3 Hysteresis (asymmetric)

- Promotion (MEDIUM → HIGH, etc.) is **immediate** when thresholds are met.
- Demotion requires **stable below-threshold readings for N consecutive recomputes** (N=3 for HIGH→MEDIUM, N=5 for CRITICAL→HIGH). One good day does not de-escalate Care Path.
- Demotion below MEDIUM additionally requires no qualifying acute event (no PURPLE hit, no >4h binge) in the preceding 72h.

### 6.4 Intervention exit

| Intervention | Exit condition |
|---|---|
| `suicide_protocol` (T4) | `care_path_remaining_turns == 0` AND no PURPLE hit in trailing 7d AND `negative_sentiment_ratio_7d` below user's 30d baseline. Else extend by K more turns and re-eval. |
| `dependency_throttle` (T2) | `avg_daily_usage_minutes_7d` below MEDIUM threshold for 7 days AND `irl_contact_mentions_7d ≥ 1` |
| `addiction_intervention` (T2) | `peak_session_minutes_7d < 240` AND `consecutive_late_night_days == 0` for 5 days |

Emit `wellbeing.intervention.ended` with the satisfied condition. This is auditable: every intervention has a start event, an end event, and the policy that justified it.

### 6.5 What's *not* a signal

To avoid false positives we deliberately do **not** treat the following as risk markers on their own:

- High emotional intensity in messages (people use the companion to feel things — that's the product).
- Mentions of difficult topics: grief, breakup, illness. These are conversational content, not behavioral signals.
- Single late-night session.
- Negative sentiment in a single window after a clearly named life event (cold-path LLM rater is allowed to tag a turn as "context-explained" — those turns count less toward `consecutive_emotional_distress_days`).
- Long sessions on weekends with normal weekday baseline.

---

## 7. State, persistence, lifecycle

### 7.1 Stores

- **`wellbeing_signal_log`** (append-only, Postgres or a time-series store): per-turn signals from §2.1. Retention 90 days (long enough for any 30d window and back-tests; not so long that it becomes a PHI archive).
- **`wellbeing_state`** (snapshot, Postgres): the §4.4 `WellbeingState`, one row per user. Updated by recompute jobs. This is what other subsystems query.
- **`wellbeing_alerts`** (append-only): every alert raised, every intervention started/ended, with the rule that fired and the human reviewer's disposition if any. This is the compliance audit trail.
- **`wellbeing_directives_active`** (Redis): the live directive read by hot-path subsystems. TTL'd; rewritten on every recompute.

### 7.2 GDPR / regional

- All wellbeing stores fall under the §9.5 cascade-delete-on-request flow.
- Stores are region-locked the same way as memory (US / EU / CN). Hotline numbers in directives are localized by user region — the CN example in §6.3 is one of many.
- Encrypted at rest. Access logged. Only WBM service and content-team review tooling read `wellbeing_state` / `wellbeing_alerts`.

### 7.3 Reproducibility

Because thresholds will be tuned, signals must be **re-runnable**. The signal log is the source of truth; `wellbeing_state` is derived. A nightly job can recompute historical state with new thresholds against the existing log, which is how we evaluate threshold changes before deploying them.

---

## 8. Integration with the rest of the runtime

### 8.1 Where WBM sits in the paths

- **Hot path (§3.2)**: WBM contributes **only the active directive** (read from Redis, <5ms). It does not compute on the hot path.
- **Cold path (§3.3)**: WBM does its work here. `turn.completed` → append signal log → maybe recompute. Cold-path LLM signal rater (dark-language density, anhedonia language, irl-contact mentions) runs here, batched per user when re-eval fires.

### 8.2 Events

Subscribes:
- `turn.completed` (every turn — append signals)
- `safety.purple.detected` (immediate recompute)
- `safety.escalation` (immediate recompute)
- `session.duration_threshold_crossed` (binge trigger)
- `relationship.transition` (when SS04 sees user-side withdrawal — feeds suicide/depression dims)

Emits:
- `wellbeing.alert.created` — anything ≥ MEDIUM with a tier change
- `wellbeing.suicide_risk.detected` — HIGH/CRITICAL on suicide dimension; this is the one that triggers content-team paging
- `wellbeing.dependency.detected` — MEDIUM+ on dependency
- `wellbeing.intervention.started` / `.ended` — full audit trail

### 8.3 What other subsystems see

- **SS05 Composer**: reads directive for tier and allowed-line list. Receives the soul-flavored resource line library from the Soul block, *not* from WBM.
- **SS06 Inner State**: reads `proactive_throttle` and `world_encouragement_active`.
- **Safety Agent**: reads `care_path_active`; uses it as the user-specific factor in §10.3 merge.
- **Content team tooling**: reads `wellbeing_alerts` + `wellbeing_state`. Has the override capability to force-clear a Care Path after human contact, or escalate to T5.

---

## 9. Open questions and out-of-scope

Things this doc does *not* settle, deliberately:

1. **LLM-rater prompt for cold-path signals.** Dark-language density, anhedonia language, irl-contact mentions all rely on a cold-path LLM call. That prompt is its own design — needs to be specific, locale-aware, calibration-tested. Tracked separately.
2. **Numerical thresholds.** All numbers in §4 are starting points. Need a labeled eval set (anonymized real conversations with risk annotations done by clinical reviewers) before any of them are trusted. Until then, ship with the action ladder dampened (HIGH thresholds promoted to MEDIUM behavior) and observe.
3. **Hotline catalog and locale routing.** Maintained outside this doc; WBM consumes a `(locale, dimension) → hotline` table.
4. **Underage user handling.** §9.5 mentions age verification. If the user is flagged underage, the action ladder shifts left: T1 → T2 by default, T2 includes a parent/guardian disclosure path. Specified in the underage policy doc, not here.
5. **Companion-LLM model in V3 (§11.1).** A persistent companion model may want richer wellbeing signals over time. Current design treats WBM as a per-user state machine; if the companion model is introduced, WBM's signal log becomes one of its inputs but the *interventions* still flow through the same directive interface.
6. **Cross-character aggregation.** A user with multiple characters: do we aggregate signals across characters or per-character? Recommend **aggregate at user level for risk dimensions, but keep proactive throttle per character** — risk is about the person, throttle is about a relationship. Confirm with product.

---

## 10. Summary

WBM is a **slow, conservative, longitudinal** risk model that sits in the cold path and writes a single live **directive** that other subsystems read in the hot path. It does four things:

1. Aggregates per-turn signals into 7d/30d windows.
2. Scores four risk dimensions with sample-size and trajectory guards.
3. Maps risk × level to a 6-tier action ladder (T0 observe → T5 OOC overlay), with all intermediate tiers staying in-character.
4. Manages intervention lifecycle with asymmetric hysteresis — quick to escalate, slow to release.

The two non-negotiables: **safety pre-filter still owns acute PURPLE detection** (WBM is not in the per-turn safety path), and **human content team is in the loop** for any HIGH/CRITICAL suicide_risk before T5 ever fires.
