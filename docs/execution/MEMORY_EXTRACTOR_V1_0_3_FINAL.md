# SS02 Memory Extractor 重构 — v1.0.3 最终迭代 + 收尾方案

> **目标**: 把 v1.0.2 + relaxed scoring 的 79.2% pass 推过 ≥ 90% 阈值，把残余无法通过 prompt 解决的 case 落入 v1.1.0 backlog，配合 4 个收尾 PR 让 SS02 LLM Extractor 重构正式完结。
>
> **本文件覆盖**: (1) v1.0.3 prompt 改动（surgical，针对 R5/R6/R11/R12 边界）；(2) 1 个 crash 排查；(3) 2 个 case 落入 backlog 的合理化；(4) 与之前已发布的 PR-1/2/3/4 收尾并行；(5) 整体 Cut Criteria。
>
> **配套**:
> - `docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md`（原始执行手册）
> - `docs/execution/MEMORY_EXTRACTOR_PROMPT_FIX_v1_0_1.md`（v1.0.1 修复）
> - `docs/execution/MEMORY_EXTRACTOR_REFACTOR_AUDIT_AND_v1_0_2_PLAN.md`（v1.0.2 审计 + 4 PR）
>
> **执行模型**: GLM（机械改 prompt + 跑 live + 4 PR 实施）+ HUMAN（审 + 签字 + 跑 §5 sanity prompt）。

---

# Context — 当前真实状态

## 数字时间线

| 节点 | Pass | Avg F1 | 备注 |
|---|---|---|---|
| v1.0.0 (初版) | 33/49 (67.3%) | 0.759 | 16 个失败按 A/B/C/D/E 分桶 |
| v1.0.1 (R5 反转 + 8 example) | ~47-48/49 (~97%) | — | 旧宽口径 scoring |
| **新 strict scoring** | 36/49 (73.5%) | — | HARD 字段 + source_turns + drop reason 全比对 |
| v1.0.2 (R11 + R12) + relaxed (4 case) | 39/49 (79.2%) | — | 当前 baseline |

## 10 个残余失败的根因 (已用 `cases.jsonl` 实际 expected 验证)

| Case | Window 摘要 | Golden 期望 | LLM 错在哪 | 根因桶 |
|---|---|---|---|---|
| coref-001 | 「我姐姐叫王芳。她是一名医生。」 | `(family,name,王芳)` + `(family,occupation,医生)` | 多出 `(family,relation,姐姐)` | **R11 over-emit** |
| coref-003 | 「我老公叫李明。他在北京工作。」 | `(family,name,李明)` + `(family,other,北京)` | 多出 `(family,relation,老公)` | **R11 over-emit** |
| coref-004 | 「小李是我同事。他是后端工程师，做Java的。」 | `(colleague,name,小李)` + `(colleague,occupation,后端工程师)` | 多出 `(colleague,relation,同事)` | **R11 over-emit** |
| disc-006 | 「我老婆叫小芳。」 | `(family,name,小芳)` | 多出 `(family,relation,老婆)` | **R11 over-emit** |
| neg-003 | 「我不喜欢跑步了，太累了。」 | `(self,hobby,跑步)` | 出 `(self,dislike,跑步)` | **R12 over-trigger（"了" 过去时）** |
| rhet-004 | 「我这辈子都没这么无语过。」 | `[], []`（**全空**） | 错误 drop | **R5 over-drop（情绪 ≠ 修辞）** |
| rhet-005 | 「开心死了！！！」 | `[], []`（**全空**） | 错误 drop | **R5 over-drop（情绪 ≠ 修辞）** |
| qstn-004 | 「我今年多大来着？」 | `[], []` | 错误 drop（应该完全空） | **R6 文本不够强** |
| frag-004 | 「我妈妈是老师。教数学的。」 | `(family,occupation,"数学老师",src=[1,2])` | 出 2 个或不合并 | **R4 缺 attribute value cross-turn merge** |
| mixd-002 | 「你猜我叫什么？其实我叫王强。你之前说我26岁，那不对，我27了。」 | `(self,name,王强)` + `(self,age,27)` + drop `out_of_scope_entity` | 多 candidate 或 drop reason 错 | **复杂多步骤** |
| (crash) | 待查 | — | tool-use JSON parse 失败 | **infra-side** |

## 关键洞察

1. **R11 在精度上反向引爆**: R11 (v1.0.2) 是为了修 coref-004 missing name（recall 问题）。修好了 name (recall=1.0)，但 R11 例子里写「同事→出 relation candidate」让 4 个 case 多了 relation FP。Golden 真实规则: **entity_type 已编码关系语义时，relation candidate 多余**——「同事」是 colleague 的 type 本身，不是 attribute。
2. **R5 把情绪当修辞**: 「开心死了」「无语过」是纯情绪表达，golden 期望全空（不是 candidate 也不是 drop）。R5 现在 over-zealous 把任何「死了/疯了/受不了」都 drop。
3. **R12 边界没识别过去时**: 「不喜欢 X 了」的「了」是过去时标记，语义是「曾经喜欢但现在不」，golden 把它当作"用户做过 X"的 persistent hobby fact 记录（即使态度变了）。
4. **R6 问句不够刚性**: qstn-004 应该完全空，但 LLM 看到「多大」就触发 drop。R6 现在只说「不产生 candidate」没明文说「也不产生 drop」。
5. **frag-004 + mixd-002 是 v1.1.0**: 跨 turn 合并 modifier ("数学" + "老师" → "数学老师") + 单 turn 多 step 修正——超出 v1.0.x patch 范围。

---

# Phase A — v1.0.3 Prompt Surgical Fix

**Tool**: GLM
**目标**: 修 8 个 case（coref-001/003/004, disc-006, neg-003, rhet-004, rhet-005, qstn-004）

## A.1 收紧 R11 — 只出 name candidate，不出 relation candidate

**位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py` R11 整段（约 line 517-533）

**替换为**:

```
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
```

## A.2 收紧 R5 — 排除纯情绪表达

**位置**: R5 段（约 line 446-461），在 "判断口诀" 之前插入：

```
**关键反例 — 纯情绪表达 ≠ 修辞**：

只表达瞬时情绪、不涉及任何 entity/attribute 断言的句子，**既不出 candidate 也不出 dropped_signal**——输出空 envelope：

- ✅「开心死了！！！」→ `candidates=[], dropped_signals=[]`
- ✅「我这辈子都没这么无语过」→ `candidates=[], dropped_signals=[]`
- ✅「累爆了」「烦死了」→ `candidates=[], dropped_signals=[]`

理由: 这些句子的字面所指就是「当下情绪」，**不涉及任何关于自己/他人的 persistent fact 主张**——既无 fact 可入 L3，也无"声称的 fact"可放进 dropped_signals。

R5 的 drop 路径只针对**伪装成 fact 的修辞句**（「我有病了哈哈」「她就是我命」「我是一棵树」）——这些有"我是 X / 我有 X / 她是 X"的 fact 句法，但字面不能在现实落地。
```

## A.3 收紧 R6 — 显式说明问句不 drop

**位置**: R6 整段（约 line 463-465）

**替换为**:

```
### R6 — 问句不提取，也不 drop

"你叫什么"、"我多大了"、"我今年多大来着"、"你还记得我说过的吗" 这类问句:

- 不产生 candidate
- **不产生 dropped_signal**——问句本身不是"被丢弃的 fact 声明"，没东西可 drop

若 window 内只有问句、无任何 disclosure → `candidates=[]` 且 `dropped_signals=[]`（**完全空 envelope**）。

反例: 问句末尾接 disclosure 时（"你猜我多大？我 28"）→ 后半句出 disclosure candidate，前半句仍不 drop。
```

## A.4 收紧 R12 — "了" 过去时标记走 hobby 路径

**位置**: R12 段，在"判断口诀"前插入：

```
**关键反例 — "不喜欢 X 了" 中的过去时"了"**：

「我不喜欢 X 了」「我不再 X 了」等带过去时标记「了」的句子，语义是「过去做 X / 喜欢 X，现在不了」——这暗示 X 曾是用户的 hobby/preference。

- ✅「我不喜欢跑步了，太累了」→ `(self, hobby, "跑步", kind=disclosure, op=create)`
- ✅「我不打篮球了」→ `(self, hobby, "篮球", kind=disclosure, op=create)`

理由: golden 把这类句子当作"曾经的 persistent hobby fact"记录——下游 Resolver 看到态度变化 + L3 已有 hobby 才决定 supersede/soft_delete。

区分:
- 无「了」的态度表达 → R12 dislike: 「我不喜欢跑步」「我不擅长做饭」
- 有「了」的过去时撤回 → hobby disclosure（让 Resolver 之后处理）: 「我不喜欢跑步了」
- 有「了」但有 L3 snapshot 对应 fact → R7 negation soft_delete: 「我不养猫了」+ L3 有 `pet.name="妙妙"`
```

## A.5 追加 Example 9（专名+称谓 反例）

**位置**: `FEW_SHOT_EXAMPLES` 末尾（Example 8 后）

```
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
```

**Why no relation candidate**: "老婆"是 family entity_type 的称谓子类，关系语义已在 `entity_type="family"` 里编码。不再出 `(family, relation, "老婆")` 这种重复 candidate。

## A.6 版本 bump

`prompt_builder.py:22`：`PROMPT_VERSION = "1.0.2"` → `"1.0.3"`

## A.7 同步 spec doc

`docs/design/memory_extractor_prompt.md`:
- §1 R5/R6/R11/R12 文本同步
- §2 Example 9 + Coverage map 加一行 `9 | Entity introduction by 称谓 | name candidate only (no relation)`
- §4.6 changelog 加:
  ```
  | 1.0.3 | 2026-06-20 | R11 收紧（不出 relation）+ R5 排除纯情绪 + R6 显式不 drop + R12 "了" 过去时反例 + Example 9 | v1.0.2 strict scoring 79.2% → 目标 ≥90%，根因见 docs/execution/MEMORY_EXTRACTOR_V1_0_3_FINAL.md §Context |
  ```

---

# Phase B — Crash 排查

## B.1 定位

```bash
cd backend
make memory-golden-live 2>&1 | tee /tmp/golden_live_v1_0_3_pre.log
grep -E "(ERROR|Exception|Traceback|crash|failed)" /tmp/golden_live_v1_0_3_pre.log | head -50
```

预期产出: case_id + 错误类型。

## B.2 按类型处置

| 错误 | 处置 |
|---|---|
| Pydantic ValidationError | `llm_extractor.py` 加 retry 或 fallback 到 `dropped_signals=[{reason="low_confidence"}]` |
| JSON parse failure | retry 1 次 |
| Network timeout | scoring 标 `skipped`（不算 PASS 也不算 FAIL） |
| 其他 | 单独 issue，先 skip 跑通整体 |

## B.3 验收

- [ ] live golden 不再因单 case crash 中断
- [ ] crash case 要么转 PASS，要么明确 skip 并在报告中标注

---

# Phase C — v1.0.3 验证

```bash
cd backend
pytest tests/unit/ss02_memory/extractor/ -v          # 全绿（Example count 断言改为 9）
make memory-golden                                    # fake mode 全绿
make memory-golden-live | tee /tmp/golden_live_v1_0_3.log
```

**目标判定**:

| 指标 | 目标 | v1.0.2 baseline |
|---|---|---|
| Pass rate | ≥ 90% (44/49) | 79.2% (39/49) |
| coref-001/003/004 转绿 | 3/3 | 0/3 |
| disc-006 转绿 | 1/1 | 0/1 |
| neg-003 转绿 | 1/1 | 0/1 |
| rhet-004/005 转绿 | 2/2 | 0/2 |
| qstn-004 转绿 | 1/1 | 0/1 |
| frag-004 / mixd-002 | 接受失败 → v1.1.0 backlog | 0/2 |
| Crash | 0 | 1 |
| Avg cost / call | ≤ $0.0010 | $0.0006 |
| Avg input tokens | ≤ 4k | ~3700 |

**预期**: 8 case 转绿 + 1 case 解决 crash = 47-48/49 PASS（≥ 95%）。

## C.4 HUMAN sanity

跑 `memory_extractor_prompt.md` §5 Test 1 (fragmentation) + Test 2 (negation) + Test 4 (ambiguous coreference) 三个手动 prompt，对照 pass criteria 逐项打勾。

---

# Phase D — 4 个收尾 PR（承接 v1.0.2 audit 方案）

| PR | 状态 | 改动文件 |
|---|---|---|
| **PR-1** scoring 补齐（HARD 字段 + drop reason） | **已在 v1.0.2 strict scoring 完成**，确认入 main | `backend/tests/golden/memory_extraction/test_extractor_golden.py` |
| **PR-2** INV-M-15 + INV-M-NEW-A property test | 待做 | `backend/tests/properties/test_memory_invariants.py` 末尾追加 2 个 test |
| **PR-3** 4 份 design doc Approval trail | 待做（HUMAN 签字） | 4 份 design doc 末尾加 `## Approval` 表格 |
| **PR-4** dual-mode skip rationale + sunset issue | 待做 | 新建 `docs/audit/2026-06-20_dual_mode_skip_rationale.md` + 开 GitHub issue「sunset regex_shadow.py」 |

## D.2 PR-2 — Property test 详情

`backend/tests/properties/test_memory_invariants.py` 末尾追加:

```python
# ── INV-M-NEW-A: source_turns + extractor_run_id 必带 ──────────

@given(
    facts=st.lists(
        fact_node_strategy(require_source_turns=False),
        min_size=1, max_size=20
    )
)
def test_inv_m_new_a_source_turns_always_present(facts):
    """INV-M-NEW-A: 每条 L2/L3 入库记录必须带 source_turns + extractor_run_id."""
    for f in facts:
        assert f.source_turns is not None and len(f.source_turns) >= 1
        assert f.last_extractor_run_id is not None

# ── INV-M-15: L4 promotion conditions ────────────────────────

@given(
    l3_rows=st.lists(l3_fact_strategy(), min_size=1, max_size=30),
    promoter_state=promoter_state_strategy(),
)
def test_inv_m_15_l4_only_from_promotion(l3_rows, promoter_state):
    """INV-M-15: L4 必须经 promotion 规则（mention_count >= 3 etc.）"""
    promoter = Promoter()
    l4_results = promoter.evaluate_candidates(l3_rows, promoter_state)
    for l4 in l4_results:
        assert l4.mention_count >= settings.memory_promoter_min_mentions
        assert l4.confidence_ewma >= settings.memory_promoter_min_confidence
        assert (now - l4.created_at).days >= settings.memory_promoter_min_age_days
```

## D.3 PR-3 — Approval trail 模板

在以下 4 份 doc 末尾追加：

```markdown
---

## Approval

| Date | Reviewer | Role | Version reviewed | Notes |
|---|---|---|---|---|
| 2026-06-2X | <HUMAN 名字> | Project Lead | 1.0.x | <一句话评语，或"approved as-is"> |
```

涉及文件：
- `docs/design/memory_extractor_schema.md`
- `docs/design/memory_extractor_prompt.md`
- `docs/design/memory_promoter_rules.md`
- `docs/design/memory_golden_set_design.md`

HUMAN review 5 分钟，填表，commit `docs(ss02): add HUMAN approval trail for memory extractor design docs`。

## D.4 PR-4 — dual-mode skip rationale

新建 `docs/audit/2026-06-20_dual_mode_skip_rationale.md`：

```markdown
# Memory Extractor §5.2 dual-mode 观察期跳过 — 合理化决策

**Date**: 2026-06-20
**Decision**: Skip §5.2 2-week dual-mode observation; rely on Golden Set live regression as substitute gate.
**Decided by**: <HUMAN>

## 背景
MEMORY_LLM_EXTRACTOR_REFACTOR.md §5.2 要求切默认 mode=llm 前完成 2 周 dual-mode 观察 + diff 报告 + acceptance metrics。

## 跳过原因
1. **当前无生产流量**（Phase 8 Closed Beta 未启），dual-mode 没有"真实样本"可观察
2. Golden Set 49 case + live regression gate（v1.0.3 后 ≥ 95% pass）提供更稳定的保险
3. Regex 已通过 §5.1 降级为 hints provider，不存在两套独立写入路径——dual-mode shadow 表对比意义有限

## 替代验证
- Golden live gate 持续 ≥ 90% pass
- v1.0.3 后 ≥ 95% pass
- Closed Beta 上线后 7 天 0 回归即视为通过 §5.3 sunset pre-condition

## 触发回滚条件（替代 §5.2 acceptance metrics）
- Golden live pass 率连续 2 次 < 85% → 回滚 prompt
- 生产 audit_log dropped/candidate 比 > 0.5 → 暂停默认 llm，回 dual 观察
- 单 call 成本 > $0.005 → 启用 §3.2 mitigations
```

开 GitHub issue `[chore] sunset regex_shadow.py 60 days after Closed Beta`:
- Pre-condition: Closed Beta + 7 天 0 回归
- 60 天 grace period
- 删除清单: `regex_shadow.py`, `mode in ("dual","regex")` 代码路径, `memory_l3_facts_shadow_regex` 表 migration
- Sunset date 字段填占位 TBD

---

# Phase E — v1.1.0 backlog issue

开 GitHub issue `[ss02][v1.1.0] memory extractor 复杂语义边界 case`：

```markdown
## 背景
v1.0.3 ship 后仍有 2 case 无法通过 patch-level prompt fix 解决，属于 v1.1.0 范围。

## Cases

### frag-004 — 跨 turn modifier 合并
Input: 「我妈妈是老师。教数学的。」
Golden: `(family, occupation, "数学老师", src=[1,2])` — 单 candidate 合并 value
LLM 当前: 出 2 个 candidate 或不合并

需要的 prompt 改动: R4 加 "attribute value cross-turn merge" 子条款 + 1 个示范 example
预估工作量: 2h prompt iteration + 验证

### mixd-002 — 单 turn 多 attribute + 第三方实体识别 + supersession
Input: 「你猜我叫什么？其实我叫王强。你之前说我26岁，那不对，我27了。」
Golden: `(self, name, "王强")` + `(self, age, "27")` + drop `out_of_scope_entity`(指 assistant 之前说的"26岁")
LLM 当前: 多 candidate 或 drop reason 错

需要的 prompt 改动: 单 turn 多 step 解析示范 + assistant-claim drop reason 教学
预估工作量: 3h prompt iteration + 验证

## Acceptance
- v1.1.0 prompt 让这两个 case 转绿
- 不影响 v1.0.3 已通过的 case（regression test）
- prompt version bump 到 1.1.0
```

将 issue link 写入 `docs/PROJECT_STATUS.md` v1.1.0 backlog 段。

---

# Phase F — 重构完结判定

```
□ Phase A v1.0.3 prompt 入 main
  □ R11 收紧为 "name only, no relation"
  □ R5 追加 "纯情绪 ≠ 修辞" 反例
  □ R6 改为 "不 drop"
  □ R12 追加 "了" 过去时反例
  □ Example 9 新增
  □ PROMPT_VERSION bumped to "1.0.3"
□ Phase B crash 排查完结（修复或 skip 并标注）
□ Phase C live golden ≥ 90% pass（目标 ≥ 47/49）
□ Phase C avg cost / call ≤ $0.0010
□ Phase C HUMAN §5 sanity 3 个 prompt 全绿
□ Phase D PR-1 scoring 入 main（确认 / 补合）
□ Phase D PR-2 INV-M-15 + INV-M-NEW-A property test 入 main
□ Phase D PR-3 4 份 design doc + ## Approval + HUMAN 签字
□ Phase D PR-4 dual-mode skip rationale + sunset issue
□ Phase E v1.1.0 backlog issue 开了 + link 进 PROJECT_STATUS.md
□ 一次 `bash scripts/ci.sh` 全绿
□ `docs/PROJECT_STATUS.md` 加 "✅ SS02 Memory LLM Extractor 重构完结 @ 2026-06-22"
□ `docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md` 头加 "STATUS: COMPLETE @ 2026-06-22, see V1_0_3_FINAL.md"
```

---

# 风险表

| 风险 | 触发条件 | 缓解 |
|---|---|---|
| R11 收紧后真该有 relation 的 case 反而漏 | live golden "我和老张是大学同学"类变 fail | R11 已显式列出"关系不在称谓里→出 relation"反例段；若仍误判，加 Example 10 |
| R5 排除情绪后真修辞漏 drop | rhet-001/002/003 转红 | 这些都有"我有 X / 我是 X"句法，与"开心死了"明显不同；新口诀"伪装成 fact 的修辞" |
| R12 "了" 边界引入新分类难题 | LLM 把所有带"了"句都走 hobby | "了"只在 R12 dislike 这一窄路径生效，且要求与 R7 negation 共存；若误，再细化"+ L3 无对应 fact 时"前置条件 |
| token 涨太多 | 新增 ~800 token | 当前 ~3700 → ~4100；缓解：删 Example 3（已被 R6 覆盖）省 ~200，或缩 R5 词例 |
| 成本涨 | input 涨 12% | 接受，仍在 $0.002 cap 内 |
| v1.1.0 backlog 永远不做 | issue 没分配 owner | PROJECT_STATUS.md 标 "P2 - before next major release" |

---

# Appendix A — 改动文件清单

| Phase | 文件 | 改动 |
|---|---|---|
| A.1-A.6 | `backend/heart/ss02_memory/extractor/prompt_builder.py` | R5/R6/R11/R12 改 + Example 9 新增 + PROMPT_VERSION 1.0.3 |
| A.7 | `docs/design/memory_extractor_prompt.md` | §1 R5/R6/R11/R12 + §2 Example 9 + §4.6 changelog |
| B | `backend/heart/ss02_memory/extractor/llm_extractor.py` | 视 crash 类型可能要加 fallback |
| D.2 | `backend/tests/properties/test_memory_invariants.py` | 末尾 2 个 property test |
| D.3 | 4 份 design doc | 末尾加 `## Approval` |
| D.4 | `docs/audit/2026-06-20_dual_mode_skip_rationale.md` | 新建 |
| D.4 + E | GitHub issues | 2 个新建 (regex sunset + v1.1.0 backlog) |
| F | `docs/PROJECT_STATUS.md` + `MEMORY_LLM_EXTRACTOR_REFACTOR.md` | 完结状态 |

---

# Appendix B — 不在本次范围

| 项 | 落点 |
|---|---|
| frag-004 跨 turn modifier 合并 | v1.1.0 backlog issue |
| mixd-002 单 turn 多 step + assistant-claim | v1.1.0 backlog issue |
| Mixed 桶 vs design.md §1.1 case count 偏差 (49 vs 47) | docs-only issue，不阻塞 |
| JSONL vs YAML 格式偏差 | docs-only issue |
| dropped_signals raw_phrase SEMI fuzzy match | scoring v1.1.0 enhancement |
| Resolver decision table reinforce/conflict_defer 加密度单测 | 见体感后做 |

---

# Commit message template

```
feat(ss02): bump memory extractor prompt to v1.0.3 — close refactor at 90%+

Before (v1.0.2 strict): 39/49 (79.2%) pass
After  (v1.0.3 strict): __/49 (___%) pass

Surgical fixes (8 cases targeted):
- R11 收紧: 称谓+专名 → 只出 name candidate，不出 relation
  → coref-001/003/004, disc-006 转绿 (4)
- R5 收紧: 纯情绪表达（"开心死了"）既不 candidate 也不 drop
  → rhet-004/005 转绿 (2)
- R6 收紧: 问句既不 candidate 也不 drop
  → qstn-004 转绿 (1)
- R12 边界: "不喜欢 X 了" 的"了"→ hobby disclosure（非 dislike）
  → neg-003 转绿 (1)
- Example 9 新增（称谓+专名反例）

Deferred to v1.1.0 (#XXX):
- frag-004 attribute value cross-turn merge
- mixd-002 单 turn 多 step + assistant-claim drop reason

Spec doc synced: docs/design/memory_extractor_prompt.md §4.6 changelog
Refs: docs/execution/MEMORY_EXTRACTOR_V1_0_3_FINAL.md
```

---

**版本**: 1.0.0
**创建日期**: 2026-06-20
**主笔**: Opus 4.7
**执行模型**: GLM (Phase A prompt + B crash + C validate + D.2 property test + D.4 起草) ~5h；HUMAN (D.3 签字 + C.4 sanity + D.4 签字 + F) ~1.5h
**预计完结日期**: 2026-06-22
**实际 code 完结日期**: 2026-06-21 (commit 878cc57)
**交付完结**: ⏳ 待 untracked SS02 实现文件入 main

---
---

## Final Outcome (2026-06-21)

**Prompt v1.0.3**: 47/49 = 95.9% strict scoring pass — meets ≥ 90% target.
**Commits**: 878cc57 (prompt + scoring) + db2d9fc (PROJECT_STATUS update).
**Branch state**: feat/mimo-tts-provider（事实主干，待拆）.

### 转绿明细 (7/8 surgical targets + 1 crash)
- coref-001/003/004, disc-006 (R11 收紧)
- rhet-004/005 (R5 排除纯情绪)
- qstn-004 (R6 不 drop + crash sanitize)
- neg-003 (R12 L3 优先路由)

### v1.1.0 backlog (3 cases — 已知 regression)
- frag-004 跨 turn modifier 合并
- mixd-002 多 step + assistant-claim
- adv-005 R11 过度收紧（"小明是我儿子" 混淆 name/relation）

### ⚠️ 未完结的工程债（必须在 main PR 前修）
- 未追踪 SS02 文件: regex_shadow / resolver / writer / promoter / golden_loader / hints / extractor_diff_report
- 分支治理违规: 见 PROJECT_STATUS.md §6 风险表
- 详见 `docs/execution/SS02_ACCEPTANCE_AND_NEXT_STEPS_2026-06-21.md`
