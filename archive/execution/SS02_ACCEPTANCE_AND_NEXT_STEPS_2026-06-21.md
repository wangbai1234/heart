# SS02 Memory LLM Extractor 重构 — 验收报告 + 关键路径文档更新 + 下一步

> **Context**
>
> 用户在两次 commit (878cc57 + db2d9fc) 后宣告"SS02 LLM Extractor 重构完结，v1.0.3 strict scoring 47/49 (95.9%)"，并要求：(a) 做验收；(b) 更新关键路径文档；(c) 梳理下一步。
>
> 本次调查发现：**功能完结属实，但工程交付不完整**——核心 SS02 实现文件 git 没追踪、分支已沦为"事实主干"反模式、PR #41 超 7 天硬性上限。"完结"成色被严重稀释，必须在合 main 前补齐。本 plan 给出验收结论、文档真相修复、与按硬性约束优先级排序的下一步。
>
> **执行模型**: opencode 顺序跑 Phase 1 → 2 → 3，HUMAN 在 P0-2 拍板分支策略选项 + P3 前端栈决策。

---

# Phase 1 — 验收（事实表）

## 1.1 已落地（绿）

| 项 | 证据 |
|---|---|
| PROMPT_VERSION 锁定 1.0.3 | `prompt_builder.py:22` |
| R11 收紧 / R5 排除纯情绪 / R6 不 drop / R12 "了"路径 / Example 9 | commit **878cc57** stat: prompt_builder.py +119 lines |
| Strict scoring + drop-reason relax + crash sanitize | commit 878cc57 同次入 `llm_extractor.py` / `test_extractor_golden.py` |
| Live golden 47/49 (95.9%) | 用户报告 + commit message |
| PROJECT_STATUS.md 标 COMPLETE | commit **db2d9fc** |
| feat/ 命名规范 | `feat/mimo-tts-provider`（命名形式合规，scope 不合规——见 1.2） |

## 1.2 不合规 / 风险（红）

| # | 问题 | 违反的 CLAUDE.md 规则 | 严重度 |
|---|---|---|---|
| **R1** | `regex_shadow.py` / `resolver.py` / `writer.py` / `promoter.py` / `golden_loader.py` / `hints/` / `extractor_diff_report.py` **git 从未追踪**（`git log --all -- <file>` 全空，文件本地存在 4KB+） | "跨分支代码状态判断必须基于 `git show` / `git ls-tree` 实际输出"——这些文件**根本不在任何 commit 里**，clone main 拿不到 | 🔴 P0 — 阻塞合 main |
| **R2** | `feat/mimo-tts-provider` 持续累积 **12 commits**：1 MiMo TTS + 3 voice fix + 5 SS02（含 LLM Extractor 5 个 commit）+ 3 其它 | "禁止把某 feature 分支变成'事实主干'（持续累积 10+ 提交、包含多个不相关功能、被当作开发基线）" | 🔴 P0 |
| **R3** | PR **#41** 已 open **7 天**（2026-06-14 → 2026-06-21） | "任何 PR open 超过 7 天必须二选一：合并 或 关闭" | 🔴 P0 |
| **R4** | 单人 open PR = 3（#39 / #40 / #41），达上限 | "任何时刻，单人 open PR 数 ≤ 3" | 🟠 P1 — 不能再开第 4 个 |
| **R5** | 工作树 43 modified + 57 untracked，跨 SS02 / SS03 / SS04 / SS05 / SS07 / SS08 / web / docs / config / migrations | 间接违反"PR scope 单一" | 🟠 P1 |
| **R6** | PROJECT_STATUS.md §3 / §5 写"待合 main"，但**当前状态合不进去**（R1 + R2 + R3） | 文档与现实脱节 | 🟡 P2 — 文档修复 |

## 1.3 验收结论

> **SS02 LLM Extractor 功能完结 = TRUE**
> **SS02 LLM Extractor 交付完结 = FALSE**

prompt / scoring / golden 都达到 ≥ 90% 阈值，从 commits 看 v1.0.3 内容正确；但 **R1 (核心实现文件未 add) 是阻断性 bug** —— 拉 main 跑就找不到 `resolver.py`，整个 LLM Extractor 跑不起来。这不是"小尾巴"，是"完结"的反义。

---

# Phase 2 — 关键路径文档真相修复

> **原则**：先把 PROJECT_STATUS.md 改成"功能完结，交付未完结"，再补 Phase 3 的执行步骤。文档说真话比说漂亮话更重要。

## 2.1 `docs/PROJECT_STATUS.md`

| 段 | 当前写法 | 改为 |
|---|---|---|
| §1 TL;DR | "✅ SS02 完结…下一步：git commit + push PR → 前端…" | "🟡 SS02 功能完结（prompt v1.0.3, 47/49 95.9% strict），交付未完结：核心实现文件未追踪 + 分支已是事实主干。下一步：拆分支 + add 未追踪文件 → SS02 独立 PR → 前端栈决策" |
| §3 Blocker 表 | "SS02 重构完结 ✅ Complete" | 拆 2 行：「v1.0.3 prompt ✅ committed (878cc57)」+ 「**SS02 实现文件未 git track P0**（regex_shadow/resolver/writer/promoter/golden_loader/hints/extractor_diff_report）」 |
| §5 下一步 | "1. 合 main / 2. HUMAN 前端决策 / 3. Frontend MVP" | "1. **抢救分支治理（P0）**：未追踪 SS02 文件 audit + add；feat/mimo-tts-provider scope 拆分 / 2. SS02-only PR → main / 3. PR #41 scope 还原 / 4. 收敛 #39 #40 / 5. HUMAN 前端决策 / 6. Frontend MVP" |
| §6 风险表 | 只有 strict scoring 75.5% 那行（旧的） | 加 3 行：「事实主干分支 → 任何 SS02 改动现都从 mimo 分支出 / PR #41 7 天上限 → 必须 24h 内收敛 / 未追踪 SS02 文件 → main 跑不通 LLM Extractor」 |
| §维护规则 | "**✅ SS02 完结 @ 2026-06-21** — v1.0.3, 47/49 (95.9%), commit 878cc57" | 改为 "**🟡 SS02 prompt 完结 @ 2026-06-21** — v1.0.3, commit 878cc57 (47/49)。**交付完结待 untracked SS02 实现文件入 main**。" |

## 2.2 `docs/execution/MEMORY_EXTRACTOR_V1_0_3_FINAL.md`

末尾追加 **`## Final Outcome (2026-06-21)`** 段：

```markdown
## Final Outcome (2026-06-21)

**Prompt v1.0.3**: 47/49 = 95.9% strict scoring pass — meets ≥ 90% target.
**Commits**: 878cc57 (prompt + scoring) + db2d9fc (PROJECT_STATUS update).
**Branch state**: feat/mimo-tts-provider（事实主干，待拆）.

### 转绿明细 (7/8 surgical targets + 1 crash)
- coref-001/003/004, disc-006 (R11 收紧)
- rhet-004/005 (R5 排除纯情绪)
- qstn-004 (R6 不 drop + sanitize)
- neg-003 (R12 L3 优先路由)
- crash → fixed via sanitize unknown drop reason → "other"

### v1.1.0 backlog (3 cases — 已知 regression)
- frag-004 跨 turn modifier 合并
- mixd-002 多 step + assistant-claim
- adv-005 R11 过度收紧（"小明是我儿子" 混淆 name/relation）

### ⚠️ 未完结的工程债（必须在 main PR 前修）
- 未追踪 SS02 文件: regex_shadow / resolver / writer / promoter / golden_loader / hints / extractor_diff_report
- 分支治理违规: 见 PROJECT_STATUS.md §6 风险表
```

## 2.3 `docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md`

文件头追加：

```markdown
**STATUS: PROMPT COMPLETE @ 2026-06-21 — v1.0.3 47/49 (95.9%)**
**DELIVERY: NOT COMPLETE — pending untracked SS02 files add + branch split. See V1_0_3_FINAL.md §Final Outcome.**
```

## 2.4 4 份 design doc 的 `## Approval` trail

- 用 `git log` + grep 验证 commit **1511ff4** 是否真把 `## Approval` 加进 4 份 doc（commit message 提了 "approval trail"）：
  ```bash
  git show 1511ff4 -- docs/design/memory_extractor_schema.md docs/design/memory_extractor_prompt.md docs/design/memory_promoter_rules.md docs/design/memory_golden_set_design.md | grep -A 5 "## Approval"
  ```
- 如已加：在 PROJECT_STATUS.md §3 标 ✅。
- 如缺漏：补在 SS02 收尾 PR 一并提（不开第 4 个 PR）。

---

# Phase 3 — 下一步（按硬性约束优先级）

> 顺序锁死。每完成一项立即勾选 PROJECT_STATUS.md。**不允许并行做 P0**。

## P0-1 抢救：未追踪 SS02 文件 audit

```bash
# 1. 列全部 untracked SS02 相关文件
git ls-files --others --exclude-standard \
  | grep -E "backend/heart/(ss02_memory|qa/golden_loader|scripts/extractor)" \
  | sort > /tmp/ss02_untracked.txt
cat /tmp/ss02_untracked.txt

# 2. 对每个文件确认是否应入 git
# 必须入：regex_shadow.py / resolver.py / writer.py / promoter.py / golden_loader.py / hints/*.py / extractor_diff_report.py
# 必须 .gitignore：本地 cache / live_runs JSON dump

# 3. 如有 backend/golden/ 是 fixture 还是 cache？
ls -la backend/golden/ | head -20
```

**判定**：
- `.py` 实现文件且被 `from heart.ss02_memory.extractor.resolver import ...` import → **必须 add**
- `backend/docs/audit/live_runs/*.json` → 是单次 run dump，**.gitignore**
- `backend/golden/` → 看内容决定（若是 golden cases 备份 → ignore；若是新增 fixtures → add）

## P0-2 抢救：分支拆解策略

> **目标**：让 SS02 重构的 commits 单独走 main hotfix-like PR；MiMo TTS 留在 feat/mimo-tts-provider；voice fix 各自归位。

**两种选项**（HUMAN 拍板）：

### 选项 A（推荐）— Cherry-pick 出新分支

```bash
# 从 origin/main 起新分支
git fetch origin
git checkout -b feat/ss02-llm-extractor-v1.0.3 origin/main

# 按依赖顺序 cherry-pick 5 个 SS02 commits
git cherry-pick 1c090b7  # LLM Extractor 基础
git cherry-pick 9e2665e  # v1.0.1
git cherry-pick 1511ff4  # strict scoring + v1.0.2 + INV + approval
git cherry-pick 878cc57  # v1.0.3
git cherry-pick db2d9fc  # PROJECT_STATUS

# P0-1 的 add：在新分支上 git add 关键 SS02 实现文件，单独 commit
git add backend/heart/ss02_memory/extractor/regex_shadow.py \
        backend/heart/ss02_memory/extractor/resolver.py \
        backend/heart/ss02_memory/extractor/writer.py \
        backend/heart/ss02_memory/promoter.py \
        backend/heart/ss02_memory/hints/ \
        backend/heart/qa/golden_loader.py \
        backend/heart/scripts/extractor_diff_report.py
git commit -m "feat(ss02): add LLM Extractor support modules (resolver/writer/promoter/regex_shadow/hints/golden_loader/diff_report)"

# Phase 2 的 doc 改动也提进同一分支
# （编辑 PROJECT_STATUS.md / V1_0_3_FINAL.md / MEMORY_LLM_EXTRACTOR_REFACTOR.md）
git add docs/PROJECT_STATUS.md \
        docs/execution/MEMORY_EXTRACTOR_V1_0_3_FINAL.md \
        docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md
git commit -m "docs(ss02): mark prompt complete + delivery pending; truth-fix branch state"

# 跑一次 ci.sh 确认 clean checkout 能过
bash scripts/ci.sh

# Push + open PR (base=main)
git push -u origin feat/ss02-llm-extractor-v1.0.3
gh pr create --base main \
  --title "feat(ss02): LLM Extractor refactor v1.0.3 — 47/49 strict pass" \
  --body "$(cat <<'EOF'
## Summary
SS02 Memory LLM Extractor 重构，v1.0.3 prompt 达到 47/49 (95.9%) strict scoring pass。

## 包含 commits
- 1c090b7 LLM Extractor 基础 (INV-M-11)
- 9e2665e v1.0.1 prompt fix
- 1511ff4 strict scoring + v1.0.2 + INV-M-15/NEW-A property test + 4 design doc approval trail
- 878cc57 v1.0.3 — R11/R5/R6/R12 + Example 9
- db2d9fc PROJECT_STATUS 标 prompt 完结
- + 1 commit: add untracked SS02 support modules
- + 1 commit: doc truth-fix (prompt complete vs delivery pending)

## 关键改动
- prompt_builder.py v1.0.3 (PROMPT_VERSION + R11/R5/R6/R12 + Example 9)
- llm_extractor.py crash sanitize
- test_extractor_golden.py strict scoring
- resolver / writer / promoter / regex_shadow / hints / golden_loader / extractor_diff_report 入 git

## Refs
- docs/execution/MEMORY_EXTRACTOR_V1_0_3_FINAL.md §Final Outcome
- docs/execution/SS02_ACCEPTANCE_AND_NEXT_STEPS_2026-06-21.md（本验收 plan）

## v1.1.0 backlog (开 issue tracking)
frag-004 / mixd-002 / adv-005
EOF
)"
```

### 选项 B — 在 feat/mimo-tts-provider 上 reset

不推荐：会破坏 PR #41 的 history，且无法把 voice fix / MiMo / SS02 干净分开。

## P0-3 PR #41 (MiMo TTS) scope 还原

- 7 天上限已到，硬性条款。
- **选项 1（推荐）**：把 PR #41 close，新建只含 MiMo TTS commits (225d3a2 + 5ac15cf + 6349ffb) 的 `feat/mimo-tts-clean` 分支重开。
- 选项 2：把 PR #41 强行合 main（如果 voice + SS02 + 未追踪文件都已经在 P0-1/P0-2 中拆走，PR #41 应回到只有 MiMo TTS 的合理体量）。

```bash
# 选项 1：
gh pr close 41 --comment "Closing for scope split — see #SS02 PR + new feat/mimo-tts-clean"
git checkout -b feat/mimo-tts-clean origin/main
git cherry-pick 225d3a2 5ac15cf 6349ffb
git push -u origin feat/mimo-tts-clean
gh pr create --base main --title "feat(voice): MiMo TTS provider" --body "..."
```

## P1-1 收敛 PR #39 / #40

- 各自 7 天计时：#39 已 8 天（**逾期**），#40 已 8 天（**逾期**）。
- 必须合并或关闭，不许继续挂。

```bash
gh pr view 39 --json title,state,additions,deletions,changedFiles
gh pr view 40 --json title,state,additions,deletions,changedFiles
# 看是否仍 relevant；若已被 mimo 分支吸收，close；否则 merge
```

## P1-2 v1.1.0 backlog GitHub issue

```bash
gh issue create \
  --title "[ss02][v1.1.0] memory extractor 复杂语义边界 case" \
  --body "$(cat <<'EOF'
## 背景
v1.0.3 ship 后仍有 3 case 无法通过 patch-level prompt fix 解决，属于 v1.1.0 范围。

## Cases
### frag-004 — 跨 turn modifier 合并
Input: 「我妈妈是老师。教数学的。」
Golden: (family, occupation, "数学老师", src=[1,2])
需要: R4 加 "attribute value cross-turn merge" 子条款 + 1 示范

### mixd-002 — 单 turn 多 step + assistant-claim
Input: 「你猜我叫什么？其实我叫王强。你之前说我26岁，那不对，我27了。」
Golden: (self,name,王强) + (self,age,27) + drop out_of_scope_entity
需要: 单 turn 多 step 解析示范 + assistant-claim drop 教学

### adv-005 — R11 收紧 regression
Input: 「小明是我儿子」
当前 v1.0.3: name/relation 路由混淆
需要: Example 10 给出"称谓+专名同句"消歧示范

## Acceptance
- v1.1.0 prompt 让这 3 case 转绿
- v1.0.3 已通过的 case 全部 regression-safe
- prompt version bump 到 1.1.0
EOF
)"
```

issue link 写入 PROJECT_STATUS.md §3 backlog 行。

## P2-1 dual-mode skip rationale doc

```bash
ls docs/audit/2026-06-20_dual_mode_skip_rationale.md
git log --all --oneline -- docs/audit/2026-06-20_dual_mode_skip_rationale.md
```

- 如缺：在 P0-2 cherry-pick 后的新分支上一并补，**不开 PR-4 独立 PR**（PR 数已紧张）。
- 内容模板见 `MEMORY_EXTRACTOR_REFACTOR_AUDIT_AND_v1_0_2_PLAN.md` §3.4 "PR-4 改动 1"。

## P3 — HUMAN 决策

P0/P1 全清后，进 PROJECT_STATUS.md §5 原计划：
1. HUMAN 前端栈决策（RN+Expo / Flutter / Next.js）→ `docs/design/frontend_stack_decision.md`
2. Phase 9 Frontend MVP

---

# Phase 4 — Cut Criteria (整体)

```
□ P0-1 untracked SS02 文件全部分类完毕（add / gitignore）
□ P0-2 feat/ss02-llm-extractor-v1.0.3 分支建立 + 5 commits + 实现文件 add commit + doc truth-fix commit
□ P0-2 bash scripts/ci.sh 在 clean checkout 上全绿
□ P0-2 SS02 PR open + base=main + body 引用 V1_0_3_FINAL.md
□ P0-3 PR #41 处置完成（关闭重开 或 合 main）
□ P1-1 PR #39 / PR #40 处置完成
□ P1-2 v1.1.0 backlog issue 开了 + link 入 PROJECT_STATUS.md
□ Phase 2 的 PROJECT_STATUS.md / V1_0_3_FINAL.md / MEMORY_LLM_EXTRACTOR_REFACTOR.md 改动随 SS02 PR 一并入 main
□ 4 份 design doc Approval trail 已存在（verify commit 1511ff4）
□ docs/audit/2026-06-20_dual_mode_skip_rationale.md 存在并签字
□ PROJECT_STATUS.md 最后一行改 "✅ SS02 Memory LLM Extractor 重构交付完结 @ <merge-date>"
```

---

# Phase 5 — 风险表

| 风险 | 触发条件 | 缓解 |
|---|---|---|
| Cherry-pick 冲突 | 5 commits 之间有 prompt_builder.py 多次叠改 | 用 `-x` 保留来源，冲突时按最新 (v1.0.3) 状态解决；测试驱动 |
| 未追踪文件其实是另一份 feature 分支的产物 | 别处也有人在做 SS02 | `git branch -a --contains <file path>` + `git log --all -S "<resolver class name>"` 排查 |
| 工作树 43 mod 跨子系统污染 SS02 PR | cherry-pick 后还能 clean | cherry-pick 在 origin/main 新分支上，工作树 mod 不传染 |
| PR #41 / #39 / #40 强行关闭丢工作 | 用户已交付的 voice/TTS 改动 | 先 cherry-pick 关键 commit 到独立分支再关 PR |
| HUMAN 一次性看到太多债务而 paralysis | 5 条 P0/P1 串行执行 | Plan 已按硬性优先级排序，逐项做即可 |

---

# Phase 6 — 改动文件清单

| 阶段 | 文件 | 改动类型 |
|---|---|---|
| P0-1 | `backend/heart/ss02_memory/extractor/{regex_shadow,resolver,writer}.py` | `git add` (首次入 git) |
| P0-1 | `backend/heart/ss02_memory/promoter.py` | `git add` |
| P0-1 | `backend/heart/ss02_memory/hints/` | `git add -A` |
| P0-1 | `backend/heart/qa/golden_loader.py` | `git add` |
| P0-1 | `backend/heart/scripts/extractor_diff_report.py` | `git add` |
| P0-1 | `.gitignore` | 加 `backend/docs/audit/live_runs/*.json`（若证实是 dump） |
| Phase 2 | `docs/PROJECT_STATUS.md` | §1/§3/§5/§6/§维护规则 重写 |
| Phase 2 | `docs/execution/MEMORY_EXTRACTOR_V1_0_3_FINAL.md` | 末尾加 `## Final Outcome` |
| Phase 2 | `docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md` | 头部加 STATUS line |
| P0-2 | `feat/ss02-llm-extractor-v1.0.3` 分支 | 新建 + cherry-pick + add commit |
| P0-3 | PR #41 | 关闭或还原 scope |
| P1-1 | PR #39 / #40 | 关闭或合并 |
| P1-2 | GitHub issue v1.1.0 backlog | 新建 |

---

# Phase 7 — Verification（执行完后跑）

```bash
# 1. clean checkout 能跑 SS02 LLM Extractor
cd /tmp && rm -rf heart-verify && git clone <repo> heart-verify
cd heart-verify
git checkout main
bash scripts/ci.sh
cd backend
python -c "from heart.ss02_memory.extractor.resolver import Resolver; print('OK')"
python -c "from heart.ss02_memory.extractor.writer import Writer; print('OK')"
python -c "from heart.ss02_memory.promoter import Promoter; print('OK')"

# 2. Live golden 在 main 上重跑
make memory-golden       # fake mode
make memory-golden-live  # 真 LLM — 应仍 ≥ 95% (47/49)

# 3. PR 状态
gh pr list --state open --author "@me"   # 应 ≤ 3，且没 PR > 7 天

# 4. Branch state
git branch -a | grep feat/mimo-tts        # 拆完后可保留也可删
git branch -a | grep feat/ss02-llm        # SS02 PR 分支
```

---

**版本**: 1.0.0
**创建日期**: 2026-06-21
**主笔**: Opus 4.7
**执行模型**: opencode 顺序跑 Phase 1 → 2 → 3；HUMAN 在 P0-2 拍板分支策略选项 + P3 前端栈决策
**预计交付完结**: 2026-06-22（24h 内 P0 全清）
