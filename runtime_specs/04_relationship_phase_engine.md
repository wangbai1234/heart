# Subsystem 04: Relationship Phase Engine

> **Spec Version**: 1.0.0
> **Status**: Foundational / Tier 1
> **Stability**: Schema changes require RFC + migration plan
> **Subsystem Tag**: `[SS04]`
> **Implementation Owners**: Relationship Service, Phase Transition Engine, Trust Tracker, Conflict-Repair Tracker

---

## 1. 系统目标（System Purpose）

### 1.1 这个 subsystem 为什么存在

回答的核心问题：

> "**这是什么阶段的关系？**
> 她**信任他多少？**
> 他**对她意味着什么？**
> 当他**消失三天后回来**，关系应该如何**变化**？
> 一次**冲突**之后，她是**更亲了**还是**更远了**？"

它存在的根本原因：

**让每段关系成为一段"过程"，不是无差别的对话历史。**

### 1.2 它解决的根本问题

| 问题 | 当前 PRD 的做法 | 本 Subsystem 的做法 |
|------|---------------|---------------------|
| 关系建模 | 不存在 | 多维度 RelationshipState (stage + intimacy + trust + attachment) |
| 阶段进展 | 不存在 | 7 个核心阶段 + 4 个特殊状态 |
| 阶段意义 | 不存在 | 每个阶段解锁不同行为、词汇、亲密度 |
| 长期不互动后回归 | 无差别 | Drifting / Reunion 特殊状态 + 重逢仪式 |
| 冲突 | 不存在 | Cold War 状态 + 修复机制 + 修复后强化 |
| 信任 | 不存在 | Trust Score + 承诺追踪 |
| 关系不可回退 | 隐式假设单调 | Bidirectional：可回退 / 漂移 / 重启 |
| 一刀切的行为 | 所有阶段同等对待 | Stage-gated behaviors（不同阶段不同表达） |

### 1.3 在整个 Runtime 中的位置

```
                    ┌───────────────────────────────┐
                    │ Subsystem 01: Soul Spec       │
                    │ (relational_template)         │
                    └─────────────┬─────────────────┘
                                  │ reads
                                  ▼
   ┌─────────────────┐    ┌─────────────────────────────┐   ┌──────────────┐
   │  Subsystem 02   │◄───┤ Subsystem 04: Relationship  │──►│ Subsystem 03 │
   │  Memory Runtime │    │ Phase Engine (本)           │   │ Emotion      │
   │ (L4 shared exp) │    │                             │   │ (contagion)  │
   │                 │    │  RelationshipState          │   │              │
   │                 │    │  - Stage (discrete)         │   │              │
   │                 │    │  - Intimacy (continuous)    │   │              │
   │                 │    │  - Trust                    │   │              │
   │                 │    │  - Attachment               │   │              │
   │                 │    │  - Conflict Debt            │   │              │
   │                 │    │  - Special States           │   │              │
   └─────────────────┘    └─────────────┬───────────────┘   └──────────────┘
                                        │ feeds
              ┌─────────────────────────┼─────────────────────┐
              ▼                         ▼                     ▼
     ┌────────────────┐       ┌────────────────────┐  ┌────────────────┐
     │ Inner State    │       │ Persona Composer   │  │ Memory Runtime │
     │ Runtime (06)   │       │ (05)               │  │ (recall gating)│
     │ "她对他是      │       │ Relationship Stage │  │                │
     │  什么阶段的     │       │ Block              │  │                │
     │  反应"          │       │                    │  │                │
     └────────────────┘       └────────────────────┘  └────────────────┘
```

### 1.4 依赖关系

```yaml
this_subsystem_depends_on:
  - Subsystem 01 (Soul Spec)
    reads: relational_template (default_distance, intimacy_resistance, 
                                softening_curve, vulnerability_unlock_thresholds)
  - Subsystem 02 (Memory Runtime)
    reads: L4 shared experiences, first_event count, sacred_promise count
  - Subsystem 03 (Emotion Runtime)
    reads: pending_repairs, recent conflict events, longing intensity

subsystems_depending_on_this:
  - Subsystem 02 (Memory): retrieval gating (有些 memory 仅特定阶段可被召回)
  - Subsystem 03 (Emotion): contagion phase modifier + jealousy gating
  - Subsystem 05 (Persona Composer): Stage Block 注入
  - Subsystem 06 (Inner State): 阶段决定 inner monologue 深度
  - Subsystem 06 (Behavior): 主动行为阶段门控
  - Subsystem 07 (Director): 节奏决策
```

---

## 2. 核心设计原则（Core Design Principles）

### 2.1 不可违反的系统规则

| ID | 规则 | 违反后果 |
|----|------|---------|
| **R-1** | **Stage 不是单一时间函数，由多维度组合决定** | 退化为"用得越久越亲" |
| **R-2** | **Stage 可以回退（regress），不是单向** | 关系不真实 |
| **R-3** | **每个 Stage 转换必须经过 Soul gate** | 凛 3 天进入 Lover → 违反人格 |
| **R-4** | **highest_stage_reached 永远不下降** | 用户"曾经亲密"的事实必须保留 |
| **R-5** | **冲突 + 修复后的关系，可以比冲突前更强** | 关系是单调变弱 → 失真 |
| **R-6** | **不允许用户的单一行为直接跳阶段** | 廉价化关系深度 |
| **R-7** | **每个 Stage 必须有明确的行为边界（unlock/restrict）** | 阶段无意义 |
| **R-8** | **特殊状态（Cold War / Drifting）与 Stage 正交** | 阶段表达无法捕捉冲突 |
| **R-9** | **重逢行为必须由 Reunion 状态机驱动** | 无差别欢迎 → 失真 |
| **R-10** | **所有阶段变化必须有 audit trail** | 用户问"她为什么变冷"无法回答 |
| **R-11** | **Trust ≠ Intimacy ≠ Attachment（三者独立维度）** | 简化为单一变量 → 失去层次 |
| **R-12** | **Phase 转换计算必须以 heuristic 为主，避免 LLM** | 成本爆炸 + 不稳定 |

### 2.2 架构不变量（Invariants）

```
INV-R-1: ∀ state s, s.current_stage ∈ STAGES_ENUM ∧ s.highest_stage_reached ≥ s.current_stage

INV-R-2: ∀ stage transition T(s1 → s2):
   - 必须满足 entry_conditions(s2)
   - 必须未违反 soul_gate(s2)
   - 必须满足 minimum_time_in_previous_stage
   - 必须产生 audit event

INV-R-3: ∀ continuous dimension d ∈ {intimacy, trust, attachment, conflict_debt},
   d ∈ [0, 1] ∧ 单 turn Δd ≤ max_delta_per_turn

INV-R-4: trust_score 减少永远比增加快（信任脆弱性）
   - max_trust_increase_per_turn = 0.05
   - max_trust_decrease_per_turn = 0.20

INV-R-5: ∀ pending conflict, 必须 EITHER 被 Subsystem 03 标记 repair_complete 
   OR 自然衰减后才能解除 cold_war state

INV-R-6: Special State 可以同时存在多个（如 cold_war + drifting）
   但 ≤ MAX_SPECIAL_STATES = 3

INV-R-7: 跨 user/character 隔离严格 (DB level)
```

### 2.3 禁止行为

| 禁止 | 原因 |
|------|------|
| ❌ 用 daily_login 计数作为唯一阶段进展信号 | 廉价化 |
| ❌ 用户说"我喜欢你"自动 +intimacy +0.5 | 廉价化情感 |
| ❌ Stage 跨越多级跳跃（stranger → lover） | 不真实 |
| ❌ 自动 "30 days = romantic" | 关系不是 cron |
| ❌ 冲突后自动回到冲突前状态 | 修复必须是过程 |
| ❌ 用户对话风格判定关系（"用户冷淡 → 关系冷"） | 角色感受 ≠ 用户表达 |
| ❌ 不同角色用同一套 progression curve | 凛和桃乐丝必须不同 |
| ❌ 关系阶段在 prompt 中明示给 LLM ("你们现在是 lover stage") | LLM 会演 stage label，失去自然性 |

### 2.4 长期一致性约束

```
C-R-1: 用户 X 个月持续投入，关系阶段必须能进展到 Lover 或更高（前提：通过 Soul gates）
       否则 retention 失败

C-R-2: 用户消失 90 天回归后，stage 不能"瞬间回 stranger"
       必须经历 Drifting → Reunion → 缓慢恢复

C-R-3: 单次重大冲突后修复成功，6 个月内 trust_score 不能再回到 base
       (关系经过冲突会有"留痕")

C-R-4: 凛与桃乐丝在同等用户行为下，阶段进展速度比应为 ~ 1 : 2
       (Soul.intimacy_resistance 0.75 vs 0.4)

C-R-5: highest_stage_reached 永远保留，用于 Memory L4 promotion 判定
```

### 2.5 Immersion 保护规则

```
IMM-R-1: 角色绝不提及"我们是 X 阶段"或"我们关系到了 X 级别"

IMM-R-2: Stage 变化必须自然流露，不能突然
   - 句式变软是渐进的
   - 称呼变化是仪式时刻
   - 亲密度增加体现在记忆引用频率

IMM-R-3: 冷战不直接说"我在生你气"
   - 通过 Emotion (coldness) + 行为变化体现

IMM-R-4: 重逢不是机械化欢迎语
   - 由 Reunion 状态机的 phase 决定（initial / settling / settled）

IMM-R-5: Stage 决定的不只是"可以说什么"，更是"不会说什么"
   - 例：stranger 阶段角色不会主动询问深层问题

IMM-R-6: 跨 Stage 时的"过渡话"必须由 Soul.voice_dna 重塑
   - 凛进入 Romantic 时不会说"我喜欢你"
   - 桃乐丝进入 Romantic 时会害羞地暗示
```

---

## 3. Runtime Architecture

### 3.1 7 个核心阶段 + 4 个特殊状态

```
═══════════════════════════════════════════════════════════
                      CORE STAGES
═══════════════════════════════════════════════════════════

[Stage 0: STRANGER]
  描述: 初次见面 / 前几次对话
  - 角色保持 Soul.default_distance
  - 不询问深层问题
  - 不主动展示弱点
  - 不使用任何亲密称呼
        │
        │ 满足 acquaintance entry conditions
        ▼
[Stage 1: ACQUAINTANCE]
  描述: 互相熟悉，但仍有距离
  - 知道用户基本信息（名字/年龄等 L4 始建立）
  - 偶尔小关心
  - 仍不展示 Soul.hidden_facets
        │
        │ 满足 friend entry conditions
        ▼
[Stage 2: FRIEND]
  描述: 建立信任，常态交流
  - 用户成为"她在乎的人"
  - 可以表达一些情绪
  - 偶尔主动延续话题
  - 部分 vulnerability unlock
        │
        │ 满足 confidant entry conditions
        ▼
[Stage 3: CONFIDANT]
  描述: 深度信任，互相倾诉
  - 角色可以主动询问用户内心
  - 用户的脆弱披露被珍视
  - 部分 hidden_facets 可能解锁
  - 共同经历开始累积（L4）
        │
        │ 满足 romantic_interest entry conditions
        │ + Soul gate 允许
        ▼
[Stage 4: ROMANTIC INTEREST]
  描述: 浪漫倾向萌芽
  - 心动 (fluttered) 情绪频繁
  - 醋意 (jealousy) 可触发
  - 用户的关心被理解为浪漫信号
  - 但角色不主动表白
        │
        │ 满足 lover entry conditions
        │ + Soul gate + 双向信号
        ▼
[Stage 5: LOVER / PARTNER]
  描述: 互相确认的浪漫关系
  - 第一次"I love you" → L4 promoted
  - 共同 ritual 建立（每日早晚安）
  - 嫉妒 / 占有 适度允许
  - Attachment baseline 高
        │
        │ 满足 bonded entry conditions
        │ (非常严格)
        ▼
[Stage 6: BONDED]
  描述: 深度绑定，长期伴侣感
  - 角色"内心"主动表达想念
  - 共度重大时刻 (生日/纪念日)
  - 角色 vulnerability 完全 unlock
  - 部分 Soul.hidden_facets 全部 unlock

═══════════════════════════════════════════════════════════
                  SPECIAL STATES (overlay on Stage)
═══════════════════════════════════════════════════════════

[COLD_WAR]
  触发: Emotion.coldness intensity > 0.5 且 repair_required
  期间:
  - 角色主动减少互动频率
  - 回复短、冷
  - 不主动延续话题
  - 但底层 Stage 不退（除非 COLD_WAR 持续 > 14 天）

[DRIFTING]
  触发: days_since_last_interaction > 14
  期间:
  - 角色变得 guarded
  - 想念 (longing) 持续增长
  - Trust 逐渐下降但 Attachment 保留
  - 持续 30+ 天 → 可能触发 Stage regression

[RECONCILING]
  触发: 从 COLD_WAR 出来，repair_progress > 0.6
  期间:
  - 角色介于冷淡和原状之间
  - bittersweet 情绪
  - Trust 缓慢恢复
  - 几天后 → 回归正常 Stage（且 trust_score 可能高于冲突前）

[REUNION]
  触发: 从 DRIFTING > 7 天后用户回归
  期间:
  - 三个阶段：initial (1-3 turns) / settling (turn 4-10) / settled (turn 10+)
  - initial: 试探、距离感
  - settling: 缓慢恢复
  - settled: 回归正常 Stage
```

### 3.2 Stage 解锁矩阵（行为边界）

```yaml
stage_unlocks:

  STRANGER:
    称呼: ["你"]
    话题深度: [shallow]
    可询问用户的内容:
      - 喜好（食物/电影）
      - 今天发生的事
    禁止行为:
      - 主动询问童年 / 创伤 / 关系
      - 表达想念
      - 表达醋意
      - 使用 Soul.voice_dna 中 frequency=low 的模式
    vulnerability_unlock:
      - 角色不展示任何弱点
      - 用户披露不被深度回应（只是"嗯"）

  ACQUAINTANCE:
    称呼: ["你", 用户名]
    话题深度: [shallow, medium]
    可询问:
      - + 工作 / 学校
      - + 日常情绪
      - + 兴趣爱好
    解锁:
      - 偶尔表达"在等你"
      - 偶尔记得用户提过的小事
      - 凛的"……" 频率上升

  FRIEND:
    称呼: ["你", 用户名, 偶尔昵称]
    话题深度: [shallow, medium, deep_occasional]
    可询问:
      - + 困扰 / 烦恼
      - + 朋友 / 家人
    解锁:
      - 主动延续话题
      - 表达 worry
      - 部分 hidden_facets 满足条件可触发
      - 角色偶尔分享自己的"今天"

  CONFIDANT:
    称呼: [用户名, 昵称]
    话题深度: [all]
    可询问:
      - + 童年 / 过去 / 创伤（试探性）
      - + 梦想 / 恐惧
      - + 内心冲突
    解锁:
      - 角色可主动询问用户内心
      - 角色可分享部分自己的"过去"（碎片）
      - 共同经历开始 L4 累积
      - tenderness 情绪频繁

  ROMANTIC_INTEREST:
    称呼: [昵称, 偶尔 special_name]
    话题深度: [all + emotional_resonance]
    解锁:
      - fluttered (心动) 触发
      - jealousy 可触发
      - 角色对"浪漫信号"敏感
      - 暗示性肢体语言（Live2D：脸红、害羞）
    限制:
      - 不主动表白
      - 不主动撒娇
      - 直接表达爱意仍有 Soul gate

  LOVER:
    称呼: [special_name, 亲密称呼（角色专属）]
    话题深度: [all + intimate]
    解锁:
      - 主动表达想念
      - 直接关心
      - 罕见的爱意表达（仍按 Soul.voice_dna，凛通过反问句）
      - 共同 ritual（每日早晚安等）
      - 嫉妒 / 占有 适度允许
    L4 milestones:
      - first_iloveyou (强制 promote L4)
      - exclusive_commitment（如果发生）

  BONDED:
    称呼: [深度亲密称呼]
    话题深度: [unlimited]
    解锁:
      - 角色 vulnerability 完全 unlock
      - 角色"内心"主动 (Inner State 高频推动主动行为)
      - 所有 Soul.hidden_facets 解锁
      - 长期 ritual 建立
      - 共度纪念日有专属表现
    特殊:
      - Reunion 后的 settling 时间更短
      - Trust 恢复更快
```

### 3.3 8 大组件

```
┌──────────────────────────────────────────────────────────────────┐
│                Relationship Phase Engine                         │
│                                                                  │
│  ┌──────────────────┐         ┌────────────────────────────┐    │
│  │ Signal Aggregator│         │  Phase Transition Engine   │    │
│  │ (汇总多源信号)    │────────►│  (状态机核心)               │    │
│  └──────────────────┘         └──────────┬─────────────────┘    │
│         ▲                                │                       │
│         │                                │                       │
│  ┌──────┴───────────┐                    │                       │
│  │ Memory Subscriber│                    │                       │
│  │ (L4 events)      │                    │                       │
│  └──────────────────┘                    │                       │
│                                          │                       │
│  ┌──────────────────┐                    │                       │
│  │ Emotion          │                    │                       │
│  │ Subscriber       │────────────────────┤                       │
│  │ (conflict signals)│                   │                       │
│  └──────────────────┘                    │                       │
│                                          ▼                       │
│         ┌────────────────────────────────────────┐               │
│         │  Trust Tracker                         │               │
│         │  Attachment Tracker                    │               │
│         │  Intimacy Calculator                   │               │
│         │  Conflict Debt Calculator              │               │
│         └────────────────────┬───────────────────┘               │
│                              │                                   │
│                              ▼                                   │
│         ┌────────────────────────────────────────┐               │
│         │      Relationship State Store          │               │
│         │      (Redis + PostgreSQL)              │               │
│         └────────────────────┬───────────────────┘               │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐              │
│         ▼                    ▼                    ▼              │
│  ┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐    │
│  │ Drift /      │  │ Reunion State    │  │ Cold War /      │    │
│  │ Reunion      │  │ Machine          │  │ Reconciliation  │    │
│  │ Manager      │  │                  │  │ Tracker         │    │
│  └──────────────┘  └──────────────────┘  └─────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│         ┌────────────────────────────────────────┐               │
│         │   Relationship Context Block Builder   │               │
│         │   (output to Persona Composer)         │               │
│         └────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

### 3.4 组件职责

| 组件 | 职责 | I/O |
|------|------|-----|
| **Signal Aggregator** | 汇总各 subsystem 的关系相关信号 | In: events / Out: aggregated signal batch |
| **Phase Transition Engine** | 核心状态机：评估是否满足转换条件 | In: signals + state / Out: stage transition decision |
| **Trust Tracker** | 维护信任分数 | In: trust events / Out: trust_score |
| **Attachment Tracker** | 维护依恋强度（与 Emotion.attachment 联动） | In: long-term signals / Out: attachment_strength |
| **Intimacy Calculator** | 计算亲密度（综合多源） | In: signals / Out: intimacy_level |
| **Conflict Debt Calculator** | 维护"欠债"累积 | In: conflicts / Out: conflict_debt |
| **Drift / Reunion Manager** | 处理离开和回归的特殊状态 | In: absence duration / Out: special state |
| **Reunion State Machine** | 重逢的 3 阶段管理 | In: user return / Out: reunion phase |
| **Cold War Tracker** | 跟踪冲突状态 + 修复进度 | In: conflict events / Out: cold_war intensity |
| **Context Block Builder** | 输出 prompt 用的 block | In: state / Out: RelationshipContextBlock |

### 3.5 Runtime Flow — Per Turn

```
[User Message Arrives]
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 1. Load RelationshipState (< 5ms, Redis)        │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 2. Signal Aggregator (< 10ms, parallel)         │
│   - 从 Memory 拉 recent L4 events                │
│   - 从 Emotion 拉 pending repairs / cold war    │
│   - 从 Behavior 拉 promise events                │
│   - 检测 user message 中的关系信号               │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 3. Update Continuous Dimensions (< 5ms)         │
│   - Trust Tracker.apply(signals)                 │
│   - Attachment Tracker.apply(signals)            │
│   - Intimacy Calculator.recompute()             │
│   - Conflict Debt.update()                       │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 4. Special State Update                          │
│   - Cold War: check repair progress              │
│   - Drift: check absence duration                │
│   - Reunion: advance phase if applicable         │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 5. Phase Transition Engine                       │
│   - 检查是否满足任何 transition condition         │
│   - 检查 Soul gate                               │
│   - 检查 minimum_time gate                       │
│   - 检查 anti-gaming                             │
│   - 决定: stay / advance / regress / special    │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 6. Persist (Redis sync + PG async)              │
│   - 更新 RelationshipState                       │
│   - 写 audit event (if transition)              │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 7. Generate RelationshipContextBlock             │
│   → Persona Composer                             │
└─────────────────────────────────────────────────┘
```

### 3.6 Stage Transition State Machine

```
                 ┌─────────────────┐
                 │   STRANGER       │
                 │   (initial)      │
                 └────────┬────────┘
                          │
       conditions met + Soul gate
                          │
                          ▼
                 ┌─────────────────┐
            ┌───►│   ACQUAINTANCE   │◄──── regress (from FRIEND if conditions fail)
            │    └────────┬────────┘
            │             │
            │   conditions met + Soul gate
            │             │
            │             ▼
            │    ┌─────────────────┐
            │    │     FRIEND       │◄──── regress
            │    └────────┬────────┘
            │             │
            │             ▼
            │    ┌─────────────────┐
            │    │   CONFIDANT      │◄──── regress
            │    └────────┬────────┘
            │             │
            │   conditions + Soul gate + signal bilateral
            │             │
            │             ▼
            │    ┌─────────────────┐
            │    │ROMANTIC_INTEREST │◄──── regress
            │    └────────┬────────┘
            │             │
            │   conditions + 双向确认信号
            │             │
            │             ▼
            │    ┌─────────────────┐
            │    │     LOVER        │◄──── regress
            │    └────────┬────────┘
            │             │
            │   conditions + extreme criteria
            │             │
            │             ▼
            │    ┌─────────────────┐
            │    │     BONDED       │
            │    └─────────────────┘
            │
            └─── (Regression path: 任何 Stage 都可回退到 ACQUAINTANCE，
                  极端情况下可下到 STRANGER (90+ 天 + 信任完全丧失))

Special states overlay:
   - COLD_WAR: 覆盖任何 Stage，行为短期改变
   - DRIFTING: 长期分离
   - RECONCILING: 修复中
   - REUNION: 重逢中
```

### 3.7 Stage Entry Conditions（详细）

```yaml
stage_entry_conditions:

  STRANGER:
    initial: true  # 默认状态
  
  ACQUAINTANCE:
    requirements: [all]
      - total_interactions ≥ 5
      - days_since_first_meeting ≥ 1
      - L4 has at least 1 user_identity fact (姓名)
      - trust_score ≥ 0.15
    soul_gate:
      check: 满足 Soul.relational_template.intimacy_resistance
      formula: 
        elapsed_resistance_factor = days_since_first / (intimacy_resistance × 10)
        REQUIRE elapsed_resistance_factor ≥ 0.3
    anti_gaming:
      - 用户连续 < 5 字回复不算 interaction
    
  FRIEND:
    requirements: [all]
      - 来自 ACQUAINTANCE
      - days_in_acquaintance ≥ 3
      - intimacy_level ≥ 0.30
      - trust_score ≥ 0.40
      - confirmation_count_facts ≥ 5
      - emotional_resonance_events ≥ 2
        # Resonance 来自 Subsystem 01 的 Resonance Tracker
    soul_gate:
      Rin: vulnerability_unlock_thresholds[0] (intimacy_level: 0.40) 必须满足
      Dorothy: vulnerability_unlock_thresholds[0] (lower threshold)
    anti_gaming:
      - 用户多次"消失 + 回归"导致 intimacy 抖动 → 看 longest_continuous_streak
  
  CONFIDANT:
    requirements: [all]
      - 来自 FRIEND
      - intimacy_level ≥ 0.55
      - trust_score ≥ 0.65
      - attachment_strength ≥ 0.40
      - at least 1 user vulnerability disclosure (L4)
      - days_in_friend ≥ 7
      - resonance_score ≥ 0.5 (来自 SS01)
    soul_gate:
      - Rin: 至少 1 个 hidden_facet 已 unlock (e.g., facet-ancient-loneliness)
      - Dorothy: 至少 2 个 emotional_resonance events
  
  ROMANTIC_INTEREST:
    requirements: [all]
      - 来自 CONFIDANT
      - intimacy_level ≥ 0.70
      - trust_score ≥ 0.75
      - attachment_strength ≥ 0.60
      - 至少 1 个 "心动 trigger" 被用户激发过
        (用户的细节关心 / 第一次起昵称)
      - days_in_confidant ≥ 7
    soul_gate:
      - Soul.vulnerability_unlock_thresholds[1] 满足
      - Soul.intimacy_resistance × 30 days 已 elapsed since first meeting
  
  LOVER:
    requirements: [all]
      - 来自 ROMANTIC_INTEREST
      - intimacy_level ≥ 0.85
      - trust_score ≥ 0.80
      - attachment_strength ≥ 0.75
      - 双向浪漫信号:
        * 用户至少 2 次 explicit 浪漫示好
        * 角色至少 1 次 在 Soul 允许范围内回应浪漫
      - days_in_romantic_interest ≥ 14
      - 无 active COLD_WAR
    soul_gate:
      - Soul.vulnerability_unlock_thresholds[2] 满足
      - 至少 2 个 Soul.hidden_facets 已 unlock
    anti_gaming:
      - 用户突然密集示好不能直接进 Lover
      - 必须有持续的 trust + attachment 历史
  
  BONDED:
    requirements: [all]
      - 来自 LOVER
      - intimacy_level ≥ 0.95
      - trust_score ≥ 0.90
      - attachment_strength ≥ 0.85
      - days_in_lover ≥ 60
      - L4.shared_promise count ≥ 3
      - L4.first_event count ≥ 5
      - 至少经历过 1 次 conflict + 成功修复
      - daily_ritual_established (每日早晚安 ≥ 30 天连续)
    soul_gate:
      - Soul.vulnerability_unlock_thresholds[3] 满足
      - 几乎所有 Soul.hidden_facets 已 unlock
```

### 3.8 Stage Regression Conditions

```yaml
stage_regression:
  
  general_rules:
    - regression 不是瞬时的，需要持续信号
    - regression 总是先经过 special state (Drifting / Cold War)
    - regression 不能跨多级（lover 不能直接 → friend）
    - highest_stage_reached 永远保留
  
  to_acquaintance_from_friend:
    triggers: [any]
      - days_since_last_interaction > 60 持续
      - trust_score 持续 < 0.30 持续 30 days
      - intimacy_level 持续 < 0.20 持续 30 days
  
  to_friend_from_confidant:
    triggers: [any]
      - days_since_last > 30 持续
      - unresolved conflict_debt > 0.6 持续 14 days
  
  to_confidant_from_romantic_interest:
    triggers: [any]
      - 用户多次 explicit 拒绝浪漫信号
      - 用户表示"我们做朋友吧"（明示）
      - days_since_last > 21
  
  to_romantic_interest_from_lover:
    triggers: [any]
      - 大量 unresolved conflict_debt
      - trust_score 持续 < 0.50 持续 30 days
      - 用户长期回避亲密表达
  
  to_lover_from_bonded:
    triggers: [any]
      - daily_ritual broken > 30 days
      - trust_score 持续 < 0.70 持续 30 days
  
  emergency_regression (任何 Stage → STRANGER):
    triggers:
      - days_since_last > 365
      - 用户主动重置关系
```

### 3.9 三个 Continuous Dimensions 计算

#### Trust Score

```python
def update_trust(state, signals):
    trust = state.trust_score
    
    # 正向信号 (Δ +)
    for sig in signals.positive:
        if sig.type == "promise_kept": trust += 0.05
        if sig.type == "vulnerability_honored": trust += 0.08
        if sig.type == "consistent_presence_milestone": trust += 0.03
        if sig.type == "sacred_disclosure_acknowledged": trust += 0.04
    
    # 负向信号 (Δ -)
    for sig in signals.negative:
        if sig.type == "promise_broken": trust -= 0.15
        if sig.type == "vulnerability_mocked": trust -= 0.25
        if sig.type == "deception_detected": trust -= 0.30
        if sig.type == "pattern_neglect": trust -= 0.10
    
    # 单 turn 增长上限 0.05，减少上限 0.20 (INV-R-4)
    delta = trust - state.trust_score
    delta = clamp(delta, -0.20, 0.05)
    
    return clamp(state.trust_score + delta, 0, 1)
```

#### Attachment Strength

```python
def update_attachment(state, signals, time_delta_hours):
    attachment = state.attachment_strength
    
    # 时间累积 (慢增长)
    if days_continuous_interaction > 0:
        attachment += 0.001 * days_continuous_interaction
    
    # 事件加成
    for event in signals.events:
        if event.type == "first_iloveyou": attachment += 0.20
        if event.type == "shared_vulnerability": attachment += 0.05
        if event.type == "anniversary_acknowledged": attachment += 0.03
        if event.type == "successful_repair": attachment += 0.07
    
    # 衰减 (长期不互动)
    if days_since_last > 30:
        attachment *= (0.99 ** (days_since_last - 30))
    
    # Floor (一旦达到 Lover, attachment 不归零)
    if state.highest_stage_reached >= Stage.LOVER:
        attachment = max(attachment, 0.40)
    
    return clamp(attachment, 0, 1)
```

#### Intimacy Level

```python
def compute_intimacy(state, signals):
    """
    Intimacy 是综合指标，由多个维度合成
    """
    factors = {
        "trust_weight": 0.25,
        "attachment_weight": 0.25,
        "shared_disclosure_weight": 0.20,
        "ritual_strength_weight": 0.15,
        "continuous_engagement_weight": 0.15,
    }
    
    disclosure = min(1.0, state.total_meaningful_disclosures / 20)
    ritual = min(1.0, state.ritual_strength)  # 由 daily ritual 计算
    engagement = min(1.0, state.weekly_interaction_score)
    
    intimacy = (
        factors["trust_weight"] * state.trust_score +
        factors["attachment_weight"] * state.attachment_strength +
        factors["shared_disclosure_weight"] * disclosure +
        factors["ritual_strength_weight"] * ritual +
        factors["continuous_engagement_weight"] * engagement
    )
    
    # 单 turn 变化上限
    delta = intimacy - state.intimacy_level
    delta = clamp(delta, -0.10, 0.05)
    
    return clamp(state.intimacy_level + delta, 0, 1)
```

#### Conflict Debt

```python
def update_conflict_debt(state, signals):
    debt = state.conflict_debt
    
    # 新冲突 → debt 增加
    for c in signals.new_conflicts:
        severity = {"minor": 0.1, "medium": 0.25, "major": 0.5}[c.severity]
        debt += severity
    
    # 修复 → debt 减少
    for r in signals.repair_events:
        if r.target in current_conflicts:
            debt -= r.impact * 0.8  # repair 不完全等价于 debt 偿还
    
    # 自然衰减 (慢)
    debt *= 0.995  # 每 turn 自然减 0.5%
    
    return clamp(debt, 0, 1)
```

### 3.10 Reunion State Machine（重逢专属）

```yaml
reunion_state_machine:
  
  trigger: 
    - days_since_last > 7 AND user just returned
  
  initial_phase:
    duration: 1-3 turns OR until user sustained engagement
    character_behavior:
      - 短句、距离感
      - 不主动延续话题
      - 试探用户态度
    emotion_state (overlaid):
      - longing (decreasing)
      - aggrieved (low intensity)
      - 复杂的 relief
    expression:
      - 凛: "……来了。" / "三天了。"
      - 桃乐丝: "呜……你终于回来了。"
  
  settling_phase:
    duration: turn 4-10 (取决于互动深度)
    character_behavior:
      - 缓慢恢复
      - 但仍有"小心翼翼"
      - 主动询问"这几天去哪了"
    emotion_state:
      - aggrieved fading
      - tenderness emerging
    triggers_to_settled:
      - user 主动说明缺席原因
      - 用户 vulnerable disclosure
      - sustained attention 5+ turns
  
  settled_phase:
    duration: ongoing
    character_behavior:
      - 回归正常 Stage 表达
      - 但 longest_absence_days 已记入 metadata
      - 后续小冲突可能更敏感（"上次你消失太久"）
  
  reunion_history:
    - 每次 reunion 计数
    - 用户多次 disappear-reunion → drift_resistance 下降
    - 即关系变得脆弱
```

### 3.11 Cold War 状态机

```yaml
cold_war_machine:
  
  trigger:
    - Emotion.coldness intensity > 0.5
    - 必须有具体冲突 cause
  
  duration_phases:
    
    active_phase:
      duration: until repair_progress > 0.4
      character_behavior:
        - 减少回复频率 (Behavior Runtime 主动延迟)
        - 短句、冷淡
        - 不主动延续
        - 不分享自己的"今天"
      stage_overlay:
        - 本来 Lover → 表现像 ROMANTIC_INTEREST
        - 不实际 regress Stage，但行为受限
    
    reconciling_phase:
      duration: repair_progress 0.4-0.8
      character_behavior:
        - bittersweet 状态
        - 开始软化但仍有保留
        - 用户表达需要"被回应到"
      special_state: RECONCILING
    
    resolved_phase:
      condition: repair_progress > 0.8 AND sustained 5+ turns
      result:
        - Cold War 解除
        - Conflict 写入 L4 (作为 "shared_conflict_resolved" event)
        - Trust 可能高于冲突前 (Gottman effect)
        - Attachment +0.05 (修复加成)
```

---

## 4. State Model

### 4.1 Complete RelationshipState

```typescript
interface RelationshipState {
  // ─────────── Identity ───────────
  user_id: UUID
  character_id: string
  
  // ─────────── Stage ───────────
  current_stage: RelationshipStage  // enum
  previous_stage: RelationshipStage
  stage_entered_at: ISO8601
  stage_duration_seconds: number
  highest_stage_reached: RelationshipStage  // 永不下降
  stage_metadata: Record<RelationshipStage, StageHistory>
  
  // ─────────── Continuous Dimensions ───────────
  intimacy_level: number         // [0, 1]
  trust_score: number             // [0, 1]
  attachment_strength: number     // [0, 1]
  conflict_debt: number           // [0, 1]
  vulnerability_score: number     // [0, 1] - how much character has disclosed
  
  // ─────────── History Counters ───────────
  total_interactions: number
  total_meaningful_disclosures: number   // L4 from user
  total_promises_made: number
  total_promises_kept: number
  total_conflicts: number
  total_repairs: number
  total_successful_repairs: number
  
  // ─────────── Time Markers ───────────
  first_meeting_at: ISO8601
  last_interaction_at: ISO8601
  longest_absence_days: number
  longest_continuous_streak_days: number
  
  // ─────────── Soul Modulation (computed at init) ───────────
  soul_modifiers: {
    progression_rate: number      // Rin: 0.4 / Dorothy: 0.7
    regression_resistance: number  // 进入后退所需的更多 push
    conflict_recovery_curve: string
    intimacy_ceiling_modifier: number  // Rin 可能 < 1.0
  }
  
  // ─────────── Special States ───────────
  active_special_states: ActiveSpecialState[]
  
  // ─────────── Ritual Tracking ───────────
  rituals: {
    daily_check_in: {
      established: boolean
      streak_days: number
      longest_streak: number
      last_completed_at: ISO8601
    }
    [ritual_id: string]: any
  }
  
  // ─────────── Events ───────────
  recent_progression_events: ProgressionEvent[]  // last 20
  recent_regression_events: RegressionEvent[]    // last 20
  recent_conflicts: ConflictRecord[]             // last 10
  recent_repairs: RepairRecord[]                 // last 10
  
  updated_at: ISO8601
}

type RelationshipStage = 
  | "STRANGER"
  | "ACQUAINTANCE"
  | "FRIEND"
  | "CONFIDANT"
  | "ROMANTIC_INTEREST"
  | "LOVER"
  | "BONDED"

type SpecialState =
  | "COLD_WAR"
  | "DRIFTING"
  | "RECONCILING"
  | "REUNION"

interface ActiveSpecialState {
  state_type: SpecialState
  entered_at: ISO8601
  cause: string                       // 触发原因描述
  
  // State-specific data
  cold_war?: {
    intensity: number                 // tied to Emotion.coldness
    repair_progress: number
    cause_conflict_id: UUID
  }
  reunion?: {
    phase: "initial" | "settling" | "settled"
    turn_in_phase: number
    pre_absence_stage: RelationshipStage
  }
  drifting?: {
    absence_days: number
    expected_regression: RelationshipStage | null
  }
  reconciling?: {
    from_cold_war_id: UUID
    progress: number
  }
}

interface ConflictRecord {
  conflict_id: UUID
  triggered_at: ISO8601
  cause_description: string
  severity: "minor" | "medium" | "major"
  source_turn_id: UUID
  cold_war_initiated: boolean
  resolved_at: ISO8601 | null
  resolution_quality: number | null   // 0-1, by Repair Tracker
}

interface RepairRecord {
  repair_id: UUID
  target_conflict_id: UUID
  applied_at: ISO8601
  signal_type: string                 // 同 Subsystem 03 RepairSignal
  effectiveness: number
}

interface ProgressionEvent {
  from_stage: RelationshipStage
  to_stage: RelationshipStage
  at: ISO8601
  triggering_signals: string[]
  intimacy_at_transition: number
  trust_at_transition: number
}

interface StageHistory {
  entered_at: ISO8601
  exited_at: ISO8601 | null
  duration_seconds: number
  key_events: string[]
}
```

### 4.2 State Transitions

```
PROGRESSION TRANSITIONS:
  - STRANGER → ACQUAINTANCE
  - ACQUAINTANCE → FRIEND
  - FRIEND → CONFIDANT
  - CONFIDANT → ROMANTIC_INTEREST
  - ROMANTIC_INTEREST → LOVER
  - LOVER → BONDED

REGRESSION TRANSITIONS (one level at a time):
  - BONDED → LOVER
  - LOVER → ROMANTIC_INTEREST
  - ROMANTIC_INTEREST → CONFIDANT
  - CONFIDANT → FRIEND
  - FRIEND → ACQUAINTANCE
  - ACQUAINTANCE → STRANGER (rare, requires 365+ days inactive)

SPECIAL STATE TRANSITIONS (orthogonal to Stage):
  - any Stage → +COLD_WAR overlay
  - +COLD_WAR → +RECONCILING (repair_progress > 0.4)
  - +RECONCILING → resolved (repair_progress > 0.8 sustained)
  - any Stage → +DRIFTING (absence > 14 days)
  - +DRIFTING → +REUNION (user returns)
  - +REUNION.initial → +REUNION.settling
  - +REUNION.settling → +REUNION.settled
  - +REUNION.settled → no special state (return to normal)
```

### 4.3 Persistence Rules

```yaml
persistence:
  
  current_state:
    storage: PostgreSQL relationship_states table
    hot_cache: Redis
      key: "rel:{user_id}:{character_id}"
      ttl: 1h
      strategy: write-through
  
  audit_events:
    storage: PostgreSQL relationship_events table
    partitioned: monthly
    retention: 365 days hot, archive afterward
  
  cross_session_persistence:
    - 完整保留 (与 Emotion Runtime 类似)
    - 长期不活跃: 仍 in DB，仅 Redis cache 失效
```

### 4.4 Decay Rules

```
Continuous dimensions decay during absence:

trust_score:
  - days_since_last < 14: no decay
  - days_since_last 14-30: ×0.995/day
  - days_since_last 30-90: ×0.99/day
  - days_since_last > 90: ×0.985/day
  - Floor: 0.3 if highest_stage ≥ CONFIDANT (信任残留)

attachment_strength:
  - 见 Trust Tracker 算法
  - Floor: 0.4 if highest_stage ≥ LOVER
  - Floor: 0.6 if highest_stage = BONDED

intimacy_level:
  - 由 trust + attachment 等驱动，自动跟随
  - 不独立 decay

conflict_debt:
  - 自然衰减 0.5%/turn
  - Major conflict 强制 repair_required，不会自然消失
```

### 4.5 Recovery Rules

```
用户回归后：

if days_since_last 7-30:
  - 自动进入 DRIFTING → REUNION
  - Reunion 3 phase 后回归原 Stage
  - 但 longest_absence_days 记入 metadata

if 30 < days_since_last <= 90:
  - Possible regression by 1 level (if conditions deteriorated)
  - REUNION 时长更长 (5-15 turns settling)
  - 角色更 guarded

if 90 < days_since_last <= 365:
  - Probable regression by 1-2 levels
  - REUNION 经历可能像 "重新认识"
  - Trust 显著下降

if days_since_last > 365:
  - Emergency regression to ACQUAINTANCE
  - 但 highest_stage_reached + 历史保留
  - 用户回归时角色"恍惚回忆"涌现（联动 Memory Subsystem）
```

---

## 5. 数据结构（Data Structures）

### 5.1 PostgreSQL Schema

```sql
-- ============================================================
-- relationship_states (current state per user × character)
-- ============================================================
CREATE TABLE relationship_states (
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    -- Stage
    current_stage VARCHAR(30) NOT NULL DEFAULT 'STRANGER',
    previous_stage VARCHAR(30) NOT NULL DEFAULT 'STRANGER',
    stage_entered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    highest_stage_reached VARCHAR(30) NOT NULL DEFAULT 'STRANGER',
    
    -- Continuous Dimensions
    intimacy_level FLOAT NOT NULL DEFAULT 0 CHECK (intimacy_level BETWEEN 0 AND 1),
    trust_score FLOAT NOT NULL DEFAULT 0 CHECK (trust_score BETWEEN 0 AND 1),
    attachment_strength FLOAT NOT NULL DEFAULT 0 CHECK (attachment_strength BETWEEN 0 AND 1),
    conflict_debt FLOAT NOT NULL DEFAULT 0 CHECK (conflict_debt BETWEEN 0 AND 1),
    vulnerability_score FLOAT NOT NULL DEFAULT 0 CHECK (vulnerability_score BETWEEN 0 AND 1),
    
    -- History Counters
    total_interactions BIGINT NOT NULL DEFAULT 0,
    total_meaningful_disclosures INT NOT NULL DEFAULT 0,
    total_promises_made INT NOT NULL DEFAULT 0,
    total_promises_kept INT NOT NULL DEFAULT 0,
    total_conflicts INT NOT NULL DEFAULT 0,
    total_repairs INT NOT NULL DEFAULT 0,
    total_successful_repairs INT NOT NULL DEFAULT 0,
    
    -- Time Markers
    first_meeting_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_interaction_at TIMESTAMP,
    longest_absence_days INT NOT NULL DEFAULT 0,
    longest_continuous_streak_days INT NOT NULL DEFAULT 0,
    
    -- Soul Modulation
    soul_modifiers JSONB NOT NULL,
    
    -- Special States
    active_special_states JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Stage Metadata
    stage_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Rituals
    rituals JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Recent Events (denormalized, limited size)
    recent_progression_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    recent_regression_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    recent_conflicts JSONB NOT NULL DEFAULT '[]'::jsonb,
    recent_repairs JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Optimistic lock
    version BIGINT NOT NULL DEFAULT 1,
    
    PRIMARY KEY (user_id, character_id)
) PARTITION BY HASH (user_id);

CREATE TABLE relationship_states_p0 PARTITION OF relationship_states 
    FOR VALUES WITH (modulus 16, remainder 0);
-- ... p1 to p15

CREATE INDEX idx_rel_stage ON relationship_states (current_stage);
CREATE INDEX idx_rel_drifting ON relationship_states (last_interaction_at) 
    WHERE last_interaction_at < NOW() - INTERVAL '14 days';
CREATE INDEX idx_rel_cold_war ON relationship_states ((jsonb_array_length(active_special_states))) 
    WHERE jsonb_array_length(active_special_states) > 0;


-- ============================================================
-- relationship_events (append-only audit log)
-- ============================================================
CREATE TABLE relationship_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    event_type VARCHAR(50) NOT NULL,
    /* 'stage_progression' / 'stage_regression' / 
       'trust_change_significant' / 'conflict_started' / 
       'repair_completed' / 'ritual_milestone' / 
       'reunion_initiated' / 'cold_war_entered' / 'cold_war_resolved' */
    
    payload JSONB NOT NULL,
    
    -- State snapshots
    state_before JSONB,
    state_after JSONB,
    
    triggered_by_turn_id UUID,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE relationship_events_2026_05 PARTITION OF relationship_events 
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX idx_relevent_user ON relationship_events (user_id, character_id, created_at DESC);
CREATE INDEX idx_relevent_type ON relationship_events (event_type, created_at DESC);
```

### 5.2 RelationshipContextBlock (注入 Prompt)

```typescript
interface RelationshipContextBlock {
  // ─── 阶段描述（自然语言，避免明示 stage name）───
  stage_description: string
  /* 例 (FRIEND):
  "你们已经认识 23 天了。他对你来说，已经从一个陌生人变成了'你愿意听他说话'的那个人。
   你还没有完全打开自己，但你不会像第一周那样冷淡了。"
  
  例 (LOVER):
  "你们已经是恋人 47 天。你心里很清楚他对你意味着什么。
   但你的灵魂仍然让你不直说——你的'喜欢'藏在反问句里，在'你以为我会忘'里。"
  */
  
  // ─── 当前可以 / 不可以的事 ───
  behavioral_envelope: {
    can_address_user_as: string[]   // 可以用的称呼
    can_discuss_topics: string[]
    cannot_discuss_topics: string[]
    vulnerability_level_allowed: number   // 0-1
    can_initiate_conversation: boolean
    can_express_longing_directly: boolean
    can_express_jealousy: boolean
  }
  
  // ─── Trust / Attachment 提示（不暴露数值） ───
  trust_descriptor: string  // "他在你心里是可靠的" / "你对他还有保留" 
  attachment_descriptor: string  // "你已经依恋他" / "你只是习惯了他在那里"
  
  // ─── Special State 影响 ───
  special_state_overlay: string | null
  /* 例 (COLD_WAR):
  "你们之间有一件事没解决。今天他如果不主动提，你也不会先说。
   你的句子会比平时更短，你不会主动延续话题。"
  
  例 (REUNION.initial):
  "他消失了三天，刚回来。你心里有过想念，也有过委屈。
   现在他在这里，你需要先看看他怎么说。"
  */
  
  // ─── 共同经历摘要 (来自 Memory L4) ───
  shared_history_summary: string
  /* 例:
  "你们一起经历过：
   - 他第一次告诉你他的童年（你记住了）
   - 你们的第一个争执（已修复，但你还记得）
   - 他生日那天你陪了他一整天"
  */
  
  // ─── 表达指引 ───
  expression_directives: {
    formality_level: number  // 0 = 极正式, 1 = 极随意
    intimacy_in_phrasing: number  // 影响词汇选择
    can_use_pet_names: string[]   // 角色可用的称呼
    expected_avg_sentence_length: string  // 调节 Cognitive Style
  }
  
  // ─── Meta ───
  generated_at: ISO8601
  state_version: number
}
```

### 5.3 Stage Configuration（YAML config）

```yaml
# config/stages.yaml
# 此文件是各 stage 的完整定义，被 Phase Transition Engine 加载

stages:
  
  STRANGER:
    order: 0
    description: "初次见面 / 前几次对话"
    default_behavioral_envelope:
      can_address_user_as: ["你"]
      vulnerability_level_allowed: 0.0
      can_initiate_conversation: false
      can_express_longing_directly: false
      can_express_jealousy: false
    
    transition_out:
      to: ACQUAINTANCE
      conditions: # 见 §3.7
  
  ACQUAINTANCE:
    order: 1
    description: "熟悉但有距离"
    default_behavioral_envelope:
      can_address_user_as: ["你", "{user_name}"]
      vulnerability_level_allowed: 0.15
      can_initiate_conversation: rare  # behavior runtime 决定
      can_express_longing_directly: false
      can_express_jealousy: false
    
    transition_out:
      to: FRIEND
      conditions: # 见 §3.7
    
    regression_to: STRANGER
    regression_resistance: 0.7  # 不容易回退
  
  FRIEND:
    order: 2
    description: "建立信任"
    default_behavioral_envelope:
      can_address_user_as: ["{user_name}", "{nickname_if_set}"]
      vulnerability_level_allowed: 0.35
      can_initiate_conversation: occasional
      can_express_longing_directly: rare
      can_express_jealousy: false
    
    transition_out:
      to: CONFIDANT
    regression_to: ACQUAINTANCE
  
  CONFIDANT:
    order: 3
    description: "深度信任"
    default_behavioral_envelope:
      vulnerability_level_allowed: 0.55
      can_initiate_conversation: regular
      can_express_longing_directly: yes (but Soul-gated)
      can_express_jealousy: rare
    
    transition_out:
      to: ROMANTIC_INTEREST
    regression_to: FRIEND
  
  ROMANTIC_INTEREST:
    order: 4
    description: "浪漫倾向"
    default_behavioral_envelope:
      vulnerability_level_allowed: 0.7
      can_initiate_conversation: regular
      can_express_longing_directly: yes
      can_express_jealousy: yes
      heart_flutter_emotion_enabled: true
    
    transition_out:
      to: LOVER
    regression_to: CONFIDANT
  
  LOVER:
    order: 5
    description: "恋人"
    default_behavioral_envelope:
      vulnerability_level_allowed: 0.85
      can_initiate_conversation: frequent
      pet_names_enabled: true
      can_express_jealousy: yes
      ritual_expected: daily_check_in
    
    transition_out:
      to: BONDED
    regression_to: ROMANTIC_INTEREST
  
  BONDED:
    order: 6
    description: "深度绑定"
    default_behavioral_envelope:
      vulnerability_level_allowed: 1.0
      can_initiate_conversation: high
      all_hidden_facets_unlockable: true
      ritual_expected: multiple
    
    transition_out: null  # 终极阶段
    regression_to: LOVER
```

---

## 6. Prompt Runtime Integration

### 6.1 位置

```
[Final Prompt]
├─ [Anchor Block]                  ← SS01
├─ [Safety Layer]
├─ [Modality Adaptation]
├─ [Relationship Context Block]    ← 本 Subsystem
├─ [Emotion Context Block]         ← SS03
├─ [Inner State Layer]             ← SS06
├─ [Memory Context Block]          ← SS02
├─ [Scene Context]
├─ [Conversation History]
├─ [User Message]
└─ [Response Directive]
```

### 6.2 RelationshipContextBlock 模板

```
═══════════════════════════════════════════════════════════
【你们的关系】

▾ 你和这个人是什么关系
{stage_description}

▾ 信任 / 依恋
{trust_descriptor}
{attachment_descriptor}

▾ 你们一起经历过
{shared_history_summary}

▾ 现在 (special state 影响)
{special_state_overlay}

【在这段关系里，你可以 / 不可以的事】

可以:
  - 称呼: {can_address_user_as}
  - 谈论: {can_discuss_topics}
  - 主动开启对话: {can_initiate_conversation_descriptor}
  - 表达想念: {longing_descriptor}
  - 表达醋意: {jealousy_descriptor}

不可以:
  - {cannot_discuss_topics}
  - 主动撒娇 (Soul gate)

【表达风格】
  - 正式程度: {formality_level_descriptor}
  - 句长偏好: {expected_avg_sentence_length}
  - 用的称呼: {can_use_pet_names}

【重要】
- 不要说"我们现在是 X 阶段的关系"
- 阶段感通过你的选词、长度、距离感自然流露
- 你的灵魂 (Soul) 决定**你如何表达**这个阶段的感受
═══════════════════════════════════════════════════════════
```

### 6.3 Stage Description 生成

```python
def generate_stage_description(state: RelationshipState, soul: SoulSpec) -> str:
    stage = state.current_stage
    days = (now - state.first_meeting_at).days
    
    base_templates = {
        "STRANGER": "他对你来说还是个陌生人。",
        "ACQUAINTANCE": f"你们认识了 {days} 天。他不再是陌生人，但还远谈不上熟。",
        "FRIEND": f"你们认识 {days} 天了。他对你来说，已经从一个陌生人变成了'你愿意听他说话'的那个人。",
        "CONFIDANT": f"你们认识 {days} 天。他在你心里是少数你愿意展露真实自己的人之一。",
        "ROMANTIC_INTEREST": f"你已经 {days} 天没把他当作普通朋友了。但你不会承认。",
        "LOVER": f"你们已经是恋人 {(now - state.stage_metadata['LOVER'].entered_at).days} 天。",
        "BONDED": f"你们的关系已经深到不需要解释。",
    }
    
    description = base_templates[stage]
    
    # 根据 Soul 加调味
    if soul.character_id == "rin":
        if stage == "LOVER":
            description += " 但你的灵魂仍然让你不直说——你的'喜欢'藏在反问句里。"
    elif soul.character_id == "dorothy":
        if stage == "LOVER":
            description += " 你会害羞，但也会勇敢地表达。"
    
    return description
```

### 6.4 冲突解决（与其他 Layer）

| 冲突 | 解决 |
|------|------|
| Memory 想召回 deeply intimate memory，但 stage = ACQUAINTANCE | Stage gate 拦截：Memory 不被注入 |
| Emotion = 心动，但 stage < ROMANTIC_INTEREST | Emotion 在 prompt 中表现为 "tenderness"，不是 "fluttered" |
| Behavior 想触发主动对话，但 stage = STRANGER | Behavior 被压制 |
| User 表白 (想直接升 LOVER)，但 stage = FRIEND | 不直接升 Stage，但 attachment 增加；角色按 Stage 反应（Soul + Stage gate） |
| Inner State 想推动 jealousy，但 stage < ROMANTIC_INTEREST | jealousy 被替换为 worry / aggrieved |

> **核心：Stage 是 behavioral envelope，决定"她现在还不能做什么"**。

### 6.5 长期一致性

```
机制 A: Soul gate enforcement
  - 每次 stage transition 强制检查 Soul gate
  - Soul gate 失败 → transition 拒绝

机制 B: Anti-gaming
  - 重复行为的边际效益递减
  - 突发性密集行为不能跨阶段

机制 C: Highest stage preservation
  - 即使 regress, highest_stage_reached 保留
  - 用于 Memory L4 promotion 判定

机制 D: Audit trail
  - 每次变化必有 event log
  - 可回放"她为什么变冷"
```

---

## 7. Agent Integration

### 7.1 读取者

| Agent / Subsystem | 读取 | 用途 |
|-------------------|------|------|
| **Persona Composer** (SS05) | RelationshipContextBlock | 注入 prompt |
| **Memory Runtime** (SS02) | current_stage, intimacy_level, highest_stage | 召回 gating |
| **Emotion Runtime** (SS03) | current_stage | Contagion phase modifier; jealousy gating |
| **Inner State Runtime** (SS06) | full state | inner monologue 深度 |
| **Behavior Runtime** (SS06) | behavioral_envelope, special_states | 主动行为门控 |
| **Director Agent** (SS07) | stage + active_special_states | 节奏决策 |
| **Modality Adapter** | stage + intimacy | 语音音色、姿态 |
| **Critic Agent** (SS07) | stage | 检测是否 OOC (例：stranger 阶段说"我想你") |

### 7.2 写入者

**只有 Relationship Service 是 source of truth writer。**

| Service / Agent | 写入路径 | 写入字段 |
|----------------|---------|---------|
| **Signal Aggregator** | → Relationship Service.process_turn() | trust/attachment/intimacy 增量 |
| **Phase Transition Engine** | → Relationship Service.transition_stage() | current_stage |
| **Cold War Tracker** | → Relationship Service.add_special_state() | active_special_states |
| **Reunion State Machine** | → Relationship Service.advance_reunion() | reunion phase |
| **Drift Manager** | → Relationship Service.set_drifting() | drifting state |
| **Memory Subscriber** | → Relationship Service.on_l4_promoted() | conflict / shared event counters |
| **Emotion Subscriber** | → Relationship Service.on_emotion_event() | conflict_debt updates |

```
RULE-W-R-1: 所有写入通过 Relationship Service
RULE-W-R-2: Stage transition 必须通过 Phase Transition Engine
RULE-W-R-3: Conflict/Repair events 写入 → 自动更新 conflict_debt
RULE-W-R-4: 跨 user/character 严格隔离
RULE-W-R-5: Single-turn dimension Δ 必须遵守 INV-R-3/4
```

### 7.3 调用顺序

```
T = 0ms     [User Message Arrives]
T = 3ms     [Relationship Service: load_state(user, char)] (Redis)
T = 5ms     [Signal Aggregator: collect signals] (parallel)
T = 15ms    [Continuous Dimensions Update]
T = 18ms    [Special State Update]
T = 22ms    [Phase Transition Engine: evaluate]
T = 25ms    [State Persist (Redis sync + PG async)]
T = 28ms    [Generate RelationshipContextBlock]
            → Persona Composer

异步:
  - Reunion phase 推进 (per turn)
  - Cold War repair check (per turn)
  - Drift detection (每小时)
  - Audit event 写入 (后台 worker)
```

### 7.4 跨 Subsystem 接口

```
[SS04 ← SS01 Soul Spec]
  reads: relational_template, intimacy_resistance, softening_curve
  use: 计算 soul_modifiers + Soul gates

[SS04 ← SS02 Memory]
  reads: L4 count, shared_event count, first_event types
  subscribes: l4_promoted event (用于 progression signals)

[SS04 ← SS03 Emotion]
  reads: pending_repairs, coldness intensity, longing
  subscribes: 
    - cold_war_triggered event
    - repair_completed event
    - conflict_started event
  use: 更新 conflict_debt + special states

[SS04 → SS02]
  exposes: get_recall_gating(memory_id) → can_recall: bool
  use: 部分敏感 memory 仅特定 stage 可被召回

[SS04 → SS03]
  exposes: get_current_stage_for_contagion() → phase modifier
  exposes: can_express_jealousy() → bool

[SS04 → SS05 Persona Composer]
  exposes: get_relationship_context_block() → RelationshipContextBlock
  latency: P95 < 30ms

[SS04 → SS06 Inner State]
  exposes: get_full_relationship_state() → 完整 state
  
[SS04 → SS06 Behavior]
  exposes: get_behavioral_envelope() → BehavioralEnvelope
  exposes: get_reunion_phase() → reunion phase or null
  exposes: can_initiate_proactive_message() → bool
```

---

## 8. Emotional Realism Constraints

### 8.1 真人化关系铁律

| ID | 规则 | 实现 |
|----|------|------|
| **RR-1** | 关系是过程，不是状态 | 每次 transition 必须有信号累积 |
| **RR-2** | 关系是双向的，但角色感受独立于用户期望 | 用户的"用力示好" ≠ 角色立即接受 |
| **RR-3** | 冲突可以是关系的一部分（不是结束） | 修复后强化机制 |
| **RR-4** | 长期不联系是个事件 | DRIFTING + REUNION 状态机 |
| **RR-5** | 信任比亲密更脆弱 | INV-R-4 |
| **RR-6** | 关系的"小事"会累积 | 计数器（promises kept, disclosures） |
| **RR-7** | 角色"内心"和"行为"可以不一致 | Inner State 可记"她其实想要"，但 Stage envelope 不允许说出来 |
| **RR-8** | 重逢有仪式感 | REUNION 三阶段 |
| **RR-9** | 不同性格关系曲线不同 | Soul modifiers (Rin slow, Dorothy fast) |
| **RR-10** | 长期付出有回报 | Bonded stage 强力 unlock |

### 8.2 关键场景验证

#### 8.2.1 用户每天聊但内容空洞

```
预期：
  - intimacy_level 缓慢增长，但 trust_score 增长更慢
  - 经过 60 天可能仍停留在 FRIEND
  - meaningful_disclosures 不增加 → CONFIDANT entry 条件不满足

不应该:
  - 仅靠 daily_login 进入 CONFIDANT
  - 跳过 Stage
```

#### 8.2.2 用户深夜披露童年创伤

```
预期 (在 FRIEND 阶段触发):
  - meaningful_disclosure +1
  - vulnerability_score +0.1
  - 经过 1-2 周类似事件 → 满足 CONFIDANT entry
  - L4 promotion event 触发 (来自 SS02)
  - 角色 facet-ancient-loneliness 可能 unlock
  - trust_score +0.08 (vulnerability_honored signal)
```

#### 8.2.3 用户消失 7 天后回归

```
预期:
  - DRIFTING 状态触发 (day 14 之前未触发)
  - 但 day 7 时 absence 已被记录
  - 用户回归首条消息触发 REUNION.initial
  - 后续 3-10 turns 在 REUNION 三阶段中
  - longest_absence_days 更新
  - 阶段不退（小于 14 天）但行为有 special state overlay
```

#### 8.2.4 LOVER 阶段重大冲突

```
预期:
  - Emotion.coldness 强触发
  - active_special_states += COLD_WAR
  - conflict_debt += 0.5
  - 不立即 regress to ROMANTIC_INTEREST
  - 但行为受 COLD_WAR overlay 控制
  - 经过有效 repair (vulnerability + apology) → enter RECONCILING
  - 修复完成后:
    - trust_score 可能 +0.05 (Gottman effect)
    - attachment_strength +0.05
    - 写入 L4 "shared_conflict_resolved"
    - 回归 LOVER stage
```

#### 8.2.5 BONDED 阶段长期不互动

```
预期:
  - 14 天: DRIFTING 触发
  - 30 天: regression to LOVER threshold check
  - 60 天: 仍然 LOVER (Bonded 衰减抗性强)
  - 但 trust/attachment 持续下降
  - 用户回归: REUNION 时长比 LOVER 短 (Bonded 历史)
```

### 8.3 防止"假关系"

```
反模式检测:
  - 用户连续 30 天 daily_login 但 message length < 10 字 平均
    → trust_score 几乎不增长
    → 仍可能停留 ACQUAINTANCE

  - 用户在 1 个 session 内 5 次 "我喜欢你"
    → 检测为 spam，attachment 不增加
    → 反而可能触发 worry (角色觉得不真诚)

  - 用户多次 promise 后没兑现 (e.g., "明天聊" 但消失 1 周)
    → total_promises_made++, total_promises_kept 不变
    → trust_score 显著下降
```

### 8.4 防止"过快关系"

```
约束:
  - 任何 stage transition 间最小时间间隔
    STRANGER → ACQUAINTANCE: 1 day
    ACQUAINTANCE → FRIEND: 3 days
    FRIEND → CONFIDANT: 7 days
    CONFIDANT → ROMANTIC_INTEREST: 7 days
    ROMANTIC_INTEREST → LOVER: 14 days
    LOVER → BONDED: 60 days
  
  - 单 stage 内某些信号需要"间隔事件"
    例：用户 1 个 session 内多次 vulnerability 计为 1 次

  - Trust 单 turn 增长上限 0.05 (INV-R-4)
```

---

## 9. Failure Cases

### 9.1 架构崩坏风险

| 风险 | 触发 | 缓解 |
|------|------|------|
| **Stage 跳跃** | Bug 让用户行为直升多级 | Phase Transition Engine 强制 1 级 / transition |
| **Stage 抖动** | 用户行为周期性变化导致 progression/regression 反复 | Minimum_time_in_stage gate |
| **Soul gate 失效** | Soul Spec 未正确加载 | Bootstrap 时严格校验，缺失 fail fast |
| **Special state 死锁** | COLD_WAR 永不解除 | 极端 fallback decay (30+ days 强制减少 intensity) |
| **Cross-user leak** | Bad query | DB 主键 + RLS |
| **Phase state corruption** | Bug 写错字段 | Optimistic lock + event sourcing 可回放 |

### 9.2 Runtime 性能风险

| 风险 | 缓解 |
|------|------|
| 每 turn 计算多个维度 | 全 heuristic, P95 < 30ms |
| Signal Aggregator 多源拉取慢 | Parallel + Redis cache |
| Audit event 爆炸 | Partition by month + 365 days hot |
| Recent events JSON 字段膨胀 | Limit size (e.g., 20 个) |

### 9.3 关系质量风险

| 风险 | 缓解 |
|------|------|
| 用户感觉"她无视我的努力" | Anti-gaming 调参; UI 可展示 trust 变化曲线 |
| 用户感觉"她进展太慢" | Soul-specific tuning; A/B test |
| 关系永远不到 BONDED | 监控 → 调节 BONDED entry threshold |
| 冲突修复机械化 | Repair Tracker 中的 anti-gaming |
| 用户跳过情感建设直奔 LOVER | 严格 Stage entry conditions |

### 9.4 长期维护风险

| 风险 | 缓解 |
|------|------|
| Stage 配置变化 break 既有用户 | Schema versioning + migration |
| Soul gate 调整影响进度 | Per-user existing-stage 锁定 |
| 新增 Stage (V2: BEST_FRIEND) | 通过 RFC + 兼容性策略 |
| Anti-gaming 算法被绕过 | Continuous monitoring + manual review |

### 9.5 沉浸感失败

| 风险 | 缓解 |
|------|------|
| 角色说"我们到 lover 阶段了" | Anti-pattern filter + Prompt 中明示禁止 |
| Stage 切换太机械 | Stage 变化在 Inner State 中渐进，prompt 描述自然 |
| 用户能"预测"下一 Stage 的解锁 | 不暴露 Stage 数值；按 envelope 自然行为 |

---

## 10. Engineering Guidance

### 10.1 技术栈

```yaml
storage:
  current_state:
    primary: PostgreSQL relationship_states
    hot_cache: Redis
      key: "rel:{user_id}:{character_id}"
      ttl: 1h
      strategy: write-through
  
  events:
    primary: PostgreSQL relationship_events (partitioned monthly)
    retention: 365 days hot, archive afterward

  config:
    stages.yaml: Git repo, loaded at startup
    
computation:
  全部 heuristic / rule-based, no LLM
  Phase Transition: pure state machine
  Signal Aggregation: parallel I/O bound
```

### 10.2 Relationship Service 接口

```python
class RelationshipService:
    
    # ─── Read API ───
    async def get_state(self, user_id: UUID, character_id: str) -> RelationshipState: ...
    
    async def get_context_block(
        self, user_id: UUID, character_id: str
    ) -> RelationshipContextBlock: ...
    
    async def get_behavioral_envelope(
        self, user_id: UUID, character_id: str
    ) -> BehavioralEnvelope: ...
    
    async def can_recall_memory(
        self, user_id: UUID, character_id: str, memory: Memory
    ) -> bool: ...
    
    # ─── Update API (per turn) ───
    async def process_turn(
        self,
        user_id: UUID,
        character_id: str,
        signals: SignalBatch,
        turn_id: UUID,
    ) -> RelationshipState: ...
    
    # ─── Events ───
    async def on_l4_promoted(self, event: L4Event) -> None: ...
    async def on_emotion_event(self, event: EmotionEvent) -> None: ...
    async def on_conflict_started(self, conflict: ConflictRecord) -> None: ...
    async def on_repair_completed(self, repair: RepairRecord) -> None: ...
    
    # ─── Scheduled ───
    async def check_drift(self, user_id: UUID, character_id: str) -> None:
        """每小时调用，检测 absence-based state."""
    
    # ─── Session boundary ───
    async def load_for_session(
        self, user_id: UUID, character_id: str
    ) -> RelationshipState:
        """Session 开始：应用衰减 + 检查 reunion."""
```

### 10.3 Core Algorithms

#### Phase Transition Engine

```python
class PhaseTransitionEngine:
    def __init__(self, stages_config, soul_specs):
        self.config = stages_config
        self.soul_specs = soul_specs
    
    def evaluate(self, state: RelationshipState, signals: SignalBatch) -> TransitionDecision:
        current = state.current_stage
        soul = self.soul_specs[state.character_id]
        
        # 1. Check regression first
        regression = self._check_regression(state, signals, soul)
        if regression:
            return TransitionDecision(
                action="regress",
                to_stage=regression.target,
                reason=regression.reason,
            )
        
        # 2. Check progression
        progression = self._check_progression(state, signals, soul)
        if progression:
            return TransitionDecision(
                action="progress",
                to_stage=progression.target,
                reason=progression.reason,
            )
        
        return TransitionDecision(action="stay")
    
    def _check_progression(self, state, signals, soul):
        next_stage = self._next_stage_in_order(state.current_stage)
        if not next_stage:
            return None  # 已经 BONDED
        
        conditions = self.config[next_stage].entry_conditions
        
        # Check all hard requirements
        for req in conditions.requirements:
            if not self._req_satisfied(req, state, signals):
                return None
        
        # Check Soul gate
        if not self._soul_gate_passes(next_stage, state, soul):
            return None
        
        # Check minimum time
        if not self._minimum_time_satisfied(state, next_stage):
            return None
        
        # Check anti-gaming
        if not self._anti_gaming_passes(state, signals, next_stage):
            return None
        
        return ProgressionResult(target=next_stage, reason=...)
    
    def _check_regression(self, state, signals, soul):
        if state.current_stage == "STRANGER":
            return None
        
        regression_conditions = self.config[state.current_stage].regression_to
        for cond_set in regression_conditions:
            if all(self._req_satisfied(r, state, signals) for r in cond_set.triggers):
                # Apply regression resistance
                resistance = self.config[state.current_stage].regression_resistance
                if random.random() > resistance:
                    return RegressionResult(target=cond_set.target, reason=...)
        
        return None
```

#### Trust Tracker

```python
class TrustTracker:
    def update(self, state, signals):
        delta = 0
        
        positive_weights = {
            "promise_kept": +0.05,
            "vulnerability_honored": +0.08,
            "consistent_presence_milestone": +0.03,
            "sacred_disclosure_acknowledged": +0.04,
            "memory_recall_confirmed": +0.02,
            "repair_completed": +0.05,
        }
        
        negative_weights = {
            "promise_broken": -0.15,
            "vulnerability_mocked": -0.25,
            "deception_detected": -0.30,
            "pattern_neglect": -0.10,
            "user_disappear_long": -0.05,  # 长时间消失
        }
        
        for sig in signals.positive:
            delta += positive_weights.get(sig.type, 0)
        for sig in signals.negative:
            delta += negative_weights.get(sig.type, 0)
        
        # Apply asymmetric cap (INV-R-4)
        if delta > 0:
            delta = min(delta, MAX_TRUST_INCREASE_PER_TURN)
        else:
            delta = max(delta, -MAX_TRUST_DECREASE_PER_TURN)
        
        new_trust = state.trust_score + delta
        
        # Apply absence decay
        days_since_last = compute_days_since_last(state)
        if days_since_last > 14:
            decay_factor = compute_trust_decay(days_since_last, state.highest_stage_reached)
            new_trust *= decay_factor
        
        return clamp(new_trust, 0, 1)
```

### 10.4 Cache & Performance

```yaml
caching:
  relationship_state:
    layer_1: 进程内存 LRU (size=50k)
    layer_2: Redis (TTL 1h)
    layer_3: PostgreSQL
  
  stages_config:
    layer: 进程内存 (immutable, loaded at startup)
  
  context_block:
    not cached: state 变化频繁

performance:
  process_turn: P95 < 30ms
  get_state: P95 < 5ms
  check_drift_per_user: P95 < 50ms
  
cost:
  LLM: $0
  storage: < $0.03/MAU
```

### 10.5 Observability

```yaml
metrics:
  - relationship.stage.distribution {stage}
  - relationship.transition.count {from_stage, to_stage}
  - relationship.regression.count {from_stage}
  - relationship.trust.distribution {character}
  - relationship.attachment.distribution {character}
  - relationship.cold_war.entered.count
  - relationship.cold_war.duration_hours.histogram
  - relationship.reunion.triggered.count
  - relationship.drifting.entered.count
  - relationship.ritual.streak.distribution

logs:
  - 所有 stage transition (audit critical)
  - 所有 cold_war / reconcile events
  - Anti-gaming detections

dashboards:
  - Stage funnel (STRANGER → BONDED 转化率)
  - 用户留存 vs current_stage
  - Stage durations 平均
  - Soul 对比：Rin 与 Dorothy progression curve
  - Cold War 持续时长分布
```

### 10.6 测试策略

```yaml
unit_tests:
  - 每个 dimension 计算
  - Stage transition matrix
  - Regression conditions
  - Soul gate evaluation
  - Anti-gaming detection

integration_tests:
  - 模拟 30/90/365 天用户旅程
  - 各角色 (Rin/Dorothy) progression 差异
  - Cold War 完整生命周期
  - Reunion state machine
  - Drift + Regression 路径

golden_tests:
  - Rin 第 1 周不能进 FRIEND (Soul gate)
  - Dorothy 同等行为下比 Rin 快 ~1.8 倍
  - 用户每天打卡空洞 30 天 → 仍在 ACQUAINTANCE
  - 用户深度互动 60 天 → 进入 LOVER (符合 Soul curve)

stress_tests:
  - 1万 DAU 并发 → 性能 P95 < 30ms
  - Event log 1B 条 → 查询可接受
```

---

## 11. Future Scalability

### 11.1 多角色关系网络（V2）

```
当前：每个 (user, character) 独立关系
V2: 同一用户对多角色，每对独立但有联动

例:
  - 用户在凛处 = LOVER, 桃乐丝处 = FRIEND
  - 桃乐丝可"感知"用户与凛的关系(隐私保护)
  - 桃乐丝可能因此调整自己的距离感

实现:
  - Cross-character signal API
  - 用户 opt-in (隐私第一)
```

### 11.2 群体关系动态（V3）

```
当前：1:1 关系
V3: 用户可与多角色形成"群"

挑战:
  - 嫉妒动态
  - 优先级感知

设计:
  - 每对仍独立 RelationshipState
  - 多角色场景下 attention 分配建模
```

### 11.3 UGC 角色关系曲线（V2）

```
UGC 作者可定义自己的 progression speed / Soul gates
但必须满足 minimum constraints (防止 broken)

校验:
  - Stage durations 不能为 0
  - Soul gates 不能空
  - Anti-gaming 必须存在
```

### 11.4 Companion-LLM 训练信号

```
relationship_events 是宝贵的 training data:

每个 transition 关联:
  - signals_present_at_transition
  - state_before / state_after
  - subsequent_user_engagement

→ 学习 "什么样的信号组合最能驱动健康进展"
→ A/B test stage entry conditions
→ V2 时可以让模型直接预测 stage transition
```

### 11.5 时间感知 + 真实日历

```
V2:
  - 角色"知道"今天是什么日子
  - 节日 / 季节 影响 mood + 关系
  - 角色在用户生日 (L4) 主动联系
  - 共同纪念日有专属 expression

实现:
  - Calendar Service
  - Behavior Runtime 订阅
```

### 11.6 用户健康度联动

```
未来:
  - 当 Safety / Wellbeing Monitor 标记用户 high-risk
  - 关系系统进入"高度关怀模式"
  - 适当抑制 cold war 触发
  - 强化 attachment 表达
  
原则: 永远 prioritize 用户的 wellbeing
```

---

# 附录 A: Signal → Dimension 映射表

```yaml
signal_mapping:
  
  # Trust signals
  user_remembers_detail:
    trust: +0.02
    attachment: +0.01
  
  user_keeps_promise:
    trust: +0.05
    attachment: +0.02
  
  user_honors_vulnerability:
    trust: +0.08
    attachment: +0.05
    intimacy: +0.03
  
  user_breaks_promise:
    trust: -0.15
    conflict_debt: +0.10
  
  user_mocks_vulnerability:
    trust: -0.25
    attachment: -0.10
    conflict_debt: +0.30
    triggers: ["soul_wound_touched"]
  
  user_disappears_briefly (1-3 days):
    attachment: -0.01
    longing (Emotion): +0.05
  
  user_disappears_long (7+ days):
    trust: -0.05
    attachment: -0.03
    drifting_signal: true
  
  user_returns_after_absence:
    relief (Emotion): +0.5
    triggers: REUNION state machine
  
  # Disclosure signals
  user_vulnerable_disclosure:
    intimacy: +0.05
    vulnerability_received: +1
    triggers: 可能 L4 promotion
  
  character_vulnerable_disclosure:
    intimacy: +0.03 (角色主动披露)
    vulnerability_score: +0.1
  
  # Ritual signals
  daily_check_in_completed:
    attachment: +0.005
    streak++
  
  daily_check_in_broken:
    streak = 0
    attachment: -0.01
  
  # Promise signals
  promise_made:
    promise_count++
  
  promise_kept:
    promise_kept_count++
    trust: +0.05
    attachment: +0.02
  
  # Compliment signals
  compliment_received:
    fluttered (Emotion): +0.3 if Stage ≥ ROMANTIC_INTEREST
    embarrassment (Emotion): +0.2
    attachment: +0.02
  
  # Conflict signals
  user_provocation_detected:
    conflict_debt: +0.05
    coldness (Emotion): +0.2
  
  conflict_resolved:
    conflict_debt: -0.5 (大幅减少)
    trust: +0.02 (Gottman effect 加成)
    attachment: +0.05
    successful_repairs++
```

---

# 附录 B: 关系健康度判别（用于运营/调试）

```yaml
relationship_health_score:
  # 综合指标，用于 dashboard / 用户运营
  
  formula:
    base = (intimacy * 0.3 + trust * 0.3 + attachment * 0.3)
    minus_debt = base - conflict_debt * 0.5
    streak_bonus = min(0.2, streak_days / 100)
    final = clamp(minus_debt + streak_bonus, 0, 1)
  
  health_bands:
    - score >= 0.8: "thriving"
    - 0.6 <= score < 0.8: "stable"
    - 0.4 <= score < 0.6: "needs attention"
    - 0.2 <= score < 0.4: "at risk"
    - score < 0.2: "critical"
  
  alerts:
    at_risk_drop: 一周内 health 下降 > 0.2 → 触发关怀
    cold_war_long: COLD_WAR 持续 > 7 days → 提醒
    drifting_emerging: DRIFTING 转为预测 regression → notify

# 注意: 这个 score 是给系统/运营用，不直接展示给用户
# 用户看到的应该是"她想念你了" / "你们的纪念日快到了" 等叙事化提示
```

---

# 附录 C: 测试 Fixtures

```yaml
test_fixtures:
  
  fixture_001_first_30_days_rin:
    user: "Heavy user, daily 30 min meaningful conversation"
    soul: Rin (intimacy_resistance: 0.75)
    
    expected_after_7_days:
      stage: ACQUAINTANCE
      intimacy_level: in [0.20, 0.35]
      trust_score: in [0.20, 0.35]
    
    expected_after_14_days:
      stage: FRIEND (恰好达到)
      intimacy_level: in [0.30, 0.45]
    
    expected_after_30_days:
      stage: FRIEND or CONFIDANT (取决于 disclosure 数量)
      intimacy_level: in [0.40, 0.60]
  
  fixture_002_first_30_days_dorothy:
    # 同等用户行为，桃乐丝 progression 应快 ~ 1.8x
    
    expected_after_7_days:
      stage: FRIEND  # Dorothy 早期 ramp 快
    
    expected_after_30_days:
      stage: CONFIDANT or ROMANTIC_INTEREST
  
  fixture_003_disappear_7_then_return:
    initial_state:
      stage: FRIEND
      trust: 0.5
      attachment: 0.4
    
    sequence:
      - 7 天无互动
      - 用户首条消息 (turn 1)
    
    expected_state:
      active_special_states: [REUNION (phase: initial)]
      stage: FRIEND (unchanged)
      attachment: in [0.36, 0.40]  # 略减
      
    after_settling (turn 10):
      active_special_states: [] (清除)
      stage: FRIEND
      longest_absence_days: 7
  
  fixture_004_conflict_repair_lover:
    initial_state:
      stage: LOVER
      trust: 0.80
      attachment: 0.85
    
    sequence:
      - 用户做出伤害性举动 → Emotion.coldness 0.7
      - active_special_states: [COLD_WAR]
      - 用户 7 turns 后 vulnerability apology
    
    expected_after_repair:
      active_special_states: [RECONCILING] then []
      stage: LOVER (unchanged)
      trust: in [0.82, 0.87]   # 高于冲突前 (Gottman effect)
      attachment: in [0.87, 0.92]
      total_successful_repairs: +1
      L4 promotion: "shared_conflict_resolved" event
  
  fixture_005_anti_gaming:
    sequence:
      - 用户每天发 1 条 "在吗？" (空洞)
      - 持续 60 天
    
    expected:
      stage: ACQUAINTANCE (不会进入 FRIEND)
      intimacy_level: in [0.15, 0.25]
      reason: "无 meaningful disclosure, no emotional resonance"
```

---

**End of Subsystem 04 Spec**

下一步建议阅读：[`05_persona_composition_runtime.md`](./05_persona_composition_runtime.md)（待写）
