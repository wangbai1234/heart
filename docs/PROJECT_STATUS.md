# PROJECT STATUS — Heart (心屿)

> **AI Session 入口文档。任何新的 AI session（包括 Claude Code、Cursor、其他 agent）必须优先读完这份文件再开始工作。**
>
> 这份文件是当前真理。其它历史文件可以参考，但当与本文件冲突时，**以本文件为准**。

**最后更新**：2026-05-24
**当前 Phase**：Phase 6 已完成，Phase 7 启动前置阶段
**当前分支**：`feat/misc-updates`（仓库重构）；主要工作分支 `feature/ss04-stage-engine`

---

## 1. 一句话 TL;DR

> SS01–SS07 七大子系统代码完成（在 super-branch 上），架构 audit 出 41 个 finding，**Top 10 必须先修才能开 Phase 7**。CI 已切到本地最小化 (`scripts/ci.sh`)，复杂云端 CI/CD 暂时废弃。

---

## 2. 当前完成度

### 2.1 子系统实现 (SS01–SS08)

| 模块 | 名称 | 代码 | Spec | 状态 |
|-----|------|------|------|------|
| SS01 | Soul / Identity Anchor | ✅ | `runtime_specs/01_*.md` | 在 main |
| SS02 | Memory (L1-L4) | ✅ | `runtime_specs/02_*.md` | 在 main |
| SS03 | Emotion (VAD) | ✅ | `runtime_specs/03_*.md` | 在 super-branch，等合并 |
| SS04 | Relationship Phase Engine | ✅ | `runtime_specs/04_*.md` | 在 super-branch，等合并 |
| SS05 | Composer (多层人设组合) | ✅ | `runtime_specs/05_*.md` | 在 super-branch，等合并 |
| SS06 | Inner State / Behavior | ✅ | `runtime_specs/06_*.md` | 在 super-branch，等合并 |
| SS07 | Orchestration + Safety | ✅ | `runtime_specs/07_*.md` | 在 super-branch，等合并 |
| SS08 | Infrastructure (data tier) | 部分 | `runtime_specs/08_*.md` | k8s 配置已在；DB/migrations 在 main |

### 2.2 Phase 完成度

```
Phase 0  Foundation                ✅ 完成
Phase 1  SS01 Soul                 ✅ 完成
Phase 2  SS02 Memory               ✅ 完成
Phase 3  SS03 Emotion              ✅ 完成（在 super-branch）
Phase 4  SS04 + SS05               ✅ 完成（在 super-branch）
Phase 5  SS06 Inner State          ✅ 完成（在 super-branch）
Phase 6  SS07 Orchestration+Safety ✅ 完成（在 super-branch）
Phase 7  集成 + Soul Drift 回归    🚧 启动前置（见 §3 blocker）
Phase 8  Closed Beta               ⏳ 未开始
```

---

## 3. 当前 Blocker（必须先做）

来源：`docs/audit/2026-05-23_architecture_audit.md`（Top 10 of 41 findings）

| # | 阻塞项 | 严重度 | 工时 | 依赖 |
|---|--------|--------|------|------|
| 1 | Wire 真 SafetyAgent 进 orchestrator（删 in-file fake） | **Critical** | 1d | — |
| 2 | Wire `CarePathHandler`（删硬编码 `_CARE_RESPONSE`） | **Critical** | 0.5d + 心理顾问签字 | #1 |
| 3 | 修 2 个 failing tests + audit 15 deselected tests | **Critical** | 3h | — |
| 4 | 合并双 LLM provider tree (`infra/llm/` vs `infra/llm_providers/`) | **Critical** | 0.5d | — |
| 5 | 统一 logging 到 structlog（16 个 stdlib 模块） | High | 1h | — |
| 6 | `EmotionService` 转 async | High | 2h | — |
| 7 | 冷路径 `asyncio.create_task` 失败追踪 + Prometheus | High | 1h | — |
| 8 | repair_profile spec drift 决策 | High | 待 RFC | HUMAN 决策 |
| 9 | 重命名 safety circuit breaker（`ss01_anchor` → `safety`） | High | 30min | — |
| 10 | 构建 governance-lint CI workflow | High | 1d | #1 |

**总预计**：~4 天（Critical 可并行压缩到 2 天）。

**前置子任务**：把 `feature/ss04-stage-engine` 上的 SS03-SS07 代码先分批合并进 main（≈163 文件，需分 4 个 PR，详见 [PHASE_7_READINESS_CHECKLIST.md](PHASE_7_READINESS_CHECKLIST.md) §3.2）。

---

## 4. 当前开发重点（按优先级）

1. **修 Top 10 Critical (#1-#4)** — 安全/正确性路径，没修这个不能开 Phase 7
2. **分批合并 super-branch** — Governance docs → SS03 → SS04+05+06 → Safety+SS07
3. **写 Phase 7 集成测试金字塔** — 设计文件已有：`docs/design/integration_test_pyramid.md`
4. **写 Soul Drift 回归套件** — 设计文件已有：`docs/design/soul_drift_regression.md`

---

## 5. 下一步：要做的 3 件事

按顺序：

1. ✋ **HUMAN 决策**：审阅 PR #7（设计文档），完成 3 方签字（架构 + 主创 + 心理顾问）
2. 🤖 **AI 执行**：开始 Top 10 #3（修 failing tests）和 #5/6/7/9（机械改动），不需要等签字
3. 🤖 **AI 执行**：Top 10 #1-#2（SafetyAgent / CarePath wiring）在 #7 签字后立即开干

---

## 6. 当前风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Super-branch 163 文件巨型合并 | 冲突 + review 疲劳 | 已规划分 4 PR slice（见 checklist §3.2） |
| Top 10 #1/#2 影响 PURPLE 安全路径 | 用户安全 | 必须 3 方签字 + 集成测试再上 main |
| 双 LLM provider tree (#4) | 计费/路由不一致 | 用 audit finding A-D3-16 推动收敛 |
| repair_profile spec drift (#8) | Soul Spec 漂移 | 卡住 = 等 RFC，不强推 |
| `engineering_execution/EXECUTION_PLAN.md` 信息密度过高 (97KB) | AI context 爆炸 | 当前仅作历史参考，新 session 不必读完 |

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
2. docs/PHASE_7_READINESS_CHECKLIST.md  ← 当前 phase 详细 checklist
3. docs/audit/2026-05-23_architecture_audit.md  ← 41 findings 全列表
4. runtime_specs/00_runtime_worldview.md   ← 想了解世界观时读
5. runtime_specs/0X_*.md          ← 想动哪个子系统时读对应那一份
```

其余文档详见 [`docs/README.md`](README.md)。

---

## 9. 维护规则

- **每次完成一个 Top 10 item 必须更新本文件 §3 表格**。
- **每个 Phase 切换必须重写本文件 §2/§4/§5**。
- **新增 blocker 必须进 §3，不进 GitHub Issues 不算数**（除非 issues 工作流后续被启用）。
- 这份文件不能超过 200 行；超了说明需要把细节移到 `docs/design/` 或 `docs/audit/`。
