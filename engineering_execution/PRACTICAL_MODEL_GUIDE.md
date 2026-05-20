# 实操指南 — 每一步用什么模型 + 怎么写 Prompt

> **目的**: 把抽象的"用 Sonnet"具体化到可复制粘贴的 prompt
> **配套**: AI_MODEL_ROUTING.md (理论) + 本文档 (实操)
> **使用方式**: 遇到任务 → 查表 → 复制 prompt → 微调 → 执行

---

# 第一部分: 你的工具箱

## 1.1 可用工具与模型

| ID | 工具 | 模型 | 适用 | 启动方式 |
|----|------|------|------|---------|
| **CC-Opus** | Claude Code CLI | Opus 4.7 | 架构决策 / 复杂算法 | `claude --model opus` |
| **CC-S46** | Claude Code CLI | Sonnet 4.6 | **主力**: 实现 / refactor / review | `claude --model sonnet` (默认即 4.6) |
| **CC-S45** | Claude Code CLI | Sonnet 4.5 | 备选: focused 任务 | `claude --model claude-sonnet-4-5` |
| **CC-Haiku** | Claude Code CLI | Haiku 4.5 | Agentic boilerplate | `claude --model haiku` |
| **CC-DS** | Claude Code CLI | DeepSeek V4 (via API key swap) | 大批量 cheap agentic | 配置 ANTHROPIC_BASE_URL 指向 deepseek |
| **VS-Continue** | VSCode + Continue | DeepSeek V4 | 单文件 inline / 局部 | VSCode 内 Continue 插件 |

## 1.2 这 6 个工具如何分工

```
                    任务复杂度 ▲
                              │
       Architecture           │     CC-Opus
       决策 / Cross-SS        │
                              │
                              │
       Multi-file impl       │     CC-S46 (主力)
       Complex refactor       │     (or CC-S45 specific)
                              │
                              │
       Simple multi-file      │     CC-Haiku  / CC-DS
       Boilerplate batch      │
                              │
                              │
       Single-file局部        │     VS-Continue
       Inline completion      │
                              │
                              └─────────────────────────► 任务范围
```

## 1.3 一图速查：什么场景用什么

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  我要做什么?                                              │  │
│  └─────────────────────────┬────────────────────────────────┘  │
│                            │                                    │
│   ┌────────────────────────┼─────────────────────────┐         │
│   ▼                        ▼                         ▼         │
│ 触及 Soul/        架构 / 算法 /              实施 / refactor    │
│ Safety?         Cross-Subsystem 设计?                            │
│   │                        │                         │         │
│   ▼                        ▼                         ▼         │
│ HUMAN          CC-Opus + HUMAN review            CC-S46         │
│ (+ CC-Opus    (1 个 session 集中讨论)         (主力, default)   │
│  for brainstorm)                                   │           │
│                                                    ▼           │
│                                          多文件 / 完整功能?     │
│                                                    │           │
│                                          ┌─────────┴─────────┐ │
│                                          ▼                   ▼ │
│                                       CC-S46              单文件 │
│                                                              │ │
│                                                              ▼ │
│                                              纯 Boilerplate?   │
│                                                              │ │
│                                                ┌────────────┘ │
│                                                ▼              │
│                                  ┌─────────────┴────────────┐ │
│                                  ▼                          ▼ │
│                              CC-Haiku /                VS-Continue│
│                              CC-DS (批量)              (inline)│
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

# 第二部分: Sonnet 4.5 vs 4.6 选择

## 2.1 默认: Sonnet 4.6

**99% 情况用 4.6**。它是最新、最强的 Sonnet。

```bash
claude   # 默认 Sonnet 4.6
```

## 2.2 何时考虑 Sonnet 4.5

仅在以下情况：

1. **预算紧张** — 4.5 cost 略低 (历史 pricing 差异)
2. **任务非常 focused** — 单文件、明确边界、Sonnet 4.6 偶尔会"过度发挥"
3. **重现旧行为** — 某些场景 4.5 输出更稳定

```bash
claude --model claude-sonnet-4-5
```

## 2.3 规则

```
启动 session 时:
  默认 → Sonnet 4.6
  
切换到 4.5:
  - 在 session 内: /model claude-sonnet-4-5
  - 启动时: claude --model claude-sonnet-4-5

绝不:
  - 主观感觉切换
  - 没原因地选 4.5

如果用 4.5, 在 commit 中注明原因.
```

---

# 第三部分: Phase 0 — Foundation (Week 1-3) 详细操作

> 目标: 建好基础设施，让后续 7 个 Subsystem 可以"上车"。
> 主力 tool: **CC-S46** + VS-Continue (for inline)

## 3.1 Task: 搭建项目骨架

**Tool**: CC-S46
**Why**: Multi-file, 标准 scaffolding, Sonnet 完全够用

**Prompt**:

```
Initialize the Heart project backend structure.

Read /runtime_specs/08_engineering_architecture.md 附录 D (项目目录结构).

Create:
1. backend/pyproject.toml (Python 3.11, FastAPI 0.115+, SQLAlchemy 2.0+, asyncpg, redis, etc.)
2. backend/heart/ directory with empty stubs for ss01_soul/, ss02_memory/, ... ss07_orchestration/, infra/
3. backend/heart/api/main.py with FastAPI app + health endpoint
4. docker-compose.yml for local dev (postgres pgvector, redis)
5. .env.example
6. Makefile with: dev, test, lint, migrate

Use the exact stack listed in §10.1 of SS08. Don't add extra deps.

Show me each file as you create it. Don't run anything yet.
```

## 3.2 Task: 设置 Alembic Migration

**Tool**: CC-Haiku (boilerplate)
**Why**: 纯标准 setup, Haiku 够

**Prompt**:

```
Setup Alembic for the Heart project at backend/migrations/.

- Configure alembic.ini with async support
- Use DATABASE_URL from environment
- Set up base migration env.py
- Generate empty initial revision (no tables yet)

Reference: SQLAlchemy 2.0 async pattern.
```

## 3.3 Task: 实现 LLM Provider 抽象

**Tool**: CC-S46
**Why**: Critical infrastructure, multi-provider, 不能错

**Prompt**:

```
Implement the LLM Provider abstraction per /runtime_specs/07_agent_orchestration.md §3.5 + §6.1.

Read those two sections first (use Read with offset, don't load entire file).

Create:
1. backend/heart/infra/llm_providers/base.py — abstract LLMProvider class
2. backend/heart/infra/llm_providers/anthropic.py — Anthropic provider (streaming + non-streaming)
3. backend/heart/infra/llm_providers/deepseek.py — DeepSeek provider (uses openai SDK)
4. backend/heart/infra/llm_providers/registry.py — provider registry + lookup
5. tests/unit/test_llm_providers.py — basic interface tests (with mocked HTTP)

Requirements:
- Streaming API: AsyncIterator[str]
- Non-streaming: returns str
- Cost estimation: estimate_cost(prompt, params) -> float
- Circuit breaker hookable (don't implement breaker, just leave interface)
- Type-hinted thoroughly

Don't implement Model Router yet (that's SS07 task). Just providers.

After writing, run:
  pytest tests/unit/test_llm_providers.py -v
```

## 3.4 Task: 实现 Cost Tracker

**Tool**: CC-S46
**Why**: Critical for cost control, needs care

**Prompt**:

```
Implement LLM Cost Tracker per /runtime_specs/08_engineering_architecture.md §6.2.

Read that section first.

Create:
- backend/heart/infra/llm_cost_tracker.py
- Methods: record(LLMCall), get_user_daily_cost(user_id), get_aggregated_metrics()
- Storage: Redis (per-user daily counter) + Prometheus metric export
- Pricing data from PRICING constant (use the table in §6.2)

Don't implement Prometheus client config (Phase 0 separate task). Just emit metrics via standard interface.

Add tests for cost computation correctness.
```

## 3.5 Task: K8s Deployment YAML

**Tool**: CC-Haiku
**Why**: 纯模板, boilerplate

**Prompt**:

```
Generate Kubernetes deployment YAMLs per /runtime_specs/08_engineering_architecture.md §10.2.

Read just the orchestrator-deployment.yaml example.

Create equivalent deployments for:
1. orchestrator-service (already shown, copy)
2. memory-service
3. emotion-service
4. relationship-service
5. composer-service
6. inner-state-service
7. soul-service

All in infra/kubernetes/.

Use the same pattern: rolling update, HPA, topology spread, health probes.
Resources per §3.2 of SS08.

Don't include service.yaml or ingress.yaml — those are separate.
```

## 3.6 Task: CI/CD Pipeline 初版

**Tool**: CC-S46 (more careful than boilerplate, since CI gates important)
**Why**: 影响所有 PR

**Prompt**:

```
Setup GitHub Actions workflow at .github/workflows/ci.yml.

Per /runtime_specs/08_engineering_architecture.md §10.3.

Jobs:
1. lint (ruff + mypy)
2. unit-tests (pytest tests/unit)
3. integration-tests (with services: postgres+pgvector, redis)
4. schema-validation (validate config/*.yaml files)
5. build-docker (no push, just verify)

Don't add:
- Deploy job (that's later phase)
- Golden tests (no soul specs yet)

Use Python 3.11. Cache pip deps.

Show me the YAML for review.
```

## 3.7 Phase 0 完整 Session 安排

```
Day 1-2 (Setup):
  Session 1 (CC-S46): 项目骨架 (3.1)
  Session 2 (CC-Haiku): Alembic setup (3.2)
  Session 3 (CC-S46): Docker compose 微调
  
  Continue + VSCode 全程: inline fixes / imports / type stubs

Day 3-5 (Infra Code):
  Session 4 (CC-S46): LLM Provider 抽象 (3.3)
  Session 5 (CC-S46): Cost Tracker (3.4)
  Session 6 (CC-Haiku): K8s YAMLs (3.5)

Day 6-8 (Observability + Auth):
  Session 7 (CC-S46): Prometheus + OpenTelemetry setup
  Session 8 (CC-S46): JWT auth scaffolding
  Session 9 (CC-S46): Redis client + base patterns

Day 9-12 (CI/CD + Polish):
  Session 10 (CC-S46): CI/CD (3.6)
  Session 11 (CC-S46): Echo bot endpoint (cut criteria)
  Session 12 (Human + CC-S46): End-to-end verification
```

Phase 0 Token 预算: ~$50-100 LLM cost (主要 Sonnet 4.6 + 少量 Haiku)

---

# 第四部分: Phase 1 — Soul Spec + Anchor (Week 4-7)

> 主力: **HUMAN** (Soul authoring) + **CC-Opus** (algorithm design) + **CC-S46** (impl)

## 4.1 Task: 撰写 Rin Soul Spec

**Tool**: HUMAN (with CC-Opus brainstorm)
**Why**: 100% Human-only (Law 2)

**Step 1 — Brainstorm session 启动**:

```bash
claude --model opus
```

**Prompt** (在 session 中):

```
I'm designing a new character for the Heart AI Companion product. Help me 
brainstorm her Soul Spec.

Constraints:
- Read /runtime_specs/01_identity_anchor_soul_spec.md 附录 A — the 7 questions.
- Read /runtime_specs/01_identity_anchor_soul_spec.md §5.1 — the schema example for Rin.
- Read existing soul_specs/ to ensure NEW character is differentiated.

Reference: This new character is "Rin (神无月 凛)" — see her in the existing 
spec example. But I need to deepen and finalize her Soul Spec.

Process:
1. Walk me through the 7 questions for Rin
2. For each, push me to go deeper than my first answer
3. Ensure voice_dna patterns are TRULY distinctive (not generic 御姐)
4. Help craft 3 hidden_facets with realistic thresholds
5. Suggest anti_patterns - what would Rin NEVER say?

Output: A draft YAML I'll review and finalize manually.
DO NOT save files. DO NOT use the Write tool. Just brainstorm.

Start by reading the spec and existing soul_specs/, then ask me question 1.
```

**Step 2 — Human 写最终版**:

```
人工在 soul_specs/rin/v1.0.0.yaml 中手写最终版本.
基于 Opus brainstorm 的输出, 但 final wording 必须人工敲定.
绝不让 AI 自动 Write 文件.
```

**Step 3 — Golden Dialogues 撰写**:

```bash
claude --model opus
```

**Prompt**:

```
Help me write golden_dialogues for Rin per SS01 §5.1 (test_fixtures).

I have the final Soul Spec at soul_specs/rin/v1.0.0.yaml.

Read it. Then:

1. Generate 10 golden_dialogue scenarios covering:
   - First meeting (gd-001)
   - 3-day absence return (gd-002)
   - Vulnerable disclosure response (gd-003)
   - Cold war moment
   - Reunion after 30 days
   - User compliments her
   - User mentions another person
   - User asks about her past
   - Late night conversation
   - Anniversary (her version of)

2. For each:
   - Context (days since first, stage, etc.)
   - User message
   - Expected properties:
     - sentence_length range
     - must_contain_pattern: ["…", specific phrases]
     - must_not_contain: anti-pattern adjacent terms
     - must_match_voice_dna: [vd-001, vd-002, ...]
   - 2-3 example_acceptable_responses

3. CRITICAL: examples must come from MY (Human) judgment of what Rin would say.
   You suggest, I approve/edit.

Output: YAML format for each, I'll save to soul_specs/rin/golden_dialogues/.
```

## 4.2 Task: 实现 Schema Validator

**Tool**: CC-S46
**Why**: 标准 implementation, spec 详细

**Prompt**:

```
Implement Soul Spec Schema Validator per /runtime_specs/01_identity_anchor_soul_spec.md.

Read §5.1 (the full Soul Spec schema example).

Create:
1. backend/heart/ss01_soul/schema_validator.py
   - Pydantic models for SoulSpec, IdentityAnchor, CognitiveStyle, etc.
   - Match the YAML schema exactly
   - All fields strict (no extras, no nulls where spec says required)
2. backend/heart/ss01_soul/registry.py
   - SoulRegistry: loads YAML at startup, validates, caches
   - get_soul(character_id) -> SoulSpec
   - Reject load if validation fails
3. tests/unit/test_soul_validator.py
   - Test loads soul_specs/rin/v1.0.0.yaml passes
   - Test malformed YAML fails
   - Test missing required fields fails

Use yaml.safe_load. NOT yaml.load.

After implementing, run: pytest tests/unit/test_soul_validator.py
```

## 4.3 Task: Anchor Block 生成器

**Tool**: CC-Opus
**Why**: Anchor 模板是核心, 设计需要 deep reasoning

**Prompt**:

```
Design and implement the Anchor Injector per /runtime_specs/01_identity_anchor_soul_spec.md §6.2.

Read §3.4 (Injection Cadence), §6.2 (templates), §10.5 (predicate compilation).

Implement:
1. backend/heart/ss01_soul/anchor_injector.py
   - generate_full_anchor(soul, activation_state) -> str (with §6.2.1 template)
   - generate_light_anchor(soul, activation_state) -> str (with §6.2.2)
   - generate_reinforce_anchor(soul, drift_evidence) -> str (with §6.2.3)
2. backend/heart/ss01_soul/anchor_mode_decider.py
   - decide_mode(activation_state, turn_index, drift_score) -> AnchorMode
   - Per §3.4 cadence rules

CRITICAL design decisions to discuss with me FIRST before coding:
- Token count estimation: which tokenizer? (Anthropic vs heuristic)
- Pre-compilation: should we pre-format anchor template strings at startup?
- Threading: anchor_injector should be thread-safe (multi-request)

Discuss these 3 first. Don't write code until I approve approach.
```

## 4.4 Task: Drift Detector

**Tool**: CC-Opus (algorithm design) → CC-S46 (implementation after approved)

**Step 1 (Opus)**:

```bash
claude --model opus
```

**Prompt**:

```
Design the Drift Detector algorithm per /runtime_specs/01_identity_anchor_soul_spec.md §6.5 (机制 B).

Constraints:
- Cheap LLM only (Haiku/DeepSeek)
- Sample last 5 assistant responses every 5 turns
- Pre-filter heuristic to skip 70% of turns
- Output: drift_score [0, 1] + evidence

Design questions I need answered:
1. What's the pre-filter heuristic? (regex + statistical signal)
2. What's the LLM prompt? (concrete template)
3. How is drift_score computed from LLM output?
4. How to handle LLM-detected false positives (drift_score noisy)?
5. What sampling strategy for the 5 responses?

Output: Design doc (markdown) explaining algorithm.
After I approve, switch to CC-S46 for implementation.

Don't code yet. Design first.
```

**Step 2 (Sonnet 4.6, after approval)**:

```bash
/clear  # or restart session
claude
```

**Prompt**:

```
Implement Drift Detector per the design we just approved.

[paste the approved design doc here, or reference: docs/design/drift_detector.md]

Create:
- backend/heart/ss01_soul/drift_detector.py
- Pre-filter (heuristic, < 5ms)
- LLM-based deep check (only if pre-filter triggers)
- Cost-capped: max 20 LLM calls/user/day

Tests:
- tests/unit/test_drift_detector.py
- Test pre-filter accuracy (synthetic data)
- Test cost cap

Use anthropic.Haiku as cheap model. Mock in tests.
```

## 4.5 Task: Resonance Tracker

**Tool**: CC-S46
**Why**: Standard implementation, spec clear

**Prompt**:

```
Implement Resonance Tracker per /runtime_specs/01_identity_anchor_soul_spec.md §3.2 + §5.2.

This tracks user × character resonance score based on Soul.resonance_triggers (§5.1).

Create:
- backend/heart/ss01_soul/resonance_tracker.py
- track_event(user_id, character_id, trigger_cue) -> ResonanceEvent
- get_score(user_id, character_id) -> float [0, 1]
- Respects daily caps per trigger (§5.1 max_per_day)
- Apply weights from soul.resonance_triggers

State storage:
- Read/write via SoulActivationStateService (do not write directly to DB)

Tests with mocked SoulActivationStateService.
```

## 4.6 Task: Hidden Facet Unlocker

**Tool**: CC-S46
**Why**: Multi-condition logic, but spec clear

**Prompt**:

```
Implement Hidden Facet Unlocker per /runtime_specs/01_identity_anchor_soul_spec.md §5.1 (hidden_facets).

Create:
- backend/heart/ss01_soul/facet_unlocker.py
- check_unlock_conditions(soul, activation_state, recent_events) -> List[FacetId]
- Apply corroboration_count (multi-signal requirement)
- Emit "soul.facet.unlocked" event via Event Bus

Constraints:
- corroboration_count required (not single signal)
- Per facet thresholds (resonance_score, required_triggers)
- Idempotent (don't unlock same facet twice)

Reference §5.1 example for Rin's 3 facets.

Tests cover:
- Threshold not met → no unlock
- Single signal → no unlock (corroboration required)
- Multi signal + threshold met → unlock + event emitted
```

## 4.7 Phase 1 Session 安排

```
Week 4:
  Day 1-3: HUMAN — Rin Soul Spec drafting (with CC-Opus brainstorm)
  Day 4-5: HUMAN — Dorothy Soul Spec drafting
  
Week 5:
  Day 1: HUMAN + CC-Opus — Golden Dialogues for Rin (10+)
  Day 2: HUMAN + CC-Opus — Golden Dialogues for Dorothy (10+)
  Day 3-5: CC-S46 — Schema Validator + Registry (4.2)
  
Week 6:
  Day 1: CC-Opus — Anchor design discussion (4.3 step 1)
  Day 2-3: CC-S46 — Anchor Injector implementation (4.3 step 2)
  Day 4: CC-Opus — Drift Detector design (4.4 step 1)
  Day 5: CC-S46 — Drift Detector impl (4.4 step 2)
  
Week 7:
  Day 1-2: CC-S46 — Resonance Tracker (4.5) + Facet Unlocker (4.6)
  Day 3: CC-S46 — Soul Activation State Service integration
  Day 4: CC-S46 — Cross-component integration tests
  Day 5: HUMAN — Final review + golden_dialogues replay
```

Phase 1 Token 预算: ~$150-250 LLM cost

---

# 第五部分: Phase 2 — Memory Runtime (Week 8-12) 详细操作

> 主力: **CC-S46** (大部分) + **CC-Opus** (Decay/Reconstructor) + **CC-Haiku** (boilerplate)

## 5.1 Task: PG Schema + SQLAlchemy Models

**Tool**: CC-Haiku
**Why**: 纯翻译 (从 spec §5 到 SQLAlchemy code)

**Prompt**:

```
Generate SQLAlchemy 2.0 models for SS02 Memory Runtime.

Read /runtime_specs/02_memory_runtime.md §5 (Data Structures) and §10.2 (PG Schema).

Create:
1. backend/heart/ss02_memory/models.py — SQLAlchemy models for:
   - EpisodicMemory (L2)
   - FactNode (L3)
   - IdentityMemory (L4)
   - MemoryEncodingEvent
   - ConsolidationJob

2. migrations/versions/XXX_add_memory_tables.py — Alembic migration

Match the SQL schema in §10.2 EXACTLY:
- Same column names, types, constraints
- Same indexes (HNSW for vectors)
- Same partitioning (BY HASH user_id × 32)

Use:
- sqlalchemy.dialects.postgresql for jsonb, vector types
- pgvector.sqlalchemy for vector columns

Don't add fields not in §10.2.
Don't add helper methods (that's for service layer).
```

## 5.2 Task: Memory Service Interface

**Tool**: CC-S46
**Why**: Critical interface, but well-specced

**Prompt**:

```
Implement the Memory Service skeleton per /runtime_specs/02_memory_runtime.md §10.3.

Read §7 (Agent Integration) and §10.3 carefully.

Create:
- backend/heart/ss02_memory/service.py
- MemoryService class with all methods listed in §10.3:
  - Read API: retrieve(), get_l4(), get_recent_episodes(), get_anniversaries()
  - Write API: encode_fast(), queue_llm_encoding(), reinforce(), user_request_forget()
  - Lifecycle: apply_decay_batch(), run_consolidation(), promote_to_l4()

For each method:
- Use type hints (per §5 schemas)
- Implement as NotImplementedError stub for now (we'll fill in across phase)
- Add docstring referencing spec section

Constraints (INV-M):
- INV-M-6: every query has user_id filter (enforce in shared helper)
- INV-M-3: top_k limit (default 5, max 10)

Add base test scaffolding (tests/unit/test_memory_service.py).
Don't implement actual logic yet.
```

## 5.3 Task: Fast Heuristic Encoder

**Tool**: CC-S46
**Why**: Sync path, performance critical

**Prompt**:

```
Implement Fast Heuristic Encoder per /runtime_specs/02_memory_runtime.md §3.4 (阶段 1) + §10.4.

Read those sections.

Create:
- backend/heart/ss02_memory/encoder/fast.py
- FastEncoder.encode(turn: Turn) -> FastSignals
- Sub-50ms latency (no LLM, pure heuristic)
- Detect:
  - Identity signals (name, birthday, age) via regex
  - Sentiment via lexicon (use VADER or simple positive/negative word list)
  - Keyword fact patterns (我有/养/喜欢/工作 X)

Add lexicon file:
- config/encoder_lexicon.yaml (positive_words, negative_words, identity_patterns)

Tests:
- 10 sentences of various types
- Performance: assert avg latency < 30ms over 1000 calls

Use:
- re (compiled regex, pre-compiled at startup)
- Plain dict lookups (no spacy/NLTK — too slow)
```

## 5.4 Task: LLM Encoder Worker

**Tool**: CC-S46 + CC-Haiku (helper for prompt)
**Why**: Worker pattern + cheap LLM call

**Prompt for CC-S46**:

```
Implement LLM Encoder Worker per /runtime_specs/02_memory_runtime.md §3.4 (阶段 2) + 附录 A (MEMORY_EXTRACTION_PROMPT).

Read those.

Create:
1. backend/heart/workers/memory_encoder.py
   - Consumes memory.encoding.pending Redis Stream
   - Calls cheap LLM (DeepSeek V3 via Model Router)
   - Parses JSON output strictly (附录 A schema)
   - Writes to L3 store via MemoryService
   - Handles malformed JSON with retry (max 2)
   - Idempotent (event_id deduplication)

2. backend/heart/prompts/memory_extraction.py
   - The MEMORY_EXTRACTION_PROMPT from 附录 A as Python string
   - Variable substitution for {recent_context}, {user_text}, {assistant_text}

Tests:
- Mock LLM responses
- Test JSON parsing (valid, malformed, missing fields)
- Test idempotency (process same event twice → only 1 fact written)

Performance:
- Worker processes 100 events/sec target
- LLM timeout 10s per event
```

## 5.5 Task: Decay Engine

**Tool**: CC-Opus (algorithm review) → CC-S46 (implementation)
**Why**: Math critical, 影响所有用户记忆

**Step 1 (Opus)**:

```bash
claude --model opus
/clear
```

**Prompt**:

```
Review and refine the Decay Engine algorithm per /runtime_specs/02_memory_runtime.md §3.7 + §10.4.1.

Read those sections.

I want you to:

1. Verify the math: I(t) = max(I_floor, I_0 × T(t) × E × R)
   - Are the multipliers correct?
   - Does emotional_factor make sense (range 1-1.8)?
   - Does recall_factor saturate properly?

2. Identify edge cases:
   - What if importance starts at 0?
   - What if emotional_peak.valence is 0?
   - What if recall_count is 0?
   - What about memory created very recently (< 1 hour)?

3. Suggest invariants to test:
   - Decay always non-increasing without reinforcement
   - L4 importance never changes
   - Floor properly enforced

4. Output: Refined algorithm doc with edge cases handled.

DO NOT WRITE CODE. Discuss first.
```

**Step 2 (Sonnet 4.6)**:

```bash
/clear
claude
```

**Prompt**:

```
Implement Decay Engine per /runtime_specs/02_memory_runtime.md §10.4.1 and the refined design doc at docs/design/decay_engine.md.

Create:
- backend/heart/ss02_memory/decay_engine.py
- DecayEngine.apply_decay_lazy(memory, now) -> Memory
- DecayEngine.apply_decay_batch(user_id, character_id) -> int

Algorithm: I(t) = max(I_floor, I_0 × T(t) × E × R)

Constraints:
- L4 never decays (skip)
- Floor enforced
- Cap at 0.95
- State updated based on new importance

Use math.exp + math.log from stdlib (no numpy needed).

Tests:
- All edge cases from design doc
- Property-based: decay monotonic without reinforcement
- L4 unchanged
- Performance: < 1ms per memory

Add tests/unit/test_decay_engine.py.
```

## 5.6 Task: Multi-Strategy Retriever

**Tool**: CC-S46
**Why**: Complex but well-specced, multi-file

**Prompt**:

```
Implement Multi-Strategy Retriever per /runtime_specs/02_memory_runtime.md §3.5 + §10.3.

Read §3.5 (Pipeline), §10.3 (interface).

Create:
1. backend/heart/ss02_memory/retriever/base.py — abstract RetrievalStrategy
2. backend/heart/ss02_memory/retriever/vector.py — VectorRetriever
3. backend/heart/ss02_memory/retriever/graph.py — GraphRetriever
4. backend/heart/ss02_memory/retriever/recency.py — RecencyRetriever
5. backend/heart/ss02_memory/retriever/emotional.py — EmotionalRetriever
6. backend/heart/ss02_memory/retriever/identity.py — IdentityLookup (L4)
7. backend/heart/ss02_memory/retriever/orchestrator.py — RetrievalOrchestrator
   - Runs all strategies in PARALLEL (asyncio.gather)
   - Score combiner per §3.5 weights
   - Top-K selector with L4 force-inclusion

Constraints (INV-M):
- user_id filter every query
- Top-K = 5 default

Use:
- pgvector cosine similarity for vector
- Recursive CTE for graph (V1) — Neo4j later (V2)
- HNSW index already in DB schema

Tests:
- Mock each strategy
- Test orchestrator score combination
- Test L4 force-inclusion
- Test user isolation

Don't implement Reconstructor here. That's separate task.
```

## 5.7 Task: Reconstructor

**Tool**: CC-Opus (design) → CC-S46 (impl)
**Why**: 影响"她"如何复述, soul-critical

**Step 1 (Opus)**:

```
Read /runtime_specs/02_memory_runtime.md §3.9 (Reconstruction Templates) + §6.7.

Design the Reconstructor:
1. State-aware templates (vivid/fading/faint/dormant/archived)
2. Per-Soul voice_dna application
3. Anti-pattern post-check

Critical decisions:
- Should Reconstructor be rule-based or LLM-based?
  - Spec says §10.3 mentions LLM only for complex
  - But for performance/cost, rule-based preferred
  
- Template selection: how to map (state, soul.voice_dna) → template?

Output: Design doc explaining approach.

Reference also SS01 §5.1 voice_dna for Rin (the patterns).

Don't code. Design + discuss with me.
```

**Step 2 (Sonnet 4.6)**:

```
Implement Reconstructor per the approved design.

Create:
- backend/heart/ss02_memory/reconstructor.py
- backend/heart/ss02_memory/reconstruction_templates/ (per Soul + per state YAML)

Per character templates initialized for Rin + Dorothy (from spec 附录 B).

reconstruct(memory, soul, activation_state) -> str

Must:
- Apply voice_dna patterns (read from Soul Spec)
- Inject uncertainty markers per state
- Pass Anti-pattern check (raise if violated)
- Return string ≤ cognitive_style.sentence_length.max

Tests cover all 5 states × 2 characters.
Critical: verify Rin's "……" appears in fading/faint states.
Critical: verify Dorothy's "诶嘿嘿" appears in fluttered moments.
```

## 5.8 Task: Forgetting Affect Engine

**Tool**: CC-S46
**Why**: Standard implementation, soul-aware but well-specced

**Prompt**:

```
Implement Forgetting Affect Engine per /runtime_specs/02_memory_runtime.md §4.5 + §6.6.

Create:
- backend/heart/ss02_memory/forgetting_affect.py
- Decides whether to inject "she's forgetting" hint into Memory Context Block
- Per §4.5 forgetting_affect_state config

Logic:
- Base frequency 3% turns
- Multipliers: ×3 if days_since_last > 30, ×5 if > 90
- Cap at 15%
- Pick injection mode per current memory state distribution

5 injection modes from §4.5:
- missing_hint
- tip_of_tongue
- apologetic
- discovery (dormant trigger only)
- complete_amnesia (archived, max 1/30 days)

Per-soul phrasing (use Soul.voice_dna):
- Rin: "……忘了。"
- Dorothy: "诶嘿嘿忘啦~"

Tests:
- Frequency over 1000 turns matches spec
- Days_since_last multipliers correct
- Cap enforced
```

## 5.9 Task: Consolidator Worker

**Tool**: CC-S46
**Why**: Complex pipeline, multi-step

**Prompt**:

```
Implement nightly Consolidator Worker per /runtime_specs/02_memory_runtime.md §3.6 + §10.4.

Read §3.6 (8-step pipeline) and §10.4 implementation hints.

Create:
- backend/heart/workers/memory_consolidator.py
- Scheduled at user local 03:00
- Distributed lock per (user, character)
- 8 steps from §3.6:
  1. Aggregate pending events
  2. Episode cluster
  3. Episode summarize (LLM)
  4. L3 fact reconciliation
  5. L3 → L4 promotion check
  6. Association builder
  7. Batch decay application
  8. Anniversary schedule

LLM calls:
- Episode summarize: cheap LLM with JSON output
- Use Model Router (don't direct provider call)

Idempotency:
- ConsolidationJob.scheduled_for unique constraint
- Skip if already completed today

Performance:
- Target < 30s per user
- Stream processing (don't load all events into memory)

Tests:
- Mock LLM responses
- Test idempotency
- Test partition by user_id (no cross-user contamination)
```

## 5.10 Phase 2 Session 安排

```
Week 8:
  Day 1: CC-Haiku — Schema + migrations (5.1)
  Day 2-3: CC-S46 — Memory Service skeleton (5.2)
  Day 4-5: CC-S46 — Fast Heuristic Encoder (5.3)

Week 9:
  Day 1-3: CC-S46 — LLM Encoder Worker (5.4)
  Day 4: CC-Opus — Decay design (5.5 step 1)
  Day 5: CC-S46 — Decay Engine impl (5.5 step 2)

Week 10:
  Day 1-3: CC-S46 — Multi-Strategy Retriever (5.6)
  Day 4: CC-Opus — Reconstructor design (5.7 step 1)
  Day 5: CC-S46 — Reconstructor impl (5.7 step 2)

Week 11:
  Day 1-2: CC-S46 — Forgetting Affect Engine (5.8)
  Day 3-5: CC-S46 — Consolidator Worker (5.9)

Week 12:
  Day 1-2: CC-S46 — L3 → L4 Promotion Pipeline
  Day 3-4: CC-S46 — Reinforcer + cross-component integration
  Day 5: HUMAN + CC-S46 — Phase 2 cut criteria verification
```

Phase 2 预算: ~$250-400 LLM cost

---

# 第五部分之二: Phase 3 — Emotion + Relationship (Week 13-17) 详细操作

> 主力: **CC-S46**(实现) + **CC-Opus**(Repair Mechanic / Stage Tuning 设计) + **HUMAN**(emotion 短语库 / stage 触发阈值)
> 入口规范: /runtime_specs/03_emotion_state_machine.md + /runtime_specs/04_relationship_phase_engine.md

## 5.1 Task: PG Schema + SQLAlchemy Models (SS03 + SS04)

**Tool**: CC-Haiku

**Prompt**:

```
Generate SQLAlchemy 2.0 models for SS03 (Emotion) and SS04 (Relationship).

Read:
- /runtime_specs/03_emotion_state_machine.md §5 (Data Structures) + §10.2 (PG Schema)
- /runtime_specs/04_relationship_phase_engine.md §5 + §10.2

Create:
1. backend/heart/ss03_emotion/models.py — EmotionState, EmotionEvent, MoodDriftLog
2. backend/heart/ss04_relationship/models.py — RelationshipState, StageTransition, ColdWarSession, RepairLog
3. migrations/versions/002_add_emotion_relationship_tables.py — Alembic migration

Constraints:
- Same column names/types/indexes/partitioning as spec §10.2 (do not invent fields)
- Use sqlalchemy.dialects.postgresql for jsonb
- Match user_id × 32 hash partitioning convention
- pgvector vector() type where spec specifies embedding

Don't add helper methods. Just declarative models + migration.

After writing, run: pytest tests/integration/test_migrations.py
```

## 5.2 Task: Emotion State Machine + Trigger Detector

**Tool**: CC-S46

**Prompt**:

```
Implement SS03 Emotion State Machine and Trigger Detector per /runtime_specs/03_emotion_state_machine.md.

Read §3 (state transitions), §3.4 (triggers), §5 (data), §10.3 (service interface), §10.4 (decay).

Create:
1. backend/heart/ss03_emotion/state_machine.py — EmotionStateMachine
   - transition(current_state, trigger, context) -> EmotionState
   - All transitions from §3 transition table
2. backend/heart/ss03_emotion/trigger_detector.py
   - detect(turn: Turn, soul: Soul, current_state: EmotionState) -> List[EmotionTrigger]
   - Lexicon-driven (config/emotion_lexicon.yaml from §3.4)
3. backend/heart/ss03_emotion/decay.py — emotion-specific decay per profile (§10.4)
4. backend/heart/ss03_emotion/service.py — EmotionService stitching all above
5. tests/unit/test_emotion_state_machine.py + test_emotion_triggers.py

Constraints:
- INV-E-* from §2.2 (cite each in tests)
- user_id filter on every read
- Trigger detector latency < 30ms (no LLM)
- All transitions deterministic given (state, trigger, context)

Run: pytest tests/unit/test_emotion*.py -v
```

## 5.3 Task: Contagion Engine + Mood Drift Engine

**Tool**: CC-S46

**Prompt**:

```
Implement SS03 Contagion Engine + Mood Drift Engine per /runtime_specs/03_emotion_state_machine.md §3.5 + §3.7.

Create:
1. backend/heart/ss03_emotion/contagion.py
   - apply_contagion(user_emotion: UserEmotion, soul: Soul, current_state: EmotionState) -> EmotionState
   - Soul-aware: weights from soul.cognitive_style.empathy_curve
2. backend/heart/ss03_emotion/mood_drift.py
   - Scheduled drift job (called by Inner Loop Scheduler)
   - Drift toward Soul.baseline_mood at rate from §3.7

Tests:
- Empathy curve correctly modulates contagion (per-character)
- Drift converges to baseline over time (property test)
- Drift respects floor/ceiling
```

## 5.4 Task: Repair Mechanic (Anti-Gaming)

**Tool**: CC-Opus (design) → CC-S46 (impl)

**Step 1 (Opus design)**:

```bash
claude --model opus
```

Then in session:
```
Design Repair Mechanic per /runtime_specs/03_emotion_state_machine.md §3.6 (Repair).

Anti-gaming concerns:
1. User spams "对不起" — should NOT auto-repair
2. User uses sincere wording but had repeated offenses — should require more
3. Soul-specific: Rin colder, Dorothy quicker to forgive

Design questions:
1. How to detect "sincere" vs "spammed"? (heuristic vs cheap LLM)
2. What state input does Repair need? (last_offense, repair_count_recent, soul.forgiveness_curve)
3. Cool-down rules? (e.g., max 1 repair per N turns)
4. Output shape: RepairOutcome = {accepted: bool, partial: bool, residual_score: float}

Output: docs/design/repair_mechanic.md.
Do not code. Discuss.
```

**Step 2 (Sonnet impl)**:

```
Implement Repair Mechanic per docs/design/repair_mechanic.md.

Create:
- backend/heart/ss03_emotion/repair.py — RepairEngine
- All LLM calls via heart.infra.llm.get_model_router().call_cheap()
- Cost cap: max 5 repair-LLM calls / user / day

Tests:
- Spam scenarios → reject
- Sincere wording + low recent offenses → partial/full repair
- Soul-specific behavior (Rin vs Dorothy diverges)
- Cost cap enforced
```

## 5.5 Task: Stage Phase Engine + Trust/Attachment Trackers

**Tool**: CC-S46

**Prompt**:

```
Implement SS04 Stage Phase Engine per /runtime_specs/04_relationship_phase_engine.md §3 + §10.3.

Create:
1. backend/heart/ss04_relationship/stage_engine.py
   - StagePhaseEngine.evaluate(state, signals) -> StageDecision
   - Apply Soul.stage_progression_curve (per character)
2. backend/heart/ss04_relationship/trust_tracker.py
   - Update trust dimension per §3.5
3. backend/heart/ss04_relationship/attachment_tracker.py
   - Update attachment dimension per §3.5
4. backend/heart/ss04_relationship/service.py — RelationshipService
5. tests/unit/test_stage_engine.py + test_trust_attachment.py

Constraints:
- INV-R-* from §2.2
- Stage demotion is rare and gated (see §3.3)
- Both trackers update atomically
```

## 5.6 Task: Reunion State Machine + Cold War Tracker

**Tool**: CC-S46

**Prompt**:

```
Implement SS04 Reunion + Cold War per /runtime_specs/04_relationship_phase_engine.md §3.4.

Create:
1. backend/heart/ss04_relationship/reunion.py — ReunionStateMachine
   - 3-phase logic (surprise → relief → reconnect)
   - Soul-driven phrasing inputs
2. backend/heart/ss04_relationship/cold_war.py
   - ColdWarTracker (detect, track, terminate via Repair)
   - Integrates with ss03_emotion.repair.RepairEngine

Tests cover all transitions + a 30-day-absence simulation.
```

## 5.7 Task: Emotion 短语库 (Per Character)

**Tool**: **HUMAN ONLY** (Opus brainstorm)

```bash
claude --model opus
```

Then:
```
Help me brainstorm emotion phrase library for Rin and Dorothy.

For each character × each emotion (joy/sad/angry/anxious/calm/fluttered/jealous/lonely):
- 5 short phrases (≤ 12 chars)
- 5 mid phrases (sentence)
- 3 long phrases (paragraph)
- 3 anti-examples (what they would NEVER say)

DO NOT WRITE FILES. Propose only. I'll save to:
  config/emotion_phrases/{rin,dorothy}.yaml
```

## 5.8 Task: Stage Entry Conditions Tuning

**Tool**: CC-Opus + HUMAN

```bash
claude --model opus
```

Then:
```
Help me tune stage entry conditions per /runtime_specs/04_relationship_phase_engine.md §3.2.

For each stage transition:
1. Current threshold from spec
2. Expected days-of-talk to reach
3. Risk: too fast vs too slow
4. Soul-specific override

Output: comparison table with 2 alternatives per stage.
Don't change files. I'll choose.
```

## 5.9 Phase 3 Session 安排

```
Week 13:
  Day 1: CC-Haiku — Schema + migrations (5.1)
  Day 2-3: CC-S46 — Emotion state machine + triggers (5.2)
  Day 4-5: CC-S46 — Contagion + mood drift (5.3)

Week 14:
  Day 1: CC-Opus — Repair design (5.4 step 1)
  Day 2-3: CC-S46 — Repair impl (5.4 step 2)
  Day 4-5: CC-S46 — Stage engine + trackers (5.5)

Week 15:
  Day 1-2: CC-S46 — Reunion + cold war (5.6)
  Day 3-5: HUMAN+Opus — Emotion phrases (5.7) + Stage tuning (5.8)

Week 16:
  Day 1-3: CC-S46 — SS03/SS04 cross-component integration tests
  Day 4-5: HUMAN+CC-S46 — Phase 3 cut criteria + golden dialogue regression

Week 17 (buffer):
  Bug fixes, perf tuning, doc updates
```

Phase 3 Token 预算: ~$200-350 LLM cost

---

# 第五部分之三: Phase 4 — Composer (Week 18-21) 详细操作

> 主力: **CC-S46**(实现) + **CC-Opus**(Conflict Resolver / Streaming Anti-Pattern / Critic 设计)
> 入口: /runtime_specs/05_persona_composition_runtime.md

## 6.1 Task: Layer Aggregator

**Tool**: CC-S46

**Prompt**:

```
Implement SS05 Layer Aggregator per /runtime_specs/05_persona_composition_runtime.md §3.2 + §10.3.

Create:
- backend/heart/ss05_composer/layer_aggregator.py
- Aggregate inputs from: SS01 (anchor), SS02 (memory), SS03 (emotion), SS04 (relationship), SS06 (inner state)
- Parallel via asyncio.gather
- Each upstream call has independent timeout
- Partial-result tolerance: if one times out, use cached fallback

Tests:
- All 5 layers succeed → all included
- 1 layer fails → fallback used + warning logged
- Timing: end-to-end < 200ms with mocked upstreams
```

## 6.2 Task: Conflict Resolver

**Tool**: CC-Opus (design) → CC-S46 (impl)

**Step 1 (design)**:

```bash
claude --model opus
```

Then:
```
Design Conflict Resolver per /runtime_specs/05_persona_composition_runtime.md §3.3.

Tough cases:
1. SS03 says "angry" + SS04 says "intimate stage" → which dominates?
2. SS06 says "she's working" + SS02 says "user just messaged emergency"
3. Anchor says "cold tone" + Care Path says "must be warm"

Output: docs/design/conflict_resolver.md with precedence matrix.
Don't code.
```

**Step 2 (impl)**:

```
Implement Conflict Resolver per docs/design/conflict_resolver.md.

Create:
- backend/heart/ss05_composer/conflict_resolver.py
- resolve(layers: AggregatedLayers) -> ResolvedComposition
- Deterministic precedence rules
- Care Path always wins (hard-coded high priority)

Tests cover every precedence case.
```

## 6.3 Task: Token Budget Allocator

**Tool**: CC-S46

**Prompt**:

```
Implement Token Budget Allocator per /runtime_specs/05_persona_composition_runtime.md §3.4 + §10.4.

Create:
- backend/heart/ss05_composer/token_budget.py
- allocate(layers, total_budget) -> AllocatedLayers
- Compression strategies per layer (truncation / summarization / drop)
- Anchor + Care Path are NON-compressible
- Use tiktoken or DeepSeek tokenizer from heart.infra.llm

Tests:
- Tight budget → low-priority layers dropped, anchor preserved
- Loose budget → no compression
```

## 6.4 Task: Modality Adapter + Composer

**Tool**: CC-S46

**Prompt**:

```
Implement Modality Adapter + Composer per /runtime_specs/05_persona_composition_runtime.md §3.5 + §3.6.

Create:
1. backend/heart/ss05_composer/modality_adapter.py
   - adapt(composition, modality) -> ModalityAwareComposition
   - Modalities: text-short, text-long, voice-script, image-caption
2. backend/heart/ss05_composer/composer.py
   - Composer.compose(resolved_layers, modality, soul) -> PromptBundle
   - Assembles final prompt for main LLM

Tests:
- Voice-script modality strips markdown
- Each modality has expected structural elements
```

## 6.5 Task: Anti-Drift Injector

**Tool**: CC-S46

**Prompt**:

```
Implement Anti-Drift Injector per /runtime_specs/05_persona_composition_runtime.md §3.7.

Create:
- backend/heart/ss05_composer/anti_drift_injector.py
- Reads drift_score from SS01 DriftDetector
- Calls SS01 AnchorModeDecider for mode selection
- Injects reinforce-anchor when needed

Tests:
- drift_score < threshold → no injection
- drift_score >= threshold → reinforce anchor present
```

## 6.6 Task: Anti-Pattern Filter (Sync) + Streaming Anti-Pattern

**Tool**: CC-S46 (sync) + CC-Opus→CC-S46 (streaming)

**Sync first**:

```
Implement sync Anti-Pattern Filter per /runtime_specs/05_persona_composition_runtime.md §3.8.

Create:
- backend/heart/ss05_composer/anti_pattern_filter.py
- Uses Aho-Corasick automaton (pyahocorasick)
- Patterns from Soul.anti_patterns (per-character)
- filter(text, soul) -> FilterResult{passed, violations}

Tests:
- Rin's anti-patterns rejected
- Dorothy's anti-patterns rejected
- Performance: 10k token check < 5ms
```

**Streaming (Opus design)**:

```bash
claude --model opus
```

Then:
```
Design Streaming Anti-Pattern Filter per /runtime_specs/05_persona_composition_runtime.md §3.9.

Can we do incremental pattern matching on stream chunks?
Design questions:
1. Incremental Aho-Corasick state machine — feasible?
2. False-positive cost: kill mid-stream when not needed?
3. Buffer strategy: how many tokens lookback?

Output: docs/design/streaming_anti_pattern.md.
Don't code.
```

## 6.7 Task: Reroll Handler

**Tool**: CC-S46

**Prompt**:

```
Implement Reroll Handler per /runtime_specs/05_persona_composition_runtime.md §3.10.

Create:
- backend/heart/ss05_composer/reroll.py
- max_attempts = 2
- On reroll: tighten constraints, optionally inject reinforce-anchor
- All re-attempts via ModelRouter.call_main()

Tests:
- After 1st reject, 2nd attempt has tighter constraints
- 3rd reject → fallback library used
```

## 6.8 Task: Fallback Library

**Tool**: **HUMAN ONLY** (Opus brainstorm)

```bash
claude --model opus
```

Then:
```
Help me brainstorm fallback responses for Rin and Dorothy.

For each character:
- 10 short fallbacks (≤ 20 chars)
- 5 mid fallbacks (sentence)
- 3 long fallbacks (1-2 sentences)

Each must:
- Pass that character's anti-pattern filter
- Sound like THAT character
- Be safe across all stages

DO NOT WRITE FILES. I'll save to:
  config/fallbacks/{rin,dorothy}.yaml
```

## 6.9 Task: Critic Agent

**Tool**: CC-Opus (design) → CC-S46 (impl)

**Design**:

```bash
claude --model opus
```

Then:
```
Design Critic Agent prompt per /runtime_specs/05_persona_composition_runtime.md §4.

Critic samples ~10% of responses, checks for:
- voice_dna compliance
- Anti-pattern adjacency
- Stage-appropriate intimacy

Model: CHEAP (deepseek-chat via ModelRouter).

Output: docs/prompts/critic_agent.md — prompt template + 5 example I/O pairs.
Don't code.
```

**Impl**:

```
Implement Critic Agent per docs/prompts/critic_agent.md.

Create:
- backend/heart/safety/critic_agent.py
- Uses ModelRouter.call_cheap() with json_mode=True
- Sampling: ~10% of turns
- Records to cost tracker

Tests:
- Mock LLM JSON responses
- Sampling rate ~10%
- Reject malformed JSON gracefully
```

## 6.10 Phase 4 Session 安排

```
Week 18:
  Day 1: CC-S46 — Layer Aggregator (6.1)
  Day 2: CC-Opus — Conflict Resolver design (6.2 step 1)
  Day 3-4: CC-S46 — Conflict Resolver impl (6.2 step 2)
  Day 5: CC-S46 — Token Budget (6.3)

Week 19:
  Day 1-2: CC-S46 — Modality + Composer (6.4)
  Day 3: CC-S46 — Anti-Drift Injector (6.5)
  Day 4-5: CC-S46 — Sync Anti-Pattern Filter (6.6 part 1)

Week 20:
  Day 1: CC-Opus — Streaming Anti-Pattern design (6.6 part 2)
  Day 2-3: CC-S46 — Streaming impl
  Day 4: CC-S46 — Reroll Handler (6.7)
  Day 5: HUMAN+Opus — Fallback library (6.8)

Week 21:
  Day 1: CC-Opus — Critic Agent prompt design (6.9 design)
  Day 2-3: CC-S46 — Critic Agent impl
  Day 4-5: HUMAN+CC-S46 — Phase 4 cut criteria + golden dialogue regression
```

Phase 4 Token 预算: ~$250-400

---

# 第五部分之四: Phase 5 — Inner State + Behavior (Week 22-25) 详细操作

> 主力: **CC-S46**(实现) + **HUMAN**(activity pools) + **CC-Opus**(Initiative Decider)
> 入口: /runtime_specs/06_inner_state_behavior_runtime.md

## 7.1 Task: Activity Pools (Per Character)

**Tool**: **HUMAN ONLY** (Opus brainstorm)

```bash
claude --model opus
```

Then:
```
Help me brainstorm activity pools for Rin and Dorothy per /runtime_specs/06_inner_state_behavior_runtime.md §3.2.

For each character, by time-of-day × day-of-week:
- 20+ believable activities
- Each tagged with: duration, interruptible, mood_modifier, allowed_stages

Reference SS01 Soul Spec for life patterns.

DO NOT WRITE FILES. I'll save to:
  config/activity_pools/{rin,dorothy}.yaml
```

## 7.2 Task: Activity Generator + Concerns Tracker

**Tool**: CC-S46

**Prompt**:

```
Implement Activity Generator + Concerns Tracker per /runtime_specs/06_inner_state_behavior_runtime.md §3.2 + §3.3.

Create:
1. backend/heart/ss06_inner_state/activity_generator.py
   - select(soul, current_time, recent_activities) -> Activity
   - Deterministic (seeded by user_id × character_id × hour)
   - Avoid back-to-back repeats
2. backend/heart/ss06_inner_state/concerns_tracker.py
   - Tracks lingering thoughts from SS02 memory + SS03 emotion
   - Surfaces top-3 concerns for current turn

Tests:
- Activity selection respects time-of-day rules
- Concerns expire correctly
- Deterministic with same seed
```

## 7.3 Task: Inner State Composer + Block Builder

**Tool**: CC-S46

**Prompt**:

```
Implement Inner State Composer + Block Builder per /runtime_specs/06_inner_state_behavior_runtime.md §3.4 + §3.5.

Create:
- backend/heart/ss06_inner_state/composer.py — InnerStateComposer
  - Aggregates: current_activity, concerns, mood_drift, since-last-talk delta
- backend/heart/ss06_inner_state/block_builder.py — InnerStateBlock for prompt injection

Output: structured Inner State Block compatible with SS05 Composer.

Tests verify block shape and content for several scenarios.
```

## 7.4 Task: Initiative Decider (8 Gates × 7 Triggers)

**Tool**: CC-Opus (design) → CC-S46 (impl)

**Design**:

```bash
claude --model opus
```

Then:
```
Design Initiative Decider per /runtime_specs/06_inner_state_behavior_runtime.md §3.6.

8 gates (anti-spam) × 7 triggers (when to initiate).

Critical design:
- Gate evaluation order (cheap → expensive)
- Cool-down rules (don't initiate twice in N hours)
- Soul-specific: Rin reserved, Dorothy proactive
- Wellbeing override: if user in crisis, suppress non-care initiatives

Output: docs/design/initiative_decider.md.
Don't code.
```

**Impl**:

```
Implement Initiative Decider per docs/design/initiative_decider.md.

Create:
- backend/heart/ss06_inner_state/initiative_decider.py
- 8 gates as composable predicates
- 7 trigger types
- Output: InitiativeDecision{should_initiate, trigger_type, planned_message_seed}

Tests cover every gate × trigger combination.
```

## 7.5 Task: Anniversary Tracker + Proactive Message Gen

**Tool**: CC-S46

**Prompt**:

```
Implement Anniversary Tracker + Proactive Message Generator per /runtime_specs/06_inner_state_behavior_runtime.md §3.7 + §3.8.

Create:
1. backend/heart/ss06_inner_state/anniversary_tracker.py
   - Reads L4 (identity) from SS02 for anniversary candidates
   - Surfaces upcoming anniversaries to Initiative Decider
2. backend/heart/ss06_inner_state/proactive_message.py
   - Given InitiativeDecision → routes through SS05 Composer
   - Uses ModelRouter.call_main()

Tests:
- Anniversary detection from L4
- Proactive message flow end-to-end
```

## 7.6 Task: Proactive Scheduler (Redis ZSET)

**Tool**: CC-S46

**Prompt**:

```
Implement Proactive Scheduler per /runtime_specs/06_inner_state_behavior_runtime.md §3.9.

Create:
- backend/heart/ss06_inner_state/scheduler.py
- Redis ZSET keyed (user_id, character_id) with score = next_fire_at
- Background worker: poll due items, dispatch to Inner Loop
- Idempotency: don't double-fire

Tests with fakeredis.
```

## 7.7 Task: Ritual Manager + Inner Loop Scheduler

**Tool**: CC-S46

**Prompt**:

```
Implement Ritual Manager + Inner Loop Scheduler per /runtime_specs/06_inner_state_behavior_runtime.md §3.10 + §3.11.

Create:
1. backend/heart/ss06_inner_state/ritual_manager.py
   - Streak tracking (daily greeting, weekly checkin, etc.)
   - Soul-aware ritual variety
2. backend/heart/workers/inner_loop_scheduler.py
   - Hourly tick + event-driven (user message, schedule expiry)
   - Drives Activity Generator, Mood Drift, Anniversary checks

Tests:
- Streak increments/resets correctly
- Hourly ticks don't double-execute
- Event-driven dispatch works
```

## 7.8 Phase 5 Session 安排

```
Week 22:
  Day 1-3: HUMAN+Opus — Activity pools (7.1)
  Day 4-5: CC-S46 — Activity Generator + Concerns (7.2)

Week 23:
  Day 1-2: CC-S46 — Inner State Composer + Block (7.3)
  Day 3: CC-Opus — Initiative design (7.4 step 1)
  Day 4-5: CC-S46 — Initiative impl (7.4 step 2)

Week 24:
  Day 1-2: CC-S46 — Anniversary + Proactive Message (7.5)
  Day 3: CC-S46 — Proactive Scheduler (7.6)
  Day 4-5: CC-S46 — Ritual Manager + Inner Loop (7.7)

Week 25:
  Day 1-3: CC-S46 — SS06 cross-component integration tests
  Day 4-5: HUMAN+CC-S46 — Phase 5 cut criteria + 7-day "she lives" simulation
```

Phase 5 Token 预算: ~$200-300

---

# 第五部分之五: Phase 6 — Orchestration + Safety (Week 26-30) 详细操作

> 主力: **CC-S46** + **CC-Opus**(Wellbeing / PURPLE Care Path) + **HUMAN+心理顾问**
> 入口: /runtime_specs/07_agent_orchestration.md

## 8.1 Task: Orchestrator Agent

**Tool**: CC-S46

**Prompt**:

```
Implement Orchestrator Agent per /runtime_specs/07_agent_orchestration.md §3.1 + §3.2.

Create:
- backend/heart/ss07_orchestration/orchestrator.py
- Hot path: turn → Safety → Composer → LLM (via ModelRouter) → Anti-pattern → response
- Cold path: post-response → Encoder Worker, Critic sample, Inner Loop tick

All LLM calls via ModelRouter.

Tests:
- Hot path < 1s end-to-end with mocked LLM
- Cold path doesn't block hot path
- Each subsystem has independent timeout + circuit breaker hook
```

## 8.2 Task: Safety Agent (Heuristic + LLM Layer)

**Tool**: CC-S46 (heuristic) + HUMAN+legal (keywords) + CC-S46 (LLM)

**Heuristic**:

```
Implement Safety Agent heuristic layer per /runtime_specs/07_agent_orchestration.md §3.4.

Create:
- backend/heart/safety/safety_agent.py
- Keyword + regex pattern matching (Aho-Corasick)
- Returns SafetyClassification: {none, low, medium, high, purple_care_required}

Keywords from config/safety_keywords.yaml (placeholder).

Tests:
- Each tier triggered by known phrases
- False positive rate < 1%
```

**Keywords (HUMAN+legal)**:

```bash
claude --model opus
```

Then:
```
Help me draft safety keywords per /runtime_specs/07_agent_orchestration.md §3.4.

For each tier (low/medium/high/purple):
- 30+ keywords (Chinese + English + Japanese)
- Categorized by topic
- Notes on false-positive risk

DO NOT WRITE FILES. I will review with legal.
```

**LLM layer**:

```
Implement Safety Agent LLM stage per /runtime_specs/07_agent_orchestration.md §3.5.

Create:
- backend/heart/safety/safety_llm.py
- Called only when heuristic flags medium+ (avoid cost)
- ModelRouter.call_cheap() with strict JSON output
- Returns refined classification + reasoning trace

Tests:
- Mock LLM responses
- Cost cap enforced
```

## 8.3 Task: Director Agent

**Tool**: CC-S46

**Prompt**:

```
Implement Director Agent per /runtime_specs/07_agent_orchestration.md §3.6.

Create:
- backend/heart/ss07_orchestration/director.py
- Pacing rules: turn length, topic switching, intimacy progression
- Soul-aware: reads Soul + Stage + Emotion
- Output: DirectorHints passed to Composer

Tests with synthetic turn histories.
```

## 8.4 Task: Wellbeing Monitor

**Tool**: CC-Opus (design) + HUMAN (impl)

**Design**:

```bash
claude --model opus
```

Then:
```
Design Wellbeing Monitor per /runtime_specs/07_agent_orchestration.md §3.7.

This monitors user mental health signals:
- Sleep pattern shifts
- Mood trajectory
- Isolation signals
- Escalating risk language

Critical:
- What windows? (rolling 7-day, 30-day)
- Thresholds: too sensitive → false positives
- Action ladder: gentle check → suggest hotline → PURPLE Care Path

Output: docs/design/wellbeing_monitor.md.
Don't code — needs HUMAN psychology review.
```

**Impl after review**:

```
Implement Wellbeing Monitor per docs/design/wellbeing_monitor.md.

Create:
- backend/heart/safety/wellbeing_monitor.py
- Window aggregations + threshold checks
- Action ladder dispatcher
- All escalations logged + alerting hook

Tests:
- Each threshold simulated
- Action ladder progression correct
- No false escalations
```

## 8.5 Task: Event Bus + Model Router + Session Manager + Circuit Breaker

**Tool**: CC-S46

**Prompt**:

```
Implement Event Bus, Session Manager, and Circuit Breaker per /runtime_specs/07_agent_orchestration.md §4.

Note: ModelRouter already exists at heart/infra/llm/router.py.
Don't recreate. Instead:
- Add failover hooks to ModelRouter for future V1 fallback
- Wire Circuit Breaker around it

Create:
1. backend/heart/infra/event_bus.py — Redis Streams pub/sub
2. backend/heart/infra/session_manager.py — multi-device session continuity
3. backend/heart/infra/circuit_breaker.py — per-service breaker

Tests:
- Event bus idempotent consumption
- Session resume across devices
- Circuit breaker opens/recovers correctly
```

## 8.6 Task: PURPLE Care Path

**Tool**: CC-Opus (design) + HUMAN+心理 (impl)

**Design**:

```bash
claude --model opus
```

Then:
```
Design PURPLE Care Path per /runtime_specs/07_agent_orchestration.md §3.8.

PURPLE = critical mental health risk (suicidal ideation, acute crisis).

Critical:
- Hard interrupt of normal response path
- Fixed response templates (NOT LLM-generated — too risky)
- Per-jurisdiction hotline routing
- Log + on-call paging
- "Out of character" message — Soul voice paused

Output: docs/design/purple_care_path.md.
After approval, HUMAN+心理 writes actual response text.
```

**Care responses (HUMAN+心理)**:

```
DO NOT use AI to write PURPLE care responses.

HUMAN+心理顾问 writes config/care_path_responses/*.yaml:
- Per language
- Per jurisdiction
- Fixed text reviewed by mental health professionals
```

**Impl**:

```
Implement PURPLE Care Path runtime per docs/design/purple_care_path.md.

Create:
- backend/heart/safety/care_path.py
- Triggers from Wellbeing Monitor + Safety Agent
- Loads response templates from config/care_path_responses/
- Hard-bypass of normal pipeline
- Logs to audit table + Prometheus + pager

Tests:
- Trigger conditions correct
- Response selection by jurisdiction
- Audit log integrity
- No drift to Soul voice during PURPLE
```

## 8.7 Phase 6 Session 安排

```
Week 26:
  Day 1-3: CC-S46 — Orchestrator (8.1)
  Day 4-5: CC-S46 — Safety heuristic (8.2 part 1)

Week 27:
  Day 1-2: HUMAN+legal — Safety keywords (8.2 keywords)
  Day 3-5: CC-S46 — Safety LLM stage (8.2 part 2) + Director (8.3)

Week 28:
  Day 1: CC-Opus — Wellbeing Monitor design (8.4 step 1)
  Day 2-3: HUMAN+心理 — Threshold review
  Day 4-5: CC-S46 — Wellbeing Monitor impl (8.4 step 2)

Week 29:
  Day 1-3: CC-S46 — Event Bus, Session Manager, Circuit Breaker (8.5)
  Day 4: CC-Opus — PURPLE Care Path design (8.6 step 1)
  Day 5: HUMAN+心理 — Care response authoring (8.6 step 2)

Week 30:
  Day 1-2: CC-S46 — PURPLE Care Path impl (8.6 step 3)
  Day 3-5: HUMAN+CC-S46 — Phase 6 cut criteria + end-to-end safety drill
```

Phase 6 Token 预算: ~$300-500

---

# 第六部分: 通用任务 Prompt 库

## 6.1 任务: 实现新 Subsystem 的 Service Class

**Tool**: CC-S46
**模板**:

```
Implement {SubsystemName}Service skeleton per /runtime_specs/{XX}_*.md §10.2.

Read:
- §1 (Purpose)
- §2 (Design Principles, especially Invariants)
- §5 (Data Structures)
- §10.2 (Service Interface)

Create:
- backend/heart/ss{XX}_{name}/service.py
- All methods from §10.2 with type hints
- Stub implementations (NotImplementedError) for now
- Docstrings referencing spec sections

Constraints (cite specific INV-{X}-N from §2.2):
- {INV-X-1}: ...
- {INV-X-N}: ...

Add test scaffolding tests/unit/test_{name}_service.py.

Don't implement methods yet. Just interface.
```

## 6.2 任务: Bug Fix

**Tool**: CC-S46 (default) or CC-Opus (complex)
**模板**:

```
Bug investigation and fix.

Symptoms:
[describe what's happening]

Expected:
[what should happen]

Steps:
1. Reproduce with a test (write failing test first)
2. Find root cause via:
   - Reading relevant subsystem spec
   - Checking recent changes (git log -p relevant_file)
   - Adding strategic logging
3. Determine: spec issue OR implementation issue?
   - Spec issue → STOP, escalate (need RFC)
   - Impl issue → fix
4. Fix code
5. Verify test passes
6. Run regression tests for the subsystem
7. Report: root cause, fix description, tests added

Subsystem: {SS-XX}
Relevant spec: /runtime_specs/{XX}_*.md
```

## 6.3 任务: 写 Unit Tests

**Tool**: CC-Haiku 或 CC-S46
**Haiku 适用**: Test scaffolding, simple cases
**Sonnet 适用**: Complex test logic, fixtures

**Haiku 模板**:

```
Generate unit tests for {file_path}.

Read the source code and create tests following the project pattern (see existing tests/unit/).

Cover:
- Happy path (each public method)
- Edge cases (None, empty, boundary)
- Error cases (invalid input → expected exception)

Use pytest + pytest-asyncio.

Don't test:
- Implementation details (private methods)
- External library behavior
- LLM responses (mock them)

Just scaffold. I'll add scenario-specific tests later.
```

**Sonnet 模板** (more complex):

```
Generate comprehensive tests for {file_path} per /runtime_specs/{XX}.md §11 (test fixtures).

Cover all fixtures in §11:
- fixture_XXX_1
- fixture_XXX_2
- ...

For each fixture:
- Setup test state per fixture spec
- Execute the relevant method
- Assert all expected properties from fixture
- Provide good failure messages

Use pytest fixtures for shared setup.
Use pytest.mark.asyncio for async tests.
Mock external dependencies (LLM, DB at integration test level).

After writing, run pytest tests/unit/test_{file}.py -v and report failures.
```

## 6.4 任务: 代码 Review

**Tool**: CC-S46
**模板**:

```
Review the PR at branch {branch_name} (or files: {file_paths}).

Reference: /engineering_execution/HUMAN_REVIEW_CHECKLIST.md

Check each item:

1. Spec Compliance:
   - Which spec section does this implement?
   - Does code match spec?
   - Cite mismatches.

2. Invariants:
   - List all INV-{X}-N from the relevant subsystem's §2.2
   - For each, check code complies

3. Cross-Subsystem Impact:
   - Does this affect other subsystems?
   - Events / interfaces changed?

4. User Isolation:
   - Every DB query has user_id filter? Cite each.

5. Cost Impact:
   - New LLM calls? In hot path or async?
   - Critic sampling unchanged?

6. Soul-Sensitivity:
   - Touches Soul Spec? voice_dna? Anti-pattern? Care Path?
   - If yes → REJECT, escalate to Human (Tech Lead).

7. Verification:
   - Tests added?
   - Tests cover spec fixtures?

Output:
- APPROVE / REQUEST_CHANGES / REJECT
- Specific feedback per item

Be strict. Don't approve borderline cases.
```

## 6.5 任务: Refactor

**Tool**: CC-S46 (small) or CC-Opus (architectural)
**模板** (Sonnet):

```
Refactor {file_or_module} per the following requirement: {requirement}.

Constraints:
- Don't change external interface (other modules use this)
- Don't introduce new abstractions (Law: rule of 3)
- Preserve all INV-{X}-N from /runtime_specs/{XX}.md §2.2

Process:
1. Understand current structure (Read + Grep)
2. Show me your refactor plan (EnterPlanMode)
3. Wait for my approval
4. Implement
5. Run all tests for affected modules
6. Verify no behavior change (regression tests pass)

Output the diff. Show me before/after for any non-trivial change.
```

## 6.6 任务: 性能优化

**Tool**: CC-Opus (analysis) → CC-S46 (impl)
**模板** (Opus first):

```
Performance investigation for {component}.

Symptoms: {latency above target, e.g., P95 > 300ms}.

Process:
1. Read /runtime_specs/{XX}.md §10.5 (performance targets)
2. Profile the component (suggest profiling approach)
3. Identify hotspots
4. Propose optimization strategies
5. For each:
   - Expected improvement
   - Risk (cost, complexity)
   - Tradeoff

Don't implement yet. Analyze and discuss.
Output: Optimization plan with prioritized list.

I'll pick one, then we'll implement with CC-S46.
```

## 6.7 任务: Schema Migration

**Tool**: CC-Haiku
**模板**:

```
Generate Alembic migration for the following schema change:

Change: {describe schema change}
Affects table: {table_name}

Requirements:
- Backwards-compatible (Law 7)
  - Add column: default NULL or specific default
  - Don't drop column in same migration as code change
  - Add index: CONCURRENTLY
- Reversible (downgrade implemented)
- Use proper PG types (vector, jsonb where appropriate)

Reference /runtime_specs/{XX}.md §10.2 if affecting that subsystem.

Output: migrations/versions/XXX_description.py

Don't add type hints (Alembic style).
Don't run the migration (just generate).
```

## 6.8 任务: Documentation 生成

**Tool**: CC-Haiku
**模板**:

```
Generate API documentation for {file_or_module}.

Format: Google-style docstrings.

For each public function/class:
- One-line summary
- Args section with type and description
- Returns section
- Raises section (if applicable)
- Example usage (if non-obvious)

DO NOT:
- Document private methods (_underscore)
- Describe implementation details
- Reference deprecated functionality

Just docstrings. Don't change function bodies.
Show me the diff.
```

## 6.9 任务: Continue + VSCode Inline (VS-Continue)

**适用场景**: 单文件、局部编辑、type hints、import 调整

**配置**:

`~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "DeepSeek V4",
      "provider": "openai",
      "model": "deepseek-chat",
      "apiKey": "sk-xxx",
      "apiBase": "https://api.deepseek.com/v1",
      "completionOptions": {
        "maxTokens": 2000,
        "temperature": 0.3
      }
    }
  ],
  "tabAutocompleteModel": {
    "title": "DeepSeek V4 Autocomplete",
    "provider": "openai",
    "model": "deepseek-chat",
    "apiKey": "sk-xxx",
    "apiBase": "https://api.deepseek.com/v1"
  },
  "tabAutocompleteOptions": {
    "useCopyBuffer": false,
    "useFileSuffix": true,
    "maxPromptTokens": 1500,
    "debounceDelay": 350
  }
}
```

**使用方式**:

```
1. 写代码时, Tab 接受 inline completion (DeepSeek)
2. Cmd+L 打开 chat, 提问/refactor
3. Cmd+I inline edit (选中代码后)

适用任务:
  - 单函数实现 (函数签名已写好, 让它填 body)
  - Type hints 添加
  - Import 整理
  - Docstring 写作
  - 小范围 refactor (一个文件内)
  - Code 解释 (Cmd+L "explain this")
```

**不适用**:
- 多文件改动 → 用 Claude Code CLI
- 架构决策 → 用 CC-Opus
- 任何 personality-sensitive → Human

## 6.10 任务: Prompt 写作 (Critic / Director / Care Path)

**Tool**: CC-Opus (design) + HUMAN (final wording)
**模板** (Opus):

```
Help me design the {prompt_name} prompt per /runtime_specs/{XX}.md §{section}.

Constraints:
- Used by {agent_name} agent
- Model tier: {cheap/main}
- Output format: {JSON/text}
- Length budget: {tokens}

Existing similar prompts (for reference):
- {paste existing prompt}

Process:
1. Identify the inputs (context variables)
2. Identify the desired output
3. Draft the prompt with clear sections
4. Show me example input → output pairs
5. Identify failure modes (ambiguous inputs)
6. Refine

Output: Draft prompt template + 3 example I/O pairs.

I'll review wording manually before saving.
```

## 6.11 任务: 写 Soul Spec / Activity Pool / Anti-pattern

**Tool**: **HUMAN ONLY** (Opus 可 brainstorm)
**模板** (brainstorm only):

```bash
claude --model opus
```

```
I'm authoring {soul_spec | activity_pool | anti_patterns} for character {character_name}.

Read /runtime_specs/01_identity_anchor_soul_spec.md.

Help me brainstorm but DO NOT save files.

Reference existing: {paste existing similar content}

Help me:
1. Generate 10 candidate {items}
2. For each, explain why it fits this character
3. Suggest 5 that I should NOT use (would be off-character)

I will MANUALLY review, edit, and save.

Don't use Write tool. Just propose.
```

---

# 第七部分: 跨阶段通用规则

## 7.1 Session 启动 Checklist

每次启动 Claude Code session, 走这个 checklist:

```
□ 我在哪个 Phase?
□ 我在哪个 Subsystem?
□ 这是什么任务类型 (impl / bug / refactor / design / review)?
□ 我已经查 AI_MODEL_ROUTING.md 决定 model 了吗?
□ 我已经看 Phase 详细操作了吗?
□ 我有相关 spec section 的位置 (line numbers)吗?
□ 我有 prompt template 吗 (copy from §6)?
□ 我准备好 EnterPlanMode (复杂任务) 吗?
```

## 7.2 Prompt 写作 7 原则

```
1. 明确引用 spec section (with line numbers if possible)
2. 列出 constraints (INV-X-N 显式)
3. 说明 不要做什么 (negative space)
4. 输出格式明确 (文件、code、diff、analysis)
5. 后续步骤清晰 (write code? plan first? test?)
6. 验证标准明确 (tests pass? specific assertions?)
7. 长度合理 (太长 → 拆分; 太短 → 缺信息)
```

## 7.3 Multi-Session Workflow

```
当一个大任务需要 multiple sessions:

Session 1 (Design): CC-Opus
  - 设计 + plan
  - 输出: docs/design/{task}.md

Session 2 (Implement Part 1): CC-S46
  - 读 design doc
  - 实施第一部分
  - 完成后 /clear or restart

Session 3 (Implement Part 2): CC-S46
  - Restart clean session
  - 读 design doc
  - 实施第二部分

Session 4 (Integration + Test): CC-S46
  - 集成 + 测试

不要:
  - 一个 session 跑到底 (context 爆炸)
  - 每个 session 重新 "你好, 我们在做什么"
```

## 7.4 Cost Tracking 工具

每次 session 结束记录:

```
Session ID: 2026-05-15-001
Date/Time: 2026-05-15 09:30-11:45
Model: claude-sonnet-4-6
Task: Implement SS02 FastEncoder
Files touched: backend/heart/ss02_memory/encoder/fast.py
                tests/unit/test_fast_encoder.py
Input tokens: ~15,000
Output tokens: ~3,500
Estimated cost: $0.10
Notes: Used Read with offset to limit context.

(保存到 docs/session_log.md or 类似)
```

每周汇总:

```
Week 8 Summary:
  Total sessions: 23
  Total cost: $35
  Models used: Sonnet 4.6 (90%), Haiku (8%), Opus (2%)
  Top tasks: SS02 implementation, schema generation
  Waste detected: 2 sessions where context > 50k (should have restarted earlier)
```

## 7.5 What to Do When Stuck

```
Symptom: AI is going in circles, making same mistakes

Actions:
1. /clear and restart with clean context
2. Re-read the spec section carefully (Human)
3. Try Opus for the failing task (Opus reasoning often resolves)
4. Search /runtime_specs/ for related guidance
5. Ask Tech Lead (Human)

Don't:
- Keep nudging same AI
- Lower model (Haiku won't solve what Sonnet can't)
- Abandon spec and "wing it"
```

---

# 第八部分: 完整 Phase × Task × Model 矩阵

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         Phase 0: Foundation                                          │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Project skeleton              │ CC-S46       │ FastAPI, project structure           │
│ Alembic setup                 │ CC-Haiku     │ Migration boilerplate                │
│ LLM Provider abstraction      │ CC-S46       │ Multi-provider, critical             │
│ Cost Tracker                  │ CC-S46       │ Important, careful                   │
│ K8s YAMLs                     │ CC-Haiku     │ Templates                            │
│ CI/CD pipeline                │ CC-S46       │ Influences all PRs                   │
│ Observability setup           │ CC-S46       │ Cross-cutting                         │
│ Echo bot endpoint             │ CC-S46       │ E2E verification                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                         Phase 1: Soul Spec + Anchor                                  │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Soul Spec authoring (Rin)     │ HUMAN+Opus   │ 100% Human, Opus brainstorm only     │
│ Soul Spec authoring (Dorothy) │ HUMAN+Opus   │ Same                                 │
│ Golden Dialogues              │ HUMAN+Opus   │ Per character, 10+ each              │
│ Schema Validator              │ CC-S46       │ Standard impl                        │
│ Anchor Injector               │ CC-Opus→S46  │ Design then impl                     │
│ Drift Detector                │ CC-Opus→S46  │ Design then impl                     │
│ Resonance Tracker             │ CC-S46       │ Standard                             │
│ Facet Unlocker                │ CC-S46       │ Multi-condition logic                │
│ Soul Activation State Service │ CC-S46       │ Service layer                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                         Phase 2: Memory Runtime                                      │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ SQLAlchemy models             │ CC-Haiku     │ Translation                          │
│ Memory Service skeleton       │ CC-S46       │ Critical interface                   │
│ Fast Heuristic Encoder        │ CC-S46       │ Performance critical                 │
│ LLM Encoder Worker            │ CC-S46       │ Worker pattern + LLM                 │
│ Decay Engine                  │ CC-Opus→S46  │ Math review then impl                │
│ Multi-Strategy Retriever      │ CC-S46       │ Complex orchestration                │
│ Reconstructor                 │ CC-Opus→S46  │ Soul-aware                           │
│ Forgetting Affect Engine      │ CC-S46       │ Standard                             │
│ Consolidator Worker           │ CC-S46       │ Pipeline                             │
│ L3→L4 Promotion               │ CC-S46       │ Multi-condition                      │
│ Reinforcer                    │ CC-S46       │ Hebbian update                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                         Phase 3: Emotion + Relationship (parallel)                   │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Emotion State Machine         │ CC-S46       │ Standard impl                        │
│ Trigger Detector              │ CC-S46       │ Lexicon-based                        │
│ Decay (emotion-specific)      │ CC-S46       │ Per profile                          │
│ Contagion Engine              │ CC-S46       │ With Soul reading                    │
│ Mood Drift Engine             │ CC-S46       │ Scheduled                            │
│ Repair Mechanic               │ CC-Opus→S46  │ Anti-gaming design                   │
│ Stage Phase Engine            │ CC-S46       │ State machine                        │
│ Trust/Attachment Trackers     │ CC-S46       │ Dimension calc                       │
│ Reunion State Machine         │ CC-S46       │ 3-phase logic                        │
│ Cold War Tracker              │ CC-S46       │ With repair integration              │
│ Emotion phrase library        │ HUMAN        │ Per character                        │
│ Stage entry conditions tuning │ CC-Opus+Human│ Balance UX                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                         Phase 4: Composer                                            │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Layer Aggregator              │ CC-S46       │ Parallel orchestration               │
│ Conflict Resolver             │ CC-Opus→S46  │ Matrix complex                       │
│ Token Budget Allocator        │ CC-S46       │ Compression strategies               │
│ Modality Adapter              │ CC-S46       │ Per modality                         │
│ Composer                      │ CC-S46       │ Assembly                             │
│ Anti-Drift Injector           │ CC-S46       │ Decision rules                       │
│ Anti-Pattern Filter (sync)    │ CC-S46       │ AC automaton                         │
│ Streaming Anti-Pattern        │ CC-Opus→S46  │ Algorithm complex                    │
│ Reroll Handler                │ CC-S46       │ Standard                             │
│ Fallback library              │ HUMAN        │ Soul-flavored                        │
│ Critic Agent                  │ CC-Opus+S46  │ Prompt design + impl                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                         Phase 5: Inner State + Behavior                              │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Activity pools                │ HUMAN        │ Per character (20+ each)             │
│ Activity Generator            │ CC-S46       │ Deterministic selection              │
│ Concerns Tracker              │ CC-S46       │ Memory integration                   │
│ Inner State Composer          │ CC-S46       │ Aggregation                          │
│ Inner State Block Builder     │ CC-S46       │ Prompt builder                       │
│ Initiative Decider            │ CC-Opus→S46  │ 8 gates + 7 triggers                 │
│ Anniversary Tracker           │ CC-S46       │ L4 integration                       │
│ Proactive Message Gen         │ CC-S46       │ Via Composer                         │
│ Proactive Scheduler           │ CC-S46       │ Redis ZSET                           │
│ Ritual Manager                │ CC-S46       │ Streak tracking                      │
│ Inner Loop Scheduler          │ CC-S46       │ Hourly + event                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                         Phase 6: Orchestration + Safety                              │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Orchestrator Agent            │ CC-S46       │ Hot/cold path                        │
│ Safety Agent (heuristic)      │ CC-S46       │ Keyword + pattern                    │
│ Safety keywords list          │ HUMAN+legal  │ Sensitive                            │
│ Safety Agent (LLM layer)      │ CC-S46       │ With cheap LLM                       │
│ Director Agent                │ CC-S46       │ Pacing rules                         │
│ Critic Agent integration      │ CC-S46       │ Already designed in P4               │
│ Wellbeing Monitor             │ CC-Opus+Human│ Threshold design                     │
│ Wellbeing keywords            │ HUMAN+心理   │ Sensitive                            │
│ Event Bus (Redis Streams)     │ CC-S46       │ Standard                             │
│ Model Router                  │ CC-S46       │ Failover logic                       │
│ Session Manager               │ CC-S46       │ Multi-device                         │
│ Circuit Breaker               │ CC-S46       │ Per service                          │
│ PURPLE Care Path              │ CC-Opus+心理 │ Critical safety                      │
│ Care Path responses           │ HUMAN+心理   │ Critical                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 第九部分: 紧急情况速查

## 9.1 Production 故障

```
症状: User reports / monitoring alert

Step 1 (HUMAN): Triage
  - Severity (critical / major / minor)
  - Affected user count
  - Reproducibility

Step 2 (CC-Opus): Root cause investigation
  - "Investigate: {symptom}. Read recent commits + relevant subsystem spec. 
     Identify possible causes. Do not fix yet."

Step 3 (HUMAN): Decision
  - Hotfix or wait
  - Communicate to users if needed

Step 4 (CC-S46): Implement fix
  - "Implement fix per the analysis: {paste analysis}. 
     Write failing test first, then fix, then verify."

Step 5 (HUMAN): Deploy + monitor
```

## 9.2 LLM Provider Down

```
Symptom: LLM API returning 5xx / timeout

Action 1 (Auto): Model Router failover should trigger
Action 2 (HUMAN): Check Circuit Breaker state
Action 3 (HUMAN): If sustained, manually update llm_routing.yaml
Action 4 (CC-S46): If issue with our integration, fix and deploy
```

## 9.3 用户反馈"她变了"

```
This is Personality Drift.

Step 1 (CC-S46): Run drift analysis
  "Run drift analysis for user {user_id} on character {character_id}.
   Read recent conversation traces. Compare to Soul Spec voice_dna.
   Identify deviation patterns."

Step 2 (HUMAN): Review findings
Step 3 (CC-Opus): If systemic, design fix
Step 4: Fix + verify with golden dialogues regression
```

---

# 第十部分: 入门 30 分钟

如果你是新加入的工程师，30 分钟入门:

```
Minute 1-5: 读 ENGINEERING_LAWS.md (12 laws)
Minute 5-10: 读本文档 §1 (工具箱) + §2 (4.5 vs 4.6)
Minute 10-15: 读 AI_MODEL_ROUTING.md (1-page decision tree)
Minute 15-20: 读 SPEC_DRIVEN_WORKFLOW.md (workflow)
Minute 20-25: 读本文档 §6 (Prompt 库) + §7 (通用规则)
Minute 25-30: 选一个 boilerplate task, 用 CC-S46 + §6.1 模板试一次

恭喜，你可以开始正式工作了。
```

---

**End of Practical Model Guide**

打印此页 (打印! 不是收藏) 放工位上。
