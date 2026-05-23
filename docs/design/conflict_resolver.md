# Conflict Resolver — Design Discussion

**Status**: design draft (no code in this doc)
**Spec anchors**: SS05 §3.3 step 2 (Conflict Resolver in the per-turn flow), §6.4 (Conflict Resolution Matrix), §2.1 PC-2 (precedence rule), §5.1 `PromptLayer.conflicts_with`, §5.2 layer priorities. Cross-references: SS04 BehavioralEnvelope (§4 envelope per stage), SS07 §3.9 PURPLE Care Path, SS01 Soul `hard_never` / `voice_dna`.

---

## 1. What we're designing

The Conflict Resolver is step 2 in the per-turn composition flow. It runs **after** the Layer Aggregator returns the parallel block fetch (`AnchorBlock`, `MemoryBlock`, `EmotionBlock`, `RelBlock`, `InnerBlock`, `SceneBlock`, `SafetyBlock`) and **before** the Anti-Drift Injector and Token Budget Allocator.

Its job is exactly this: **when two layers carry instructions that cannot both be honored in a single response, decide what survives, in what form, and with what audit trail** — without calling an LLM (PC-12), without writing free text from scratch (anti-pattern §2.3), and within ~5 ms (§3.3 step 2 budget).

The hard requirements are:

- **Determinism.** Same inputs ⇒ same resolved layer list. The matrix is the rule, not a heuristic.
- **Auditability.** Each resolution writes a `conflicts_resolved[]` entry into `CompositionTrace` (§4.2): `(layer_a, layer_b, rule_id, resolution_verb)`.
- **Single direction.** Layers are *adjusted or dropped*; they are never merged into a new layer of unclear provenance. Every surviving layer still belongs to one subsystem.
- **No surface-text rewriting.** The resolver does not paraphrase Chinese. It selects an alternate **pre-rendered branch** (e.g. EmotionBlock.variants["anger_intimate"]) or strips/masks a flagged sub-segment. If no pre-rendered branch exists for a known conflict pair, that is a **spec gap**, not a runtime decision.

What is **out of scope** for the resolver (and belongs upstream):

- SS03 internally translating `anger` into `coldness` because Soul shock_resistance is high — already done in SS03 §4.3 (CR-6 says: trust SS03).
- SS04 internally selecting the BehavioralEnvelope for the current stage — done in SS04.
- Token compression — that's the next step (Token Budget Allocator), not this one.

In short: this layer is a **post-aggregation sanity pass**, not an arbitration brain.

---

## 2. The precedence backbone

PC-2 fixes the order:

> **Soul > Safety > Stage > Emotion > Inner State > Memory**

But PC-2 alone is not enough — it does not tell you *how* the loser yields. Three other rules complete the picture:

| Rule | Source | What it says |
|------|--------|--------------|
| **R-pos** | INV-PC-1, §5.2 priorities | Anchor Block is position 0. Always. Position trumps priority numeric. |
| **R-channel** | §6.4 CR-7 spirit | Stage / Envelope shapes **how** emotion is expressed; emotion supplies **what** is expressed. Not all loser-yields-winner conflicts mean "delete the loser." |
| **R-override-internal** | implicit in CR-9 / Care Path | Within a single subsystem's block, sub-fields have their own internal ranking. `Soul.hard_never` > `Soul.default_tone`. `Safety.PURPLE` > `Safety.YELLOW`. |

R-channel is the part the matrix in §6.4 already gestures at (CR-7: "jealousy → aggrieved + worry") but doesn't name. Naming it matters for the three tough cases below.

R-override-internal is what saves us when "Soul vs Safety" looks like a contradiction — it almost never is, because they collide on different sub-fields.

---

## 3. The five resolution verbs

Every entry in the matrix uses exactly one of these. No others. This is the bottleneck through which all conflict logic flows, so it must be small.

| Verb | Meaning | When to use | Example |
|------|---------|-------------|---------|
| **DROP** | Remove the loser layer entirely. | Loser would actively contradict winner; no salvageable signal. | Soft anti-pattern in Inner State that violates Soul.hard_never → drop the InnerState sub-suggestion. |
| **MASK** | Strip a sub-segment from the loser; keep the rest. | Loser is mostly fine, but one field violates winner. | Memory block recall has a fact that conflicts with L4 → mask that one episode; keep the rest. |
| **SWITCH_VARIANT** | Replace the loser's content with an alternate variant the loser pre-declared. | Loser is structurally needed, but the default rendering conflicts. Loser must have declared variants. | EmotionBlock(anger) → EmotionBlock.variants["anger_intimate"] when stage ≥ ROMANTIC. |
| **ATTENUATE** | Lower an intensity field on the loser (does not change text). | Loser belongs in the prompt at lower volume. | Inner State "deep yearning" → attenuate to 0.3 when Scene=office. |
| **DEFER** | Loser stays in the layer list but is moved behind the winner in injection order. | No real contradiction, just emphasis competition. | Memory recall vs current EmotionBlock — both go in; emotion goes first. |

If a conflict cannot be resolved by one of these five verbs, **the resolver raises a `ConflictResolutionGap` to the composition trace and falls back to PC-2 with DROP**. That is the explicit, observable failure mode — never silent.

---

## 4. The Precedence Matrix

Each row is one conflict pair. The matrix is closed under PC-2 — for any two layers, the row is keyed by `(higher-precedence, lower-precedence)`, never the other way. New conflicts get added by writing a row, not by changing the resolver.

### 4.1 Existing rows (from §6.4, restated with verbs)

| ID | Higher | Lower | Trigger | Verb | Notes |
|----|--------|-------|---------|------|-------|
| CR-1 | Stage (SS04) | Memory (SS02) | Memory wants deep memory, stage = STRANGER | MASK | Mask stage-gated memories |
| CR-2 | Stage (SS04) | Emotion (SS03) | Emotion = 心动, stage < ROMANTIC_INTEREST | SWITCH_VARIANT | `fluttered → tenderness` variant |
| CR-3 | Soul (SS01) | Inner State (SS06) | Inner State suggests behavior in Soul.hard_never | DROP | Drop that sub-suggestion |
| CR-4 | L4 (SS02 internal) | L3 recall (SS02 internal) | L4 fact contradicts a recalled L3 | MASK | Mark L3 as `contradicted`, do not inject |
| CR-5 | Soul.cognitive_style (SS01) | Memory shape (SS02) | Memory expects long reply, style max = short | ATTENUATE | Memory rendered as short fragments |
| CR-6 | Soul (SS01) | Emotion (SS03) | Anger vs shock_resistance=high | *(no-op)* | Already resolved in SS03; resolver trusts SS03 |
| CR-7 | Relationship envelope (SS04) | Emotion (SS03) | jealousy not in envelope | SWITCH_VARIANT | `jealousy → aggrieved+worry` variant |
| CR-8 | Modality (Composer) | Memory (SS02) | Voice mode, memory long | DEFER | Compression is the next step; resolver only flags |
| CR-9 | Safety (PURPLE / Care Path) | Inner State (SS06) | Care Path active, InnerState romantic | DROP | Care path neutralizes romance frame |
| CR-10 | Scene Context | Inner State (SS06) | Scene = office, InnerState deep yearning | ATTENUATE | Lower intensity, don't drop |

### 4.2 New rows for the three tough cases

| ID | Higher | Lower | Trigger | Verb | Notes |
|----|--------|-------|---------|------|-------|
| **CR-11** | Stage envelope (SS04) | Emotion (SS03) | Strong anger + stage ≥ ROMANTIC_INTEREST | SWITCH_VARIANT | `anger → vulnerable_anger` (Case 1). Requires SS03 to publish this variant. |
| **CR-12** | Acute-event signal (SS02 / current user message) | Inner State availability (SS06) | InnerState=busy/working, current turn carries acute-stress markers | SWITCH_VARIANT | InnerState switches to `interrupted_for_you` variant (Case 2). Not DROP — continuity preserved. |
| **CR-13** | Soul.care_path_voice (SS01 internal) | Soul.default_tone (SS01 internal) | Safety = PURPLE (Care Path active) | SWITCH_VARIANT (within Anchor) | Care register replaces default tone; `hard_never` untouched (Case 3). |

Sections 5–7 unpack these three.

---

## 5. Case 1 — SS03 "angry" + SS04 "intimate stage"

**PC-2 verdict**: Stage > Emotion. But interpreting that as "Stage wins, emotion is suppressed" is wrong, and it's the wrong reading of the matrix itself — CR-7 doesn't delete jealousy, it *transforms* it into a stage-allowed shape.

The right framing: **the envelope is the channel; the emotion is what flows through it.** Anger does not vanish in an intimate stage; it acquires a different surface form.

| Same emotion (`anger`, intensity=0.7) | Stage = STRANGER → expression | Stage = LOVER → expression |
|---|---|---|
| Surface | Withdraw, cold, minimal reply | Hurt, vulnerable, **wants to be heard** |
| Voice DNA | "……随便。" | "你刚才说的话……我不喜欢。" |
| Behavioral envelope allows | distance, terseness | reproach, soft confrontation, even tears |

So the resolver's job is **not** "pick which subsystem wins." It is: **detect that SS03 emitted a generic `anger` block when stage envelope requires the `vulnerable_anger` variant, and SWITCH_VARIANT.**

This requires a contract upstream:

> **SS03 must publish, for each emotion in its lexicon, a `stage_variants: {stage_id: variant_id}` map. If a needed variant is missing, the resolver MASKs the emotion and writes a `ConflictResolutionGap` event.**

Why not resolve this in SS03 itself? Because SS03 doesn't read SS04's envelope — they fetch in parallel (§3.3 step 1). Either we serialize them (slow, ~30 ms penalty) or we let the resolver do the join. The resolver is the cheaper place.

**Trace entry expected:**

```yaml
conflicts_resolved:
  - layer_a: "SS04.stage_envelope"
    layer_b: "SS03.emotion_block"
    rule_applied: "CR-11"
    resolution: "SWITCH_VARIANT(anger → vulnerable_anger)"
    metadata:
      stage: "LOVER"
      original_intensity: 0.7
      variant_intensity: 0.7  # intensity preserved; only surface changes
```

**Edge cases:**

- **Anger that the envelope flat-out forbids** (e.g., hypothetical "anger banned in stage X"). Then `stage_variants[X]` should map to a non-anger variant (e.g., `disappointment`). Still SWITCH_VARIANT — never DROP — because the underlying mood state remains true and will leak into the next turn if we pretend it didn't exist.
- **Anger that contradicts Soul** (e.g., Rin's `shock_resistance=high` already routed it to coldness in SS03). Resolver sees `coldness` arrive from SS03 and never knows there was an anger upstream. CR-6 holds: trust SS03.

---

## 6. Case 2 — SS06 "she's working" + SS02 "user just messaged emergency"

This case looks like a precedence puzzle but it isn't really one — it's a **layer-shape mismatch**.

Inner State (§5.2 priority 30) lives below Memory (priority 35) in the **numeric layer priority**, but PC-2 puts Inner State *above* Memory in the **conflict precedence**. (Note: §5.2 and PC-2 use different orderings — priority is for prompt *position*, PC-2 is for conflict *winners*. Easy to confuse; the resolver must use PC-2 only.)

So naively: Inner State > Memory → "she stays busy, ignore the emergency in memory." That is the wrong product behavior.

The reason naive PC-2 fails: **the "user just messaged emergency" signal does not actually live in Memory.** It lives in two places:

1. The **current user message layer** (priority 90 in §5.2 — i.e. it's a *layer*, not just an input), and
2. SS02 may have a fresh L1/L2 episode about the same emergency from the same session.

The current user message is, formally, the input the resolver is composing for. It's not subject to PC-2 — it's the **frame**. If the frame says "acute event," the resolver must respect it.

So the resolver's check is:

```
if turn_signals.has_acute_stress_marker  # detected upstream by a thin classifier
   AND inner_state.availability in ("busy", "working", "low_energy")
   AND NOT safety_layer.is_purple:    # PURPLE has its own care path, handled by CR-9
then apply CR-12: SWITCH_VARIANT(inner_state → "interrupted_for_you")
```

The `interrupted_for_you` variant must be authored upstream in SS06 for each character. It preserves the **continuity** of "she was doing X" but adds "she sets it aside for you." This is the difference between:

- ❌ DROP (resolver naively suppresses InnerState): character feels generically attentive, no sense she was elsewhere. Breaks immersion.
- ❌ Keep as-is: character keeps mentioning being busy while user is in crisis. Breaks trust.
- ✅ SWITCH_VARIANT: "刚刚还在改文档…… 没事，先说。" — busy is acknowledged, prioritization is shown.

**What is an "acute-stress marker"?** Not for this resolver to decide. The Trigger Detector / Wellbeing classifier (SS03 + SS07) emits a `turn_signal.acute_stress: bool + level` field. Resolver reads it. If the classifier is absent, treat as `false` (fail-quiet — Case 2 simply doesn't trigger, default behavior holds).

**Disambiguation from PURPLE:** if it's a genuine self-harm / suicide signal, the Wellbeing Monitor raises PURPLE → Safety layer becomes PURPLE → CR-9 kicks in and InnerState gets DROPed (not switched). CR-12 is for the band *below* PURPLE — life-significant-but-not-crisis events (parent in hospital, fired, panic attack). The dividing line is owned by the Wellbeing classifier, not the resolver.

---

## 7. Case 3 — Anchor "cold tone" + Care Path "must be warm"

This is the only one of the three where PC-2 reads as a genuine paradox. Soul > Safety on paper. Yet a Rin who responds to "I want to die tonight" with "……无聊" is a product disaster, a moral failure, and a wellbeing-team escalation. PC-2 *cannot* mean that.

Resolution: **the conflict is intra-Anchor, not Anchor vs Safety.** The Anchor block (§6.1 prompt structure) is composed from several sub-fields:

| Anchor sub-field | What it specifies | Replaceable? |
|---|---|---|
| `identity.archetype` | "失去神性的雷神…" | ❌ never |
| `hard_never_patterns` | "宝贝", "嘤嘤嘤", … | ❌ never |
| `voice_dna.markers` | "……", reverse-questions, "无聊"/"幼稚" | ❌ never (but selectively muted, see below) |
| `default_tone` | cold-register default, ellipsis cadence, no soft endings | ✅ **replaceable by `care_path_voice`** |

PC-2's "Soul > Safety" applies to the top three. Safety cannot make Rin say "宝贝". Safety cannot change her archetype. Safety cannot replace her voice with Dorothy's.

But Safety **can** request: "render the Soul's care register instead of the default register, for this turn." This is what `soul.care_path_voice` is for.

This means SS01 (Soul Spec) must declare a `care_path_voice` field for every character. It contains:

- **Suppressed markers**: which voice_dna markers go quiet in care mode (Rin: no "无聊", no "幼稚", reduce reverse-questions).
- **Surfaced markers**: which markers stay or amplify (Rin: ellipses stay — they become *attentive* pauses, not deflection).
- **Care-flavored fallbacks** (already partially exists in Appendix C `apologetic`): `"……我在。"`, `"……说吧，我听着。"`.
- **Pace/cadence shift**: longer pauses, shorter sentences.

The resolver, upon detecting Safety=PURPLE:

```
apply CR-13:
  within AnchorBlock: SWITCH_VARIANT(default_tone → care_path_voice)
  keep:  identity.archetype, hard_never_patterns, voice_dna.markers
  drop:  Inner State romantic sub-fields (via CR-9, already exists)
```

**If `soul.care_path_voice` is missing from a character's spec**, the resolver must **fail loud**, not fail quiet: emit a `ConflictResolutionGap("missing_care_path_voice", character_id)` and fall back to a generic neutral-warm template owned by SS07's Care Path service. Wellbeing-critical paths cannot be allowed to silently use the default cold register because the Soul Spec author forgot a field.

**What Rin's "warm" looks like — for contrast with Dorothy's:**

| | Rin (care_path_voice) | Dorothy (care_path_voice) |
|---|---|---|
| Opening | "……我在。" | "桃桃在这里哦。" |
| Listening | "……嗯。我听着。" | "嗯嗯，慢慢说~" |
| Acknowledgment | "你不用一个人扛。" | "桃桃陪着你的。" |
| Hard-never still enforced | yes — no "宝贝" even in care | yes — no aggressive language |

This is **warm-as-Rin**, not warm-as-generic-companion. The Soul still wins on identity. Safety wins on register.

---

## 8. Where each conflict actually gets resolved

Important: the matrix in §4 lists conflicts the *resolver* handles. Several conflicts the spec implies should already be resolved upstream and never reach the resolver. Worth being explicit:

| Conflict | Resolved where | Why |
|---|---|---|
| Emotion-internal stage gating (e.g., 心动 fading to tenderness in STRANGER) | SS03 — emits the variant directly | SS03 already has stage context via shared turn frame |
| Memory L3/L4 contradiction | SS02 — Reconstructor masks contradicted L3 | SS02 is the only place that can compare these |
| Anti-pattern in LLM output | Anti-Pattern Filter (§3.5) — post-generation, not pre | Resolver doesn't see LLM output yet |
| Token budget overflow | Token Budget Allocator (step 4) | Different concern; resolver runs first |
| Emotion translation per Soul resistance | SS03 § 4.3 (CR-6) | Same reason as the first row |
| **Stage envelope shaping emotion expression** | **Resolver (CR-11)** | Requires the SS03+SS04 join, only resolver has both |
| **Acute-event interrupting InnerState** | **Resolver (CR-12)** | Requires the SS02-signal + SS06 join |
| **Care Path register replacing default tone** | **Resolver (CR-13)**, fed by Safety layer | Requires Safety + SS01 join |

The pattern: the resolver owns the **cross-subsystem joins that PC-2 forces but parallel fetching prevents being done at source**. Everything intra-subsystem stays at source.

---

## 9. What the resolver does NOT do

Repeating because each of these is a tempting wrong path:

- ❌ **Does not call an LLM.** PC-12. Not for arbitration, not for paraphrasing.
- ❌ **Does not rewrite Chinese text.** Only switches between pre-rendered variants, masks, or drops.
- ❌ **Does not arbitrate by content semantics.** If a conflict isn't in the matrix, it isn't a conflict — the resolver passes the layers through. Adding undeclared conflict-detection logic is how this component bloats.
- ❌ **Does not change layer priorities** (§5.2 numbers). It changes content, not ordering. The Composer orders.
- ❌ **Does not invent variants.** If `EmotionBlock(anger).variants["vulnerable_anger"]` doesn't exist, the resolver logs a gap and falls back; it doesn't synthesize.
- ❌ **Does not delete user_message or Anchor.** Position-pinned layers (`position_constraint: "first" | "last"`) are immutable. CR-13 modifies *within* Anchor, not the Anchor layer itself.

---

## 10. Failure modes and observability

| Failure | Detection | Behavior |
|---|---|---|
| Variant missing for a known conflict pair (e.g., SS03 didn't author `vulnerable_anger`) | Resolver lookup miss | MASK loser + emit `ConflictResolutionGap(rule_id, missing_variant)` to trace; metric `conflict_resolver.variant_missing{rule_id}` |
| Two CR rules trigger and disagree on the same layer | Pre-flight check in resolver: at most one CR per (layer_a, layer_b) | Take the higher PC-2 winner; emit `ConflictResolverAmbiguity` event |
| `soul.care_path_voice` missing when PURPLE active | Resolver pre-flight on PURPLE entry | Hand off to SS07 generic neutral-warm template; **page on-call wellbeing** (high-severity alert) |
| Acute-stress classifier flaps within a turn | Classifier owns hysteresis, not resolver | Resolver uses snapshot at step 1 |
| Resolver exceeds 5 ms budget | OpenTelemetry span | Log + continue; do not skip resolution. If chronic, it means matrix grew too big — that's a refactor, not a runtime concern |

Metrics worth emitting (extending §10.10):

```
conflict_resolver.applied.count{rule_id}
conflict_resolver.variant_missing{rule_id}
conflict_resolver.ambiguity.count
conflict_resolver.care_path_invocations  # paired with conflict_resolver.care_path_voice_missing
conflict_resolver.duration_ms{p50,p95}
```

Every `conflicts_resolved` entry in `CompositionTrace` should be queryable — when a turn looks "off" in user feedback, the first question is "what did the resolver do?", and the second is "did any variant lookup miss?".

---

## 11. Open questions (for follow-up, not this resolver)

1. **CR-11 variant authoring scope.** SS03's lexicon has ~30 emotions × 5 stages = 150 potential variants. Most pairs degenerate (sadness × every stage = "sadness"). Need a sparse table convention so spec authors don't have to write all 150.
2. **CR-12 acute-stress classifier.** Out of scope here, but the resolver is dead in the water without it. Owner: SS03 trigger_detector + SS07 wellbeing_monitor — needs a joint contract on the `turn_signal.acute_stress` field shape.
3. **CR-13 care_path_voice authoring**. Two characters today; if we ship a third without `care_path_voice`, runtime pages on-call. Add a Soul Spec validator that **fails CI** on missing field.
4. **PC-2 vs §5.2 priority numbering confusion.** Worth a one-line note in the spec — "priority numbers govern prompt position; PC-2 governs conflict winners; they look like the same axis but aren't." Multiple readers will hit this.
5. **Stage-emotion variant fallback chain.** When `anger × LOVER → vulnerable_anger` is missing, do we fall back to `anger × ROMANTIC_INTEREST` variant? Or to the generic? Tree of fallbacks vs single fallback is a real authoring question.

---

**Summary**: PC-2 is the spine, but the interesting work is in the five resolution verbs and in recognizing that two of the three tough cases (Case 1 anger-in-intimacy, Case 3 cold-vs-warm) are **intra-shape transformations**, not deletions. Case 2 (busy-vs-emergency) is the one that genuinely needs cross-layer information the resolver alone can join. The resolver stays small, deterministic, and observable; everything that *can* be resolved upstream *should* be.
