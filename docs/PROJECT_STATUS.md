# PROJECT STATUS — Heart (心屿)

> **AI Session 入口文档。任何新的 AI session（包括 Claude Code、Cursor、其他 agent）必须优先读完这份文件再开始工作。**
>
> 这份文件是当前真理。其它历史文件可以参考，但当与本文件冲突时，**以本文件为准**。

**最后更新**：2026-06-04
**当前 Phase**：Phase 7 验证完成 → 准备进入 R-FE-01（前端 MVP）+ Phase 9-11 路线
**当前分支**：`main`（SS03-07 已集成，governance 已合并，热路径接线已落地）

---

## 1. 一句话 TL;DR

> SS01–SS07 七大子系统代码完成并集成到 main，7 Phase 验证全部通过；`/api/chat` 热路径已通过 Orchestrator 真实穿过 SS02/SS03/SS05/SS07 + Safety（`backend/heart/api/wiring.py` 验证）。**当前唯一 active blocker：双 LLM provider tree 收敛**。下一步：收敛 LLM tree → 前端技术栈 HUMAN 决策 → 执行 Phase 9 (Frontend MVP) → Phase 10 (Closed Alpha) → Phase 11 (Beta)。

---

## 2. 当前完成度

### 2.1 子系统实现 (SS01–SS08)

| 模块 | 名称 | 代码 | Spec | 状态 |
|-----|------|------|------|------|
| SS01 | Soul / Identity Anchor | ✅ | `runtime_specs/01_*.md` | 在 main |
| SS02 | Memory (L1-L4) | ✅ | `runtime_specs/02_*.md` | 在 main |
| SS03 | Emotion (VAD) | ✅ | `runtime_specs/03_*.md` | 在 main（PR #17 集成） |
| SS04 | Relationship Phase Engine | ✅ | `runtime_specs/04_*.md` | 在 main（PR #17 集成） |
| SS05 | Composer (多层人设组合) | ✅ | `runtime_specs/05_*.md` | 在 main（PR #17 集成） |
| SS06 | Inner State / Behavior | ✅ | `runtime_specs/06_*.md` | 在 main（PR #17 集成） |
| SS07 | Orchestration + Safety | ✅ | `runtime_specs/07_*.md` | 在 main（PR #17 集成） |
| SS08 | Infrastructure (data tier) | 部分 | `runtime_specs/08_*.md` | k8s 配置已在；DB/migrations 在 main |

### 2.2 Phase 完成度

```
Phase 0  Foundation                ✅ 完成
Phase 1  SS01 Soul                 ✅ 完成
Phase 2  SS02 Memory               ✅ 完成
Phase 3  SS03 Emotion              ✅ 完成（已合并 main，PR #17）
Phase 4  SS04 + SS05               ✅ 完成（已合并 main，PR #17）
Phase 5  SS06 Inner State          ✅ 完成（已合并 main，PR #17）
Phase 6  SS07 Orchestration+Safety ✅ 完成（已合并 main，PR #17）
Phase 7  集成 + Soul Drift 回归    ✅ 验证完成（7 Phase 全通过）
Phase 8  Closed Beta               ⏳ 未开始
```

---

## 3. 当前 Blocker（必须先做）

来源：`docs/audit/2026-05-23_architecture_audit.md`（Top 10 of 41 findings）

| # | 阻塞项 | 严重度 | 工时 | 依赖 | 状态 |
|---|--------|--------|------|------|------|
| 1 | Wire 真 SafetyAgent 进 orchestrator（删 in-file fake） | **Critical** | 1d | — | ✅ 已完成 |
| 2 | Wire `CarePathHandler`（删硬编码 `_CARE_RESPONSE`） | **Critical** | 0.5d | #1 | ✅ 已完成（CarePathHandler + 14 模板 + _routing.yaml） |
| 3 | 修 2 个 failing tests + audit 15 deselected tests | **Critical** | 3h | — | ✅ 已完成（612 unit + 111 contract） |
| 4 | 合并双 LLM provider tree (`infra/llm/` vs `infra/llm_providers/`) | **Critical** | 0.5d | — | ❌ **未解决——当前唯一 active blocker** |
| 5 | 统一 logging 到 structlog | High | 1h | — | ✅ 已完成 |
| 6 | `EmotionService` 转 async | High | 2h | — | ✅ 已完成（get_context_block 已是 async） |
| 7 | 冷路径 `asyncio.create_task` 失败追踪 + Prometheus | High | 1h | — | ⏳ 待验证 |
| 8 | repair_profile spec drift 决策 | High | 待 RFC | HUMAN 决策 | ⏳ 等 RFC |
| 9 | 重命名 safety circuit breaker（`ss01_anchor` → `safety`） | High | 30min | — | ⏳ 待验证 |
| 10 | 构建 governance-lint CI workflow | High | 1d | #1 | ✅ 已完成（PR #16） |

**剩余工作**：#4（双 LLM tree 收敛）约 0.5d + #7/#9 待验证。

**已验证落地（2026-06-04）**：`/api/chat` 不再用 None 占位——`routes.py:144` 注入 `Depends(get_orchestrator)`，`wiring.py` 实接 MemoryService / EmotionService / SafetyAgent / ComposerService / Orchestrator。restore_project.md 中 R-HOT-01 / R-SAFE-01 / R-SS07-01（最小可用版）的前置条件已满足。

---

## 4. 当前开发重点（按优先级）

> 路线决策（2026-06-04 HUMAN 决策）：**先收 LLM tree → 前端栈对比 → R-FE-01 → Phase 10-11**。
> Phase 7 集成测试金字塔 + Soul Drift 回归套件**延后**，与 Phase 9 联调期并行推进，避免阻塞前端可演示节点。

1. **修 Top 10 剩余 Critical (#4)** — 双 LLM provider tree 收敛（`infra/llm/` vs `infra/llm_providers/`），0.5d
2. **R-FE-01 §3.1 前端技术栈决策** — 输出 `docs/design/frontend_stack_decision.md`，对比 React Native+Expo / Flutter / Next.js Web，**HUMAN 批准后方可进入实施**
3. **R-FE-01 §3.2–3.6 前端 MVP 实施** — 照搬 `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` Phase 9 全部子任务
4. **Phase 10 Closed Alpha** — Staging bring-up / Secrets pre-flight / Alpha onboarding / Cost cap / Drift 实时监控（Phase 9 cut criteria 全绿后启动）
5. **Phase 11 Beta** — Multi-region K8s / Auto-scaling / Beta cohort / PURPLE live drill（Phase 10 cut criteria 全绿后启动）
6. **并行债务**：集成测试金字塔、Soul Drift 回归、SS05/SS06 单测补齐

---

## 5. 下一步：要做的 3 件事（严格按顺序）

1. 🤖 **AI 执行**：收敛双 LLM provider tree（合并 `infra/llm_providers/` 进 `infra/llm/`，或反向；最终保留单一权威实现）。完成前不开 R-FE-01。
2. 🤖 **AI 输出 + 👤 HUMAN 决策**：`docs/design/frontend_stack_decision.md`——三方案对比（RN+Expo / Flutter / Next.js Web），按演示成本 / 跨端覆盖 / 单人维护成本评分。HUMAN 在 PR review 中拍板。
3. 🤖 **AI 执行**：按 HUMAN 决策的栈，进入 Phase 9 §3.2（API contract lockdown / OpenAPI + TS gen）→ §3.3 scaffold → §3.4 Chat UI MVP → §3.5 Auth + Push → §3.6 cut criteria。Phase 9 cut criteria 全绿后无缝转 Phase 10。

---

## 6. 当前风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 双 LLM provider tree (#4) | 计费/路由不一致 | 内测前必须收敛 |
| SS05/SS06 测试覆盖不足 | 回归风险 | 补充单元测试 |
| repair_profile spec drift (#8) | Soul Spec 漂移 | 卡住 = 等 RFC，不强推 |
| Observability 覆盖不足 | 内测可观测性 | 仅 turn_profiler，需补 Prometheus + log 聚合 |

---

## 7. CI / 工程基础设施

**已废弃**：Gitee Go 高级流水线、artifact upload、deploy、release workflow。原因：需要主机组，billing 复杂，当前阶段不需要。

**当前 CI**：`scripts/ci.sh` 单一脚本，本地 / GitHub Actions 行为完全一致。

```bash
bash scripts/ci.sh                # lint + unit-tests + schema-validation
bash scripts/ci.sh lint
bash scripts/ci.sh unit-tests
bash scripts/ci.sh integration-tests   # opt-in，需本地 postgres + redis + API key
```

历史 CI 配置存放：`archive/ci-legacy/`。

---

## 8. 文档导航（最小集）

新 session 推荐阅读顺序：

```
1. docs/PROJECT_STATUS.md          ← 本文件（必读）
2. docs/audit/2026-05-23_architecture_audit.md  ← 41 findings 全列表
3. docs/design/integration_test_pyramid.md  ← Phase 7 集成测试设计
4. docs/design/soul_drift_regression.md  ← Soul Drift 回归设计
5. runtime_specs/00_runtime_worldview.md   ← 想了解世界观时读
6. runtime_specs/0X_*.md          ← 想动哪个子系统时读对应那一份
```

其余文档详见 [`docs/README.md`](README.md)。

---

## 9. 维护规则

- **每次完成一个 Top 10 item 必须更新本文件 §3 表格**。
- **每个 Phase 切换必须重写本文件 §2/§4/§5**。
- **新增 blocker 必须进 §3，不进 GitHub Issues 不算数**（除非 issues 工作流后续被启用）。
- 这份文件不能超过 200 行；超了说明需要把细节移到 `docs/design/` 或 `docs/audit/`。
