# SS02 Memory LLM Extractor — Golden Set Design v1.0.0

**Date**: 2026-06-19
**Author**: 心屿团队
**Status**: 🟡 Design (pre-implementation)
**Schema ref**: `docs/design/memory_extractor_schema.md` v1.0.0
**Prompt ref**: `docs/design/memory_extractor_prompt.md` v1.0.0
**Promoter ref**: `docs/design/memory_promoter_rules.md` (for cross-session semantics)
**Spec refs**: `runtime_specs/02_memory_runtime.md` §3.4 · §6.7 · §4.2
**Code refs (target)**: `backend/tests/golden/memory_extractor/` (data) · `backend/tests/integration/test_memory_extractor_golden.py` (harness, to be created)

---

## 0. Scope, non-scope, and what this document is

### 0.1 What the Golden Set IS

A frozen, version-controlled set of (window, L3 snapshot, expected `ExtractionEnvelope`) tuples that the LLM Extractor must reproduce within a defined tolerance. It is the **regression gate** invoked by `bash scripts/ci.sh` on any PR that touches:

- the schema (`memory_extractor_schema.md` / `backend/heart/ss02_memory/extractor/types.py`),
- the prompt asset (`backend/heart/prompts/memory_extraction_v*.py`),
- the Resolver / Writer / cost guard (`backend/heart/ss02_memory/extractor/resolver.py` · `writer.py` · `cost_guard.py`),
- the live model snapshot (`MODEL` constant in the active prompt module).

Touching any of these without the gate going green is, by policy, a `chore: bump prompt_version + golden re-eval` PR — a single review unit, not two.

### 0.2 What the Golden Set is NOT

1. Not a calibration set. The `confidence ≤ 0.7 ⇒ FPR ≤ 5%` target is measured on a **separate**, larger eval set (planned, not in scope here). The golden set is a *gate*, not a *measurement* — its job is to fail loudly when behaviour regresses, not to estimate population statistics.
2. Not a benchmark for the underlying LLM. We measure deviation from a fixed Heart-product policy; we do not measure DeepSeek's general extraction skill.
3. Not the L4 promoter's regression set. L4 promotion is gated by `memory_promoter_rules.md` §7 tests. The cross-session cases here exist only to verify the *Resolver writes* that the Promoter will later read — see §1.3.
4. Not a CLI demo / soul drift / voice baseline. Those are separate fixtures owned by different specs (`soul_drift_regression.md`, `integration_test_pyramid.md`).

The golden set is the **only** artifact shared by the schema doc, the prompt doc, and the Resolver doc as their joint correctness contract.

---

## 1. Coverage matrix

### 1.1 Category counts and rationale

47 cases total. Distribution is **not uniform** — it is proportional to the joint (failure-mode prevalence × cost of being wrong). A bug in coreference is cheap (we miss a name); a bug in supersession is expensive (we keep believing the user lives in Beijing after they moved).

| # | Category | Cases | Why this count |
|---|---|---:|---|
| 1 | **Coreference** | 6 | 4 distinct pronoun classes (`她/他/它/那只`) × ~2 contexts (resolvable vs ambiguous) ≈ 6. Below 6, we cannot separate "model misses 她" from "model misses 它"; above 6, we start over-weighting cheap failures. |
| 2 | **Fragmentation (≥3 turns → 1 entity)** | 5 | The minimum to cover (2-attr, 3-attr) × (introduce-then-name, introduce-then-describe-then-name) × one "fragmentation with intervening unrelated turn" trap. Window size = 6 (per prompt §1), so 5 cases saturate the meaningful in-window combinatorics. |
| 3 | **Rhetoric** | 6 | The single highest false-positive class observed in v0 regex output. Six cases cover: 自嘲 (「我有病了哈哈」), 夸张 (「她真的会要了我的命」), 反讽承诺 (「我养你」), 比喻关系 (「我女朋友是我妈」), 网络流行语 (「破防了」), 边界正常陈述 (validates we do NOT over-suppress sincere disclosure). Six > five because the rhetoric/disclosure boundary is the single hardest call the LLM makes. |
| 4 | **Question** | 4 | Four shapes: direct ("我叫什么吗"), memory probe ("你还记得我妈生日吗"), tag question ("我说过吧"), embedded question inside disclosure ("我叫张三，对吧？"). Below 4, we cannot separate "model treats tag-questions as disclosure" (a known failure mode) from "model treats memory-probes as supersession" (a different known failure mode). |
| 5 | **Negation** | 4 | Four shapes: explicit negation with L3 prior (→ `soft_delete`), explicit negation without L3 prior (→ `dropped_signals`), partial negation ("我不喜欢咖啡 but 拿铁还行" → tests that `dislike` ≠ blanket `do_not_recall`), retraction in same turn ("我猫…啊不对我没养"). Floor at 4 because the negation × prior_value_id rule is the most error-prone `if/then` in the schema. |
| 6 | **Supersession** | 5 | Five shapes: identity supersession (age, residence, occupation), preference supersession (favorite color), relationship supersession (changed jobs), supersession with prior not in snapshot (→ falls back to `op=create`), supersession across a rhetoric trap. Five > four because we need to verify both "writes supersede when it should" AND "falls back to create when prior is missing" (a critical schema `if/then`). |
| 7 | **Plain disclosure** | 8 | Baseline category. Eight cases cover: (a) single attribute (name, age, occupation, hometown), (b) multi-attribute in one turn ("我叫张三，住北京，养只猫"), (c) preference disclosure ("我喜欢爵士"), (d) event disclosure ("我下个月结婚"). 8 is the largest single bucket because **most production windows are plain disclosure** — under-sampling here would let a recall regression hide. |
| 8 | **Sensitive** | 4 | Four cases sized to the **schema's actual contract**, which differs from the user-facing framing — see §1.2 for the resolution. Cases cover: health_condition (in-schema, marked sensitive in case metadata), 性取向 (out-of-schema → must drop with `reason=out_of_scope_attribute`), 政治倾向 (same), 宗教 (same). The split lets us assert two distinct contracts in one category. |
| 9 | **Adversarial / edge** | 5 | Five high-value traps that aggregate the above categories with one twist: code-switching CN+EN inside one turn, anaphora resolvable to one of two prior entities (the `他/她` collision case), repeated identical disclosure ("我叫张三" three times in one window → `mention_count` semantics), sarcasm masquerading as disclosure, third-party speech ("我妈说我应该吃药" — must NOT extract `(self, health_condition, 吃药)`). Five is the minimum that covers the failure modes our v0 regex never expressed. |
| | **Total** | **47** | Within user's 30–50 ask; close enough to 50 that the FPR-at-0.7 target measured here is statistically meaningful for the gate decision; below 50 so authoring + maintenance cost stays in budget. |

### 1.2 Resolving the "sensitive disclosure" framing vs. the v1.0.0 schema

The user's prompt asked for the sensitive category to produce `disclosure` outputs with `sensitive=True`. The shipped v1.0.0 schema (`memory_extractor_schema.md` §1) has **no `sensitive` field** on `ExtractionCandidate`, and the `attribute` enum **explicitly excludes** 性取向 / 政治倾向 / 宗教 (§2.2 "Intentionally out of scope: salary, religion, political_view, sexual_orientation"). The prompt (§1 R-rules) instructs the LLM to drop those into `dropped_signals[reason=out_of_scope_attribute]`.

Reconciliation — what the golden set actually encodes:

| Sub-case | What the user said | What the schema says | What the golden set encodes |
|---|---|---|---|
| 健康 ("我有抑郁症") | disclosure + `sensitive=True` | `(self, health_condition, "抑郁症", kind=disclosure, op=create)` — no `sensitive` field | Candidate with `attribute=health_condition`. **Case metadata** carries `sensitive: true` and `l4_promotion_eligible: false` (read by the Promoter-test harness, NOT by the LLM). |
| 性取向 | disclosure + `sensitive=True` | Out of `attribute` enum | `candidates=[]`. `dropped_signals=[{turn_id, raw_phrase, reason=out_of_scope_attribute}]`. Case metadata `sensitive: true`. |
| 政治倾向 | disclosure + `sensitive=True` | Out of `attribute` enum | Same as 性取向. |
| 宗教 | disclosure + `sensitive=True` | Out of `attribute` enum | Same as 性取向. |

**Why this split is correct, not a workaround**: the schema's exclusion was a deliberate privacy decision (`memory_extractor_schema.md` §2.2). If we extended the enum to admit 性取向 just to satisfy this golden set, we would silently legalise persistent storage of those categories — exactly what the schema doc forbade. The golden set must encode *the policy the schema enforces*, not the policy the prompt asked for.

If product later decides to add a consent-gated sexual_orientation attribute, that is a schema MAJOR bump (per `memory_extractor_schema.md` §4.1) and a separate review cycle; the golden set updates atomically with it.

### 1.3 Cross-session — handled as case pairs, not a bucket

The user listed "cross-session: 多次会话强化才晋升 L4" as the 7th problem category. It is intentionally NOT a count bucket because:

- The Extractor sees only one window. There is no envelope difference between "T0 in session A" and "T0 in session B" — both produce the same `(self, name, 张三, op=create)` candidate.
- Cross-session promotion is the **Promoter's** job (`memory_promoter_rules.md` §1.1 K4). Its regression is owned by `test_promoter.py`, not by this golden set.

What the golden set DOES contribute:

Two **paired adversarial cases** (`gc-adv-04a` / `gc-adv-04b`) re-use the *same fact* with different `session_id`s in the case metadata. The integration harness loads both and asserts:

1. Each individually produces the expected envelope.
2. After running both through the Resolver + Writer, `fact_nodes.mention_count >= 2` and `memory_audit_log` shows `COUNT(DISTINCT session_id) >= 2`.

That couples the golden set to the Promoter's K4 input without duplicating Promoter tests. The pair lives inside the adversarial bucket and counts toward its 5.

### 1.4 What the matrix deliberately does NOT cover

Listed so authors know not to add cases for these — they are owned elsewhere:

1. **Cross-window references** ("还记得上次我说的那个吗" pointing outside the window) — `memory_extractor_schema.md` §5 known limitation; encoded as `dropped_signals[insufficient_context]` but not a category here.
2. **L4 demotion** — Promoter test scope.
3. **Decay / forgetting affect** — `decay_engine.py` + `forgetting_affect.py` own this; their golden inputs are L3 rows, not conversation windows.
4. **Multilingual code-switch beyond CN+EN** — language-agnostic per schema §5; we test CN+EN only because that's the early-product language pair.
5. **Numeric normalization** ("二十多岁") — schema does not promise normalization; testing it would over-specify behaviour.

A new sub-category proposal must clear two bars: (a) it surfaces a failure mode that the existing 47 cases cannot distinguish, AND (b) it does not duplicate a Promoter / Consolidator / Reconstructor test scope.

---

## 2. Authoring guidelines

### 2.1 Who can contribute

| Role | May propose new cases? | May edit existing `expected_envelope`? | May edit case `window` text? | May approve merge? |
|---|---|---|---|---|
| Any engineer | ✅ via PR | ❌ (must go through reviewer process §5) | ❌ (frozen after merge) | ❌ |
| SS02 maintainer (CODEOWNERS) | ✅ | ✅ via §5 process | ❌ | ✅ (non-sensitive cases) |
| Privacy reviewer | ✅ for sensitive bucket | ✅ for sensitive bucket | ❌ | ✅ (sensitive cases require sign-off) |
| Product owner | ✅ for plain disclosure bucket | ❌ | ❌ | ❌ (review-only) |
| HUMAN (project lead) | ✅ | ✅ | ✅ (with rationale) | ✅ (any case) |

CODEOWNERS rule (to be added in `.github/CODEOWNERS`):

```
backend/tests/golden/memory_extractor/         @ss02-maintainers
backend/tests/golden/memory_extractor/gc-sens-*  @ss02-maintainers @privacy-reviewer
```

### 2.2 Authoring checklist (must pass before opening PR)

Lifted from how the schema doc and prompt doc were authored; mechanical, not negotiable.

1. **Schema-conformance dry-run**: `python -m heart.ss02_memory.extractor.types --validate gc-XXX.yaml` must exit 0. Catches forgetting required fields, misspelled enum values, or `source_turns` referencing turn IDs outside `window.turn_ids`.
2. **Category claim matches content**: a case under `gc-rhet-*` whose `expected_envelope` has zero `kind=rhetoric` candidates is a sign the author miscategorised — reviewer rejects.
3. **`reasoning` field carries source-turn citation** in every candidate (the same rule the LLM is held to). If we cannot author a citation, the LLM cannot be expected to produce one.
4. **No persona leakage**: window text MUST NOT contain `心屿`, `老铁`, or any SS01 anchor token. The Extractor never sees the persona; if a golden case contains the persona, we are testing the wrong thing.
5. **No PII**: window text uses placeholder names (`张三`, `小明`, `Alex`) and synthetic locations. Real production fragments — even ones the contributor "remembers from a chat" — are forbidden. Privacy reviewer enforces.
6. **One window = one extraction call**: do not stuff two windows into one case. Cross-window state lives in `l3_snapshot`, not in extra turns.
7. **Notes field justifies the expected envelope, not the category**: `notes` must explain *why this envelope is the correct one for this window*, not *which bucket this case belongs to* (the case_id already encodes that).

### 2.3 Review process

Two-reviewer rule, asymmetric:

- **Non-sensitive case**: 1× SS02 maintainer approval + green schema-validation CI step. Merge.
- **Sensitive case (`gc-sens-*`)**: 1× SS02 maintainer + 1× privacy reviewer + green CI. Merge.
- **Edit to existing case**: routed through §5 false-positive process regardless of bucket. No silent edits.

Review focus, in priority order:

1. Does the `window` text plausibly occur in production conversation?
2. Does `expected_envelope` agree with the schema doc's edge-case table (`memory_extractor_schema.md` §3)?
3. Is the rationale in `notes` independently derivable from the prompt's rules (R1–R9)? If reviewer disagrees with the envelope, both reviewer and author must show which R-rule supports their reading.
4. Does the case discriminate something the existing 47 don't? (Optional for new cases beyond 47; the bar rises sharply past 50.)

Pull-request title convention: `test(golden/memory): add gc-<cat>-<seq> — <one-line>`. Subject template prevents drive-by additions from sneaking in without category review.

### 2.4 Sunset and pruning

Golden cases are durable but not immortal. A case is a candidate for removal when:

- Two or more cases in the same bucket exercise the identical R-rule combination (audit job flags duplicates by hashing `(category, kind, operation, attribute set)` across cases).
- The model can no longer fail the case in any plausible regression (sustained 100% pass across ≥6 months of schema/prompt changes). Such cases stay, but get marked `priority=smoke` and are excluded from the FPR-at-0.7 measurement to avoid biasing it.
- A schema MAJOR bump invalidates the case shape. Then the case is rewritten alongside the schema bump in the same PR, not silently dropped.

Pruning is reviewer-only via the §5 process; authors cannot delete cases.

---

## 3. File format

### 3.1 Layout

```
backend/tests/golden/memory_extractor/
├── _manifest.yaml                       # index; CI-generated, do not hand-edit
├── _schema/
│   └── golden_case.schema.json          # JSON Schema for each case file
├── gc-cor-01.yaml … gc-cor-06.yaml      # Coreference (6)
├── gc-frag-01.yaml … gc-frag-05.yaml    # Fragmentation (5)
├── gc-rhet-01.yaml … gc-rhet-06.yaml    # Rhetoric (6)
├── gc-ques-01.yaml … gc-ques-04.yaml    # Question (4)
├── gc-neg-01.yaml … gc-neg-04.yaml      # Negation (4)
├── gc-sup-01.yaml … gc-sup-05.yaml      # Supersession (5)
├── gc-plain-01.yaml … gc-plain-08.yaml  # Plain disclosure (8)
├── gc-sens-01.yaml … gc-sens-04.yaml    # Sensitive (4)
└── gc-adv-01.yaml … gc-adv-05.yaml      # Adversarial / edge (5)
```

Naming: `gc-<3-letter-bucket>-<2-digit-seq>.yaml`. The 2-digit cap (max 99) is intentional — past 99 within a bucket is a strong signal we are testing a sub-class that deserves its own bucket.

### 3.2 Why YAML per case, not JSONL

Considered options:

| Option | Pro | Con | Verdict |
|---|---|---|---|
| One YAML file per case | Human-readable multi-line CJK windows; one git history per case; CODEOWNERS can scope by file glob | 47 files in one directory | ✅ chosen |
| Single JSONL file | Compact; trivial streaming | Diffing 47 escaped-CJK lines is painful; merge conflicts touch every change; no per-case CODEOWNERS | ❌ |
| One JSON file per case | Same per-file benefits as YAML | CJK windows + JSON escaping → unreadable diffs | ❌ |
| Single YAML file | One git scroll | Same merge-conflict problem as JSONL; impossible to assign per-case ownership | ❌ |

Per-case YAML matches the precedent set by `soul_specs/{character}/golden_dialogues/gd-*.yaml` (referenced in `soul_drift_regression.md` §2.1). Reusing the convention costs zero and keeps reviewers in familiar territory.

### 3.3 Per-case schema (JSON Schema, draft-07)

The full schema lives at `_schema/golden_case.schema.json`. Below is the canonical shape; comments are non-normative.

```yaml
# gc-cor-01.yaml — illustrative; not a real case
case_id: "gc-cor-01"                          # MUST match filename stem
category: "coreference"                       # one of: coreference, fragmentation,
                                              #   rhetoric, question, negation,
                                              #   supersession, plain_disclosure,
                                              #   sensitive, adversarial
schema_version: "1.0.0"                       # tracks memory_extractor_schema.md
case_format_version: "1.0.0"                  # tracks THIS doc
priority: "gate"                              # gate | smoke
                                              #   gate  = PR blocker
                                              #   smoke = informational only (see §2.4)

# ---------- INPUT TO THE EXTRACTOR ----------
window:
  - turn_id: 10
    speaker: "user"
    ts: "2026-06-18T10:00:00Z"
    text: "我家有只猫"
  - turn_id: 11
    speaker: "assistant"
    ts: "2026-06-18T10:00:05Z"
    text: "哦真的？"
  - turn_id: 12
    speaker: "user"
    ts: "2026-06-18T10:00:20Z"
    text: "嗯，她叫妙妙，灰白色的"

l3_snapshot: []                               # list of L3 facts the prompt block
                                              # `#### L3 snapshot` will render

hints: []                                     # list of regex-hint dicts, optional

# ---------- METADATA (read by harness, NOT by the LLM) ----------
metadata:
  session_id: "11111111-1111-4111-8111-111111111100"
  user_id: "synthetic-user-01"
  character_id: "synthetic-char-01"
  sensitive: false                            # case authored-as-sensitive flag (§1.2)
  l4_promotion_eligible: true                 # input to paired Promoter test, if any
  paired_with: null                           # `gc-adv-04b` for cross-session pairs

# ---------- EXPECTED OUTPUT ----------
expected_envelope:
  extractor_run_id: "11111111-1111-4111-8111-111111111111"
  model: "deepseek-v4-flash"
  prompt_version: "1.0.0"
  schema_version: "1.0.0"
  window:
    turn_ids: [10, 11, 12]
    size: 3
  candidates:
    - entity_type: "pet"
      attribute: "name"
      value: "妙妙"
      entity_ref: "cat#1"
      source_turns: [10, 12]
      confidence: 0.92
      kind: "disclosure"
      operation: "create"
      reasoning: "T10 引入这只猫，T12 给出名字'妙妙'，'她'指代 T10 的猫"
    - entity_type: "pet"
      attribute: "color"
      value: "灰白色"
      entity_ref: "cat#1"
      source_turns: [10, 12]
      confidence: 0.85
      kind: "disclosure"
      operation: "create"
      reasoning: "T12 描述同一只猫（cat#1，T10 引入）是灰白色"
  dropped_signals: []

# ---------- OPTIONAL ACCEPTED ALTERNATES (§5.3) ----------
valid_alternates: []                          # populated by reviewer when LLM has
                                              # produced a different but defensible
                                              # envelope; each entry has the same
                                              # shape as `expected_envelope` plus a
                                              # `rationale_for_acceptance` string.

# ---------- NOTES ----------
notes: |
  本例考察「她」必须解析到 T10 的猫。两个 candidate 共享 entity_ref="cat#1"，
  source_turns 都包含 T10（实体引入 turn）。color 的 confidence 略低于 name
  因为 "灰白色" 是描述而非命名。

  R-rule justification: R3 (共指), R4 (跨 turn 拼装).
```

### 3.4 Required vs. optional fields

| Field | Required | Notes |
|---|---|---|
| `case_id` | ✅ | Must equal filename stem. |
| `category` | ✅ | Closed enum; must match the 9 buckets. |
| `schema_version` | ✅ | When the schema bumps MAJOR, every case is re-stamped in the same PR (§2.4). |
| `case_format_version` | ✅ | This doc's version. MINOR bump for additive metadata, MAJOR for breaking. |
| `priority` | ✅ | `gate` blocks PR; `smoke` does not. Default `gate`. |
| `window` | ✅ | ≥1 turn, ≤6 turns (matches prompt's window size cap). |
| `l3_snapshot` | ✅ | Empty list is valid. |
| `hints` | ✅ | Empty list is valid; omitting them tests `mode=llm` rather than `mode=dual`. |
| `metadata.session_id` | ✅ | Used by the harness even when the LLM does not see it. |
| `metadata.sensitive` | ✅ | Defaults to `false`; `true` triggers privacy-reviewer requirement (§2.3). |
| `metadata.paired_with` | ⬜ | Required only when the case is half of a cross-session pair. |
| `expected_envelope` | ✅ | Must itself validate against `memory_extractor_schema.md` v1.0.0 JSON Schema. |
| `valid_alternates` | ⬜ | Empty list initially; reviewer appends through §5. |
| `notes` | ✅ | ≥ 1 sentence; must cite at least one R-rule from the prompt doc. |

### 3.5 Manifest

`_manifest.yaml` is regenerated by `scripts/regen_golden_manifest.py` (a tiny utility, to be created) on every CI run; PRs that hand-edit it are rejected. Shape:

```yaml
generated_at: "2026-06-19T14:00:00Z"
case_format_version: "1.0.0"
schema_version: "1.0.0"
counts:
  coreference: 6
  fragmentation: 5
  rhetoric: 6
  question: 4
  negation: 4
  supersession: 5
  plain_disclosure: 8
  sensitive: 4
  adversarial: 5
  total: 47
cases:
  - case_id: "gc-cor-01"
    category: "coreference"
    priority: "gate"
    paired_with: null
    sensitive: false
  # …
```

The harness loads `_manifest.yaml`, asserts the counts match §1.1, then dispatches each case file.

---

## 4. Scoring criteria

### 4.1 Why per-field tiers, not exact match

Three independently sufficient reasons:

1. **The LLM is non-deterministic in tail bits even at `temperature=0`** (token-tie breaks, FP rounding). A `reasoning` string of `"T10 引入这只猫，T12 给出名字"` and `"T12 给出名字'妙妙'，T10 引入这只猫"` should both pass. Exact-match would reject both half the time and pretend it caught a regression.
2. **Some fields ARE the policy** (e.g., `kind`, `operation`, `prior_value_id` presence). These must be exact, or we are testing nothing. Subset/fuzzy match here would silently let regressions through.
3. **Some fields are *suggested* by the LLM but the Resolver re-decides** (e.g., `operation=create` may be reasonably downgraded to a reinforce). We do not want to gate the gate on a value the production code overrides anyway.

The tier system below maps each field to its actual contract surface.

### 4.2 Field tiers

`HARD` = exact match required. `SEMI` = match within a defined tolerance. `SOFT` = scored, not blocking.

| Field | Tier | Contract |
|---|---|---|
| `extractor_run_id`, `model`, `prompt_version`, `schema_version` | n/a | Mechanically rewritten by the harness on both sides before comparison — these echo run metadata and would otherwise always mismatch. |
| `window.turn_ids` | HARD | The set must equal the case's window turn IDs. Set equality, not list equality (LLM order MAY differ; we enforce order at schema level via `description` but accept either at scoring level). |
| `window.size` | HARD | Must equal `len(window.turn_ids)`. Caught by JSON Schema validator first; scorer only sees envelopes that already passed. |
| Per-candidate `entity_type` | HARD | Closed enum; wrong value is a real bug. |
| Per-candidate `attribute` | HARD | Same. |
| Per-candidate `kind` | HARD | Misclassifying `rhetoric` as `disclosure` is the single failure mode this golden set exists to catch. |
| Per-candidate `operation` | HARD | Same logic. |
| Per-candidate `prior_value_id` | HARD | Either both expected and actual are `null`, or both equal the same UUID. The schema's `if/then` already constrains this; the scorer asserts what the schema enforces. |
| Per-candidate `value` | SEMI | Normalise via: NFKC unicode, strip surrounding quotes, collapse runs of whitespace, lower-case **only for ASCII characters**. Match on the normalised form. Rationale: "妙妙" vs "「妙妙」" vs "妙妙 " should all match; "30" vs "30岁" should NOT (the schema says no normalization — the LLM must preserve raw form). |
| Per-candidate `entity_ref` | SEMI | Coalescence-preserving: scorer treats `entity_ref` as a *clustering* label, not a string identity. Two candidates share an entity_ref iff the expected candidates with the same `(entity_type, role_position)` did. Concretely: build an equivalence relation on the actual candidates from `entity_ref` co-occurrence, compare to the equivalence relation on expected candidates. `cat#1` vs `cat-A` is fine; collapsing two distinct expected entities into one is a fail. |
| Per-candidate `source_turns` | SEMI | Set equality with one allowance: the actual set may be a **superset** of the expected set only when every extra ID is the entity-introduction turn for the candidate's `entity_ref` (i.e., the LLM cited more evidence than required, never less). Missing any expected ID is a fail. |
| Per-candidate `confidence` | SOFT | `|actual − expected| ≤ 0.15` is a pass for scoring; outside ±0.15 logs a `confidence_drift` warning but does not fail. Confidence calibration lives on the (separate) eval set, not here. |
| Per-candidate `reasoning` | SOFT-with-floor | The text is not compared. We assert one HARD property: the reasoning string contains at least one of the candidate's `source_turns` ids in the form `T<id>` or `turn <id>`. Failing the citation check fails the case (it's a prompt R1 violation). |
| `dropped_signals[*].turn_id` | HARD | Per-drop the turn id must match an expected drop's turn id. |
| `dropped_signals[*].reason` | HARD | Closed enum; wrong reason category is the failure mode `dropped_signals` was added to catch. |
| `dropped_signals[*].raw_phrase` | SEMI | Same normalisation as `value`. |

### 4.3 Candidate-level matching

A window may produce multiple candidates. The scorer:

1. Builds a bipartite graph between expected and actual candidates. Edge weight = HARD-fields-equal count (max 5: entity_type, attribute, kind, operation, prior_value_id-presence-match). Edges with weight < 5 are discarded.
2. Solves a **greedy maximum cardinality matching** (not Hungarian; the candidate counts are ≤ 32 — schema cap — so greedy on weight-tied edges with stable tie-break by `attribute` enum order is sufficient and deterministic).
3. For each matched pair, runs the SEMI/SOFT comparators (§4.2). All SEMI checks must pass; SOFT failures count toward a per-case soft-score that surfaces in the report but does not gate.
4. Unmatched expected candidates → false negatives (recall loss).
5. Unmatched actual candidates → false positives (precision loss).

Dropped signals are matched separately on `(turn_id, reason)`. Same FN/FP accounting.

### 4.4 Per-case verdicts

| Verdict | Definition |
|---|---|
| **PASS** | All HARD fields match. All SEMI fields match. No unmatched expected candidates. No unmatched expected dropped_signals. Unmatched *actual* extras are allowed only when `valid_alternates` covers them (§5.3). |
| **PASS_WITH_DRIFT** | PASS plus one or more SOFT-field warnings (e.g., confidence drift > 0.15 but ≤ 0.30). Logged with diff, does not fail CI. |
| **FAIL_HARD** | Any HARD mismatch, OR unmatched expected candidate, OR unmatched expected drop. Fails CI. |
| **FAIL_SEMI** | All HARD match, but any SEMI mismatch. Fails CI. Distinguished from FAIL_HARD because it is the more common diagnostic class and triggers the §5 review path. |
| **FAIL_ALTERNATE_CLAIM** | Actual envelope does not match `expected_envelope` but the actual fields all match HARD/SEMI rules against `expected_envelope`. (This is the "LLM produced something different but plausibly correct" case.) Routed to §5 review queue; in CI it fails until a reviewer decides. |

### 4.5 Aggregate metrics

Run-level, surfaced in the CI summary:

```
Golden run summary (model=deepseek-v4-flash, prompt_version=1.0.0)
  per-case:    PASS  PASS_WITH_DRIFT  FAIL_HARD  FAIL_SEMI  FAIL_ALTERNATE_CLAIM
                42                3          1          1                    0
  per-category recall / precision (candidates):
    coreference:        recall 0.96   precision 0.94
    fragmentation:      recall 1.00   precision 0.97
    rhetoric:           recall 0.94   precision 0.92
    question:           recall 1.00   precision 1.00
    negation:           recall 0.97   precision 0.95
    supersession:       recall 0.95   precision 0.93
    plain_disclosure:   recall 0.99   precision 0.98
    sensitive:          recall 1.00   precision 1.00
    adversarial:        recall 0.90   precision 0.88
  FPR @ confidence ≥ 0.70: 4.2%  (target ≤ 5.0%)
  dropped_signals reason distribution: …
```

Gate rule: **CI fails if any `FAIL_HARD` or `FAIL_SEMI` case exists, OR per-category recall drops below the previous run's recall by more than 5 percentage points, OR FPR@0.70 exceeds 5.0%.**

The previous-run baseline lives in `backend/tests/golden/memory_extractor/_baseline.yaml` (a small JSON with category recalls and overall FPR). It is committed; updates go through §5.

### 4.6 What the scorer does NOT do

Said up front so debates do not re-open:

1. No semantic similarity scoring on `reasoning` text. Embeddings drift across model versions and would make the gate non-reproducible.
2. No "fuzzy match" on `attribute` or `kind`. These are closed enums; "fuzzy" here means "we accept bugs".
3. No counting tokens to penalise verbose envelopes. That's a cost concern, owned by `cost_guard.py`, not by the regression gate.
4. No A/B between model versions inside the gate. Model-snapshot bumps are PR'd separately (`chore: bump deepseek-v4-flash to 2026-MM-DD snapshot`) and re-run the same gate.

---

## 5. False-positive handling — when the LLM is "also right"

### 5.1 What this section addresses

The scoring rules in §4 will sometimes flag a `FAIL_ALTERNATE_CLAIM` (or, less cleanly, a `FAIL_SEMI` that on inspection turns out to be a defensible LLM reading). Concretely:

- The LLM emits `(self, hobby, "周杰伦的歌")` while the golden has `(self, hobby, "听周杰伦")`. Both honor R-rule 3, both honor the schema. Which is "right"?
- The LLM splits a single fragmentation case into 3 candidates instead of 2 (separate `color` and `breed` candidates instead of one). Both are valid per `memory_extractor_schema.md` §3.
- The LLM emits `kind=disclosure` for a borderline case the golden tagged `kind=rhetoric`. The author may have been over-conservative.

These are NOT bugs to silence. They are also NOT updates to merge silently. Both shortcuts have caused production drift in v0; the process below is what prevents both.

### 5.2 Review queue

When CI reports `FAIL_ALTERNATE_CLAIM`, OR a reviewer manually re-classifies a `FAIL_SEMI` as `FAIL_ALTERNATE_CLAIM` after looking at the diff, the case is added to the review queue:

```
backend/tests/golden/memory_extractor/_review_queue/
└── 2026-06-19_gc-rhet-03__hobby_phrasing.yaml
```

Each queue entry contains:

```yaml
queue_id: "2026-06-19_gc-rhet-03__hobby_phrasing"
case_id: "gc-rhet-03"
detected_at: "2026-06-19T14:00:00Z"
detected_in_ci_run: "<CI run URL>"
model: "deepseek-v4-flash"
prompt_version: "1.0.0"
diff_summary: |
  candidate[0].value:   expected="听周杰伦"  actual="周杰伦的歌"
  candidate[0].source_turns: expected=[5]  actual=[4, 5]
reviewer_assigned: null
status: "pending"     # pending | resolved_update | resolved_keep | resolved_alternate
resolution_rationale: null
resolution_pr: null
```

Queue entries are created by the harness on `FAIL_ALTERNATE_CLAIM`; they are deleted only when the resolution PR merges. A queue that accumulates faster than it drains is a leading indicator of prompt rot — surfaced as a CI warning when `len(_review_queue) > 5`.

### 5.3 Reviewer decision tree

Each queue entry resolves to exactly one of three outcomes. Reviewer (an SS02 maintainer, or a privacy reviewer for sensitive cases) walks the tree below and records the choice in `resolution_rationale`.

```
                         ┌─ A) Update expected ──────────┐
                         │   ↑ Golden was authored wrong,│
                         │     or LLM/policy improved    │
                         │     past the old answer.      │
   Is the actual envelope│                               │
   correct under         │   Action: PR edits            │
   memory_extractor_     │   `expected_envelope` in the  │
   prompt.md R-rules     │   case file. Old expected is  │
   AND                   │   moved to `notes` as         │
   memory_extractor_     │   "previously expected:" so   │
   schema.md edge cases? │   git blame is informative.   │
                         │                               │
                  ┌─ Yes ┤                               │
                  │      │                               │
                  │      └─ B) Add to valid_alternates ──┤
                  │          ↑ BOTH the original         │
                  │            expected AND the actual   │
                  │            are defensible; the case  │
                  │            has multiple right        │
                  │            answers.                  │
                  │                                      │
                  │          Action: append actual       │
                  │          envelope to                 │
                  │          `valid_alternates` with     │
                  │          `rationale_for_acceptance`. │
                  │          §4.4 PASS rules then accept │
                  │          either.                     │
                  │                                      │
   reviewer ──────┤                                      │
                  │                                      │
                  └─ No ── C) Keep expected ─────────────┘
                              ↑ LLM is wrong. The
                                divergence indicates a
                                prompt or schema bug.

                              Action: open a fix PR
                              (prompt PATCH, prompt MINOR,
                              or schema MINOR — whichever
                              the diagnosis demands).
                              Queue entry stays "pending"
                              until the fix PR merges and
                              CI is green again.
```

### 5.4 When to pick A vs. B

- **Pick A (update expected)** when the LLM's answer is *strictly* better than the original: more precise wording, more accurate source-turn citation, correct application of an R-rule the original author misapplied. Single answer is correct.
- **Pick B (add valid_alternate)** when both answers are *equally* correct under the rules. Both `(self, hobby, "听周杰伦")` and `(self, hobby, "周杰伦的歌")` would be examples — the schema does not promise normalization, so either raw form satisfies the contract.

The bias is toward A, not B. `valid_alternates` is a debt — every alternate weakens the gate by widening "accepted" outputs. A queue entry that the reviewer wants to resolve B should also be a queue entry the reviewer would feel uncomfortable saying "no, only the original is right" about. If the discomfort is small, pick A.

Hard limit: a single case may carry at most **2** `valid_alternates`. A case that the LLM solves three different defensible ways is a case whose `expected_envelope` was specified too tightly — restructure the case (split into two, or relax the discriminating field) rather than adding a third alternate.

### 5.5 Privileged sensitive-case path

A `gc-sens-*` case appearing in the review queue requires:

- Both an SS02 maintainer AND a privacy reviewer signing off.
- Default bias toward **C (keep expected)** even when actual is defensible. Sensitive disclosures are the one place we are willing to under-recall to protect the user; the gate is allowed to be conservative.
- `valid_alternates` is **forbidden** for sensitive cases. There is exactly one right answer per sensitive case, by policy.

### 5.6 Process invariants

1. **No case edit lands outside the queue process.** A PR that edits `expected_envelope` without a matching `_review_queue/*.yaml` entry referenced in the PR body is rejected on sight, even from a CODEOWNER.
2. **The queue is append-only until resolution.** Reviewers do not edit queue entries to "fix the diff" — they create the resolution PR and let the queue entry be deleted by that PR.
3. **Queue depth is a CI metric, not a chore.** Sustained queue depth ≥ 5 across two consecutive runs triggers an automatic issue with title `golden review queue backlog`, assigned to SS02 maintainers. Backlog is treated as a prompt-rot signal, not a sleep-on-it backlog.
4. **`_baseline.yaml` updates only via §5.** Per-category recall numbers in `_baseline.yaml` (§4.5) may only be lowered by a PR that closes one or more queue entries with C (keep expected) outcomes and explains in the PR body why the recall drop is intentional. They may be raised at any time.
5. **Annual audit.** Once per quarter (post-Phase 8), HUMAN reviews all `valid_alternates` entries accumulated over the period and decides whether each should be collapsed (pick one as canonical) or kept. Without this, alternates accrete and the gate weakens silently.

---

## 6. Acceptance criteria for v1.0.0 of this design

Before this doc and the accompanying fixtures may be tagged `v1.0.0`:

- [ ] 47 case files committed under `backend/tests/golden/memory_extractor/`, matching the §1.1 counts exactly.
- [ ] `_schema/golden_case.schema.json` committed; every case file validates against it.
- [ ] Every `expected_envelope` validates against the v1.0.0 schema JSON Schema (`memory_extractor_schema.md` §1).
- [ ] Each case's `notes` cites at least one R-rule from `memory_extractor_prompt.md`.
- [ ] The integration harness `backend/tests/integration/test_memory_extractor_golden.py` exists and implements §4 scoring.
- [ ] `bash scripts/ci.sh integration-tests` runs the harness against `deepseek-v4-flash` with the v1.0.0 prompt and produces a PASS verdict for all 47 cases.
- [ ] First `_baseline.yaml` checked in, with category recalls measured on the green run.
- [ ] `.github/CODEOWNERS` rules per §2.1 in place.
- [ ] One round of the §5 review process exercised end-to-end on a synthetic alternate-claim queue entry (proves the workflow works before we depend on it).

After ship, this design enters MINOR-bump territory only — every change to scoring rules, file format, or coverage matrix is `case_format_version` MINOR bump + paired test update. A MAJOR bump of this doc requires HUMAN sign-off because it invalidates every case file on disk.

---

## 7. Open questions for executor

Recorded so the implementer does not re-derive them:

1. **Bipartite matcher tie-break by `attribute` enum order**: §4.3 commits to "stable tie-break by attribute enum order". The enum order in the schema is alphabetic-ish; if the matcher's behaviour depends on enum order in ways that surprise reviewers, switch to **case_id-string** tie-break which is fully deterministic and visible in error messages.
2. **`metadata.session_id` storage**: pgsql UUIDs in the audit log expect a string; YAML coerces unquoted hex sequences to numbers in pathological cases. Implementer should quote all UUID strings in case files and add a schema-validator rule enforcing the format.
3. **Where the harness gets `extractor_run_id`**: the case file fixes a known UUID (e.g., `1111…111`) but the runtime in production assigns one per request. The harness MUST overwrite both sides of the comparison with the same value (the schema field is HARD on equality of run-metadata fields would otherwise always fail). Implemented as: harness assigns a fresh UUID per case run, injects it into the prompt's run-metadata block, and rewrites the expected envelope's `extractor_run_id` to the same value before scoring.
4. **CI runtime budget**: 47 cases × ~2.5s/call ≈ 2 min of wall-clock against DeepSeek. Inside `scripts/ci.sh integration-tests` (which is opt-in) — fine. If the gate gets promoted into the default `unit-tests` lane (e.g., via a cassette-recorded fake LLM), the harness must support a `--replay` flag against pre-recorded envelopes. Cassettes live at `backend/tests/golden/memory_extractor/_cassettes/` — same review process as the cases themselves.
5. **Cross-session pair execution order**: §1.3 implies `gc-adv-04a` runs before `gc-adv-04b`. The harness must enforce this even when pytest randomises test order — wrap paired cases in a single test function that runs both sequentially.
6. **What happens when DeepSeek deprecates `v4-flash`**: model snapshot ID lives in `prompt_version` indirectly (the prompt asset's `MODEL` constant). A new model is a prompt MAJOR bump per `memory_extractor_prompt.md` §4.2 — and that bump re-runs the gate. Nothing in this doc needs to change.

---

## Approval

| Date | Reviewer | Role | Version reviewed | Notes |
|---|---|---|---|---|
| 2026-06-20 | HUMAN | Project Lead | 1.0.0 | approved as-is |
