# 记忆 / 上下文系统修复方案（供 Mimo 执行）

> ## ✅ 已全部实现并合并 main（2026-07-06）——本文件为历史工单，勿再据此重做
> PR1→**#87** · PR2→**#89** · PR3→**#90** · PR4→**#91/#92/#93/#94**。
> 因此下文中所有"现在时"的坏状态断言均**已过时**（已修复），例如：
> `retrieve() 从不调用 reinforce()`（已回写）、`semantic_vector 零命中/语义召回是死的`（已写入+已接线，
> 本地已回填并实测 `vector` 策略生效）、`L2 情绪/重要性硬编码`（已用真实 VAD+多信号）、
> `EmotionEvent 永不落库`（已持久化）、`RECENT_HISTORY_LIMIT=40`（已改 50）、`EmbeddingService 无实现`
> （`backend/heart/infra/embeddings.py` 已存在）。
> 仅 P2 项按计划保留为"设计如此/非 bug"。启用/操作见 [`docs/EXECUTION_MANUAL.md`](EXECUTION_MANUAL.md)。


> 依据：`docs/TEST_RESULTS.md` 8 个问题 + 实际代码走查（非推断）。
> 结论先行：**短期上下文（最近 40 条注入）是好的**（测试 1/3/5 通过）；
> 8 个"问题"里，真正的 bug 集中在 **记忆召回链路** 和 **冷路径 L2 写入**，
> 有几个是"设计如此/非 bug"，下文逐条标注。

---

## 0. 一张图看懂现状

一个 turn 实际发生的事（`routes_chat_ws.py` → `orchestrator.py` → `composer/service.py`）：

```
用户消息
  │
  ├─(A) 注入最近 40 条 chat_messages 到 prompt.history   ← 短期上下文，工作正常
  │       routes_chat_ws.py:27  RECENT_HISTORY_LIMIT = 40
  │
  ├─(B) composer 调 memory_service.retrieve()            ← 长期召回，基本失效
  │       composer/service.py:543  QueryContext(query_text="")  无 embedding
  │       → VectorRetriever 直接 return []（无 query_embedding）
  │       → 且 DB 里 semantic_vector 从没被写过（全库无 embedding）
  │       → 实际只有 RecencyRetriever(L2, 72h) + IdentityLookup(L4) 生效
  │       → retrieve() 从不调用 reinforce() → recall_count 永远 0
  │
  └─(C) 冷路径 fire-and-forget                            ← L2/L3 写入
          orchestrator.py:711 _cold_path_memory_encode
          - 只编码 user_message（assistant 回复不进记忆）
          - 直接插一条 L2 EpisodicMemory：
              emotional_peak = {valence: sentiment, arousal: 0.5}  ← 硬编码
              importance_score = max(0.3, abs(sentiment))          ← 硬编码
              scene_context 不设置                                  ← null
              semantic_vector 不设置                                ← null
          - queue_llm_encoding() 进 L3 抽取队列（异步 worker 处理）
```

**根因归纳（3 条主线）：**

1. **语义召回层是死的**：全库从不写 `semantic_vector`，热路径也从不算 query embedding。
   → L3 事实无法按语义召回，只能靠 72h recency（L2）和 L4 强制注入。
   （这是问题 1 的核心机制）
2. **召回不回写**：`MemoryService.retrieve()` 违反自身注释里的 INV-M-4，从不 `reinforce()`。
   （问题 5）
3. **L2 冷路径用假数据**：情绪/重要性硬编码、场景缺失、只存用户侧、无 embedding。
   （问题 3/4/6，部分 7）

---

## 1. 逐问题根因 + 修复（按优先级）

### 🔴 P0-1｜长期记忆召回失效（对应问题 1、部分 5）

**现象**：第 1 条"猫叫年糕"，50 条后追问答成"六子"。

**根因（实证）**：
- `web`/`orchestrator` 把最近 **40** 条注入 prompt（`routes_chat_ws.py:27`）。第 1 条早已超出 40 窗口。
- 超窗后唯一指望是 `memory_service.retrieve()`。但：
  - `composer/service.py:543-547` 传 `QueryContext(query_text="")`，**无 embedding、无 keywords**。
  - `retriever/vector.py:68` `if query_context.query_embedding is None: return []` → **向量召回永远空跑**。
  - 全仓 `grep 'semantic_vector ='` **零命中** → L2/L3 从没写过 embedding，即使传了 query embedding 也匹配不到。
  - 实际只剩 `recency.py`（L2，近 72h，按 created_at desc）+ `identity.py`（L4）。
  - 冷路径给**每条**用户消息都建一条 L2 episode（`orchestrator.py:784`）。50 条消息 = 50 条 L2，全在 72h 内，recency 打分最旧的"年糕"最低 → top_k=5 里永远排不进 → 不进 prompt → 模型幻觉"六子"。

**修复（三选一，按投入递增；建议至少做 A+B）**：

- **A. 加大短期窗口 + 兜底（最小改动，立刻见效）**
  - `routes_chat_ws.py:27` `RECENT_HISTORY_LIMIT = 40 → 50`（与文档"最近 50 条"对齐，当前文档/代码不一致）。
  - 说明：只治标，>50 条仍丢。

- **B. 修复 recency 召回不会淹没关键事实**（治本第一步，不依赖 embedding）
  - 让 `RecencyRetriever` 的打分不要只看时间：`recency.py:108` 的 `score_breakdown` 已经带了 `importance`，但由于冷路径把 importance 全写成 0.3（见 P1-1），recency 权重 0.15 下所有条目几乎同分。**先修 P1-1**，让重要消息 importance 高，才能在 top_k 里胜出。
  - 或：`RecencyRetriever` 增加 `window_hours` 到更大，并让 orchestrator 冷路径**不要给每句闲聊都建 L2 episode**（见 P2-2），减少噪声条目。

- **C. 真正启用语义召回（治本，工作量最大）**
  1. 落地一个 `EmbeddingService`（当前只有引用无实现）。可用 DeepSeek/OpenAI/本地模型；`MemoryService.__init__` 已预留 `embedding_service` 参数。
  2. `wiring.py:359 get_memory_service` 注入 `embedding_service`。
  3. **写入端**：冷路径建 L2 episode（`orchestrator.py:784`）和 Writer 建 L3 FactNode（`extractor/writer.py:203`）时，计算并写 `semantic_vector`。
  4. **查询端**：`composer/service.py:543` 用当前 `user_message`（可拼最近几轮）算 query embedding，填进 `QueryContext.query_embedding` / `query_text` / `keywords`。
  5. 给存量数据补 embedding 的一次性回填脚本。

> 建议：先 **A + B + P1-1**（几十行，立刻缓解），语义召回（C）作为独立 PR 跟进。

---

### 🔴 P0-2｜召回从不回写 recall_count（问题 5）

**现象**：所有记忆 `recall_count=0`、`last_recalled_at=null`。

**根因（实证）**：`service.py:223 retrieve()` 的 docstring 写着 "INV-M-4: Updates recall tracking"，但函数体**从头到尾没有调用 `reinforce()`**。`reinforce()`（`service.py:637`）实现是好的，只是没人调它（读路径没调，orchestrator 也没调）。

**修复**：
- 在 `MemoryService.retrieve()` 返回前，对本次命中的 `memories`（L2/L3）调用 `reinforce(memory_ids, trigger)`：
  ```python
  # service.py，retrieve() 组装完 retrieved 之后、return 之前
  hit_ids = [m.memory_id for m in retrieved if m.memory_type in ("L2", "L3")]
  if hit_ids:
      await self.reinforce(
          hit_ids,
          ReinforcementTrigger(trigger_type="recall_no_objection", context="auto_recall", boost=0.0),
      )
  ```
  - `boost=0.0`：只记 recall_count/last_recalled_at，不无脑抬 importance（避免召回即升权的正反馈失控）。
- **注意事务**：热路径里 `retrieve()` 用的是 WS 的 `async with AsyncSession(...) as db`（`routes_chat_ws.py:410`），该 session 不会自动 commit。`reinforce()` 内部只 `flush`。需确认这条 session 在 turn 结束时 commit；若不 commit，reinforce 会随 session 关闭丢失。建议：在 `_run_orchestrator` 那个 `async with` 块结束前显式 `await db.commit()`，或让 `reinforce` 写入走冷路径独立 session。
- **L4 不 reinforce**（L4 不衰减、不需要，避免污染 identity 表）。

---

### 🔴 P0-3｜L4 身份记忆脏数据 "什么吗"（问题 2）

**现象**：`L4 {key:"name", value:"什么吗", disclosure_context:"我叫什么吗"}`。

**根因（实证）**：
- Fast encoder 的身份识别**已废弃**（`encoder/fast.py:104` 恒返回 `[]`），**不是**它误判。
- L4 只能由 L3 事实晋升而来（`promoter.py:_promote_one` 或 `service.py:promote_to_l4`），`value = fact.object`。
- L3 事实由 LLM 抽取 → Resolver → Writer 产生。Resolver **已有**拦截：`resolver.py:109` 对 `kind in {rhetoric, question, hypothetical}` 直接 REJECT。
- 所以 "什么吗" 能落库，说明 **LLM extractor 把疑问句"我叫什么吗"错标成了 disclosure（kind=disclosure, value="什么吗"）**，绕过了 Resolver 的 kind 拦截。

**修复（两层，都要做）**：
1. **抽取层（治本）**：`extractor/prompt_builder.py` 的抽取 prompt 增加明确约束：
   - 疑问句 / 反问 / 假设（"我叫什么""你猜我是谁""如果我是…"）必须标 `kind=question/hypothetical`，禁止当 disclosure。
   - 补 few-shot 反例：`"我叫什么吗" → kind=question, 不产出 name 事实`。
2. **Resolver 防御式校验（兜底）**：`resolver.py:_resolve_one` 在 CREATE/SUPERSEDE 前加 value 合法性校验：
   - identity 类属性（name/nickname/birthday…）的 `value` 若命中疑问词表（什么/谁/哪/吗/呢/几…）或就是代词，直接 REJECT。
   - 建议实现为 `_is_implausible_identity_value(attribute, value)`，命中则 `DecisionType.REJECT`。
3. **数据清理**：对已存在的脏 L4 做一次性清理（`demoted_at` 置位或 `user_initiated_forget`，遵守 M-1 不物理删除）。同时清其来源 L3 `is_corrected=True`，防止再次晋升。

---

### 🟡 P1-1｜L2 情绪/重要性硬编码（问题 3、4）

**现象**：L2 情绪几乎全是 `arousal:0.5, valence:0`；importance 几乎全 0.3。

**根因（实证）**：`orchestrator.py:784-806` 冷路径直接造 L2 episode：
```python
emotional_peak={"valence": signals.sentiment, "arousal": 0.5, ...}  # arousal 恒 0.5
importance_score=max(0.3, abs(signals.sentiment))                    # 中性→0.3
```
`signals.sentiment` 来自词典法 fast encoder（`encoder/fast.py:114`），大多数中性句 = 0。且**完全没用** ss03 的真实情绪分析结果。

**修复**：
- 冷路径在建 episode 前，读取 ss03 的真实情绪上下文（orchestrator 已持有 `_emotion_service`，且本 turn 已在 `_update_emotion` 里更新过）：
  ```python
  ecb = await self._emotion_service.get_context_block(user_id, character_id)
  vad = ecb.get("vad", {})
  emotional_peak = {"valence": vad.get("valence", 0.0),
                    "arousal": vad.get("arousal", 0.3), "label": ...}
  ```
- importance 用多信号：情绪强度 + 是否命中身份/事实 hint（`signals.detected_keywords`）+ 消息长度等，给出区分度，而非 `max(0.3, |sentiment|)`。
- **注意时序**：`_update_emotion` 在 compose 前跑（`orchestrator.py:235`），冷路径在 turn 末尾 fire（:291），此时情绪状态已是最新，可安全读取。

---

### 🟡 P1-2｜情绪事件表为空 + 情绪几乎不变（问题 8 的一半）

**现象**：`emotion_events` 表为空；VAD 基本不动。

**根因（实证）**：
- `wiring.py:137 get_emotion_service` 构造 `EmotionService()` **不传 db_session**（进程单例）。
- `service.py:276` 持久化 EmotionEvent 的分支是 `if self._db is not None:` → **永远为 None → 永不落库**。
- 且 `orchestrator.py:525 _update_emotion` 把 `user_emotion_vad` **写死**成 `{valence:0, arousal:0.3, dominance:0.5}`，没把 fast encoder 的真实 sentiment 传进去 → 情绪传染输入恒定 → VAD 几乎不变。

**修复**：
1. 给 EmotionService 一个可持久化的 DB 通道。两种做法：
   - **推荐**：把 EmotionEvent 落库改成"冷路径独立 session"（像 memory 冷路径那样 `_get_session_factory()`），避免把进程单例和请求 session 绑定；或
   - 改为请求级构造 EmotionService（传 db_session），但要处理 state 缓存的跨请求语义。
2. `orchestrator.py:_update_emotion`：把真实用户情绪传进去。fast encoder 的 sentiment 已在冷路径算过，可提前算一次共享，或在此处基于 `req.user_message` 快速取 sentiment 填 `user_emotion_vad.valence`。

---

### 🟢 P2-1｜scene_context 缺失（问题 6）

**根因**：`orchestrator.py:784` 建 episode 不设 `scene_context`；`QueryContext.scene_context`（`retriever/base.py:43`）也从不填。
**修复**：冷路径写 episode 时用 relationship phase / 时段 / 最近话题生成简短 scene_context（如 "深夜倾诉""日常问候"）。非阻塞、低优先。

---

### 🟢 P2-2｜L2/L3 不一致（问题 7）— **大部分是设计如此**

**根因（实证）**：
- L2：冷路径对**每条**用户消息同步直插（`episode_summary=user_message[:200]`）。
- L3：只对带 hint 的消息、经 LLM 异步 worker 抽取才产出事实（受 `mode.is_llm_enabled()` 门控 + ~5min 延迟）。
- 两者触发条件、内容模型（原句 vs 结构化事实）、时机都不同 → 表面不一致是**结构性正常现象**，不是数据损坏。

**建议**（可选，非必须）：
- 若要一致性，改为 L2 也走"consolidation 聚合"而非每句直插（当前 `orchestrator.py:780` 注释明说 "bypass consolidation"）。这是较大的架构调整，建议单列 issue，不在本次修复。
- 至少：把"每句都建 L2"改成"有信息量才建"（长度/hint/情绪阈值），既降噪又缓解 P0-1。

---

### 🟢 P2-3｜drifting 状态（问题 8 的另一半）— **非 bug**

**根因（实证）**：`drifting` 是 `ss04_relationship/special_states.py:27` 的正常特殊态，`service.py:275` 在 `days_since_last` 超阈值时进入，属**设计预期**（久未互动→关系漂移）。测试账号有时间间隔，出现 drifting 合理。
**处置**：无需修复。若产品上不希望短期不活跃就 drift，调阈值即可（不属本次记忆修复范围）。

---

## 2. 优先级与批次建议

| 批次 | 内容 | 覆盖问题 | 说明 |
|---|---|---|---|
| **PR1（快速止血）** | P0-2 reinforce 回写 + P1-1 L2 真实情绪/重要性 + P0-1.A 窗口 40→50 + P2-2 降噪 | 5,3,4,1(部分) | 改动集中在 `service.py`/`orchestrator.py`/`routes_chat_ws.py`，几十行，风险低 |
| **PR2（脏数据）** | P0-3 extractor prompt + resolver 校验 + L4 清理脚本 | 2 | 独立，含一次性数据清理 |
| **PR3（情绪落库）** | P1-2 EmotionEvent 持久化 + 真实 user_emotion_vad | 8(一半) | 注意 session 归属 |
| **PR4（语义召回，最大）** | P0-1.C EmbeddingService + 写/查 embedding + 回填 | 1(治本) | 单独立项，工作量最大 |

> ⚠️ 遵守 `.claude/CLAUDE.md`：每个 PR 独立 base=main、7 天内可合、单人 open PR ≤3。不要把 4 个批次堆到一个分支。

---

## 3. 关键文件 / 行号索引（走查确认）

| 位置 | 事实 |
|---|---|
| `backend/heart/api/routes_chat_ws.py:27` | `RECENT_HISTORY_LIMIT = 40`（文档写 50，不一致）|
| `backend/heart/api/routes_chat_ws.py:41-66` | 注入最近 40 条到 history（短期上下文，OK）|
| `backend/heart/ss07_orchestration/orchestrator.py:711-829` | 冷路径 encode：只存 user 侧、硬编码情绪/重要性、无 scene/embedding |
| `backend/heart/ss07_orchestration/orchestrator.py:525` | `user_emotion_vad` 写死常量 |
| `backend/heart/ss05_composer/service.py:543-552` | `QueryContext(query_text="")` 无 embedding |
| `backend/heart/ss02_memory/service.py:223-334` | `retrieve()` 从不调用 `reinforce()` |
| `backend/heart/ss02_memory/service.py:637-680` | `reinforce()` 实现存在但无人调用 |
| `backend/heart/ss02_memory/retriever/vector.py:68` | 无 query_embedding 即 `return []` |
| （全仓）`grep 'semantic_vector ='` | **零命中**：从不写入 embedding |
| `backend/heart/ss02_memory/extractor/resolver.py:109` | 已拦 question/rhetoric/hypothetical，但依赖 LLM 正确打 kind |
| `backend/heart/api/wiring.py:137` | `EmotionService()` 不传 db → 事件永不落库 |
| `backend/heart/api/wiring.py:359` | `MemoryService` 不传 embedding_service |
| `backend/heart/ss04_relationship/special_states.py:27` | `drifting` 为设计预期，非 bug |

---

## 4. Mimo 执行 Prompt（PR1 快速止血，可直接复制）

```
你在 Heart 仓库（对外名 yuoyuo）修复记忆系统 PR1「召回回写 + L2 真实情绪 + 降噪」。
分支 fix/memory-recall-l2，base=main。严格按 docs/MEMORY_FIX_PLAN.md 的 P0-2 / P1-1 / P0-1.A / P2-2。

1) service.py retrieve()：命中的 L2/L3 记忆在 return 前调用 reinforce(hit_ids,
   ReinforcementTrigger("recall_no_objection","auto_recall",boost=0.0))；L4 不 reinforce。
   确保这条 db_session 在 turn 末尾 commit（否则 flush 丢失）——在 routes_chat_ws.py
   _run_orchestrator 的 async with 块结束前显式 await db.commit()，或让 reinforce 走独立 session。

2) orchestrator.py _cold_path_memory_encode()：建 L2 EpisodicMemory 前，读
   emotion_service.get_context_block(user_id,character_id) 的真实 vad，填 emotional_peak；
   importance_score 改为多信号（情绪强度 + 是否命中 detected_keywords + 长度），去掉恒 0.3。

3) orchestrator.py _update_emotion()：user_emotion_vad 用 req.user_message 的真实 sentiment
   （复用 fast encoder / 词典），不要写死 {valence:0,arousal:0.3}。

4) routes_chat_ws.py:27 RECENT_HISTORY_LIMIT 40 → 50（对齐文档）。

5) 降噪：冷路径不要对每条用户消息都建 L2 episode；加阈值（消息长度 / 有 hint / |sentiment|>0）
   才建，闲聊不建。

约束：不改 semantic_vector / embedding 相关（留 PR4）；补/改单测覆盖 reinforce 被调用、
L2 情绪非硬编码、window=50；ci.sh 全绿；alembic 无新迁移；开 PR 写清 base=main。
```

---

**编写时间**：2026-07-05
**依据**：TEST_RESULTS.md + backend 实际代码走查（git HEAD，fix/commercial-acceptance 分支）
