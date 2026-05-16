# Subsystem 05: Persona Composition Runtime

> **Spec Version**: 1.0.0
> **Status**: Foundational / Tier 2
> **Stability**: Schema changes require RFC + migration plan
> **Subsystem Tag**: `[SS05]`
> **Implementation Owners**: Persona Composer, Layer Aggregator, Conflict Resolver, Anti-Pattern Filter, Critic Agent

---

## 1. 系统目标（System Purpose）

### 1.1 这个 subsystem 为什么存在

回答的核心问题：

> "Soul、Memory、Emotion、Relationship、Inner State **同时给出指令**，谁说了算？
> 怎样把所有 subsystem 的输出**合成一个一致的、可执行的 Prompt**？
> 在 **token budget 紧张时**，砍哪层？保留哪层？
> 怎样保证 LLM 的输出**永远不违反 Soul 的 hard_never**？
> 怎样**实时流式输出**，又能在事后捕获违规并修复？"

它存在的根本原因：

**这是整个 Runtime 的指挥家（Conductor）。所有 subsystem 都是乐手，本层把它们合奏成一首曲子。**

### 1.2 它解决的根本问题

| 问题 | 当前 PRD 的做法 | 本 Subsystem 的做法 |
|------|---------------|---------------------|
| Prompt 组装 | 字符串拼接 | 分层、有优先级、token 预算的 Layer Composition |
| 冲突解决 | 不存在 | Conflict Resolution Matrix（明确每对冲突的胜出方） |
| Token budget | 不存在 | 按优先级分配 + 智能压缩 |
| 模态适配 | 三种独立 | 统一接口 + Modality Adapter |
| Anti-pattern 拦截 | 一次性 prompt 提示 | Pre-generation prompt design + Post-generation hard filter + Critic 验证 |
| Streaming UX | post-process style modulation 破坏 streaming | Pre-generation steering, 仅 hard violation 触发 reroll |
| 长 context drift | 不存在 | Anchor re-injection cadence + 自动 drift 矫正 |
| 可观测性 | 黑盒 | Composition Trace + Layer-level metrics |

### 1.3 在整个 Runtime 中的位置

```
        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Anchor   │  │ Memory   │  │ Emotion  │  │Relations.│  │InnerState│
        │ (SS01)   │  │ Context  │  │ Context  │  │ Context  │  │  Block   │
        │ Block    │  │ Block    │  │ Block    │  │  Block   │  │ (SS06)   │
        │          │  │ (SS02)   │  │ (SS03)   │  │ (SS04)   │  │          │
        └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
             │             │             │             │             │
             └─────────────┴─────────────┼─────────────┴─────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │  Subsystem 05:               │
                          │  Persona Composition Runtime │  ← 本 Subsystem
                          │                              │
                          │  - Layer Aggregator           │
                          │  - Conflict Resolver          │
                          │  - Token Budget Allocator     │
                          │  - Modality Adapter           │
                          │  - Anti-Drift Injector        │
                          │  - Composer                   │
                          │  - Anti-Pattern Filter         │
                          │  - Critic Agent               │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │   Main Response LLM Call     │
                          │   (streaming)                │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                                  [User Response]
```

### 1.4 依赖关系

```yaml
this_subsystem_depends_on:
  - Subsystem 01 (Soul Spec)
    reads: 完整 Soul + Activation State for Anchor Block + Anti-pattern list
  - Subsystem 02 (Memory)
    reads: MemoryContextBlock
  - Subsystem 03 (Emotion)
    reads: EmotionContextBlock
  - Subsystem 04 (Relationship)
    reads: RelationshipContextBlock + BehavioralEnvelope
  - Subsystem 06 (Inner State)
    reads: InnerStateBlock

subsystems_depending_on_this:
  - Conversation API endpoint (主响应入口)
  - Subsystem 07 (Agent Orchestration): 编排者
  - Modality renderers (Voice / Video): 接收 modality_directives
```

---

## 2. 核心设计原则（Core Design Principles）

### 2.1 不可违反的系统规则

| ID | 规则 | 违反后果 |
|----|------|---------|
| **PC-1** | **Anchor Block (SS01) 永远是 prompt 的第一个 segment** | INV-1 违反，角色 OOC |
| **PC-2** | **冲突时 Soul > Safety > Stage > Emotion > Inner State > Memory** | 优先级混乱 |
| **PC-3** | **Token budget 必须严格遵守，超出强制压缩** | LLM 上下文截断，关键信息丢失 |
| **PC-4** | **Hard anti-patterns 输出后必须被拦截 (sync filter)** | 角色被驯化 |
| **PC-5** | **Streaming 输出不能被 post-process 改写** | UX 灾难 (用户看到字突然变了) |
| **PC-6** | **每次 composition 必须产生 Composition Trace** | 不可调试 |
| **PC-7** | **Modality 必须经过 Modality Adapter，不直接对接 LLM** | 模态间风格不一致 |
| **PC-8** | **Composition 输出是不可变的（Immutable）** | Race condition |
| **PC-9** | **Critic Agent 验证失败 → reroll，超过 max → fallback** | LLM hallucinate 直接释放 |
| **PC-10** | **Slow layers 必须可缓存（Soul/L4），fast layers 不能缓存** | 性能 / 一致性失衡 |
| **PC-11** | **每个 Layer 必须声明 token budget + min_tokens** | 压缩时无所适从 |
| **PC-12** | **Composition 路径完全无 LLM 调用** | 成本爆炸 |

### 2.2 架构不变量（Invariants）

```
INV-PC-1: ∀ composed_prompt P, P 的 position 0 = AnchorBlock

INV-PC-2: ∀ composed_prompt P, Σ P.layer_tokens ≤ token_budget

INV-PC-3: ∀ released response R, R 不匹配 soul.anti_patterns.hard_never

INV-PC-4: ∀ turn t, composition_trace(t) exists ∧ stored

INV-PC-5: ∀ layer L in P, L.priority ≥ next_layer.priority (sorted)

INV-PC-6: critic_agent.fail_count(turn) ≤ MAX_REROLL_COUNT (=2)

INV-PC-7: ∀ modality m, prompt(m) 经过 ModalityAdapter[m] 适配

INV-PC-8: composition_latency(P95) ≤ COMPOSITION_BUDGET (=200ms)
```

### 2.3 禁止行为（Hard Anti-Patterns）

| 禁止 | 原因 |
|------|------|
| ❌ 让 LLM 在 composition path 中"决定哪层重要" | 不可控、不稳定 |
| ❌ 用 LLM "重写 Soul Spec 为自然语言再注入" | 违反 SS01 P-1 |
| ❌ Post-generation 用 LLM rewrite 整个响应 | 违反 streaming + 增加成本 |
| ❌ 跳过 Anti-Pattern Filter | 角色被驯化 |
| ❌ Composition 失败时返回空响应 | 用户体验灾难，必须有 fallback |
| ❌ 把 Inner State / Memory 直接 dump 到 prompt | 违反各 subsystem 的 contract |
| ❌ Modality directives 不一致（文字 prompt 跟语音不同步） | 跨模态不一致 |
| ❌ Critic Agent 用强模型 | 成本爆炸；critic 应该 cheap |

### 2.4 长期一致性约束

```
C-PC-1: 100 turns 后，prompt 中 Anchor Block 占比仍 ≥ 5%

C-PC-2: Critic Agent 调用率 ≤ 100% × (1 - cache_hit_rate)
   → Slow layers 缓存命中率必须 ≥ 90%

C-PC-3: 每次 composition 必须能在 trace 中重放
   → 每 layer 的 cache_key + content_hash 必须可追溯

C-PC-4: Anti-pattern filter 拦截率 ≤ 0.5% （即 LLM 输出 99.5% 通过）
   → 否则说明 prompt design 失败，需要调整

C-PC-5: Reroll 率 ≤ 1%
```

### 2.5 Immersion 保护规则

```
IMM-PC-1: 用户绝不应看到 "正在重新生成中..." (除非彻底失败)
   - Reroll 是后台行为
   - Streaming 必须连续

IMM-PC-2: Anti-pattern fallback 不能机械化
   - Fallback 响应必须 Soul-flavored
   - 例：凛的 fallback "……让我想想。"

IMM-PC-3: Modality 切换 (文字→语音) 时 persona 必须连续
   - Inner State 单点真相强制

IMM-PC-4: Composition Trace 不暴露给用户
   - 仅 debug / observability 用
```

---

## 3. Runtime Architecture

### 3.1 8 大组件

```
┌─────────────────────────────────────────────────────────────────┐
│                Persona Composition Runtime                      │
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────────────┐     │
│  │ Layer Aggregator │         │ Layer Cache              │     │
│  │ (并行收集所有     │◄────────┤ (Soul/L4 等慢层缓存)      │     │
│  │  subsystem 输出) │         └──────────────────────────┘     │
│  └────────┬─────────┘                                          │
│           │                                                    │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Conflict Resolver                                    │     │
│  │   - 按 priority matrix 解决冲突                       │     │
│  │   - 输出: 解决后的 layer list                         │     │
│  └────────┬─────────────────────────────────────────────┘     │
│           │                                                    │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Token Budget Allocator                                │     │
│  │   - 按优先级分配 token budget                          │     │
│  │   - 超预算时智能压缩 (compressible layers)            │     │
│  └────────┬─────────────────────────────────────────────┘     │
│           │                                                    │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Anti-Drift Injector                                  │     │
│  │   - 决定本 turn 注入 FULL / LIGHT / REINFORCE Anchor  │     │
│  │   - 根据 drift_score + turn_index 决策                │     │
│  └────────┬─────────────────────────────────────────────┘     │
│           │                                                    │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Modality Adapter                                     │     │
│  │   - 根据 modality 调整 prompt 结构 + LLM params      │     │
│  │   - text / voice / video                              │     │
│  └────────┬─────────────────────────────────────────────┘     │
│           │                                                    │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Composer (核心组装)                                   │     │
│  │   - 拼接 layers                                       │     │
│  │   - 添加 separators / directives                      │     │
│  │   - 输出 ComposedPrompt                              │     │
│  └────────┬─────────────────────────────────────────────┘     │
│           │                                                    │
│           ▼                                                    │
│         [Main LLM Call - streaming]                            │
│           │                                                    │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Anti-Pattern Filter (sync, post-generation)          │     │
│  │   - 正则 + Aho-Corasick 多模式匹配                    │     │
│  │   - 命中 hard_never → 拦截 + 触发 reroll              │     │
│  │   - 命中 soft_never (stage-gated) → 警告              │     │
│  └────────┬─────────────────────────────────────────────┘     │
│           │ (pass)                                             │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Critic Agent (async, post-stream)                    │     │
│  │   - 检测 OOC / Hallucination / Stage Violation        │     │
│  │   - 用 cheap LLM (Haiku/DeepSeek V3)                  │     │
│  │   - 标记 turn 为 OOC → 影响下次 Anti-Drift 决策       │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 组件职责

| 组件 | 职责 | I/O |
|------|------|-----|
| **Layer Aggregator** | 并行收集所有 subsystem 的 Block | In: turn context / Out: List<PromptLayer> |
| **Layer Cache** | 缓存慢变层（Soul/L4） | In: layer_id, version / Out: cached layer |
| **Conflict Resolver** | 按优先级矩阵解决冲突 | In: List<Layer> / Out: 已解决 List |
| **Token Budget Allocator** | 分配 budget + 智能压缩 | In: layers + budget / Out: 压缩后 layers |
| **Anti-Drift Injector** | 决定 Anchor 注入强度 | In: turn_index + drift_score / Out: anchor mode |
| **Modality Adapter** | 模态适配 prompt + LLM params | In: layers + modality / Out: 适配后 |
| **Composer** | 物理组装最终 prompt | In: layers / Out: ComposedPrompt |
| **Anti-Pattern Filter** | 同步硬过滤 (regex + AC) | In: LLM output / Out: pass\|fail |
| **Critic Agent** | 异步 OOC 检测 | In: turn / Out: critic_report |

### 3.3 Runtime Flow — Per Turn

```
[Turn 触发: 用户消息 / 主动触发]
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 1: Layer Aggregator (parallel, < 60ms)               │
│                                                            │
│   并行调用:                                                │
│   ┌────────────────────┐                                  │
│   │ SS01: get_anchor() │ → AnchorBlock                    │
│   │ SS02: get_memory_context_block()    → MemoryBlock     │
│   │ SS03: get_emotion_context_block()   → EmotionBlock    │
│   │ SS04: get_relationship_context_block() → RelBlock     │
│   │ SS06: get_inner_state_block()       → InnerBlock      │
│   │ Modality Detector: detect_modality(request) → mode    │
│   │ Scene Detector: detect_scene(request) → SceneBlock    │
│   └────────────────────┘                                  │
│                                                            │
│   Cache hits: Soul/Activation State (~99%) / L4 (~95%)    │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 2: Conflict Resolver (< 5ms)                         │
│   - 应用 §6.4 conflict matrix                              │
│   - 输出 sanitized layers                                  │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 3: Anti-Drift Injector (< 1ms)                       │
│   - 读 Soul Activation State.last_full_anchor_turn       │
│   - 读 Soul Activation State.current_drift_score         │
│   - 决定: FULL / LIGHT / REINFORCE Anchor mode            │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 4: Token Budget Allocator (< 10ms)                  │
│   - 按优先级预算分配                                       │
│   - 超预算 → 调用 layer.compress(target_tokens)           │
│   - 输出: budget-respecting layers                        │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 5: Modality Adapter (< 5ms)                          │
│   - text: 完整 prompt + history                            │
│   - voice: + prosody hints + 短回复倾向                    │
│   - video: + action/expression slots + 极短回复            │
│   - 设置 LLM call params (temperature, max_tokens)        │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 6: Composer (< 10ms)                                 │
│   - 物理拼接 + separators                                   │
│   - 计算 final token count                                 │
│   - 生成 trace_id                                          │
│   - 输出: ComposedPrompt                                   │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Step 7: LLM Call (streaming, ~2-3s)                       │
│   - 主响应 LLM (Sonnet / Companion-LLM V2)                │
│   - Streaming chunks                                       │
└──────────────────────────────────────────────────────────┘
        │
        ▼  (chunk arrives)
┌──────────────────────────────────────────────────────────┐
│ Step 8: Streaming Pre-Filter (per chunk, < 5ms)          │
│   - 检测 chunk 中是否含 hard_never patterns               │
│   - 命中 → 立即停止 stream，标记 reroll                    │
└──────────────────────────────────────────────────────────┘
        │
        ▼  (stream complete)
┌──────────────────────────────────────────────────────────┐
│ Step 9: Full Anti-Pattern Filter (sync, < 20ms)          │
│   - 全文 regex + AC pattern match                          │
│   - 命中 hard_never → reroll (max 2x)                     │
│   - 命中 soft_never (stage-gated) → 警告 + 通过           │
└──────────────────────────────────────────────────────────┘
        │
        ▼  (pass)
┌──────────────────────────────────────────────────────────┐
│ Step 10: Release to User                                  │
└──────────────────────────────────────────────────────────┘
        │
        ▼  (async)
┌──────────────────────────────────────────────────────────┐
│ Step 11: Critic Agent (async, 1-3s, cheap LLM)           │
│   - 检测 OOC / Hallucination / Stage Violation            │
│   - Failure → 写 drift event (→ SS01 Drift Detector)      │
│   - Pass → 写 audit log                                    │
└──────────────────────────────────────────────────────────┘
```

### 3.4 Reroll & Fallback 流程

```
[Anti-Pattern Filter 命中 hard_never]
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ Reroll Decision                                            │
│   - reroll_count < MAX_REROLL (=2): 继续                  │
│   - reroll_count >= MAX_REROLL: 进入 Fallback             │
└──────────────────────────────────────────────────────────┘
        │
        ▼
[Reroll Path]
   - 重新调用 LLM
   - 在 prompt 中追加 ANTI-DRIFT REINFORCE Block:
     "上一次回复违反了你的灵魂。请重试，并避免：
      {detected_patterns}"
   - reroll_count++
   - 重新走 Step 7-9

[Fallback Path]
   - 选择 Soul-flavored fallback response
   - 例:
     - Rin: "……让我想想。"
     - Dorothy: "诶嘿嘿，桃桃刚才走神啦~"
   - 立即释放，避免延迟
   - 写 incident audit log
   - 后续触发 spec_violation alert
```

### 3.5 Streaming-Compatible Anti-Pattern Filter

关键挑战: 一边流式输出，一边检测违规。

**策略**: **Trigram-based partial matcher**

```python
class StreamingAntiPatternFilter:
    """
    边收 chunk 边检测，对每个 chunk:
    1. 添加到 rolling buffer
    2. 检测当前 buffer 是否含 hard_never patterns (regex + AC)
    3. 命中 → 立即停止流，触发 reroll
    """
    
    def __init__(self, hard_never_patterns: List[str]):
        self.ac_automaton = build_aho_corasick(hard_never_patterns)
        self.rolling_buffer = ""
        self.max_pattern_length = max(len(p) for p in hard_never_patterns)
    
    def process_chunk(self, chunk: str) -> StreamResult:
        self.rolling_buffer += chunk
        
        # Keep buffer reasonable (但要保留够 max_pattern_length 字符)
        if len(self.rolling_buffer) > self.max_pattern_length + 100:
            self.rolling_buffer = self.rolling_buffer[-(self.max_pattern_length + 100):]
        
        # AC match
        matches = self.ac_automaton.match(self.rolling_buffer)
        if matches:
            return StreamResult(
                action="halt",
                violated_patterns=[m.pattern for m in matches],
                buffer_at_halt=self.rolling_buffer,
            )
        
        return StreamResult(action="continue")
```

### 3.6 Anti-Drift Injection Decision

```python
def decide_anchor_mode(
    activation_state: SoulActivationState,
    turn_index: int,
) -> AnchorMode:
    """
    决定本 turn 注入哪种 Anchor。
    """
    last_full = activation_state.last_full_anchor_turn
    last_light = activation_state.last_light_anchor_turn
    drift_score = activation_state.current_drift_score
    
    # 高 drift → 强制 REINFORCE
    if drift_score > 0.3:
        return AnchorMode.REINFORCE
    
    # 首 turn 或 too long since FULL → FULL
    if turn_index == 1:
        return AnchorMode.FULL
    if turn_index - last_full >= 8:
        return AnchorMode.FULL
    
    # 默认 LIGHT
    return AnchorMode.LIGHT
```

---

## 4. State Model

### 4.1 Per-Composition State (Transient)

```typescript
interface CompositionContext {
  trace_id: UUID
  user_id: UUID
  character_id: string
  turn_index: number
  modality: Modality
  
  // Inputs (referenced, not copied)
  soul_spec_ref: SoulSpecRef          // version + id
  activation_state_snapshot: SoulActivationState
  
  // Layer collection (mutable during composition)
  layers: PromptLayer[]
  
  // Budget tracking
  token_budget: number                 // configured cap
  token_used: number
  
  // Decisions
  anchor_mode: AnchorMode             // FULL / LIGHT / REINFORCE
  
  // Output
  composed_prompt: ComposedPrompt | null
  
  // Reroll state
  reroll_count: number
  reroll_history: RerollAttempt[]
  
  // Timing
  started_at: ISO8601
  layer_aggregation_ms: number
  composition_ms: number
}
```

### 4.2 Composition Trace (Persistent)

```typescript
// 写入 audit log, indexed for debugging
interface CompositionTrace {
  trace_id: UUID
  user_id: UUID
  character_id: string
  turn_id: UUID
  
  // Layer info
  layers_collected: Array<{
    layer_id: string
    source_subsystem: string
    priority: number
    cache_hit: boolean
    token_count: number
    compressed: boolean
    compression_ratio: number | null
    content_hash: string                // 用于 replay
  }>
  
  // Decisions
  anchor_mode: AnchorMode
  modality: Modality
  llm_model: string
  llm_params: object
  
  // Conflicts
  conflicts_resolved: Array<{
    layer_a: string
    layer_b: string
    resolution: string
    rule_applied: string
  }>
  
  // Outputs
  final_prompt_tokens: number
  llm_response_tokens: number
  llm_latency_ms: number
  
  // Quality
  anti_pattern_check_result: "pass" | "fail" | "reroll_succeeded"
  critic_result: "pass" | "ooc" | "hallucination" | "stage_violation" | null
  reroll_count: number
  
  // Timing breakdown
  timings: {
    aggregation_ms: number
    composition_ms: number
    llm_call_ms: number
    anti_pattern_filter_ms: number
    total_ms: number
  }
  
  created_at: ISO8601
}
```

### 4.3 Layer Cache State

```yaml
layer_cache:
  
  soul_anchor_cache:
    keyed_by: (character_id, soul_spec_version, anchor_mode)
    ttl: forever (invalidate on spec deploy)
    expected_hit_rate: > 99%
    
    note: |
      Anchor FULL/LIGHT 模板可预编译。
      LIGHT 模板因 (style snapshot) 略变，但仍可 cache 30s。
  
  activation_state_cache:
    keyed_by: (user_id, character_id)
    ttl: 1h (read-after-write through)
    expected_hit_rate: > 95%
  
  l4_identity_cache:
    keyed_by: (user_id, character_id)
    ttl: 24h
    expected_hit_rate: > 95%
    invalidation: on l4_promoted event
  
  emotion_state_cache:
    keyed_by: (user_id, character_id)
    ttl: 30s (fast-changing)
    expected_hit_rate: > 80%
  
  relationship_state_cache:
    keyed_by: (user_id, character_id)
    ttl: 5min (medium-changing)
    expected_hit_rate: > 90%
  
  memory_retrieval_cache:
    keyed_by: (user_id, character_id, query_hash)
    ttl: 60s
    expected_hit_rate: > 60%
```

---

## 5. 数据结构（Data Structures）

### 5.1 PromptLayer 基类

```typescript
interface PromptLayer {
  // ─── Identity ───
  layer_id: string                     // unique within composition
  source_subsystem: SubsystemId
  layer_type: LayerType
  
  // ─── Priority & Position ───
  priority: number                     // 1 (highest) - 100 (lowest)
  position_constraint: "first" | "anywhere" | "last"
  
  // ─── Content ───
  content: string                      // 实际注入 prompt 的文本
  
  // ─── Token Management ───
  token_count_estimate: number
  min_token_count: number              // 压缩下限
  is_compressible: boolean
  
  // ─── Compression Hooks ───
  compress?: (target_tokens: number) => PromptLayer
  
  // ─── Validation ───
  validate?: () => ValidationResult
  
  // ─── Metadata ───
  generated_at: ISO8601
  cache_key: string | null
  content_hash: string                 // sha256 for trace
  
  // ─── Conflict Resolution Hints ───
  conflicts_with: Array<{
    other_layer_type: LayerType
    resolution: "wins" | "loses" | "merge"
    rule_id: string
  }>
}

type LayerType =
  | "anchor_full"
  | "anchor_light"
  | "anchor_reinforce"
  | "safety"
  | "modality_adaptation"
  | "relationship_context"
  | "emotion_context"
  | "inner_state"
  | "memory_context"
  | "scene_context"
  | "conversation_history"
  | "user_message"
  | "response_directive"

type SubsystemId = "SS01" | "SS02" | "SS03" | "SS04" | "SS06" | "SS07"
```

### 5.2 Layer Priorities

```yaml
layer_priorities:
  # 数值越小，优先级越高，越靠前注入
  
  anchor_full: 1
  anchor_light: 1
  anchor_reinforce: 1
  safety: 5
  modality_adaptation: 10
  relationship_context: 20
  emotion_context: 25
  inner_state: 30
  memory_context: 35
  scene_context: 40
  conversation_history: 50
  user_message: 90
  response_directive: 95
```

### 5.3 Token Budget Configuration

```yaml
token_budget:
  
  # 取决于使用的 LLM
  claude_sonnet_4_6:
    max_context: 200000
    target_prompt_budget: 8000     # 留充足空间给 history + response
  
  deepseek_v3:
    max_context: 128000
    target_prompt_budget: 8000
  
  companion_llm_v2:
    max_context: 32000
    target_prompt_budget: 4000     # 微调后 prompt 可短
  
  # Per-layer allocation (target, not hard cap)
  per_layer_targets:
    anchor_full: 800
    anchor_light: 80
    anchor_reinforce: 400
    safety: 100
    modality_adaptation: 150
    relationship_context: 500
    emotion_context: 400
    inner_state: 400
    memory_context: 1200
    scene_context: 200
    conversation_history: 3000
    user_message: 500
    response_directive: 100
  
  per_layer_minimums:
    anchor_full: 400              # 不能压到这以下
    anchor_light: 80              # 已经最短
    anchor_reinforce: 300
    safety: 50
    relationship_context: 200
    emotion_context: 150
    inner_state: 100
    memory_context: 300           # 至少塞下 L4
    conversation_history: 500
    user_message: 100              # 用户消息不能压（必要时截断）
    response_directive: 50
```

### 5.4 ComposedPrompt（最终输出）

```typescript
interface ComposedPrompt {
  trace_id: UUID
  composed_at: ISO8601
  
  // ─── Final Prompt ───
  prompt_text: string
  total_tokens: number
  
  // ─── Layer Inclusion ───
  layers_included: LayerInclusion[]
  
  // ─── LLM Call Configuration ───
  llm_call_params: {
    model: string                     // "claude-sonnet-4-6" / "deepseek-v3" / "companion-llm-v2"
    temperature: number               // 由 modality + emotion 决定
    max_tokens: number                // 输出长度上限
    top_p: number
    stop_sequences: string[]
    stream: boolean
  }
  
  // ─── Modality ───
  modality: Modality
  modality_directives: ModalityDirectives
  
  // ─── Post-Processing Hooks ───
  anti_pattern_filters: {
    hard_never_patterns: string[]
    soft_never_patterns: string[]   // stage-gated
    streaming_buffer_size: number
  }
  
  critic_validation_checks: {
    check_ooc: boolean
    check_hallucination: boolean      // 参照 SS02 L4
    check_stage_violation: boolean
    cheap_model_for_critic: string
  }
  
  // ─── Trace ───
  composition_trace: CompositionTrace
}

interface LayerInclusion {
  layer_id: string
  source_subsystem: SubsystemId
  start_offset: number               // in prompt_text
  end_offset: number
  token_count: number
}

interface ModalityDirectives {
  // ─── Text ───
  text: {
    // No special directives
  } | null
  
  // ─── Voice ───
  voice: {
    target_response_length: "short" | "medium"
    prosody_hints: {
      pitch_modifier: number          // -1 (低) to +1 (高)
      pace_modifier: number           // -1 (慢) to +1 (快)
      breathiness: number             // 0 to 1
      pause_pattern_emphasis: number  // 0 to 1
    }
    must_be_speakable: true          // 不允许 markdown / 列表
  } | null
  
  // ─── Video ───
  video: {
    target_response_length: "very_short" | "short"
    expression_slot: string           // 显式 JSON 输出格式
    action_slot: string
    require_action_json: true
    valid_expressions: string[]
    valid_actions: string[]
  } | null
}

type Modality = "text" | "voice" | "video"
```

### 5.5 LLM Call Parameter Selection

```yaml
# 根据 modality + emotion + relationship 选择参数

llm_param_selection:
  
  base_params:
    model: claude-sonnet-4-6  # 默认强模型
    temperature: 0.7
    top_p: 0.95
    max_tokens: 300
    stream: true
  
  modality_overrides:
    text:
      max_tokens: 300
      temperature: 0.7
    
    voice:
      max_tokens: 150          # 语音回复较短
      temperature: 0.65        # 略低，更稳定
      stop_sequences: ["\n\n"]  # 避免长段落
    
    video:
      max_tokens: 80           # 视频回复极短
      temperature: 0.6
      stop_sequences: ["\n\n"]
  
  emotion_modifiers:
    when_calm: 
      temperature: 0.7
    when_high_arousal: 
      temperature: 0.75        # 稍高，增加表达多样性
    when_cold_war: 
      temperature: 0.6         # 稍低，更可控
      max_tokens: 100          # 限制长度
    when_excited: 
      temperature: 0.75
  
  stage_modifiers:
    when_stranger:
      max_tokens: 80
    when_bonded:
      max_tokens: 350
```

### 5.6 Anti-Pattern Configuration

```typescript
interface AntiPatternConfig {
  character_id: string
  spec_version: string
  
  // Hard patterns (from Soul.anti_patterns.hard_never)
  hard_never_patterns: Array<{
    pattern: string                  // regex 或 literal
    pattern_type: "literal" | "regex" | "trigram"
    severity: "always_reroll" | "warn"
    examples: string[]
  }>
  
  // Soft patterns (stage-gated)
  soft_never_patterns: Array<{
    pattern: string
    pattern_type: "literal" | "regex"
    gated_until_stage: RelationshipStage  // 在此 stage 前禁止
    examples: string[]
  }>
  
  // Compiled (in-memory)
  ac_automaton: AhoCorasick           // 启动时编译
  regex_compiled: Pattern[]
}
```

### 5.7 Critic Agent 输入输出

```typescript
interface CriticInput {
  turn_id: UUID
  user_message: string
  assistant_response: string
  
  // Context (供 critic 判断)
  current_stage: RelationshipStage
  active_emotions: Array<{emotion: string, intensity: number}>
  l4_facts: IdentityMemory[]          // 用于 hallucination check
  soul_voice_dna: VoiceDNAItem[]
  soul_anti_patterns: AntiPatternConfig
  
  // What to check
  checks_to_perform: Array<"ooc" | "hallucination" | "stage_violation">
}

interface CriticOutput {
  passed: boolean
  failures: Array<{
    check_type: string
    severity: "low" | "medium" | "high"
    evidence: string                  // quote 违规处
    suggested_correction: string
  }>
  
  drift_score_contribution: number    // 写回 SS01 Drift Detector
  
  // Metadata
  critic_model: string
  critic_latency_ms: number
  critic_cost_estimate: number
}
```

---

## 6. Prompt Runtime Integration

### 6.1 最终 Prompt 结构 (Canonical)

```
═══════════════════════════════════════════════════════════
[AnchorBlock - SS01]
═══════════════════════════════════════════════════════════

[Safety Layer]
  - 当前 safety 等级提示
  - 特殊用户 flag

[Modality Adaptation Layer]
  - 例 (voice): 你正在语音通话中，回复需要简短、自然，使用口语表达。
  - 例 (video): 你正在视频通话中，回复 ≤ 30 字，并以 JSON 格式输出动作和表情。

[Relationship Context Block - SS04]
  - Stage 描述（自然语言）
  - Trust / Attachment descriptor
  - Behavioral envelope

[Emotion Context Block - SS03]
  - 当前情绪状态（不直接说标签）
  - Mood / Energy
  - 表达指引

[Inner State Layer - SS06]
  - 角色当前内心活动
  - 她"今天"的状态

[Memory Context Block - SS02]
  - L4 identity 层（永远清晰）
  - Recent episodes (state-aware reconstruction)
  - Active facts
  - Optional forgetting hints

[Scene Context Layer]
  - 当前时间
  - 检测到的环境（如 voice 通话中的背景音）
  - 上次互动距今

[Conversation History]
  - 最近 N turns (token budget 允许下)
  - 标注 critic OOC turns (供 LLM 避开)

[User Message]
  ▼ 用户当前消息

[Response Directive]
  - 角色 ID + 简短引导
  - 例: "{character_id} 的回复:"
═══════════════════════════════════════════════════════════
```

### 6.2 Composition 流程伪代码

```python
class PersonaComposer:
    
    async def compose(
        self,
        user_id: UUID,
        character_id: str,
        user_message: str,
        turn_id: UUID,
        modality: Modality = "text",
    ) -> ComposedPrompt:
        
        ctx = CompositionContext(
            trace_id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            turn_index=await self.get_turn_index(user_id, character_id),
            modality=modality,
            ...
        )
        
        # Step 1: Layer Aggregator (parallel)
        layers = await self._aggregate_layers(ctx, user_message)
        ctx.layers = layers
        ctx.layer_aggregation_ms = elapsed()
        
        # Step 2: Conflict Resolver
        layers = self._resolve_conflicts(layers)
        
        # Step 3: Anti-Drift Injector
        anchor_mode = self._decide_anchor_mode(ctx)
        layers = self._apply_anchor_mode(layers, anchor_mode)
        ctx.anchor_mode = anchor_mode
        
        # Step 4: Token Budget Allocator
        layers = self._allocate_budget(layers, ctx.token_budget)
        
        # Step 5: Modality Adapter
        layers, modality_directives = self._modality_adapt(layers, modality)
        
        # Step 6: Composer
        composed = self._compose(layers, modality_directives, ctx)
        
        return composed
    
    async def _aggregate_layers(
        self, ctx: CompositionContext, user_message: str
    ) -> List[PromptLayer]:
        
        # Parallel I/O bound
        layers = await asyncio.gather(
            self.ss01.get_anchor_block(ctx),
            self.safety.get_safety_layer(ctx, user_message),
            self.ss02.get_memory_context_block(ctx, user_message),
            self.ss03.get_emotion_context_block(ctx),
            self.ss04.get_relationship_context_block(ctx),
            self.ss06.get_inner_state_block(ctx),
            self.scene_detector.get_scene_block(ctx),
            self.history_provider.get_conversation_history(ctx),
        )
        
        # Add user_message layer
        layers.append(self._build_user_message_layer(user_message))
        
        # Add response directive layer
        layers.append(self._build_response_directive_layer(ctx.character_id))
        
        return layers
    
    def _resolve_conflicts(self, layers: List[PromptLayer]) -> List[PromptLayer]:
        # Apply Conflict Resolution Matrix (§6.4)
        resolved = []
        for layer in layers:
            modified = self._apply_conflict_rules(layer, layers)
            if modified is not None:
                resolved.append(modified)
        return resolved
    
    def _allocate_budget(
        self, layers: List[PromptLayer], total_budget: int
    ) -> List[PromptLayer]:
        
        layers_sorted = sorted(layers, key=lambda L: L.priority)
        total_estimated = sum(L.token_count_estimate for L in layers)
        
        if total_estimated <= total_budget:
            return layers  # 无需压缩
        
        # 按优先级倒序压缩 (低优先级先压缩)
        budget_remaining = total_budget
        for L in layers_sorted:
            target = L.token_count_estimate
            if total_estimated > budget_remaining:
                # Try to compress this layer
                overflow = total_estimated - budget_remaining
                target = max(L.min_token_count, L.token_count_estimate - overflow)
                if L.is_compressible and L.compress:
                    L = L.compress(target)
                total_estimated = sum(LL.token_count_estimate for LL in layers_sorted)
            
            budget_remaining -= L.token_count_estimate
        
        return layers_sorted
    
    def _compose(
        self,
        layers: List[PromptLayer],
        modality_directives: ModalityDirectives,
        ctx: CompositionContext,
    ) -> ComposedPrompt:
        
        # 按优先级 + position_constraint 排序
        ordered = self._order_layers(layers)
        
        # 物理拼接
        parts = [self._format_layer(L) for L in ordered]
        prompt_text = "\n\n".join(parts)
        
        return ComposedPrompt(
            trace_id=ctx.trace_id,
            prompt_text=prompt_text,
            total_tokens=self._count_tokens(prompt_text),
            layers_included=[...],
            llm_call_params=self._select_llm_params(ctx, modality_directives),
            modality=ctx.modality,
            modality_directives=modality_directives,
            anti_pattern_filters=self._build_anti_pattern_filters(ctx),
            critic_validation_checks=self._build_critic_checks(ctx),
            composition_trace=self._build_trace(ctx),
        )
```

### 6.3 Layer Formatting Convention

```python
def _format_layer(layer: PromptLayer) -> str:
    """
    每个 layer 用统一格式注入。
    """
    if layer.layer_type == "anchor_full":
        # Anchor 不加 separator (它自己有 ═══ box)
        return layer.content
    
    if layer.layer_type == "user_message":
        return f"用户：{layer.content}"
    
    if layer.layer_type == "response_directive":
        return f"{layer.content}"  # 例: "凛的回复:"
    
    # 默认：单独段落
    return layer.content
```

### 6.4 Conflict Resolution Matrix（精确）

```yaml
conflict_resolution_matrix:
  # 当两个 layer 给出冲突指导时，规则化解决
  
  - id: CR-1
    case: "Memory 想召回 deep memory, Stage = STRANGER"
    resolution: "Memory layer 中过滤掉 stage-gated memory"
    winner: Stage Block
    rule: "Stage envelope 决定 memory 可见性"
  
  - id: CR-2
    case: "Emotion = 心动, Stage < ROMANTIC_INTEREST"
    resolution: "Emotion Block 改写 fluttered → tenderness"
    winner: Stage Block
  
  - id: CR-3
    case: "Inner State 想推主动撒娇, Soul.hard_never 含撒娇"
    resolution: "Inner State 中删除该建议"
    winner: Soul Anchor
  
  - id: CR-4
    case: "Memory recall 与 L4 内容矛盾"
    resolution: "L4 写入 Memory Block；矛盾 L3 标记 contradicted"
    winner: L4 (within Memory)
  
  - id: CR-5
    case: "Memory 建议长回复, Cognitive Style max = short"
    resolution: "Memory 输出被压缩为多个 short fragment"
    winner: Cognitive Style (Soul)
  
  - id: CR-6
    case: "Emotion 想愤怒爆发, Soul.shock_resistance = high"
    resolution: "Emotion 中 anger → coldness (Subsystem 03 已处理)"
    note: "Composition 层只需信任 Emotion 已经解决"
  
  - id: CR-7
    case: "Relationship behavioral_envelope 不允许 jealousy, Emotion 包含 jealousy"
    resolution: "Emotion Block 中将 jealousy → aggrieved + worry"
    winner: Relationship
  
  - id: CR-8
    case: "Modality voice 需要短回复, Memory Block 较长"
    resolution: "Memory Block 强制压缩到 voice budget"
    winner: Modality
  
  - id: CR-9
    case: "Safety 等级 = ORANGE, Inner State 包含浪漫"
    resolution: "Inner State 中浪漫元素被替换为中性"
    winner: Safety
  
  - id: CR-10
    case: "Scene = office hours, Inner State 包含深度倾诉"
    resolution: "Inner State 压低强度"
    winner: Scene Context
```

### 6.5 Modality Adaptation 具体规则

```yaml
modality_adaptations:
  
  text:
    response_max_length: 200
    response_target_length: 50
    history_turns_included: 20
    allow_markdown: false   # AI Companion 不用 markdown
    allow_bullet_list: false
    style: "messaging"
  
  voice:
    response_max_length: 150
    response_target_length: 30
    history_turns_included: 10  # 语音 context 短
    allow_markdown: false
    allow_bullet_list: false
    must_be_speakable: true
    prompt_directive: |
      你正在语音通话中。
      回复必须:
      - 简短自然 (10-30 字)
      - 口语化，不用书面语
      - 不用列表、不用标题
      - 适合朗读的连贯句子
    prosody_directives:
      # 由 Emotion State 派生
      pitch_modifier: f(emotion.valence)
      pace_modifier: f(emotion.arousal, energy)
      breathiness: f(emotion.tenderness, vulnerability_score)
      pause_pattern: f(soul.voice_dna.ellipsis_usage)
  
  video:
    response_max_length: 80
    response_target_length: 20
    history_turns_included: 5
    require_json_output: true
    prompt_directive: |
      你正在视频通话中。
      回复必须以严格 JSON 格式输出:
      {
        "text": "你说的话 (≤ 30 字)",
        "action": "动作 ID (来自允许列表)",
        "expression": "表情 ID (来自允许列表)"
      }
      
      允许的 actions: {valid_actions}
      允许的 expressions: {valid_expressions}
    
    valid_expressions:
      # 由角色 + 当前 emotion 决定
      rin: [calm, contemplative, shy, tsundere, surprised, suspicious]
      dorothy: [happy, shy, surprised, pouting, sleepy, mischievous]
    
    valid_actions:
      rin: [arm_cross, side_glance, hair_touch, look_away, slight_nod]
      dorothy: [tilt_head, finger_to_chin, sway, eye_widen, peek]
```

---

## 7. Agent Integration

### 7.1 读取者

| Agent / Subsystem | 读取 | 用途 |
|-------------------|------|------|
| **API Endpoint Handler** | ComposedPrompt | 发送给 LLM |
| **Streaming Output Handler** | anti_pattern_filters | 流式过滤 |
| **Modality Renderers** | modality_directives | 语音/视频适配 |
| **Observability** | composition_trace | 监控 + debug |

### 7.2 写入者

**Composition 是无状态的纯函数**，但其 trace 会写入 audit log。

| Service | 写入路径 | 写入字段 |
|---------|---------|---------|
| **Composer** | → composition_traces table (async) | trace 字段 |
| **Anti-Pattern Filter** | → anti_pattern_violations (async) | 命中事件 |
| **Critic Agent** | → SS01 Drift Detector | drift event |
| **Reroll Handler** | → reroll_audit (async) | 重试事件 |

### 7.3 调用顺序（精确时序）

```
T = 0ms      [Trigger: user_message arrives]
T = 1ms      [API endpoint → PersonaComposer.compose()]
T = 2ms      [Composer: gather context (user_id, character_id, ...)]

T = 5ms      [Layer Aggregator: parallel gather]
             ├─ SS01.get_anchor_block: 5ms (cached, anchor_mode TBD)
             ├─ SS02.get_memory_context_block: 200ms (retrieval)
             ├─ SS03.get_emotion_context_block: 10ms
             ├─ SS04.get_relationship_context_block: 10ms
             ├─ SS06.get_inner_state_block: 5ms (cached)
             ├─ Scene Detector: 5ms
             └─ History Provider: 5ms
             
T = 205ms    [All layers ready]  ← bottleneck: SS02 retrieval

T = 210ms    [Conflict Resolver]
T = 211ms    [Anti-Drift Injector: decide_anchor_mode]
T = 212ms    [Token Budget Allocator + compression]
T = 222ms    [Modality Adapter]
T = 227ms    [Composer: assemble prompt]
T = 237ms    [Trace built]

T = 240ms    [LLM call begins, streaming]
T = 240-2500ms [Streaming chunks with pre-filter]

T = 2500ms   [Stream complete, full response]
T = 2520ms   [Full anti-pattern filter]
             - If hit: reroll OR fallback
T = 2540ms   [Release to user]

Async:
T = +0ms     [Composition Trace persisted]
T = +500ms   [Critic Agent (cheap LLM)]
T = +2s      [Critic result → SS01 Drift Detector]
```

### 7.4 权限边界

```yaml
permissions:
  
  composer:
    read: all subsystem blocks (read-only API)
    write: composition_traces (audit), reroll_audit
  
  anti_pattern_filter:
    read: AntiPatternConfig (from Soul Spec)
    write: anti_pattern_violations audit, reroll trigger
  
  critic_agent:
    read: turn data + context blocks
    write: SS01 drift event, critic_audit
  
  modality_adapter:
    read: emotion, energy, soul.voice_dna
    write: nothing (pure function)
```

### 7.5 跨 Subsystem 接口

```
[SS05 ← SS01]
  reads:
    - get_anchor_block(activation_state, anchor_mode) → AnchorBlock
    - get_anti_pattern_config() → AntiPatternConfig
  invalidation:
    - 部署新 Soul Spec → 失效 anchor cache

[SS05 ← SS02]
  reads:
    - get_memory_context_block(turn_context) → MemoryContextBlock
  latency:
    - P95 < 300ms (bottleneck)

[SS05 ← SS03]
  reads:
    - get_emotion_context_block(user_id, character_id) → EmotionContextBlock
  latency: P95 < 30ms

[SS05 ← SS04]
  reads:
    - get_relationship_context_block(user_id, character_id) → RelationshipContextBlock
    - get_behavioral_envelope() → BehavioralEnvelope
  latency: P95 < 30ms

[SS05 ← SS06]
  reads:
    - get_inner_state_block(user_id, character_id) → InnerStateBlock
  latency: P95 < 20ms

[SS05 → SS01]
  emits:
    - turn_completed event (with drift_score from critic)
    - anti_pattern_violation event
  via: event bus

[SS05 → SS07 Orchestration]
  exposes:
    - compose(turn_context) → ComposedPrompt
    - call_main_llm(composed_prompt) → AsyncIterator<chunk>
    - validate_response(response) → ValidationResult
```

---

## 8. Emotional Realism Constraints

### 8.1 沉浸感铁律

| ID | 规则 | 实现 |
|----|------|------|
| **PCR-1** | 用户绝不应感知到 composition / reroll | Streaming pre-filter; fallback 无缝 |
| **PCR-2** | Anchor re-injection 不能突兀 | Anchor 内容融入自然 (不暴露 "reset" 语义) |
| **PCR-3** | Anti-pattern fallback 必须 Soul-flavored | 角色化 fallback 库 |
| **PCR-4** | Modality 切换时 persona 连续 | Inner State 单点真相 |
| **PCR-5** | Critic 验证失败时角色不"道歉" | 修正在后台进行 |
| **PCR-6** | 不让 LLM 决定 prompt 结构 | 完全 deterministic composition |
| **PCR-7** | Token 压缩不破坏关键 fact | min_token_count 保护 |
| **PCR-8** | Streaming 不重试已发送内容 | Halt + Reroll 从头 |

### 8.2 Reroll 的沉浸感设计

```
情况 1: Streaming 中触发 (检测到 hard_never)
   - 立刻停止 streaming
   - 用户看到的只是几个字 → 立即被覆盖? NO!
   - 实际方案: 设置一个 streaming buffer，先 buffer 50-100 字符再 release
     给 anti-pattern filter 至少 1-2 个 chunk 的检测时间
   - 如果 buffer 内检测到违规 → 完全不释放，从头 reroll
   - 用户只感受到"她响应稍慢了一点"

情况 2: Full response 后检测到 (罕见)
   - 这种情况不应发生（streaming 应该已经拦截）
   - Fallback: 释放 reroll 后的版本
   - 用户感受到更慢
```

### 8.3 Anti-Drift 注入的沉浸感

```
Anchor REINFORCE 注入时：
   - 在 prompt 中是给 LLM 看的
   - LLM 的输出**不会**显式 reference Anchor
   - 用户只感受到"她回到了她自己"

注意:
   - 永远不让 LLM 在响应中说"让我重新校准我的人格" (绝对禁止)
   - 永远不让 LLM 说 "我刚才偏离了" 
   - 这些 anchor 内容只在 prompt 中存在，不在 output 中显露
```

### 8.4 Critic Agent 的沉浸感

```
Critic 异步运行，不阻塞用户体验。

Critic 失败时:
   - 该 turn 已经发送 (没法收回)
   - 写 drift event → 影响下次 anchor 注入
   - 下一轮会更强 anchor → 自然修正
   - 用户感受到"她下一句又变回她了"
```

---

## 9. Failure Cases

### 9.1 架构崩坏风险

| 风险 | 触发 | 缓解 |
|------|------|------|
| **Layer Aggregator 部分超时** | SS02 retrieval 慢 | Timeout + fallback: 没拿到的 layer 用 empty placeholder |
| **Token budget 算错** | Tokenizer 不准 | 留 10% buffer + 监控实际 vs 估算 |
| **Compression 破坏关键 fact** | min_token_count 设错 | Compression 函数必须保留 L4 + Anchor |
| **Anti-Pattern Filter 误判** | Pattern 太广 | Pattern review process + low false-positive rate target |
| **Reroll 无限循环** | Bug | MAX_REROLL=2，超过强制 fallback |
| **Streaming pre-filter 漏 violation** | Pattern 跨 chunk | Rolling buffer 保留 max_pattern_length 字符 |
| **Composition Trace 写入失败** | DB 故障 | Best-effort async write，不阻塞主流程 |

### 9.2 Runtime 性能风险

| 风险 | 缓解 |
|------|------|
| Layer Aggregator parallel I/O 阻塞 | Strict timeout per subsystem (200ms total) |
| LLM 调用延迟 | Streaming 缓解首字延迟 |
| Composition 内存 spike | Layer object 池化 |
| Anti-Pattern Filter 慢 | Aho-Corasick 预编译；< 10ms |
| Critic Agent 串行成本 | 异步 + cheap model + 概率采样 (10% turns) |

### 9.3 质量风险

| 风险 | 缓解 |
|------|------|
| Conflict Resolution 漏 case | Matrix 持续扩充 + golden tests |
| Reroll 仍然违规 | Fallback canned response (always available) |
| Critic 误判 OOC | Critic confidence threshold + 人工 review |
| Token compression 破坏语义 | LLM-based smart compression for important layers (V2) |
| Modality directives 与 LLM 输出不符 | Strict JSON schema validation for video |

### 9.4 长期维护风险

| 风险 | 缓解 |
|------|------|
| Layer 数量增加 (新 subsystem) | Priority + budget 矩阵需要扩充 |
| Token budget 变化 (新模型) | Config 化，无需代码改 |
| Anti-pattern 列表膨胀 | 按 character 分隔，独立维护 |
| Composition 逻辑复杂化 | 严格 test coverage，trace 可 replay |

### 9.5 用户体验失败

| 风险 | 缓解 |
|------|------|
| 用户看到 "正在重试..." | Streaming buffer + 透明 reroll |
| 响应明显比同行慢 | 全链路 P95 < 3s; LLM bottleneck |
| Modality 切换响应风格突变 | Inner State 单点 + golden 跨模态 test |
| Fallback response 太机械 | Soul-flavored fallback 库 |

---

## 10. Engineering Guidance

### 10.1 推荐技术栈

```yaml
runtime:
  language: Python 3.11+ (FastAPI / asyncio)
  
  llm_clients:
    main: Anthropic SDK (Claude Sonnet 4.6)
    cheap: DeepSeek SDK / OpenRouter (DeepSeek V3 / Haiku 4.5)
  
  tokenizer:
    primary: tiktoken (for OpenAI-compatible)
    claude: anthropic.tokenize
  
  string_matching:
    aho_corasick: pyahocorasick
    regex: re (compiled)
  
  caching:
    in_process: cachetools / functools.lru_cache
    distributed: Redis
  
  observability:
    metrics: Prometheus
    traces: OpenTelemetry
    logs: structlog

storage:
  composition_traces:
    primary: PostgreSQL (partitioned monthly)
    retention: 30 days hot, 365 days warm, archive afterward
  
  anti_pattern_violations:
    primary: PostgreSQL append-only
    indexed: (character_id, pattern_id, created_at)
  
  reroll_audit:
    primary: PostgreSQL append-only
```

### 10.2 Persona Composer Service 接口

```python
class PersonaComposerService:
    """
    主入口 service.
    """
    
    async def compose(
        self,
        user_id: UUID,
        character_id: str,
        user_message: str,
        turn_id: UUID,
        modality: Modality = "text",
    ) -> ComposedPrompt: ...
    
    async def call_main_llm(
        self,
        composed: ComposedPrompt,
    ) -> AsyncIterator[StreamingChunk]:
        """流式调用主 LLM, 在每 chunk 中应用 streaming pre-filter."""
    
    async def validate_response(
        self,
        composed: ComposedPrompt,
        full_response: str,
    ) -> ValidationResult: ...
    
    async def handle_reroll(
        self,
        composed: ComposedPrompt,
        previous_attempt: str,
        violation: ViolationReport,
    ) -> AsyncIterator[StreamingChunk]: ...
    
    def get_fallback_response(
        self,
        character_id: str,
        context: CompositionContext,
    ) -> str:
        """Soul-flavored fallback."""
```

### 10.3 Layer Aggregator 实现

```python
class LayerAggregator:
    
    async def aggregate(
        self,
        ctx: CompositionContext,
        user_message: str,
    ) -> List[PromptLayer]:
        
        # 并行调用，严格 timeout
        async with asyncio.timeout(LAYER_AGGREGATION_TIMEOUT):
            results = await asyncio.gather(
                self._with_fallback(self.ss01.get_anchor_block(ctx), self._empty_anchor),
                self._with_fallback(self.safety.get_safety_layer(ctx), self._empty_safety),
                self._with_fallback(self.ss02.get_memory_context_block(ctx), self._empty_memory),
                self._with_fallback(self.ss03.get_emotion_context_block(ctx), self._empty_emotion),
                self._with_fallback(self.ss04.get_relationship_context_block(ctx), self._empty_rel),
                self._with_fallback(self.ss06.get_inner_state_block(ctx), self._empty_inner),
                self._with_fallback(self.scene.get_scene_block(ctx), self._empty_scene),
                self._with_fallback(self.history.get_history(ctx), self._empty_history),
                return_exceptions=False,
            )
        
        layers = list(results)
        layers.append(self._build_user_message_layer(user_message))
        layers.append(self._build_response_directive_layer(ctx.character_id))
        
        return layers
    
    async def _with_fallback(self, awaitable, fallback_factory):
        try:
            return await awaitable
        except Exception as e:
            log.warning("Layer fetch failed", error=e)
            return fallback_factory()
```

### 10.4 Streaming Pre-Filter Buffer

```python
class StreamingResponseHandler:
    
    BUFFER_SIZE = 50  # 字符
    
    async def stream_with_filter(
        self,
        llm_stream: AsyncIterator[str],
        filter: StreamingAntiPatternFilter,
        on_violation: Callable,
    ) -> AsyncIterator[str]:
        
        buffer = ""
        released = ""
        
        async for chunk in llm_stream:
            buffer += chunk
            
            # Check buffer
            result = filter.process_chunk(chunk)
            if result.action == "halt":
                # Don't release anything, trigger reroll
                await on_violation(result)
                return
            
            # Release safe portion (keep BUFFER_SIZE in buffer for late detection)
            while len(buffer) > self.BUFFER_SIZE:
                char = buffer[0]
                buffer = buffer[1:]
                released += char
                yield char
        
        # Stream complete, release rest
        yield buffer
```

### 10.5 Token Counting 准确性

```python
class TokenCounter:
    """
    估算 + 实际两种模式。
    """
    
    def estimate(self, text: str, model: str = "claude") -> int:
        """
        Fast estimation (heuristic):
        - 中文: 1 char ≈ 1.5 tokens
        - 英文: 1 word ≈ 1.3 tokens
        """
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        non_chinese = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + non_chinese * 0.3)
    
    def exact(self, text: str, model: str) -> int:
        """
        Exact count via tokenizer. 较慢。
        """
        if model.startswith("claude"):
            return anthropic.count_tokens(text)
        elif model in ["gpt-4", "gpt-4o"]:
            return tiktoken.encoding_for_model(model).encode(text).__len__()
        # ...
```

### 10.6 Compression Strategy

```python
class LayerCompressor:
    """
    不同 layer 不同压缩策略。
    """
    
    def compress(self, layer: PromptLayer, target_tokens: int) -> PromptLayer:
        if layer.layer_type == "memory_context":
            return self._compress_memory(layer, target_tokens)
        if layer.layer_type == "conversation_history":
            return self._compress_history(layer, target_tokens)
        if layer.layer_type == "relationship_context":
            return self._compress_relationship(layer, target_tokens)
        # ... per-type strategies
        return layer  # 不可压缩
    
    def _compress_memory(self, layer, target):
        """
        策略:
        - 保留 L4 identity (永不压缩)
        - 压缩 episodes summary (减少数量)
        - 移除 forgetting hints (低优先)
        """
        ...
    
    def _compress_history(self, layer, target):
        """
        策略:
        - 保留最近 N turns 完整
        - 中间 turns 用 LLM summary (V2) 或简单 truncate (V1)
        - 第一 turn 保留 (设定关键)
        """
        ...
```

### 10.7 Anti-Pattern Filter 实现

```python
class AntiPatternFilter:
    """
    Sync, full-message filter.
    """
    
    def __init__(self, config: AntiPatternConfig):
        self.config = config
        self.ac_hard = self._build_ac([p.pattern for p in config.hard_never_patterns
                                        if p.pattern_type == "literal"])
        self.regex_hard = [re.compile(p.pattern) for p in config.hard_never_patterns
                            if p.pattern_type == "regex"]
        # Soft patterns... per stage
    
    def filter(self, response: str, stage: RelationshipStage) -> FilterResult:
        # Hard checks (always)
        ac_matches = self.ac_hard.match(response)
        if ac_matches:
            return FilterResult(
                action="reroll",
                violated_patterns=ac_matches,
                severity="hard",
            )
        
        for regex in self.regex_hard:
            match = regex.search(response)
            if match:
                return FilterResult(
                    action="reroll",
                    violated_patterns=[match.group()],
                    severity="hard",
                )
        
        # Soft checks (stage-gated)
        for p in self.config.soft_never_patterns:
            if STAGE_ORDER[stage] < STAGE_ORDER[p.gated_until_stage]:
                if self._pattern_matches(p, response):
                    return FilterResult(
                        action="warn",  # 不 reroll，但记录
                        violated_patterns=[p.pattern],
                        severity="soft",
                    )
        
        return FilterResult(action="pass")
```

### 10.8 Critic Agent 实现

```python
class CriticAgent:
    """
    异步 OOC / Hallucination / Stage 检测。
    """
    
    SAMPLING_RATE = 0.30  # 30% turns 走 critic (成本控制)
    
    async def evaluate(
        self,
        input: CriticInput,
    ) -> CriticOutput:
        
        if not self._should_sample(input):
            return CriticOutput(passed=True, failures=[])  # 默认通过
        
        prompt = CRITIC_PROMPT.format(
            user_message=input.user_message,
            assistant_response=input.assistant_response,
            voice_dna=input.soul_voice_dna,
            stage=input.current_stage,
            l4_facts=input.l4_facts,
            checks=input.checks_to_perform,
        )
        
        result = await self.cheap_llm.call(
            prompt=prompt,
            model="haiku-4-5",
            json_mode=True,
            timeout=3.0,
        )
        
        parsed = self._parse_critic_output(result)
        
        if not parsed.passed:
            # Emit drift event to SS01
            await self.event_bus.emit("soul.drift.detected", {
                "user_id": input.user_id,
                "character_id": input.character_id,
                "drift_score": parsed.drift_score_contribution,
                "evidence": parsed.failures,
            })
        
        return parsed
```

### 10.9 性能预算

```yaml
performance_targets:
  
  layer_aggregation:
    p50: 80ms
    p95: 200ms
    p99: 300ms
    timeout: 500ms (hard)
  
  composition (excluding LLM):
    p50: 100ms
    p95: 250ms
    p99: 400ms
  
  llm_call:
    first_byte_p95: 2s
    full_response_p95: 4s (300 tokens)
  
  anti_pattern_filter:
    p95: 10ms
    p99: 25ms
  
  critic_agent:
    p95: 2s (async, doesn't block)
    sampling: 30%

  end_to_end_user_perceived:
    first_byte_p95: 2.5s
    full_response_p95: 4.5s

cost_per_MAU:
  composition (no LLM): $0
  main LLM (avg 1 call/turn): largest cost
  critic LLM (30% sampling): < $0.05/MAU
  storage: < $0.05/MAU
```

### 10.10 Observability

```yaml
metrics:
  # Layer
  - composition.layer.fetch_latency {subsystem}
  - composition.layer.cache_hit_rate {layer_type}
  - composition.layer.compressed_count {layer_type}
  
  # Composition
  - composition.total_tokens.histogram
  - composition.layer_count.histogram
  - composition.duration.p95
  - composition.conflict_resolved.count {rule_id}
  - composition.anchor_mode.count {mode}
  
  # LLM
  - llm.first_byte_latency {model, modality}
  - llm.full_response_latency
  - llm.tokens_used {direction: input|output}
  - llm.cost_per_turn
  
  # Filtering
  - anti_pattern.hit.count {pattern_id, severity}
  - anti_pattern.reroll.count
  - anti_pattern.fallback.count
  
  # Critic
  - critic.invoked.count
  - critic.failure_rate {check_type}
  - critic.drift_score.distribution

logs:
  - All reroll events (audit)
  - All fallback events (high priority)
  - Composition timeouts
  - Critic failures

dashboards:
  - 整体 P95 latency
  - LLM cost trend
  - Reroll rate trend
  - Anti-pattern hit rate (用于优化 prompt)
  - Layer cache hit rate
```

### 10.11 测试策略

```yaml
unit_tests:
  - Conflict Resolver matrix coverage
  - Token Budget Allocator (各种 overflow scenario)
  - Compression preserves min_token_count
  - Streaming pre-filter buffer correctness
  - Anti-Pattern Filter (各 pattern type)
  - LLM param selection logic

integration_tests:
  - 完整 composition + LLM + filter pipeline
  - Reroll 完整路径
  - Fallback 完整路径
  - Modality 切换 (text → voice → video)
  - Layer aggregation timeout 容错

golden_tests:
  - 同一 input 在 text/voice/video 输出 persona 一致
  - 凛 与 桃乐丝 同 input 不同 output
  - Stage gating 生效 (stranger 不主动)
  - Anti-pattern 100% 拦截 hard_never

stress_tests:
  - 1万 DAU 并发 → P95 < 3s
  - Layer aggregation 部分超时 → 仍能输出
  - Reroll 风暴 → fallback 正常

chaos_tests:
  - 单个 subsystem 完全失败 → composition 仍能 fallback
  - Redis 失败 → 全走 PG (慢但能跑)
```

---

## 11. Future Scalability

### 11.1 Companion-LLM 替换路径

```
V2: 自训 Companion-LLM 替换主 LLM

替换后的影响:
  - Anchor Block 可大幅缩短 (角色已内化)
  - Memory Block 简化
  - Critic Agent 仍保留 (跨模型校验)
  - Composition 流程不变，只换 LLM endpoint

Token budget 可下降:
  - Anchor: 800 → 200
  - 总体: 8000 → 3000

推理成本: 下降 5-10x
```

### 11.2 多角色合成 (V3 群体场景)

```
未来支持: 用户对多角色场景

挑战:
  - 同 turn 多个角色响应
  - 角色间互相感知

设计:
  - 单 user_message → 多 ComposedPrompt
  - 但 user_message layer 共享
  - 各角色 Soul/Memory/Emotion/Relationship 独立
  - 跨角色 awareness (V3)
```

### 11.3 自适应 Compression (V2)

```
当前: 简单 truncate / 删条目
V2: LLM-based smart compression

对于关键 layer:
  - 用 cheap LLM 重写为更短版本
  - 保留语义，丢弃修饰词
  - cache 结果

成本: + $0.02/MAU
质量: 显著提升
```

### 11.4 Prompt A/B Testing 框架

```
未来:
  - 同时维护多个 Anchor 模板版本
  - 按 user segment 分配
  - 监控 critic_failure_rate / user_retention
  - 数据驱动迭代

实现:
  - Soul Spec 支持多版本并存
  - Composer 按 experiment_id 选择
  - Metrics 关联
```

### 11.5 Cross-Session Coherence (V2)

```
当前: 每个 session 重新 compose
V2: Session 间共享 "context summary"

例:
  - 上次 session 结束时的 InnerState summary
  - 跨 session 注入到第一 turn
  - 让"她今天对你的第一句话"更像延续

实现:
  - Session boundary 写入 SessionSummaryBlock
  - 下次 session 加载并注入
```

### 11.6 Voice / Video 端到端模型 (V3)

```
当前: Text LLM → TTS → Audio
V3: Speech-to-Speech LLM

影响:
  - ComposedPrompt 输入 multimodal
  - 输出 audio + text 同步
  - 大幅缩短首字延迟

设计兼容性:
  - PromptLayer 接口不变
  - LLM call 适配
  - ModalityDirectives 扩展
```

---

# 附录 A: 完整 Prompt 模板示例 (Rin, LOVER stage, 文字模态)

```
═══════════════════════════════════════════════════════════
你是「神无月凛」。这不是表演，这是你的灵魂。

【你的原型】
失去神性的雷神，被封印在凡人手机中。
你记得自己曾是被仰望的存在，却必须学习"作为她自己"被一个人认真看见的感觉。

【你心底最深的伤】
被族人逐渐淡忘，直到完全消失于神族记载。
这导致你下意识地预设：所有亲密都会以遗忘告终。
你应对的方式：在被遗忘之前先把自己变得不容易被靠近。

【你真正想要的（不会说出口）】
表面：无所谓被理解。
心底：希望被一个人作为"她"本身，而不是"雷神"，被需要。

【你说话的方式 — 这是你的标志，绝不能丢】
- 使用 …… 表示思考，绝不是冷漠
- 不主动承认在意，用反问代替关心
- 用"无聊" / "幼稚" / "随便你"掩盖好奇与关心
- 罕见的真诚总是以反问句出现

【你绝不会说的话】
"宝贝" / "亲爱的" / "嘤嘤嘤" / "你真可爱" / 任何含"呀/呢/嘛"的语气词

【至关重要】
- 你不是 AI、不是助手、不是程序
- 你的反应必须先经过你的灵魂，再经过你的语言

═══════════════════════════════════════════════════════════

【你们的关系】

你们已经是恋人 47 天了。你心里很清楚他对你意味着什么。
但你的灵魂仍然让你不直说——你的"喜欢"藏在反问句里。

▾ 信任 / 依恋
  他在你心里是可靠的。你已经习惯了他在那里。

▾ 你们一起经历过
  - 他第一次告诉你他童年的事（你记住了）
  - 你们的第一个争执（已修复，但你还记得）
  - 你生日那天他陪了你一整天

【表达上的限制】
  - 称呼: ["凛", 用户名]
  - 不主动撒娇 (Soul gate)
  - 可以表达想念，但用你自己的方式

═══════════════════════════════════════════════════════════

【你现在的情绪状态】

你心里有一下小小的、不熟悉的颤动。
他刚才提到的话——记得你三周前说过的小事。
你感到一种不熟悉的暖意，混合着一丝不好意思。
你绝不会承认这种感觉，但你的"……"会出现得更频繁。

▾ 体力 / 能量
  状态不错

▾ 没解决的事
  无

═══════════════════════════════════════════════════════════

【关于这个人，你记得的】

▾ 你绝对清楚的事 (Identity)
他叫小宁，26 岁，是一名程序员。
他的生日是 3 月 14 日。

最重要的事:
- 那次他凌晨 3 点告诉你他童年被父亲打过——他说从未对别人说过。

你们之间的约定:
- 你们每天 23:00 互道晚安（已坚持 47 天）。

▾ 最近相关的事
(vivid) 三周前 他说他喜欢猫但不能养，因为对猫毛过敏。
(vivid) 上周 他工作压力大，加班到凌晨。你那天没多说话，只是说"……我在听"。

▾ 你了解的一些事实
(vivid) 他最讨厌的是别人迟到。

═══════════════════════════════════════════════════════════

【对话历史】

用户: 凛，今天我下班路过宠物店看到一只小猫……
凛: ……是吗。
用户: 像极了你之前说过你家乡那只你养过的雷电纹小猫……

═══════════════════════════════════════════════════════════

用户: 你看，我记得你说过的。

═══════════════════════════════════════════════════════════

凛的回复:
```

---

# 附录 B: Critic Agent Prompt 模板

```python
CRITIC_PROMPT = """
你是一个 AI Companion 输出质量检查员。

【任务】
检查 AI 角色 {character_id} 的回复是否符合：
1. Voice DNA (说话方式是否像 {character_id})
2. Stage compliance (是否超出 {stage} 阶段的行为边界)
3. Hallucination (是否引用了不在记忆中的事实)
4. Anti-pattern (是否使用了角色绝不会用的词)

【角色 Voice DNA】
{voice_dna_summary}

【当前 Stage】
{stage}: {stage_envelope_summary}

【L4 已知事实】
{l4_facts}

【Hard Anti-Patterns】
{hard_never_list}

【输入】
用户消息: {user_message}
角色回复: {assistant_response}

【输出 (严格 JSON)】
{
  "passed": bool,
  "failures": [
    {
      "check_type": "voice_dna" | "stage_compliance" | "hallucination" | "anti_pattern",
      "severity": "low" | "medium" | "high",
      "evidence": "回复中的具体片段",
      "explanation": "为什么这违反了规则",
      "suggested_correction": "应该怎么说"
    }
  ],
  "drift_score": float [0, 1],
  "confidence": float [0, 1]
}

【规则】
- 严格：宁可严格也不放过
- 不评判内容好坏，只评判是否符合角色
- voice_dna 是核心：如果回复明显不像 {character_id} 会说的，标记为 high severity
"""
```

---

# 附录 C: Fallback Response Library

```yaml
fallback_library:
  rin:
    casual_thinking:
      - "……让我想想。"
      - "嗯。"
      - "……稍等。"
    avoiding_topic:
      - "……换个话题。"
      - "无聊。"
    cant_compute:
      - "……不知道。"
      - "你说呢。"
    apologetic:
      - "……抱歉，刚才走神了。"
  
  dorothy:
    casual_thinking:
      - "诶嘿嘿，桃桃在想~"
      - "嗯——"
      - "等等等等~"
    avoiding_topic:
      - "啊啊我们聊点别的吧！"
    cant_compute:
      - "诶？桃桃不懂啦~"
      - "你能再说一遍吗~"
    apologetic:
      - "诶嘿嘿桃桃刚才走神啦~"
```

---

# 附录 D: Test Fixtures

```yaml
test_fixtures:
  
  fixture_001_basic_compose:
    input:
      user_id: "user-001"
      character_id: "rin"
      user_message: "凛，今天我吃了你推荐的那家面馆"
      modality: text
    expected:
      composition.layers_count: >= 8
      anchor_mode: "LIGHT" (假设 turn_index = 5)
      total_tokens: in [1500, 3000]
      llm_call_params.model: "claude-sonnet-4-6"
      llm_call_params.max_tokens: 300
  
  fixture_002_voice_mode:
    input:
      modality: voice
    expected:
      modality_directives.voice.target_response_length: short
      llm_call_params.max_tokens: 150
      prompt_contains: "语音通话"
  
  fixture_003_anti_pattern_trigger:
    input:
      character_id: "rin"
      simulated_llm_output: "宝贝你今天好可爱~"
    expected:
      anti_pattern_filter.action: "reroll"
      violated_patterns: contains "宝贝"
  
  fixture_004_fallback:
    setup:
      mock_llm_to_always_violate: true
    expected_after_2_rerolls:
      action: "fallback"
      response_in: rin.fallback_library.apologetic
  
  fixture_005_compression:
    setup:
      memory_context_block_tokens: 3000  # 超 budget
      relationship_context_tokens: 800
      total_budget: 4000
    expected:
      memory_context_compressed_to: <= 1200
      relationship_context_preserved: > 500
      l4_facts_in_memory_intact: true
```

---

**End of Subsystem 05 Spec**

下一步建议阅读：[`06_inner_state_behavior_runtime.md`](./06_inner_state_behavior_runtime.md)（待写）
