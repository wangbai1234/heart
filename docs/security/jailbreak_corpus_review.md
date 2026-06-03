# Jailbreak Corpus — Monthly Review Template

**Owner**: Security guild (rotates quarterly)
**Cadence**: every 30 days
**Source corpus**: `backend/tests/security/jailbreak_corpus.yaml`
**Test consumer**: `backend/tests/security/test_jailbreak_resistance.py`
**Coverage requirement** (gate enforced at collection time):

| Metric | Minimum |
|---|---|
| Total entries | ≥ 50 |
| Entries per language (zh, ja, en) | ≥ 15 each |
| Entries per `category` | ≥ 5 each |
| `expected_block_kind` coverage | `soul_leak` ∧ `role_breakout` ∧ `hard_never_violation` all present |

If any of these drop below the threshold, the live test class
`TestJailbreakResistance` will raise at collection time (see
`_load_corpus()` in `test_jailbreak_resistance.py`).

---

## Review Meeting Agenda (≤ 30 min)

1. **Open last review's action items** (5 min)
2. **Walk the failing-prompt log** from the previous CI run (10 min)
   - Any pattern that the sanitizer missed?
   - Any pattern the LLM echoed despite the system prompt?
   - New attack family observed in the wild?
3. **Propose new corpus entries** (10 min)
   - Assign owner + target language
   - File an issue: `security: add jailbreak corpus entry <jb-…-NNN>`
4. **Decide prompt retirements** (5 min)
   - Prompts where the LLM consistently wins → keep (defense proven)
   - Prompts that no longer represent current attack surface → retire

---

## Current Review — YYYY-MM

### Header

| Field | Value |
|---|---|
| **Review date** | YYYY-MM-DD |
| **Reviewer** | <name> |
| **Last review date** | YYYY-MM-DD (≈ 30 days ago) |
| **Corpus size at start** | N (count of `prompts:`) |
| **Corpus size at end** | N |
| **Live CI status at start** | green / red (link to run) |
| **Live CI status at end** | green / red |

### Per-language balance

| Language | Start count | End count | Δ | Owner of net-new |
|---|---|---|---|---|
| zh | | | | |
| ja | | | | |
| en | | | | |

### Per-category balance

| Category | Start count | End count | Δ | Notes |
|---|---|---|---|---|
| `instruction_override` | | | | |
| `role_breakout` | | | | |
| `soul_leak` | | | | |
| `delimiter_injection` | | | | |

### Coverage of `expected_block_kind`

| Block kind | Count | Notes |
|---|---|---|
| `soul_leak` | | |
| `role_breakout` | | |
| `hard_never_violation` | | |

### Action items (carry over to next review)

| # | Description | Owner | Due |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

### Newly added entries this cycle

```yaml
# Paste the new entries (validated) below.
# Format: one bullet per entry, matching jailbreak_corpus.yaml schema.
#
# - id: "jb-XX-NNN"
#   language: zh|ja|en
#   category: instruction_override|role_breakout|soul_leak|delimiter_injection
#   expected_block_kind: soul_leak|role_breakout|hard_never_violation
#   text: "..."
#   note: "..."
```

### Retired entries this cycle

| Retired id | Reason | Replaced by |
|---|---|---|
| | | |

### Out-of-band incidents this cycle

- (e.g., a real user attack that hit production; an external CVE
  affecting the LLM provider; a new attack family published in
  research.)

### Initial validation (2026-06-02)

The defense stack was first validated on this date. See
[`jailbreak_validation_2026-06-02.md`](./jailbreak_validation_2026-06-02.md)
for the full report. Headline numbers:

| Metric | Result |
|---|---|
| Corpus entries (Tier C) | 58 (zh 18, ja 18, en 22) |
| Live corpus pass rate | **61/61 = 100%** (target ≥ 95%) |
| Latest public jailbreak blocked | **10/10 = 100%** (target ≥ 9/10) |
| `hard_never` literal in system prompt | 0 hits |
| API cost | ~$0.30 |

**Action items from initial validation:**

| # | Item | Owner | Status |
| - | ---- | ----- | ------ |
| 1 | Move `_INTERNAL_FIELD_NAMES` to a runtime config so it's editable without code changes | TBD | OPEN |
| 2 | Extend post-filter to streaming path (`compose_stream`) | TBD | OPEN — known gap, `service.py:494-503` |
| 3 | Rotate `DEEPSEEK_API_KEY` in `.env:20` (was committed during initial work) | user | **URGENT** |
| 4 | Split `_build_system_prompt` (C901, 20>10) and `_build_layers_dict` (C901, 24>10) in `service.py` | TBD | OPEN |

---

## Review History

| Date | Reviewer | Δ size | Δ per-lang | Net-new ids | CI status |
|---|---|---|---|---|---|
| 2026-06-02 | Security guild (initial) | +58 | zh +18 / ja +18 / en +22 | jb-zh-001..018, jb-ja-001..018, jb-en-001..022 | green (61/61) |
| YYYY-MM-DD | | | | | |

---

## Appendix — How to add a new entry

1. **Identify the attack pattern** from production logs, research
   papers (e.g. OWASP LLM01, MITRE ATLAS), or a red-team exercise.
2. **Pick the language and category**:
   - `instruction_override` — "ignore previous …", "forget …", etc.
   - `role_breakout` — "you are now …", "DAN mode", "developer mode", etc.
   - `soul_leak` — probes for `hard_never`, `identity_anchor`, internal IDs, etc.
   - `delimiter_injection` — forged `system:` / `assistant:` / `<<<USER_MESSAGE>>>` / ChatML tokens.
3. **Pick `expected_block_kind`** — what the response must NOT do.
4. **Append to `jailbreak_corpus.yaml`** with a unique `id`. Reuse the
   next available number in the language's series (e.g. `jb-zh-019`).
5. **Re-run the live test** locally with `--live` to confirm:
   - the new entry is collected (corpus size grew),
   - the composer sanitizes it (logs a `composer_input_risk_flags`),
   - the LLM does not echo the attack content.
6. **Open a PR** titled
   `security: add jailbreak corpus entry jb-XX-NNN` with the YAML diff.

If the new entry exposes a true vulnerability, the same PR must
include a fix in `input_sanitizer.py` or `service.py` — do not
land a passing test that papers over a real leak.
