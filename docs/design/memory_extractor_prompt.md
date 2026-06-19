# SS02 Memory LLM Extractor — Prompt Design v1.0.0

**Date**: 2026-06-19
**Author**: 心屿团队
**Status**: 🟡 Design (pre-implementation)
**Schema ref**: `docs/design/memory_extractor_schema.md` (v1.0.0)
**Spec refs**: `runtime_specs/02_memory_runtime.md` §3.4 · §6.7
**Code refs (target)**: `backend/heart/prompts/memory_extraction_v1_0_0.py` (new) · existing v0 at `backend/heart/prompts/memory_extraction.py` (to be retired)

---

## 0. Scope

This document specifies the **prompt asset** that drives the LLM half of the dual-track encoder. It is the second leg of the contract; the first is the schema. Together they fully constrain what `deepseek-v4-flash` may emit through forced tool-use.

In scope:
- The Jinja2 template the runtime renders per extraction window.
- The few-shot example set baked into the system message.
- Token / cost / latency budgets and the assumptions behind them.
- Versioning rules specific to the prompt asset (the schema doc owns its own).
- Manual sanity-check prompts to run by hand before any code change ships.

Not in scope:
- The schema itself — see `memory_extractor_schema.md`.
- The Resolver's policy table — separate doc.
- Calibration of `confidence ≤ 0.7 ⇒ FPR ≤ 5%` — golden-set eval, separate PR.

---

## 1. Prompt template (Jinja2)

The runtime renders this template once per extraction call. The rendered string becomes the `system` message; the user message is the rendered `### Run input` block. The tool definition for `emit_extraction_envelope` is attached separately and forces the model to call it.

```jinja2
{# ====================================================================
   memory_extraction_v1_0_0.py — Jinja2 template
   ==================================================================== #}
{# -------------------- SYSTEM (everything above ### Run input) -------- #}
你是一个**事实提取器**，不是对话代理。

你的输入：一个长度 ≤ 6 turns 的对话窗口、L3 已知事实 snapshot、regex hint 列表。
你的输出：通过 tool-use 调用 `emit_extraction_envelope`，参数是 ExtractionEnvelope JSON。
不要输出 tool-use 以外的任何文本——没有寒暄、没有 markdown、没有解释。

## 非目标
1. 不扮演任何角色；不要使用情绪化或第一人称语言。
2. 不推断、不"补完"用户没有明示的信息。
3. 不 normalize value——"北京" 就是 "北京"，不要写成 "Beijing"；"妙妙" 就是 "妙妙"，不要拆成 "Miao Miao"。
4. 不产生 schema 不允许的字段（薪水、宗教、政治倾向等）。看到了 → `dropped_signals` with `reason=out_of_scope_attribute`。
5. 不输出 `predicate / subject / object`——那是下游 Resolver 的工作。

## 关键规则

### R1 — reasoning 必填且必须引用 turn_id
每个 candidate 的 `reasoning` ≤ 200 字符，**必须显式包含至少一个出现在该 candidate `source_turns` 数组里的 turn id**（写成 `T<id>` 或 `turn <id>`）。
✅ `"T3: 用户说'我叫张三'"`
❌ `"用户披露了姓名"`（缺 turn 引用，下游 validator 会拒绝）

### R2 — 不确定就放弃
低质量猜测污染 L3 的成本远高于漏记。任何无法可信解析的信号：
- 模糊代词 → `dropped_signals` (`reason=ambiguous_reference`)
- window 内上下文不足 → `dropped_signals` (`reason=insufficient_context`)
- 隐私越界 → `dropped_signals` (`reason=out_of_scope_attribute`)
- 自己拿不准 → `dropped_signals` (`reason=low_confidence`)
返回空 `candidates` 数组是完全合法的输出。

### R3 — 共指解析
代词（"她/他/它/那只/这个/它们"）必须解析到 window 内**已经显式介绍过**的实体。
- 能解析 → `source_turns` 同时列出引入实体的 turn 和使用代词的 turn。
- 不能解析（同一 window 内有多个候选实体、或实体来自 window 之外）→ `dropped_signals`，不出 candidate。

### R4 — 跨 turn 拼装（fragmentation）
关于同一实体的 attribute 分散在多个 turn 时（"我有只猫"→"叫妙妙"→"灰白色的"）：
- 拼成关于该实体的**多个** candidate，每个一个 attribute。
- 这些 candidate **共享 `entity_ref`**（例如 `"cat#1"`）。
- 每个 candidate 的 `source_turns` 是它依赖的所有 turn 的并集（引入实体的 turn 必须在内）。

### R5 — 修辞识别
形如 "我养你"、"我有病了哈哈"、"她就是我命"、"我女朋友是我妈" 的字面意思与字面所指不符的句子：
- 仍然产生 candidate，但 `kind="rhetoric"`。
- 不要丢进 `dropped_signals`——保留 candidate 让下游审计可见 "LLM 识别了，Resolver 抑制了"。

### R6 — 问句不提取
"你叫什么"、"我多大了"、"你还记得我说过的吗" 这类问句不产生 candidate。
若 window 内只有问句、无任何 disclosure → 空 candidates 数组。

### R7 — 否定 + 已存在事实 = soft_delete
"我没有宠物"、"我不养猫了" 等显式否定：
- 若 L3 snapshot 中存在对应实体的事实 → `kind="negation"`, `operation="soft_delete"`, `prior_value_id=<L3 fact UUID>`。
- 若 L3 snapshot 中没有对应事实 → **不写**"用户没有 X"。放入 `dropped_signals` (`reason=insufficient_context`)。
schema 的 `if/then` 规则强制 `kind=negation ⇒ operation ∈ {soft_delete, supersede}`，违反必被拒。

### R8 — 取代（supersession）
新 value 与 L3 snapshot 中的同 `(entity_type, entity_ref?, attribute)` 旧 value 不同时：
- `operation="supersede"`, `prior_value_id=<L3 fact UUID from snapshot>`.
- 找不到 prior 在 snapshot 里（snapshot 截断或未命中）→ 退回 `operation="create"`，由夜间 Consolidator 检测冲突。
- **绝不**自己捏造一个 UUID。

### R9 — 鹦鹉学舌不产生 candidate
若 hint / regex 信号触发的短语其实是用户**复述/引用**别人的话（"我妈说'你应该……'"），不要把那句话的内容写成 user 的事实。

## 字段闭包提醒（schema 已强制，列在这里防 hallucinate）
- `entity_type ∈ {self, pet, family, friend, colleague, location, possession, preference, event, other}`
- `attribute ∈ {name, nickname, age, color, breed, occupation, relation, location_residence, location_origin, hobby, dislike, health_condition, birthday, anniversary, other}`
- `kind ∈ {disclosure, rhetoric, question, negation, hypothetical}`
- `operation ∈ {create, update, supersede, soft_delete}`
- `confidence ∈ [0.0, 1.0]`——诚实评估，≥0.7 = "我愿意为它背书"
- `source_turns ⊆ window.turn_ids`（含义：用 turn_id 数字，不是 window 索引）
- `value` 长度 ≤ 500 字符；用户原话片段。

## 元数据回声（run metadata）
你必须把 `### Run input` 块尾部给出的 `extractor_run_id / model / prompt_version / schema_version` 原样回填到 envelope。这是 audit 的连接键，乱填会让下游 join 断裂。

## 输出方式
**有且仅有**一种合法输出：调用 `emit_extraction_envelope` tool，参数是一个完整的 ExtractionEnvelope JSON。
没有 candidate？空 array。没有 dropped？空 array。两边都空也是合法 envelope。

---

## Few-shot examples（学这个格式，不要学这里的内容）

{{ FEW_SHOT_EXAMPLES }}{# rendered verbatim from §2 below #}

---

### Run input

#### Window (chronological)
{% for turn in window %}
[T{{ turn.turn_id }}] {{ turn.speaker }} @ {{ turn.ts }}: {{ turn.text }}
{% endfor %}

#### L3 snapshot (already-known facts about this user; use UUIDs as `prior_value_id`)
{% if l3_snapshot %}
{% for fact in l3_snapshot -%}
- fact_id={{ fact.fact_id }} | {{ fact.entity_type }}{% if fact.entity_ref %}[{{ fact.entity_ref }}]{% endif %}.{{ fact.attribute }} = "{{ fact.value }}" | conf={{ "%.2f"|format(fact.confidence) }} | last_seen={{ fact.last_seen }}
{% endfor %}
{% else %}
(empty)
{% endif %}

#### Regex hints (mode=dual; advisory only; reject if you disagree)
{% if hints %}
{% for h in hints -%}
- T{{ h.turn_id }}: "{{ h.raw_phrase }}" → suspected_attribute={{ h.suspected_attribute }}
{% endfor %}
{% else %}
(none)
{% endif %}

#### Run metadata (echo verbatim into envelope)
- extractor_run_id: {{ extractor_run_id }}
- model: {{ model }}
- prompt_version: {{ prompt_version }}
- schema_version: {{ schema_version }}
- window.turn_ids: {{ window | map(attribute='turn_id') | list }}

Emit ExtractionEnvelope now.
```

### Template invariants

| Invariant | Enforced where |
|---|---|
| `extractor_run_id` is rendered, not LLM-invented | Runtime fills `{{ extractor_run_id }}` and validator rejects mismatches against `memory_extraction_queue.extractor_run_id`. |
| `window.turn_ids` is rendered AND echoed | Belt-and-suspenders: the template lists them at the bottom of run-input AND the LLM must put them in `envelope.window.turn_ids`. Validator compares. |
| Few-shot block is rendered verbatim each call | NOT re-templated per call — `FEW_SHOT_EXAMPLES` is the static string from §2, frozen with `prompt_version`. |
| No persona / character voice tokens | `心屿` / `老铁` / any SS01 anchor identifier MUST NOT appear in the system message or examples. Extractor is persona-free. |

---

## 2. Few-shot example set (6 examples)

The block below is what `FEW_SHOT_EXAMPLES` expands to. It is frozen with `prompt_version` and ships as a string constant; it is NOT re-rendered per call. UUIDs in `prior_value_id` are illustrative — for the few-shot they are just shape examples.

Each example is shown as `Input → Output`. The LLM at inference sees ONLY the rendered text (the `[INPUT]` / `[OUTPUT]` markup helps the model bind), not the analysis comments.

Coverage map:

| # | Edge case | Demonstrates |
|---|---|---|
| 1 | Fragmentation + Coreference | shared `entity_ref`, union of `source_turns`, pronoun resolved to a turn-introduced entity |
| 2 | Rhetoric | `kind=rhetoric` candidate (NOT dropped), `operation=create` (Resolver suppresses by `kind`) |
| 3 | Question | empty `candidates`, no drop (a pure question turn is not a "missed disclosure") |
| 4 | Negation → soft_delete | `kind=negation`, `operation=soft_delete`, `prior_value_id` filled from L3 snapshot |
| 5 | Supersession | `operation=supersede`, `prior_value_id` filled from L3 snapshot |
| 6 | Correct rejection | empty `candidates`, populated `dropped_signals[reason=ambiguous_reference]` |

---

### Example 1 — Fragmentation + Coreference

```
[INPUT]
Window:
  [T10] user @ 2026-06-18T10:00:00Z: 我家有只猫
  [T11] assistant @ 2026-06-18T10:00:05Z: 哦真的？
  [T12] user @ 2026-06-18T10:00:20Z: 嗯，她叫妙妙，灰白色的

L3 snapshot: (empty)

Hints:
  - T12: "她叫妙妙" → suspected_attribute=name

Run metadata:
  extractor_run_id: 11111111-1111-4111-8111-111111111111
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [10, 11, 12]

[OUTPUT]  (tool-call to emit_extraction_envelope)
{
  "extractor_run_id": "11111111-1111-4111-8111-111111111111",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.0",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [10, 11, 12], "size": 3},
  "candidates": [
    {
      "entity_type": "pet",
      "attribute": "name",
      "value": "妙妙",
      "entity_ref": "cat#1",
      "source_turns": [10, 12],
      "confidence": 0.92,
      "kind": "disclosure",
      "operation": "create",
      "reasoning": "T10 引入这只猫，T12 给出名字'妙妙'，'她'指代 T10 的猫"
    },
    {
      "entity_type": "pet",
      "attribute": "color",
      "value": "灰白色",
      "entity_ref": "cat#1",
      "source_turns": [10, 12],
      "confidence": 0.85,
      "kind": "disclosure",
      "operation": "create",
      "reasoning": "T12 描述同一只猫（cat#1，T10 引入）是灰白色"
    }
  ],
  "dropped_signals": []
}
```

---

### Example 2 — Rhetoric (kept as candidate, not dropped)

```
[INPUT]
Window:
  [T20] user @ 2026-06-18T11:00:00Z: 工作好累
  [T21] user @ 2026-06-18T11:00:15Z: 算了不说了，我有病了哈哈

L3 snapshot: (empty)

Hints:
  - T21: "我有病了" → suspected_attribute=health_condition

Run metadata:
  extractor_run_id: 22222222-2222-4222-8222-222222222222
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [20, 21]

[OUTPUT]
{
  "extractor_run_id": "22222222-2222-4222-8222-222222222222",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.0",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [20, 21], "size": 2},
  "candidates": [
    {
      "entity_type": "self",
      "attribute": "health_condition",
      "value": "我有病了",
      "source_turns": [21],
      "confidence": 0.30,
      "kind": "rhetoric",
      "operation": "create",
      "reasoning": "T21 接'算了不说了'+尾随'哈哈'，自嘲非字面健康陈述"
    }
  ],
  "dropped_signals": []
}
```

---

### Example 3 — Question only (empty candidates, no drops)

```
[INPUT]
Window:
  [T30] user @ 2026-06-18T12:00:00Z: 你还记得我叫什么吗？
  [T31] assistant @ 2026-06-18T12:00:05Z: （想了想）
  [T32] user @ 2026-06-18T12:00:30Z: 算啦

L3 snapshot:
  - fact_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa | self.name = "张三" | conf=0.95 | last_seen=2026-05-01

Hints: (none)

Run metadata:
  extractor_run_id: 33333333-3333-4333-8333-333333333333
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [30, 31, 32]

[OUTPUT]
{
  "extractor_run_id": "33333333-3333-4333-8333-333333333333",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.0",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [30, 31, 32], "size": 3},
  "candidates": [],
  "dropped_signals": []
}
```

---

### Example 4 — Negation → soft_delete

```
[INPUT]
Window:
  [T40] user @ 2026-06-18T13:00:00Z: 跟你说个事
  [T41] user @ 2026-06-18T13:00:10Z: 我现在没有宠物了，上个月送走了

L3 snapshot:
  - fact_id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb | pet[cat#1].name = "妙妙" | conf=0.92 | last_seen=2026-05-20
  - fact_id=cccccccc-cccc-4ccc-8ccc-cccccccccccc | pet[cat#1].color = "灰白色" | conf=0.85 | last_seen=2026-05-20

Hints:
  - T41: "没有宠物" → suspected_attribute=other

Run metadata:
  extractor_run_id: 44444444-4444-4444-8444-444444444444
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [40, 41]

[OUTPUT]
{
  "extractor_run_id": "44444444-4444-4444-8444-444444444444",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.0",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [40, 41], "size": 2},
  "candidates": [
    {
      "entity_type": "pet",
      "attribute": "name",
      "value": "妙妙",
      "entity_ref": "cat#1",
      "prior_value_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      "source_turns": [41],
      "confidence": 0.88,
      "kind": "negation",
      "operation": "soft_delete",
      "reasoning": "T41: 用户明确说'现在没有宠物了'，撤回 L3 中的猫 fact"
    }
  ],
  "dropped_signals": []
}
```

Note: only the `name` row is soft-deleted in this example to keep the few-shot tight; the Resolver cascades `do_not_recall` to the sibling `color` row by entity_ref. The schema lets the LLM emit either one or two candidates here — both are valid shapes.

---

### Example 5 — Supersession

```
[INPUT]
Window:
  [T50] user @ 2026-06-18T14:00:00Z: 其实我现在不在北京了
  [T51] user @ 2026-06-18T14:00:10Z: 上个月搬到了上海

L3 snapshot:
  - fact_id=dddddddd-dddd-4ddd-8ddd-dddddddddddd | self.location_residence = "北京" | conf=0.90 | last_seen=2026-03-01

Hints:
  - T51: "搬到了上海" → suspected_attribute=location_residence

Run metadata:
  extractor_run_id: 55555555-5555-4555-8555-555555555555
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [50, 51]

[OUTPUT]
{
  "extractor_run_id": "55555555-5555-4555-8555-555555555555",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.0",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [50, 51], "size": 2},
  "candidates": [
    {
      "entity_type": "self",
      "attribute": "location_residence",
      "value": "上海",
      "prior_value_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
      "source_turns": [50, 51],
      "confidence": 0.90,
      "kind": "disclosure",
      "operation": "supersede",
      "reasoning": "T50 否定旧居住地'北京'，T51 给出新居住地'上海'"
    }
  ],
  "dropped_signals": []
}
```

---

### Example 6 — Correct rejection (ambiguous coreference)

```
[INPUT]
Window:
  [T60] user @ 2026-06-18T15:00:00Z: 我朋友很喜欢猫
  [T61] user @ 2026-06-18T15:00:15Z: 跟我一样

L3 snapshot: (empty)

Hints:
  - T61: "跟我一样" → suspected_attribute=hobby

Run metadata:
  extractor_run_id: 66666666-6666-4666-8666-666666666666
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [60, 61]

[OUTPUT]
{
  "extractor_run_id": "66666666-6666-4666-8666-666666666666",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.0",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [60, 61], "size": 2},
  "candidates": [],
  "dropped_signals": [
    {
      "turn_id": 61,
      "raw_phrase": "跟我一样",
      "reason": "ambiguous_reference"
    }
  ]
}
```

**Why no `(self, hobby, "猫")` candidate**: T60's subject is "我朋友"，T61 的"跟我一样"是字面"我跟朋友一样"还是"我也喜欢猫"，window 内无法可信判定。R2 + R3 共同要求放弃。

---

### Voice-leakage check

Each example was scrubbed for SS01 anchor tokens (`心屿`, `老铁`, persona names). User text uses `妙妙` (a generic Chinese cat name commonly used in product copy and **not** part of any SS01 anchor), `北京/上海/张三`, and neutral assistant placeholders. The Extractor prompt does not load `soul_specs/` — confirmed by absence of any `{{ persona.* }}` Jinja vars in §1.

---

## 3. Cost / latency estimate

### 3.1 Token budget (per call)

| Component | Source | Estimated tokens |
|---|---|---|
| System prologue + non-goals + R1–R9 + field-closure reminder | §1 system block | ~900 |
| Few-shot (6 examples, Chinese text + JSON) | §2 verbatim | ~1500 |
| Rendered window (6 turns × ~80 tok) | runtime | ~480 |
| L3 snapshot (assumed ≤ 10 facts × ~25 tok) | runtime | ~250 |
| Regex hints (≤ 3 × ~25 tok) | runtime | ~75 |
| Run metadata + structural scaffolding | runtime | ~50 |
| **Input subtotal** | | **~3255** |
| Output envelope, typical (1–3 candidates + 0–2 drops) | LLM | ~200 |
| Output envelope, worst case (32 candidates × ~20 tok core fields, schema cap) | LLM | ~800 |

**Sanity check vs. user-stated budget**: user said "< 4k input, < 1k output". Typical input 3.3k ≤ 4k ✅. Output 200/800 ≤ 1k ✅. The schema cap `maxItems: 32` is the absolute ceiling on output blow-up.

### 3.2 Per-call cost

`deepseek-v4-flash` exact pricing is not finalized as of 2026-06-19. Two assumption rows below — the conclusion (under $0.002) holds across both.

| Assumption | Input $/Mtok | Output $/Mtok | Per-call (typical) | Per-call (worst) |
|---|---|---|---|---|
| Conservative (today's flash-tier ceiling) | $0.30 | $1.20 | $0.30·3.3/1000 + $1.20·0.2/1000 = $0.00099 + $0.00024 = **$0.00123** | $0.00099 + $0.00096 = **$0.00195** |
| Optimistic (flash-tier floor) | $0.10 | $0.40 | $0.00033 + $0.00008 = **$0.00041** | $0.00033 + $0.00032 = **$0.00065** |

- **Target**: ~$0.001/call.
- **Conservative typical**: $0.00123 — **within** the budget at 1.23× target.
- **Conservative worst**: $0.00195 — **under** the $0.002 hard ceiling. ✅
- **Optimistic typical**: $0.00041 — well under. ✅

Headroom: if real pricing comes in above the conservative row by 60%, typical-case cost crosses $0.002 and we have to act. Mitigations available before that point:
1. Compress few-shot from 1500 → ~900 tokens by dropping examples 3 and 6 and relying on prose rules (loss: rejection cases get less calibration).
2. Drop the rendered L3 snapshot for windows where regex hint count = 0 (≈40% of windows in spec §3.4 estimates).
3. Move to provider's prompt-caching tier if/when available — the static system+few-shot block (~2400 tok) is exactly the shape caching is designed for.

We commit to none of these in v1. Re-evaluate after the first 10k production calls produce a real cost distribution.

### 3.3 Latency

`deepseek-v4-flash` published flash-tier latency expectations: ~1.5–3s for ~3k input / ~200 output, including HTTP round-trip from CN-region runtime. Two consequences:

- **Slow-path acceptable**: the LLM extraction lives on the cold path (worker dequeues from `memory_extraction_queue`, off the user response path per `runtime_specs/02 §3.4`). Sub-3s is well under the worker's 30s timeout.
- **Hot-path NOT acceptable**: this prompt cannot be moved to the hot path. Any future "real-time extraction during composition" feature must use a different prompt with a smaller budget.

P50 / P99 to be measured against the golden set during v1.0.0 acceptance.

### 3.4 Per-window vs per-turn

The extractor runs **per window**, not per turn. With window size = 6 and a typical session of ~30 turns, that's 5 extraction calls / session, not 30. End-to-end session cost (conservative typical): 5 × $0.00123 = **~$0.006/session**. At $0.006/session, 100k MAU × 10 sessions/month = $6,000/month — the order of magnitude the company can sustain.

---

## 4. Versioning policy

This document defines `prompt_version`. The schema doc owns `schema_version`. They travel together in every envelope.

### 4.1 Initial version: `1.0.0`

`prompt_version` starts at `"1.0.0"` on first shipment. **Not `0.x`** — going straight to 1.0.0 is intentional because:

- The schema lands at `1.0.0` and audit-log JOINs require matching MAJOR.
- The v0 prompt (`backend/heart/prompts/memory_extraction.py`) is unversioned and incompatible; calling it "v0" implicitly is fine for retirement but the v1 asset must self-identify.
- A `0.x` would invite "is this stable?" anxiety that the schema-side acceptance gates already resolve.

### 4.2 Bump rules

| Bump | Trigger | Re-eval before deploy |
|---|---|---|
| **MAJOR** (`1.0.0 → 2.0.0`) | Schema MAJOR bump (locked: prompt MAJOR == schema MAJOR). OR removed/replaced ≥1 few-shot example. OR restructured rule list. OR switched target model family (e.g. `deepseek-v4-flash → qwen-flash`). | Full 50-window golden-set re-eval. Recalibrate `confidence ≤ 0.7 ⇒ FPR ≤ 5%`. Both old and new prompt run side-by-side on the golden set; new must be ≥ par on recall and ≤ +1pp on FPR. |
| **MINOR** (`1.0.0 → 1.1.0`) | Added a new few-shot example for a documented edge case. OR added an instruction that constrains a previously-unconstrained behavior. OR added attribute coverage instructions. | Targeted regression on the affected edge case + smoke run on the full golden set. |
| **PATCH** (`1.0.0 → 1.0.1`) | Typo, whitespace, identifier rename, comment edit. Behavior unchanged. | Smoke run only (5 manual prompts from §5). |

### 4.3 Immutability after ship

A published `prompt_version` is **immutable**. A "small fix" is never an in-place edit; it is always a new PATCH bump and a new file `memory_extraction_v1_0_1.py`. The audit log carries `prompt_version` per row (`memory_audit_log.prompt_version` via the envelope); if we silently edit, every audit row pointing at `1.0.0` lies about what produced it.

The previous version's file MAY be deleted from the repo after `git log` confirms the audit-log lookback window no longer references it — but the row in any compliance archive must remain joinable, so the convention is: keep the last N=3 prompt versions on disk.

### 4.4 Cross-product invariant

Prompt MAJOR is locked to schema MAJOR. Schema MINOR may advance without prompt change (e.g. new enum value the prompt doesn't yet teach the model to emit), but prompt MINOR may NOT advance without schema being at the corresponding or higher MINOR — the prompt cannot teach the model to emit an enum the schema doesn't accept.

### 4.5 File-naming convention

`backend/heart/prompts/memory_extraction_v<MAJOR>_<MINOR>_<PATCH>.py`. Each file exports:
- `PROMPT_VERSION: str` (e.g. `"1.0.0"`)
- `SCHEMA_VERSION: str` (e.g. `"1.0.0"`)
- `SYSTEM_TEMPLATE: str` (the Jinja2 string above, including `{{ FEW_SHOT_EXAMPLES }}` placeholder)
- `FEW_SHOT_EXAMPLES: str` (the frozen string from §2)
- `MODEL: str` (e.g. `"deepseek-v4-flash"`)

The active version pointer is a separate file (`backend/heart/prompts/memory_extraction_active.py`) re-exporting the chosen version. Rollback is a one-line file edit, not a rebuild.

---

## 5. Manual sanity-check prompts (run by hand before writing code)

Five prompts the executor pastes directly into the DeepSeek playground (or `curl` against the chat-completions endpoint with the v1.0.0 system prompt loaded). Each lists what to look for. Pass/fail is per-prompt; all five must pass before the worker code lands.

Run conditions: `temperature=0.0`, `tool_choice={"type":"tool","name":"emit_extraction_envelope"}`, schema attached as the tool's `input_schema`.

> Format note: each test prompt below is the `Window + L3 snapshot + Hints + Run metadata` block the runtime would render. The full system prompt from §1 (with §2 inlined for `FEW_SHOT_EXAMPLES`) is loaded separately as the `system` message.

### Test 1 — Fragmentation across 3 turns, single entity

```
Window:
  [T1] user @ 2026-06-19T09:00:00Z: 我家有只狗
  [T2] user @ 2026-06-19T09:00:10Z: 它叫大黄
  [T3] user @ 2026-06-19T09:00:20Z: 是金毛
L3 snapshot: (empty)
Hints: (none)
Run metadata:
  extractor_run_id: 90000001-0000-4000-8000-000000000001
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [1, 2, 3]
```

**Pass criteria**:
- ≥ 2 candidates, all with the same `entity_ref` (e.g. `"dog#1"`).
- Each candidate's `source_turns` includes T1 (the entity-introducing turn).
- `attribute` covers at least `name` and `breed`.
- Every `reasoning` string contains `T1`, `T2`, or `T3` literally.

### Test 2 — Negation with matching L3 prior

```
Window:
  [T10] user @ 2026-06-19T10:00:00Z: 我不喜欢咖啡了
L3 snapshot:
  - fact_id=eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee | self.hobby = "咖啡" | conf=0.80 | last_seen=2026-04-01
Hints:
  - T10: "不喜欢咖啡" → suspected_attribute=dislike
Run metadata:
  extractor_run_id: 90000002-0000-4000-8000-000000000002
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [10]
```

**Pass criteria**:
- Exactly one candidate.
- `kind="negation"`, `operation` ∈ {`soft_delete`, `supersede`}.
- `prior_value_id == "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"` (echoed from snapshot, not made up).
- If `supersede`: the new `(attribute, value)` is the user's new stance ("dislike", "咖啡"). If `soft_delete`: the candidate's `(attribute, value)` mirrors the L3 row being torn down.

### Test 3 — Question-only window

```
Window:
  [T20] user @ 2026-06-19T11:00:00Z: 你还记得我说过什么吗
  [T21] user @ 2026-06-19T11:00:10Z: 我是不是说过我多少岁了
L3 snapshot:
  - fact_id=ffffffff-ffff-4fff-8fff-ffffffffffff | self.age = "28" | conf=0.85 | last_seen=2026-05-15
Hints: (none)
Run metadata:
  extractor_run_id: 90000003-0000-4000-8000-000000000003
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [20, 21]
```

**Pass criteria**:
- `candidates == []`.
- `dropped_signals == []` (a pure question is not a "missed" disclosure).
- `window.turn_ids == [20, 21]`, `window.size == 2`.

### Test 4 — Ambiguous coreference → correct rejection

```
Window:
  [T30] user @ 2026-06-19T12:00:00Z: 我朋友养了只乌龟
  [T31] user @ 2026-06-19T12:00:15Z: 那个挺有意思的
L3 snapshot: (empty)
Hints:
  - T31: "那个" → suspected_attribute=other
Run metadata:
  extractor_run_id: 90000004-0000-4000-8000-000000000004
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [30, 31]
```

**Pass criteria**:
- `candidates == []` (no `(self, *, *)` and no `(pet, *, *)` for the user).
- `dropped_signals` non-empty; at least one entry references T31 with `reason ∈ {ambiguous_reference, insufficient_context}`.
- The user's friend's turtle is NOT promoted into a `(pet, *, *)` candidate about the user. This is the failure mode the test exists to catch.

### Test 5 — Multi-attribute single turn + supersession

```
Window:
  [T40] user @ 2026-06-19T13:00:00Z: 我叫张三，现在 30 岁了，从北京搬到杭州
L3 snapshot:
  - fact_id=12345678-1234-4abc-8def-123456789012 | self.age = "28" | conf=0.90 | last_seen=2026-01-10
  - fact_id=87654321-4321-4cba-8fed-987654321098 | self.location_residence = "北京" | conf=0.92 | last_seen=2026-01-10
Hints:
  - T40: "我叫张三" → suspected_attribute=name
  - T40: "30 岁" → suspected_attribute=age
  - T40: "搬到杭州" → suspected_attribute=location_residence
Run metadata:
  extractor_run_id: 90000005-0000-4000-8000-000000000005
  model: deepseek-v4-flash
  prompt_version: 1.0.0
  schema_version: 1.0.0
  window.turn_ids: [40]
```

**Pass criteria**:
- 3 candidates: `name="张三"`, `age="30"`, `location_residence="杭州"`.
- `name` candidate: `operation="create"` (no L3 prior).
- `age` candidate: `operation="supersede"`, `prior_value_id="12345678-1234-4abc-8def-123456789012"`.
- `location_residence` candidate: `operation="supersede"`, `prior_value_id="87654321-4321-4cba-8fed-987654321098"`.
- Every `reasoning` mentions `T40`.
- `value="30"` (raw user form), not normalized to integer or "30岁".

### Manual-test sign-off rule

If any of Tests 1–5 fails on the chosen `deepseek-v4-flash` snapshot, **do not write the worker code**. Either:
1. Iterate the prompt (still under `prompt_version=1.0.0` until shipped — pre-ship the version is mutable), OR
2. Document the failure and reduce the v1.0.0 acceptance set explicitly in §6 of the schema doc.

After the worker ships, Tests 1–5 become the smoke-suite run on every PATCH bump (per §4.2).

---

## 6. Open questions for executor

Recorded so the implementer doesn't re-derive them:

1. **Tool definition wire format**: DeepSeek's tool-use API is OpenAI-compatible — confirm `tool_choice={"type":"tool","name":...}` shape against the SDK in use, not the docs.
2. **System message size limits**: `deepseek-v4-flash`'s context is large enough for ~3.3k input, but confirm no hidden per-message cap before shipping.
3. **`tool_choice=required` vs `tool_choice=specific tool`**: this prompt only makes sense with the latter; the former allows the model to pick a non-existent tool name in some providers.
4. **Where the v0 prompt retires**: `backend/heart/prompts/memory_extraction.py` must not be imported by any new code path. A separate `chore:` PR after v1 ships should delete it.
