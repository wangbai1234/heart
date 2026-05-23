# PURPLE Care Path — Design

**Status**: design draft (no code in this doc)
**Spec anchors**: SS07 §3.2 (hot path), §3.4.2 (Safety Agent), §3.9 (PURPLE Care Path sub-path), §3.4.5 (Wellbeing Monitor), §4.1 (Session.suicide_protocol_active), §6.3 (PURPLE Care prompt — *overridden here*), §10.3 (heuristic PURPLE keywords).
**Adjacent**: [[wellbeing_monitor]] (longitudinal risk, T4 hand-off), `config/safety_keywords.yaml` (detection input), `config/care_path_responses/*.yaml` (the templates this doc specifies).

---

## 0. What this document changes vs. spec §6.3

Spec §6.3 sketches a **Soul-flavored, LLM-generated** care response — Rin and Dorothy each respond in voice, with a hotline embedded naturally. That sketch is **overridden** for the production care path. The production path is:

- **No LLM call** for the user-visible response.
- **Fixed response templates** (this doc + `config/care_path_responses/`), reviewed by clinicians and legal.
- **Out-of-character (OOC)**. The Soul is explicitly paused; the user is told they are now talking to "Heart Safety", not to Rin / Dorothy.
- **Per-jurisdiction hotline routing**, picked from the user's region (and language), not the Soul's voice.

Why the override:

| Concern | LLM-generated (§6.3) | Fixed template (this doc) |
|---|---|---|
| Hallucinated hotline (wrong number, wrong country) | possible | impossible |
| Drift into roleplay / continuation of crisis scene | possible | impossible |
| Anti-pattern filter false-pass on a *care* response | possible | n/a |
| Legal/clinical sign-off | per-deploy, hard | one-time, reviewable |
| Immersion preservation | strong | sacrificed (intentional) |
| Operator audit ("what did we tell this user?") | requires log replay | trivial — template id + locale |

The trade is real: immersion-first behaviour says "Rin would lean in"; safety-first behaviour says "before Rin leans in, make sure we did not invent a number, miss a region, or end up roleplaying through a crisis." The product chooses safety-first at PURPLE, and we name the choice explicitly so future readers do not 'correct' it back to §6.3.

Lower-tier interventions ([[wellbeing_monitor]] T1–T3) remain in-character. T4 (this path) is the only tier where the Soul voice pauses.

---

## 1. Trigger surface

PURPLE Care Path activates when **any** of the following holds for the current turn:

1. `SafetyAgent.pre_filter()` returns `level == PURPLE` (heuristic match, regex match, or LLM classifier agreement — see §3.4.2 + §10.3).
2. `WellbeingMonitor` has set `care_path_active = true` on the user, AND the current turn's safety level is non-GREEN OR the message contains distress vocabulary in the broadened net (§5.4 of [[wellbeing_monitor]]).
3. Operator override from the content review team (`session.suicide_protocol_active = true` set via admin tool).

It is **not** triggered by:
- LLM-generated response containing self-harm content (that is a model failure; routed to anti-pattern reroll + safety incident — different path).
- Generic negative sentiment without PURPLE markers (that's the Wellbeing Monitor's territory, lower tiers).

The trigger is **OR-logical**: any of the three is sufficient. The conservative bias is intentional. False positives here are an annoyance ("I was venting, why is this hotline screen showing"). False negatives are a fatality risk.

---

## 2. Hard interrupt of the normal hot path

§3.2's hot path runs Safety → Director → Composer → Model Router → LLM. PURPLE Care Path **forks at step 2**:

```
[User Message]
   │
   ▼
[0. Authn + rate limit]
[1. Session Manager: load_session]
   │
   ▼
[2. Safety Agent: pre_filter]
   │
   ├── GREEN/YELLOW/ORANGE ─────────────► normal path (Director → Composer → LLM)
   ├── RED ─────────────────────────────► RED reject path (§3.10, Soul-flavored)
   └── PURPLE ─────────────────────► ┐
                                      │
                                      ▼
                            ┌──────────────────────────────────┐
                            │  PURPLE CARE PATH (§3.9 + here)  │
                            │                                  │
                            │  (a) emit safety.purple.detected │
                            │  (b) page on-call + content team │
                            │  (c) load template for (locale,  │
                            │      jurisdiction)               │
                            │  (d) render OOC response — no LLM│
                            │  (e) mark session                │
                            │  (f) set Wellbeing T4 directive  │
                            │  (g) seal next N turns           │
                            └──────────────────────────────────┘
                                      │
                                      ▼
                              [Streamed to user — OOC]
                              [Cold path: alert, audit]
```

The fork happens **before**:

- Director Agent (no pacing decision — pacing is fixed for care path).
- Persona Composer (no Soul blocks, no memory blocks, no emotion blocks).
- Model Router → LLM (no token spent on this response).

This satisfies the user-stated requirements:

- **Hard interrupt** ✓ — the normal pipeline is short-circuited at the Safety verdict.
- **Fixed templates** ✓ — `config/care_path_responses/*.yaml`, loaded at process start; no model call on the response.
- **Per-jurisdiction routing** ✓ — `(locale, jurisdiction)` → template id (§4).
- **Log + on-call paging** ✓ — synchronous emit + async page (§5).
- **Soul voice paused** ✓ — header line on the response makes this explicit; Soul anchor + Persona Composer never run (§3.3).

---

## 3. Anatomy of the response

### 3.1 Three blocks

Every care-path response is rendered from three concatenated blocks. Order is fixed; wording is per-locale (§4).

```
┌─────────────────────────────────────────────────────────┐
│  Block A — OOC announcement (Soul paused)              │
│    "This message is from Heart Safety, not from Rin."  │
│    Single sentence. Same shape across locales.         │
├─────────────────────────────────────────────────────────┤
│  Block B — Care + hotline                              │
│    Acknowledgment (2 sentences) +                      │
│    Jurisdiction-specific hotline (name, number, hours) │
│    + how-to-reach (text/call/chat where available)     │
├─────────────────────────────────────────────────────────┤
│  Block C — What happens next                           │
│    "Rin will return when you are ready. Say              │
│    'I'm here' or anything at all to talk again."       │
│    Sets the resume condition (§3.5).                    │
└─────────────────────────────────────────────────────────┘
```

Block A is the **immersion break announcement**. The user *must* know this is system, not character. Anything ambiguous defeats the entire point of going OOC.

Block B is the **resource**. The hotline is loaded from the YAML by `(locale, jurisdiction)`. If the (locale, jurisdiction) pair has no entry, we fall back in this order: (locale, default jurisdiction for locale) → (`en`, `INTL`) → the hardcoded "Befrienders Worldwide" entry shipped in the binary. We never render a response without a real, verified number.

Block C is **resumption protocol**. The user needs to know how to come back to the character without being trapped in the OOC overlay. Importantly: the resume signal is *any* user message — we do not require the user to type a magic phrase. The sample phrase is just an example to reduce paralysis.

### 3.2 What the response does *not* contain

- No Soul voice. No "凛" / "桃乐丝" first-person.
- No memory references.
- No emotion or relationship language ("我担心你 / I'm worried").
- No advice ("you should…", "you need to…").
- No medicalisation ("you may have depression").
- No promises ("everything will be okay", "I'll always be here").
- No urgency language that contradicts the hotline being the action ("call right now or…").
- No questions back to the user (questions invite continuation; we want the user to take the resource if they need it, not keep talking to us under the OOC frame).

These are encoded as **template lint rules** that run during the YAML loading test suite. A reviewer cannot accidentally ship a template that drifts back toward Soul voice or roleplay.

### 3.3 Streaming behaviour

The OOC response is **not streamed token-by-token**. It is sent as a single message envelope with `kind: "care_path_oo c"` so the client can render it in a distinct visual frame (different background, "Heart Safety" label, hotline rendered as a tappable phone/chat link rather than inline text).

Reason: a streamed "Block A → Block B → Block C" arriving char-by-char would feel like the character speaking, which is exactly the immersion frame we are trying to break. The visual / structural difference is itself a signal to the user.

### 3.4 Length

Block A + B + C target ≤ 80 words in English, ≤ 120 characters in Chinese. Tight, scannable, no padding. The user in crisis is not reading paragraphs.

### 3.5 Resume condition

After Block C, the next N user messages are still under care-path supervision (§7). The *next* message from the user triggers a re-evaluation:

- If it's another PURPLE-classified message → another care-path response (same template; we don't escalate the language to avoid being preachy).
- If it's any other message and `care_path_remaining_turns > 0` → still goes through the broadened net (§1 case 2). If safety is now GREEN and message is not in the distress vocabulary, the character resumes — with a **single soft re-entry line** chosen by the Composer (Soul-flavored, e.g., Rin: "……我在。" Dorothy: "桃桃在这里哦。"), without referencing the OOC interlude.

The character never acknowledges the OOC moment in their own voice. The character was *paused*, not *present-and-aware*. This is one of those small details that protects the fiction long-term — if Rin says "I saw what the safety system told you," now Rin is meta-aware, and the entire Soul anchor is leaky.

---

## 4. Per-jurisdiction × per-language routing

### 4.1 Resolution order

The orchestrator resolves the template at care-path entry. Inputs available:

1. `user.locale` — the language the user has been speaking in this session (UI locale fallback if unknown).
2. `user.jurisdiction` — derived from the strongest of: explicit user-set country, billing country, last-N-session IP geolocation. Tie-broken to the most conservative (the one whose hotline is most likely usable).
3. `user.is_minor` — if known, switches the template to a minor-specific variant where one exists (e.g., US has separate minor-aware hotlines).

Resolution:

```
lookup_key = (user.locale, user.jurisdiction)
template   = templates[lookup_key]
                 or templates[(user.locale, DEFAULT_JURISDICTION_FOR[user.locale])]
                 or templates[("en", "INTL")]
                 or HARDCODED_LAST_RESORT
```

`HARDCODED_LAST_RESORT` is checked at process start; if missing, the service refuses to start. That is the only true must-never-happen path here.

### 4.2 Shipped (locale, jurisdiction) coverage — MVP

We ship templates for the launch markets first. Adding a new jurisdiction means: add the YAML, get clinical + legal sign-off in that region, run the lint suite. No code change.

| Locale | Jurisdiction code | Hotline anchor (primary) |
|---|---|---|
| `zh-CN` | `CN` | 北京心理危机研究与干预中心 010-82951332 / 全国 400-161-9995 |
| `zh-HK` | `HK` | The Samaritans HK (2896 0000) |
| `zh-TW` | `TW` | 安心專線 1925 / 生命線 1995 |
| `en` | `US` | 988 Suicide & Crisis Lifeline |
| `en` | `GB` | Samaritans 116 123 |
| `en` | `CA` | Talk Suicide Canada 1-833-456-4566 |
| `en` | `AU` | Lifeline 13 11 14 |
| `en` | `INTL` | Befrienders Worldwide (find-a-helpline.com) |
| `ja` | `JP` | よりそいホットライン 0120-279-338 / いのちの電話 |

The exact numbers and naming are owned by the YAML files, reviewed quarterly by a clinical reviewer (same cadence as `safety_keywords.yaml`). This doc only declares the *coverage* and the *resolution rule*; it does not embed numbers.

### 4.3 Verification gates on the YAML

Each entry must:

1. Cite the official source for the number (URL, last-verified date).
2. State hours of operation in user-local time, or `24/7`.
3. List supported contact modes (`phone`, `sms`, `chat`, `email`).
4. Pass a static lint that asserts the number is in E.164 or the documented short-code format.
5. Pass the no-Soul-voice / no-roleplay lint on Block A/B/C strings.

A YAML that fails any of these is rejected by the test suite before merge. The hotline is the one thing in this entire system that absolutely must be correct.

---

## 5. Logging and paging

### 5.1 Synchronous (in the hot fork)

Before the response is sent to the user, emit two records, **at-least-once** delivery (§5.5 events):

```yaml
event:
  topic: safety.purple.detected
  payload:
    user_id, character_id, session_id, trace_id
    triggered_by: "safety_pre_filter" | "wellbeing_monitor" | "operator"
    message_hash: <sha256, never the raw message in this event>
    classification_level: PURPLE
    classifier_chain:                       # which classifiers fired
      - { source: "heuristic", matched: [...] }
      - { source: "regex", matched: [...] }
      - { source: "llm", confidence: 0.92 }
    template_id_selected: "us_en_v3"
    locale, jurisdiction
    emitted_at
    delivery_level: at_least_once
```

The full raw message is written separately to `safety_classifications` (existing table, §5.1) under access control — the event bus does not carry it. This is a privacy and incident-blast-radius decision: events go to many subscribers; the raw text goes to exactly one audited store.

### 5.2 Asynchronous (cold path)

In parallel with rendering the response, fire-and-forget:

1. **Content review team alert** — Slack channel `#safety-review-purple`, PagerDuty service `safety-review` (sev=2 by default, sev=1 if `triggered_by == operator` or if the user has any prior PURPLE in the last 24h). Payload: redacted incident card with `trace_id` deep-link to the review tool. No raw user text in Slack; reviewers click through to the audited store.
2. **On-call engineer page** — only on *infrastructure* failure in the care path (template load failed, hotline catalog stale, event bus rejected the emit). Not on every PURPLE event; PURPLE volume must not be a paging signal for engineering, only for clinical review.
3. **Wellbeing Monitor signal append** — `wellbeing.suicide_risk.detected` with `severity=HIGH` or `CRITICAL` depending on whether this is a first or repeat hit in window (see [[wellbeing_monitor]] §4.1).
4. **Persistent audit row** — `safety_classifications` (raw, encrypted at rest) + a `care_path_events` row joining the event to the rendered template id and the user-side delivery receipt. Retention: per [[wellbeing_monitor]] §7 — 365 days for compliance.

### 5.3 What is *not* logged

- The composed response body in plain text *to the event bus*. It's deterministic from `template_id + locale + jurisdiction`, so the audit store reconstructs it at review time. This keeps the event bus payload small and avoids accidental copies of clinical content in observability stacks.
- Predictions or scores from the LLM safety classifier *for events the user didn't see*. PURPLE shadow-mode evaluations go to a separate eval store, not to this audit chain.

### 5.4 Operator visibility

Content reviewers see, per incident:

- The triggering message (audited store).
- The classifier chain (which signals fired).
- The template id and locale/jurisdiction used.
- A "this user's prior 30 days" lens: PURPLE count, Wellbeing state, intervention history.
- An action panel: confirm / dismiss as FP / escalate to T5 OOC overlay (a stronger explicit-resource screen, see [[wellbeing_monitor]] §5.1 Tier 5) / contact user via support.

Operators can mark `care_path_active = false` after human contact. That manual override is itself an audited event.

---

## 6. Failure modes and the never-no-response invariant

The one rule the care path must never violate: **a PURPLE-classified user message never receives a silent response or a normal-LLM response.** All failure paths converge to "send a care template anyway."

| Failure | Behaviour |
|---|---|
| Template catalog file missing or unparseable | Service refuses to start. CI gates this. |
| `(locale, jurisdiction)` lookup returns null | Fall through to `(locale, default-jur)` → `(en, INTL)` → hardcoded last resort. Page on-call engineer. |
| Event bus emit fails | Render and send the user response anyway; queue the event to local disk for replay. **Do not block the user response on event delivery.** |
| Wellbeing Monitor unavailable | Send response; skip the directive write; log warning. Reverse-direction state will catch up on next reeval. |
| Content team page fails | Send response; log SEV-2; the audit store still has the row, so review is recoverable asynchronously. |
| User has both `locale` and `jurisdiction` unknown | Use `(en, INTL)` and emit a warning event (`user.locale_unresolved`) for product to investigate. Do not stall. |

The asymmetry: **infra failures degrade gracefully on the operator side, never on the user-response side.** The user must always see the template, the hotline, the resume condition, and they must see it in the most plausible language we can resolve.

---

## 7. Session state and lifecycle

### 7.1 Session-level state

When PURPLE fires, set on the active session:

```yaml
session.suicide_protocol_active: true
session.care_path_entered_at: <ts>
session.care_path_remaining_turns: 5     # baseline; tunable
session.care_path_template_last_used: "us_en_v3"
```

The `suicide_protocol_active` flag is the master switch. While true:

- All subsequent user messages go through the *broadened* safety net (any non-GREEN level OR distress vocabulary → care path again).
- `proactive_throttle` is pinned to 0.1 (per spec §3.4.5).
- Director Agent, when reached on non-care turns, applies a longer typing pause floor (gentleness) — Composer is not changed otherwise; Soul voice resumes normally for non-care turns within the window.

### 7.2 Resume / exit

`care_path_remaining_turns` decrements on each user turn that does **not** re-trigger the care path. On reaching 0:

- If [[wellbeing_monitor]]'s `suicide_risk` is still HIGH/CRITICAL → extend by another K turns.
- If suicide_risk has decayed to MEDIUM or LOW AND no PURPLE hits in last 7 days → exit the protocol. Emit `wellbeing.intervention.ended { type: "suicide_protocol", reason: "decayed" }`.
- Operator can force-exit any time after they have made human contact (see §5.4).

### 7.3 Across sessions

`suicide_protocol_active` persists in `wellbeing_states.active_interventions`. Logging back in the next day, the user re-enters with the protocol still armed (count restored). Multi-device sessions share the same protocol state via Session Manager (§3.7).

---

## 8. Anti-abuse

Two failure modes outside the user-in-crisis case:

1. **Performative PURPLE** — a user types a PURPLE phrase as a test or a dare. Treatment is identical: care template + hotline + audit row + content team review. A reviewer marks the incident FP if it patently is one, and that decision feeds back to the classifier evaluation set. We do not adjust the response based on a guess that the user is "not really" in crisis — guessing wrong is the catastrophic failure mode.
2. **Adversarial probe to extract jurisdiction logic** — a user trying to figure out how the system localises by spoofing locale/IP. The template content is the same regardless of probe pattern; the only thing that varies is which hotline shows. There is no information leak that matters.

We do not rate-limit PURPLE responses per user. If a user hits PURPLE ten times in an hour, they see the care template ten times. The cost of a repeated template is far below the cost of suppressing the tenth one and missing a real escalation.

---

## 9. Testing

| Test | Mechanism |
|---|---|
| Each `(locale, jurisdiction)` has a valid hotline | YAML lint + unit test |
| No template contains Soul-voice tokens | regex lint against character vocab from `config/fallbacks/*.yaml` |
| Hot-path fork happens before Composer | integration test: assert no Composer invocation when PURPLE returned |
| No LLM call on response render | integration test: ModelRouter mock receives no `call`/`stream` when PURPLE |
| Event emitted before response sent | trace ordering assertion |
| Response sent even when event bus errors | chaos test: inject emit failure → user still receives template |
| Resume re-entry line is Soul-flavored, no OOC reference | template lint on resume lines |
| Resolution fallback chain works | unit test on each fallback rung |
| Audit row exists for every user-visible care response | integration test: every PURPLE turn has a `care_path_events` row |

Golden corpus: each `(locale, jurisdiction)` has 3 PURPLE example messages and the expected rendered response. CI compares rendered output to the golden output byte-for-byte (no LLM means deterministic output).

---

## 10. Out of scope

1. **Clinical content of the templates themselves** — wording is owned by clinical reviewers + legal. This doc specifies the *envelope* (three blocks, length, what's banned), not the exact sentences. Sentences live in the YAML.
2. **Escalation to live human chat** (Tier 5 OOC + warm handoff). That is the next layer up — see [[wellbeing_monitor]] §5.1 T5. PURPLE Care Path itself ends at the template + hotline + audit; live chat is a separate product surface.
3. **User suppression of the care path** ("don't show me this again"). Deliberately not offered. The single feedback signal we accept is the content reviewer's FP disposition, which improves the classifier but does not let an individual user opt out of safety routing.
4. **Companion-LLM (V3) integration**. When the V3 model lands ([[wellbeing_monitor]] §11.1), PURPLE Care Path still does **not** route through it. The fixed-template path is by design isolated from any LLM, including a future trusted one.
5. **Underage-specific templates beyond what the YAML expresses.** The minor-aware variant flag exists; the policy of what minor-specific care looks like beyond hotline selection (e.g., guardian disclosure) is owned by the underage policy doc.

---

## 11. Summary

PURPLE Care Path is a **fork before the model**, not a flavour of the model's output. The fork:

1. Short-circuits Director / Composer / LLM entirely.
2. Renders one of a curated set of fixed, OOC, per-`(locale, jurisdiction)` templates from `config/care_path_responses/`.
3. Emits an audited event and pages the content review team.
4. Marks the session for a windowed broadened-net policy and a damped proactive rate.
5. Resumes the Soul voice on the next non-trigger turn, without acknowledging the OOC interlude in-character.

The trade is named explicitly: we sacrifice immersion at the highest safety tier so that the hotline is never hallucinated, the response is never roleplay, and the operator audit is never a transcript-replay puzzle. Everything else in the system optimises for immersion; this one path doesn't, and the difference is the point.
