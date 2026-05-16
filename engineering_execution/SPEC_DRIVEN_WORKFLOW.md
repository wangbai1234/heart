# Spec-Driven Workflow — Quick Reference

> **目的**: 每天的工作流程
> **配套**: EXECUTION_PLAN.md §5

---

## 1. The Loop

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   TASK ──▶ ROUTE ──▶ EXECUTE ──▶ VERIFY ──▶ MERGE       │
│    ▲                                          │         │
│    │                                          │         │
│    └──────────── RFC if blocked ◀─────────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Per-Task Workflow (10 步)

### 启动一个 Task

```bash
# 在 task tracker 中创建/认领 task
# 例: P2-SS02-encoder-fast

# 决定 routing (见 AI_MODEL_ROUTING.md)
# 假设: Sonnet (standard implementation)
```

### Step 1: 读 Spec

```bash
claude  # 启动 Claude Code session

# 在 session 中:
> Read runtime_specs/02_memory_runtime.md §3.4 to understand Fast Encoder pipeline.
> Also read §5.7 for the encoding event schema.
```

**关键**: 用 Read with offset/limit, 不要 cat 整个文件.

### Step 2: 检查现有代码

```bash
> List backend/heart/ss02_memory/ to see existing structure
> Read existing encoder.py if exists
```

### Step 3: Plan

```bash
> EnterPlanMode
> Plan:
  1. Implement FastEncoder class
  2. Lexicon-based sentiment
  3. Regex identity signal extraction
  4. Queue LLM encoding event
  
  Files to touch:
  - backend/heart/ss02_memory/encoder/fast.py
  - tests/unit/test_fast_encoder.py
  
> ExitPlanMode (after user/Tech Lead approves)
```

### Step 4: Implement

```bash
> Write backend/heart/ss02_memory/encoder/fast.py
> (use Edit / Write tools)
```

### Step 5: Test

```bash
> Write tests/unit/test_fast_encoder.py
> Run: bash pytest tests/unit/test_fast_encoder.py -v
```

### Step 6: Verify Invariants

```bash
> Check INV-M-* compliance:
  - user_id present in all event payloads? ✓
  - No DELETE on memory? ✓
  - Heuristic returns < 50ms? (profile)
```

### Step 7: Spec Validator

```bash
# 调用 spec-validator subagent
> /verify-spec
```

### Step 8: Commit

```bash
git add backend/heart/ss02_memory/encoder/fast.py tests/unit/test_fast_encoder.py
git commit -m "feat(SS02): implement FastEncoder per §3.4

Spec: runtime_specs/02_memory_runtime.md §3.4
Touches: SS02 encoding pipeline (sync hot path)
Tests: tests/unit/test_fast_encoder.py (4 cases)
Performance: P95 < 50ms verified
"
```

### Step 9: PR

```bash
gh pr create --title "feat(SS02): FastEncoder" --body "$(cat <<'EOF'
## What
Implement Fast Heuristic Encoder for SS02.

## Spec References
- runtime_specs/02_memory_runtime.md §3.4
- runtime_specs/02_memory_runtime.md §5.7 (encoding event schema)

## Touches
- backend/heart/ss02_memory/encoder/fast.py

## Personality-Sensitive?
- [x] No, pure plumbing

## Verification
- [x] Unit tests pass (4 cases)
- [x] P95 latency < 50ms verified  
- [x] INV-M-* preserved (no DELETE, user_id filtering)
- [x] Spec validator pass
EOF
)"
```

### Step 10: After Merge

```bash
# Update task tracker
# Move to next task
# 关闭 Claude session (回收 token)
```

---

## 3. Daily Routine

### 09:00 — Day Start

```bash
# 1. Check overnight CI / alerts
gh run list --limit 5
# 看 Grafana for production metrics (if applicable)

# 2. Pull latest
git pull origin main

# 3. Review yesterday's PRs (any pending?)
gh pr list --author "@me"

# 4. Check assigned tasks
# (consult task tracker / TaskList tool)
```

### 09:30 — Stand-up (10 min)

```
- Yesterday: 完成什么
- Today: 要做什么
- Blocker: 是否有 (Spec 不清 / 依赖未完成 / etc.)
```

### 09:40 — 开始 task

按 §2 10 步 workflow

### 12:00 — Lunch break

```
# 暂停 Claude session
# Cost check: 上午用了多少 token?
```

### 13:00 — Continue tasks

### 16:00 — PR Review (your turn)

```bash
# Review queue
gh pr list --review-requested "@me"

# Per PR, use HUMAN_REVIEW_CHECKLIST.md
```

### 17:30 — End of Day

```bash
# 1. Commit WIP if any
git add -p
git commit -m "wip: partial impl of X"
git push

# 2. Update TaskUpdate
# (mark completed / in_progress / blocked)

# 3. Note token usage
# (cost dashboard or local tracking)

# 4. Tomorrow's plan
```

---

## 4. Weekly Routine

### Monday Morning — Sprint Planning

```
1. Review last week's velocity
2. Pick this week's tasks from backlog (priority + dependency)
3. Assign per engineer
4. Identify any spec ambiguity → RFC if needed
```

### Wednesday — Mid-week Sync

```
- Quick standup
- Any blockers?
- Adjust priorities if needed
```

### Friday — Retrospective

```
- Demo what's done this week
- Cost review (any waste?)
- Drift report (Critic failure rate trend)
- Tech debt accumulated?
- Process improvement?
```

---

## 5. 使用 Claude Code 高效技巧

### 5.1 Session 管理

```
原则: 1 session = 1 task

不要:
  - 一个 session 实现整个 subsystem
  - Session 内反复读大文件
  - Session > 50k tokens (重启)

要:
  - Task 完成后 /clear 或重启
  - 大任务 → spawn subagent 隔离
  - 关键决策前 用 EnterPlanMode
```

### 5.2 Context 高效

```
# 不好 (读整个文件)
> Read runtime_specs/02_memory_runtime.md

# 好 (定位 + 精确读)
> Bash: grep -n "Top-K" runtime_specs/02_memory_runtime.md
# 输出: line 1234: ## §3.5 Top-K Selector
> Read runtime_specs/02_memory_runtime.md offset 1234 limit 50
```

### 5.3 Subagent 隔离

```
# 在主 session 已经 30k token, 需要做 unrelated task

# 不好:
> Now also implement the consolidator...
# (主 session 继续膨胀)

# 好:
> Agent(
    description="Implement consolidator",
    subagent_type="memory-impl",
    prompt="Read §3.6 and implement Consolidator per spec."
  )
# (Subagent 隔离 context)
```

### 5.4 多文件同时编辑

```
# 不好: 一个一个 Edit
> Edit file1.py ...
> Edit file2.py ...

# 好: 同一 message 多个 tool calls (并行)
> [Edit file1.py + Edit file2.py + Edit file3.py in single message]
```

### 5.5 Plan Mode 用于复杂

```
对于:
  - Multi-file refactor
  - 新模块设计
  - Cross-subsystem 变更

强制使用:
> EnterPlanMode
> [show plan]
> ExitPlanMode (after approval)

不要直接开始 Edit/Write 而不 plan.
```

---

## 6. AI Coding 不要做的事

### ❌ Don't

```
- 没读 spec 就开始写
- 一次 Edit 多个 file 但没 plan
- "AI 觉得 spec 应该这样" 自主修改 spec
- 跳过测试
- "性能应该够吧" 不 profile
- 在 hot path 加 LLM call 不评估成本
- Read 整个大文件 (用 grep + offset)
- 反复让 AI 总结代码 (浪费 token)
- 用 Opus 写 boilerplate
- 用 Haiku 做 Critical
```

### ✅ Do

```
- Spec 先, code 后
- Plan, then implement
- 写测试 (per spec §11)
- Profile + cost track
- Sub-agent 隔离 context
- 引用 spec section in commits
- Periodic /clear and restart session
- Cite specific spec invariants in PR
```

---

## 7. Cheat Sheet: Common Tasks

### Task: 实现新 Subsystem 的 Service

```
1. Read §1, §2, §3, §7 of subsystem spec
2. Plan based on §10.2 (Service Interface)
3. Generate SQLAlchemy from §5 with Haiku
4. Implement Service class with Sonnet
5. Tests from §11 fixtures
```

### Task: Bug fix

```
1. Reproduce
2. Identify which subsystem (从 file path)
3. Read relevant spec section
4. Check if Bug is in code or spec ambiguity
   - Spec ambiguity → RFC
   - Code bug → fix
5. Write failing test
6. Fix
7. Verify all tests + invariants
```

### Task: Performance optimization

```
1. Profile to identify hotspot
2. Read §10 of relevant subsystem
3. Check performance targets in §10
4. Optimize
5. Verify still meets all invariants + targets
6. Check cost impact
```

### Task: New character

```
1. Read SS01 附录 A (7 questions)
2. Brainstorm with Opus (subagent: soul-spec-author)
3. Human writes Soul Spec
4. Generate golden_dialogues (Human)
5. Run golden_dialogues regression
6. Soul Spec sign-off (creator + Tech Lead)
7. Deploy
```

---

## 8. 1-Page Summary

```
Day starts → Pull → Stand-up → Task
                                  ↓
                          Route (model)
                                  ↓
                    Claude Code session
                                  ↓
                  Read Spec (precise) → Plan → Implement → Test
                                                              ↓
                  Verify INV → Spec validator → Commit → PR
                                                              ↓
                                          Reviewer (Human) → Merge
                                                              ↓
                                                          Next task

Cost rules:
  - Default Sonnet
  - Opus 只 for architecture
  - Haiku/DeepSeek 只 for spec-driven boilerplate
  - Soul stuff → Human only
  - 50k token → restart session

Spec rules:
  - Read precisely (offset/limit)
  - Cite in commits
  - Validator on every PR
  - INV always preserved
```
