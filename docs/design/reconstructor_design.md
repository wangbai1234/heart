# Memory Reconstructor — Design

**Date**: 2026-05-17
**Author**: 心屿团队
**Status**: 🟡 Design (pre-implementation)
**Spec refs**: `02_memory_runtime.md` §3.9 (templates) + §6.7 (workflow) + §10.5 (perf) · `01_identity_anchor_soul_spec.md` §5.1 (voice_dna)

---

## 1. What the Reconstructor does

Turns a `raw memory` (L2 EpisodicMemory / L3 FactNode / L4 IdentityMemory + computed `state`) into a **character-voiced recall string** that gets embedded into the Memory Context Block fed to Persona Composer.

Inputs:
- `memory` (raw payload — `episode_summary` / `fact.literal_text` / `l4.canonical_form`)
- `state` ∈ {vivid, fading, faint, dormant, archived} (from §3.8 decay)
- `soul_spec.voice_dna`, `soul_spec.anti_patterns`
- `activation_state.current_cognitive_style` (sentence_length, verbosity — from Subsys 06)
- `emotion_state` (used for emotional_color adjustment only, not content)

Output:
- A single recall string of bounded length, voice-consistent, anti-pattern-clean, with state-correct uncertainty markers.

This is **not** the LLM response generator. It produces the *internal recall sentence* that sits inside the prompt's `▾ 最近相关的事` / `▾ 你了解的一些事实` blocks (see §6.4 / §6.5 examples).

---

## 2. Critical decision: Rule-based vs LLM-based

### Recommendation: **rule-based primary + narrow LLM fallback**

| Factor | Rule-based | LLM-based |
|---|---|---|
| Latency budget §10.5 (`reconstruct_top_5 P95 < 150ms`, i.e. ~30ms per memory) | ✅ 1–5ms | ❌ 500–1500ms per call |
| Cost budget §10.5 (`total < $0.55 / MAU`; encoding + consolidation already eat $0.45) | ✅ ~0 | ❌ ~$0.10–$0.30/MAU at scale |
| Anti-pattern hit rate must be **0** (SS01 §5.1 acceptance criteria) | ✅ Guaranteed by construction (post-check is enforcement, not hope) | ⚠️ Probabilistic; needs reroll loop |
| Determinism / auditability (Critic Agent grounds against source_evidence) | ✅ Every output traceable to template + filler choices | ⚠️ Black-box; hard to audit |
| Voice_dna top-3 hit rate ≥ 60% (SS01 acceptance) | ✅ Applied by construction | ⚠️ Need few-shot conditioning; brittle |
| Fluency on long vivid episodes | ⚠️ Mechanical when content is rich | ✅ Natural prose |
| Onboarding new Souls | ⚠️ Per-Soul filler authoring (small YAML) | ✅ Only voice_dna text needed |

**Why the spec hint "LLM only for complex" applies here**:
The §3.9 templates are *highly structural* — they're not creative writing, they're "fact + hedge in the right shape". State→hedge mapping is mechanical. voice_dna patterns are mostly **string-level transformations** (ellipsis insertion, "我们"→"你和我", rhetorical-question reshape, time-precision substitution). The interesting variance is the *fact content*, which is supplied verbatim from the memory row — we don't need a generative model to write it.

**LLM fallback** (rare, capped — see §6) is the escape hatch for the genuinely hard cases (rich vivid episodes, post-check repeated failure).

---

## 3. Architecture

```
                  ┌──────────────────────────────┐
                  │ MemoryRetrievalResult        │
                  │ (top-K ScoredMemory, mixed   │
                  │  L2/L3/L4)                   │
                  └──────────────┬───────────────┘
                                 ▼
            ┌───────────────────────────────────────────┐
            │  Reconstructor.reconstruct(memory, soul)  │
            └───────────────────────┬───────────────────┘
                                    │
       ┌────────────────────────────┼───────────────────────────┐
       ▼                            ▼                           ▼
┌──────────────┐         ┌─────────────────────┐      ┌──────────────────┐
│ 1. Extract   │   ───▶  │ 2. Select skeleton  │ ───▶ │ 3. Fill skeleton │
│   core_text  │         │   by state          │      │   from Soul YAML │
└──────────────┘         └─────────────────────┘      └────────┬─────────┘
                                                               ▼
                                              ┌──────────────────────────────┐
                                              │ 4. Apply voice_dna transforms│
                                              │    (top-N by frequency)      │
                                              └──────────────┬───────────────┘
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │ 5. Apply cognitive_style     │
                                              │    (truncate / compress)     │
                                              └──────────────┬───────────────┘
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │ 6. Anti-pattern post-check   │
                                              │    hard_never + regex        │
                                              └──────────────┬───────────────┘
                                          ✅ pass            │ ❌ fail
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │ 7. Retry → LLM fallback      │
                                              │    → degraded recall         │
                                              └──────────────────────────────┘
```

### 3.1 Module layout

```
backend/heart/ss02_memory/reconstructor/
├── __init__.py
├── base.py              # Reconstructor protocol, ReconstructInput, ReconstructResult
├── extractor.py         # core_text extraction per layer (L2/L3/L4)
├── skeletons.py         # state → skeleton templates (in code, not YAML)
├── voice_applier.py     # voice_dna pattern dispatcher + transforms
├── style_clamp.py       # cognitive_style (sentence_length, verbosity) clamping
├── anti_pattern.py      # hard_never + regex post-check
├── reconstructor.py     # orchestrator
└── llm_fallback.py      # capped LLM escape hatch (V1: stub, V2: enabled)
```

---

## 4. Template selection: how (state, voice_dna) maps to a template

### 4.1 Three candidate models — we pick **C**

**A. Per-Soul template files** — each `soul_specs/<char>/reconstruction_templates.yaml` enumerates 5 full templates.
  - ❌ High authoring burden, drifts from voice_dna over time, duplicates content.

**B. Generic templates in code, voice_dna applied only as post-transform**
  - ❌ Templates would be character-blind ("you said something about your cat") and lose Rin's vd-001 ellipsis structure that *is* the hedge.

**C. ★ Skeletons in code + per-Soul fillers extracted from voice_dna**
  - Skeletons are *structural placeholders* (`{hedge_low}`, `{core}`, `{emergence_marker}`).
  - Each Soul Spec contributes a tiny `reconstruction_fillers` block (one section per state) with phrases pulled from / consistent with the character's voice_dna.
  - voice_dna *transforms* (ellipsis, time precision, "我们"→"你和我") run as post-filters on the rendered string.

### 4.2 Skeleton catalog (in `skeletons.py`)

```python
SKELETONS = {
    "vivid":    "{core}",
    "fading":   "{core_softened}{hedge_low}",
    "faint":    "{hedge_strong}{core_fragmentary}",
    "dormant":  "{emergence_marker}{core_fragmentary}",
    "archived": "{disorientation_marker}{core_question}",
}
```

The skeleton is *not* the final sentence — it's the structural slot list. `{core_softened}` ≠ `{core}`: it's the *same* core fact rephrased into a less assertive form (assertion→inference, declarative→hedge-frame). `extractor.py` produces all four variants up-front from the raw memory.

### 4.3 Per-Soul filler block (NEW addition to Soul Spec)

Proposed Soul Spec extension under `voice_dna`:

```yaml
voice_dna:
  - id: vd-001
    pattern: ...
    ...
  reconstruction_fillers:        # NEW — derived from voice_dna, not in conflict with it
    fading:
      hedge_low:
        - "……对吧"               # vd-001 ellipsis + vd-002 rhetorical-confirm
        - "……什么来着"
        - "好像"
    faint:
      hedge_strong:
        - "……"
        - "好像"
        - "……过"
    dormant:
      emergence_marker:
        - "……"
        - "……是不是"
    archived:
      disorientation_marker:
        - "……等等。"
        - "……我好像，想起什么了。"
        - "你以前不是……"
```

These map 1:1 to §3.9's Rin examples. For Dorothy, the same slots get her flavor (`"诶？……"`, `"嗯？……对吧？"`) without changing the skeleton table.

**Why put fillers in Soul Spec rather than code**: voice_dna is owned by the Soul curator; reconstruction fillers are *the same author's voice*. Keeping them next to `voice_dna` keeps voice consistency reviewable in one place. Skeletons in code; fillers in YAML.

### 4.4 voice_dna transforms (post-fill, in `voice_applier.py`)

A registry of named transforms keyed by `voice_dna.id`. Each transform = pure function `str → str`. The Reconstructor runs only the **top-N (N=3) by frequency=high** transforms per turn, matching SS01's "voice_dna top-3 hit rate ≥ 60%" acceptance criterion.

| voice_dna id | Transform | Implementation |
|---|---|---|
| vd-001 (ellipsis) | Insert `……` at pause points | Splice between subject and predicate when state ∈ {fading, faint} |
| vd-002 (rhetorical-statement) | Re-shape declarative→rhetorical confirm, drop `?` | Pattern-rewrite "X 吗？" → "X。"; "你 X" → "你以为，X"; idempotent if already rhetorical |
| vd-NEW-A (time precision) | Substitute `{time_placeholder}` with exact value from `memory.metadata.precise_time` | Falls back to vague form only if Memory has no precise value (per cross_check note in Rin YAML) |
| vd-NEW-C (avoid 我们) | `s/我们/你和我/g`; `s/我们俩/你和我/g` | Pure substitution |
| vd-NEW-D (nature imagery) | Only triggers if `emotion_state.label` ∈ {gloomy, melancholic}; injects scene-set sentence | Optional, low-frequency, gated |
| vd-006 (short past sentences) | If core mentions Rin's past, hard-cap sentence_length to 8 chars | Length clamp |

Crucially, transforms are **idempotent and commutative** where possible, so order doesn't change correctness. Order chosen: substitution transforms (NEW-C, NEW-A) → shape transforms (vd-002) → insertion transforms (vd-001) → clamps (vd-006).

---

## 5. Per-layer core extraction

`extractor.py` produces a struct of four core variants from each layer:

| Layer | source field | `core` (vivid) | `core_softened` (fading) | `core_fragmentary` (faint/dormant) | `core_question` (archived) |
|---|---|---|---|---|---|
| L2 EpisodicMemory | `episode_summary` | full summary | summary with key entities preserved, modifiers dropped | only key entities + scene_context | "你以前是不是……" + scene_context |
| L3 FactNode | `literal_text` | literal | key noun + predicate | key noun only | key noun + "……" |
| L4 IdentityMemory | `canonical_form` | always rendered as vivid (§4.1 — L4 never decays) | n/a | n/a | n/a |

L4 short-circuits the state machine: §3.9 doesn't apply to L4 (L4 is always vivid). The Reconstructor returns L4's `canonical_form` directly, *only* applying anti-pattern post-check and voice_dna substitution transforms (no hedging).

---

## 6. Anti-pattern post-check

This is the **only gate that can fail-loud**. The pipeline guarantees by construction that hard_never / forbidden_patterns are not introduced, but post-check enforces.

### 6.1 Checks

1. **hard_never**: substring match against `soul_spec.anti_patterns.hard_never` list. Case + character-form normalized (full-width / half-width).
2. **forbidden_patterns**: regex check against `soul_spec.anti_patterns.forbidden_patterns`.
3. **rare_unlock_words**: if the word appears (e.g. "永远") AND conditions in Soul Spec are not met → fail.

### 6.2 On failure

```
fail → re-roll with different filler choice (max 2 retries with deterministic seed bumps)
   → if still failing → LLM fallback (rate-limited: max 1% of recalls per user per day)
       → if LLM also fails post-check → emit `degraded_recall` (use raw core without voice styling)
                                       + log metric `memory.reconstruct.degraded_count`
                                       + Critic Agent flag for this turn
```

**Why not just retry forever**: a persistent post-check failure means the *core content itself* contains a forbidden phrase (e.g. user said something containing "宝宝" to Rin; that word is hard_never for her). Retrying voice transforms can't fix it. The honest behavior is to degrade and log.

### 6.3 Latency impact

Anti-pattern check is O(|text| × |hard_never|) substring + O(|regex|) regex. With ~30 strings + 6 regex on a ~50-char output, this is sub-millisecond.

---

## 7. Cognitive style clamping (step 5)

`activation_state.current_cognitive_style` provides:
- `sentence_length.max` (chars)
- `verbosity` (low / medium / high)

Clamp logic:
- If output > `sentence_length.max` → drop trailing clauses (split on `，` / `、` / `。`), keep head.
- If `verbosity == low` → strip parenthetical clauses, hedges to one per sentence max.

This step happens *before* anti-pattern check (truncation might re-introduce a hard_never substring that was previously inside an otherwise-fine phrase — defensive ordering).

---

## 8. Caching

`retrieval_results` cache (§10.6) already caches at the retrieval layer (60s TTL). The reconstructed *string* is also stable for a (memory_id, state, soul_spec_version, cognitive_style_bucket) tuple — we can add a second-level cache:

```
key:  "rec:{memory_id}:{state}:{soul_version}:{cog_bucket}"
ttl:  300s (invalidated by decay state change)
```

Hit rate expected high during active sessions (same memory recalled across turns). Avoids re-running 6 transforms per turn.

---

## 9. Interfaces (preview, no code)

```python
class Reconstructor:
    async def reconstruct(
        self,
        memory: ScoredMemory,
        soul_spec: SoulSpec,
        activation_state: SoulActivationState,
        emotion_state: EmotionState,
    ) -> ReconstructResult: ...

    async def reconstruct_batch(
        self,
        memories: list[ScoredMemory],
        ...
    ) -> list[ReconstructResult]:
        # asyncio.gather over reconstruct() — but each call is sync CPU work
        # so this is really concurrent.map on a thread pool.

@dataclass
class ReconstructResult:
    text: str
    memory_id: UUID
    state: str
    transforms_applied: list[str]   # voice_dna IDs
    degraded: bool                  # True if fell through to raw core
    latency_ms: float
```

---

## 10. Observability (additions to §10.7)

```yaml
metrics:
  - memory.reconstruct.latency.p95 {layer, state}
  - memory.reconstruct.degraded_count
  - memory.reconstruct.llm_fallback_count
  - memory.reconstruct.anti_pattern_violations  # post-check catches
  - memory.reconstruct.voice_dna_hit_rate {soul, vd_id}  # for SS01 acceptance criteria
```

The `voice_dna_hit_rate` metric directly satisfies the Rin acceptance criterion "voice_dna top-3 命中率 ≥ 60%" — we instrument it at the source of truth.

---

## 11. Open questions for discussion

These are the genuine fork points I want a call on before coding:

1. **Per-Soul `reconstruction_fillers` block** — am I right that this belongs in the Soul Spec YAML next to `voice_dna`? Alternative: ship default fillers in code, override per-Soul only when needed.

2. **LLM fallback in V1 or V2?** I lean **V2** (ship pure rule-based first, measure `degraded_count`, only add LLM if degradation rate > some threshold). This keeps V1 latency + cost predictable. Acceptable?

3. **vd-NEW-A (time precision)** has a cross-check note: "Memory Runtime 必须能 supply 准确数字". Right now `ScoredMemory.memory_id` doesn't carry a `precise_time` slot. Should the Reconstructor:
   - (a) Compute precise time on the fly from `memory.created_at` / `memory.episode_start_at`?
   - (b) Require Encoder to write `metadata.precise_time` at write time?
   - I lean (a) — it's data we already have.

4. **L4 anti-pattern check policy**: L4 `canonical_form` is curator-authored. Should we still run anti-pattern post-check on L4? I'd say yes (defense-in-depth — if a L3→L4 promotion ever slipped through with a banned word, we catch it).

5. **Reconstruct on retrieve, or lazy on render?** Spec is ambiguous. I'd put `reconstruct_batch` as a call from Persona Composer **after** retrieval, **before** prompt assembly. That gives Persona Composer the freedom to drop a memory (e.g. cognitive_style says "this turn is very low verbosity") without paying reconstruction cost. Agree?

---

## 12. Non-goals (V1)

- Cross-memory narrative weaving (e.g. "她想起了你的猫和你的工作之间的连接") — that's a Persona Composer concern.
- Emotional color modulation of reconstructed text — emotion injection happens in the prompt template, not in the recall sentence (§6.8 conflict resolution row 4).
- Multilingual support — zh-CN only in V1 (matches Soul Spec `locale`).

---

## 13. Test strategy (preview)

- **Unit**: each transform in isolation (vd-001 ellipsis on N inputs, vd-002 rhetorical reshape, etc.)
- **Golden recall tests**: input fixture (memory, state, soul) → expected output string. ~30 fixtures covering Rin × 5 states × {L2, L3, L4} + Dorothy × 5 states (subset).
- **Anti-pattern fuzz**: random core_text containing hard_never tokens → assert degraded=true + metric increments.
- **Acceptance**: voice_dna top-3 hit rate ≥ 60% over a 500-sample synthetic dataset.

---

**References**:
- Spec: `/runtime_specs/02_memory_runtime.md` §3.9, §6.7, §10.5
- Spec: `/runtime_specs/01_identity_anchor_soul_spec.md` §5.1
- Soul Spec: `/soul_specs/rin/v1.0.0.yaml` voice_dna + anti_patterns
- Prior art: `/docs/design/retriever_implementation.md` (upstream)
