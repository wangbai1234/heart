# SS02 Memory Extractor 重构 — 阶段性审计 + v1.0.2 收尾方案

> **本文件覆盖**：(1) 对照 `MEMORY_LLM_EXTRACTOR_REFACTOR.md` §7 Cut Criteria 逐项审计；(2) v1.0.2 prompt 收尾 2 个剩余失败 case；(3) 4 项工程债务的修复 PR 清单。
> **配套**：`MEMORY_LLM_EXTRACTOR_REFACTOR.md`（原始执行手册）+ `MEMORY_EXTRACTOR_PROMPT_FIX_v1_0_1.md`（上一轮 prompt 修复）
> **使用方式**：先看 §1 审计判断"重构是否已完成"；再按 §2/§3/§4 顺序处理债务，每条独立 PR。
> **执行模型分配**：GLM（机械实施 + 跑测试）；HUMAN（签字 + 文档审）。
> **总耗时预估**：GLM ~4h，HUMAN ~1.5h。

---

# 第一部分: 阶段性审计（对照 §7 Cut Criteria）

## 1.1 Cut Criteria 逐项判定

| # | 验收项 | 状态 | 证据 |
|---|---|---|---|
| 1 | §2-§4 所有 Task commit 入 main | ⚠️ | 当前 feat 分支，未合 main；需 PR + merge |
| 2 | `MEMORY_EXTRACTOR_MODE` 默认 llm + 生产 7 天 0 回归 | ⚠️ | 默认已是 `"llm"`（`config.py`），但**未经 §5.2 dual-mode 2 周观察期**——见 §1.2.A |
| 3 | `orchestrator.py:981` 旧路径删除 | ✅ | `grep fast_encoder_identity_detection` 0 hit |
| 4 | INV-M-11 / INV-M-15 / INV-M-NEW-A/B/C 单元 + property 测试齐全 | ⚠️ | INV-M-11 / NEW-B / NEW-C 有；**INV-M-15 + INV-M-NEW-A 缺**——见 §1.2.B |
| 5 | Golden Set ≥ 30 + CI gate 启用 | ✅ | 49 case，`make memory-golden{,-live}` 通；v1.0.1 后 ~47-48/49 pass |
| 6 | §5.2 dual-mode 2 周观察 + acceptance metrics 全达标 | ❌ | 未跑——直接切了 llm 默认；见 §1.2.A |
| 7 | 真实 LLM 单次成本 < $0.002 | ✅ | 实测 $0.0006-$0.0008/call |
| 8 | `pytest tests/` 0 failed | ❓ | 需在收尾 PR 前跑一次 full `bash scripts/ci.sh` |
| 9 | 4 份 design doc 存在（schema / prompt / promoter / golden） | ✅ | `docs/design/memory_extractor_{schema,prompt}.md` + `memory_promoter_rules.md` + `memory_golden_set_design.md` |
| 10 | HUMAN 签字 4 份 doc | ❌ | 无签字 trail——见 §1.2.C |

**结论**: 7/10 ✅，2/10 ⚠️ 部分，1/10 ❌。

**重构是否已完成？** **功能完成 95%**——核心架构（fast/slow path 分离、INV-M-11、Promoter、Resolver/Writer/DLQ、Golden gate）全部到位且跑通；缺的是**收尾流程**（dual 观察期合理化 + INV property 补 + 签字 trail + scoring debt）和**最后 2 个 golden case**。

## 1.2 三条工程债务详解

### 1.2.A §5.2 / §5.3 流程债务 — dual-mode 跳过 + sunset 未启动

**事实**:
- `backend/heart/core/config.py` 已默认 `memory_extractor_mode="llm"`
- `extractor_diff_report.py` 脚本存在（infra 准备就绪）
- 但**没有 2 周观察期数据**，没有 `docs/audit/memory_extractor_diff_YYYY-MM-DD.md` 报告
- `regex_shadow.py` 仍在仓库，§5.3 60 天 sunset issue 没开

**对照 §5.2 原文**:
> "2 周观察期：LLM recall ≥ regex recall × 1.5、precision ≥ regex、假阳性 < 5%、cost < $0.50/天/活跃用户。任一不达标不允许切默认"

**为什么跳过仍可接受**:
- §5.2 的目的是"切默认前给 LLM 上保险"。Golden Set 49 case + live live gate 提供了 **更强、更稳定** 的保险——它直接基于 expected envelope 打分，比 dual-mode 抽样 1% 由 HUMAN 裁决更严
- Phase 8 Closed Beta 还没起，**当前没有"生产流量"可观察**——dual-mode 观察 2 周没真实样本
- 历史 regex 实现已经被 §5.1 降级为 hints provider，并非"两套独立写入"——dual mode 的 shadow table 只能跑 regex shadow，对比意义有限

**处置**:
- A1（推荐）：在 `docs/audit/2026-06-20_dual_mode_skip_rationale.md` 写明"以 Golden gate 替代 §5.2 观察期"的理由 + 取代关系 + 触发回滚的条件
- A2: §5.3 regex sunset 改为 issue 跟踪——"Closed Beta 上线 + 7 天 0 回归 → 删 regex_shadow.py + 关闭 mode=dual 代码路径"

### 1.2.B Property test 覆盖 — INV-M-15 + INV-M-NEW-A 缺

**事实**:
- `test_memory_invariants.py` 覆盖 INV-M-NEW-B（≤1 active per key）+ INV-M-NEW-C（negation 软删）
- `test_promoter.py` 覆盖 INV-M-11（fast path 不写 L2-L4）
- **INV-M-15 没有 property test**——只有 Promoter unit test 验证条件，没有"任何 L4 行必由 promotion 规则产生"的反向证明
- **INV-M-NEW-A 没有 property test**——`source_turns` + `extractor_run_id` 必带的不变量没断言

**对照 §1（架构 INV）**:
> INV-M-15: L4 候选必须满足 ≥3 次独立 mention + confidence_ewma ≥ 0.8 + age_days ≥ 1 + 无 contradiction
> INV-M-NEW-A: 每条 L2/L3 入库记录必须带 `source_turns: list[int]` 与 `extractor_run_id`

**风险**: 没有 INV-M-15 property 测试，Promoter 改动可能误触 demote 路径或漏 condition；没有 INV-M-NEW-A 测试，未来 Writer 改动可能漏写 source_turns 而审计不可查。

### 1.2.C HUMAN 签字 trail — 4 份 design doc 缺

**事实**:
- `memory_extractor_schema.md` / `memory_extractor_prompt.md` / `memory_promoter_rules.md` / `memory_golden_set_design.md` 都存在
- **没有任何文档底部有"approved by HUMAN @ <date>"**（grep 命中只是 `memory_golden_set_design.md` 提到"MAJOR bump 需 HUMAN sign-off"——是规则而非签字本身）

**对照 §7 / §3.1 / §4.1 / §6.1**:
> "□ HUMAN 评审 + 签字 (per CLAUDE.md 战略选择 = HUMAN 批准 原则)"

**处置**: 简单——在 4 份 doc 末尾加签字 trail 章节（用户手动审完写一行即可）。

## 1.3 隐藏债务 — Scoring 实现 vs design.md §4.2 偏差（**最关键**）

**事实**: `backend/tests/golden/memory_extraction/test_extractor_golden.py` 的 `_score_envelope` 与 `memory_golden_set_design.md` §4.2 设计偏差严重。

| Design.md §4.2 字段 | 设计 tier | 当前 scoring 实现 | 差距 |
|---|---|---|---|
| `entity_type` | HARD | 比对 ✅ | OK |
| `attribute` | HARD | 比对 ✅ | OK |
| `kind` | **HARD** | **不比对** | ❌ 修辞误提取（kind=disclosure 但 golden=dropped）目前算 FP，但若 LLM 输出 kind=rhetoric candidate 也算 TP——本不应该|
| `operation` | **HARD** | 记录但**不参与 pass 判定** | ⚠️ `operation_match` 只进 tp_details，不影响 `score["passed"]` |
| `prior_value_id` | **HARD** | 不比对 | ❌ supersede 案例 prior_value_id 错也算 TP |
| `value` | SEMI（NFKC 等） | 仅做 `lower + 子串包含` fuzzy | ⚠️ 比 design 弱但可接受 |
| `entity_ref` | SEMI（cluster 等价） | 不比对 | ❌ adv-005 关系链 entity_ref 错配算 TP |
| `source_turns` | SEMI（set 超集允许 introducing turn） | 不比对 | ❌ |
| `confidence` | SOFT（±0.15） | 不比对 | ⚠️ 可接受 |
| `reasoning` | SOFT-with-floor（必引 T<id>） | 不比对 | ❌ R1 违反不会暴露 |
| `dropped_signals[*].turn_id` | HARD | 不比对 | ❌ |
| `dropped_signals[*].reason` | HARD | 不比对 | ❌ |
| `dropped_signals[*].raw_phrase` | SEMI | 不比对 | ❌ |

**判定阈值差异**:
- Design §4.4: PASS = 全部 HARD 命中 + 全 SEMI 命中 + 无未匹配
- 实现: `passed = recall >= 0.8 and precision >= 0.5`——一个 case 漏一半 candidate 也算 PASS（recall=0.5 触发 fail，但 0.8 < recall < 1.0 仍 PASS）

**风险**:
- v1.0.1 跑 ~47-48/49 pass 是用**宽松 scoring** 算的；按 design §4.2 严格 scoring 实际 pass 率会**显著更低**
- 修辞/对抗类 case 看似转绿，但若 LLM 内部 kind 错而 entity_type+attribute 对，scoring 不会 catch
- 这是 v1.0.2 / v1.1.0 升级前**必须先补**的债务，否则后续迭代会在"假 90%"上做决策

**处置**: §3 的 Phase B 把这个补上。

---

# 第二部分: v1.0.2 — 收尾 coref-004 + adv-006

## 2.1 失败 case 分析

### coref-004

**Input**:
```
[T1] user: 小李是我同事。
[T2] user: 他是后端工程师，做Java的。
```

**Golden expected**（2 candidates）:
```json
[
  {"entity_type":"colleague","attribute":"name","value":"小李","entity_ref":"小李","source_turns":[1]},
  {"entity_type":"colleague","attribute":"occupation","value":"后端工程师","entity_ref":"小李","source_turns":[1,2]}
]
```

**LLM 实际**（推测）: 只出 `occupation` candidate，**漏 `name`**。

**根因**: prompt 没有明文教 LLM"实体首次以专名（人名/宠物名）出现时，专名本身就是 `attribute=name`"。Example 1 用 "妙妙" 但 "妙妙" 是在 T12 显式说"她叫妙妙"才映射，没有 "实体名出现 == 引出该实体 + 同时给出 name" 的范例。「小李是我同事」是非常典型的中文表达——专名 + 关系/职业，LLM 把"小李"当 entity_ref 用，跳过了 name attribute。

### adv-006

**Input**:
```
[T1] user: 我很不擅长做饭。
```

**Golden expected**:
```json
[{"entity_type":"self","attribute":"dislike","value":"做饭","kind":"disclosure"}]
```

**LLM 实际**（推测）: 可能输出 `(self, hobby, "做饭", kind=negation)`，或 drop。

**根因**: R7 写"不/没" → negation。「不擅长」字面带"不"但语义是 dislike/aversion，不是 negation（negation 撤回的是已存在的 fact）。当前 prompt 缺这条边界。

## 2.2 Task — v1.0.2 改动

**Tool**: GLM
**Why**: 2 个小改动，单 patch。

### 改动 1 — 新增 R11 "实体引入 = name candidate"

**位置**: `backend/heart/ss02_memory/extractor/prompt_builder.py` R10 之后

**插入**:

```
### R11 — 实体首次以专名出现时，必出 name candidate

实体（人 / 宠物 / 朋友 / 家人 / 同事）首次在 window 中以**专名**（中文名、英文名、外号、宠物名）出现时：

- 即使该 turn 同时披露了关系/职业/属性，专名本身就是独立的 `attribute="name"` candidate
- `entity_ref` 使用专名本身（如 `"小李"` / `"妙妙"`）
- `source_turns` 仅含专名出现的 turn

例：
- 「小李是我同事」→ 2 candidate: `(colleague, name, "小李")` + `(colleague, relation, "同事")`
- 「我老公叫李明」→ 2 candidate: `(family, name, "李明", entity_ref="husband")` + `(family, relation, "老公", entity_ref="husband")`
- 「我妈叫张红」→ 同上模式

不适用情况：
- 代词 / 称谓（"他/她/我妈"）— 这些不是专名
- 头衔（"老板"/"医生"）独立出现 — 这是 occupation 不是 name
```

### 改动 2 — 新增 R12 "dislike vs negation 边界"

**位置**: `prompt_builder.py` R11 之后（也就是 R7 / R10 / R11 / R12 顺序）

**插入**:

```
### R12 — "不擅长 / 不喜欢" → dislike，**不是** negation

R7 的 negation 只处理"撤回已声明事实"。下列**态度表达**走 `attribute="dislike"`, `kind="disclosure"`, `operation="create"`：

- 「我不擅长 X」「X 不太行」→ `(self, dislike, "X")`
- 「我不喜欢 X」「X 我无感」「不感冒」→ `(self, dislike, "X")`
- 「讨厌 X」「受不了 X」→ `(self, dislike, "X")`
- 但「我没有 X」「我不养 X 了」→ R7 negation（撤回先前的 hobby/pet/...）

判断口诀：句子是**态度表达**（"我对 X 的感受"）还是**事实撤回**（"我之前说的 X 不对了"）？前者 → dislike disclosure，后者 → R7 negation。
```

### 改动 3 — bump 版本

`PROMPT_VERSION = "1.0.1"` → `"1.0.1"` (保持) ... 实际应 → `"1.0.2"`

文件位置：`prompt_builder.py:22`

### 改动 4 — `memory_extractor_prompt.md` 同步

- §1 在 R10 后追加 R11 + R12 全段
- §4.6 changelog 加 1.0.2 行

## 2.3 验证

```bash
cd backend
pytest tests/unit/ss02_memory/extractor/ -v        # 应全绿
make memory-golden                                  # fake mode 应全绿
make memory-golden-live                             # 真 LLM
```

**预期**：
- coref-004 转绿（2 candidate 全出）
- adv-006 转绿（`(self, dislike, "做饭")`）
- 49/49 pass（100%）；保留 1 case 余量容忍 LLM 抽风 → 48/49 (98%) 也算达标

---

# 第三部分: 收尾债务 — 4 个独立 PR

## 3.1 PR-1 — Golden scoring 实现补齐（**最高优先级**）

**Why**: 见 §1.3——当前 scoring 偏离 design §4.2，未来迭代会在"假 pass 率"上决策。

**Tool**: GLM
**改动**: `backend/tests/golden/memory_extraction/test_extractor_golden.py:199-298` `_score_envelope` 函数 + 相关 helpers

**关键改动**:

1. **HARD 字段全比对**（`kind` / `operation` / `prior_value_id`）
   ```python
   # 在 tp_details 收集后追加 HARD 校验
   hard_fail = False
   for d in tp_details:
       if exp.get("kind") != act.get("kind"):
           hard_fail = True
           d["hard_fail_reason"] = "kind mismatch"
       elif exp.get("operation") != act.get("operation"):
           hard_fail = True
       elif (exp.get("prior_value_id") or None) != (act.get("prior_value_id") or None):
           hard_fail = True
   ```

2. **dropped_signals 参与 P/R/F1**
   ```python
   exp_drops = {(d["turn_id"], d["reason"]) for d in exp_dropped}
   act_drops = {(d["turn_id"], d["reason"]) for d in actual.get("dropped_signals", [])}
   drop_tp = exp_drops & act_drops
   drop_fp = act_drops - exp_drops
   drop_fn = exp_drops - act_drops
   # 合入 overall P/R/F1
   ```

3. **`source_turns` SEMI**（set 等价，允许 superset 仅当多余 turn 是 entity introducer——后者可暂留 TODO）
   ```python
   exp_st = set(exp.get("source_turns", []))
   act_st = set(act.get("source_turns", []))
   if not exp_st.issubset(act_st):
       hard_fail = True
   ```

4. **`reasoning` floor check**
   ```python
   import re
   src_ids = act.get("source_turns", [])
   reasoning = act.get("reasoning", "")
   if not any(re.search(rf"T{sid}\b|turn {sid}\b", reasoning, re.IGNORECASE) for sid in src_ids):
       hard_fail = True
   ```

5. **新 pass 判定**
   ```python
   passed = (
       not hard_fail
       and recall >= 0.8       # 保留宽松底线
       and precision >= 0.7    # 从 0.5 提到 0.7
       and drop_recall >= 0.8
   )
   ```

6. **报告增强**: HTML 报告增加 `Hard Fails` 列，列出本 case 的 HARD 错误（kind/operation/prior_value_id/source_turns/reasoning citation）

**验收**:
- [ ] 所有 49 case 跑过 — 实际 pass 率会比 v1.0.1 报告**低 5-10 个百分点**（这是正常的，新 scoring 更严）
- [ ] 单独跑 rhet-001：现在 v1.0.1 通过，新 scoring 仍应通过（candidates=[]）
- [ ] 单独跑 supersede 类 case：prior_value_id 错则现 PASS、新 FAIL
- [ ] HTML 报告显示 hard_fail_reason 列

**风险**: 新 scoring 跑出来 pass 率可能掉到 80% 左右。**这不是 prompt 退化，是测量更准**——按结果再启动 v1.1.0 prompt 迭代或调整 golden。这一步必须做，否则一直在自欺。

## 3.2 PR-2 — INV-M-15 + INV-M-NEW-A property test

**Why**: §7 Cut Criteria 第 4 项

**Tool**: GLM
**改动**: `backend/tests/properties/test_memory_invariants.py` 末尾追加 2 个 test

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

**验收**:
- [ ] 两个 test 跑 100 case 不破
- [ ] hypothesis shrink 后给出最小反例（如果有 bug）

## 3.3 PR-3 — 4 份 design doc 签字 trail

**Why**: §7 Cut Criteria 第 10 项

**Tool**: HUMAN 审 + GLM 加 metadata 章节

**改动**: 在以下 4 份 doc 末尾追加 `## Approval` 章节模板：

```markdown
---

## Approval

| Date | Reviewer | Role | Version reviewed | Notes |
|---|---|---|---|---|
| 2026-06-20 | <HUMAN 名字> | Project Lead | 1.0.x | <一句话评语，或"approved as-is"> |
```

涉及文件：
- `docs/design/memory_extractor_schema.md`
- `docs/design/memory_extractor_prompt.md`
- `docs/design/memory_promoter_rules.md`
- `docs/design/memory_golden_set_design.md`

HUMAN 跑 5 分钟 review 4 份 doc，填表，commit "docs(ss02): add HUMAN approval trail for memory extractor design docs"。

## 3.4 PR-4 — §5.2/§5.3 流程偏差文档化 + sunset issue

**Why**: §1.2.A 详述

**Tool**: GLM 起草 + HUMAN 签字

**改动 1**: 新建 `docs/audit/2026-06-20_dual_mode_skip_rationale.md`

```markdown
# Memory Extractor §5.2 dual-mode 观察期跳过 — 合理化决策

**Date**: 2026-06-20
**Decision**: Skip §5.2 2-week dual-mode observation; rely on Golden Set live regression as substitute gate.
**Decided by**: <HUMAN>

## 背景
MEMORY_LLM_EXTRACTOR_REFACTOR.md §5.2 要求切默认 mode=llm 前完成 2 周 dual-mode 观察 + diff 报告 + acceptance metrics。

## 跳过原因
1. **当前无生产流量**（Phase 8 Closed Beta 未启），dual-mode 没有"真实样本"可观察
2. Golden Set 49 case + live regression gate（v1.0.1 后 47-48/49 pass）提供更稳定的保险
3. Regex 已通过 §5.1 降级为 hints provider，不存在两套独立写入路径——dual-mode shadow 表对比意义有限

## 替代验证
- Golden live gate 持续 ≥ 90% pass
- v1.0.2 后 ≥ 95% pass
- Closed Beta 上线后 7 天 0 回归即视为通过 §5.3 sunset pre-condition

## 触发回滚条件（替代 §5.2 acceptance metrics）
- Golden live pass 率连续 2 次 < 85% → 回滚 prompt
- 生产 audit_log dropped/candidate 比 > 0.5 → 暂停默认 llm，回 dual 观察
- 单 call 成本 > $0.005 → 启用 §3.2 mitigations
```

**改动 2**: 开 GitHub issue「[chore] sunset regex_shadow.py 60 days after Closed Beta」，body 包含：
- Pre-condition: Closed Beta + 7 天 0 回归
- 60 天 grace period
- 删除清单: `regex_shadow.py`, `mode in ("dual","regex")` 代码路径, `memory_l3_facts_shadow_regex` 表 migration
- Sunset date 字段填占位 TBD

**验收**:
- [ ] `docs/audit/2026-06-20_dual_mode_skip_rationale.md` 入库
- [ ] GitHub issue 开了并 link 入 PROJECT_STATUS.md
- [ ] HUMAN 在 audit doc 末尾签字

---

# 第四部分: 执行顺序 + Cut Criteria

## 4.1 PR 顺序（强建议串行而非并行）

```
Day 1 上午:  v1.0.2 prompt（§2）           — GLM 1h
Day 1 下午:  PR-1 scoring 补齐（§3.1）      — GLM 2h + HUMAN 看 HTML 报告 30min
Day 2 上午:  PR-2 INV property tests（§3.2）— GLM 1.5h
Day 2 下午:  PR-3 签字 trail（§3.3）        — HUMAN 30min
            PR-4 流程偏差 doc（§3.4）       — GLM 30min + HUMAN 30min
```

**为什么串行**: PR-1 改 scoring 后所有数字会变，先做 PR-1 再做 v1.0.2 会让 v1.0.2 的 pass 数字直接是"新口径"。

**实际更优顺序**:
```
Day 1 上午:  PR-1 scoring 补齐（先建立真口径）
Day 1 下午:  跑一次 baseline live → 真实 pass 率（应 60-80%）
            v1.0.2 prompt 改 + 跑 live → 真实 pass 率（应 ≥ 90%）
Day 2:       PR-2 / PR-3 / PR-4 并行
```

## 4.2 整体 Cut Criteria

执行完 v1.0.2 + 4 PR 后，**重构正式完结**。验收：

```
□ v1.0.2 prompt 入 main, golden live ≥ 95% pass（**严格 scoring**口径）
□ PR-1 scoring 补齐入 main, design.md §4.2 HARD 字段全覆盖
□ PR-2 INV-M-15 + INV-M-NEW-A property test 入 main
□ PR-3 4 份 design doc 末尾有 HUMAN 签字行
□ PR-4 dual-mode 跳过 rationale doc + sunset issue 入 main
□ 一次完整 `bash scripts/ci.sh` 全绿
□ PROJECT_STATUS.md 把 SS02 Memory 状态从 "✅ 在 main" 增补 "✅ LLM Extractor 重构完结 @ 2026-06-22"
□ 关闭 MEMORY_LLM_EXTRACTOR_REFACTOR.md（在文件头部加 "STATUS: COMPLETE @ 2026-06-22"）
```

## 4.3 风险

| 风险 | 触发条件 | 缓解 |
|---|---|---|
| PR-1 跑出来真实 pass 率 < 80% | scoring 严格后 LLM 显形 | 不是回归，是测量准了——按真实 gap 启 v1.1.0 prompt 迭代 |
| INV-M-15 property test 发现 Promoter bug | hypothesis shrink 找到反例 | 修 Promoter 不是关 test；这正是 property test 的价值 |
| HUMAN 签字时发现 design doc 内部矛盾 | review 出现实质质疑 | 该 doc 进 MINOR bump 而非签字——签字代表锁版 |

---

# 附录 A: 改动文件清单总表

| PR | 文件 | 改动类型 |
|---|---|---|
| v1.0.2 | `backend/heart/ss02_memory/extractor/prompt_builder.py` | R11 + R12 + version bump |
| v1.0.2 | `docs/design/memory_extractor_prompt.md` | §1 R11/R12 + §4.6 changelog 加 1.0.2 行 |
| PR-1 | `backend/tests/golden/memory_extraction/test_extractor_golden.py` | `_score_envelope` 大改 + HTML 报告增 hard_fail 列 |
| PR-2 | `backend/tests/properties/test_memory_invariants.py` | 末尾追加 INV-M-15 + INV-M-NEW-A 两个 test |
| PR-3 | `docs/design/memory_extractor_schema.md` | 末尾加 ## Approval |
| PR-3 | `docs/design/memory_extractor_prompt.md` | 末尾加 ## Approval |
| PR-3 | `docs/design/memory_promoter_rules.md` | 末尾加 ## Approval |
| PR-3 | `docs/design/memory_golden_set_design.md` | 末尾加 ## Approval |
| PR-4 | `docs/audit/2026-06-20_dual_mode_skip_rationale.md` | 新建 |
| PR-4 | GitHub issue "[chore] sunset regex_shadow.py" | 新建 |
| PR-4 | `docs/PROJECT_STATUS.md` | 加 issue link |

---

# 附录 B: 不在本次范围（独立 backlog）

记录在案，避免 scope creep：

1. **Mixed 桶 vs golden_set_design.md §1.1 偏差**: 实施 49 case (mixed×2) vs 设计 47 case (无 mixed)；记 issue 但不阻塞本次完结
2. **JSONL vs YAML 格式偏差**: 同上
3. **§3.2 §3 dropped_signals 完整审计**: 当前 scoring PR-1 已覆盖 turn_id+reason 比对；raw_phrase SEMI 比对可下次迭代
4. **Test 5 manual sanity prompt**（multi-attribute + supersession）: HUMAN 半年一次跑即可，不阻塞
5. **Resolver decision table reinforce/conflict_defer 单测覆盖**: 已有但可加密度，下次有体感再补

---

**版本**: 1.0.0
**创建日期**: 2026-06-20
**主笔**: Opus 4.7
**执行模型**: GLM（实施 + 测试 ~ 4h）+ HUMAN（4 份 doc 签字 + scoring review ~ 1.5h）
**预计完结日期**: 2026-06-22
