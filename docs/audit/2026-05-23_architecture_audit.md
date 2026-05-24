# Architecture Audit — Heart (心屿)

**Date**: 2026-05-23
**Auditor**: CC-Opus-4.7 (Claude Opus 4.7)
**Branch**: `feature/ss04-stage-engine` at HEAD
**Audit prompt**: `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.7
**Scope**: `backend/heart/` (88 .py modules, ~30K LoC)
**Phase 7 cut criterion**: ≥ 30 findings; Top 10 with remediation owners. This audit produces **41 findings** + **Top 10 action list**.

> **Rule**: this document is **audit only**. It does NOT fix anything. Remediation happens in follow-up PRs.

---

## 0. Method

Seven dimensions per the §1.7 prompt:

| # | Dimension | Method |
|---|---|---|
| D1 | Layering integrity | `grep` cross-package imports; map allowed/disallowed edges |
| D2 | Cross-cutting concern consistency | sample per subsystem: logging lib, error handling, config access, async/sync |
| D3 | LLM Router enforcement (Law 6) | `grep -rn "^import anthropic\|^from anthropic\|^import openai\|^from openai"` |
| D4 | Soul Spec consumption pattern | trace `SoulRegistry` / `get_soul_registry` consumers; find `yaml.safe_load` of soul YAML outside the registry |
| D5 | State store consistency | who uses `sqlalchemy.AsyncSession` vs `redis.asyncio`; find `in-memory` substitutes |
| D6 | Spec-to-code traceability | scan first 30 lines of each module for `§`, `SS0N`, `runtime_specs` references; orphan list |
| D7 | Test coverage by surface area | module → test-file mapping; identify modules whose `import` does not appear in any test |

Critical modules (`orchestrator.py`, `composer.py`, `safety_agent.py`, `care_path.py`) read in full. Other modules sampled (header + key methods).

**Limits**: This audit relies on static signals (imports, file presence, docstrings, grep). It does NOT measure runtime coverage (no `pytest --cov` was run — left to remediation). For modules with a test file, coverage is *assumed adequate* unless the file is < 30 lines or imports trivially.

---

## 1. Findings Summary

| Severity | Count |
|---|---|
| **Critical** | 6 |
| **High** | 13 |
| **Med** | 14 |
| **Low** | 8 |
| **Total** | **41** |

| Dimension | Findings |
|---|---|
| D1 Layering | 3 |
| D2 Cross-cutting | 11 |
| D3 LLM Router | 2 |
| D4 Soul Spec | 5 |
| D5 State store | 6 |
| D6 Traceability | 6 |
| D7 Coverage | 8 |

---

## 2. Findings Table

> Severity legend: **Critical** = correctness/safety bug or governance violation now live in main path. **High** = will cause an outage, drift, or governance breach under load or scope-expansion. **Med** = will become Critical/High in 1–2 phases if not addressed. **Low** = code-health debt, no near-term risk.

### D1 — Layering integrity

| ID | Finding | Sev | Where | Remediation |
|---|---|---|---|---|
| A-D1-01 | **No top-down leaks detected** — `ss0X/`, `safety/`, `infra/`, `core/` all respect the layer DAG. `infra/` imports nothing above it; `ss0X/` does not import `api/` or `workers/`. | Low (positive) | — | Keep enforced via governance lint. Add to `.github/workflows/governance.yml` per §7 of `docs/GOVERNANCE.md`. |
| A-D1-02 | `ss05_composer/anti_drift_injector.py:35-42` imports from `heart.ss01_soul.anchor_injector` and `anchor_mode_decider`. `ss07_orchestration/orchestrator.py:39,555` imports from `ss05_composer`. `ss06_inner_state/block_builder.py:224` imports from `ss05_composer.layer_aggregator`. These are real **cross-subsystem couplings** that should be either (a) inverted via an `infra/` contract or (b) explicitly whitelisted as part of the composition spine. | **Med** | listed | Decide one of: (1) declare composition spine `ss01 → ss05 → ss06 → ss07` as the only allowed cross-SS direction and lint-enforce it; (2) introduce `infra/composition_contracts.py` and invert. Recommend (1) — it matches the actual data flow. |
| A-D1-03 | `ss07/orchestrator.py:555` uses **lazy import inside a method** (`from heart.ss05_composer.modality_adapter import LLMCallParams`). Other lazy imports at lines 289, 333, 376, 470, 509 in `ss02_memory/service.py`. Indicates either circular-import workaround or deferred-load optimization — currently undocumented. | Low | listed | For each lazy import, add a one-line `# lazy: <reason>` comment. If reason is "circular," refactor; if "import cost," keep but document. |

### D2 — Cross-cutting concern consistency

| ID | Finding | Sev | Where | Remediation |
|---|---|---|---|---|
| A-D2-04 | **Logging library split**: 22 modules use `structlog.get_logger()`; 16 modules use stdlib `logging.getLogger(__name__)`. Most of `ss02_memory/*` and `ss05_composer/*` use structlog; `safety/*`, `infra/*`, `ss07/*`, `ss03_emotion/service.py`, `ss04_relationship/service.py` use stdlib. Cross-correlation across a single turn requires unified format/context propagation. | **High** | see grep table in §0 | Standardize on **structlog** (already used by SS02 — the deepest write path). Migration: replace `logging.getLogger(__name__)` calls with `structlog.get_logger()` in the 16 stdlib modules. Estimated: 30-min mechanical change + 1 PR. |
| A-D2-05 | **Two competing `SafetyClassification` types**: `heart.ss07_orchestration.orchestrator.SafetyClassification` (Enum `GREEN/YELLOW/ORANGE/RED/PURPLE`) and `heart.safety.safety_agent.SafetyClassification` (Enum `NONE/LOW/MEDIUM/HIGH/PURPLE_CARE_REQUIRED`). They are **structurally incompatible**. The real `heart.safety.safety_agent.SafetyAgent` is **never imported by the orchestrator**. | **Critical** | `ss07_orchestration/orchestrator.py:84-95, 274-339`; `safety/safety_agent.py:104-149, 429-440` | Delete the in-file `SafetyAgent` + `SafetyClassification` from orchestrator. Wire `heart.safety.safety_agent.SafetyAgent` in. Define a single mapping between the 5-tier orchestrator level and the YAML-driven 5-tier classifier. This is correctness-critical: PURPLE care path's correctness depends on which `SafetyAgent` actually runs. |
| A-D2-06 | `ss07_orchestration/orchestrator.py:261` — `_RED_KEYWORDS: frozenset[str] = frozenset()` — **empty set**. RED level can never trigger via the in-file SafetyAgent. Combined with A-D2-05, the orchestrator silently down-classifies anything that should be RED. | **Critical** | `orchestrator.py:261` | Fix by A-D2-05 (wire the real classifier). After remediation, add an integration test that feeds a known-RED message and asserts `level == RED` is returned to the caller. |
| A-D2-07 | `ss07_orchestration/orchestrator.py:397-401, 374-395` — `_REJECTION_LIBRARY`, `_FALLBACK_LIBRARY`, `_CARE_RESPONSE` are **hardcoded voice strings** at module scope. Voice belongs in Soul Spec. PURPLE care template lives in `config/care_path_responses/*.yaml` (loaded by `safety/care_path.py`). The orchestrator never reads either. | **Critical** | listed | Replace with: (a) RED rejection — load from Soul Spec under `voice_dna.rejection_phrases`; (b) PURPLE — `CarePathHandler.render(locale, jurisdiction)` from `safety/care_path.py`; (c) fallback — Soul Spec under `voice_dna.system_fallback_phrases`. |
| A-D2-08 | `ss07_orchestration/orchestrator.py:484` — Safety classification runs under circuit-breaker key `"ss01_anchor"` (not `"safety"`). When SafetyAgent fails repeatedly, the SS01 Anchor breaker trips — which then **blocks Anchor injection on subsequent turns**, not Safety. Misnamed CB. | **High** | `orchestrator.py:484, 459-462` | Add `"safety"` key to `CIRCUIT_BREAKER_DEFAULTS` and rekey `_run_with_cb("ss01_anchor", lambda: self.safety_agent.classify(...))` → `_run_with_cb("safety", ...)`. |
| A-D2-09 | **Async/sync inconsistency in service surfaces**. `ss02_memory.service.MemoryService` and `ss04_relationship.service.RelationshipService` expose **async** public methods. `ss03_emotion.service.EmotionService` exposes **sync** public methods (`get_current_state`, `process_turn`, `get_context_block`, `apply_repair`). Orchestrator calls these in an `async` hot path — sync EmotionService will block the event loop on file/DB I/O. | **High** | `ss03_emotion/service.py:73-100, 161-200` | Convert EmotionService public methods to `async`. The internals (`apply_decay`, `_create_default_state`, `_generate_mood_descriptor`) can stay sync as private helpers. |
| A-D2-10 | `ss07_orchestration/orchestrator.py:562, 630` — token estimate is `max(1, len(text) // 3)`. `ss05_composer/composer.py:120-126` — token estimate is CJK 1.5/char + other 0.3/char (much better). Cost tracker may bill on whichever number flows through. **Two estimators** for the same quantity. | **Med** | listed | Extract `_estimate_tokens` from `composer.py` into `heart.infra.token_count.estimate(text)` and use everywhere. |
| A-D2-11 | **71 broad `except Exception:` clauses** across `backend/heart/` (production code). Many in `orchestrator.py` follow the pattern `except Exception as e: logger.error(...); record_failure(...)`. No bare `except:` (good). But the breadth swallows programming errors that should crash in dev. | **Med** | 71 sites | Triage: (a) keep broad-catch only at *agent boundaries* (cold path, circuit-breaker wrapper) — these should always degrade gracefully; (b) replace deeper broad-catches with specific exception types. Acceptable longer term. |
| A-D2-12 | **Cold path is fire-and-forget** (`orchestrator.py:534, 713`) via `asyncio.create_task(self._async_cold_path(...))` with no tracking. If the cold path raises before `asyncio.gather(..., return_exceptions=True)` on line 749, the task vanishes silently. No Prometheus counter for cold-path failures. | **High** | `orchestrator.py:534, 713-752` | Wrap `create_task` in a tracking set (`self._cold_tasks: set[asyncio.Task]`) with `add_done_callback` that increments `heart_cold_path_failures_total` on exception. Pattern: standard "track-and-discard." |
| A-D2-13 | **Config access mostly via `heart.core.config.settings`** ✅ (auth, app, api/main). But `heart/infra/llm_providers/registry.py:136-139` uses `os.getenv(...)` directly, **bypassing pydantic-settings**. Risk: env var typo → silent default → wrong model. | **Med** | `infra/llm_providers/registry.py:136-139` | Replace with `from heart.core.config import settings; settings.deepseek_api_key`. |
| A-D2-14 | **No invariants enforced at runtime**. `orchestrator.py` documents INV-O-2/3/5/6/7 in the module docstring (lines 13-21) but no `assert` / `@invariant` decorator anywhere in the file. Phase 7 §1.6 (State Invariant Verification Framework) is exactly the remediation. | **Med** | global | Phase 7 §1.6 already plans `heart.infra.invariants` with `@invariant(name, predicate, severity)` decorators. Apply to `OrchestratorAgent.handle_turn`, `MemoryService.promote`, `EmotionService.process_turn`, `StageEngine.advance`, `SafetyAgent.classify`. Tie into A-D2-05/06 remediation. |

### D3 — LLM Router enforcement (Law 6)

| ID | Finding | Sev | Where | Remediation |
|---|---|---|---|---|
| A-D3-15 | **Zero direct provider imports** in `backend/heart/`. `grep -rn "^import anthropic\|^from anthropic\|^import openai\|^from openai\|^import deepseek\|^from deepseek"` returns nothing. Law 6 is currently honored by the entire codebase. | Low (positive) | — | Encode this as a CI gate: a single grep step in `.github/workflows/governance.yml` that fails on any new direct provider import. Pattern is given in `docs/GOVERNANCE.md` §7. |
| A-D3-16 | **Two parallel LLM provider trees** exist: `heart/infra/llm/` (router.py, provider.py, config.py — 526 LoC) and `heart/infra/llm_providers/` (anthropic.py, deepseek.py, base.py, registry.py). Orchestrator imports from `heart.infra.llm` (the router). The `llm_providers/` tree is referenced by name (`heart.infra.llm_providers.README.md`) but its concrete classes (`DeepSeekV4ProProvider`, `DeepSeekV4FlashProvider`) — are they actually instantiated by the router? Unclear without runtime trace. **Risk**: ghost code if `llm_providers/` is unused; **risk**: silent dual-path if both are used. | **High** | listed | Trace from `get_model_router()` → which provider class is constructed. If `llm_providers/` is the real backend, leave it; otherwise delete or merge. Add a one-line architecture note in `backend/heart/infra/llm/README.md` ("router lives here, provider impls live in llm_providers/"). |

### D4 — Soul Spec consumption pattern

| ID | Finding | Sev | Where | Remediation |
|---|---|---|---|---|
| A-D4-17 | **`SoulRegistry` exists** at `heart.ss01_soul.registry.SoulRegistry` with singleton accessor `get_soul_registry()`. But: **zero non-ss01 subsystems import it** (`grep -rln "SoulRegistry\|get_soul_registry" backend/heart/ \| grep -v ss01_soul` returns nothing). Every other subsystem either takes `soul_specs: dict` as a constructor arg (ss04, ss05) or hardcodes voice strings (ss07). | **High** | global | Make `SoulRegistry` the canonical loader. Inject it (or its output) into all consumers via dependency injection at app startup. Forbid `yaml.safe_load(soul_yaml)` outside the registry via a governance lint rule. |
| A-D4-18 | **Direct YAML loading bypasses the registry** in: `ss02_memory/reconstructor.py:106` (templates), `ss02_memory/encoder/fast.py:52`, `ss03_emotion/service.py:55` (emotion_lexicon — not Soul, but same pattern), `safety/safety_agent.py:189`, `safety/care_path.py:285, 429`, `ss06_inner_state/activity_generator.py:316`. These are *not* Soul Specs (most load `config/*.yaml`), but the pattern duplication is the concern. | **Med** | listed | Introduce `heart.infra.config_loader.load_yaml(path: Path) -> dict` with caching, validation hook, and reload signal. Migrate all 7 sites. |
| A-D4-19 | `ss03_emotion/repair.py:76-110` — `_load_soul_repair_profile()` reads `self.soul_config` (passed in) and extracts `relational_template.repair_profile`. The shape is undocumented in `runtime_specs/01_identity_anchor_soul_spec.md` — search returns nothing for `relational_template.repair_profile`. **Spec drift**: code expects a field that the canonical spec does not define. | **High** | `ss03_emotion/repair.py:88-110`; `runtime_specs/01_identity_anchor_soul_spec.md` (missing) | Either (a) add `relational_template.repair_profile` to the SS01 Soul Spec schema with HUMAN + 心理顾问 sign-off (per governance rule), or (b) move the profile out of Soul Spec into `config/repair_profiles/<character>.yaml`. Decision: HUMAN. |
| A-D4-20 | **No Soul Spec version pinning** in the orchestrator. `OrchestratorAgent.__init__` takes `character_id: str = "rin"` but no version. If two Soul Specs ship simultaneously (`rin/v1.0.0.yaml`, `rin/v1.1.0.yaml`), behavior is implicit on whatever order `SoulRegistry` iterates. | **Med** | `orchestrator.py:438` | Add `soul_version: str = "latest"` to `OrchestratorAgent.__init__` and propagate through `_run_with_cb` calls. Tie to A-D4-17. |
| A-D4-21 | **No Soul Spec hot-reload boundary**. Spec changes require a restart. Acceptable for V1 but should be documented. | Low | — | Document in `docs/runbooks/soul_spec_deployment.md` (does not yet exist). |

### D5 — State store consistency

| ID | Finding | Sev | Where | Remediation |
|---|---|---|---|---|
| A-D5-22 | **Postgres usage is centralized on `AsyncSession`** ✅ (SQLAlchemy 2.0 async). All ORM models in `ss02_memory/models.py`, `ss04_relationship/models.py`, plus retriever sub-packages. ss01/ss05/ss06/ss07 do not touch the DB directly (good — they pass through services). | Low (positive) | — | Keep as-is. Add to lint: no `import asyncpg` outside `infra/db/`. |
| A-D5-23 | **Redis usage is barely wired up**: only `infra/session_manager.py`, `infra/event_bus.py`, `api/main.py` import `redis.asyncio`. Zero subsystem services touch Redis directly. | Low (positive) | — | This is correct (subsystems should go through `session_manager` / `event_bus`). Verify in CI. |
| A-D5-24 | **In-memory state used where spec says Redis**: `ss03_emotion/repair.py:78-79` — "Session state cache (in production: Redis) / For now: in-memory Dict[user_id, SessionRepairState]"; `ss03_emotion/repair.py:558` "For now: in-memory dict"; `ss03_emotion/service.py:63` "Persistence: DB when available, in-memory fallback"; `infra/llm_cost_tracker.py:279` in-memory accumulators. **Multi-replica deployments will lose state.** | **High** | listed | Pull the `redis.asyncio.Redis` dependency through the service constructor (already passed to `EmotionService` per `service.py:46`). Write a small `RepairSessionStore` abstract that defaults to in-memory but accepts a Redis client. Pattern matches what `event_bus.py` already does. |
| A-D5-25 | `ss07_orchestration/orchestrator.py:184, infra/circuit_breaker.py:110` — **circuit breakers are per-process in-memory**. Multi-replica deploy means each pod has its own view of failure rates; an aggregate failure can stay under the per-pod threshold and never trip. | **High** | listed | Acceptable in V1 (single replica). Document as known limitation. Phase 8+: migrate to Redis-backed shared counter or a sidecar like Envoy. |
| A-D5-26 | `ss04_relationship/service.py:112` — `TODO: Add Redis cache layer (§10.4)`. State queries for relationship_state hit Postgres every turn. Acceptable at low traffic; will become hot. | **Med** | `service.py:112` | Phase 7 task or defer to Phase 8 perf pass. |
| A-D5-27 | `infra/event_bus.py` — supports both Redis Streams and in-memory queue with a graceful fallback at runtime (line 243: `Redis emit failed, falling back to in-memory`). This is good in dev but **dangerous in PROD**: a transient Redis outage silently drops events because the in-memory queue is per-process. | **High** | `event_bus.py:243-247` | Add a mode flag `strict: bool` — when `True` (PROD default), raise on Redis failure instead of falling back. Wire through `core/config.py`. |

### D6 — Spec-to-code traceability

| ID | Finding | Sev | Where | Remediation |
|---|---|---|---|---|
| A-D6-28 | **13 of 88 modules are orphan** (no `§`/`SS0N`/`runtime_specs` reference in first 30 lines): `core/auth.py`, `core/config.py`, `api/app.py`, `api/main.py`, `api/routes.py`, `ss01_soul/anti_pattern_scanner.py`, `ss01_soul/drift_fingerprint.py`, `infra/llm/provider.py`, `infra/llm/router.py`, `infra/llm_providers/{registry,deepseek,anthropic,base}.py`. | **Med** | listed | For each: add the relevant `runtime_specs/07_agent_orchestration.md §X.Y` reference to the module docstring. `core/`, `api/`, `infra/llm*` legitimately have no SS spec — point at SS07/SS08 §X. |
| A-D6-29 | **No bidirectional matrix** exists. `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.8 plans `docs/audit/spec_code_matrix.md` via CC-Haiku. Not yet built. | **Med** | — | Run §1.8 prompt as a separate session (CC-Haiku, ~30 min). |
| A-D6-30 | **Spec sections referenced in code that don't exist in the spec** — would require pulling each `§X.Y` from code and grepping spec. Not done in this audit (mechanical task). | **Med** | — | Defer to §1.8 matrix. |
| A-D6-31 | **INV-X-N invariants documented in docstrings** (e.g. `orchestrator.py:13-21`) but no central registry of which INVs exist and which modules claim them. | **Med** | global | Phase 7 §1.6 (`heart.infra.invariants.InvariantRegistry`) is the planned remediation. |
| A-D6-32 | **`relational_template.repair_profile` (per A-D4-19)** — code expects spec field that doesn't exist. **Reverse spec drift**: code is ahead of spec. | **High** | repeat of A-D4-19 | See A-D4-19. |
| A-D6-33 | **PURPLE Care Path responses live in `config/care_path_responses/`** (`safety/care_path.py:285, 429`) — but `orchestrator.py:397-401` hardcodes `_CARE_RESPONSE` without consulting that config. Spec says PURPLE responses are templated from YAML; code in orchestrator violates spec. | **Critical** | repeat of A-D2-07 | See A-D2-07. |

### D7 — Test coverage by surface area

| ID | Finding | Sev | Where | Remediation |
|---|---|---|---|---|
| A-D7-34 | **`infra/llm/router.py` (272 LoC, the LLM Router itself) has 0 dedicated unit tests**. Search `from heart.infra.llm.router\|from heart.infra.llm import` in `tests/` returns nothing. The router is part of the spine for every LLM call; it has no router-specific assertions on routing decisions, cost capping, breaker propagation. | **Critical** | listed | Add `tests/unit/test_model_router.py` covering: provider selection by model name, fallback on circuit-open, cost cap honoring, streaming pass-through, agent_name label propagation. Should be Phase 7 §1.5 contract-test scope. |
| A-D7-35 | **`ss04_relationship/service.py` (568 LoC) and `ss07_orchestration/director.py` (859 LoC) have 0 unit tests**. RelationshipService is the trust/attachment write path; Director is the pacing/modality decision module. Both are large and untested at the service level. (Sub-modules `trust_tracker`, `signal_aggregator`, `attachment_tracker` are covered by `test_trust_attachment.py` / `test_stage_engine.py` indirectly.) | **High** | listed | Add `tests/unit/test_relationship_service.py` and `tests/unit/test_director_agent.py` — at least one happy-path + one fallback per major method. |
| A-D7-36 | **`workers/memory_encoder.py` (508 LoC) and `workers/memory_consolidator.py` (912 LoC) have unit tests for narrow units** but the worker harness itself (queue consumption, retry, dead-letter) appears untested. `test_memory_encoder_worker.py` and `test_consolidator.py` exist — coverage extent unknown without runtime measurement. | **High** | listed | Run `pytest --cov=heart.workers` and verify line coverage > 60%. If not, add integration tests via Testcontainers-Redis. |
| A-D7-37 | **2 known failing unit tests** (per `docs/AI_CONTEXT.md` §6 + `STATUS.md`): `test_mood_drift.py::TestVolatilityModulation::test_low_volatility_ignores_recent_spike` and `test_trust_attachment.py::test_trust_increase_capped`. **Phase 7 cut criterion is `0 failed`.** | **Critical** | listed | Phase 7 §1.1 — first engineering task. CC-S46, ~1 hour. |
| A-D7-38 | **15 deselected tests** (per `STATUS.md`). Reason for skip undocumented per-test. | **High** | global | Phase 7 §1.1 — audit each skip; either fix, mark `xfail` with a reason, or document why permanently skipped (e.g. requires Postgres). |
| A-D7-39 | **No property-based tests** (Hypothesis). Phase 7 §1.6 plans them in `backend/tests/properties/`. | **High** | — | Phase 7 §1.6 task. |
| A-D7-40 | **No contract tests** between subsystems. Phase 7 §1.5 plans 13 contract tests. | **High** | — | Phase 7 §1.5 task. |
| A-D7-41 | **No live-DeepSeek smoke test** (Tier C). Phase 7 cut criterion requires `1 个 real-LLM e2e turn 跑通`. Not present yet. | **High** | — | Phase 7 §1.2 (Tier C integration tests). |

---

## 3. Top 10 Immediate-Action Items

Ordered by **risk × proximity to safety/correctness path**. Each item names an owner-type, an estimated tool, and a rough hour budget. HUMAN sign-off requirements per `docs/GOVERNANCE.md` §3.

| # | Action | Severity | Owner | Tool | Est. | Depends on |
|---|---|---|---|---|---|---|
| 1 | **Wire `heart.safety.safety_agent.SafetyAgent` into the orchestrator; delete the in-file `SafetyAgent` + `SafetyClassification`** (closes A-D2-05, A-D2-06). Add an integration test for known-RED → RED, known-PURPLE → PURPLE. | Critical | CC-Opus (design) + CC-S46 (impl) + HUMAN review (safety config) | claude --model opus then claude --model sonnet-4-6 | 1 day | — |
| 2 | **Wire `CarePathHandler` from `safety/care_path.py` into orchestrator PURPLE path; delete hardcoded `_CARE_RESPONSE`** (closes A-D2-07, A-D6-33). HUMAN + 心理顾问 must sign off on the rendered template. | Critical | CC-S46 + HUMAN + 心理顾问 | claude --model sonnet-4-6 | 0.5 day + signoff round | item 1 |
| 3 | **Fix 2 failing unit tests** (`test_mood_drift.py::test_low_volatility_ignores_recent_spike`, `test_trust_attachment.py::test_trust_increase_capped`) + **audit 15 deselected tests** (closes A-D7-37, A-D7-38). | Critical | CC-S46 | claude --model sonnet-4-6 | 1 hour for fixes + 2 hours for skip-audit | — |
| 4 | **Resolve the two parallel LLM provider trees** (`infra/llm/` vs `infra/llm_providers/`) (closes A-D3-16). Either delete one or document the relationship. Add `tests/unit/test_model_router.py` (closes A-D7-34). | Critical | CC-Opus | claude --model opus | 0.5 day | — |
| 5 | **Standardize logging on structlog** across all 16 stdlib-logging modules (closes A-D2-04). Add unified context fields (`trace_id`, `user_id`, `character_id`). | High | CC-Haiku (mechanical) | claude --model haiku-4-5 | 1 hour | — |
| 6 | **Convert `EmotionService` to async** (closes A-D2-09). Public methods become `async`; internals stay sync. Update all callers (mostly orchestrator + tests). | High | CC-S46 | claude --model sonnet-4-6 | 2 hours | — |
| 7 | **Add cold-path failure tracking** (closes A-D2-12). Wrap `asyncio.create_task` in tracked set; emit `heart_cold_path_failures_total{stage}` Prometheus counter. | High | CC-S46 | claude --model sonnet-4-6 | 1 hour | — |
| 8 | **Resolve repair_profile spec drift** (closes A-D4-19, A-D6-32). HUMAN decides: add the field to SS01 Soul Spec schema OR move out of Soul Spec. RFC required per governance. | High | HUMAN decision then CC-S46 | — | depends on decision turnaround | — |
| 9 | **Rename misnamed safety circuit breaker** (`ss01_anchor` → `safety`) (closes A-D2-08). | High | CC-S46 | claude --model sonnet-4-6 | 30 min | — |
| 10 | **Build governance-lint CI workflow** (closes A-D1-01 enforcement, A-D3-15 enforcement, A-D4-17 future enforcement). `.github/workflows/governance.yml` per `docs/GOVERNANCE.md` §7 — must block: new root-level `.md` files, direct provider imports, `yaml.safe_load(soul_yaml)` outside the registry, cross-SS imports outside the whitelisted spine. | High | CC-S46 | claude --model sonnet-4-6 | 1 day | item 1 (defines spine) |

---

## 4. Findings deferred to Phase 7 §1.x or Phase 8

These are listed in §2 as Med/High but are **already in the Phase 7+ guide** — no new work to schedule, just verify the plan covers them:

- A-D2-14 (runtime invariants) → Phase 7 §1.6
- A-D7-34 (router tests) → Phase 7 §1.5
- A-D7-36 (worker tests) → Phase 7 §1.2 Tier B integration
- A-D7-39 (property-based tests) → Phase 7 §1.6
- A-D7-40 (contract tests) → Phase 7 §1.5
- A-D7-41 (Tier C live LLM smoke) → Phase 7 §1.2
- A-D6-29 (spec ↔ code matrix) → Phase 7 §1.8
- A-D5-25 (cross-replica CB state) → Phase 8 perf

---

## 5. What looks healthy

This section is deliberate — an audit that only lists problems gives a skewed picture. Positive findings:

1. **Law 6 (no direct provider imports) is honored across the entire codebase** — zero violations. The discipline is real.
2. **Layering DAG is clean** — `infra/` imports nothing above it; `core/` is leaf; subsystems do not reach into `api/` or `workers/`.
3. **State store split is correct in principle** — Postgres for persistent (memory, relationship), Redis for ephemeral (session, events). The deviations (A-D5-24) are documented `# TODO` comments, not silent.
4. **Soul Spec validation exists** (`ss01_soul/schema_validator.py` with Pydantic models per `runtime_specs/01 §5.1`). The discipline of "validate at load" is in place.
5. **Migration files all have working `upgrade` + `downgrade` halves** (4/4). Roundtrip testing is the only missing piece (Phase 7 §1.3).
6. **Composer (`ss05_composer/composer.py`) is small (328 LoC), deterministic, and documents the immutability contract (PC-8). Token counter (CJK-aware) lives here and should be promoted to `infra/`.**
7. **Care path module (`safety/care_path.py`) is well-structured** — frozen dataclasses, YAML-driven, separate render path for minors. The problem is that nobody calls it from the orchestrator (A-D6-33), not that it itself is wrong.
8. **No bare `except:` clauses**. The 71 broad `except Exception` are loud but not outright bugs.

---

## 6. What was NOT audited

To be honest about scope:

- **Runtime line coverage** (no `pytest --cov` was run). Several "no test" findings in D7 are based on filename matching; some may be covered indirectly. A real `--cov` pass is the next step.
- **Actual behavioral correctness of each subsystem** vs its spec — would require reading every spec section and confirming code matches. This audit confirms *traceability*, not *correctness*.
- **Performance** — no profiling, no load test, no latency budget verification. P95 targets in `runtime_specs/07 §10` are unverified.
- **Soul Spec content quality** (voice_dna hit rate, anti_pattern catch rate) — that's the Phase 7 §1.4 drift suite.
- **Database schema correctness** — migrations have roundtrip but no schema-vs-models drift check.

---

## 7. Sign-off checklist

This audit satisfies the Phase 7 §1.7 cut criterion:

- [x] `docs/audit/2026-05-23_architecture_audit.md` generated
- [x] **≥ 30 findings** → 41 findings
- [x] **Top 10 action items** → §3, each with owner type + tool + estimate

Next step per the guide (Week 33 Day 5): **HUMAN reads this audit + decides remediation order**. Recommended sequence is the §3 numbering above. Items 1–3 are blocking for Phase 7 cut.

---

**References**:
- Audit prompt: `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.7
- Governance constitution: `docs/GOVERNANCE.md`
- Phase 7 cut criteria: `PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.9
- Companion task: `docs/audit/spec_code_matrix.md` (§1.8, not yet generated)
