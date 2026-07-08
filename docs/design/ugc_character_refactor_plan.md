# 角色 UGC 架构重构规划

> 状态：规划（大型 epic，分阶段独立 PR，需 HUMAN 拍板）
> 来源：`docs/TEST_REPORT_2026-07-08.md` SUG-3 / 登记为 BUG-3
> 最后更新：2026-07-08

---

## 背景与目标

当前两个角色（神无月凛 `rin`、桃乐丝 `dorothy`）的人设、语气、关系阶段模板、仪式模板部分数据驱动、部分硬编码。目标：支持**用户自定义角色（UGC）**——自定义名称/头像/人设、语气风格、关系阶段模板、仪式模板。

**好消息**：规范化的 Soul Spec 机制已存在且**运行时数据驱动**——
- `soul_specs/<id>/vX.Y.Z.yaml` 由 `ss01_soul/registry.py` 的 `SoulRegistry.load_all()` 启动加载，`ss01_soul/schema_validator.py`（Pydantic `SoulSpec`）校验；
- 经 `ss05_composer/service.py` + `ss01_soul/anchor_injector.py` 注入 system prompt；
- 关系阶段**阈值**已从 spec 的 `relational_template` 读取（`ss04_relationship/stage_engine.py`），`api/wiring.py` 已对所有已注册角色生效。

即 identity 解析链路 `character_id → SoulRegistry.get_soul() → SoulSpec → anchor block → prompt` 已经是 UGC-ready 的骨架。

---

## 障碍（UGC 的真正工作量）

1. **无 characters 目录表**——`character_id` 是各 per-user 表（`relationship_states`/`emotion_states`/`fact_nodes`/`chat_messages`/`sessions` …）上的自由文本，无 FK、无校验；`api/routes_chat_ws.py` 默认 `"rin"`。合法角色集隐式由「`soul_specs/` 目录 + 硬编码列表」决定。
2. **加载生命周期是「启动一次、进程内不可变」**——`load_all()` 只在 boot，`anchor_injector` 启动预编译全部 skeleton，无热加载（`reset_anchor_injector()` 有先例但仅测试用）。
3. **散落的硬编码 `{"rin":..,"dorothy":..}` 字典绕过 Soul Spec**（重构主战场）：
   - `ss06_inner_state/proactive_message.py`：`DIRECTIVE_TEMPLATES` / `_build_style_guide()` / `_resolve_character_name()` / `_check_anti_pattern()`
   - `ss06_inner_state/service.py`：`PROACTIVE_PERSONA`（L45）、`PROACTIVE_TEMPLATES`（L50，fallback 默认 `rin`）
   - `ss06_inner_state/inner_loop_worker.py`：ritual 模板（`_check_ritual_triggers`）
   - `ss06_inner_state/ritual_manager.py`：`SOUL_RITUAL_FLAVOR`（有 `_DEFAULT_RITUAL_FLAVOR` 兜底）
   - `ss06_inner_state/block_builder.py`：`if character_id == "rin" … elif "dorothy"`
   - 说明：这些内联 persona 是**刻意的成本优化**（避免在便宜的小时级内循环加载完整 Soul Spec）。UGC 下须改为从 Soul Spec 派生（预投影缓存以保留该优化）。
4. **前端目录硬编码**：`web/src/components/CharacterSelector.tsx` 的 `CHARACTERS` 数组、`web/src/stores/appStore.ts` 的 `CharacterId = 'rin' | 'dorothy'` 编译期联合类型，及 `chatStore.ts`/`useWebSocket.ts`/`data/uiContent.ts`/`CharacterPage.tsx` 多处引用（`taolesi→dorothy` 已有迁移先例可参考）。

---

## 分阶段路线图（每阶段独立 PR）

### C1 — 消灭硬编码（不改存储，先收敛）
给 Soul Spec schema 增补 compact 字段（如 `proactive_hint`、`ritual_flavor`、`display_name`），把「障碍 3」所有硬编码字典改为**从 Soul Spec 派生**（保留内循环便宜优化＝预投影缓存）。
- 此阶段 `rin`/`dorothy` 行为**不变**，作为回归安全网。
- 收益：新增内置角色不再需要改多处代码。
- 触及：`ss01_soul/schema_validator.py` + 两个 `soul_specs/*.yaml` + 上述 5 个 ss06 文件。

### C2 — characters 目录表 + 列表 API
- 新增 `characters` 表：`id`、`owner_user_id`、`visibility`（system/private/public）、`soul_spec` 版本指针、状态、创建时间。
- 新增 `GET /api/characters` 列表端点（当前 `routes_characters.py` 只有 per-user settings 子路由）。
- 在 `routes_chat_ws.py` / `routes_characters.py` 边界**校验 `character_id`**（现为无约束自由文本）。
- 存量 `rin`/`dorothy` 作为系统内置角色回填；per-user 表沿用同一字符串 key → **零数据迁移**。

### C3 — Soul Spec 来源与生命周期改造（风险最高）
- `registry.py` 从 DB / 对象存储读 spec（替代 `soul_specs/` 文件）；支持热加载 / 失效。
- UGC 提交的 spec 走 `schema_validator.py` 校验 + 安全审查（anti-pattern、越权词、注入防护）。
- **风险**：触及记忆/情绪/关系全链路的 `character_id` 语义与 Soul Spec 不可变性契约（`runtime_specs/01_*.md` P-4/P-10），需专门设计版本化与 Soul Drift 回归。

### C4 — 前端动态化
- `CharacterId` 联合类型 → 运行时列表；`CharacterSelector` / `chatStore` / `uiContent` 改为消费 `GET /api/characters`。

### C5 — UGC 创作 UI + 审核流
- 角色创建/编辑表单、可见性（私有/公开）、内容审核与举报。属独立大 epic。

---

## 建议

- **先落地 C1 → C2**（低风险、立即让「新增内置角色」变简单，且不动存储契约）。
- **C3 及之后再评审**——涉及不可变性契约与 drift 回归，需单独设计文档与充分测试。
- 每阶段独立 PR、base main；若需重写既有实现，PR 描述须写明「为什么放弃既有版本」（CLAUDE.md 平行实现禁令）。
