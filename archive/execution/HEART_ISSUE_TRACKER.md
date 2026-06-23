# Heart (心屿) — 问题汇总（Issue Tracker）

> 本文档列出所有已知问题，供其他 AI 模型直接修复。每个问题包含：文件位置、问题描述、修复建议。
> 按严重度排序：🔴 阻塞 → 🟠 高 → 🟡 中 → 🟢 低

---

## 🔴 阻塞级（不修不能用）

### 1. composer_memory_block_failed — ScoredMemory 缺少 reconstructed_text

**现象**：每轮对话都报错 `'ScoredMemory' object has no attribute 'reconstructed_text'`
**根因**：`ss05_composer/service.py:557` 访问 `m.reconstructed_text`，但 `ss02_memory/retriever/base.py:59` 的 `ScoredMemory` 数据类没有这个属性
**影响**：记忆块构建失败，降级为空记忆。LLM 能回复但缺少记忆上下文（不知道用户之前说过什么）
**日志**：`composer_memory_block_failed error="'ScoredMemory' object has no attribute 'reconstructed_text'`
**修复方案**：在 `ScoredMemory` 添加 `reconstructed_text: str = ""` 字段，或修改 composer 从 `m.memory.summary` / `m.memory.episode_summary` 取值
**代码位置**：`backend/heart/ss02_memory/retriever/base.py:59` 和 `backend/heart/ss05_composer/service.py:557`

### 2. encoder-worker 重启循环

**现象**：`heart-encoder-worker` 容器持续 Restarting (1)
**影响**：L2/L3 向量编码不工作，记忆召回（语义搜索）不可用。聊天本身不受影响。
**代码位置**：`backend/heart/workers/memory_encoder.py`
**排查方向**：`docker logs heart-encoder-worker` 查看退出码。可能是 OOM、model load 失败、DB 连接失败。
**Issue**：#48

### 3. 迁移 009 缺失（已修复，待合并）

**现象**：`alembic upgrade head` 在新数据库上崩溃，报错 `KeyError: '009_memory_l4_extras'`
**根因**：迁移 010 依赖 009，但 009 文件不存在（已被删除或未提交）
**修复**：已创建 `fix/migration-009-sa-column` 分支（PR #45），包含完整的 009 迁移文件
**状态**：PR #45 已开，等待合并

---

## 🟠 高优先级（影响核心功能）

### 4. E2E 会话写入竞态

**现象**：`/api/chat` 返回 200 后，立即查 DB 发现 `sessions.turn_count=0`
**根因**：session row commit 在 HTTP response 之后执行（fire-and-forget）
**代码位置**：`backend/heart/api/routes.py:171`（`await orchestrator.handle_turn()`）和 `backend/heart/ss07_orchestration/orchestrator.py:150`（`await self._session_manager.record_turn()`）
**修复方案**：把 `record_turn()` 移到 `handle_turn()` 返回之前（同事务 flush + commit）
**禁止**：禁止用 `await asyncio.sleep(0.5)` 创可贴
**Issue**：#47

### 5. fast_encoder 15 个测试失败

**现象**：`test_fast_encoder.py` 的 `TestIdentitySignals` 和 `TestDiverseSentences` 类共 15 个测试失败
**根因**：`IdentitySignal` 提取方式已废弃（`encoder/__init__.py:25` 标记 deprecated），但测试未更新
**代码位置**：`backend/tests/unit/test_fast_encoder.py`
**修复方案**：删除或重写 `TestIdentitySignals` 测试类，使用新的 `RegexHintsProvider` 方式

### 6. 迁移测试过期

**现象**：`test_migration_roundtrip.py` 全部 7 个测试失败
**根因**：测试硬编码期望 head=003，实际 head=010
**代码位置**：`backend/tests/integration/test_migration_roundtrip.py`
**修复方案**：更新测试中的 expected head 为 `010_memory_regex_shadow`

### 7. consolidator 测试导入阻塞

**现象**：`test_consolidator.py` 产生 15 个 collection-time ERROR
**根因**：`from heart.ss02_memory.models import ConsolidationJob` 在模块顶层执行，缺 pg-only 依赖时直接 fail
**代码位置**：`backend/tests/unit/test_consolidator.py`
**修复方案**：把 import 移到 fixture 内（lazy import），或把文件挪到 `tests/integration/`
**Issue**：#46

### 8. SS04 关系系统特殊状态未实现

**现象**：`service.py:297` 有 TODO 注释
**位置**：`backend/heart/ss04_relationship/service.py:297`
**内容**：`# TODO: Implement DRIFTING, COLD_WAR, REUNION state updates`
**影响**：冷战、漂移、复合等关系状态转换不工作
**修复方案**：实现 DRIFTING/COLD_WAR/REUNION 状态机逻辑

### 9. emotion_events 表为空 — 情绪事件未持久化

**现象**：查询 `emotion_events` 表返回 0 行，但 emotion 状态 API 返回正确数据
**根因**：`EmotionService` 更新了内存中的情绪状态，但没有将事件写入 `emotion_events` 表
**影响**：重启后情绪事件丢失，无法审计情绪变化历史
**代码位置**：`backend/heart/ss03_emotion/service.py`
**修复方案**：在 `process_turn()` 中添加 `emotion_events.insert()` 调用

---

## 🟡 中优先级（技术债务）

### 10. WebSocket 端点返回 404

**现象**：`curl http://localhost:8000/api/chat/ws` 返回 404
**影响**：WebSocket 实时聊天不可用（前端无法建立 WS 连接）
**代码位置**：`backend/heart/api/routes_chat_ws.py`
**修复方案**：检查路由注册，确保 `/api/chat/ws` 正确挂载

### 11. 4 个独立的 DeclarativeBase

**现象**：`ss02_memory/models.py`、`ss03_emotion/models.py`、`ss04_relationship/models.py`、`replay/__init__.py` 各自定义了自己的 `Base(DeclarativeBase)`
**影响**：可能导致 metadata 不一致、迁移冲突
**修复方案**：统一为一个共享的 `Base`，放在 `heart/core/base.py`

### 12. 两个 LLM Provider 树

**现象**：`infra/llm/`（router.py + config.py）和 `infra/llm_providers/`（base/deepseek/fake/registry）两套代码
**影响**：维护负担，容易改一处忘另一处
**修复方案**：保留 `infra/llm_providers/`，删除 `infra/llm/` 的冗余代码

### 11. JWT 算法不匹配

**现象**：AGENTS.md 说 RS256，实际 `core/config.py:103` 和 `core/auth.py:41` 用 HS256
**影响**：安全级别低于规范要求
**修复方案**：生成 RSA 密钥对，修改 auth.py 使用 RS256

### 12. FastAPI `on_event` 已废弃

**现象**：`api/main.py:188-189` 使用 `app.on_event("startup")` 和 `app.on_event("shutdown")`
**影响**：未来 FastAPI 版本可能移除
**修复方案**：迁移到 `lifespan` 上下文管理器

### 13. CORS 允许所有来源

**现象**：`api/main.py` 设置 `allow_origins=["*"]`
**影响**：开发环境可以，生产环境必须限制
**修复方案**：从环境变量读取允许的来源列表

### 14. wellbeing_monitor 返回 NotImplemented

**现象**：`safety/wellbeing_monitor.py:51,56` 有 `return NotImplemented`
**影响**：幸福感监控的某些路径不工作
**代码位置**：`backend/heart/safety/wellbeing_monitor.py:51` 和 `:56`
**修复方案**：实现 fallthrough 逻辑，或返回合理的默认值

### 15. Regex shadow 表已废弃

**现象**：`ss02_memory/mode.py` 标记 "regex" 和 "dual" 模式 deprecated，`memory_l3_facts_shadow_regex` 表已创建但不再使用
**影响**：死代码，增加维护负担
**修复方案**：删除 `regex_shadow.py`、shadow 表、相关迁移，只保留 "llm" 模式

### 16. emotion/service.py 返回类型不匹配

**现象**：`ss03_emotion/service.py:528` 函数声明返回 `str` 但某些路径返回 `None`
**影响**：mypy 报错，运行时可能 crash
**代码位置**：`backend/heart/ss03_emotion/service.py:528`
**修复方案**：确保所有路径返回 str，或改返回类型为 `Optional[str]`

### 17. memory_extractor_worker 类型不安全

**现象**：`workers/memory_extractor_worker.py:164` — `"object" has no attribute "run"`
**影响**：mypy 报错，运行时如果 extractor 未正确注入会 crash
**代码位置**：`backend/heart/workers/memory_extractor_worker.py:164`
**修复方案**：给 `__init__` 的 `extractor` 参数加正确的类型注解

---

## 🟢 低优先级（优化项）

### 18. TODO 列表（7 个）

| # | 文件 | 行号 | 内容 |
|---|------|------|------|
| 1 | `ss05_composer/token_budget.py` | 91 | `# TODO(heart-V2): plug in tiktoken / DeepSeek tokenizer` |
| 2 | `workers/memory_consolidator.py` | 121 | `# TODO: Add semantic similarity clustering` |
| 3 | `ss03_emotion/repair.py` | 419 | `# TODO: Optional LLM Critic call` |
| 4 | `ss04_relationship/service.py` | 109 | `TODO: Add Redis cache layer` |
| 5 | `ss04_relationship/service.py` | 297 | `# TODO: Implement DRIFTING, COLD_WAR, REUNION state updates` |
| 6 | `ss02_memory/retriever/base.py` | 238 | `# TODO: Implement proper deduplication` |
| 7 | `ss02_memory/retriever/base.py` | 263 | `TODO: Implement proper deduplication` |

### 19. deprecated 标记（8 个）

全部集中在 `ss02_memory/`：
- `mode.py:5-6` — "regex" 和 "dual" 模式 deprecated
- `core/config.py:77` — 注释
- `encoder/__init__.py:25` — `IdentitySignal` deprecated，使用 `Hint`
- `encoder/fast.py:4,82` — deprecated 路径
- `service.py:428` — `candidate_identity_signals` 始终为空（deprecated）

### 20. mypy 类型错误（15 个）

| 文件 | 行号 | 错误 |
|------|------|------|
| `ss02_memory/hints/regex_hints.py` | 63 | `str\|None` 传给 `open()` |
| `safety/wellbeing_monitor.py` | 1041 | `WellbeingState\|None` 传给需要 `WellbeingState` 的参数 |
| `ss02_memory/retriever/vector.py` | 107, 168 | `list[float]\|None` 传给 `map()` |
| `infra/llm_providers/deepseek_pro.py` | 80 | `str\|None` 传给 `base_url` |
| `infra/llm_providers/deepseek.py` | 83 | 同上 |
| `infra/invariant_predicates.py` | 199 | `Any\|list\|None` 传给 `len()` |
| `ss01_soul/resonance_tracker.py` | 160 | `None` 不可迭代 |
| `ss01_soul/facet_unlocker.py` | 182, 320, 350 | `None` 不可迭代 / `max()` 参数类型 |
| `workers/memory_extractor_worker.py` | 164 | `"object"` 没有 `run` 属性 |
| `ss02_memory/encoder/fast.py` | 41 | `str\|None` 传给 `open()` |
| `ss03_emotion/service.py` | 528 | 返回 `None` 但声明返回 `str` |
| `ss07_orchestration/orchestrator.py` | 184 | 函数在布尔上下文中始终为真 |

### 21. ss01_soul None 安全问题（3 处）

| 文件 | 行号 | 问题 |
|------|------|------|
| `ss01_soul/resonance_tracker.py` | 160 | `list[ResonanceTrigger]\|None` 直接迭代 |
| `ss01_soul/facet_unlocker.py` | 182 | `list[HiddenFacet]\|None` 直接迭代 |
| `ss01_soul/facet_unlocker.py` | 320 | 同上 |

**修复方案**：在迭代前加 `if items is not None:` 或用 `items or []`

### 22. 未使用的 SS02 字段

**现象**：`memory_encoding_events` 表有 `semantic_vector` 字段，但始终为 NULL
**影响**：浪费存储空间
**修复方案**：如果不需要，删除该字段；如果需要，在编码时填充

### 23. emotion_states 表为空

**现象**：查询 `emotion_states` 表返回 0 行，但 `emotion_events` 有数据
**影响**：情绪状态可能只存在内存中，重启丢失
**排查方向**：检查 `EmotionService` 是否正确持久化到 `emotion_states` 表

### 24. 没有外键约束

**现象**：所有表都没有外键（因为分区表不支持标准 FK）
**影响**：数据完整性靠应用层保证
**修复方案**：在应用层加强校验，或考虑非分区表使用 FK

### 25. replay_snapshots 无清理机制

**现象**：设计文档说 7 天保留期，但没有定时清理任务
**影响**：表会无限增长
**修复方案**：添加定时清理任务，删除 7 天前的快照

---

## 按子系统汇总

| 子系统 | 🔴 阻塞 | 🟠 高 | 🟡 中 | 🟢 低 |
|--------|---------|-------|-------|-------|
| API/Auth | 0 | 0 | 3 | 0 |
| SS01 Soul | 0 | 0 | 0 | 3 |
| SS02 Memory | 0 | 2 | 3 | 4 |
| SS03 Emotion | 0 | 1 | 1 | 1 |
| SS04 Relationship | 0 | 1 | 0 | 2 |
| SS05 Composer | 1 | 0 | 0 | 1 |
| SS06 Inner State | 0 | 0 | 0 | 0 |
| SS07 Orchestration | 0 | 1 | 0 | 0 |
| SS08 Voice | 0 | 0 | 0 | 0 |
| Safety | 0 | 0 | 1 | 0 |
| Infrastructure | 0 | 0 | 3 | 1 |
| 测试 | 0 | 2 | 0 | 0 |
| DB | 0 | 0 | 1 | 3 |
| **合计** | **1** | **7** | **12** | **15** |

---

## 修复优先级建议

### 立即修复（阻塞级）
1. **ScoredMemory reconstructed_text** — 记忆块每轮崩溃，影响记忆上下文注入
2. 修复 encoder-worker 重启循环（#48）
3. 合并 PR #45（迁移 009 hotfix）

### 本周修复（高优先级）
4. 合并 PR #42（SS02 v1.0.3）和 PR #43（MiMo TTS）
5. 修复 E2E 会话竞态（#47）
6. 修复 emotion_events 持久化
7. 更新迁移测试（head=010）
8. 修复 fast_encoder 测试
9. 修复 consolidator 测试导入（#46）
10. 实现 SS04 特殊状态

### 后续修复（中优先级）
11. 修复 WebSocket 端点
12. 统一 DeclarativeBase
13. 合并 LLM provider 树
12. 升级 JWT 到 RS256
13. 迁移到 FastAPI lifespan
14. 修复 mypy 类型错误
15. 实现 wellbeing_monitor fallthrough

### 清理（低优先级）
16. 删除 deprecated regex_shadow 代码
17. 处理 TODO 项
18. 清理 replay_snapshots
19. 添加 emotion_states 持久化验证
