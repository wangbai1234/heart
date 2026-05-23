# 心屿 — 项目当前状态（5 分钟读完）

> **Last updated**: 2026-05-23
> **Updated by**: Claude Opus 4.7
> **Next update due**: 完成下一个 Phase 7 任务时
> **强制规则**: 任何 PR 合并必须同时更新本文件的 "当前状态" + "下一步" + "Last updated"

---

## 1. 你现在在哪里？(30 秒)

```
Phase 完成度:
  ████████████████████░░░░░░░░░░░░░░░░░░░░  35%

  ✅ Phase 0  Foundation             (Week 1-3)    100%  closed
  ✅ Phase 1  Soul + Anchor          (Week 4-7)    100%  closed
  ✅ Phase 2  Memory Runtime         (Week 8-12)   100%  closed
  ✅ Phase 3  Emotion + Relationship (Week 13-17)  100%  closed
  ✅ Phase 4  Composer               (Week 18-21)  100%  closed
  ✅ Phase 5  Inner State + Behavior (Week 22-25)  100%  closed
  ✅ Phase 6  Orchestration + Safety (Week 26-30)  100%  closed
  ▶  Phase 7  Integration Hardening  (Week 31-34)  0%    in progress ← 你在这里
  ⏸  Phase 8  Local MVP              (Week 35-38)
  ⏸  Phase 9  Frontend MVP           (Week 39-44)
  ⏸  Phase 10 Closed Alpha           (Week 45-48)
  ⏸  Phase 11 Beta                   (Week 49-54)
  ⏸  Phase 12 Production Hardening   (Week 55-58)
  ⏸  Phase 13 Production GA          (Week 59+)
```

**核心一句话**：**Spec-complete, integration-pending。** 100+ Python 文件已写，1677 unit tests 通过，但**没有一次真实 LLM e2e turn 跑通过**，**没有 frontend**。

---

## 2. 现在最该做什么？(60 秒)

### 立刻执行清单 (Phase 7 前置, 本周必做)

| # | 任务 | 工具 | 时长 | 状态 |
|---|------|------|------|------|
| 1 | 修复 GitHub Actions 账单 | HUMAN | 30 min | ⚠️ HUMAN action required |
| 2 | 创建 docs/INDEX.md | CC-Haiku | 30 min | ✅ DONE (本次 PR) |
| 3 | 创建 .github/pull_request_template.md | CC-S46 | 15 min | ✅ DONE (本次 PR) |
| 4 | 初始化 docs/session_log.md | HUMAN+AI | 5 min | ✅ DONE (本次 PR) |
| 5 | 跑一次架构 audit dry-run | CC-Opus | 1 day | ⏸ 待启动 (`PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.7) |
| 6 | 修复 2 个失败单测 | CC-S46 | 1 hour | ⏸ 待启动 (`PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.1) |

### 下一个 task（推荐）

**「修复 2 个失败单测 + 审计 deselected」**
- File: `backend/tests/unit/test_mood_drift.py`、`backend/tests/unit/test_trust_attachment.py`
- Why: Phase 7 不允许带病开始
- How: 见 `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.1
- Model: CC-S46
- Time: 1 hour
- HUMAN review needed: 否（除非要改 spec）

---

## 3. 当前最大 Blocker (60 秒)

| # | Blocker | Severity | Owner | ETA |
|---|---------|----------|-------|-----|
| B1 | 没有一次真实 DeepSeek e2e turn 验证过 | 🔴 P0 | AI (CC-S46) | Phase 7.2 |
| B2 | 没有 frontend (无法 demo / alpha) | 🔴 P0 | AI + HUMAN | Phase 9 |
| B3 | GitHub Actions 账单未恢复 | 🟠 P1 | HUMAN | 本周 |
| B4 | 仅 1 个 integration test (vs 1677 unit) | 🟠 P1 | AI (CC-S46) | Phase 7.2 |
| B5 | 2 个 unit tests 失败 + 15 deselected 未审计 | 🟡 P2 | AI (CC-S46) | 本周 |

---

## 4. 当前关键路径 (Critical Path)

```
本周 → 修单测 + INDEX/STATUS/AI_CONTEXT 建立 + CI 账单
   ↓
Week 31-32 → Integration test pyramid (Tier A/B) + Contract tests
   ↓
Week 33   → Architecture audit (Opus) + Invariant framework
   ↓
Week 34   → Voice drift baseline (花真钱跑 DeepSeek)
   ↓ Phase 7 cut criteria 全绿
Week 35-38 → Local MVP (CLI demo + docker-compose 完整栈 + Grafana)
   ↓ MVP demo 可录屏
Week 39-44 → Frontend MVP (Expo RN — pending HUMAN decision)
   ↓ 真机可用
Week 45-48 → Closed Alpha (10-20 用户, 4 周)
   ↓ Cohort retention ≥ D7 40%
Week 49-54 → Beta (250+ 用户, multi-region)
   ↓
Week 55-58 → Production Hardening
   ↓
Week 59+   → Public Launch
```

---

## 5. 禁止 AI 自由发挥的边界

> **以下区域 AI 必须 HUMAN approval 才能修改。** 详见 `engineering_execution/HUMAN_REVIEW_CHECKLIST.md`.

| 区域 | AI 可做 | AI 不可做 |
|------|---------|----------|
| `runtime_specs/` | 读 + 提 RFC | 直接修改 spec |
| `soul_specs/<char>/*.yaml` | 读 | 任何 voice_dna / hard_never 修改 |
| `config/safety_keywords.yaml` | 读 | 修改 PURPLE / HIGH 关键词 |
| `config/care_path_responses/` | 读 | 任何文本修改（必须心理顾问 review） |
| Soul Spec versioning logic | 读 | 修改 rollout / rollback 策略 |
| PURPLE Care Path runtime | 读 | 修改触发逻辑 |
| Wellbeing 阈值 | 读 | 修改 thresholds.yaml |
| Production K8s YAMLs | 读 | 修改 limits / replicas in prod |

**禁止 AI 自由发挥的具体动作**：
- ❌ 创建任何根目录新 `.md`（必须遵守 `docs/GOVERNANCE.md` Layer 规则）
- ❌ 创建任何 `*_IMPLEMENTATION_SUMMARY.md` / `*_COMPLETION_REPORT.md` / `CHANGES_SUMMARY.md`
- ❌ 修改 `.claude/CLAUDE.md` 不经 HUMAN review
- ❌ 修改 `docs/GOVERNANCE.md`（本治理文件）
- ❌ 任何 `git push --force` / `rm -rf` 类操作
- ❌ 任何 LLM provider 直连（必须走 ModelRouter, 见 `engineering_execution/ENGINEERING_LAWS.md` Law 6）

---

## 6. 项目核心指标 (Snapshot)

```
代码:
  Python source files:    106
  Test files:             59 (~ 1694 collected tests)
  Test pass rate:         1677 / 1694  (99.0%, 2 failing)
  Integration tests:      1
  Subsystems implemented: SS01-SS07 + safety ✅

数据:
  Soul specs:             2 (Rin, Dorothy)
  Alembic migrations:     4 (forward only — no roundtrip verified)
  K8s deployments:        7 YAMLs (not deployed)

文档:
  Runtime specs:          9 + README (canonical SSOT)
  Engineering process:    8 documents
  Design docs:            12 (清理后会下降到 9)
  Module READMEs:         5 (清理后会下降到 3)
  Archive:                4+ (新增)
  根目录 .md:             8 → 3 (清理后)

真实 LLM 验证:
  E2E turns run:          0  ← 这是项目最大的诚实点
  Voice drift baseline:   未生成
  PURPLE drill:           未执行
```

---

## 7. 哪里找什么（导航）

> 完整文件索引见 [`docs/INDEX.md`](docs/INDEX.md)

| 问题 | 文件 |
|------|------|
| 项目到底是什么？ | `README.md` |
| 现在该做什么？ | **本文件** (`STATUS.md`) |
| 文件结构与索引 | `docs/INDEX.md` |
| 仓库治理规则 | `docs/GOVERNANCE.md` |
| AI 应该如何工作？ | `docs/AI_CONTEXT.md` |
| 系统级 spec | `runtime_specs/*` |
| 当前 Phase 7+ 操作 | `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` |
| 模型路由 | `engineering_execution/AI_MODEL_ROUTING.md` |
| 12 条工程法则 | `engineering_execution/ENGINEERING_LAWS.md` |
| 人工 review 边界 | `engineering_execution/HUMAN_REVIEW_CHECKLIST.md` |
| 单个 component 设计 | `docs/design/<component>.md` |
| Soul 实例 | `soul_specs/<character>/` |
| 历史 / 一次性报告 | `docs/archive/` |
| PRD | `docs/vision/PRD_v1.0_overseas.md` |

---

## 8. 健康检查清单（你打开仓库时该做的）

```
本地环境:
  □ docker-compose up 起来？        (Phase 8 之前: 不必要 / Phase 8 后: 必须)
  □ pytest tests/unit -q 通过？      (应 1677+ passed, ≤ 2 failed)
  □ make lint 通过？

了解状态:
  □ 读过 docs/AI_CONTEXT.md？        (新 session 强制)
  □ 读过 STATUS.md (本文件)？        (新 session 强制)
  □ 知道下一个 task 是什么？         (见上方 §2)
```

---

## 9. 紧急情况指引

| 状况 | 该看 |
|------|------|
| 生产/staging 故障 | `engineering_execution/PRACTICAL_MODEL_GUIDE.md` §9.1 + `docs/runbooks/` |
| LLM Provider 宕机 | `engineering_execution/PRACTICAL_MODEL_GUIDE.md` §9.2 |
| 用户反映"她变了" | `engineering_execution/PRACTICAL_MODEL_GUIDE.md` §9.3 + voice drift suite |
| PURPLE 误报 | `docs/runbooks/05_purple_escalation.md` (待创建, Phase 11.5) |

---

## 10. 给你自己的话

如果你在读这份文件，你大概率是**几周后回到项目的开发者本人**或**一个新 AI session**。

记住：

> 项目当前**不缺代码**。
> 缺的是**让代码真正运行起来 + 让 AI 写出的东西可治理**。
>
> 下一步不是"再加 feature"。
> 是 **Phase 7: 把已经有的东西真正连起来**。

---

**当本文件 last_updated 超过 14 天还没改 → 项目处于失活状态 → 立刻 update。**
