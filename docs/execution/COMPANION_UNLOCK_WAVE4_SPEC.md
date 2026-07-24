# Wave 4 设计规格 — Companion 解锁 + 相遇摘要（草案，待产品拍板）

> **状态**：设计草案，**不含实现**。Wave 3（剧情邀约卡）已随本 PR 落地；Wave 4 因存在硬依赖缺口（见 §1）暂缓实现，先出本文档定义清楚再动工。
>
> **背景**：`docs/UIdesign.md` 五节「解锁角色流程」描述的视觉小说式解锁：
> `剧情中遇见 → Character 页「相遇中」卡 → 达成关键节点/结局 → 解锁转正 → 长期陪伴`，
> 记忆策略是「只写入一条结构化『相遇摘要』，不导入完整剧情聊天记录」。

---

## 1. 为什么 Wave 4 现在做不了（硬依赖缺口）

调查（`git ls-tree` + 读实际代码，非推断）确认了三个缺口，任一都足以阻塞 Wave 4(b)：

| # | 缺口 | 证据 | 影响 |
|---|------|------|------|
| G1 | **剧情引擎没有「结局/完成」事件** | `story_runs.status` CHECK 仅 `active`/`ended`/`deleted`（`042_story_scenarios.py`）。`ended` = 被新 run 顶替/关闭，**不是**叙事结局。SS09 无结局检测、无完成回调。 | 「达成结局 → 转正」没有触发点可挂。 |
| G2 | **scenario 与 character 无任何关联** | 全代码库无 `character_id`↔`scenario` 外键/join。scenario 的「角色」只作为自由文本活在 `gm_system_prompt` 里。唯一的 `character_id=f"story:{scenario.id}"`（`service.py:326`）是喂给安全分类器的合成串，非外键。 | 「哪个剧情解锁哪个角色」无数据可依。Wave 3 的 `character_story_hooks` 是**第一个**真实关联，但它是「角色邀你去玩剧情」，方向与「剧情解锁角色」相反。 |
| G3 | **story 与 memory 零集成** | `grep memory\|MemoryService\|FactNode\|IdentityMemory` 在 `ss09_story/` 无命中。story run 与 SS02 记忆完全隔离。 | 「相遇摘要写 L3/L4」没有现成写入路径。 |

补充：`story_scenario_unlocks`（`043_story_unlock.py`）是**付费解锁 scenario 访问权**的收费表（一次性 80 悠悠币），与「角色转正陪伴」是**完全不同的轴**，不能复用。名字是 false friend。

### 结论
Wave 4 是一个**新子系统**，不是「挂个 hook」。且 4(a) 的 `companion_status` 三态表若无 4(b) 填数据就是空表——**Wave 4 本质上是全有或全无**，必须先定义清楚「转正」语义。

---

## 2. 待产品拍板的问题（实现前必须回答）

**Q1. 「转正」到底由什么事件触发？** 三个候选：
- **(a) GM 结局标记**：剧情脚本在结局回合输出一个结构化标记（如 `【结局】` 或 JSON `{"ending": true}`），后端 WS 解析到就置 `story_runs.status='completed'`。优点：贴合「达成结局」原意。成本：需要脚本约定 + WS 解析 + 45 个已导入剧本回填标记。
- **(b) 用户显式操作**：剧情播放页加「结束这段故事」按钮，用户主动结算。优点：零脚本改动、确定性强。缺点：不是「达成结局」而是「用户说结束」。
- **(c) 阈值触发**：玩够 N 回合 / 计费满 M 分钟即视为「相遇达成」。优点：最简单。缺点：与「结局」语义最远，可能在剧情中途误触发。

**Q2. 一个 scenario 解锁「哪个」角色？** scenario 是多 NPC 的（如「联姻对象」有 3 个男主）。需要一张 `scenario_character_map(scenario_id, character_id, role)` 显式声明「玩通这个剧情解锁 character X」。由谁维护？运营手配 or 脚本导入时带？**且被解锁的 character 必须先存在于 `characters` 目录表**——目前 45 个剧本里的 NPC 都不是 `characters` 表里的行，需要先决定「剧情 NPC 转正为可陪伴角色」时如何建 `characters` 行 + `soul_specs`。

**Q3. 相遇摘要写 L3 还是 L4？**（见 §4 技术细节，两者约束不同，需要产品决定这条记忆的「神圣程度」。）

**Q4. 转正是否可逆 / 可重复？** 同一 scenario 玩两遍、或多个 scenario 都指向同一 character，摘要写一条还是多条？（影响唯一约束设计。）

---

## 3. 提议的数据模型（待 Q1/Q2 定案后细化）

### 3.1 `user_character_companion_state`（新表，支撑 4(a) 三态）
```sql
CREATE TABLE user_character_companion_state (
    user_id            UUID NOT NULL,
    character_id       TEXT NOT NULL,
    companion_status   TEXT NOT NULL DEFAULT 'encountered'
                          CHECK (companion_status IN ('locked','encountered','companioned')),
    encountered_via_run_id UUID REFERENCES story_runs(id),  -- 从哪个 run 相遇
    encountered_at     TIMESTAMPTZ,
    companioned_at     TIMESTAMPTZ,                          -- 转正时间
    PRIMARY KEY (user_id, character_id)
);
```
- **读侧接入点**：`routes_companions.py:219` 现在硬编码 `"companion_status": "companioned"`。Wave 4 加第 5 个 batch 查询（keyed on `visible_ids`），把 219 换成 `state_map.get(e.id, "companioned")`——**默认 `companioned` 保留现有内置/UGC 行为**，只有走过相遇流程的角色才有非默认态。
- **`source` 字段**（`routes_companions.py:214`）同时可从 `built_in`/`user_created` 扩展出 `story_encounter`（design 六节 VM 里的枚举），数据源就是本表的 `encountered_via_run_id IS NOT NULL`。

### 3.2 `scenario_character_map`（新表，补 G2）— 待 Q2 定案
```sql
CREATE TABLE scenario_character_map (
    scenario_id   UUID NOT NULL REFERENCES story_scenarios(id),
    character_id  TEXT NOT NULL,
    role          TEXT,        -- 'lead' / 'love_interest' / ...
    PRIMARY KEY (scenario_id, character_id)
);
```

### 3.3 `story_runs.status` 扩展 — 待 Q1 定案
若选 Q1(a)/(b)：CHECK 加 `'completed'`，并在完成时机写 `user_character_companion_state`（`encountered`→`companioned`）+ 触发相遇摘要写入。

---

## 4. 相遇摘要写记忆（4(b) 技术细节）

SS02 **没有**「写一条结构化 fact」的公开方法——现有 Write API（`MemoryService`）全是 turn 驱动的：
`encode_fast(turn)`（仅 L1）、`queue_llm_encoding(event)`（异步抽取队列）、`promote_to_l4(fact_id)`（只能提升**已存在**的 L3，且要求 `importance>=0.85`）。正常建 L3 走 `Extractor→Resolver→Writer` 管线，chat-turn 耦合 + LLM 门控。

**唯一的「非 turn 直接 seed 记忆」先例**：`orchestrator.py:100` 的 `_create_user_message_episode` 直接构造 `EpisodicMemory`(L2) + `session.add()`。L3/L4 无等价 helper，但同样「构造 model + add + commit」可行。

### 提议：新增 `MemoryService.write_seed_fact(...)`
把直接构造的知识**留在 SS02**（不要让 story 层去 import ORM model）。两个落点二选一（对应 Q3）：

**选项 A — 写 L3 `FactNode`**（推荐，除非产品认为相遇是「神圣」级）
- 必填字段：`id, user_id, character_id, predicate, subject, object, literal_text, raw_evidence, confidence, emotional_charge, importance, state`（如 `"vivid"`），`source_turns` 默认 `[]`。
- `semantic_vector` 是 `Vector(1024)` 且 **nullable**——**embedding 可选**，无 embedding service 时留 NULL，fact 仍可被 recency/predicate 召回（只是非向量召回）。
- 建议 `importance=0.7~0.8`、`state="vivid"`。
- ⚠️ **`character_id` 陷阱**：抽取管线 `Writer` 把每条 fact 硬编码 `character_id="default"`（`writer.py:231/328`）。而召回按 `user_id + character_id` 过滤（`_enforce_user_isolation`, `service.py:1072`）。相遇摘要**必须**写真实被解锁角色的 id，否则召回不到。写入前需确认召回侧对 `"default"` 的处理，别踩同一个坑。

**选项 B — 写 L4 `IdentityMemory`**（若产品要「永不衰减的身份级事实」）
- 必填：`id, user_id, character_id, category, key, value, disclosed_at, sacred_reason, significance_score, promotion_trigger`。
- **硬约束**：`significance_score >= 0.85`（model CHECK）；`UNIQUE(user_id, character_id, key)`——重复转正必须 ON CONFLICT/upsert 否则报错（呼应 Q4）。
- L4 **无 embedding 列**，走 category/key 查找（`get_l4`, `service.py:483`）。

### 摘要内容（design 五节原意）
> 不导入完整剧情聊天记录。只写入一条结构化「相遇摘要」，例如：
> 「你们在《雨停，天晴》中相遇；她选择留下来继续陪你。」

摘要文本可取 `story_runs.summary`（剧情引擎已维护的滚动摘要）截断，或用固定模板 + scenario title 拼。**不要**塞 `story_messages` 全文（污染长期聊天记忆，正是 design 明令避免的）。

---

## 5. 分阶段实现计划（Q1–Q4 定案后）

| 阶段 | 内容 | 依赖 |
|------|------|------|
| 4.0 | 迁移：`user_character_companion_state` + `scenario_character_map` + `story_runs.status` 加 `completed` | Q2 |
| 4.1 | `routes_companions.py` 接真实 `companion_status`（batch 查询 + 换掉硬编码 219，默认兜底 `companioned`）+ `source` 扩展 `story_encounter` | 4.0 |
| 4.2 | 转正触发：按 Q1 选型实现完成事件检测（GM 标记解析 / 结束按钮 / 阈值），置 `companioned` | Q1, 4.0 |
| 4.3 | `MemoryService.write_seed_fact()` + 转正时调用写相遇摘要（L3 或 L4，按 Q3） | 4.2, Q3 |
| 4.4 | 前端：「相遇中」卡（`companion_status==='encountered'`）、转正动画/文案、「共同回忆」区接相遇摘要（CharacterPage archive panel 已留 TODO(Wave 4) 锚点） | 4.1–4.3 |

**单独 PR**（CLAUDE.md：Wave 4 最高风险，独立 PR）。触碰 SS04 只读、SS02 新增写方法（不改现有管线）、SS09 加完成事件。

---

## 6. 风险与铁律对齐

- **禁止 `except Exception:` 静默**：转正写记忆失败必须 `logger.exception + raise`，不能吞成「看着转正了其实没写记忆」。
- **迁移幂等**：所有新表 `IF NOT EXISTS`；回填/backfill 独立 UPDATE；无业务 import（raw SQL）。
- **`character_id="default"` 召回陷阱**（§4）：写入前实测召回能命中真实 character_id，否则相遇摘要写了也召不回，等于没写。
- **不平行实现**：动 SS02/SS04/SS09 前先 `git ls-tree` 核查现状（本文档已做，见 §1 证据列）。
- **测试**：`write_seed_fact` 单测（必填字段、embedding NULL 路径、L4 唯一约束 upsert）；转正触发的集成测试（完成事件 → 状态变更 → 记忆行落库 → 召回命中）。

---

## 附：本轮（Wave 3）已交付，供对照
- `character_story_hooks` 表（迁移 047）+ 种子 hook（rin ↔ 《雨停，天晴》）。
- `/api/companions` 返回 `available_story_hook`（后端按 stage rank + intimacy 阈值判定资格，cold_war 排除）。
- 前端 `StoryInviteCard`（chat 页事件卡 + CharacterPage 档案面板），CTA 走 `getActiveRun` → 续玩 `/story/:runId` 或新开 `/explore/:scenarioId`，dismissal 走 localStorage cooldown。

