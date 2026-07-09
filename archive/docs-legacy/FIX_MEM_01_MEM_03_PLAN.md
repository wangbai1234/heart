# Plan: 修复 MEM-01 / MEM-03 记忆召回缺陷（供 Sonnet 执行）

## Context

`docs/TEST_REPORT_2026-07-07.md`（mimo 全功能测试）报出两个高危 FAIL：

- **MEM-01**：发送「我养了一只叫年糕的猫」→ 清空 → 追问宠物名，AI 幻觉出「朔夜」，没召回「年糕」。
- **MEM-03**：多个同义谓词（`worries_about`/`concerned_about`、3× 面试、7× 地点）各存一行，追问「最担心什么」答非所问。

**代码核查纠正了报告的两处根因判断（务必以此为准）：**

1. **召回热路径是"纯向量"**。关键词/图检索器（`graph.py` 的 `LIKE '%kw%'`）在聊天热路径里是**死代码**——唯一构造 `QueryContext` 的地方（`ss05_composer/service.py:545-549`）从不填充 `keywords`/`entry_nodes`，所以 `GraphRetriever._find_entry_nodes` 永远返回 `[]`。L3 事实**只能**通过 `VectorRetriever`（`retriever/vector.py`，对 `literal_text` 的嵌入做 pgvector 余弦 kNN）被召回。报告说的"关键词 LIKE 匹配失败"其实无关——那条路根本没跑。
   - MEM-01 真因：`literal_text = "user has_pet 一只叫年糕的猫"`（英文谓词结构串）的嵌入与纯中文查询「你还记得我宠物叫什么吗？」对齐差；用户有 ~48 条事实，该行进不了向量 top-N 候选集。`select_top_k`（`retriever/base.py:219-288`）虽然会**强制包含高置信 L3（confidence≥0.9，最多 2 条）**，但只能作用于**已进入候选集**的事实——进不了候选集就救不回来。→ 杠杆在**嵌入文本对齐**。

2. **有两条 L3 写入管线，且都在跑**（`workers/runner.py:38` 起 `MemoryEncoderWorker` = Path A，`:55` 起 `MemoryExtractorWorker` = Path B）：
   - **Path A** `workers/memory_encoder.py::write_facts_to_l3`：**自由谓词**（LLM 随意生成 `worries_about`/`concerned_about`…），`literal_text = f"{subject} {predicate} {object}"`，去重按 `predicate` **精确字符串相等**（`memory_encoder.py:232-243`）→ 同义谓词各建一行。**报告里的问题事实全出自这条路。**
   - **Path B** `ss02_memory/extractor/writer.py`：闭合 `Attribute` 枚举（15 值），`literal_text = f"{subject}: {predicate} = {value}"`。
   - 报告把修复点写成 `writer.py:222`（Path B），**判断错误**——失败事实是 Path A 的自由谓词。
   - 检索期 `deduplicate_memories`（`base.py:291-337`）**已实现**，会折叠字节完全相同的 `(subject,object)`。所以 MEM-03 的真缺陷是**写入期碎片化**（存量脏数据 + 新写入继续分裂），需在写入期规范谓词 + 清理存量。

**采用方案（已与用户确认）：**
- 范围：**只修两个记忆 bug**；BUG-3 角色系统重构/UGC 留到独立规划周期。
- 嵌入：**解耦**——`literal_text` 保持原样（prompt 注入/展示不变，避免动 reconstructor、L4 快照、~12 个测试 fixture），新增共享 `build_embedding_text()` 把谓词映射成中文后**只用于生成 `semantic_vector`**。

---

## 一、新增共享词表模块

新文件 `backend/heart/ss02_memory/predicate_vocab.py`：

- `_PREDICATE_ALIASES: dict[str, str]` — 同义谓词归一（取 `TEST_REPORT` 第 424-450 行的映射，逐条审校）：`concerned_about→worries_about`、`has_upcoming_interview/has_scheduled_interview→has_interview`、`located_at/located_in/is_located_in/is_in_location→location`、`has_sister→has_sibling`、`likes_food/likes_color/likes_to_go_to→likes` 等。
- `_PREDICATE_ZH: dict[str, str]` — 英文谓词→中文 gloss（取报告第 452-508 行 + 补全 Path B 的 15 个枚举值 `name/nickname/age/color/breed/occupation/relation/location_residence/location_origin/hobby/dislike/health_condition/birthday/anniversary/other`）：`has_pet→养了宠物`、`worries_about→担心`、`has_interview→有面试`、`location→所在地`…
- `normalize_predicate(pred: str) -> str` — `strip().lower()` 后过 `_PREDICATE_ALIASES`，未知谓词原样返回（**不丢信息**）。
- `build_embedding_text(subject: str, predicate: str, object_: str) -> str` — 产出中文自然串用于嵌入。规则：`gloss = _PREDICATE_ZH.get(normalize_predicate(pred), pred)`；返回如 `f"用户{gloss}：{object_}"`（`object_` 本身携带中文内容，如「一只叫年糕的猫」；宠物查询里「宠物」经 gloss「养了宠物」进入嵌入串，与查询词面/语义对齐）。subject 非 "user" 时前缀带上。

单测 `backend/tests/unit/ss02_memory/test_predicate_vocab.py`：`normalize_predicate("concerned_about")=="worries_about"`；`build_embedding_text("user","has_pet","一只叫年糕的猫")` 含「宠物」；未知谓词透传。

## 二、Path A — `workers/memory_encoder.py::write_facts_to_l3`

- 进函数先 `pred = normalize_predicate(fact["predicate"])`，**去重 SELECT（:232-243）与落库都用 canonical `pred`** → 同义谓词命中同一行、走 REINFORCE（`confirmation_count += 1`、抬 confidence），不再分裂。
- CREATE 分支：`semantic_vector = await _embed_fact_text(build_embedding_text(subject, pred, object))`（替换当前对 `literal_text` 的嵌入，`memory_encoder.py:276`）。`literal_text` 仍按 `f"{subject} {pred} {object}"` 存（展示串不变，仅谓词变 canonical）。
- REINFORCE 补嵌入分支（`:251-254`）：改成 `build_embedding_text(existing_fact.subject, existing_fact.predicate, existing_fact.object)`，不再嵌 `literal_text`。

## 三、Path B — `ss02_memory/extractor/writer.py`

- `_handle_create`(:222) 与 `_handle_supersede`(:317) 的 `_embed_literal(...)` 调用，改为嵌 `build_embedding_text(subject, attribute.value, value)`。`literal_text` 格式不变。Path B 谓词已是闭合枚举，无需 alias 归一（但 `_PREDICATE_ZH` 需含这 15 个枚举的 gloss，见第一节）。

## 四、存量数据修复（operator 运行，非本仓 CI）

1. **合并存量重复事实** — 新脚本 `backend/heart/scripts/dedupe_facts.py`（默认 dry-run，`--apply` 落库）：
   - 按 `(user_id, character_id)` 取 `is_active` 事实；`normalize_predicate` 后按 `(subject, canonical_predicate)` 分组，并合并共享 `(subject, object)` 的组。
   - 保留 `(confidence, confirmation_count)` 最高者为 survivor：写 canonical predicate、累加 `confirmation_count`/`mention_count`、`build_embedding_text` 重嵌；败者软删（`is_active=False` + `superseded_by_id=survivor.id`，与 `models.py:252-253` 约定一致）。
2. **全量重嵌** — 改 `backend/heart/scripts/backfill_embeddings.py`：
   - L3 取文本 lambda 从 `f.literal_text` 改为 `build_embedding_text(f.subject, f.predicate, f.object)`（`:83`）。
   - 加 `--reembed-all` 开关：置位时去掉 `FactNode.semantic_vector.is_(None)` 过滤（`:68`），重嵌**所有** active 事实以吃到新嵌入文本；不置位维持"只补 NULL"旧行为。

## 五、测试（本仓，`bash scripts/ci.sh` 必绿）

- 新 `test_predicate_vocab.py`（见第一节）。
- 扩 `backend/tests/unit/test_memory_encoder_worker.py`：
  - `concerned_about` 写入时归一到 `worries_about`，命中既有行走 REINFORCE、**不新增行**。
  - CREATE 时断言传给 embedder 的文本是 `build_embedding_text` 的中文串（含 gloss，如「养了宠物」/「宠物」），而非 `"has_pet"`。
- backfill 单测：`--reembed-all` 放宽过滤且用 `build_embedding_text`。
- 既有 fixture（`literal_text="user has_pet …"` 等 ~12 处）**无需改**——本方案不改 `literal_text` 格式。

## 六、不在本次范围（如实登记，不静默）

- **BUG-3** 角色硬编码 / UGC：大型架构重构，独立规划。
- **P6 EMAIL_PROVIDER 未配置**、**PWA 需 HTTPS**、**稳定性/并发 BLOCKED 项**：属运维/环境配置，非代码缺陷。
- **可选后续硬化**（不做）：复活关键词检索（填充 `QueryContext.keywords` + 中文分词）、调大 VectorRetriever 每层 L3 取数上限。向量对齐修复已足够，力量来自 `select_top_k` 对高置信 L3 的强制包含。

---

## 执行与治理（按 `.claude/CLAUDE.md`）

单个聚焦 PR：`fix/memory-recall-vocab`，base=main。含：共享词表模块 + 两条写入路径 + backfill 开关 + dedupe 脚本 + 测试。`bash scripts/ci.sh` 绿后 push、`gh pr create`、squash 合并即删分支。提交尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`，PR body 尾 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`。

## 验证

1. **本仓**：`bash scripts/ci.sh`（新旧单测全绿）。
2. **Operator（合并后在测试库跑一次）**：
   - `python -m heart.scripts.dedupe_facts --apply`（合并存量同义谓词行）
   - `python -m heart.scripts.backfill_embeddings --reembed-all --apply`（全量重嵌新对齐文本）
3. **复现回归**：
   - MEM-01：重跑「年糕」链路，追问宠物名应答「年糕」。
   - MEM-03：追问「最担心什么」应一致指向「自我介绍」，不再分裂/答非所问。
4. **诚实口径**：MEM-01 最终关闭需 DB 环境实跑复现确认；MEM-03 的具体应答还取决于 LLM 排序选择，修复降低碎片化后须重验，不能仅凭单测判定关闭。
