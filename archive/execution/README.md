# 心屿 — AI-Assisted Engineering Execution Plan

> **角色**: Engineering Execution Bible
> **配套**: Runtime Specification Bible (`/runtime_specs/`)
> **读者**: Engineering Director / Tech Lead / AI Coding Agents / Reviewers
> **状态**: 必须遵守。所有 AI 协同开发以此为准。

---

## 0. 这套文档是什么

**Runtime Bible 是"造什么"。**
**Execution Plan 是"怎么用 AI 把它造出来。"**

这套文档解决一个具体问题：

> 我们有 19,445 行工业级 Spec。
> 现在要把它实施成产品。
> 在 **AI Native 时代**，
> 怎样用 Claude Opus / Sonnet / DeepSeek / Haiku / Human
> 这套组合，
> 以**最低成本、最高速度、零架构污染**实施？

---

## 1. 文档结构

```
engineering_execution/
├── README.md                              ← 本文件（导航 + 心智模型）
├── EXECUTION_PLAN.md                      ← 主文档：9 大输出（理论框架）
├── PRACTICAL_MODEL_GUIDE.md               ← ★ 实操手册：每步用什么模型 + Prompt 模板
├── AI_MODEL_ROUTING.md                    ← 速查：每类任务用哪个模型
├── HUMAN_REVIEW_CHECKLIST.md              ← 速查：人工 review 边界
├── SPEC_DRIVEN_WORKFLOW.md                ← 速查：每天工作流程
├── ENGINEERING_LAWS.md                    ← 速查：不可违反的法则
└── CLAUDE_CODE_AGENTS.md                  ← 速查：subagent 配置建议
```

### 阅读顺序

| 角色 | 顺序 |
|------|------|
| **Engineering Director / Tech Lead** | README → EXECUTION_PLAN 全文 |
| **AI Coding Session 开始前** | ENGINEERING_LAWS → SPEC_DRIVEN_WORKFLOW → AI_MODEL_ROUTING |
| **Code Reviewer** | HUMAN_REVIEW_CHECKLIST → AI_FAILURE_MODES (EXECUTION_PLAN §8) |
| **新加入工程师** | README → EXECUTION_PLAN §1 §5 §9 |

---

## 2. 核心心智模型

### 2.1 AI Coding ≠ Vibe Coding

```
Vibe Coding:
  - 给 AI 一句话, 让它自由发挥
  - 期望 AI 理解所有 context
  - 接受不一致的输出
  - 不可复现
  - 适用: 一次性脚本

AI Coding (本项目使用):
  - 给 AI 精确的 Spec + 精确的任务
  - Spec 是 source of truth
  - 输出可验证、可复现
  - 适用: 工业级产品
```

### 2.2 模型能力分级 ≠ 通用智能

```
我们不基于"哪个模型最聪明"分配任务，
而基于"哪种任务需要哪种能力"。

任务的关键维度:
  1. 决策复杂度 (这个决定影响多深)
  2. Context 跨度 (要看多少 spec)
  3. Personality sensitivity (是否触及"她")
  4. 可验证性 (输出能否被 test 验证)
  5. 后果不可逆性 (做错了 rollback 成本)
```

### 2.3 Spec-First, Model-Routed

```
所有任务的入口:
  1. 任务来自一个 Spec 的明确章节
  2. 没有 Spec 的任务必须先写 Spec (Opus/Human)
  3. 任务被 routing 到合适的 Model
  4. Model 输出经过 verification gate
  5. 通过 → merge; 不过 → 回到 routing 决策
```

### 2.4 Cost = Context × Calls × Model Tier

```
降低成本的三个杠杆:

杠杆 1: Context size
  - 不要把整个 Runtime Bible 塞给 Haiku
  - 用 Read offset / grep 取相关章节
  - Subagent 隔离 context

杠杆 2: Call frequency
  - 不要让 Sonnet 重复推理同样的事
  - Cache prompt prefix (Anthropic prompt caching)
  - 一次 plan, 多次 execute

杠杆 3: Model tier
  - 90% boilerplate 可以 Haiku/DeepSeek
  - 10% architectural 必须 Opus
  - 默认不要用 Opus 写代码（除非 architectural）
```

---

## 3. 三层职责模型

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: HUMAN                                             │
│  - "她" 的声音 / 灵魂相关                                    │
│  - Safety threshold tuning                                  │
│  - Architecture decisions                                   │
│  - Final QA on personality                                  │
│  时间投入: 30%                                                │
│  价值: 不可替代                                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: OPUS (顶级模型)                                    │
│  - 复杂架构决策                                              │
│  - Cross-subsystem 集成设计                                 │
│  - Critical bug investigation                               │
│  - Prompt template design                                    │
│  时间投入: 10%                                                │
│  Cost: 高（但被 spec-driven 隔离）                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: SONNET (主力)                                      │
│  - Subsystem 实现（按 spec）                                 │
│  - 复杂 refactor                                            │
│  - Multi-file 编辑                                          │
│  - Code review                                              │
│  - Test design                                              │
│  时间投入: 50%                                                │
│  Cost: 中（主要成本来源）                                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: HAIKU / DEEPSEEK / CONTINUE                       │
│  - Boilerplate generation                                    │
│  - Unit test scaffolding                                    │
│  - Schema migration drafts                                  │
│  - Type annotations                                         │
│  - Import organization                                      │
│  - Documentation drafts                                     │
│  时间投入: 10% (但产生 60% 代码)                              │
│  Cost: 极低                                                  │
└─────────────────────────────────────────────────────────────┘

总成本构成 (预估):
  Opus: 10% 任务 × 高单价 = 30% 总成本
  Sonnet: 50% 任务 × 中单价 = 60% 总成本
  Haiku/DeepSeek: 40% 任务 × 低单价 = 10% 总成本
  Human: 不算入 LLM 成本
```

---

## 4. 关键文档之间的关系

```
┌────────────────────────────────────────────────────────────┐
│ runtime_specs/  (Runtime Bible)                             │
│   - 系统要做成什么样                                          │
│   - 数据结构、接口、算法                                      │
│   - 19,445 行 工业级 spec                                     │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           │ AI Coding 时引用
                           ▼
┌────────────────────────────────────────────────────────────┐
│ engineering_execution/ (Execution Bible)                    │
│   - 怎样用 AI 把上面造出来                                    │
│   - 模型路由、人工边界、防漂移                                 │
│   - 本文档                                                   │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           │ 落地为代码
                           ▼
┌────────────────────────────────────────────────────────────┐
│ backend/heart/ (Implementation)                             │
│   - 8 个 subsystem 的实际代码                                │
│   - 严格遵守 runtime_specs                                    │
│   - 严格遵守 engineering_execution                            │
└────────────────────────────────────────────────────────────┘
```

---

## 5. 三个不可妥协的原则（必须刻在脑子里）

### 原则 1: Spec is Truth
```
代码 ≠ Spec 时, Spec 永远胜出.
  - 要么修代码
  - 要么发起 RFC 修 Spec

绝不允许:
  - "代码这样写了，Spec 跟着改"
  - "AI 写的，应该是对的"
```

### 原则 2: AI 永远不接触"她"
```
任何触及角色灵魂的事:
  - Soul Spec 内容
  - voice_dna patterns
  - Anti-pattern lists
  - Care Path responses
  - Anniversary content

→ 100% HUMAN (Layer 3)

AI 只能在被 Spec 框定的边界内做工程实现.
```

### 原则 3: 成本可观测，质量可验证
```
每个 AI 调用必须:
  - 记录 model + tokens (cost tracking)
  - 输出可被 test 验证 (no vibe checking)
  
每周 review:
  - 成本是否在预算内
  - drift 是否在阈值内
```

---

## 6. 进入 Execution Plan 前的检查清单

在开始任何 AI 协同开发前，确认：

- [ ] 已读完整套 `runtime_specs/`
- [ ] 已读完整套 `engineering_execution/`
- [ ] 团队都签字承认 Spec-First 原则
- [ ] AI 模型 API keys 配置完成
- [ ] Repository 按 EXECUTION_PLAN §6 结构搭建
- [ ] CI 验证 hooks 就位
- [ ] Cost tracking 就位
- [ ] Human review boundaries 团队达成共识

---

**下一步**: 阅读 [`EXECUTION_PLAN.md`](./EXECUTION_PLAN.md)
