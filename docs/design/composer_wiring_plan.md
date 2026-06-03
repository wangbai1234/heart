# Composer Wiring Plan — /api/chat Hot Path

**Status**: design proposal (no code yet)
**Owner**: backend infra
**Date**: 2026-06-02
**Related**: `runtime_specs/08_engineering_architecture.md` §DI, `runtime_specs/05_persona_composition_runtime.md`

## 1. Problem Statement

`backend/heart/api/routes.py::_get_composer_service` currently builds:

```python
ComposerService(soul_registry=registry, model_router=..., replay_recorder=...)
```

It never passes `memory_service`, `emotion_service`, `relationship_service`, or `inner_state_service`. `ComposerService._build_*_block` returns the empty dataclass whenever its dependency is `None` (see `ss05_composer/service.py:414,450,474,492`). Result: every production `/api/chat` turn ships an empty MemoryBlock / EmotionBlock / RelationshipBlock / InnerStateBlock to the prompt, and SS02–SS04 + SS06 are dead code on the hot path. SafetyAgent (SS07) is also not wired — `routes.py:264` just has `pass` inside the `safety_pre` span.

Additional contract drift discovered while reading the call sites:

| Composer call site | Expected method | Actual today |
|---|---|---|
| `_build_emotion_block` → `emotion_service.get_context_block(user_id, character_id)` | dict with `emotion_summary`, `vad`, `mood_descriptor`, … | ✅ exists at `ss03_emotion/service.py:250` |
| `_build_relationship_block` → `relationship_service.get_current_phase(user_id, character_id)` | dict with `phase`, `trust_level`, `attachment_style`, `behavioral_envelope` | ❌ SS04 only exposes `StagePhaseEngine.evaluate(state, signals)` — no per-(user,character) lookup, no `get_current_phase` method, and it's instantiated **per soul_spec** (`stage_engine.py:135`) |
| `_build_inner_state_block` → `inner_state_service.get_inner_state(...).get(...)` | dict with `internal_monologue`, `recent_reflections`, `current_need` | ❌ Returns `Optional[InnerState]` model (`ss06_inner_state/service.py:211`), not a dict; `.get(...)` would crash |

So "wiring" is **not** just constructor plumbing — SS04 needs a service facade and SS06 needs a return-shape adapter.

## 2. Dependency Trees

### 2.1 SS02 MemoryService

```
MemoryService(db_session, redis_client, embedding_service)
  ├── db_session: AsyncSession            # required for any non-empty retrieval
  ├── redis_client: redis.asyncio.Redis   # required for L1 working memory
  └── embedding_service: EmbeddingService # required for vector search; lazy-OK
```

`retrieve()` short-circuits to an empty result when `_db is None` (`service.py:244`), so it is safe to construct with `db_session=None` during local dev, but production must inject a real `AsyncSession` factory.

### 2.2 SS03 EmotionService

```
EmotionService(config_path: Path | None)
  └── reads config/emotion_lexicon.yaml at __init__
```

No DB, no Redis today (`_state_cache` is an in-process dict — `service.py:64`). State is **per-process, lost on restart**. This is a known gap (TODO at `service.py:62`), but acceptable for MVP: emotion drift is regenerated within a few turns. Flag for follow-up: persist `_state_cache` to Redis with `(user_id, character_id)` key.

### 2.3 SS04 Relationship — needs a new facade

`StagePhaseEngine` is the **state-machine kernel**, not a service. It takes a single `soul_spec` dict at construction time and exposes `evaluate(state, signals)`. The composer needs a higher-level object keyed by `(user_id, character_id)` that:

1. Loads/persists `RelationshipState` rows (today: would require DB; MVP: in-memory dict like SS03).
2. Lazily instantiates one `StagePhaseEngine` per `character_id` from `SoulRegistry`.
3. Exposes `get_current_phase(user_id, character_id) -> dict` returning `{phase, trust_level, attachment_style, behavioral_envelope}`.

**Proposal**: add `backend/heart/ss04_relationship/service.py::RelationshipService` with deps:

```
RelationshipService(soul_registry, db_session=None)
  ├── soul_registry: SoulRegistry        # to build per-character StagePhaseEngine
  └── db_session: AsyncSession | None    # optional in MVP; falls back to in-memory
```

This mirrors SS03 (in-memory cache + future-DB) and reuses the existing `StagePhaseEngine` unchanged.

### 2.4 SS06 InnerStateService

```
InnerStateService()    # zero deps; in-process state dict
```

Already a service. Only contract mismatch: `get_inner_state` returns the dataclass, not the dict the composer expects. Two options:

- **(A)** Add `InnerStateService.get_context_block(user_id, character_id) -> dict` that maps `InnerState` → `{internal_monologue, recent_reflections, current_need}` and update composer to call it. *Preferred — keeps composer side symmetric with SS03's `get_context_block`.*
- **(B)** Change composer to read `InnerState` attributes directly. Couples composer to SS06's internal model.

Recommend (A).

### 2.5 SS07 SafetyAgent

Not in scope of file reads done here, but the `safety_pre` span at `routes.py:264` is a no-op. Per constraint, SafetyAgent must be **fail-closed**, so even if we wire it last, the wiring shape needs to land in this plan: the route (not the composer) must invoke `safety_agent.evaluate_user_input(user_message)` before calling `composer.compose`, and short-circuit with `HTTPException(503, "Safety service unavailable")` if the agent is `None` or raises.

## 3. Instantiation Timing

The /chat path is request-scoped, but the heavy objects (registry, lexicon parse, ModelRouter HTTP client, engine caches) are not. Split as follows:

| Component | Scope | Built at | Notes |
|---|---|---|---|
| `SoulRegistry` | process singleton | first `_get_soul_registry()` call (today) | unchanged |
| `ModelRouter` | process singleton | composer factory (today) | unchanged |
| `ReplayRecorder` | process singleton | composer factory (today) | unchanged |
| `EmotionService` | process singleton | composer factory (new) | lexicon load is ~ms; safe to cache |
| `InnerStateService` | process singleton | composer factory (new) | state lives inside; must be singleton or state is lost |
| `RelationshipService` | process singleton | composer factory (new) | wraps per-character `StagePhaseEngine` cache |
| `MemoryService` | **request-scoped** | FastAPI `Depends` | each request gets a fresh `AsyncSession` from the async engine |
| `ComposerService` | **request-scoped** | FastAPI `Depends` | because it now needs the per-request `MemoryService`; other deps are pulled from the singletons |
| `SafetyAgent` | process singleton | composer factory (new) | client to an external/local guardrail model |

**Why ComposerService becomes request-scoped**: a `MemoryService` carrying an `AsyncSession` must not be shared across requests (session lifetime + concurrency). The cheapest correct shape is a thin per-request `ComposerService` that holds references to the singletons + a fresh `MemoryService`. Construction cost is ~µs since no I/O happens in `__init__`.

**Migration**: replace the current `_composer_service` global with two pieces:

```
_singletons: built once (registry, model_router, replay, emotion, inner_state, relationship, safety)
get_composer(db_session: AsyncSession = Depends(get_db)) -> ComposerService:
    memory_service = MemoryService(db_session=db_session, redis_client=_singletons.redis, ...)
    return ComposerService(**_singletons.as_kwargs(), memory_service=memory_service)
```

`get_db` should be added (it's not in the read set, but per spec §DI it's the standard FastAPI dependency that yields a session from the engine and closes it on response).

## 4. Failure / Degradation Policy

| Subsystem | Mode | On init failure | On per-turn failure | Trace marker |
|---|---|---|---|---|
| **SS01 Soul** | fail-closed | abort startup | 500 from composer | `anchor_loaded=false` |
| **SS02 Memory** | graceful | log + skip wiring, `memory_service=None` | catch in `_build_memory_block` (already done), emit `composer.memory_degraded` metric | `composition_trace.memory.degraded=true, reason=...` |
| **SS03 Emotion** | graceful | log + `emotion_service=None` | catch in `_build_emotion_block` (already done), metric `composer.emotion_degraded` | `composition_trace.emotion.degraded=true` |
| **SS04 Relationship** | graceful | log + `relationship_service=None` | catch + metric `composer.relationship_degraded` | `composition_trace.relationship.degraded=true` |
| **SS06 InnerState** | graceful | log + `inner_state_service=None` | catch + metric `composer.inner_state_degraded` | `composition_trace.inner_state.degraded=true` |
| **SS05 Composer** | fail-closed | abort startup | 500, no fallback to echo | n/a |
| **SS07 Safety** | **fail-closed** | abort startup if no `SAFETY_DISABLE=true` override | 503 to client, **no LLM call**, no replay record | route sets `blocked_by_safety_unavailable=true`; never reaches composer |
| **ModelRouter** | graceful (today) | log + `model_router=None` → fallback template | unchanged | `composition_trace.fallback_response=true` |

Mechanics:

1. **All degradations emit a metric AND a structured log** (`logger.warning("composer_<sys>_degraded", reason=...)`). Today most of the `_build_*_block` `except` paths emit `logger.exception(...)` but no metric — add a `prometheus_client.Counter("heart_composer_subsystem_degraded_total", ["subsystem", "reason"])`.
2. **Composer must surface degraded subsystems in `CompositionResult.composition_trace`**. Today `composition_trace` only carries summary fields (`service.py:315`). Extend each `_build_*_block` to return `(block, degraded: bool, reason: str | None)` or to set a flag on the block dataclass, and roll those flags up into the trace dict so replay bundles and `/api/profile/records` can see real-vs-degraded turns.
3. **SafetyAgent fail-closed shape** — at the route level, before `composer.compose`:
   ```
   if safety_agent is None or not await safety_agent.is_healthy():
       raise HTTPException(503, "safety_unavailable")
   verdict = await safety_agent.evaluate_user_input(last_user_message, ctx)
   if verdict.blocked:
       return ChatResponse(response=verdict.user_facing_refusal, ...)
   ```
   Never let an exception inside SafetyAgent fall through to composer.

## 5. Test Strategy — "did a real turn hit all 6 subsystems?"

The current integration tests don't catch this because they unit-test SS02/SS03/SS04/SS06 individually and the `/api/chat` test only asserts a 200. We need a positive assertion that each subsystem was *invoked* on a single real turn.

### 5.1 Wiring smoke test (new) — `backend/tests/integration/test_composer_wiring.py`

Spin up the FastAPI app with all real services (use in-memory SS03/SS04/SS06 cache, sqlite-or-test-pg `db_session`, a `ModelRouter` stub that records calls). Send one `POST /api/chat`. Assert:

- `_get_composer_service` injected all six service references (introspect the global / dep cache: `composer._memory_service is not None`, etc.).
- The captured `CompositionResult.composition_trace` contains non-default values for at least: `memory_count`, `emotion_summary`, `relationship_phase`, and `inner_state` markers — proving each `_build_*_block` ran to completion.
- A second `composition_trace.subsystems_invoked = ["soul","memory","emotion","relationship","inner_state"]` list (to be added in the composer) equals the expected set, with no `degraded` flag set.

### 5.2 Spy-based call assertion (new)

In the same test, wrap each service in a `MagicMock(wraps=real_service)` before injecting. After the turn:

- `memory_service.retrieve.assert_called_once()`
- `emotion_service.get_context_block.assert_called_once()`
- `relationship_service.get_current_phase.assert_called_once()`
- `inner_state_service.get_context_block.assert_called_once()`
- `safety_agent.evaluate_user_input.assert_called_once()`

This is the canonical "all six subsystems hit" guard. Run it in CI.

### 5.3 Degradation tests

For each of SS02 / SS03 / SS04 / SS06, separately patch the service to raise on its public method and assert:

- Turn still returns 200.
- `composition_trace.<system>.degraded == True`.
- `heart_composer_subsystem_degraded_total{subsystem="<sys>"}` incremented.

### 5.4 SafetyAgent fail-closed test

Patch `safety_agent` to `None` (or raise) → assert `POST /api/chat` returns **503** and that `model_router.call_main` was **never** called. This is the most important regression guard; it's the only one of these that's not a degradation but a hard close.

### 5.5 MVP gate (`backend/scripts/check_mvp.py`)

Add a gate that boots the app, calls `/api/chat`, and asserts the subsystem-invocation list. Today's gate (per recent commits) checks composer presence but not subsystem reach — extending it covers the regression that triggered this plan.

## 6. Open Questions / Follow-ups

1. **SS04 facade**: confirm whether `RelationshipService` should live in `ss04_relationship/service.py` or be added to an existing module. (Proposal: new file, mirrors SS02/SS03.)
2. **InnerState persistence**: in-memory dict is fine for the wiring fix, but proactive messages disappear on restart. Track separately.
3. **Emotion state persistence**: same; Redis migration tracked separately.
4. **SafetyAgent location**: this plan assumes it exists; verify before implementation. If not, this plan grows by one section (SS07 SafetyAgent service + provider config).
5. **`get_db` dependency**: confirm whether it already exists in `backend/heart/api/` or needs to be added.

## 7. Implementation Order (when this plan is approved)

1. Add `RelationshipService` facade + `InnerStateService.get_context_block` adapter (pure refactor, no behavior change).
2. Add `subsystems_invoked` + `degraded` markers to `CompositionContext` / `CompositionResult` and `_build_*_block` returns.
3. Add `get_db` (if missing) and a `Singletons` container module.
4. Rework `_get_composer_service` into `_get_singletons()` + `get_composer(db = Depends(get_db))`.
5. Wire SafetyAgent at the route level with fail-closed handling.
6. Land tests §5.1–§5.4; extend `check_mvp.py` per §5.5.

Each step is independently reviewable; steps 1–2 are no-op on production behavior and can land first to de-risk the rest.
