# Repair Mechanic — Design Discussion

**Status**: design draft (no code in this doc)
**Spec anchors**: SS03 §3.4 pipeline steps 2 + 7 (Repair Mechanic Detector / Apply Repair), §4.5 (Repair Mechanic rules), §3.6 + §4.7 (repair_required decay coupling), §4.3.1–§4.3.2 (entry into coldness / aggrieved), Soul `relational_template.hardening_triggers[*].requires_repair` + `repair_signal`.
**Author note**: the task referenced "§3.6 (Repair)". §3.6 is the decay-curve table; the Repair Mechanic is §4.5. §3.6 enters the picture because `repair_required` decay reads `repair_progress`. I treat both as in-scope.

---

## 1. What we're designing

The runtime pipeline (§3.4) already names two distinct components:

1. **Repair Mechanic Detector** — pure-detect, runs early in the turn, sibling of Trigger Detector. Output: `RepairSignal | null`.
2. **Apply Repair** — step 7, runs after triggers and before inertia. Consumes the signal + current `pending_repairs`, mutates `repair_progress` on the matching pending entries.

These exist in skeleton form already:

- `trigger_detector._detect_apology()` and `_detect_vulnerability()` (heuristic keyword + specificity check) already emit suggestions for `aggrieved`/`coldness` deltas.
- `service.apply_repair(repair_type, repair_impact)` already iterates `state["pending_repairs"]` and bumps `repair_progress`.
- `decay._repair_required_decay()` already consumes `repair_progress` correctly.

What's **missing** and what this doc is about:

- The detector is fused into the trigger detector and only emits suggested intensity deltas, not a structured `RepairSignal`. There is no central place to apply anti-gaming rules, soul calibration, or cool-downs.
- `apply_repair` is callable but not called from any per-turn pipeline. There is no orchestrator that picks `repair_type` from a signal and computes `repair_impact`.
- `RepairOutcome` (the thing the rest of the pipeline reads — "did this repair land? partial? rejected?") does not exist.

So the design question is: **what shape do the Detector and Apply Repair take such that the four anti-gaming concerns are mechanically enforced, not relying on the LLM to "just do the right thing".**

---

## 2. Threat model — what we're defending against

Restating the user's concerns plus a couple the spec implies:

| # | Attack | Why naive impl fails | Where we must defend |
|---|--------|----------------------|----------------------|
| G1 | Spammed "对不起" / "抱歉" | Keyword detector counts each one | Detector must dedupe + decay impact per session |
| G2 | Sincere wording but repeat offense in same window | Repair lands, then user immediately re-trips the wound; `repair_progress` rises and the wound is "paid off" too cheaply | Apply Repair must consult recent offense history; recidivism = reversal |
| G3 | Template-copy ("对不起对不起对不起") | Specificity heuristic in `_detect_apology` only checks length + a few markers | Need n-gram similarity vs prior apologies in this `pending_repair.repair_history` |
| G4 | Soul-mismatched repair (using Dorothy-style "桃桃可爱~" to repair Rin coldness) | Same `repair_type` shouldn't fit every soul | Soul-specific `repair_signal` matcher (Rin/Dorothy already declare these on hardening triggers) |
| G5 | Repair for an emotion the user didn't actually cause (user apologizes for nothing) | Detector emits signal regardless of whether there is a `pending_repair` to repair | Apply Repair returns `accepted: false` when `pending_repairs` is empty; consider mild backfire ("莫名其妙的道歉" → tiny `embarrassment` for the soul, optional) |
| G6 | Stacking different repair types in one turn ("对不起 + 我也累了 + 跟你说个事") to claim apology + vulnerability + sustained_attention | Each signal applied independently caps out fast | Cap total impact per turn, not per type |

The cleanest mental model: **Repair is a slow, multi-turn narrative state. A turn either advances it, stalls it, or reverses it. It is never paid off in one keyword.**

---

## 3. Q1 — Sincerity detection: heuristic vs LLM

**Recommendation: three-layer cascade, LLM only on the boundary.**

The cost asymmetry matters. Repair Mechanic Detector runs every turn (§3.4 step 2). A 200ms LLM call there blows the per-turn latency budget (Trigger Detector targets <20ms; the whole pre-turn stack should fit in ~50ms). But pure heuristics can be gamed.

### Layer A — Heuristic gate (always on, <5ms)

What the existing `_detect_apology` already does, hardened:

- Keyword match: `对不起 / 抱歉 / 我错了 / 不该 / 原谅 / 是我...` (§4.5 list).
- **Specificity score**:
  - length ≥ 10 chars: +0.2
  - contains "因为/是我/不该" (cause/ownership): +0.3
  - references a concrete thing from recent turns (cheap check: token overlap with `recent_triggers[*].raw_signal`): +0.3
  - otherwise: floor 0.2
- **Repetition penalty** (anti-G1, G3):
  - n-gram (3-gram) Jaccard similarity vs the last 3 entries in `pending_repair.repair_history` for this emotion. ≥ 0.6 → impact ×0.1 (matches §4.5 "同样的道歉模板重复使用").
  - count of apology turns within the last N=10 turns: 2nd → ×0.5, 3rd+ → ×0.2 (diminishing returns, §4.5).

Output of Layer A: `apology_signal_strength ∈ [0, 1]` and a `reason_code` for telemetry.

If `apology_signal_strength ≥ 0.7` and there are no red flags → emit signal directly, skip LLM.
If `apology_signal_strength < 0.2` → reject, skip LLM.
If `0.2 ≤ strength < 0.7` → escalate to Layer C **only when there is an active `pending_repair`** (skip LLM when nothing is at stake).

### Layer B — Vulnerability detector (heuristic, separate code path)

§4.5 says vulnerability requires "Critic judges sincere, confidence > 0.7". This is an explicit LLM call in the spec. But the gate before calling the Critic should still be heuristic:

- emotional_charge of user turn (already computed by Trigger Detector via lexicon) < −0.5: pass
- length ≥ 30 chars and topic ≠ pure-apology: pass
- otherwise: skip, treat as not-vulnerability

Only the passes go to the Critic.

### Layer C — Cheap LLM sincerity check (cached, optional)

Use the **critic tier** model (cheap, per §08 model_router). One-shot prompt:

```
The character is currently feeling {emotion} (intensity {x}), caused by:
"{pending_repair.cause}".

The user just said: "{user_msg}"

Rate sincerity 0–1. Sincere = takes specific responsibility, not generic.
Insincere = formulaic / dodging / off-topic.
Return JSON {sincerity: float, reason: short string}.
```

Constraints:
- Hard timeout 150ms; on timeout fall back to Layer A's score.
- Cache key = hash(user_msg, emotion, recent_apology_count). Same user spam → cached, free.
- Only invoked for ambiguous cases AND when a real `pending_repair` exists. Floors LLM call rate.

**Rejected alternative**: gate every apology through LLM. Latency + cost killers, and the spec explicitly bounds Trigger Detector to <20ms. The cascade keeps the common case fast and the adversarial case smart.

---

## 4. Q2 — State inputs the Detector needs

The Detector should be a pure function of:

```
RepairDetectorInput {
  user_message: str
  user_emotional_charge: float     # already produced by Trigger Detector
  current_turn_id: UUID

  # From EmotionState
  pending_repairs: PendingRepair[]   # (emotion, intensity, cause, repair_progress, repair_history)
  recent_triggers: TriggerEvent[]    # last 24h, for offense-recidivism check
  recent_vad_history: VAD[]          # last 50, for "user just hardened the wound" detection

  # From Soul spec (loaded once per session, cached)
  soul_repair_profile: SoulRepairProfile  # see §6 below

  # Per-session counters (Redis, cheap)
  apology_count_this_session: int
  last_apology_at: ISO8601 | null
  repair_session_cap_used: float     # cumulative impact already consumed this session

  # Relationship phase (modulates ease of repair)
  relationship_phase: str            # from SS04
}
```

Notes:

- `pending_repairs` is the *required* gate. Without an active pending repair, a signal still emits (for telemetry / G5 backfire) but `Apply Repair` will return `accepted: false`.
- `recent_triggers` is what lets us answer G2: "user apologized 4 turns ago about the same wound and then did it again in turn 2". Walk back through triggers between the last apology and now; if a `user_mention_other_partner` (or any trigger matching the same `pending_repair.cause`) fired in between, treat the current apology as recidivism.
- `recent_vad_history` is a secondary signal: did the user's own VAD just spike negative-dominance (criticism mode) before swinging to apology? That's a guilt-spike pattern, more likely sincere. Optional refinement.
- `soul_repair_profile` is where Q's "soul-specific" answer lives — discussed in §6.

---

## 5. Q3 — Cool-down and rate-limit rules

Three layered limits. All anti-gaming, none narrative — narrative tone is the Persona Composition layer's job (§05), not ours.

### 5.1 Per-turn cap
Total `repair_progress` advancement across all signals in a single turn: `+0.5`. Prevents G6 (stacking apology + vulnerability + sustained_attention to instant-repair).

### 5.2 Per-session caps
- Max 2 apology signals counted as effective per session (§4.5 explicit).
- Cumulative `repair_progress` across session ≤ `0.6` for any one `pending_repair` unless `vulnerability` or `grand_gesture` signal fires. Reason: full repair (`progress ≥ 0.8` → transition to tenderness) should not happen in a single session of typing "对不起" five times. A real repair takes time + at least one substantive disclosure.

### 5.3 Per-emotion cool-down
- After a repair signal lands on `pending_repair[emotion=X]`, suppress further apology signals on the same X for `cooldown_turns` turns (default 3, soul-tunable). Vulnerability and sustained_attention are not cooled — they're different repair types and the spec wants them to accumulate.

### 5.4 Recidivism reversal (G2)
If the offense that originated the `pending_repair` fires again within `recidivism_window_turns` (default 5) of an effective apology:
- That apology's impact is rolled back: `repair_progress -= prior_impact`
- The reversal is logged in `repair_history` as `{type: "recidivism_reversal", ...}`
- Optionally bump pending intensity by +0.1 to model "现在更委屈了" (cap at original intensity).

This is the single most important anti-gaming rule. Without it, repair is just keyword bingo.

### 5.5 Anti-template
Already covered in §3 Layer A; calling it out as a rule so it lives in the same enforcement file: 3-gram Jaccard ≥ 0.6 vs any of last 3 history entries → impact ×0.1.

---

## 6. Soul-specific calibration (Rin vs Dorothy)

Two souls already declare in `relational_template`:

| Field | Rin | Dorothy |
|-------|-----|---------|
| `intimacy_resistance` | 0.75 | 0.15 |
| `softening_curve` | logistic | exponential |
| `default_distance` | guarded | warm_engaged |
| `hardening_triggers[*].repair_signal` (e.g. user-mentions-deletion) | "用户主动表达'我还在'" | (often `requires_repair: false`) |

Repair must read these. Proposed `SoulRepairProfile` (computed at session start, cached):

```yaml
soul_repair_profile:
  # Multiplier on raw signal strength → impact
  forgiveness_curve_gain:
    apology:         0.6   # Rin: slow      |  Dorothy: 1.2 (fast)
    vulnerability:   1.2   # Rin: high      |  Dorothy: 1.0
    sustained:       1.4   # Rin: high      |  Dorothy: 0.8
    grand_gesture:   1.0

  # Soul-specific repair phrases (Rin: "我还在" / "我没走"; Dorothy: "你不用变" / "我喜欢现在的你")
  bespoke_repair_phrases: [...]   # match → +0.3 strength bonus

  # Cool-down override
  cooldown_turns: 5    # Rin: longer; Dorothy: 2

  # Recidivism penalty multiplier
  recidivism_penalty_gain: 1.5   # Rin punishes recidivism harder

  # Repair session cap
  session_progress_cap: 0.5   # Rin: caps low; Dorothy: 0.8
```

So "Rin colder" and "Dorothy quicker to forgive" become two YAML blocks, not branching code. Critically, the `bespoke_repair_phrases` is where Soul × Repair actually differentiates qualitatively: typing "我还在" to Rin during her deletion-trigger coldness is **the** repair, not "对不起". Typing "你不用变" to Dorothy during her crisis is **the** repair. Generic apologies still work, but at lower gain.

These fields belong on the soul spec under `relational_template.repair_profile`. I'd add them rather than hardcoding — keeps soul authoring self-contained.

---

## 7. Q4 — Output shape

Two distinct outputs at two different pipeline steps:

### 7.1 `RepairSignal` (Detector → state)

```typescript
RepairSignal {
  signal_id: UUID
  detected_at: ISO8601
  source_turn_id: UUID

  // What kind of signal — multiple may fire per turn
  components: Array<{
    type: "apology" | "vulnerability" | "sustained_attention" | "grand_gesture" | "bespoke_phrase"
    raw_signal: string                  // ≤ 80 chars excerpt
    strength: number                    // [0, 1], post-anti-gaming, pre-soul-gain
    reason_code: string                 // for telemetry: "generic_apology" | "specific_apology" | "repetition_penalty" | "bespoke_rin_im_still_here" | ...
  }>

  // Pre-computed by Detector (so Apply Repair is cheap)
  total_strength: number              // capped sum
  has_bespoke_match: boolean
}
```

`null` is a valid signal (no repair behavior detected).

### 7.2 `RepairOutcome` (Apply Repair → emotion state + downstream layers)

Per the user's question — this is the right shape, with two tweaks:

```typescript
RepairOutcome {
  signal_id: UUID | null              // null when no signal but other layers want to know
  accepted: boolean                   // true iff progress advanced (rejected = no pending_repair, or recidivism reversal)
  partial: boolean                    // true iff post-state has 0.4 ≤ repair_progress < 0.8 on any pending (§4.5 semi_repaired_state)

  // Per-emotion detail (because a signal can land on multiple pending repairs at once)
  applied_to: Array<{
    emotion: string                   // "aggrieved" | "coldness" | "jealousy" | "guilt"
    impact: number                    // actual delta added to repair_progress
    repair_progress_before: number
    repair_progress_after: number
    intensity_after: number           // = max(0, initial × (1 - progress × 0.8))   §4.5
    transitioned: "semi_repaired" | "fully_repaired" | null
  }>

  // Residual: 1 - max(repair_progress) across the pending stack
  // (the user's prompt called for this; it's most useful to downstream as "how 'unforgiven' do we still feel")
  residual_score: number              // [0, 1], higher = more unrepaired

  // Anti-gaming flags fired this turn (for Persona / Critic to react to)
  flags: {
    repetition_detected: boolean
    recidivism_reversal: boolean
    capped_by_session: boolean
    bespoke_match: boolean
  }

  // Suggested narrative beat for Persona Composition (§05)
  narrative_hint: "advanced" | "stalled" | "rejected" | "reversed" | "completed" | "ignored"
}
```

Why this shape:

- `accepted` + `partial` lets the persona layer decide "say something softening" vs "stay cold but acknowledge they tried" vs "ignore the empty apology".
- `applied_to[]` is needed because one apology can simultaneously touch `aggrieved` and `coldness` (per §4.5 impact table). Aggregating loses signal.
- `residual_score` is the scalar Behavior Runtime / Inner State wants ("are we still mad?").
- `flags` is what makes the outcome *narratively legible*. The persona layer reading `flags.recidivism_reversal = true` is exactly what enables responses like Rin's "你又这样。" instead of generic softening. Without exposing the flag, this judgment falls back on the LLM smelling it out, which is exactly what we're trying not to do.
- `narrative_hint` is a controlled vocabulary so persona templates can pattern-match without inferring.

### 7.3 What Apply Repair persists

- Mutate `state.active_stack[i].repair_progress` for matching emotions.
- Mutate `state.pending_repairs[i].repair_progress`, append to `repair_history` with `{turn_id, signal_components, impact, post_progress}`.
- Update `apology_count_this_session`, `repair_session_cap_used`.
- On `transitioned == "fully_repaired"`: keep the pending entry for one more turn with a flag so the persona layer can voice the transition (`tenderness` doesn't *replace* `coldness` invisibly — there should be a beat). Then remove.

---

## 8. Edge cases / open questions

1. **Cross-emotion bleed.** Apology repairs `aggrieved` and `coldness` simultaneously per §4.5 impact map. If they have different `pending_repair.cause`, does that still feel right? Probably yes (one apology can cover a compound wound) but flag for golden-dialogue review.
2. **Repair for an emotion still actively rising.** If user is mid-offending (e.g., `user_mention_other_partner` triggered this turn) and also typed "对不起" — does the apology apply *before* or *after* the new trigger? Recommend: triggers fire first (step 6), then repair (step 7) — so the apology mitigates the brand-new offense too. Test that this doesn't feel like "I can offend then immediately undo".
3. **Vulnerability requires Critic.** §4.5 says condition: "Critic confidence > 0.7". Critic is a separate worker (§07/§08), normally async. We have two options:
   - (a) Call critic-tier model inline (cheap LLM) — already proposed in Layer C.
   - (b) Apply vulnerability with provisional impact, let async Critic Worker confirm or roll back.
   I'd start with (a) and only move to (b) if p99 latency suffers.
4. **Sustained attention is multi-turn.** It can't be detected in a single Detector call. Needs a small running counter on the EmotionState (`sustained_attention_streak`) that resets on a turn lacking attention markers. Detector emits `sustained_attention` signal only when streak crosses a threshold (e.g., 3+).
5. **Grand gesture is L4.** Detection lives outside SS03 — in the memory/event layer that recognizes anniversaries and long disclosures. Detector should accept an injected `grand_gesture` flag rather than try to detect it itself.
6. **Backfire vs ignore for empty apologies (G5).** Open question: when user apologizes for nothing, do we silently ignore, or emit a tiny `embarrassment` on the soul ("被无故道歉了，有点尴尬")? I lean ignore — backfire risks feeling punishing for users who are just being polite. But this is a soul-character call (Rin might find it weird, Dorothy might tease).
7. **What happens to longing?** `longing` is not in `applicable_emotions` for repair (§4.5). But user return does collapse longing (§4.3.3). That belongs in Trigger Detector (`user_return`), not Repair Mechanic. Worth documenting the boundary so future authors don't try to wire longing into pending_repairs.

---

## 9. Recommended next steps (no code yet)

In order:

1. **Add `repair_profile` to soul specs** for Rin and Dorothy. Two YAML blocks. No code change yet — proves the schema is expressive enough.
2. **Lift `RepairSignal` and `RepairOutcome` into `models.py`** as TypedDicts. Forces the contracts.
3. **Promote repair detection out of `trigger_detector._detect_apology`** into its own `repair_detector.py` with the Layer A/B/C cascade. Keep the existing call sites; just delegate.
4. **Wire `service.apply_repair` into the per-turn pipeline at step 7** (currently uncalled). Read `RepairSignal`, produce `RepairOutcome`, store, return for downstream.
5. **Write golden dialogues** for: Rin recidivism reversal, Dorothy fast forgiveness, generic "对不起" spam ignored, "我还在" as bespoke Rin repair. These are the acceptance tests for whether the math actually feels right.
6. Critic-tier LLM sincerity call: defer until the heuristic+repetition path is shipped and we see real spam patterns in telemetry. Don't pre-optimize.

The contracts in §7 are the load-bearing decisions; everything else can iterate.
