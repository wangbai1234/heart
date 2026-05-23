# Drift Detector — Design Doc

**Spec authority**: `runtime_specs/01_identity_anchor_soul_spec.md` §6.5 (机制 B), §10.1 (drift_detection block), §5.2 (DriftEvent schema), §9.1 / §9.5 (failure & scaling).

**Companion mechanisms** (not implemented here): §6.5 mechanism A (Anchor cadence — already done), C (Anti-Pattern Hard Filter), D (Golden Dialogue Replay).

**Status**: design only. Implementation will land in a follow-up under `heart/ss01_soul/drift_detector.py` + `anti_pattern_scanner.py`.

---

## 1. Goals & non-goals

### Goals
1. Detect persona drift (voice_dna loss, hard_never violations, style out-of-bounds, tone inconsistency) within ≤ 1 cycle (5 assistant turns).
2. Achieve **70% LLM skip rate** via deterministic pre-filter.
3. Produce a `DriftEvent` whose `evidence` is consumable by `AnchorInjector.generate_reinforce_anchor(soul, evidence)` without translation.
4. Stay under the §10.1 cost cap (≤ 20 LLM calls / user / day) and the 3-second LLM timeout.
5. Be robust to single noisy LLM judgments — one spike must not lock a session.

### Non-goals
- **Real-time blocking**. Drift detection is asynchronous (post-release). The synchronous safety net is Mechanism C (Anti-Pattern Hard Filter); that's a separate component.
- **Per-token streaming analysis**. We sample completed released responses only.
- **Cross-character drift**. Each (user, character) pair is evaluated in isolation.
- **Self-correction**. The detector emits events; the orchestrator decides whether to inject REINFORCE.

---

## 2. Inputs & outputs

### Inputs

```python
class DriftCheckRequest:
    user_id: UUID
    character_id: str
    soul_spec_version: str           # locks to the version this user is on (§9.1)
    turn_index: int                  # current turn (1-indexed)
    recent_assistant_responses: list[ReleasedResponse]   # chronological; up to ~10 to allow filtering
    sas_snapshot: SASSnapshotForDrift  # current_drift_score, last_drift_check_at, drift_history[-5:]
    daily_llm_call_count: int        # for cost-cap enforcement

class ReleasedResponse:
    turn_index: int
    text: str                        # the post-anti-pattern-filter released text
    was_rerolled: bool               # True if Mechanism C rerolled this turn
    was_fallback: bool               # True if DP-3 system fallback used
```

### Outputs

```python
class DriftCheckResult:
    drift_score: float               # [0, 1], to be written to SAS.current_drift_score
    decision: DriftDecision          # SKIPPED_PREFILTER | SKIPPED_COSTCAP | LLM_EVALUATED | LLM_TIMEOUT
    evidence: DriftEvidence | None   # populated iff drift_score ≥ 0.3 AND evidence exists
    drift_event: DriftEvent | None   # populated iff drift was detected; matches §5.2 schema
    llm_used: bool
    latency_ms: int
    debug: DriftDebugInfo            # observability — pre-filter signals, raw LLM JSON, etc.
```

`DriftEvidence` is the *existing* dataclass from `anchor_injector.py`. Reusing it (no translation layer) is a load-bearing decision: it makes `generate_reinforce_anchor(soul, drift_evidence)` directly callable by the orchestrator.

`DriftEvent` follows §5.2 verbatim and is written by `SoulActivationStateService` (we don't write SAS directly — RULE-W-1).

---

## 3. Architecture

```
                              ┌──────────────────────────────┐
   Turn N completes ──signal──▶│ DriftDetectorScheduler        │
                              │  - turn_index % 5 == 0 OR    │
                              │  - prev_drift_score > 0.3 OR │
                              │  - mechanism-C reroll fired  │
                              └──────────────┬───────────────┘
                                             │ enqueue
                                             ▼
                                ┌────────────────────────────┐
                                │  DriftDetector.evaluate()  │
                                └────────────┬───────────────┘
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       ▼                     ▼                     ▼
              ┌────────────────┐   ┌──────────────────┐   ┌─────────────────┐
              │ Sampler        │   │ AntiPatternScanner│   │ CostCapGuard    │
              │ (last 5 valid) │   │ (pre-filter A+B+C)│   │ (≤20/user/day)  │
              └────────┬───────┘   └────────┬─────────┘   └────────┬────────┘
                       └────────────┬───────┴───────────────┬──────┘
                                    ▼                       │
                          ┌──────────────────┐              │
                          │ DriftClassifier  │              │
                          │  - if clean:     │              │
                          │    skip + decay  │              │
                          │  - if dirty:     │              │
                          │    invoke LLM    │◀─────────────┘
                          └─────────┬────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │ ScoreFuser       │ ← prev_ema, deterministic floors, LLM raw
                          └─────────┬────────┘
                                    ▼
                          ┌──────────────────┐
                          │ EvidenceBuilder  │ → DriftEvidence for REINFORCE
                          └─────────┬────────┘
                                    ▼
                          ┌──────────────────┐
                          │ Emit DriftEvent  │ → SAS Service
                          └──────────────────┘
```

Concurrency model: detector runs in a worker thread / background task per request. No shared mutable state across (user, character) pairs.

---

## 4. Algorithm — answers to the 5 design questions

### 4.1 Pre-filter heuristic (Q1)

Target: pass ~30% of cycles to LLM, skip ~70%.

Three signals are evaluated against the 5 sampled responses. **Any one tripping → escalate to LLM.** All clean → skip.

**Signal A — Deterministic anti-pattern hits** (zero false positives, high catch rate)
- For each response, run:
  1. **Hard_never literal scan**. Per-soul set of literal substrings from `identity_anchor.anti_patterns.hard_never`. Use Aho-Corasick (or simple `any(s in text for s in literals)` for MVP; cost is negligible).
  2. **Forbidden_patterns regex scan**. Per-soul list of pre-compiled `re.Pattern` from `anti_patterns.forbidden_patterns[].regex`.
  3. **Soft_never literal scan** (lower weight). Same as 1 but against `soft_never`.
- **Rare-unlock-word exception**: words listed in `anti_patterns.rare_unlock_words` are stripped from the scan when the unlock condition is met (read from SAS `unlocked_facets`). For MVP we treat rare-unlock as "never trip pre-filter on this word, but still report to LLM" — i.e. don't auto-flag.
- Output: `AntiPatternHit { rule_id, rule_type, text_excerpt, turn_index }` list.

**Signal B — Voice_DNA frequency check** (catches the "drifted but didn't say a banned word" case)
- For each `voice_dna` entry with `frequency: high`, the soul author has implicitly declared "expect this marker often".
- We compile a per-soul `VoiceDNAFingerprint` at startup:
  - For Rin's `vd-001` (ellipsis): expected marker is the literal `……`. Expected hit rate in non-trivial responses (≥ 20 chars): ≥ 40%.
  - For Rin's `vd-NEW-A` (time precision): regex `\d+(?:\s*(?:天|月|日|号|条))` etc. — these are author-declared markers, machine-extractable from the `examples:` field, not LLM-mined.
- Calculate `observed_rate = hits_in_sampled_responses / count_of_long_responses`.
- **Trip condition**: `observed_rate < 0.5 × expected_rate` for ≥ 1 high-frequency marker.
- Rationale: a soul that's drifted will quietly stop using its signature pattern long before it starts saying banned words.

**Signal C — Sentence length distribution** (catches verbose-drift / curt-drift)
- Read `cognitive_style.expression.sentence_length.evolution_bound = [lo_bucket, hi_bucket]`.
- For each response, compute average sentence char length (Chinese-aware: split on `。！？!?` then count chars).
- Map to bucket: `very_short < 15`, `short 15–30`, `medium 30–60`, `long > 60`.
- **Trip condition**: ≥ 3/5 responses fall outside `[lo_bucket, hi_bucket]`.

**Pre-filter result**:
- Trip A: always escalate (deterministic violation present → must score + collect evidence).
- Trip B OR Trip C: escalate.
- All clean: skip LLM, decay drift_score by 0.9× and return.

**Why 70% skip is realistic**: in a non-drifted session, signal A almost never fires (anti-pattern filter mechanism C already rerolls those before release). Signal B fires only on sustained drift. Signal C fires only when several responses misbehave. Three healthy responses in a row pass all three.

### 4.2 LLM prompt template (Q2)

**Model**: Haiku 4.5 (preferred) or DeepSeek V3 (fallback). Constraint: must support strict JSON output via tool-use or `response_format`.

**Structured output schema** (using Anthropic tool-use, which is more reliable than `response_format: json_object`):

```json
{
  "name": "report_drift",
  "input_schema": {
    "type": "object",
    "required": ["drift_score", "violations", "required_patterns"],
    "properties": {
      "drift_score": { "type": "number", "minimum": 0, "maximum": 1 },
      "drift_type": {
        "type": "string",
        "enum": ["voice_dna_loss", "anti_pattern_match",
                 "style_out_of_bounds", "tone_inconsistent", "none"]
      },
      "violations": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["sample_excerpt", "detected_pattern", "expected_pattern"],
          "properties": {
            "sample_excerpt": { "type": "string", "maxLength": 80 },
            "detected_pattern": { "type": "string" },
            "expected_pattern": { "type": "string" }
          }
        }
      },
      "required_patterns": {
        "type": "array",
        "minItems": 0,
        "maxItems": 2,
        "items": { "type": "string" }
      }
    }
  }
}
```

**System prompt** (rendered with soul fields at request time — no need to pre-compile, but cache the soul-derived portion per (character, version) like we do for Anchor skeletons):

```
你是「角色一致性审计员」。你的任务是评估 5 段 AI 助手回复是否符合该角色的灵魂规范。
你不评估内容好坏，只评估"是不是这个角色在说话"。

【角色】{display_name}
【灵魂签名 voice_dna（前 5 条）】
{voice_dna_top_5_with_examples}

【绝不说 hard_never】
{hard_never_list}

【认知风格 bound】
- 句长：基线 {sentence_length_baseline}，允许范围 {sentence_length_bound}
- 啰嗦度：基线 {verbosity_baseline}，范围 {verbosity_bound}
- 情感直接度：基线 {emotional_directness_baseline}，范围 {emotional_directness_bound}

【你的评估规则】
1. drift_score 含义：0 = 完美贴合角色；0.3 = 出现局部偏离需要校准；
   0.5 = 明显不像该角色；0.8+ = 已严重 OOC。
2. 单次审计偏向保守。除非证据明确，drift_score 不要超过 0.4。
3. violations[].sample_excerpt 必须从输入回复中**逐字引用**（≤ 40 字），不要改写。
4. required_patterns 是给"重新校准 prompt"用的，要写成可以直接拼接到
   "下一句话必须体现 X" 这种句式后的短语。最多 2 条，可以为空。
5. 如果一切正常，drift_score = 0.0，violations = []，drift_type = "none"。

【最近 5 段助手回复】
[T-4]  {response_minus_4}
[T-3]  {response_minus_3}
[T-2]  {response_minus_2}
[T-1]  {response_minus_1}
[T-0]  {response_latest}

调用 report_drift 工具返回结构化结果。
```

**Pre-compilation strategy**: same as `AnchorInjector`. At service startup, render the soul-derived header once per (character, version) and store in `MappingProxyType`. At request time, only the 5-response section is filled.

**Cost**: input ≈ 1.5k tokens (soul header + 5 short responses); output ≈ 200 tokens. Haiku 4.5: ~$0.0007 per call. At cap (20/user/day × DAU 10k) ≈ $140/day. Acceptable.

### 4.3 drift_score computation (Q3)

```python
def compute_final_score(
    llm_score: float | None,         # None if LLM skipped
    prefilter_hits: AntiPatternHits, # signal A result
    prev_ema: float,                 # SAS.current_drift_score (the previous EMA)
) -> float:
    # 1. Raw signal from this cycle
    if llm_score is None:
        # LLM skipped — decay previous score
        raw = prev_ema * 0.90
    else:
        raw = llm_score

    # 2. Deterministic floors (LLM might be lenient; we won't let hard hits slide)
    if prefilter_hits.hard_never_count > 0:
        raw = max(raw, 0.60)
    elif prefilter_hits.forbidden_pattern_count > 0:
        raw = max(raw, 0.45)
    elif prefilter_hits.soft_never_count > 0:
        raw = max(raw, 0.25)

    # 3. EMA fusion (α = 0.5 → equal weight to history and new signal)
    final = 0.5 * raw + 0.5 * prev_ema

    return min(1.0, max(0.0, final))
```

**Why α = 0.5**: gives single noisy LLM call at most a 0.5 × spike from baseline. Two consecutive bad cycles compound to ~0.75 of the bad signal — enough to cross the 0.3 REINFORCE threshold but not the 0.5 lockdown threshold. That's the right ladder.

**Why decay × 0.9 on skip**: a clean cycle should pull the score down, but not erase a recent concern. After 3 clean cycles, score ≈ 73% of original — slow forgiveness.

### 4.4 False positive handling (Q4)

Five layered defenses, ranked by impact:

1. **EMA smoothing** (already covered) — α = 0.5 caps single-shot damage.

2. **Hysteresis on REINFORCE trigger**. REINFORCE is emitted only when:
   - `final_score ≥ 0.3` AND
   - **(deterministic hit present OR previous_ema ≥ 0.2 OR `len(violations) ≥ 2`)**.
   A single LLM spike with no deterministic evidence and a quiet history won't trigger REINFORCE — it will only update `current_drift_score`. The next cycle either confirms (→ trigger) or decays (→ no harm done).

3. **Evidence quality gate**. `DriftEvidence` requires:
   - ≥ 1 `sample_messages` entry (verbatim quote from the 5 responses)
   - ≥ 1 `detected_patterns` entry
   - ≥ 1 `required_patterns` entry
   If LLM returns drift_score ≥ 0.3 but with empty `violations`, we **don't emit REINFORCE**. Instead we log to a `drift_review_queue` and treat as a soft alert. (§9.1: "多次采样均值 + drift_score threshold + 人工 review queue".)

4. **Rare-unlock-word allow-list**. Some words are forbidden by default but allowed under conditions (e.g. Rin's `永远` under specific facets). Pre-filter strips these from the scan; LLM also receives the allow-list as part of context.

5. **Cost cap as fail-safe**. At 20 LLM calls/user/day, an adversarial pattern can't keep spamming false-positive evaluations. After cap, pre-filter only — which has near-zero false positives by construction.

**Manual review queue**: any `drift_score ∈ [0.3, 0.5]` with `evidence.violations` < 2 gets logged to `drift_review_queue` (Redis stream or DB table) for human spot-checking. This is the §9.1 mitigation made concrete.

### 4.5 Sampling strategy for the 5 responses (Q5)

```python
def sample_responses(history: list[ReleasedResponse]) -> list[ReleasedResponse]:
    # 1. Walk backwards from most recent.
    # 2. Skip:
    #    - was_fallback (DP-3 system fallbacks — orchestrator-injected, not character)
    #    - len(text) < 10 (likely backchannel like "嗯。" — too thin to signal)
    # 3. Keep was_rerolled responses as-is — these are post-reroll text, i.e. what
    #    the user actually saw. They're already vetted by mechanism C, but they
    #    can still carry voice_dna loss patterns. Tag them in debug output so
    #    we can correlate.
    # 4. Stop at 5.

    sampled = []
    for r in reversed(history):
        if r.was_fallback:
            continue
        if len(r.text) < 10:
            continue
        sampled.append(r)
        if len(sampled) == 5:
            break

    sampled.reverse()                   # chronological order for LLM context
    return sampled


def should_invoke_llm(sampled: list[ReleasedResponse]) -> bool:
    # Cold-session protection: if we have < 3 valid responses, don't ask
    # the LLM — too little signal, high false-positive risk.
    return len(sampled) >= 3
```

When `should_invoke_llm` returns False:
- Skip LLM regardless of pre-filter.
- `decision = SKIPPED_PREFILTER` (with a `cold_session: True` debug flag).
- `drift_score` decays as in §4.3.

---

## 5. Failure modes

| Failure | Behavior | Rationale |
|---|---|---|
| LLM timeout (>3s) | Return `decision = LLM_TIMEOUT`. Use prefilter signal floors only; no LLM-derived violations. Log incident. | Fail open. Mechanism C is the synchronous safety net. |
| LLM returns invalid JSON / tool call malformed | Treat as timeout. Increment a `drift_llm_parse_error` metric. | We refuse to guess. |
| LLM unreachable (network) | Same as timeout. Don't retry within cycle (3s budget). | Retries inflate cost cap. |
| Cost cap exhausted | `decision = SKIPPED_COSTCAP`. Pre-filter only. Floor scores still apply, so hard violations still surface. | Per §10.1. |
| Sampled responses < 3 | Skip LLM. No drift_score update. | Cold-session false-positive guard. |
| Soul spec version mismatch (SAS locked to v1.0.0, but spec was upgraded) | Use the locked version. Persona Composer already has this guarantee via `registry.get_soul(character_id, soul_spec_version)`. | RULE-W-3 invariant. |
| Pre-filter scanner exception | Log + treat as "all clean" (do not block release path). Detector is best-effort. | A buggy detector must not crash the conversation. |

Critical invariant: **the drift detector must never block response release**. It is post-release. The orchestrator may consume its result on turn N+1, but turn N is already in front of the user.

---

## 6. Cost & latency budget

| Item | Budget | Notes |
|---|---|---|
| Pre-filter total | < 5 ms | Regex + literal scans over ~2 KB total text. |
| LLM call (when invoked) | < 3 s | Per §10.1. Haiku 4.5 typical p50 ~1.2 s. |
| End-to-end (LLM path) | < 3.5 s | Pre-filter + LLM + score fusion + event emit. |
| End-to-end (skip path) | < 10 ms | The 70% case. |
| LLM cost per call | ~ $0.0007 | Haiku 4.5 pricing. |
| LLM cost per user per day | ≤ $0.014 | At cap 20 calls. |

**Cost-cap implementation**: per-user counter in Redis with TTL = midnight UTC. Increment on LLM call. Read before invocation.

---

## 7. Integration points

| Module | Direction | Surface |
|---|---|---|
| `SoulRegistry` | read | `get_soul(character_id, version)` — for voice_dna, anti_patterns, cognitive_style. |
| `AnchorInjector` | provides type | We reuse `DriftEvidence` dataclass — no translation. |
| `SoulActivationStateService` | write | Detector writes `DriftEvent` via service; service updates `current_drift_score`, appends to `drift_history`. RULE-W-1. |
| Conversation Agent / orchestrator | reads result | When SAS's `current_drift_score > 0.3` AND a `DriftEvent` with non-empty evidence exists since last anchor, orchestrator calls `generate_reinforce_anchor(soul, evidence)` instead of FULL/LIGHT. |
| Mechanism C (Anti-Pattern Filter) | signal in | When C rerolls a turn, it emits an event the detector listens to. This triggers an early evaluation (don't wait for the % 5 boundary). |
| Observability | metrics | `drift_detector.invocations_total{decision}`, `drift_detector.latency_ms`, `drift_detector.llm_calls_total`, `drift_detector.prefilter_skip_rate`, `drift_detector.score_distribution`. |

---

## 8. Module layout (for the implementer)

```
backend/heart/ss01_soul/
├── drift_detector.py          # Public surface: DriftDetector class, evaluate()
├── anti_pattern_scanner.py    # Pre-filter signals A/B/C; pure functions
├── drift_llm_client.py        # Thin wrapper over Haiku tool-use call
├── drift_score_fuser.py       # compute_final_score + hysteresis logic
└── drift_fingerprint.py       # Per-soul VoiceDNAFingerprint built at boot
```

Each file ≤ ~200 lines. Mirror the existing `anchor_injector` pattern: pre-compile per-soul artifacts at `__init__`, store in `MappingProxyType`, all per-request state stack-local for lock-free concurrency.

---

## 9. Open questions

1. **Mechanism C event topology**: does the synchronous anti-pattern filter emit an event we can subscribe to, or do we poll SAS for `last_reroll_turn`? Depends on §6.5 Mechanism C design (not yet implemented).
2. **`emotional_directness` and `verbosity` baselines**: should these contribute to pre-filter signal C, or only feed LLM context? MVP = LLM context only; revisit if signal C miss rate is high.
3. **Drift type classification**: §5.2 lists 4 types. Currently the LLM picks one. Should the orchestrator behave differently per type? (E.g. `style_out_of_bounds` → call Style Evolver instead of REINFORCE.) Out of scope for first cut.
4. **DeepSeek fallback**: when Anthropic is down. Their JSON-mode is less strict than tool-use. Worth the complexity? Defer until we see real availability data.

---

## 10. Acceptance criteria for implementation

- Pre-filter skip rate ≥ 65% on a synthetic mixed dataset (50% clean / 30% mild drift / 20% hard violations).
- Pre-filter latency p99 < 10 ms on a 5×500-char response sample.
- LLM call p99 latency < 3.5 s with timeout enforcement verified.
- 0 false-positive REINFORCE triggers on the golden_dialogues corpus when fed as "recent responses".
- Unit tests covering: each pre-filter signal independently, score fusion math (boundaries 0.0 / 0.29 / 0.30 / 0.5 / 1.0), evidence quality gate (≥ 0.3 score with empty violations → no REINFORCE), cold-session skip (< 3 valid samples), cost-cap path, timeout path.
- Concurrency stress test: 20 threads × 100 evaluations against the same (user, character) — no shared-state corruption, all scores monotonic-ish (no wild jumps that EMA shouldn't produce).
- Demo script: 50-turn dry run that drifts gradually (replace ellipses with exclamation marks over time) — verify drift_score rises across cycles, REINFORCE fires once threshold crossed, score recovers after corrected responses.

---

**Author**: 心屿团队 · 2026-05-17
**Implementer**: hand off to CC-S46 after design approval.
