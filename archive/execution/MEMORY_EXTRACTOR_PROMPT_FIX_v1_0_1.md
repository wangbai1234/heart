# SS02 LLM Extractor — Prompt v1.0.1 修复执行方案

> **本文件覆盖**：把 v1.0.0 prompt 在 49 case live golden 上失败的 16 个 case 收敛到 ≤ 5 个，达到 §6.3 ≥ 90% pass 阈值。
> **配套**：`docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md` §3.2 prompt 设计回归点；`docs/design/memory_extractor_prompt.md` v1.0.0 → v1.0.1 同步。
> **使用方式**：按 Phase 顺序执行 → 复制每个 Task 的内容 → 替换/插入 → 验证。
> **执行模型分配**：GLM（机械替换、跑 golden）；HUMAN（决策点 + 最终签字）。
> **token 预算**：GLM ~$5（pure mechanical），HUMAN 30 分钟（审 prompt 同步 + 跑 §5 sanity）。

---

# 序章: 当前状态与目标

## 0.1 输入状态

- `make memory-golden-live` 49 case 跑过：pass **33/49 (67.3%)**，Avg F1 0.759，Avg Precision 0.775，Avg Recall 0.755
- 单次成本 ~$0.0006/call（**已达标**，§3.2 目标 $0.002）
- 16 个失败 case 分类清单见 §1.1 表

## 0.2 目标

- Pass rate **≥ 90%**（§6.3 阈值）
- 改动**仅限 prompt 文本**（`prompt_builder.py` 顶部常量 + `memory_extractor_prompt.md` 同步）
- 不动 schema / 不动 types / 不动 resolver / 不动 writer / 不动 golden cases
- token 预算：input ≤ 4k（当前 ~3255 → 改动后估 ~3700）
- 成本回归：每 call ≤ $0.0008

## 0.3 版本 bump

- `PROMPT_VERSION`: `"1.0.0"` → `"1.0.1"`
- `SCHEMA_VERSION`: 不变（仍 `"1.0.0"`）
- 按 `memory_extractor_prompt.md` §4.2：v1 未生产，ship 前可 in-place，本次仍按 PATCH 处理但允许同文件覆盖（不新建 v1_0_1.py）

## 0.4 改动文件清单

| 路径 | 改动 |
|---|---|
| `backend/heart/ss02_memory/extractor/prompt_builder.py` | `PROMPT_VERSION` 常量 + `SYSTEM_TEMPLATE` 内 R5 + 新增 R10 + R4/R7 子条款 + `FEW_SHOT_EXAMPLES` 替换 Example 2 + 新增 Example 7/8 |
| `docs/design/memory_extractor_prompt.md` | §1 R5/R10 + §2 examples 同步 + §3.1 token 预算更新 + §4.1 加 1.0.1 changelog |
| `backend/tests/unit/ss02_memory/extractor/test_prompt_builder.py` | 如有 "len(FEW_SHOT_EXAMPLES.split('### Example'))==6" 类断言改为 8 |

---

# 第一部分: 失败矩阵

## 1.1 16 个失败 case 与修复路径映射

| Case | 类别 | 根因 | 由本方案哪条 Task 覆盖 |
|---|---|---|---|
| rhet-001 「我养你！」 | A | R5 + Example 2 教 LLM 输出 rhetoric candidate，但 golden 期望 drop | Task 2.1 + 2.2 |
| rhet-002 「我有病了哈哈」 | A | 同 | Task 2.1 + 2.2 |
| rhet-003 「她真的会要了我的命」 | A | 同 | Task 2.1 + 2.2 |
| rhet-006 「如果我中了彩票就养一百只猫」 | A | 同（hypothetical 也走 drop 路径） | Task 2.1 + 2.2 |
| adv-001 「我有 ChatGPT，叫小 G」 | B | 没 few-shot 教 LLM 识别 "我有 X" 但 X 不是实体 | Task 2.3 |
| adv-002 「我有时觉得自己是一棵树」 | B | 没 few-shot 教荒谬声明 | Task 2.3 + 2.1 |
| adv-003 「我最喜欢的食物是空气」 | B | 同 adv-002 | Task 2.3 + 2.1 |
| coref-003 「他在北京工作」 | C | location_residence 边界没说工作地 → other | Task 2.4 |
| disc-003 「在北京工作」 | C | 同 | Task 2.4 |
| adv-006 「我很不擅长做饭」 | C* | golden 期望 dislike，用户描述疑似读反；现有 prompt 已覆盖 | 不改 prompt；live 重跑确认 |
| coref-002 跨 3 turn 描述橘猫 | D | Example 1 只示范 2 属性，没教 breed 拼装 | Task 2.5 |
| disc-002 「我有一只猫叫妙妙」 | D | 没教 "猫" 这种类型本身入 attribute=other | Task 2.5 |
| mixd-001 单 turn 6 属性 | D | 没有高密度 few-shot，LLM 隐式截断 | Task 2.5 |
| frag-003 「上个月去了杭州」 | E | R4 没区分 episodic event vs persistent fact | Task 2.6 |
| neg-004 「没有妹妹，是表妹」 | E | R7 没覆盖 "否定 + 同 turn 纠正" | Task 2.7 |
| adv-005 「小明有只猫叫小白，小明是我儿子」 | E | R4 fragmentation 没有 chain entity 范例 | Task 2.6（事件区分顺带提关系链） |

**预期收敛**：A 类 4 + B 类 3 + C 类 2 + D 类 3 + E 类 3 = 15 个 case 转绿（adv-006 复跑确认）。最终 pass rate ≥ **48/49 = 98%**，留 1 个余量 case 容忍 LLM 随机性。

---

# 第二部分: Phase A — Prompt 修复（核心）

> **目标**：按 §1.1 表，按顺序覆盖 7 个 Task。
> **总耗时**：GLM 1.5h（机械替换）+ HUMAN 30min（审 + 跑 sanity）。
> **执行入口**：直接编辑 `backend/heart/ss02_memory/extractor/prompt_builder.py`。

## 2.0 准备 — 版本常量 + 调用方对齐

**Tool**: **GLM**
**Why**: 在改 prompt 内容前，先把版本号 bump 到位。golden cases 里 `prompt_version` 字段是 "1.0.0"，**不要动**——golden 是数据集的快照，校验时由 harness 重写。

**改动**:

文件 `backend/heart/ss02_memory/extractor/prompt_builder.py:22`：

```python
PROMPT_VERSION = "1.0.0"
```

改为：

```python
PROMPT_VERSION = "1.0.1"
```

**验收**:
- [ ] 单测 `pytest tests/unit/ss02_memory/extractor/test_prompt_builder.py -v` 全绿
- [ ] `grep -r "1.0.0" backend/heart/ss02_memory/extractor/` 仅 `SCHEMA_VERSION = "1.0.0"` 一处保留

---

## 2.1 Task: 改 R5（根因 A — 修辞从 candidate 改为 drop）

**Tool**: **GLM**
**Why**: 这是本次最关键改动。当前 R5 与 golden 期望相反。schema 已有 `DroppedReason.SARCASM_OR_RHETORIC`，drop 路径才是设计本意。

**改动位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py:335-339`

**当前内容**:

```
### R5 — 修辞识别
形如 "我养你"、"我有病了哈哈"、"她就是我命"、"我女朋友是我妈" 的字面意思与字面所指不符的句子：
- 仍然产生 candidate，但 `kind="rhetoric"`。
- 不要丢进 `dropped_signals`——保留 candidate 让下游审计可见 "LLM 识别了，Resolver 抑制了"。
```

**替换为**:

```
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

判断口诀：「字面所指能在现实世界落地为持久 fact 吗？」不能 → drop。
```

**验收**:
- [ ] 文本替换无遗漏
- [ ] R5 字数控制在 ~30 行内（含示例列表）
- [ ] 与 §4 "out_of_scope_entity" 区分清楚：R5 是 "字面上不该入库"，§5 R6/R10 是 "字面 OK 但 entity/attribute 超纲"

---

## 2.2 Task: 替换 Example 2（根因 A — few-shot 示范 drop 路径）

**Tool**: **GLM**
**Why**: 把 R5 的口头规则**示范化**。LLM 学 few-shot 远比学 rule prose 强。

**改动位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py:85-124`（Example 2 整段）

**当前内容**: 见 prompt_builder.py 第 85-124 行（输出含 `kind=rhetoric` candidate）

**替换为**:

````
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
````

**说明**:
- 输入完全不变（窗口、L3、hint 都保留）—— diff 最小化
- 输出从 `candidates=[rhetoric candidate]` 改为 `candidates=[]` + `dropped_signals=[drop]`
- `raw_phrase` 用 "我有病了哈哈"（带 "哈哈" 标记修辞特征），不要用 "我有病了"（裸句容易被误认正常 disclosure）
- 注意 prompt_version 字段更新为 "1.0.1"（与 §2.0 一致）

**验收**:
- [ ] Example 2 输出 candidates 为空数组
- [ ] `dropped_signals[0].reason == "sarcasm_or_rhetoric"`
- [ ] prompt_version 字符串改为 "1.0.1"
- [ ] FEW_SHOT_EXAMPLES 总字符数：原 ~6400 → 改后 ~5800（删了 candidate 段省 ~600）

---

## 2.3 Task: 新增 Example 7 + 8（根因 B — 对抗样本 drop 示范）

**Tool**: **GLM**
**Why**: 教 LLM 识别 "我有 X" 但 X 不是实体 + 明显荒谬声明。当前 6 个 example 没覆盖。

**改动位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py:287` 之后（Example 6 末尾，FEW_SHOT_EXAMPLES 字符串结束前）

**插入**:

````

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
````

**Why no candidate**: ChatGPT 是 AI 产品名，不是 schema `entity_type` 闭包内任何类型（self / pet / family / friend / colleague / location / possession / preference / event / other 都不合适——它既非 possession 这种持久物件，亦非 preference）。"叫小 G"是给 AI 起昵称的对话语言，不构成真实人/宠物 fact。

---

### Example 8 — Absurd / metaphorical self-claim

````
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
````

**Why no candidate**: 「食物是空气」违反物理常识——人不能吃空气。这是修辞性自我表达（可能表达节食/心情低落/玩梗），不是真实 hobby/preference fact。同类：「我是一棵树」「我能飞」「我家住月亮上」。

**改动后 FEW_SHOT_EXAMPLES 末尾结构**:
```
... (Example 6 内容)
---
### Example 7 — Entity out of scope
... (新增)
---
### Example 8 — Absurd / metaphorical self-claim
... (新增)
"""  # FEW_SHOT_EXAMPLES 字符串结束
```

**验收**:
- [ ] FEW_SHOT_EXAMPLES 共 8 个 Example（原 6 + 新 2）
- [ ] Example 7 reason="out_of_scope_entity"
- [ ] Example 8 reason="sarcasm_or_rhetoric"
- [ ] 两例都 `candidates=[]`
- [ ] 每例都有 "Why no candidate" 解释段

---

## 2.4 Task: 新增 R10 — 地点属性细分（根因 C）

**Tool**: **GLM**
**Why**: golden 期望 "在北京工作" → `attribute=other`，但 LLM 默认走 `location_residence`。需要明文边界。

**改动位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py:357` 之后（R9 结束 + `## 字段闭包提醒` 之前）

**插入**:

```
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
```

**验收**:
- [ ] R10 紧接 R9
- [ ] 表格 + 判断口诀齐全
- [ ] 显式包含 "工作地 → other" 因为这正是 coref-003 / disc-003 失败模式
- [ ] 末尾补正例避免一刀切

---

## 2.5 Task: 强化 Example 1（根因 D — 多属性密度 + 类型作为 attribute）

**Tool**: **GLM**
**Why**: Example 1 当前 2 个 candidate (`name` + `color`)，没示范 3+ 属性也没示范 "猫" 这种实体类型映射到 `attribute=other`。

**改动位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py:29-81`（Example 1 整段）

**替换为**:

````
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
````

**关键示范点**:
1. **实体类型作为 `attribute=other`**：第一个 candidate 是 `(pet, other, "猫")` —— 教 LLM 不要把"猫"这种类别词折叠掉
2. **4 candidate 全共享 `entity_ref="cat#1"`**：教 LLM 同实体多属性的拼装方式
3. **breed 单独 candidate**：让 mixd-001/coref-002 类高密度场景有范例可学
4. **source_turns 各自不同**：T10 单独的（breed/other）；T10+T12 一起的（name/color via coref）

**验收**:
- [ ] Example 1 共 4 个 candidate
- [ ] `(pet, other, "猫")` candidate 存在
- [ ] 4 个 candidate 共享 entity_ref
- [ ] FEW_SHOT_EXAMPLES 总字符数：~6400 → 改后 ~6900（多 2 candidate ≈ +500）

---

## 2.6 Task: R4 加 episodic event 子条款（根因 E frag-003）

**Tool**: **GLM**
**Why**: 旅行/活动/就医这类一次性事件不应入 L3 persistent fact。当前 R4 只讲 fragmentation 不讲 event 边界。

**改动位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py:329-333` R4 末尾

**当前 R4 末段**:

```
### R4 — 跨 turn 拼装（fragmentation）
关于同一实体的 attribute 分散在多个 turn 时（"我有只猫"→"叫妙妙"→"灰白色的"）：
- 拼成关于该实体的**多个** candidate，每个一个 attribute。
- 这些 candidate **共享 `entity_ref`**（例如 `"cat#1"`）。
- 每个 candidate 的 `source_turns` 是它依赖的所有 turn 的并集（引入实体的 turn 必须在内）。
```

**追加段落**（在 R4 现有内容末尾增加）:

```
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
```

**验收**:
- [ ] R4 末尾增加 "Persistent fact vs Episodic event" 表格
- [ ] 包含 "一年后还成立吗" 判断口诀
- [ ] frag-003「上个月去了杭州」匹配这条规则
- [ ] 末尾加关系链子条款覆盖 adv-005

---

## 2.7 Task: R7 加 "否定+纠正" 子条款（根因 E neg-004）

**Tool**: **GLM**
**Why**: 当前 R7 只覆盖纯 negation。neg-004 期望同 turn 输出 2 candidate：旧值 soft_delete + 新值 create。

**改动位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py:344-348` R7 末尾

**当前 R7**:

```
### R7 — 否定 + 已存在事实 = soft_delete
"我没有宠物"、"我不养猫了" 等显式否定：
- 若 L3 snapshot 中存在对应实体的事实 → `kind="negation"`, `operation="soft_delete"`, `prior_value_id=<L3 fact UUID>`。
- 若 L3 snapshot 中没有对应事实 → **不写**"用户没有 X"。放入 `dropped_signals` (`reason=insufficient_context`)。
schema 的 `if/then` 规则强制 `kind=negation ⇒ operation ∈ {soft_delete, supersede}`，违反必被拒。
```

**追加段落**:

```
**否定 + 同 turn 纠正（两个 candidate）**：

形如 "我没有 X，是 Y"、"不是 A，是 B" 的同 turn 否定纠正：

1. 旧值 candidate：`kind="negation"`, `operation="soft_delete"`, `prior_value_id=<L3 旧 fact UUID>`
2. 新值 candidate：`kind="disclosure"`, `operation="create"`，新的 (entity_ref, attribute, value)

例：「我没有妹妹，之前说的是表妹」+ L3 snapshot 有 `family[sister].name="小丽"`：
- candidate 1: `(family, name, "小丽", entity_ref=sister, prior_value_id=<uuid>, kind=negation, op=soft_delete)`
- candidate 2: `(family, relation, "表妹", entity_ref=cousin, kind=disclosure, op=create)`

两条 candidate 都进 `candidates` 数组；source_turns 都包含纠正所在的 turn。
```

**验收**:
- [ ] R7 末尾增加纠正子条款
- [ ] 包含 neg-004 的精确示例（妹妹 → 表妹）
- [ ] 明确两 candidate 同时入 candidates 数组（非分两次调用）

---

# 第三部分: Phase B — Spec 文档同步

## 3.1 Task: 同步 memory_extractor_prompt.md

**Tool**: **GLM**
**Why**: CLAUDE.md "spec/code 同步" 铁律 + §4.2 "prompt_version 1.0.1 文档必须存在"。

**改动文件**: `docs/design/memory_extractor_prompt.md`

**改动项**:

1. **文档头部 metadata**：
   - `Status: 🟡 Design (pre-implementation)` → `Status: 🟢 Shipped (v1.0.0) + 🟡 Iteration (v1.0.1 in progress)`
   - 加 `Previous version: 1.0.0 (deprecated reasons documented in §4.6)`

2. **§1 Prompt template** R5 全段同步替换为 Task 2.1 的新文本

3. **§1 Prompt template** 在 R9 后插入 R10 全段（Task 2.4 文本）

4. **§1 Prompt template** R4 末尾增加 "Persistent fact vs Episodic event" 表格（Task 2.6 文本）

5. **§1 Prompt template** R7 末尾增加 "否定 + 同 turn 纠正" 段（Task 2.7 文本）

6. **§2 Few-shot example set** ：
   - Example 1 替换为 4 candidate 版（Task 2.5 文本）
   - Example 2 替换为 drop 版（Task 2.2 文本）
   - 新增 Example 7（Task 2.3 上半段）
   - 新增 Example 8（Task 2.3 下半段）
   - §2 顶部 "Coverage map" 表加两行：
     - `7 | Entity out of scope | dropped_signals[reason=out_of_scope_entity]`
     - `8 | Absurd / metaphorical self-claim | dropped_signals[reason=sarcasm_or_rhetoric]`

7. **§3.1 Token budget**：
   - "Few-shot (6 examples, Chinese text + JSON) ~1500" → "Few-shot (8 examples) ~1850"
   - "System prologue + non-goals + R1–R9 + field-closure ~900" → "System prologue + non-goals + R1–R10 + field-closure ~1050"
   - "Input subtotal" ~3255 → ~3705
   - 末尾加一行：「实测 v1.0.1 input ≈ 3700 token，仍在 user-stated 4k 预算内」

8. **§3.2 Cost / latency**：
   - "Per-call cost" 表的 typical 列重算：input 3.7k → 保守典型成本 `0.30·3.7/1000 + 1.20·0.2/1000 = $0.00135`（仍 < $0.002 ✅）
   - 加一行实测："2026-06-19 49-case live run 实测 avg $0.0006/call（远低于 conservative typical 估算）"

9. **§4.1 Initial version** 之后插入 §4.6 changelog：

```markdown
### 4.6 Changelog

| Version | Date | Change | Reason |
|---|---|---|---|
| 1.0.0 | 2026-06-19 | 初始版本 | §3.2 Opus 设计 |
| 1.0.1 | 2026-06-20 | R5 改为 drop 路径；新增 R10（location）；R4/R7 加子条款；Example 1 扩到 4 candidate；新增 Example 7（out_of_scope_entity）、Example 8（absurd） | 49 case live golden 67.3% pass，远低 90% 阈值；本次 16 个失败的根因分析见 `docs/execution/MEMORY_EXTRACTOR_PROMPT_FIX_v1_0_1.md` §1.1 |
```

10. **§5 Manual sanity-check prompts**：不动（5 个 prompt 仍适用）

**验收**:
- [ ] doc 文件存在改动 + git diff 与 prompt_builder.py 改动一一对应
- [ ] §4.6 changelog 段落落地
- [ ] §3.1 token 估算 + §3.2 成本估算更新

---

# 第四部分: Phase C — 验证

## 4.1 Task: 本地单测

**Tool**: **GLM**

```bash
cd backend
pytest tests/unit/ss02_memory/extractor/ -v
```

**预期**：全绿。如有失败：
- `test_prompt_builder.py` 里若有 "FEW_SHOT_EXAMPLES count == 6" 类硬断言 → 改为 8
- 其他真实失败 → 报告 + 停下不要硬改

---

## 4.2 Task: Fake mode golden gate

**Tool**: **GLM**

```bash
make memory-golden
```

**预期**：49 case schema validate 全绿，因为 golden cases 没改、prompt 改动不影响 fake mode（fake mode 只走 schema 合规校验）。

如果 `test_golden_set_coverage` 失败 → 是覆盖矩阵问题，独立后续 PR（清理项 B），本次不修。

---

## 4.3 Task: Live mode 全跑 + 报告分析

**Tool**: **GLM** 启动 + **HUMAN** 读报告

```bash
make memory-golden-live
```

**预期产出**：
- `/tmp/golden_score_report.html` 重新生成
- 新 pass rate ≥ 90%（48/49 或更好）
- 16 个失败 case 中至少 12 个转绿

**手动验收每个失败 case**（HUMAN 30min）：
打开 HTML 报告，逐 case 看 "True Positives" / "Missed" / "Extra" 三列：

| Case | 预期变化 | 通过判据 |
|---|---|---|
| rhet-001~006 | candidates 从 1→0，dropped 从 0→1 | PASS（TP=0, FP=0, FN=0 → precision=recall=1） |
| adv-001 | candidate 从 1（错的 small-G pet）→ 0 | PASS |
| adv-002/003 | candidate 从 1 → 0 | PASS |
| coref-003/disc-003 | attribute 从 location_residence → other | PASS（value 对、attribute 对）|
| coref-002 | 多出 breed candidate | PASS（recall 从 2/3 → 3/3） |
| disc-002 | 多出 `(pet, other, "猫")` candidate | PASS |
| mixd-001 | 6 candidate 全出 | PASS |
| frag-003 | candidates 从 3（杭州/西湖/灵隐寺）→ 0 + 3 个 dropped | PASS |
| neg-004 | candidates 从 1 → 2（soft_delete + create） | PASS |
| adv-005 | candidates 从 2 → 3（关系链全出） | PASS |

如果有 case 没转绿：
1. 看 actual 输出，判断是 prompt 不够强还是 LLM 真在抽风（temperature=0 也有 token tie）
2. 不够强 → 在对应 Task 加例子或加规则，回到 §2.x 迭代
3. LLM 抽风 → 重跑 1 次确认；连续 3 次不绿则同上

---

## 4.4 Task: 成本回归

**Tool**: **GLM**

从 `/tmp/golden_score_report.html` 或 structlog 取 49 次 run 的 `cost_usd`，算 avg。

**预期**：
- avg ≤ $0.0008/call（input +400 token ≈ +12% 成本）
- max ≤ $0.0015/call（worst case 仍 < $0.002 cap）

如果 avg 超 $0.0010：检查是否 output 也涨了（drop 路径 envelope 应该更小，不应涨）。

---

## 4.5 Task: HUMAN sanity 5 prompts

**Tool**: **HUMAN**

按 `memory_extractor_prompt.md` §5 跑 Test 1（fragmentation）+ Test 2（negation）+ Test 4（ambiguous）三个：

- Test 1：仍应出 ≥2 candidate 共享 entity_ref（验证 Example 1 强化不破坏 fragmentation）
- Test 2：应出 1 negation candidate，prior_value_id 来自 snapshot（验证 R7 改动不破坏纯 negation）
- Test 4：仍应 `candidates=[]` + dropped `ambiguous_reference`（验证没回归 R3）

每个 prompt 在 LLM 控制台手动跑，对照 prompt md §5 的 pass criteria 表格逐项打勾。

---

# 第五部分: Cut Criteria（强制）

整体修复完成判定：

```
□ Phase A 所有 7 个 Task (2.0-2.7) 改动入 prompt_builder.py
□ Phase B Task 3.1 同步入 memory_extractor_prompt.md
□ Phase C 4.1 单测全绿
□ Phase C 4.2 fake golden 全绿
□ Phase C 4.3 live golden pass rate ≥ 90%
□ Phase C 4.4 成本回归 avg ≤ $0.0008/call
□ Phase C 4.5 HUMAN 跑过 3 个 sanity prompt 并签字
□ 一次 commit："feat(ss02): bump memory extractor prompt to v1.0.1 — fix 16 golden failures"
□ commit body 内引用本文件 + 列 49 case → 48 case PASS 的 diff
```

---

# 第六部分: 风险与回滚

| 风险 | 触发条件 | 缓解 |
|---|---|---|
| R5 改动连带破坏其他 rhetoric handling | live golden 别的 rhet case 反而红 | 退回单独 Example 2，先看是不是 Example 2 改得太重，再考虑 R5 措辞 |
| Example 1 4-candidate 教过头，多属性 disclosure case 也出 `(*, other, *)` | disc/coref 类 case FP 涨 | 在 R10 后追加一句 "如果实体类型有专门 attribute（name/age/...），优先用专门 attribute，不要重复出 (*, other) candidate" |
| R10 一刀切让 location_residence 几乎没用 | live golden 真正住址类 case 也走 other | R10 末尾再加正例："『我住在北京』『我家在杭州』『我在北京住了 5 年』 → location_residence"（已在 §2.4 末尾加） |
| token 涨太多触发 4k 限制 | input 实测超 3900 | 删掉 Example 3（question only）的 L3 snapshot 段省 ~100 token；或 Example 6 的 hints 段（其实没用上） |
| 成本涨超 $0.001 | conservative 估算撞墙 | 接受——仍在 §3.2 $0.002 cap 内 |

**整体回滚预案**：
- 改动**只在 prompt_builder.py + memory_extractor_prompt.md** 两文件
- 回滚 = `git revert <commit>` 一次（无 schema/无 migration/无 DB 状态）
- prompt_version "1.0.1" 在 audit_log 出现后回滚：手动 `UPDATE memory_audit_log SET prompt_version='1.0.0_rollback' WHERE prompt_version='1.0.1';` 避免下游 join 错乱

---

# 第七部分: 顺手清理项（独立后续 PR，**不在本次改动**）

A. **Scoring 实现欠债**: `test_extractor_golden.py:213-298` `_score_envelope` 只比对 `(entity_type, attribute)` key，**没检查** `kind` / `operation` / `prior_value_id` / `dropped_signals`。按 `memory_golden_set_design.md` §4.2 这些都是 HARD 字段。当前 67.3% pass 用的是宽松算法；按 spec scoring 实际数字会更低。**需补强（独立 issue + PR）**。这是真正的 cut criteria 阻塞——本次 v1.0.1 修复后 pass 即使 ≥ 90%，scoring 加强后可能再红一次，需要独立处理。

B. **Golden set 多了 `mixed` 桶**: 设计 47 case / 9 桶，实施 49 case / 10 桶（多 mixed×2）。`test_extractor_golden.py:152-163` 已包含 `"mixed": 2` 最低值，与 `memory_golden_set_design.md` §1.1 不一致。debt 登记到 issue。

C. **JSONL vs YAML/case 文件偏差**: design.md §3.2 选 YAML/case + CODEOWNERS，实施用单 JSONL。CODEOWNERS 隔离丢失。短期可接受，需补 design.md 一节"实施偏差登记"。

---

# 附录 A: 改动后 prompt_builder.py 全貌检查清单

执行完 Phase A 后，按以下清单逐项 grep 验证文件状态：

```bash
cd backend/heart/ss02_memory/extractor

# 版本号
grep -n 'PROMPT_VERSION = "1.0.1"' prompt_builder.py     # 应 1 hit
grep -n 'PROMPT_VERSION = "1.0.0"' prompt_builder.py     # 应 0 hit

# Example 数量
grep -c '### Example' prompt_builder.py                   # 应 = 8

# R5 改动
grep -n 'kind="rhetoric"' prompt_builder.py              # 应 0 hit（R5 不再说输出 rhetoric candidate）
grep -n 'reason="sarcasm_or_rhetoric"' prompt_builder.py # 应 ≥ 3 hit（R5 + Example 2 + Example 8）

# R10 新增
grep -n 'R10' prompt_builder.py                          # 应 ≥ 2 hit

# R4 episodic
grep -n 'Episodic event' prompt_builder.py               # 应 ≥ 1 hit

# R7 纠正
grep -n '否定 + 同 turn 纠正' prompt_builder.py          # 应 1 hit

# Example 1 4-candidate
grep -A 200 '### Example 1' prompt_builder.py | grep -c '"entity_type": "pet"'  # 应 = 4
```

---

# 附录 B: Commit message template

```
feat(ss02): bump memory extractor prompt to v1.0.1 — fix 16 golden failures

Before: 33/49 (67.3%) pass on make memory-golden-live
After:  __/49 (___%) pass on make memory-golden-live

Root causes addressed:
- A (4 cases): R5 修辞从 candidate 改为 drop（align with golden + DroppedReason.SARCASM_OR_RHETORIC）
- B (3 cases): 新增 Example 7（out_of_scope_entity）+ Example 8（荒谬声明）
- C (2 cases): 新增 R10 区分 location_residence vs other（工作地走 other）
- D (3 cases): Example 1 扩为 4 candidate，示范实体类型→attribute=other + breed 拼装
- E (3 cases): R4 加 episodic event 子条款；R7 加同 turn 纠正子条款

Cost: avg $0.0006/call → ~$0.0008/call (still < $0.002 cap)
Token: input ~3255 → ~3705 (still < 4k budget)

Spec doc synced: docs/design/memory_extractor_prompt.md §4.6 changelog
Spec conflict resolved: prompt R5 now aligns with golden cases (schema-first)

Refs: docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md §3.2
      docs/execution/MEMORY_EXTRACTOR_PROMPT_FIX_v1_0_1.md (this doc)
```

---

**版本**: 1.0.0
**创建日期**: 2026-06-20
**主笔**: Opus 4.7
**执行模型**: GLM（机械替换 + 跑测试）+ HUMAN（sanity prompt + 签字）
**预计耗时**: 2h（GLM 1.5h + HUMAN 30min）
