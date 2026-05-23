# Streaming Anti-Pattern Filter — Design Discussion

**Status**: design draft (no code in this doc)
**Spec anchors**: SS05 §3.3 step 8 (Streaming Pre-Filter in the per-turn flow), §3.5 (Streaming-Compatible Anti-Pattern Filter), §3.4 (Reroll & Fallback), §8.2 (Reroll immersion), §10.4 (Streaming Pre-Filter Buffer), §10.7 (full sync filter), §9.1 (`Streaming pre-filter 漏 violation` row), §2.1 PC-5, INV-PC-3, PCR-1, PCR-8.
**Companion (already shipped)**: `backend/heart/ss05_composer/anti_pattern_filter.py` (full sync filter, post-stream).

---

## 1. What we're designing

The streaming pre-filter is **step 8** in the per-turn flow — it sits between the LLM call (step 7, streaming) and the full sync filter (step 9, post-stream). Its job, stated tightly:

> **Watch each chunk as it arrives from the LLM; if any `hard_never` literal pattern starts appearing in the still-unreleased tail of the response, halt the stream, cancel the LLM call, and signal a reroll — all before the violating bytes reach the user.**

The shipped `AntiPatternFilter` runs *after* the stream completes and scans the full response in ~10 ms. That is the **system of record** for INV-PC-3 ("no released response may match `soul.anti_patterns.hard_never`"). The streaming pre-filter does **not** replace it. It exists for one reason: by step 9, the response is already streaming live to the user (PC-5: "streaming output cannot be rewritten post-process"), so without a pre-filter the only way to enforce INV-PC-3 *and* PC-5 simultaneously is to never release a single byte until the full response is in hand — which kills the streaming UX we paid for in step 7.

The pre-filter buys back streaming by holding a small **release buffer** of the most-recent unreleased characters, scanning the buffer on each chunk, and only releasing characters that have aged past the buffer window without triggering a match. The release buffer is what makes a mid-stream halt invisible to the user (§8.2 情况 1).

Hard requirements:

- **Pre-release detection.** If a `hard_never` literal lands anywhere in the response, it must be detected **before** the bytes containing it cross out of the release buffer. (PC-5, INV-PC-3, PCR-8.)
- **Cross-chunk matches.** Patterns that straddle a chunk boundary must still match. (§9.1 row "Streaming pre-filter 漏 violation".)
- **Sub-5ms per chunk.** Step 8 budget is < 5 ms (§3.3). At typical Claude streaming rates (~20–40 chars/sec for Chinese, chunks of 1–6 tokens), we have headroom — but we cannot do an O(n²) re-scan of a growing transcript.
- **No user-visible artifact on halt.** Once we halt, nothing in the release buffer ever reaches the wire. The user perceives only "a slightly slower turn" (§8.2). PCR-8: "streaming does not retry already-sent content" — so reroll is always *from zero*.
- **Cheap false positives.** A false halt costs one extra LLM call and ~2–3 s wall-clock; it does NOT cost a user-visible glitch (because the buffered prefix never shipped). The math in §3 below shows why this lets us err toward halting.

Out of scope for the pre-filter (and handled by step 9):

- `forbidden_patterns` (regex). Streaming regex matching against an arbitrary user-defined regex is unsafe (catastrophic backtracking risk per chunk) and unnecessary — regex hard patterns are rare and the full filter catches them in ~10 ms post-stream. The pre-filter handles **only `hard_never` literals**.
- `soft_never` (stage-gated). These are *warn*-severity, never trigger reroll, and don't need pre-release interception.
- Critic-style OOC / hallucination judgments — those are step 11, async, cheap LLM. Not deterministic, not in this filter's domain.

In short: **the pre-filter is a tail-window scanner for literal substrings, defending INV-PC-3 against the small window of time during which bytes are in flight to the user.**

---

## 2. The three design questions

### 2.1 Q1 — Incremental Aho-Corasick: feasible?

**Yes, and it's the natural fit, but for our load the simpler "scan-the-tail-buffer" form gets us there with no custom state machine.**

Aho-Corasick is already a state machine — the textbook formulation maintains a `current_state` pointer, advances one character at a time, and emits a match every time the pointer lands on (or fails to) a node with terminal labels. So "incremental AC" is just AC used the way it was designed: feed characters as they arrive, persist the state pointer between chunks, get O(1) amortized work per character.

Two concrete implementations, picking between them:

| Approach | How it works | Per-chunk cost | Implementation cost |
|---|---|---|---|
| **A. True incremental (persistent state pointer)** | Maintain `current_node` across chunks. For each new char, follow `goto`/`fail` transitions. Emit matches when crossing terminal nodes. | O(chars in chunk) | Custom AC implementation (or fork `pyahocorasick` to expose state). `pyahocorasick.Automaton.iter()` does NOT expose the state pointer. |
| **B. Re-scan rolling tail buffer (recommended)** | Each chunk: append to `buffer`, run `Automaton.iter(buffer)` over the whole tail, trim `buffer` to last `max_pattern_length + safety` chars. | O(buffer_size) per chunk | Trivial — reuses the existing `pyahocorasick` setup from `anti_pattern_filter.py`. |

The cost difference at our scale is negligible. With ~80 hard_never literals per character (largest pattern ~40 chars), `max_pattern_length + safety` ≈ 100 chars. Chunks arrive at ~5–20 chars each. Each scan is ~100 chars over an automaton with ~80 patterns → low microseconds in C-extension `pyahocorasick`. P95 sub-millisecond. We are nowhere near the 5 ms budget.

Approach B also wins on **operational properties**:

- Reuses the *same* compiled automaton object the post-stream filter uses (constructed once per character/spec_version at startup) — no risk of state divergence between pre-filter and full filter.
- Replay-friendly: a stuck stream can be replayed by re-running the same `iter()` over the captured chunks. With a persistent state pointer, replay needs you to also serialize the pointer at the halt instant.
- The match-position emitted by `iter()` is an offset into the buffer, which is what we need to decide "did the match start within the unreleased tail or after the release cutoff?" (See §4 below.) With true incremental, we'd have to maintain our own absolute-offset counter alongside the state pointer.

So: **adopt B (re-scan rolling tail with the same `ahocorasick.Automaton` already built for the sync filter)**. Reserve A as the answer if profiling ever shows tail-scan CPU pain — which it won't until pattern counts grow ~100× or chunk rates grow ~10×.

One caveat for B: `Automaton.iter()` over the rolling buffer **re-emits** matches that already fired on a prior chunk if those matched bytes are still in the buffer. The pre-filter must dedupe by tracking which absolute offsets have already been seen — or, more simply, must trim the buffer *after* a successful scan so a matched-and-skipped offset doesn't get re-reported next chunk. The simplest rule: on each chunk, scan the buffer; if no match, retain the last `max_pattern_length + safety` chars; if there is a match, halt — dedup moot. This works because a single match is sufficient to halt.

### 2.2 Q2 — False-positive cost: halt mid-stream when not needed?

**Yes — under the buffered-streaming design, false positives are backend-only cost (~$0.003 + 2–3 s reroll latency), not user-visible glitches. This makes "halt aggressively on any AC hit" the correct policy for `hard_never` literals.**

The full cost-asymmetry table:

| Scenario | What the user sees | Backend cost |
|---|---|---|
| True positive halt (real `hard_never` hit, no user release) | Slightly slower turn (~2–3 s extra). | 1 extra LLM call (~$0.003 on Sonnet). |
| False positive halt (AC hit on benign text) | Slightly slower turn. | Same — 1 extra LLM call. |
| Missed violation (pre-filter says fine, step 9 catches it) | Either: (a) violation already released → INV-PC-3 broken; (b) violation still in buffer → step 9 reroll fires normally → still no user-visible artifact. | One extra LLM call IF step 9 reroll. (a) is the disaster case. |

Two things make halting cheap:

1. **The release buffer hides false positives.** §8.2 情况 1: "the user only feels she responded a little slower." With BUFFER_SIZE ≥ max_pattern_length, the matched bytes were never on the wire; the halt is invisible.
2. **`hard_never` is *literal substring* matching.** Unlike regex, literal AC matches have **zero structural false-positive rate** — if the literal "你的回复违反了你的灵魂" appears as a substring, it appears. The only way to get a false positive is for the literal to be over-broad (e.g., a 3-char literal that incidentally appears in valid output). That's a **pattern-curation problem**, not a filter-design problem, and §9.1 already lists it ("Pattern review process + low false-positive rate target"). The filter's job is to be honest about substring presence; if the pattern set has bad literals, fix the patterns.

The asymmetry only breaks down in two situations the design must guard against:

- **Reroll storms** — if a poorly-tuned pattern fires on, say, 5 % of responses, we'd pay 5 % extra LLM calls and 5 % users see a 2–3 s delay. MAX_REROLL=2 + fallback (§3.4) caps the per-turn blast radius, but doesn't prevent the systemic cost. **Mitigation**: emit `streaming_pre_filter.halt {pattern_id}` counter; alert if any single pattern's halt rate > 1 % over a 1 h window.
- **Halt-then-step-9-passes** — pre-filter halts on a literal hit, but step 9 (which would also catch it) would have ruled the same response acceptable through some other lens. This cannot happen for `hard_never` literals because the full filter checks the *same* AC automaton; if the pre-filter found a match in the buffer, the full filter would find the same match in the full text. The two filters are consistent by construction.

The one decision worth being explicit about: **on a single AC hit, do we halt immediately, or wait to confirm with the post-stream filter?** Waiting would mean releasing the matched bytes through the buffer to the user before step 9 runs. That violates PC-5 (already-streamed content cannot be rewritten) and INV-PC-3. So: **halt on first hit, always. No "soft" mid-stream warnings.**

### 2.3 Q3 — Buffer strategy: how many tokens lookback?

There are **two distinct buffers**, and conflating them is the bug in §9.1's "Streaming pre-filter 漏 violation" row. Naming them:

- **Detection buffer** (`scan_window`) — the rolling tail of recently-received characters that the AC automaton scans on each chunk. Must be long enough that a pattern split across chunk boundaries is fully contained on the chunk that completes it.
- **Release buffer** (`hold_window`) — the most-recent characters of the response that have NOT yet been yielded to the user. Must be long enough that on a match, the entire matched substring is still inside the hold and therefore never released.

The relationship: **`hold_window ≥ max_pattern_length`** is the load-bearing invariant. The scan window can be larger (it's just memory), but the hold window must be at least the longest pattern, otherwise a pattern whose first character has already aged out of the hold cannot be retracted.

Recommended values:

| Buffer | Recommended size | Why |
|---|---|---|
| `scan_window` | `max_pattern_length + 32` chars (§3.5 says "+100"; 32 is plenty in practice for our 1–6-char chunk arrivals) | Bounds re-scan cost. The +32 safety tail absorbs chunk-boundary alignment. |
| `hold_window` | `max(50, max_pattern_length)` chars (§10.4 starts at 50) | 50 chars ≈ 1.5 s of streaming at typical Chinese rates — short enough that the user perceives normal streaming, long enough to contain the longest curated literal. |

"Tokens" vs "chars": the question asked "how many tokens lookback" but the spec consistently uses **characters**, and that's the right unit:

- LLM chunks arrive as decoded UTF-8 `str`, not as token IDs. Counting in tokens forces a tokenizer round-trip on each chunk (extra latency, model-dependent).
- AC literals are character-level patterns by curation (Chinese `voice_dna` violations, English meta-commentary, etc.).
- Token boundaries don't align with semantic boundaries — patterns split across token boundaries are common.

One subtle char-vs-byte issue: chunks from the Anthropic SDK are pre-decoded `str`, so we never see partial multi-byte sequences at chunk boundaries. If we ever switch to a raw-bytes transport (e.g. a custom Companion-LLM gateway), the design must decode-to-str before appending to either buffer, since AC over bytes would fragment Chinese characters.

**Latency-vs-safety tradeoff in `hold_window`**:

The hold window adds end-to-end first-byte latency equal to `hold_window / streaming_rate`. At 30 chars/sec, a 50-char hold adds ~1.7 s — *if* we treat it as a warmup period. The §10.4 reference implementation gets this right: it does NOT wait to fill the hold before releasing the first character. It releases as soon as `len(buffer) > BUFFER_SIZE`, i.e. it's a *sliding window of unreleased tail*, not a *warmup*. So the actual latency cost is:

> First byte arrives when the buffer first exceeds `hold_window`, then yields one character per chunk thereafter.

For a 50-char hold and Claude's typical first-chunk size, first-byte-to-user is ~50 chars (~1.5 s) behind first-byte-from-LLM. This is the latency penalty we pay for INV-PC-3 under PC-5, and it's the right trade.

If a character has very long hard_never literals (say 80+ chars — e.g. full sentences in the pattern list), `hold_window` must grow to match, and FTB latency grows linearly. **Recommendation**: cap individual `hard_never` literals at 40 chars by curation policy. Anything longer is almost certainly a regex pattern misclassified as literal.

---

## 3. The pre-filter's contract with step 9

The streaming pre-filter and the post-stream `AntiPatternFilter` must be **consistent under one input**: if a response would be rejected by step 9, the pre-filter must either have halted it earlier *or* the post-stream filter still catches it on the residual tail. The simplest way to guarantee this is for both to use **the same compiled `ahocorasick.Automaton`** for `hard_never` literals.

| Step | Filter | What it scans | What it does on hit |
|---|---|---|---|
| 8 (streaming) | Pre-filter (this doc) | Sliding scan window of recent chars, on each chunk arrival | Halt LLM stream, drop hold buffer, return `reroll` |
| 9 (post-stream) | `AntiPatternFilter.filter()` | Full final text | Return `FilterResult(passed=False, severity="hard")` |

The pre-filter handles the **fast path** for INV-PC-3 violations that would otherwise reach the wire. Step 9 handles:

1. The **regex** `forbidden_patterns`.
2. The **soft_never** stage-gated literals (warn only).
3. Any `hard_never` literal that landed entirely inside the final hold window and was therefore caught on the post-stream flush.

Case 3 is the failure-tolerant design: even if the pre-filter is somehow disabled or buggy, the post-stream filter still runs against the full text (which by then is in memory), and the response can be discarded before any byte ships. PCR-8 ("streaming does not retry already-sent content") is preserved because, on a step-9 catch, the hold buffer has not been flushed to the user yet — the post-stream filter runs on the flush boundary.

This means the **flush-on-stream-complete** path in step 8 must call into step 9 *before* releasing the final hold contents. The §10.4 reference (`yield buffer` at end without filter check) is a small spec gap — should be `await step_9.filter(released + buffer)` then yield only if pass. Worth noting in the implementation.

---

## 4. State and metrics

State held by the pre-filter for one turn:

- `scan_buffer`: `str`, the rolling detection window.
- `hold_buffer`: `str`, the unreleased tail.
- `released_offset`: `int`, characters already sent to the user (for offset-based match-position checks if we later switch to true incremental AC).
- A reference to the shared compiled `ahocorasick.Automaton`.
- A reference to the active `llm_stream` (for cancellation on halt).

State that survives the turn: none. The compiled automaton is per-(character_id, spec_version), built at composer startup and reused across turns/users.

Metrics (extending the §10.10 observability section):

| Metric | Cardinality | Purpose |
|---|---|---|
| `streaming_pre_filter.scanned_chunks` | total | Sanity: did the pre-filter actually run? |
| `streaming_pre_filter.halt_count` `{pattern_id, character_id}` | per pattern | Pattern-tuning alerting. >1 % halt rate for any pattern → review. |
| `streaming_pre_filter.halt_position_chars` (histogram) | distribution | How early do halts happen? Late halts = wasted LLM cost. |
| `streaming_pre_filter.scan_latency_ms` (p95, p99) | distribution | Verify < 5 ms budget. |
| `streaming_pre_filter.step9_caught_what_we_missed` | counter | If this is ever > 0 for `hard_never` literals, the pre-filter has a bug. |

Audit log on every halt:

```
event: streaming_pre_filter.halt
trace_id, character_id, spec_version
matched_pattern (literal)
chars_received_before_halt
chars_held_at_halt (must equal len(hold_buffer); never released)
reroll_count (passed to step-7 retry)
```

---

## 5. Failure modes and how the design handles them

| Failure | How it shows up | Mitigation |
|---|---|---|
| **Cross-chunk pattern split** | Pattern's first half in chunk N, second half in chunk N+1 | Scan buffer holds last `max_pattern_length + 32` chars — covered by Q3 invariant. |
| **Pattern longer than hold buffer** | Match detected but first chars already released | Pattern curation cap (40 chars). At ingest time, `AntiPatternFilter.__init__` should refuse / warn on literals longer than configured `hold_window`. Worth adding as a startup check. |
| **Reroll storm from bad pattern** | High halt-rate for one `pattern_id` | Per-pattern halt-rate metric + alert (§4 table). Manual deactivate via `soul_spec` override; no hot-fix in code. |
| **LLM stream doesn't terminate after halt** | Cost leak | On halt, must `await llm_stream.aclose()` (or equivalent for the Anthropic SDK's `AsyncStream.close()`). Verified by `step9_caught_what_we_missed` staying at 0 *and* `llm.tokens_used` not exceeding the halt position. |
| **Pre-filter exception mid-stream** | Stream stalls or skips filter | Wrap the per-chunk scan in try/except. On exception, log + skip pre-filter (do not halt). Step 9 still runs and catches violations post-stream — degraded but safe. |
| **Stream ends inside hold buffer with a violation** | Final flush would release violating bytes | Run step 9 against `released + hold_buffer` BEFORE flushing the hold. (Closes the §10.4 spec gap noted above.) |
| **Automaton hot-swap mid-stream** (spec deploy lands mid-turn) | Halt decisions inconsistent across the turn | Snapshot the automaton reference at stream start; do not refresh until the turn completes. Same model used by per-composition state (§4.1). |
| **Empty `hard_never` set** | No automaton built | Skip step 8 entirely; pass chunks through verbatim. Step 9 still runs (and is also a no-op). Saves the per-chunk scan cost. |

---

## 6. Recommendation summary

The three answers, in one line each:

1. **Incremental AC is feasible — and trivial if we reuse the existing `pyahocorasick.Automaton` and just re-scan a small rolling tail buffer on each chunk.** No custom state machine needed at our scale.
2. **Halt aggressively on any `hard_never` literal hit.** With the hold buffer in place, false positives cost backend dollars and seconds, not user-visible glitches — and `hard_never` is literal substring matching, so structural FP rate is zero (bad literals are a curation problem, not a filter problem).
3. **Two buffers, sized in chars, not tokens.** `scan_window = max_pattern_length + 32`, `hold_window = max(50, max_pattern_length)`. Cap individual `hard_never` literals at 40 chars by curation policy so first-byte latency stays bounded.

Coverage in the streaming filter is **`hard_never` literals only**. Regex `forbidden_patterns` and stage-gated `soft_never` stay with the post-stream full filter. Step 9 is the system of record for INV-PC-3; step 8 is the cheap gate that lets us keep streaming UX while honoring it.

The §10.4 reference loop is correct in shape but has one closeable spec gap: it must run step 9 against `released + hold_buffer` before the final flush, not yield the hold unconditionally. That should land in the implementation PR.
