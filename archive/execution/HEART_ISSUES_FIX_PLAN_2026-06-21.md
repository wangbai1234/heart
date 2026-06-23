# Heart Issues — 修复方案（2026-06-21）

> **配套**：`engineering_execution/HEART_ISSUE_TRACKER.md`（问题清单）
> **执行模型**：opencode（机械实施 + 跑测试）；HUMAN（PR review + merge）
> **总耗时预估**：~12-16h
> **约束**：必须遵守 `.claude/CLAUDE.md` 分支命名（统一 `feat/`）、PR ≤ 3 open / 7 天合规、独立分支 / 独立 PR；每次 push 前跑 `bash scripts/ci.sh`。

---

## 0. 阅读说明（opencode 必看）

1. **一个 PR 只做一件事**。不要把多个 Issue 塞进一个分支。
2. **从 main 切分支**：`git checkout main && git pull && git checkout -b <branch>`。
3. **修完跑 `bash scripts/ci.sh`** 全绿才 push；CI 红的 PR 不要开。
4. **遵守集成验证分档**（CLAUDE.md §"🧯 集成验证分档"）：A/B 档功能错误必修；C 档既有债务走债务登记；D 档领域冲突局部 `# noqa: <rule> — <理由>`。
5. **PR open 数 ≤ 3**。如果当前 #42 / #43 / #45 还没合，先收敛旧 PR 再开新的。
6. **不要跨分支复制 fix**。fix 先合 main，其他分支 `git rebase main`。
7. **进入任何 SSxx 改动前先 `git ls-tree -r HEAD -- backend/heart/ssXX_*`** 确认现状，禁止凭印象。

---

## 1. 验证结论速览

| # | Tracker 严重度 | 验证 | 处理 |
|---|---|---|---|
| 1 ScoredMemory.reconstructed_text | 🔴 | ✅ CONFIRMED（根因更深：两套 `MemoryRetrievalResult` 类型并存，service.retrieve 出口未做转换，reconstructor 模块未串入） | **PR-A** |
| 2 encoder-worker 重启 | 🔴 | ⚠️ 需 docker logs 取证 | **PR-B**（取证 + 决断） |
| 3 迁移 009 缺失 | 🔴 | ✅ 已修在 PR #45 等 merge | Batch 0 |
| 4 E2E session race | 🟠 | ✅ CONFIRMED（root: bare except 吞 commit 异常 + cold path 复用同一 session） | **PR-C** |
| 5 fast_encoder 15 fail | 🟠 | ✅ CONFIRMED（测试用 deprecated `candidate_identity_signals`） | **PR-E** |
| 6 迁移测试期望 head=003 | 🟠 | ✅ CONFIRMED（硬编码到 REV_003，head 已是 010） | **PR-E** |
| 7 consolidator test 导入 | 🟠 | ✅ CONFIRMED（pytestmark 在 import 之前但不阻止 import） | **PR-E** |
| 8 SS04 特殊状态 TODO | 🟠 | ✅ CONFIRMED（service.py:297） | **PR-F** |
| 9 emotion_events 表空 | 🟠 | ✅ CONFIRMED（EmotionEvent model 存在，service 零写入） | **PR-D** |
| 10 WS /api/chat/ws 404 | 🟡 | ❌ **WRONG DIAGNOSIS**：路由 `@router.websocket("/api/chat/ws")` 已注册（routes_chat_ws.py:213），`curl GET` 测 WS 端点本就 404，需用 `wscat` | 删除 / Batch 4 备注 |
| 11a 4 个 DeclarativeBase | 🟡 | ✅ CONFIRMED | Batch 4（开 RFC） |
| 12a 两个 LLM provider 树 | 🟡 | ✅ CONFIRMED | Batch 4（开重构 issue） |
| 11b JWT HS256 vs spec RS256 | 🟡 | ✅ CONFIRMED | Batch 4（Closed Beta 前） |
| 12b FastAPI on_event 废弃 | 🟡 | ✅ CONFIRMED（main.py:188-189） | **PR-G** |
| 13 CORS allow_origins=["*"] | 🟡 | ✅ CONFIRMED（main.py:86） | **PR-G** |
| 14 wellbeing NotImplemented | 🟡 | ❌ **WRONG DIAGNOSIS**：51/56 是 `__lt__`/`__le__` 返回 `NotImplemented`——Python 富比较的**正确惯例**，不是 bug | 删除 |
| 15 regex shadow 死代码 | 🟡 | ✅ CONFIRMED；已有 sunset audit doc | Batch 4（等 Closed Beta + 7 天 0 回归） |
| 16 emotion service `-> str` 返回 None | 🟡 | ✅ CONFIRMED（service.py:525-528） | **PR-D** 顺手 |
| 17 memory_extractor_worker typing | 🟡 | ✅ CONFIRMED（__init__:66 用 `object \| None`） | **PR-H** |
| 18 TODOs (7) | 🟢 | catalog | Batch 4 |
| 19 deprecated 标记 (8) | 🟢 | catalog | Batch 4 |
| 20 mypy 类型错误 (15) | 🟢 | catalog | **PR-H** 局部 + Batch 4 |
| 21 ss01_soul None 安全 (3) | 🟢 | catalog | **PR-H** |
| 22 未使用 SS02 字段 | 🟢 | catalog | Batch 4 |
| 23 emotion_states 表空 | 🟢 | catalog（依 Issue 9 修复后回归） | Batch 4 |
| 24 无外键约束 | 🟢 | 设计选择（分区表不支持 FK） | 不修 |
| 25 replay_snapshots 无清理 | 🟢 | catalog | Batch 4 |

---

## 2. Batch 0 — 现有 PR（等 merge）

| PR | 标题 | 处理 |
|---|---|---|
| #42 | feat(ss02): LLM Extractor refactor v1.0.3 | 等 review + merge |
| #43 | feat(voice): MiMo TTS provider | 等 review + merge |
| #45 | fix(migrations): use sa.Column in 009 | 等 review + merge → Issue 3 自动消失 |

执行：`gh pr merge 45 --squash`，`gh pr merge 42 --squash`，`gh pr merge 43 --squash`（按依赖顺序，先 45 再 42 再 43）。

---

## 3. Batch 1 — 🔴 阻塞

### PR-A `fix/ss02-composer-memory-block`

**目标**：消除 `composer_memory_block_failed error="'ScoredMemory' object has no attribute 'reconstructed_text'"`，让 LLM 真正拿到记忆上下文。

**修复 Issue**：#1

**根因（必读）**：
- `heart/ss02_memory/service.py:131-147` 定义的 `MemoryRetrievalResult.memories` 类型是 `list[RetrievedMemory]`（带 `reconstructed_text` + `uncertainty_level`）。
- `heart/ss02_memory/retriever/base.py:88-110` 定义了**另一个**同名 `MemoryRetrievalResult.memories: list[ScoredMemory]`（只有 score，**没有** `reconstructed_text` / `uncertainty_level`）。
- `MemoryService.retrieve()`（service.py:209-265）在 line 251 直接 `return await orchestrator.retrieve(...)`，**把 retriever 层的类型当 service 层类型返回**（`# type: ignore[arg-type,return-value]` 是 smoking gun）。
- 现成的 `Reconstructor`（`heart/ss02_memory/reconstructor.py`）就是干这个转换的，但根本没被串到出口。

**改的文件**：
- `backend/heart/ss02_memory/service.py:209-265` — `retrieve()` 拿 orchestrator 结果后逐条用 Reconstructor 转成 `RetrievedMemory`，返回 service 层 `MemoryRetrievalResult`。
- `backend/heart/ss02_memory/__init__.py` 或 service.py 顶部 — 加 lazy import `Reconstructor`。

**Diff 思路**：

```python
# backend/heart/ss02_memory/service.py 内部
async def retrieve(self, user_id, character_id, query_context, top_k=DEFAULT_TOP_K):
    self._enforce_user_isolation(user_id, character_id, query_context)
    top_k = self._enforce_top_k(top_k)

    if self._db is None:
        return MemoryRetrievalResult(query_id=uuid4(), retrieved_at=..., memories=[], ...)

    try:
        from heart.ss02_memory.retriever.orchestrator import RetrievalOrchestrator
        from heart.ss02_memory.reconstructor import Reconstructor

        orchestrator = RetrievalOrchestrator(self._db)
        retriever_result = await orchestrator.retrieve(query_context, top_k)

        # NEW: convert ScoredMemory -> RetrievedMemory
        reconstructor = self._get_reconstructor()  # lazy init
        retrieved: list[RetrievedMemory] = []
        for sm in retriever_result.memories:
            try:
                rec = reconstructor.reconstruct(sm, character_id=character_id)
                retrieved.append(RetrievedMemory(
                    memory_id=sm.memory_id,
                    memory_type=sm.memory_type,
                    state=getattr(sm.memory, "state", "vivid"),
                    reconstructed_text=rec.text,
                    raw_content=_extract_raw(sm.memory),
                    score=sm.score,
                    score_breakdown=sm.score_breakdown,
                    uncertainty_level=_state_to_uncertainty(getattr(sm.memory, "state", "vivid")),
                    voice_dna_applied=rec.transforms_applied,
                    source_evidence=_extract_raw(sm.memory),
                ))
            except Exception as e:
                logger.warning("reconstruct_failed_fallback", memory_id=str(sm.memory_id), error=str(e))
                # 兜底：不掉链子，给 composer 一个降级文本
                retrieved.append(RetrievedMemory(
                    memory_id=sm.memory_id,
                    memory_type=sm.memory_type,
                    state="vivid",
                    reconstructed_text=_fallback_text(sm.memory),
                    raw_content=_fallback_text(sm.memory),
                    score=sm.score,
                    score_breakdown=sm.score_breakdown,
                    uncertainty_level=0.5,
                    voice_dna_applied=[],
                    source_evidence=_fallback_text(sm.memory),
                ))

        return MemoryRetrievalResult(
            query_id=uuid4(),
            retrieved_at=datetime.now(timezone.utc),
            memories=retrieved,
            recently_forgotten_hints=retriever_result.recently_forgotten_hints,
            total_candidates=retriever_result.total_candidates,
            retrieval_strategies_used=retriever_result.strategies_used,
            retrieval_latency_ms=int(retriever_result.retrieval_time_ms),
            l4_included=bool(retriever_result.l4_included),
        )
    except Exception as e:
        logger.error("retrieve_failed", error=str(e), user_id=str(user_id))
        return MemoryRetrievalResult(query_id=uuid4(), retrieved_at=..., memories=[], ...)


def _fallback_text(memory) -> str:
    """Best-effort raw text when reconstruct fails."""
    for attr in ("summary", "episode_summary", "literal_text", "raw_evidence", "identity_text"):
        v = getattr(memory, attr, None)
        if v:
            return str(v)
    return ""


def _state_to_uncertainty(state: str) -> float:
    return {"vivid": 0.0, "fading": 0.3, "faint": 0.6, "dormant": 0.8, "archived": 0.95}.get(state, 0.5)
```

> 注：**不动 composer**。当前 composer/service.py:557 / :560 访问 `m.reconstructed_text` / `m.uncertainty_level` 是正确意图，错的是上游 service 没产出这个类型。

**测试**：
- `backend/tests/unit/test_memory_service_retrieve_reconstruct.py`（新）：
  - mock RetrievalOrchestrator 返回 2 个 ScoredMemory
  - 断言 `retrieve()` 返回的 `MemoryRetrievalResult.memories[0].reconstructed_text` 是 str
  - 断言 `uncertainty_level` 是 0-1 float
  - 断言 Reconstructor raise 时 fallback 不抛
- `backend/tests/unit/test_composer_memory_block.py`（如有，确认 not raising）

**本地验收**：
```bash
cd backend
pytest tests/unit/test_memory_service_retrieve_reconstruct.py -v
bash ../scripts/ci.sh
# 然后手测：起服务，跑 /api/chat 真 LLM 5 轮，grep 日志确认 "composer_memory_block_failed" 不再出现
```

**PR 模板**：
```
Title: fix(ss02): wire reconstructor in MemoryService.retrieve to fix composer memory block
Body:
## Root cause
`MemoryService.retrieve()` returned retriever-layer `MemoryRetrievalResult` (list[ScoredMemory]) directly instead of the service-layer type (list[RetrievedMemory]). Composer accesses `m.reconstructed_text` and `m.uncertainty_level`, which only exist on RetrievedMemory. The Reconstructor module exists but was never wired in.

## Fix
- Wire `Reconstructor` between orchestrator output and service return
- Add fallback path so retrieval still degrades to raw text on reconstruction failure (composer no longer empty-blocks)
- Remove `# type: ignore` smoke signal at service.py:251

## Verify
- New unit test asserts retrieve() returns RetrievedMemory with both fields
- Manual: 5 turns of real LLM chat → no `composer_memory_block_failed` in logs

Closes #1 (in tracker)
```

---

### PR-B `chore/encoder-worker-debug`

**目标**：定位 + 修复 heart-encoder-worker 重启循环。

**修复 Issue**：#2（GitHub Issue #48）

**形式**：分两段。

#### B.1 取证
```bash
docker logs heart-encoder-worker --tail 500 > /tmp/encoder_log.txt
docker inspect heart-encoder-worker --format '{{.State.ExitCode}} {{.RestartCount}}'
```

按 traceback 关键字归类：

| 关键字 | 根因 | 修复点 |
|---|---|---|
| `ImportError`, `ModuleNotFoundError` | 镜像缺包 | `backend/requirements.txt` + Dockerfile |
| `Connection refused`, `asyncpg` | DB 启动顺序 / DSN 错 | worker entrypoint 加 retry；k8s manifest readinessProbe 依赖 postgres |
| `OOMKilled` | model load OOM | k8s manifest 调 memory limit |
| `Pydantic ValidationError` | env 缺值 | `core/config.py` 加默认值或 fail-fast 报错 |
| 无 traceback，exit 0 / 1 反复 | `start_workers` 退出 | `workers/runner.py` 加 `while True` 守护 |

#### B.2 修复 + 验收
- 改文件根据 B.1 结论选择：`backend/heart/workers/memory_encoder.py` / `backend/heart/workers/runner.py` / `backend/Dockerfile` / `infra/kubernetes/encoder-worker.yaml`。
- 加 `/health/live` 端点（worker 暴露 8080，回 200 if `not self._should_stop`）。
- 验收：`watch -n 5 'docker inspect heart-encoder-worker --format "{{.RestartCount}}"'` 30 分钟保持不变。

**PR 模板**：
```
Title: fix(workers): stabilize encoder-worker restart loop
Body:
## Diagnosis (from docker logs)
<paste traceback summary>

## Fix
<具体改动>

## Verify
- RestartCount 30min steady
- L2/L3 vector encoding pipeline 见到 pending event 被消费（grep `event_processed_successfully`）

Closes #48
```

---

## 4. Batch 2 — 🟠 高优先级

### PR-C `fix/ss07-session-race`

**目标**：让 `/api/chat` 返回 200 后 `sessions.turn_count` 必 +1。

**修复 Issue**：#4（GitHub Issue #47）

**根因**：
- `session_manager.record_turn()`（session_manager.py:69-95）用 bare `except Exception:` 吞掉异常（line 94-95），commit 抛错时 caller 不知道。
- `_fire_cold_path()`（orchestrator.py:147）用 caller 传进来的 `db_session` 给后台 task，AsyncSession 不允许跨 task 并发 → 触发 record_turn 那次 commit 时连接被占用。

**改的文件**：
- `backend/heart/ss07_orchestration/session_manager.py:80-95`
- `backend/heart/ss07_orchestration/orchestrator.py:130-166` 调整顺序 + cold path 自己 open session

**Diff 思路**：

```python
# session_manager.py:69-95
async def record_turn(self, db_session: AsyncSession, session: Session) -> None:
    await db_session.execute(
        text("UPDATE sessions SET turn_count = turn_count + 1, last_activity_at = NOW() "
             "WHERE id = :session_id"),
        {"session_id": str(session.session_id)},
    )
    await db_session.commit()
    session.turn_count += 1
    session.last_activity_at = datetime.now(timezone.utc)
    # ← 去掉 try/except，让异常上浮
```

```python
# orchestrator.py:130-166 调整为
async def handle_turn(...):
    ...
    # Step 4 compose
    response_text = await self._compose(req, db_session, session.session_id, p)

    # Step 5 record turn FIRST（同事务 + commit）
    await self._session_manager.record_turn(db_session, session)

    # Step 6 cold path 用独立 session（fire-and-forget OK）
    self._fire_cold_path(req, p, response_text, db_session_factory=self._db_session_factory, days_since_last=days_since_last)
    # ↑ cold path 内部 async with self._db_session_factory() as cold_session: ...

    return TurnResponse(...)
```

> 关键：`_fire_cold_path` 不再共享 db_session；orchestrator 需要在 wiring 时拿到 `db_session_factory`。

**测试**：
- `backend/tests/integration/test_session_race.py`（新）：
  - 真 PG，POST `/api/chat`，等响应
  - 同事务外 SELECT `sessions.turn_count` 必 ≥ 1

**本地验收**：
```bash
cd backend
pytest tests/integration/test_session_race.py -v
bash ../scripts/ci.sh
# Tier E：起 uvicorn + PG + 跑 e2e
```

**PR 模板**：
```
Title: fix(ss07): commit session record before response + isolate cold path session
Body:
## Root cause
record_turn() swallowed commit exceptions; cold path reused the request DB session in a fire-and-forget task, racing record_turn's commit.

## Fix
- Drop bare except; let commit errors bubble to FastAPI rollback path
- Cold path now opens its own AsyncSession via session_factory

Closes #47
```

---

### PR-D `fix/ss03-emotion-event-persist`

**目标**：让 `emotion_events` 每轮 +1 行；顺手修 service.py:528 返回类型。

**修复 Issue**：#9 + #16

**改的文件**：
- `backend/heart/ss03_emotion/service.py`（找到 process_turn / 更新状态的地方，写 EmotionEvent；line 525 函数签名 `-> str` → `-> Optional[str]`）
- 顶部加 `from heart.ss03_emotion.models import EmotionEvent`

**Diff 思路**：

```python
# 找到 EmotionService.process_turn 或类似入口，在状态更新后：
async def process_turn(self, ..., db_session: AsyncSession) -> ...:
    ...  # 现有内存态更新逻辑
    if db_session is not None:
        event = EmotionEvent(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            turn_id=turn_id,
            valence=new_vad["valence"],
            arousal=new_vad["arousal"],
            dominant_emotion=dominant,
            trigger=trigger,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(event)
        await db_session.flush()  # 不 commit，由 orchestrator 统一提交
```

```python
# line 525
def _generate_repairs_summary(self, pending_repairs: List[Dict[str, Any]]) -> Optional[str]:
    if not pending_repairs:
        return None
    ...
```

**测试**：
- `backend/tests/unit/test_emotion_event_persist.py`：mock db_session，process_turn 后断言 `db_session.add` 被调一次且参数是 EmotionEvent。
- `backend/tests/integration/test_emotion_event_persist.py`：真 PG，process_turn 后 `SELECT count(*) FROM emotion_events` 必 = 1。

**本地验收**：
```bash
cd backend
pytest tests/unit/test_emotion_event_persist.py tests/integration/test_emotion_event_persist.py -v
```

---

### PR-E `chore/ss02-tests-update`

**目标**：让 unit 测试套不再有 30 个 fail（fast_encoder 15 + migration 7 + consolidator 15 collection error）。

**修复 Issue**：#5 + #6 + #7

**改的文件**：
- `backend/tests/unit/test_fast_encoder.py` —— 删 `TestIdentitySignals` 整个 class（已 deprecated）；如果还想要等价覆盖，新文件 `test_regex_hints.py` 测 `RegexHintsProvider`。
- `backend/tests/integration/test_migration_roundtrip.py` —— 更新 `BASE..REV_010` + `TABLES_BY_REV` 加 007/008/009/010 的预期表（参考各迁移 upgrade() 里 `op.create_table` 的表名）。
- `backend/tests/unit/test_consolidator.py` —— 顶部加 `pytest.importorskip("sqlalchemy.dialects.postgresql.asyncpg")` 之类，或把整个文件挪到 `backend/tests/integration/`（推荐后者，反正只能在 PG 跑）。

**Diff 思路**：

```python
# test_migration_roundtrip.py:22-27
BASE = "e814230ade46"
REV_001 = "001_add_memory_tables"
REV_002 = "002_add_emotion_rel"
REV_003 = "003_ss04_threshold_tuning_v1_1"
REV_004 = "004_replay_snapshots"
REV_005 = "005_safety_events"
REV_006 = "006_sessions"
REV_007 = "007_memory_extractor_audit"
REV_008 = "008_memory_extraction_dlq"
REV_009 = "009_memory_l4_extras"
REV_010 = "010_memory_regex_shadow"

ALL_REVISIONS = [BASE, REV_001, REV_002, REV_003, REV_004, REV_005, REV_006, REV_007, REV_008, REV_009, REV_010]

# 更新 TABLES_BY_REV，逐个迁移 grep create_table 拿表名
```

```bash
# 推荐做法：把 consolidator 测试挪走
git mv backend/tests/unit/test_consolidator.py backend/tests/integration/test_consolidator.py
# 然后改 import 路径 / conftest 引用
```

**本地验收**：
```bash
cd backend
pytest tests/unit/test_fast_encoder.py -v        # 0 fail
pytest tests/integration/test_migration_roundtrip.py -v    # 0 fail（需 PG）
pytest tests/unit/ --collect-only 2>&1 | grep -c "ERROR"   # 0
```

---

### PR-F `feat/ss04-special-states`

**目标**：实现 SS04 DRIFTING / COLD_WAR / REUNION 状态机。

**修复 Issue**：#8

**Spec 参考**：`runtime_specs/04_relationship.md` §3.5 step 4。

**改的文件**：
- `backend/heart/ss04_relationship/service.py:296-298` 替换 TODO
- 新增 `backend/heart/ss04_relationship/special_states.py` 放评估逻辑（DRIFTING/COLD_WAR/REUNION 判定函数）
- `backend/heart/ss04_relationship/models.py` 确认 `RelationshipState` 是否已有特殊状态字段（如 `special_state: Optional[str]`），无则加（同时写一个 alembic 011 migration）

**Diff 思路**：

```python
# special_states.py
from enum import Enum

class SpecialState(str, Enum):
    NONE = "none"
    DRIFTING = "drifting"
    COLD_WAR = "cold_war"
    REUNION = "reunion"

def evaluate_special_state(state, signals, days_since_last):
    # COLD_WAR 优先级最高
    if signals.conflict_unresolved_count >= 3 and not signals.recent_apology:
        return SpecialState.COLD_WAR
    # DRIFTING
    if days_since_last > 14 and state.intimacy_level_drop_7d > 0.2:
        return SpecialState.DRIFTING
    # REUNION（从 DRIFTING / COLD_WAR 回来）
    if state.special_state in (SpecialState.DRIFTING, SpecialState.COLD_WAR) \
       and (signals.recent_apology or signals.warmth_signal_count >= 2):
        return SpecialState.REUNION
    # REUNION 持续 3 turn 后回 NONE
    if state.special_state == SpecialState.REUNION and state.reunion_turn_count >= 3:
        return SpecialState.NONE
    return state.special_state or SpecialState.NONE
```

```python
# service.py:296-298 替换
# 3. Update special states (§3.5 step 4)
from heart.ss04_relationship.special_states import evaluate_special_state, SpecialState
new_special = evaluate_special_state(state, signals, days_since_last)
if new_special != state.special_state:
    logger.info("special_state_transition", old=state.special_state, new=new_special)
    state.special_state = new_special
    if new_special == SpecialState.REUNION:
        state.reunion_turn_count = 0
    if new_special != SpecialState.REUNION:
        state.reunion_turn_count = None
elif new_special == SpecialState.REUNION:
    state.reunion_turn_count = (state.reunion_turn_count or 0) + 1
```

**测试**：
- `backend/tests/unit/ss04_relationship/test_special_states.py`（新）：
  - 每条状态的进入条件 1 个 test
  - 每条状态的退出 / 转移条件 1 个 test
  - REUNION 持续 3 turn 后回 NONE

**本地验收**：
```bash
cd backend
pytest tests/unit/ss04_relationship/ -v
alembic upgrade head    # 011 migration
```

---

## 5. Batch 3 — 🟡 中优先级

### PR-G `chore/api-modernize`

**目标**：FastAPI lifespan + 可配置 CORS。

**修复 Issue**：#12b + #13

**改的文件**：
- `backend/heart/api/main.py:39-90, 178-189`
- `backend/heart/core/config.py` 加 `cors_allowed_origins: str = ""`

**Diff 思路**：

```python
# main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup()
    yield
    await _shutdown()

def create_app():
    app = FastAPI(..., lifespan=lifespan)
    origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()] or ["http://localhost:3000"]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    ...
    # 删除 app.on_event("startup")(_startup) / shutdown
```

**本地验收**：
```bash
cd backend
uvicorn heart.api.main:app
# 启动日志看到 llm_router_initialized 即 lifespan 生效
curl -H "Origin: http://localhost:3000" http://localhost:8000/health/ready -v 2>&1 | grep Access-Control
```

---

### PR-H `chore/typing-cleanup`

**目标**：清掉 PR-D 没碰的 mypy + None-safe 一批 low-cost easy wins。

**修复 Issue**：#17 + #21 + #20 部分

**改的文件**：
- `backend/heart/workers/memory_extractor_worker.py:63-68` —— 新增 `ExtractorProtocol`（typing.Protocol），`extractor: ExtractorProtocol | None = None`
- `backend/heart/ss01_soul/resonance_tracker.py:160` —— `for trigger in (triggers or []):`
- `backend/heart/ss01_soul/facet_unlocker.py:182, 320` —— 同上
- `backend/heart/ss02_memory/hints/regex_hints.py:63` —— `open(str(path), ...)` 或 None-check
- `backend/heart/ss02_memory/encoder/fast.py:41` —— 同上
- `backend/heart/infra/llm_providers/deepseek.py:83` + `deepseek_pro.py:80` —— `base_url=base_url or ""`
- `backend/heart/ss02_memory/retriever/vector.py:107, 168` —— None-check before map

**约束**：不全量改，**只动 low-cost 改一行的**。任何需要重设计的留给 Batch 4 单独 issue。

**本地验收**：
```bash
cd backend
mypy heart/ 2>&1 | wc -l   # 应明显减少
bash ../scripts/ci.sh
```

---

## 6. Batch 4 — 仅登记（不修，开 GitHub issue）

把以下条目用 `gh issue create` 开成 tracking issue。模板见下。

| Issue | 原 tracker # | 处置 |
|---|---|---|
| `[chore] Unify DeclarativeBase across SSxx` | 11a | 开 RFC，跨 4 子系统改动大 |
| `[chore] Merge two LLM provider trees (infra/llm + infra/llm_providers)` | 12a | 重构 issue，保留 `infra/llm_providers/` |
| `[security] Upgrade JWT to RS256` | 11b | Closed Beta 前必修 |
| `[chore] Remove deprecated regex_shadow once 7d clean` | 15 | 等 Closed Beta + 7 天 0 回归 |
| `[chore] Clean up 7 TODOs` | 18 | 拆每条独立 issue |
| `[chore] mypy cleanup (remaining 15 errors)` | 20 | PR-H 没碰的留这里 |
| `[chore] Drop unused semantic_vector field in memory_encoding_events` | 22 | DB schema change |
| `[chore] Add replay_snapshots cleanup cron` | 25 | 设计 + 实现 |
| `[meta] Tracker errata` | 10 + 14 | 关闭这两条，附理由 |

**模板**：
```bash
gh issue create \
  --title "[chore] Unify DeclarativeBase across SSxx" \
  --body "$(cat <<'EOF'
## Problem
Currently 4 independent `class Base(DeclarativeBase)` definitions:
- backend/heart/ss02_memory/models.py:46
- backend/heart/ss03_emotion/models.py:39
- backend/heart/ss04_relationship/models.py:38
- backend/heart/replay/__init__.py:11

Risk: metadata inconsistency, migration conflicts.

## Proposal
Centralize at `backend/heart/core/base.py`. Each SS imports from there.

## Acceptance
- One Base class
- All existing migrations still upgrade clean
- No table metadata divergence

## Refs
- HEART_ISSUE_TRACKER.md #11a
EOF
)" \
  --label "chore,refactor"
```

**Tracker errata 模板**：
```bash
gh issue create \
  --title "[meta] HEART_ISSUE_TRACKER.md errata: WS 404 + wellbeing NotImplemented" \
  --body "$(cat <<'EOF'
## Errata 1 — Issue #10 WebSocket /api/chat/ws 404
Route IS registered (`@router.websocket("/api/chat/ws")` at `backend/heart/api/routes_chat_ws.py:213`) and main.py:185 already includes router. `curl GET` returns 404 because WS endpoints don't respond to GET. Test with wscat:
```
wscat -c ws://localhost:8000/api/chat/ws
```

## Errata 2 — Issue #14 wellbeing_monitor NotImplemented
Lines 51 and 56 return `NotImplemented` from `__lt__` / `__le__` rich comparison — this is the correct Python idiom (lets interpreter try the reverse op). NOT a bug.

Please remove both entries from the tracker.
EOF
)" \
  --label "documentation"
```

---

## 7. 修复后全局验收清单

执行完上面 8 个 PR + Batch 0 三个合 main 后，跑：

- [ ] `bash scripts/ci.sh` 0 fail
- [ ] `cd backend && pytest tests/unit/ -v` 全绿
- [ ] `cd backend && pytest tests/integration/ -m "not e2e" -v` 全绿（需本地 PG）
- [ ] `cd backend && pytest tests/e2e/ -m e2e -v` 全绿（Tier E）
- [ ] `alembic upgrade head` 干净
- [ ] **手测**：起 uvicorn + Postgres + Redis + workers，跑 `/api/chat` 真 LLM 5 轮，对每轮：
  - [ ] HTTP 200
  - [ ] `grep composer_memory_block_failed logs` 0 hit
  - [ ] `SELECT turn_count FROM sessions WHERE id=X` == 5
  - [ ] `SELECT count(*) FROM emotion_events WHERE user_id=X` >= 5
- [ ] `watch -n 5 'docker inspect heart-encoder-worker --format "{{.RestartCount}}"'` 30 分钟稳
- [ ] PR ≤ 3 open（任何时刻），任何 PR open ≤ 7 天
- [ ] 更新 `docs/PROJECT_STATUS.md` §3 表格反映这些修复

---

## 附录 — 关键文件索引

| 关注点 | 文件:行 |
|---|---|
| Issue 1 修复核心 | `backend/heart/ss02_memory/service.py:209-265` |
| Issue 1 类型冲突 a | `backend/heart/ss02_memory/service.py:96-147`（service 层 RetrievedMemory / MemoryRetrievalResult）|
| Issue 1 类型冲突 b | `backend/heart/ss02_memory/retriever/base.py:58-110`（retriever 层 ScoredMemory / MemoryRetrievalResult）|
| Issue 1 复用组件 | `backend/heart/ss02_memory/reconstructor.py:30+`（Reconstructor）|
| Issue 1 调用方 | `backend/heart/ss05_composer/service.py:529-580` |
| Issue 2 worker | `backend/heart/workers/memory_encoder.py` |
| Issue 4 race | `backend/heart/ss07_orchestration/session_manager.py:69-95` |
| Issue 4 cold path | `backend/heart/ss07_orchestration/orchestrator.py:130-166, 658+` |
| Issue 4 FastAPI DI | `backend/heart/api/wiring.py:51-62` |
| Issue 5 测试 | `backend/tests/unit/test_fast_encoder.py:64+` |
| Issue 6 测试 | `backend/tests/integration/test_migration_roundtrip.py:22-27` |
| Issue 7 测试 | `backend/tests/unit/test_consolidator.py:27-42` |
| Issue 8 TODO | `backend/heart/ss04_relationship/service.py:270-317` |
| Issue 9 模型 | `backend/heart/ss03_emotion/models.py:178+` |
| Issue 9 + 16 service | `backend/heart/ss03_emotion/service.py:510-540` |
| Issue 12b + 13 | `backend/heart/api/main.py:85-90, 178-189` |
| Issue 17 typing | `backend/heart/workers/memory_extractor_worker.py:63-68, 164` |

---

**作者**：Claude (Opus 4.7)
**日期**：2026-06-21
**版本**：1.0
