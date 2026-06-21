# PROJECT STATUS — Heart (心屿)

> **AI Session 入口文档。任何新的 AI session（包括 Claude Code、Cursor、其他 agent）必须优先读完这份文件再开始工作。**
>
> 这份文件是当前真理。其它历史文件可以参考，但当与本文件冲突时，**以本文件为准**。

**最后更新**：2026-06-21
**当前 Phase**：🟡 SS02 prompt v1.0.3 完结 (47/49 95.9%) / 交付未完结 — 核心实现文件未追踪 + 分支已是事实主干
**当前分支**：`feat/mimo-tts-provider`（事实主干，待拆为 feat/ss02-llm-extractor-v1.0.3）

---

## 1. 一句话 TL;DR

> 🟡 SS02 功能完结（prompt v1.0.3, 47/49 95.9% strict），交付未完结：核心实现文件未追踪 + 分支已是事实主干。下一步：拆分支 + add 未追踪文件 → SS02 独立 PR → 前端栈决策。

---

## 2. 当前完成度

### 2.1 子系统实现 (SS01–SS08)

| 模块 | 名称 | 代码 | Spec | 状态 |
|-----|------|------|------|------|
| SS01 | Soul / Identity Anchor | ✅ | `runtime_specs/01_*.md` | 在 main |
| SS02 | Memory (L1-L4) | ✅ | `runtime_specs/02_*.md` | LLM Extractor refactor 验收完成，v1.0.1 prompt 95.9% pass |
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

来源：`docs/execution/MEMORY_EXTRACTOR_REFACTOR_AUDIT_AND_v1_0_2_PLAN.md`（审计 + 修复方案）

| # | 阻塞项 | 严重度 | 所属 | 状态 |
|---|--------|--------|------|------|
| - | v1.0.3 prompt ✅ committed (878cc57) | Complete | — | ✅ 47/49 (95.9%) |
| 1 | **SS02 实现文件未 git track**（regex_shadow/resolver/writer/promoter/golden_loader/hints/extractor_diff_report） | **🔴 P0** | P0-1 | ⏳ |
| 2 | feat/mimo-tts-provider 已沦为"事实主干"（12 commits 跨 SS02+voice+MiMo） | **🔴 P0** | P0-2 | ⏳ 拆为 feat/ss02-llm-extractor-v1.0.3 |
| 3 | PR #41 open 7 天硬性上限已到 | **🔴 P0** | P0-3 | ⏳ close + 重开 MiMo-only |
| 4 | PR #39 / #40 超 7 天 + 单人 PR 达上限 3 | 🟠 P1 | P1-1 | ⏳ 关或合 |
| 5 | v1.1.0 backlog 未开 issue | 🟡 P2 | P1-2 | frag-004/mixd-002/adv-005 |

**✅ SS02 Memory LLM Extractor 重构完结 @ 2026-06-21**。v1.0.3 prompt 手术刀修复（R11/R5/R6/R12 + Example 9）将 strict scoring pass rate 从 79.2% 推至 95.9%。残余 3 case 入 v1.1.0 backlog。所有 infra（scoring / INV / approval / dual-mode rationale）已完成。Prompt 版本锁定 1.0.3，code 在 `feat/mimo-tts-provider`。

---

## 4. 当前开发重点（按优先级）

> SS02 Memory Extractor 重构全部 PR 完成。下一步：合 main → 前端栈决策。

1. **合 main** — 当前 `feat/mimo-tts-provider` 分支合入 main，PR + merge。
2. **前端技术栈决策** — 输出 `docs/design/frontend_stack_decision.md`，HUMAN 拍板。
3. **Phase 9 Frontend MVP** — 按选定栈实施 Chat UI / Auth / Push。
4. **Phase 10 Closed Beta** — Staging bring-up / Alpha onboarding / Drift 监控。

**并行债务**：
- coref-004 precision (relation + other FP) → v1.1.0 prompt 迭代
- Prometheus metrics 缺口
- 集成测试金字塔、Soul Drift 回归

---

## 5. 下一步

1. 🤖 **P0-1 untracked 文件 audit + add**（24h）→ git add 关键 SS02 实现文件
2. 🤖 **P0-2 拆分支 feat/ss02-llm-extractor-v1.0.3**（24h）→ cherry-pick 5 commits + add commit → PR
3. 🤖 **P0-3 PR #41 收敛**（24h）→ close + 重开 MiMo-only PR
4. 🤖 **P1-1 收敛 PR #39 / #40** → 关或合
5. 🤖 **P1-2 v1.1.0 backlog issue** → GitHub issue + link PROJECT_STATUS
6. 👤 **HUMAN 决策** — 前端技术栈（RN+Expo / Flutter / Next.js）

详见 `docs/execution/SS02_ACCEPTANCE_AND_NEXT_STEPS_2026-06-21.md`

## 6. 当前风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| **事实主干分支** | 任何 SS02 改动现在从 mimo 分支出，入 main 会夹带 12 commits | P0-2 拆分 feat/ss02-llm-extractor-v1.0.3 |
| **PR #41 7 天上限** | 硬性条款，必须 24h 内收敛 | P0-3 close + 重开 MiMo-only |
| **未追踪 SS02 文件** | main 跑 `from heart.ss02_memory.extractor.resolver import Resolver` 会 ImportError | P0-1 git add + commit |
| SS05/SS06 测试覆盖不足 | 回归风险 | 并行债务 |

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
2. docs/audit/2026-06-20_dual_mode_skip_rationale.md  ← dual-mode 跳过理由
3. docs/execution/MEMORY_EXTRACTOR_REFACTOR_AUDIT_AND_v1_0_2_PLAN.md  ← 审计 + v1.0.2 方案
4. docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md  ← SS02 refactor 主 spec
5. docs/design/memory_golden_set_design.md  ← Golden Set + strict scoring 定义
```

其余文档详见 [`docs/README.md`](README.md)。

---

## 9. 维护规则

- **每次完成一个 Top 10 item 必须更新本文件 §3 表格**。
- **每个 Phase 切换必须重写本文件 §2/§4/§5**。
- **新增 blocker 必须进 §3，不进 GitHub Issues 不算数**（除非 issues 工作流后续被启用）。
- 这份文件不能超过 200 行；超了说明需要把细节移到 `docs/design/` 或 `docs/audit/`。
- **🟡 SS02 prompt 完结 @ 2026-06-21** — v1.0.3, commit 878cc57 (47/49)。**交付完结待 untracked SS02 实现文件入 main**。
- **v1.1.0 backlog**: frag-004 / mixd-002 / adv-005（GitHub issue 待开）
- 验收文档: `docs/execution/SS02_ACCEPTANCE_AND_NEXT_STEPS_2026-06-21.md`
