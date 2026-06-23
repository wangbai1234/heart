# SS02 Memory — LLM Extractor 重构执行手册

**STATUS: PROMPT COMPLETE @ 2026-06-21 — v1.0.3 47/49 (95.9%)**
**DELIVERY: NOT COMPLETE — pending untracked SS02 files add + branch split. See V1_0_3_FINAL.md §Final Outcome.**

> **本文件覆盖**：把 SS02 Memory 当前基于正则的事实提取链路，替换为「Fast Path 只写 L1 + Slow Path LLM 提取 + 独立 L3→L4 晋升」的双路径架构。
> **配套**：`docs/design/state_invariants.md`（INV-M-* 不变量）+ `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md`（执行风格参照）
> **使用方式**：按 Phase 顺序执行 → 复制 prompt → 选模型 → 执行 → 验收。
> **执行模型分配**：Opus 负责架构 / Schema / Prompt 设计 / 不变量定义；GLM 负责实施 / 迁移 / 测试 / 机械重构。
> **总 Token 预算**：Opus ~$80–120，GLM ~$60–100。

---

# 序章: 当前状态与重构目标

## 0.1 当前实现的根本问题

正则方式本质是「用确定性工具处理不确定性问题」，已暴露 7 类系统性缺陷：

| # | 缺陷 | 影响 |
|---|------|------|
| 1 | 覆盖率：用户表达千变万化，正则无法穷举 | 假阴性高，永远在补 pattern |
| 2 | 上下文依赖：代词、跨消息引用无法解析 | 「她也在杭州」无法关联实体 |
| 3 | 歧义：无法区分真实披露 / 修辞 / 提问 / 否定 | 「我养你」误入库为宠物 |
| 4 | 维护成本：补 pattern 互相干扰，测试爆炸 | 改一处坏一处 |
| 5 | 假阳性：模糊匹配带来错误事实 | 污染长期记忆 |
| 6 | 信息碎片化：跨多 turn 提供的完整事实无法拼装 | 「妙妙」的颜色 / 年龄 / 名字分散 |
| 7 | **违反 Spec**：当前从 fast path 直接生成 L4 候选，跳过 INV-M-11（fast path 只更新 L1）+ INV-M-15（L3→L4 经多重条件晋升） | 架构债务 |

## 0.2 重构目标

- **架构**：fast path 不再做语义提取；slow path 用 LLM + structured output 做提取；L4 由独立 Promoter 按 INV-M-15 晋升。
- **质量**：在 Golden Set 上 precision ≥ 现有 regex + recall 显著高于 regex；歧义场景假阳性归零。
- **可观测性**：每一条 L2/L3/L4 写入都有 source_turns + audit log + confidence。
- **零回归**：fast path 延迟保持 < 50ms（不引入 LLM 调用）；现有单元 / 集成测试 0 红。

## 0.3 现状文件清单（已核对，2026-06-19）

| 路径 | 当前职责 | 重构后 |
|------|---------|--------|
| `backend/heart/ss02_memory/encoder/fast.py` | 正则 + identity patterns + lexicon | 退化为「只写 L1 + 产 hints」；正则迁移到 `hints/regex_hints.py` |
| `backend/heart/ss02_memory/service.py:encode_fast()` | 调 FastEncoder | 保持签名；内部只写 L1 + enqueue slow path |
| `backend/heart/ss07_orchestration/orchestrator.py:981` | `sacred_reason="fast_encoder_identity_detection"` | 改为 hint-only，不再触发 L4 直写 |
| `backend/heart/scripts/seed_demo.py` | demo 用 FastEncoder | 不变；新增 fake LLM extractor 保证 idempotent |
| `config/encoder_lexicon.yaml` | identity patterns 配置 | 保留，作为 hints provider 的输入 |

> ⚠️ **执行前先 `git ls-tree -r HEAD -- backend/heart/ss02_memory/` 确认现状**——这是 CLAUDE.md 「平行实现禁令」的硬约束。

---

# 第一部分: 整体架构方案

```
用户消息 (Turn)
   │
   ├── Fast Path（同步，<50ms）
   │      └─ MemoryService.encode_fast(turn)
   │          ├─ 写 L1 Working Memory（原文 + ts + turn_id + session_id）
   │          ├─ regex_hints.scan(turn) → 候选 hints（仅作为下一步的辅助信号）
   │          ├─ extraction_queue.enqueue(turn_id, session_id, hints)
   │          └─ 返回 FastSignals（保留现有 contract）
   │
   └── Slow Path（异步 worker，触发条件见 §3）
          ├─ Extractor    : LLM(Haiku 4.5) + structured output → ExtractionCandidate[]
          ├─ Resolver     : 对照 L2/L3 现状 → ResolverDecision[] (create/update/supersede/reject)
          ├─ Writer       : 落 L2 (episodic) / L3 (semantic) + audit_log
          └─ Promoter     : 独立调度，按 INV-M-15 条件 L3 → L4
```

**关键不变量（INV）**

- `INV-M-11`: fast path 只写 L1 — 任何对 L2/L3/L4 的写入必须经过 slow path
- `INV-M-15`: L4 候选必须满足 ≥3 次独立 mention + confidence_ewma ≥ 0.8 + age_days ≥ 1 + 无 contradiction
- `INV-M-NEW-A`: 每条 L2/L3 入库记录必须带 `source_turns: list[int]` 与 `extractor_run_id`
- `INV-M-NEW-B`: 同一 (entity, attribute) 在 L3 中至多 1 条 active 记录（其余 superseded）
- `INV-M-NEW-C`: 用户否认（kind=negation）必须软删除而非物理删除，保留审计

---

# 第二部分: Phase A — 基础设施（Schema + Worker 骨架 + Feature Flag）

> **目标**：把双路径的骨架立起来，但行为完全等价于现状（旧 regex 还在跑）。
> **总耗时**：1.5–2 天。

## 2.1 Task: 数据库 Migration

**Tool**: **GLM**
**Why**: 纯机械工作，schema 定义清晰。

**Prompt**:

```
Add Alembic migration for SS02 Memory LLM extractor refactor.

Create: backend/migrations/versions/004_memory_extractor_audit.py

Tables to add:
1. memory_extraction_queue
   - id (UUID, pk)
   - session_id (UUID, indexed)
   - turn_id (BIGINT, indexed)
   - hints_json (JSONB, nullable)  -- regex hints 作为辅助信号
   - status (VARCHAR: pending/processing/done/failed/skipped)
   - enqueued_at, started_at, finished_at (TIMESTAMPTZ)
   - extractor_run_id (UUID, nullable)
   - error_message (TEXT, nullable)
   - retry_count (INTEGER, default 0)
   - Index: (status, enqueued_at)  -- worker poll

2. memory_audit_log
   - id (UUID, pk)
   - user_id (UUID, indexed)
   - session_id (UUID, indexed)
   - tier (VARCHAR: L1/L2/L3/L4)
   - operation (VARCHAR: create/update/supersede/soft_delete/promote/demote)
   - entity_type (VARCHAR)
   - entity_ref (VARCHAR, nullable)
   - attribute (VARCHAR, nullable)
   - old_value (JSONB, nullable)
   - new_value (JSONB, nullable)
   - source_turns (INTEGER[], not null)
   - extractor_run_id (UUID, nullable)
   - actor (VARCHAR: extractor/resolver/promoter/admin)
   - reasoning (TEXT, nullable)  -- LLM 给出的理由
   - created_at (TIMESTAMPTZ)
   - Index: (user_id, created_at DESC)

3. memory_l3_facts (如已存在则 alter)
   - 新增列:
     - source_turns (INTEGER[], not null, default '{}')
     - mention_count (INTEGER, not null, default 1)
     - confidence_ewma (FLOAT, not null, default 0.5)
     - last_extractor_run_id (UUID, nullable)
     - is_active (BOOLEAN, not null, default TRUE)  -- supersede 用
     - superseded_by_id (UUID, nullable, fk self)
   - 如不存在则按上述列 + (id, user_id, entity_type, entity_ref, attribute, value, created_at, updated_at) 创建

Constraints:
- Both up() and down() implemented (per CLAUDE.md migration roundtrip 要求)
- downgrade() 必须能完整回滚 (drop tables / drop columns)
- 使用 SQLAlchemy + Alembic, 不写 raw SQL

After:
- alembic upgrade head 跑通
- alembic downgrade -1 跑通
- alembic upgrade head 再跑通

Commit: "feat(ss02): add migration for LLM extractor queue + audit log + L3 supersede"
```

**验收**:
```
□ alembic upgrade head → 3 张表存在
□ alembic downgrade -1 → 3 张表 / 列被干净回收
□ alembic upgrade head 再次成功（roundtrip）
□ backend/tests/integration/test_migration_roundtrip.py 增加 004 case
```

## 2.2 Task: Feature Flag 体系

**Tool**: **GLM**
**Why**: 灰度切换必备，无判断难度。

**Prompt**:

```
Add a memory extractor mode feature flag.

File: backend/heart/core/config.py (extend) 
- Add Pydantic setting:
  MEMORY_EXTRACTOR_MODE: Literal["regex", "llm", "dual"] = "regex"
  MEMORY_EXTRACTOR_LLM_MODEL: str = "claude-haiku-4-5-20251001"
  MEMORY_EXTRACTOR_BATCH_TURNS: int = 6     # N turns to batch
  MEMORY_EXTRACTOR_IDLE_SECS: int = 30      # session idle trigger
  MEMORY_EXTRACTOR_COST_CAP_USD: float = 0.05  # per extraction run
  MEMORY_PROMOTER_INTERVAL_SECS: int = 300
  MEMORY_PROMOTER_MIN_MENTIONS: int = 3
  MEMORY_PROMOTER_MIN_CONFIDENCE: float = 0.8
  MEMORY_PROMOTER_MIN_AGE_DAYS: int = 1

Behavior:
- regex: 当前行为（保留）
- llm: 关闭 regex extraction → 不再产生 L4 候选；仅 slow path LLM 路径运行
- dual: 两者都跑，仅 LLM 路径真实落库；regex 输出作为 hints 注入 LLM prompt，并独立写一份 shadow 表（memory_l3_facts_shadow_regex）用于对照

Add module: backend/heart/ss02_memory/mode.py
- get_mode() -> Literal["regex", "llm", "dual"]
- 提供单元测试覆盖 env 切换

DO NOT change any current behavior yet (默认 regex 模式)。

Commit: "feat(ss02): add MEMORY_EXTRACTOR_MODE feature flag"
```

**验收**:
```
□ HEART_MEMORY_EXTRACTOR_MODE=llm pytest tests/unit/ss02_memory → 不崩
□ 默认值 regex，所有现有测试 0 改动通过
□ docs/state_invariants.md 增加 flag 说明
```

## 2.3 Task: Slow Path Worker 骨架

**Tool**: **GLM**
**Why**: 现有 workers 包已存在（见 `backend/heart/workers/`），模式可复用。

**Prompt**:

```
Create the Slow Path memory extractor worker skeleton.

Path: backend/heart/workers/memory_extractor_worker.py

Reference existing workers in backend/heart/workers/ for shared patterns:
- DB session management
- Graceful shutdown
- Prometheus metric labels
- structlog conventions

Worker responsibilities (skeleton only this step, real extractor in Phase B):
1. Poll memory_extraction_queue WHERE status='pending' ORDER BY enqueued_at LIMIT 10
2. For each batch:
   - mark status='processing', started_at=now
   - call placeholder: ExtractorPlaceholder.run(batch) -> returns []
   - mark status='done', finished_at=now
3. Sleep 5s between empty polls

Add hooks (NotImplemented stubs, filled by Phase B):
- class Extractor (Protocol)
  - async def run(batch: list[QueueItem]) -> list[ExtractionCandidate]
- class Resolver (Protocol)
- class Writer (Protocol)

Prometheus metrics:
- heart_memory_extractor_runs_total{status}
- heart_memory_extractor_latency_seconds (histogram)
- heart_memory_extractor_queue_depth (gauge)
- heart_memory_extractor_cost_usd_total

Also: enqueue function in service.py
- MemoryService._enqueue_extraction(turn, hints) — called inside encode_fast() AFTER L1 写入
- Behind feature flag: only enqueue if mode in ("llm", "dual")

Tests:
- backend/tests/unit/ss02_memory/test_extractor_worker_skeleton.py
  - Worker 启动 / 优雅关停
  - 空队列时 sleep 后再次 poll
  - placeholder 跑通

Commit: "feat(ss02): add slow path memory extractor worker skeleton"
```

**验收**:
```
□ worker 可独立启动 (python -m heart.workers.memory_extractor_worker)
□ encode_fast() 在 mode=llm 时把任务塞队列；mode=regex 时不塞
□ 单测 0 红
□ docker-compose.yml 增加 service memory-extractor-worker（如果已经有 worker pattern 参考）
```

---

# 第三部分: Phase B — LLM Extractor 主体

> **目标**：跑通 turn → 候选事实 → resolve → 落 L2/L3 全链路。
> **总耗时**：3–4 天（Opus 设计 1.5 天 + GLM 实施 2 天）。

## 3.1 Task: Structured Output Schema 设计

**Tool**: **Opus**
**Why**: schema 决定整套抽取的天花板；这里的判断需要架构师视角，不要让 GLM 拍脑袋。

**Prompt**:

```
Design the StructuredOutput schema for SS02 Memory LLM Extractor.

Context:
- Input: window of N=6 recent turns (raw text + speaker + ts) + relevant L3 snapshot
- Output: list of ExtractionCandidate that downstream Resolver consumes
- Model: claude-haiku-4-5-20251001 with tool-use forced structured output
- Must handle: coreference, fragmentation, rhetoric, ambiguity, supersession, negation

Design the JSON Schema (draft-07) for:

1. ExtractionCandidate (the unit produced by LLM)
   Required: entity_type, attribute, value, source_turns, confidence, kind, operation, reasoning
   Optional: entity_ref, prior_value_id (when supersede)
   
   - entity_type enum: self | pet | family | friend | colleague | location | possession | preference | event | other
   - attribute enum: name | nickname | age | color | breed | occupation | relation | location_residence | location_origin | hobby | dislike | health_condition | birthday | anniversary | other
   - operation enum: create | update | supersede | soft_delete  (Resolver may override)
   - kind enum: disclosure | rhetoric | question | negation | hypothetical
   - confidence: float [0.0, 1.0]
   - source_turns: array of int (turn IDs, NOT array indexes)
   - reasoning: string, ≤ 200 chars, MUST cite the turn(s) that grounded the decision

2. ExtractionEnvelope (top-level)
   {
     extractor_run_id: uuid,
     model: str,
     prompt_version: str (semver, locked once shipped),
     candidates: ExtractionCandidate[],
     dropped_signals: [{turn_id, raw_phrase, reason}]  -- LLM-recognized but rejected
   }

Decisions you must justify:
- Why this enum set (and what's intentionally out-of-scope for v1)
- Why "kind" lives on the candidate (not as a separate filter step)
- Why reasoning is required not optional
- Why dropped_signals exists (audit + future regex retirement evidence)

Edge cases the schema must enable (NOT solve, but enable downstream to solve):
- "我有只猫" then turn+1 "叫妙妙" then turn+3 "灰白色的" → 3 candidates with overlapping source_turns OR 1 candidate updated over the window
- "我没有宠物" 30 turns after "我有只猫叫妙妙" → soft_delete operation on the existing fact
- 「跟我一样」需要 LLM 解析为具体 reference，否则归入 dropped_signals

DO NOT WRITE CODE YET. Output: docs/design/memory_extractor_schema.md
- §1 schema (formal, copy-pasteable JSON Schema)
- §2 enum closure rationale
- §3 edge case coverage table
- §4 versioning policy (when to bump prompt_version vs schema_version)
- §5 known limitations (v1 不解决的 case，明文列出)
```

**验收**:
```
□ docs/design/memory_extractor_schema.md 存在
□ §1 JSON Schema 可被 jsonschema 库 validate
□ §5 限制列表 ≥ 5 条（说明 v1 不解决什么）
□ HUMAN 评审 + 签字 (per CLAUDE.md "战略选择 = HUMAN 批准" 原则)
```

## 3.2 Task: Extractor Prompt 设计

**Tool**: **Opus**
**Why**: prompt 是这个系统效果的命脉；必须用最强模型设计 + 迭代。

**Prompt**:

```
Design the Extractor prompt for SS02 Memory LLM Extractor v1.

Context:
- Schema locked in docs/design/memory_extractor_schema.md
- Model: Haiku 4.5, forced tool-use to emit ExtractionEnvelope
- Token budget per call: < 4k input, < 1k output
- Must run cheap & fast (target: ~$0.001/call)

Inputs the prompt receives:
1. Recent window: list of {turn_id, speaker, ts, text}
2. Relevant L3 snapshot: list of {entity_type, entity_ref, attribute, value, confidence, last_seen}
3. Hint signals from regex (mode=dual): list of {turn_id, raw_phrase, suspected_attribute}

Required behaviors:
- Coreference: "她" / "他" / "那只" 必须解析到具体 entity_ref；不能解析 → dropped_signals
- Fragmentation: 同一实体跨 turn 拼装为单一 candidate，source_turns 列全
- Rhetoric detection: "我养你" / "我有病了哈哈" → kind=rhetoric → 不入库
- Question detection: "我叫什么吗" → kind=question → 不入库
- Negation: "我没有宠物" → kind=negation + operation=soft_delete（针对已存在事实）
- Supersession: 新值 vs L3 旧值不同 → operation=supersede + prior_value_id 填上
- 拒绝产出：不确定时返回空 candidates 数组，而不是低质量猜测

Prompt structure (output as a Jinja2 template):
1. System: persona + task + non-goals + JSON-only output rule
2. Examples: 6 few-shot examples covering the 6 edge-case categories above
3. User: serialized window + L3 snapshot + hints

Critical:
- Examples must include at least 1 "correct rejection" (returning empty candidates)
- Examples must include 1 supersession case
- No example should leak character-specific voice (this is extractor, not composer)
- Prompt must instruct LLM that "reasoning" field is REQUIRED for every candidate, citing turn_id

Cost / latency analysis:
- Estimate input tokens (window 6 turns × 80 tokens + L3 snapshot 200 tokens + hints + few-shot ~1500 = ~2200)
- Estimate output tokens (avg 200, max 800)
- Per call cost @ Haiku 4.5 pricing  → must come in under $0.002

DO NOT WRITE CODE YET. Output:
- docs/design/memory_extractor_prompt.md
  - §1 Prompt template (Jinja2)
  - §2 Few-shot example set (6 examples, full input + expected output)
  - §3 Cost / latency estimate with assumptions
  - §4 Versioning policy (prompt_version starts at "1.0.0")
  - §5 Test prompts to run by hand (5 prompts the executor should manually run to sanity-check before writing code)
```

**验收**:
```
□ docs/design/memory_extractor_prompt.md 存在
□ §2 至少 6 个 few-shot（rhetoric / question / negation / fragmentation / coreference / 正常 disclosure 各 1）
□ §3 估算成本 < $0.002/call
□ HUMAN 跑 §5 的 5 个测试 prompt，确认 LLM 输出符合 schema
```

## 3.3 Task: Extractor 实施

**Tool**: **GLM**
**Why**: Schema + Prompt 都已锁定，剩下是机械实现。

**Prompt**:

```
Implement the SS02 Memory LLM Extractor.

References (read first, do NOT redesign):
- docs/design/memory_extractor_schema.md
- docs/design/memory_extractor_prompt.md
- CLAUDE.md 「LLM Router 强制」铁律：所有 LLM 调用走 heart.infra.llm.router，禁止直接 import provider SDK

Files to create:
1. backend/heart/ss02_memory/extractor/__init__.py
2. backend/heart/ss02_memory/extractor/types.py
   - Pydantic models matching the locked schema
   - ExtractionCandidate, ExtractionEnvelope, QueueItem, ExtractorRunResult
3. backend/heart/ss02_memory/extractor/prompt_builder.py
   - Jinja2 renderer for the prompt template
   - PromptBuilder.build(window: list[Turn], l3_snapshot: list[L3Fact], hints: list[Hint]) -> str
4. backend/heart/ss02_memory/extractor/llm_extractor.py
   - class LLMExtractor:
     - __init__(router, prompt_version: str)
     - async def run(batch: list[QueueItem]) -> ExtractorRunResult
   - On structured output validation failure: retry once with error feedback in prompt
   - On second failure: mark queue item failed, log structured error
   - Enforce cost cap from settings (MEMORY_EXTRACTOR_COST_CAP_USD)
5. backend/heart/ss02_memory/extractor/cost_guard.py
   - Wraps CostTracker; enforce per-run cap; raise CostCapExceeded before LLM call when projected cost > cap

Tests:
- backend/tests/unit/ss02_memory/extractor/test_prompt_builder.py
  - Renders deterministically given same input
  - Includes all 3 input sections
- backend/tests/unit/ss02_memory/extractor/test_llm_extractor.py
  - Use fake LLM provider that returns canned ExtractionEnvelope JSON
  - 6 canonical scenarios from few-shot (positive cases)
  - 2 malformed JSON → retry → success
  - 1 cost cap exceeded → CostCapExceeded raised
  - 1 schema validation failure → marked failed

Integration test (Tier B):
- backend/tests/integration/ss02_memory/test_extractor_end_to_end.py
  - Real PG + fake LLM
  - Enqueue → worker pick up → extract → return envelope (NOT yet written to L2/L3, that's Resolver/Writer)

Constraints:
- All LLM calls via heart.infra.llm.router (NO direct provider SDK)
- prompt_version locked to "1.0.0" — bump requires HUMAN approval (matches §2.2 versioning policy)
- structlog: every run emits {extractor_run_id, candidates_count, dropped_count, cost_usd, latency_ms}

Commit: "feat(ss02): implement LLM Extractor (prompt builder + extractor + cost guard) — INV-M-11"
```

**验收**:
```
□ pytest tests/unit/ss02_memory/extractor → 全绿
□ pytest tests/integration/ss02_memory/test_extractor_end_to_end.py → 全绿（fake LLM）
□ 1 次手工真实 Haiku 调用：HEART_MEMORY_EXTRACTOR_MODE=llm + 真 API key，6 个 few-shot 输入复跑，输出与 §3.2 §5 测试 prompt 期望一致
□ 单次 run cost 实测 < $0.002
□ extractor_run_id 出现在 structlog
```

## 3.4 Task: Resolver + Writer 实施

**Tool**: **GLM**
**Why**: 决策规则在 §1 已固化（INV-M-NEW-B 等），实现是查 L3 + 比对 + 落库 + 写 audit。

**Prompt**:

```
Implement Resolver + Writer for SS02 Memory LLM Extractor.

References (read first):
- docs/design/memory_extractor_schema.md  
- docs/design/state_invariants.md  (INV-M-NEW-A/B/C)
- docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md §1 (this doc)

Files:
1. backend/heart/ss02_memory/extractor/resolver.py
   - class Resolver:
     - async def resolve(envelope: ExtractionEnvelope, user_id: UUID) -> list[ResolverDecision]
   - For each candidate, look up matching active L3 row by (user_id, entity_type, entity_ref, attribute)
   - Decision table:
     - candidate.kind in {rhetoric, question, hypothetical} → REJECT (do not write)
     - candidate.kind == negation + matching L3 exists → SOFT_DELETE
     - candidate.kind == disclosure:
        - no match → CREATE
        - match + same value → REINFORCE (mention_count++, confidence_ewma update, last_seen=now)
        - match + different value + candidate.confidence >= 0.7 → SUPERSEDE (mark old is_active=False, superseded_by_id; insert new)
        - match + different value + candidate.confidence < 0.7 → CONFLICT_DEFER (do not write, log; future: requires human review or repeated mention)
   - confidence_ewma update rule: ewma_new = 0.7 * ewma_old + 0.3 * candidate.confidence

2. backend/heart/ss02_memory/extractor/writer.py
   - class Writer:
     - async def commit(decisions: list[ResolverDecision], envelope: ExtractionEnvelope, user_id: UUID) -> None
   - Transactional: all decisions for one envelope in one DB tx
   - Writes L2 episodic record (raw candidate + reasoning) for every decision (yes, including REJECT — we want auditability)
   - Writes L3 changes per CREATE/SUPERSEDE/REINFORCE/SOFT_DELETE
   - Writes memory_audit_log row for every state change, including old_value/new_value
   - Updates extraction_queue.status = "done"
   - On exception: tx rollback, mark queue status="failed", retry_count++

3. Wire into worker:
   - backend/heart/workers/memory_extractor_worker.py:
     - Replace ExtractorPlaceholder with LLMExtractor
     - Pipeline: Extractor.run → Resolver.resolve → Writer.commit
     - Idempotency: same extractor_run_id → reject second commit (use unique constraint on audit_log.extractor_run_id + entity/attribute)

Tests:
- backend/tests/unit/ss02_memory/extractor/test_resolver.py
  - Each row of the decision table
  - confidence_ewma update math
- backend/tests/unit/ss02_memory/extractor/test_writer.py
  - Each decision type writes correct rows
  - Idempotency via duplicate envelope replay
  - Rollback on partial failure
- backend/tests/integration/ss02_memory/test_slow_path_full_pipeline.py
  - Real PG + fake LLM + canned envelope → assert L2/L3/audit rows match expectations
- backend/tests/properties/test_memory_invariants.py (extend existing)
  - INV-M-NEW-B: at any time, ≤1 active row per (user_id, entity_type, entity_ref, attribute)
  - INV-M-NEW-C: negation never physically deletes

Constraints:
- All DB writes via existing SQLAlchemy session pattern (no raw SQL)
- Every L3 write MUST cite source_turns (INV-M-NEW-A)
- No silent failures — failed envelopes go to a DLQ table (memory_extraction_dlq) for HUMAN inspection

Commit: "feat(ss02): implement Resolver + Writer for slow path (INV-M-NEW-A/B/C)"
```

**验收**:
```
□ Resolver decision table 每一行都有单测
□ Writer 完整 commit + rollback 测试
□ Property test 跑 1000 case 不变量不破
□ 集成测试：6 个 §3.2 few-shot 复跑 → L2/L3/audit_log 数据正确
□ DLQ 表存在 + HUMAN-readable 列
```

---

# 第四部分: Phase C — L3 → L4 Promoter

> **目标**：满足 INV-M-15，把当前从 fast path 直写 L4 的债务彻底还掉。
> **总耗时**：1.5 天。

## 4.1 Task: Promoter 规则设计

**Tool**: **Opus**
**Why**: 阈值选择需要 trade-off 判断（误晋升 vs 晋升过慢），需要架构师视角。

**Prompt**:

```
Design the L3 → L4 Promoter rules for SS02 Memory.

Context:
- L3 = semantic facts written by Resolver
- L4 = profile-tier identity facts visible to Composer / Reconstructor
- INV-M-15: L4 must be promoted from L3 through "multiple conditions" — make those conditions formal

Conditions to formalize (provide rationale per threshold):
1. mention_count >= K1 (suggest 3, justify)
2. confidence_ewma >= K2 (suggest 0.8)
3. age_days >= K3 (suggest 1)  — guards against single-session over-promotion
4. cross_session_count >= K4 (suggest 2 distinct sessions)
5. last_contradiction == null OR contradiction_age_days > K5
6. NOT in attribute blocklist (some attributes should NEVER promote to L4 — list them; e.g. transient mood, current location-temporary)

Demotion (L4 → L3):
- When L4 fact is contradicted by ≥2 disclosures within 14 days → demote
- Demoted facts stay in L3 with `was_l4=True` flag for audit

For each condition: how is it computed? what's the SQL query shape?

Output: docs/design/memory_promoter_rules.md
- §1 Promotion predicate (formal boolean)
- §2 Demotion predicate
- §3 Attribute blocklist (with rationale per attribute)
- §4 Scheduling: how often does Promoter run, and why
- §5 Idempotency: how do we ensure a single fact isn't promoted twice
- §6 Failure modes: what if Promoter crashes mid-batch
- §7 Test scenarios (≥ 8) covering each branch
```

**验收**:
```
□ docs/design/memory_promoter_rules.md 存在
□ §3 blocklist 至少含 3 条 + rationale
□ §7 测试场景 ≥ 8
□ HUMAN 签字 (涉及人格层数据)
```

## 4.2 Task: Promoter 实施

**Tool**: **GLM**

**Prompt**:

```
Implement L3 → L4 Promoter for SS02 Memory.

References:
- docs/design/memory_promoter_rules.md
- docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md §4

Files:
1. backend/heart/ss02_memory/promoter.py
   - class Promoter:
     - async def run_batch(user_ids: list[UUID] | None = None) -> PromoterRunResult
   - Query L3 candidates per the promotion predicate from §1 of design doc
   - For each candidate:
     - Insert L4 fact row
     - Write audit_log with operation=promote
     - Mark L3 row with promoted_to_l4_at timestamp
   - Demotion: separate pass per §2

2. backend/heart/workers/memory_promoter_worker.py
   - Singleton worker (per CLAUDE.md / existing consolidator pattern)
   - Schedule: every MEMORY_PROMOTER_INTERVAL_SECS
   - Lock via redis SETNX to prevent double-run across replicas

3. Add migration 005_memory_l4_extras.py
   - L4 table: add columns (was_l4 BOOLEAN, promoted_from_l3_id UUID, promoted_at TIMESTAMPTZ)

Tests:
- backend/tests/unit/ss02_memory/test_promoter.py
  - All 8 §7 scenarios
  - Blocklist enforcement
- backend/tests/integration/ss02_memory/test_promoter_end_to_end.py
  - Seed L3 with controlled facts → run promoter → assert L4 + audit_log

Wire into orchestrator:
- Remove `sacred_reason="fast_encoder_identity_detection"` direct-to-L4 path in
  backend/heart/ss07_orchestration/orchestrator.py:981
- Replace with NO-OP (slow path now handles this) + log a deprecation warning
- Add a follow-up test asserting fast path NEVER writes L4 (INV-M-11 property test)

Commit: "feat(ss02): add L3→L4 Promoter + remove fast-path direct L4 write (INV-M-11/15)"
```

**验收**:
```
□ 所有 §7 测试场景 pass
□ orchestrator.py:981 不再直写 L4 — 由 property test 保证
□ Redis singleton lock 工作正常
□ promoter 跑批可观测 (Prometheus + structlog)
```

---

# 第五部分: Phase D — Regex 灰度下线

> **目标**：在保留回滚能力的前提下，把 regex 提取逻辑彻底退化为 hints provider，最终移除。
> **总耗时**：2 天 + 2 周观察期。

## 5.1 Task: Regex → Hints Provider 重构

**Tool**: **GLM**
**Why**: 机械重构 + 移动代码。

**Prompt**:

```
Refactor regex extraction logic to a hints provider.

Goal: 把 backend/heart/ss02_memory/encoder/fast.py 中的语义提取部分剥离出来，仅作为 LLM Extractor 的辅助信号。

Files to change:
1. NEW: backend/heart/ss02_memory/hints/__init__.py
2. NEW: backend/heart/ss02_memory/hints/regex_hints.py
   - 把 fast.py 的 _compile_fact_patterns / _extract_identity_signals / load_lexicon 全部搬过来
   - 新接口: 
     class RegexHintsProvider:
       def scan(self, turn_text: str) -> list[Hint]
     Hint = dataclass { raw_phrase: str, suspected_attribute: str, span: tuple[int, int] }
   - 不再产出 IdentitySignal / 不再触发 L4 写入

3. MODIFY: backend/heart/ss02_memory/encoder/fast.py
   - 删除 fact / identity patterns 相关代码
   - FastEncoder.encode() 保持原签名，返回 FastSignals
   - 内部：
     - 仍然写 L1 (Working Memory)
     - 调 RegexHintsProvider.scan(turn.text) 得到 hints
     - 通过 MemoryService._enqueue_extraction(turn, hints) 入队
     - 不再返回 IdentitySignal[]（或返回空列表保持类型兼容）
   - 在 FastEncoder docstring 顶部加 deprecation note 指向本文档

4. MODIFY: backend/heart/ss02_memory/encoder/__init__.py
   - 移除 IdentitySignal 的 re-export（或保留但标 Deprecated）

5. MODIFY: backend/heart/ss02_memory/service.py
   - encode_fast() 内部确认仅写 L1 + enqueue
   - 新增 INV-M-11 runtime assertion: 不允许任何 L2/L3/L4 写在 fast path

6. MODIFY: backend/heart/scripts/seed_demo.py
   - FastEncoder 调用保持，但 seed 现在走 fake LLM extractor（保证 idempotent 不依赖真 LLM）

7. MODIFY: backend/heart/ss07_orchestration/orchestrator.py
   - 删除 sacred_reason="fast_encoder_identity_detection" 相关分支
   - 替换为 NO-OP + 一次性 deprecation log

Update tests:
- 任何依赖 IdentitySignal 的现有测试 → 改为依赖 Hint 或 mock LLM extractor 输出
- 不许"通过删除测试让它绿"——按 CLAUDE.md 档 A/B 规则处置

Compatibility:
- mode=regex 时不入队（保持当前行为，方便回滚）
- mode=dual 时 fast path 仍跑 regex hints，但落库走 LLM 路径
- mode=llm 时 regex hints 仍跑（作为提示），但不再有任何独立写入路径

Commit: "refactor(ss02): demote regex extraction to hints provider; fast path obeys INV-M-11"
```

**验收**:
```
□ fast.py 不再含 fact patterns；regex_hints.py 接管
□ 全套单测 0 红
□ orchestrator.py:981 残留代码移除
□ INV-M-11 property test 加固：fast path 在所有 mode 下都不写 L2/L3/L4
□ CLAUDE.md 档 C 债务（如有）登记到 pyproject.toml per-file-ignores + 开 tracking issue
```

## 5.2 Task: 双跑对照（mode=dual）

**Tool**: **GLM**（实施） + **HUMAN**（评估）

**Prompt**:

```
Run dual-mode comparison for 2 weeks in staging.

Setup:
1. Deploy with MEMORY_EXTRACTOR_MODE=dual
2. Shadow table: memory_l3_facts_shadow_regex 写 regex 路径的输出（不影响主 L3）
3. 主 L3 仅接受 LLM 路径输出
4. Daily job: backend/heart/scripts/extractor_diff_report.py
   - 列出每日 LLM vs regex 的差异：
     - LLM 新增但 regex 漏的（recall gain）
     - regex 新增但 LLM 漏的（recall loss / 需要 prompt 调整）
     - 同一 entity 两边值不同（需要人工裁决）
   - 输出: docs/audit/memory_extractor_diff_YYYY-MM-DD.md

Acceptance metrics (2 周观察期累计):
- LLM recall ≥ regex recall × 1.5
- LLM precision ≥ regex precision (按 HUMAN sampling 评估)
- LLM 假阳性率 < 5%（按 HUMAN sampling 评估）
- LLM 成本 < $0.50/天/活跃用户

If 任一条件不达标：
- 不准移除 regex
- 提 issue 调整 prompt（回到 §3.2）或 schema（回到 §3.1）
- 重新跑 2 周观察期
```

**验收**:
```
□ 2 周累计 diff 报告齐全
□ HUMAN sampling 1% 真实记录裁决
□ acceptance metrics 全达标 OR 提了改进 issue
```

## 5.3 Task: Regex 移除

**Tool**: **HUMAN**（决策） + **GLM**（执行）

**Prompt**:

```
Sunset regex extraction.

Pre-conditions (HUMAN signs off):
- §5.2 acceptance metrics 全达标
- Golden Set (§6) 上 LLM 全绿 持续 ≥ 7 天

Action:
1. Default config: MEMORY_EXTRACTOR_MODE=llm
2. mode=regex / mode=dual 标记 Deprecated（日志 warn）
3. 60 天后（独立 PR）：
   - 删除 RegexHintsProvider 实现（保留 stub 返回空列表）
   - 删除 shadow 表 migration（新建 migration drop table）
   - 关闭 dual mode 代码路径
4. 60 天观察期结束确认无回归后：完全删除 RegexHintsProvider + Hint 类型

Commit: "chore(ss02): default to LLM extractor; deprecate regex mode"
```

**验收**:
```
□ MEMORY_EXTRACTOR_MODE 默认 llm
□ 生产 7 天 0 回归
□ 60 天 sunset issue 已开（含 dueDate）
```

---

# 第六部分: Phase E — Golden Set + 回归

> **目标**：建立可持续的回归网，让未来任何对 schema / prompt / resolver 的改动都有金本位。
> **总耗时**：2 天（设计） + 1 周（HUMAN 标注）。

## 6.1 Task: Golden Set 设计

**Tool**: **Opus**

**Prompt**:

```
Design the Golden Set for SS02 Memory LLM Extractor regression.

Goal: a curated set of conversation snippets with expected ExtractionEnvelope outputs.
Used as: PR-gate test (must pass for any change to schema / prompt / resolver).

Coverage matrix (must cover all 7 problem categories):
1. Coreference: "她" / "他" / "那只" / "跟我一样" 
2. Fragmentation: 3+ turn 拼装单一实体
3. Rhetoric: 「我养你」「我有病了哈哈」「她真的会要了我的命」
4. Question: 「我叫什么吗」「你还记得我妈生日吗」
5. Negation: 「我没有宠物」after prior disclosure
6. Supersession: 旧值 vs 新值（年龄、住址、工作）
7. Cross-session: 多次会话强化才晋升 L4

Plus baseline cases:
8. Plain disclosure: 「我叫张三」「我有只猫叫妙妙」
9. Mixed: 一个 turn 含多个事实
10. Sensitive: 健康 / 性取向 / 政治倾向（必须正确归为 disclosure 但标记 sensitive=True，影响 L4 晋升规则）

Per case format:
{
  case_id: str,
  category: str,
  window: [{turn_id, speaker, ts, text}],
  l3_snapshot: [...],
  expected_envelope: ExtractionEnvelope,
  notes: str (为什么这条是对的)
}

Size: 30–50 cases initial. 期望分布：
- Coreference 6
- Fragmentation 5
- Rhetoric 6
- Question 4
- Negation 4
- Supersession 5
- Plain disclosure 8
- Sensitive 4
- Adversarial / edge 5+

Output:
- docs/design/memory_golden_set_design.md
  - §1 Coverage matrix (categories × count × rationale)
  - §2 Authoring guidelines (谁可以贡献 / 评审流程)
  - §3 File format (JSONL / YAML)
  - §4 Scoring criteria: how do we compare LLM output to expected envelope (exact match? subset match? per-field tolerance?)
  - §5 False-positive handling: 当 LLM 输出"也合理"但和 expected 不同 → 评审 → 决定更新 expected
```

**验收**:
```
□ docs/design/memory_golden_set_design.md 存在
□ §4 scoring criteria 明确（不能含糊"差不多就行"）
□ HUMAN 评审
```

## 6.2 Task: Golden Set 标注与落地

**Tool**: **HUMAN**（主导） + **GLM**（数据加载脚本）

**Prompt**:

```
Populate the Golden Set.

Path: backend/tests/golden/memory_extraction/cases.jsonl

Process:
1. HUMAN drafts 30–50 cases per §6.1 coverage matrix
   - Use real-world inspiration (脱敏)
   - Include hard adversarial cases ("我有 ChatGPT" — is ChatGPT a pet?)
2. GLM writes the data loader: backend/heart/qa/golden_loader.py
   - Validates each case against schema
   - Reports duplicates / missing fields
3. HUMAN reviews each case end-to-end
4. Commit cases under "test(ss02): seed Memory Extractor golden set v1"
```

**验收**:
```
□ cases.jsonl ≥ 30 条
□ 覆盖率符合 §6.1 §1 矩阵
□ golden_loader 单测覆盖
```

## 6.3 Task: CI Gate

**Tool**: **GLM**

**Prompt**:

```
Wire Golden Set as a PR gate.

Files:
1. backend/tests/golden/memory_extraction/test_extractor_golden.py
   - 参数化每个 case
   - Marker: @pytest.mark.golden
   - 使用 fake LLM provider 注入 expected envelope → 测试整条 Resolver + Writer 流水
   - 另一组：@pytest.mark.golden_live (真实 LLM)，仅 nightly 跑

2. 真实 LLM 模式：
   - 运行 LLMExtractor 真调 → 用 §6.1 §4 的 scoring criteria 评分
   - 输出: /tmp/golden_score_report.html (per case pass/fail + diff)
   - 整体 pass threshold: 90% cases pass

3. CI integration:
   - 任何 PR 修改:
     - backend/heart/ss02_memory/**
     - config/encoder_lexicon.yaml
     - docs/design/memory_extractor_*.md
   触发 golden suite (fake LLM mode, 必过)
   - Nightly cron: golden_live (真 LLM)，结果发邮件，不阻塞 PR

4. Make targets:
   - make memory-golden: pytest -m golden
   - make memory-golden-live: pytest -m golden_live --live

Reference:
- backend/tests/live/test_voice_drift.py 作为 live 测试模式参照

Commit: "test(ss02): add Memory Extractor golden set PR gate + nightly live regression"
```

**验收**:
```
□ make memory-golden 在 fake mode 跑通
□ make memory-golden-live 真 LLM 调用跑通，pass rate ≥ 90%
□ CI hook 配置（待 GitHub Actions 账单解决后生效）
```

---

# 第七部分: Cut Criteria（强制）

整体重构完成判定：

```
□ 所有 §2-§4 任务 commit 入 main
□ MEMORY_EXTRACTOR_MODE 默认 llm 持续生产 7 天 0 回归
□ orchestrator.py:981 旧路径删除
□ INV-M-11 / INV-M-15 / INV-M-NEW-A/B/C 单元 + property 测试齐全
□ Golden Set ≥ 30 条 + CI gate 启用
□ §5.2 dual-mode 2 周观察期 acceptance metrics 全达标
□ 真实 LLM 调用单次成本 < $0.002，按 100 turn/天活跃用户估算 < $0.20/天
□ pytest tests/  0 failed
□ docs/design/memory_extractor_schema.md / memory_extractor_prompt.md / memory_promoter_rules.md / memory_golden_set_design.md 全部存在
□ HUMAN 签字 docs：schema、prompt、promoter、golden set 各一份
```

---

# 第八部分: Session 安排（按模型分配）

```
Week 1 (Phase A 基础设施)
  Day 1: GLM — 2.1 Migration + 2.2 Feature Flag
  Day 2: GLM — 2.3 Worker 骨架 + 单测

Week 2 (Phase B Extractor 设计)
  Day 1: Opus — 3.1 Schema 设计（半天）+ HUMAN 评审签字
  Day 2: Opus — 3.2 Prompt 设计 + 6 few-shot + 手工 sanity check
  Day 3: HUMAN — 跑 §3.2 §5 测试 prompt 5 条，签字

Week 3 (Phase B 实施)
  Day 1-2: GLM — 3.3 Extractor 实施 + 单元 + 集成
  Day 3-4: GLM — 3.4 Resolver + Writer 实施
  Day 5: HUMAN+GLM — 真实 Haiku 一次性 sanity run，对 6 个 few-shot

Week 4 (Phase C Promoter)
  Day 1: Opus — 4.1 Promoter 规则设计 + HUMAN 签字
  Day 2-3: GLM — 4.2 Promoter 实施 + 干净掉 orchestrator.py:981

Week 5 (Phase D 灰度上线)
  Day 1: GLM — 5.1 regex → hints 重构
  Day 2: 部署 staging mode=dual + diff 报告脚本
  Day 3-14: HUMAN — 每日 5 分钟看 diff 报告，每周抽样 1%

Week 6 (Phase E Golden Set)
  Day 1: Opus — 6.1 设计
  Day 2-4: HUMAN — 6.2 标注 30-50 条 cases
  Day 5: GLM — 6.3 CI gate

Week 7 (灰度完成 + 收尾)
  Day 1: HUMAN 评 §5.2 acceptance metrics
  Day 2: GLM — 5.3 切默认 mode=llm
  Day 3-7: 生产观察 + Cut Criteria 验收
```

---

# 第九部分: 风险与回滚

| 风险 | 触发条件 | 缓解 |
|------|---------|------|
| LLM 提取漏关键事实（recall 跌） | §5.2 dual-mode 显示 LLM 漏抓 regex 能抓的事实 | 不切默认；调整 prompt / 加 few-shot；再观察 |
| LLM 成本超预算 | cost_guard 频繁触发上限 | 降批 size / 加强 idle 触发 / 调短窗口 |
| LLM 输出 schema 偶发不合规 | retry 后仍失败比例 > 1% | prompt 加强 + 升级模型（Haiku → Sonnet）局部切换 |
| 隐私敏感事实误入 L4 | §6.1 §10 敏感分类失效 | 阻断 L4 晋升 + HUMAN review |
| Promoter 误晋升 | 单测漏边界 case | 立即关闭 Promoter (feature flag 单独控制) + 手工 demote |
| Migration 005 出问题 | down→up 失败 | 严格走 §1.3 reference 的 roundtrip 测试，PR 必跑 |

**整体回滚预案**：
- 任意阶段失败 → 切回 `MEMORY_EXTRACTOR_MODE=regex`
- 数据回滚：audit_log + extraction_queue 永不物理删除，可按 extractor_run_id 反向纠正
- Migration 回滚：`alembic downgrade -1` 已在 §2.1 §1.3 验证

---

# 附录 A: 给执行模型的 Hand-off Checklist

**给 Opus 的 prompts**（4 个）：
- §3.1 Schema 设计
- §3.2 Prompt 设计
- §4.1 Promoter 规则
- §6.1 Golden Set 设计

**给 GLM 的 prompts**（8 个）：
- §2.1 Migration
- §2.2 Feature Flag
- §2.3 Worker 骨架
- §3.3 Extractor 实施
- §3.4 Resolver + Writer
- §4.2 Promoter 实施
- §5.1 Regex → Hints 重构
- §6.3 CI Gate

**HUMAN 必须亲自做的事**：
- 4 份设计文档评审签字
- §3.2 §5 5 个手工 prompt 试跑
- §5.2 2 周观察 + 1% 抽样裁决
- §6.2 Golden Set 30–50 条标注

**模型选择铁律**（不允许颠倒）：
- 任何「枚举、阈值、unit 设计、prompt 工艺」→ Opus
- 任何「写代码、写测试、迁移、CI、机械重构」→ GLM
- 任何「跨模块影响、人格层数据」→ HUMAN 把关

---

# 最后

这个重构会**还掉两个核心 spec 债务**：
- INV-M-11 ：fast path 重新只写 L1
- INV-M-15 ：L4 晋升经过多重条件，而不是 regex 拍脑袋

完成后，未来任何「为什么 AI 记得 / 忘了 / 误记 X」类问题都能通过 `memory_audit_log` 反查到具体 turn 和 extractor_run_id，从机械可调试变成结构可解释。

> **重构不是新增 feature，是把已经有的东西真正连起来 + 加防御。**
> （引自 PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md 序章）

---

**版本**: 1.0.0
**创建日期**: 2026-06-19
**主笔**: Opus 4.7
**执行模型**: Opus（架构 / Schema / Prompt 设计） + GLM（实施 / 测试 / 重构）
**下次修订**: Phase B Extractor 实施后第一次 retro
