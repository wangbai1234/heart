# 仓库治理 — Single Source of Truth, 分层, 与清理计划

> **角色**: 仓库治理宪法 (Repository Governance Constitution)
> **目标读者**: HUMAN (拍板) + 所有 AI agent (必读)
> **修改门槛**: 任何对本文件的修改必须 PR + HUMAN approve
> **配套阅读顺序**: `STATUS.md` (现在的位置) → 本文件 (规则) → `docs/INDEX.md` (索引)

---

# 0. 这份文档解决什么问题

> 你已经用 AI 写了 53 个 .md 文件。其中有重复、过时、散落、上下文割裂。
> 任何新 session 都要花 5-30 分钟才能搞清楚"现在到底是什么状态"。
>
> 本文件的存在是为了让这件事**永远不再发生**。

它定义三件事：

1. **每一个话题，到底哪份文件是唯一真相源 (SSOT)**
2. **每一份文件属于哪一层，能写什么、不能写什么**
3. **当前散落的文档怎么清理 (cleanup plan)**

如果一个 AI session 不读本文件，它对仓库的认知必然过时。

---

# 1. Repository Audit (审计报告 — 2026-05-23)

## 1.1 文档总览

| 维度 | 数量 |
|------|------|
| 总 .md 文件 | 53 |
| Runtime Spec (SSOT) | 10 |
| Engineering Process | 10 |
| Design Docs | 12 |
| Module READMEs | 9 |
| Migration Docs | 4 |
| Root Level Files | 8 |
| 一次性报告 (应归档) | 6 |
| 设计 vs 实施总结混杂 | 4 |

**核心问题**：根目录 8 个 .md + backend/ 散落 6 个 .md + migrations/ 4 个 = **18 个文件在它们不该在的位置**。

## 1.2 文件分类清单

### 🟢 核心 SSOT (10) — 神圣不可侵犯

| File | Role |
|------|------|
| `runtime_specs/00_runtime_worldview.md` | 世界观 |
| `runtime_specs/01_identity_anchor_soul_spec.md` | SS01 spec |
| `runtime_specs/02_memory_runtime.md` | SS02 spec |
| `runtime_specs/03_emotion_state_machine.md` | SS03 spec |
| `runtime_specs/04_relationship_phase_engine.md` | SS04 spec |
| `runtime_specs/05_persona_composition_runtime.md` | SS05 spec |
| `runtime_specs/06_inner_state_behavior_runtime.md` | SS06 spec |
| `runtime_specs/07_agent_orchestration.md` | SS07 spec |
| `runtime_specs/08_engineering_architecture.md` | SS08 spec |
| `runtime_specs/README.md` | spec navigation |

**判定**：✅ 全部保留。已分层、已唯一。

### 🟢 Engineering Process (10) — 保留但有内部去重

| File | Role | 状态 |
|------|------|------|
| `engineering_execution/README.md` | dir 入口 | ✅ keep |
| `engineering_execution/EXECUTION_PLAN.md` | 战略 (96K, 3139 行) | ⚠️ FREEZE，标注 v1.0 / Historical |
| `engineering_execution/PRACTICAL_MODEL_GUIDE.md` | Phase 0-6 操作 | ✅ keep |
| `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` | Phase 7+ 操作 | ✅ keep |
| `engineering_execution/AI_MODEL_ROUTING.md` | 路由决策 | ✅ keep (SSOT for routing) |
| `engineering_execution/HUMAN_REVIEW_CHECKLIST.md` | review 边界 | ✅ keep (SSOT for review) |
| `engineering_execution/ENGINEERING_LAWS.md` | 12 条法则 | ✅ keep (SSOT for laws) |
| `engineering_execution/SPEC_DRIVEN_WORKFLOW.md` | 工作流 | ✅ keep |
| `engineering_execution/CLAUDE_CODE_AGENTS.md` | agent 配置 | ✅ keep |

**判定**：EXECUTION_PLAN.md 与其余 6 个有大量内容重叠（§3=routing, §7=human review, §8=failure modes, §9=laws）。**不删，但标记 Historical/Frozen**，新内容只进 ROUTING/REVIEW/LAWS。

### 🟡 Design Docs (12) — 需要区分设计 vs 实施总结

#### 真·设计文档（保留，spec 实施前的决策记录）

| File | 状态 |
|------|------|
| `docs/design/conflict_resolver.md` | ✅ keep |
| `docs/design/decay_engine_implementation.md` | ✅ keep (重命名 → `decay_engine.md`) |
| `docs/design/initiative_decider.md` | ✅ keep |
| `docs/design/purple_care_path.md` | ✅ keep |
| `docs/design/reconstructor_design.md` | ✅ keep (重命名 → `reconstructor.md`) |
| `docs/design/repair_mechanic.md` | ✅ keep |
| `docs/design/retriever_implementation.md` | ✅ keep (重命名 → `retriever.md`) |
| `docs/design/streaming_anti_pattern.md` | ✅ keep |
| `docs/design/wellbeing_monitor.md` | ✅ keep |

#### Implementation Summary（一次性 postmortem，**代码即真相，应归档**）

| File | 动作 |
|------|------|
| `docs/design/consolidator_implementation_summary.md` | 📦 → `docs/archive/impl_summaries/` |
| `docs/design/forgetting_affect_implementation_summary.md` | 📦 → `docs/archive/impl_summaries/` |
| `docs/design/reconstructor_implementation_summary.md` | 📦 → `docs/archive/impl_summaries/` |
| `backend/heart/ss01_soul/IMPLEMENTATION_SUMMARY.md` | 📦 → `docs/archive/impl_summaries/ss01_soul.md` |

**原则**：implementation summary 是历史记录。**代码 + spec + commit message 才是 source of truth**。归档但不删（git history 可查证）。

### 🟡 Prompts (1) — 需要扩张

| File | 状态 |
|------|------|
| `docs/prompts/critic_agent.md` | ✅ keep |

**判定**：`docs/prompts/` 是未来 Prompt Spec 层的位置。**目前只有 1 个 prompt 被显式归档**——其他 6+ agent prompt（Orchestrator system、Safety LLM、Reconstructor、Wellbeing、Director、Care Path templates）散落在代码字符串里。**Phase 7 任务**：把所有"prompt 文本"集中到 `docs/prompts/`。

### 🔴 Root 污染 (8) — 必须清理

| File | 动作 | 原因 |
|------|------|------|
| `README.md` | ✅ keep | 项目入口 |
| `STATUS.md` | 🆕 NEW | 5-分钟开发入口（本次新增） |
| `.claude/CLAUDE.md` | ✅ keep (in .claude/) | Claude Code 配置 |
| `AGENTS.md` | ⚠️ 与 `.claude/CLAUDE.md` 合并或保留为多 agent 通用入口 | 待 HUMAN 决定 |
| `CHANGES_SUMMARY.md` | 📦 → `docs/archive/2026-05-15_llm_simplification.md` | 一次性 |
| `CI_FIX_REPORT.md` | 📦 → `docs/archive/2026-05-20_ci_fix.md` | 一次性 |
| `PHASE_0_COMPLETION_REPORT.md` | 📦 → `docs/archive/phase_0_completion.md` | 一次性 |
| `QUICKSTART_LLM.md` | 📦 → `docs/quickstart_llm.md` | 不是项目入口 |
| `「心屿」产品需求文档 v1.0（海外版）.md` | 📦 → `docs/vision/PRD_v1.0_overseas.md` | PRD 该在 vision/ |

**目标**：根目录 .md 文件 **从 8 个降到 ≤ 3 个**（README, STATUS, 可选 AGENTS）。

### 🔴 Backend 散落 (8) — 必须合并/移动

| File | 动作 |
|------|------|
| `backend/README.md` | ✅ keep (backend 入口) |
| `backend/ALEMBIC_QUICKSTART.md` | 🔥 merge into `backend/migrations/README.md`，删 |
| `backend/docs/LLM_GUIDE.md` | ⚠️ consolidate with `QUICKSTART_LLM.md` → keep 1 个，放 `docs/llm_guide.md` |
| `backend/heart/infra/llm_providers/README.md` | ✅ keep (module-level) |
| `backend/heart/infra/README_COST_TRACKER.md` | ⚠️ 重命名 → `backend/heart/infra/llm_cost_tracker.README.md`（与 `llm_cost_tracker.py` 配对） |
| `backend/heart/ss01_soul/DRIFT_DETECTOR_DESIGN.md` | 🚚 → `docs/design/drift_detector.md` |
| `backend/heart/ss01_soul/IMPLEMENTATION_SUMMARY.md` | 📦 archive |
| `backend/heart/ss01_soul/README.md` | ✅ keep |
| `backend/heart/ss03_emotion/CONTAGION_MOODDRIFT_README.md` | 🔥 merge into `backend/heart/ss03_emotion/README.md`，删 |
| `backend/heart/ss03_emotion/README.md` | ✅ keep |

### 🔴 Migrations (4) — 过度文档化

| File | 动作 |
|------|------|
| `backend/migrations/README.md` | ✅ keep (扩充 = SETUP_GUIDE + EXAMPLES) |
| `backend/migrations/SETUP_GUIDE.md` | 🔥 merge into README，删 |
| `backend/migrations/MIGRATION_EXAMPLES.md` | 🔥 merge into README "Examples" section，删 |
| `backend/migrations/CONFIG_SUMMARY.md` | 📦 archive (历史状态快照) |

---

# 2. Single Source of Truth Map (SSOT 强约束)

> **规则**：每个话题只有一个 SSOT 文件。其他文件**只能引用**，不能并行定义。
> 违反此规则的 PR 必须被拒绝。

| 话题 | SSOT 文件 | 谁可以改 | 修改门槛 |
|------|-----------|----------|---------|
| Runtime Worldview | `runtime_specs/00_runtime_worldview.md` | HUMAN | RFC + HUMAN approve |
| SS01 Soul Spec | `runtime_specs/01_identity_anchor_soul_spec.md` | HUMAN | RFC |
| SS02 Memory | `runtime_specs/02_memory_runtime.md` | HUMAN | RFC |
| SS03 Emotion | `runtime_specs/03_emotion_state_machine.md` | HUMAN | RFC |
| SS04 Relationship | `runtime_specs/04_relationship_phase_engine.md` | HUMAN | RFC |
| SS05 Composer | `runtime_specs/05_persona_composition_runtime.md` | HUMAN | RFC |
| SS06 Inner State | `runtime_specs/06_inner_state_behavior_runtime.md` | HUMAN | RFC |
| SS07 Orchestration | `runtime_specs/07_agent_orchestration.md` | HUMAN | RFC |
| SS08 Infrastructure | `runtime_specs/08_engineering_architecture.md` | HUMAN | RFC |
| 工程法则 (Engineering Laws) | `engineering_execution/ENGINEERING_LAWS.md` | HUMAN | RFC |
| AI Model Routing | `engineering_execution/AI_MODEL_ROUTING.md` | HUMAN | PR |
| 人工 Review 边界 | `engineering_execution/HUMAN_REVIEW_CHECKLIST.md` | HUMAN | PR |
| Phase 0-6 操作 | `engineering_execution/PRACTICAL_MODEL_GUIDE.md` | AI 可改 prompt，HUMAN 改 phase 结构 | PR |
| Phase 7+ 操作 | `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` | 同上 | PR |
| 当前项目状态 (Dev Entry) | `STATUS.md` | AI 必须每个 phase 收尾时更新 | PR |
| 文件索引 | `docs/INDEX.md` | AI + HUMAN | PR |
| AI Compressed Context | `docs/AI_CONTEXT.md` | HUMAN 主导 | PR |
| 仓库治理 (本文件) | `docs/GOVERNANCE.md` | HUMAN | RFC |
| 产品需求 (PRD) | `docs/vision/PRD_v1.0_overseas.md` | HUMAN | RFC |
| Soul 实例 (Rin/Dorothy) | `soul_specs/<character>/v*.yaml` | HUMAN + 心理顾问 | 见 SS01 §10 |
| Activity Pool | `config/activity_pools/<character>.yaml` | HUMAN | 见 SS06 §10 |
| 单 Subsystem 模块说明 | `backend/heart/ss0X_<name>/README.md` | AI 可改 | PR |
| Subsystem Design 决策 | `docs/design/<topic>.md` | AI 可起草 → HUMAN approve | PR |
| Agent Prompt 文本 | `docs/prompts/<agent>.md` | AI 可改 → HUMAN review | PR |
| 一次性报告 / 历史快照 | `docs/archive/YYYY-MM-DD_<topic>.md` | 写一次后冻结 | 不改 |

## 2.1 SSOT 冲突仲裁

```
情况 A: 代码与 spec 不一致
  → spec 赢。改代码。
  → 如果 spec 错了：提 RFC 改 spec，再改代码。
  
情况 B: design doc 与 spec 不一致
  → spec 赢。design doc 必须更新或归档。
  
情况 C: README 与代码不一致
  → 代码赢。改 README。
  
情况 D: 两个 doc 定义了同一件事
  → 这是违反治理规则。指认 SSOT，删除/合并另一个。
```

---

# 3. Documentation Hierarchy (五层)

> **规则**：每个 .md 文件**必须**归属于一层。一个文件不能跨层。

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Vision         产品愿景 / PRD                       │
│  Where: docs/vision/                                         │
│  Lifetime: 半年-1 年                                          │
│  Edit: HUMAN only                                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Runtime Spec   系统级 spec (SSOT for "what")        │
│  Where: runtime_specs/                                       │
│  Lifetime: 整个项目                                            │
│  Edit: HUMAN, RFC 制                                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Engineering    工程过程 (SSOT for "how to build")    │
│  Where: engineering_execution/                               │
│  Lifetime: 整个项目，但允许 phase-revision                     │
│  Edit: AI + HUMAN                                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Implementation 具体实现 design + module README       │
│  Where: docs/design/, docs/prompts/, backend/**/README.md    │
│  Lifetime: 实施期间，code 落地后可归档                          │
│  Edit: AI + HUMAN                                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Archive        一次性报告 / postmortem / 历史快照    │
│  Where: docs/archive/                                        │
│  Lifetime: 永久保存，永不再改                                   │
│  Edit: write-once                                            │
└─────────────────────────────────────────────────────────────┘

横切 (cross-cutting, 不属于任何 layer):
- README.md                  → 项目入口
- STATUS.md                  → 5-分钟开发入口
- docs/INDEX.md              → 文件索引
- docs/AI_CONTEXT.md         → AI session 压缩上下文
- docs/GOVERNANCE.md         → 本文件
- .claude/CLAUDE.md          → Claude Code 配置
- .github/pull_request_template.md
- docs/session_log.md        → AI session 成本日志
```

## 3.1 每一层允许写什么

### Layer 1: Vision (docs/vision/)
- ✅ 产品定位、用户画像、市场分析
- ✅ 大方向决策（公开 vs 闭源、地区策略、定价模型）
- ❌ 技术实现细节
- ❌ 状态机、API、schema

### Layer 2: Runtime Spec (runtime_specs/)
- ✅ Subsystem 接口、状态机、不变量 (INV-X-N)
- ✅ 数据模型 (table 结构、schema)
- ✅ 跨 subsystem 协议
- ❌ 具体 Python 代码
- ❌ 项目管理（谁负责、deadline）
- ❌ AI prompt 模板

### Layer 3: Engineering (engineering_execution/)
- ✅ Phase plan、task 分解、model routing
- ✅ AI 工作流、cost optimization、review 流程
- ✅ Engineering Laws、failure modes、防御机制
- ❌ Runtime 语义（属于 Layer 2）
- ❌ 单模块实施细节（属于 Layer 4）

### Layer 4: Implementation (docs/design/, docs/prompts/, backend/**/README.md)
- ✅ 单 component 的设计决策（why this algorithm, what alternatives considered）
- ✅ Agent prompt 模板的完整文本
- ✅ 单 module 的 README（API + 使用示例）
- ❌ 跨 component 系统级决策（属于 Layer 2）
- ❌ "完成总结" / "我做了 X"（属于 Layer 5 archive）

### Layer 5: Archive (docs/archive/)
- ✅ Phase completion report
- ✅ Postmortem / incident report
- ✅ Old version of decisions (历史快照)
- ❌ 任何"还在用"的文档

---

# 4. Cleanup Plan (可直接执行)

> 下面每条都是**可执行命令** + **原因** + **风险**。已勾选的 ✅ 表示本 PR 已执行。

## 4.1 Phase A: 移动到归档 (无破坏性, 立刻执行)

| # | 命令 | 原因 | 风险 |
|---|------|------|------|
| A1 | `git mv CHANGES_SUMMARY.md docs/archive/2026-05-15_llm_simplification.md` | 一次性报告 | 无 |
| A2 | `git mv CI_FIX_REPORT.md docs/archive/2026-05-20_ci_fix.md` | 一次性报告 | 无 |
| A3 | `git mv PHASE_0_COMPLETION_REPORT.md docs/archive/2026-05-16_phase_0_completion.md` | 一次性报告 | 无 |
| A4 | `git mv 「心屿」产品需求文档\ v1.0（海外版）.md docs/vision/PRD_v1.0_overseas.md` | PRD 该在 vision 层 | 无 |
| A5 | `git mv QUICKSTART_LLM.md docs/quickstart_llm.md` | 不是项目入口 | 无 |
| A6 | `git mv backend/heart/ss01_soul/DRIFT_DETECTOR_DESIGN.md docs/design/drift_detector.md` | 设计文档应在 docs/design/ | 无 |
| A7 | `git mv backend/heart/ss01_soul/IMPLEMENTATION_SUMMARY.md docs/archive/impl_summaries/ss01_soul.md` | postmortem 归档 | 无 |
| A8 | `git mv docs/design/consolidator_implementation_summary.md docs/archive/impl_summaries/consolidator.md` | 同上 | 无 |
| A9 | `git mv docs/design/forgetting_affect_implementation_summary.md docs/archive/impl_summaries/forgetting_affect.md` | 同上 | 无 |
| A10 | `git mv docs/design/reconstructor_implementation_summary.md docs/archive/impl_summaries/reconstructor.md` | 同上 | 无 |
| A11 | `git mv backend/migrations/CONFIG_SUMMARY.md docs/archive/2026-05-16_alembic_config.md` | 状态快照 | 无 |

## 4.2 Phase B: 合并 (中风险, 先读再合并)

| # | 命令 | 原因 | 风险 |
|---|------|------|------|
| B1 | 合并 `backend/migrations/{SETUP_GUIDE.md, MIGRATION_EXAMPLES.md}` → `backend/migrations/README.md`；然后 `git rm` 两个原文件 | 4 → 1 | 低（先读全文） |
| B2 | 合并 `backend/ALEMBIC_QUICKSTART.md` → `backend/migrations/README.md` "Quick Start" 章节；删 | 同上 | 低 |
| B3 | 合并 `backend/heart/ss03_emotion/CONTAGION_MOODDRIFT_README.md` → `backend/heart/ss03_emotion/README.md`；删 | 同 module 内只该有 1 个 README | 低 |
| B4 | 合并 `QUICKSTART_LLM.md` (已 mv 到 docs/) + `backend/docs/LLM_GUIDE.md` → `docs/llm_guide.md`；删另一个 | 同一主题 2 份 | 低 |
| B5 | 重命名 `backend/heart/infra/README_COST_TRACKER.md` → `backend/heart/infra/cost_tracker.README.md`（与 .py 配对） | 命名规范 | 无 |

## 4.3 Phase C: Rename (无风险)

| # | 命令 | 原因 |
|---|------|------|
| C1 | `git mv docs/design/decay_engine_implementation.md docs/design/decay_engine.md` | 去掉 "_implementation" 后缀 |
| C2 | `git mv docs/design/reconstructor_design.md docs/design/reconstructor.md` | 去掉 "_design" 后缀 |
| C3 | `git mv docs/design/retriever_implementation.md docs/design/retriever.md` | 同上 |

## 4.4 Phase D: 标记 Frozen (无破坏性)

| # | 动作 | 文件 |
|---|------|------|
| D1 | 在文件顶部加 frontmatter `> **Status**: FROZEN @ 2026-05-23. 新内容请进 PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md 或 ENGINEERING_LAWS.md。` | `engineering_execution/EXECUTION_PLAN.md` |
| D2 | 决定 `AGENTS.md` 与 `.claude/CLAUDE.md` 关系。**推荐**：保留 AGENTS.md 作为"任何 AI agent"通用入口 + `.claude/CLAUDE.md` 只放 Claude Code 特有指令 | (HUMAN 决定) |

## 4.5 完成状态 (本次 PR)

- [x] 创建 `docs/archive/`、`docs/vision/`、`docs/runbooks/` 目录
- [x] 创建 `docs/GOVERNANCE.md` (本文件)
- [x] 创建 `STATUS.md` (5-分钟开发入口)
- [x] 创建 `docs/INDEX.md` (文件索引)
- [x] 创建 `docs/AI_CONTEXT.md` (AI 压缩上下文)
- [x] 创建 `.github/pull_request_template.md`
- [x] 创建 `docs/session_log.md`
- [x] Phase A (A1-A11): 移动归档
- [x] Phase C (C1-C3): rename
- [x] Phase D1: freeze EXECUTION_PLAN
- [ ] Phase B (合并): **延迟到下一个 PR**，因为合并需要逐文件读取再合并，单 PR 过大
- [ ] Phase D2: AGENTS.md 去留 → **由 HUMAN 决定**

---

# 5. 文件命名规范

强制约定：

| 类型 | 命名 | 示例 |
|------|------|------|
| Runtime Spec | `NN_<subsystem_name>.md` (两位数字 + 蛇形) | `01_identity_anchor_soul_spec.md` |
| Engineering Process | `SCREAMING_SNAKE.md` | `ENGINEERING_LAWS.md` |
| Module README | `README.md` (每个 module 至多 1 个) | `backend/heart/ss01_soul/README.md` |
| Design Doc | `<component>.md` (无后缀) | `docs/design/conflict_resolver.md` |
| Prompt | `<agent>.md` | `docs/prompts/critic_agent.md` |
| Archive | `YYYY-MM-DD_<topic>.md` | `docs/archive/2026-05-20_ci_fix.md` |
| Runbook | `NN_<incident_type>.md` | `docs/runbooks/05_purple_escalation.md` |
| Status Snapshot | 在 `docs/archive/` 中 | (永远不要回到根目录) |

**禁止**：
- ❌ `IMPLEMENTATION_SUMMARY.md` (说明书在 spec + code 里)
- ❌ `*_COMPLETION_REPORT.md` (一次性，归档 only)
- ❌ `CHANGES_SUMMARY.md` (用 git log / CHANGELOG)
- ❌ `QUICKSTART_*.md` 在根目录 (放 docs/)
- ❌ 同目录两个 README

---

# 6. AI Context Compression Strategy (与 docs/AI_CONTEXT.md 配套)

## 6.1 问题

每个 AI session 启动时，如果让它"了解项目"，最坏情况是它读 53 个 .md 文件 = **~150K tokens**。这会：
- 让 session 在加载阶段就消耗主力 context 的 60%
- 让 AI 产生"信息检索式"而非"任务驱动式"的工作模式
- 让真正的工作 token 预算被挤占

## 6.2 解决方案：分层加载

```
Tier 0 (强制加载, ~3K tokens)
  └── docs/AI_CONTEXT.md       ← 精简的 "你需要知道的最少信息"
                                  包含: 当前 phase, blocker, SSOT 指针, 12 条法则要点

Tier 1 (任务相关加载, ~5K tokens)
  └── STATUS.md                 ← 当前在做什么
  └── docs/INDEX.md             ← "我要找 X 应该看哪个文件"

Tier 2 (按需 Read with offset, 每文件 < 10K tokens)
  └── 任务命中的 1-2 个 SSOT 文件 (e.g. runtime_specs/04_*.md §3)
  └── 任务命中的 design doc (e.g. docs/design/stage_engine.md)

Tier 3 (从不全文加载)
  └── EXECUTION_PLAN.md (96K) — 永远只读特定 section
  └── PRACTICAL_MODEL_GUIDE*.md (~80K each) — 只读当前 phase 章节
  └── 任何 backend/ Python 文件 — 用 Read offset
```

## 6.3 强制规则

```
任何 AI session 启动时:
  □ 必读: docs/AI_CONTEXT.md (全文，~3K tokens)
  □ 必读: STATUS.md (全文，~2K tokens)
  □ 必读: 任务相关的 spec section (用 Read offset)
  
任何 AI session 中:
  □ 禁止 Read 任何 > 500 行的文件全文 — 必须用 offset + limit
  □ 禁止 cat 任何 .md (用 Read)
  □ 禁止 "我需要全面理解项目" 式的盲目读取
  □ 当 context 超过 50K 时 → /clear + 重启 session
```

## 6.4 维护

- `docs/AI_CONTEXT.md` 每 Phase 收尾时由 AI 起草更新 → HUMAN review
- `STATUS.md` 每个完成的任务/PR 后必须 update（CI hook 强制检查 STATUS.md `last_updated` 字段是否在 7 天内）
- `docs/INDEX.md` 每月 review 一次

---

# 7. 治理违规检测 (Governance Linting)

**目标**: CI 必须能检出治理违规。

```
.github/workflows/governance.yml 应该检查:

1. 根目录 .md 文件数 ≤ 4 (README, STATUS, AGENTS, optional CHANGELOG)
2. 没有任何 IMPLEMENTATION_SUMMARY.md
3. 没有任何 *_COMPLETION_REPORT.md
4. 没有任何 CHANGES_SUMMARY.md
5. docs/design/ 没有 *_implementation_summary.md
6. docs/archive/ 没有任何文件被 git diff 修改 (write-once 约束)
7. docs/GOVERNANCE.md, docs/AI_CONTEXT.md, STATUS.md 都存在
8. 任何新 .md > 500 行 → warn
9. SSOT 表中的文件如果删除 → fail
```

**Phase 7 任务**：建立 `governance.yml` workflow (CC-S46, 1 小时)

---

# 8. 给后续 AI Session 的一段话

如果你是 AI 助手，第一次接触本仓库：

```
1. 读 docs/AI_CONTEXT.md  (强制，~3K tokens)
2. 读 STATUS.md           (强制，~2K tokens)
3. 不要读其他文档 unless 任务需要
4. 任务需要某个 spec 时:
   - 看 docs/INDEX.md 找到正确文件
   - 用 Read with offset/limit 读相关 section
   - 不要全文读
5. 任何 SSOT 修改:
   - 必须 PR
   - 必须 HUMAN approve
   - 不可绕过
6. 任何根目录新增 .md:
   - 99% 是错的
   - 自查: 这真的不能放在 layer 1-5 的某一层？
```

---

# 9. 修订历史

| Version | Date | By | Change |
|---------|------|-----|--------|
| 1.0.0 | 2026-05-23 | Claude Opus 4.7 + HUMAN | 初始建立。完成 Phase A、C、D1 清理。Phase B 合并、Phase D2 决策延迟。 |

---

**End of Governance**

**仓库的健康度从今天起以这份文件为依据。**
