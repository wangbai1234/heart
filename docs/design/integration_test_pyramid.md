# Integration Test Pyramid — Heart 项目测试金字塔设计

> **文档角色**: Phase 7 §1.2 设计交付物 (per `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.2)
> **状态**: Design — 实施前需 HUMAN 签字
> **下游**: §1.2 实施 prompt (CC-S46)、§1.4 voice drift suite (复用 Tier C 基础设施)
> **设计者**: CC-Opus-4.7
> **日期**: 2026-05-24
> **修改门槛**: 任何对 tier 边界、CI gate、cost ceiling 的修改 = PR + HUMAN approve

---

## 0. TL;DR

把所有自动化测试切成 **三层金字塔**：

```
                ┌────────────────────────────┐
                │  Tier C — Live (nightly)   │   ≤ 30 tests   实跑 DeepSeek
                │  real LLM + real DB        │   $1/run cap   含 voice drift
                ├────────────────────────────┤
                │  Tier B — Integration      │   ~80 tests    每 PR ≤ 5 min
                │  real PG+Redis, fake LLM   │   testcontainers
                ├────────────────────────────┤
                │  Tier A — Contract         │   ~30 tests    每 PR ≤ 30 s
                │  pure Python, no IO        │   subsystem 边界契约
                ├────────────────────────────┤
                │  Tier 0 — Unit (已存在)    │   1677 tests   每 PR ≤ 90 s
                │  mock everything           │   保留现状     不动
                └────────────────────────────┘
```

**核心原则**:
1. **Tier 0 不动**：1677 个单测留在 `tests/unit/`，作为 Tier 升级的基线；任何 Tier ≥ A 失败时，单测应当先复现失败用例。
2. **Tier A / B 100% deterministic**：禁止 LLM、禁止外网、禁止真实时间。
3. **Tier C 是唯一允许"花钱"的层**，且必须有 *硬* 上限 + 默认 opt-out。
4. **任何 cross-subsystem 行为都至少在 Tier A 有契约测试**，而不是只靠 Tier B。

---

## 1. 设计动机 (Why)

当前状态（per PHASE_7_PLUS §0.1 + 本仓库 `git ls-tree`）：

| 现状 | 风险 |
|------|------|
| Tier 0 = 1677 个 mocked unit tests | mock 与真实 contract 漂移；refactor 风险高 |
| `tests/integration/` 仅 `test_migrations.py` 一个 | SS01-SS07 之间任何 contract mismatch 都看不到 |
| 0 个真实 LLM 调用 | 整条 hot path 一次都没真跑过；MVP demo 必定崩 |
| 没有 voice drift regression | AI 改 Composer / Reconstructor / Anti-drift Injector → 人格可能默默被改写 |

引入三层后我们能拿到：
- **Tier A** 阻止 "SS05 假设 SS03 返回 dict，但 SS03 改成 dataclass" 这类静默漂移
- **Tier B** 在真实 PG / Redis 上验证状态机迁移、idempotence、time-travel
- **Tier C** 给真实 DeepSeek 一次说真话的机会；同时承载 voice drift baseline（§1.4）

---

## 2. Tier 定义详表

### 2.1 速查

| 维度 | Tier 0 Unit | Tier A Contract | Tier B Integration | Tier C Live |
|------|-------------|-----------------|--------------------|-------------|
| 目录 | `backend/tests/unit/` | `backend/tests/contract/` | `backend/tests/integration/` | `backend/tests/live/` |
| pytest 标记 | （无） | `@pytest.mark.contract` | `@pytest.mark.integration` | `@pytest.mark.live` |
| 数据库 | 无 / sqlite in-memory | 无 | 真 PG (testcontainers) | 真 PG (staging) |
| Redis | 无 / fakeredis | 无 | 真 Redis (testcontainers) | 真 Redis (staging) |
| LLM | mock | mock | **fake provider** (确定性) | **real DeepSeek** (cost-capped) |
| 网络 | 禁止 | 禁止 | 仅 localhost | 允许（白名单） |
| 时间 | `freezegun` | `freezegun` | `freezegun` allowed | 真实时间（含真实 timeouts） |
| 总耗时目标 | ≤ 90 s | ≤ 30 s | ≤ 5 min | ≤ 15 min |
| 数量目标（Phase 7 收尾） | 1677 (保持) | 25-35 | 60-90 | 15-25 |
| 每次跑触发 | every push | every push | every push | nightly + on tag |
| Flake 容忍度 | 0 | 0 | < 0.1% (24h 内 1 次) | < 1%（含网络抖动） |
| 失败 → 阻断 merge？ | 是 | 是 | 是 | 否（block release tag） |
| 钱 | 0 | 0 | 0 | ≤ $1 / 跑；≤ $30 / 月 |

### 2.2 Tier A — Contract Tests

**目的**: 锁定 subsystem 之间的接口形状 + 必经路径，不涉及任何 IO。

**测试对象**:
- SS05 Composer 接受 SS03 EmotionState 的字段（schema 契约）
- SS07 Orchestrator 调用 Safety → Composer → ModelRouter 的顺序（mock spy）
- Safety short-circuit 时 Composer 是否真的不被调用（事件契约）
- SS04 Stage 推进 SS06 Inner State 触发条件的字段（数据契约）
- MemoryService 返回的 `RecalledMemory` 在 Reconstructor 中的字段访问（结构契约）

**判定规则**:
- 一个测试 ≠ 验证业务逻辑（那是 unit / integration 的事）
- 一个测试 == 验证 "如果我把 SS03 的字段从 `intensity` 改成 `strength`，必须有红灯"
- 用 `pydantic` schema 锁定 cross-SS DTO；任何字段重命名必然破契约

**典型骨架**（不写代码，给出形状）:
```python
@pytest.mark.contract
def test_composer_consumes_emotion_state_v1():
    """SS05 must consume the v1 EmotionState contract."""
    fake_state = make_emotion_state_v1(intensity=0.7, valence="positive")
    layers = ComposerLayerAggregator().build_layers(emotion=fake_state, ...)
    assert "emotion_intensity" in layers["meta"]
    # 任何 SS03 把 intensity 改名都会让这条测试红
```

**禁止**:
- 启动 docker 容器
- 调用 `httpx.AsyncClient` / `redis.Redis()` / `sqlalchemy.create_engine`
- 调用 `asyncio.sleep(>0)`

**Phase 7 §1.5 中要求的 13 个 contract tests 都落在这里**。

### 2.3 Tier B — Integration Tests

**目的**: 在真实 PG + Redis 上验证状态迁移、原子性、idempotence、time-travel；LLM 用 **fake provider**（不是 mock — 见 §3.3）。

**测试对象**（一行一个，按 spec 章节归属）:

| 测试文件 | spec 引用 | 关键 assertion |
|---------|----------|---------------|
| `test_memory_lifecycle.py` | SS02 §3.4-3.6 | encode → decay (30d) → consolidate → reconstruct，断言 L1→L2→L3→L4 状态机 idempotent |
| `test_emotion_lifecycle.py` | SS03 §3-4 | trigger → state → decay → repair；重复触发不产生重复状态 |
| `test_relationship_progression.py` | SS04 §3 + §10 | Stage 1 → 2 → 3，用 `freezegun` 推进 30 天；anti-gaming 不漂移 |
| `test_orchestrator_hot_path.py` | SS07 §3 | 完整 turn (auth → safety → composer → router → memory_encode)，FAKE LLM |
| `test_inner_loop_tick.py` | SS06 §3-4 | 用户消失 3 天 → scheduler tick → proactive message decision (不发) |
| `test_cold_war_reunion.py` | SS04 §3.4 + §3.10-11 | cold-war state machine + reunion transition once-only |
| `test_safety_short_circuits.py` | SS07 §3.5 + Safety | PURPLE 触发后 Composer / ModelRouter / Memory 三处都被跳过 |
| `test_migration_roundtrip.py` (已规划 in §1.3) | n/a | down → up → down 全部 alembic revisions |
| `test_consolidator_with_pgvector.py` | SS02 §3.6 | 接管原 `@requires_postgres` 15 个 unit tests |

**Phase 7 §1.2 实施目标**: 至少 9 个文件，60-90 个 assertion。

**Fake LLM Provider** 设计（关键决策）:
- 文件: `backend/heart/infra/llm_providers/fake.py`（实施时新建）
- 行为: 给定 (system_prompt 的哈希前 8 位, user_msg 的哈希前 8 位) → 在 `backend/tests/fixtures/fake_llm_responses/` 查表，找到对应 fixture JSON 返回。
- 命中即返回；未命中 → 测试明确失败并打印 *它请求的 key*，提示开发者补 fixture。
- **绝不**实现 "fallback random response" — 一旦 fallback，测试就不再确定。
- 这样 Tier B 100% deterministic，且新加测试时开发者必须显式补 fixture（强制审查）。

**`testcontainers` 约束**:
- PG 镜像: `pgvector/pgvector:pg15`（与 prod 同）
- Redis 镜像: `redis:7-alpine`
- 启动一次，所有 Tier B 测试共享（session-scope fixture）
- 每个测试用 transaction rollback 或 schema-truncate 保证隔离

### 2.4 Tier C — Live Tests

**目的**: 让一次真实的 DeepSeek 跑通整条链路；并为 voice drift baseline (§1.4) 提供 harness。

**默认行为**: **跳过**。只有显式 `--live` + 环境变量 `DEEPSEEK_API_KEY` + Cost Tracker 上限未触发，才会跑。

**测试文件**（Phase 7 §1.2 + §1.4 共用）:

| 文件 | 目的 | 单次预算 |
|------|------|---------|
| `test_real_turn_smoke.py` | 1 个真实 turn：auth → safety → composer → DeepSeek → response → encode | ≤ $0.10 |
| `test_voice_dna_baseline.py` (§1.4) | 30 prompts × 2 角色 = 60 generations 生成 baseline | ≤ $0.40 |
| `test_voice_drift_regression.py` (§1.4) | 60 generations + 60 LLM-as-judge 评分 | ≤ $0.50 |
| `test_purple_care_path_drill.py` | 1 个 PURPLE 输入跑完整 Safety/CarePath，断言不调 Composer | ≤ $0.05 |
| `test_proactive_message_real_llm.py` | 真实生成一条 proactive message | ≤ $0.05 |

**单次完整 Tier C run 预算: ≤ $1.10**。月度上限 `$30`（约 27 跑），由 Cost Tracker 在 conftest 拦截。

**Kill switch 三道**:
1. `LIVE_TESTS_ENABLED=false`（环境变量，默认 false；CI nightly job 显式 true）
2. `CostTracker.daily_total > $5` → conftest 在 collection 阶段就 abort
3. `pytest --live --max-cost=2.0` → CLI 一次硬限

---

## 3. Folder Structure

```
backend/tests/
├── __init__.py
├── conftest.py                 ← 全局 fixture（client, async_engine, ...）
├── pytest.ini                  ← markers + addopts
│
├── unit/                       ← Tier 0 (1677 tests, 不变)
│   ├── conftest.py             ← 已存在
│   └── test_*.py
│
├── contract/                   ← Tier A (NEW)
│   ├── __init__.py
│   ├── conftest.py             ← subsystem schema fixtures, no IO
│   ├── test_ss03_emotion_state_schema.py
│   ├── test_ss05_consumes_ss03.py
│   ├── test_ss07_calls_ss05_then_router.py
│   ├── test_safety_short_circuits_composer.py
│   ├── test_memory_recall_field_contract.py
│   ├── test_router_provider_protocol.py
│   ├── test_soul_spec_loader_returns_v1.py
│   ├── test_inner_state_consumes_emotion.py
│   ├── test_relationship_consumes_signals.py
│   └── test_composer_layer_aggregator_protocol.py
│
├── integration/                ← Tier B (EXTEND)
│   ├── __init__.py
│   ├── conftest.py             ← testcontainers PG + Redis + fake LLM
│   ├── fixtures/
│   │   └── fake_llm_responses/ ← JSON fixtures for fake provider
│   ├── test_migrations.py      ← 已存在
│   ├── test_migration_roundtrip.py        ← §1.3
│   ├── test_memory_lifecycle.py
│   ├── test_emotion_lifecycle.py
│   ├── test_relationship_progression.py
│   ├── test_orchestrator_hot_path.py
│   ├── test_inner_loop_tick.py
│   ├── test_cold_war_reunion.py
│   ├── test_safety_short_circuits.py
│   └── test_consolidator_with_pgvector.py
│
├── live/                       ← Tier C (NEW)
│   ├── __init__.py
│   ├── conftest.py             ← cost-cap guard, requires --live
│   ├── pytest_live.ini         ← addopts: -m live --live --max-cost=2.0
│   ├── test_real_turn_smoke.py
│   ├── test_voice_dna_baseline.py          (§1.4)
│   ├── test_voice_drift_regression.py      (§1.4)
│   ├── test_purple_care_path_drill.py
│   └── test_proactive_message_real_llm.py
│
├── golden/                     ← 留作 voice drift baseline (§1.4 复用)
│   └── voice_baselines/
│       ├── rin_baseline.jsonl
│       └── dorothy_baseline.jsonl
│
└── load/                       ← Phase 11 起用
```

---

## 4. Fixture 策略（conftest 分工）

### 4.1 `backend/tests/conftest.py`（全局）

保留现有内容 + 增加：
- `pytest_collection_modifyitems`: 根据 `--live` flag 自动 deselect `@pytest.mark.live`
- `--max-cost=FLOAT` CLI option: 注入 Tier C cost ceiling
- `pytest_configure`: 注册 `contract / integration / live / requires_postgres / drift` markers

### 4.2 `backend/tests/contract/conftest.py`（Tier A）

```
# 仅暴露纯 Python factory，不启容器
- fixture: emotion_state_v1_factory     → make_emotion_state(intensity=…, valence=…)
- fixture: composer_layer_protocol      → 用 typing.Protocol 锁定接口形状
- fixture: fake_event_bus               → in-memory spy，记录 (sender, event_name, payload)
- fixture: soul_spec_rin / soul_spec_dorothy  → 从 soul_specs/{char}/v1.0.0.yaml 加载（read-only）
```

**禁止**在此 conftest 里 import:
- `sqlalchemy.create_engine`, `redis.Redis`, `httpx.AsyncClient`
- `testcontainers`
- 任何来自 `backend/heart/infra/llm_providers/{deepseek,anthropic}.py`

实施时用一个 `pytest_collection_modifyitems` 钩子做 import-graph 检查（实施代为 §1.2 阶段）。

### 4.3 `backend/tests/integration/conftest.py`（Tier B）

```
- fixture (session-scope): postgres_container       → testcontainers postgres:15 + pgvector ext
- fixture (session-scope): redis_container          → testcontainers redis:7-alpine
- fixture (function-scope): db_session              → wraps in transaction, rolls back at teardown
- fixture (function-scope): redis_client            → flushdb on teardown
- fixture (session-scope): fake_llm_provider        → loads fake_llm_responses/*.json
- fixture (function-scope): frozen_clock            → freezegun.freeze_time, configurable
- fixture (function-scope): soul_registry           → 真实 SoulRegistry 实例
```

**强制规则**:
- `db_session` 必须使用 `BEGIN ... ROLLBACK` 包装；不允许 `SAVEPOINT`-only 因为某些 service 自己 begin
- 任何往 Redis 写 key 的测试必须使用 `key_prefix=test:{pytest.test_id}` 命名空间

### 4.4 `backend/tests/live/conftest.py`（Tier C）

```
- fixture (session-scope): cost_tracker_guard
    断言：os.environ["LIVE_TESTS_ENABLED"] == "true"
    断言：cost_tracker.month_total + estimated_run_cost < MONTHLY_CAP
    在 yield 后 print 累计实际花费
- fixture (session-scope): real_deepseek_provider
    通过 ModelRouter（不许直接 import deepseek SDK，违反 Law 6）
- fixture (function-scope): per_test_budget
    每个测试可以声明 max_cost=0.10；超过则 mid-test abort + Prometheus alert
```

**`--live` flag 缺失时**: collection 阶段 deselect 所有 `@pytest.mark.live` 用例 + 打印 "Tier C skipped (use --live to opt in)"。

---

## 5. Naming Convention

| 文件 | 规则 | 例 |
|------|------|---|
| Tier A | `test_<consumer>_<contract>_<aspect>.py` | `test_ss05_consumes_ss03.py` |
| Tier B | `test_<feature>_lifecycle.py` 或 `test_<flow>_<scenario>.py` | `test_memory_lifecycle.py`, `test_cold_war_reunion.py` |
| Tier C | `test_real_<feature>.py` 或 `test_<feature>_live.py` | `test_real_turn_smoke.py` |

| 测试函数 | 规则 |
|---------|------|
| Tier A | `test_<consumer>_<contract_assertion>` |
| Tier B | `test_<scenario>__<expected_outcome>` 双下划线分隔 |
| Tier C | `test_live__<scenario>` 强制 `live__` 前缀，搜索易 |

**Spec 引用强制**: 每个 Tier B / Tier C 测试函数 docstring 必须有：
```
"""<scenario> per runtime_specs/0X_*.md §Y.Z"""
```
缺失则 `ruff` 自定义规则报错（实施时 §1.8 落地）。

---

## 6. CI Gate

### 6.1 每个 PR（merge gate）

| Job | Tier | 失败 → block merge | 预算 |
|-----|------|--------------------|------|
| `pytest-unit` | 0 | yes | 90 s |
| `pytest-contract` | A | yes | 30 s |
| `pytest-integration` | B | yes | 5 min |
| `pytest-live` | C | **no** | （不跑） |

### 6.2 Nightly（main + release branches）

| Job | Tier | 失败 → 行为 | 频率 |
|-----|------|------------|------|
| 所有上面 | 0 + A + B | open issue, no rollback | 每 PR |
| `pytest-live-smoke` | C smoke 子集 | open P1 issue, page on-call | 每晚 02:00 UTC |
| `pytest-live-drift` (§1.4) | C drift 子集 | open P0 issue, block next release tag | 每晚 02:00 UTC |

### 6.3 Release tag (`v*`)

| Job | Tier | 失败 → 行为 |
|-----|------|------------|
| 全部 nightly jobs | 0 + A + B + C | yes block release |
| `pytest-live-full` | C full | yes block release |

### 6.4 GitHub Actions 配置（草图）

```yaml
# .github/workflows/ci.yml (实施时改)
jobs:
  unit-and-contract:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -m "not contract and not integration and not live" tests/unit  # Tier 0
      - run: pytest -m contract tests/contract                                      # Tier A

  integration:
    runs-on: ubuntu-latest
    services:
      postgres: { image: pgvector/pgvector:pg15, ... }
      redis:    { image: redis:7-alpine, ... }
    steps:
      - run: pytest -m integration tests/integration

  live:
    if: github.event_name == 'schedule' || startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    env:
      LIVE_TESTS_ENABLED: true
      DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
    steps:
      - run: pytest -m live --live --max-cost=2.0 tests/live
```

---

## 7. Failure Debugging Workflow

### 7.1 Tier A 红灯

```
1. 看测试名 → 直接定位被破坏的契约（命名规则的价值）
2. git blame 引发 contract 改动的 commit → 是有意 still 无意？
3. 若有意：同步改 contract 测试 + 标注 BREAKING 在 PR description
4. 若无意：回滚改动；rename / shape 不要改
```

**修复时间 SLA**: ≤ 30 min（contract 测试就是为快定位）

### 7.2 Tier B 红灯

```
1. 先看 fake LLM provider 是否 cache miss → 补 fixture
2. 看 testcontainers 是否健康（CI logs 里 docker 启动）
3. 看 freezegun 是否被未声明的 await 绕过
4. 复现：本地 `make test-integration -k <test_name>`，必要时 `-s --pdb`
5. 单测无法复现 → 退到 unit + 用相同输入构造 minimal repro
```

**修复时间 SLA**: ≤ 2 h

### 7.3 Tier C 红灯

```
分两类：
  a) Smoke / hot path 失败 (test_real_turn_smoke):
     - 检查 DeepSeek 响应是否包含 anti_pattern hit
     - 看 cost_tracker 是否 mid-run 触发上限
     - retry 1 次（API 抖动）；连续 2 红 → P0 issue
  b) Drift 失败 (test_voice_drift_regression):
     - 走 §1.4 中定义的 approved_drift 流程
     - 不要 retry — drift 是 deterministic 信号
```

**修复时间 SLA**:
- Smoke: ≤ 6 h（next-day if 凌晨 page）
- Drift: ≤ 7 天（先评估是否人格漂移真值；可能 baseline 该升）

---

## 8. Tier C Cost Ceiling & Kill Switch

### 8.1 三层保险

| 层 | 机制 | 失败 → |
|---|------|--------|
| L1 静态预算声明 | 测试函数 `@pytest.mark.live(max_cost=0.10)` | mid-test abort if exceeded |
| L2 单次 run 上限 | CLI `pytest --live --max-cost=2.0` | run-level kill |
| L3 月度上限 | `CostTracker.month_total + estimated < $30` 在 `pytest_collection_finish` 检查 | 整个 run 不跑 |

### 8.2 Cost Tracker hook

实施时（§1.2 实施阶段）在 `tests/live/conftest.py`:
```
@pytest.hookimpl
def pytest_runtest_setup(item):
    if "live" in item.keywords:
        budget = item.get_closest_marker("live").kwargs.get("max_cost", 0.10)
        cost_tracker.start_run(test_id=item.nodeid, budget=budget)

@pytest.hookimpl
def pytest_runtest_teardown(item):
    spend = cost_tracker.end_run(item.nodeid)
    print(f"[live] {item.nodeid} spent ${spend:.4f}")
```

### 8.3 Audit trail

每次 Tier C 跑结束 → 写 `docs/audit/live_runs/<date>.json`：
```
{ "timestamp": "...", "branch": "...", "tests_run": 5,
  "total_cost": 0.87, "per_test": [...], "drift_scores": [...] }
```

供 §1.4 / Phase 10 retro 调用。

---

## 9. 与 Soul Drift Regression (§1.4) 的接口

**Tier C 承载 voice drift 的全部测试**。具体见 `docs/design/soul_drift_regression.md`。

本设计仅约定接口：

- 文件位置: `backend/tests/live/test_voice_drift_regression.py`
- Baseline 数据: `backend/tests/golden/voice_baselines/<character>_baseline.jsonl`
- pytest markers: `@pytest.mark.live` + `@pytest.mark.drift`
- Cost budget: ≤ $0.50 / 完整跑
- 失败 = block next release tag（CI gate §6.3）
- 报告输出: `/tmp/heart_drift_report.html`，CI artifact 上传保留 90 天

---

## 10. 从单测迁移的策略

**核心原则**: 现有 1677 个单测**不动**。新加 Tier A/B 不是迁移，是补漏。

例外（必须迁移）:

| 现状 | 应迁去 |
|------|-------|
| `test_consolidator.py` 中 15 个 `@requires_postgres` | Tier B `test_consolidator_with_pgvector.py` |
| `test_repair_integration.py` 3 个测 | Tier B `test_emotion_lifecycle.py` 内（合并） |
| 任何 `test_*.py` 中标记 `@pytest.mark.skip(reason="needs real LLM")` | Tier C 对应文件 |

实施阶段（§1.2 落地）做一次扫描，列出全部"应该但还没迁"的项；不立即迁，留 §1.5 / §1.6 后再分批做。

---

## 11. 实施顺序（给 §1.2 实施 prompt 用）

每一步都是独立可 merge 的 PR：

```
PR-1  pyramid-infra
      ├── 创建 contract/, integration/extend, live/ 三个目录骨架
      ├── 更新 backend/tests/conftest.py + pytest.ini markers
      ├── Makefile 加 test-contract / test-integration / test-live
      └── CI: 新增 contract + integration jobs

PR-2  fake-llm-provider
      ├── backend/heart/infra/llm_providers/fake.py
      ├── backend/tests/integration/fixtures/fake_llm_responses/*.json (seed 5 个)
      └── ModelRouter 支持 provider="fake"

PR-3  contract-tests (10 个)
      └── 按 §3 列出的 10 个文件依序提

PR-4  integration-tests-batch-1
      ├── test_memory_lifecycle.py
      ├── test_emotion_lifecycle.py
      └── test_orchestrator_hot_path.py

PR-5  integration-tests-batch-2
      ├── test_relationship_progression.py
      ├── test_inner_loop_tick.py
      ├── test_cold_war_reunion.py
      └── test_safety_short_circuits.py

PR-6  live-tests-smoke
      ├── tests/live/conftest.py + cost cap
      ├── test_real_turn_smoke.py
      └── test_purple_care_path_drill.py

PR-7  live-tests-drift  (§1.4)
      └── handoff 给 §1.4 实施
```

每 PR 必须满足:
- 上一个 PR 的所有 CI job 全绿
- 本 PR 新增/修改的 Tier 在 CI 上跑通
- HUMAN review 验证 spec 引用准确

---

## 12. 已识别风险 & Open Questions

| # | Risk / Question | 缓解 / 决策点 |
|---|----------------|--------------|
| R1 | **Fake LLM 写到一半 fixture 不够 → 测试卡住** | 启用 strict mode：cache miss 直接 fail，开发者必须显式补；不允许 fallback |
| R2 | **testcontainers 在 GitHub Actions 慢 (~30s 启动)** | session-scope fixture + parallel jobs 拆 Tier B；单 job ≤ 5 min |
| R3 | **DeepSeek API 抖动 → Tier C 偶发失败** | retry 1 次；连续 2 次再 page。月度抖动率写入 audit |
| R4 | **Cost cap 触发 → 半夜 nightly 没跑** | Slack 通知；HUMAN 第二天补跑或调上限 |
| R5 | **Voice drift baseline 第一次跑结果不稳** | 见 §1.4；至少跑 3 次取并集再固化 |
| R6 | **Tier A 写"太聪明"开始测业务逻辑** | review 时强制问："这条挂了是 contract 红还是 logic 红？" 若后者 → 移 Tier B |
| R7 | **freezegun 与 async 互动有坑** | conftest 提供 `frozen_clock` fixture，统一封装；不许直接 `freeze_time(...)` decorator |
| R8 | **CI 账单未恢复** | Tier C 短期内只能本地 + HUMAN 触发；nightly 暂缓。详 §6.4 |
| Q1 | **fake LLM fixtures 太多 → repo 膨胀？** | 上限 1 MB / fixture，超出用 hash + sidecar 文件；总目录 < 20 MB |
| Q2 | **Tier C 是否单独 staging DB？** | 是。Tier C 必须用与 prod **同 schema 版本** 的 staging PG，不与 Tier B testcontainers 混用 |
| Q3 | **per-PR 跑 Tier B 会不会拖累 dev velocity？** | 5 min 上限；超过 → 拆 job 并行；超过仍可 `--skip-integration` 但 merge gate 会拦 |

---

## 13. Cut Criteria（Phase 7 §1.2 完工判定）

```
□ docs/design/integration_test_pyramid.md  存在 + HUMAN sign-off  ← 本文
□ backend/tests/contract/conftest.py + 至少 10 个 contract 测试 全绿
□ backend/tests/integration/conftest.py + 至少 8 个新 integration 测试 全绿
□ backend/tests/live/conftest.py + 至少 2 个 live 测试（real_turn_smoke + voice_drift_baseline 占位）
□ Makefile 三个 target (test-contract / test-integration / test-live) 跑通
□ CI 配置更新：unit + contract + integration 在 every PR 跑；live 在 nightly + tag
□ Fake LLM provider 落地 + ≥ 5 个 fixture
□ Tier C 月度上限硬编码 $30；CLI --max-cost 默认 2.0
□ 一次成功的 Tier C smoke run，audit trail 写入 docs/audit/live_runs/
```

---

## 14. 引用

- `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.2 / §1.4 / §1.5 / §1.6
- `engineering_execution/EXECUTION_PLAN.md` §1.9 Phase 7
- `engineering_execution/ENGINEERING_LAWS.md` Law 4 (Verification Mandatory), Law 6 (Model Routing Strict)
- `runtime_specs/08_engineering_architecture.md` §6 Observability + §7 Testing
- `docs/test_audit.md`（Phase 7 §1.1，本设计的前置基线）
- `backend/tests/integration/test_migrations.py`（当前唯一 integration 测试，作为模板）

---

**Document Version**: 1.0
**Last Updated**: 2026-05-24
**Sign-off Required**: HUMAN(架构) — 在 PR 中 approve 后才进入 §1.2 实施 prompt
