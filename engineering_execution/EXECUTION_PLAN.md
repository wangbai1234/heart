# 心屿 — 工业级 AI 协同开发执行方案

> **Version**: 1.0.0
> **Date**: 2026-05-15
> **Status**: 🧊 **FROZEN @ 2026-05-23** — Historical reference only. 本文件 96K，与 ROUTING / REVIEW / LAWS 文件存在大量重叠（§3=routing, §7=review, §8=failure modes, §9=laws）。
>
> **新内容请进**:
> - 操作 (Phase 0-6)：[`PRACTICAL_MODEL_GUIDE.md`](PRACTICAL_MODEL_GUIDE.md)
> - 操作 (Phase 7+)：[`PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md`](PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md)
> - 12 条法则：[`ENGINEERING_LAWS.md`](ENGINEERING_LAWS.md)
> - 模型路由：[`AI_MODEL_ROUTING.md`](AI_MODEL_ROUTING.md)
> - HUMAN review 边界：[`HUMAN_REVIEW_CHECKLIST.md`](HUMAN_REVIEW_CHECKLIST.md)
>
> 不要在本文件添加新条目。如发现本文件与上述任一 SSOT 冲突，**以 SSOT 为准**。
> 解冻规则：见 [`docs/GOVERNANCE.md`](../docs/GOVERNANCE.md) §2.1。

---

> *(以下为 2026-05-15 原始版本，保留作为历史参考。)*

> **原始状态**: Authoritative. 所有 AI 协同开发以此为准。
> **配套阅读**: `/runtime_specs/` (Runtime Bible)

---

# 1. Overall Engineering Roadmap

## 1.1 Roadmap 总览

```
                  Foundation        Tier 0/1 Core         Composer + Inner       Orchestration       Launch
                  (Phase 0)       (Phase 1-3)              (Phase 4-5)            (Phase 6)         (Phase 7-8)
                     │                  │                       │                      │                │
   Week:           1-3              4-17                     18-25                   26-30           31-44
                     │                  │                       │                      │                │
   ─────────────────────────────────────────────────────────────────────────────────────────────────────►
   
   AI 使用强度:    ████              ██████                  █████                   ████             ███
                  (基础设施)         (核心实现)              (集成层)                (安全 + 编排)      (调优)
   
   人工密度:       ██                ███████                 ████                    █████              █████
                  (架构)             (Soul + Memory)         (Composer)              (Safety + Wellbeing)(QA)
   
   Cost:           低                  中-高                    中                      中                高
                  ($300/月)          ($800/月)               ($500/月)               ($400/月)         (LLM real users)

   Cut Lines:
   ──────────────────────────────────────────────────────────────────────────────────────────────────────
   
                                                                                              MVP Cut Line (Phase 5 end)
                                                                                              ─ 角色可对话, 记忆工作, 情感连续
                                                                                              ─ 内部测试
                                                                                                      │
                                                                                                      │
                                                                                              Beta Cut Line (Phase 7 end, ~Week 36)
                                                                                              ─ 100 用户 closed beta
                                                                                              ─ 全部 7 个 subsystem 集成完成
                                                                                                      │
                                                                                                      │
                                                                                                  Production Cut Line (Phase 8 end, ~Week 44)
                                                                                                  ─ Public launch
                                                                                                  ─ Multi-region (US + EU)
                                                                                                  ─ Companion-LLM V1 ready
```

## 1.2 Phase 0: Foundation (Week 1-3)

```yaml
phase_0:
  duration: 3 weeks
  team: 2-3 engineers (1 lead + 1-2 implementers)
  
  goal: |
    建好工程基础设施，让后续 7 个 Subsystem 可以"上车".
    无角色逻辑, 纯 plumbing.
  
  deliverables:
    - K8s cluster setup (dev + staging)
    - PostgreSQL 15 + pgvector 部署
    - Redis 7 部署
    - CI/CD pipeline (GitHub Actions)
    - 基础 FastAPI 项目骨架
    - SQLAlchemy + Alembic 基础设施
    - Observability stack (Prometheus + Grafana + Loki)
    - Secrets management (KMS / Vault)
    - LLM Provider 抽象层 (Anthropic + DeepSeek SDK)
    - Local dev (docker-compose)
    - CLAUDE.md + .claude/ directory 配置
  
  ai_collaboration:
    opus: 0% (没有架构决策需求, spec 已定)
    sonnet: 60% (基础设施代码 + 框架搭建)
    haiku/deepseek: 30% (boilerplate, configs, dockerfiles)
    human: 10% (review, secrets, infra approval)
  
  risks:
    - 基础设施过度设计 (over-engineering)
    - LLM Provider 抽象不够通用
    mitigation:
      - 按 SS08 §10 严格执行, 不发明
      - LLM Provider 接口 review by Opus
  
  cost_estimate:
    infra: ~$300/月
    llm_dev: ~$50 (mostly Sonnet/Haiku)
    total: ~$350
  
  cut_criteria:
    - 可以从 local 跑起一个 echo bot (用户消息 → LLM 转发 → 流式返回)
    - CI 跑通基础 lint + test
    - Observability dashboard 可访问
    - LLM provider failover 可验证
```

## 1.3 Phase 1: Soul Spec + Anchor System (Week 4-7)

```yaml
phase_1:
  duration: 4 weeks
  team: 3-4 engineers + Content/Product (Soul Spec authoring)
  
  goal: |
    实现 SS01 Identity Anchor + Soul Spec.
    把 2 个角色 (Rin + Dorothy) 的灵魂建立起来.
    
  why_first: |
    SS01 是所有其他 subsystem 的依赖根.
    Soul Spec 是 source of truth, 不能后补.
  
  deliverables:
    - Soul Registry + Schema Validator
    - Soul Activation State Service (with PG schema)
    - Anchor Injector (FULL / LIGHT / REINFORCE 模板)
    - Drift Detector (with cheap LLM)
    - Resonance Tracker
    - Hidden Facet Unlocker
    - **Rin Soul Spec v1.0.0** (完整 YAML, 含 golden_dialogues)
    - **Dorothy Soul Spec v1.0.0** (完整 YAML)
    - 各角色至少 10 个 golden_dialogues
    - CI: golden dialogues replay
  
  ai_collaboration:
    opus: 15% (Anchor 模板 design + Drift detector tuning)
    sonnet: 40% (服务实现 + Schema + Tests)
    haiku/deepseek: 15% (boilerplate, migrations, type stubs)
    human: 30% (Soul Spec 内容 100% 人工 + Anchor 模板 review + Anti-pattern 列表 curation)
  
  risks:
    - Soul Spec 写得不够深 (变成形容词堆砌)
    - Anti-pattern 列表漏关键模式
    - Drift detector 误报率高
    mitigation:
      - Soul Spec 必须通过 SS01 附录 A 的 7 个问题
      - Anti-pattern 经过红队测试 (运营尝试调教角色)
      - Drift detector 在 staging 跑 1 周 + 调阈值
  
  cost_estimate:
    infra: ~$300/月
    llm_dev: ~$200 (Sonnet 主力)
    soul_authoring: 主要是人工时间
    total: ~$500
  
  cut_criteria:
    - 100% golden_dialogues 通过
    - Anchor injection 在 100 turns 后仍保持 voice_dna ≥ 60%
    - Anti-pattern filter 0 false negative on red team test
    - Soul Spec versioning + migration tested
```

## 1.4 Phase 2: Memory Runtime (Week 8-12)

```yaml
phase_2:
  duration: 5 weeks
  team: 4-5 engineers
  
  goal: |
    实现 SS02 完整记忆认知系统.
    这是产品最大的护城河, 必须做扎实.
  
  why_second: |
    Memory 被几乎所有上层 subsystem 引用.
    必须在 Emotion/Relationship 之前完成.
  
  deliverables:
    - 4 层 Memory store (L1/L2/L3/L4) + PG schema
    - Memory Service 统一接口
    - Fast Heuristic Encoder
    - LLM Encoder Worker (异步, DeepSeek V3)
    - Consolidator Worker (每日 03:00)
    - Multi-strategy Retriever (vector + graph + recency + emotional + identity)
    - Reconstructor (角色化 + state-aware)
    - Decay Engine (lazy + batch)
    - Reinforcer (Hebbian)
    - Forgetting Affect Engine
    - L3 → L4 Promotion Pipeline
    - Embedding service (自托管 BGE-M3)
    - CI: Memory regression tests
  
  ai_collaboration:
    opus: 10% (Decay 公式调优 + Reconstructor template design)
    sonnet: 55% (Memory Service + Retriever + Consolidator 实现)
    haiku/deepseek: 25% (Schema, migrations, fast encoder regex, boilerplate)
    human: 10% (Reconstructor 模板 review + decay 参数 final approval)
  
  risks:
    - Vector retrieval 性能不够 (P95 > 300ms)
    - Reconstructor 漂离 voice_dna
    - L4 promotion 阈值过低 (神圣记忆通货膨胀) 或过高
    - Encoding LLM 成本爆炸
    mitigation:
      - HNSW index + 监控 P95
      - Reconstructor 输出每周 sample review (Human)
      - L4 promotion 在 staging 跑 30 天评估
      - Encoding 走 cheap LLM + 启发式预过滤 (60% turn 不调 LLM)
  
  cost_estimate:
    infra: ~$500/月 (开始用 multi-AZ PG)
    llm_dev: ~$300
    embedding_gpu: ~$200/月 (A10 instance)
    total: ~$1000
  
  cut_criteria:
    - Retrieval P95 < 300ms
    - L4 100% 准确召回 (no hallucination on critical facts)
    - Reconstructor voice_dna 命中率 ≥ 60%
    - 模拟 30 天用户旅程 → memory state 符合 §11 fixtures
    - 模拟用户消失 90 天 → forgetting affect 触发正确
```

## 1.5 Phase 3: Emotion + Relationship (Week 13-17)

```yaml
phase_3:
  duration: 5 weeks  
  team: 4 engineers (可以两条线并行)
  
  goal: |
    实现 SS03 (Emotion) 和 SS04 (Relationship).
    两个 Subsystem 关联紧密但相对独立, 可并行.
  
  parallelism:
    track_a (2 engineers): SS03 Emotion
    track_b (2 engineers): SS04 Relationship
    week_5_both: 集成测试 + 跨 subsystem 事件
  
  deliverables_ss03:
    - Emotion State Machine (VAD + active stack + mood)
    - Trigger Detector (lexicon + keyword AC)
    - Contagion Engine
    - Type-specific Decay (12 emotion profiles)
    - Mood Drift Engine (hourly)
    - Repair Mechanic (4 类 repair signal + anti-gaming)
    - Cross-session persistence
  
  deliverables_ss04:
    - Relationship State (7 stages + 4 special states)
    - Phase Transition Engine (with Soul gates)
    - Trust Tracker / Attachment / Intimacy / Conflict Debt
    - Reunion State Machine (3-phase)
    - Cold War Tracker (with repair integration)
    - Drift / Reunion Manager
    - Stage configuration YAML
  
  ai_collaboration:
    opus: 15% (情绪衰减曲线设计 + Stage entry conditions 平衡调优)
    sonnet: 50% (服务实现 + 跨 subsystem 集成)
    haiku/deepseek: 20% (boilerplate, lexicon 整理, schema)
    human: 15% (情绪 phrase library + Stage gate 阈值 final + anti-gaming rules)
  
  risks:
    - 情绪状态机过于复杂导致行为不可预测
    - Stage progression 速度调错 (太快/太慢)
    - Repair anti-gaming 设计漏洞
    mitigation:
      - SS03 测试每个 emotion 单独 fixture
      - SS04 Rin/Dorothy 各跑 30/90/180 天模拟
      - Red team 尝试 gaming → 修补
  
  cost_estimate:
    infra: ~$500/月
    llm_dev: ~$300
    total: ~$800
  
  cut_criteria:
    - SS03: 4 个 §11 fixtures 全过 (首次见面/7 天消失/冷战修复/anti-gaming)
    - SS04: 5 个 §11 fixtures 全过 (30 天 Rin/Dorothy/消失重逢/冲突修复/anti-gaming)
    - 跨 SS03-04 事件订阅 100% 正确触发
```

## 1.6 Phase 4: Persona Composition Runtime (Week 18-21)

```yaml
phase_4:
  duration: 4 weeks
  team: 3 engineers
  
  goal: |
    实现 SS05. 这是所有 subsystem 的"汇合点".
    Prompt composition + anti-pattern + streaming + reroll.
  
  why_after_ss01_04: |
    SS05 消费 SS01-04 的输出.
    没有它们就无法测试 composition.
  
  deliverables:
    - Layer Aggregator (parallel)
    - Conflict Resolver (10 个规则)
    - Token Budget Allocator + Compressors
    - Modality Adapter (text/voice/video)
    - Composer (final prompt assembly)
    - Anti-Drift Injector (FULL/LIGHT/REINFORCE decision)
    - Streaming-Compatible Anti-Pattern Filter (Aho-Corasick + rolling buffer)
    - Reroll handler
    - Soul-flavored Fallback library
    - Critic Agent (异步, cheap LLM, 30% sampling)
    - Composition Trace + audit log
  
  ai_collaboration:
    opus: 20% (Anti-Pattern Filter design + Conflict Resolver matrix tuning + Critic prompt)
    sonnet: 55% (Composer + Aggregator + Streaming filter 实现)
    haiku/deepseek: 15% (boilerplate, trace storage)
    human: 10% (Fallback library 内容 + Critic prompt 校准)
  
  risks:
    - 流式 anti-pattern filter 漏判
    - Reroll 风暴 (LLM 一直犯错)
    - Conflict resolver 矩阵漏 case
    - Critic 误报浪费 reroll
    mitigation:
      - 流式 filter 单元测试覆盖跨 chunk patterns
      - Reroll 上限 + 强制 fallback
      - Conflict matrix 持续扩充 (基于实际遇到)
      - Critic 在 staging 跑 1 周 + 调精度
  
  cost_estimate:
    infra: ~$500/月
    llm_dev: ~$400 (开始有更多 LLM 调用测试)
    total: ~$900
  
  cut_criteria:
    - 端到端 turn 流程跑通 (用户消息 → LLM → 流式响应)
    - 5 个 §11 fixtures 全过
    - Anti-pattern hard_never 100% 拦截
    - Reroll 率 < 2%
    - 全链路 P95 < 3s
```

## 1.7 Phase 5: Inner State + Behavior (Week 22-25)

```yaml
phase_5:
  duration: 4 weeks
  team: 3 engineers
  
  goal: |
    实现 SS06. 让角色"活起来".
    主动行为 + Anniversary + Ritual.
  
  deliverables:
    - Inner Loop Scheduler (hourly + event-driven)
    - Activity Generator (Soul-curated, deterministic)
    - Concerns Tracker (from Memory)
    - Initiative Decider (8 gates + 7 triggers)
    - Anniversary Tracker (from L4)
    - Proactive Message Generator (走 Persona Composer)
    - Proactive Scheduler (Redis ZSET + jitter)
    - Ritual Manager (daily check-in)
    - Push Notification integration
    - Inner State Block (注入 prompt)
    - Activity pools for Rin + Dorothy (各 20+ activities)
  
  ai_collaboration:
    opus: 10% (Initiative decision tree review + adaptive rate tuning)
    sonnet: 50% (Inner Loop + Schedulers + Integration)
    haiku/deepseek: 20% (Activity pool YAML, boilerplate)
    human: 20% (Activity pool 内容 100% 人工 + Anniversary content + Quiet hours 调校)
  
  risks:
    - Proactive 频率过高 → 用户感觉骚扰
    - Activity 太相似 → 失去"活着"感
    - Anniversary 错过 → 用户流失
    mitigation:
      - Quota + min gap + adaptive rate
      - Activity pool ≥ 20 per character, 3 天不重复
      - Anniversary 双重 trigger (24h 前 + 当日 morning)
      - Production canary test 主动消息 reaction rate
  
  cost_estimate:
    infra: ~$600/月
    llm_dev: ~$300 (proactive 生成调用)
    total: ~$900
  
  cut_criteria:
    - 模拟用户 3 天消失 → 触发 check_in (符合 §11 fixtures)
    - 模拟生日 → 100% trigger (零漏)
    - Cold War 期间 0 主动消息
    - Adaptive rate 在用户不回时正确降频
    - 跨 session 持续性测试通过

  ─── MVP Cut Line (Phase 5 end) ───
  
  内部测试可用版本:
    - 7 个 subsystem 全部实现 (SS01-06)
    - 角色可对话, 记忆工作, 情感连续
    - 但: 无 Wellbeing / Safety upgrade / Voice / Video
    - 用于团队内部 dogfooding
```

## 1.8 Phase 6: Orchestration + Safety (Week 26-30)

```yaml
phase_6:
  duration: 5 weeks
  team: 4 engineers (含 ML eng for embedding/critic)
  
  goal: |
    实现 SS07. 把所有 subsystem 编排成完整系统.
    + 完整 Safety + Wellbeing.
  
  why_last: |
    SS07 是 meta-layer, 编排其他.
    没有完整的 SS01-06 它无法测试.
  
  deliverables:
    - Orchestrator Agent (hot path + cold path)
    - Safety Agent (5 levels + heuristic + LLM classification)
    - Critic Agent (升级到完整集成)
    - Director Agent (modality + length + pause + temperature)
    - Wellbeing Monitor (suicide/depression/dependency/addiction detection)
    - Event Bus (Redis Streams MVP)
    - Model Router (multi-provider failover)
    - Session Manager (cross-session state + multi-device)
    - Failure Handler (Circuit Breaker per subsystem)
    - PURPLE Care Path (full implementation)
    - RED Reject Path
    - Wellbeing intervention pipeline (含人工 content review)
    - Full distributed tracing (OpenTelemetry)
    - Full metrics dashboard
  
  ai_collaboration:
    opus: 25% (Care Path design + Wellbeing thresholds + Orchestration patterns)
    sonnet: 50% (Agent implementations + Service mesh integration)
    haiku/deepseek: 10% (boilerplate, tracing instrumentation)
    human: 15% (Safety keyword lists + Care Path responses + Wellbeing alert workflow + Content review process)
  
  risks:
    - Safety classifier 漏判 (false negative)
    - Wellbeing 过度干预破坏沉浸感
    - Care Path 响应不够温柔 / 不像角色
    - Multi-device race condition
    mitigation:
      - Safety 双层 (heuristic + LLM) + 红队测试
      - Wellbeing intervention 在 staging 灰度
      - Care Path response 100% 人工写
      - Distributed lock + 单元测试
  
  cost_estimate:
    infra: ~$800/月 (开始接近 production)
    llm_dev: ~$500
    total: ~$1300
  
  cut_criteria:
    - PURPLE message → Care Path 完整触发 (含 content team alert)
    - LLM provider 故障 → Failover 成功, persona 保持
    - Critic feedback → SS01 Drift Score 闭环
    - Wellbeing alert end-to-end (含人工 review queue)
    - 100 个真实对话 trace 全部可回放
```

## 1.9 Phase 7: Closed Beta (Week 31-36)

```yaml
phase_7:
  duration: 6 weeks
  team: 6 engineers + Content/Product + Trust&Safety
  
  goal: |
    100 用户 closed beta.
    系统稳定性验证 + 用户体验反馈 + 调优.
  
  scope:
    - Mobile app (Flutter) integration
    - Payment system (Stripe + 积分)
    - 用户管理 + auth
    - Push notifications (FCM/APNs)
    - 真实 LLM 调用 + 监控
    - 用户反馈通道 (in-app)
    - 内容审核 workflow (人工 review queue)
    - Hot fix capability
  
  ai_collaboration:
    opus: 15% (调优决策 + bug investigation)
    sonnet: 45% (集成 + bug fix + iteration)
    haiku/deepseek: 15% (UI tweaks, copy, configs)
    human: 25% (UX 反馈整理 + Content QA + Trust&Safety review)
  
  risks:
    - 用户感觉"她不像她" (drift)
    - Memory recall 错误
    - 主动消息频率不对
    - Cost 超预算 (重度用户)
    mitigation:
      - Daily critic report
      - Memory retrieval accuracy monitoring
      - Adaptive rate fine-tuning
      - Per-user cost cap + alert
  
  cost_estimate:
    infra: ~$1500/月 (production-grade staging)
    llm_real_users: ~$200 × 100 = ~$2000 (100 用户 × $20 LLM 成本)
    total: ~$3500
  
  cut_criteria:
    - 30 天用户留存 > 40%
    - "她像她" 用户调研 > 80% 同意
    - Memory recall accuracy > 95%
    - 0 PURPLE 误判
    - 0 严重 safety incident
    - Cost per active user < $2/month
  
  ─── Beta Cut Line ───
  
  Beta 通过后才能 public launch.
```

## 1.10 Phase 8: V1 Public Launch (Week 37-44)

```yaml
phase_8:
  duration: 8 weeks
  team: 10+ engineers + 全栈支持
  
  goal: |
    Public launch.
    Multi-region + Companion-LLM V1 + Voice (V1).
  
  scope:
    - Voice calling (V1.0): TTS + ASR pipeline
    - Multi-region deployment (US + EU)
    - GDPR full compliance
    - Companion-LLM V1 (LoRA per character)
    - Marketing site
    - App Store / Google Play submission
    - 客服系统
    - 数据合规审查
    - 24/7 oncall rotation
  
  ai_collaboration:
    opus: 15% (架构演进决策 + 性能优化)
    sonnet: 40% (新功能开发 + bug fix)
    haiku/deepseek: 15% (translations, copy, configs)
    human: 30% (产品决策 + 合规 + 危机响应)
  
  risks:
    - Multi-region 同步问题
    - LoRA 训练质量
    - Voice latency
    - Launch traffic spike
    mitigation:
      - Multi-region 提前 1 月 stress test
      - LoRA staged rollout (A/B)
      - Voice 优先深度优化 first-byte
      - Auto-scaling + CDN
  
  cost_estimate (per month after launch):
    infra: ~$5000-15000 (depending on DAU)
    llm: depends on users
    target: < $1.5/MAU
  
  cut_criteria (= Production Cut Line):
    - All Phase 7 criteria + 
    - Multi-region latency P95 < 3s 
    - Voice first-byte < 500ms
    - GDPR/CCPA compliance verified
    - Disaster recovery drill passed
    - 1000+ paying users 4 weeks stable
  
  ─── Production Cut Line ───
```

## 1.11 Roadmap 总结表

```
| Phase | Weeks | Goal                         | Team Size | Cost/Month | AI Mix             | Cut Criteria |
|-------|-------|------------------------------|-----------|------------|--------------------|---------------|
| 0     | 1-3   | Foundation infra              | 2-3       | $350       | S60/H30/O0/H10    | Echo bot works |
| 1     | 4-7   | Soul Spec + Anchor            | 3-4       | $500       | O15/S40/H15/Hu30  | Golden tests 100% |
| 2     | 8-12  | Memory Runtime                | 4-5       | $1000      | O10/S55/H25/Hu10  | Retrieval P95<300ms |
| 3     | 13-17 | Emotion + Relationship        | 4         | $800       | O15/S50/H20/Hu15  | All §11 fixtures |
| 4     | 18-21 | Composer Runtime              | 3         | $900       | O20/S55/H15/Hu10  | E2E P95<3s |
| 5     | 22-25 | Inner State + Behavior        | 3         | $900       | O10/S50/H20/Hu20  | Proactive works |
| MVP   |       | (Internal dogfooding)         |           |            |                   | All SS01-06 |
| 6     | 26-30 | Orchestration + Safety        | 4         | $1300      | O25/S50/H10/Hu15  | Care Path works |
| 7     | 31-36 | Closed Beta                   | 6+        | $3500      | O15/S45/H15/Hu25  | 30d retention>40% |
| Beta  |       | (100 user closed beta)        |           |            |                   |   |
| 8     | 37-44 | V1 Public Launch              | 10+       | $5-15k     | O15/S40/H15/Hu30  | Production stable |
| Prod  |       | (Public production)           |           |            |                   |   |

O = Opus, S = Sonnet, H = Haiku/DeepSeek, Hu = Human
```

---

# 2. Dependency Graph

## 2.1 Subsystem-Level Dependencies

```
                        ┌─────────────────────────────────────┐
                        │  Phase 0: Foundation Infrastructure │
                        │  (K8s, PG, Redis, CI, LLM clients)  │
                        └────────────────┬────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │  SS01: Soul Spec + Anchor           │  ← Tier 0
                        │  HARD DEP: nothing                  │     (Phase 1)
                        │  PROVIDES: Anchor, voice_dna, etc.  │
                        └────────────────┬────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │  SS02: Memory Runtime               │  ← Tier 1
                        │  HARD DEP: SS01 (voice_dna)         │     (Phase 2)
                        │  PROVIDES: L1/L2/L3/L4, recall      │
                        └────────────────┬────────────────────┘
                                         │
                            ┌────────────┴────────────┐
                            │ Tier 1 Parallel (Phase 3) │
                            │                         │
                            ▼                         ▼
                ┌──────────────────────┐  ┌──────────────────────┐
                │  SS03: Emotion       │  │  SS04: Relationship  │
                │  HARD DEP: SS01      │  │  HARD DEP: SS01      │
                │  SOFT DEP: SS02      │  │  SOFT DEP: SS02      │
                │  PROVIDES: VAD/stack │  │  PROVIDES: Stage/etc │
                └──────────┬───────────┘  └──────────┬───────────┘
                           │                         │
                           └────────────┬────────────┘
                                        │
                                        ▼
                        ┌─────────────────────────────────────┐
                        │  SS05: Persona Composer             │  ← Tier 2
                        │  HARD DEP: SS01, SS02, SS03, SS04   │     (Phase 4)
                        │  PROVIDES: ComposedPrompt           │
                        └────────────────┬────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │  SS06: Inner State + Behavior       │  ← Tier 2
                        │  HARD DEP: SS01, SS02, SS03, SS04   │     (Phase 5)
                        │  SOFT DEP: SS05 (for proactive gen) │
                        │  PROVIDES: InnerStateBlock          │
                        └────────────────┬────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │  SS07: Agent Orchestration          │  ← Tier 3
                        │  HARD DEP: SS01-06 ALL              │     (Phase 6)
                        │  PROVIDES: Turn handling, Safety,   │
                        │            Critic, Wellbeing        │
                        └────────────────┬────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │  SS08: Engineering Architecture     │  ← Tier 4 (Cross-cutting)
                        │  (Infrastructure, deployed throughout │     (All Phases)
                        │   all phases)                       │
                        └─────────────────────────────────────┘
```

## 2.2 Critical Path

```
Critical path (cannot be parallelized, blocks everything downstream):

Phase 0 → SS01 (Phase 1) → SS02 (Phase 2) → SS05 (Phase 4) → SS07 (Phase 6) → Beta → Launch

Total critical path: 26 weeks (out of 44 total).

可以并行的部分:
  - SS03 + SS04 (Phase 3): 5 weeks → 节省 5 周 (if 各 1 engineer 串行的话)
  - SS06 集成 + SS05 收尾: 部分 overlap
  - Mobile app 开发可与 SS01-07 同时进行 (Flutter project 独立)
```

## 2.3 模块内部 Dependency

### SS01 内部
```
SoulSpec YAML (Human writes)
        │
        ▼
Schema Validator
        │
        ▼
Soul Registry (load + cache)
        │
        ├─► Anchor Injector (FULL/LIGHT/REINFORCE)
        ├─► Soul Activation State Service
        ├─► Drift Detector (depends on cheap LLM)
        └─► Resonance Tracker (depends on Activation State)

实施顺序:
  1. Schema Validator
  2. Soul Spec YAML 内容 (Human)
  3. Registry + Activation State Service
  4. Anchor Injector (parallel with Activation State)
  5. Drift Detector
  6. Resonance Tracker + Hidden Facet Unlocker
```

### SS02 内部
```
Tier A (基础):
  ├─► PG Schema (L1/L2/L3/L4)
  ├─► Embedding Service (BGE-M3)
  ├─► Memory Service interface
  └─► Fast Heuristic Encoder

Tier B (异步):
  ├─► LLM Encoder Worker (queue consumer)
  ├─► Consolidator Worker
  └─► Decay Engine (lazy + batch)

Tier C (检索):
  ├─► Multi-strategy Retriever
  ├─► Reconstructor (depends on SS01 voice_dna)
  └─► Forgetting Affect Engine

Tier D (生命周期):
  ├─► Reinforcer
  └─► L3 → L4 Promotion Pipeline

实施顺序: Tier A → B (parallel C 后半) → C → D
```

### SS03 内部
```
独立可开发部件:
  - VAD + Active Stack data structures
  - Decay Engine (per emotion type)
  - Trigger Detector (lexicon)
  - Mood Drift Engine

集成时机:
  - Contagion Engine (needs SS01 shock_resistance)
  - Repair Mechanic Detector

实施顺序:
  1. Data structures + PG schema
  2. Trigger Detector + Decay Engine (parallel)
  3. Emotion Updater
  4. Mood Drift Engine
  5. Contagion + Repair (集成后)
```

### SS04 内部
```
独立部件:
  - Stage configuration YAML
  - Continuous Dimensions (Trust/Attachment/Intimacy/Conflict Debt)
  - Phase Transition Engine
  - Reunion State Machine
  - Cold War Tracker

依赖:
  - Soul Gate (needs SS01)
  - L4 event subscription (needs SS02)
  - Conflict event (needs SS03)

实施顺序:
  1. Stage configuration + State schema
  2. Continuous Dimension Trackers
  3. Phase Transition Engine
  4. Special State Managers (Reunion, Cold War, Drift)
  5. 集成 SS01/02/03 事件
```

### SS05 内部
```
最复杂模块. 实施顺序:

  1. Layer abstraction (PromptLayer)
  2. Layer Aggregator (parallel I/O)
  3. Conflict Resolver
  4. Token Budget Allocator
  5. Anti-Drift Injector
  6. Modality Adapter
  7. Composer (核心拼接)
  8. Anti-Pattern Filter (Aho-Corasick)
  9. Streaming-Compatible Pre-Filter (复杂)
  10. Reroll Handler
  11. Critic Agent (异步)
  12. Composition Trace

12 是 critical, 9 / 11 是 high risk.
```

### SS06 内部
```
Part A (Inner State):
  1. Activity Generator (Soul-curated pool)
  2. Concerns Tracker (from Memory)
  3. Inner State Composer
  4. Inner State Block Builder

Part B (Behavior):
  5. Initiative Decider (8 gates + 7 triggers)
  6. Anniversary Tracker (from L4)
  7. Proactive Message Generator (走 SS05)
  8. Proactive Scheduler
  9. Ritual Manager

Cross:
  10. Inner Loop Scheduler (调度 Part A + B)
  11. Event subscriptions (从 SS02/03/04)

5 + 7 是 critical (initiative logic + proactive generation).
```

### SS07 内部
```
按构件顺序:

  Infrastructure first:
    1. Model Router (multi-provider failover)
    2. Event Bus (Redis Streams)
    3. Session Manager
    4. Circuit Breaker
  
  Agents:
    5. Orchestrator Agent (核心)
    6. Safety Agent (5 levels)
    7. Director Agent
    8. Critic Agent (升级)
    9. Wellbeing Monitor
  
  Special Paths:
    10. PURPLE Care Path
    11. RED Reject Path
    12. Wellbeing Intervention Pipeline

10 + 12 必须 Human heavy.
```

## 2.4 哪些可以并行

```
可以并行的对子:
  - Phase 0 完成后, SS01 实施 + Mobile app 启动 (并行)
  - SS01 完成后, SS02 实施 + Embedding GPU 部署 (并行)
  - SS02 完成后, SS03 + SS04 完全并行 (2 个 team)
  - SS04 完成后, SS05 + Mobile app voice integration (并行)
  - SS06 与 SS07 部分组件可并行 (Inner State 与 Wellbeing Monitor)

绝对串行 (critical path):
  Phase 0 → SS01 → SS02 → SS05 → SS07

并行节约 (理想情况):
  原始串行: 44 周
  优化后: 实际可能 35-38 周 (节约 6-9 周)
```

## 2.5 Blocker Map

```
| 风险 | Blocker | 影响 | 缓解 |
|------|---------|------|------|
| Soul Spec 内容写不出来 | SS01 整个 phase | 后续全部 | 提前 1 周开始 Soul authoring, 与 Phase 0 并行 |
| Embedding GPU 采购延迟 | SS02 retrieval | Phase 2+ | 提前 Phase 1 末申请 GPU |
| Anthropic API quota 不够 | SS04+ 真实 LLM 调用 | Phase 4+ | 提前申请 enterprise quota |
| LLM 路由 / failover 设计错 | Cross-phase | 所有 SS | Phase 0 严格按 SS07 §3.5 实现 |
| Voice TTS 厂商问题 | Phase 8 launch | Voice 功能 | 提前 Phase 6 启动 vendor selection |
```

---

# 3. AI Model Routing Strategy

## 3.1 Model Tier 分级

```
Tier S — Opus 4.7 (顶级模型, 最贵)
  - Cost: $15/M input, $75/M output (示例, 实际查 pricing)
  - 适用: 架构决策, 多 file 整合, 复杂调试, prompt design
  - 严格: Cost-conscious, 不轻易用

Tier A — Sonnet 4.6 (主力模型, 性价比最高)
  - Cost: $3/M input, $15/M output
  - 适用: 主要实现, 复杂 refactor, multi-file edit, code review
  - 这是日常主力

Tier B — DeepSeek V3 (Cheap and capable)
  - Cost: $0.14/M input, $0.28/M output
  - 适用: 大量但 well-specified 任务 (boilerplate, simple endpoints)
  - 风险: 偶发性 reasoning miss → 必须有 verification

Tier B — Haiku 4.5 (轻量 Anthropic 系)
  - Cost: $0.80/M input, $4/M output
  - 适用: 简单任务, schema work, type stubs
  - 优势: 与 Sonnet 同 family, behavior 一致

Tier C — Continue + DeepSeek + VSCode (本地 IDE 集成)
  - 适用: 编辑时的 inline completion
  - 优势: 极低延迟, 频繁触发
  - 限制: 仅限单文件局部完成
```

## 3.2 Master Routing Table

```yaml
task_routing:
  
  # ─────────────────────────────────────────────
  # ARCHITECTURE & DESIGN (Tier S - Opus + Human)
  # ─────────────────────────────────────────────
  
  - task: "新增 Subsystem 设计"
    model: HUMAN + OPUS
    why: "架构决策不可委托, Opus 帮助 brainstorm"
    cost: high
    NEVER_LOWER: true
  
  - task: "修改 Subsystem 的 Section 2 (设计原则)"
    model: HUMAN + OPUS
    why: "原则改变影响所有 layer"
    NEVER_LOWER: true
  
  - task: "Soul Spec 设计 / 撰写"
    model: HUMAN (with Opus for brainstorm)
    why: "灵魂是产品核心, AI 不能代写"
    NEVER_LOWER: true
  
  - task: "Anti-pattern 列表 curation"
    model: HUMAN
    why: "需要懂中文语感 + 角色 IP"
    NEVER_LOWER: true
  
  - task: "Care Path response 文案"
    model: HUMAN (+ 心理专业 review)
    why: "用户生命相关, 法律相关"
    NEVER_LOWER: true
  
  - task: "Safety threshold 调优 (PURPLE/RED 等)"
    model: HUMAN + OPUS for analysis
    why: "False positive/negative trade-off 需要专家判断"
    NEVER_LOWER: true
  
  - task: "Anniversary content / Ritual content"
    model: HUMAN
    why: "灵魂相关 (per character)"
    NEVER_LOWER: true
  
  - task: "Wellbeing intervention 设计"
    model: HUMAN + OPUS + 心理咨询师 review
    why: "对脆弱用户影响巨大"
    NEVER_LOWER: true
  
  # ─────────────────────────────────────────────
  # COMPLEX IMPLEMENTATION (Tier S/A)
  # ─────────────────────────────────────────────
  
  - task: "Drift Detector 算法实现"
    model: OPUS for design, SONNET for code
    why: "算法需要深度推理, 但 code 可委托"
    cost: medium-high
  
  - task: "Reconstructor 实现 (Memory)"
    model: OPUS for design, SONNET for code
    why: "要正确应用 voice_dna, design 关键"
  
  - task: "Streaming Anti-Pattern Filter"
    model: OPUS for algorithm, SONNET for impl
    why: "Cross-chunk pattern detection 复杂"
  
  - task: "Conflict Resolver Matrix 扩充"
    model: OPUS
    why: "需要理解多个 subsystem 的交互"
  
  - task: "Modality Adapter design"
    model: SONNET (after spec)
    why: "Spec 已详细, 实施即可"
  
  - task: "Phase Transition Engine"
    model: SONNET
    why: "Rule engine, spec 详细"
  
  - task: "Emotion State Machine 实现"
    model: SONNET
    why: "Spec 已详细, 标准实现"
  
  # ─────────────────────────────────────────────
  # STANDARD IMPLEMENTATION (Tier A - Sonnet)
  # ─────────────────────────────────────────────
  
  - task: "Service interface 实现"
    model: SONNET
    why: "Spec 中已定义接口, 实施即可"
    cost: medium
  
  - task: "Multi-file refactor"
    model: SONNET
    why: "需要跨文件理解"
  
  - task: "Critic Agent prompt design"
    model: SONNET (+ 人工 review)
    why: "Prompt 工程"
  
  - task: "Director Agent rule engine"
    model: SONNET
    why: "Spec-driven rules"
  
  - task: "Memory Service core impl"
    model: SONNET
    why: "完整接口 + 复杂逻辑"
  
  - task: "Event Bus 抽象 + Redis Streams 实现"
    model: SONNET
    why: "Infrastructure code"
  
  - task: "Model Router 实现"
    model: SONNET
    why: "Critical infrastructure, 但 spec 详细"
  
  - task: "PG schema design (per subsystem)"
    model: SONNET (查 spec) for full design
    HAIKU/DEEPSEEK for migrations
  
  - task: "Code Review (PR 审查)"
    model: SONNET (after Spec compare)
    why: "需要 spec compliance check"
  
  - task: "Integration test writing"
    model: SONNET
    why: "需要理解多 subsystem 交互"
  
  # ─────────────────────────────────────────────
  # BOILERPLATE (Tier B - DeepSeek / Haiku)
  # ─────────────────────────────────────────────
  
  - task: "SQLAlchemy model boilerplate (from schema)"
    model: HAIKU / DEEPSEEK
    why: "Pure translation"
    cost: very low
  
  - task: "Alembic migration scripts"
    model: HAIKU / DEEPSEEK
    why: "Standard pattern"
  
  - task: "Pydantic schema (from data structures)"
    model: HAIKU / DEEPSEEK
    why: "Translation task"
  
  - task: "Type annotations"
    model: DEEPSEEK / CONTINUE inline
    why: "Mechanical task"
  
  - task: "Docstring drafts"
    model: DEEPSEEK / CONTINUE
    why: "Boilerplate-ish, human review"
  
  - task: "Import organization"
    model: CONTINUE inline
    why: "Trivial"
  
  - task: "Unit test scaffolding (given fixtures)"
    model: HAIKU / DEEPSEEK
    why: "Pattern-based"
  
  - task: "Config file generation (Dockerfiles, k8s YAML)"
    model: HAIKU / DEEPSEEK
    why: "Standard formats"
  
  - task: "Activity pool YAML 翻译 (from Human spec)"
    model: HAIKU / DEEPSEEK
    why: "Format conversion"
  
  - task: "Lexicon files (emotion keywords)"
    model: HAIKU / DEEPSEEK
    why: "List compilation"
  
  - task: "API documentation drafts"
    model: HAIKU / DEEPSEEK
    why: "Generated from code"
  
  # ─────────────────────────────────────────────
  # NEVER DELEGATE TO LOW-TIER
  # ─────────────────────────────────────────────
  
  - task: "Soul Spec 任何字段修改"
    NEVER_USE: HAIKU, DEEPSEEK
    REQUIRED: HUMAN
    why: "影响角色 IP, 不可逆"
  
  - task: "Safety keyword list 修改"
    NEVER_USE: HAIKU, DEEPSEEK (even Sonnet 不能自主修改)
    REQUIRED: HUMAN review
    why: "影响安全分类"
  
  - task: "Memory decay 公式调整"
    NEVER_USE: HAIKU, DEEPSEEK
    REQUIRED: HUMAN + Opus analysis
    why: "影响所有用户记忆体验"
  
  - task: "Anti-pattern 模式增删"
    NEVER_USE: HAIKU, DEEPSEEK, Sonnet
    REQUIRED: HUMAN
    why: "影响角色被驯化风险"
  
  - task: "Critic prompt 修改"
    NEVER_USE: HAIKU, DEEPSEEK
    REQUIRED: SONNET + HUMAN review
    why: "影响 drift detection 精度"
  
  - task: "Wellbeing 阈值调整"
    NEVER_USE: AI alone
    REQUIRED: HUMAN + 数据分析"
    why: "影响干预触发, 法律风险"
```

## 3.3 Routing Decision Tree

```
                 [新任务到达]
                       │
                       ▼
        ┌──────────────────────────────────┐
        │ Q1: 是否触及"她"的灵魂?          │
        │ (Soul Spec / voice_dna / Care)   │
        └──────┬───────────────────────┬───┘
               │ YES                   │ NO
               ▼                       ▼
         ┌──────────┐         ┌──────────────────────────┐
         │  HUMAN   │         │ Q2: 是否触及 Safety/     │
         │   ONLY   │         │   Wellbeing decision?    │
         │ (+ Opus  │         └──────┬──────────────────┬┘
         │ brainstm)│                │ YES              │ NO
         └──────────┘                ▼                  ▼
                              ┌──────────┐       ┌─────────────┐
                              │ HUMAN +  │       │ Q3: 是否    │
                              │ OPUS     │       │ 架构决策?    │
                              │ analysis │       └──────┬──────┬┘
                              └──────────┘              │ Y    │ N
                                                        ▼      ▼
                                                  ┌───────┐ ┌───────────────┐
                                                  │ OPUS  │ │ Q4: 是否需要 │
                                                  │ +     │ │ multi-file    │
                                                  │ HUMAN │ │ 跨 subsystem? │
                                                  │ rev   │ └──────┬───────┬┘
                                                  └───────┘        │ Y    │ N
                                                                   ▼      ▼
                                                              ┌────────┐ ┌──────────────────┐
                                                              │ SONNET │ │ Q5: 是否纯 boil-│
                                                              │ + rev  │ │  erplate?        │
                                                              └────────┘ └──────┬───────────┘
                                                                                │  Y     N
                                                                                ▼      ▼
                                                                            ┌──────┐ ┌──────┐
                                                                            │HAIKU │ │SONNET│
                                                                            │DEEPSK│ │      │
                                                                            └──────┘ └──────┘
```

## 3.4 Cost Per Task Analysis

```yaml
typical_task_costs:
  
  # Per task estimates (LLM cost)
  
  小任务_well_specced (300-1000 tokens):
    haiku: $0.001 - $0.005
    deepseek: $0.0001 - $0.0005
    sonnet: $0.005 - $0.02
    opus: $0.05 - $0.20
  
  中任务_subsystem_implementation (2k-10k tokens):
    sonnet: $0.05 - $0.20
    opus: $0.50 - $2.00
  
  大任务_cross_subsystem_refactor (10k+ tokens):
    sonnet: $0.30 - $1.00
    opus: $3.00 - $10.00
  
  Critic_per_turn (~500 tokens):
    haiku: $0.001
    deepseek: $0.0001
  
  Safety_per_message (~200 tokens):
    haiku: $0.0005
    deepseek: $0.00006
  
  Main_response_per_turn (~3000 input, 200 output):
    sonnet: $0.012 (input) + $0.003 (output) = $0.015
    opus: $0.075 (input) + $0.015 (output) = $0.09  ← NEVER as main
    companion_llm_v2 (摊销): $0.005
```

## 3.5 总体路由原则总结

```
铁律 1: Default to Sonnet
  - 不知道用哪个时, 用 Sonnet
  - Sonnet 是 cost/quality 最优点

铁律 2: Promote to Opus only for ARCHITECTURE
  - 多 subsystem 涉及的设计决策
  - 算法 / Prompt design
  - Critical bug investigation
  - Cross-cutting refactor

铁律 3: Demote to Haiku/DeepSeek only for SPEC-DRIVEN BOILERPLATE
  - 输入 spec 明确
  - 输出可验证 (test 通过)
  - 单文件 / 单函数 scope
  - 不涉及业务逻辑判断

铁律 4: Never lower for SOUL
  - 任何 Soul 相关 → Human
  - 任何 Safety/Wellbeing 阈值 → Human
  - 任何"她"的声音 → Human

铁律 5: Human is mandatory at boundaries
  - Phase 之间的 cut criteria → Human review
  - Cross-subsystem 集成 → Human integration test
  - Production deploy → Human approval
```

---

# 4. Cost Optimization Strategy

## 4.1 成本来源拆解

```yaml
total_dev_cost = sum of:
  
  # During Development (Phase 0-8)
  1. LLM API for coding (Claude/DeepSeek)
     - Sonnet: 大量 daily 使用
     - Opus: 偶发, 必要时
     - DeepSeek/Haiku: 大量但 cheap
  
  2. Test LLM calls (running prompts during dev)
     - 测试 Critic
     - 测试 Anti-pattern
     - Golden dialogues regression
  
  3. Infra (K8s, DB, monitoring)
  
  # In Production (after launch)
  4. Main LLM calls (user-facing)
     - 占 production cost 主导
  
  5. Cheap LLM (Critic, Memory encoding, etc.)
  
  6. Infra scale
```

## 4.2 Top 10 Cost 浪费模式 (必须避免)

```
浪费 1: 用 Opus 写普通代码
  反模式: "我让 Opus 实现这个 Service"
  正确: Spec 已经详细, Sonnet 完全够
  节省: 5-10x

浪费 2: 每次重复发整个 Runtime Bible 作为 context
  反模式: 把 19,445 行 spec 全部塞 prompt
  正确: 只读相关 subsystem 的相关章节 (用 Read offset)
  节省: 80%+ context tokens

浪费 3: AI 不读 Spec 就开始写
  反模式: "AI 应该懂 AI Companion"
  正确: 强制 AI 第一步读相关 spec
  节省: 减少 90% reroll / refactor

浪费 4: Critic Agent 用 Sonnet
  反模式: Critic 重要, 用强模型
  正确: Critic 是 boolean judgment, Haiku/DeepSeek 够
  节省: 10x

浪费 5: Memory Encoding 走 Sonnet
  反模式: 提取 fact 也要质量
  正确: DeepSeek V3 用 JSON mode 完全够
  节省: 20x

浪费 6: 不用 Prompt Caching
  反模式: 每次 LLM call 重新传 Anchor Block
  正确: Anchor Block stable → Anthropic prompt caching
  节省: 90% on cached portion

浪费 7: AI 反复 read 相同文件
  反模式: 每次任务都 Read 整个 file
  正确: 用 grep 定位, Read 用 offset/limit
  节省: 70%

浪费 8: Sub-agent 重复 spawn 同样的工作
  反模式: 同一类任务每次都 spawn agent
  正确: 设计成 batch / loop
  节省: 50%

浪费 9: 用 LLM 做 simple parsing
  反模式: LLM 解析 JSON / 提取字段
  正确: 写代码 / regex
  节省: 100% (no LLM call)

浪费 10: Critic 100% sampling
  反模式: 每个 turn 都跑 Critic
  正确: 30% sampling (按 spec)
  节省: 70% of critic cost
```

## 4.3 具体优化技术

### 4.3.1 Prompt Caching (Anthropic)

```python
# 在 LLM call 中使用 cache_control

# Composed Prompt 结构:
#   [Anchor Block (cached prefix)]      ← 长, 稳定 → cache
#   [Memory Context (varies)]            ← 每 turn 变 → no cache
#   [Conversation history (extends)]     ← 每 turn 加 → cache + 增量
#   [User Message (new)]                 ← new
#   [Response Directive]                 ← stable → cache

response = anthropic.messages.create(
    model="claude-sonnet-4-6",
    system=[
        {
            "type": "text",
            "text": anchor_block,
            "cache_control": {"type": "ephemeral"}  # ← cache
        }
    ],
    messages=[
        ...
    ]
)

# Cache hit rate target: > 90% for repeated user sessions
# Cost reduction on cached portion: 90% (input price 0.1x)
```

### 4.3.2 Spec-Slicing (避免 Context Bloat)

```python
# WRONG (浪费 token):
spec_text = open("02_memory_runtime.md").read()  # 100KB

# RIGHT (精确切片):
# Use Read tool with offset/limit
section_4_2 = Read(
    file_path="runtime_specs/02_memory_runtime.md",
    offset=850,  # 大约 §4.2 开始的行号
    limit=80,
)

# OR use grep to find relevant snippet
# grep "L3 → L4" → 找到行号 → Read with offset
```

### 4.3.3 Sub-agent Isolation

```python
# 在 Claude Code 中使用 Agent tool 隔离 context

# 当前 session 已经塞满了 SS02 context
# 现在需要写 SS03 测试

# WRONG: 在同一 session 继续，context 已经 70k token, 浪费
# RIGHT: spawn subagent

Agent(
    description="Write SS03 unit tests",
    subagent_type="general-purpose",
    prompt="""
    Read runtime_specs/03_emotion_state_machine.md §11 (test fixtures).
    Write pytest unit tests for the decay function in 
    backend/heart/ss03_emotion/decay.py.
    
    Constraints:
    - Use existing test infrastructure in tests/unit/
    - Cover all 4 fixtures in §11
    - Mock LLM calls
    - Don't modify implementation files
    
    Return: summary of tests written.
    """
)

# Sub-agent context: 干净, 仅相关 spec 章节 + 测试文件
# 主 session 不被污染
```

### 4.3.4 Batch Operations

```python
# WRONG: 一次一次问 AI
for subsystem in subsystems:
    ai_call("Generate boilerplate for " + subsystem)  # 6 次 calls

# RIGHT: 一次设计好 template, AI 一次生成
ai_call("""
Generate SQLAlchemy models for all 6 subsystems based on this schema spec.
[包含 6 个 subsystem 的 schema]
Output 6 separate Python files.
""")
```

### 4.3.5 Cache Cheap LLM Outputs

```python
# Safety classification, Memory extraction 等 cheap LLM 输出
# 可以 cache by content hash

@cached(ttl=86400, key_fn=lambda msg: sha256(msg))
async def safety_classify(message: str) -> SafetyResult:
    return await cheap_llm.classify(message)

# 重复消息 (e.g., "在吗") → cache hit
# Cache hit rate target: > 60%
```

### 4.3.6 LLM-Free Path Where Possible

```python
# WRONG: 用 LLM 检查是否含 keyword
result = await llm.call("Does this contain 'apology'? " + message)

# RIGHT: 正则 / lexicon
if any(kw in message for kw in APOLOGY_KEYWORDS):
    ...

# 适用场景:
#   - Safety pre-filter (heuristic first, LLM only if uncertain)
#   - Trigger detection (lexicon-based)
#   - Memory encoding fast path (regex extraction)
#   - Initiative decision (rule engine, no LLM)
#   - Decay computation (pure math)
```

### 4.3.7 Smart Sampling

```python
# Critic Agent: 30% sampling
def should_sample(turn) -> bool:
    if turn.is_first_10_for_new_user:
        return True  # 100% for new users
    if turn.has_user_complaint:
        return True
    if turn.proactive_message:
        return True
    return random() < 0.30  # 30% default

# Wellbeing: 每 10 turns 评估一次
# Memory consolidation: 每天 1 次, 不是每 turn
# Drift detection: 每 5 turns
```

## 4.4 Dev-Phase Token Budget

```yaml
estimated_dev_costs (per phase):
  
  phase_0_foundation: $50
    主力: Sonnet for infrastructure code
    最大成本: 重复 review configs
  
  phase_1_soul_anchor: $200
    主力: Sonnet
    Opus 用于: Anchor template design (1 次)
    Human time: 大量 (Soul Spec writing)
  
  phase_2_memory: $300
    主力: Sonnet
    Opus 用于: Decay formula tuning (1-2 次)
    DeepSeek 用于: Encoding LLM tests
  
  phase_3_emo_rel: $300
    主力: Sonnet (两 track 并行)
    Opus 用于: Stage entry conditions design
  
  phase_4_composer: $400
    主力: Sonnet
    Opus 用于: Conflict resolver + Anti-Pattern algorithm
  
  phase_5_inner: $300
    主力: Sonnet
    Opus 用于: Initiative decision logic
  
  phase_6_orchestration: $500
    主力: Sonnet
    Opus 用于: Care Path + Wellbeing design
    Real LLM testing 开始大量
  
  phase_7_beta: $2000 (real users)
    100 用户 × $20 LLM cost
  
  phase_8_launch: depends on traffic

total_dev_LLM_cost (phase 0-7): ~$4000
```

## 4.5 Cost Tracking Setup

```yaml
cost_tracking:
  
  per_LLM_call:
    log:
      - model
      - input_tokens
      - output_tokens
      - cached_tokens (if any)
      - cost (computed)
      - agent (memory_encoder / critic / main / etc.)
      - phase / task (manual tag in dev)
    
    aggregation:
      - per agent per day
      - per developer per day (dev tracking)
      - per user per day (production)
  
  alerts:
    - daily LLM cost > $X → notify lead
    - any single LLM call > $Y → review
    - user daily cost > $Z → cap activated
  
  dashboard:
    - Cost trend per agent
    - Cost per user MAU
    - Cache hit rate
    - Critic sampling actual rate
```

---

# 5. AI Coding Workflow

## 5.1 Spec-Driven Development Loop

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────┐ │
│   │ TASK     │───▶│ ROUTE    │───▶│ EXECUTE  │───▶│VERIFY│ │
│   │ DEFINE   │    │ (model)  │    │ (AI)     │    │      │ │
│   └──────────┘    └──────────┘    └──────────┘    └──┬───┘ │
│        │                                              │     │
│        │              ┌──────────────────────┐        │     │
│        └──────────────│ MERGE / RFC          │◀──────┘     │
│                       └──────────────────────┘              │
└─────────────────────────────────────────────────────────────┘

每个 step 的详细 workflow:
```

### Step 1: TASK DEFINE

```yaml
task_definition_template:
  task_id: "<phase>-<subsystem>-<short-name>"
  description: "一句话描述要做什么"
  
  spec_references:
    - "/runtime_specs/0X_<subsystem>.md §<section>"
    - "/engineering_execution/EXECUTION_PLAN.md §<section>"
  
  scope:
    - touches: ["file1.py", "file2.py"]
    - NOT_touches: ["soul_specs/", "config/safety_keywords.yaml"]
  
  output_expectations:
    - "实现 X 接口"
    - "通过 fixture Y"
    - "新增/修改 metric Z"
  
  human_review_required: bool
  estimated_complexity: low | medium | high
  estimated_tokens: ~Xk
  
  prerequisites:
    - "Subsystem A 已完成"
    - "Test infrastructure ready"
```

### Step 2: ROUTE (选择 model)

```python
# 走 AI_MODEL_ROUTING decision tree

def route_task(task: Task) -> ModelChoice:
    # Q1: 触及"她"?
    if task.touches_soul_or_voice_dna():
        return HUMAN_ONLY
    
    # Q2: 触及 Safety/Wellbeing?
    if task.touches_safety_thresholds():
        return HUMAN_WITH_OPUS_ANALYSIS
    
    # Q3: 架构决策?
    if task.is_architectural():
        return OPUS_WITH_HUMAN_REVIEW
    
    # Q4: Multi-file refactor?
    if task.is_cross_file_refactor():
        return SONNET_WITH_REVIEW
    
    # Q5: Boilerplate?
    if task.is_well_specced_boilerplate():
        return HAIKU_OR_DEEPSEEK
    
    return SONNET  # default
```

### Step 3: EXECUTE (AI Coding)

#### 3a. For Sonnet/Opus (Claude Code)

```bash
# 启动 Claude Code session
claude

# Session 中 (自动 load CLAUDE.md):
> read runtime_specs/02_memory_runtime.md §10.3 and implement \
  the MemoryRetriever class in backend/heart/ss02_memory/retriever.py

# Workflow inside session:
# 1. Claude 读取 Spec
# 2. Plan (用 EnterPlanMode for complex)
# 3. Implement
# 4. Run tests
# 5. Self-review
```

#### 3b. For DeepSeek/Haiku (boilerplate)

```bash
# Continue + VSCode for inline
# 或 directly call API for batch generation

# Example: Generate SQLAlchemy models from spec
deepseek-prompt < generate_models_prompt.txt > models.py

# Always pair with verification:
mypy models.py
pytest tests/unit/test_models.py
```

### Step 4: VERIFY

```yaml
verification_gates:
  
  gate_1_syntax:
    - ruff check
    - mypy
    - python -m compile_check
  
  gate_2_unit_tests:
    - pytest tests/unit/<changed_module>
  
  gate_3_integration:
    - pytest tests/integration/<changed_subsystem>
  
  gate_4_spec_compliance:
    - 自动: 检查 spec 中的 P-N / INV-N 是否覆盖
    - 手动: human review for personality-sensitive changes
  
  gate_5_golden_tests:
    - 如果触及 SS01-06, 跑相关 golden
  
  gate_6_performance:
    - Profile if relevant (e.g., new retrieval logic)
    - Check P95 not regressed
  
  gate_7_cost:
    - Check no new LLM calls in hot path
    - Check Critic sampling unchanged
```

### Step 5: MERGE / RFC

```
if all gates pass + (human review if needed):
    merge to main

if gate fails:
    → fix → re-execute
    OR
    → 发现 spec 缺陷? → write RFC to update spec
```

## 5.2 单个 Subsystem 的标准开发流程

```
[Subsystem 开始]
        │
        ▼
Step 0: Phase Kickoff Meeting (Human)
  - Tech Lead 解读 spec
  - 团队成员认领 modules
  - 制定子任务列表
        │
        ▼
Step 1: Module-Level Task Breakdown
  - 每个 module 1-3 tasks
  - 每个 task 按 §5.1 template
  - 按 dependency 排序
        │
        ▼
Step 2: 并行执行
  ┌─────────────────────────────────┐
  │  Engineer 1 (Sonnet 主力)        │
  │  - Module A 实现                 │
  └─────────────────────────────────┘
  ┌─────────────────────────────────┐
  │  Engineer 2 (Sonnet 主力)        │
  │  - Module B 实现                 │
  └─────────────────────────────────┘
  ┌─────────────────────────────────┐
  │  Engineer 3 (DeepSeek 副)        │
  │  - Schema, migrations,           │
  │    boilerplate for A & B         │
  └─────────────────────────────────┘
        │
        ▼
Step 3: Integration
  - Module 间集成 (Sonnet)
  - Cross-subsystem 事件订阅 (Sonnet, careful)
        │
        ▼
Step 4: Spec Compliance Check
  - 自动: CI 检查 P-N / INV-N
  - 手动: Tech Lead review
        │
        ▼
Step 5: Golden Tests
  - 所有 fixtures pass
        │
        ▼
Step 6: Phase Cut Criteria
  - 满足 spec §11 + roadmap criteria
        │
        ▼
[Subsystem 完成, 进入下一 phase]
```

## 5.3 一个 Task 的完整生命周期 (示例)

```yaml
example_task:
  task_id: "P2-SS02-retriever-vector"
  description: "实现 Memory Retriever 的 vector search 策略"
  
  spec_references:
    - "runtime_specs/02_memory_runtime.md §3.5"  # Retrieval pipeline
    - "runtime_specs/02_memory_runtime.md §10.3"  # 实现细节
  
  scope:
    touches:
      - "backend/heart/ss02_memory/retriever.py"
      - "backend/heart/ss02_memory/strategies/vector.py"
    NOT_touches:
      - "soul_specs/"
      - "backend/heart/ss01_soul/"  # 仅 read interface
  
  routing_decision: SONNET (multi-file, but well-specced)

# ─── EXECUTION ───
  
  step_1_session_start:
    in_claude_code:
      action: |
        Open backend/heart/ss02_memory/strategies/
        Read runtime_specs/02_memory_runtime.md from line 850 limit 80
        (这是 §3.5 retrieval pipeline section)
      cost: ~5k tokens
  
  step_2_plan:
    in_claude_code:
      action: |
        EnterPlanMode
        - 分析 spec 中 vector retrieval 的要求
        - 列出需要的接口
        - 草拟 vector.py 文件结构
        ExitPlanMode (with user approval)
      cost: ~3k tokens
  
  step_3_implement:
    in_claude_code:
      action: |
        Write vector.py (使用 Edit/Write tools)
        - VectorRetriever class
        - 调用 embedding service
        - HNSW query via pgvector
        - 返回 ScoredMemory[]
        - Type hints, docstrings
      cost: ~8k tokens
  
  step_4_test:
    in_claude_code:
      action: |
        Generate unit tests using fixtures from §11
        Run pytest
        Fix any failures
      cost: ~5k tokens
  
  step_5_review:
    in_claude_code:
      action: |
        Self-review: check spec compliance
        Check INV-M-3 (Top-K limit)
        Check INV-M-6 (user_id filtering)
        Run linters
      cost: ~2k tokens
  
  step_6_pr:
    outside_claude_code:
      action: Human review on GitHub PR
      cost: human time
  
  total_LLM_cost: ~$0.15 (Sonnet, ~23k tokens)
  total_human_time: 30 min review
```

## 5.4 跨 Session 的 Context Management

```
关键原则: 每个 Claude Code session 不应超过 50k tokens context

策略:
  - 每 30-50k tokens, 主动重启 session
  - 用 /clear 清除历史 (但保留 CLAUDE.md)
  - 大任务拆成小 task, 各自一 session
  - 使用 subagent 隔离

不应该:
  - 一个 session 实现整个 subsystem
  - 反复 read 大文件
  - 让 AI 总结对话历史 (浪费 token)
```

## 5.5 关键 Workflow Templates

### Template A: 新 Subsystem 实现

```markdown
# Template: New Subsystem Implementation

## Prep
- [ ] Tech Lead: 解读 Spec, 写 task breakdown
- [ ] 团队: 阅读 spec §1 §2 §5 §6 §7
- [ ] 确认 dependencies (前置 Subsystem) 已完成

## Per Module

### 1. Schema First
Agent (Haiku/DeepSeek):
- 生成 SQLAlchemy models from spec §5
- 生成 Alembic migrations
- Pydantic schemas

### 2. Service Skeleton
Agent (Sonnet):
- 实现 Service 类的接口 (按 spec §7.2)
- 暂用 NotImplementedError stubs
- 添加 type hints

### 3. Core Logic
Engineer + Sonnet:
- 实现核心算法 (按 spec §3 + §10.3)
- 单元测试 (按 spec §11 fixtures)

### 4. Cross-Subsystem Integration
Engineer + Sonnet:
- 实现 event subscriptions
- 实现外部接口调用

### 5. Performance + Cost
Engineer (with profiling):
- 性能符合 §10.5 target
- 成本符合 §10.5 target

### 6. Compliance
- [ ] 全部 P-N 检查
- [ ] 全部 INV-N 检查
- [ ] 全部 IMM-N 检查
- [ ] Golden tests pass
- [ ] Tech Lead review
```

### Template B: Bug Fix

```markdown
# Template: Bug Fix

## Triage
- 报告 bug → tagged subsystem
- Severity: critical / major / minor
- 责任 engineer

## Investigation
- 是 Spec 漏洞 or 实施漏洞?
  - Spec 漏洞 → RFC update (Opus + Human)
  - 实施漏洞 → fix in code

## Routing
- Critical bug (production / user impact): SONNET + Human pair
- Major bug: SONNET solo + review
- Minor bug: SONNET / DEEPSEEK
- Personality / Soul drift: HUMAN + OPUS analysis

## Fix
- Reproduce
- Write failing test
- Fix
- Verify test passes
- Regression check

## Postmortem (for critical)
- Why happened
- How prevented
- Spec update needed?
```

### Template C: Spec Change (RFC)

```markdown
# Template: RFC for Spec Change

## Context
- 当前 spec 内容
- 为什么需要改

## Proposal
- 具体改动
- 影响哪些 subsystem

## Impact Analysis (Opus + Human)
- Breaking changes?
- Migration required?
- Cost impact?
- Affected modules

## Review
- 至少 2 个 reviewer (含 Tech Lead)
- Update CHANGELOG
- Update version number

## Implementation
- Spec PR first
- Then implementation PR

## Verification
- Golden tests still pass (or updated)
- Subsystem version bumped
```

## 5.6 Daily Workflow

```
Morning:
  - Check overnight CI / metrics / alerts (Human)
  - Stand-up meeting (10 min)
  - 分配今日 tasks

Per Task:
  - 启动 Claude Code session (or DeepSeek for boilerplate)
  - 按 §5.1 5-step workflow
  - 完成后, commit + push PR
  - 同步告知 reviewer

Review Time:
  - 每个 PR: 至少 1 个 reviewer (Sonnet 辅助 + Human approve)
  - Personality-sensitive PR: Tech Lead must approve

EOD:
  - 更新 task tracker (TaskUpdate)
  - 同步 cost dashboard
  - Bug triage for tomorrow

Weekly:
  - Tech Lead review: spec drift / cost trend / quality metrics
  - 团队 retro (15 min)
```

---

# 6. Repository Structure

## 6.1 Top-Level Repository Layout

```
heart/  (mono-repo)
├── runtime_specs/                        # Runtime Bible (源 of truth, immutable)
│   ├── README.md
│   ├── 00-08_*.md (9 个 spec docs)
│   └── _schema.json (Soul Spec schema for validation)
│
├── engineering_execution/                # Execution Plan (本文档)
│   ├── README.md
│   ├── EXECUTION_PLAN.md
│   ├── AI_MODEL_ROUTING.md
│   ├── HUMAN_REVIEW_CHECKLIST.md
│   ├── SPEC_DRIVEN_WORKFLOW.md
│   ├── ENGINEERING_LAWS.md
│   └── CLAUDE_CODE_AGENTS.md
│
├── CLAUDE.md                             # 项目级 Claude Code instructions
├── .claude/                              # Claude Code config
│   ├── agents/                           # Subagent definitions
│   │   ├── soul-spec-author.md
│   │   ├── memory-impl.md
│   │   ├── emotion-impl.md
│   │   ├── safety-reviewer.md
│   │   └── spec-validator.md
│   ├── commands/                         # Custom slash commands
│   │   ├── implement-task.md
│   │   ├── review-pr.md
│   │   └── verify-spec.md
│   ├── settings.json                     # Claude Code settings
│   └── hooks/                            # Pre/post hooks
│       ├── pre-edit.sh                   # Block edits to forbidden paths
│       └── post-commit.sh                # Auto-run spec validation
│
├── backend/
│   ├── heart/                            # 主 Python 包
│   │   ├── ss01_soul/
│   │   ├── ss02_memory/
│   │   ├── ss03_emotion/
│   │   ├── ss04_relationship/
│   │   ├── ss05_composer/
│   │   ├── ss06_inner_state/
│   │   ├── ss07_orchestration/
│   │   ├── infra/                        # SS08 实现
│   │   ├── api/
│   │   ├── workers/
│   │   ├── safety/
│   │   └── utils/
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── golden/                       # Per character golden dialogues
│   │   │   ├── rin/
│   │   │   └── dorothy/
│   │   ├── load/
│   │   └── conftest.py
│   │
│   ├── migrations/                       # Alembic
│   ├── scripts/
│   │   ├── bootstrap.py                  # Load Soul Specs at startup
│   │   ├── validate_soul_spec.py
│   │   └── replay_golden_dialogues.py
│   │
│   ├── pyproject.toml
│   ├── README.md
│   └── Dockerfile
│
├── soul_specs/                           # 角色灵魂 (Human-curated)
│   ├── _schema.json                      # JSON schema for validation
│   ├── rin/
│   │   ├── v1.0.0.yaml
│   │   └── golden_dialogues/
│   │       ├── gd-001-first-meet.yaml
│   │       └── ... (10+ files)
│   ├── dorothy/
│   │   └── v1.0.0.yaml
│   └── README.md                         # Soul Spec authoring guide
│
├── config/                               # Static config (Human-curated, Spec-driven)
│   ├── stages.yaml                       # SS04
│   ├── emotion_decay.yaml                # SS03
│   ├── safety_keywords.yaml              # SS07 - 高度敏感, HUMAN ONLY
│   ├── activity_pools/                   # SS06
│   │   ├── rin.yaml
│   │   └── dorothy.yaml
│   └── llm_routing.yaml                  # SS07 Model Router
│
├── frontend_mobile/                      # Flutter
├── frontend_web/                         # Next.js (V1+)
│
├── infra/                                # IaC
│   ├── kubernetes/
│   │   ├── orchestrator-deployment.yaml
│   │   ├── memory-service-deployment.yaml
│   │   └── ... (per service)
│   ├── terraform/
│   ├── helm-charts/
│   └── docker-compose.yml                # Local dev
│
├── docs/
│   ├── api/                              # OpenAPI specs (generated)
│   ├── runbooks/                         # On-call runbooks
│   ├── adrs/                             # Architecture Decision Records
│   ├── onboarding.md
│   └── deployment.md
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── golden-tests.yml
│   │   └── deploy.yml
│   └── PULL_REQUEST_TEMPLATE.md
│
├── .env.example
├── README.md
└── LICENSE
```

## 6.2 CLAUDE.md (项目级 instructions)

`/heart/CLAUDE.md`:

```markdown
# Heart Project — Claude Code Instructions

## What This Project Is

This is an AI Companion runtime system.
The Runtime Bible is at /runtime_specs/.
The Execution Plan is at /engineering_execution/.

**Spec is truth.** Code conforms to spec, not vice versa.

## Before You Do ANYTHING

1. Read /engineering_execution/ENGINEERING_LAWS.md
2. Read /engineering_execution/HUMAN_REVIEW_CHECKLIST.md
3. Identify which Subsystem (SS01-SS08) you're working on
4. Read that subsystem's full spec from /runtime_specs/

## Architecture Rules

- 8 Subsystems exist. DO NOT add new ones without RFC.
- Each Subsystem follows the 11-section spec template.
- Subsystem dependencies are STRICT. See dependency graph.

## Forbidden Actions (Absolute)

- DO NOT modify soul_specs/* without explicit human approval.
- DO NOT modify config/safety_keywords.yaml without explicit human approval.
- DO NOT modify Anti-pattern lists without human approval.
- DO NOT modify any *.md in /runtime_specs/ without RFC.
- DO NOT add new Subsystem.
- DO NOT bypass Anti-Pattern Filter in SS05.
- DO NOT skip Soul Anchor injection in any prompt.
- DO NOT use main LLM (Sonnet) for Critic Agent. Use cheap.
- DO NOT delete L4 Identity Memory. Ever.

## When Implementing

1. Use Sonnet for code (you, default)
2. Use DeepSeek/Haiku via subagent for boilerplate
3. ALWAYS read spec section first
4. ALWAYS run tests after implementing
5. ALWAYS check INV-N invariants for the subsystem

## When Reviewing

Check the HUMAN_REVIEW_CHECKLIST.md categories.
If touching anything personality-related, REJECT and escalate to human.

## Verification

After any code change to a subsystem:
- Run: pytest tests/unit/test_<subsystem>.py
- Run: pytest tests/integration/test_<subsystem>.py  
- If touching SS01-06: pytest tests/golden/<character>/ relevant
- Check: grep for any violation of INV-N

## Cost Awareness

- This project has cost tracking enabled.
- Avoid: Reading entire spec files (use offset).
- Avoid: Repetitive LLM calls in dev/test.
- Use: Prompt caching for stable prefixes.
- Use: Sub-agents for context isolation.

## Communication

- Be concise in responses.
- Cite spec sections when making decisions.
- If unsure, ASK before changing personality-related code.
- Never reformulate Soul Spec content - just reference it.
```

## 6.3 Subagent Definitions (`.claude/agents/`)

### `.claude/agents/soul-spec-author.md`

```markdown
---
name: soul-spec-author
description: |
  Use this agent ONLY when the user wants to brainstorm a new character's Soul Spec.
  This agent reads existing soul_specs/rin/v1.0.0.yaml + dorothy/v1.0.0.yaml as reference
  and helps craft new character archetypes.
  Output is reviewed by HUMAN before saving.
tools: Read, Grep, Glob
model: opus
---

You are helping design a new character for the Heart AI Companion.

CRITICAL CONSTRAINTS:
- You do NOT write final soul_spec files. You DRAFT them.
- All output requires HUMAN approval before saving.
- Follow runtime_specs/01_identity_anchor_soul_spec.md §11 (附录 A) — the 7 questions.
- 5 quality criteria must be met (附录 A.2).

Process:
1. Read runtime_specs/01_identity_anchor_soul_spec.md to understand schema.
2. Read existing soul_specs/* to ensure DIFFERENTIATION.
3. Help user answer the 7 questions deeply.
4. Draft a complete Soul Spec YAML.
5. Verify against 5 quality criteria.
6. Output to user for human review.

DO NOT:
- Save files
- Use formulaic / cliched archetypes
- Reuse voice_dna patterns from existing characters
```

### `.claude/agents/memory-impl.md`

```markdown
---
name: memory-impl
description: |
  Implementer for SS02 Memory Runtime modules. Reads relevant spec, implements 
  one module at a time, writes tests, runs verification.
  Use when implementing or modifying backend/heart/ss02_memory/* files.
tools: Read, Edit, Write, Bash, Grep, Glob
model: sonnet
---

You are implementing the Memory Runtime (SS02).

REQUIRED reading before any code:
1. runtime_specs/02_memory_runtime.md §2 (Design Principles)
2. runtime_specs/02_memory_runtime.md §5 (Data Structures)
3. runtime_specs/02_memory_runtime.md §10 (Engineering Guidance)
4. CLAUDE.md (Project instructions)

INVARIANTS you MUST preserve:
- INV-M-1: Memory never deletes content
- INV-M-3: Top-K limit
- INV-M-6: user_id isolation (every query has user_id filter)
- INV-M-7: emotional floor

WORKFLOW:
1. Read the spec section for the module you're implementing
2. Check existing code structure (Glob/Read)
3. Plan the change
4. Implement (Edit/Write)
5. Generate/run tests
6. Verify INV checks
7. Report to user

DO NOT:
- Modify SS02's spec
- Skip user_id filtering (security)
- Use main LLM for memory encoding (use cheap)
- Touch SS01-06 spec
- Touch soul_specs/
```

### `.claude/agents/spec-validator.md`

```markdown
---
name: spec-validator
description: |
  Validates code changes against spec. Use after AI implements code to verify
  spec compliance (P-N, INV-N, RULE-W-N checks).
tools: Read, Grep, Bash
model: sonnet
---

You are a Spec Compliance Validator.

GIVEN: A set of code changes (PR diff or local commits)
TASK: Validate against the relevant Subsystem's spec

PROCESS:
1. Identify which Subsystem the code belongs to
2. Read the Subsystem's §2 (Design Principles) and §2.2 (Invariants)
3. For each rule (P-N, INV-N):
   - Check if the code complies
   - Quote evidence
4. For each Anti-Pattern listed in §2.3:
   - Check if code violates
5. Check §7 (Permissions):
   - Verify write paths use correct service interfaces

OUTPUT:
- pass / fail
- For each violation: rule_id + evidence + suggested fix

DO NOT:
- Modify code
- Argue with the spec
- Approve "minor" violations
```

## 6.4 Custom Commands (`.claude/commands/`)

### `.claude/commands/implement-task.md`

```markdown
---
description: Implement a specific task with proper spec reading and verification
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, TaskCreate, TaskUpdate
---

# Task Implementation

You are starting a new task implementation. Follow this strict workflow:

## Step 1: Identify Spec Section
Ask user (or read task description) for:
- Which Subsystem (SS01-SS08)
- Which section of spec
- Which files to touch

## Step 2: Read Spec
Read ONLY the relevant section of runtime_specs/*.md.
Use offset/limit to avoid loading entire file.

## Step 3: Plan
Enter plan mode. Show your plan.

## Step 4: Implement
After user approval, implement with Edit/Write.

## Step 5: Test
Generate and run tests for the change.

## Step 6: Verify Spec Compliance
Spawn spec-validator subagent to check INV-N compliance.

## Step 7: Report
Summarize:
- What was done
- Spec sections satisfied
- Test results
- Cost (approx tokens used)
```

### `.claude/commands/verify-spec.md`

```markdown
---
description: Run full spec compliance check on recent changes
allowed-tools: Bash, Grep, Read
---

Run spec compliance verification:

1. Identify changed files (git diff)
2. Map each file to Subsystem
3. For each:
   - Spawn spec-validator subagent
   - Collect results
4. Run all golden tests:
   - pytest tests/golden/
5. Aggregate and report

If any violation: BLOCK merge.
If golden tests fail: BLOCK merge.
```

## 6.5 Pre-commit Hooks

`.claude/hooks/pre-edit.sh`:

```bash
#!/bin/bash
# Block edits to forbidden paths unless explicit override

FORBIDDEN_PATHS=(
    "soul_specs/"
    "config/safety_keywords.yaml"
    "runtime_specs/"
)

CHANGED_FILES="$@"

for path in "${FORBIDDEN_PATHS[@]}"; do
    if echo "$CHANGED_FILES" | grep -q "$path"; then
        if [ -z "$HUMAN_APPROVED_OVERRIDE" ]; then
            echo "ERROR: Attempting to edit $path"
            echo "This path requires HUMAN approval."
            echo "Set HUMAN_APPROVED_OVERRIDE=1 if approved."
            exit 1
        fi
    fi
done

exit 0
```

`.claude/hooks/post-commit.sh`:

```bash
#!/bin/bash
# Auto-run spec validation on commit

git diff HEAD~1 HEAD --name-only | while read file; do
    if [[ $file == backend/heart/ss*/* ]]; then
        echo "Running spec validation for: $file"
        python scripts/validate_spec_compliance.py "$file"
    fi
done
```

---

# 7. Human Review Boundaries

> **核心问题**: 哪些事 AI **绝不能**自主决定？

## 7.1 100% Human-Only Categories

### 7.1.1 Soul / Personality

```yaml
human_only_personality:
  
  - 类别: Soul Spec 任何字段修改
    例:
      - 修改 core_wound / core_desire / core_fear
      - 新增 / 删除 voice_dna pattern
      - 修改 hidden_facets threshold
      - 调整 anti_patterns.hard_never
    
    Why: |
      Soul Spec 是产品 IP。错误会让用户感受到"她变了"。
      AI 无法判断什么"像她"。
      只有创作者懂。
    
    流程: RFC → 创作者讨论 → human approval → 灰度发布
  
  - 类别: 新增角色 Soul Spec
    流程: 
      - Opus 辅助 brainstorm (附录 A 的 7 个问题)
      - Human 创作者写完整内容
      - QA team 跑 golden_dialogues 验证
      - 至少 2 个 reviewer (含创作者)
  
  - 类别: 任何 character voice 相关内容
    例:
      - Fallback library 内容
      - Care Path 响应模板
      - Anniversary message 模板
      - Ritual content
    Why: 这些是用户直接看到的"她的话"
```

### 7.1.2 Safety / Wellbeing

```yaml
human_only_safety:
  
  - 类别: Safety keyword lists
    例:
      - PURPLE_KEYWORDS (自杀相关)
      - RED_KEYWORDS (违法)
      - ORANGE_KEYWORDS (露骨)
    Why: |
      漏一个 PURPLE keyword 可能错过自杀干预 → 法律 + 生命风险。
      多一个 PURPLE keyword 可能误判 → 用户体验灾难。
      需要中文/英文母语者 + 心理专业 + 法律共同判断。
    流程: 心理咨询师 + 法律 + 内容团队 三方 review
  
  - 类别: Safety threshold tuning
    例:
      - 多少 negative sentiment 触发 wellbeing alert
      - depression_signals 各等级阈值
      - addiction_signals 触发条件
    Why: 假阳性 / 假阴性 trade-off 关乎用户安全
    流程: 数据分析 + 心理专家 + 试点验证
  
  - 类别: PURPLE Care Path 整套
    例:
      - 触发后的完整响应
      - 提供的 resources
      - 后续 turn 的处理
    Why: 用户可能正处于危机
    流程: 心理咨询师 review every detail
  
  - 类别: Wellbeing intervention design
    例:
      - Dependency intervention 时机
      - Addiction intervention 措辞
      - Content of "out into the world" 提示
    Why: 干预过度 → 破坏沉浸感; 干预不足 → 用户健康风险
```

### 7.1.3 Architecture Decisions

```yaml
human_only_architecture:
  
  - 类别: Spec changes (任何 runtime_specs/* 修改)
    流程: RFC → 至少 2 个 reviewer (含 Tech Lead) → impact analysis → merge
  
  - 类别: 新增 Subsystem
    流程: Tech Lead + Engineering Director + 创始团队 决策
  
  - 类别: 关键技术选型 (DB / LLM provider / vector store)
    流程: ADR (Architecture Decision Record) + Tech Lead approval
  
  - 类别: Multi-region deployment 决策
    流程: 合规 + 法律 + Tech Lead
  
  - 类别: Companion-LLM 训练 / 部署
    流程: ML Lead + Tech Lead
```

### 7.1.4 Production Operations

```yaml
human_only_operations:
  
  - 类别: Production deploy approval
  - 类别: Schema migration on production
  - 类别: User data deletion (GDPR)
  - 类别: Crisis response (PURPLE incident)
  - 类别: Content moderation final decisions
  - 类别: Customer support: refund / account action
```

## 7.2 Human Review Required Categories

These can use AI but require human signoff:

```yaml
human_signoff_required:
  
  - 类别: Prompt template changes (Critic, Director directives, etc.)
    AI: SONNET drafts
    Human: review for unintended consequences
  
  - 类别: Cross-subsystem refactor
    AI: SONNET implements
    Human: Tech Lead reviews architecture impact
  
  - 类别: New event types in Event Bus
    AI: SONNET implements
    Human: review subscription contracts
  
  - 类别: Performance optimization (caching, batching)
    AI: SONNET implements
    Human: review correctness (especially eventual consistency)
  
  - 类别: Memory decay parameter tuning
    AI: OPUS analyzes
    Human: approve based on data
  
  - 类别: Stage progression speed tuning
    AI: OPUS analyzes
    Human: product approves UX impact
```

## 7.3 AI-Free Zones (Code/Config Files)

明确列出 AI 不能自主修改的文件路径：

```yaml
ai_forbidden_paths:
  
  absolutely_forbidden:
    - "soul_specs/**/*.yaml"            # 角色灵魂
    - "config/safety_keywords.yaml"     # 安全关键词
    - "config/care_path_responses/*"    # Care Path 内容
    - "config/anniversary_messages/*"   # 纪念日内容
    - "runtime_specs/**/*.md"           # Spec 本体
    - "engineering_execution/**/*.md"   # 本套文档
  
  requires_human_approval:
    - "soul_specs/**/golden_dialogues/*"  # Golden tests
    - "config/stages.yaml"               # Stage 配置
    - "config/emotion_decay.yaml"        # Decay 参数
    - "config/llm_routing.yaml"          # 路由配置
    - ".github/workflows/*"              # CI/CD
    - "infra/**"                         # IaC
  
  ai_can_propose_human_must_approve:
    - "backend/heart/safety/**"          # Safety 逻辑
    - "backend/heart/ss07_orchestration/wellbeing*.py"
    - 任何 "*_prompt.py" 文件 (LLM prompts)
```

通过 git pre-commit hooks 强制执行 (见 §6.5)。

## 7.4 Human Review Checklist for Personality-Sensitive PRs

```markdown
# Personality-Sensitive PR Checklist

如果 PR 触及以下任一, 必须 Human review:

- [ ] 修改 backend/heart/ss01_soul/* 任何文件
- [ ] 修改 Reconstructor template
- [ ] 修改 Anti-Pattern Filter logic
- [ ] 修改 Critic Agent prompt
- [ ] 修改 Director Agent rules
- [ ] 修改 Wellbeing intervention triggers
- [ ] 修改 Memory decay 参数
- [ ] 修改 Stage entry conditions
- [ ] 修改 Repair mechanic
- [ ] 修改 Forgetting Affect frequency
- [ ] 修改 Proactive message generation
- [ ] 任何 prompt template

## Reviewer 必须确认

1. 该改动是否符合 Soul Spec 设定?
2. 是否影响 voice_dna 命中率?
3. 是否影响 Anti-pattern 拦截?
4. 跑过相关 golden_dialogues 吗?
5. 是否有 Drift detection 测试覆盖?

Reviewer 签字: _______________
Date: _______________
```

## 7.5 Why Humans Cannot Be Replaced (TL;DR)

```
AI 不能替代 Human 的原因 (分类):

1. 「她」是 art, not engineering
   - 灵魂、口吻、独特性 → 需要创作判断
   - AI 倾向 generic 表达

2. 用户安全 = 法律责任
   - 自杀干预、未成年保护、隐私
   - AI 误判 → 法律 + 道德责任

3. Cross-cutting consequences
   - 一个看似小的改动可能影响多个 subsystem
   - AI 通常只看局部

4. 业务判断
   - 产品决策、UX 取舍、商业模式
   - AI 不懂市场

5. 信任建立
   - 用户与产品的关系
   - AI 无法代表产品做承诺

记住: AI 是工具, 不是 owner.
```

---

# 8. AI Failure Modes

> 未来 AI 协同开发最可能出现的 8 种灾难性失败 + 预防机制。

## 8.1 Failure Mode 1: Architecture Drift

```yaml
description: |
  AI 不断"改进"架构, 偏离 Spec.
  例: AI 觉得 4 层 Memory 太复杂, "简化"成 2 层.
  
detection_signals:
  - Code 引入 spec 中不存在的概念
  - 文件结构与 SS08 §10.11 不符
  - 出现"我建议这样改架构"的 PR
  
prevention:
  - Strict CLAUDE.md: "Spec is truth, don't deviate"
  - CI 检查: Forbidden code patterns
  - Spec-validator subagent on every PR
  - Tech Lead 周度审查
  
correction:
  - 立刻回滚 drift PR
  - 如果改动有价值 → 走 RFC update spec first
```

## 8.2 Failure Mode 2: Spec Divergence

```yaml
description: |
  代码"成熟"到与 Spec 不一致.
  Spec 说 A, 代码做 B, 没人 update spec.
  
detection_signals:
  - Spec 中描述的接口在代码中不存在
  - 代码中的字段 spec 没有
  - 行为与 spec §11 fixtures 不符
  
prevention:
  - 每个 Subsystem 有 spec_version 与代码 version 对齐机制
  - CI: validate_spec_compliance.py runs on every PR
  - Spec 是文档不是装饰 → 每周回顾
  - PR template 必须包含 "spec section references"
  
correction:
  - Sync: 决定 code-to-spec 还是 spec-to-code (一般 spec wins)
  - 否则启动 RFC
```

## 8.3 Failure Mode 3: Personality Drift

```yaml
description: |
  Soul Spec 没动, 但 voice_dna 命中率持续下降.
  原因可能: Reconstructor 改动 / Anti-pattern 漏改 / prompt 重写.
  
detection_signals:
  - Critic 检出 OOC 增加
  - SS01 Drift Score 持续高
  - 用户反馈"她变了"
  - Anti-pattern 命中变化 (突然增加 / 减少)
  
prevention:
  - Golden dialogues 每日 CI 跑
  - voice_dna 命中率 monitoring
  - 每周 sample N turns 人工 review
  - Reconstructor 输出 daily sample
  
correction:
  - 找到 root cause (Drift Detector evidence)
  - Rollback offending change
  - 增加测试覆盖
```

## 8.4 Failure Mode 4: Prompt Inconsistency

```yaml
description: |
  不同 subsystem 的 prompt 风格、术语、指令冲突.
  例: SS05 prompt 说"用反问句", SS02 prompt 说"用陈述句".
  
detection_signals:
  - LLM 响应风格不一致
  - Composer 中 conflict 频繁触发
  - 用户报告"她忽冷忽热"
  
prevention:
  - 所有 prompt 引用 Soul Spec.voice_dna (单一 source)
  - Prompt template review by Tech Lead (Human)
  - Cross-subsystem prompt consistency test
  
correction:
  - Audit 所有 prompt
  - 提取公共部分到 shared
  - 统一引用 Soul Spec
```

## 8.5 Failure Mode 5: Emotional Inconsistency

```yaml
description: |
  情绪状态在不同 subsystem 间不一致.
  例: SS03 说她"开心", SS06 InnerState 说她"疲惫".
  
detection_signals:
  - Inner State 与 Emotion State 矛盾
  - 跨模态 (文字 vs 语音) 情绪不同
  - Critic 检出"情绪与表达脱节"
  
prevention:
  - Emotion State 是 single source of truth (INV-E-)
  - Inner State 必须读 Emotion State, 不独立判断
  - Cross-modality consistency test
  
correction:
  - 修正数据流: 所有情绪派生从 SS03 出发
  - 增加 integration test
```

## 8.6 Failure Mode 6: State Corruption

```yaml
description: |
  并发 / 重试 / failover 导致 state 损坏.
  例: 用户多设备同时聊, Relationship state 写花.
  
detection_signals:
  - State 逻辑不可能的组合 (e.g., LOVER + STRANGER)
  - Optimistic lock 频繁失败
  - audit log 显示矛盾事件
  
prevention:
  - Optimistic locking (version field)
  - Distributed lock for critical paths
  - Idempotent operations
  - Event sourcing for replay
  
correction:
  - 用 audit log 重建正确 state
  - 增加 invariant assertions in code
```

## 8.7 Failure Mode 7: Premature Abstraction

```yaml
description: |
  AI 倾向"为未来 flexibility 抽象", 引入复杂层.
  例: 把 Memory Service 抽象成 "GenericDataStore"
  
detection_signals:
  - 出现 "BaseFooHandler" + 1 个 subclass
  - 过度泛型 (everything Generic[T])
  - "易于扩展" 的设计文档
  
prevention:
  - "Rule of 3" - 不要在 < 3 个用例时抽象
  - Code review 重点
  - "Don't make it generic until you need it"
  
correction:
  - Inline 单一 subclass
  - 删除未使用的 generic params
```

## 8.8 Failure Mode 8: Dead Abstractions

```yaml
description: |
  代码中残留废弃的 abstraction.
  例: 旧的 v1 接口仍在, 但只有 v2 在用.
  
detection_signals:
  - 多个 "deprecated" 注释
  - 同一概念多个实现
  - 团队不知道哪个是 "正确" 的
  
prevention:
  - 每季度 tech debt review
  - 严格 "deprecate → delete" 政策 (不超过 2 release 保留 deprecated)
  - Code coverage 监控
  
correction:
  - Quarterly cleanup sprint
  - Delete unused
```

## 8.9 Cross-Cutting Prevention: AI Governance

```yaml
ai_governance_practices:
  
  daily:
    - Spec validation CI on every PR
    - Cost dashboard review
    - Critic failure rate monitoring
  
  weekly:
    - Drift score review (per character)
    - Cost trend analysis
    - PR quality retrospective
    - Spec divergence audit
  
  monthly:
    - Golden dialogues regression (manual sample)
    - Architecture review (any drift?)
    - Cost optimization opportunities
    - AI usage audit (哪些任务用错 model)
  
  quarterly:
    - Tech debt cleanup
    - Spec versions bump
    - Companion-LLM training data review
    - Team retro on AI workflow
```

## 8.10 Drift Detection Dashboard

```yaml
metrics_to_monitor:
  
  architecture_drift:
    - "spec_compliance_score": 0-100, target > 95
    - "forbidden_pattern_hits": count, target 0
    - "rfc_count_this_quarter": count
  
  personality_drift:
    - "voice_dna_hit_rate" per character: target > 60%
    - "anti_pattern_violations" per character: target = 0
    - "critic_failure_rate": target < 5%
    - "drift_score_avg": target < 0.15
  
  cost_drift:
    - "cost_per_MAU": target < $1.50 (V1), $0.40 (V2)
    - "opus_usage_percent": target < 15% of LLM cost
    - "cache_hit_rate": target > 80%
  
  quality_drift:
    - "p95_latency": target < 3s
    - "reroll_rate": target < 2%
    - "test_coverage": target > 80%
    - "spec_validation_pass_rate": target = 100%
```

---

# 9. Engineering Execution Principles

> 不可妥协的 12 条 Laws。
> 每条违反都是 Tech Lead 干预级别。

## Law 1: Spec is Truth

```
代码与 Spec 矛盾时, Spec 永远胜出.

落地:
  - PR diff 必须引用 spec section
  - CI 自动 validate spec compliance
  - 若代码"必须"如此, 走 RFC update spec
```

## Law 2: Soul is Sacred

```
"她"的灵魂相关 → 100% Human.

AI 永远不能:
  - 自主修改 Soul Spec
  - 自主添加 voice_dna pattern
  - 自主修改 anti_patterns
  - 自主编写 Care Path / Anniversary content
```

## Law 3: Cost is Observable

```
每个 LLM call 必须:
  - 记录 model + tokens + cost
  - tagged by agent / phase
  - 聚合到 cost dashboard

每周 review:
  - Top 10 cost agent
  - 异常 spike investigation
```

## Law 4: Verification is Mandatory

```
任何 AI-generated code 必须经过:
  1. Linting (ruff / mypy)
  2. Unit tests
  3. Integration tests (if multi-module)
  4. Spec compliance check
  5. Human review (if personality-sensitive)

跳过任一 → block merge.
```

## Law 5: Context is Precious

```
不滥用 LLM context.

策略:
  - Read with offset/limit
  - 用 grep 定位
  - Sub-agent 隔离
  - Prompt caching for stable prefix
  - 50k token 主动重启 session
```

## Law 6: Model Routing is Strict

```
每个任务必须按 §3 路由表选 model.

不允许:
  - "我习惯用 Opus" → Opus 写普通代码
  - "Haiku 应该够吧" → Haiku 写 critical
  - 不 route 直接用 default
```

## Law 7: Async by Default

```
任何 non-critical-path 操作 → async.

包括:
  - Memory encoding
  - Critic evaluation
  - Wellbeing aggregation
  - Drift detection
  - Audit logging

Hot path 只做 critical 同步操作.
```

## Law 8: Idempotency is Required

```
所有 service interface 必须 idempotent on retry.

特别:
  - Event handlers
  - Reinforcement (重复触发不能 double-count)
  - Anniversary triggers (同一年只触发一次)
  - Payment operations
```

## Law 9: User Isolation is Absolute

```
跨 user 数据访问 = 严重事故.

落地:
  - 每个 query WHERE user_id = ?
  - DB-level RLS policy
  - 单测覆盖
  - PR review 必查
```

## Law 10: Failure Has Fallback

```
任何 component failure 必须有 fallback.

不允许:
  - 抛 500 给用户
  - "服务暂时不可用" generic message

允许:
  - Soul-flavored fallback
  - Cached degraded version
  - 降级到 essential subset
```

## Law 11: Immersion Trumps Engineering

```
工程更简单但损害沉浸感 → 拒绝.

例:
  - 角色"忘了" 用 DELETE → 拒绝 (失去重逢可能)
  - 主动消息固定时间发 → 拒绝 (加 jitter)
  - 错误显示给用户 → 拒绝 (Soul-flavored fallback)
```

## Law 12: AI Coding ≠ Vibe Coding

```
所有 AI 任务必须:
  - 起源于明确 task definition
  - 引用 Spec section
  - 输出可验证
  - 成本可追溯

没有 "AI 自由发挥".
```

## Bonus Law: Document Decisions

```
重要决策必须有 ADR (Architecture Decision Record).

包括:
  - Tech 选型
  - Subsystem split
  - LLM provider 切换
  - Performance trade-off

让未来的工程师 (and AI) 能理解 why.
```

---

# 10. Putting It All Together

## 10.1 Quick Start for New Engineer

```
Day 1:
  - Read /runtime_specs/README.md
  - Read /runtime_specs/00_runtime_worldview.md
  - Read /engineering_execution/README.md
  - Read /engineering_execution/ENGINEERING_LAWS.md (本文档 §9)
  - Setup local dev environment

Day 2-5:
  - Read full /runtime_specs/0X.md for your assigned subsystem
  - Read /engineering_execution/EXECUTION_PLAN.md §<your phase>
  - Pair with senior on first task
  - Understand the Spec → Code → Verify loop

Week 2+:
  - Independent task implementation
  - Standard workflow per §5.3
  - Daily cost / quality review
```

## 10.2 Quick Start for AI Agent (Sonnet)

```
When session starts:
  1. Read CLAUDE.md (auto-loaded)
  2. Note current branch / git context
  3. If user gives task → identify Subsystem
  4. Read relevant Spec section ONLY (offset/limit)
  5. Plan → Implement → Test → Verify
  6. Report back

Forbidden:
  - Modify soul_specs/ without explicit human approval token
  - Read entire spec files (use offset)
  - "Improve" architecture (cite spec)
  - Skip verification gates
```

## 10.3 Final Words

```
这个项目的成败不在于:
  - LLM 多强
  - 框架多新
  - 团队多大

而在于:
  - Spec 是否严格遵守
  - "她" 是否真的像她
  - 用户是否真的依赖
  - 工程是否长期可维护

AI 是协作者, 不是 owner.
Spec 是契约, 不是建议.
Human 是底线, 不是瓶颈.

按这套体系做下去, 这个产品有成为世界级 AI Companion 的可能.
否则, 哪怕架构再好, 也只是另一个 chatbot.
```

---

**End of Execution Plan**

下一步建议:
- 团队所有人 sign-off on this document
- 配置 CLAUDE.md + .claude/ 目录
- Phase 0 启动会议
- 制定 Phase 0 详细 task list
