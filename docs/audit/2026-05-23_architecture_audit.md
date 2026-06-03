# Architecture Audit — Heart

| Field | Value |
|---|---|
| Date | 2026-05-23 (run 2026-05-24) |
| Auditor | Claude Opus 4.7 |
| Commit | `efefb7a` (HEAD) |
| Branch | `feat/misc-updates` ⚠️ (user requested "main branch HEAD" — current branch differs; this audit reflects HEAD state) |
| Working tree | dirty — see `git status` snapshot in §0.2 |
| Scope | `backend/heart/` (≈ 85 .py modules) and `backend/tests/` |
| Dimensions | D1 layering · D2 cross-cutting · D3 LLM router · D4 soul spec · D5 state stores · D6 traceability · D7 coverage |
| Total findings | **51** (Critical: 12 · High: 17 · Medium: 16 · Low: 6) |
| Constraint | **Audit only — no code changes.** |

---

## 0. Preliminaries

### 0.1 Method
- D1 / D3: full-tree `grep` for `from heart.*`, `import anthropic`, `import openai`, `from openai`.
- D2: read 5 files per subsystem (`__init__.py`, `service.py`/key engine, two leaves) and compare logging / config / error / async style.
- D4 / D5 / D6 / D7: delegated to four `Explore` sub-agents with tight prompts; results cross-checked against direct reads.
- D9 critical modules (orchestrator middleware, composer, safety agent, LLM router, invariants framework) read in full, not skimmed.

### 0.2 Working-tree caveat
`git status` shows uncommitted modifications to `safety/__init__.py`, `ss02_memory/service.py`, `ss03_emotion/state_machine.py`, `ss04_relationship/stage_engine.py`, `ss07_orchestration/__init__.py`, plus untracked `infra/invariants.py`, `infra/invariant_predicates.py`, `infra/llm_providers/fake.py`, `safety/safety_agent.py`, `ss07_orchestration/middleware.py`, `qa/`, contract & integration test packages. Several **Critical** findings below would shift if these files were on `main` — but as of this commit they are present in the working tree and read.

### 0.3 Spec inventory (for D6)
`runtime_specs/` (10 files): `00_runtime_worldview.md`, `01..08_…`, `README.md`.
`docs/design/` (10 files) including `state_invariants.md`.

---

## 1. Headline findings (read these first)

1. **Composer (SS05) is a placeholder.** `ss05_composer/__init__.py` is one line ("Subsystem placeholder"); the only real file is `example_usage.py` — *example code in production package*. There is no Composer service, no protocol, no DI wiring. This is the system's main response path.
2. **Inner-state subsystem (SS06) is empty.** `ss06_inner_state/__init__.py` = 1 line; no other modules. Spec `06_inner_state_behavior_runtime.md` is unimplemented.
3. **Orchestrator (SS07) is just an invariant-sampling middleware.** `middleware.py` (84 lines) wraps `inner_fn` and runs invariants on a sample. There is no Orchestrator class, no turn pipeline, no Composer/Safety routing. Spec `07_agent_orchestration.md` is unimplemented.
4. **Safety is a hard-coded English keyword list.** `safety/safety_agent.py` matches six PURPLE strings (`"kill myself"`, …) and six YELLOW strings (`"lonely"`, …). No Chinese, no LLM, no context window. Critical-safety surface, zero unit tests.
5. **Two parallel LLM stacks exist; only one is wired.** `infra/llm/` (router → single `DeepSeekProvider`) is what callers use. `infra/llm_providers/` (registry + multiple providers + circuit-breaker interface + `fake.py`) is orphan code — `infra/llm/router.py` does not import from it. The orphan tree also contains the misnamed `llm_providers/anthropic.py` which actually implements `DeepSeekV4ProProvider` (its docstring admits this).
6. **`EmotionService._state_cache` is a `Dict`, not Postgres.** Service-layer comment is *“TODO: Initialize database connections (Redis + PostgreSQL). For now, use in-memory storage for development.”* Means RULE-W-E-2 (audit-log emission) cannot be satisfied: no `emotion_events` rows are written. Same TODO pattern reportedly in `ss02_memory/service.py`.
7. **Layering is otherwise clean.** No upward leaks (no `from heart.api` outside `api/`, no subsystem importing from `workers`, no peer-subsystem coupling outside `ss02_memory` internal sub-packages).
8. **No direct SDK leak.** `grep -n "^import anthropic\|^from anthropic\|^import openai\|^from openai" backend/heart` → **empty**. `INV-O-5 no-raw-sdk-leak` is registered as always-on. ✅
9. **Spec traceability ≈ 79 %.** Strong in SS02/SS03/SS04 (100 %), zero in `api/` and `core/`, partial (45 %) in `infra/`.
10. **Critical surfaces fail the 80 % unit-coverage bar.** API routes, safety agent, orchestrator middleware, composer all have **zero unit tests**. Coverage is paid only by integration / contract tests.

---

## 2. Findings table

> Severity: **C**ritical / **H**igh / **M**edium / **L**ow.
> "Reme­diation" is a one-line hint, not an implementation plan.

### D1 — Layering integrity

| # | Finding | Sev | Location | Remediation |
|---|---|---|---|---|
| F1 | Allowed-edge map is not declared anywhere (no `ARCHITECTURE.md`, no `__init__.py` `__all__` discipline at package boundaries). Audit had to be inferred. | M | repo-wide | Add `docs/architecture.md` with the layer DAG + an `import-linter` config. |
| F2 | `ss05_composer/example_usage.py` is the *only* file in `ss05_composer` and imports `from heart.infra.llm import get_model_router`. So an "example" file is the sole code path; downstream callers (workers, future orchestrator) have nothing else to import. | C | `heart/ss05_composer/example_usage.py:8` | Rename to `composer.py`, surface `Composer` class via `__init__.py`, delete the "example" framing. |
| F3 | `workers/memory_consolidator.py` directly imports `from heart.ss02_memory.decay_engine import DecayEngine` and SS02 model classes. Workers reach into a peer subsystem's internals rather than going through `ss02_memory/service.py`. | M | `heart/workers/memory_consolidator.py:35-42` | Expose a `MemoryService.consolidate(...)` API; have the worker call that. |
| F4 | `ss02_memory/encoder/fast.py:25` imports `from heart.ss02_memory.service import FastSignals, IdentitySignal, Turn` — *child sub-package importing back into the parent service*. Circular shape only saved by lazy access. | M | `heart/ss02_memory/encoder/fast.py:25` | Move `FastSignals`/`IdentitySignal`/`Turn` dataclasses into `ss02_memory/models.py` or a new `ss02_memory/types.py`. |
| F5 | `ss02_memory/service.py` uses **inline `from heart.ss02_memory.* import ...`** inside methods (lines 246, 410, 561, 605) — a code smell that hides circular deps from static analysis. | L | `heart/ss02_memory/service.py:246,410,561,605` | Resolve the cycles at module top; remove the inline-import workaround. |
| F6 | `ss07_orchestration/__init__.py` re-exports `orchestrate_with_invariants` only; no orchestrator class, no `Orchestrator` symbol. Upstream callers (none yet — API does not call it) cannot depend on a stable surface. | H | `heart/ss07_orchestration/__init__.py:3` | Either declare the subsystem "incomplete" in README, or land an `Orchestrator` class with stable methods. |

### D2 — Cross-cutting concerns

| # | Finding | Sev | Location | Remediation |
|---|---|---|---|---|
| F7 | Logger acquisition style varies: most modules use `structlog.get_logger()` (no name); two new files use `structlog.get_logger(__name__)`. Inconsistent — module-scoped names are better for filtering. | L | `infra/invariants.py:22`, `ss07_orchestration/middleware.py:25` vs every other module | Pick one: standardize on `structlog.get_logger(__name__)`. Add a lint rule. |
| F8 | `infra/invariants.py:63-71` reads `os.environ["HEART_INVARIANTS"]` and `["HEART_ENV"]` directly, bypassing the `Settings` object that already declares both. Two sources of truth. | M | `heart/infra/invariants.py:63-71` and `heart/core/config.py:17-18` | Route through `settings.heart_invariants` / `settings.heart_env`. |
| F9 | `Settings.jwt_secret_key` defaults to `"your-secret-key-here"` and *passes silently* if `.env` is missing — `Settings()` does not require the secret. | H | `heart/core/config.py:72` | Make `jwt_secret_key` mandatory in non-dev; fail-fast at startup if unset and `heart_env != "dev"`. |
| F10 | `ss02_memory/service.py` uses bare `except Exception:` 9 times (lines 249, 301, 348, 386, 424, 487, 522, 566, 609). Swallows all errors; logs but does not propagate. | H | `heart/ss02_memory/service.py:249–609` | Catch specific exception types; let unexpected ones bubble up. |
| F11 | `ss07_orchestration/middleware.py:57` tests `hasattr(inner_fn, "__await__")` *on the function itself* (not its return value) to decide sync vs async. This is wrong: a `def` returning a coroutine has no `__await__`; an `async def` function has no `__await__` either (the *coroutine object* does). | C | `heart/ss07_orchestration/middleware.py:57` | Use `inspect.iscoroutinefunction(inner_fn)` or always `await asyncio.ensure_future(...)`. |
| F12 | `Settings` mixes config for *every* subsystem (DB, Redis, LLM, S3, JWT, Stripe, FCM, observability) in one Pydantic model. Hard to validate per-subsystem. | L | `heart/core/config.py` | Split into nested settings (`DBSettings`, `LLMSettings`, …) using `pydantic-settings` composition. |
| F13 | Async/sync mixed in SS03 — `ss03_emotion/mood_drift.py` is mostly sync (8 sync functions, 0 async), but `ss03_emotion/repair.py` is async because it calls the router. No convention. | M | `heart/ss03_emotion/*` | Decide per-subsystem: either "service async, engines sync" or all async. Document. |
| F14 | Config access pattern leaks `settings.deepseek_api_key` into `api/app.py:40-41` rather than a single LLM bootstrap function. If a second app entry-point appears (e.g. Celery worker), this re-wires by copy/paste. | M | `heart/api/app.py:40-41` | Add `heart.infra.llm.bootstrap()` reading settings once. |

### D3 — LLM router enforcement

| # | Finding | Sev | Location | Remediation |
|---|---|---|---|---|
| F15 | **No raw SDK import anywhere.** `grep -n "^import anthropic\|^from anthropic\|^import openai\|^from openai"` returns empty across `backend/`. Law 6 holds at the import level. | ✅ Info | — | None. |
| F16 | **Two parallel LLM packages.** `heart/infra/llm/` (used) and `heart/infra/llm_providers/` (orphan). The router in `llm/router.py:10` imports only `DeepSeekProvider` from `llm/provider.py`. The richer `llm_providers/` registry (multi-provider, circuit-breaker interface, `fake.py`) is **never imported** by `llm/`. | C | `heart/infra/llm/` vs `heart/infra/llm_providers/` | Decide one: either retire `llm_providers/` (delete) or wire `llm/router.py` to call `llm_providers.get_provider(...)` and delete the local `provider.py`. The split silently creates two truths about "what providers exist". |
| F17 | `infra/llm_providers/anthropic.py` is *named* anthropic but implements DeepSeek (`class DeepSeekV4ProProvider`). The docstring openly admits this ("Named 'anthropic.py' but implements DeepSeek V4-pro for MVP simplification"). Sets up future confusion when a real Anthropic provider lands. | H | `heart/infra/llm_providers/anthropic.py:1-6` | Rename file to `deepseek_pro.py`; reserve `anthropic.py` for actual Anthropic. |
| F18 | `infra/llm/router.py:111-113` initializes a single `DeepSeekProvider` only. There is no fallback / failover / cost-aware routing despite the existence of `llm_providers/registry.py` (which has `ProviderRegistry` and circuit-breaker hooks). The "Router" is a thin wrapper. | H | `heart/infra/llm/router.py:18-20` | Replace `self.deepseek_provider = DeepSeekProvider(...)` with `self.providers = ProviderRegistry.initialize(config)` and route by `ModelTier`. |
| F19 | `ModelRouter.call_main` / `call_cheap` accept `agent_name` only for logging. There is no cost-tracking hook, no per-tenant quota, no `INV-O-5` enforcement at call time (only at import time). | H | `heart/infra/llm/router.py:22-93` | Inject `LLMCostTracker` (already exists at `infra/llm_cost_tracker.py`), enforce `user_daily_cost_limit`. |
| F20 | `get_model_router()` raises `RuntimeError("ModelRouter not initialized")` at runtime. No type-system guarantee. `api/app.py:36-44` is the only initializer; if a worker process starts without it, the first LLM call crashes. | M | `heart/infra/llm/router.py:120-125` | Have workers call `initialize_router` in their own bootstrap; document the invariant. |
| F21 | `ss03_emotion/repair.py` uses lazy `from heart.infra.llm import get_model_router` inside the method. So static analysers can't see the dependency. | L | `heart/ss03_emotion/repair.py` | Move the import to module top. |

### D4 — Soul Spec consumption

| # | Finding | Sev | Location | Remediation |
|---|---|---|---|---|
| F22 | `qa/baseline_runner.py:46-50` reads soul specs via direct `yaml.safe_load(open(...))`, bypassing `SoulRegistry`. Schema validation, version locking, and caching all skipped. | C | `heart/qa/baseline_runner.py:46` | Replace with `get_soul_registry().get_soul(character_id)`. |
| F23 | `qa/regression_runner.py:68` delegates to `baseline_runner.load_soul_spec()` — inherits the same bypass. | H | `heart/qa/regression_runner.py:68` | Fix at the source (F22). |
| F24 | Multiple subsystems accept `soul_spec` as a plain `dict` instead of a validated `SoulSpec` object — `ss02_memory/reconstructor.py:87`, `ss02_memory/forgetting_affect.py:97`, `ss04_relationship/stage_engine.py:104`, `qa/voice_judge.py:61`. Schema contract is enforced only inside SS01; downstream callers can be fed invalid dicts. | H | as listed | Change signatures to take `SoulSpec` (from `ss01_soul/schema_validator`). |
| F25 | Unit tests construct fresh `SoulRegistry(soul_specs_dir=...)` instances per test (`tests/unit/test_anchor_injector.py:160`, `tests/unit/test_soul_validator.py:77`), bypassing the singleton used in production. | M | as listed | Use the `soul_registry` fixture from `tests/integration/conftest.py:172`, or add an equivalent unit-level fixture. |
| F26 | `ss01_soul/IMPLEMENTATION_SUMMARY.md` documents `from heart.ss01_soul.anchor_block import get_anchor_generator, AnchorMode` — but **`anchor_block.py` does not exist** in the package. Doc references dead code. | M | `heart/ss01_soul/IMPLEMENTATION_SUMMARY.md:324,411-412` | Either restore the module or fix the doc. |

### D5 — State store consistency

| # | Finding | Sev | Location | Remediation |
|---|---|---|---|---|
| F27 | `EmotionService._state_cache: Dict[...]` is a process-local dict; comment marks it as a TODO. All emotion state lives in process memory, is lost on restart, and races across concurrent requests. | C | `heart/ss03_emotion/service.py:64` | Inject `AsyncSession`; back state with `emotion_states` table. |
| F28 | Because F27 is in-memory, `emotion_events` audit log (mandated by RULE-W-E-2) is **never written**. The append-only history table exists in the schema but has no producer. | C | `heart/ss03_emotion/service.py` | When F27 lands, emit an `emotion_events` row on every mutation. |
| F29 | Same TODO pattern reported by the D5 agent in `ss02_memory/service.py:62` — "in-memory storage for development". Memory service has no PG backend wired up. | C | `heart/ss02_memory/service.py:62` | Wire up `AsyncSession`; current writes are not durable. |
| F30 | `memory_encoding_events` table has no retention policy. `llm_done` / `failed` rows accumulate forever (partition by month exists but no purge). | H | `heart/ss02_memory/models.py:357-403` + migrations | DELETE done/failed rows older than 7 d; or expire partitions older than 6 mo. |
| F31 | `consolidation_jobs` table also unbounded — successful jobs are never cleaned. Not partitioned. | H | `heart/ss02_memory/models.py:419-476` | Same: cleanup or partitioning. |
| F32 | `workers/memory_consolidator.py:44` has no distributed lock per `(user_id, character_id)`. Two workers can race and produce duplicate episodes/facts. Spec mandates a lock; uniqueness on `scheduled_for` is not sufficient if both workers grab the same scheduled_for. | H | `heart/workers/memory_consolidator.py:44` | Use Postgres advisory locks (`pg_try_advisory_lock`) per `(user_id, character_id)` for the duration of the job. |
| F33 | Redis is declared in `core/config.py` (`redis_url`, `redis_cache_ttl`) and health-checked in `api/main.py:108-109`, but no business-logic module imports or uses it. Pure dead config (until ephemeral caches are added). | M | `heart/core/config.py:28-29`, `heart/api/main.py:108-109` | Either implement an ephemeral cache (embedding cache TTL is set but no cache exists) or drop Redis from the architecture for now. |
| F34 | `ss02_memory/retriever/vector.py` builds queries with f-string template injection: `text(f"semantic_vector <=> '{embedding_str}'::vector")`. Embedding source is internal so SQL-injection risk is low, but the pattern is unsafe and breaks if the string contains a quote. | M | `heart/ss02_memory/retriever/vector.py:~50-65` | Use SQLAlchemy `bindparam(...)` with the `pgvector.sqlalchemy.Vector` type. |
| F35 | `emotion_states` / `relationship_states` snapshots have no `archived_at` / TTL. Inactive users accumulate forever; event logs for inactive users accumulate forever. | M | `heart/ss03_emotion/models.py:56`, `heart/ss04_relationship/models.py:55` | Add archive policy (move to cold table after N months inactive). |
| F36 | `relationship_states` schema has `Index("idx_rel_cold_war", "user_id", "character_id") if False else None` — dead code (the `if False`). | L | `heart/ss04_relationship/models.py:~197` | Delete or actually create the index. |

### D6 — Spec-to-code traceability

(Stats computed by D6 sub-agent.)

| Subsystem | Files | Traceable | % |
|---|---:|---:|---:|
| ss02_memory | 13 | 13 | 100 % |
| ss03_emotion | 8 | 8 | 100 % |
| ss04_relationship | 4 | 4 | 100 % |
| ss07_orchestration | 1 | 1 | 100 % |
| safety | 1 | 1 | 100 % |
| workers | 2 | 2 | 100 % |
| prompts | 2 | 2 | 100 % |
| qa | 5 | 5 | 100 % |
| ss01_soul | 11 | 9 | 81 % |
| infra | 11 | 5 | 45 % |
| api | 3 | 0 | 0 % |
| core | 2 | 0 | 0 % |
| **Total** | **63** | **50** | **79 %** |

| # | Finding | Sev | Location | Remediation |
|---|---|---|---|---|
| F37 | `api/` tier (app.py, main.py, routes.py) — **0/3** traceable. This is the spec §3-§4 surface of SS07. | C | `heart/api/*.py` | Add header docstring referencing `runtime_specs/07_agent_orchestration.md`. |
| F38 | `infra/llm_providers/*` (6 files) — 0 % traceable. Implements SS08 §5 (LLM router design). | H | `heart/infra/llm_providers/*.py` | Add docstring referencing `08_engineering_architecture.md §5`. |
| F39 | `core/auth.py`, `core/config.py` — no spec ref. | M | `heart/core/*.py` | Header line tying to SS08 §6 (or mark explicitly as non-spec engineering glue). |
| F40 | `ss01_soul/anchor_injector.py:38` references "**SS05 §3.6**" — but the active code in `ss05_composer/` is a placeholder. Reference points to spec section that has no implementation. | M | `heart/ss01_soul/anchor_injector.py:38` | Either flag SS05 as "not yet implemented" or remove the reference until SS05 ships. |
| F41 | `ss01_soul/anti_pattern_scanner.py`, `ss01_soul/drift_fingerprint.py` lack spec markers despite the rest of SS01 (9/11) being traceable. Inconsistent local convention. | L | as listed | Add spec line for symmetry. |

### D7 — Test coverage by surface area

| # | Finding | Sev | Location | Remediation |
|---|---|---|---|---|
| F42 | `safety/safety_agent.py` (137 lines) — **zero unit tests.** Crisis-detection logic relied on by `INV-O-2`, `INV-O-3` is exercised only by property tests (and indirectly). | C | `backend/heart/safety/safety_agent.py` | Add `tests/unit/test_safety_agent.py` covering the PURPLE / YELLOW lexicon paths and the severity-cap invariant. |
| F43 | `ss07_orchestration/middleware.py` — **zero unit tests.** No coverage of the sampling decision, the sync/async branch, or the exception-swallowing path. | C | `backend/heart/ss07_orchestration/middleware.py` | Unit tests with mocked `InvariantRegistry`. Also covers F11. |
| F44 | `ss05_composer/example_usage.py` — **zero unit tests.** Both because it's the only file and because it's framed as "example". | C | `backend/heart/ss05_composer/example_usage.py` | Once SS05 is renamed (F2), add unit tests for `generate_response`, `stream_response`, and the LLM-router call. |
| F45 | `api/routes.py` — **zero unit tests.** Auth-login, refresh, verify, chat-echo endpoints have no direct test. | C | `backend/heart/api/routes.py` | `pytest` with FastAPI `TestClient` covering happy path + 401/403 + 5xx. |
| F46 | `infra/invariants.py` — 38 `def test_` against 20+ public symbols; property tests dominate. No direct test for `InvariantRegistry.reset()`, sampling decision, FATAL-mode handling. | C | `backend/heart/infra/invariants.py` | Add targeted unit tests for `_sample_decision`, `should_check`, FATAL-raise in DEV, no-raise in PROD. |
| F47 | `infra/llm/router.py` — covered indirectly via memory-worker mocks. No direct test isolates `call_main` / `stream_main` / `call_cheap` parameter forwarding, `agent_name` propagation, or the un-initialized error. | C | `backend/heart/infra/llm/router.py` | Add `tests/unit/test_llm_router.py` with a fake `DeepSeekProvider`. |
| F48 | `qa/` — **5 modules, 1133 lines, zero tests.** Includes the QA regression harness itself; if it has a bug, we won't know. | H | `backend/heart/qa/*` | At least smoke-test `baseline_runner.run`, `drift_scorer.score`, `report_builder.write`. |
| F49 | `ss02_memory/retriever/graph.py` — 286 lines, **zero tests**. Recursive CTE / spreading activation logic. | H | `backend/heart/ss02_memory/retriever/graph.py` | Unit test with seeded `FactNode` graph (no DB → use a stub retriever). |
| F50 | `ss01_soul/drift_fingerprint.py` — 171 lines, zero tests. | M | `backend/heart/ss01_soul/drift_fingerprint.py` | Add basic tests for fingerprint determinism + collision sensitivity. |
| F51 | `infra/invariant_predicates.py` — exists (untracked) but only ≈ 10 `def test_` against ~15+ predicates. Predicates exercised indirectly via property tests. | M | `backend/heart/infra/invariant_predicates.py` | Targeted unit tests per predicate. |

---

## 3. Top 10 immediate-action items

Priority = (severity × blast-radius) ÷ effort. "Owner" is a *suggested* role; this audit does not assign humans.

| # | Action | Severity | Owner role | Why now |
|---|---|---|---|---|
| **1** | Land a real **SS05 Composer** module (`composer.py` + `Composer` class), retire `example_usage.py`. (F2, F44, F40) | Critical | SS05 owner | Composer is the main response path; currently a stub. Blocks SS07 orchestrator wiring and SS01 anchor-injection downstream tests. |
| **2** | Wire **`ss03_emotion/service.py`** and **`ss02_memory/service.py`** to real `AsyncSession`; emit `emotion_events` audit rows on mutation. (F27, F28, F29) | Critical | SS02/SS03 owner | Without this, the system has no durable emotion or memory state; tests can pass while production loses data. |
| **3** | **Land an Orchestrator** in `ss07_orchestration/` (turn pipeline: safety → memory → emotion → composer → router). The current 84-line middleware is not an orchestrator. (F6) | Critical | SS07 owner | API endpoints have nothing to call into. |
| **4** | Fix `orchestrate_with_invariants` async detection (`inspect.iscoroutinefunction`, not `hasattr(__await__)`); add direct unit tests. (F11, F43) | Critical | SS07 owner | One-line bug that silently breaks coroutine handling. |
| **5** | Resolve the **dual LLM stack** (`infra/llm/` vs `infra/llm_providers/`): either delete the orphan or refactor `router.py` to use the registry. Rename misnamed `llm_providers/anthropic.py`. (F16, F17, F18) | High | Platform / SS08 owner | Two truths about "which providers we have" is a foot-gun. |
| **6** | Add **PG advisory lock** in `workers/memory_consolidator.py` per `(user_id, character_id)`. (F32) | High | Workers owner | Concurrent workers can corrupt L3/L4. |
| **7** | Replace **direct YAML reads** in `qa/baseline_runner.py` and `qa/regression_runner.py` with `get_soul_registry()`. (F22, F23) | High | QA owner | Regressions can pass against unvalidated spec. |
| **8** | Cover **safety + api/routes + composer + orchestrator middleware** with unit tests (currently zero). (F42, F43, F44, F45) | High | Each subsystem | These four are the largest "no test" surfaces and three of them are safety-critical. |
| **9** | **`jwt_secret_key` must be mandatory** in non-dev environments. (F9) | High | Core / security | Default `"your-secret-key-here"` will ship if `.env` is forgotten. |
| **10** | Add **retention policies** for `memory_encoding_events` and `consolidation_jobs`; pick a cleanup window. (F30, F31) | Medium | DB owner | Tables grow unbounded; first symptom will be partition bloat in 3-6 months. |

---

## 4. What's NOT broken (counter-balance)

Audit must also call out what is healthy, so remediation does not over-rotate.

- **No raw SDK leak** — Law 6 holds at the import boundary (F15).
- **Layering DAG is otherwise clean** — no peer-subsystem coupling outside `ss02_memory` internals; no upward leak from a subsystem to `api/` or `workers/`.
- **Logging is consistent** — every module uses `structlog`; only the `__name__` vs no-name choice differs (F7).
- **Spec traceability is strong inside the core subsystems** — SS02, SS03, SS04, safety, workers, qa are all 100 % annotated.
- **Invariant framework is well-engineered** — `infra/invariants.py` has sampling, modes, Prometheus metrics, always-on safety IDs, and FATAL-vs-WARN handling (the framework itself, not its usage).
- **Database schema is partitioned correctly** — HASH partitioning on user_id for state tables, RANGE on created_at for event tables. Just missing retention.
- **Tests do exist** — 53 of 64 source modules have at least one related test file; integration / contract / properties / live test packages are all populated (just unevenly).

---

## 5. Open questions for the team

These are flagged for human decision, not findings:

1. **Is `ss06_inner_state` deliberately deferred?** The spec exists but the package is empty. If deferred, mark in README + spec front-matter.
2. **Is `safety/safety_agent.py` meant to be the production safety surface or a placeholder for an LLM-based classifier?** The current rule-based form is English-only and easy to bypass.
3. **Is the `infra/llm_providers/` package frozen-but-aspirational, or actively replacing `infra/llm/`?** Affects how to resolve F16.
4. **Why is the audit doc dated 2026-05-23 but the run date 2026-05-24?** Per the task spec — kept as requested; flagged here for record.

---

*Audit ends. 51 findings, 10 top-priority actions, 4 open questions. No code modified.*
