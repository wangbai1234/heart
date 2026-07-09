# docs/ — 文档导航

> AI 入口在 [**PROJECT_STATUS.md**](PROJECT_STATUS.md)。先读它，再来这里。

本目录只放 **当前活跃** 的文档。历史/废弃文档已移到 [`../archive/`](../archive/)。

---

## 1. 必读

| 文件 | 用途 |
|------|------|
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | 当前 phase、blocker、下一步——任何新 session 必读 |
| [`../HEART_PROJECT_VERIFICATION_MASTER_PLAN.md`](../HEART_PROJECT_VERIFICATION_MASTER_PLAN.md) | 验证计划（7 Phase 只读验证） |
| [`audit/2026-05-23_architecture_audit.md`](audit/2026-05-23_architecture_audit.md) | 41 findings 全表 |

## 2. 设计文档（`docs/design/`）

落地某个组件前查相应文件：

| 文件 | 主题 |
|------|------|
| `composer_wiring_plan.md` | Composer 接线方案 |
| `consolidator_implementation_summary.md` | Memory consolidator |
| `data_integrity_decisions_2026-06-22.md` | 数据完整性决策 |
| `decay_engine_implementation.md` | Memory decay |
| `forgetting_affect_implementation_summary.md` | 遗忘 × 情感 |
| `integration_test_pyramid.md` | Phase 7 集成测试金字塔 |
| `memory_extractor_prompt.md` | Memory extractor prompt |
| `memory_extractor_schema.md` | Memory extractor schema |
| `memory_golden_set_design.md` | Memory golden set 设计 |
| `memory_promoter_rules.md` | Memory promoter 规则 |
| `orchestrator_min_viable.md` | Orchestrator 最小可行方案 |
| `proactive_frontend_plan.md` | 主动消息前端方案 |
| `reconstructor_design.md` | Memory reconstructor 设计 |
| `reconstructor_implementation_summary.md` | Reconstructor 实现总结 |
| `repair_mechanic.md` | Relationship 修复机制 |
| `retriever_implementation.md` | Memory retriever |
| `safety_overhaul.md` | Safety 大修 |
| `soul_drift_regression.md` | Soul drift 回归套件 |
| `ss04_special_states_implementation_choice.md` | SS04 特殊状态实现选择 |
| `state_invariants.md` | 状态不变量 |
| `ugc_character_refactor_plan.md` | UGC 角色重构方案 |

## 3. 执行文档（`docs/execution/`）

| 文件 | 主题 |
|------|------|
| `BACKEND_HARDENING_PLAN_2026-06-22.md` | 后端加固方案 |
| `MEMORY_EXTRACTOR_V1_0_3_FINAL.md` | Memory extractor v1.0.3 最终迭代 |
| `MEMORY_LLM_EXTRACTOR_REFACTOR.md` | SS02 Memory LLM Extractor 重构执行手册 |

## 4. Runbooks（`docs/runbooks/`）

待补，Phase 11.5。

## 5. Vision / PRD（`docs/vision/`）

| 文件 | 用途 |
|------|------|
| `PRD_v1.0_overseas.md` | 海外版产品需求文档 v1.0 |

## 6. 其它顶层目录

| 路径 | 说明 |
|------|------|
| [`../runtime_specs/`](../runtime_specs/) | SS01–SS08 Runtime Bible（动子系统前必读对应一份） |
| [`../engineering_execution/`](../engineering_execution/) | 工程方法、AI 模型路由、Phase 7+ 操作手册 |
| [`../backend/`](../backend/) | Python 服务代码 |
| [`../soul_specs/`](../soul_specs/) | 角色 Soul Spec YAML（Rin, Dorothy …） |
| [`../config/`](../config/) | 应用配置 YAML |
| [`../scripts/`](../scripts/) | `ci.sh` 等开发脚本 |
| [`../archive/`](../archive/) | 历史 / 废弃文档（仅参考） |

---

**维护规则**：
- 新文档进 `docs/design/` 或 `docs/runbooks/`，不要再加根级文件。
- 废弃文档移到 `archive/`，**不要删除**——保留历史决策可追溯。
- 本文件 ≤ 100 行；超了说明结构出问题了。
