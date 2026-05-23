# AI Context — 最小化的"你必须知道"

> **本文件是任何 AI session 启动时的强制第一阅读 (~3K tokens)。**
> **更新规则**: 每个 Phase 收尾时由 AI 起草更新 → HUMAN approve。当前内容反映 2026-05-23 状态。

---

# 0. 你是谁，在哪里

```
Project:   心屿 (Heart) — AI Companion
Stack:     Python 3.11 + FastAPI + PostgreSQL + Redis + DeepSeek-only LLM
Repo:      /Users/wanglixun/heart  (github.com/wangbai1234/heart, public)
Branch:    feature/ss04-stage-engine
Current:   Phase 7 (Integration Hardening) — Week 31-34
```

# 1. 三层圣经，按这个顺序

**你只需要读这三个 SSOT 之一，根据任务类型：**

1. **你要实现/修改 subsystem 功能** → `runtime_specs/0X_*.md` 对应 section (用 Read offset)
2. **你要决定怎么用 AI / 跑什么 phase** → `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` (Phase 7+) 或 `PRACTICAL_MODEL_GUIDE.md` (Phase 0-6)
3. **你要遵守规则** → `engineering_execution/ENGINEERING_LAWS.md` (12 条) + `docs/GOVERNANCE.md`

**禁止做的**：盲目 Read 多个大文件去"建立全局认知"。

# 2. 12 条工程法则（速记版，完整版见 ENGINEERING_LAWS.md）

```
L1  Spec is Truth        — 代码与 spec 冲突，spec 赢
L2  Soul is Sacred       — Soul spec / voice_dna 改动必须 HUMAN approve
L3  Cost is Observable   — 每个 LLM call 走 CostTracker
L4  Verification is Mandatory — 没 test 不 merge
L5  Context is Precious  — Read with offset，session 超 50K → /clear
L6  Model Routing is Strict — LLM call 必须走 ModelRouter，禁止直接 import anthropic/openai
L7  Async by Default     — 阻塞 hot path = 错
L8  Idempotency Required — Worker 必须可重入
L9  User Isolation Absolute — 跨用户数据访问 = 安全 bug
L10 Failure Has Fallback — Circuit breaker + fallback msg
L11 Immersion Trumps Engineering — UX 体验感 > 内部架构优雅
L12 AI Coding ≠ Vibe Coding — 引用 spec + 不变量，不能"感觉对"
```

# 3. 项目当前真相 (Honest Truth)

```
✅ 完成:
  - Phase 0-6 所有 subsystem 已实现 (100+ Python 文件)
  - 1677 / 1694 unit tests 通过
  - Soul specs: rin, dorothy
  - 4 个 Alembic migration
  - 7 个 K8s deployment YAML (未部署)
  - 9 个 Runtime Spec + 完整 engineering_execution/ 文档体系

❌ 未完成:
  - 真实 DeepSeek e2e turn  ZERO 次跑通
  - Integration tests        仅 1 个 (test_migrations.py)
  - Frontend                  完全没有
  - Voice drift baseline      未生成
  - PURPLE drill              未执行
  - Architecture audit        未做
  - GitHub Actions CI         账单暂停 (HUMAN action required)

⚠️  当前 2 个失败 unit test:
  - test_mood_drift::test_low_volatility_ignores_recent_spike
  - test_trust_attachment::test_trust_increase_capped
  + 15 个 deselected 待审计
```

# 4. 文件去哪找（最小映射，全表见 docs/INDEX.md）

```
runtime_specs/01..08_*.md      — 系统级 SSOT（每个 subsystem 唯一）
engineering_execution/         — AI 工作流、phase 计划
docs/design/                   — 单 component 设计决策
docs/prompts/                  — agent prompt 文本
backend/heart/ss0X_*/          — 实际代码
backend/heart/ss0X_*/README.md — 模块级 readme（每个模块至多 1 个）
config/                        — runtime config (YAML)
soul_specs/<character>/        — 角色定义
docs/archive/                  — 历史快照 (永不回写)
docs/vision/                   — PRD
docs/runbooks/                 — 故障 runbook (待补)
docs/GOVERNANCE.md             — 仓库治理宪法
STATUS.md                      — 当前进度 + 下一步
```

# 5. 禁止 AI 自由发挥的硬边界

```
✗ 不准修改: runtime_specs/* (必须 RFC + HUMAN)
✗ 不准修改: soul_specs/<char>/*.yaml (HUMAN + 心理顾问)
✗ 不准修改: config/safety_keywords.yaml (legal + 心理)
✗ 不准修改: config/care_path_responses/ (心理顾问签字)
✗ 不准修改: .claude/CLAUDE.md (HUMAN)
✗ 不准修改: docs/GOVERNANCE.md (HUMAN)
✗ 不准 git push --force / rm -rf
✗ 不准直接 import anthropic/openai (L6)
✗ 不准在根目录创建新 .md (除非 README/STATUS/AGENTS)
✗ 不准创建 *_IMPLEMENTATION_SUMMARY.md / *_COMPLETION_REPORT.md
```

# 6. 现在做什么（具体）

```
Phase 7 入口任务: PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md §1.1
  → 修复 2 个失败 unit test + 审计 15 个 deselected
  → Tool: CC-S46
  → Time: 1 hour
  → 不需要 HUMAN review

Phase 7 整体序: §1.1 → §1.2 (Opus 设计) → §1.2 (S46 实施) → §1.3 → ...
完整 cut criteria: 见 PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md §1.9
```

# 7. AI Session Hygiene（强制）

```
□ 启动: 读 docs/AI_CONTEXT.md (本文件) + STATUS.md → 立刻进入任务
□ 工作: 用 Read offset/limit，禁止全文读 > 500 行文件
□ Token 预算: 设计任务 < 100K, 实施 < 50K
□ 写 PR: 用 .github/pull_request_template.md
□ 结束: 在 docs/session_log.md 添加一行 (model, task, files touched, token est, regret 1-5)
□ Context > 50K: /clear 重启
```

# 8. 一句话 hand-off

> **你不需要重新理解项目。你需要的是：(a) 读 STATUS.md 看下一个 task；(b) 读 PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md 找该 task 的 prompt；(c) 执行。**

---

**文件 token 估计：~2.5K**
**Last updated**: 2026-05-23 by Claude Opus 4.7
