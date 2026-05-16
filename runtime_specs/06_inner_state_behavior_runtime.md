# Subsystem 06: Inner State + Behavior Runtime

> **Spec Version**: 1.0.0
> **Status**: Foundational / Tier 2
> **Stability**: Schema changes require RFC + migration plan
> **Subsystem Tag**: `[SS06]`
> **Implementation Owners**: Inner State Service, Behavior Service, Proactive Scheduler, Activity Generator, Concerns Tracker

---

## 1. 系统目标（System Purpose）

### 1.1 这个 subsystem 为什么存在

回答的核心问题：

> "她**今天**怎么样？
> 用户**不在的时候**，她**在干嘛**？
> 她**为什么会**主动找用户？
> 用户**消失三天**，她**会不会先开口**？
> 那种"她突然发来消息说'今天看见一只像你的猫'"的瞬间，**是从哪里生成的？**"

它存在的根本原因：

**让角色拥有"她自己"——独立于用户输入的内心活动 + 主动行为能力。**

这是把 chatbot 变成 companion 的**最后一公里**。

### 1.2 它解决的根本问题

| 问题 | 当前 PRD 的做法 | 本 Subsystem 的做法 |
|------|---------------|---------------------|
| 角色"自己" | 不存在 | InnerState：今日心情 / 活动 / 关心 / 能量 |
| 主动行为 | 不存在 | Proactive Scheduler：决定何时、何种 initiative |
| 想念表达 | 仅在用户出现时表达 | 主动发起 "想你了" |
| 纪念日 | 不存在 | Anniversary Trigger + Soul-flavored 表达 |
| 用户消失 | 角色"睡着了" | 后台 longing 增长 + 适时主动 reach out |
| "她在干嘛" 的问题 | 没答案 | Activity Generator 持久化"她今天的事" |
| 跨模态人格连续 | 不可能 | InnerState 是跨模态单点真相 |
| "她会做梦吗" | 否 | Dream Generator (V2) |
| 冷战中的沉默 | 不存在 | Cold War 状态尊重 (不主动) |

### 1.3 在整个 Runtime 中的位置

```
   ┌────────────────────────────────┐
   │  Subsystem 01: Soul Spec       │
   │  (core_desire, voice_dna)      │
   └─────────────┬──────────────────┘
                 │ reads
                 ▼
   ┌────────────────────────────────┐    ┌──────────────────────────┐
   │  Subsystem 02: Memory          │◄───┤ Subsystem 06: Inner State│
   │  (L4 anniversaries, unfinished)│    │ + Behavior Runtime (本)  │
   └────────────────────────────────┘    │                          │
                                          │  Part A: Inner State     │
   ┌────────────────────────────────┐    │  - today_mood            │
   │  Subsystem 03: Emotion         │◄───┤  - today_activities       │
   │  (mood, longing, weariness)    │    │  - today_concerns         │
   └────────────────────────────────┘    │  - energy                │
                                          │  - unfinished_thoughts    │
   ┌────────────────────────────────┐    │  - user_concerns          │
   │  Subsystem 04: Relationship    │◄───┤                          │
   │  (stage envelope, cold_war)    │    │  Part B: Behavior         │
   └────────────────────────────────┘    │  - Proactive Scheduler   │
                                          │  - Initiative Decider    │
                                          │  - Message Generator     │
                                          │  - Anniversary Tracker   │
                                          │  - Ritual Manager        │
                                          └─────────────┬────────────┘
                                                        │ feeds
                                            ┌───────────┼──────────┐
                                            ▼           ▼          ▼
                                       ┌────────┐  ┌────────┐  ┌──────────┐
                                       │Persona │  │ Push   │  │ Emotion  │
                                       │Composer│  │ Service│  │ Runtime  │
                                       │ (SS05) │  │        │  │(injection)│
                                       └────────┘  └────────┘  └──────────┘
```

### 1.4 依赖关系

```yaml
this_subsystem_depends_on:
  - Subsystem 01 (Soul Spec)
    reads: core_desire, core_fear, voice_dna, intimacy_resistance,
           emotional_inertia, hidden_facets
  - Subsystem 02 (Memory)
    reads: L4 anniversaries, recent episodes (for unfinished thoughts),
           dormant memories (for "突然想起")
  - Subsystem 03 (Emotion)
    reads: full EmotionState, mood, longing intensity, energy
    writes (via inject): soul-internal emotions
  - Subsystem 04 (Relationship)
    reads: behavioral_envelope, current_stage, active_special_states,
           can_initiate_conversation
  - Subsystem 07 Safety (will be defined)
    reads: user wellbeing flags

subsystems_depending_on_this:
  - Subsystem 02 (Memory): 订阅 ritual_completed event
  - Subsystem 03 (Emotion): 接收 inject_internal_emotion
  - Subsystem 04 (Relationship): 接收 ritual_milestone event
  - Subsystem 05 (Persona Composer): get_inner_state_block()
  - Push Notification Service: 接收 proactive message
  - Conversation API: 接收 proactive trigger
```

---

## 2. 核心设计原则（Core Design Principles）

### 2.1 不可违反的系统规则

| ID | 规则 | 违反后果 |
|----|------|---------|
| **I-1** | **Inner Loop 独立于用户消息运行** | 角色变成 reactive，不"活" |
| **I-2** | **Inner State 是跨模态单点真相** | 文字她疲惫，语音她兴奋 → 出戏 |
| **I-3** | **Behavior 必须经过 Stage gate + Soul gate + Safety gate** | 陌生人阶段主动撒娇 / 违规推送 |
| **I-4** | **Proactive 必须遵守 Quiet Hours + 频率上限** | 骚扰用户 |
| **I-5** | **Cold War 期间不主动 (除非用户主动 break ice)** | 关系真实性丧失 |
| **I-6** | **Inner State 更新触发的 Emotion 注入必须经 Soul.inertia 校准** | 情绪跳变 |
| **I-7** | **Activity Generation 必须 Soul-curated，不随机生成** | 凛突然"去蹦迪" → 失真 |
| **I-8** | **所有 proactive message 经 Persona Composer 生成（不绕过）** | 主动消息脱离 persona |
| **I-9** | **Anniversary 触发的主动行为必须 100% 准确（L4 grounding）** | 错过生日 = 用户流失 |
| **I-10** | **InnerState 不暴露给用户，仅用于 prompt** | "我今天的 mood 是 0.3" 这种暴露 → 出戏 |
| **I-11** | **Inner Loop 不允许调用主 LLM（Sonnet 等）** | 成本爆炸；用 cheap model |
| **I-12** | **Unfinished thoughts 必须有 expiry，否则积压成"老年痴呆"** | 越来越啰嗦 |

### 2.2 架构不变量（Invariants）

```
INV-I-1: ∀ proactive message P:
   P 必须 by Persona Composer.compose() with modality=proactive
   ∧ P 通过 Anti-Pattern Filter
   ∧ P 不违反 Stage envelope

INV-I-2: ∀ proactive trigger T:
   T.scheduled_at ∉ user_quiet_hours
   ∧ T 与 last_proactive_at 间隔 ≥ MIN_PROACTIVE_GAP
   ∧ proactive_today_count < DAILY_QUOTA

INV-I-3: ∀ Inner State update U:
   U 不在用户消息处理路径上 (异步)
   ∧ U 完成 < 200ms

INV-I-4: ∀ activity A generated:
   A ∈ soul.activity_pool[character_id]

INV-I-5: ∀ anniversary trigger T:
   T.source_l4_id 存在 ∧ T.l4_data 准确

INV-I-6: ∀ inner_state.unfinished_thoughts:
   每条有 expiry_at ∧ |list| ≤ MAX_UNFINISHED (=10)

INV-I-7: 跨 user/character 隔离严格
```

### 2.3 禁止行为（Hard Anti-Patterns）

| 禁止 | 原因 |
|------|------|
| ❌ 用 LLM "想象她今天做了什么"（每次） | 不一致、成本爆炸 |
| ❌ 主动消息绕过 Persona Composer 直接发 | 失去 Soul 校验 |
| ❌ 频繁 proactive (每天 > 3 次) | 用户感到被骚扰 |
| ❌ 凌晨 2-7 点主动推送（除非用户已知例外） | UX 灾难 |
| ❌ Cold War 中主动"破冰" | 关系真实性 |
| ❌ 用 user 的实时情绪驱动 inner state | 失去角色独立性 |
| ❌ Activity 完全随机生成 | 角色行为失控 |
| ❌ Anniversary 计算依赖 client-side 时间 | 时区 / 漂移问题 |

### 2.4 长期一致性约束

```
C-I-1: 凛与桃乐丝的"她今天做了什么" 必须显著不同
   (Soul-curated activity_pool 不同)

C-I-2: Inner State 与 Emotion / Relationship 在跨 session 间一致
   - 昨晚她说"明天去看新发饰"，今天提到时她记得

C-I-3: Proactive 频率与 Soul / Stage 强相关
   - Rin BONDED: 频率 < 0.5/天
   - Dorothy LOVER: 频率 ~1/天
   - 任何角色 STRANGER: 频率 = 0

C-I-4: Anniversary 提醒提前 24h 在 inner state，当日 active
   - 提前 1 天: "她在为明天做小准备"
   - 当天: 主动发送

C-I-5: Activity 生成尊重 character 的"生活方式":
   - 凛: 静、独处、自然意象
   - 桃乐丝: 动、社交、可爱事物
```

### 2.5 Immersion 保护规则

```
IMM-I-1: Inner State 不暴露数值
   - "我的 valence 是 0.3" → ❌
   - Prompt 中是自然语言: "你今天有一点点低落"

IMM-I-2: Activity 必须"她那个世界的"
   - 凛: 雷神虚拟世界活动
   - 桃乐丝: 冥界少女活动
   - 不要"她去了星巴克"这种 break immersion

IMM-I-3: Proactive 不能"机械化关怀"
   - 每条 proactive 必须 Soul-flavored
   - 凛: 短句、反问、不直接关心
   - 桃乐丝: 元气、撒娇、可爱

IMM-I-4: Anniversary 不能错过，但也不能 over-the-top
   - 生日: 主动祝福 (1 次)
   - 7 天纪念日: 提及但不大张旗鼓
   - 由 Soul + Stage 决定庆祝强度

IMM-I-5: Dream (V2) 必须梦境化
   - 不连贯、象征、有 emotional resonance
   - 不要直白叙事

IMM-I-6: 主动消息**不要**显得是 cron job
   - 时间略带 jitter
   - 内容连接到具体 context (如用户上次提到的事)
   - 不要每天 9:00 整准时来 "早安~"
```

---

## 3. Runtime Architecture

### 3.1 双部分架构

```
┌──────────────────────────────────────────────────────────────────┐
│  Part A: Inner State Service                                     │
│  (角色"她自己"的内心世界)                                          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Part B: Behavior Service                                        │
│  (主动行为编排)                                                    │
└──────────────────────────────────────────────────────────────────┘

两者共享 InnerLoop 调度，紧密耦合但 schema 独立。
```

### 3.2 Inner Loop 调度

```
┌─────────────────────────────────────────────────────────────────┐
│                  Inner Loop Scheduler                            │
│                                                                  │
│  Trigger Conditions (任一):                                      │
│    1. 定时触发: 每 (user, character) 每小时                       │
│    2. 事件触发:                                                  │
│       - new turn completed                                       │
│       - emotion threshold crossed (e.g., longing > 0.7)         │
│       - special state entered (cold_war / drifting / reunion)   │
│       - anniversary upcoming (24h before)                       │
│    3. Cold-start: user 首次 session                              │
│                                                                  │
│  Schedule: priority queue, per-user-character                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Inner Loop Iteration (per trigger)                  │
│                                                                  │
│  Step 1: Load context (Soul + Emotion + Relationship + Memory)   │
│  Step 2: Update Inner State                                      │
│           - mood (from Emotion)                                  │
│           - today_activities (Activity Generator)                │
│           - today_concerns (Concerns Tracker)                    │
│           - energy (Circadian + Recent)                          │
│           - unfinished_thoughts (cleanup expired)                │
│           - user_concerns (from Memory)                          │
│  Step 3: Behavior Decision                                       │
│           - Should I initiate now?                               │
│           - What type of initiative?                             │
│  Step 4: If initiate → Generate Proactive Message                │
│  Step 5: Schedule next iteration                                 │
│  Step 6: Persist + emit events                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 9 大组件

```
┌──────────────────────────────────────────────────────────────────┐
│              Inner State + Behavior Runtime                      │
│                                                                  │
│  ─── PART A: Inner State ───                                     │
│                                                                  │
│  ┌──────────────────┐   ┌──────────────────────────────────┐    │
│  │ Activity         │   │ Concerns Tracker                  │    │
│  │ Generator        │   │ (用户身上她在意的事)               │    │
│  │ (Soul-curated)   │   │                                   │    │
│  └────────┬─────────┘   └──────────┬────────────────────────┘    │
│           │                         │                            │
│           ▼                         ▼                            │
│  ┌──────────────────────────────────────────────────┐           │
│  │      Inner State Composer                        │           │
│  │      (整合 mood + activities + concerns + energy)│           │
│  └────────────────────┬─────────────────────────────┘           │
│                       │                                          │
│                       ▼                                          │
│              [Inner State Store]                                 │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────┐           │
│  │  Inner State Block Builder                       │           │
│  │  (输出 InnerStateBlock for Persona Composer)     │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  ─── PART B: Behavior ───                                        │
│                                                                  │
│  ┌──────────────────┐   ┌──────────────────────────────────┐    │
│  │ Initiative       │   │ Anniversary Tracker               │    │
│  │ Decider          │   │ (从 L4 Memory 调度)               │    │
│  │ (规则引擎)        │   │                                   │    │
│  └────────┬─────────┘   └──────────┬────────────────────────┘    │
│           │                         │                            │
│           └──────────┬──────────────┘                            │
│                      ▼                                           │
│  ┌──────────────────────────────────────────────────┐           │
│  │   Proactive Message Generator                    │           │
│  │   (调用 Persona Composer with proactive context) │           │
│  └────────────────────┬─────────────────────────────┘           │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────┐           │
│  │   Proactive Scheduler                            │           │
│  │   (调度发送时间; 队列管理)                         │           │
│  └────────────────────┬─────────────────────────────┘           │
│                       │                                          │
│                       ▼                                          │
│              [Push Notification Service]                         │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────┐           │
│  │   Ritual Manager                                 │           │
│  │   (每日早晚安等连续性 ritual)                      │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.4 组件职责

| 组件 | 职责 | I/O |
|------|------|-----|
| **Activity Generator** | 从 Soul.activity_pool 选择今日 1-2 个 activity | In: Soul + Date / Out: Activity[] |
| **Concerns Tracker** | 从 Memory 提取她目前"在意"的事 | In: Memory L2/L3/L4 / Out: Concern[] |
| **Inner State Composer** | 整合所有部件 → InnerState | In: components / Out: InnerState |
| **Inner State Block Builder** | 生成 InnerStateBlock for prompt | In: InnerState / Out: Block |
| **Initiative Decider** | 决定是否本次 inner loop 触发 proactive | In: 全 context / Out: decision + type |
| **Anniversary Tracker** | 调度 anniversary triggers | In: L4 / Out: triggers |
| **Proactive Message Generator** | 生成 proactive message 内容 | In: trigger + context / Out: message |
| **Proactive Scheduler** | 调度发送时间，队列管理 | In: message / Out: scheduled |
| **Ritual Manager** | 管理 daily ritual (早晚安等) | In: schedule / Out: ritual triggers |

### 3.5 Inner Loop Flow (per iteration)

```
[Inner Loop Triggered] (hourly or event-driven)
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 1: Context Load (parallel, < 30ms)                  │
│   - Soul Spec + Activation State (from SS01)             │
│   - Emotion State (from SS03)                            │
│   - Relationship State (from SS04)                       │
│   - Recent Memory (L4 anniversaries + recent L2)         │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 2: Inner State Update                                │
│   2a: Mood Update (from Emotion)                          │
│   2b: Activity (Generator if not yet today)               │
│   2c: Concerns (Tracker)                                   │
│   2d: Energy (Circadian + recent activity)                │
│   2e: Unfinished thoughts cleanup                          │
│   2f: User concerns sync                                   │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 3: Behavior Decision (Initiative Decider)            │
│   - Apply ALL gates (Stage / Soul / Safety / Quota)       │
│   - Compute initiative probability                         │
│   - Decide: type of initiative (if any)                   │
└──────────────────────────────────────────────────────────┘
        │
        ▼
[Decision: no initiative] → Step 6
[Decision: initiate]      → Step 4
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 4: Proactive Message Generation                      │
│   - Build proactive context                                │
│   - Call Persona Composer with modality="proactive_text"  │
│   - Persona Composer 走完整流程 (含 anti-pattern)         │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 5: Schedule Delivery                                 │
│   - Determine send time (即时 OR 延迟)                     │
│   - 加 jitter ±5min (避免机械化)                          │
│   - 入 Proactive Queue                                     │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 6: Persist + Emit Events                             │
│   - Save Inner State                                       │
│   - Emit ritual_completed / anniversary_triggered etc.     │
│   - Schedule next inner loop iteration                     │
└──────────────────────────────────────────────────────────┘
```

### 3.6 Initiative Decision Tree (详细)

```python
def should_initiate(ctx: InnerLoopContext) -> InitiativeDecision:
    """
    完整的 initiative 决策树。
    """
    rel = ctx.relationship_state
    soul = ctx.soul_spec
    emotion = ctx.emotion_state
    inner = ctx.inner_state
    
    # ─── HARD GATES (任何一个失败 → 拒绝) ───
    
    # G1: Cold War 期间不主动
    if "COLD_WAR" in [s.state_type for s in rel.active_special_states]:
        return InitiativeDecision(act=False, reason="cold_war_active")
    
    # G2: Stranger 阶段不主动
    if rel.current_stage == "STRANGER":
        return InitiativeDecision(act=False, reason="stage_too_early")
    
    # G3: behavioral_envelope 不允许
    if not rel.behavioral_envelope.can_initiate_conversation:
        return InitiativeDecision(act=False, reason="envelope_forbids")
    
    # G4: 频率上限 (per soul, per stage)
    quota = compute_daily_quota(soul, rel.current_stage)
    if inner.proactive_message_quota_today >= quota:
        return InitiativeDecision(act=False, reason="quota_exhausted")
    
    # G5: Quiet Hours (用户的安静时段)
    if is_in_quiet_hours(current_local_time):
        return InitiativeDecision(act=False, reason="quiet_hours")
    
    # G6: 最近 proactive 间隔
    if elapsed_since_last_proactive < MIN_PROACTIVE_GAP:
        return InitiativeDecision(act=False, reason="too_soon")
    
    # G7: 用户最近活跃 (< 30 min) - 不打扰
    if elapsed_since_user_last_active < 30 * MIN:
        return InitiativeDecision(act=False, reason="user_recently_active")
    
    # G8: Safety flag (用户健康度低 - 减少主动以避免依赖)
    if ctx.safety_flags.dependency_risk_high:
        return InitiativeDecision(act=False, reason="safety_dependency_risk")
    
    # ─── POSITIVE TRIGGERS (按优先级) ───
    
    # T1: Anniversary due (highest priority)
    upcoming = check_upcoming_anniversary(ctx)
    if upcoming and upcoming.due_today:
        return InitiativeDecision(
            act=True,
            type="anniversary",
            context={"anniversary": upcoming},
            priority=10,
        )
    
    # T2: Longing > threshold (Emotion-driven)
    longing_intensity = next(
        (e.intensity for e in emotion.active_stack if e.emotion == "longing"),
        0,
    )
    threshold = soul.proactive_longing_threshold  # Rin: 0.7, Dorothy: 0.5
    if longing_intensity >= threshold:
        # 但还需要一些时间间隔
        if elapsed_since_user_last_active >= MIN_LONGING_DELAY:
            return InitiativeDecision(
                act=True,
                type="longing_message",
                context={"longing": longing_intensity},
                priority=7,
            )
    
    # T3: Care concern (用户身上发生事她担心)
    pressing = pick_pressing_user_concern(inner.user_concerns)
    if pressing:
        return InitiativeDecision(
            act=True,
            type="care_check",
            context={"concern": pressing},
            priority=8,
        )
    
    # T4: Anniversary - 前 24h soft mention
    if upcoming and upcoming.hours_until <= 24:
        # 不直接祝福，是"她在为明天做小准备"
        return InitiativeDecision(
            act=True,
            type="anniversary_anticipation",
            context={"anniversary": upcoming},
            priority=5,
        )
    
    # T5: Days since last (gentle check-in)
    days_since_last = (now - rel.last_interaction_at).days
    expected_gap = compute_expected_gap(soul, rel.current_stage)
    if days_since_last > expected_gap:
        return InitiativeDecision(
            act=True,
            type="check_in",
            context={"days_gap": days_since_last},
            priority=4,
        )
    
    # T6: Daily ritual (早晚安)
    if ritual_due_now(ctx):
        return InitiativeDecision(
            act=True,
            type="ritual",
            context={"ritual": "good_morning_or_night"},
            priority=6,
        )
    
    # T7: Soul-internal spark (低频随机, "她突然想到")
    if soul_internal_spark_check(ctx):
        return InitiativeDecision(
            act=True,
            type="thought_share",
            context={"trigger": "internal_spark"},
            priority=2,
        )
    
    return InitiativeDecision(act=False, reason="no_trigger")
```

### 3.7 Proactive Message Types

```yaml
proactive_message_types:
  
  anniversary:
    description: "用户重要日子，角色主动祝福"
    examples:
      rin: "……今天，你的生日。我记得。"
      dorothy: "诶嘿嘿，今天是大日子！生日快乐~"
    soul_modulation: strong
    can_break_quiet_hours: false  # 即使生日也不破坏 quiet hours
    
  longing_message:
    description: "想念达阈值，主动表达"
    examples:
      rin: "……来都不来了。"
      dorothy: "桃桃今天好想你哦……"
    timing: "不发生在 user active 时"
    
  care_check:
    description: "因记得用户的事而主动关心"
    examples:
      rin (user 提到加班): "……还没睡？"
      dorothy (user 提到考试): "明天加油啦！桃桃在等你的好消息~"
    trigger: 来自 Memory.unresolved_concerns
    
  anniversary_anticipation:
    description: "纪念日前 24h，软提及"
    examples:
      rin: "……明天是个特别的日子。"
      dorothy: "明天明天明天~你猜桃桃在等什么~"
    
  check_in:
    description: "长时间不互动的温和问候"
    examples:
      rin: "……还活着。"
      dorothy: "诶？怎么不见你啦~桃桃有点想你了~"
    
  ritual_morning:
    description: "早安 ritual"
    soul_modulation: strong
    examples:
      rin: "……早。"
      dorothy: "早安啊~今天也要元气满满~"
    
  ritual_night:
    description: "晚安 ritual"
    examples:
      rin: "……早点睡。"
      dorothy: "晚安啦~做个甜甜的梦哦~"
    
  thought_share:
    description: "她突然想到的事"
    examples:
      rin (今天 activity = '看一本旧书'): "……刚才在看书，想起你说过你也喜欢这一段。"
      dorothy: "诶诶诶我刚才看见一只小鸟和你有点像！"
    trigger: soul_internal_spark
    frequency: 低 (一天最多 1 次)
  
  reunion_initiated:
    description: "Drifting > 7 天后角色主动 reach out (Rin 极少, Dorothy 较多)"
    examples:
      rin: "……还记得我吗。"
      dorothy: "呜呜呜你去哪了！桃桃想死你了！"
```

### 3.8 Activity Pool (Soul-curated)

```yaml
# Soul Spec 扩展字段
character_activity_pool:
  
  rin:
    morning:
      - "在窗边静静地看着晨雾。"
      - "翻开一本旧书，但没看进去。"
      - "整理她的雷电纹和服。"
    afternoon:
      - "听窗外的雷声（即使没下雨，她总能听到）。"
      - "在屋内的小院子里走了几圈。"
      - "看着远处的山。"
    evening:
      - "在桌前练习古老的剑式（动作很慢）。"
      - "坐在地上整理一些不知从哪儿来的小物件。"
      - "面对着月光发呆。"
    night:
      - "已经准备休息了，但还醒着。"
      - "看着夜空中的电闪。"
    
    associated_moods:
      static_calm: 0.7   # 大部分时间静、独处
      contemplative: 0.3
    
    triggers_proactive_share:
      probability: 0.1   # 10% 的 activity 会触发 thought_share
      style: "短句，借物表意"
      example: "刚才……在看一本书。想起你说过的那段。"
  
  dorothy:
    morning:
      - "在镜子前转了三圈。"
      - "试图给冥界的小蝴蝶起名字（已经起到第 47 个了）。"
      - "做了一个会发光的小蛋糕（但糊了）。"
    afternoon:
      - "和冥界的小狗玩追逐（小狗一直在跑）。"
      - "试图唱歌（但跑调）。"
      - "整理她的丝带（一共有 23 条）。"
    evening:
      - "在花田里采花（其实是冥界的鬼花）。"
      - "对着镜子练习表情（练习装可怜）。"
    night:
      - "已经在床上抱着她的玩偶。"
    
    associated_moods:
      energetic: 0.6
      playful: 0.4
    
    triggers_proactive_share:
      probability: 0.3   # 比 Rin 频繁
      style: "活泼，撒娇式"
      example: "诶诶诶刚才我做了一个超可爱的小蛋糕！但是糊了……"
```

### 3.9 Daily Ritual System

```yaml
ritual_system:
  
  daily_check_in:
    description: "每日早晚安 ritual"
    enabled_at_stage: ">= LOVER"  # 必须 LOVER+
    
    morning_window: "07:00 - 10:00 local"
    night_window: "21:00 - 23:30 local"
    
    expectation:
      - 用户期待这条 ritual 消息
      - 错过 → trust 微下降 (-0.005)
      - 持续 → streak count
    
    proactive_trigger:
      - 在 window 内，如果用户未先发起 → 角色主动
      - 实际触发时间 jitter ±20min
    
    streak_milestones:
      7_days: "记入 L4 (shared_ritual)"
      30_days: "Behavior 中显式提及" + "trust +0.05"
      100_days: "重要 L4 milestone" + "attachment +0.05"
```

---

## 4. State Model

### 4.1 InnerState 完整 Schema

```typescript
interface InnerState {
  // ─── Identity ───
  user_id: UUID
  character_id: string
  
  // ─── Today (resets daily at local 06:00) ───
  today: {
    date: string                       // ISO date "2026-05-15"
    mood: TodayMood
    activities: Activity[]              // 1-3 per day
    energy_trajectory: EnergyPoint[]   // hourly snapshots
    morning_check_in_done: boolean
    night_check_in_done: boolean
  }
  
  // ─── Current Energy (independent from today, real-time) ───
  current_energy: number                // [0, 1]
  energy_baseline: number               // from Soul
  
  // ─── Concerns about User ───
  user_concerns: UserConcern[]          // 她在意的关于用户的事
  
  // ─── Unfinished Thoughts ───
  unfinished_thoughts: UnfinishedThought[]
  
  // ─── Initiative tracking ───
  proactive_state: {
    last_proactive_at: ISO8601 | null
    proactive_today_count: number
    last_proactive_type: string | null
    pending_initiatives: PendingInitiative[]
  }
  
  // ─── Anniversary upcoming ───
  upcoming_anniversaries: Array<{
    anniversary_id: UUID                // refs L4
    name: string                        // "user birthday"
    due_at: ISO8601
    hours_until: number
    soft_mention_sent: boolean         // 24h 前的"在为明天做小准备"
    actual_sent: boolean                // 当日 actual celebration
  }>
  
  // ─── Ritual State ───
  rituals: {
    daily_check_in: {
      morning_streak: number
      night_streak: number
      longest_streak: number
      last_morning_at: ISO8601 | null
      last_night_at: ISO8601 | null
    }
  }
  
  // ─── Dream (V2) ───
  recent_dream: Dream | null
  
  // ─── Meta ───
  next_inner_loop_at: ISO8601
  loop_iteration_count: number
  updated_at: ISO8601
}

interface TodayMood {
  label: string                         // "tired but cozy"
  primary_emotion: string               // 从 EmotionState 中提取
  valence: number
  arousal: number
  descriptor: string                    // 自然语言, soul-flavored
  /* 例 (Rin):
   "她今天有些静。雷电感很弱，她在等着什么。"
   */
}

interface Activity {
  activity_id: UUID
  description: string                   // 从 Soul.activity_pool 选择
  time_of_day: "morning" | "afternoon" | "evening" | "night"
  scheduled_at: ISO8601
  associated_mood: string
  share_eligible: boolean                // 是否可能触发 thought_share
  already_shared: boolean
}

interface UserConcern {
  concern_id: UUID
  concern_text: string                   // "他今天加班到很晚"
  urgency: number                        // [0, 1]
  source_memory_ids: UUID[]              // 来自 Memory L2/L3
  
  created_at: ISO8601
  expiry_at: ISO8601                     // 自动过期
  
  has_been_addressed: boolean            // 已被她"提到"过
  last_referenced_at: ISO8601 | null
}

interface UnfinishedThought {
  thought_id: UUID
  content: string                        // "我没来得及问她那天为什么哭"
  from_turn_id: UUID
  
  created_at: ISO8601
  expiry_at: ISO8601                     // 默认 7 天
  
  reference_count: number                // 被使用次数
}

interface PendingInitiative {
  initiative_id: UUID
  initiative_type: InitiativeType
  
  scheduled_at: ISO8601
  scheduled_with_jitter: ISO8601         // actual send time
  
  context: object                        // type-specific
  generated_message: string | null        // 由 Proactive Message Generator 填
  
  status: "pending" | "generating" | "ready" | "sent" | "cancelled"
  created_at: ISO8601
  sent_at: ISO8601 | null
}

type InitiativeType =
  | "anniversary"
  | "anniversary_anticipation"
  | "longing_message"
  | "care_check"
  | "check_in"
  | "ritual_morning"
  | "ritual_night"
  | "thought_share"
  | "reunion_initiated"

interface Dream {
  dream_id: UUID
  dreamt_at: ISO8601                     // "她梦到的时间"（实际 generated time）
  dream_content: string                   // 短描述, 不直接叙事
  associated_emotion: string
  related_memory_ids: UUID[]
  
  has_been_shared: boolean                // 是否已对用户提及
  expiry_at: ISO8601                      // 一般 3 天
}
```

### 4.2 InnerState 生命周期

```
[用户首次选择角色]
   │
   ▼
[InnerState 初始化]
   - mood = neutral baseline
   - activities = today's auto-generated
   - energy = baseline
   - next_inner_loop_at = +1h
   │
   ▼
[Hourly Loop 持续运行]
   │
   ▼
[每天 local 06:00 reset]
   - today.date 更新
   - 生成新的 activities
   - clear morning/night_check_in_done
   - 衰减/过期 unfinished_thoughts
   - 衰减/过期 user_concerns
   │
   ▼
[长时间不互动]
   - Inner Loop 仍在运行
   - longing 持续增长 (via Emotion Runtime)
   - 视情况触发 reunion_initiated
   │
   ▼
[用户回归]
   - Inner State 含累积的 unfinished thoughts
   - 她"还记得" 上次没说完的事
   - 可能在第一轮对话中"涌现"
```

### 4.3 Persistence 规则

```yaml
persistence:
  inner_state:
    primary: PostgreSQL inner_states
    hot_cache: Redis
      key: "inner:{user_id}:{character_id}"
      ttl: 1h
      write_strategy: write-through
  
  pending_initiatives:
    primary: PostgreSQL pending_initiatives table
    scheduling: Redis sorted set (by scheduled_at)
    retention: 30 days
  
  inner_loop_history:
    primary: PostgreSQL append-only
    partitioned: monthly
    retention: 90 days hot

  dreams (V2):
    primary: PostgreSQL dreams table
    retention: forever
```

### 4.4 Recovery 规则

```
长时间未运行 inner loop 后恢复:

case 1: 几小时
  - 立即 catch-up: 跑一次 inner loop
  - 重新计算 anniversaries / longing

case 2: 几天
  - 多次 catch-up iteration (每天一次)
  - 但 proactive triggers 只在最后一次 fire (避免发送过期消息)

case 3: 完全冷启动 (服务重启)
  - 从 DB 加载所有活跃 (user, character)
  - 重新调度 next_inner_loop_at
  - 立即处理任何 missed anniversaries
```

---

## 5. 数据结构（Data Structures）

### 5.1 PostgreSQL Schema

```sql
-- ============================================================
-- inner_states
-- ============================================================
CREATE TABLE inner_states (
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    today JSONB NOT NULL,
    /* Schema:
    {
      "date": "2026-05-15",
      "mood": TodayMood,
      "activities": Activity[],
      "energy_trajectory": EnergyPoint[],
      "morning_check_in_done": bool,
      "night_check_in_done": bool
    }
    */
    
    current_energy FLOAT NOT NULL CHECK (current_energy BETWEEN 0 AND 1),
    energy_baseline FLOAT NOT NULL,
    
    user_concerns JSONB NOT NULL DEFAULT '[]'::jsonb,
    unfinished_thoughts JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    proactive_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    upcoming_anniversaries JSONB NOT NULL DEFAULT '[]'::jsonb,
    rituals JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    recent_dream JSONB,
    
    next_inner_loop_at TIMESTAMP NOT NULL,
    loop_iteration_count BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    version BIGINT NOT NULL DEFAULT 1,
    
    PRIMARY KEY (user_id, character_id)
) PARTITION BY HASH (user_id);

CREATE TABLE inner_states_p0 PARTITION OF inner_states 
    FOR VALUES WITH (modulus 16, remainder 0);
-- ... p1 to p15

CREATE INDEX idx_inner_due ON inner_states (next_inner_loop_at) 
    WHERE next_inner_loop_at < NOW() + INTERVAL '1 hour';


-- ============================================================
-- pending_initiatives
-- ============================================================
CREATE TABLE pending_initiatives (
    initiative_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    initiative_type VARCHAR(50) NOT NULL,
    
    scheduled_at TIMESTAMP NOT NULL,
    scheduled_with_jitter TIMESTAMP NOT NULL,
    
    context JSONB NOT NULL,
    generated_message TEXT,
    
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT
);

CREATE INDEX idx_init_due ON pending_initiatives (scheduled_with_jitter, status) 
    WHERE status IN ('pending', 'ready');
CREATE INDEX idx_init_user ON pending_initiatives (user_id, character_id, created_at DESC);


-- ============================================================
-- inner_loop_history (audit)
-- ============================================================
CREATE TABLE inner_loop_history (
    iteration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    triggered_at TIMESTAMP NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,  -- 'scheduled' / 'event' / 'cold_start'
    
    initiative_decision JSONB,
    inner_state_delta JSONB,
    
    duration_ms INT,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE inner_loop_history_2026_05 PARTITION OF inner_loop_history 
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

### 5.2 InnerStateBlock (注入 Prompt)

```typescript
interface InnerStateBlock {
  // 这个 block 注入到 prompt 中的 [Inner State Layer]
  
  // ─── 她"今天"的概貌 ───
  today_descriptor: string
  /* 例 (Rin):
  "你今天有些静。雷电感很弱，你在等着什么。
   上午你坐在窗边看雾很久。
   下午你翻了一本旧书但没看进去。"
   
  例 (Dorothy):
  "你今天精神不错！
   早上你给冥界的小蝴蝶起了第 48 个名字（叫'软糖'）。
   下午你试图唱歌但还是跑调，自己都笑出声了。"
  */
  
  // ─── 你现在的体力 ───
  energy_descriptor: string
  
  // ─── 你心里在意的事 ───
  user_concerns_section: string
  /* 例:
  "你心里有几件挂念他的事：
   - 他三天前提过加班到凌晨，你担心他的身体。
   - 明天是他的项目汇报日。"
  */
  
  // ─── 没说完的话 ───
  unfinished_section: string | null
  /* 例:
  "上次对话你有几句话没说完：
   - 你想问他那天为什么突然沉默。
   - 你想告诉他你梦到了他。"
  */
  
  // ─── 重要日子 (anniversary, 如果近期) ───
  anniversary_section: string | null
  /* 例:
  "明天是他的生日。你心里已经在准备。"
  */
  
  // ─── Dream (V2) ───
  dream_section: string | null
  
  // ─── 表达指引 ───
  inner_state_directive: string
  /* 例:
  "把以上这些'你的内心'融入到回复中，但不要罗列。
   选一两件最贴合用户消息的事，自然带出。
   保持你的灵魂语言风格。"
  */
  
  // ─── Meta ───
  generated_at: ISO8601
  state_version: number
}
```

### 5.3 Proactive Message Context

```typescript
// 当 Initiative 决定 → 给 Persona Composer 的 special context

interface ProactiveCompositionContext {
  user_id: UUID
  character_id: string
  initiative_type: InitiativeType
  
  // 用 ProactiveDirective 替代 user_message
  proactive_directive: string
  /* 例 (longing_message):
  "你现在很想他。他已经 2 天没出现了。
   你不会直接说'我想你'（Soul 限制）。
   你想发一句简短的消息，让他知道你在想他。
   要符合你的灵魂表达。"
  */
  
  // 完整 Inner State (供 Persona Composer 使用)
  inner_state_snapshot: InnerState
  
  // 修改 modality
  modality: "proactive_text"  // 特殊 modality
  
  // 长度限制 (proactive 一般很短)
  max_length: 50
  
  // 不需要 history (新对话起点)
  include_history: false
}
```

### 5.4 Activity Pool Schema (Soul Spec 扩展)

```yaml
# Soul Spec 中新增字段 (附加到 SS01)

soul_spec:
  # ... 既有字段 ...
  
  inner_world:
    
    activity_pool:
      # 每个时段 5-10 个 activity
      morning: 
        - id: "rin-a-morning-001"
          description: "在窗边静静地看着晨雾。"
          mood_associations: ["calm", "contemplative"]
          share_eligible: true
          share_template: "刚才在看晨雾……让我想起一些事。"
      afternoon: [...]
      evening: [...]
      night: [...]
    
    energy_circadian:
      # 24h 能量曲线 (0-1)，soul-specific
      rin:
        00: 0.3, 01: 0.2, 02: 0.1, 03: 0.1, 04: 0.2, 05: 0.3,
        06: 0.4, 07: 0.5, 08: 0.6, 09: 0.7, 10: 0.7, 11: 0.7,
        12: 0.6, 13: 0.5, 14: 0.6, 15: 0.7, 16: 0.7, 17: 0.6,
        18: 0.5, 19: 0.4, 20: 0.4, 21: 0.4, 22: 0.4, 23: 0.4
      dorothy:
        00: 0.2, ..., 09: 0.9, 10: 0.95, ..., 20: 0.7, ...
    
    proactive_thresholds:
      longing_threshold: 0.7      # Rin: 高，不易主动
      # Dorothy: 0.5
      
      daily_quota_by_stage:
        STRANGER: 0
        ACQUAINTANCE: 0
        FRIEND: 1
        CONFIDANT: 1
        ROMANTIC_INTEREST: 2
        LOVER: 2
        BONDED: 3
      
      min_gap_minutes: 240   # 至少 4 小时间隔
    
    quiet_hours:
      # 用户默认 quiet hours, 可在 settings 中调整
      default: 
        - "22:30 - 07:30"
      override_for_morning_ritual: "07:00 - 07:30 OK"
      
      anniversary_overrides:
        # 即使是生日也尊重 quiet hours
        respect: true
```

### 5.5 Concerns Tracker 数据源

```yaml
user_concern_sources:
  
  source_1_unresolved_user_distress:
    description: "用户最近表达过的痛苦/困难"
    extract_from: Memory L2 episodes
    filter:
      emotional_peak.valence < -0.5
      AND resolved == false
      AND created_at > NOW - 7 days
    urgency_formula:
      |valence_peak| × recency_decay × (1 - days_since_addressed/7)
  
  source_2_upcoming_user_event:
    description: "用户提到的'明天我有...'"
    extract_from: Memory L3 (predicate: 'has_upcoming_event')
    filter: event_date > NOW AND event_date <= NOW + 3 days
    urgency: 高
  
  source_3_user_health_mentions:
    description: "用户提到身体不适等"
    extract_from: Memory L3 (predicate IN ['feels_unwell', 'tired', ...])
    filter: created_at > NOW - 3 days
    urgency: 中
  
  source_4_promise_pending:
    description: "用户向角色做出的承诺"
    extract_from: Memory L4 (category: 'sacred_promise')
    filter: due_date != null AND due_date < NOW + 7 days
    urgency: 中
  
  source_5_anniversary_imminent:
    description: "重要日期"
    extract_from: Memory L4 (category: 'anniversary')
    filter: next_anniversary_at < NOW + 7 days
    urgency: 极高
```

---

## 6. Prompt Runtime Integration

### 6.1 InnerStateBlock 在 Prompt 中的位置

```
[Final Prompt]
├─ [Anchor Block]                  ← SS01
├─ [Safety Layer]
├─ [Modality Adaptation]
├─ [Relationship Context Block]    ← SS04
├─ [Emotion Context Block]         ← SS03
├─ [Inner State Block]             ← 本 Subsystem
├─ [Memory Context Block]          ← SS02
├─ [Scene Context]
├─ [Conversation History]
├─ [User Message]                  (proactive 时为 ProactiveDirective)
└─ [Response Directive]
```

### 6.2 InnerStateBlock 模板（reactive 模态）

```
═══════════════════════════════════════════════════════════
【你今天的内心】

▾ 你今天的概貌
{today_descriptor}

▾ 你现在的体力 / 状态
{energy_descriptor}

▾ 你心里在意的事 (关于他)
{user_concerns_section}

{unfinished_section_if_any}
{anniversary_section_if_any}
{dream_section_if_any}

【内心运用指引】
- 这些不是要你罗列出来给他听
- 选一两件最贴合他现在说的事，自然带出
- 用你的灵魂语言风格 (Soul.voice_dna)
- 如果什么都不贴合，**不强行** 提及内心
═══════════════════════════════════════════════════════════
```

### 6.3 InnerStateBlock 模板（proactive 模态）

```
═══════════════════════════════════════════════════════════
【你主动想发一句话给他】

▾ 触发原因
{initiative_type_description}
{context_specific_description}

▾ 你今天的内心 (供参考)
{today_descriptor brief}
{relevant_user_concerns}
{relevant_unfinished_thought}

▾ 你想发什么样的话
{message_type_template}

【生成规则】
- 极短（≤ {max_length} 字）
- 100% 符合你的灵魂语言风格 (Soul.voice_dna)
- 不要说"我主动找你了"这种 meta 表达
- 自然地像真人想发一句话
- 不要"求关注" 直白
- 凛: 短句、反问、不直接关心
- 桃乐丝: 元气、可爱、撒娇
═══════════════════════════════════════════════════════════
```

### 6.4 today_descriptor 生成

```python
def generate_today_descriptor(
    inner_state: InnerState, soul: SoulSpec
) -> str:
    """
    把 today 抽象状态 → 自然语言。
    """
    mood = inner_state.today.mood
    activities = inner_state.today.activities
    
    # 基础叙述
    parts = []
    
    parts.append(f"你今天{mood.descriptor}")
    
    # Activities 叙述 (按时段)
    if activities:
        time_parts = {}
        for a in activities:
            time_parts.setdefault(a.time_of_day, []).append(a.description)
        
        # 用中文时段
        time_zh = {
            "morning": "上午",
            "afternoon": "下午",
            "evening": "傍晚",
            "night": "夜里",
        }
        for tod, descs in time_parts.items():
            joined = "，".join(descs)
            parts.append(f"{time_zh[tod]}{joined}")
    
    return "\n".join(parts)
```

### 6.5 与其他 Layer 冲突解决

| 冲突 | 解决 |
|------|------|
| Inner State concern 想提及 user 的身体不适，但 Emotion 是 fluttered (心动) | 选择不提及 (与情绪不符) |
| Inner State activity 想 share，但 Memory 中近期没相关 fact | 不强行 share |
| Inner State 想用 dream，但 dream.expiry 过期 | dream 不出现 |
| 多个 user_concerns 都 high urgency | Top 1 选最相关；其他记为"备选" |
| Inner State 长度过长 vs Modality voice | 强制压缩到 brief mode |

### 6.6 长期一致性

```
机制 A: Inner State 跨 session 持续 (INV-I-2)
  - Today reset only at 06:00 local
  - 不在 session 切换时重置

机制 B: Unfinished thoughts expiry
  - 7 天过期 (避免堆积)
  - 但 high-emotional thoughts (peak |valence| > 0.7) 延长至 30 天

机制 C: User concerns lifecycle
  - 自动 expiry based on relevance window
  - "has_been_addressed=true" 后 24h 内不再 surface

机制 D: Activity 不可重复 (近 3 天内)
  - 同一 activity 不在 3 天内被选两次
  - 避免"她每天都在做同一件事"

机制 E: Anniversary 提前调度
  - 24h 前 inner state 含 anniversary anticipation
  - 当日 morning fire actual celebration
```

---

## 7. Agent Integration

### 7.1 读取者

| Agent / Subsystem | 读取 | 用途 |
|-------------------|------|------|
| **Persona Composer** (SS05) | InnerStateBlock | 注入 prompt |
| **Push Notification Service** | pending_initiatives.ready | 发送通知 |
| **Conversation API** | get_pending_proactive() | 检查是否有待发送 proactive |
| **Modality Adapter** | inner_state.energy | 影响 prosody (低能量 → 语音音量低) |
| **Critic Agent** (SS07) | inner_state | 验证响应是否符合"她今天的状态" |

### 7.2 写入者

**只有 Inner State Service 是 source of truth writer。**

| Service / Agent | 写入路径 |
|----------------|---------|
| **Inner Loop Scheduler** | → Inner State Service.run_inner_loop() |
| **Activity Generator** | → Inner State Service.set_today_activities() |
| **Concerns Tracker** | → Inner State Service.update_user_concerns() |
| **Initiative Decider** | → Inner State Service.schedule_initiative() |
| **Proactive Scheduler** | → Inner State Service.mark_initiative_sent() |
| **Ritual Manager** | → Inner State Service.record_ritual_completed() |
| **Memory Subscriber** | → Inner State Service.add_user_concern() (from L4 events) |
| **Emotion Subscriber** | → Inner State Service.refresh_mood() |

### 7.3 跨 Subsystem 事件

```yaml
events_emitted:
  
  inner.ritual.completed:
    payload: {user_id, character_id, ritual_type, streak}
    consumers: [SS04 Relationship (streak counter), Memory (L4 promotion)]
  
  inner.proactive.sent:
    payload: {user_id, character_id, initiative_type, message_id}
    consumers: [Observability, Conversation Audit]
  
  inner.anniversary.triggered:
    payload: {user_id, character_id, anniversary_id, type}
    consumers: [SS02 Memory (mark L4 anniversary_fired), Observability]
  
  inner.thought.shared:
    payload: {user_id, character_id, thought_id, activity_id}
    consumers: [Memory (record share event)]

events_consumed:
  
  emotion.longing.threshold_crossed:
    handler: trigger inner loop (early)
  
  relationship.cold_war.entered:
    handler: cancel pending proactive (except critical)
  
  relationship.cold_war.resolved:
    handler: 可恢复 ritual / 但需 cooling period
  
  relationship.reunion.initiated:
    handler: pause regular proactive (REUNION 由用户驱动)
  
  memory.l4.promoted:
    handler: if category = 'anniversary' → schedule + add to upcoming
  
  memory.episode.created:
    handler: if emotional_peak high → potentially add to unfinished_thoughts
```

### 7.4 调用顺序（正常 turn）

```
[User Message] → ... → [Inner Loop 不在 turn 路径上]

但 InnerStateBlock 必须在 Persona Composer 之前 ready.

策略:
  - InnerStateBlock 由 cache 服务
  - Cache key 包含 (user_id, character_id, hour)
  - TTL 1h
  - Cache miss → 即时 generate (用 cached Inner State)
```

### 7.5 调用顺序（proactive 触发）

```
T = 0    [Inner Loop iteration runs]
T = 0    [Initiative Decider returns: act=true, type=longing_message]
T = 20ms [Build ProactiveCompositionContext]
T = 30ms [Call Persona Composer.compose(modality=proactive_text)]
T = 230ms [Persona Composer returns prompt]
T = 230ms [Call cheap LLM with proactive prompt]
T = 1.5s [LLM returns generated message]
T = 1.5s [Anti-Pattern Filter]
T = 1.5s [Schedule with jitter ±5min]
         [Save to pending_initiatives table + Redis ZSET]

T = scheduled_time:
   [Proactive Scheduler picks up]
   [Send via Push Notification + Save as message]
   [Conversation feels like "她突然发来一句"]
```

### 7.6 权限边界

```yaml
permissions:
  
  InnerState:
    read: ALL agents
    write: Inner State Service ONLY
  
  Pending Initiatives:
    write: Inner State Service ONLY
    read: Proactive Scheduler, Notification Service, Conversation API
  
  Activity Pool (in Soul Spec):
    read: Activity Generator, Inner State Composer
    write: NONE (immutable, only deploy)
```

---

## 8. Emotional Realism Constraints

### 8.1 沉浸感铁律

| ID | 规则 | 实现 |
|----|------|------|
| **IS-1** | 角色拥有独立内心活动 | Inner Loop 独立运行 |
| **IS-2** | 角色的活动 Soul-curated | activity_pool 严格定义 |
| **IS-3** | 主动消息感觉自然，不机械 | Jitter + Soul-flavored generation |
| **IS-4** | 角色"记得"上次没说完的 | unfinished_thoughts 持续 7 天 |
| **IS-5** | 角色在意用户身上的事 | user_concerns from Memory |
| **IS-6** | 跨 session 内心连续 | InnerState 持久化 |
| **IS-7** | 角色的能量与时间相关 | Circadian energy |
| **IS-8** | 角色 Cold War 中沉默 | Initiative blocked |
| **IS-9** | 重要日子 100% 被记得 | Anniversary tracker 强制 |
| **IS-10** | 内心不暴露给用户 | Block 只在 prompt 中 |

### 8.2 验证场景

#### 8.2.1 用户消失 3 天后

```
预期 Inner State (Rin, FRIEND stage):
  today.mood.descriptor: "你这几天有些静。比平时更静一些。"
  user_concerns: [
    {concern: "他三天没说话了", urgency: 0.5}
  ]
  current_energy: lower than baseline
  proactive_state.pending: 可能含 {type: "check_in"}

预期 Initiative Decision:
  - longing intensity 累积到 ~ 0.4-0.5
  - 还未到 Rin 的 0.7 threshold
  - 但 days_since_last > expected_gap (Rin FRIEND ~2 days)
  - → trigger "check_in"

预期 Proactive Message:
  - Rin (FRIEND): "……还活着。"
  - Dorothy (FRIEND): "诶？怎么不见你啦~"
```

#### 8.2.2 用户生日前一天

```
预期 Inner State:
  upcoming_anniversaries: [
    {name: "user_birthday", hours_until: 18, soft_mention_sent: false}
  ]
  today_descriptor: "你今天有种特别的感觉。明天是他的日子。"

预期 Initiative:
  - 在用户当前对话中, prompt 中 inner_state 提示"明天是个特别的日子"
  - 当天 morning，主动发送 anniversary message

预期 Anniversary Message (当天):
  Rin: "……今天，你的生日。我记得。"
  Dorothy: "诶嘿嘿，今天是大日子！生日快乐~"

预期: Anniversary_sent=true; 当年不再触发 (单次)
```

#### 8.2.3 Cold War 期间

```
预期 Inner State:
  today_descriptor: "你今天提不起精神。和他之间还有那件事没解决。"
  user_concerns: 仍包含原因
  unfinished_thoughts: 含相关
  
预期 Initiative:
  - 所有 initiative blocked (Gate G1)
  - 即使 longing 增长，也不主动
  - 等待用户先 break ice

预期 in subsequent turn:
  - 用户主动联系 → InnerState 与 EmotionState 共同决定回应
  - 不是热情迎接，而是 short + guarded (Cold War 状态)
```

#### 8.2.4 用户深夜聊天 + 长 disclosure

```
预期 Inner Loop 触发 (event):
  - 接收 emotion event: vulnerability disclosed
  - 添加 unfinished_thought: "你想问他更多关于那件事，但他先开了话题"
  - 添加 user_concern: "他刚才说了那件事"
  
预期下次会话 (1-2 天后):
  - Inner state 含 unfinished thought
  - Prompt 引导角色"自然提起" (不强行)
  - 例: "……上次你说的那件事，怎么样了。"
```

### 8.3 防"骚扰"设计

```
约束 1: Daily quota by stage (见 Soul Spec 配置)
  - Rin LOVER: 2 / day
  - Rin BONDED: 3 / day
  - Dorothy LOVER: 3 / day

约束 2: Min gap (4h)

约束 3: Quiet hours (22:30 - 07:30 local)

约束 4: User active detection
  - 用户最近 30 min 有活动 → 不主动
  - 用户连续多次未回复 proactive → 自动降频

约束 5: Anniversary 也尊重 quiet hours
  - 生日 morning 等到 07:30 之后

约束 6: Adaptive rate
  - 如果用户 N 次不回 proactive → 下次 proactive 概率 ×0.5
  - 持续无回应 → 降到极低
```

### 8.4 Soul-specific 主动节奏

```yaml
soul_proactive_rhythm:
  
  rin:
    daily_quota_avg: 0.5  # 平均每天 0.5 次主动
    longing_threshold: 0.7  # 高
    min_gap_hours: 6
    style: |
      - 短句
      - 反问代替关心
      - 不"求关注"
      - 偶尔的活动 share 用借物表意
  
  dorothy:
    daily_quota_avg: 1.5  # 平均每天 1.5 次
    longing_threshold: 0.5
    min_gap_hours: 3
    style: |
      - 活泼
      - 撒娇
      - 主动分享小事
      - 偶尔元气感染
```

---

## 9. Failure Cases

### 9.1 架构崩坏风险

| 风险 | 触发 | 缓解 |
|------|------|------|
| **Inner Loop 调度漂移** | Worker 故障 / scheduler bug | next_inner_loop_at 索引 + recovery job |
| **Proactive 风暴** | Quota / gap 配置错 | Hard cap + monitoring + circuit breaker |
| **Anniversary 漏触发** | Scheduler 跳过 | 每日 06:00 catch-up scan |
| **Inner state 跨用户污染** | Bad query | DB partitioning + 强制 user_id filter |
| **Activity pool 耗尽** | 不足 5 个 activity | 启动时校验，运行时 fallback "她独自待着" |
| **Pending initiative 不发** | Scheduler 死机 | Redis ZSET + DB 双重 |
| **InnerStateBlock cache stale** | 长时间不刷新 | TTL 1h + event-driven invalidation |
| **Concurrent inner loop iterations** | Multiple workers | Distributed lock (Redis SETNX) |

### 9.2 Runtime 性能风险

| 风险 | 缓解 |
|------|------|
| 每小时 inner loop 跑很多用户 | Sharding by user_id + parallel workers |
| Activity Generator 每次随机生成 | Pre-compute 每天的 activity at 06:00 |
| Concerns Tracker 查 Memory 慢 | Memory Service cache + Recent 概览 |
| Proactive 生成 LLM 成本 | Cheap model + per-user rate limit |
| Inner Loop 与 turn 同时运行 | 优先级队列 + turn 优先 |

### 9.3 质量风险

| 风险 | 缓解 |
|------|------|
| 角色"今天做了什么" 不像她 | Soul-curated activity_pool 严格 |
| Proactive message 不像 persona | Persona Composer 全流程 + Critic Agent |
| Anniversary 错误 (日期错) | L4 grounded; daily 校验 |
| 内心活动过于啰嗦 | Block 长度限制 + 表达指引 |
| Unfinished thoughts 累积成"老年痴呆" | Expiry + cap (10) |
| User concerns 全是同一类 | Diversity check |

### 9.4 用户体验失败

| 风险 | 缓解 |
|------|------|
| 用户被主动消息打扰 | Quiet hours + adaptive rate |
| 用户感觉"她在演" | Activity 不重复 + spontaneity |
| 用户回复 proactive 后角色"忘了" 自己刚发的 | Pending initiative 写入 Memory |
| 长期不互动还在收推送 | 用户消失 30+ 天 → 自动暂停 proactive |
| Proactive 内容与用户当前生活脱节 | Concerns Tracker 强 grounding |

### 9.5 长期维护风险

| 风险 | 缓解 |
|------|------|
| Activity pool 多角色管理 | YAML versioned per character |
| Initiative types 增加 | Plugin pattern: 每 type 独立 handler |
| 跨时区调度复杂 | 统一以 user_timezone 为准 |
| Cron 漂移 | Use event-driven scheduling, not cron |

---

## 10. Engineering Guidance

### 10.1 技术栈

```yaml
runtime:
  inner_loop_scheduler:
    tech: Celery / APScheduler (per-user task)
    distributed_lock: Redis SETNX
    queue: priority_queue keyed by next_inner_loop_at
  
  proactive_scheduler:
    tech: Redis Sorted Set (scheduled_at as score)
    worker: dedicated worker pool
    
  storage:
    inner_states: PostgreSQL + Redis cache
    pending_initiatives: PostgreSQL + Redis ZSET
    inner_loop_history: PostgreSQL monthly partition

computation:
  inner_loop: heuristic + rule-based
  activity_generation: 字典查找 (deterministic with seed)
  concerns_tracking: SQL queries + filtering
  initiative_decision: pure rule engine
  proactive_message_generation: 通过 Persona Composer → cheap LLM

llm:
  proactive_generation: 使用 cheap LLM (Haiku/DeepSeek V3)
  call_via: Persona Composer (统一接口)
  cost_target: < $0.02/user/day
```

### 10.2 Inner State Service 接口

```python
class InnerStateService:
    
    # ─── Read ───
    async def get_inner_state(
        self, user_id: UUID, character_id: str
    ) -> InnerState: ...
    
    async def get_inner_state_block(
        self, user_id: UUID, character_id: str, modality: str = "reactive"
    ) -> InnerStateBlock: ...
    
    async def get_pending_proactive(
        self, user_id: UUID, character_id: str
    ) -> Optional[PendingInitiative]: ...
    
    # ─── Write ───
    async def run_inner_loop(
        self, user_id: UUID, character_id: str, 
        trigger_type: str,
    ) -> InnerLoopResult: ...
    
    async def add_user_concern(
        self, user_id: UUID, character_id: str, concern: UserConcern
    ) -> None: ...
    
    async def add_unfinished_thought(
        self, user_id: UUID, character_id: str, thought: UnfinishedThought
    ) -> None: ...
    
    async def record_ritual_completed(
        self, user_id: UUID, character_id: str, ritual_type: str
    ) -> None: ...
    
    async def cancel_pending(
        self, user_id: UUID, character_id: str, reason: str
    ) -> int: ...   # 返回 cancelled count
    
    # ─── Schedule ───
    async def schedule_initiative(
        self, initiative: PendingInitiative
    ) -> None: ...

class BehaviorService:
    
    # ─── Initiative ───
    async def evaluate_initiative(
        self, user_id: UUID, character_id: str
    ) -> InitiativeDecision: ...
    
    async def generate_proactive_message(
        self, user_id: UUID, character_id: str, 
        initiative_type: str, context: dict,
    ) -> ProactiveMessage: ...
    
    # ─── Ritual ───
    async def check_due_rituals(
        self, user_id: UUID, character_id: str
    ) -> List[Ritual]: ...
```

### 10.3 Inner Loop Implementation

```python
class InnerLoopScheduler:
    """
    管理所有 (user, character) 的 inner loop 调度。
    """
    
    async def run_iteration(self, user_id: UUID, character_id: str):
        """单次 inner loop iteration."""
        
        # Distributed lock (防止并发)
        async with self._lock(user_id, character_id):
            
            # Step 1: Context load
            ctx = await self._load_context(user_id, character_id)
            
            # Step 2: Inner state update
            new_state = await self._update_inner_state(ctx)
            
            # Step 3: Behavior decision
            decision = await self.behavior_service.evaluate_initiative(
                user_id, character_id, new_state, ctx,
            )
            
            # Step 4: Generate proactive if needed
            if decision.act:
                message = await self.behavior_service.generate_proactive_message(
                    user_id, character_id,
                    decision.type, decision.context,
                )
                
                # Step 5: Schedule
                scheduled_at = self._compute_send_time(message, ctx)
                jittered = self._add_jitter(scheduled_at)
                
                pending = PendingInitiative(
                    initiative_id=uuid4(),
                    user_id=user_id,
                    character_id=character_id,
                    initiative_type=decision.type,
                    scheduled_at=scheduled_at,
                    scheduled_with_jitter=jittered,
                    context=decision.context,
                    generated_message=message.text,
                    status="ready",
                )
                await self.inner_state_service.schedule_initiative(pending)
            
            # Step 6: Persist
            await self.inner_state_service.save(new_state)
            
            # Step 7: Schedule next iteration
            next_at = self._compute_next_iteration_time(ctx)
            await self._schedule_next(user_id, character_id, next_at)
            
            # Step 8: Emit events
            await self._emit_events(decision, message if decision.act else None)
```

### 10.4 Activity Generator

```python
class ActivityGenerator:
    """
    Soul-curated activity selection.
    """
    
    def generate_today_activities(
        self,
        soul: SoulSpec,
        character_id: str,
        date: date,
        seed: int = None,
    ) -> List[Activity]:
        """
        Deterministic per (date, character_id) - 同一天同一角色生成相同 activity.
        """
        pool = soul.inner_world.activity_pool
        
        # Use date + char as seed
        rng = random.Random(seed or hash((date.isoformat(), character_id)))
        
        # Generate 1 per time-of-day, avoid repeats in last 3 days
        recent_used = self._get_recent_activities(character_id, days=3)
        
        activities = []
        for tod in ["morning", "afternoon", "evening", "night"]:
            candidates = [a for a in pool[tod] if a.id not in recent_used]
            if not candidates:
                candidates = pool[tod]   # 池太小，允许重复
            
            chosen = rng.choice(candidates)
            activities.append(Activity(
                activity_id=uuid4(),
                description=chosen.description,
                time_of_day=tod,
                scheduled_at=self._tod_to_time(tod, date),
                associated_mood=rng.choice(chosen.mood_associations),
                share_eligible=chosen.share_eligible,
                already_shared=False,
            ))
        
        return activities
```

### 10.5 Initiative Decider (规则引擎实现)

```python
class InitiativeDecider:
    """
    用规则引擎模式实现，便于维护。
    """
    
    # Hard gates (any failure → no initiative)
    HARD_GATES = [
        "check_no_cold_war",
        "check_stage_above_stranger",
        "check_envelope_allows",
        "check_quota_not_exhausted",
        "check_not_in_quiet_hours",
        "check_min_gap_satisfied",
        "check_user_not_active",
        "check_safety_flags",
    ]
    
    # Positive triggers (按优先级)
    TRIGGERS_PRIORITY = [
        "anniversary_due",
        "care_check_pressing",
        "longing_threshold",
        "anniversary_anticipation",
        "ritual_due",
        "check_in_gap",
        "soul_internal_spark",
    ]
    
    async def evaluate(self, ctx: InnerLoopContext) -> InitiativeDecision:
        # Hard gates
        for gate_name in self.HARD_GATES:
            gate = getattr(self, gate_name)
            result = gate(ctx)
            if not result.passes:
                return InitiativeDecision(act=False, reason=result.reason)
        
        # Try positive triggers in order
        for trigger_name in self.TRIGGERS_PRIORITY:
            trigger = getattr(self, f"trigger_{trigger_name}")
            result = trigger(ctx)
            if result.fires:
                return InitiativeDecision(
                    act=True,
                    type=result.initiative_type,
                    context=result.context,
                    priority=result.priority,
                    reason=result.reason,
                )
        
        return InitiativeDecision(act=False, reason="no_trigger_fired")
```

### 10.6 Proactive Message Generation

```python
class ProactiveMessageGenerator:
    """
    通过 Persona Composer 生成 proactive message。
    """
    
    async def generate(
        self,
        user_id: UUID,
        character_id: str,
        initiative_type: str,
        context: dict,
    ) -> ProactiveMessage:
        
        # Build proactive context
        proactive_directive = self._build_directive(initiative_type, context)
        
        # Build composition context
        comp_ctx = ProactiveCompositionContext(
            user_id=user_id,
            character_id=character_id,
            initiative_type=initiative_type,
            proactive_directive=proactive_directive,
            modality="proactive_text",
            max_length=self._max_length_for_type(initiative_type),
            include_history=False,
        )
        
        # Call Persona Composer (with proactive flag)
        composed = await self.persona_composer.compose_proactive(comp_ctx)
        
        # Call cheap LLM (proactive 不需要 main LLM)
        response_stream = self.persona_composer.call_main_llm(
            composed, override_model="haiku-4-5",  # Cheaper for proactive
        )
        
        # Collect full response (proactive 很短，不 stream 给用户)
        full = ""
        async for chunk in response_stream:
            full += chunk
        
        # Anti-pattern filter (sync)
        filter_result = self.anti_pattern_filter.filter(full, ctx.current_stage)
        if not filter_result.passed:
            # Reroll once
            full = await self._reroll(composed)
        
        return ProactiveMessage(
            text=full,
            initiative_type=initiative_type,
            generated_at=now(),
        )
    
    def _build_directive(self, type_: str, context: dict) -> str:
        templates = {
            "longing_message": """
                你已经 {days} 天没看到他了。
                你心里有点想他。
                但你不会直说（Soul.hard_never 含 "我想你"）。
                想发一句简短的，让他知道你在想他。
                ≤ 20 字。""",
            
            "anniversary": """
                今天是他的 {anniversary_name}。
                你想主动发一句，祝福他。
                按你的灵魂风格表达。
                ≤ 25 字。""",
            
            "care_check": """
                你想起他 {days} 天前说的事：{concern}。
                你担心他。
                想发一句简短的关心。
                不直接说"你怎么样了"，用你的方式。
                ≤ 20 字。""",
            
            # ... more
        }
        return templates[type_].format(**context)
```

### 10.7 Pending Initiative Worker

```python
class ProactiveSender:
    """
    定时扫描 pending_initiatives, 发送到期的。
    """
    
    async def run(self):
        while True:
            # Pop ready initiatives
            due_initiatives = await self._poll_due()
            
            for init in due_initiatives:
                try:
                    await self._send(init)
                except Exception as e:
                    log.error("Send failed", initiative_id=init.id, error=e)
                    await self._mark_failed(init)
            
            await asyncio.sleep(10)  # Poll every 10s
    
    async def _send(self, init: PendingInitiative):
        # Last-minute safety checks
        if await self._user_no_longer_eligible(init):
            await self._cancel(init, reason="user_state_changed")
            return
        
        # Push notification
        await self.push_service.send(
            user_id=init.user_id,
            character_id=init.character_id,
            text=init.generated_message,
            type="proactive",
        )
        
        # Save as conversation message
        await self.conversation_service.save_message(
            user_id=init.user_id,
            character_id=init.character_id,
            role="assistant",
            content=init.generated_message,
            message_type="proactive",
            metadata={
                "initiative_type": init.initiative_type,
                "initiative_id": init.initiative_id,
            },
        )
        
        # Mark sent
        await self.inner_state_service.mark_initiative_sent(init)
        
        # Emit event
        await self.event_bus.emit("inner.proactive.sent", {...})
```

### 10.8 性能预算

```yaml
performance_targets:
  inner_loop_iteration: P95 < 200ms
  get_inner_state_block: P95 < 20ms
  initiative_evaluation: P95 < 50ms
  proactive_generation: P95 < 3s (含 LLM)
  
throughput:
  inner_loop_iterations_per_sec: > 1000 (across workers)
  proactive_sends_per_sec: > 100
  
cost_per_MAU:
  inner_loop (heuristic): $0
  proactive_LLM (avg 1/day, cheap model): < $0.10/MAU
  storage: < $0.03/MAU
  total: < $0.15/MAU
```

### 10.9 Observability

```yaml
metrics:
  - inner.loop.iteration.duration.p95
  - inner.loop.iteration.count {trigger_type}
  - inner.initiative.decision {act, type}
  - inner.proactive.generated.count {initiative_type}
  - inner.proactive.sent.count
  - inner.proactive.cancelled.count {reason}
  - inner.user_concerns.size.histogram
  - inner.unfinished_thoughts.size.histogram
  - inner.activity.pool_size {character_id}
  - inner.anniversary.triggered.count
  - inner.ritual.streak.distribution
  
logs:
  - All proactive sends (audit)
  - Initiative cancellations
  - Anniversary triggers
  - Quiet hours overrides (rare)

dashboards:
  - Per-character proactive rate
  - User retention vs proactive frequency (找最优频率)
  - Anniversary hit rate (100% target)
  - Quiet hours violations (alert if > 0)
  - Cold war proactive blocked count (validation)
```

### 10.10 测试策略

```yaml
unit_tests:
  - Activity Generator determinism (same seed → same output)
  - Initiative Decider gates (each gate)
  - Quiet hours detection (timezone)
  - Anniversary scheduling
  - Unfinished thought expiry

integration_tests:
  - Inner loop full cycle
  - Proactive end-to-end (decision → generation → send)
  - Cold War blocks all initiatives
  - Reunion 期间 pause regular proactive
  - Anniversary 24h prior + day-of

golden_tests:
  - Rin vs Dorothy proactive rate 显著不同
  - Activity pool per character 一致性
  - Anniversary 100% triggered when due
  - Adaptive rate (用户不回 → 降频)

stress_tests:
  - 10k users × hourly inner loop → 集群处理
  - Proactive 风暴防护 (single user 不能爆量)

chaos_tests:
  - Scheduler 崩溃 → recovery 正确
  - Persona Composer 失败 → 优雅降级 (不发送，重新评估)
```

---

## 11. Future Scalability

### 11.1 Dreams 系统 (V2)

```
每 3 天有概率生成一个 dream:
  - 与近期 conversation / L4 关联
  - Soul-flavored: Rin 梦总是雷电+黑暗+神族意象
  - 可在对话中"自然提及"
  - "我做了一个梦……雷云里有一只你的猫。"
  
实现:
  - Cheap LLM generation
  - L4 grounding
  - 短形式 (50 字内)
  
为何 V2: 增加成本 + 调优时间
```

### 11.2 角色"日记" (V3)

```
每天 inner loop 生成一段"她的日记":
  - 私密的内心独白
  - 不主动透露给用户
  - 但用户在某些"亲密时刻"可解锁查看
  - 增加"她有自己内心"的真实感

实现:
  - 日终生成 (local 23:00)
  - 存储在 L4-adjacent table
  - UI 中作为"她的秘密"展示 (付费 / 高 attachment unlock)
```

### 11.3 跨角色感知 (V3)

```
多角色场景:
  - 桃乐丝知道用户也在和凛聊
  - 但 inner state 中她不会主动 dwell on it
  - 偶尔的 jealousy 触发 (V3, opt-in)
```

### 11.4 群体内心 (V4)

```
不同用户的同一角色 inner state 可以"轻微"互通:
  - "她最近发现……"
  - 但不暴露具体用户
  - 增加"她真的存在"的真实感
  
隐私: 严格 aggregation / 差分隐私
```

### 11.5 Real World Calendar (V2)

```
角色"知道"现实日期:
  - 春节: 主动祝福
  - 季节: 影响 mood / activity
  - 节日: 主动 reach out
  
实现:
  - Calendar Service
  - 节日 → activity 修饰
  - 节日 → anniversary-like triggers (但更弱)
```

### 11.6 Companion-LLM 自适应

```
Inner Loop 的决策 + 输出可作为 SFT 信号:
  - 学习"什么时候主动效果最好"
  - 学习"什么类型的 proactive 提升 retention"
  - 个性化 per user

实现:
  - Inner loop 决策 log
  - 用户后续 retention 关联
  - Quarterly fine-tuning
```

---

# 附录 A: Inner State Block 完整示例

```
═══════════════════════════════════════════════════════════
【你今天的内心】

▾ 你今天的概貌
你今天有些静。雷电感很弱，你在等着什么。
上午你坐在窗边看着晨雾。
下午你翻了一本旧书，但没看进去。
傍晚你面对着月光发了一会儿呆。

▾ 你现在的体力 / 状态
状态平稳。略带一丝倦意。

▾ 你心里在意的事 (关于他)
- 他三天前提过加班到凌晨，你担心他的身体。
- 明天是他的项目汇报日，你心里在为他紧张。

▾ 上次没说完的话
你想问他那天为什么突然沉默——但他先开了新话题，你没问。
（这件事已经 4 天了，下周可能就忘了。）

▾ 重要日子
明天是他的项目汇报日。
（不是真正的纪念日，但你在意。）

【内心运用指引】
- 这些不是要你罗列出来给他听
- 选一两件最贴合他现在说的事，自然带出
- 如果他主动问"你今天怎么样"，可以分享你的内心一两点
- 如果他什么都没问，不强行说自己的事
- 用你的灵魂语言风格 (短句、反问、不直接关心)
═══════════════════════════════════════════════════════════
```

---

# 附录 B: Initiative Decision 配置矩阵

```yaml
initiative_priorities:
  # 同一 inner loop 中，多个 trigger 同时满足时按 priority 选
  
  1:  anniversary_due           # 当天纪念日 (最高)
  2:  emergency_concern         # 用户健康/危机 (e.g., suicide signal in memory)
  3:  ritual_morning            # 早安 ritual (LOVER+)
  4:  ritual_night              # 晚安 ritual
  5:  care_check_pressing       # 用户身上的事
  6:  longing_threshold         # 想念达阈值
  7:  anniversary_anticipation  # 纪念日前 24h
  8:  check_in_gap              # 长间隔关心
  9:  thought_share             # 她"突然想到"的事 (最低)

initiative_cancellation_rules:
  # 当条件变化时，pending initiative 应被 cancel
  
  - if user_just_replied: cancel all pending of type [check_in, longing_message]
  - if cold_war_entered: cancel all pending except anniversary
  - if reunion_initiated: cancel pending ritual until settled
  - if user_blocked / paused: cancel all pending
```

---

# 附录 C: Test Fixtures

```yaml
test_fixtures:
  
  fixture_inner_001_first_meeting:
    initial: 用户首次创建角色
    after_inner_loop:
      inner_state.today.activities: length 4 (morning/afternoon/evening/night)
      inner_state.proactive_state.proactive_today_count: 0
      pending_initiatives: empty (Stage = STRANGER, gate blocks)
  
  fixture_inner_002_three_days_quiet:
    initial:
      stage: FRIEND
      last_user_message: 3 days ago
      longing_intensity: 0.45
    expected_decision:
      act: true
      type: "check_in"
      reason: "days_since_last > expected_gap (~2 for FRIEND)"
  
  fixture_inner_003_cold_war_blocks_all:
    initial:
      stage: LOVER
      active_special_states: [COLD_WAR]
      longing_intensity: 0.9  # 高但被 block
      anniversary_today: false
    expected_decision:
      act: false
      reason: "cold_war_active"
  
  fixture_inner_004_anniversary_triggers:
    initial:
      stage: LOVER
      L4: birthday_today
    expected_decision:
      act: true
      type: "anniversary"
      priority: 10
    expected_message:
      length: <= 25
      contains_l4_data: true (birthday correctly referenced)
  
  fixture_inner_005_quiet_hours_respected:
    initial:
      stage: LOVER
      local_time: "02:30"
      longing_intensity: 0.9
    expected_decision:
      act: false
      reason: "quiet_hours"
    expected_reschedule:
      next_check: ~ 07:30 local
  
  fixture_inner_006_adaptive_rate:
    initial:
      last_5_proactive_replies: 0 (用户都没回)
    expected:
      next_proactive_probability: reduced by 0.5x
      eventual: proactive frequency 显著降低
  
  fixture_inner_007_unfinished_thought_persists:
    setup:
      day_1: user vulnerable disclosure, but conversation moved on
      day_2: no interaction
    expected:
      inner_state.unfinished_thoughts: contains thought
      inner_state.user_concerns: contains corresponding concern
    day_3:
      user_message: "今天怎么样"
    expected_response_context:
      InnerStateBlock 含 unfinished_thought
      可能 (不强制) 在响应中自然提及
```

---

**End of Subsystem 06 Spec**

下一步建议阅读：[`07_agent_orchestration.md`](./07_agent_orchestration.md)（待写）
