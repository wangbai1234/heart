# docs/ — 文档导航

> AI 入口在 [**PROJECT_STATUS.md**](PROJECT_STATUS.md)。先读它，再来这里。

本目录只放 **当前活跃** 的文档。历史/废弃文档已移到 [`../archive/`](../archive/)。

---

## 1. 必读

| 文件 | 用途 |
|------|------|
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | 当前 phase、blocker、下一步——任何新 session 必读 |
| [`PHASE_7_READINESS_CHECKLIST.md`](PHASE_7_READINESS_CHECKLIST.md) | Phase 7 启动详细 checklist（含分支合并策略） |
| [`audit/2026-05-23_architecture_audit.md`](audit/2026-05-23_architecture_audit.md) | 41 findings 全表 |

## 2. 设计文档（`docs/design/`）

落地某个组件前查相应文件：

| 文件 | 主题 |
|------|------|
| `consolidator_implementation_summary.md` | Memory consolidator |
| `decay_engine_implementation.md` | Memory decay |
| `forgetting_affect_implementation_summary.md` | 遗忘 × 情感 |
| `integration_test_pyramid.md` | Phase 7 集成测试金字塔 |
| `reconstructor_design.md` | Memory reconstructor 设计 |
| `reconstructor_implementation_summary.md` | Reconstructor 实现总结 |
| `repair_mechanic.md` | Relationship 修复机制 |
| `retriever_implementation.md` | Memory retriever |
| `soul_drift_regression.md` | Soul drift 回归套件 |

## 3. Runbooks（`docs/runbooks/`）

待补，Phase 11.5。

## 4. Vision / PRD（`docs/vision/`）

| 文件 | 用途 |
|------|------|
| `PRD_v1.0_overseas.md` | 海外版产品需求文档 v1.0 |

## 5. 其它顶层目录

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
