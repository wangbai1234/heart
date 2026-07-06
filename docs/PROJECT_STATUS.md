# PROJECT STATUS — Heart (心屿)

> **AI Session 入口文档。任何新的 AI session（包括 Claude Code、Cursor、其他 agent）必须优先读完这份文件再开始工作。**
>
> 这份文件是当前真理。其它历史文件可以参考，但当与本文件冲突时，**以本文件为准**。

**最后更新**：2026-07-06
**当前 Phase**：✅ 商业外壳 + 记忆系统修复 + 语义召回 全部合并 main，进入手机端（响应式 Web）全面测试
**当前分支**：main（PR #86–#94 均已合并）

> 📖 **启动/部署/手机端测试/启用语义召回，一律看 [`docs/EXECUTION_MANUAL.md`](EXECUTION_MANUAL.md)（单一操作手册）。**

---

## 0. 近期进展（2026-07-06）— 记忆系统已修复，勿再当坏的

> ⚠️ 给新会话：下面这些**已经修完并合并 main**。旧文档 `docs/TEST_RESULTS.md` / `docs/MEMORY_FIX_PLAN.md`
> 描述的"记忆坏了/召回不触发/情绪硬编码/L4 脏数据"**都已修复**，那两份是历史工单，勿据其重做。

- **#86** 商业外壳（Email OTP 登录、积分、Profile、聊天持久化、语音）+ fastapi<0.137 修复。
- **#87** 记忆 PR1：召回回写 `recall_count` + L2 真实情绪/importance + 短期窗口 40→50。
- **#88** CI 修复：前端 `vite build` 崩溃（rolldown 单平台 lockfile 缺 linux 原生二进制）。
- **#89** 记忆 PR2：Resolver 拦截疑问句污染 L4（"什么吗"）+ `cleanup_dirty_l4.py`。
- **#90** 记忆 PR3：`EmotionEvent` 持久化（此前从不落库）。
- **#91–#94** 记忆 PR4：**语义召回端到端打通**——`EmbeddingService`（bge-m3 1024 维）、
  `semantic_vector` 768→1024（迁移 017）、L2/L3 写向量、composer 算 query embedding、回填脚本。
  **门控于 `EMBEDDING_API_KEY`**：不配则退回 recency/identity，系统正常。

**本地 docker 环境已启用语义召回**（迁移 017 已跑、572 L2 + 196 L3 已回填、脏 L4 已清、实测 `vector` 策略生效）。
staging/prod 需各自跑：`alembic upgrade heads` + `backfill_embeddings.py --apply` + 配 key（详见执行手册 §7）。

**仍保留（设计如此/非 bug）**：scene_context 缺失、L2/L3 结构差异、`drifting` 关系态。

**待办功能（未实现）**：`docs/upgrade/commercial/06_anonymous_email_delivery.md`（匿名邮件 OTP 投递，
前置 `EmailSender` 抽象已就绪，可直接开发）；PWA "安装到桌面/主屏"（当前无 manifest/SW，见手册 §9）。

---

## 1. 一句话 TL;DR（历史，2026-06-21）

> ✅ SS02 Memory LLM Extractor 重构交付完结。v1.0.3 达到 47/49 (95.9%) strict pass。
> （注：其后已叠加 #86–#94，见上方 §0。）

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

| # | 阻塞项 | 严重度 | Issue/PR | 状态 |
|---|--------|--------|----------|------|
| - | v1.0.3 prompt + strict scoring | Complete | PR #42 | ✅ 47/49 (95.9%) |
| - | migration 009 typo fix | Hotfix | PR #45 | ✅ alembic upgrade head 全绿 |
| - | MiMo TTS provider | — | PR #43 | ✅ open |
| 1 | consolidator test 顶层 import 阻塞 unit collection | 🟡 P2 | #46 | ⏳ pre-existing |
| 2 | E2E /api/chat returns before session commit | 🟡 P2 | #47 | ⏳ 不阻塞前端 |
| 3 | encoder-worker restart loop | 🟠 P1 | #48 | ⏳ 阻塞 Closed Beta |
| 4 | v1.1.0 backlog (frag-004/mixd-002/adv-005) | 🟡 P2 | #44 | ⏳ prompt 迭代 |

**✅ SS02 Memory LLM Extractor 重构交付完结 @ 2026-06-21**。PR #42 等 review + merge。P0 全清（untracked files 入 git / 分支拆解 / PR 合规 / migration hotfix）。

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

1. ~~P0-1 untracked 文件 audit + add~~ ✅
2. ~~P0-2 拆分支 feat/ss02-llm-extractor-v1.0.3~~ ✅ PR #42 open
3. ~~P0-3 PR #41 收敛~~ ✅ closed → PR #43 MiMo clean
4. ~~P1-1 收敛 PR #39/#40~~ ✅ closed
5. ~~P1-2 v1.1.0 backlog issue~~ ✅ #44
6. ~~P0-A migration 009 hotfix~~ ✅ PR #45
7. ~~P1-A/B + P2-B issue 登记~~ ✅ #46/#47/#48
8. 👤 **HUMAN 决策** — 前端技术栈（RN+Expo / Flutter / Next.js）
9. ⏳ 等 PR #42 (SS02) + #43 (MiMo) + #45 (migration) merge → 前端启动

详见 `docs/execution/POST_SS02_NEXT_STEPS_2026-06-21.md`

## 6. 当前风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| **encoder-worker restart loop** | Closed Beta 时 L2/L3 pipeline 不通 | #48 登记，Phase 10 前置条件 |
| **E2E session write race** | E2E 不稳定，误报 | #47 登记，commit-then-respond 修 |
| consolidator test collection 阻塞 | unit run 有 15 个 error | #46 登记，lazy import |
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
- **✅ SS02 Memory LLM Extractor 重构交付完结 @ 2026-06-21** — PR #42 (v1.0.3, 47/49 95.9%)
- **PR open**: #42 (SS02) + #43 (MiMo TTS) + #45 (migration hotfix)
- **Issues**: #44 (v1.1.0) / #46 (consolidator) / #47 (E2E) / #48 (encoder)
- **P0 全清** — untracked files 入 git / 分支拆解 / PR 合规 / migration hotfix
- 验收文档: `docs/execution/SS02_ACCEPTANCE_AND_NEXT_STEPS_2026-06-21.md` + `POST_SS02_NEXT_STEPS_2026-06-21.md`
