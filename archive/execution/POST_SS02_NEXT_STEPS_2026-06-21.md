# Heart 全链路测试验收 + 前端开发启动条件 — 2026-06-21

> **Context**
>
> 用户已完成 `docs/execution/SS02_ACCEPTANCE_AND_NEXT_STEPS_2026-06-21.md` 全部执行项（P0/P1 全清，PR #42/#43 已开，#39/#40/#41 已关，#44 backlog 已建），并跑了一次 9 层全链路测试矩阵。本文件给出：
> (a) 对测试报告的独立验证结论；
> (b) 前端开发是否可以启动的判定；
> (c) 剩余债务的优先级清单与处置；
> (d) opencode 顺序执行 checklist。
>
> **执行模型**: opencode 顺序跑 P0-A → P1-A/B/P2-B issue 登记 → 等 PR #42/#43 merge；HUMAN 在 §3.2 拍板前端栈。

---

# Phase 1 — 测试报告独立验证

## 1.1 用户报告 vs 实际代码

| 报告 claim | 验证 | 结论 |
|---|---|---|
| Unit 962 pass / 15 fail (pre-existing consolidator) | `tests/unit/test_consolidator.py` 头部 `pytestmark = pytest.mark.requires_postgres`，但 import 在模块顶层 (`from heart.ss02_memory.models import ConsolidationJob, ...`)。`ConsolidationJob` 在 `models.py:433` **存在** | ⚠️ **诊断有偏差**：不是 "缺 models 属性"，是 **import 在 collection 阶段执行 → 缺 pg-only 依赖时 collect 报错 → 15 个 error**。属于测试结构问题，pre-existing |
| Fake Golden 197/0 | — | ✅ 接受 |
| Properties 15/0 | — | ✅ 接受 |
| Live Golden 47/49 (95.9%) | 与 v1.0.3 commit `878cc57` 一致 | ✅ 接受 |
| Integration 22/6 (migration gap) | 见下 P0-A | ✅ 根因正确 |
| E2E 1/1 fail (session write race) | `tests/e2e/test_login_chat_db.py:49-63` 同步 HTTP → 立即查 DB。无 wait/poll | ⚠️ **症状对、方案错**：`sleep(0.5)` 是创可贴，根因是 `/api/chat` 在 session row commit 前 return 200 |
| P0 migration 009 `op.Column` 错用 | `backend/migrations/versions/009_memory_l4_extras.py:25, 28, 34, 38` **4 处全是 `op.Column(...)`** | ✅ **真实 P0**，4 行 typo，单独 hotfix PR |

## 1.2 验收结论

> **SS02 LLM Extractor 重构交付完结 = TRUE**（PR #42 等 review/merge）
> **Heart 全栈 main 可部署 = FALSE**（migration 009 阻塞 `alembic upgrade head`）
> **前端开发可启动 = CONDITIONAL**（修完 migration 009 + HUMAN 前端栈决策 = 可启动）

---

# Phase 2 — 遗留问题清单（按优先级）

## P0 — 阻塞 main 部署，必须 24h 内修

### P0-A migration 009 `op.Column` → `sa.Column`

**文件**: `backend/migrations/versions/009_memory_l4_extras.py`

**修复**: 第 25 / 28 / 34 / 38 行 4 处 `op.Column(...)` 改为 `sa.Column(...)`。

```python
# line 25
op.add_column("fact_nodes", sa.Column("was_l4", Boolean, nullable=False, server_default="false"))
# lines 28, 34, 38
sa.Column("previously_l4_id", PG_UUID(as_uuid=True), nullable=True),
sa.Column("demoted_at", DateTime(timezone=True), nullable=True),
sa.Column("demotion_reason", Text, nullable=True),
```

确保文件头有 `import sqlalchemy as sa`，若没则补上。

**验证**:
```bash
cd backend
alembic upgrade head     # 必须能跑到 010 不报错
pytest tests/integration/test_migration_roundtrip.py -v   # 6 个红应转绿
```

**PR**: 单独 `fix(migrations): use sa.Column in 009_memory_l4_extras`，**不混 SS02 PR #42、不混 MiMo PR #43**（CLAUDE.md：CI/fix 必须独立 PR）

**估时**: 10 分钟

## P1 — 不阻塞前端，但前端启动前应登记 issue

### P1-A consolidator test 收集失败（pre-existing 结构问题）

- **现象**: 15 个 collect-time error，因为 `from heart.ss02_memory.models import ConsolidationJob` 在 module 顶层执行，unit 跑无 pg 依赖时直接 fail
- **处置选项**:
  1. (推荐) 把 import 移到 fixture 里（lazy import），`pytestmark = requires_postgres` 才真生效
  2. 把 `test_consolidator.py` 整文件挪到 `tests/integration/`（语义上本来就是 integration）
- **动作**: 开 GitHub issue `[ss02][test-infra] consolidator test 顶层 import 阻塞 unit collection`
- **不阻塞前端**

### P1-B E2E session write race — 修根因，禁创可贴

- **现象**: `/api/chat` 返回 200 后 `sessions` 行 `turn_count=0`
- **根因**: 写 session row 是 fire-and-forget / 异步 commit，在 response 后才完成
- ❌ **禁用 `await asyncio.sleep(0.5)` 创可贴**（CLAUDE.md：禁止把档 A 错误伪装成档 C）
- **正确修法**: `backend/heart/api/routes_chat_ws.py` / `/api/chat` 路由把 session row commit 移到 return 之前（同事务 flush + commit）
- **动作**: 开 GitHub issue `[ss07][e2e] /api/chat returns 200 before sessions row commit`
- **不阻塞前端**（影响 E2E 稳定性，不影响功能正确性）

## P2 — 已知债务

### P2-A v1.1.0 backlog #44

- 已记录: frag-004 / mixd-002 / adv-005
- **触发时机**: 前端 MVP 跑通后回头做 prompt 迭代

### P2-B encoder-worker 容器 restart loop

- **现象**: `heart-encoder-worker` 持续重启
- **影响**: SS02 后台编码（向量入 pgvector）跑不通
- **处置**: 看 pod log 找退出码，可能是 OOM / model load 失败 / DB 连接
- **动作**: 开 GitHub issue `[ss02][infra] encoder-worker restart loop`
- **不阻塞前端**（前端 chat 走 LLM 直出，不依赖 encoder-worker 实时）
- **阻塞 Closed Beta**（无 encoder = L2/L3 memory pipeline 不通）

---

# Phase 3 — 前端开发启动条件

## 3.1 启动 checklist（按顺序）

```
□ P0-A migration 009 hotfix PR open + merge (10 分钟)
□ PR #42 (SS02 v1.0.3) review + merge → PROJECT_STATUS 标 "✅ SS02 交付完结 @ <date>"
□ PR #43 (MiMo TTS) review + merge
□ P1-A consolidator + P1-B E2E + P2-B encoder-worker 各开 1 GitHub issue（登记，不修）
□ HUMAN 拍板前端技术栈 → docs/design/frontend_stack_decision.md
□ Phase 9 Frontend MVP 启动
```

## 3.2 HUMAN 前端栈决策模板

填一份 `docs/design/frontend_stack_decision.md`（参考维度）:

| 维度 | RN + Expo | Flutter | Next.js + Capacitor |
|---|---|---|---|
| 单代码库覆盖 iOS + Android + Web | ✅ | ✅ | ✅（Web 原生 + iOS/Android 套壳） |
| 团队栈匹配（React/TS 熟悉度） | ✅ | ⚠️ Dart 学习曲线 | ✅ |
| WebSocket 长连接 + 流式 | ✅ | ✅ | ✅ |
| Push（iOS APNs / Android FCM） | ✅ Expo Notifications | ✅ | ⚠️ Capacitor 插件依赖原生壳 |
| 语音输入/播放（SS08 接口） | ✅ Expo AV | ✅ | ⚠️ Capacitor 插件 |
| App Store 上架预期工作量 | 中 | 中 | 高（套壳审核风险） |
| 开发节奏 | 快（hot reload + Expo Go） | 中 | 快 |
| Heart 当前 `web/` 目录复用度 | 中（React 组件可借） | 低 | **高**（直接用 web/） |

**默认推荐**:
- 若 Closed Beta 目标是「先 web 后 mobile」→ **Next.js + Capacitor**（直接用现有 `web/`，含 `web/src/hooks/useWebSocket.ts`）
- 若目标是「mobile-first」→ **RN + Expo**

HUMAN 拍板后填表，提 PR `docs(design): frontend stack decision`。

---

# Phase 4 — Cut Criteria

```
□ migration 009 hotfix merge + alembic upgrade head 全绿
□ PR #42 SS02 + PR #43 MiMo merge
□ P1-A / P1-B / P2-B 3 个 issue 已建并 link 入 PROJECT_STATUS.md §6
□ docs/design/frontend_stack_decision.md HUMAN 签字
□ PROJECT_STATUS.md 维护规则段最后一行改:
  "✅ SS02 Memory LLM Extractor 重构交付完结 @ <date>
   🚀 Phase 9 Frontend MVP 启动 @ <date>，栈 = <选定>"
```

---

# Phase 5 — 改动文件清单

| 阶段 | 文件 | 改动 |
|---|---|---|
| P0-A | `backend/migrations/versions/009_memory_l4_extras.py` | 4 处 `op.Column` → `sa.Column`（必要时补 `import sqlalchemy as sa`） |
| P1-A | GitHub issue | 新建 `[ss02][test-infra] consolidator collect fail` |
| P1-B | GitHub issue | 新建 `[ss07][e2e] /api/chat returns before commit` |
| P2-B | GitHub issue | 新建 `[ss02][infra] encoder-worker restart loop` |
| P3 | `docs/design/frontend_stack_decision.md` | HUMAN 新建 + 签字 |
| Phase 4 | `docs/PROJECT_STATUS.md` | §3 加 P1-A/B/P2-B issue link + §维护规则段更新 |

---

# Phase 6 — Verification

```bash
# 1. migration 链能跑到头
cd backend && alembic upgrade head
pytest tests/integration/test_migration_roundtrip.py -v   # 6 红 → 全绿

# 2. PR 状态
gh pr list --state open --author "@me"   # 应 ≤ 3，全部 < 7 天

# 3. PROJECT_STATUS 一致
grep -E "SS02 .* 交付完结" docs/PROJECT_STATUS.md
grep -E "Phase 9 .* 启动" docs/PROJECT_STATUS.md
```

---

# Phase 7 — 风险表

| 风险 | 触发 | 缓解 |
|---|---|---|
| P0 hotfix 与 SS02 PR #42 冲突 | 都改 backend/migrations/ 同区域 | 009 改动只 4 行，PR #42 已不动 migrations；按时间顺序 merge |
| HUMAN 前端栈决策被拖延 | 3 个候选都"够用"导致 paralysis | 给出默认推荐（见 §3.2），HUMAN 只需"接受/否决" |
| consolidator 与 E2E issue 永远不修 | 没排进 Phase 9/10 sprint | 在 PROJECT_STATUS.md §3 留行，每 Phase 切换时 review |
| encoder-worker 在 Closed Beta 前未修 | L2/L3 memory pipeline 不通 | Phase 10 Closed Beta 前置条件，进 §3 blocker 表 |
| P1-B 用 sleep 创可贴蒙混过去 | 怕动 routes_chat_ws.py | 已明确禁用，issue body 写"reject any PR with sleep() workaround" |

---

# Phase 8 — opencode 执行 checklist（顺序）

```bash
# === P0-A: migration 009 hotfix ===
git fetch origin
git checkout -b fix/migration-009-sa-column origin/main
# 编辑 backend/migrations/versions/009_memory_l4_extras.py（4 处 op.Column → sa.Column）
cd backend && alembic upgrade head    # 本地验证
pytest tests/integration/test_migration_roundtrip.py -v
cd ..
git add backend/migrations/versions/009_memory_l4_extras.py
git commit -m "fix(migrations): use sa.Column in 009_memory_l4_extras"
bash scripts/ci.sh
git push -u origin fix/migration-009-sa-column
gh pr create --base main \
  --title "fix(migrations): use sa.Column in 009_memory_l4_extras" \
  --body "10-line typo blocking alembic upgrade to head. Fixes 6 integration migration tests."

# === P1/P2 issue 登记 ===
gh issue create --title "[ss02][test-infra] consolidator test 顶层 import 阻塞 unit collection" --body "..."
gh issue create --title "[ss07][e2e] /api/chat returns 200 before sessions row commit" --body "..."
gh issue create --title "[ss02][infra] encoder-worker restart loop" --body "..."

# === 等 PR #42 / #43 / migration hotfix merge ===
# 然后 HUMAN 进 §3.2 决策
```

---

# 一句话总结

**SS02 重构成功。migration 009 是唯一 P0（10 分钟修）。前端可以启动，只欠 HUMAN 拍板技术栈。consolidator / E2E race / encoder-worker 都不阻塞前端，但要先登记 issue 防 forget。**

---

**版本**: 1.0.0
**创建日期**: 2026-06-21
**主笔**: Opus 4.7
**执行模型**: opencode 跑 P0-A + issue 登记；HUMAN 拍板 §3.2 前端栈
**预计 Phase 9 启动**: 2026-06-22（24h 内）
