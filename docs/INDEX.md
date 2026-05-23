# 文件索引 — "我要找 X 应该看哪个文件"

> **目标**: 30 秒内定位到任何信息所在的文件
> **维护**: 每月 review；任何新增 SSOT-tier 文件必须更新

---

# 速查表（按问题）

| 问题 | 文件 |
|------|------|
| 项目是什么？ | [README.md](../README.md) |
| 现在做什么？ | [STATUS.md](../STATUS.md) |
| AI 必读最小集？ | [docs/AI_CONTEXT.md](AI_CONTEXT.md) |
| 仓库怎么治理？ | [docs/GOVERNANCE.md](GOVERNANCE.md) |
| 第 N phase 怎么干？ | engineering_execution/PRACTICAL_MODEL_GUIDE*.md |
| 用什么模型？ | engineering_execution/AI_MODEL_ROUTING.md |
| 这事 HUMAN 要 review 吗？ | engineering_execution/HUMAN_REVIEW_CHECKLIST.md |
| 我能修改它吗？ | engineering_execution/HUMAN_REVIEW_CHECKLIST.md + docs/GOVERNANCE.md §2 |
| 12 条法则？ | engineering_execution/ENGINEERING_LAWS.md |
| SS0X spec？ | runtime_specs/0X_*.md |
| SS0X 代码？ | backend/heart/ss0X_*/ |
| SS0X 模块说明？ | backend/heart/ss0X_*/README.md |
| 某 component 设计？ | docs/design/<component>.md |
| 某 agent 的 prompt？ | docs/prompts/<agent>.md |
| Rin / Dorothy 定义？ | soul_specs/<char>/v*.yaml |
| 历史快照？ | docs/archive/ |
| PRD？ | docs/vision/PRD_v1.0_overseas.md |
| LLM 怎么用？ | docs/llm_guide.md (Phase B 合并后) |
| 数据库迁移？ | backend/migrations/README.md |
| API endpoint？ | docs/api/openapi.yaml (Phase 9.2 后生成) |
| 故障 runbook？ | docs/runbooks/ (待补，Phase 11.5) |

---

# 完整文件清单（按层）

## Layer 0: 横切 (Cross-cutting)

```
README.md                    项目入口
STATUS.md                    当前状态 + 下一步 (新 session 必读)
.claude/CLAUDE.md            Claude Code 项目级配置
AGENTS.md                    AI agent 通用指令（与 .claude/CLAUDE.md 关系待确定）
.github/pull_request_template.md   PR 模板
docs/INDEX.md                本文件
docs/AI_CONTEXT.md           AI session 强制阅读
docs/GOVERNANCE.md           仓库治理宪法
docs/session_log.md          AI session 成本与质量日志
```

## Layer 1: Vision

```
docs/vision/PRD_v1.0_overseas.md    海外版产品需求文档 v1.0
```

## Layer 2: Runtime Spec (Single Source of Truth)

```
runtime_specs/README.md                              spec 导航
runtime_specs/00_runtime_worldview.md                整体世界观
runtime_specs/01_identity_anchor_soul_spec.md        SS01 Soul Spec
runtime_specs/02_memory_runtime.md                   SS02 Memory
runtime_specs/03_emotion_state_machine.md            SS03 Emotion
runtime_specs/04_relationship_phase_engine.md        SS04 Relationship
runtime_specs/05_persona_composition_runtime.md      SS05 Composer
runtime_specs/06_inner_state_behavior_runtime.md     SS06 Inner State
runtime_specs/07_agent_orchestration.md              SS07 Orchestration + Safety
runtime_specs/08_engineering_architecture.md         SS08 Infrastructure
```

## Layer 3: Engineering Process

```
engineering_execution/README.md                            dir 入口
engineering_execution/EXECUTION_PLAN.md                    战略 (FROZEN @ 2026-05-23)
engineering_execution/PRACTICAL_MODEL_GUIDE.md             Phase 0-6 操作 (active)
engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md Phase 7+ 操作 (active)
engineering_execution/AI_MODEL_ROUTING.md                  模型路由 (SSOT)
engineering_execution/HUMAN_REVIEW_CHECKLIST.md            review 边界 (SSOT)
engineering_execution/ENGINEERING_LAWS.md                  12 条法则 (SSOT)
engineering_execution/SPEC_DRIVEN_WORKFLOW.md              工作流
engineering_execution/CLAUDE_CODE_AGENTS.md                subagent 配置
```

## Layer 4: Implementation

### 4.1 Design Docs

```
docs/design/conflict_resolver.md            SS05 Conflict Resolver 设计
docs/design/decay_engine.md                 SS02 Decay Engine 设计 (Phase C: rename)
docs/design/drift_detector.md               SS01 Drift Detector 设计 (Phase A: 从 ss01_soul/ 移过来)
docs/design/initiative_decider.md           SS06 Initiative Decider 设计
docs/design/purple_care_path.md             Safety PURPLE Care Path 设计
docs/design/reconstructor.md                SS02 Reconstructor 设计 (Phase C: rename)
docs/design/repair_mechanic.md              SS03 Repair Mechanic 设计
docs/design/retriever.md                    SS02 Retriever 设计 (Phase C: rename)
docs/design/streaming_anti_pattern.md       SS05 Streaming Anti-Pattern 设计
docs/design/wellbeing_monitor.md            Safety Wellbeing Monitor 设计
```

### 4.2 Prompts

```
docs/prompts/critic_agent.md                Critic Agent prompt 文本
(Phase 7 待补: orchestrator, safety_llm, reconstructor, wellbeing_monitor, director, care_path)
```

### 4.3 Module READMEs

```
backend/README.md                                       backend 入口
backend/heart/ss01_soul/README.md                        SS01 模块说明
backend/heart/ss03_emotion/README.md                     SS03 模块说明
backend/heart/infra/llm/README.md                        LLM Router 模块说明 (V1 single-provider)
backend/heart/infra/cost_tracker.README.md               Cost Tracker 模块说明 (Phase B: rename)
backend/migrations/README.md                             Alembic 迁移说明 (Phase B: 合并 SETUP + EXAMPLES + ALEMBIC_QUICKSTART)
```

### 4.4 LLM / Quick Start

```
docs/llm_guide.md                            LLM 使用指南 (Phase B: 合并自 QUICKSTART_LLM + backend/docs/LLM_GUIDE)
```

## Layer 5: Archive

```
docs/archive/2026-05-15_llm_simplification.md        LLM 配置简化 (原 CHANGES_SUMMARY.md)
docs/archive/2026-05-16_phase_0_completion.md        Phase 0 完成报告 (原 PHASE_0_COMPLETION_REPORT.md)
docs/archive/2026-05-16_alembic_config.md            Alembic 配置历史快照 (原 backend/migrations/CONFIG_SUMMARY.md)
docs/archive/2026-05-20_ci_fix.md                    CI/CD 修复报告 (原 CI_FIX_REPORT.md)
docs/archive/impl_summaries/ss01_soul.md             SS01 实施总结 (原 backend/heart/ss01_soul/IMPLEMENTATION_SUMMARY.md)
docs/archive/impl_summaries/consolidator.md          Consolidator 实施总结
docs/archive/impl_summaries/forgetting_affect.md     Forgetting Affect 实施总结
docs/archive/impl_summaries/reconstructor.md         Reconstructor 实施总结
```

## 数据目录（非 .md）

```
soul_specs/rin/v1.0.0.yaml                Rin Soul Spec v1.0
soul_specs/dorothy/v1.0.0.yaml            Dorothy Soul Spec v1.0
config/activity_pools/                    Activity pool YAMLs
config/care_path_responses/               PURPLE response templates
config/emotion_lexicon.yaml               Emotion trigger lexicon
config/emotion_phrases/                   Emotion phrase library
config/encoder_lexicon.yaml               Memory encoder lexicon
config/fallbacks/                         Fallback responses
config/safety_keywords.yaml               Safety classification keywords
infra/kubernetes/*.yaml                   K8s deployment manifests
backend/migrations/versions/              Alembic migration files
backend/heart/                            实际 Python code (106 files)
backend/tests/                            Test code (59 files, 1694 collected)
```

---

# 文件命名规范（强制）

```
✅ runtime_specs/NN_<subsystem>.md           (canonical spec)
✅ engineering_execution/SCREAMING.md         (process docs)
✅ docs/design/<component>.md                 (design docs)
✅ docs/prompts/<agent>.md                    (prompt text)
✅ docs/archive/YYYY-MM-DD_<topic>.md         (archive)
✅ docs/runbooks/NN_<incident>.md             (runbooks)
✅ backend/.../<module>/README.md             (module readme; 1 per module)

❌ 任何 *_IMPLEMENTATION_SUMMARY.md  (代码即真相)
❌ 任何 *_COMPLETION_REPORT.md       (一次性 → archive)
❌ 任何 *_CHANGES_SUMMARY.md         (用 git log / CHANGELOG)
❌ 根目录除 README/STATUS/AGENTS 外的 .md
❌ 一个目录两个 README
```

---

# 维护规则

```
谁可以改本文件:
  - AI 可起草 (尤其是新文件加入时)
  - HUMAN 必须 review (因为是导航文件)
  
何时必须改:
  - 新增 SSOT-tier 文件 → 同 PR 更新
  - 文件 rename / move → 同 PR 更新
  - Phase 收尾时 → review 一遍
  
何时禁止改:
  - 不要在 PR 中只改本文件不动其他 — 索引必须跟实际文件 git 状态同步
```

---

**Last updated**: 2026-05-23
