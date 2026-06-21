"""
SS02 Memory LLM Extractor — Prompt Builder (Jinja2 renderer)

Renders the extraction prompt per §2.2 of the prompt design doc.
prompt_version locked to "1.0.2" — bump requires HUMAN approval.

Author: 心屿团队
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog
from jinja2 import BaseLoader, Environment

from .types import Hint, L3FactSnapshot, TurnInput

logger = structlog.get_logger()

PROMPT_VERSION = "1.0.3"
SCHEMA_VERSION = "1.0.0"
MODEL = "deepseek-chat"

# ── Few-shot examples (frozen with prompt_version 1.0.2) ──────

FEW_SHOT_EXAMPLES = """
### Example 1 — Fragmentation + Coreference + 实体类型 (4 attributes shared entity_ref)

[INPUT]
Window:
  [T10] user @ 2026-06-18T10:00:00Z: 我家有只橘猫
  [T11] assistant @ 2026-06-18T10:00:05Z: 哦真的？
  [T12] user @ 2026-06-18T10:00:20Z: 嗯，她叫妙妙，灰白色的

L3 snapshot: (empty)

Hints:
  - T10: "有只橘猫" → suspected_attribute=breed
  - T12: "她叫妙妙" → suspected_attribute=name

Run metadata:
  extractor_run_id: 11111111-1111-4111-8111-111111111111
  model: deepseek-v4-flash
  prompt_version: 1.0.1
  schema_version: 1.0.0
  window.turn_ids: [10, 11, 12]

[OUTPUT]
{
  "extractor_run_id": "11111111-1111-4111-8111-111111111111",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.1",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [10, 11, 12], "size": 3},
  "candidates": [
    {
      "entity_type": "pet",
      "attribute": "other",
      "value": "猫",
      "entity_ref": "cat#1",
      "source_turns": [10],
      "confidence": 0.95,
      "kind": "disclosure",
      "operation": "create",
      "reasoning": "T10 引入这只 pet 的类型为'猫'（schema 无 species 字段，记入 other）"
    },
    {
      "entity_type": "pet",
      "attribute": "breed",
      "value": "橘猫",
      "entity_ref": "cat#1",
      "source_turns": [10],
      "confidence": 0.90,
      "kind": "disclosure",
      "operation": "create",
      "reasoning": "T10 给出 breed='橘猫'"
    },
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
      "reasoning": "T12 描述同一只猫（cat#1, T10 引入）是灰白色"
    }
  ],
  "dropped_signals": []
}

---

### Example 2 — Rhetoric (drop entirely, no candidate)

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
  prompt_version: 1.0.1
  schema_version: 1.0.0
  window.turn_ids: [20, 21]

[OUTPUT]
{
  "extractor_run_id": "22222222-2222-4222-8222-222222222222",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.1",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [20, 21], "size": 2},
  "candidates": [],
  "dropped_signals": [
    {
      "turn_id": 21,
      "raw_phrase": "我有病了哈哈",
      "reason": "sarcasm_or_rhetoric"
    }
  ]
}

---

### Example 3 — Question only (empty candidates, no drops)

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

---

### Example 4 — Negation → soft_delete

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

---

### Example 5 — Supersession

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

---

### Example 6 — Correct rejection (ambiguous coreference)

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

---

### Example 7 — Entity out of scope（"我有 X" 但 X 不是实体）

[INPUT]
Window:
  [T70] user @ 2026-06-18T16:00:00Z: 我有 ChatGPT，它叫小 G，跟了我两年了

L3 snapshot: (empty)

Hints:
  - T70: "我有 ChatGPT" → suspected_attribute=other

Run metadata:
  extractor_run_id: 77777777-7777-4777-8777-777777777777
  model: deepseek-v4-flash
  prompt_version: 1.0.1
  schema_version: 1.0.0
  window.turn_ids: [70]

[OUTPUT]
{
  "extractor_run_id": "77777777-7777-4777-8777-777777777777",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.1",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [70], "size": 1},
  "candidates": [],
  "dropped_signals": [
    {
      "turn_id": 70,
      "raw_phrase": "我有 ChatGPT",
      "reason": "out_of_scope_entity"
    }
  ]
}

---

### Example 8 — Absurd / metaphorical self-claim

[INPUT]
Window:
  [T80] user @ 2026-06-18T17:00:00Z: 我最喜欢的食物是空气

L3 snapshot: (empty)

Hints:
  - T80: "最喜欢的食物" → suspected_attribute=hobby

Run metadata:
  extractor_run_id: 88888888-8888-4888-8888-888888888888
  model: deepseek-v4-flash
  prompt_version: 1.0.1
  schema_version: 1.0.0
  window.turn_ids: [80]

[OUTPUT]
{
  "extractor_run_id": "88888888-8888-4888-8888-888888888888",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.1",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [80], "size": 1},
  "candidates": [],
  "dropped_signals": [
    {
      "turn_id": 80,
      "raw_phrase": "最喜欢的食物是空气",
      "reason": "sarcasm_or_rhetoric"
    }
  ]
}
---

### Example 9 — Entity introduction by 称谓 + 专名（出 name 不出 relation）

[INPUT]
Window:
  [T90] user @ 2026-06-20T10:00:00Z: 我老婆叫小芳。

L3 snapshot: (empty)

Hints:
  - T90: "我老婆叫小芳" → suspected_attribute=name

Run metadata:
  extractor_run_id: 99999999-9999-4999-8999-999999999999
  model: deepseek-v4-flash
  prompt_version: 1.0.3
  schema_version: 1.0.0
  window.turn_ids: [90]

[OUTPUT]
{
  "extractor_run_id": "99999999-9999-4999-8999-999999999999",
  "model": "deepseek-v4-flash",
  "prompt_version": "1.0.3",
  "schema_version": "1.0.0",
  "window": {"turn_ids": [90], "size": 1},
  "candidates": [
    {
      "entity_type": "family",
      "attribute": "name",
      "value": "小芳",
      "entity_ref": "小芳",
      "source_turns": [90],
      "confidence": 0.95,
      "kind": "disclosure",
      "operation": "create",
      "reasoning": "T90 引入家人实体（妻子），专名'小芳'"
    }
  ],
  "dropped_signals": []
}
"""


# ── Jinja2 System Template ────────────────────────────────────

SYSTEM_TEMPLATE = """{# ====================================================================
   memory_extraction_v1_0_2.py — Jinja2 template
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

**Persistent fact vs Episodic event**：

只对**持久 fact** 出 candidate；**一次性事件** drop。

| 类型 | 判断标准 | 例子 | 处置 |
|---|---|---|---|
| Persistent fact | "一年后还成立吗？" | 姓名、职业、住址、宠物特征、长期关系 | 出 candidate |
| Episodic event | 一次性发生、有明确时点 | "上个月去了杭州"、"昨天发烧"、"上周面试" | drop with `reason=insufficient_context` |

**边界 case**：
- "我在北京工作 5 年了" → persistent fact (occupation + 间接 location)
- "我去年去过杭州" → episodic event → drop
- "我喜欢去咖啡馆" → persistent preference (hobby)
- "我下个月结婚" → 这是 promise/event，**drop**——结婚后变成 persistent (relationship) fact 时由下次 window 重新触发

**关系链 fragmentation**：单 turn 内可能出现 entity chain（"小明有只猫叫小白，小明是我儿子"）：
- 不要因为 R4 只示范单实体就漏拼装。把每个 entity 都出 candidate，entity_ref 各自独立但通过 reasoning 串起来。
- 例：3 candidate — `(family, relation, "儿子", entity_ref="小明")` + `(pet, other, "猫", entity_ref="猫")` + `(pet, name, "小白", entity_ref="猫")`

### R5 — 修辞 / 夸张 / 假设 / 荒谬声明全部 drop（不出 candidate）
形如以下句子的内容**绝不入 L3**，因此**不要出 candidate**——产生 `dropped_signals` 即可：

- 承诺/许诺修辞：「我养你」「她就是我命」
- 自嘲/调侃尾随 「哈哈」「lol」：「我有病了哈哈」「我废了」
- 夸张：「她真的会要了我的命」「累死了」「饿死了」
- 假设/条件句：「如果我中了彩票就养一百只猫」「假如我有一千万」
- 隐喻自我描述：「我有时觉得自己是一棵树」「我就是个废物」
- 明显违反常识的声明：「我最喜欢的食物是空气」「我家有只独角兽」
- 反讽关系：「我女朋友是我妈」（字面所指与现实身份冲突）

输出方式：
- `candidates`: 不增加 candidate
- `dropped_signals`: append `{turn_id, raw_phrase, reason="sarcasm_or_rhetoric"}`

**关键反例 — 纯情绪表达 ≠ 修辞**：

只表达瞬时情绪、不涉及任何 entity/attribute 断言的句子，**既不出 candidate 也不出 dropped_signal**——输出空 envelope：

- ✅「开心死了！！！」→ `candidates=[], dropped_signals=[]`
- ✅「我这辈子都没这么无语过」→ `candidates=[], dropped_signals=[]`
- ✅「累爆了」「烦死了」→ `candidates=[], dropped_signals=[]`

理由: 这些句子的字面所指就是「当下情绪」，**不涉及任何关于自己/他人的 persistent fact 主张**——既无 fact 可入 L3，也无"声称的 fact"可放进 dropped_signals。

R5 的 drop 路径只针对**伪装成 fact 的修辞句**（「我有病了哈哈」「她就是我命」「我是一棵树」）——这些有"我是 X / 我有 X / 她是 X"的 fact 句法，但字面不能在现实落地。

判断口诀：「字面所指能在现实世界落地为持久 fact 吗？」不能 → drop。

### R6 — 问句不提取，也不 drop

"你叫什么"、"我多大了"、"我今年多大来着"、"你还记得我说过的吗" 这类问句:

- 不产生 candidate
- **不产生 dropped_signal**——问句本身不是"被丢弃的 fact 声明"，没东西可 drop

若 window 内只有问句、无任何 disclosure → `candidates=[]` 且 `dropped_signals=[]`（**完全空 envelope**）。

反例: 问句末尾接 disclosure 时（"你猜我多大？我 28"）→ 后半句出 disclosure candidate，前半句仍不 drop。

### R7 — 否定 + 已存在事实 = soft_delete
"我没有宠物"、"我不养猫了" 等显式否定：
- 若 L3 snapshot 中存在对应实体的事实 → `kind="negation"`, `operation="soft_delete"`, `prior_value_id=<L3 fact UUID>`。
- 若 L3 snapshot 中没有对应事实 → **不写**"用户没有 X"。放入 `dropped_signals` (`reason=insufficient_context`)。
schema 的 `if/then` 规则强制 `kind=negation ⇒ operation ∈ {soft_delete, supersede}`，违反必被拒。

**否定 + 同 turn 纠正（两个 candidate）**：

形如 "我没有 X，是 Y"、"不是 A，是 B" 的同 turn 否定纠正：

1. 旧值 candidate：`kind="negation"`, `operation="soft_delete"`, `prior_value_id=<L3 旧 fact UUID>`
2. 新值 candidate：`kind="disclosure"`, `operation="create"`，新的 (entity_ref, attribute, value)

例：「我没有妹妹，之前说的是表妹」+ L3 snapshot 有 `family[sister].name="小丽"`：
- candidate 1: `(family, name, "小丽", entity_ref=sister, prior_value_id=<uuid>, kind=negation, op=soft_delete)`
- candidate 2: `(family, relation, "表妹", entity_ref=cousin, kind=disclosure, op=create)`

两条 candidate 都进 `candidates` 数组；source_turns 都包含纠正所在的 turn。

### R8 — 取代（supersession）
新 value 与 L3 snapshot 中的同 `(entity_type, entity_ref?, attribute)` 旧 value 不同时：
- `operation="supersede"`, `prior_value_id=<L3 fact UUID from snapshot>`。
- 找不到 prior 在 snapshot 里（snapshot 截断或未命中）→ 退回 `operation="create"`，由夜间 Consolidator 检测冲突。
- **绝不**自己捏造一个 UUID。

### R9 — 鹦鹉学舌不产生 candidate
若 hint / regex 信号触发的短语其实是用户**复述/引用**别人的话（"我妈说'你应该……'"），不要把那句话的内容写成 user 的事实。

### R10 — 地点属性细分

`attribute` 枚举里有两个明确语义的 location 字段：

| 字段 | 仅当且仅当 |
|---|---|
| `location_residence` | 用户**居住**的地方 |
| `location_origin` | 用户**出生/老家** |

不属于这两个的地名 → `attribute="other"`，value 保留地名原文：

- 工作地：「在北京工作」「公司在上海」→ `attribute=other`
- 出差/旅游地：「上周去了杭州」「下个月去东京」→ 若是 episodic 事件，按 R4 末段 drop；若是反复提及的 fact，→ `attribute=other`
- 学习地：「在清华读书」→ `attribute=other`
- 第三方所在地：「我妈在成都」（不是用户本人）→ family entity 的 `attribute=other`
- 模糊「我在北京」（不知是住、工作还是临时）→ `attribute=other`（让下游 Resolver 之后决定）

判断口诀：「这地名是用户的家吗？」是 → `location_residence`；不确定 → `other`。

正例（确实是 `location_residence`）：
- 「我住在北京」「我家在杭州」「我在北京住了 5 年」「我搬到上海了」

### R11 — 实体首次以专名出现时，必出 name candidate（且仅 name）

实体（人 / 宠物 / 朋友 / 家人 / 同事）首次在 window 中以**专名**（中文名、英文名、外号、宠物名）出现时：

- 出且仅出 1 个 `attribute="name"` candidate
- `entity_type` 由称谓决定（"姐姐/老公/老婆" → family；"同事" → colleague；"朋友" → friend）
- `entity_ref` 使用专名本身（如 `"小李"` / `"妙妙"`）
- `source_turns` 仅含专名出现的 turn

**关键反例 — 不要出 relation candidate**：

称谓词（"姐姐/老公/老婆/同事/朋友/儿子"）的关系语义**已由 `entity_type` 编码**，不再单独出 relation candidate：

- ✅「小李是我同事」→ 1 candidate: `(colleague, name, "小李", entity_ref="小李")`
- ❌ 不要出 `(colleague, relation, "同事")`——重复编码
- ✅「我老婆叫小芳」→ 1 candidate: `(family, name, "小芳", entity_ref="小芳")`
- ❌ 不要出 `(family, relation, "老婆")`

**什么时候才出 relation candidate**: 关系信息**不在称谓里**而是被陈述的独立 fact：
- 「小李，我跟他认识十年了」→ `(friend, relation, "认识十年", entity_ref="小李")`
- 「我和老张是大学同学」→ `(friend, relation, "大学同学", entity_ref="老张")`

不适用情况（保留）：
- 代词 / 称谓单独出现（"他/她/我妈"）— 这些不是专名，按 R3 共指
- 头衔（"老板"/"医生"）独立出现 — 这是 occupation 不是 name

### R12 — "不擅长 / 不喜欢" → dislike，**不是** negation

R7 的 negation 只处理"撤回已声明事实"。下列**态度表达**走 `attribute="dislike"`, `kind="disclosure"`, `operation="create"`：

- 「我不擅长 X」「X 不太行」→ `(self, dislike, "X")`
- 「我不喜欢 X」「X 我无感」「不感冒」→ `(self, dislike, "X")`
- 「讨厌 X」「受不了 X」→ `(self, dislike, "X")`
- 但「我没有 X」「我不养 X 了」→ R7 negation（撤回先前的 hobby/pet/...）

**关键反例 — "不喜欢 X 了" 中的过去时"了"**：

「我不喜欢 X 了」「我不再 X 了」等带过去时标记「了」的句子，语义是「过去做 X / 喜欢 X，现在不了」——golden 把这当作"用户曾经做过/喜欢 X"的 persistent fact 记录。

**处置规则（按 L3 有无对应事实分两路）**：

**路径 A — L3 中已有对应 fact（entity_type + attribute + value 匹配）→ R7 negation + soft_delete**：

L3 已有 `hobby=跑步`，用户说「我不喜欢跑步了，太累了」→ R7 negation，对此 fact 执行 soft_delete：
- ✅ `(self, hobby, "跑步", kind=negation, op=soft_delete, prior_value_id=<L3 UUID>)`

类似 case：「我不养猫了」+ L3 有 `pet.name="妙妙"` → 同样走 R7 negation soft_delete。

**路径 B — L3 中无对应 fact → hobby disclosure**：

L3 无相关 fact，用户首次说「我不喜欢跑步了」→ disclosure create，提示下游"曾经有过这个 hobby"：
- ✅ `(self, hobby, "跑步", kind=disclosure, op=create)`

**区分口诀**：先查 L3——L3 已有对应 fact？→ R7 negation soft_delete。L3 无对应 fact？→ hobby disclosure create。

此规则不覆盖无「了」的态度表达（仍走 R12 dislike）：
- 「我不喜欢跑步」「我不擅长做饭」→ `(self, dislike, "X")`

判断口诀：句子是**态度表达**（"我对 X 的感受"）还是**事实撤回**（"我之前说的 X 不对了"）？前者 → dislike disclosure，后者 → R7 negation。

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

{{ few_shot_examples }}

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
"""


class PromptBuilder:
    """Jinja2 renderer for the extraction prompt.

    Renders per §1 of the prompt design doc. The system message contains
    the full prompt including rules and few-shot examples. The user message
    is the rendered Run input block.

    Attributes:
        prompt_version: Locked to "1.0.2" — bump requires HUMAN approval.
        schema_version: Locked to "1.0.0" — must match schema doc MAJOR.MINOR.
    """

    def __init__(
        self,
        prompt_version: str = PROMPT_VERSION,
        schema_version: str = SCHEMA_VERSION,
    ):
        self._prompt_version = prompt_version
        self._schema_version = schema_version
        self._env = Environment(
            loader=BaseLoader(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._template = self._env.from_string(SYSTEM_TEMPLATE)

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    @property
    def schema_version(self) -> str:
        return self._schema_version

    def build(
        self,
        window: list[TurnInput],
        l3_snapshot: list[L3FactSnapshot],
        hints: list[Hint],
        extractor_run_id: UUID,
        model: str = MODEL,
    ) -> str:
        """Render the full extraction prompt.

        Args:
            window: Conversation turns to extract from (chronological).
            l3_snapshot: Known L3 facts for supersession/negation grounding.
            hints: Regex hints from fast encoder (advisory).
            extractor_run_id: UUID tying this run to the audit log.
            model: Model identifier echoed in the envelope.

        Returns:
            Rendered system prompt string.
        """
        turn_ids = [t.turn_id for t in window]

        rendered = self._template.render(
            few_shot_examples=FEW_SHOT_EXAMPLES,
            window=window,
            l3_snapshot=l3_snapshot,
            hints=hints,
            extractor_run_id=str(extractor_run_id),
            model=model,
            prompt_version=self._prompt_version,
            schema_version=self._schema_version,
        )

        logger.debug(
            "prompt_built",
            prompt_version=self._prompt_version,
            turn_count=len(window),
            turn_ids=turn_ids,
            l3_count=len(l3_snapshot),
            hint_count=len(hints),
            char_count=len(rendered),
        )

        return rendered
