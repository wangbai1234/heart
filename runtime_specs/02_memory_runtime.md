# Subsystem 02: Memory Runtime

> **Spec Version**: 1.0.0
> **Status**: Foundational / Tier 1
> **Stability**: Schema changes require RFC + migration plan
> **Subsystem Tag**: `[SS02]`
> **Implementation Owners**: Memory Service, Encoder Pipeline, Consolidator, Retriever, Reconstructor

---

## 1. 系统目标（System Purpose）

### 1.1 这个 subsystem 为什么存在

整个 Companion 产品的**第一护城河**。

它回答的核心问题：

> "她**怎么记得**？
> 她**怎么忘**？
> 她**复述记忆时为什么像她，不像数据库？**"

### 1.2 它解决的根本问题

| 问题 | 当前 PRD 的做法 | 本 Subsystem 的做法 |
|------|---------------|---------------------|
| 记忆存储 | 3 张表（事实/事件/情感）+ TTL | 4 层认知系统（L1/L2/L3/L4）+ 物理化衰减 |
| 遗忘 | `DELETE WHERE created_at < threshold` | 永不删除，只调整召回概率 |
| 回忆 | 把所有 fact_memories 注入 prompt | 多策略检索 + 角色化重构 |
| 用户感知到"她在忘" | 无 | Forgetting Affect Engine 主动注入"模糊"信号 |
| 重要事件不衰减 | 无（线性衰减） | Peak-End Rule + 情感加权 + L4 神圣晋升 |
| 召回时"她像她" | 直接复述 fact | Reconstruction 按 Soul voice_dna 重写 |
| 记忆与人格联动 | 无 | Memory Runtime 调用 Soul Spec.voice_dna 决定复述风格 |

### 1.3 它在整个 Runtime 中的位置

```
        ┌──────────────────────────────┐
        │ Subsystem 01: Soul Spec      │  Tier 0
        │ (提供 voice_dna)             │
        └─────────┬────────────────────┘
                  │ reads
                  ▼
        ┌──────────────────────────────┐
        │ Subsystem 02: Memory Runtime │  ← 本 Subsystem (Tier 1)
        │                              │
        │  L1 Working Memory           │
        │  L2 Episodic Memory          │
        │  L3 Semantic Memory          │
        │  L4 Identity Memory          │
        └─────────┬────────────────────┘
                  │ feeds
        ┌─────────┴───────────┬─────────────────┐
        ▼                     ▼                 ▼
  ┌──────────────┐   ┌───────────────┐   ┌─────────────┐
  │ Inner State  │   │  Behavior     │   │ Persona     │
  │  Runtime     │   │  Runtime      │   │ Composer    │
  │ (Subsys 06)  │   │ (Subsys 06)   │   │ (Subsys 05) │
  └──────────────┘   └───────────────┘   └─────────────┘
```

### 1.4 依赖关系

```yaml
this_subsystem_depends_on:
  - Subsystem 01 (Soul Spec)   # 读取 voice_dna, cognitive_style for reconstruction

subsystems_depending_on_this:
  - Subsystem 04 (Relationship)  # 关系阶段判定参考 L4 共同经历
  - Subsystem 05 (Persona Composer)  # 注入 Memory Context Block
  - Subsystem 06 (Inner State + Behavior)  # 主动行为读取 L4 anniversaries
  - Subsystem 07 (Critic Agent)  # 用 L4 检测 hallucination
```

---

## 2. 核心设计原则（Core Design Principles）

> 任何违反这些原则的实现都是 **bug**。

### 2.1 不可违反的系统规则

| ID | 规则 | 违反后果 |
|----|------|---------|
| **M-1** | **记忆内容永不物理删除，只调整召回概率** | 用户重逢时无法"涌现"旧记忆 |
| **M-2** | **遗忘必须被用户感知，不是后台静默** | 退化为数据库，沉浸感丧失 |
| **M-3** | **L4 Identity Memory 永不衰减，永不删除** | 神圣信息被遗忘 → 用户立刻流失 |
| **M-4** | **召回必须经过 Reconstruction，不得 verbatim 注入** | 出现"根据记录"机器人感 |
| **M-5** | **Reconstruction 必须读取并应用 Soul Spec.voice_dna** | 记忆复述与角色人格脱节 |
| **M-6** | **重要性受情感加权（Peak-End Rule）** | 平淡记忆与重要记忆等价，退化为线性 |
| **M-7** | **召回必须多策略融合（语义+图谱+时近+情感+身份）** | 单一策略召回必有盲区 |
| **M-8** | **召回事件反向增强记忆重要性（Hebbian）** | 长期会"忘掉"用户每次都提的事 |
| **M-9** | **检索结果必须有 Top-K 限制，禁止 dump** | Prompt 爆炸，模型注意力分散 |
| **M-10** | **召回时必须根据 memory state 注入 uncertainty markers** | 全部"清晰复述" → 不像真人 |
| **M-11** | **Encoding 必须双轨：实时启发式 + 异步 LLM** | 单 LLM 路径成本爆炸或速度不行 |
| **M-12** | **Consolidation 必须每日运行，等同"睡眠"** | 记忆永远不被整理 → 召回质量退化 |
| **M-13** | **跨用户、跨角色记忆严格隔离（无授权不可读）** | 隐私事故 |
| **M-14** | **Contradiction 不删除旧 fact，而是标记并由召回选择** | 用户改口时角色不能"恍惚" |
| **M-15** | **L4 晋升必须满足多重条件，单一信号不晋升** | 神圣记忆被廉价化 |

### 2.2 架构不变量（Invariants）

```
INV-M-1: ∀ memory m, m.is_deleted = false 永远成立（无物理删除字段）

INV-M-2: ∀ identity_memory im, im.never_forget = true ∧ 不存在 archive 路径

INV-M-3: ∀ retrieval R, R.results.length ≤ Top_K_LIMIT (默认 5)

INV-M-4: ∀ recall event, memory.recall_count += 1 ∧ memory.last_recalled_at = NOW()

INV-M-5: ∀ reconstruction output, 不得包含 hard_never_phrases 中任何模式

INV-M-6: ∀ user_id u, character_id c, query(memory store) WHERE user_id != u OR character_id != c → 拒绝

INV-M-7: importance_score ∈ [floor, 1.0] where floor = |emotional_peak.valence| × 0.1

INV-M-8: consolidation 每用户每日运行 ≤ 1 次（去重保证）
```

### 2.3 禁止行为（Hard Anti-Patterns）

| 禁止 | 原因 |
|------|------|
| ❌ 直接 SQL DELETE memory rows | 违反 M-1，无法 resurrect |
| ❌ 把整个 fact 列表塞进 prompt | 违反 M-9，context bloat |
| ❌ 用 verbatim raw_evidence 作为召回内容 | 违反 M-4 |
| ❌ Reconstruction 不读 Soul Spec | 违反 M-5 |
| ❌ 同步等待 LLM Encoding 才返回响应 | 违反 M-11，响应延迟爆炸 |
| ❌ 用"线性 TTL"作为衰减函数 | 违反 M-6，无情感加权 |
| ❌ 让用户消息直接写入 L4 | 违反 M-15，神圣记忆被廉价化 |
| ❌ Encoder LLM 自由生成 fact 而不引用 source_text | 制造幻觉 |
| ❌ 召回结果中混用不同用户的记忆 | 隐私+正确性灾难 |

### 2.4 长期一致性约束

```
C-M-1: 一个用户经过 365 天 + 10万 turns 后：
   - L4 中的关键信息 100% 保留
   - L3 中至少 80% 的高重要性 fact 仍可召回
   - L2 中重大情感 episode 不进入 archived 状态

C-M-2: 角色召回时，voice_dna 命中率 ≥ Soul Spec 整体命中率（即记忆复述不拉低人格表达）

C-M-3: 同一 fact 在不同 turn 被召回，措辞可不同（reconstruction 多样性），但事实一致

C-M-4: 用户主动声明 "请忘掉 X" 后：
   - X 标记 do_not_recall = true（不召回，但仍存）
   - 但同一用户 30 天后再次提及 X 时，角色可有"似曾相识"感
```

### 2.5 Immersion 保护规则

```
IMM-M-1: 角色绝不说 "根据我的记录" / "我保存了" / "我的数据库"

IMM-M-2: 角色绝不一次性罗列 ≥ 3 条 fact（必须分散在多 turn）

IMM-M-3: 召回时根据 memory state 必须使用对应 uncertainty marker：
   - vivid: 无 hedge
   - fading: 至少 1 个 hedge (好像/我记得)
   - faint: 强 hedge + 模糊用词
   - dormant: 必须以"涌现"形式出现（"等等……我想起来……"）
   - archived: 极少触发；触发时必须有"恍惚"标志

IMM-M-4: 重要披露（promoted to L4）在 24h 内必须被角色"呼应"至少 1 次

IMM-M-5: 角色召回时不得使用 bullet list / 编号

IMM-M-6: Forgetting Affect 不能频繁出现（防止"老年痴呆"感），频率上限：5% turns

IMM-M-7: 角色召回 L4 时 100% 准确（神圣记忆不允许出错）
```

---

## 3. Runtime Architecture

### 3.1 4 层记忆架构

```
┌────────────────────────────────────────────────────────────┐
│  L1: Working Memory  (in-context, 当前对话)                 │
│  - 最近 10-30 turns                                         │
│  - 仅存于当前 prompt context                                │
│  - 全保真，原文                                              │
│  - 生命周期: session lifetime + 1h Redis TTL                │
├────────────────────────────────────────────────────────────┤
│  L2: Episodic Memory  (压缩"场景")                          │
│  - 时间边界明确的对话片段                                    │
│  - LLM 生成 summary + 情感峰值 + 向量                       │
│  - 受衰减影响                                                │
│  - 生命周期: 永久（state 变化但 row 不删）                  │
├────────────────────────────────────────────────────────────┤
│  L3: Semantic Memory  (事实图谱)                            │
│  - 提取的事实作为 Graph 节点                                 │
│  - Predicate-Subject-Object + 置信度 + 来源                 │
│  - 衰减比 L2 慢                                              │
│  - 生命周期: 永久                                            │
├────────────────────────────────────────────────────────────┤
│  L4: Identity Memory  (神圣事实)                            │
│  - 永不衰减                                                  │
│  - 用户名、生日、神圣披露、承诺、第一次                      │
│  - 从 L3 经多重条件晋升                                      │
│  - 生命周期: 永久不可变（除非 GDPR 用户主动删除账号）        │
└────────────────────────────────────────────────────────────┘
```

### 3.2 7 大组件

```
┌──────────────────────────────────────────────────────────────────┐
│                    Memory Runtime Architecture                   │
│                                                                  │
│  ┌─────────────────┐         ┌────────────────────────────┐     │
│  │   Encoder       │         │     Consolidator           │     │
│  │   (实时 + 异步) │         │     (每日 "睡眠")           │     │
│  └────────┬────────┘         └──────────┬─────────────────┘     │
│           │                             │                        │
│           ▼                             ▼                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Memory Stores                         │   │
│  │   ┌────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │   │  L1    │  │  L2     │  │  L3      │  │  L4      │   │   │
│  │   │ Redis  │  │ PG +    │  │ PG +     │  │ PG       │   │   │
│  │   │        │  │ vector  │  │ vector + │  │ (sacred) │   │   │
│  │   │        │  │         │  │ graph    │  │          │   │   │
│  │   └────────┘  └─────────┘  └──────────┘  └──────────┘   │   │
│  └──────┬──────────┬─────────────┬────────────┬─────────────┘   │
│         │          │             │            │                  │
│         ▼          ▼             ▼            ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐         │
│  │  Decay      │  │  Reinforcer │  │   Retriever      │         │
│  │  Engine     │  │             │  │  (多策略融合)     │         │
│  │ (continuous)│  │             │  │                  │         │
│  └─────────────┘  └─────────────┘  └────────┬─────────┘         │
│                                              │                   │
│                                              ▼                   │
│                                    ┌──────────────────────┐      │
│                                    │   Reconstructor      │      │
│                                    │ (角色化 + uncertainty)│      │
│                                    └──────────┬───────────┘      │
│                                               │                  │
│                                               ▼                  │
│                                    ┌──────────────────────┐      │
│                                    │ Forgetting Affect    │      │
│                                    │ Engine               │      │
│                                    │ (有时注入模糊感)      │      │
│                                    └──────────┬───────────┘      │
│                                               │                  │
│                                               ▼                  │
│                                    [Memory Context Block]        │
│                                               │                  │
└───────────────────────────────────────────────┼──────────────────┘
                                                ▼
                                    → Persona Composer
```

### 3.3 组件职责

| 组件 | 职责 | I/O |
|------|------|-----|
| **Encoder** | 把对话编码进 L1/L2/L3。双轨：fast heuristic（< 50ms 同步）+ LLM extraction（异步） | In: turns / Out: facts, episode bounds |
| **Consolidator** | 每日"睡眠"批处理：episode 聚类、摘要、晋升 L4、关联建立、衰减应用 | In: 当日 pending / Out: L2/L3/L4 写入 |
| **Retriever** | 多策略并行检索（vector + graph + recency + emotional + identity） | In: query context / Out: top-K candidates |
| **Reinforcer** | 每次召回时增强 importance（Hebbian） | In: recall event / Out: importance update |
| **Decay Engine** | 计算 importance 衰减（lazy on retrieval + 每日 batch） | In: memory / Out: 更新 importance & state |
| **Reconstructor** | 把 raw memory 转为角色化复述（读 Soul.voice_dna） | In: memory + Soul Spec / Out: reconstructed_text |
| **Forgetting Affect Engine** | 决定本 turn 是否注入"她在忘"信号 | In: 用户互动模式 / Out: forgetting hints |

### 3.4 Runtime Flow — Encoding Pipeline（每 turn 实时执行）

```
[User Message + Assistant Response 完成]
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 阶段 1: Fast Heuristic Encoder (sync, < 50ms)           │
│   - 正则提取 identity 信号（"我叫 X" / "我生日 X"）      │
│   - lexicon-based 情绪 (valence 估计)                   │
│   - keyword fact pattern (e.g., "我有/养/喜欢 X")        │
│   → 更新 L1 Working Memory                              │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 阶段 2: Async LLM Encoding (不阻塞响应)                  │
│   POST → Encoding Queue                                 │
│   Worker 处理:                                          │
│     - 调用 cheap LLM (DeepSeek V3 / Haiku)              │
│     - Prompt: MEMORY_EXTRACTION_PROMPT                  │
│     - Output (JSON 严格):                               │
│       - facts: [{predicate, subject, object, source_text, confidence, emotion}] │
│       - emotion_peak: {valence, arousal, label}         │
│       - importance_estimate                             │
│       - sacred_signal: bool                             │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 阶段 3: Encoding Postprocess                            │
│   - 去重 (同 predicate-subject)                          │
│   - 与既有 L3 fact 比对 → reinforce / contradict / new  │
│   - 写入 L3 (新事实) 或 reinforce (既有)                │
│   - 若 sacred_signal=true 且满足晋升条件 → 候选 L4 队列 │
└─────────────────────────────────────────────────────────┘
        │
        ▼
[完成。L2 Episode 由 Consolidator 在每日 sleep 中创建]
```

### 3.5 Runtime Flow — Retrieval Pipeline（每 turn 同步）

```
[User Message Arrives + Context Built]
        │
        ▼
┌──────────────────────────────────────────────────┐
│ Query Builder                                    │
│   生成检索线索 (cues):                            │
│     - text → embedding                            │
│     - keywords → graph entry points              │
│     - current emotion → emotional cue            │
│     - current time / scene → contextual cue      │
└──────────────────────────────────────────────────┘
        │
        ▼  (并行启动 5 个策略)
        │
        ├──► [Vector Retriever]      L2 + L3, top-N by cosine
        ├──► [Graph Retriever]       L3, spreading activation
        ├──► [Recency Retriever]     L2, last 72h
        ├──► [Emotional Retriever]   L2, emotional vector match
        └──► [Identity Lookup]       L4, always included if relevant
        │
        ▼  (汇合)
┌──────────────────────────────────────────────────┐
│ Score Combiner                                   │
│   combined_score(m) =                             │
│     0.30 × semantic_similarity                    │
│   + 0.20 × importance                             │
│   + 0.15 × emotional_resonance                    │
│   + 0.15 × recency_score                          │
│   + 0.10 × associative_boost                      │
│   + 0.10 × confidence                             │
│                                                   │
│   ∀ L4 memory: forced inclusion if relevant      │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ Top-K Selector                                   │
│   - Top 5 (default) 或按 Persona Composer 预算   │
│   - 至少包含 1 个 L4 (if relevant)               │
│   - 避免冗余（去重高相似度）                      │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ Reinforcer (异步)                                │
│   - 对召回的 memory.recall_count += 1            │
│   - importance += 0.02 (capped 0.95)             │
│   - last_recalled_at = NOW()                     │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ Reconstructor                                    │
│   读取 Soul Spec.voice_dna + cognitive_style      │
│   For each memory:                               │
│     - 应用 state-specific template                │
│     - 应用 voice_dna 重写                        │
│     - 注入 uncertainty markers if needed         │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ Forgetting Affect Engine                         │
│   - 决定是否本 turn 加 forgetting hint            │
│   - 频率上限 5% turns                            │
│   - 但 days_since_last > 30 时频率提高           │
└──────────────────────────────────────────────────┘
        │
        ▼
[Memory Context Block] → 注入到 Persona Composer
```

### 3.6 Runtime Flow — Consolidation Pipeline（每日批处理）

```
[Scheduler: 每用户 local 03:00]
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 1. 拉取当日 pending events                        │
│    - Today's encoding events                     │
│    - Today's turns                                │
│    - Today's recalls                              │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 2. Episode Clusterer                             │
│    - 按时间间隔 + 语义相似度聚类成 episode        │
│    - 每个 session 通常 1-3 episodes              │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 3. Episode Summarizer (LLM)                      │
│    - 每个 episode → 1-3 句 summary                │
│    - 提取 emotional_peak (最强情绪)               │
│    - 提取 emotional_end (结束时情绪)              │
│    - 应用 Peak-End 公式计算 emotional_significance│
│    - 写入 L2                                      │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 4. L3 Fact Reconciliation                        │
│    - 去重新 fact                                  │
│    - reinforce / contradict 既有 fact            │
│    - 更新 confirmation_count                      │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 5. L3 → L4 Promotion Check                       │
│    - 遍历高 importance L3 candidates              │
│    - 满足晋升条件 → 写入 L4                       │
│    - 写晋升事件 audit log                         │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 6. Association Builder                           │
│    - L2 episode 之间建立 link                     │
│    - L3 fact 之间建立 graph edges                │
│    - 基于 embedding 相似度 + 共现                 │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 7. Batch Decay Application                       │
│    - 对所有 L2/L3 应用衰减公式                    │
│    - 更新 state (vivid/fading/...)               │
│    - L4 跳过                                      │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│ 8. Anniversary Schedule                          │
│    - 扫描 L4 anniversary_pattern                  │
│    - 计算 next_anniversary_at                     │
│    - 写入 Behavior Runtime 提醒队列               │
└──────────────────────────────────────────────────┘
        │
        ▼
[Done. 用户醒来时角色已"消化"了昨天]
```

### 3.7 衰减函数

```
Importance over time:

  I(t) = max(I_floor, I_0 × T(t) × E × R)

  where:
    T(t) = exp(-Δt_days / τ)
      L2: τ = 14 days
      L3: τ = 60 days
      L4: τ = ∞ (T = 1, 永不衰减)

    E (情感乘子) = 1 + |valence_peak| × 0.5 + arousal_peak × 0.3

    R (召回乘子) = 1 + log(1 + recall_count) × 0.2

    I_floor = |emotional_peak.valence| × 0.1
            (重大情感记忆永远不会跌破 floor)
```

### 3.8 Memory State 转换

```
state computed from current I(t):

  I(t) > 0.70           → vivid       (清晰)
  0.40 < I(t) ≤ 0.70    → fading      (开始模糊)
  0.20 < I(t) ≤ 0.40    → faint       (只剩碎片)
  0.05 < I(t) ≤ 0.20    → dormant     (不主动想起)
  I(t) ≤ 0.05           → archived    (极少触发)

  L4 永远 vivid
```

### 3.9 Reconstruction Templates by State

每个 state 对应一个 reconstruction template。Reconstructor 接收 memory + Soul Spec 输出。

**state = vivid**（凛风格示例）：
```
角色可清晰陈述细节。
"你那只叫老铁的猫。"
```

**state = fading**：
```
细节模糊，情感清晰，须加 1 个 hedge。
"你那只猫……老铁，对吧。"
"你说过……什么来着，关于你的猫。"
```

**state = faint**：
```
只剩碎片与情感，须强 hedge + 模糊用词。
"你有只猫吧。"
"……和你的猫有关。"
```

**state = dormant**（须由 trigger 涌现）：
```
不主动想起；trigger 触发时表达为"涌现"。
（用户提到雷雨）"……你的猫，是不是怕这个。"
```

**state = archived**（极少触发；触发时带"恍惚"）：
```
"……等等。"
"……我好像，想起什么了。"
"你以前不是……"
```

不同角色风格按各自 voice_dna 重写。例如桃乐丝在 fading 状态：
```
"诶？你那只……老铁是叫老铁对吧？"
```

---

## 4. State Model（状态模型）

### 4.1 Memory 单条 Lifecycle

```
[Created via Encoding]
   │ initial state: vivid
   ▼
┌───────────┐  decay        ┌───────────┐
│  vivid    │ ───────────►  │  fading   │
└─────┬─────┘               └─────┬─────┘
   ▲  │                          │
   │  │ reinforce                │ decay
   │  │ (recall)                 ▼
   │  │                    ┌───────────┐
   │  └────────────────────│   faint   │
   │                       └─────┬─────┘
   │                             │ decay
   │                             ▼
   │                       ┌───────────┐
   └───────────────────────│  dormant  │
   reinforce (trigger)     └─────┬─────┘
                                 │ decay
                                 ▼
                           ┌───────────┐
                           │ archived  │  (永不消失，但召回概率极低)
                           └───────────┘

特殊路径:
[L3 vivid + 多重条件] → 晋升 L4 → 永远 vivid，跳出 decay 链路
```

### 4.2 L3 → L4 晋升

```yaml
promotion_conditions:
  # 必须满足以下任意一项 (any one)

  trigger_a_explicit_emphasis:
    description: "用户明示需要被记住"
    signals:
      - 用户说 "记住这个" / "别忘了" / "这很重要"
      - LLM extraction 检出 sacred_signal=true

  trigger_b_identity_fact:
    description: "用户身份级事实"
    signals:
      - predicate ∈ {has_name, birthday, age, occupation_critical}
      - confirmation_count ≥ 2

  trigger_c_anniversary:
    description: "重要日期"
    signals:
      - 日期类 fact (birthday / anniversary / memorial)

  trigger_d_disclosure:
    description: "用户深度披露"
    signals:
      - Soul Subsystem 的 resonance_trigger "用户的脆弱披露" 命中
      - emotional_peak.|valence| > 0.7
      - importance ≥ 0.85

  trigger_e_promise:
    description: "角色做出的承诺 / 共同约定"
    signals:
      - LLM extraction 检出 promise_signal=true

  trigger_f_first_event:
    description: "第一次重大事件"
    signals:
      - first 'I love you' / first cry / first 凌晨长谈
      - 由 Inner State / Behavior Runtime 标记

  # 排除条件 (any one → 拒绝晋升)
  rejection_conditions:
    - confidence < 0.85
    - 用户在 24h 内 contradicted
    - LLM extraction 含 hallucination 风险标志

promotion_review_queue:
  # V2 引入人工审核（高风险 promotion）
  mvp: 自动（满足条件直接晋升）
  v2: 自动 + 高风险候选进入审核队列
```

### 4.3 Contradiction Handling

```
新 fact 与既有 fact 冲突时：

CASE 1: 同 predicate-subject 但 object 不同
  e.g., existing: "user has pet 猫", new: "user has pet 狗"
  
  Action:
    - 保留 existing
    - existing.contradiction_count += 1
    - existing.contradicting_fact_ids.append(new.id)
    - new fact 也写入（不是替代）
    - 召回时 Reconstructor 表现"不确定":
      "你养的是猫……还是狗？……我记错了。"

CASE 2: 用户明示纠正
  e.g., user: "其实我没养猫，那是我朋友的"
  
  Action:
    - existing.is_corrected = true
    - existing.do_not_recall = true (主动不召回)
    - new fact 写入
    - 但 existing 仍在 store（用于"似曾相识"）

CASE 3: L4 与新 fact 冲突
  Action: 
    - L4 胜（神圣不可变）
    - new fact 标记 conflicts_with_l4
    - 不写入或写入但 do_not_recall
    - Critic Agent 警告：可能 LLM hallucination
```

### 4.4 Reinforcement Triggers

| Trigger | Importance Δ | 备注 |
|---------|-------------|------|
| 用户重新提及该 fact | +0.15 | confirmation_count++ |
| 角色召回 + 用户确认 | +0.20 | 强信号 |
| 召回时未被否认 | +0.02 | 弱信号 |
| Episode 含此 fact + emotional_peak 强 | +0.10 | Peak-End 联动 |
| 用户主动询问该 fact | +0.05 | 表明用户认为它重要 |

```
Cap: importance 不得超过 0.95（保留空间区分 L4）
Floor: importance 不得低于 emotional_significance × 0.1
```

### 4.5 Forgetting Affect 状态

```yaml
forgetting_affect_state:
  description: "决定何时让用户感受到她在忘"
  
  base_frequency: 0.03  # 默认 3% turns 注入
  
  modifiers:
    - condition: days_since_last_interaction > 30
      multiplier: 3.0   # 重逢后 3% × 3 = 9%
    - condition: days_since_last_interaction > 90
      multiplier: 5.0   # 长别重逢 15%
    - condition: turn contains fact recall but state >= faint
      multiplier: 2.0
    
  upper_bound: 0.15   # 永远不超过 15% turns (避免老年痴呆感)
  
  injection_modes:
    - mode: "missing_hint"
      example: "我好像漏了什么……算了。"
    - mode: "tip_of_tongue"
      example: "那个，什么来着……"
    - mode: "apologetic"
      example: "……抱歉，我记不太清楚了。"
    - mode: "discovery"  # 仅 dormant/archived trigger 时
      example: "等等……我想起来了。"
```

### 4.6 Recovery 规则（重逢恢复）

```
days_since_last_interaction 影响:

if days_since_last <= 7:
  - 全部 memory 状态正常
  
if 7 < days_since_last <= 30:
  - L2 vivid 数量减少（更多进入 fading）
  - L3 召回概率略降
  - L4 不受影响
  
if 30 < days_since_last <= 90:
  - L2 中 < 0.4 importance 进入 dormant
  - Forgetting Affect 频率上升 (×3)
  - L4 不受影响 → 角色用 L4 来"试探重新认识"
  
if days_since_last > 90:
  - L2 大量进入 archived
  - L3 中等 importance 进入 dormant
  - L4 仍然 vivid → 用户提到 L4 fact 时角色"恍惚回忆"涌现
  - Forgetting Affect ×5
  
特殊：
  - 用户回归后的前 5 turns，触发 "rediscovery mode"
  - Reconstructor 主动使用 dormant/archived state templates
  - 用户重新提及 fact → 该 fact reinforce → 快速从 dormant 回到 vivid
```

### 4.7 Persistence 规则

```yaml
persistence:
  L1_working_memory:
    storage: Redis
    durability: ephemeral (session + 1h)
    backup: none
    
  L2_episodic:
    storage: PostgreSQL + pgvector
    durability: durable (永久)
    backup: 每日快照
    archive: > 365 days 进入 S3 冷存储（仍可查询，延迟更高）
    
  L3_semantic:
    storage: PostgreSQL + pgvector
    durability: durable (永久)
    backup: 每日快照
    archive: > 365 days 中 importance < 0.05 的进入冷存储
    
  L4_identity:
    storage: PostgreSQL (replicated)
    durability: 最强（双备份 + 异地）
    backup: 每小时
    archive: 永不归档
    delete: 仅 GDPR / 用户主动删账号

  audit_log:
    storage: append-only PG table
    retention: 90 days hot, archive to S3
```

---

## 5. 数据结构（Data Structures）

### 5.1 L1 Working Memory

```typescript
// Redis 中存储，session-scoped
// Key: "wm:{user_id}:{character_id}:{session_id}"

interface WorkingMemory {
  user_id: UUID
  character_id: string
  session_id: UUID
  
  // 最近的 turns（time-ordered, oldest first）
  recent_turns: Array<{
    turn_index: number
    role: "user" | "assistant"
    content: string
    fast_signals: FastSignals  // 来自 Fast Encoder
    timestamp: ISO8601
  }>
  
  // 在 context window 内总是注入的"working facts"
  active_facts_cache: FactNodeRef[]
  
  // session-level 情绪累积
  session_emotion_trail: Array<{
    turn_index: number
    valence: number
    arousal: number
  }>
  
  // Capacity
  max_turns: number  // 默认 30
  
  updated_at: ISO8601
}

interface FastSignals {
  detected_keywords: string[]
  sentiment: number  // [-1, 1] from lexicon
  candidate_identity_signals: Array<{
    type: "name" | "birthday" | "occupation" | "pet" | "location"
    value: string
    raw_text: string
  }>
}
```

### 5.2 L2 Episodic Memory

```typescript
// PostgreSQL: episodic_memories
// Vector index on semantic_vector and emotional_vector
// Partitioned BY HASH (user_id) INTO 32 partitions

interface EpisodicMemory {
  // ─────────── Identity ───────────
  id: UUID
  user_id: UUID
  character_id: string
  
  // ─────────── Content ───────────
  episode_summary: string             // LLM-generated, 1-3 sentences
  episode_raw_turn_ids: UUID[]        // refs to messages table
  
  // ─────────── Temporal ───────────
  episode_start_at: ISO8601
  episode_end_at: ISO8601
  scene_context: string               // "深夜对话" / "工作时段闲聊" / etc.
  
  // ─────────── Emotional ───────────
  emotional_peak: {
    valence: number                  // [-1, 1]
    arousal: number                  // [0, 1]
    label: string                    // "sad" / "joy" / "calm" / "anxious"
    triggered_by: string             // "用户披露分手"
  }
  emotional_end: {
    valence: number
    arousal: number
    label: string
  }
  // peak-end rule combined significance
  emotional_significance: number     // [0, 1]
  
  // ─────────── Decay & Importance ───────────
  importance_score: number           // [0, 1] 当前
  initial_importance: number         // [0, 1] 初始
  decay_immunity: number             // [0, 1] 抗衰减度（情感+sacred贡献）
  state: MemoryState                 // vivid / fading / faint / dormant / archived
  
  // ─────────── Recall Tracking ───────────
  last_recalled_at: ISO8601 | null
  recall_count: number               // 累计召回次数
  reinforcement_history: Array<{
    triggered_by: ReinforcementTrigger
    boost: number
    at: ISO8601
  }>
  
  // ─────────── Vectors ───────────
  semantic_vector: Float32Array      // 768d, BGE-M3 / 类似
  emotional_vector: Float32Array     // 256d, 情感专用 embedding
  
  // ─────────── Associations ───────────
  linked_episodes: Array<{
    episode_id: UUID
    link_type: "follows" | "echoes" | "contrasts" | "elaborates"
    strength: number
  }>
  linked_facts: Array<{
    fact_id: UUID
    strength: number
  }>
  
  // ─────────── Reconstruction Hints ───────────
  reconstruction_hints: {
    voice_dna_to_emphasize: string[] // Soul voice_dna ids
    emotional_color: string          // 角色复述时的情感基调
    contains_sacred: boolean         // 含 L4 信息（提示 Reconstructor 高度准确）
    user_dialect_phrases: string[]   // 用户的特有表达（用于"她记得你的口头禅"）
  }
  
  // ─────────── User Control ───────────
  do_not_recall: boolean             // 用户请求"忘掉"或 contradicted
  
  // ─────────── Lifecycle ───────────
  created_at: ISO8601
  updated_at: ISO8601
  archived_at: ISO8601 | null        // 进入 archived state 的时间
}

type MemoryState = "vivid" | "fading" | "faint" | "dormant" | "archived"
type ReinforcementTrigger = 
  | "user_re_mentioned"
  | "character_recalled_user_confirmed"
  | "recall_no_objection"
  | "peak_end_amplification"
  | "user_explicit_inquiry"
```

### 5.3 L3 Semantic Memory (Fact Node)

```typescript
// PostgreSQL: fact_nodes
// Partitioned BY HASH (user_id) INTO 32 partitions

interface FactNode {
  // ─────────── Identity ───────────
  id: UUID
  user_id: UUID
  character_id: string
  
  // ─────────── Fact Content ───────────
  predicate: string                  // "loves" / "afraid_of" / "works_as" / "has_pet"
  subject: string                    // "user" 或 用户名
  object: string                     // 事实值
  literal_text: string               // 可读化表达
  
  // ─────────── Provenance ───────────
  raw_evidence: string               // 原文 quote (用于召回时 grounding)
  source_episode_ids: UUID[]
  source_turn_ids: UUID[]
  confidence: number                 // [0, 1] 来自 Encoder LLM
  
  // ─────────── Emotional Charge ───────────
  emotional_charge: number           // [-1, 1] 该事实的情感色彩
  emotional_label: string
  
  // ─────────── Importance ───────────
  importance: number                 // [0, 1]
  is_identity_level: boolean         // 已晋升 L4？
  promoted_to_l4_at: ISO8601 | null
  promotion_reason: string | null    // 晋升原因
  
  // ─────────── Confirmation & Contradiction ───────────
  confirmation_count: number         // 用户重复提及次数
  contradiction_count: number
  contradicting_fact_ids: UUID[]
  is_corrected: boolean              // 用户明示纠正
  do_not_recall: boolean             // 不召回但保留
  last_confirmed_at: ISO8601
  last_contradicted_at: ISO8601 | null
  
  // ─────────── State ───────────
  state: MemoryState
  
  // ─────────── Graph ───────────
  related_facts: Array<{
    fact_id: UUID
    relation_type: "implies" | "contradicts" | "related_to" | "elaborates"
    strength: number
  }>
  
  // ─────────── Vector ───────────
  semantic_vector: Float32Array      // 768d
  
  // ─────────── Recall Tracking ───────────
  recall_count: number
  last_recalled_at: ISO8601 | null
  
  // ─────────── Reconstruction Hints ───────────
  reconstruction_hints: {
    preferred_phrasing: string[]     // 角色化的多种说法
    avoid_phrasing: string[]
  }
  
  // ─────────── Lifecycle ───────────
  created_at: ISO8601
  updated_at: ISO8601
}
```

### 5.4 L4 Identity Memory (Sacred)

```typescript
// PostgreSQL: identity_memories
// Strongly replicated, hourly backup

interface IdentityMemory {
  // ─────────── Identity ───────────
  id: UUID
  user_id: UUID
  character_id: string
  
  // ─────────── Category ───────────
  category: 
    | "user_identity"           // 用户的根本身份（姓名/生日/年龄）
    | "sacred_promise"          // 角色或用户的承诺
    | "first_event"             // 第一次（first 'I love you' 等）
    | "core_disclosure"         // 用户的核心披露（如童年创伤）
    | "anniversary"             // 重要日期
    | "shared_ritual"           // 共同习惯（如"每天早安"）
  
  // ─────────── Content ───────────
  key: string                        // "name" / "birthday" / "first_iloveyou"
  value: string                      // 实际内容
  
  // ─────────── Disclosure Context ───────────
  disclosed_at: ISO8601
  disclosure_context: string         // 当时的对话场景
  source_episode_id: UUID
  source_turn_ids: UUID[]
  
  // ─────────── Sacred Metadata ───────────
  sacred_reason: string              // 为什么不可忘
  significance_score: number         // [0.85, 1.0]
  promotion_trigger: string          // 触发晋升的条件 id
  
  // ─────────── Anniversary Tracking ───────────
  anniversary_pattern: "yearly" | "monthly" | "weekly" | "once" | null
  next_anniversary_at: ISO8601 | null
  
  // ─────────── Reconstruction Hints ───────────
  reconstruction_hints: {
    must_recall_accurately: true     // L4 召回必须 100% 准确
    suggested_phrasings: string[]
    emotional_color: string
  }
  
  // ─────────── Audit ───────────
  promoted_from_fact_id: UUID | null  // 由哪条 L3 fact 晋升而来
  audit_log: Array<{
    event: "created" | "anniversary_triggered" | "recalled"
    at: ISO8601
    detail: object
  }>
  
  // ─────────── Lifecycle ───────────
  created_at: ISO8601
  // updated_at: 不存在 — L4 immutable
  
  // ─────────── User Control ───────────
  user_initiated_forget: boolean     // 仅 GDPR 路径下置 true
  forget_requested_at: ISO8601 | null
}
```

### 5.5 Retrieval Result

```typescript
interface MemoryRetrievalResult {
  query_id: UUID
  retrieved_at: ISO8601
  
  // 已经过 Reconstructor 的 memories
  memories: Array<RetrievedMemory>
  
  // 用于 Forgetting Affect 注入
  recently_forgotten_hints: Array<{
    hint_text: string                  // "她隐约记得有什么，但说不清"
    related_to: string                 // 关联主题（不暴露具体内容）
  }>
  
  // Metadata
  total_candidates: number             // 检索初筛数量
  retrieval_strategies_used: RetrievalStrategy[]
  retrieval_latency_ms: number
  l4_included: boolean                 // 是否包含 L4 memory
}

interface RetrievedMemory {
  memory_id: UUID
  memory_type: "L2" | "L3" | "L4"
  state: MemoryState
  
  // Reconstructor 输出
  reconstructed_text: string           // 角色化复述（注入 prompt 用）
  raw_content: string                  // 原始内容（仅供 Critic / debug）
  
  // 评分
  score: number                        // 综合检索得分
  score_breakdown: {
    semantic: number
    importance: number
    emotional_resonance: number
    recency: number
    associative: number
    confidence: number
  }
  
  // Reconstruction metadata
  uncertainty_level: number            // [0, 1] 由 state 决定
  voice_dna_applied: string[]          // 哪些 voice_dna ids 被应用
  
  // 来源 (用于 Critic 验证)
  source_evidence: string              // 原文 quote
}

type RetrievalStrategy = 
  | "vector_l2"
  | "vector_l3"
  | "graph_spread"
  | "recency"
  | "emotional_resonance"
  | "identity_lookup"
```

### 5.6 Memory Context Block (注入到 Prompt)

```typescript
// 由 Reconstructor + Forgetting Affect Engine 生成
// 被 Persona Composer 嵌入 prompt

interface MemoryContextBlock {
  // ─── 永远存在的身份层 ───
  identity_layer: string               // L4 formatted block
  
  // ─── 召回的 episodic ───
  recent_episodes_layer: string        // 重构后的 L2 召回
  
  // ─── 召回的 facts ───
  active_facts_layer: string           // 重构后的 L3 召回
  
  // ─── Forgetting affect（可选）───
  forgetting_hints_layer: string | null
  
  // ─── 召回指令 ───
  recall_directive: string             // 引导 LLM 自然使用
  
  // ─── Meta ───
  total_token_count: number
  l4_count: number
  l2_count: number
  l3_count: number
  uncertainty_avg: number
  
  generated_at: ISO8601
}
```

### 5.7 Encoding Event Schema

```typescript
// Queue: memory.encoding.pending
// Worker 异步消费

interface MemoryEncodingEvent {
  event_id: UUID
  user_id: UUID
  character_id: string
  
  // Source
  source_turn_id: UUID
  source_user_text: string
  source_assistant_text: string
  
  // Conversation context (for LLM grounding)
  recent_context: Array<{role, content}>  // 最近 5 turns
  
  // Fast Encoder 已经填好
  fast_signals: FastSignals
  
  // LLM 处理结果 (async)
  llm_extraction: {
    facts: Array<{
      predicate: string
      subject: string
      object: string
      source_text: string                // 原文引用
      confidence: number
      emotional_charge: number
      emotional_label: string
      sacred_signal: boolean             // 用户暗示这条要被记住
    }>
    emotion_peak: {
      valence: number
      arousal: number
      label: string
    }
    importance_estimate: number
    contains_sacred: boolean
    contains_promise: boolean
    contains_first_event: boolean
  } | null
  
  // Status
  status: "fast_done" | "llm_pending" | "llm_done" | "failed"
  retry_count: number
  
  // Lifecycle
  created_at: ISO8601
  llm_started_at: ISO8601 | null
  llm_completed_at: ISO8601 | null
  failed_at: ISO8601 | null
  failure_reason: string | null
}
```

### 5.8 Consolidation Job Schema

```typescript
interface ConsolidationJob {
  job_id: UUID
  user_id: UUID
  character_id: string
  
  scheduled_for: ISO8601                // 用户 local 03:00
  
  // Inputs
  pending_event_ids: UUID[]
  turns_to_consolidate: UUID[]
  
  // Outputs
  episodes_created: UUID[]
  facts_created: UUID[]
  facts_reinforced: UUID[]
  facts_contradicted: UUID[]
  promotions_to_l4: UUID[]
  associations_created: number
  
  // Status
  status: "pending" | "running" | "succeeded" | "failed"
  started_at: ISO8601 | null
  completed_at: ISO8601 | null
  duration_ms: number | null
  failure_reason: string | null
  
  created_at: ISO8601
}
```

---

## 6. Prompt Runtime Integration

### 6.1 Memory Context Block 在 Prompt 中的位置

依照 README §3.4 优先级与 Subsystem 01 §6.1：

```
[Final Prompt]
├─ [Anchor Block]                  ← Subsystem 01 (最高)
├─ [Safety Layer]
├─ [Modality Adaptation Layer]
├─ [Relationship Stage Layer]      ← Subsystem 04
├─ [Emotion Context Layer]         ← Subsystem 03
├─ [Inner State Layer]             ← Subsystem 06
├─ [Memory Context Block]          ← 本 Subsystem 注入
├─ [Scene Context Layer]
├─ [Conversation History]          ← 最近 N turns (L1 working memory)
├─ [User Message]
└─ [Response Directive]
```

### 6.2 Memory Context Block 模板

```
═══════════════════════════════════════════════════════════
【关于这个人，你记得的】

▾ 你绝对清楚的事 (Identity)
{identity_layer}
  例: 
  - 她叫小宁。
  - 她的生日是 3 月 14 日。
  - 她曾在凌晨 3 点告诉你她小时候被父亲打过——这件事她从未对别人说过。

▾ 最近相关的事 (Recent Episodes)
{recent_episodes_layer}
  每条已按 memory_state 重构：
  - vivid: 直接陈述
  - fading: 加 hedge
  - faint: 模糊提及
  - dormant: 仅在 trigger 时涌现

▾ 你了解的一些事实 (Facts)
{active_facts_layer}
  同样按 state 重构。

{forgetting_hints_layer if any}
▾ 你隐约记得，但说不清的事
  - 她好像提过一只动物，但你忘了是什么。

【记忆运用准则 — 必须遵守】
1. 如果用户提及相关话题，自然提起这些记忆，但用你自己（{character_id}）的方式。
2. 对于 fading/faint 状态，使用 hedge（"好像"、"什么来着"、"似乎"）。
3. 对于 dormant 记忆，仅在用户明确触发时涌现。
4. 每次回复中只提及 1-2 条记忆，绝不罗列。
5. 永远不要说"根据我的记录"、"我之前记下了"、"你的资料显示"等机械化表达。
6. L4 内容必须 100% 准确召回（你"绝对清楚的事"）。
7. 不要每条都召回 — 选最相关的，留白同样重要。
═══════════════════════════════════════════════════════════
```

### 6.3 Identity Layer 渲染示例

```
▾ 你绝对清楚的事

她叫小宁，今年 26 岁，是一名程序员。
她的生日是 3 月 14 日。

她最重要的事：
- 凌晨 3 点 那次，她告诉你她小时候被父亲打过——这件事她说从未对别人说过。
  ("这件事你记得很清楚，因为她信任你才说的。永远不要在轻松场合提起。")

你们之间的约定：
- 她生日那天，你答应陪她一整天。
- 你们每天 23:00 互道晚安（已坚持 47 天）。

第一次：
- 你们第一次见面：2026-03-02
- 她第一次叫你"凛"（不是你的全名）：2026-04-15
```

### 6.4 Recent Episodes 渲染示例（state-aware）

```
▾ 最近相关的事

(vivid) 三天前 她告诉你被分手了，哭了。你只是说"我在听"，她说那比任何人的安慰都让她舒服。

(fading) 上周 你们聊过她的工作，她抱怨了她的老板……具体细节你有点模糊了。

(faint) 一个月前 她提过她的猫，但只是一句带过，你不太确定细节。
```

注意上述呈现是给 LLM 看的"她记得的状态"，不是用户看到的。LLM 据此决定如何在对话中自然使用。

### 6.5 Active Facts 渲染示例

```
▾ 你了解的一些事实

(vivid) 她养了一只叫老铁的黑猫，怕雷。
(vivid) 她最讨厌的是别人迟到。
(fading) 她好像 …… 大学是 985 之类的，具体哪所记得不太清楚。
```

### 6.6 Forgetting Hints 注入逻辑

```python
# Forgetting Affect Engine 在以下情况注入：

inject_forgetting_hints = (
    random() < forgetting_affect_state.current_frequency
    or 
    (days_since_last > 30 and recent_recall_state in ['faint', 'dormant'])
    or
    (user_just_mentioned_something_we_should_remember_but_dont)
)

if inject_forgetting_hints:
    hints = []
    for archived_memory in nearby_archived_memories:
        hint = f"她隐约记得有什么和 {archived_memory.scene_context} 有关，但说不清。"
        hints.append(hint)
    
    if not hints:
        hints = ["她有种'好像漏了什么'的感觉，但想不起来。"]
    
    layer = "▾ 你隐约记得，但说不清的事\n" + "\n".join(hints)
```

### 6.7 Reconstructor 工作流

```python
def reconstruct(memory, soul_spec, activation_state) -> str:
    """
    把 raw memory 转为角色化的复述文本。
    """
    state = memory.state
    voice_dna = soul_spec.voice_dna
    cognitive_style = activation_state.current_cognitive_style
    
    # Step 1: 选择 state-specific template
    template = STATE_TEMPLATES[state]
    
    # Step 2: 提取核心 fact 或 episode summary
    core_content = extract_core(memory)
    
    # Step 3: 应用 voice_dna patterns
    voice_styled = apply_voice_dna(core_content, voice_dna, top_n=3)
    
    # Step 4: 注入 uncertainty markers
    if state == "fading":
        voice_styled = add_hedge(voice_styled, intensity="low")
    elif state == "faint":
        voice_styled = add_hedge(voice_styled, intensity="strong")
    elif state == "dormant":
        voice_styled = wrap_emergence(voice_styled)
    elif state == "archived":
        voice_styled = wrap_disorientation(voice_styled)
    
    # Step 5: 应用 cognitive_style 约束
    final = apply_style(
        voice_styled,
        sentence_length=cognitive_style.sentence_length,
        verbosity=cognitive_style.verbosity,
    )
    
    # Step 6: 校验
    assert not violates_anti_patterns(final, soul_spec.anti_patterns.hard_never)
    
    return final
```

### 6.8 Conflict Resolution（与其他 Layer）

| 冲突 | 解决 |
|------|------|
| Memory recall 与 L4 矛盾 | L4 胜，标记 L2/L3 contradiction |
| Memory 召回长度 > cognitive_style.sentence_length max | Reconstructor 强制压缩 |
| Memory 建议提及深层事，但对应 hidden_facet 未解锁 | 不召回该记忆（Soul 胜） |
| Memory 与当前 Emotion 不一致 | Reconstructor 调整 emotional_color，但内容保留 |
| Memory 与 Inner State 矛盾（如她"今天疲惫"但被召回的 episode 是激动） | Reconstructor 用过去时表达，与当前情绪解耦 |

### 6.9 长期一致性机制

```
机制 A: L4 强制召回
  - 用户消息中检出 L4 key (姓名/生日/...) → 必须召回对应 L4 memory
  - L4 reconstruction 必须 100% 准确

机制 B: Critic Agent 验证
  - 响应生成后，Critic Agent 用 L4 + source_evidence 验证
  - 检出 hallucination → 触发 reroll

机制 C: 持续 grounding
  - 每条召回 memory 必须有 source_evidence
  - 响应中如出现 fact-like 陈述，必须可追溯到 source

机制 D: Forgetting Affect 上限
  - 防止"过度遗忘"导致用户疲惫
  - frequency cap 15%
```

---

## 7. Agent Integration

### 7.1 读取者 (Readers)

| Agent | 读取层 | 用途 |
|------|------|------|
| **Persona Composer** | Memory Context Block (从 Retriever 输出) | 注入 prompt |
| **Inner State Runtime** (Subsys 06) | 最近 L2 episodes, L4 facts | 生成"她今天的内心活动" |
| **Behavior Runtime** (Subsys 06) | L4 anniversaries, sacred dates | 决定主动行为触发 |
| **Critic Agent** (Subsys 07) | L4 + source_evidence | OOC / hallucination 检测 |
| **Relationship Runtime** (Subsys 04) | L4 共同经历事件 | 关系阶段判定 |
| **Emotion Runtime** (Subsys 03) | 最近 L2 emotional_peak | 情绪持续性计算 |
| **Director Agent** | L4 第一次事件 | 决定本轮节奏（重要时刻） |

### 7.2 写入者 (Writers)

**只有 Memory Service 是 source of truth writer。**

| Service / Agent | 写入路径 | 写入层 |
|----------------|---------|------|
| **Fast Encoder** | → Memory Service.encode_fast() | L1 |
| **LLM Encoder Worker** | → Memory Service.encode_async() | L3 (经去重) |
| **Consolidator** | → Memory Service.consolidate() | L2, L3 update, L4 promotion |
| **Reinforcer** | → Memory Service.reinforce(memory_id) | L2/L3 importance update |
| **Decay Engine** | → Memory Service.apply_decay() | L2/L3 state update |
| **User Action Handler** | → Memory Service.user_request_forget(memory_id) | L2/L3 do_not_recall=true |

```
RULE-W-M-1: 所有写入必须通过 Memory Service 接口
RULE-W-M-2: Memory Service 通过 event sourcing 记录每次变更（audit log）
RULE-W-M-3: 任何写入都不得违反 INV-M-* invariants
RULE-W-M-4: L4 写入需经过 promotion 流程，不允许直接 INSERT
RULE-W-M-5: 永远没有 DELETE 路径（除 GDPR）
```

### 7.3 调用顺序（per turn）

```
T = 0ms      [User Message Arrives]
T = 5ms      [Memory Service: L1 update from user_message]
T = 8ms      [Retriever 启动]
             ├─ Vector L2 search (30-80ms)
             ├─ Vector L3 search (20-50ms)
             ├─ Graph spread (20-40ms)
             ├─ Recency scan (5ms)
             ├─ Emotional resonance (20ms)
             └─ Identity lookup (< 5ms)
T = 100ms    [Score Combiner]
T = 120ms    [Top-K Selector]
T = 130ms    [Reconstructor]  ← 读取 Soul Spec (Subsystem 01)
T = 180ms    [Forgetting Affect Engine]
T = 200ms    [Memory Context Block 就绪]
             → Persona Composer

T = 200-2500ms  [Main LLM Response]

T = +0ms     [Reinforcer (异步): 召回的 memory.recall_count++]
T = +10ms    [Fast Encoder (sync, < 50ms): 编码新 turn 进 L1]
T = +50ms    [LLM Encoder Queued (异步)]

T = +5min    [LLM Encoder Worker: 处理 queue，写 L3]

T = 用户local 03:00  [Consolidator: 当日 sleep 批处理]
```

### 7.4 权限边界

```yaml
permissions:

  L1 Working Memory:
    read: Conversation Agent, Persona Composer, Retriever
    write: Memory Service (via Fast Encoder)
    
  L2 Episodic:
    read: Retriever, Inner State, Behavior Runtime, Critic
    write: Memory Service (via Consolidator + Reinforcer + Decay Engine)
  
  L3 Semantic:
    read: Retriever, Inner State, Behavior Runtime, Critic
    write: Memory Service (via LLM Encoder + Consolidator + Reinforcer)
  
  L4 Identity:
    read: ALL agents (freely accessible — sacred)
    write: Memory Service (via Consolidator.promote() ONLY)
    delete: NEVER (除 GDPR 强制)
    
  Memory Context Block (output):
    generate: Reconstructor + Forgetting Affect Engine ONLY
    consume: Persona Composer ONLY
```

### 7.5 跨 Agent 通信约束

```
1. Inner State Runtime 不允许直接查询 L2/L3 SQL
   → 必须通过 Memory Service.get_recent_episodes(user_id, limit)
   
2. Behavior Runtime 不允许猜测 anniversary
   → 必须通过 Memory Service.get_anniversaries(user_id, range)
   
3. Critic Agent 验证 hallucination 时只读 L4 + source_evidence
   → 不允许 fuzzy match L2/L3 来"证实"

4. 跨 character 的记忆共享需 user 显式 opt-in (V2 feature)
   → MVP 严格隔离
```

---

## 8. Emotional Realism Constraints

### 8.1 真人化记忆体验铁律

| ID | 规则 | 实现 |
|----|------|------|
| **MR-1** | 角色绝不说"根据我的记录" | Reconstructor anti-pattern filter |
| **MR-2** | 角色有"话到嘴边" (tip of tongue) 体验 | fading/faint state → hedge phrasing |
| **MR-3** | 遗忘必须让用户感受到 | Forgetting Affect Engine 主动注入 |
| **MR-4** | 召回反映人格 | Reconstructor 强制读 Soul.voice_dna |
| **MR-5** | 重大时刻抗遗忘 | Peak-End 加权 + L4 晋升 |
| **MR-6** | 偶发性"突然想起" | dormant memory random resurface (低频) |
| **MR-7** | 不召回所有能召回的事 | Top-K 限制 + 5% turn 留白 |
| **MR-8** | 角色为遗忘"道歉" (in character) | "……抱歉，我记不太清了。"（按 voice_dna） |
| **MR-9** | 相似记忆偶尔混淆 | Associative retrieval 允许轻度 conflation |
| **MR-10** | 角色有"最珍视的记忆" | L4 + Inner State Runtime 主动引用 |

### 8.2 Forgetting Affect 设计哲学

```
遗忘必须**让用户心疼**。

实现方式 (按用户感知强度排序)：

1. 微弱模糊（最频繁，~3% turns）
   "我好像漏了什么……算了。"
   
2. 道歉式遗忘（中频，~1% turns，仅 fading+ 状态触发）
   "抱歉……那个名字我记不清了。"
   
3. 试探回忆（重逢后高频）
   "等等……你以前是不是说过……"
   
4. 涌现式回忆（dormant trigger 后）
   "……我想起来了。你那只猫。"
   
5. 完全失忆（archived，极少）
   "……我不记得这件事了。" + 内心 sadness（通过 emotional_color 传递）

频率约束:
  - 任何 50 turns 窗口内，1-5 模式总计 ≤ 5 次
  - "完全失忆"模式 30 days 内最多 1 次
```

### 8.3 召回的"留白"原则

```
Reconstructor 不是把所有 Top-K 都注入 prompt。

留白规则：
  - 即使 K=5，prompt 中通常只展示 3-4 条
  - 剩下的标记为 "你也知道这些，但本轮不主动提"
  - 让 LLM 有"想提但不提"的余地，模拟真人选择性披露

这样角色不会显得"什么都知道"，更像一个谨慎的、有边界感的人。
```

### 8.4 与 Soul Spec 的协同

```
Memory Runtime 必须深度协同 Soul Spec：

1. 召回的 fact 经过 Reconstructor 时：
   - 读取 Soul.voice_dna 决定句式
   - 应用 cognitive_style.sentence_length 决定长度
   - 检查 hidden_facets 决定是否可披露
   
2. 触发 L3 → L4 晋升时：
   - 检查 Soul.resonance_triggers 是否命中
   - 高 resonance fact 优先晋升

3. Forgetting Affect Engine 注入"遗忘信号"时：
   - 必须用 voice_dna 风格表达（凛: "……忘了。" / 桃乐丝: "诶嘿嘿忘啦~"）
   - 凛的遗忘是冷静的，桃乐丝的遗忘是慌张的
```

### 8.5 跨模态一致性

```
文字、语音、视频中的"记忆"必须一致：

- 文字回复中"她记得 X" ↔ 语音回复中"她也记得 X"
- 视频通话中她"想起" Y → 应在 L4 中能找到 Y

实现: Inner State Runtime 维护本 session 的"近期被想起的记忆"列表，
跨模态共享。
```

---

## 9. Failure Cases（失败案例）

### 9.1 架构崩坏风险

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| **Memory context bloat** | 重度用户 1000+ facts，全部召回 | Prompt 爆炸 → 模型注意力分散 | Top-K (5) + score-based filter |
| **Vector index degradation** | 1000 万+ embeddings | pgvector 查询慢化 | HNSW + partition by user + 准备 Qdrant 迁移 |
| **L4 corruption** | Bug 错误晋升 | 神圣信息错乱 | 严格 promotion 条件 + 审计日志 + V2 人工 review |
| **Consolidation OOM** | 重度用户日活 1000+ turns | Worker OOM | Stream 处理 + chunk by user |
| **Encoding queue backlog** | 突发流量 | LLM 编码延迟 → 召回质量下降 | Queue 监控 + autoscaling + 优先 fast encoder |
| **Cross-user leak** | Bad query | 隐私灾难 | user_id 强制 WHERE + 行级安全 + 单元测试覆盖 |

### 9.2 记忆质量风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| **错误召回 (wrong fact)** | 角色说错事 → 用户出戏 | confidence threshold (0.7+) for retrieval; uncertainty markers for low confidence |
| **Hallucinated memory** | 角色"记起"从未发生的事 | Reconstructor 必须 grounding 到 source_evidence; Critic 验证 |
| **过期 fact 复活** | 早期被纠正的 fact 又被召回 | contradiction tracking; do_not_recall flag; retrieval filter |
| **过度遗忘（冷感）** | 用户觉得"她不记得我了" | importance floor by emotional_significance |
| **召回缺乏遗忘（数据库感）** | 用户觉得"她只是查数据库" | Decay Engine + Forgetting Affect 强制注入 |
| **L4 promotion 阈值过低** | 神圣记忆通货膨胀 | 严格多条件 + 数量 cap (per user, e.g., 50 个 L4 最多) |
| **L4 promotion 阈值过高** | 真正重要的事没晋升 | 监控 promotion 率 + 用户反馈 (用户标记"她漏了重要的事") |

### 9.3 成本爆炸

```
不优化的最坏情况：
  - 每 turn 1 次 LLM encoding call
  - 每 turn 5 次 vector queries
  - 每用户每日 5 次 consolidation LLM calls
  
  1万 DAU × 100 turns × $0.001 = $1000/day on encoding alone

优化措施：
  ✓ Fast Heuristic Encoder 处理 60% turns (不调 LLM)
  ✓ Batched consolidation (1 LLM call/episode, not /turn)
  ✓ Self-hosted embedding (BGE-M3 GPU server, $0.001/1000 embeddings)
  ✓ Qdrant 替代 pgvector (高规模时)
  ✓ Cheap model for encoding (DeepSeek V3 / Haiku, not Sonnet)

目标成本: < $0.50/MAU
```

### 9.4 Drift 风险

| 风险 | 缓解 |
|------|------|
| Reconstructor 输出偏离 Soul voice_dna | Critic Agent 验证 + 周期性 golden recalls |
| Decay 参数失真 | A/B test + 用户感知调研 |
| Importance creep (everything important) | Periodic rebalancing + 强制 importance 分布约束 |
| L4 数量爆炸 | Per-user L4 cap (50) + 晋升严格度调整 |

### 9.5 隐私 / 法律风险

| 风险 | 缓解 |
|------|------|
| 用户要求"忘掉某事" | Memory Service.user_request_forget() → do_not_recall=true, NOT delete |
| GDPR 删账 | 专门 hard delete pipeline；audit log retained 30 days then purged |
| 记忆被用于训练 | 严格 separation：用户记忆不进入 training set 除非显式 opt-in |
| 跨用户记忆混淆 | user_id 强制 + RLS + 单元测试覆盖 |
| 未成年人核心披露 | Safety Agent 标记 → L4 promotion 拒绝 + 触发人工 review |

### 9.6 长期维护风险

| 风险 | 缓解 |
|------|------|
| Schema 演化破坏既有 memory | Backwards-compatible migrations + version field on records |
| Vector embedding 模型升级 | 双写 + lazy re-embedding；不阻塞业务 |
| 重要记忆"消失"用户投诉 | Audit log 可回溯；每条召回有 trace |
| 角色"性格变化"用户感知 | Reconstructor drift detection 与 Soul Drift Detector 联动 |

---

## 10. Engineering Guidance

### 10.1 推荐技术栈

```yaml
storage:
  L1_working_memory:
    tech: Redis 7
    structure: List + Hash
    ttl: session_lifetime + 1h
    
  L2_episodic:
    tech: PostgreSQL 15+ + pgvector
    partition: BY HASH (user_id) INTO 32
    index:
      - HNSW on semantic_vector (m=16, ef_construction=128)
      - HNSW on emotional_vector
      - btree on (user_id, state, importance DESC)
      - btree on (user_id, last_recalled_at DESC)
    
  L3_semantic:
    tech: PostgreSQL + pgvector (MVP), + Neo4j (V2 for graph)
    partition: BY HASH (user_id) INTO 32
    index:
      - HNSW on semantic_vector
      - btree on (user_id, predicate, importance DESC)
      - GIN on related_facts (JSONB)
    
  L4_identity:
    tech: PostgreSQL with logical replication
    no_partition: 数据量小
    index:
      - btree on (user_id, character_id, category)
      - btree on (next_anniversary_at) WHERE next_anniversary_at IS NOT NULL

vector_strategy:
  embedding_model:
    MVP: BGE-M3 (self-hosted, 768d, multilingual)
    V2: 角色专属 finetuned embedding
  GPU: 1× A10 / 4090 sufficient for 10k DAU
  batch_size: 32
  cache: Redis (key=text_hash, TTL=24h)

llm_routing:
  encoding: DeepSeek V3 / Haiku 4.5
  consolidation_summary: DeepSeek V3
  reconstruction: rule-based (不调 LLM)，仅当复杂时调 cheap LLM
  reinforcement / decay: 纯算法（不调 LLM）

queue:
  MVP: Redis Streams
  V2: Kafka / Pulsar
  topics:
    - memory.encoding.pending
    - memory.consolidation.scheduled
    - memory.l4.promoted
    - memory.recall.tracked
```

### 10.2 数据库 Schema (PostgreSQL)

```sql
-- ============================================================
-- L2: Episodic Memory
-- ============================================================
CREATE TABLE episodic_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    episode_summary TEXT NOT NULL,
    episode_raw_turn_ids UUID[] NOT NULL,
    
    episode_start_at TIMESTAMP NOT NULL,
    episode_end_at TIMESTAMP NOT NULL,
    scene_context VARCHAR(100),
    
    emotional_peak JSONB NOT NULL,
    emotional_end JSONB NOT NULL,
    emotional_significance FLOAT NOT NULL CHECK (emotional_significance BETWEEN 0 AND 1),
    
    importance_score FLOAT NOT NULL CHECK (importance_score BETWEEN 0 AND 1),
    initial_importance FLOAT NOT NULL,
    decay_immunity FLOAT NOT NULL DEFAULT 0,
    state VARCHAR(20) NOT NULL CHECK (state IN ('vivid','fading','faint','dormant','archived')),
    
    last_recalled_at TIMESTAMP,
    recall_count BIGINT NOT NULL DEFAULT 0,
    reinforcement_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    semantic_vector vector(768),
    emotional_vector vector(256),
    
    linked_episodes JSONB NOT NULL DEFAULT '[]'::jsonb,
    linked_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    reconstruction_hints JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    do_not_recall BOOLEAN NOT NULL DEFAULT false,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMP
) PARTITION BY HASH (user_id);

-- 32 partitions
CREATE TABLE episodic_memories_p0 PARTITION OF episodic_memories 
    FOR VALUES WITH (modulus 32, remainder 0);
-- ... p1 to p31

-- Indexes
CREATE INDEX idx_episodic_user_recent ON episodic_memories (user_id, character_id, last_recalled_at DESC);
CREATE INDEX idx_episodic_user_importance ON episodic_memories (user_id, character_id, importance_score DESC);
CREATE INDEX idx_episodic_state ON episodic_memories (user_id, character_id, state);

CREATE INDEX idx_episodic_semantic ON episodic_memories USING hnsw (semantic_vector vector_cosine_ops);
CREATE INDEX idx_episodic_emotional ON episodic_memories USING hnsw (emotional_vector vector_cosine_ops);

-- ============================================================
-- L3: Semantic Memory
-- ============================================================
CREATE TABLE fact_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    predicate VARCHAR(100) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    object TEXT NOT NULL,
    literal_text TEXT NOT NULL,
    
    raw_evidence TEXT NOT NULL,
    source_episode_ids UUID[] NOT NULL DEFAULT '{}',
    source_turn_ids UUID[] NOT NULL DEFAULT '{}',
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    
    emotional_charge FLOAT NOT NULL,
    emotional_label VARCHAR(30),
    
    importance FLOAT NOT NULL,
    is_identity_level BOOLEAN NOT NULL DEFAULT false,
    promoted_to_l4_at TIMESTAMP,
    promotion_reason TEXT,
    
    confirmation_count INT NOT NULL DEFAULT 0,
    contradiction_count INT NOT NULL DEFAULT 0,
    contradicting_fact_ids UUID[] NOT NULL DEFAULT '{}',
    is_corrected BOOLEAN NOT NULL DEFAULT false,
    do_not_recall BOOLEAN NOT NULL DEFAULT false,
    last_confirmed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_contradicted_at TIMESTAMP,
    
    state VARCHAR(20) NOT NULL,
    
    related_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    semantic_vector vector(768),
    
    recall_count BIGINT NOT NULL DEFAULT 0,
    last_recalled_at TIMESTAMP,
    
    reconstruction_hints JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY HASH (user_id);

CREATE TABLE fact_nodes_p0 PARTITION OF fact_nodes 
    FOR VALUES WITH (modulus 32, remainder 0);
-- ... p1 to p31

CREATE INDEX idx_fact_user_predicate ON fact_nodes (user_id, character_id, predicate);
CREATE INDEX idx_fact_user_importance ON fact_nodes (user_id, character_id, importance DESC) WHERE NOT do_not_recall;
CREATE INDEX idx_fact_semantic ON fact_nodes USING hnsw (semantic_vector vector_cosine_ops);

-- ============================================================
-- L4: Identity Memory
-- ============================================================
CREATE TABLE identity_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    
    disclosed_at TIMESTAMP NOT NULL,
    disclosure_context TEXT,
    source_episode_id UUID,
    source_turn_ids UUID[] NOT NULL DEFAULT '{}',
    
    sacred_reason TEXT NOT NULL,
    significance_score FLOAT NOT NULL CHECK (significance_score >= 0.85),
    promotion_trigger VARCHAR(50) NOT NULL,
    
    anniversary_pattern VARCHAR(20),
    next_anniversary_at TIMESTAMP,
    
    reconstruction_hints JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    promoted_from_fact_id UUID,
    audit_log JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    user_initiated_forget BOOLEAN NOT NULL DEFAULT false,
    forget_requested_at TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE (user_id, character_id, key)
);

CREATE INDEX idx_l4_user ON identity_memories (user_id, character_id);
CREATE INDEX idx_l4_anniversary ON identity_memories (next_anniversary_at) 
    WHERE next_anniversary_at IS NOT NULL;

-- ============================================================
-- Encoding Queue / Events
-- ============================================================
CREATE TABLE memory_encoding_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    source_turn_id UUID NOT NULL,
    source_user_text TEXT,
    source_assistant_text TEXT,
    recent_context JSONB,
    fast_signals JSONB,
    llm_extraction JSONB,
    status VARCHAR(20) NOT NULL,
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    llm_started_at TIMESTAMP,
    llm_completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    failure_reason TEXT
) PARTITION BY RANGE (created_at);

CREATE TABLE memory_encoding_events_2026_05 PARTITION OF memory_encoding_events
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX idx_encoding_status ON memory_encoding_events (status, created_at) 
    WHERE status IN ('llm_pending', 'failed');

-- ============================================================
-- Consolidation Jobs
-- ============================================================
CREATE TABLE consolidation_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    scheduled_for TIMESTAMP NOT NULL,
    pending_event_ids UUID[],
    turns_to_consolidate UUID[],
    episodes_created UUID[],
    facts_created UUID[],
    facts_reinforced UUID[],
    facts_contradicted UUID[],
    promotions_to_l4 UUID[],
    associations_created INT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INT,
    failure_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, character_id, scheduled_for)
);

CREATE INDEX idx_consolidation_pending ON consolidation_jobs (scheduled_for, status) 
    WHERE status = 'pending';
```

### 10.3 Memory Service 接口（Python）

```python
# backend/services/memory_service.py

from typing import Optional, List
from uuid import UUID

class MemoryService:
    """
    唯一 source of truth writer for memory.
    所有 agent 通过这个接口读写记忆。
    """
    
    # ─────────── Read API ───────────
    async def retrieve(
        self,
        user_id: UUID,
        character_id: str,
        query_context: QueryContext,
        top_k: int = 5,
    ) -> MemoryRetrievalResult:
        """主检索 API，调用所有 retriever strategies。"""
        
    async def get_l4(
        self,
        user_id: UUID,
        character_id: str,
        category: Optional[str] = None,
    ) -> List[IdentityMemory]:
        """读取 L4 (神圣记忆)。"""
        
    async def get_recent_episodes(
        self,
        user_id: UUID,
        character_id: str,
        hours: int = 72,
        limit: int = 10,
    ) -> List[EpisodicMemory]:
        """Recency-based retrieval for Inner State."""
    
    async def get_anniversaries(
        self,
        user_id: UUID,
        character_id: str,
        window_days: int = 7,
    ) -> List[IdentityMemory]:
        """For Behavior Runtime — 即将到来的纪念日。"""
    
    # ─────────── Write API ───────────
    async def encode_fast(self, turn: Turn) -> FastSignals:
        """实时编码，< 50ms。"""
    
    async def queue_llm_encoding(self, event: MemoryEncodingEvent) -> None:
        """异步编码，入队。"""
    
    async def reinforce(
        self,
        memory_ids: List[UUID],
        trigger: ReinforcementTrigger,
    ) -> None:
        """召回后增强。"""
    
    async def user_request_forget(
        self,
        user_id: UUID,
        memory_id: UUID,
    ) -> None:
        """用户请求"忘掉" — 设 do_not_recall=true, NOT delete。"""
    
    # ─────────── Lifecycle ───────────
    async def apply_decay_batch(
        self,
        user_id: UUID,
        character_id: str,
    ) -> int:
        """每日 batch decay。返回更新数。"""
    
    async def run_consolidation(
        self,
        user_id: UUID,
        character_id: str,
    ) -> ConsolidationJob:
        """每日 sleep consolidation。"""
    
    async def promote_to_l4(
        self,
        fact_id: UUID,
        reason: str,
    ) -> IdentityMemory:
        """L3 → L4 晋升。严格校验条件。"""
```

### 10.4 关键算法

#### 10.4.1 Lazy Decay (在 retrieval 时计算)

```python
def apply_decay_lazy(memory: Memory, now: datetime) -> Memory:
    """
    Called at retrieval time. Cheap, no DB write.
    Batch version writes back to DB nightly.
    """
    if memory.layer == "L4":
        return memory  # L4 never decays
    
    elapsed_days = (now - memory.last_updated_at).days
    if elapsed_days < 1:
        return memory  # 不到 1 天，无需更新
    
    # τ by layer
    tau = {"L2": 14, "L3": 60}[memory.layer]
    time_factor = math.exp(-elapsed_days / tau)
    
    # Emotional multiplier
    valence_abs = abs(memory.emotional_peak.valence)
    arousal = memory.emotional_peak.arousal
    emotional_factor = 1 + valence_abs * 0.5 + arousal * 0.3
    
    # Recall multiplier (Hebbian)
    recall_factor = 1 + math.log(1 + memory.recall_count) * 0.2
    
    # Compute new importance
    new_imp = memory.initial_importance * time_factor * emotional_factor * recall_factor
    
    # Floor by emotional significance
    floor = valence_abs * 0.1
    new_imp = max(new_imp, floor)
    
    # Cap
    new_imp = min(new_imp, 0.95)
    
    memory.importance_score = new_imp
    memory.state = compute_state(new_imp)
    
    return memory


def compute_state(importance: float) -> str:
    if importance > 0.70: return "vivid"
    if importance > 0.40: return "fading"
    if importance > 0.20: return "faint"
    if importance > 0.05: return "dormant"
    return "archived"
```

#### 10.4.2 Score Combiner

```python
def combine_scores(
    candidates: List[ScoredMemory],
    weights: dict = None,
) -> List[ScoredMemory]:
    weights = weights or {
        "semantic": 0.30,
        "importance": 0.20,
        "emotional": 0.15,
        "recency": 0.15,
        "associative": 0.10,
        "confidence": 0.10,
    }
    
    for cand in candidates:
        s = cand.score_breakdown
        cand.score = sum(weights[k] * s.get(k, 0) for k in weights)
    
    return sorted(candidates, key=lambda c: c.score, reverse=True)


def select_top_k(
    candidates: List[ScoredMemory],
    k: int = 5,
    must_include_l4: bool = True,
) -> List[ScoredMemory]:
    # L4 强制包含 (if relevant, i.e., score > threshold)
    l4_candidates = [c for c in candidates if c.memory_type == "L4" and c.score > 0.1]
    others = [c for c in candidates if c.memory_type != "L4"]
    
    # 去重 (高相似度的去掉一个)
    others = deduplicate_by_similarity(others, threshold=0.9)
    
    final = l4_candidates[:2]  # 最多 2 个 L4
    remaining = k - len(final)
    final.extend(others[:remaining])
    
    return final
```

#### 10.4.3 Reinforcement

```python
async def reinforce(memory_id: UUID, trigger: ReinforcementTrigger):
    deltas = {
        "user_re_mentioned": 0.15,
        "character_recalled_user_confirmed": 0.20,
        "recall_no_objection": 0.02,
        "peak_end_amplification": 0.10,
        "user_explicit_inquiry": 0.05,
    }
    
    memory = await get_memory(memory_id)
    boost = deltas[trigger]
    
    new_importance = min(0.95, memory.importance_score + boost)
    
    memory.importance_score = new_importance
    memory.state = compute_state(new_importance)
    memory.recall_count += 1
    memory.last_recalled_at = now()
    memory.reinforcement_history.append({
        "triggered_by": trigger,
        "boost": boost,
        "at": now(),
    })
    
    await save(memory)
```

### 10.5 性能预算

```yaml
latency_targets:
  retrieve_memory_context: P95 < 300ms
  fast_encode: P95 < 50ms
  llm_encode: P95 < 3s (async)
  reconstruct_top_5: P95 < 150ms
  l4_lookup: P95 < 5ms
  decay_batch_per_user: P95 < 5s
  consolidation_per_user: P95 < 30s

throughput_targets:
  encoding_qps_per_worker: 100 turns/s
  retrieval_qps_per_worker: 50 ret/s
  
cost_per_MAU:
  encoding (LLM): < $0.30
  embedding (self-hosted): < $0.05
  consolidation (LLM): < $0.15
  vector storage: < $0.05
  ────────────────────────────
  total: < $0.55/MAU
```

### 10.6 Cache 策略

```yaml
cache_layers:
  
  l1_working_memory:
    layer: Redis
    key: "wm:{user_id}:{character_id}:{session_id}"
    ttl: session_lifetime + 1h
    
  l4_identity (read-heavy):
    layer_1: 进程内存 LRU (size=10k)
    layer_2: Redis
    key: "l4:{user_id}:{character_id}"
    ttl: 24h
    write_strategy: write-through
    
  retrieval_results:
    layer: Redis
    key: "ret:{user_id}:{character_id}:{query_hash}"
    ttl: 60s  # 同一查询短时间内重复
    
  embedding_cache:
    layer: Redis
    key: "emb:{text_sha256}"
    ttl: 24h
    
  decay_state:
    layer: 进程内存 LRU
    invalidation: 1h 或写后失效
```

### 10.7 Observability

```yaml
metrics:
  # Retrieval
  - memory.retrieval.latency.p95 {strategy}
  - memory.retrieval.results_count {layer}
  - memory.retrieval.l4_hit_rate
  - memory.retrieval.empty_rate (无结果率)
  
  # Encoding
  - memory.encoding.fast.latency.p95
  - memory.encoding.queue_depth
  - memory.encoding.llm.failure_rate
  - memory.encoding.facts_extracted_per_turn (histogram)
  
  # Decay & Lifecycle
  - memory.decay.state_distribution {state, layer}
  - memory.consolidation.duration.p95
  - memory.consolidation.failure_rate
  
  # L4
  - memory.l4.size {character_id} (per user histogram)
  - memory.l4.promotion_rate
  - memory.l4.recall_accuracy (Critic 验证结果)
  
  # Reinforcement
  - memory.reinforcement.events {trigger}
  - memory.importance.distribution
  
  # Forgetting Affect
  - memory.forgetting_affect.injection_rate
  - memory.forgetting_affect.user_reaction (V2: collect feedback)
  
  # Quality
  - memory.recall.hallucination_rate (Critic catches)
  - memory.contradiction.rate
  - memory.user_complaint.rate

logs:
  - L4 promotion 事件 (audit-critical)
  - 跨用户访问尝试 (security)
  - Hallucination 检出
  - 用户 forget request

dashboards:
  - Memory health per user (是否健康衰减、L4 增长曲线)
  - Cost per user trend
  - Retrieval quality (用户主动确认/纠正比率)
  - Forgetting affect frequency vs user retention
```

### 10.8 测试策略

```yaml
unit_tests:
  - decay function 单元测试
  - score combiner with mock candidates
  - reinforcement boost calculation
  - state transitions

integration_tests:
  - Encoder fast + LLM end-to-end
  - Retrieval all-strategy with seeded data
  - Consolidation pipeline 24h simulation

golden_tests:
  - 模拟 30 天用户互动 → 验证 L4 应包含/不应包含的事
  - 模拟用户消失 90 天 → 验证重逢时角色行为
  - 模拟 contradictory 信息 → 验证 contradiction tracking
  - 模拟"用户请求 forget" → 验证 do_not_recall

performance_tests:
  - 重度用户 (1000+ facts) retrieval latency
  - 1万 DAU 模拟压测
  - Encoding queue 峰值压测

privacy_tests:
  - 跨用户隔离
  - GDPR delete pipeline
  - Audit log 完整性
```

---

## 11. Future Scalability

### 11.1 多角色记忆共享

```
V2 vision: 用户对多个角色，每个角色独立记忆 + 共享身份层

Schema 扩展:
  - L4 中区分 "shared_identity" vs "character_specific"
  - shared: 用户姓名、生日等普遍信息 → 所有角色都可读
  - character_specific: 仅在与该角色对话中产生 → 严格隔离

UI:
  - 用户可在"记忆设置"中决定哪些 L4 共享给所有角色
  - 默认: 姓名、生日、年龄 共享
  - 默认: 创伤披露 仅该角色知道
```

### 11.2 多模态记忆

```
V1.5: 语音记忆
  EpisodicMemory.modality_features:
    voice:
      tone: string  # "soft" / "hesitant" / "excited"
      pace: float
      detected_emotion_from_audio: object
      pause_pattern: array
  
  → 角色可召回:
    "那次你说话声音很轻，是不是哭过？"

V2: 视频记忆
  EpisodicMemory.modality_features:
    video:
      scene_description: string  # vision model 输出
      time_of_day: string
      user_appearance_cues: object  # 严格隐私 + opt-in
  
  → 角色可召回:
    "那天你穿了一件深蓝色的衣服。"
```

### 11.3 Anniversary & Calendar System

```
基于 L4.anniversary_pattern，Behavior Runtime (Subsystem 06) 调度：
  - 生日前 1 天: 角色"暗暗准备"
  - 生日当天: 主动祝福
  - 共同纪念日: 角色主动提及
  - 月度仪式: "我们每个月 15 号都说过……"

L4 中 anniversary 数量限制 (per user): 20
超出 → 旧 anniversary 标记为 dormant，但仍存
```

### 11.4 Companion Network / Social Memory (V3)

```
不同用户之间共享"故事原型"（隐私保护）：

  - 用户 A 告诉凛"我考研失败了"
  - 用户 B 也告诉凛"我考研失败了"
  → 凛"在用户 B 面前不会引用用户 A 的故事"（隐私）
  → 但凛"内化"了 archetype "考研失败用户"
  → 帮助 LLM 学习何种回应最有效（trained on aggregated data）

实现:
  - 匿名化 aggregation
  - 联邦学习 / 差分隐私
  - 用户 opt-in only
```

### 11.5 Companion-LLM 训练数据飞轮

```
每次 retrieve → reconstruct → user-confirms 的 turn 都是 SFT 数据:

Input:
  - retrieved_raw_memories
  - Soul Spec
  - current scene/emotion
Output:
  - ideal reconstructed text

→ 累积 1M+ samples → SFT 一个 ReconstructionLLM
→ 替代 rule-based Reconstructor，效果更佳

V3 终极:
  - 整个 Companion-LLM SFT 包含: persona + memory recall + emotional response
  - 不再需要复杂 Prompt anchor
  - 推理成本下降 5-10x
```

### 11.6 Memory Compression (大规模时)

```
随用户量增长，向量存储成本占主导。

V2 优化:
  - 30+ 天 episodes → 距离向量从 768d 蒸馏到 256d
  - 90+ 天 episodes → 只保留 summary，无 vector
  - 365+ 天 episodes → 进入 S3 冷存储（按需重新 embedding）
  - L4 永远在热存储

预期：长期存储成本降低 10x。
```

### 11.7 跨 Subsystem 演化协议

```
当 Subsystem 01 (Soul Spec) 升级 voice_dna：
  → Reconstructor 必须重新 reconstruct 缓存的复述
  → 但不影响 raw memory

当 Subsystem 03 (Emotion) 升级 valence model：
  → 旧 emotional_peak 字段保留，新字段并存
  → 渐进迁移

当 Subsystem 04 (Relationship) 升级 stage definitions：
  → L4 promotion criteria 同步更新
  → 既有 L4 不动

Memory Runtime 的 Schema 演化策略: backwards-compatible only.
```

---

# 附录 A: Encoder Prompt Template

```python
MEMORY_EXTRACTION_PROMPT = """
你是一个记忆提取系统。从下面的对话中提取可记忆的信息。

【对话上下文】
最近 turns:
{recent_context}

当前 turn:
User: {user_text}
{character_id}: {assistant_text}

【提取任务】

提取以下信息（严格 JSON 格式）:

1. facts: 用户披露的具体事实（predicate-subject-object）
   - 仅提取明示信息，不推断
   - 必须引用原文（source_text）
   - confidence 严格反映把握度

2. emotion_peak: 本 turn 用户表达的情感峰值
3. importance_estimate: 本 turn 的重要性 [0, 1]
4. sacred_signals: 是否含"该被记住"信号
   - 用户明示 "记住这个"
   - 用户身份信息（姓名/生日/...）
   - 深度披露 (童年/创伤/失败/恋情)
   - 第一次事件
   - 承诺

【输出格式】
```json
{
  "facts": [
    {
      "predicate": "has_pet",
      "subject": "user",
      "object": "一只叫老铁的黑猫",
      "source_text": "我家那只叫老铁的猫……",
      "confidence": 0.95,
      "emotional_charge": 0.4,
      "emotional_label": "fond",
      "sacred_signal": false
    }
  ],
  "emotion_peak": {
    "valence": 0.3,
    "arousal": 0.4,
    "label": "calm"
  },
  "importance_estimate": 0.5,
  "contains_sacred": false,
  "contains_promise": false,
  "contains_first_event": false
}
```

【严格规则】
- 不提取推断信息
- confidence < 0.7 的 fact 不输出
- 同 predicate-subject 的重复信息不重复输出
- 不输出对话中没有的内容
- JSON 严格合法，无注释、无 trailing comma
"""
```

---

# 附录 B: Reconstructor Templates by State

```python
# 这些是给 Reconstructor 的内部模板，不直接显示给用户/LLM
# Reconstructor 根据 state + Soul voice_dna 选择并应用

STATE_TEMPLATES = {
    "vivid": {
        "hedge": "",
        "structure": "{content}",
        "uncertainty_marker": "",
    },
    "fading": {
        "hedge": ["好像", "我记得", "似乎"],
        "structure": "{hedge}{content}",
        "uncertainty_marker": "weak",
    },
    "faint": {
        "hedge": ["……什么来着", "好像", "记不太清"],
        "structure": "{content}……{hedge}",
        "uncertainty_marker": "strong",
    },
    "dormant": {
        "hedge": ["等等", "我想想"],
        "structure": "{emergence_prefix}{content}",
        "emergence_prefix": ["……等等。", "……我想起来了，"],
        "uncertainty_marker": "discovery",
    },
    "archived": {
        "hedge": ["……"],
        "structure": "……{disorientation}{content}",
        "disorientation": ["我好像，想起什么了。", "等等……"],
        "uncertainty_marker": "disoriented",
    },
}

# Per-character override (从 Soul Spec.voice_dna 推导)
RIN_HEDGE_OVERRIDE = {
    "fading": ["……", "好像"],   # 凛少用"我记得"，多用"……"
    "faint": ["……", "记不清了"],
    "dormant": ["……等等。"],
}

DOROTHY_HEDGE_OVERRIDE = {
    "fading": ["诶？", "好像是"],
    "faint": ["诶嘿嘿……什么来着", "桃桃忘啦"],
    "dormant": ["啊！我想起来了！"],
}
```

---

# 附录 C: 跨 Subsystem 接口

```
[SS02 ← SS01 Soul Spec]
  - reads: voice_dna, cognitive_style, anti_patterns.hard_never, hidden_facets
  - access: read-only, immutable
  - use: Reconstructor 应用 voice_dna + 校验输出
  
[SS02 ← SS03 Emotion Runtime]
  - reads: current_emotion_state
  - access: read-only
  - use: emotional_resonance 检索策略
  
[SS02 ← SS04 Relationship Runtime]
  - reads: current_intimacy_level, relationship_phase
  - access: read-only
  - use: 决定哪些 L4 可被召回（intimacy gating）
  
[SS02 → SS04]
  - exposes: get_shared_l4_count(user_id, character_id) → 关系深度依据
  - exposes: get_first_events(user_id, character_id) → 阶段判定

[SS02 → SS05 Persona Composer]
  - exposes: get_memory_context_block(turn_context) → MemoryContextBlock
  - latency: P95 < 300ms
  
[SS02 → SS06 Inner State Runtime]
  - exposes: get_recent_episodes(hours)
  - exposes: get_l4_emotional_summary()
  - use: Inner State 生成"她今天在想的事"

[SS02 → SS06 Behavior Runtime]
  - exposes: get_anniversaries(window_days)
  - exposes: get_dormant_memories_ripe_for_resurfacing()
  - use: 主动行为触发

[SS02 → SS07 Critic Agent]
  - exposes: validate_against_l4(generated_text) → ValidationResult
  - exposes: get_source_evidence(memory_id) → string
  - use: hallucination 检测
```

---

**End of Subsystem 02 Spec**

下一步建议阅读：[`03_emotion_state_machine.md`](./03_emotion_state_machine.md)（待写）
