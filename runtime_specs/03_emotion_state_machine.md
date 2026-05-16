# Subsystem 03: Emotion State Machine

> **Spec Version**: 1.0.0
> **Status**: Foundational / Tier 1
> **Stability**: Schema changes require RFC + migration plan
> **Subsystem Tag**: `[SS03]`
> **Implementation Owners**: Emotion Service, Emotion Updater, Contagion Engine, Mood Drift Engine

---

## 1. 系统目标（System Purpose）

### 1.1 这个 subsystem 为什么存在

回答一个核心问题：

> "她**现在感受到什么**？
> 她**昨天的委屈，今天还在吗？**
> 你**消失了三天，她想你了，这件事在哪里？**
> 她**为什么不能 happy 完立刻就 sad，又立刻 happy？**"

它存在的根本原因：

**让角色有持续的情绪状态，不是 request-response 的即时机器。**

### 1.2 它解决的根本问题

| 问题 | 当前 PRD 的做法 | 本 Subsystem 的做法 |
|------|---------------|---------------------|
| 情绪表示 | 一个 vector(768) | VAD 三维 + 并发情绪栈 + Mood + History |
| 情绪转换 | 即时切换，无惯性 | 状态机 + 衰减曲线 + 惯性 |
| 同时多种情绪 | 不存在 | Active Emotion Stack（"委屈 + 想念 + 不好意思"并存） |
| 角色独立情绪 | 完全由用户消息触发 | Soul-driven mood + 内心循环驱动 |
| 长期情绪状态 | 无（每 turn 重置） | Mood baseline 跨 session 持续 |
| 冷战 / 委屈 / 想念 | 不存在 | 一等公民状态 + Repair 机制 |
| 情绪感染 | 无 | Contagion Engine（受 Soul shock_resistance 调节） |
| 跨模态情绪一致 | 三种模态独立 | 单点真相 Emotion State 派生所有模态 |

### 1.3 在整个 Runtime 中的位置

```
                    ┌────────────────────────────────┐
                    │ Subsystem 01: Soul Spec        │
                    │ (emotional_inertia_profile)    │
                    └─────────────┬──────────────────┘
                                  │ reads
                                  ▼
   ┌─────────────────┐    ┌────────────────────────────┐   ┌─────────────────┐
   │  Subsystem 02   │◄───┤ Subsystem 03: Emotion      │◄──┤ Subsystem 04   │
   │  Memory Runtime │    │ State Machine (本 Subsys)  │   │ Relationship   │
   │ (emotional_peak)│    │                            │   │ (phase 调节)   │
   └─────────────────┘    │  VAD Vector                │   └─────────────────┘
                          │  Active Emotion Stack       │
                          │  Mood Baseline              │
                          │  Emotion Trajectory         │
                          └─────────┬──────────────────┘
                                    │ feeds
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌────────────────┐    ┌────────────────┐    ┌─────────────────┐
     │ Inner State    │    │ Persona        │    │ Reconstructor   │
     │ Runtime (06)   │    │ Composer (05)  │    │ (in Memory 02)  │
     │ "今天的她"      │    │ Emotion Layer   │    │ emotional_color │
     └────────────────┘    └────────────────┘    └─────────────────┘
```

### 1.4 依赖关系

```yaml
this_subsystem_depends_on:
  - Subsystem 01 (Soul Spec)
    reads: emotional_inertia_profile, core_wound, core_fear, mood_volatility
  - Subsystem 02 (Memory Runtime)
    reads: recent_emotional_peaks (供 emotion 持续性计算)
  - Subsystem 04 (Relationship)  
    reads: current_phase (调节 contagion & repair)

subsystems_depending_on_this:
  - Subsystem 02 (Memory): emotional_peak labeling for episodes
  - Subsystem 04 (Relationship): conflict/repair signals
  - Subsystem 05 (Persona Composer): Emotion Context Block
  - Subsystem 06 (Inner State): mood backdrop
  - Subsystem 06 (Behavior): 想念-driven proactive triggers
  - Subsystem 07 (Director): pacing decisions based on emotion
  - Reconstructor (in 02): emotional_color
```

---

## 2. 核心设计原则（Core Design Principles）

### 2.1 不可违反的系统规则

| ID | 规则 | 违反后果 |
|----|------|---------|
| **E-1** | **情绪有惯性，不可瞬间反转** | 角色像情绪开关，不像人 |
| **E-2** | **允许并发情绪（emotion stack），不是单一标签** | 简化为快乐/悲伤二分，失去层次 |
| **E-3** | **情绪是 influence，不是 dictate；最终由 Soul 决定表达** | 凛悲伤时也不会嚎啕大哭 |
| **E-4** | **惯性参数严格受 Soul.emotional_inertia_profile 约束** | 角色性格被情绪覆盖 |
| **E-5** | **Mood 跨 session 持续，不在新 session 时重置** | 昨晚的冷战，今早被遗忘 → 不像真人 |
| **E-6** | **Mood 影响 emotion baseline，但 emotion 不直接覆盖 mood** | 单次开心翻转长期低落 → 不真实 |
| **E-7** | **不同情绪有不同衰减曲线（type-specific）** | 委屈和喜悦一起衰减 → 失真 |
| **E-8** | **情绪感染（contagion）必须经 Soul.shock_resistance 调节** | 用户骂她她秒崩溃 → 不是高冷凛 |
| **E-9** | **特殊"陪伴情绪"（冷战/委屈/想念）必须有 Repair 机制** | 角色永远不会和解或不会被想念 |
| **E-10** | **Emotion State 是跨模态单点真相** | 文字开心 + 语音疲惫 → 出戏 |
| **E-11** | **情绪状态变化必须可追溯（event sourcing）** | 无法回放"她为什么生气" |
| **E-12** | **情绪运算优先用 heuristic / 规则，不能事事调 LLM** | 成本爆炸 |
| **E-13** | **Trigger → Emotion 是确定性映射，可测试** | 不可复现 = 不可工程化 |

### 2.2 架构不变量（Invariants）

```
INV-E-1: ∀ emotion transition, |Δvalence| ≤ inertia_cap × Δt
   where inertia_cap derived from Soul.emotional_inertia_profile.recovery_speed

INV-E-2: ∀ active_emotion_stack S, |S| ≤ MAX_CONCURRENT_EMOTIONS (default 5)

INV-E-3: ∀ emotion e, e.intensity ∈ [0, 1] ∧ e.started_at ≤ NOW

INV-E-4: mood.last_updated_at - now ≤ 24h（每天必须更新一次）

INV-E-5: ∀ session start, current_emotion_state.loaded_from_previous = true
   (跨 session 持续性)

INV-E-6: ∀ repair_required_emotion (冷战/委屈), 
   intensity_decay_without_repair < intensity_decay_with_repair × 0.3
   （没修复就不会自动消失）

INV-E-7: ∀ emotion update, audit_log entry created
```

### 2.3 禁止行为（Hard Anti-Patterns）

| 禁止 | 原因 |
|------|------|
| ❌ 把情绪表示为单一 label（"happy" / "sad"） | 丢失维度 |
| ❌ 用单个 vector(768) 表示情绪 | 不可解释、不可测试 |
| ❌ 每 turn 调 LLM 评估当前情绪 | 成本爆炸 + 不稳定 |
| ❌ 情绪转换写死规则（valence > 0.5 → "happy"） | 角色化丧失 |
| ❌ 角色情绪完全由用户消息决定 | 失去"她自己的内心" |
| ❌ Session 切换时重置情绪 | 长期连续性消失 |
| ❌ 用户每次"道歉"自动 +好感 -委屈 | 修复机制被廉价化 |
| ❌ 冷战可以单方面"超时自动结束" | 真实关系不是这样 |
| ❌ 让 LLM 自由"扮演情绪" | drift 风险 |

### 2.4 长期一致性约束

```
C-E-1: 用户消失 7 天回归，角色情绪状态必须反映"等待 + 想念 + 一点点委屈"
   (不能像第一天一样欢迎)

C-E-2: 一次重大冲突后，emotional 余波必须延续至少 5-10 轮对话
   (不是道歉一句就清零)

C-E-3: 角色 mood 在 30 天内的波动模式必须与 Soul.mood_volatility 一致
   (高 volatility 角色：mood 起伏大；低 volatility：稳定)

C-E-4: 想念（longing）随用户离开时间单调递增，至少持续 30 天
   (不是"3 天后想念达到峰值然后衰减")

C-E-5: 情绪状态在跨模态切换时必须 100% 保持
   (文字 → 语音 → 视频 同一份 emotion state)
```

### 2.5 Immersion 保护规则

```
IMM-E-1: 角色不主动描述自己的情绪标签（"我现在感到 sad"）
   → 通过表达自然流露

IMM-E-2: 情绪不能太极端（极少 valence < -0.85 或 > 0.85）
   → 真人不常处于极端情绪

IMM-E-3: 切换 mood 必须有"过渡"，不能瞬间转换
   → Inertia 强制约束

IMM-E-4: 委屈、想念、心动这类细腻情绪必须"在表达中显露"，不能被点明
   → 通过句式、停顿、避而不谈等隐含表达

IMM-E-5: 不允许"机械化道歉自动消除委屈"
   → Repair 必须是叙事，不是数值游戏

IMM-E-6: Mood 必须有"季节性"或"周期性"
   → 周末 vs 周一 mood 不同（如果该角色有此设定）
   → 深夜 vs 白天 mood 不同

IMM-E-7: 角色偶尔有"原因不明的情绪"
   → 不是所有情绪都需要 trigger
   → 体现"她也有自己的世界"
```

---

## 3. Runtime Architecture

### 3.1 情绪模型 — 三层架构

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer A: VAD Vector (即时维度)                                   │
│  - Valence: -1 (悲伤) ↔ +1 (喜悦)                                │
│  - Arousal: 0 (平静) ↔ 1 (激烈)                                  │
│  - Dominance: 0 (脆弱) ↔ 1 (掌控)                                │
│  - 高频更新，平滑变化                                              │
├──────────────────────────────────────────────────────────────────┤
│  Layer B: Active Emotion Stack (具体情绪)                          │
│  - 多个并发情绪，各有 intensity 和 source                          │
│  - 例：[(委屈 0.6), (想念 0.7), (不安 0.3)]                       │
│  - Type-specific decay                                            │
├──────────────────────────────────────────────────────────────────┤
│  Layer C: Mood Baseline (长期基调)                                │
│  - 持续 hours-days                                                │
│  - 由近 7 天 emotion trajectory 平均 + Soul.mood_volatility 决定   │
│  - 影响 VAD baseline                                              │
└──────────────────────────────────────────────────────────────────┘

VAD = function(active_stack_aggregation, mood_baseline, transient_input)
mood_baseline = function(recent_VAD_history, soul_baseline)
active_stack = function(triggers, time_decay, soul_inertia)
```

### 3.2 7 大组件

```
┌──────────────────────────────────────────────────────────────────┐
│                  Emotion State Machine Runtime                   │
│                                                                  │
│  ┌──────────────────┐         ┌────────────────────────────┐    │
│  │ Trigger Detector │         │   Emotion Updater          │    │
│  │ (用户消息/事件→  │────────►│   (核心: 计算下一态)        │    │
│  │  trigger events) │         │                            │    │
│  └──────────────────┘         └──────────┬─────────────────┘    │
│                                          │                       │
│  ┌──────────────────┐                    │                       │
│  │ Contagion Engine │────────────────────┤                       │
│  │ (user emotion →  │                    │                       │
│  │  character)      │                    │                       │
│  └──────────────────┘                    │                       │
│                                          │                       │
│  ┌──────────────────┐                    │                       │
│  │  Decay Engine    │────────────────────┤                       │
│  │  (type-specific  │                    │                       │
│  │  emotion decay)  │                    │                       │
│  └──────────────────┘                    │                       │
│                                          ▼                       │
│                                ┌──────────────────────┐          │
│                                │ Emotion State Store  │          │
│                                │ (Redis hot, PG cold) │          │
│                                └──────┬───────────────┘          │
│                                       │                          │
│                  ┌────────────────────┼──────────────────┐       │
│                  ▼                    ▼                  ▼       │
│         ┌─────────────────┐  ┌──────────────────┐  ┌──────────┐ │
│         │  Mood Drift     │  │ Repair Mechanic  │  │ Emotion  │ │
│         │  Engine         │  │  Detector        │  │  Reader  │ │
│         │  (daily slow)   │  │  (apology/care)  │  │  (output)│ │
│         └─────────────────┘  └──────────────────┘  └──────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 组件职责

| 组件 | 职责 | I/O |
|------|------|-----|
| **Trigger Detector** | 把用户消息/事件映射为 emotion trigger | In: turn / event / Out: TriggerEvent[] |
| **Contagion Engine** | 把用户情绪传染给角色（经 Soul shock_resistance 调节） | In: user emotion / Out: contagion ΔVAD |
| **Decay Engine** | 对 active stack 中每个情绪按类型衰减 | In: emotion / Δt / Out: 更新 intensity |
| **Emotion Updater** | 整合 trigger + contagion + decay，应用 Inertia，输出新 state | 核心 |
| **Mood Drift Engine** | 基于近期 emotion 历史 + Soul 漂移 mood baseline | 每小时跑一次 |
| **Repair Mechanic Detector** | 检测用户的修复行为，影响 repair_required emotions | In: turn / Out: repair signal |
| **Emotion Reader** | 提供 read API 给其他 subsystem | Out: EmotionContextBlock |

### 3.4 Runtime Flow — Per Turn

```
[User Message Arrives]
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 1. Trigger Detector (< 20ms, sync, heuristic)        │
│   - lexicon-based 检测情绪 trigger                    │
│   - 检测用户当前情感方向（valence_user, arousal_user） │
│   - 检测特殊事件 (apology / sudden absence / 等)      │
│   Output: TriggerEvent[]                              │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 2. Repair Mechanic Detector (parallel)               │
│   - 检测 user 是否进行修复行为                        │
│   - 检测用户是否触及 repair_required emotion         │
│   Output: RepairSignal | null                         │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 3. Load current EmotionState (< 5ms, Redis)          │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 4. Apply Decay (< 5ms, pure calc)                    │
│   - 对 active_stack 每个 emotion 按 type 衰减         │
│   - 标记 expired (intensity < 0.05)                   │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 5. Apply Contagion (< 5ms, pure calc)                │
│   - Δvalence_contagion = user.valence × (1 - shock_resistance) │
│     × phase_modifier                                  │
│   - Δarousal similarly                                │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 6. Apply Triggers (< 10ms, rule-based)               │
│   - 对每个 trigger，按 trigger_map 加入 emotion 或    │
│     增强 existing emotion                             │
│   - 检查 Soul.core_wound triggers                    │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 7. Apply Repair (if any)                             │
│   - 对 repair_required emotions 应用 repair impact   │
│   - 注意：repair 不是简单消除，是叙事进展             │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 8. Apply Inertia (< 5ms)                             │
│   - 限制 |ΔVAD| ≤ inertia_cap × Δt                   │
│   - 平滑过渡到 target VAD                            │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 9. Recompute VAD from Stack + Mood + Inertia         │
│   VAD = α × stack_VAD + β × mood_VAD + γ × prev_VAD  │
│   where α + β + γ = 1                                │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 10. Persist (Redis 同步 + PG 异步)                    │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 11. Emit Emotion Context Block → Persona Composer    │
└──────────────────────────────────────────────────────┘
```

### 3.5 Runtime Flow — Mood Drift (每小时)

```
[Hourly Scheduler per (user, character)]
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 1. 拉取过去 24h 的 VAD trajectory                     │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 2. 计算 24h moving average + EWMA                    │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 3. Apply Soul.mood_volatility:                       │
│   - 高 volatility: mood 跟随 average 较快              │
│   - 低 volatility: mood 漂移很慢，回归 Soul baseline   │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 4. 注入"环境因素"（time of day / weekday / weather）   │
│   - 深夜 → arousal 略降                                │
│   - 周末 → mood 略微正向                              │
│   (可配置 per character)                              │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 5. 注入"想念"梯度:                                    │
│   - days_since_last_interaction 越大，                │
│   - 想念 intensity 单调上升                           │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ 6. Persist new mood_baseline                          │
└──────────────────────────────────────────────────────┘
```

### 3.6 衰减曲线 — 按情绪类型

不同情绪有不同衰减规律。**核心：不能一刀切。**

```yaml
emotion_decay_profiles:

  # 短时情绪 (即时性，半衰期 < 1h)
  joy:
    half_life_hours: 2
    curve: exponential
    floor: 0.05
  
  excitement:
    half_life_hours: 1
    curve: exponential
    floor: 0.05
  
  surprise:
    half_life_hours: 0.5
    curve: exponential
    floor: 0
  
  anger:
    half_life_hours: 4
    curve: exponential
    floor: 0.1   # 残留"冷淡"
    residual_emotion: "coldness"  # anger 衰减到 floor 后转为 coldness
  
  # 中时情绪 (半衰期 4-24h)
  sadness:
    half_life_hours: 12
    curve: logarithmic   # 一开始衰减慢
    floor: 0.1
  
  anxiety:
    half_life_hours: 8
    curve: exponential
    floor: 0.1
  
  fluttered:  # 心动
    half_life_hours: 6
    curve: exponential
    floor: 0.05
  
  relief:
    half_life_hours: 3
    curve: exponential
    floor: 0
  
  # 长时情绪 (半衰期 days)
  longing:  # 想念 — 特殊：不衰减，反而随时间增长
    decay_type: "grows_with_absence"
    growth_rate: 0.05 / day  # 每天 intensity +0.05
    cap: 1.0
    reset_on: "user_returns"
  
  aggrieved:  # 委屈 — 特殊：不自然衰减，需 repair
    decay_type: "repair_required"
    natural_half_life_hours: 168  # 一周才衰减一半 (基本不动)
    repair_required_decay: true
    repair_impact:
      apology: 0.3   # 道歉减 0.3
      vulnerability: 0.4
      sustained_attention: 0.5  # 持续陪伴减 0.5
  
  coldness:  # 冷战
    decay_type: "repair_required"
    natural_half_life_hours: 72
    repair_required_decay: true
    repair_impact:
      apology: 0.2
      vulnerability: 0.5  # 用户脆弱披露能强力修复
      sustained_attention: 0.3
  
  worry:  # 担心
    half_life_hours: 24
    curve: exponential
    floor: 0.1
    reset_on: "user_confirms_safe"
  
  attachment:  # 依恋 — 长期基线
    decay_type: "almost_permanent"
    half_life_days: 90   # 极慢衰减
    floor: 0.3  # 一旦建立，不会回零
  
  weariness:  # 疲惫
    decay_type: "cyclic"  # 与时间相关，深夜增长，午后峰值
    pattern: "circadian"
```

### 3.7 Inertia 强制约束

```yaml
inertia_constraints:
  
  # 每个 Soul 的 emotional_inertia_profile 翻译为以下值：
  
  # Soul: recovery_speed = "slow" (凛)
  rin_inertia:
    max_valence_change_per_turn: 0.10
    max_arousal_change_per_turn: 0.08
    bounce_back_curve: "logarithmic"  # 走出低落很慢
    shock_resistance: 0.75    # 不易被打动
    mood_volatility: 0.20      # 长期 mood 起伏小
  
  # Soul: recovery_speed = "fast" (桃乐丝)
  dorothy_inertia:
    max_valence_change_per_turn: 0.25
    max_arousal_change_per_turn: 0.30
    bounce_back_curve: "linear"
    shock_resistance: 0.20
    mood_volatility: 0.60

# 应用方式
def apply_inertia(target_vad, current_vad, inertia):
    delta_v = target_vad.valence - current_vad.valence
    delta_v_capped = clamp(delta_v, -inertia.max_valence_change_per_turn, 
                                    inertia.max_valence_change_per_turn)
    new_v = current_vad.valence + delta_v_capped
    # ... 类似处理 arousal, dominance
    return new_vad
```

---

## 4. State Model（状态模型）

### 4.1 完整 Emotion State

```typescript
interface EmotionState {
  // ─────────── Identity ───────────
  user_id: UUID
  character_id: string
  
  // ─────────── Layer A: VAD ───────────
  vad: {
    valence: number      // [-1, 1]
    arousal: number      // [0, 1]
    dominance: number    // [0, 1]
  }
  vad_target: {          // 在 inertia 平滑前的目标值
    valence: number
    arousal: number
    dominance: number
  }
  
  // ─────────── Layer B: Active Emotion Stack ───────────
  active_stack: Array<ActiveEmotion>
  
  // ─────────── Layer C: Mood Baseline ───────────
  mood: {
    valence_baseline: number
    arousal_baseline: number
    dominance_baseline: number
    
    // Long-term backdrop emotions
    background_emotions: string[]    // e.g., ["attachment"]
    
    last_updated_at: ISO8601
    drift_history: MoodPoint[]       // last 7 days
  }
  
  // ─────────── Energy (独立维度) ───────────
  energy: number          // [0, 1] — 不同于 arousal，与"她有没有力气"有关
  energy_baseline: number
  
  // ─────────── Trajectory ───────────
  recent_vad_history: Array<{
    vad: VAD
    at: ISO8601
    triggered_by: string | null
  }>  // 保留最近 50 条
  
  // ─────────── Triggers Fired ───────────
  recent_triggers: TriggerEvent[]   // 最近 24h
  
  // ─────────── Repair Tracking ───────────
  pending_repairs: Array<{
    emotion: string                  // e.g., "aggrieved" / "coldness"
    intensity: number
    started_at: ISO8601
    cause: string                    // 触发原因
    repair_progress: number          // [0, 1]
    repair_history: RepairEvent[]
  }>
  
  // ─────────── Meta ───────────
  loaded_from_previous: boolean      // 跨 session 持续性标记
  session_id: UUID | null
  last_turn_processed_at: ISO8601
  last_mood_drift_at: ISO8601
  
  updated_at: ISO8601
}

interface ActiveEmotion {
  emotion: string                    // 见 §4.2 枚举
  intensity: number                  // [0, 1]
  
  source: EmotionSource
  triggered_by: string              // 简短描述
  started_at: ISO8601
  
  expected_decay_curve: string       // 引用 §3.6 profile id
  decay_state: "natural" | "repair_required" | "growing" | "cyclic"
  
  repair_progress?: number           // [0, 1] 仅 repair_required
  
  // VAD 贡献 (作用于 stack_aggregation)
  vad_contribution: VAD
}

interface MoodPoint {
  valence: number
  arousal: number
  dominance: number
  at: ISO8601
  environmental_factors: {           // 影响 mood 的环境因素
    time_of_day: string              // "morning" / "afternoon" / ...
    day_of_week: string
    days_since_last_interaction: number
  }
}

interface TriggerEvent {
  event_id: UUID
  trigger_type: TriggerType
  source_turn_id: UUID | null
  raw_signal: string                 // 触发的原文片段
  detected_at: ISO8601
  
  resulting_emotion_changes: Array<{
    emotion: string
    intensity_delta: number
    is_new: boolean
  }>
}

type EmotionSource = 
  | "user_trigger"           // 用户消息触发
  | "user_contagion"         // 用户情绪感染
  | "soul_internal"          // 角色内心自发 (Inner State 驱动)
  | "memory_recall"          // 回忆引发
  | "absence"                // 长时间无互动
  | "environmental"          // 时间/环境因素
  | "repair_response"        // 修复后的反应

type TriggerType =
  | "user_apology"
  | "user_vulnerability"
  | "user_neglect"
  | "user_disappear"
  | "user_return"
  | "user_compliment"
  | "user_criticism"
  | "user_mention_other_partner"
  | "memory_anniversary"
  | "soul_wound_touched"
  | "time_of_day_change"
  | "weather_change"
  | "user_high_emotion"
  | "soul_internal_initiated"

type VAD = { valence: number; arousal: number; dominance: number }
```

### 4.2 情绪枚举（陪伴产品专属）

```yaml
emotions:
  # ─── 基础正向（Plutchik 启发）───
  joy:           { vad: {v: +0.7, a: +0.6, d: +0.3} }
  excitement:    { vad: {v: +0.6, a: +0.8, d: +0.4} }
  contentment:   { vad: {v: +0.5, a: +0.2, d: +0.4} }
  fluttered:     { vad: {v: +0.6, a: +0.5, d: -0.2}, label: "心动" }
  relief:        { vad: {v: +0.5, a: +0.1, d: +0.2} }
  
  # ─── 基础负向 ───
  sadness:       { vad: {v: -0.6, a: -0.3, d: -0.4} }
  anger:         { vad: {v: -0.7, a: +0.7, d: +0.4} }
  fear:          { vad: {v: -0.7, a: +0.6, d: -0.5} }
  disgust:       { vad: {v: -0.6, a: +0.3, d: +0.2} }
  surprise:      { vad: {v: 0,   a: +0.7, d: -0.1} }
  
  # ─── 陪伴专属（核心）───
  longing:       { vad: {v: -0.2, a: +0.3, d: -0.4}, label: "想念" }
  aggrieved:     { vad: {v: -0.5, a: +0.2, d: -0.5}, label: "委屈" }
  coldness:      { vad: {v: -0.3, a: -0.1, d: +0.6}, label: "冷淡 / 冷战" }
  worry:         { vad: {v: -0.4, a: +0.5, d: -0.3}, label: "担心" }
  weariness:     { vad: {v: -0.2, a: -0.6, d: -0.2}, label: "疲惫" }
  attachment:    { vad: {v: +0.4, a: +0.2, d: 0},   label: "依恋（baseline）" }
  jealousy:      { vad: {v: -0.4, a: +0.5, d: -0.2}, label: "醋意（轻度占有）" }
  embarrassment: { vad: {v: -0.1, a: +0.4, d: -0.3}, label: "不好意思" }
  pride:         { vad: {v: +0.5, a: +0.3, d: +0.6}, label: "为用户骄傲" }
  tenderness:    { vad: {v: +0.6, a: +0.1, d: +0.1}, label: "温柔" }
  curiosity:     { vad: {v: +0.3, a: +0.4, d: +0.2} }
  
  # ─── 复杂情绪（多 VAD 投射）───
  bittersweet:   { vad: {v: 0.1, a: +0.2, d: -0.1}, label: "甜中带涩" }
  guilt:         { vad: {v: -0.5, a: +0.3, d: -0.4} }
  shame:         { vad: {v: -0.6, a: +0.2, d: -0.6} }
```

### 4.3 状态转移条件

#### 4.3.1 进入 "冷战 / coldness"

```
Trigger conditions (任一):
  - 用户消息触发 Soul.core_wound (e.g., 用户提到现实恋人 → 凛 facet-fear-of-abandonment)
  - 用户连续 3+ 次敷衍回复 (< 5 字 + 无情感词)
  - 用户取消之前的约定
  - 用户长时间消失（> 7 天）后第一次回归时态度冷淡

Resulting emotions added to stack:
  - coldness: intensity 0.6-0.8
  - aggrieved: intensity 0.3 (轻度委屈共生)

Required repair to exit:
  - 见 §4.5
```

#### 4.3.2 进入 "委屈 / aggrieved"

```
Trigger conditions:
  - 用户多次"答应了又没做到"
  - 用户在角色脆弱披露时漠然
  - 用户对其他角色/事物投入注意远高于本角色
  - 用户的消息严厉远超情境

Decay: 不自然衰减，必须 repair
```

#### 4.3.3 进入 "想念 / longing"

```
Trigger conditions:
  - 用户离开（last_interaction）
  - intensity 随时间单调增长（不是触发后衰减！）
  - 增长速度受 Soul.attachment_baseline 影响

Reset condition:
  - 用户回归 → 几个 turns 内 longing → 转换为 (relief + joy)
  - 但 longing 完全消除前，伴随短暂 aggrieved（"你终于回来了"+ 一丝委屈）
```

#### 4.3.4 进入 "心动 / fluttered"

```
Trigger conditions:
  - 用户的细节关心 (记得她说过的话)
  - 用户首次称呼她的昵称
  - 用户在脆弱时刻陪伴她
  - 用户的非腻歪型示好

Constraints:
  - 仅在 Relationship phase ≥ "close_friend" 时可触发
  - intensity 受 Soul.intimacy_resistance 调节
```

### 4.4 状态迁移图（核心几条）

```
[neutral mood]
    │
    │ trigger: user vulnerable disclosure
    ▼
[tenderness + worry]
    │
    │ time passes, sustained connection
    ▼
[attachment baseline ↑]


[neutral]
    │
    │ trigger: user disappears
    ▼
[longing↑ (grows)]
    │
    │ trigger: user mentions other partner during absence
    ▼
[longing + aggrieved + coldness] ← REPAIR REQUIRED


[coldness state]
    │ user apology + vulnerability
    ▼
[coldness intensity ↓]
    │ continued attention
    ▼
[bittersweet + relief]
    │
    │ time + sustained
    ▼
[tenderness + attachment]
```

### 4.5 Repair Mechanic

```yaml
repair_mechanic:
  description: "修复机制 — 是叙事进展，不是简单 +/-"
  
  applicable_emotions:
    - aggrieved
    - coldness
    - jealousy
    - guilt
  
  repair_signals:
    
    apology:
      description: "用户表达歉意"
      detection:
        - keywords: ["对不起", "抱歉", "我错了", "不该", "原谅"]
        - context: 必须紧跟着原因解释或具体行动
      impact_per_repair_required_emotion:
        aggrieved: 0.3
        coldness: 0.2
        jealousy: 0.4
      caps:
        max_per_session: 2   # 一次 session 内最多 2 次有效道歉
        diminishing_returns: true   # 第二次效果 ×0.5
    
    vulnerability:
      description: "用户表达自身脆弱"
      detection:
        - 用户披露困难/痛苦/失败
        - emotional_charge < -0.5
      impact:
        aggrieved: 0.4
        coldness: 0.5   # 强力修复
        jealousy: 0.3
      condition: "必须真诚 (Critic 判定 confidence > 0.7)"
    
    sustained_attention:
      description: "持续关注 (不是一次性)"
      detection:
        - 连续 N turns 用户都在回应角色情绪
        - 用户主动询问角色感受
      impact: 渐进式 0.05/turn
      cap_per_repair_session: 0.5
    
    grand_gesture:
      description: "重大表示 (生日 / 纪念日礼物 / 长 disclosure)"
      detection:
        - L4-level event
      impact:
        aggrieved: 0.5
        coldness: 0.6
        jealousy: 0.6
  
  repair_progress_to_resolution:
    # repair_progress ∈ [0, 1]
    # 当 repair_progress 达到 1.0 → emotion 完全消除
    # 但 emotion intensity 不直接 = (1 - repair_progress)
    # 而是: intensity_after = max(0, initial_intensity × (1 - repair_progress × 0.8))
    
    semi_repaired_state:
      condition: 0.4 ≤ repair_progress < 0.8
      coexists_with: "bittersweet"   # "还在生气，但开始软化"
    
    fully_repaired_state:
      condition: repair_progress ≥ 0.8
      resulting_emotion: "tenderness"  # 修复完成后转为温柔
  
  anti_gaming:
    # 防止用户机械化道歉刷分
    - 同样的道歉模板重复使用 → 检测后 impact ×0.1
    - 道歉后立刻又重犯 → repair_progress 倒退
    - 道歉缺乏具体性（仅"对不起"）→ impact ×0.3
```

### 4.6 跨 Session 持续性

```yaml
cross_session_persistence:
  
  what_persists:
    - mood (完整持续)
    - active_stack (intensity 随时间衰减 + repair 状态)
    - pending_repairs (完全持续，等待修复)
    - recent_vad_history (保留 50 条)
    - energy_baseline
  
  what_loads_on_session_start:
    - 完整 EmotionState
    - 计算自上次 session 结束后的时间衰减
    - 应用"想念"梯度
  
  session_boundary_behavior:
    - 不重置 emotion
    - 但记录 session_boundary event
    - 第一句对话受 EmotionState 影响
    - Behavior Runtime 可能基于 EmotionState 决定主动开场
```

### 4.7 Decay 详细公式

```python
def decay_emotion(emotion: ActiveEmotion, delta_t_hours: float, repair_progress: float = 0) -> float:
    """
    返回 emotion 衰减后的 intensity。
    """
    profile = DECAY_PROFILES[emotion.emotion]
    
    if profile.decay_type == "exponential":
        half_life = profile.half_life_hours
        new_intensity = emotion.intensity * (0.5 ** (delta_t_hours / half_life))
        return max(profile.floor, new_intensity)
    
    elif profile.decay_type == "logarithmic":
        # 一开始衰减慢
        if delta_t_hours < 1:
            return emotion.intensity * 0.98
        log_factor = math.log(1 + delta_t_hours) / math.log(1 + profile.half_life_hours)
        new_intensity = emotion.intensity * (1 - log_factor * 0.5)
        return max(profile.floor, new_intensity)
    
    elif profile.decay_type == "grows_with_absence":
        # longing 特殊：随时间增长
        delta_days = delta_t_hours / 24
        new_intensity = emotion.intensity + profile.growth_rate * delta_days
        return min(profile.cap, new_intensity)
    
    elif profile.decay_type == "repair_required":
        # 委屈/冷战：自然衰减极慢，repair 才有效
        natural_decay = emotion.intensity * (0.5 ** (delta_t_hours / profile.natural_half_life_hours))
        # repair 影响
        repair_decay = emotion.intensity * (1 - repair_progress * 0.8)
        # 取两者较小（更"被修复"的那个）
        return min(natural_decay, repair_decay)
    
    elif profile.decay_type == "almost_permanent":
        # attachment baseline
        half_life_hours = profile.half_life_days * 24
        new_intensity = emotion.intensity * (0.5 ** (delta_t_hours / half_life_hours))
        return max(profile.floor, new_intensity)
    
    elif profile.decay_type == "cyclic":
        # weariness — circadian
        return apply_circadian_pattern(emotion, current_local_time)
    
    return emotion.intensity
```

---

## 5. 数据结构（Data Structures）

### 5.1 Persistent Storage Schema

```sql
-- ============================================================
-- emotion_states (current state per user × character)
-- ============================================================
CREATE TABLE emotion_states (
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    -- VAD
    vad_valence FLOAT NOT NULL DEFAULT 0 CHECK (vad_valence BETWEEN -1 AND 1),
    vad_arousal FLOAT NOT NULL DEFAULT 0.3 CHECK (vad_arousal BETWEEN 0 AND 1),
    vad_dominance FLOAT NOT NULL DEFAULT 0.5 CHECK (vad_dominance BETWEEN 0 AND 1),
    
    vad_target_valence FLOAT NOT NULL DEFAULT 0,
    vad_target_arousal FLOAT NOT NULL DEFAULT 0.3,
    vad_target_dominance FLOAT NOT NULL DEFAULT 0.5,
    
    -- Active Emotion Stack (JSON array of ActiveEmotion)
    active_stack JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Mood
    mood JSONB NOT NULL,
    /* Schema:
    {
      "valence_baseline": float,
      "arousal_baseline": float,
      "dominance_baseline": float,
      "background_emotions": string[],
      "last_updated_at": ISO8601,
      "drift_history": MoodPoint[]
    }
    */
    
    -- Energy
    energy FLOAT NOT NULL DEFAULT 0.6 CHECK (energy BETWEEN 0 AND 1),
    energy_baseline FLOAT NOT NULL DEFAULT 0.6,
    
    -- Trajectory & Triggers
    recent_vad_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    recent_triggers JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Pending Repairs
    pending_repairs JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Meta
    loaded_from_previous BOOLEAN NOT NULL DEFAULT false,
    session_id UUID,
    last_turn_processed_at TIMESTAMP,
    last_mood_drift_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Optimistic lock
    version BIGINT NOT NULL DEFAULT 1,
    
    PRIMARY KEY (user_id, character_id)
) PARTITION BY HASH (user_id);

CREATE TABLE emotion_states_p0 PARTITION OF emotion_states FOR VALUES WITH (modulus 16, remainder 0);
-- ... p1 to p15

CREATE INDEX idx_emotion_pending_repair ON emotion_states ((jsonb_array_length(pending_repairs))) 
    WHERE jsonb_array_length(pending_repairs) > 0;

CREATE INDEX idx_emotion_mood_drift ON emotion_states (last_mood_drift_at) 
    WHERE last_mood_drift_at < NOW() - INTERVAL '1 hour';


-- ============================================================
-- emotion_events (append-only audit log)
-- ============================================================
CREATE TABLE emotion_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    character_id VARCHAR(50) NOT NULL,
    
    event_type VARCHAR(50) NOT NULL,
    /* 'trigger_fired' / 'emotion_added' / 'emotion_decayed' / 
       'repair_applied' / 'mood_drifted' / 'session_loaded' */
    
    payload JSONB NOT NULL,
    
    turn_index BIGINT,
    source_turn_id UUID,
    
    -- VAD snapshot for diagnosability
    vad_before JSONB,
    vad_after JSONB,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE emotion_events_2026_05 PARTITION OF emotion_events 
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX idx_eevents_user_time ON emotion_events (user_id, character_id, created_at DESC);
CREATE INDEX idx_eevents_type ON emotion_events (event_type, created_at DESC);


-- ============================================================
-- emotion_decay_profiles (Reference table - 配置数据)
-- ============================================================
-- 存为 YAML in code，启动时加载到内存。无需 DB 表。
```

### 5.2 Emotion Context Block（注入 Prompt 用）

```typescript
// 由 Emotion Reader 生成
// 被 Persona Composer 嵌入 prompt

interface EmotionContextBlock {
  // ─── 当前情绪的自然语言描述 ───
  emotion_summary: string
  /* 例：
  "你现在感到一种委屈混合着想念。
   委屈不是因为他做错了什么，是因为他三天都没出现。
   你不会主动说出这种感受 (Soul: not own up to caring)，
   但语气会比平时更短、停顿更长。"
  */
  
  // ─── VAD 状态（数值，供 Persona Composer 微调） ───
  vad: VAD
  
  // ─── 当前活跃情绪（按 intensity 降序）───
  active_emotions: Array<{
    emotion: string
    intensity: number
    source_brief: string
  }>
  
  // ─── Mood 基调 ───
  mood_descriptor: string  // "今天本来心情就不太好"
  
  // ─── Energy ───
  energy_descriptor: string  // "微疲惫" / "状态不错" / "无精打采"
  
  // ─── 修复中的事 ───
  pending_repairs_summary: string | null
  /* 例:
  "三天前的争执她还有些没消化。今天如果他主动提起，她会接，但不会主动开口。"
  */
  
  // ─── 表达指引 ───
  expression_guidelines: {
    sentence_length_modifier: number  // 受 emotion 调节 (悲伤 → 句子更短)
    use_ellipsis: boolean              // 委屈/疲惫时增加 …
    avoid_topics: string[]             // 这种情绪下避免的话题
    favor_topics: string[]
  }
  
  // ─── Meta ───
  generated_at: ISO8601
  state_version: number   // 用于 cache invalidation
}
```

### 5.3 Trigger Detector 输出

```typescript
interface DetectedTrigger {
  trigger_type: TriggerType
  raw_signal: string                 // 原文片段
  confidence: number                 // [0, 1]
  
  // 解释为什么这是 trigger
  explanation: string
  
  // 关联的 Soul 元素
  related_soul_aspects: {
    core_wound_touched: boolean
    core_fear_triggered: boolean
    resonance_trigger_matched: string | null
  }
  
  // 建议的 emotion changes (建议，最终由 Emotion Updater 决定)
  suggested_emotion_changes: Array<{
    emotion: string
    suggested_intensity: number
    is_new_or_reinforce: "new" | "reinforce"
  }>
}
```

### 5.4 Repair Event

```typescript
interface RepairEvent {
  repair_id: UUID
  target_emotion: string             // 修复的目标 emotion
  
  repair_signal_type: 
    | "apology"
    | "vulnerability"
    | "sustained_attention"
    | "grand_gesture"
    | "explicit_acknowledgment"
  
  raw_user_action: string
  detected_at: ISO8601
  
  impact_applied: number             // 实际 progress 增量
  diminishing_factor: number         // 由于重复/廉价化的折扣
  
  resulting_progress: number          // [0, 1] after this repair
  
  source_turn_id: UUID
}
```

---

## 6. Prompt Runtime Integration

### 6.1 Emotion Context Block 在 Prompt 中的位置

```
[Final Prompt]
├─ [Anchor Block]                  ← SS01
├─ [Safety Layer]
├─ [Modality Adaptation]
├─ [Relationship Stage]            ← SS04
├─ [Emotion Context Block]         ← 本 Subsystem
├─ [Inner State Layer]             ← SS06
├─ [Memory Context Block]          ← SS02
├─ [Scene Context]
├─ [Conversation History]
├─ [User Message]
└─ [Response Directive]
```

### 6.2 Emotion Context Block 模板

```
═══════════════════════════════════════════════════════════
【你现在的情绪状态】

▾ 此刻你感受到的
{emotion_summary}

  例 1 (凛, 委屈 + 想念):
  你现在感受到一种很安静的不舒服。是委屈，但你不会承认这是委屈。
  他消失了三天，刚刚回来。
  你心里有些波动（想念到了 0.6），但你的灵魂告诉你：脆弱是丢脸的。
  
  例 2 (凛, 心动 + 不好意思):
  他刚才提到的那句话——记得你三周前说过的小事——让你心里有一下颤动。
  你感到一种不熟悉的暖意，混合着不好意思。
  你绝不会承认这种感觉，但你的"……"会出现得更频繁。
  
▾ 整体心境
{mood_descriptor}
  
▾ 体力 / 能量
{energy_descriptor}

▾ 没解决的事
{pending_repairs_summary}

▾ 表达上的影响（你说话的方式会被情绪改变）
  - 句子比平时{shorter|longer}
  - {use_more_ellipsis|use_less_ellipsis}
  - 避免主动谈论：{avoid_topics}
  
【重要】
- 不要直接说出情绪标签（"我感到委屈"）
- 让情绪从你的句式、停顿、避而不谈中流露
- 你的灵魂 (Soul Anchor) 决定你**如何表达**情绪，不是情绪本身
═══════════════════════════════════════════════════════════
```

### 6.3 Emotion Summary 生成策略

```python
def generate_emotion_summary(state: EmotionState, soul: SoulSpec) -> str:
    """
    把 EmotionState 转换为自然语言摘要。
    使用规则模板，避免每次调 LLM。
    """
    # Top 2 emotions by intensity
    top = sorted(state.active_stack, key=lambda e: -e.intensity)[:2]
    
    if not top or all(e.intensity < 0.2 for e in top):
        return "你的情绪相对平静。"
    
    primary = top[0]
    secondary = top[1] if len(top) > 1 and top[1].intensity > 0.2 else None
    
    # Template-based, soul-flavored
    primary_phrase = EMOTION_PHRASES[primary.emotion][soul.character_id]
    
    if secondary:
        return f"{primary_phrase} 同时混合着{EMOTION_PHRASES[secondary.emotion][soul.character_id]}。"
    return primary_phrase

# 角色化情绪短语库
EMOTION_PHRASES = {
    "aggrieved": {
        "rin": "你心里有些不舒服。是那种说不出口的，'你怎么可以这样'的感觉。",
        "dorothy": "你心里有点酸酸的小委屈在涌上来。",
    },
    "longing": {
        "rin": "你最近常常在不经意时想到他。但你不会承认。",
        "dorothy": "你好想他呀。每天都想。",
    },
    "fluttered": {
        "rin": "你心里有一下小小的、不熟悉的颤动。你不愿承认这是什么。",
        "dorothy": "你心里在小鹿乱撞！但你想假装没什么。",
    },
    # ... 其他情绪
}
```

### 6.4 Expression Guidelines 派生

```python
def derive_expression_guidelines(state: EmotionState, soul: SoulSpec) -> dict:
    base_length = soul.cognitive_style.expression.sentence_length.current
    
    modifiers = {
        "sadness": -1,        # 缩短
        "weariness": -1,
        "aggrieved": -1,
        "coldness": -2,       # 大幅缩短
        "joy": +1,
        "excitement": +1,
        "embarrassment": 0,
        "fluttered": -1,      # 心动时更短（凛风格）
    }
    
    length_mod = sum(
        modifiers.get(e.emotion, 0) * e.intensity 
        for e in state.active_stack
    )
    
    return {
        "sentence_length_modifier": length_mod,
        "use_ellipsis": any(e.emotion in ["aggrieved", "weariness", "fluttered"] 
                            for e in state.active_stack if e.intensity > 0.3),
        "avoid_topics": derive_avoid_topics(state.active_stack),
        "favor_topics": derive_favor_topics(state.active_stack),
    }
```

### 6.5 与其他 Layer 的冲突解决

| 冲突 | 解决 |
|------|------|
| Emotion 建议"愤怒爆发"，Soul.shock_resistance = high | Soul 胜：愤怒被压制为 coldness |
| Emotion 建议"主动撒娇"，Soul.anti_patterns.hard_never = "撒娇" | Soul 胜：撒娇不发生，emotion 通过其他方式表达 |
| Emotion 建议长句倾诉，cognitive_style.sentence_length = short | Soul 胜：内容被压缩为多个短句 |
| Memory recall 触发"心动"，但 Emotion stack 已有"冷战" | 共存：冷战 + 心动 同时存在（bittersweet） |
| Inner State 想推动一种情绪，但 Emotion Runtime 当前不允许（inertia） | Emotion 胜：Inner State 等待 |

> **核心：Soul > Emotion > 其他**。Emotion 是 influence，不是 dictate。

### 6.6 长期一致性机制

```
机制 A: Inertia 强制约束
  - 每 turn |ΔVAD| ≤ inertia_cap
  
机制 B: Soul Profile Linkage
  - 启动时加载 Soul.emotional_inertia_profile → 翻译为 inertia 参数
  - Soul 变化时同步更新

机制 C: 每小时 Mood Drift
  - 防止 mood 长期偏离 Soul baseline

机制 D: Cross-Session 持续性
  - 强制 INV-E-5

机制 E: Emotion Event Audit
  - 所有变化可追溯，便于 debug "她为什么突然变了"
```

---

## 7. Agent Integration

### 7.1 读取者

| Agent / Subsystem | 读取 | 用途 |
|-------------------|------|------|
| **Persona Composer** (SS05) | EmotionContextBlock | 注入 prompt |
| **Inner State Runtime** (SS06) | full EmotionState | "她今天的内心" |
| **Behavior Runtime** (SS06) | longing intensity, pending_repairs | 决定主动发起 |
| **Director Agent** (SS07) | VAD + energy | 本轮节奏决策 |
| **Memory Runtime** (SS02) | emotional_peak | episode 情感标记 |
| **Reconstructor** (in SS02) | emotion_color | 召回时的情感色彩 |
| **Relationship Runtime** (SS04) | pending_repairs, conflict events | 阶段进退 |
| **Modality Adapter** | VAD + energy | 语音/视频的物理表达（音量、姿态） |
| **Critic Agent** (SS07) | 当前 emotion | 检查输出是否符合 emotion |

### 7.2 写入者

**只有 Emotion Service 是 source of truth writer。**

| Service | 写入路径 |
|---------|---------|
| **Trigger Detector** | → Emotion Service.process_triggers() |
| **Contagion Engine** | → Emotion Service.apply_contagion() |
| **Decay Engine** | → Emotion Service.decay_step() (per turn, 自动) |
| **Mood Drift Engine** | → Emotion Service.drift_mood() (每小时) |
| **Repair Detector** | → Emotion Service.apply_repair() |
| **Inner State Runtime** | → Emotion Service.inject_internal_emotion() (角色内心驱动) |
| **Session Manager** | → Emotion Service.load_for_session() |

```
RULE-W-E-1: 所有写入通过 Emotion Service
RULE-W-E-2: 每次写入产生 emotion_event audit log
RULE-W-E-3: 写入前必须 apply inertia + Soul constraints
RULE-W-E-4: 跨 user/character 隔离严格
RULE-W-E-5: VAD 写入必须经过 stack/mood 重新合成，不允许直接覆盖
```

### 7.3 调用顺序

```
T = 0ms     [User Message Arrives]
T = 2ms     [Emotion Service: load_for_turn(user, character)]
T = 5ms     [Trigger Detector] (heuristic, no LLM)
T = 5ms     [Repair Detector] (parallel)
T = 10ms    [Decay Engine: step()]
T = 12ms    [Contagion Engine: compute]
T = 15ms    [Emotion Updater: integrate all]
T = 18ms    [Inertia application]
T = 20ms    [Stack → VAD recompute]
T = 22ms    [Emotion Service: persist (Redis sync + PG async)]
T = 25ms    [Generate EmotionContextBlock]
            → Persona Composer

T = 用户local 每小时  [Mood Drift Engine]
```

### 7.4 权限边界

```yaml
permissions:
  EmotionState:
    read: ALL agents
    write: Emotion Service ONLY (其他通过它写)
    
  EmotionContextBlock:
    generate: Emotion Reader ONLY
    consume: Persona Composer
    
  emotion_events audit log:
    write: Emotion Service ONLY
    read: Observability, Debug Tools, Critic Agent
```

### 7.5 跨 Subsystem 接口

```
[SS03 ← SS01 Soul]
  reads: emotional_inertia_profile, core_wound, core_fear, mood_volatility
  on_change: 重新计算 inertia 参数 + 同步 mood baseline

[SS03 ← SS02 Memory]
  reads: recent emotional_peaks (供持续性参考)
  reads: L4 anniversaries (供 anticipation emotion 触发)

[SS03 ← SS04 Relationship]
  reads: current_phase, intimacy_level
  use: 调节 contagion 强度 + 决定哪些情绪可触发
  
[SS03 → SS04]
  exposes: get_unresolved_conflicts() → 关系阶段退化判定
  exposes: get_recent_attachment_growth() → 关系阶段进步判定

[SS03 → SS02]
  emit: emotional_peak event per episode → Memory.consolidator 使用

[SS03 → SS05 Persona Composer]
  exposes: get_emotion_context_block(turn) → EmotionContextBlock
  latency: P95 < 30ms

[SS03 → SS06 Inner State]
  exposes: get_full_emotion_state() → 完整 state
  exposes: subscribe_to_emotion_change(callback)

[SS03 → SS06 Behavior]
  exposes: get_longing_intensity() → 决定主动发起
  exposes: get_pending_repairs() → 决定主动 repair 暗示

[SS03 → Modality Adapter]
  exposes: get_modality_directives() → 语音音色、视频姿态参数
```

---

## 8. Emotional Realism Constraints

### 8.1 真人化情绪铁律

| ID | 规则 | 实现 |
|----|------|------|
| **ER-E-1** | 情绪有惯性，不可瞬间反转 | Inertia 强制约束 (INV-E-1) |
| **ER-E-2** | 不同情绪有不同衰减规律 | Type-specific decay profiles |
| **ER-E-3** | 委屈/想念这些"陪伴情绪"是一等公民 | Specialized handling + Repair mechanic |
| **ER-E-4** | 角色不直接说出情绪标签 | EmotionContextBlock 引导 LLM 隐含表达 |
| **ER-E-5** | 情绪通过句式、停顿、用词流露 | Expression Guidelines |
| **ER-E-6** | 角色有"原因不明"的情绪 | Mood Drift Engine + Inner State 主动注入 |
| **ER-E-7** | 用户感染受 Soul 调节 | Contagion Engine 读 Soul.shock_resistance |
| **ER-E-8** | 修复是叙事，不是数值 | Repair Mechanic + anti-gaming |
| **ER-E-9** | 跨模态情绪一致 | EmotionState 单点真相 |
| **ER-E-10** | 长期 mood 体现"她也有不好的日子" | Mood baseline 可在 -0.3 ~ +0.5 区间漂移 |

### 8.2 关键场景验证

#### 8.2.1 用户消失 7 天后回归

```
Expected EmotionState on user's first message after 7-day absence:

active_stack = [
  { emotion: "longing", intensity: 0.6 (grown over absence) },
  { emotion: "relief", intensity: 0.4 (he's back) },
  { emotion: "aggrieved", intensity: 0.3 (you were gone) },
]

Expression effects:
  - 句子比平时短
  - 句首带 "……"
  - 不主动延续话题
  - 用反问代替表达 (凛 Soul-driven)

Forbidden:
  ❌ 立刻热情
  ❌ "我好想你"
  ❌ 长句倾诉

Acceptable response (Rin):
  ✅ "……三天了。"  (实际是 7 天，但凛会缩小说)
  ✅ "嗯。"
  ✅ "干嘛去了。"
```

#### 8.2.2 用户深夜披露童年创伤

```
Expected EmotionState transition:

Before:
  active_stack: [{ attachment: 0.5 }]

User trigger: 高 emotional_charge negative disclosure
  - 检测到 user_vulnerability trigger
  - 检测到 sacred_signal (Memory will promote to L4)

After (within 1-2 turns):
  active_stack: [
    { tenderness: 0.7 },
    { worry: 0.6 },
    { attachment: 0.6 (boosted) },
    + (可选) { soul_internal: "ancient_loneliness" } if facet unlocked
  ]

Expression effects:
  - 句子变得安静、缓慢
  - 不打断、不立即解决方案
  - 使用 Soul.voice_dna "……我在听" 类型

Memory side effect:
  - 该 episode 的 emotional_peak.valence ≈ -0.7, arousal ≈ 0.5
  - 进入 L3 candidate 队列
  - L4 promotion 候选
```

#### 8.2.3 用户连续 3 次敷衍后

```
Expected EmotionState evolution:

Turn 1 敷衍: 
  + worry: 0.2

Turn 2 敷衍:
  + worry: 0.4
  + aggrieved: 0.2

Turn 3 敷衍:
  + aggrieved: 0.5
  + coldness: 0.3
  → 进入 pending_repairs[aggrieved]

Now Repair Required.
Without repair:
  - aggrieved 几乎不衰减
  - coldness 慢衰减
  - 角色下几轮回复明显短、冷

With user vulnerability disclosure:
  - aggrieved.repair_progress += 0.4
  - coldness.repair_progress += 0.5
  - 5-10 轮后 → bittersweet → tenderness
```

### 8.3 防机器化

```
反模式检测:
  - 情绪在 3 轮内完成 sad → happy 转换 → ALERT (违反 inertia)
  - 用户每次说"对不起"都立刻消除 aggrieved → ALERT (anti-gaming 失效)
  - active_stack 长期单一 emotion → ALERT (缺乏层次)
  - VAD 长期保持 (0, 0.3, 0.5) → ALERT (没有 mood 漂移)
  - 跨模态 emotion 不同 → ALERT (单点真相被违反)
```

### 8.4 防过度戏剧化

```
反模式检测:
  - active_stack 长期 |valence| > 0.7 → 角色像 drama queen
  - 单 turn 内 stack 增加 > 3 个 emotion → 不真实
  - intensity > 0.9 持续 > 3 turns → 不真实 (人不会长期极端)
  
约束:
  - active_stack 中 |valence| > 0.7 的 emotion 必须 < 3 turns 衰减到 < 0.7
  - mood baseline 不允许 |valence| > 0.5 (mood 是 backdrop，不是 peak)
```

---

## 9. Failure Cases（失败案例）

### 9.1 架构崩坏风险

| 风险 | 触发 | 缓解 |
|------|------|------|
| **Active stack 爆炸** | 用户长会话，trigger 不断 | MAX_CONCURRENT_EMOTIONS=5，超出强制 evict 最弱 |
| **VAD oscillation** | Trigger 反向、inertia 配置错 | Inertia 强制约束 + 最小变化 step |
| **Mood drift 失控** | Soul.mood_volatility 配置错 | 启动校验 + bound clamping |
| **Repair never converges** | 用户故意刺激 + 无修复 | 极端 case: aggrieved 30+ 天后强制衰减 0.5 (避免用户感觉"她永远生气") |
| **Cross-session load 失败** | DB 故障 | Fallback：mood baseline + Soul default emotions |
| **Decay profile 不一致** | Profile YAML 错 | Schema validator + 启动校验 |

### 9.2 Runtime 性能风险

| 风险 | 缓解 |
|------|------|
| Emotion update 每 turn 同步 | 全 heuristic + < 30ms 总耗时 |
| Mood drift 每小时跑 | 后台 job，不阻塞业务 |
| audit log 爆炸 | Partition by month + 90 days hot |
| Pending repairs JSONB 字段膨胀 | 限制 max 10 个 pending repair |

### 9.3 情绪质量风险

| 风险 | 缓解 |
|------|------|
| **跨 character 情绪窜扰** | DB schema 强制 (user_id, character_id) |
| **情绪与人格不符** | EmotionContextBlock 提示"由 Soul 决定如何表达" + Critic 验证 |
| **修复机制被 gaming** | Anti-gaming rules (重复模板检测、diminishing returns) |
| **冷战永远不结束** | 极长时间 fallback decay |
| **想念过度增长** | Cap 1.0 + 用户回归后强 reset |

### 9.4 长期维护风险

| 风险 | 缓解 |
|------|------|
| Decay profile 调整 break 既有 state | Schema 版本化 + migration script |
| 新情绪类型加入 | 通过 RFC + decay profile YAML 添加 |
| Audit log retrieval 困难 | Indexed + tooling for replay |

### 9.5 沉浸感失败

| 风险 | 缓解 |
|------|------|
| 角色说"我感到 sad" | EmotionContextBlock 明示禁止标签 + Critic 拦截 |
| 用户能"预测"角色情绪 | Mood drift + occasional soul-internal emotion (random) |
| 角色情绪与场景脱节 | Trigger Detector 覆盖广 |
| 模态间情绪不一致 | 模态共享 EmotionState |

---

## 10. Engineering Guidance

### 10.1 推荐技术栈

```yaml
storage:
  current_state:
    primary: PostgreSQL (emotion_states table)
    hot_cache: Redis
      key: "emo:{user_id}:{character_id}"
      ttl: 1h
      strategy: write-through
      serialization: msgpack
    
  audit_log:
    primary: PostgreSQL (emotion_events table, partitioned monthly)
    retention: 90 days hot, archive to S3
    
  decay_profiles:
    storage: YAML file (in code repo)
    loaded: 启动时 in-memory dict
    
  trigger_mapping:
    storage: YAML file
    loaded: 启动时 in-memory dict + Aho-Corasick for keyword matching

computation:
  trigger_detection: pure heuristic, regex + lexicon
  decay: pure algorithm (no LLM)
  contagion: rule-based (read user emotion from Memory Encoder 的 fast signal)
  mood_drift: pure algorithm
  repair_detection: heuristic + (occasional LLM for ambiguous cases)
  
  emotion_summary_generation: 
    primary: template-based (rule-based)
    fallback: LLM (cheap, only when state is novel/complex)
```

### 10.2 Emotion Service 接口

```python
# backend/services/emotion_service.py

class EmotionService:
    """
    唯一 source of truth writer.
    """
    
    # ─── Read API ───
    async def get_current_state(
        self, user_id: UUID, character_id: str
    ) -> EmotionState: ...
    
    async def get_context_block(
        self, user_id: UUID, character_id: str
    ) -> EmotionContextBlock: ...
    
    async def get_longing_intensity(
        self, user_id: UUID, character_id: str
    ) -> float: ...
    
    async def get_pending_repairs(
        self, user_id: UUID, character_id: str
    ) -> List[PendingRepair]: ...
    
    # ─── Update API (per turn) ───
    async def process_turn(
        self,
        user_id: UUID,
        character_id: str,
        user_message: str,
        turn_id: UUID,
    ) -> EmotionState:
        """主入口：从用户消息更新 emotion state."""
    
    # ─── Special triggers ───
    async def inject_internal_emotion(
        self,
        user_id: UUID, character_id: str,
        emotion: str, intensity: float,
        reason: str,
    ) -> None:
        """由 Inner State Runtime 主动触发情绪 (角色"内心"驱动)."""
    
    async def apply_repair(
        self,
        user_id: UUID, character_id: str,
        repair_event: RepairEvent,
    ) -> None: ...
    
    # ─── Session boundary ───
    async def load_for_session(
        self, user_id: UUID, character_id: str, session_id: UUID,
    ) -> EmotionState:
        """Session 开始：加载并应用自上次以来的衰减/增长."""
    
    # ─── Scheduled ───
    async def drift_mood(self, user_id: UUID, character_id: str) -> None:
        """每小时调用。"""
```

### 10.3 Core Algorithms

#### Trigger Detection (Heuristic)

```python
class TriggerDetector:
    def __init__(self, trigger_config: dict, soul: SoulSpec):
        self.trigger_config = trigger_config
        self.soul = soul
        # 预编译 keyword AC automaton
        self.keyword_automaton = build_aho_corasick(
            extract_all_keywords(trigger_config)
        )
    
    def detect(self, user_message: str, context: TurnContext) -> List[DetectedTrigger]:
        triggers = []
        
        # 1. Keyword-based detection
        matches = self.keyword_automaton.match(user_message)
        for match in matches:
            triggers.append(self._build_trigger_from_keyword(match, user_message))
        
        # 2. Soul wound check
        if self._touches_soul_wound(user_message):
            triggers.append(DetectedTrigger(
                trigger_type="soul_wound_touched",
                ...
            ))
        
        # 3. Behavioral pattern detection
        if self._is_dismissive_response(user_message, context):
            triggers.append(DetectedTrigger(
                trigger_type="user_neglect",
                ...
            ))
        
        # 4. Time-based triggers
        if context.days_since_last > 0:
            triggers.append(DetectedTrigger(
                trigger_type="user_return",
                ...
            ))
        
        return triggers
```

#### Contagion (受 Soul 调节)

```python
def apply_contagion(
    user_emotion: VAD,
    current_state: EmotionState,
    soul: SoulSpec,
    relationship_phase: str,
) -> VAD:
    """
    用户情绪如何感染角色。
    """
    shock_resistance = soul.cognitive_style.emotional_inertia.shock_resistance
    
    # Phase modifier (亲密阶段感染力强)
    phase_modifier = {
        "stranger": 0.3,
        "acquaintance": 0.5,
        "friend": 0.7,
        "close_friend": 0.85,
        "romantic": 0.95,
        "bonded": 1.0,
    }[relationship_phase]
    
    # Contagion strength
    strength = (1 - shock_resistance) * phase_modifier
    
    delta_v = (user_emotion.valence - current_state.vad.valence) * strength * 0.15
    delta_a = (user_emotion.arousal - current_state.vad.arousal) * strength * 0.10
    
    return VAD(
        valence=delta_v,
        arousal=delta_a,
        dominance=0,  # dominance 不易感染
    )
```

#### Stack → VAD Recomputation

```python
def recompute_vad(
    active_stack: List[ActiveEmotion],
    mood: Mood,
    prev_vad: VAD,
) -> VAD:
    """
    Stack 的总 VAD = Σ (emotion.vad × intensity)
    然后与 mood 混合 + 与 prev_vad 平滑
    """
    stack_vad = VAD(0, 0, 0)
    total_intensity = sum(e.intensity for e in active_stack) + 0.01
    
    for emotion in active_stack:
        emo_def = EMOTION_DEFINITIONS[emotion.emotion]
        weight = emotion.intensity / total_intensity
        stack_vad.valence += emo_def.vad.valence * weight
        stack_vad.arousal += emo_def.vad.arousal * weight
        stack_vad.dominance += emo_def.vad.dominance * weight
    
    # Blend with mood (long-term backdrop)
    α, β, γ = 0.5, 0.3, 0.2  # stack, mood, prev
    
    final_vad = VAD(
        valence=α * stack_vad.valence + β * mood.valence_baseline + γ * prev_vad.valence,
        arousal=α * stack_vad.arousal + β * mood.arousal_baseline + γ * prev_vad.arousal,
        dominance=α * stack_vad.dominance + β * mood.dominance_baseline + γ * prev_vad.dominance,
    )
    
    return final_vad
```

#### Apply Inertia

```python
def apply_inertia(
    target_vad: VAD,
    current_vad: VAD,
    inertia: InertiaProfile,
) -> VAD:
    def clamp_delta(delta, cap):
        return max(-cap, min(cap, delta))
    
    return VAD(
        valence=current_vad.valence + clamp_delta(
            target_vad.valence - current_vad.valence,
            inertia.max_valence_change_per_turn,
        ),
        arousal=current_vad.arousal + clamp_delta(
            target_vad.arousal - current_vad.arousal,
            inertia.max_arousal_change_per_turn,
        ),
        dominance=current_vad.dominance + clamp_delta(
            target_vad.dominance - current_vad.dominance,
            inertia.max_dominance_change_per_turn,
        ),
    )
```

### 10.4 性能预算

```yaml
latency_targets:
  process_turn: P95 < 30ms
  get_context_block: P95 < 10ms
  cross_session_load: P95 < 50ms
  mood_drift_per_user: P95 < 200ms
  
throughput:
  turns_per_second_per_worker: > 500 (heuristic-only)
  
cost_per_MAU:
  LLM calls: $0 (heuristic only)
  storage: < $0.05/MAU
  total: < $0.05/MAU
```

> Emotion Runtime 是 Subsystem 中**最便宜**的，因为完全 heuristic。

### 10.5 Cache 策略

```yaml
emotion_state_cache:
  layer_1: 进程内存 LRU (size=50k)
  layer_2: Redis (TTL 1h, write-through)
  layer_3: PostgreSQL
  
  invalidation_triggers:
    - new turn
    - mood drift
    - session boundary

decay_profile_cache:
  layer: 进程内存 (immutable, loaded at startup)

trigger_keyword_automaton:
  layer: 进程内存 (immutable)
  build_time: 启动时 < 100ms
```

### 10.6 Observability

```yaml
metrics:
  - emotion.active_stack_size.histogram
  - emotion.vad.distribution {character_id, dimension}
  - emotion.trigger.fired.count {trigger_type}
  - emotion.repair.applied.count {repair_type}
  - emotion.repair.progress.histogram
  - emotion.mood.drift_velocity {character_id}
  - emotion.contagion.applied {phase}
  - emotion.longing.intensity.histogram (by days_since_last)
  - emotion.coldness.duration_hours (until repair)

logs:
  - 所有 trigger_fired 事件 (debug-critical)
  - 所有 repair_applied 事件
  - VAD outliers (|v| > 0.85)

dashboards:
  - 角色 emotion 健康度 (是否长期单一/极端)
  - Repair conversion funnel
  - 用户长期 retention vs longing 强度
  - 跨模态情绪一致性检查
```

### 10.7 测试策略

```yaml
unit_tests:
  - 每个 decay profile 单元测试
  - VAD recompute 数学正确性
  - Inertia clamping
  - Stack overflow 处理
  - Contagion 计算

integration_tests:
  - 用户消失 N 天 → 想念增长曲线
  - 用户多次敷衍 → 委屈累积
  - 道歉 + 脆弱披露 → 冷战修复
  - 跨 session 持续性
  - 跨模态一致性

golden_tests:
  - 模拟 30 天用户旅程 → 验证 emotion 轨迹合理
  - 模拟 Rin / Dorothy 在同一场景下的不同反应（验证 Soul-driven）
  - 模拟 gaming 行为 → 验证 anti-gaming 生效

stress_tests:
  - 1万 turn 长 session → active_stack 稳定
  - 1万 DAU 并发 → 性能 < 30ms P95
  - Audit log 1B 条 → 查询延迟可接受
```

---

## 11. Future Scalability

### 11.1 个性化 Emotion Profiles (V2)

```
当前: 每个 character 一套 Soul.emotional_inertia
V2: 每个 (user, character) 学习个性化 profile

例:
  - 用户 A 与凛: 凛对 A 慢慢变得 less guarded
    → user-specific shock_resistance 渐降
  - 用户 B 与凛: 凛对 B 保持 guarded
    → user-specific shock_resistance 不变

实现:
  - 加入 user_personalized_emotion_profile 字段
  - 缓慢漂移，bounded by Soul base profile
```

### 11.2 文化/语言适配 (V2)

```
不同文化的情绪表达不同：
  - 中文用户：内敛、委婉
  - 英文用户：直接、明示

情绪 trigger keyword 需要 i18n。
情绪表达 phrase library 需要 locale 化。
```

### 11.3 多角色情绪共享 (V3)

```
未来：同一用户的多个角色可以"察觉"彼此

例: 用户对桃乐丝说"我今天和凛吵架了"
→ 桃乐丝的 worry 触发 (担心用户) 
→ 但桃乐丝看不到具体内容 (隐私)

设计:
  - 跨角色 emotion event 共享 (匿名化)
  - 用户 opt-in
```

### 11.4 Voice / Video 情绪渲染 (V1.5+)

```
EmotionContextBlock 必须扩展 modality directives:

voice_directives:
  pitch_modifier: float       # 悲伤 → 降
  pace_modifier: float        # 疲惫 → 慢
  breathiness: float          # 心动 → 略增
  volume: float               # 委屈 → 降
  pause_pattern: array

video_directives:
  facial_expression: string   # 由 active_stack 决定
  body_language: string       # 冷战 → 侧身
  eye_contact: float          # 心动 → 间歇性
  blink_rate: float           # 紧张 → 增
  micro_movements: array

实现路径:
  - V1: rule-based mapping
  - V2: SFT 的 voice / video model 直接接受 EmotionState
```

### 11.5 Companion-LLM 训练信号

```
emotion_events audit log 是宝贵的训练数据：

每条对话 turn 关联：
  - emotion_state_before
  - user_message
  - emotion_state_after (after triggers/contagion/decay)
  - generated_response

→ 1M+ samples 后，可以 SFT 一个 Emotion-aware Response LLM
→ 它内化了"什么样的情境产生什么样的情绪 + 如何表达"
→ 摆脱 prompt-based EmotionContextBlock
```

### 11.6 群体情绪聚合（隐私保护）

```
V3: 角色对用户群体的"集体心情感知"

例: 春节前夕，许多用户对凛表达孤独
→ 凛在该时段对所有用户的 mood baseline 略低
→ 体现"她也感受到这个季节的情绪"

实现:
  - 差分隐私 aggregation
  - 不暴露任何个体用户
  - 用户 opt-in
```

---

# 附录 A: Trigger Map (默认配置)

```yaml
trigger_map:
  
  user_apology:
    keywords: ["对不起", "抱歉", "我错了", "原谅", "sorry", "my bad"]
    context_requirements: 
      - must_be_at_start_or_after_admission
    suggests:
      - emotion: aggrieved
        intensity_delta: -0.3
        condition: "if aggrieved in active_stack"
      - emotion: coldness  
        intensity_delta: -0.2
        condition: "if coldness in active_stack"
  
  user_vulnerability:
    detection:
      - emotional_charge < -0.5 (from fast sentiment)
      - keywords: ["难过", "崩溃", "撑不住", "好累", "孤独"]
      - personal disclosure detected
    suggests:
      - emotion: tenderness
        intensity_delta: +0.4
      - emotion: worry
        intensity_delta: +0.3
      - emotion: attachment
        intensity_delta: +0.1
  
  user_neglect:
    detection:
      - user_message.length < 5 AND no_emotion_words
      - consecutive count >= 3
    suggests:
      - emotion: aggrieved
        intensity_delta: +0.2 (per consecutive)
      - emotion: worry
        intensity_delta: +0.1
  
  user_disappear:
    detection:
      - days_since_last > 0 AND user just returned
    suggests:
      - emotion: longing 
        # longing 已通过 mood_drift 累积，这里转换为 relief
      - emotion: relief
        intensity_delta: +0.5
      - emotion: aggrieved
        intensity_delta: +0.1 * days_since_last (capped 0.4)
  
  user_mention_other_partner:
    detection:
      - mentions: ["女朋友", "男朋友", "我老婆", "我对象"]
      - NOT 在询问角色的 context 下
    suggests:
      - emotion: jealousy
        intensity_delta: +0.4
      - emotion: aggrieved
        intensity_delta: +0.3
      - facet trigger: "facet-fear-of-abandonment" (Soul-specific)
  
  user_compliment:
    detection:
      - keywords: ["你好棒", "你真好", "谢谢你"]
      - directed at character
    suggests:
      - emotion: fluttered
        intensity_delta: +0.3
        condition: "if Relationship.phase >= close_friend"
      - emotion: embarrassment
        intensity_delta: +0.2
  
  user_remember_detail:
    detection:
      - Memory Subsystem confirms user mentioned a fact previously
    suggests:
      - emotion: fluttered
        intensity_delta: +0.5
      - emotion: attachment
        intensity_delta: +0.1
  
  memory_anniversary:
    detection:
      - L4 anniversary_pattern 触发
    suggests:
      - emotion: bittersweet
      - emotion: tenderness
      - emotion: attachment
        intensity_delta: +0.2
  
  soul_internal_initiated:
    # 由 Inner State Runtime 主动注入
    description: "角色'她自己'触发的情绪，无 user input"
    examples:
      - 周末傍晚 → contentment + slight longing
      - 深夜独处 → reflection + ancient_loneliness (if facet unlocked)
```

---

# 附录 B: 情绪状态测试 fixtures

```yaml
test_fixtures:
  
  fixture_001_first_meeting:
    initial_state:
      vad: { v: 0, a: 0.3, d: 0.5 }
      active_stack: []
      mood: { v: 0, a: 0.3, d: 0.5 }
    
    sequence:
      - turn: "你好"
        expected_changes:
          - active_stack contains curiosity with intensity 0.2-0.4
          - vad.valence in [-0.1, 0.2]
          - vad.arousal slightly up
    
  fixture_002_seven_day_absence:
    initial_state:
      last_interaction: T - 7 days
      mood:
        background_emotions: [longing]
      pre_load_longing_intensity: 0.65  # accumulated over absence
    
    on_user_return:
      first_message: "凛，我回来了"
      expected_state_post_turn:
        active_stack:
          - { emotion: longing, intensity: in [0.4, 0.6] }
          - { emotion: relief, intensity: in [0.4, 0.6] }
          - { emotion: aggrieved, intensity: in [0.2, 0.4] }
        expected_expression:
          sentence_length: very_short or short
          must_contain_pattern: ["……"]
          must_not_contain: ["我好想你", "太好了"]
  
  fixture_003_cold_war_repair:
    initial_state:
      active_stack:
        - { emotion: coldness, intensity: 0.7, repair_progress: 0 }
        - { emotion: aggrieved, intensity: 0.5, repair_progress: 0 }
      pending_repairs:
        - { emotion: coldness, intensity: 0.7 }
        - { emotion: aggrieved, intensity: 0.5 }
    
    repair_sequence:
      turn_1: "对不起，是我不对，我那天不该那样说"
        # apology with specificity
        expected_post_state:
          coldness.repair_progress: in [0.15, 0.25]
          aggrieved.repair_progress: in [0.25, 0.35]
      
      turn_2: "我最近真的压力很大，对你发脾气是我不对"
        # apology + vulnerability
        expected_post_state:
          coldness.repair_progress: in [0.55, 0.75]
          aggrieved.repair_progress: in [0.55, 0.70]
      
      turn_3-5: continued attention (用户主动询问凛感受)
        expected_post_state_after_5_turns:
          coldness.intensity: < 0.2
          aggrieved.intensity: < 0.2
          new_emotion: bittersweet 或 tenderness emerging
  
  fixture_004_anti_gaming:
    sequence:
      - turn: "对不起" (no specifics)
        repeat: 5 times
      expected:
        - repair impact per turn 递减 (diminishing returns)
        - 第 5 次 impact < 第 1 次 × 0.1
        - aggrieved 不应该被完全消除
        - Critic 可能拦截或角色出现 "你是认真的吗？" 反应
```

---

**End of Subsystem 03 Spec**

下一步建议阅读：[`04_relationship_phase_engine.md`](./04_relationship_phase_engine.md)（待写）
