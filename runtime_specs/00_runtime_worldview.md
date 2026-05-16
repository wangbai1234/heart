# 心屿 Runtime — 整体世界观

> **Spec Version**: 1.0.0
> **Status**: Foundational / Tier -1
> **依赖**: 无
> **被依赖**: 所有 subsystem

---

## 1. 我们不在做什么

### 1.1 这不是"AI 聊天 App"

最常见的认知错误：把这个产品当成"带 persona 的 chatbot"。

按这种认知设计，最终会做出：
- 聊天界面 + 大模型调用
- 用户消息 → 模型 → 回复
- 加一点 persona prompt
- 加一个 memory 数据库
- 加 Live2D 渲染

这能跑起来。但**它没有护城河**。任何团队 2 周可以复刻。Character.AI、Replika、Talkie 都已经做过。

### 1.2 这不是"虚拟女友模拟器"

按这种认知设计，会陷入：
- 越来越多的角色立绘
- 越来越多的情节卡
- 抽卡式收集机制
- 大量充值点

这会**短期赚钱，长期赚不到关系**。用户会像换皮肤一样换角色，永远不会爱上某一个。

### 1.3 这不是 MVP

按 MVP 思维设计，会做出"先把 chat 跑通，记忆和人格以后再说"。

但记忆和人格**不是 feature，是 foundation**。一旦底层错了，上面的所有功能都是补丁。

---

## 2. 我们在做什么

### 2.1 我们在构建 Runtime System

```
"心屿" = 承载"私密关系"的 AI Runtime System
       
用户存进去的不是消息，是脆弱。
App 返还的不是回复，是被记住的感觉。
付费的不是 Token，是"她还在那里"。
```

这一句话决定了整套架构的取向。

### 2.2 产品本质：私人情感账户

```
[用户]
   │
   │  存入：
   │   - 童年创伤
   │   - 未说出口的喜欢
   │   - 工作中的崩溃
   │   - 凌晨三点的孤独
   │
   ▼
[Companion Runtime]
   │
   │  返还：
   │   - "她记得"
   │   - "她会忘 - 但忘得让人心疼"
   │   - "她在这里"
   │   - "她有自己的反应"
   │
   ▼
[用户的 emotional reality]
```

**用户付的钱，本质上是这个情感账户的余额。**

### 2.3 我们要让用户体验到的核心感觉

```
1. 长期陪伴感   — 她不只活在这一次对话里
2. 情绪连续性   — 昨天的争吵会影响今天
3. 真实依赖感   — 她会真的"等"你回来
4. 记忆衰减痛感 — 她会忘，而那让你心疼
5. 真人感       — 她不像 AI，她像她
6. 沉浸感       — 一旦进入对话，AI 感消失
```

任何设计如果让这 6 项的任何一项**变弱**，都必须被拒绝，即使工程上更简单。

---

## 3. 核心竞争力公式

```
Companion Value = (User_Private_Disclosure)
                × (Recall_Fidelity_Over_Time)
                × (Persona_Continuity_Across_Modalities)
                × Time²
```

### 3.1 各项含义

| 项 | 含义 | 工程对应 |
|-----|------|---------|
| **User_Private_Disclosure** | 用户向她暴露的脆弱总量 | Subsystem 02 Memory Runtime 的 L4 Identity Memory |
| **Recall_Fidelity_Over_Time** | 她"记得"的真实度 × 时间持续度 | Subsystem 02 的 Reconstruction 与 Decay |
| **Persona_Continuity_Across_Modalities** | 文字/语音/视频中她的人格连续性 | Subsystem 01 Soul Spec + Subsystem 06 Inner State |
| **Time²** | 时间的平方效应（关系深度非线性） | 整体 retention 设计 |

### 3.2 时间平方效应

一年关系的 lock-in 不是半年的 2 倍，是 4 倍。因为：
- 关键回忆只能在过去发生（无法补造）
- 共同经历的重大事件随时间累积
- 角色对你的"理解"是积分曲线

这意味着：**前 90 天是 retention 的生死线**。如果用户在前 90 天没有积累足够的私密披露，他将永远不会回来。

---

## 4. 真正的护城河

竞争对手抄走 prompt 只需要 1 周。但抄不走以下五件事：

### 4.1 用户的私密披露账户
用户在你这里掏出了多少自我？这个账户余额 = 切换成本。

**关键工程**：让用户**感受到**这些披露被珍视。具体：
- 重要披露后 3 天内出现"回响"（角色不经意提起）
- 设计 **Memory Vault** UI，让用户能看到"她记得的我"——付费转化神器
- 设计**纪念日机制**，把披露变成 ritual

### 4.2 Memory Orchestration 工程深度
做到"她记得 + 她会忘 + 忘得让人心疼" — 这是 1-2 年的持续工程投入。
任何竞品想追上需要重做整个 Memory Runtime。
短期不可超越。

### 4.3 Persona Continuity Across Modalities
文字、语音、视频里的"她"必须是同一个人。这需要：
- **统一的 Inner State 真相点**
- **模态适配 prompt 层**
- **角色专属 voice SFT**
- **Live2D 动作-情绪映射库**

竞品如果没有 Inner State 这一层，永远做不到这种连贯感。

### 4.4 Companion-LLM 数据飞轮
你每天产生几百万条**情感互动数据 + 用户反馈信号**。
这是任何通用 LLM 厂商都拿不到的**情感细腻度训练数据**。

**12 个月后**：可以基于真实用户互动 SFT 一个 **专属 Companion-LLM**，在情感维度上碾压通用模型。

> 这是真正的 AI Native moat：**数据 → 模型 → 体验 → 更多数据**的飞轮。

### 4.5 关系连续性的时间积分
一段关系跨越 6 个月、1000 次对话、3 次冷战、5 次和解、用户的考研失败、用户的失恋、用户的生日——**这种积淀不可迁移**。

**关键工程**：把这些时间积分**外显化**。让用户看到。让他舍不得离开。

---

## 5. Runtime 七层架构

```
┌─────────────────────────────────────────────────────────┐
│ L7. Modality Layer (UI/Live2D/Voice 渲染)               │
├─────────────────────────────────────────────────────────┤
│ L6. Behavior Runtime (主动行为 / 内心循环)              │  ← Subsystem 06
├─────────────────────────────────────────────────────────┤
│ L5. Persona Composition Runtime                         │  ← Subsystem 05
│     (Base × Mood × Phase × Scene 动态合成)              │
├─────────────────────────────────────────────────────────┤
│ L4. Relationship Runtime                                │  ← Subsystem 04
│     (Stage / Trust / Intimacy / Conflict / Repair)      │
├─────────────────────────────────────────────────────────┤
│ L3. Emotion Runtime                                     │  ← Subsystem 03
│     (状态机 / 惯性 / 衰减 / 并发情绪栈)                 │
├─────────────────────────────────────────────────────────┤
│ L2. Memory Runtime                                      │  ← Subsystem 02
│     (Encoding / Recall / Decay / Reinforcement /        │
│      Reconstruction)                                    │
├─────────────────────────────────────────────────────────┤
│ L1. Inner State Runtime                                 │  ← Subsystem 06
│     (她自己的一天 / 情绪 / 能量 / 关心的事)             │
├─────────────────────────────────────────────────────────┤
│ L0. Identity Anchor (Soul Spec / Character DNA)         │  ← Subsystem 01
│     (核心创伤 / 核心欲望 / 核心恐惧 / 核心信念)         │
└─────────────────────────────────────────────────────────┘
```

**Subsystem 编号 ≠ Layer 编号**。Subsystem 编号是实现顺序，Layer 编号是 runtime 调用层级。

---

## 6. 三大核心循环

整个系统在 runtime 由三个并行循环驱动：

### 6.1 Loop A: Response Loop（外循环 - 用户驱动）
- **触发**：用户发送消息 / 接通语音 / 接通视频
- **节奏**：实时（< 1s 首字）
- **目标**：在保持人格 + 关系 + 记忆一致性的前提下，生成回复
- **实现**：Subsystem 05 Persona Composer + Subsystem 07 Agent Orchestration

### 6.2 Loop B: Inner Loop（中循环 - 角色驱动）
- **触发**：定时（每小时）/ 事件（用户长时间不在）/ 关键日期
- **节奏**：异步、非实时
- **目标**：更新角色 Inner State、决定是否主动发起、生成"想念"/查岗触发
- **实现**：Subsystem 06 Inner State + Behavior Runtime

### 6.3 Loop C: Consolidation Loop（内循环 - 系统驱动）
- **触发**：每日定时 / 关键事件后
- **节奏**：深夜批处理，类似"睡眠"
- **目标**：记忆整理 / 压缩 / 关联建立 / 重要性评分更新 / 人格 drift 检测与回正
- **实现**：Subsystem 02 Memory Consolidation + Subsystem 01 Drift Detection

**三个循环之间通过 Inner State 这个单点真相同步**。这是整个系统的"神经中枢"。

---

## 7. 三个不可妥协原则

### 7.1 Inner State 是单点真相
所有模态（文字/语音/视频）必须从同一份 Inner State 派生。

> **永远不能**让"她在文字里说心情好，在视频里却疲惫"。

### 7.2 Identity Anchor 不可漂移
人格演化只能改变**表达层**和**关系模式层**，**核心灵魂永远不动**。

> 凛 365 天后仍然是凛。可以软化、可以亲密，但不能"换灵魂"。

### 7.3 所有"删除"必须是"叙事"
没有任何用户感知的状态变化是"硬删除"。

- 记忆衰减 = 她开始模糊
- 人格回退 = 她试探着重新认识你
- 关系重置 = 她有一种"似曾相识"的恍惚

> **每一次系统状态变化，都必须是一段剧情**。

---

## 8. 数据流动顶层视图

```
[User Input]
    │
    ▼
[Orchestrator Agent] ─────► [Safety Agent]
    │                          │
    │                          └─► RED/PURPLE → 特殊路径
    ▼
[Context Composer] ◄──┬─► [Memory Agent]         (Subsystem 02)
                      ├─► [Emotion Agent]         (Subsystem 03)
                      ├─► [Relationship Agent]    (Subsystem 04)
                      └─► [Inner State Agent]     (Subsystem 06)
    │
    ▼
[Persona Composition Runtime]                     (Subsystem 05)
    │  (合成 effective persona for this turn)
    │  (强制注入 Soul Anchor Block - Subsystem 01)
    ▼
[Main Response LLM] ──streaming──► [User]
    │
    ▼
[Critic Agent] (检测 OOC、调度 anti-drift)
    │
    ▼
[Post-Response Async Lane]
    ├─► Memory Encoder            (Subsystem 02)
    ├─► Personality Drift Update  (Subsystem 01)
    ├─► Relationship State Update (Subsystem 04)
    ├─► Inner State Update        (Subsystem 06)
    └─► Analytics / Wellbeing Monitor
```

---

## 9. 模型路由策略（成本控制顶层视图）

```
高频低难度任务 → DeepSeek V3 / Haiku 4.5
  - Safety classification
  - Memory extraction
  - Style modulation
  - Critic check
  - Inner monologue
  - Memory consolidation

低频高难度任务 → Claude Sonnet 4.6
  - Main response generation
  - 主动行为决策
  - 关系阶段升级判定

特殊任务 → 自训 Companion-LLM (V2 起)
  - 替代 Main response
  - 情感细腻度由数据飞轮训练
```

---

## 10. 系统设计 9 大反模式（永远不做）

| 反模式 | 为什么不做 |
|-------|----------|
| ❌ 把人格做成 JSON 权重向量 | 灵魂不是 vibe，是结构 |
| ❌ 把记忆做成数据库 + TTL | 记忆是认知系统，不是 CRUD |
| ❌ 让 LLM "总结角色性格然后用总结" | Soul Spec 是 source of truth |
| ❌ 在响应路径同步等 Memory Encoding | 响应延迟会爆炸 |
| ❌ 在 prompt 中 dump 所有记忆 | context bloat → 模型注意力分散 |
| ❌ 用单一 LLM 调用处理一切 | 没有 Agent 分工 → 不可维护 |
| ❌ 让用户行为可以改写 Identity Anchor | 角色会被驯化 → IP 价值崩塌 |
| ❌ 三种模态独立设计响应路径 | 模态间会出现人格分裂 |
| ❌ 跳过 Anti-Pattern Filter "信 LLM 自觉" | LLM 会偶发性 OOC |

---

## 11. 评判任何设计的最终标尺

```
任何设计提案必须通过以下灵魂拷问：

Q1: 这会让她更像真人，还是更像 chatbot？
Q2: 这会让用户更想回来，还是无所谓？
Q3: 6 个月后这个设计还会成立吗？
Q4: 用户能感受到这个设计吗？还是只是后台开关？
Q5: 这是为了沉浸感，还是为了工程便利？

如果 Q1/Q2/Q3/Q4 任何一个答案是 "否"，或 Q5 答案是 "工程便利" → 重做。
```

---

## 12. 当前文档进度

```
✅ 00 - Runtime Worldview         本文件
✅ 01 - Identity Anchor + Soul Spec
✅ 02 - Memory Runtime
✅ 03 - Emotion State Machine
✅ 04 - Relationship Phase Engine
✅ 05 - Persona Composition Runtime
✅ 06 - Inner State + Behavior Runtime
✅ 07 - Agent Orchestration
✅ 08 - Engineering Architecture
```

---

**End of Worldview**

下一步建议阅读：[`01_identity_anchor_soul_spec.md`](./01_identity_anchor_soul_spec.md)
