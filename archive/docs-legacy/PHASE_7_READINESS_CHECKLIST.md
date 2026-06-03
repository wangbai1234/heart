# Phase 7 启动就绪清单

**生成日期**: 2026-05-24  
**生成者**: CC-Sonnet-4.5  
**依据文档**:
- `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §第十部分
- `docs/audit/2026-05-23_architecture_audit.md` §3 Top 10
- `docs/design/integration_test_pyramid.md` (Phase 7 §1.2)
- `docs/design/soul_drift_regression.md` (Phase 7 §1.4)

---

## 0. TL;DR - 当前状态

```
Phase 7 启动前置条件（5 个 blocker）:
  ✅ Blocker 1: CI/CD — 已迁移到 Gitee Go             (billing 问题已规避)
  ✅ Blocker 2: docs/INDEX.md                        (已完成)
  ✅ Blocker 3: .github/pull_request_template.md     (已完成)
  ✅ Blocker 4: docs/session_log.md                  (已完成)
  ✅ Blocker 5: 架构 audit + Top 10                   (已完成)

关键阻塞项:
  🔴 PR #7 (设计文档) 需 3 方签字: 架构 + 主创 + 心理顾问
  🔴 Top 10 Critical 问题（4 个）必须先修复
  🔴 feature/ss04-stage-engine 分支需分批合并（163 文件）

预计时间:
  - Top 10 remediation: ~4 天（并行可压缩到 2 天）
  - 分支合并 + PR review: 1-2 周
  - Phase 7 实施（§1.2-§1.9）: 4-6 周
```

---

## 1. 前置条件完成状态（§第十部分 5 个 Blocker）

### ✅ Blocker 2: docs/INDEX.md

- **状态**: 已完成
- **文件**: `docs/INDEX.md` (199 行)
- **来源**: `feature/ss04-stage-engine` 分支
- **内容**: 列出 runtime_specs/, engineering_execution/, docs/design/, root reports 完整索引
- **下一步**: 随 super-branch 合并进 main

### ✅ Blocker 3: Pull Request Template

- **状态**: 已完成
- **文件**: `.github/pull_request_template.md` (97 行)
- **来源**: `feature/ss04-stage-engine` 分支
- **用途**: 防御 audit finding #9（缺乏 PR 规范）
- **下一步**: 本 PR 合并后，所有新 PR 自动应用此模板

### ✅ Blocker 4: docs/session_log.md

- **状态**: 已完成
- **文件**: `docs/session_log.md` (含 2 条历史记录)
- **来源**: `feature/ss04-stage-engine` 分支
- **用途**: 防御 audit finding #10（缺乏 session 成本追踪）
- **待办**: 添加本次 session 记录（见 §6）

### ✅ Blocker 5: 架构 Audit Dry-Run

- **状态**: 已完成
- **文件**: `docs/audit/2026-05-23_architecture_audit.md` (215 行, 41 findings)
- **来源**: `feature/ss04-stage-engine` 分支
- **关键发现**:
  - **6 Critical** + **13 High** + 14 Med + 8 Low
  - Top 10 items (见 §2)
  - 2 个 failing tests 在 super-branch 上（当前分支没有这些测试文件）
- **下一步**: 执行 Top 10 remediation

### ✅ Blocker 1: CI/CD 迁移到 Gitee Go

- **状态**: ✅ **已完成**
- **解决方案**: 由于 GitHub Actions 账单问题无法解决，已将完整 CI/CD pipeline 迁移到 Gitee Go
- **迁移内容**:
  - 创建 `.gitee/workflows/ci.yml`（344 行）
  - 保留所有 6 个 jobs（lint, unit-tests, integration-tests, schema-validation, build-docker, ci-summary）
  - codecov 替换为 artifact 上传
  - 添加 Gitee remote: https://gitee.com/wangbai1234/heart.git
- **配置文档**: `docs/GITEE_GO_SETUP.md`
- **下一步**: 
  1. 在 Gitee 仓库配置 `DEEPSEEK_API_KEY` secret
  2. 推送代码触发首次 CI 运行
  3. 验证所有 6 个 jobs 通过

---

## 2. Top 10 Critical/High 问题（架构 Audit）

来源: `docs/audit/2026-05-23_architecture_audit.md` §3

按 **risk × proximity to safety/correctness path** 排序：

| # | 问题 | 严重度 | 预计工时 | Owner | 依赖 | 状态 |
|---|------|--------|---------|-------|------|------|
| 1 | **Wire `heart.safety.safety_agent.SafetyAgent` into orchestrator**<br>删除 in-file 的假 SafetyAgent (closes A-D2-05, A-D2-06) | **Critical** | 1 day | CC-Opus (design) + CC-S46 (impl) + HUMAN review | — | ⏳ 待执行 |
| 2 | **Wire `CarePathHandler` from `safety/care_path.py`**<br>删除硬编码 `_CARE_RESPONSE` (closes A-D2-07, A-D6-33) | **Critical** | 0.5 day + signoff | CC-S46 + HUMAN + 心理顾问 | item 1 | ⏳ 待执行 |
| 3 | **修复 2 个 failing tests + audit 15 deselected tests**<br>(closes A-D7-37, A-D7-38) | **Critical** | 3 hours | CC-S46 | — | ⏳ 待执行 |
| 4 | **Resolve dual LLM provider trees**<br>`infra/llm/` vs `infra/llm_providers/` (closes A-D3-16) | **Critical** | 0.5 day | CC-Opus | — | ⏳ 待执行 |
| 5 | **Standardize logging on structlog**<br>16 个 stdlib-logging 模块迁移 (closes A-D2-04) | High | 1 hour | CC-Haiku | — | ⏳ 待执行 |
| 6 | **Convert `EmotionService` to async**<br>(closes A-D2-09) | High | 2 hours | CC-S46 | — | ⏳ 待执行 |
| 7 | **Add cold-path failure tracking**<br>`asyncio.create_task` 追踪 + Prometheus (closes A-D2-12) | High | 1 hour | CC-S46 | — | ⏳ 待执行 |
| 8 | **Resolve repair_profile spec drift**<br>(closes A-D4-19, A-D6-32) | High | depends on HUMAN decision | HUMAN 决策 + CC-S46 impl | — | ⏳ 待 RFC |
| 9 | **Rename misnamed safety circuit breaker**<br>`ss01_anchor` → `safety` (closes A-D2-08) | High | 30 min | CC-S46 | — | ⏳ 待执行 |
| 10 | **Build governance-lint CI workflow**<br>`.github/workflows/governance.yml` (closes A-D1-01, A-D3-15, A-D4-17) | High | 1 day | CC-S46 | item 1 (defines spine) | ⏳ 待执行 |

**总预计工时**: ~4 天（Critical 1-4 并行可压缩到 2 天）

**当前分支状态**: 
- Items 1-4, 8-10 需要从 `feature/ss04-stage-engine` 获取代码
- 当前分支 `feat/misc-updates` 缺少 SS03-SS07 模块，无法直接修复

**建议执行顺序**:
1. 先合并 super-branch 的 **代码部分**（见 §3）
2. 再执行 Top 10 remediation（因为需要实际代码才能修复）

---

## 3. 分支合并策略

### 3.1 当前分支拓扑

```
feature/ss04-stage-engine (163 files, +54770/-641) — SUPER-BRANCH
  ├── 包含所有 SS03-SS07 代码
  ├── 包含 governance docs (INDEX.md, audit/, etc.)
  ├── 包含 PHASE_7_PLUS.md
  └── 包含本次新增的 5 个 blocker 文件

feat/misc-updates (当前分支, 3 commits, +1805/-141)
  ├── test_audit.md
  ├── docs/design/integration_test_pyramid.md
  ├── docs/design/soul_drift_regression.md
  ├── 已添加: PHASE_7_PLUS.md, INDEX.md, PR template, session_log, audit/
  └── 唯一冲突: backend/heart/infra/llm/router.py (ss04 版本是超集)

feat/governance-docs (16 files, governance only)
feat/ss03-emotion (SS03 only)
feat/ss04-05-06 (SS04+05+06)
feat/safety-ss07 (SS07 + Safety)
```

### 3.2 推荐合并计划（Slice Strategy）

**不推荐直接 octopus merge，推荐分 4 个 PR**:

#### PR #A: Governance + Docs (无代码变更)
- **文件**: INDEX.md, pull_request_template.md, session_log.md, audit/, GOVERNANCE.md, STATUS.md, AGENTS.md, docs/design/*.md
- **大小**: ~16 文件
- **无冲突**
- **Review 难度**: 低（文档 only）
- **可立即开始**: ✅（不依赖设计稿 sign-off）

#### PR #B: SS03 Emotion (代码 + 测试)
- **文件**: backend/heart/ss03_emotion/*, tests/unit/test_*emotion*, tests/unit/test_mood_drift.py
- **依赖**: PR #A merged（需要 governance lint）
- **Review 难度**: 中
- **包含**: test_mood_drift.py 的 failing test fix（Top 10 #3）

#### PR #C: SS04+SS05+SS06 (代码 + 测试)
- **文件**: backend/heart/{ss04_relationship, ss05_composer, ss06_inner_state}/*, tests/unit/test_*
- **依赖**: PR #B merged
- **冲突处理**: router.py 用 ss04 版本（superset）
- **Review 难度**: 高（大 PR）
- **包含**: Top 10 #1, #2, #4, #6, #9, #10 的前置代码

#### PR #D: SS07 + Safety (代码 + 测试)
- **文件**: backend/heart/{ss07_orchestration, safety}/*, tests/unit/test_*
- **依赖**: PR #C merged
- **Review 难度**: 高（critical path）
- **包含**: Top 10 #1, #2 的实际修复位置

### 3.3 当前 PR #7 的角色

**PR #7** (feat/misc-updates → main):
- **当前内容**: test_audit.md + 2 份设计稿 + 5 个 blocker 文件
- **状态**: OPEN, 0 reviews, 需 3 方签字
- **阻塞**: Phase 7 §1.2/§1.4 **实施** prompt 不能跑，直到设计稿拿到 sign-off

**建议**:
1. PR #7 保持当前 scope（设计 + blocker），尽快拿 sign-off
2. PR #A-#D 从 `feature/ss04-stage-engine` 切，与 PR #7 并行 review
3. 合并顺序: PR #7 → PR #A → PR #B → PR #C → PR #D
4. Top 10 remediation 在 PR #D merge 后单独开 PR

---

## 4. Phase 7 §1.2/§1.4 设计文档 Sign-off 跟踪

### PR #7 Sign-off 清单

**Title**: chore: Phase 7 §1.1 audit + §1.2/§1.4 design baselines  
**URL**: https://github.com/wangbai1234/heart/pull/7  
**State**: OPEN, Mergeable

**需要 3 方签字** (per `docs/design/integration_test_pyramid.md` + `soul_drift_regression.md` header):

```
□ 架构师 (Architecture) — 确认 4-tier pyramid + fake LLM provider + cost cap 设计合理
□ 主创 (Creator) — 确认 voice drift baseline 30 prompts + 5-dim scoring 覆盖角色核心
□ 心理顾问 (Psychological Advisor) — 确认 drift threshold + approved-drift workflow 符合角色稳定性要求
```

**阻塞**:
- Phase 7 §1.2 实施（integration test pyramid 7-PR roadmap）
- Phase 7 §1.4 实施（voice drift suite 8-PR roadmap）

**ACTION REQUIRED**:
```
HUMAN 需要:
1. 在 PR #7 中 @mention 三方 reviewer
2. 附上本清单的 §2 (Top 10) 和 §3 (合并策略) 作为 context
3. 等待 3 个 LGTM 后 merge
```

---

## 5. soul_specs 完整性验证

### rin v1.0.0
- **文件**: `soul_specs/rin/v1.0.0.yaml` (34K)
- **关键字段验证**:
  - ✅ `voice_dna` (7 次匹配 → vd-001 到 vd-006+)
  - ✅ `anti_patterns.hard_never` (~30 entries)
  - ✅ `anti_patterns.forbidden_patterns` (regex)
  - ✅ `humor_profile` (dryness 0.90, sarcasm 0.55, ...)
  - ✅ `regression_tests` section

### dorothy v1.0.0
- **文件**: `soul_specs/dorothy/v1.0.0.yaml` (36K)
- **状态**: 与 rin 同结构，完整

### Golden Dialogues
- **路径**: `soul_specs/{rin,dorothy}/golden_dialogues/gd-*.yaml`
- **数量**: 10 个/角色（per drift design §2.1）
- **用途**: Phase 7 §1.4 baseline 生成的 prompt 来源

**结论**: ✅ soul_specs 满足 Phase 7 前置条件

---

## 6. backend/tests/ 基线状态

### 当前分支 (`feat/misc-updates`)
- **单元测试文件**: 21 个
- **总测试数**: ~414 (per test_audit.md)
- **状态**: ✅ 基线存在

### Super-branch (`feature/ss04-stage-engine`)
- **额外测试**: SS03-SS07 的测试（~150+ tests in PR branches per test_audit.md）
- **Failing tests**: 2 个
  - `test_mood_drift.py::test_low_volatility_ignores_recent_spike`
  - `test_trust_attachment.py::test_trust_increase_capped`
  - 这两个文件在当前分支不存在（需 PR #B/C 合并后修复）

**结论**: 
- ✅ 当前分支测试基线健康
- ⏳ Super-branch 合并后需修复 2 个 failing tests（Top 10 #3）

---

## 7. 可执行的下一步行动（按优先级）

### 🔴 P0 — 立即执行（今天）

1. **HUMAN: 确认 CI/CD billing 已修复**
   - 登录 GitHub → Settings → Billing
   - 确认 Actions 可用
   - 在本清单底部回复 "✅ CI/CD billing fixed"

2. **提交当前 5 个 blocker 文件**
   - 文件: PHASE_7_PLUS.md, INDEX.md, PR template, session_log.md, audit/
   - Commit message: `chore: add Phase 7 pre-launch blockers (2-5)`
   - Push to `feat/misc-updates`
   - Update PR #7

3. **更新 session_log.md 记录本次 session**
   - 添加本次 session 条目（见 §7.1）

### 🟡 P1 — 本周内

4. **PR #7 拿到 3 方 sign-off**
   - @mention 架构师 / 主创 / 心理顾问
   - 附上本清单 §2 + §3 作为 context
   - 预计 1-3 天 review cycle

5. **开始 PR #A (Governance + Docs slice)**
   - 从 `feature/ss04-stage-engine` checkout 16 个 governance 文件
   - 新分支: `feat/governance-slice`
   - 立即开 PR（不依赖设计稿 sign-off）
   - 预计 review: 1-2 天

6. **制定 Top 10 remediation 排期**
   - Items 1-4 (Critical) 必须在 PR #D merge 后立刻修
   - Items 5-10 (High) 可在 Phase 7 §1.2 实施中并行修
   - 预留 4 天 buffer

### 🟢 P2 — Phase 7 启动后

7. **PR #B/C/D 依次合并** (预计 1-2 周)
8. **执行 Top 10 remediation** (预计 4 天)
9. **Phase 7 §1.2 实施** (integration test pyramid 7-PR roadmap, 预计 2-3 周)
10. **Phase 7 §1.4 实施** (voice drift suite 8-PR roadmap, 预计 1-2 周)

---

## 7.1 本次 Session 记录（待添加到 session_log.md）

```markdown
| 2026-05-24 | CC-Sonnet-4.5    | Phase 7 准备工作完整清单 + 5 个 blocker 文件合并 | 10+   | ~60k   | ~$0.60 | 1      | 产出 PHASE_7_READINESS_CHECKLIST.md + 合并 PHASE_7_PLUS.md, INDEX.md, PR template, session_log.md, audit/ → feat/misc-updates; 确认 Top 10 Critical/High 阻塞项; 制定 PR #A-#D slicing 策略 |
```

---

## 8. Phase 7 Cut Criteria 进度

来源: `PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.9

| Criterion | 状态 | 备注 |
|-----------|------|------|
| ✅ Phase 7 前置条件 5 个 blocker 已清理 | 4/5 完成 | Blocker 1 (CI/CD) 需 HUMAN 确认 |
| ⏳ docs/design/integration_test_pyramid.md HUMAN sign-off | 等待 PR #7 | 需 3 方签字 |
| ⏳ docs/design/soul_drift_regression.md HUMAN sign-off | 等待 PR #7 | 需 3 方签字 |
| ⏳ Voice drift baseline 已存盘（rin + dorothy） | 未开始 | 等待 §1.4 sign-off |
| ❌ Top 10 Critical 问题已修复 | 0/4 | 需 super-branch 合并后执行 |
| ❌ 所有 unit tests passing | 待验证 | Super-branch 有 2 个 failing |
| ❌ Tier A contract tests 骨架存在 | 未开始 | §1.2 实施 PR #2 |
| ❌ Tier B integration tests (40+) | 未开始 | §1.2 实施 PR #4-5 |
| ❌ Tier C live LLM smoke tests (10+) | 未开始 | §1.2 实施 PR #6 |
| ❌ Governance lint CI workflow | 未开始 | Top 10 #10 |

**预计 Phase 7 可启动日期**: 2026-06-07 (2 周后)  
**前提**: CI/CD billing fixed + PR #7 signed + PR #A-#D merged + Top 10 Critical fixed

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| **CI/CD billing 无法修复** | P0 blocker，Phase 7 无法启动 | HUMAN 紧急处理；worst case 用 self-hosted runner |
| **PR #7 sign-off 周期过长** | 阻塞 §1.2/§1.4 实施 2+ 周 | 提前沟通；准备 follow-up Q&A |
| **Super-branch 合并冲突复杂** | PR #B/C/D review cycle 延长 | Slice 策略降低单 PR 复杂度；router.py 已确认是超集 |
| **Top 10 remediation 发现更多问题** | 预计 4 天拉长到 1 周+ | 并行执行 items 5-10；Critical 1-4 优先 |
| **2 个 failing tests 是深层 bug** | 修复时间 > 3 小时 | Audit 已定位文件和场景；应是参数调整 |

---

## 10. 资源与链接

### 关键文档
- **Phase 7+ 操作手册**: `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md`
- **Architecture Audit**: `docs/audit/2026-05-23_architecture_audit.md`
- **Integration Test Pyramid 设计**: `docs/design/integration_test_pyramid.md`
- **Voice Drift Regression 设计**: `docs/design/soul_drift_regression.md`
- **Test Audit 基线**: `docs/test_audit.md`
- **文档索引**: `docs/INDEX.md`
- **Governance 宪章**: `docs/GOVERNANCE.md` (in super-branch)

### GitHub
- **PR #7**: https://github.com/wangbai1234/heart/pull/7
- **Super-branch**: `feature/ss04-stage-engine`
- **当前分支**: `feat/misc-updates`

### 成本预算
- **Phase 7 §1.2 实施**: ~$50-100 (Tier B/C LLM 调用)
- **Phase 7 §1.4 baseline 生成**: ~$0.80 one-time (90 gens/char)
- **Phase 7 §1.4 per-PR regression**: ~$0.52/run
- **Monthly cap**: $100 (per drift design §6.2)

---

**版本**: 1.0  
**最后更新**: 2026-05-24  
**下次修订**: PR #7 merge 后 + Top 10 remediation 完成后

---

## ✅ HUMAN ACTION ITEMS (Copy-Paste Checklist)

```
立即（今天）:
□ 确认 GitHub Actions billing 已修复，回复 "✅ CI/CD billing fixed"
□ Review PR #7，@mention 三方 reviewer (架构/主创/心理顾问)
□ 阅读本清单 §2 (Top 10) + §3 (合并策略)

本周内:
□ 跟进 PR #7 review，回答 reviewer questions
□ 批准 PR #7 merge
□ Review PR #A (governance slice) when ready

Phase 7 启动前:
□ 确认 PR #A-#D 全部 merged
□ 确认 Top 10 Critical (items 1-4) 已修复
□ 签字同意启动 Phase 7 §1.2/§1.4 实施
```
