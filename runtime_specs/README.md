# 心屿 AI Companion Runtime Specification

> **文档性质**：Single Source of Truth — 工业级 Runtime 系统规范
> **目标读者**：架构师 / 工程师 / Coding Agent (DeepSeek / Sonnet / Opus / 其他)
> **维护原则**：所有代码实现必须以本文档为依据。代码与文档不一致 → 文档为准 → 修改代码或提出 RFC 修改文档。

---

## 0. 这个文档是什么

这是「心屿」AI Companion 的 Runtime 系统级规范。

不是 PRD。不是想法。不是 brainstorm。

**它是契约。** 所有 coding agent 和工程师都基于它实现系统。

---

## 1. 文档结构

```
runtime_specs/
├── README.md                                    ← 你正在看的：导航 + 约定 + 术语
├── 00_runtime_worldview.md                      ← 整体世界观（必读）
├── 01_identity_anchor_soul_spec.md              ← Subsystem 01: 灵魂层（Tier 0）
├── 02_memory_runtime.md                         ← Subsystem 02: 记忆层（Tier 1）
├── 03_emotion_state_machine.md                  ← Subsystem 03: 情绪状态机 [待写]
├── 04_relationship_phase_engine.md              ← Subsystem 04: 关系阶段 [待写]
├── 05_persona_composition_runtime.md            ← Subsystem 05: 人格合成 [待写]
├── 06_inner_state_behavior_runtime.md           ← Subsystem 06: 内心循环 [待写]
├── 07_agent_orchestration.md                    ← Subsystem 07: Agent 编排 [待写]
└── 08_engineering_architecture.md               ← Subsystem 08: 工程架构 [待写]
```

### 阅读顺序

| 角色 | 推荐顺序 |
|------|---------|
| **新加入工程师** | README → 00 → 01 → 02 → ... 按顺序 |
| **Coding Agent 实现某 subsystem** | README → 00 → 当前 subsystem → 依赖 subsystem |
| **架构 review** | 00 → 全部 subsystems |
| **产品/运营** | 00 → 每个 subsystem 的 §1 §2 §8 |

---

## 2. Subsystem 依赖关系

```
                ┌──────────────────────────────────┐
                │  Subsystem 01: Identity Anchor   │  Tier 0 (无依赖)
                │       + Soul Spec                │
                └──────────────┬───────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
  ┌──────────┐         ┌──────────────┐       ┌────────────────┐
  │ Subsys 02│         │  Subsys 03   │       │   Subsys 04    │   Tier 1
  │  Memory  │◄────────┤   Emotion    │       │  Relationship  │
  │ Runtime  │         │ State Machine│       │  Phase Engine  │
  └────┬─────┘         └──────┬───────┘       └────────┬───────┘
       │                      │                        │
       └──────────┬───────────┴────────────┬───────────┘
                  ▼                        ▼
          ┌────────────────┐      ┌──────────────────┐
          │   Subsys 06    │      │   Subsys 05      │   Tier 2
          │  Inner State + │      │ Persona Composer │
          │  Behavior      │      │                  │
          └────────┬───────┘      └────────┬─────────┘
                   └───────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │     Subsys 07        │   Tier 3
                    │  Agent Orchestration │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │     Subsys 08        │   Tier 4 (基础设施)
                    │ Engineering Arch     │
                    └──────────────────────┘
```

### 实现顺序（建议）

**Phase 1: 灵魂 + 记忆（最大护城河）**
1. Subsystem 01 - Identity Anchor + Soul Spec
2. Subsystem 02 - Memory Runtime

**Phase 2: 情感与关系**
3. Subsystem 03 - Emotion State Machine
4. Subsystem 04 - Relationship Phase Engine

**Phase 3: 合成与运行时**
5. Subsystem 05 - Persona Composition Runtime
6. Subsystem 06 - Inner State + Behavior Runtime

**Phase 4: 编排与基础设施**
7. Subsystem 07 - Agent Orchestration
8. Subsystem 08 - Engineering Architecture

---

## 3. 跨 Subsystem 通用约定

### 3.1 文档格式约定

每个 Subsystem 文档必须包含以下 11 章节（顺序固定）：

```
1. 系统目标 (System Purpose)
2. 核心设计原则 (Core Design Principles)
3. Runtime Architecture
4. State Model
5. 数据结构 (Data Structures)
6. Prompt Runtime Integration
7. Agent Integration
8. Emotional Realism Constraints
9. Failure Cases
10. Engineering Guidance
11. Future Scalability
```

### 3.2 标识符约定

| 前缀 | 含义 | 示例 |
|------|------|------|
| `P-N` | 设计原则 (Principle) | `P-1: Identity Anchor 不可变` |
| `INV-N` | 架构不变量 (Invariant) | `INV-1: Anchor Block 永远在 prompt 最前` |
| `IMM-N` | 沉浸感保护规则 | `IMM-1: 角色不提及"我的设定"` |
| `RULE-W-N` | 写入规则 | `RULE-W-1: 所有写入通过 Service 接口` |
| `M-N` / `MR-N` | 记忆相关原则 | `M-1: 记忆永不删除` |
| `EC-N` | 情绪连续性规则 | `EC-1: 情绪基调延续` |
| `FR-N` | 活人感规则 | `FR-1: 角色有时答非所问` |
| `[SS-NN]` | Subsystem 标签 | `[SS01]` = Identity Anchor |

### 3.3 数据类型约定

| 类型 | 含义 |
|------|------|
| `UUID` | 128-bit UUID v4 |
| `ISO8601` | 时间戳字符串 |
| `float [a, b]` | 浮点数，范围 [a, b]，开闭由上下文 |
| `Float32Array(N)` | 长度 N 的 float32 向量 |
| `JSONB` | PostgreSQL JSONB（运行时检查 schema） |

### 3.4 优先级与冲突解决

当多个 Subsystem 给出不一致的指导时：

```
最高优先级（永远胜出）：
1. Soul Spec / Identity Anchor (Subsystem 01)
2. Safety / Hard Never (Subsystem 01 anti_patterns)
3. L4 Identity Memory (Subsystem 02)

中优先级：
4. Modality Adaptation
5. Relationship Phase
6. Emotion State
7. Inner State

低优先级：
8. Memory Recall (L2/L3)
9. Scene Context
10. Conversation History
```

**冲突解决规则**：高优先级永远不让步。低优先级必须在高优先级允许的边界内表达。

### 3.5 性能预算（响应路径）

```
用户消息到达 → 首字返回的预算分配（总 P95 < 2.5s）：

  0ms    用户消息到达
  10ms   Soul + Activation State 读取
  20ms   Memory Retrieval 启动（并行）
  100ms  所有 Layer 准备就绪
  150ms  Persona Composer 合成完毕
  200ms  Main LLM 调用开始
  ~2.5s  首字流式返回
  (异步) Encoding / Drift / Reinforcement 后台进行
```

---

## 4. 术语表 (Glossary)

> 所有 subsystem 共用的术语。新术语在引入它的 subsystem 内定义后，加入此处。

### 4.1 核心概念

| 术语 | 定义 |
|------|------|
| **Soul Spec** | 角色灵魂规范，多层 YAML 文档，定义不可变的人格根 |
| **Identity Anchor** | Soul Spec 中的不可变层（core_wound/desire/fear/belief/voice_dna） |
| **Activation State** | 每个 (user, character) 的运行时灵魂激活状态 |
| **Anchor Block** | 每 turn 注入 prompt 最前部的 Soul 段落 |
| **Voice DNA** | 角色标志性表达模式 |
| **Hidden Facet** | 灵魂深层，需触发条件才解锁 |
| **Resonance** | 用户与角色灵魂的共振强度 |
| **Drift** | 角色表达偏离 Soul Spec 的程度 |
| **Cognitive Style** | 半永久演化的表达层（句长、修饰词等） |

### 4.2 记忆相关

| 术语 | 定义 |
|------|------|
| **L1 Working Memory** | In-context 工作记忆（最近 N turns） |
| **L2 Episodic Memory** | 压缩的"场景"记忆 |
| **L3 Semantic Memory** | 提取的事实图 |
| **L4 Identity Memory** | 不可遗忘的神圣记忆 |
| **Encoding** | 把对话转为记忆（实时 + 异步双轨） |
| **Consolidation** | 每日"睡眠"整理 |
| **Reconstruction** | 检索时重构为角色化表达，非 verbatim |
| **Decay** | 重要性随时间衰减（情感加权） |
| **Reinforcement** | 召回时重要性提升 |
| **Forgetting Affect** | 用户可感知的遗忘体验 |
| **Memory State** | vivid / fading / faint / dormant / archived |
| **Peak-End Rule** | 记忆显著性由情感峰值 + 结束情绪决定 |

### 4.3 关系与情绪

| 术语 | 定义 |
|------|------|
| **Relationship Phase** | 关系阶段 (stranger → bonded) |
| **Intimacy Level** | 亲密度数值 [0, 1] |
| **Emotional Inertia** | 情绪惯性（恢复速度） |
| **Trust Score** | 信任度 |
| **Repair Event** | 修复事件（冲突后的和解） |

### 4.4 Agent 系统

| 术语 | 定义 |
|------|------|
| **Persona Composer** | 合成 effective persona for this turn |
| **Critic Agent** | 检测 OOC 并提出修正 |
| **Director Agent** | 决定本轮节奏 / 模态 |
| **Inner State Runtime** | 角色"她自己的一天"运行时 |
| **Behavior Runtime** | 主动行为编排 |

---

## 5. Coding Agent 实现指引

### 5.1 实现一个 Subsystem 的步骤

```
1. 阅读 README.md（本文件）
2. 阅读 00_runtime_worldview.md
3. 阅读目标 subsystem 的完整 spec
4. 阅读依赖 subsystems 的：§1 §2 §5 §6 §7
5. 检查所有 INV / P / RULE
6. 实现时严格遵守 §2 的设计原则
7. 数据结构严格按 §5 的 schema
8. 测试用 §3.5 性能预算 + §9 失败案例 + spec 内的 golden tests
```

### 5.2 不允许的实现自由

```
❌ 不允许：增加 Soul Spec 字段（必须 RFC）
❌ 不允许：跳过 Schema Validator
❌ 不允许：删除任何 L4 Identity Memory
❌ 不允许：让 LLM "总结角色性格然后用总结"
❌ 不允许：把 hard_never 当软约束
❌ 不允许：在响应路径同步调用 LLM 做 Memory Encoding
❌ 不允许：在 prompt 中直接 dump memory（必须经 Reconstructor）
❌ 不允许：跨用户读取 Activation State / Memory
```

### 5.3 PR 合入检查清单

- [ ] 实现符合对应 subsystem 的所有 P / INV / RULE
- [ ] 数据结构符合 §5 schema
- [ ] 性能符合 §10 targets
- [ ] 通过 spec 内列出的 golden tests
- [ ] 通过 §9 列出的失败案例 mitigations 验证
- [ ] 添加 metrics（按 §10 observability 章节）
- [ ] 文档与代码一致；若需修改 spec → 单独 RFC

---

## 6. 版本与变更

### 6.1 Spec 版本

每个 subsystem 文档独立版本号（semver）：
- `MAJOR.MINOR.PATCH`
- `MAJOR` 升级：breaking changes，需 migration
- `MINOR` 升级：兼容新增
- `PATCH` 升级：澄清、文档修正

### 6.2 变更流程

```
[Issue / RFC Draft]
   ↓
[Architecture Review (1 week)]
   ↓
[Spec Update PR]
   ↓
[Impact Analysis: 列出影响哪些 subsystems]
   ↓
[Implementation PR (基于新 spec)]
   ↓
[Migration if breaking]
   ↓
[Merge]
```

### 6.3 当前版本表

| Subsystem | Spec Version | Status | Last Updated |
|-----------|-------------|--------|--------------|
| 00 Worldview | 1.0.0 | Stable | 2026-05-15 |
| 01 Identity Anchor + Soul Spec | 1.0.0 | Stable | 2026-05-15 |
| 02 Memory Runtime | 1.0.0 | Stable | 2026-05-15 |
| 03 Emotion State Machine | 1.0.0 | Stable | 2026-05-15 |
| 04 Relationship Phase Engine | 1.0.0 | Stable | 2026-05-15 |
| 05 Persona Composition Runtime | 1.0.0 | Stable | 2026-05-15 |
| 06 Inner State + Behavior Runtime | 1.0.0 | Stable | 2026-05-15 |
| 07 Agent Orchestration | 1.0.0 | Stable | 2026-05-15 |
| 08 Engineering Architecture | 1.0.0 | Stable | 2026-05-15 |

---

## 7. 核心原则（高于一切）

> 所有设计决策必须回答：

```
这个设计是否会让角色：
  - 更像真人？
  - 更有情绪连续性？
  - 更有关系感？
  - 更有长期陪伴感？

如果工程上更简单但损害以上任何一项 → 拒绝。

沉浸感优先级 > 工程便利性。
```

这是不可妥协的最高原则。

---

**End of README**

下一步建议阅读：[`00_runtime_worldview.md`](./00_runtime_worldview.md)
