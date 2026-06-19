# SS02 Memory LLM Extractor — StructuredOutput Schema

**Date**: 2026-06-19
**Author**: 心屿团队
**Status**: 🟡 Design (pre-implementation)
**Spec refs**: `runtime_specs/02_memory_runtime.md` §3.4 (Encoding Pipeline) · §6.7 (Reconciliation) · §10.2 (PG Schema)
**Code refs**: `backend/heart/ss02_memory/models.py` (`MemoryExtractionQueue`, `MemoryAuditLog`, `FactNode`) · `backend/heart/ss02_memory/mode.py` (regex / llm / dual switch)

---

## 0. Scope and non-scope

This document defines the **contract between the LLM Extractor and the downstream Resolver**, expressed as a JSON Schema (draft-07) used to enforce StructuredOutput on the extraction call.

- **In scope**: the wire format the LLM emits, the enum closure, the audit envelope, the versioning rules.
- **Not in scope**:
  - the extraction prompt text (lives in `backend/heart/prompts/`, versioned via `prompt_version`),
  - Resolver decision logic (separate doc),
  - Writer / L3 row construction (already constrained by `FactNode` + `MemoryAuditLog`).

The schema is the **only** thing both sides agree on. Everything else is replaceable.

The extractor is the LLM half of the dual-track encoder per §3.4. It is gated by `MEMORY_EXTRACTOR_MODE ∈ {regex, llm, dual}` (see `mode.py`). This schema applies whenever the LLM half runs — i.e. mode ∈ {llm, dual}.

---

## 1. Schema (formal, JSON Schema draft-07, copy-pasteable)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://heart.internal/schemas/ss02/memory_extractor/v1.0.0.json",
  "title": "SS02MemoryExtractionEnvelope",
  "description": "Top-level envelope emitted by the LLM Memory Extractor for a single extraction run over a fixed conversation window. Consumed by the Resolver which projects candidates into L3 FactNode writes via the audit log.",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "extractor_run_id",
    "model",
    "prompt_version",
    "schema_version",
    "window",
    "candidates",
    "dropped_signals"
  ],
  "properties": {
    "extractor_run_id": {
      "type": "string",
      "format": "uuid",
      "description": "UUIDv4 tying this envelope to memory_extraction_queue.extractor_run_id and memory_audit_log.extractor_run_id for cross-table joining."
    },
    "model": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "description": "Provider model identifier, e.g. 'deepseek-v4-flash'. Recorded verbatim — provider+id, not a friendly alias."
    },
    "prompt_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "SemVer of the extraction prompt asset. Locked once shipped — see §4."
    },
    "schema_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "SemVer of THIS schema document. Must match the $id MAJOR.MINOR."
    },
    "window": {
      "type": "object",
      "additionalProperties": false,
      "required": ["turn_ids", "size"],
      "properties": {
        "turn_ids": {
          "type": "array",
          "items": { "type": "integer", "minimum": 0 },
          "minItems": 1,
          "maxItems": 64,
          "description": "The exact turn IDs fed to the LLM, in chronological order. Audit anchor: 'what did the LLM see?'"
        },
        "size": {
          "type": "integer",
          "minimum": 1,
          "maximum": 64,
          "description": "len(turn_ids). Redundant on purpose — catches truncation bugs at deserialize time."
        }
      }
    },
    "candidates": {
      "type": "array",
      "maxItems": 32,
      "items": { "$ref": "#/definitions/ExtractionCandidate" },
      "description": "Candidate facts (and rejections that the LLM still wants to surface as candidates with kind != disclosure). Resolver decides what to write. Empty array is valid — uneventful windows extract nothing."
    },
    "dropped_signals": {
      "type": "array",
      "maxItems": 32,
      "items": { "$ref": "#/definitions/DroppedSignal" },
      "description": "Phrases the LLM RECOGNIZED as potential facts but chose NOT to surface even as a kind!=disclosure candidate. Audit-only; never reaches the Writer. See §2.4."
    }
  },
  "definitions": {
    "ExtractionCandidate": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "entity_type",
        "attribute",
        "value",
        "source_turns",
        "confidence",
        "kind",
        "operation",
        "reasoning"
      ],
      "properties": {
        "entity_type": {
          "type": "string",
          "enum": [
            "self",
            "pet",
            "family",
            "friend",
            "colleague",
            "location",
            "possession",
            "preference",
            "event",
            "other"
          ],
          "description": "WHO/WHAT this fact is about. See §2.1 for closure rationale."
        },
        "attribute": {
          "type": "string",
          "enum": [
            "name",
            "nickname",
            "age",
            "color",
            "breed",
            "occupation",
            "relation",
            "location_residence",
            "location_origin",
            "hobby",
            "dislike",
            "health_condition",
            "birthday",
            "anniversary",
            "other"
          ],
          "description": "WHICH PROPERTY of the entity. Maps 1:1 onto memory_audit_log.attribute (VARCHAR 50). See §2.2."
        },
        "value": {
          "type": "string",
          "minLength": 1,
          "maxLength": 500,
          "description": "The literal value. Raw user-language string (e.g. '妙妙', '北京', '蓝色'). NO normalization here — Resolver normalizes."
        },
        "entity_ref": {
          "type": ["string", "null"],
          "maxLength": 100,
          "description": "OPTIONAL stable handle the LLM assigns within this envelope for coreference (e.g. 'cat#1', 'mom'). Lets the Resolver coalesce three candidates onto the same L3 row. NOT a DB id. Stable WITHIN the envelope only."
        },
        "prior_value_id": {
          "type": ["string", "null"],
          "format": "uuid",
          "description": "REQUIRED when operation ∈ {supersede, soft_delete}. UUID of the L3 fact_nodes row being replaced/marked do_not_recall. NULL otherwise. The LLM gets candidate prior IDs from the L3 snapshot passed in the prompt; if it cannot ground the supersession to a specific row, it MUST emit operation=create and let the Resolver detect the contradiction."
        },
        "source_turns": {
          "type": "array",
          "items": { "type": "integer", "minimum": 0 },
          "minItems": 1,
          "maxItems": 16,
          "uniqueItems": true,
          "description": "Turn IDs (NOT array indexes into the window). Subset of envelope.window.turn_ids. Validator MUST reject candidates whose source_turns escape the window."
        },
        "confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "LLM self-reported confidence. Calibration target: at threshold 0.7 the false-positive rate should be ≤ 5% on the golden set (acceptance, not contract)."
        },
        "kind": {
          "type": "string",
          "enum": ["disclosure", "rhetoric", "question", "negation", "hypothetical"],
          "description": "The speech act. Carried on the candidate, not as a pre-filter. See §2.3."
        },
        "operation": {
          "type": "string",
          "enum": ["create", "update", "supersede", "soft_delete"],
          "description": "LLM's suggested write. Resolver MAY override (e.g. demote create → reinforce when L3 already has the row). Never includes hard delete — project policy is logical delete only."
        },
        "reasoning": {
          "type": "string",
          "minLength": 1,
          "maxLength": 200,
          "description": "≤ 200 chars. MUST name at least one turn id from source_turns. Required, not optional — see §2.5."
        }
      },
      "allOf": [
        {
          "if": { "properties": { "operation": { "enum": ["supersede", "soft_delete"] } } },
          "then": { "required": ["prior_value_id"] }
        },
        {
          "if": { "properties": { "kind": { "const": "negation" } } },
          "then": { "properties": { "operation": { "enum": ["soft_delete", "supersede"] } } }
        }
      ]
    },
    "DroppedSignal": {
      "type": "object",
      "additionalProperties": false,
      "required": ["turn_id", "raw_phrase", "reason"],
      "properties": {
        "turn_id": {
          "type": "integer",
          "minimum": 0,
          "description": "Turn that contained the phrase. Single int — drops are always tied to one turn."
        },
        "raw_phrase": {
          "type": "string",
          "minLength": 1,
          "maxLength": 500,
          "description": "Quoted span from the turn text. Used by the regex-retirement audit to compute 'LLM saw it' coverage."
        },
        "reason": {
          "type": "string",
          "enum": [
            "ambiguous_reference",
            "out_of_scope_entity",
            "out_of_scope_attribute",
            "low_confidence",
            "sarcasm_or_rhetoric",
            "duplicate_of_l3",
            "insufficient_context",
            "other"
          ],
          "description": "Closed enum so we can aggregate by reason in the audit dashboard. 'other' is the explicit escape hatch and is itself a metric to watch."
        }
      }
    }
  }
}
```

### Mapping to DB columns (so Writer construction is mechanical)

| Schema field | DB column (target) |
|---|---|
| `extractor_run_id` | `memory_audit_log.extractor_run_id`, `memory_extraction_queue.extractor_run_id` |
| `candidate.entity_type` | `memory_audit_log.entity_type` (VARCHAR 50) |
| `candidate.entity_ref` | `memory_audit_log.entity_ref` (VARCHAR 100) |
| `candidate.attribute` | `memory_audit_log.attribute` (VARCHAR 50) |
| `candidate.value` | becomes `fact_nodes.object` and is summarized into `fact_nodes.literal_text` by Resolver |
| `candidate.source_turns` | `memory_audit_log.source_turns` (ARRAY[Integer]); union goes to `fact_nodes.source_turn_ids` |
| `candidate.confidence` | `fact_nodes.confidence` |
| `candidate.operation` | `memory_audit_log.operation` |
| `candidate.reasoning` | `memory_audit_log.reasoning` |
| `candidate.kind` | NOT stored on `fact_nodes`. Stored in `memory_encoding_events.llm_extraction` JSONB only. Used by Resolver to gate writes. |
| `dropped_signals[*]` | `memory_encoding_events.llm_extraction.dropped_signals`. Never reaches `fact_nodes` or `memory_audit_log`. |

`predicate` / `subject` / `object` on `FactNode` are derived by the Resolver from `(entity_type, attribute, value, entity_ref)`. The Extractor never produces them directly — this is intentional decoupling (§2.2).

---

## 2. Enum closure rationale

### 2.1 `entity_type` — 10 values

Chosen to cover the disclosure surface that drives SS04 trust-stage advancement (which gates SS05 persona unlock) in the first 30 days of a companion relationship:

- `self` — the user. Required for `name / age / occupation / location_residence / birthday`.
- `pet` — companion animals. Companion-product hot category; co-recall is high.
- `family / friend / colleague` — the three social rings SS04 distinguishes.
- `location` — places relevant to recall (hometown, workplace, current city).
- `possession` — "I have/own X" facts that are not preferences.
- `preference` — likes/dislikes/hobbies as standalone subjects.
- `event` — birthdays, anniversaries, milestones (drives L4 promotion §4.2 of spec).
- `other` — explicit escape hatch. Tracked as a metric; if `other` exceeds 10% of candidates over 7 days, that's the signal to add a new enum value.

**Intentionally out of scope for v1**:
- `medical_provider`, `financial_account`, `legal_doc` — sensitive, requires separate consent UI; not productizable in the companion window.
- `brand`, `media_title` — collapse into `preference` for v1 (e.g. `preference.hobby = "听周杰伦"`).
- `pronouns`, `gender_identity` — schema would be wrong without product input; refuse to encode until the surface exists.
- `abstract_concept` — non-anchorable; degrades into noise.

A v1.x MINOR bump can add enum values without breaking readers (§4).

### 2.2 `attribute` — 15 values

Maps onto the audit log's `VARCHAR(50)` and onto the high-frequency disclosure attributes observed in early-relationship conversational data:

- Identity primitives: `name / nickname / age / birthday / occupation`.
- Visual/physical (mostly for pets): `color / breed`.
- Relational: `relation` (the join between `entity_type=family|friend|colleague` and the user), `location_residence / location_origin`.
- Preference primitives: `hobby / dislike / health_condition`.
- Time-anchored: `anniversary`.
- `other` — same escape-hatch contract as `entity_type.other`.

**Why `attribute` is decoupled from `predicate`**:
`FactNode.predicate` is a free-form VARCHAR(100) used by the graph layer. The Extractor must not invent predicates because (a) we cannot enum-close graph predicates without breaking the graph retriever, and (b) graph predicate naming is a Resolver / Consolidator concern that needs the L3 snapshot context. The Extractor surfaces *what kind of attribute it is*; the Resolver picks the canonical predicate (e.g. `attribute=location_residence → predicate="lives_in"`).

**Intentionally out of scope**:
- `salary`, `religion`, `political_view`, `sexual_orientation` — privacy class P0; require separate consent flow before they may be persisted.
- `MBTI`, `blood_type`, `zodiac` — encode as `preference.hobby` if user volunteers; not first-class.
- `physical_appearance` (for the user themselves) — high false-positive rate from rhetoric ("我胖了五斤") and limited recall value.

### 2.3 `kind` — 5 values, and why it lives on the candidate

`kind ∈ {disclosure, rhetoric, question, negation, hypothetical}`.

**Why on the candidate (not a pre-filter step)**:

A pre-filter would discard rhetoric / question / hypothetical before they ever reach the Resolver. We deliberately keep them as `kind != disclosure` candidates because:

1. **Auditability**: when a fact later turns out to have been a joke ("我女朋友是我妈"), we need the audit trail that says "the LLM SAW this as a rhetorical disclosure with kind=rhetoric — the Resolver suppressed the write because of kind, not because the LLM missed it". Without the candidate, we cannot distinguish "LLM missed it" from "LLM correctly suppressed it".
2. **Single decision point**: the Resolver becomes the only place where the (kind × operation × prior_value_id × confidence) policy is encoded. A pre-filter would scatter policy across two layers.
3. **Negation expressiveness**: `kind=negation + operation=soft_delete + prior_value_id=<X>` is a single coherent message. A pre-filter would have to invent a separate "delete intent" envelope, doubling the schema surface.
4. **Latency**: one LLM call producing a tagged candidate is cheaper than (filter call → extraction call).

The `allOf.if/then` rules in §1 enforce a minimum coherence (`kind=negation → operation ∈ {soft_delete, supersede}`) so the Resolver can trust the combination.

### 2.4 Why `dropped_signals` exists

Two distinct purposes — and they're worth the schema cost individually:

1. **Audit / prompt regression**: when the prompt's quality drops between versions, `dropped_signals` lets us see *what the LLM noticed but threw away*. Without it, a regression looks like a uniform recall drop — indistinguishable from "model deprecated" or "input distribution shifted".
2. **Evidence for regex retirement** (the bigger one): SS02 ships with `MEMORY_EXTRACTOR_MODE ∈ {regex, llm, dual}`. The plan to retire the regex track requires evidence that the LLM track *catches what regex caught*. `dropped_signals` is the place where the LLM admits "I saw this phrase, I considered it, here is my reason for not writing it." In `dual` mode the offline diff is:
   - regex_hits ∩ llm_candidates → LLM caught it
   - regex_hits ∩ llm_dropped → LLM saw it and explicitly rejected (review by reason)
   - regex_hits \ (candidates ∪ dropped) → LLM blind spot, regex must stay

Without `dropped_signals` the third bucket is silently merged with the second, and we can never confidently retire regex.

The phrase 「跟我一样」 (anaphoric reference that cannot be resolved within the window) goes here with `reason=ambiguous_reference`.

### 2.5 Why `reasoning` is required, not optional

Three independent reasons, each sufficient:

1. **Hallucination guard** (per spec §132): the format `≤ 200 chars + must cite a source_turns id` is the cheapest forcing function we have to make the LLM ground in evidence rather than confabulate. A schema validator can post-check that the reasoning string contains at least one of the candidate's `source_turns` ids; failing candidates are auto-rejected by the Resolver.
2. **Debuggability**: every L3 row that turns out to be wrong becomes an archeology problem unless the audit log carries the per-write justification. `memory_audit_log.reasoning` is a real column (see `models.py:563`); making it required upstream means it is never NULL downstream.
3. **Prompt-quality regression metric**: reasoning-length variance, citation-rate, and "reasoning that names no source turn" are leading indicators of prompt rot. They are cheap to measure and they catch problems before the recall metrics do.

**Why ≤ 200 chars**: token budget. Per-candidate reasoning at full LLM verbosity would 3–5× the extractor output cost. 200 chars (~50 tokens) is enough for one cited turn + a short justification.

### 2.6 Why `operation` excludes hard `delete` and excludes `promote`

- **No hard `delete`**: project rule (`AGENTS.md` line 184: "No hard deletes on user data — use logical delete"). The schema cannot offer a hard-delete option because the column does not exist downstream — `do_not_recall=true` is the only delete-equivalent.
- **No `promote`**: L3 → L4 promotion is the **Promoter's** job in the nightly Consolidator, not the Extractor's. The Extractor can suggest `is_identity_level=true` indirectly via high `confidence` + `attribute ∈ {name, birthday, anniversary}`, but the Schema does not let it write the promotion. This keeps the Promoter as the single source of truth for L4 (per spec M-3 "L4 永不衰减，永不删除").

---

## 3. Edge case coverage

The schema does not *solve* these cases — the Resolver does. The schema's job is to make sure the Resolver receives enough information to solve them. Each row below is "this case is REPRESENTABLE in the envelope".

| Case | What the user says | Envelope shape | Resolver expectation |
|---|---|---|---|
| **Fragmentation across turns** | T0 "我有只猫" → T1 "叫妙妙" → T3 "灰白色的" | 3 candidates: `(pet, other, 'a cat', entity_ref="cat#1", op=create, src=[T0])`, `(pet, name, '妙妙', entity_ref="cat#1", op=update, src=[T0,T1])`, `(pet, color, '灰白色', entity_ref="cat#1", op=update, src=[T0,T3])`. Shared `entity_ref` is the coalescence key. | Resolver creates one FactNode for the cat existence and applies updates by attribute. |
| **Single-shot consolidation** (LLM coalesces internally) | same as above | 1 candidate: `(pet, name, '妙妙', entity_ref="cat#1", op=create, src=[T0,T1,T3], reasoning="T1: 叫妙妙; T3: 灰白色")` plus separate color candidate. | Equally valid. Resolver does not care whether coalescence happened at LLM time or its own time. |
| **Supersession with explicit prior** | "其实我现在不喜欢草莓了" 30 turns after "我喜欢草莓" (and the old fact was passed in the L3 snapshot) | `(self, dislike, '草莓', kind=disclosure, op=supersede, prior_value_id=<UUID of old fact>, src=[T30])` | Resolver marks old fact `is_corrected=true`, writes new fact with `contradicting_fact_ids=[old_id]`. |
| **Supersession without prior in snapshot** | same as above but L3 snapshot was truncated and didn't include the old fact | `(self, dislike, '草莓', kind=disclosure, op=create, src=[T30], reasoning="可能与既往偏好冲突，但 snapshot 未含")`. The `if/then` rule in §1 PREVENTS op=supersede here because `prior_value_id` is null. | Consolidator nightly job detects the contradiction. Expected and acceptable. |
| **Negation as soft-delete** | "我没有宠物" 30 turns after "我有只猫叫妙妙" | `(pet, other, '猫', kind=negation, op=soft_delete, prior_value_id=<UUID of cat fact>, src=[T30,T31])` | Resolver sets `do_not_recall=true` on the L3 cat fact. The `if/then` rule enforces `kind=negation → op ∈ {soft_delete, supersede}`. |
| **Negation without resolvable prior** | "我没有宠物" with no prior cat fact in the L3 snapshot | Must NOT be a candidate (no fact to delete and we don't write "user has no pet" as a fact). Goes to `dropped_signals` with `reason=insufficient_context`. | Audit trail preserved. No write. |
| **Rhetoric** | "我女朋友是我妈" | `(family, relation, 'mom', kind=rhetoric, op=create, src=[T5], reasoning="比喻，非字面")` | Resolver sees `kind=rhetoric` → skip write. Audit log records the suppressed candidate. |
| **Question** | "你叫什么名字" | No candidate. The window contains zero disclosures from this turn. | n/a |
| **Hypothetical** | "如果我中了彩票…" | `(self, hobby, '环游世界', kind=hypothetical, op=create, src=[T10])` (only if LLM mistakenly thinks it's a disclosure) | Resolver sees `kind=hypothetical` → skip. The point of representing it is so prompt regressions are detectable, not so it writes anything. |
| **Anaphora that cannot be resolved in window** | A: "我朋友很喜欢猫" B: "跟我一样" | `dropped_signals: [{turn_id: T_B, raw_phrase: "跟我一样", reason: "ambiguous_reference"}]` | No candidate. Future schema vN may add a `pronoun_target` field; v1 deliberately does not. |
| **Multi-fact in one turn** | "我叫张三，住北京" | 2 candidates: `(self, name, '张三')` and `(self, location_residence, '北京')`, both `src=[T0]`. `maxItems: 32` allows this. | Two writes. |
| **Reinforcement of an existing fact** | T+0 "我猫叫妙妙" then T+50 "对我家猫叫妙妙" | Two candidates with overlapping content. Resolver detects prior L3 row, downgrades op to `update` (reinforce), increments `confirmation_count`. LLM is not required to detect this — the audit trail still shows two candidates. | Per spec §3.4 Step 3 reinforcement path. |
| **Soft-delete then re-assert** | "我没有猫" → 100 turns later "我家猫怎么样" | First creates `op=soft_delete` on the prior fact. Second creates a new `(pet, other, '猫', op=create)` with no `prior_value_id`. Resolver sees the previously-soft-deleted row and may either un-mark `do_not_recall` or create a fresh row. This is intentionally a Resolver policy decision, not a schema concern. | Out-of-band Resolver doc. |

---

## 4. Versioning policy

Two independent SemVer streams that travel together in every envelope and every audit log row.

### 4.1 `schema_version` (this document)

The string in `envelope.schema_version` MUST equal the MAJOR.MINOR of the `$id` URL. PATCH may differ.

| Bump | Trigger | Reader compatibility |
|---|---|---|
| **MAJOR** | Required field added, required field removed, enum value removed, field type changed, `if/then` rule tightened (a previously-valid envelope becomes invalid). | Breaking. Readers MUST reject mismatched MAJOR. |
| **MINOR** | New OPTIONAL field added, new enum value added, new `definitions` entry added, new `if/then` rule that only constrains a previously-unconstrained combination. | Backward-compatible. Old readers ignore new optional fields, but they cannot validate new enum values — so validators are upgraded ahead of producers. |
| **PATCH** | `description` / docstring edits, examples added, schema test-suite fixes. No semantic change. | Fully compatible. |

Rollout rule: validator-then-producer. Bump validators (consumers) to vN.MINOR.0 before any producer emits vN.MINOR.0 output. Otherwise inflight envelopes get rejected for using a newly-added enum value.

### 4.2 `prompt_version`

The SemVer of the prompt asset shipped at `backend/heart/prompts/memory_extraction_v<MAJOR>_<MINOR>_<PATCH>.py` (proposed convention — separate PR).

| Bump | Trigger | Re-eval policy |
|---|---|---|
| **MAJOR** | Removed / replaced a few-shot example, removed a safety instruction, restructured the prompt skeleton, switched the model family the prompt is tuned for. | Full golden-set re-eval REQUIRED before deployment. Calibration of the `confidence ≤ 0.7 ⇒ FPR ≤ 5%` target must be re-measured. |
| **MINOR** | Added a new few-shot example for a documented edge case, added an instruction that constrains a previously-unconstrained behavior, added a new attribute coverage. | Targeted regression on the affected edge case + smoke run on the full golden set. |
| **PATCH** | Typo fix, whitespace, identifier rename, comment edit. Behavior unchanged. | Smoke run only. |

**Locked once shipped**: a published `prompt_version` is immutable. A "small fix" never edits an existing version — it is always a new PATCH bump. The audit log retains the original string; if we silently edit, every audit row pointing at the old string lies about which prompt produced it.

### 4.3 Cross-product invariant

`memory_audit_log` records both `schema_version` and `prompt_version` on every row (the existing `extractor_run_id` joins to the envelope where both live). A given `prompt_version` pins exactly one `schema_version` — if a prompt change requires a schema change, both bump together and the lock advances atomically.

---

## 5. Known limitations (v1 does NOT solve)

Listed explicitly so we don't pretend the schema covers them. Each one is a tracked v1.x or v2 candidate.

1. **Cross-window references** — "还记得上次我说的那个吗" pointing at content outside the 6-turn window. The LLM sees only the window. The L3 snapshot helps but does not include historical raw turns. Goes to `dropped_signals.reason=insufficient_context`. Future: pass a denser "recent fact summary" alongside the snapshot.
2. **Multi-entity coreference within window** — "他和她去北京了" where "他" and "她" refer to two distinct previously-introduced people. The LLM may produce a single `entity_ref` for both. Resolver cannot fix this without re-reading the source turns. Future: a `pronoun_resolution` field listing `(pronoun, turn_id, resolved_to_entity_ref)`.
3. **Subjective truth** — "我妈说她最漂亮". v1 records this as `(family, other, '最漂亮')` if at all. There is no `according_to` field. Future: an `attribution` optional field.
4. **Negation polarity strength** — "我有点不喜欢" and "我完全讨厌" both surface as `(self, dislike, X, kind=disclosure)`. Confidence captures uncertainty about extraction, not about intensity of the disclosed feeling.
5. **Numeric normalization** — "二十多岁" stored verbatim as `value`. Resolver may or may not normalize. The schema does not promise normalization.
6. **Cross-day contradiction detection** — the Extractor sees the current window only. Contradictions across days are the **Consolidator's** job (§3.6 Step 4 in spec).
7. **Sarcasm** — there is no `kind=sarcasm`. Sarcastic disclosures may mis-extract as `kind=disclosure`. The user-correction path ("其实不是") triggers `kind=negation + op=supersede`, which is the recovery mechanism.
8. **Multilingual code-switch within a single turn** — the schema is language-agnostic; behavior is the LLM's responsibility. We do not validate language in v1.
9. **Confidence calibration is acceptance, not contract** — the schema accepts any `[0.0, 1.0]`. The "0.7 ⇒ FPR ≤ 5%" target is enforced by the golden-set eval gating prompt releases, not by the schema.
10. **`entity_ref` collision across envelopes** — `cat#1` in envelope A and `cat#1` in envelope B are NOT the same entity. The handle is envelope-scoped on purpose; making it durable would require entity-resolution UI that does not exist.
11. **L3 snapshot freshness window** — the LLM may emit `op=supersede` against a `prior_value_id` that was soft-deleted by an interleaved extraction run. Resolver MUST treat `prior_value_id` as a hint and re-check the DB row's current state before writing. Schema cannot enforce this; it's a Resolver invariant.
12. **No PII redaction at the schema layer** — values are raw user strings. Redaction (if it ever ships) lives upstream of the LLM call or downstream of the Resolver, not in this schema.

---

## 6. Acceptance criteria for v1.0.0

Before this schema can be shipped as `v1.0.0` (not `v0.x`):

- [ ] Validator implemented (Python `jsonschema` draft-07) and called inside the deepseek-v4-flash tool-use response handler.
- [ ] Golden set of 50 windows, each with a human-labeled expected envelope.
- [ ] At schema validation level: 100% of envelopes that the LLM emits parse without error (the StructuredOutput tool-call layer guarantees enum/required-field conformance; validator catches `if/then` rule violations and `source_turns ⊆ window.turn_ids`).
- [ ] At `reasoning` quality level: ≥ 95% of candidates' `reasoning` strings contain at least one of their declared `source_turns` ids.
- [ ] `dropped_signals` is non-empty on at least 60% of windows that contain regex hits (otherwise the regex-retirement evidence path is broken).
- [ ] Resolver doc (separate) consumes this schema and writes its own state machine; Resolver doc lands before this schema bumps off `v1.0.0`.

---

## Approval

| Date | Reviewer | Role | Version reviewed | Notes |
|---|---|---|---|---|
| 2026-06-20 | HUMAN | Project Lead | 1.0.0 | approved as-is |
