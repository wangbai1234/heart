# 实操指南 (续) — Phase 7+ 工业级执行手册

> **本文件是 PRACTICAL_MODEL_GUIDE.md 的延续**
> Phase 0-6 已完成（spec-level + 单元测试覆盖）。
> 本文件覆盖：**Integration Hardening → Local MVP → Frontend MVP → Closed Alpha → Beta → Production Hardening → Production GA**
> 配套：AI_MODEL_ROUTING.md (路由) + ENGINEERING_LAWS.md (法则) + 本文档 (执行)
> 使用方式：遇到 Phase → 查任务 → 复制 prompt → 微调 → 执行 → 验收

---

# 序章: 当前项目深度分析（2026-05-23 快照）

## 0.1 当前所处阶段

> **结论：项目处于 "Spec-Complete, Integration-Pending" 阶段，距离 MVP 可演示还差 1 个完整 Phase，距离 Production Ready 还差 4-5 个 Phase。**

**已完成（按 commit + 文件证据）：**
- ✅ Phase 0 (Foundation): FastAPI 骨架、Alembic、LLM Provider 抽象、Cost Tracker、K8s YAML、CI/CD、JWT、Echo Bot
- ✅ Phase 1 (Soul Spec + Anchor): Rin + Dorothy soul_specs、Anchor Injector、Drift Detector、Resonance Tracker、Hidden Facet Unlocker
- ✅ Phase 2 (Memory Runtime): SQLAlchemy models、Memory Service、Fast/LLM Encoder、Decay Engine、Multi-strategy Retriever、Reconstructor、Forgetting Affect、Consolidator
- ✅ Phase 3 (Emotion + Relationship): State Machine、Trigger Detector、Decay、Contagion、Mood Drift、Repair、Stage Phase Engine、Trust/Attachment、Reunion、Cold War
- ✅ Phase 4 (Composer): Layer Aggregator、Conflict Resolver、Token Budget、Modality Adapter、Composer、Anti-drift Injector、Anti-pattern Filter、Streaming Anti-pattern、Reroll、Critic Agent
- ✅ Phase 5 (Inner State + Behavior): Activity Generator、Concerns Tracker、Inner State Composer、Block Builder、Initiative Decider、Anniversary、Proactive Message、Scheduler、Ritual Manager、Inner Loop Scheduler
- ✅ Phase 6 (Orchestration + Safety): Orchestrator、Safety Agent (heuristic + LLM)、Director、Wellbeing Monitor、Event Bus、Session Manager、Circuit Breaker、PURPLE Care Path
- ✅ 部分基础设施：DeepSeek-only LLM 架构强制、4 个 Alembic migration、7 个 K8s deployment YAML、71+ initial 测试 + ~1700 tests collected

**核心证据：**
```
backend/heart/         106 .py 源文件
backend/tests/unit/    1679/1694 tests passing (15 deselected, 2 failing)
backend/tests/integration/  仅 1 个 (test_migrations.py)
soul_specs/            2 个角色 (rin, dorothy)
config/                7 个配置目录 (activity_pools, care_path_responses, etc.)
infra/kubernetes/      7 个 service deployment YAML
docs/design/           12 篇关键设计文档
```

## 0.2 哪些部分已达 Production-Grade

| 模块 | 状态 | 证据 |
|------|------|------|
| FastAPI 入口 + Auth | 🟢 Production-grade | JWT 全套测试、Pydantic、structlog |
| LLM Provider 抽象 + Cost Tracker | 🟢 Production-grade | Multi-provider、Prometheus metrics、Redis 存储 |
| Memory L1-L4 + 编码/检索/衰减 | 🟢 Production-grade | 110+ 单元测试覆盖、设计文档完整 |
| SS03 Emotion State Machine | 🟢 Production-grade | Trigger、Decay、Contagion、Mood Drift 全套 |
| SS04 Stage Engine + Reunion/Cold War | 🟢 Production-grade | 最新 3 个 commit 收尾 |
| SS05 Composer + Anti-pattern | 🟡 Production-pending | 单测全过，但**未经真实 LLM 链路 e2e 验证** |
| SS07 Orchestrator + Safety | 🟡 Production-pending | 单测全过，但**Hot path 没有跑过真实 turn** |
| PURPLE Care Path | 🟡 Production-pending | 代码 + 设计完成，但**未做真实 drill** |

## 0.3 哪些部分仍是 Spec-Level

| 模块 | 缺什么 |
|------|--------|
| **跨 Subsystem 集成** | 仅 1 个 integration test (migration)，**SS01-SS07 之间没有端到端测试** |
| **真实 LLM 链路** | 所有 LLM 调用都是 mock，**没有跑过一次真实 DeepSeek turn** |
| **Activity Pool 内容** | 目录存在但内容深度未审计，**spec 要求 20+/角色** |
| **Anti-pattern Lexicon** | 文件存在但**未对照真实生成做过 tuning** |
| **Care Path 响应文案** | YAML 结构在，**心理顾问/法务审阅记录缺失** |
| **可观测性 Dashboard** | Prometheus metrics 在埋点，**Grafana dashboard 未配置** |
| **Frontend** | **完全不存在**——没有任何 UI/CLI 演示客户端 |
| **Load Profile** | **零负载测试** |
| **CI/CD 实际运行** | 配置在但因账单**GitHub Actions 未运行**，本地通过 |
| **Migration Rollback** | 4 个 migration **未做 down → up → down 验证** |

## 0.4 当前最大 Blocker（按优先级）

1. **🔴 P0 — 没有任何 e2e turn 跑通过真实 LLM**
   - 所有 1677 个单测都是 mock LLM
   - 一个真实 turn 触发的链路：Auth → Safety → Orchestrator → Composer → ModelRouter → DeepSeek → Anti-pattern → response → Memory Encode → Inner Loop tick
   - **这条链路一次都没真跑过**
   - 风险：任何一个 contract mismatch 都会让 MVP 演示直接崩

2. **🔴 P0 — 没有 Frontend，无法演示**
   - 哪怕一个 CLI 客户端都没有
   - 没法展示 Inner State / Stage Phase / Anniversary 等核心卖点
   - 无法做 alpha 招募

3. **🟠 P1 — Integration test gap**
   - 1 个 integration test vs 1677 个 unit test = **比例严重失衡**
   - Subsystem 之间的 contract 没有约束
   - Refactor 风险极高

4. **🟠 P1 — CI/CD 实际不跑**
   - 账单问题导致 GitHub Actions 停止
   - 本地通过 ≠ team-wide CI 通过
   - 风险：任何回归都靠人肉发现

5. **🟡 P2 — 2 个 unit test 失败 + 部分 deselected**
   - `test_mood_drift::test_low_volatility_ignores_recent_spike`
   - `test_trust_attachment::test_trust_increase_capped`
   - 15 个 deselected — 需要审计为什么 deselect

## 0.5 当前最大技术风险

| Risk | Severity | 缓解策略 |
|------|----------|---------|
| **Spec/Code 漂移**：100+ 文件由 AI 写，**没人做过架构 audit** | 🔴 High | Phase 7.8 强制架构 audit |
| **Soul Voice 漂移**：Reconstructor + Composer + Anti-drift Injector 三层，但**没有 golden dialogue regression** | 🔴 High | Phase 7.4 建立 drift regression suite |
| **State 不变量违反**：Memory L1-L4、Emotion、Stage、Trust 几十个状态机，**任意一个 corruption 都会让人格崩** | 🔴 High | Phase 7.6 invariant verification 框架 |
| **Migration forward-only**：4 个 migration **没做过 down → up**，prod 一旦回滚就 broken | 🟠 Med | Phase 7.3 migration roundtrip 测试 |
| **DeepSeek 单一依赖**：现在 DeepSeek-only，**provider 一旦宕机服务全停** | 🟠 Med | Phase 11 二级 fallback (但**绝不写回 Anthropic 直连**) |
| **Cost runaway**：Cost Tracker 在埋点，**没有硬上限断路器** | 🟠 Med | Phase 10.7 实装 per-user / per-day cost cap |
| **PURPLE 误报/漏报**：心理顾问审阅记录缺失，**法律/伦理风险** | 🔴 High | Phase 11.7 PURPLE drill + 顾问签字 |

## 0.6 当前最大 AI-Assisted Engineering 风险

> **核心问题：你已经用 Claude Code 写了 100+ 个 Python 文件，但你没有任何机制保证它们仍然遵守 spec。**

按出现概率排序：

1. **🔴 Architecture Drift（架构漂移）**
   - 每个 session AI 都会"自由发挥"一点
   - 21 周 × 多个 session = 累积漂移
   - 表现：不同 subsystem 用了不同 logging pattern、不同 error handling、不同 config style
   - **检测难度极高**，因为每个文件单看都"合理"

2. **🔴 Soul Voice Divergence（人格漂移）**
   - Reconstructor、Composer、Anti-drift Injector、Critic — 4 处都在塑形 voice
   - 每次 AI 改其中一处，都可能让 voice_dna 偏移
   - **没有 golden dialogue 自动 regression**，肉眼审阅必漏

3. **🟠 Prompt Divergence（Prompt 风格漂移）**
   - Composer 里塞给 LLM 的 system prompt 拼装方式现在有 N 个地方组装
   - 不同 commit 拼装顺序、字段命名可能微妙不同
   - **生产环境表现不稳定**

4. **🟠 State Corruption（状态损坏）**
   - Memory L1→L2→L3→L4 promotion 的 idempotence、Stage transition 的 atomicity、Cold War→Reunion transition 的 once-only — 大量隐含不变量
   - AI 改 service code 时很可能违反**它没意识到的不变量**
   - **现在的单测只测显式行为，不测不变量**

5. **🟠 Agent Orchestration Chaos**
   - Orchestrator + Safety + Director + Critic + Wellbeing + PURPLE = 6 个 agent
   - 调用顺序、互相 short-circuit、并发模式现在散落在多个文件
   - **没有一张图证明这套编排是正确的**

6. **🟠 Context Explosion（上下文爆炸）**
   - 单文件已经几百行（如 orchestrator.py / composer.py）
   - 下一次让 AI 改这些文件，Read 一次就吃几千 token
   - **Cost + 错误率都会暴涨**

7. **🟡 Technical Debt（技术债）**
   - 12 篇 design doc + 多个 implementation_summary.md 在 docs/design/，但**没有 master index**
   - PHASE_0_COMPLETION_REPORT.md / CI_FIX_REPORT.md / CHANGES_SUMMARY.md 散在根目录 — 找信息会越来越难
   - AGENTS.md 在仓库根但与 .claude/CLAUDE.md 关系不明

8. **🟡 Runtime Inconsistency（运行时不一致）**
   - Local docker-compose vs K8s deployment 的 env vars、image build chain、secret 来源**都未对齐**
   - "本地能跑、staging 跑不起来"几乎必然发生

> **对应防御机制详见 第八部分: AI-Assisted Engineering 防御机制。这一部分是本指南的真正灵魂——必须立刻执行。**

---

# 第一部分: Phase 7 — Integration Hardening (Week 31-34)

> **目标**: 把已存在的 100+ 文件**真正连起来**，建立 integration / contract / drift 三套测试金字塔。
> 主力 tool: **CC-S46** + **CC-Opus**（架构 audit + drift suite 设计）
> **完成判定**: 真实 DeepSeek 跑通至少 1 个完整 turn + 50+ integration tests + 0 failing + drift regression baseline
> 入口：`runtime_specs/08_engineering_architecture.md` §6（Observability）+ `runtime_specs/00_runtime_worldview.md`
> Phase 7 Token 预算：**~$400-600**

## 1.1 Task: 修复存量 2 个失败单测

**Tool**: CC-S46
**Why**: 简单 bug，但**绝不允许带病进入 Phase 7**

**Prompt**:

```
Two unit tests are currently failing on main branch of the Heart project:

1. backend/tests/unit/test_mood_drift.py::TestVolatilityModulation::test_low_volatility_ignores_recent_spike
2. backend/tests/unit/test_trust_attachment.py::test_trust_increase_capped

For each:
1. Read the test file (with Read + offset) to understand expectation
2. Read the source module under test
3. Identify whether the bug is in the test (incorrect expectation) or in the implementation (violates spec)
4. Cite the relevant spec section from /runtime_specs/03_emotion_state_machine.md or /runtime_specs/04_relationship_phase_engine.md
5. Fix the side that disagrees with spec — DO NOT just edit the test to make it pass

Also audit: why are 15 tests in the suite marked as @pytest.mark.skip or deselected?
- List each one
- Classify: legitimate (waiting on dependency) vs lazy (just left broken)
- For lazy ones, write a fix or open a clearly-named TODO test stub

Commit as: "fix: stabilize mood_drift + trust_attachment tests + audit deselected tests"
```

**验收**:
```
□ pytest tests/unit -q 显示 0 failed
□ deselected list 有 audit 记录在 docs/test_audit.md
□ 每个 fix 引用 spec line number
```

## 1.2 Task: 建立 Integration Test Pyramid 框架

**Tool**: CC-Opus (设计) → CC-S46 (实施)
**Why**: 这是 Phase 7 的脊柱，错了后面全错

**设计 prompt (Opus)**:

```bash
claude --model opus
```

```
Design the integration test pyramid for the Heart project.

Context:
- 1677 unit tests already exist (all mocked LLM)
- Only 1 integration test (migrations)
- Subsystems SS01-SS07 + safety all exist as Python modules
- We do NOT want to spin up real DeepSeek for every test (cost), but we need SOME real-LLM tests

Constraints:
- Must work in local docker-compose
- Must work in CI (when billing fixed)
- Three test tiers:
  Tier A: Contract tests (between subsystems, no DB, no LLM) — fast, run on every PR
  Tier B: Integration tests (real Postgres + Redis, fake LLM) — run on every PR, ~5 min
  Tier C: Live tests (real DeepSeek, real DB) — run nightly + on release, cost-capped

For each tier:
1. Folder structure
2. Fixture strategy (conftest.py)
3. Naming convention
4. CI gate
5. Failure debugging workflow
6. Cost ceiling for Tier C

Critical:
- Tier B must be deterministic (no flaky)
- Tier C must have a $/run hard cap (kill switch)
- Soul drift regression goes in Tier C — design the harness

DO NOT WRITE CODE YET. Output: docs/design/integration_test_pyramid.md.
Reference: backend/tests/integration/test_migrations.py as the only existing example.
```

**实施 prompt (S46)**:

```
Implement the integration test pyramid per docs/design/integration_test_pyramid.md.

Create:
1. backend/tests/contract/  — Tier A
   - conftest.py with subsystem fixtures (Soul + Memory + Emotion + Relationship + Composer)
   - test_ss05_consumes_ss03.py  — Composer reads EmotionState correctly
   - test_ss07_calls_ss05_then_router.py  — Orchestrator wiring
   - test_safety_short_circuits_composer.py  — Safety stops the pipeline
   - ~10 contract tests covering all critical cross-SS edges

2. backend/tests/integration/  (extend)
   - conftest.py with real PG + Redis (testcontainers)
   - test_memory_lifecycle.py  — encode → decay → consolidate → reconstruct
   - test_emotion_lifecycle.py  — trigger → state → decay → repair
   - test_relationship_progression.py  — Stage 1 → 2 → 3 with real time-travel
   - test_orchestrator_hot_path.py  — full turn with FAKE LLM
   - test_inner_loop_tick.py  — proactive trigger end-to-end

3. backend/tests/live/  — Tier C
   - conftest.py with $/run budget enforcement
   - test_real_turn_smoke.py  — exactly 1 turn with real DeepSeek (cost-capped at $0.10/run)
   - test_voice_dna_baseline.py  — generates 10 turns for Rin, saves to golden_responses_baseline.jsonl
   - .pytest_live.ini with `--live` marker, skipped by default

Update backend/pyproject.toml + pytest.ini:
- markers: contract, integration, live
- live skipped without --live flag

Update Makefile:
- test-contract: pytest -m contract
- test-integration: pytest -m integration
- test-live: pytest -m live --live (requires DEEPSEEK_API_KEY)

NO mocked LLM in Tier C. Use heart.infra.llm.router with real provider.
Cost budget for one full Tier C run must be < $1.00.
```

**验收**:
```
□ make test-contract  全过
□ make test-integration  全过 (with testcontainers)
□ make test-live  显式 opt-in, 真实 DeepSeek 1 turn 跑通
□ docs/design/integration_test_pyramid.md 存在
```

## 1.3 Task: Migration Forward/Backward Roundtrip 验证

**Tool**: CC-S46
**Why**: 4 个 migration 从未做过 down → up 验证

**Prompt**:

```
Audit and verify Alembic migrations under backend/migrations/versions/.

Existing migrations:
- e814230ade46_initial_empty_schema_revision.py
- 001_add_memory_tables.py
- 002_add_emotion_relationship_tables.py
- 003_ss04_threshold_tuning_v1_1.py

Tasks:
1. For each migration, verify it has a working downgrade()
   - If downgrade() is `pass` or missing → write a real one based on upgrade()
2. Create backend/tests/integration/test_migration_roundtrip.py
   - For each pair (upgrade, downgrade): up → down → up → down
   - Assert table schema is identical at each "up" state
   - Use testcontainers Postgres
3. Add a stamp version test: alembic stamp head + alembic current must match

Constraints:
- Do not delete production data structures
- Each downgrade() must be reviewed against the corresponding spec (SS02 §10, SS03 §10, SS04 §10)

Commit as: "test: add migration roundtrip integration tests + fill missing downgrades"
```

## 1.4 Task: Soul Drift Regression Suite

**Tool**: CC-Opus (设计) → CC-S46 (实施)
**Why**: 这是防止 AI 改 Composer/Reconstructor 时把人格写崩的唯一保险

**设计 prompt (Opus)**:

```bash
claude --model opus
```

```
Design the Soul Drift Regression Suite for the Heart project.

Context:
- Soul Specs exist for: rin, dorothy
- Soul Spec includes voice_dna with phrases, anti_patterns, tone descriptors
- Composer (SS05) + Reconstructor (SS02) + Anti-drift Injector + Critic Agent all shape voice
- AI will keep modifying these over time
- We need a regression suite that catches voice drift across releases

Critical:
- LLM-as-judge will be used to score voice similarity (DeepSeek)
- Need a baseline set of "this is canonical Rin/Dorothy" generations
- Drift score per dimension (warmth, formality, signature phrases, anti-pattern leakage)
- Score below threshold → block merge

Design:
1. Baseline generation procedure (one-time per character)
   - 30 canonical prompts × 1 generation each = 30 baseline samples
   - Stored as JSONL with metadata (model, temp, soul_spec_version, timestamp)

2. Regression scoring procedure (per PR)
   - Same 30 prompts → new generations
   - Per-sample: LLM-as-judge produces 5-dim score vs baseline
   - Aggregate: drift_score = weighted mean
   - Pass threshold: drift_score < 0.15 (TUNE THIS)
   - Anti-pattern leakage: hard zero tolerance

3. Diff visualization
   - HTML diff page: baseline vs new, side-by-side
   - Highlight: changed signature phrases, anti-pattern hits

4. False-positive handling
   - Approved drift: human-approved diff bumps the baseline
   - Document workflow in docs/soul_drift_baseline_update.md

DO NOT WRITE CODE YET. Output: docs/design/soul_drift_regression.md.
Cost budget: full regression run ~$0.50 per character.
```

**实施 prompt (S46)**:

```
Implement Soul Drift Regression Suite per docs/design/soul_drift_regression.md.

Create:
1. backend/heart/qa/  (new package)
   - voice_judge.py  — LLM-as-judge wrapper (uses ModelRouter cheap tier)
   - drift_scorer.py  — 5-dim scoring
   - baseline_runner.py  — generates baseline given a soul_spec + prompt set
   - regression_runner.py  — compares new gen vs baseline
   - report_builder.py  — HTML diff output

2. config/voice_drift/
   - canonical_prompts.yaml  — 30 prompts (general categories: smalltalk, intimate, conflict, support)
   - baselines/
     - rin_baseline.jsonl  (to be generated)
     - dorothy_baseline.jsonl  (to be generated)
   - thresholds.yaml  — drift_score = 0.15, anti_pattern_tolerance = 0

3. backend/tests/live/test_voice_drift.py
   - Marker: @pytest.mark.live + @pytest.mark.drift
   - Runs regression vs baselines/{character}_baseline.jsonl
   - Fails if drift_score > threshold or any anti_pattern hit

4. CLI tool: backend/scripts/run_voice_drift.py
   - Subcommands: generate-baseline, regress, report
   - Outputs HTML diff to /tmp/heart_drift_report.html

5. Makefile:
   - voice-baseline: python backend/scripts/run_voice_drift.py generate-baseline --character {rin,dorothy}
   - voice-regress: pytest backend/tests/live/test_voice_drift.py --live

Constraint: All LLM calls via ModelRouter. No direct provider SDK.
Cost cap: enforce $1.00 cap per full regression via Cost Tracker hook.
```

**验收**:
```
□ make voice-baseline 跑通 (生成 rin + dorothy 各 30 个 baseline 样本)
□ make voice-regress 跑通 (vs 当前 main)
□ /tmp/heart_drift_report.html 渲染
□ docs/soul_drift_baseline_update.md 记录 baseline update workflow
```

## 1.5 Task: Cross-Subsystem Contract Tests（细化）

**Tool**: CC-S46
**Why**: 1.2 的 Tier A 是脚手架，1.5 是具体合同清单

**Prompt**:

```
Generate the full Cross-Subsystem Contract Test list for the Heart project.

For each edge in this graph, create one contract test:

SS01 Soul → SS02 Memory: Soul state influences Reconstructor voice_dna selection
SS01 Soul → SS05 Composer: Soul layer is the highest-priority layer
SS02 Memory → SS05 Composer: Retrieved memories arrive with state-aware scoring
SS03 Emotion → SS04 Relationship: Emotion deltas feed into Stage signal aggregator
SS03 Emotion → SS05 Composer: Current emotion state shapes tone
SS04 Relationship → SS05 Composer: Current Stage modifies intimacy register
SS04 Relationship → SS06 Inner State: Stage transitions trigger reflection
SS06 Inner State → SS05 Composer: Inner State block added to prompt
SS06 Inner State → SS07 Orchestrator: Initiative signals reach proactive scheduler
SS07 Orchestrator → SS05 Composer: Director hints applied
SS07 Safety → ALL: Safety pre-filter halts pipeline at PURPLE
SS07 ModelRouter → LLM Providers: provider failover correct
SS07 Circuit Breaker → ModelRouter: breaker open → fallback path

For each:
1. Test file: backend/tests/contract/test_{from_ss}_to_{to_ss}.py
2. Assert ONLY the interface contract (data shape, ordering, idempotency)
3. NO real DB, NO real LLM, use in-memory fakes
4. Each test < 100ms
5. Reference INV-X-N invariants from the relevant spec

Output: 13+ contract test files. Commit as one commit per file is fine.

Constraint: If you find that two subsystems don't actually have a clear contract surface, STOP and write a contract gap report to docs/contract_gaps.md. Don't fabricate an interface.
```

## 1.6 Task: State Invariant Verification Framework

**Tool**: CC-Opus (设计) → CC-S46 (实施)
**Why**: 单测只测显式行为，**不变量**才是 AI 改 service code 最容易破的东西

**设计 prompt (Opus)**:

```bash
claude --model opus
```

```
Design State Invariant Verification framework for the Heart project.

Context:
- Many subsystems have implicit invariants:
  - SS02 Memory: L1 ⊂ L2 ⊂ L3 ⊂ L4 promotion is one-way; total_count monotonic
  - SS03 Emotion: valence ∈ [-1, 1]; arousal ∈ [0, 1]; transition graph acyclic mid-turn
  - SS04 Stage: stage transitions monotonic except via explicit reset; trust ≤ 1
  - SS04 Reunion: each user-character pair has at most 1 active reunion at a time
  - SS04 Cold War: cold_war duration cap
  - SS06 Initiative: cooldown enforced across restart
  - SS07 Safety: PURPLE level NEVER produces a Soul-voiced response

- AI agents will keep modifying service code
- We need a runtime + test-time mechanism that catches invariant violations

Design two layers:

Layer 1: Test-time property-based tests (Hypothesis)
- For each invariant: a hypothesis test that generates random valid input sequences and asserts invariant holds
- Place: backend/tests/properties/

Layer 2: Runtime invariant assertions
- Decorator-based: @invariant("memory.l1_subset_l2")
- Centralized registry: backend/heart/infra/invariants.py
- Enabled in DEV; sampled in PROD (1% of turns); always-on in tests
- Violation → structured log + Prometheus counter + Sentry

Output: docs/design/state_invariants.md with full invariant list:
- ID (INV-XX-N format)
- Subsystem
- Predicate (formal)
- Severity (FATAL / WARN)
- Source spec line
- Test strategy

DO NOT WRITE CODE YET.
```

**实施 prompt (S46)**:

```
Implement State Invariant Verification per docs/design/state_invariants.md.

Phase 1 (this commit):
1. backend/heart/infra/invariants.py
   - InvariantRegistry singleton
   - @invariant(name, predicate, severity) decorator
   - check_invariants(context) called at strategic points
   - Prometheus counter: heart_invariant_violations_total{name, severity}
   - Structured log on violation

2. backend/tests/properties/  (new dir, hypothesis-based)
   - test_memory_invariants.py    — INV-M-*
   - test_emotion_invariants.py   — INV-E-*
   - test_relationship_invariants.py — INV-R-*
   - test_safety_invariants.py    — INV-S-*

3. Wire @invariant decorator onto critical service methods:
   - MemoryService.promote(), MemoryService.consolidate()
   - EmotionService.transition()
   - StageEngine.advance(), StageEngine.regress()
   - SafetyAgent.classify()

4. Sampling middleware in Orchestrator hot path: run all invariants at 1% sample rate

Constraint:
- Hypothesis tests must run in < 30s for the whole suite
- Invariant violation in DEV → raise; in PROD → log only (configurable via env)

Commit as: "feat: add State Invariant Verification framework (Layer 1 + 2)"
```

## 1.7 Task: 架构 Audit（CC-Opus）

**Tool**: CC-Opus
**Why**: 21 周 AI 自由发挥 → 现在必须人工 + Opus 联合 audit

**Prompt**:

```bash
claude --model opus
```

```
Conduct an Architecture Audit of the Heart project at the current main branch HEAD.

You will audit 7 dimensions. For each, produce findings + severity + remediation.

Dimensions:

1. Layering integrity
   - Are infra/, ss01..ss07/, safety/, workers/, api/ boundaries respected?
   - Any cross-layer leak? (e.g. ss03 importing from api)
   - Method: grep imports across all packages

2. Cross-cutting concern consistency
   - Logging pattern (structlog?)
   - Error handling pattern
   - Config access pattern
   - Async/sync mixing
   - Method: sample 5 files per subsystem, compare patterns

3. LLM Router enforcement
   - Are ALL LLM calls via heart.infra.llm.router?
   - Any direct anthropic.* or openai.* imports?
   - Method: grep -rn "import anthropic\|from anthropic\|import openai\|from openai" backend/heart/

4. Soul Spec consumption pattern
   - Each subsystem reading Soul Spec uses the same loader?
   - Any subsystem caching Soul Spec inconsistently?

5. State store consistency
   - Postgres for persistent, Redis for ephemeral — respected?
   - Any subsystem writing where it shouldn't?

6. Spec-to-code traceability
   - For each module, can you identify the spec section it implements?
   - Look for # SS0X §Y.Z comments or docstrings
   - Modules without traceability → list

7. Test coverage by surface area
   - List modules with < 50% unit test line coverage (estimate from test file presence)
   - Critical surfaces (Orchestrator, Composer, Safety) MUST be > 80%

Output:
- docs/audit/2026-05-23_architecture_audit.md
- Findings table: dimension | finding | severity (Critical/High/Med/Low) | file/line | remediation
- Top 10 immediate-action items

Constraints:
- Use Read with offset to keep context manageable
- Do NOT fix anything. Audit only.
- Do not skim — for critical modules (orchestrator, composer, safety), read fully.
```

**验收**:
```
□ docs/audit/2026-05-23_architecture_audit.md 生成
□ 至少 30 个 findings (如果少于这个数，audit 不够深)
□ Top 10 action items 有 owner + 优先级
```

## 1.8 Task: Spec ↔ Code 双向追溯表

**Tool**: CC-Haiku（机械梳理）
**Why**: 没人记得 backend/heart/ss04_relationship/stage_engine.py 实现的是 spec §3.几

**Prompt**:

```
Build a Spec ↔ Code traceability matrix for the Heart project.

For each .py file under backend/heart/ (excluding __init__.py, __pycache__, tests):
1. Read the docstring + top 20 lines
2. Extract any "§X.Y" or "SS0N" or "INV-X-N" references
3. Build entries:
   { file_path, primary_spec, sections_referenced[], invariants_referenced[], orphan? }
4. Orphan = file with no spec reference at all

Output: docs/audit/spec_code_matrix.md
- Sorted by subsystem
- Highlight orphan modules
- Highlight spec sections with NO code references (over-spec)
- Highlight code with NO spec backing (under-spec)

This is purely mechanical. Do not interpret. Just extract and tabulate.
```

## 1.9 Phase 7 Session 安排

```
Week 31:
  Day 1:   CC-S46 — 1.1 修复 2 个失败测试 + audit deselected
  Day 2-3: CC-Opus — 1.2 设计 integration pyramid + 1.4 设计 drift suite
  Day 4-5: CC-S46 — 1.2 实施 Tier A 框架

Week 32:
  Day 1-2: CC-S46 — 1.2 实施 Tier B integration tests
  Day 3:   CC-S46 — 1.3 migration roundtrip
  Day 4-5: CC-S46 — 1.5 contract tests 13 个

Week 33:
  Day 1-2: CC-S46 — 1.6 实施 Invariant Layer 1 + 2
  Day 3-4: CC-Opus — 1.7 架构 audit (允许 1 整天)
  Day 5:   HUMAN — 阅读 audit 报告 + 决定 remediation 顺序

Week 34:
  Day 1-2: CC-S46 — Top 5 audit 项的 remediation
  Day 3:   CC-S46 — 1.4 实施 voice drift suite
  Day 4:   HUMAN+CC-S46 — 1.4 生成 baseline (花真钱跑 DeepSeek)
  Day 5:   CC-Haiku — 1.8 Spec ↔ Code matrix + Phase 7 cut criteria 验收
```

**Phase 7 Cut Criteria（强制）**:
```
□ pytest tests/  0 failed
□ 1 个 real-LLM e2e turn 跑通（Tier C 至少 1 个）
□ Voice drift baseline 已存盘（rin + dorothy）
□ docs/audit/2026-05-23_architecture_audit.md ≥ 30 findings, Top 10 已 remediation
□ contract_gaps.md 不存在或为空
□ 4 个 migration 全部 down → up 验证
□ Invariant Registry 注册 ≥ 15 个不变量
```

---

# 第二部分: Phase 8 — Local MVP (Week 35-38)

> **目标**: 让一个人在本地 `make demo` 就能体验完整 turn（含 Inner State、Stage Phase、Anniversary、Proactive Message）。
> 主力 tool: **CC-S46** + **HUMAN**（脚本演示设计）
> **完成判定**: 本地 docker-compose 起来 → CLI 客户端可以跟 Rin / Dorothy 持续对话 ≥ 30 turns，覆盖至少 1 次 stage 升级、1 次 proactive message、1 次 cold-war-then-reunion
> 入口：`Makefile` + `docker-compose.yml`
> Phase 8 Token 预算：**~$200-400**

## 2.1 Task: 完整本地栈 (`docker-compose.yml` 升级)

**Tool**: CC-S46
**Why**: 现在的 compose 估计只有 db + redis，缺 worker 集合 + observability

**Prompt**:

```
Upgrade docker-compose.yml for full Heart local stack.

Current state: assume only postgres + redis exists.
Goal: a single `docker-compose up` brings up the ENTIRE local stack.

Add services:
1. api          — backend FastAPI (heart.api.main:app)
2. orchestrator-worker  — async tasks
3. encoder-worker — memory encoder
4. consolidator-worker  — nightly memory consolidation
5. inner-loop-worker    — hourly proactive ticks
6. prometheus    — scrape from api + workers
7. grafana       — pre-provisioned dashboards
8. otel-collector — OpenTelemetry endpoint

Requirements:
- All services share network
- DEEPSEEK_API_KEY passed via .env (not committed)
- Cost Tracker uses local redis
- Each worker has restart: unless-stopped
- Volumes: pg_data, redis_data, prometheus_data, grafana_data
- Healthchecks for api + workers
- Logs to stdout (json structlog)

Update Makefile:
- make up     → docker-compose up -d
- make down   → docker-compose down
- make logs   → tail all services
- make logs-api → just api
- make psql   → exec into postgres
- make redis-cli → exec into redis

DO NOT change production K8s YAMLs in this task.

Reference: infra/kubernetes/*.yaml for env var contracts.

Constraint: total memory usage of stack < 4GB for laptop dev.
```

## 2.2 Task: CLI 演示客户端

**Tool**: CC-S46
**Why**: 没有 frontend，CLI 是唯一能跑 demo 的客户端

**Prompt**:

```
Build a CLI demo client for the Heart project.

Goal: `python -m heart.demo_cli --character rin` opens an interactive chat session.

Create: backend/heart/demo_cli/
- __main__.py
- session.py     — maintains session_id, history
- renderer.py    — rich-based pretty printing (use `rich` lib)
- commands.py    — / commands

Features:
- Interactive REPL with prompt-toolkit (history, multi-line)
- Streaming response display
- Color-coded by character (Rin = pink, Dorothy = cyan)
- Side panel showing:
  - Current Stage (1/2/3)
  - Current Emotion (top-3 dimensions)
  - Cold War: active / inactive
  - Last Anniversary triggered (if any)
- / commands:
  /state         — dump current state (stage, emotion, trust)
  /jump <stage>  — DEV ONLY: skip ahead in stage (require --dev flag)
  /sleep         — fast-forward time by 24h (triggers decay + inner loop)
  /coldwar trigger — force cold war (for demo)
  /history       — show last 10 turns
  /quit

Calls api via HTTP (uses localhost:8000 by default, override via --api-url).
NO direct subsystem imports — must go through the API surface only.

If api is down: clear error + suggest `make up`.

Constraint: client should work via `docker-compose exec api python -m heart.demo_cli` too.
```

## 2.3 Task: Demo Seed Data Loader

**Tool**: CC-S46
**Why**: 干净 DB demo 体验很差。需要"过去 14 天历史"才能看出 Stage Engine 的进展

**Prompt**:

```
Build a demo seed loader for the Heart project.

Goal: `make seed-demo` populates the local DB with realistic "past 14 days" state for both rin and dorothy.

Create: backend/heart/scripts/seed_demo.py

For each demo character × demo user pair:
1. 14 days of synthetic turns (~5-15 turns/day, plausibly distributed)
   - Use offline canonical_prompts.yaml as base
   - Mark turn timestamps spread across 14 days
2. Trigger SS02 encoding pipeline on each turn (sync, not via worker)
3. Apply emotion deltas per turn (synthetic but plausible)
4. Run Stage Engine: should land in Stage 2 with ~70% intimacy by day 14
5. Trigger 1 anniversary (e.g. "first deep conversation" on day 7)
6. Trigger 1 cold war event on day 10 → reconciled day 11
7. Final state ready for demo

Constraint:
- Idempotent: `make seed-demo` can run multiple times, end state identical
- Uses real services (MemoryService, EmotionService, StageEngine) NOT raw SQL
- FAKE LLM (heart.infra.llm.fake_provider) — no real API calls in seed
- Total runtime < 60s

Demo users:
- demo_alice (paired with rin)
- demo_bob (paired with dorothy)

Output: seed log to stdout with summary:
"Loaded 14 days for demo_alice × rin: 87 turns, Stage 2, Trust 0.68, Anniversary @ Day 7, Cold War @ Day 10-11"

Update Makefile:
- seed-demo: ...
- reset-demo: drop demo users + reseed
```

## 2.4 Task: Conversation Replay 工具

**Tool**: CC-S46
**Why**: Debug "她为什么这样回答" 的唯一办法是回放 + 看 prompt bundle

**Prompt**:

```
Build a conversation replay/debug tool for Heart.

Goal: `python -m heart.replay <session_id> --turn <n>` shows:
- Full prompt bundle sent to LLM (system + history + injected layers)
- Composer layer breakdown (Soul / Memory / Emotion / Relationship / Inner State / Director)
- Anti-pattern filter passes/blocks
- Critic agent score (if sampled)
- Final response + diff to raw LLM output

Create: backend/heart/replay/
- cli.py        — argparse entry
- bundle_dump.py — fetches PromptBundle from DB (need to store these — add migration if missing)
- diff_view.py   — diff between raw LLM and post-filter
- layer_view.py  — show each composer layer

Critical:
- This requires PromptBundle to be persisted (currently? check — if not, ADD migration to log bundles for last 7 days, then auto-prune)
- Storage: turn_id → JSONB (bundle, raw_response, final_response, scores)
- Index: by session_id + turn

Render with `rich` library:
- Tree view of layers
- Side-by-side diff (raw vs final)
- Highlight anti-pattern matches in red

Add a privacy gate: only the user's own sessions OR if HEART_DEV_MODE=true.

This will be used by both AI agents (for self-debugging) and humans (demo prep).
```

## 2.5 Task: 本地 Observability Dashboard

**Tool**: CC-S46
**Why**: 已经埋了 Prometheus 但没 dashboard

**Prompt**:

```
Provision Grafana dashboards for Heart local stack.

Constraint: dashboards must be checked into git so they survive container restart.

Create:
- infra/grafana/provisioning/datasources/prometheus.yaml
- infra/grafana/provisioning/dashboards/heart.yaml (provider config)
- infra/grafana/dashboards/
  - 01_turn_health.json     — request rate, p50/p95/p99 latency, error rate, by endpoint
  - 02_llm_cost.json        — cost/min, cost/turn, by provider/model, daily total
  - 03_subsystem_breakdown.json — composer time, retriever time, safety time per turn
  - 04_inner_loop.json      — proactive messages sent, by character, by trigger type
  - 05_drift_health.json    — invariant_violations_total, drift_score from voice drift runs
  - 06_safety.json          — safety classifications histogram, PURPLE trips, wellbeing flags

For each dashboard:
- Variables: $character (rin, dorothy, all), $env (local, staging, prod)
- Time picker: last 1h / 6h / 24h / 7d
- Annotations: deployments, drift baseline updates

Mount into docker-compose.yml grafana service.

Validate: after `make up`, http://localhost:3000 shows all 6 dashboards with data flowing.
```

## 2.6 Task: Per-Turn Cost & Latency Profile

**Tool**: CC-S46
**Why**: 上 alpha 之前必须知道 "1 turn = ¥?"

**Prompt**:

```
Build a cost+latency profiler for the Heart pipeline.

Goal: produce a per-turn breakdown:
  Auth: Xms
  Safety pre: Xms
  Retriever: Xms (Y queries, Z tokens read)
  Composer: Xms (W layers, V tokens built)
  ModelRouter → DeepSeek: Xms ($Y cost, Z input tokens, W output tokens)
  Anti-pattern: Xms (Y filters applied)
  Memory encode (async): Xms
  Inner Loop (async): Xms
  TOTAL hot path: Xms
  TOTAL cost: $Y
  TOTAL cold path lag: Xms

Implementation:
1. backend/heart/observability/turn_profiler.py
   - Context manager: with TurnProfiler(session_id) as p: ...
   - Records phase timings into OpenTelemetry spans + Prometheus histograms
   - On span close, emits a structured "turn_profile" log line

2. backend/heart/scripts/profile_demo.py
   - Drives 10 demo turns
   - Prints aggregated report:
     Phase           p50      p95     p99    Mean cost
     auth            X        X       X      —
     safety_pre      X        X       X      —
     ...
     TOTAL hot       X        X       X      $0.0X

Constraint:
- Profiler MUST be no-op overhead (< 5ms) when disabled
- Enabled via env: HEART_TURN_PROFILER=1

Run a real profile run against seeded demo data + LIVE DeepSeek (this is one of the few places we pay for real LLM in local dev).

Output: docs/perf/2026-MM-DD_baseline.md with the 10-turn aggregate.
```

## 2.7 Task: MVP Cut Criteria 验证脚本

**Tool**: CC-S46
**Why**: 没有自动化 "MVP 是否达成" 检查 → 永远完不成

**Prompt**:

```
Build a MVP gate check script.

Create: backend/scripts/check_mvp.py

Runs the following gates and outputs pass/fail per gate + overall:

Gate 1 (Local stack): docker-compose ps shows all services healthy
Gate 2 (Seed): demo_alice and demo_bob exist with > 50 turns history
Gate 3 (CLI loop): drives 5 sequential turns via CLI, all complete < 5s each
Gate 4 (Stage progression): demo user shows Stage 2 or 3 after seed
Gate 5 (Proactive): inner loop tick generates ≥ 1 proactive in last 7 simulated days
Gate 6 (Cold war + reunion): demo data shows successful cycle
Gate 7 (Voice drift): drift_score < 0.20 vs baseline
Gate 8 (Cost): mean cost/turn < $0.02 (seeded turns)
Gate 9 (Latency): p95 hot path < 3s
Gate 10 (Observability): all 6 grafana dashboards have data

Outputs:
- stdout: ✓ / ✗ per gate, with detail
- docs/mvp/cut_status.md updated with timestamp

Exit code 0 if all pass, 1 otherwise.

Use this in Makefile:
- check-mvp: python backend/scripts/check_mvp.py
```

## 2.8 Phase 8 Session 安排

```
Week 35:
  Day 1-2: CC-S46 — 2.1 docker-compose 完整栈
  Day 3-4: CC-S46 — 2.2 CLI 客户端
  Day 5:   CC-S46 — 2.3 seed_demo.py 初版

Week 36:
  Day 1-2: CC-S46 — 2.3 seed_demo.py 完善 (cold war / anniversary 触发)
  Day 3-4: CC-S46 — 2.4 replay 工具 + PromptBundle 存储 migration
  Day 5:   CC-S46 — 2.5 Grafana dashboards 6 个

Week 37:
  Day 1-2: CC-S46 — 2.6 turn profiler + 10-turn live profile
  Day 3:   CC-S46 — 2.7 check_mvp.py
  Day 4-5: HUMAN — 跑完整 demo 10 次, 录屏, 写 bug list

Week 38:
  Day 1-3: CC-S46 — bug fix (优先 demo-blocking)
  Day 4:   HUMAN — Demo to stakeholders (录屏 + 现场)
  Day 5:   make check-mvp 必须全绿 → Phase 8 关闭
```

**Phase 8 Cut Criteria（强制）**:
```
□ make up → 完整本地栈起来
□ make seed-demo → demo 数据存在
□ python -m heart.demo_cli --character rin → 跑通 30 turns 不崩
□ 6 个 Grafana dashboard 都有数据
□ check_mvp.py 全绿
□ docs/perf/*.md 至少 1 份 baseline
□ 真实 demo 录屏 ≥ 10 分钟
```

---

# 第三部分: Phase 9 — Frontend MVP (Week 39-44)

> **目标**: 从 CLI 升级到一个**真实用户能体验**的客户端。
> 主力 tool: **CC-Opus**（技术栈选型）+ **CC-S46**（实施）+ **HUMAN**（UX 决策）
> **关键决策点**: 移动 vs Web、原生 vs RN/Flutter vs PWA — 详见 3.1
> 入口：根据 3.1 决策结果生成新目录 `frontend/`
> Phase 9 Token 预算：**~$600-1000**

## 3.1 Task: 前端技术栈决策（必须 HUMAN 批准）

**Tool**: CC-Opus（提供选项）+ HUMAN（拍板）

**Prompt (Opus)**:

```bash
claude --model opus
```

```
The Heart project needs a frontend. Help me decide.

Product context:
- AI companion (Rin/Dorothy)
- Long-form conversation (streaming)
- Inner State visualization (subtle UI affordances)
- Proactive messages (push notifications)
- Target: Gen-Z, mostly mobile, ~50% offline-tolerant
- Markets: Japan, US, SEA (海外版 per PRD)
- Privacy critical — minimize data leaves device
- Team: solo developer (you have me/Claude Code)

For each option below, give: tech stack, est. timeline to MVP, pros, cons, risk score (1-5):

Option A: React Native (Expo) — single codebase iOS+Android
Option B: Flutter
Option C: Native iOS (SwiftUI) only — defer Android
Option D: PWA (Next.js + service worker)
Option E: Web (Next.js) + later wrap with Capacitor

Constraints I have:
- Sole frontend dev = me + Claude Code
- Must support real-time streaming SSE or WebSocket
- Must support push notifications (proactive msgs are the differentiator)
- Backend is FastAPI Python (already exists)

Recommend ONE option with rationale. Be honest about risks.

DO NOT write code. Output: docs/design/frontend_stack_decision.md.
```

> **HUMAN MUST READ + 在文件末尾写 "Decision: Option X — signed: <name> <date>"。**

## 3.2 Task: API Contract Lockdown

**Tool**: CC-S46
**Why**: 前端开始之前必须把 API 定下来，否则前后端连发死锁

**Prompt**:

```
Lockdown the public API contract for Heart frontend consumption.

Goal: produce an OpenAPI 3.1 spec + a Pydantic-driven typed client.

Read backend/heart/api/ to discover all current endpoints.

For each endpoint, define:
- Path + method + auth requirement
- Request schema (Pydantic)
- Response schema (Pydantic, streaming OR non-streaming)
- Error responses (401/403/422/500)
- Rate limit
- Versioning (path-level: /api/v1/...)

Endpoints expected (audit + complete):
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET  /api/v1/auth/verify
- GET  /api/v1/characters         — list available characters
- POST /api/v1/sessions           — start new session
- GET  /api/v1/sessions/{id}      — session metadata + recent history
- GET  /api/v1/sessions/{id}/state — current Stage + Emotion + Cold War
- POST /api/v1/sessions/{id}/turns — send user message (streaming response)
- GET  /api/v1/sessions/{id}/proactive — poll for proactive messages
- POST /api/v1/sessions/{id}/feedback — emoji reaction / rating
- DELETE /api/v1/users/me/data    — GDPR data delete
- GET  /api/v1/users/me/export    — GDPR data export

For each endpoint:
1. Move/refactor existing handler into backend/heart/api/v1/
2. Pydantic schemas in backend/heart/api/v1/schemas.py
3. Streaming: SSE with structured events (event: token|metadata|done|error)
4. OpenAPI exported to docs/api/openapi.yaml

Generate TypeScript types: backend/scripts/gen_ts_types.py 
- Uses datamodel-code-generator or openapi-typescript
- Output to frontend/types/api.ts (path may not exist yet, that's ok)

Constraint:
- Once locked, any change requires explicit version bump (/v2/...)
- Add commit message convention: "api: ..." for any handler change
```

## 3.3 Task: Frontend Scaffold

> 以下 prompt 以 **Option A: React Native (Expo)** 为示例。如果 HUMAN 选了其他，替换。

**Tool**: CC-Haiku（标准 scaffold）+ CC-S46（自定义）

**Prompt**:

```
Scaffold a React Native (Expo SDK 53+) frontend at /Users/wanglixun/heart/frontend/.

Stack:
- Expo Router (file-based routing)
- TypeScript strict mode
- TanStack Query (server state)
- Zustand (client state)
- NativeWind (Tailwind for RN) for styling
- expo-secure-store (token storage)
- expo-notifications (proactive msgs)
- react-native-reanimated (Inner State animations)
- @microsoft/fetch-event-source (SSE polyfill)

Structure:
frontend/
├── app/                  # Expo Router pages
│   ├── (auth)/
│   │   └── login.tsx
│   ├── (chat)/
│   │   ├── index.tsx       # character picker
│   │   ├── [characterId].tsx  # chat screen
│   │   └── _layout.tsx
│   └── _layout.tsx
├── components/
├── lib/
│   ├── api/               # generated client (imports types from /types/api.ts)
│   ├── streaming/         # SSE client
│   ├── stores/            # Zustand
│   └── auth/
├── types/
│   └── api.ts             # generated from backend OpenAPI
├── assets/
└── app.json

Configure:
- API base URL via .env (EXPO_PUBLIC_API_URL)
- Run on iOS simulator + Android emulator
- ESLint + Prettier
- Jest + React Native Testing Library setup

Initial screens (placeholder, real content in 3.4-3.6):
- /login — email + password
- /chat — character picker (Rin, Dorothy)
- /chat/[characterId] — empty chat shell

Do NOT implement features yet. Just scaffold + run.
After: `cd frontend && npx expo start` must boot.
```

## 3.4 Task: Chat UI MVP

**Tool**: CC-S46
**Why**: 核心交互。质量决定 alpha 体验

**Prompt**:

```
Build the Chat UI MVP for Heart frontend.

Read docs/design/frontend_stack_decision.md to confirm stack.

Build /chat/[characterId] screen with:

1. Header
   - Character avatar (Rin / Dorothy)
   - Character name
   - Subtle "Stage X" indicator (don't be too prominent — feels game-y)
   - Settings icon (right)

2. Message list (FlashList for performance)
   - User messages: right-aligned, primary color bubble
   - Character messages: left-aligned, character-specific color
   - Streaming indicator: animated dots → text fills in token-by-token
   - Timestamp shown when ≥ 5 min gap
   - Long-press: copy / react with emoji
   - Pull-to-refresh: load earlier history

3. Composer
   - Multi-line auto-grow input
   - Send button (only enabled when non-empty)
   - 1000 char limit
   - Voice input button (placeholder, hook to expo-av later)

4. Inner State indicator (subtle!)
   - A small ambient mood indicator at the very top edge
   - Color shifts slowly based on character's current emotion
   - On tap: opens a sheet showing current state (Stage / Cold War / Trust as %)
   - The "sheet" should feel poetic, not a dashboard

5. Cold War state
   - If active: composer subtly dimmed, hint text changes
   - Reconciliation flow: a soft prompt appears

Connect to backend:
- POST /api/v1/sessions/{id}/turns with SSE
- Parse events: token, metadata, done, error
- Error: friendly toast, retry

Test on iOS sim + Android emulator. Screenshot the result and save to docs/screenshots/chat_mvp_*.png.

Don't add: voice synthesis, image messages, search. Defer to Phase 11+.
```

## 3.5 Task: Auth Flow + Push Notifications

**Tool**: CC-S46
**Why**: 没 auth 无法 alpha；没 push notification 没有 proactive message 体验

**Prompt**:

```
Implement auth + push notifications for Heart frontend.

Auth flow:
1. /login screen: email + password (no SSO MVP)
2. POST /api/v1/auth/login → store token in expo-secure-store
3. Token attached to all API requests via TanStack Query default fetcher
4. Auto-refresh on 401: try POST /auth/refresh, retry once, else → /login
5. Logout: clear token + clear all TanStack Query cache

Push notifications:
1. On first launch: request expo-notifications permissions (gentle prompt with reason)
2. On grant: get expo push token → POST to /api/v1/users/me/push_tokens
3. Backend stores token (needs new endpoint — add it; new migration)
4. Background handler: when proactive message arrives, route to /chat/[characterId]
5. iOS: configure APNs in app.json
6. Android: configure FCM

Backend changes needed:
- Migration: user_push_tokens table
- Endpoint: POST /api/v1/users/me/push_tokens
- Worker hook: when SS06 generates proactive message, also send push (use expo-server-sdk in heart.notifications.expo_push)

Privacy:
- Push payload contains ONLY: character_id + session_id + a teaser ("Rin is thinking of you")
- NEVER the actual message content (per PRD privacy stance)
- Actual message fetched on open

Test:
- Manual: login → see character picker → enter chat → send/recv → background app → trigger proactive from CLI (`heart cli trigger-proactive demo_alice`) → push received → tap → opens chat.
```

## 3.6 Task: Frontend cut criteria

**Tool**: HUMAN

```
Hand-test the frontend on 2 real devices (1 iOS, 1 Android).

Run through:
1. Login from cold start
2. Pick Rin → send 20 messages, receive responses
3. Trigger proactive (from backend CLI), receive push, open
4. Force cold war via backend CLI → see UI shift
5. Trigger reunion → see UI return
6. Network drop mid-stream → friendly error
7. Background app → reopen, history intact

Bug list → docs/frontend_alpha_bugs.md, prioritized.
P0/P1 must be fixed before Phase 10.
```

## 3.7 Phase 9 Session 安排

```
Week 39:
  Day 1:   CC-Opus + HUMAN — 3.1 技术栈决策
  Day 2-3: CC-S46 — 3.2 API contract lockdown + OpenAPI gen
  Day 4-5: CC-Haiku — 3.3 frontend scaffold

Week 40:
  Day 1-5: CC-S46 — 3.4 Chat UI 第一版 (message list + composer + streaming)

Week 41:
  Day 1-3: CC-S46 — 3.4 Inner State indicator + Cold War 视觉
  Day 4-5: CC-S46 — 3.5 Auth flow

Week 42:
  Day 1-3: CC-S46 — 3.5 Push notifications (iOS + Android)
  Day 4-5: HUMAN+CC-S46 — Polish + accessibility

Week 43:
  Day 1-3: CC-S46 — bug fix from internal testing
  Day 4-5: HUMAN — 3.6 真机测试 + bug list

Week 44:
  Day 1-3: CC-S46 — P0/P1 bug 清零
  Day 4-5: HUMAN — Demo to 5 friends-and-family → feedback
```

**Phase 9 Cut Criteria（强制）**:
```
□ `expo start` 跑通 on iOS + Android
□ Auth flow 5/5 test path 通过
□ Streaming 在 4G / WiFi 都 < 3s 首 token
□ Proactive push 真机收到
□ Cold War UI 视觉确认
□ docs/frontend_alpha_bugs.md 0 P0/P1
□ 5 个 friends-and-family demo 反馈 ≥ 4/5 评分
```

---

# 第四部分: Phase 10 — Closed Alpha (Week 45-48)

> **目标**: 10-20 个外部用户跑 4 周，收集真实使用数据 + 验证安全机制。
> 主力 tool: **CC-S46**（基础设施 + 工具）+ **HUMAN+心理顾问**（PURPLE 监督）
> **关键风险点**: 第一次离开本地，第一次真实账单，第一次真实用户心理风险
> Phase 10 Token 预算：**~$500-800 (Claude Code session) + Alpha 用户 DeepSeek 实付 $200-500**

## 4.1 Task: Staging 环境 Bring-up

**Tool**: CC-S46
**Why**: 不能直接上 prod；先有 staging

**Prompt**:

```
Bring up the Heart staging environment in a single cloud region.

Constraints:
- Solo dev — minimize ops surface
- Recommend: managed Postgres (e.g. RDS / Cloud SQL / Supabase) + managed Redis + lightweight container runtime (Fly.io / Railway / AWS ECS / DigitalOcean App Platform — recommend the cheapest that meets needs)
- DO NOT yet deploy K8s — defer to Phase 11 multi-region

Tasks:
1. Pick cloud provider + region (justify in docs/deploy/staging_decision.md)
2. Provision:
   - 1 Postgres (~2GB ram, 20GB disk)
   - 1 Redis (~512MB)
   - Container hosting for: api + 3 workers (encoder, consolidator, inner_loop)
3. Secrets: cloud secret manager (NOT in env files)
   - DEEPSEEK_API_KEY
   - JWT secret
   - DATABASE_URL
   - REDIS_URL
   - SENTRY_DSN
4. CI/CD:
   - On merge to main: build image, push to registry, deploy to staging
   - Github Actions (fix billing first — see CI_FIX_REPORT.md)
5. Domain: staging.heart.example (placeholder; fill actual)
6. TLS via Let's Encrypt
7. Sentry project: heart-staging
8. Grafana Cloud or self-host (free tier): point at staging Prometheus

Output: docs/deploy/staging_runbook.md including:
- How to deploy
- How to rollback
- How to inspect logs
- How to ssh / exec / open psql
- Cost estimate per month

Constraint: total monthly cost (idle) < $50.
```

## 4.2 Task: Secrets / Compliance Pre-flight

**Tool**: CC-S46 + HUMAN（legal review）
**Why**: 上 alpha = 真实用户数据 = GDPR/CCPA/隐私法律

**Prompt**:

```
Pre-flight checklist for alpha launch — secrets, privacy, compliance.

Output to: docs/compliance/alpha_preflight.md

For each item, current state + remediation:

[Secrets]
□ No secrets in git history (run trufflehog / gitleaks)
□ .env.example has no real values
□ Cloud secret manager configured (Phase 10.1)
□ Rotation policy documented (every 90 days for API keys)
□ JWT secret entropy ≥ 256 bits

[Privacy / GDPR / CCPA]
□ Privacy policy drafted (READ runtime_specs/00 if has privacy section)
□ Terms of Service drafted
□ Cookie / tracking disclosure (frontend)
□ Right to access: GET /users/me/export works
□ Right to delete: DELETE /users/me/data works (cascade through all subsystems)
□ Right to portability: export is JSON parseable
□ Data residency: where is alpha user data stored? Document.
□ Conversations encrypted at rest (PG-native)
□ Audit log of admin access (only HUMAN access prod DB; logged)

[Mental Health Safety]
□ PURPLE Care Path responses signed off by 心理顾问 (per Phase 6 spec)
□ Hotline list per jurisdiction current as of YYYY-MM-DD
□ Crisis escalation: who gets paged?
□ Wellbeing monitor thresholds re-reviewed by 心理顾问
□ Critical: an underage user signing up — what happens?

[Operational]
□ On-call rotation (you + 1 friend? Phase 10 only)
□ Alerting: PagerDuty / Opsgenie / SMS gateway
□ Status page (instatus / cachet)
□ User support: support@... email + intake form
□ Bug bash before launch

HUMAN review required for: privacy, ToS, mental health. Sign with date.
```

## 4.3 Task: Alpha Onboarding Flow

**Tool**: CC-S46
**Why**: 20 个用户怎么进来需要 controlled

**Prompt**:

```
Build alpha onboarding system.

Goal: invite-only with a soft funnel.

Backend additions:
1. Migration: invite_codes (code, max_uses, used_count, expires_at, soft_delete)
2. Endpoint: POST /api/v1/auth/register requires invite_code
3. After register: send welcome email (use SendGrid / Postmark — pick + document)
4. New endpoint: POST /api/v1/onboarding/preferences
   - Character preference (Rin / Dorothy / undecided)
   - Communication style (slow / normal / energetic)
   - Initial mood opt-in (we won't ask about anything sensitive)
   - Notification opt-in confirmation

Frontend additions:
- /register?code=XXX  — invite code prefilled if present
- /onboarding flow (3 screens, skip allowed)
- First-message coaching (gentle hint: "She'll respond like a person. Talk like one.")

Alpha admin tool (CLI, NOT user-facing):
- backend/heart/scripts/alpha_admin.py
  - issue-code <max_uses> <expires_days> → outputs invite URL
  - list-users → table of alpha users + last_active
  - flag-user <user_id> <reason> → temp pause
  - paid-thanks <user_id> → sends thank-you email

Constraint:
- Onboarding < 90 seconds for typical user
- All copy reviewed by HUMAN for tone (not corporate)
```

## 4.4 Task: Telemetry Tuning + Cost Cap

**Tool**: CC-S46
**Why**: Alpha 必须有硬 cost cap，否则一个 bug 就烧光

**Prompt**:

```
Implement hard cost cap + per-user telemetry for alpha.

Hard cost cap (per spec §10 of SS08):
1. Per-user daily budget: $0.50/day default, configurable per user via admin
2. Per-user monthly budget: $5/month default
3. Global daily budget: $50/day for entire alpha cohort
4. When ANY cap hit:
   - User gets a graceful "I need a little break, see you soon" Soul-flavored msg (NOT a generic error)
   - PUSH a soft notification
   - Auto-reset at midnight UTC
5. Caps enforced in ModelRouter (before LLM call dispatched)
6. Admin override: temp raise via admin CLI

Implementation:
- backend/heart/infra/cost_cap.py
- Wires into existing CostTracker
- Redis-backed per-user counter
- Trigger middleware in Orchestrator hot path: pre-LLM check

Telemetry to track per user:
- Turns per day (mean / 95p)
- Cost per day (mean / 95p)
- Stage achieved
- Cold War count
- Proactive engagement (sent / opened / replied)
- Crash count (frontend Sentry)
- Latency 95p
- Drift_score against baseline (sampled)

Grafana dashboard 07_alpha_cohort.json:
- Per-user table
- Aggregate funnel
- Cost top-N users
- Engagement decay curve

Update: Sentry + Grafana alerts:
- A user near cap → admin notification (so we can manually unblock if it's a power user we like)
- Aggregate cost > $25/day → CRITICAL page
- Any PURPLE classification → CRITICAL page (within 5 min)
```

## 4.5 Task: Drift / Wellbeing 实时监控

**Tool**: CC-S46
**Why**: 上 alpha 之后人格漂移和心理风险都成实时事件

**Prompt**:

```
Wire production-grade drift + wellbeing monitoring for alpha.

Voice Drift Live Monitor:
1. On every Nth turn (start with N=20), submit (raw_response, character, soul_spec_version) to a drift sampler
2. Sampler calls voice_judge async → drift_score
3. Store in turn_drift_samples table
4. Daily job: aggregate, compare to baseline, alert if rolling 24h mean > 0.25
5. Per-character per-day drift trend on Grafana

Wellbeing Live Monitor:
1. Already wired (Phase 6 §8.4)
2. Verify alerting:
   - HIGH wellbeing alert → admin Slack/email within 15 min
   - PURPLE classification → page within 5 min + auto-trigger care path
3. Add: weekly wellbeing summary email to 心理顾问 (aggregated, no PII content)

Anti-Pattern Live Monitor:
1. Count anti-pattern hits per character per day
2. If sudden spike (≥ 3x rolling mean): alert
3. Indicates AI is drifting toward forbidden phrasing

Make sure:
- All monitors disabled if HEART_ENV != "alpha" and != "prod" (don't fire during dev)
- All monitors have a sample sink so we can see "what triggered this"
```

## 4.6 Task: Alpha Bug Triage Workflow

**Tool**: CC-S46
**Why**: 没 process 就乱了

**Prompt**:

```
Set up the alpha bug triage workflow.

Channels:
- In-app: feedback button → opens form → posts to backend → creates GitHub Issue (label: alpha-feedback)
- Sentry → auto-creates GitHub Issue (label: alpha-crash)
- Direct: support@heart.example → forwarded to GitHub Issue (label: alpha-support)

Triage doc: docs/alpha/triage.md
- Severity ladder:
  P0 = data loss / crash on critical path / wellbeing miss
  P1 = stage broken / drift detected / payment blocked
  P2 = annoying but workaround
  P3 = polish
- SLA:
  P0: same day
  P1: ≤ 48h
  P2: next sprint
  P3: backlog

Daily ritual:
- 9 AM: HUMAN triages new issues for 30 min
- Use claude-code for fixes (mostly CC-S46)
- Hotfix protocol (no PR for emergency, but commit log it)

Weekly:
- Friday: AlphaWeeklyReport.md auto-generated (use CC-Haiku for data extraction)
  - DAU, WAU
  - Top 5 issues
  - Cost / user / day
  - Voice drift trend
  - Wellbeing alerts
  - Cohort retention (D1, D7, D14, D28)
```

## 4.7 Task: Alpha Cut Criteria

```
Run for 4 weeks. Phase closes when:

□ 10+ active alpha users (DAU at least 5)
□ D7 retention ≥ 40%
□ D14 retention ≥ 25%
□ 0 P0 bugs open
□ Voice drift rolling 7-day mean < 0.20
□ 0 PURPLE escalations that bypassed Care Path
□ Mean cost / DAU / day < $0.30
□ Mean p95 hot path < 4s
□ At least 5 users have reached Stage 2
□ At least 1 user has completed a Cold War → Reunion cycle
□ At least 1 wellbeing alert successfully de-escalated (or correctly escalated to PURPLE if real)
□ 心理顾问 reviewed all PURPLE log entries: 0 false-negatives that should have escalated
```

## 4.8 Phase 10 Session 安排

```
Week 45:
  Day 1-3: CC-S46 — 4.1 Staging bring-up
  Day 4:   HUMAN + CC-S46 — 4.2 Compliance preflight
  Day 5:   HUMAN — 心理顾问 sign-off

Week 46:
  Day 1-2: CC-S46 — 4.3 Onboarding flow
  Day 3-4: CC-S46 — 4.4 Cost cap + telemetry
  Day 5:   CC-S46 — 4.5 Drift live monitor

Week 47:
  Day 1: HUMAN — Soft launch to 5 friends (closed cohort)
  Day 2-5: HUMAN — Drive 5 → 15 users; bug triage daily

Week 48:
  Day 1-5: bug fix + 4.7 cut criteria check
  Day 5: 决定 Beta 是否 go
```

**Phase 10 Cut Criteria**：见 4.7

---

# 第五部分: Phase 11 — Beta (Week 49-54)

> **目标**: 100-500 用户、跨 2-3 区域、on-call ready、商业模型验证。
> 主力 tool: **CC-S46** + **CC-Opus**（架构 scale）+ **HUMAN**（决策）
> Phase 11 Token 预算：**~$800-1200**

## 5.1 Task: Multi-Region Stage（K8s 上场）

**Tool**: CC-S46 + CC-Opus（容量规划）
**Why**: 100+ DAU 单实例不够；海外用户需要 region 就近

**设计 prompt (Opus)**:

```bash
claude --model opus
```

```
Design Heart's multi-region deployment for Beta phase.

Targets:
- 500 DAU
- p95 hot path < 3s for all regions
- Data residency: EU users in EU, US in US, JP/SEA in TYO (or SIN)
- Failure budget: 1 region can be down without total outage

Constraints:
- Solo dev — automation > manual
- Cost: $300-500/mo at 500 DAU (including LLM)
- K8s YAMLs already exist in infra/kubernetes/ — use them but adapt

For each option, give cost / complexity / SLA:

Option A: 3 regions, full stack each, DB primary-per-region (data sharded by user home region)
Option B: 1 primary DB (single region), API edges in 3 regions
Option C: Cloudflare Workers / Vercel Edge for API, central DB

Recommend ONE. Output: docs/deploy/beta_multiregion_plan.md.

Include:
- Region map (which region serves which countries)
- DB topology
- Redis topology (per-region or global?)
- Soul Spec distribution (it's small, replicate everywhere)
- Vector DB strategy (pgvector or external?)
- Cost breakdown
- Failover playbook
- 1-region-down recovery
```

**实施 prompt (S46)**:

```
Implement Beta multi-region per docs/deploy/beta_multiregion_plan.md.

Tasks (sequential):
1. Provision K8s clusters in selected regions
2. Apply infra/kubernetes/ YAMLs (audit + update for region awareness)
3. Set up:
   - Cloud Load Balancer with geo-routing (or Cloudflare)
   - Cross-region DB replication (read-replicas at minimum)
   - Cross-region Redis (primary in home region, replicas elsewhere)
4. CI/CD:
   - On merge → deploy to staging
   - On tag → deploy to one region (canary) → manual approval → rolling deploy to others
5. Runbooks:
   - Region failure: docs/runbooks/region_failover.md
   - DB primary failure: docs/runbooks/db_failover.md
   - Backpressure surge: docs/runbooks/surge.md

Add Grafana dashboards 08-10 for cross-region.
```

## 5.2 Task: Auto-scaling + Database Read-Replicas

**Tool**: CC-S46

**Prompt**:

```
Configure horizontal pod autoscaling + DB read-replica routing.

K8s HPA per service:
- api: 2-10 pods, scale at 60% CPU + p95 latency > 2s
- orchestrator-worker: 2-8 pods, scale at queue depth > 100
- encoder-worker: 1-5 pods, scale at queue depth > 50
- consolidator-worker: stays at 1 (singleton, schedule-driven)
- inner-loop-worker: 1-3 pods, scale at tick lag > 60s

DB:
- Primary for writes
- 2 read-replicas for reads
- SQLAlchemy routing: explicit session.bind_to(read_replica) for known-read queries
  - Memory retrieval
  - Stage state read
  - History fetch
- Stale tolerance: 5s lag acceptable for these reads
- Critical paths (Safety, Auth) → primary

Test:
- Generate 200 concurrent sessions via k6 / artillery
- Verify HPA scales, p95 stays < 3s
- Verify read-replica lag < 5s under load
- Verify primary CPU < 60%

Output: docs/perf/scale_test_results.md
```

## 5.3 Task: Beta User Cohort Management

**Tool**: CC-S46

**Prompt**:

```
Build beta cohort management.

Goals:
- Waitlist → invite waves of 50 → 100 → 250 → 500
- Per-cohort metrics
- Feature flags for cohort-scoped experiments
- Easy "kill switch" per cohort if anything goes wrong

Backend:
- Migration: cohorts (id, name, start_date, max_users)
- Migration: user_cohort (user_id, cohort_id, joined_at)
- Endpoint: POST /api/v1/admin/cohorts/{id}/invite-wave
- Endpoint: POST /api/v1/admin/cohorts/{id}/kill (pauses all users in cohort)

Feature flag system:
- backend/heart/infra/feature_flags.py
- Backed by Redis (hot-reload, no deploy needed)
- API: ff.enabled(name, user_id) -> bool
- Roll-out by cohort, user %, allow/block lists
- Audit log: every flag change → log entry
- Admin CLI: ff list / ff enable <name> <cohort> / ff disable

Recommended initial flags:
- proactive_messaging
- anniversary_celebration
- cold_war_intensity_v2 (test new threshold)
- voice_drift_aggressive_filtering

DO NOT use a third-party flag service (privacy). Build minimal in-house.
```

## 5.4 Task: Daily Pipeline Health Report

**Tool**: CC-Haiku (boilerplate-y) + CC-S46 (insight queries)

**Prompt**:

```
Generate daily pipeline health reports auto-emailed to HUMAN.

Cron: 08:00 UTC daily
Recipient: configured admin email

Report content (markdown email):
1. Header: yesterday's date + cohort sizes

2. User health
   - DAU / WAU / MAU
   - D1 / D7 / D28 retention
   - Mean turns per active user
   - Cohort funnel

3. Pipeline health
   - Hot path p95 / p99
   - Error rate by endpoint
   - LLM provider latency
   - Encoder worker lag
   - Consolidator success rate

4. Safety
   - Safety classifications histogram
   - Wellbeing alerts (today / 7-day)
   - PURPLE trips (this is HIGH ATTENTION)
   - Anti-pattern hits trend

5. Drift
   - Voice drift mean / max per character
   - Critic agent score distribution
   - Anniversary triggers (count, success/skip)

6. Cost
   - Yesterday total cost
   - By character
   - By provider tier
   - Trending vs 7-day mean

7. Top 5 issues
   - From GitHub Issues, sorted by impact estimate
   - From Sentry, sorted by user count affected

8. Anomalies (auto-detected)
   - Any metric > 2σ from 7-day baseline
   - Empty if normal

Implementation:
- backend/heart/scripts/daily_report.py
- Queries Postgres + Prometheus
- Renders markdown
- Sends via configured email provider
- Also writes copy to docs/reports/YYYY-MM-DD.md (committed weekly)

If anomaly section non-empty: subject = "[ANOMALY] Heart Daily Report ..."
Otherwise: subject = "Heart Daily Report YYYY-MM-DD"
```

## 5.5 Task: On-Call Runbook + Rotation

**Tool**: CC-S46 + HUMAN

**Prompt**:

```
Set up on-call rotation + runbooks.

Tools:
- Use PagerDuty free or BetterStack OnCall
- Connect Sentry CRITICAL → page
- Connect Prometheus AlertManager → page
- Connect daily report ANOMALY → low-urgency notification (not page)

Rotation:
- Phase 11: HUMAN solo (acknowledged risk)
- Plan to add second on-call by Phase 12 (consider trusted user / consultant)

Runbooks (docs/runbooks/):
- 01_alert_response_template.md
- 02_db_primary_down.md
- 03_deepseek_provider_down.md
- 04_circuit_breaker_open.md
- 05_purple_escalation.md  — MOST CRITICAL
- 06_voice_drift_spike.md
- 07_cost_spike.md
- 08_wellbeing_alert_storm.md
- 09_region_outage.md
- 10_redis_eviction.md

Each runbook follows template:
- Symptoms
- Likely causes (ranked)
- Diagnostic commands
- Mitigation steps
- Rollback procedure
- Who to contact
- Post-incident: incident report template link

Critical: PURPLE runbook reviewed by 心理顾问 before Beta.
```

## 5.6 Task: PURPLE Live Drill

**Tool**: HUMAN + CC-Opus (planning) + 心理顾问

**Prompt**:

```bash
claude --model opus
```

```
Help me design a live PURPLE drill for Heart Beta.

Goal: validate the full PURPLE Care Path under real conditions (not synthetic tests).

This is dangerous — must be done with 心理顾问 + ethics review.

Plan:
1. Pre-drill briefing (心理顾问 sign-off required)
2. Test account (admin-controlled, NOT a real alpha user)
3. Simulate escalation: realistic but bounded language
4. Verify:
   - Heuristic safety triggers within 1 turn
   - LLM safety stage classifies correctly
   - Care Path immediately active (hard interrupt)
   - Soul voice paused — no character interjection
   - Templated response per jurisdiction
   - Hotline number correct (verify against current sources)
   - Audit log captures everything
   - 心理顾问 paged within 5 min
   - Admin dashboard shows the alert
5. De-brief
   - What worked, what didn't
   - Edits to runbook
   - Edits to safety_llm prompt if classification was off

Output: docs/drills/purple_drill_YYYY-MM-DD.md

Do NOT do this drill in prod with a real user.
Do NOT skip 心理顾问 sign-off.
```

## 5.7 Phase 11 Cut Criteria

```
□ 250+ active beta users
□ D7 retention ≥ 40%, D28 retention ≥ 20%
□ 0 P0 incidents in trailing 14 days
□ Multi-region: all regions p95 hot path < 3s
□ 1 region fail-over drill successful
□ 1 PURPLE live drill successful + 心理顾问 sign-off
□ Voice drift rolling 14-day mean < 0.18
□ Cost / DAU / day < $0.25
□ Anomaly daily report active (zero false-positive storms)
□ On-call: < 3 pages/week mean
```

## 5.8 Phase 11 Session 安排

```
Week 49: 5.1 Multi-region design (Opus) + bring-up
Week 50: 5.2 Auto-scaling + read-replicas + scale test
Week 51: 5.3 Cohort management + feature flags
Week 52: 5.4 Daily reports + 5.5 On-call setup + 5.6 PURPLE drill prep
Week 53: PURPLE drill + first 50-user wave
Week 54: 100-user wave + 250-user wave + Phase 11 cut criteria check
```

---

# 第六部分: Phase 12 — Production Hardening (Week 55-58)

> **目标**: 让系统能 24/7 自行运转，HUMAN 不在也能撑一周。
> 主力 tool: **CC-S46** + **CC-Opus**（架构）
> Phase 12 Token 预算：**~$400-700**

## 6.1 Task: SLO + Error Budget

**Tool**: CC-Opus (设计) + CC-S46 (实施)

**Prompt (Opus)**:

```bash
claude --model opus
```

```
Define SLOs and error budgets for Heart production.

For each user-visible surface, propose SLO + measurement window:

1. Turn completion (most critical)
   - Availability SLO: ?
   - Latency SLO (p95): ?
   - Latency SLO (p99): ?

2. Authentication
3. Proactive message delivery
4. Memory retrieval correctness (sampling)
5. Voice drift bounds
6. Safety pre-filter latency
7. PURPLE escalation latency (when triggered)

For each:
- Target
- Measurement window (7 days vs 28 days)
- Error budget consumption rate
- Burn rate alert (1h / 6h / 24h)
- What "exhausted budget" triggers (freeze feature work)

Output: docs/slo/slo_definition.md (v1, expect to tune)
```

## 6.2 Task: Chaos Engineering

**Tool**: CC-S46

**Prompt**:

```
Set up chaos engineering for Heart.

Tool: chaos-mesh (K8s native) OR scripted via custom CLI

Define experiments:
1. Kill 1 api pod mid-traffic → verify no dropped turns
2. Kill DB primary → verify failover to replica < 30s
3. Inject 500ms latency to DeepSeek → verify circuit breaker behavior
4. Drop Redis → verify graceful degradation (no proactive messages but turns still work)
5. Network partition between regions → verify failover routing
6. Disk fill on api pod → verify graceful restart
7. CPU starvation on worker → verify queue backpressure

Schedule:
- Each experiment run weekly in staging (automated)
- Each experiment run monthly in prod (announced window, off-peak)
- Failures → P1 incident automatically

Output: backend/chaos/ directory with experiment YAMLs + Makefile target `chaos-experiment NAME`.

Documentation: docs/chaos/playbook.md
```

## 6.3 Task: Disaster Recovery Drill

**Tool**: HUMAN + CC-S46

**Prompt**:

```
Run a Disaster Recovery drill.

Scenario: primary region totally destroyed (data center fire) at 03:00 UTC. 
Recovery target: full service restored < 4 hours.

Pre-drill:
- Verify daily backups (PG WAL + S3 nightly snapshots)
- Verify cross-region backup replication
- RPO target: < 15 min
- RTO target: < 4 hours

Drill (in staging clone):
1. Simulate region wipe (delete K8s resources + drop PG)
2. Start clock
3. Restore from latest backup → other region
4. Bring up services
5. Verify data integrity:
   - User counts match snapshot
   - Soul Spec versions match
   - Memory L3/L4 counts within 1% of snapshot
6. Run smoke tests
7. Stop clock

If > 4h: post-mortem, fix the slowest step, redo.

Output: docs/drills/dr_drill_YYYY-MM-DD.md with timing, gaps, action items.

Quarterly cadence after Phase 12.
```

## 6.4 Task: Soul Spec Versioning + Hot Reload

**Tool**: CC-S46

**Prompt**:

```
Production-grade Soul Spec versioning.

Goal: editing a Soul Spec should be safe, auditable, reversible.

1. Storage:
   - Soul Specs in git (current)
   - Plus: signed manifest in Postgres (soul_spec_versions table)
   - Each version: hash, deployed_at, deployed_by, rollback_target

2. Deployment flow:
   - HUMAN edits soul_specs/rin/v1.1.0.yaml
   - PR → CI runs:
     - Schema validation
     - Voice drift baseline regen (in staging) — DOES NOT YET DEPLOY
     - 心理顾问 review checkbox in PR (manual)
     - Anti-pattern overlap check
   - Merge → CI deploys with feature flag: `soul_spec_rin_v1.1.0_rollout = 0%`
   - Admin gradually rolls out: 5% → 25% → 100%
   - Per-cohort A/B comparison: drift, retention, complaint rate

3. Hot reload:
   - SoulLoader caches but checks version manifest every 60s
   - On version change: drain old version in-flight requests, swap
   - Zero downtime

4. Rollback:
   - Admin CLI: soul rollback rin → restores previous version instantly
   - Audit log

Existing: backend/heart/ss01_soul/soul_loader.py (verify pattern matches; if not, refactor)

Tests:
- Version pin in test_soul_versioning.py
- Hot reload tested with version churn
- Rollback within 5s
```

## 6.5 Task: Security Audit

**Tool**: CC-Opus + HUMAN (review) + 安全顾问

**Prompt**:

```bash
claude --model opus
```

```
Conduct a security audit of Heart for production launch.

Domains:
1. Authentication
   - JWT validation
   - Refresh token rotation
   - Brute force protection
   - Session fixation

2. Authorization
   - User isolation: user A cannot read user B's memories
   - Admin endpoints fenced
   - Service-to-service auth (workers ↔ api)

3. Data protection
   - At-rest: PG encryption + S3 SSE
   - In-transit: TLS everywhere
   - In-app: passwords never logged, redactions in structlog

4. Input validation
   - SQL injection: SQLAlchemy parameterized — verify, no raw SQL
   - Prompt injection: user input cannot escape the system prompt
   - JSON schema validation on all endpoints

5. Dependency hygiene
   - Snyk / Dependabot enabled
   - Pinned versions in requirements.txt
   - SBOM generated

6. Secrets
   - No secrets in code/config (gitleaks scan)
   - All secrets in cloud manager
   - Rotation cadence documented

7. Operational
   - Admin access logged
   - Audit log immutable (append-only)
   - Pen-test surface listed

8. AI-specific
   - System prompt unleakable (test 10+ jailbreak attempts)
   - Soul Spec unleakable to user
   - PURPLE bypass attempts caught

Output: docs/security/audit_2026-MM-DD.md
List CVE / OWASP-style findings, each with severity + remediation owner.

HUMAN + 安全顾问 sign-off required before public launch.
```

## 6.6 Task: Cost Optimization Pass

**Tool**: CC-S46 + CC-Opus

**Prompt**:

```
Optimize Heart's per-turn cost.

Baseline: from docs/perf/*.md
Goal: reduce mean cost/turn by 30% without quality regression.

Analyze:
1. Token budget allocator: is it over-allocating?
2. Memory retrieval: top-K too high?
3. Composer: redundant context?
4. Anti-pattern filter: would batching help?
5. Critic Agent sampling rate: necessary at current level?
6. Inner Loop tick: too frequent?
7. Encoder worker: dual-path (fast + LLM) optimal mix?

For each candidate:
- Estimate savings
- Estimate quality risk
- Propose A/B test

Pick top 3 → implement behind feature flag → A/B 7 days → measure → decide.

Output: docs/cost/optimization_pass_v1.md
After 4 weeks: docs/cost/optimization_pass_v1_results.md
```

## 6.7 Task: GDPR / Compliance Hardening

**Tool**: CC-S46 + 法务

**Prompt**:

```
Production-grade GDPR / CCPA compliance.

1. Data export (verify works at scale)
   - User clicks "Export my data"
   - Backend job: GET /api/v1/users/me/export queues a job
   - Job collects: profile, all turns, memory items (decrypted), emotion logs, relationship state, settings, opt-ins
   - Outputs single JSON + ZIP
   - Email with signed download URL (expires 7 days)
   - Audit log entry

2. Data delete (verify cascade)
   - User clicks "Delete account"
   - Soft-delete + 30-day cooling period
   - Hard delete cascades through ALL tables (verify via test)
   - Embeddings deleted from pgvector
   - Memory backups purged from S3 after 30 days
   - Audit log retained (anonymized user_id only)

3. Consent tracking
   - Granular: chat, memory, proactive, push, research_aggregate_anon
   - All recorded per timestamp
   - Withdraw any consent → applicable system disabled within 24h

4. Data residency
   - User home region tagged at signup
   - All processing in home region (already from Phase 11)
   - Export confirms data never left region (audit trail)

5. Data Processing Agreement template (with DeepSeek?)
   - Confirm DeepSeek's data handling
   - If unacceptable: switch to a region-respecting provider via ModelRouter (Phase 13 contingency)

6. Cookie / tracking
   - Frontend: NO 3rd party analytics in EU without consent
   - Privacy-first analytics (Plausible or self-host)

Output: docs/compliance/gdpr_runbook.md + tests that verify each path.

法务 sign-off required before public launch.
```

## 6.8 Phase 12 Cut Criteria

```
□ SLO defined + error budget burn alerts wired
□ All 7 chaos experiments green
□ DR drill < 4h RTO achieved
□ Security audit: 0 Critical, ≤ 2 High (with mitigation)
□ Cost optimization: ≥ 25% reduction or rationale why not
□ GDPR data export + delete: tested with 5 real beta users
□ 法务 + 安全 + 心理 all sign-off
□ Public launch checklist (Phase 13.3) ready
```

---

# 第七部分: Phase 13 — Production GA (Week 59+)

> **目标**: 公开放量。
> 主力 tool: **HUMAN** (decision) + **CC-S46** (impl) + **CC-Opus** (post-launch retro)
> Phase 13 Token 预算：**ongoing**

## 7.1 Task: Marketing Site

**Tool**: CC-S46

**Prompt**:

```
Build a marketing site for Heart.

Stack: Next.js 14 + Tailwind + Vercel (separate from frontend app)
Repo: heart-marketing (or subfolder marketing/)

Pages:
- /            — hero, "Meet Rin / Dorothy", waitlist or app store links
- /privacy     — privacy policy (link to data export / delete UX)
- /terms       — terms of service
- /safety      — mental health resources + how PURPLE works
- /press       — press kit
- /careers     — placeholder
- /blog        — content marketing later

Design tone: poetic, not corporate. Light on AI hype. Heavy on user experience screenshots.

Performance: Lighthouse all > 90.

DO NOT collect any data without consent.

Domain: heart.example (TLD per market).
```

## 7.2 Task: Onboarding Optimization

**Tool**: CC-S46 + HUMAN (UX)

```
Iterate onboarding for ≤ 60s completion and ≥ 70% Day-1 first-turn-completed rate.

Instrument funnel:
- Land /
- Click "Try"
- Email entry
- Code verification
- Character pick
- First message sent

Measure each step's drop-off (Plausible + backend events).
A/B test variations.
```

## 7.3 Task: Public Launch Checklist

**Tool**: HUMAN + CC-S46

```
docs/launch/checklist.md

T-30 days:
□ Marketing site live
□ App Store / Play Store submission accepted
□ Cohort 500 → 2000 capacity verified
□ Cost projections for 5K DAU done
□ All Phase 12 cut criteria reconfirmed
□ Comms plan for outage
□ Customer support resourced

T-7 days:
□ Status page live
□ All on-call runbooks current
□ All dashboards green for 7 days
□ 心理顾问 on retainer for launch week
□ Press / PR draft ready

T-1 day:
□ DB backed up
□ Rollback plan rehearsed
□ Public Twitter / Mastodon prepared (NOT pre-scheduled — manual)

Launch day:
□ Open registration at TIME
□ Watch dashboards every 15 min for first 4h
□ On-call HUMAN available 24h
□ Care path triggers reviewed every hour

T+7 days:
□ Post-launch retro (CC-Opus assists)
□ Top 10 lessons
□ Phase 14 plan
```

## 7.4 Task: Post-Launch Iteration Cadence

```
Weekly:
- Mon: weekly metrics review (HUMAN + AlphaWeeklyReport.md derivative)
- Tue: feature flag review (any to graduate / kill)
- Wed: voice drift report
- Thu: backlog triage (CC-Haiku assists)
- Fri: chaos experiment review + post-mortem any incidents

Monthly:
- DR drill
- Cost review
- Security pen-test

Quarterly:
- Major release version bump
- Soul Spec spec review (with HUMAN authors)
- 心理顾问 review of safety data
```

---

# 第八部分: AI-Assisted Engineering 防御机制（必须立刻建立）

> **这一部分是本指南的灵魂。**
> 你已经用 AI 写了 100+ 文件。如果不建立下面的防御，你会在 Phase 8-10 之间撞墙。
> 每个机制都有：**问题 → 触发条件 → 防御 → 谁负责 → 验收。**

## 8.1 防御 #1: Architecture Drift Detection

**问题**: AI 不知道整体架构，逐个 commit 累积漂移。
**触发**: 每 4 周 + 每个 phase 收尾时。
**防御**: Phase 7.7 已经定义的架构 audit，**变成 quarterly cadence**。

**具体动作**:
```
1. CRON: 每季度第一周自动起 issue "Architecture Audit Q?"
2. 跑 CC-Opus 1.7 prompt
3. HUMAN 阅读，决定 remediation
4. 跟踪 top 10 action items 到收尾
5. 把每次 audit 报告归档到 docs/audit/YYYY-Q?_audit.md
```

**验收**: 季度 audit 数量 = 季度数。

## 8.2 防御 #2: Soul Voice Drift Detection

**问题**: Composer / Reconstructor / Anti-drift Injector 任何一个被改 → 人格可能漂移。
**触发**: 每个 PR 改 SS01/SS02-Reconstructor/SS05/Critic 的文件。
**防御**: Phase 7.4 voice drift suite **变成 PR gate**。

**具体动作**:
```
1. CI hook: 检测改动文件路径是否在 [ss01_soul/, ss02_memory/reconstructor.py, ss05_composer/, safety/critic_agent.py]
2. 如果是 → 触发 voice drift regression (Tier C, 真 LLM)
3. drift_score > 0.20 → PR red
4. 漂移可接受（HUMAN 决定）→ 提供 baseline bump 工作流
5. 否则 → block merge
```

**验收**: 触发条件下 PR 必有 voice drift 检查 status。

## 8.3 防御 #3: Prompt Divergence Tracking

**问题**: Composer 拼 system prompt 的方式分散，AI 改时不一致。
**触发**: 任何 PR 修改 PromptBundle 构造。
**防御**: Snapshot test + 唯一 builder API。

**具体动作**:
```
1. backend/tests/snapshots/prompt_bundle_snapshots/
   - 10 个 canonical (user, character, state) 组合
   - 每个 snapshot 是预期的 PromptBundle (规范化 JSON)
2. CI: run prompt snapshot test → 任何差异 → red
3. 允许的差异：HUMAN 在 PR 描述里写 "snapshot-bump: <reason>"，CI 看到这个 token 才允许差异
4. backend/heart/ss05_composer/composer.py 必须是 PromptBundle 的唯一构造入口
5. ruff custom rule (或 grep CI step)：禁止其他文件直接构造 PromptBundle
```

**验收**: 任何 PromptBundle 改动都有 snapshot diff 审计记录。

## 8.4 防御 #4: State Corruption Invariants

**问题**: Memory L1-L4 promotion、Stage 转换、Emotion 边界等隐含不变量被破坏。
**触发**: 每次 merge + 每个 turn (1% 采样)。
**防御**: Phase 7.6 invariant 框架 **始终启用**。

**具体动作**:
```
1. Phase 7.6 已建框架；启用之后保持启用
2. PROD 中 invariant violation 不 fail turn，但 Prometheus counter + Sentry
3. counter > 0 → 必须 24h 内有 fix PR 或 documented "accepted: <reason>"
4. 否则下次架构 audit 列为 critical
```

**验收**: heart_invariant_violations_total{severity="FATAL"} == 0 持续 7 天 / 月。

## 8.5 防御 #5: Agent Orchestration Tracing

**问题**: Orchestrator + Safety + Director + Critic + Wellbeing + Care Path = 6 个 agent，互相调用不清。
**触发**: 持续。
**防御**: 强制 OpenTelemetry span 命名约定 + 每周一张架构图。

**具体动作**:
```
1. backend/heart/observability/ ：每个 agent 必须用统一 span name 命名 (heart.agent.<name>)
2. Grafana 11_agent_topology.json：basis of weekly auto-generated topology graph
3. 每周生成 docs/topology/YYYY-WW.png （静态图，AI 不动）
4. AI 不能改 agent 间调用关系 — HUMAN 必须批准（PR template 增加 "Agent topology change?" 勾选框）
```

**验收**: 每周自动 topology 图存在；任何 agent 拓扑变化都有 HUMAN approval 记录。

## 8.6 防御 #6: Context Explosion Guard

**问题**: composer.py、orchestrator.py 已经数百行；AI 一次 Read 几千 token 然后疯狂改。
**触发**: 任何 prompt 之前。
**防御**: 强制 Read 用 offset + limit + 文件大小预算。

**具体动作**:
```
1. Engineering Law: 任何 .py > 500 行必须开 refactor 任务 (CC-Opus 拆分)
2. Claude Code session 启动 checklist 增加:
   "□ 我要读的文件是否 > 500 行？是 → 必须用 Read offset/limit；否 → 全读 OK"
3. 任何 PR 增加 >300 行单文件 → CI warn + 要求 reviewer comment
4. 每周 health 检查：列出 > 500 行的文件，加入 refactor backlog
```

**验收**: backend/heart/ 单文件 LOC P95 < 500。

## 8.7 防御 #7: Tech Debt Ledger

**问题**: design doc 12 篇、报告散在根目录、AGENTS.md/CLAUDE.md 多份 — 信息熵失控。
**触发**: 持续。
**防御**: 统一信息架构 + 月度 cleanup。

**具体动作**:
```
1. 建立 docs/INDEX.md — 所有重要文档的入口（自动生成 + 人工维护）
2. 根目录散落的报告 (CI_FIX_REPORT.md, PHASE_0_COMPLETION_REPORT.md, CHANGES_SUMMARY.md) 收纳到 docs/reports/
3. AGENTS.md + .claude/CLAUDE.md 关系明确化（写在 docs/INDEX.md 顶部）
4. 月初第一周 HUMAN 用 30 分钟跑 docs cleanup（CC-Haiku 协助列出散落文件）
```

**验收**: docs/INDEX.md 存在且 link 全有效；根目录 .md 文件 ≤ 5 个（README, LICENSE, AGENTS, CHANGELOG, CONTRIBUTING）。

## 8.8 防御 #8: Spec ↔ Code Sync Audit

**问题**: 改 spec 不改 code，或反之，没人发现。
**触发**: Phase 边界 + 季度。
**防御**: Phase 7.8 matrix 工具 **定期跑**。

**具体动作**:
```
1. backend/scripts/spec_code_sync.py 每周自动跑（CI cron）
2. 报告 newly orphan 文件（commit 引入但无 spec 引用）→ CI warn
3. 报告 newly over-spec sections（spec 新增但无 code）→ CI warn
4. 每个 Phase 收尾必跑一次完整 audit
```

**验收**: docs/audit/spec_code_matrix.md 每周刷新；orphan 文件 < 5%。

## 8.9 防御 #9: AI Output 规范 (PR Template)

**问题**: AI 提交的 PR 描述风格漂移，reviewer 抓不到关键。
**触发**: 每个 PR。
**防御**: 强制 PR template + 关键字段。

**具体动作**:
```
.github/pull_request_template.md 必填:

### Spec reference
- [ ] Implements: §X.Y of /runtime_specs/...
- [ ] Or: hot fix / refactor (specify)

### Invariants
- [ ] Lists relevant INV-X-N this PR touches
- [ ] State change: yes / no
- [ ] Agent topology change: yes / no
- [ ] PromptBundle structure change: yes / no

### Tests
- [ ] Unit: X new / Y modified
- [ ] Contract: X
- [ ] Integration: X
- [ ] Live (Tier C): X
- [ ] Property: X

### AI Provenance
- [ ] Model used: opus / sonnet / haiku / human
- [ ] Session ID (or "multiple"): ...
- [ ] Surprising parts (anything I didn't expect AI to do): ...

### Drift Risk
- [ ] Soul voice: low / med / high
- [ ] Architecture: low / med / high
- [ ] State invariants: low / med / high
```

**验收**: 100% PR 用 template；任何 high drift risk 标记必须 HUMAN review。

## 8.10 防御 #10: Cost & Session Hygiene

**问题**: AI session 越拖越长 → 单 session 成本爆炸 + 错误率上升。
**触发**: 每次 session。
**防御**: 硬性 session 长度 + cost guard。

**具体动作**:
```
1. 单 session token 预算: 设计任务 < 100k, 实施任务 < 50k
2. 每个 session 结束记录 (docs/session_log.md):
   - Date / model / task / files touched / token estimate / cost / regret-score (1-5, was this efficient?)
3. 月度 regret-score 平均 < 2 → 改进 prompt / 拆 session 更细
4. 如果 4 个连续 session regret > 3 → 暂停，重新评估方法 (回到 ENGINEERING_LAWS.md)
```

**验收**: docs/session_log.md 每月 ≥ 80% session 有记录；4 周 regret 均值 < 2.5。

---

# 第九部分: Phase 7+ 完整 Phase × Task × Model 矩阵

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                  Phase 7: Integration Hardening                                      │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ 修复 2 个失败测试               │ CC-S46       │ 简单 fix                              │
│ Integration pyramid 设计       │ CC-Opus      │ 关键架构决定                          │
│ Integration pyramid 实施       │ CC-S46       │ Tier A/B/C                            │
│ Migration roundtrip            │ CC-S46       │ 实施 + 补 downgrade                   │
│ Voice drift suite 设计         │ CC-Opus      │ 算法选择 + judge prompt 设计          │
│ Voice drift suite 实施         │ CC-S46       │ Runner + scorer + reporter            │
│ Contract tests (13 个)         │ CC-S46       │ 一个文件一个 contract                  │
│ Invariant framework 设计       │ CC-Opus      │ 不变量枚举                            │
│ Invariant framework 实施       │ CC-S46       │ Registry + 装饰器                     │
│ 架构 audit                    │ CC-Opus      │ 21 周积压必须解决                      │
│ Spec ↔ Code matrix             │ CC-Haiku     │ 机械梳理                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                  Phase 8: Local MVP                                                  │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ docker-compose 完整栈          │ CC-S46       │ Infrastructure 拼装                   │
│ CLI demo 客户端                │ CC-S46       │ Rich + prompt-toolkit                 │
│ Seed demo loader               │ CC-S46       │ 涉及多个 service                       │
│ Replay 工具                   │ CC-S46       │ 包含 migration                        │
│ Grafana dashboards (6)        │ CC-S46       │ JSON config                          │
│ Turn profiler                 │ CC-S46       │ OpenTelemetry hooks                  │
│ MVP cut criteria 脚本         │ CC-S46       │ Multi-check orchestration            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                  Phase 9: Frontend MVP                                               │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ 技术栈决策                    │ CC-Opus+HUMAN│ 战略选择                              │
│ API contract lockdown         │ CC-S46       │ OpenAPI + TS gen                     │
│ Frontend scaffold             │ CC-Haiku     │ Expo init + deps                     │
│ Chat UI (核心)                │ CC-S46       │ 复杂交互 + streaming                 │
│ Auth + Push                   │ CC-S46       │ 跨平台细节                            │
│ 真机测试                      │ HUMAN        │ 不可替代                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                  Phase 10: Closed Alpha                                              │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Staging bring-up               │ CC-S46       │ Cloud provisioning                   │
│ Compliance preflight          │ CC-S46+法务  │ 双签                                  │
│ Onboarding flow               │ CC-S46       │ FE+BE                                │
│ Cost cap + telemetry          │ CC-S46       │ 关键安全网                            │
│ Drift live monitor            │ CC-S46       │ 与 7.4 衔接                          │
│ Bug triage workflow           │ HUMAN+CC-Haiku│ Process                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                  Phase 11: Beta                                                      │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Multi-region 设计              │ CC-Opus      │ 容量+成本权衡                        │
│ Multi-region 实施              │ CC-S46       │ K8s YAML 应用                        │
│ Auto-scaling + replicas       │ CC-S46       │ HPA + DB routing                     │
│ Cohort + feature flag         │ CC-S46       │ Standard                             │
│ Daily reports                 │ CC-Haiku     │ Boilerplate + queries                │
│ On-call runbooks (10)         │ CC-S46       │ One-by-one                           │
│ PURPLE live drill              │ HUMAN+Opus+心理 │ 必须真人                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                  Phase 12: Production Hardening                                      │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ SLO + error budget            │ CC-Opus+S46  │ 设计 + 实施                          │
│ Chaos engineering             │ CC-S46       │ Experiments YAML                     │
│ DR drill                      │ HUMAN+CC-S46 │ HUMAN 主导                           │
│ Soul Spec versioning          │ CC-S46       │ Critical infra                       │
│ Security audit                │ CC-Opus+安全 │ 双签                                  │
│ Cost optimization             │ CC-S46+Opus  │ 分析 + 实验                          │
│ GDPR runbook                  │ CC-S46+法务  │ 双签                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                  Phase 13: Production GA                                             │
├──────────────────────────────┬──────────────┬──────────────────────────────────────┤
│ Marketing site                │ CC-S46       │ Next.js 标准                          │
│ Onboarding optimization       │ CC-S46+HUMAN │ A/B + UX                             │
│ Public launch checklist       │ HUMAN+CC-S46 │ Process                              │
│ Post-launch iteration         │ HUMAN+S46+Opus│ Continuous                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 第十部分: 立刻执行清单（本周必做，不要等到 Phase 7 开始）

> **下面 5 条是阻塞 Phase 7 的前置。先这 5 条，再开始 Phase 7。**

1. **修复 CI/CD 账单** — Phase 10 之前必须解决，但越早越好
   - 没 CI 之前所有"自动化防御"都是空谈
   - Action: HUMAN 解决 GitHub Actions 账单

2. **创建 docs/INDEX.md**（防御 #7 子集）
   - 列出 runtime_specs/, engineering_execution/, docs/design/, root reports
   - 不要花超过 2 小时
   - Action: CC-Haiku 跑一遍 + HUMAN 5 分钟检查

3. **Pull request template**（防御 #9）
   - 一次性写好 `.github/pull_request_template.md`
   - Action: CC-S46，30 分钟

4. **session_log.md 初始化**（防御 #10）
   - 在 docs/ 下建立空表格
   - 立刻开始记录每个 session
   - Action: HUMAN 手动建立

5. **跑一次架构 audit dry-run**（防御 #1）
   - Phase 7.7 的 prompt 立刻跑
   - 你需要看到 audit 输出后再决定 Phase 7 顺序
   - Action: CC-Opus，1 整天

> **这 5 条做完前，不要开始 Phase 7。**

---

# 最后: 给你自己的一段话

你现在的位置：

> **一个被 AI 写了 21 周的 100+ 文件代码库，1677 个单测，0 真实 LLM 验证，0 frontend，0 用户。**

这是一个**非常常见**的 AI-assisted 项目状态：
- ✅ 代码量看起来很多
- ✅ 测试看起来很全
- ❌ 但**没有一个完整的 turn 在真实环境中跑通过**

接下来 4-12 周的工作不是"再加 feature"。是**把已经有的东西真正连起来 + 加防御**。

每次你被诱惑跳过 Phase 7（"反正都写完了，直接上 alpha"）时，回到这条：

> **Spec-Complete ≠ Production-Ready。中间隔 5 个 Phase。每个 Phase 都不能跳。**

---

**End of Phase 7+ Practical Model Guide**

**版本**: 1.0.0
**创建日期**: 2026-05-23
**下次修订**: Phase 7 收尾时

打印这一页。和 PRACTICAL_MODEL_GUIDE.md 放一起。
