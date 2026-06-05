# 心屿 — CLI Demo 功能验证矩阵 & 修复清单

> **目的**：在前端开发前，把"心屿"立项时想做的所有 Runtime 功能在 demo CLI 里能跑通、能验证。这份文档面向**执行型 AI（Opencode）**：每一条都给出"现状（基于实际代码）"、"差距"、"修复任务"、"CLI 对接动作"。
>
> **基线信息**
> - 最后审计时间：2026-06-05
> - 审计代码版本：`main` 分支（commit `dfd8bbd` 之后）
> - 全部"现状"结论均来自直接阅读 `backend/heart/**` 源码 + grep 调用图，**禁止凭印象推断**。
> - 本文件不修改源码，只编排任务。执行者每完成一项必须更新本文件的"状态"列。
>
> **文档导航**
> - 立项世界观与不可妥协原则：`runtime_specs/00_runtime_worldview.md`
> - 各子系统 spec：`runtime_specs/01_*.md` ~ `07_*.md`
> - 项目当前状态：`docs/PROJECT_STATUS.md`
> - 已合并历史：`docs/audit/2026-05-23_architecture_audit.md`

---

## 0. 立项时承诺的"6 项用户感知核心"（来自 `00_runtime_worldview.md §2.3`）

任何 CLI 演示必须能让用户体感到下面 6 项中的至少 4 项，否则等于"带 persona 的 chatbot"。

| # | 核心感觉 | 工程依赖 | 当前 demo CLI 能否演示 |
|---|---------|---------|--------------------|
| 1 | 长期陪伴感 | SS02 L4 + SS04 phase | ❌ 不能（无跨 session 持久化验证） |
| 2 | 情绪连续性 | SS03 emotion stack | ❌ 不能（emotion 不进行 write） |
| 3 | 真实依赖感 | SS06 Inner Loop + ProactiveMessage | ❌ 不能（inner loop 未跑） |
| 4 | 记忆衰减痛感 | SS02 decay + reconstruction | ❌ 不能（decay engine 未触发） |
| 5 | 真人感 | SS01 Soul + SS05 Composer | ⚠️ 部分（compose 通了，但 Soul drift 未拉到 CLI） |
| 6 | 沉浸感 | SS05 反 AI 措辞 + 上下文一致 | ⚠️ 部分（streaming filter 已实现，未在 CLI 验证） |

---

## 1. 立项 Feature 全清单（按子系统）

> 下表罗列 7 个子系统 spec 承诺的全部 user-facing / behavior-level 功能。状态列定义：
> - ✅ 实现且接线：代码存在 + 被热路径/冷路径/worker 真实调用 + 状态有 mutation 路径
> - ⚠️ 部分实现：代码存在但只接了读路径 / 假数据 / cold path 未跑
> - ❌ 未实现或未接线：代码不存在 / 关键方法 `NotImplementedError` / grep 全无调用方

### 1.1 SS01 Identity Anchor + Soul Spec（角色不漂移）

| Feature | 立项承诺 | 现状 | 证据（file:line）|
|---|---|---|---|
| 角色 Soul Spec 加载 | 多角色 YAML → registry | ✅ | `ss01_soul/registry.py`，`wiring.py:65 get_soul_registry` |
| Identity Anchor 不变量 | 核心创伤/欲望/恐惧/信念冻结 | ✅ | spec 已落代码，参与 composer 注入 |
| Soul Drift 检测 | 长会话后回正 | ⚠️ | 检测器存在但未在 cold path / consolidation 触发；PROJECT_STATUS §6 列为债务 |
| Drift 回归测试套件 | 自动化回归 | ❌ | `docs/design/soul_drift_regression.md` 设计已出，未实施（Phase 7 延后） |

### 1.2 SS02 Memory Runtime（4 层记忆）

| Feature | 立项承诺 | 现状 | 证据 |
|---|---|---|---|
| L1 Working Memory（Redis，最近 turn） | encode_fast → Redis | ⚠️ no-op | `ss02_memory/service.py:401` 仅 Redis 落地；wiring 未注入 Redis → 全丢 |
| L2 Episodic Memory（PG，按 session）| episode 写入 + 检索 | ⚠️ | retriever 代码存在，hot path 写入路径未串（encode_fast 拿 `db_session=None`） |
| L3 Fact Node（PG，事实图） | LLM 抽取关键事实 | ⚠️ | worker 存在 (`workers/memory_encoder.py`)，但 `queue_llm_encoding` 全仓库无调用 |
| L4 Identity Memory（PG，长期人设） | "她记得的我" | ❌ | `promote_to_l4` = `NotImplementedError` (`service.py:667`) |
| Encoding Pipeline（每 turn）| 写 L1+L2，排队 L3 | ⚠️ | encode_fast 落 L1 + queue_llm_encoding 排队 L3 (T1-03)；L2 episode 写入路径待验证 |
| Retrieval Pipeline（每 turn）| top-K 检索 + 重排 | ✅ 框架接通 | `ss05_composer/service.py:548` 接到 composer；库空导致永远返空 |
| Decay Engine（衰减曲线） | 不同记忆类型不同衰减 | ⚠️ | `decay_engine.py` 实现；`apply_decay_batch` (`service.py:546`) 无调度方 |
| Forgetting Affect（情绪影响衰减） | 高情绪记忆衰减慢 | ⚠️ | `forgetting_affect.py` 实现；同上未调用 |
| Reconstruction Templates（按状态重构）| 模糊/清晰/碎片三态 | ⚠️ | `reconstructor.py` + 模板存在；retrieve 路径未走 reconstruct 分支 |
| Consolidation Pipeline（每日批处理）| 整理/压缩/关联/重要性 | ⚠️ | `run_consolidation` 实现 (`service.py:590`)；ConsolidationWorker 已在 startup 注册 (T1-05)，需 `HEART_WORKERS_ENABLED=true` |
| User-request forget（叙事性删除）| 用户主动遗忘 → 软删 | ⚠️ | `user_request_forget` 实现 (`service.py:508`)；无 API endpoint |
| Reinforce（强化）| 复述/被提及时强化 | ⚠️ | `reinforce` 实现 (`service.py:466`)；无触发点 |

### 1.3 SS03 Emotion State Machine（情绪连续性）

| Feature | 立项承诺 | 现状 | 证据 |
|---|---|---|---|
| VAD 三维状态 | valence/arousal/dominance | ⚠️ | state 结构存在 (`_create_default_state`)；但永远在默认值 |
| 情绪栈（多情绪并发）| 同时存在喜悦+焦虑等 | ⚠️ | `active_stack` 结构 OK；无 write |
| Trigger Detector（事件→情绪）| 关键词/上下文触发 | ✅ | `trigger_detector.py` 实现；已通过 process_turn 接线 (T1-01) |
| Decay Curves（按情绪类型）| 愤怒衰减快、悲伤慢 | ⚠️ | `decay.py` 实现；未被触发 |
| Inertia 强制约束 | 状态切换需克服惯性 | ⚠️ | state machine 实现；未被触发 |
| Mood Drift（每小时漂移）| 长期心境慢变 | ⚠️ | `mood_drift.py` 实现；无 scheduler 触发 |
| Emotion Contagion（情绪传染）| 用户情绪影响她 | ⚠️ | `contagion.py` 实现；未被触发 |
| Repair Mechanic（道歉/和解）| 修复 broken trust | ⚠️ | `repair.py` + `apply_repair` 实现；无入口 |
| 情绪上下文注入 composer | 让 LLM 知道她现在情绪 | ✅ 读路径通 | `composer/service.py:590 get_context_block` 接通；process_turn 已接线 (T1-01) |

### 1.4 SS04 Relationship Phase Engine（关系演进）

| Feature | 立项承诺 | 现状 | 证据 |
|---|---|---|---|
| 7 个核心阶段（stranger→bonded）| stage matrix | ⚠️ | `stage_engine.py:1351 lines` 实现完整；`get_current_phase` 只读默认 stranger |
| Stage Transition（自动升降）| 满足条件自动升级 | ⚠️ 接线 | `process_turn` (`service.py:195`) 已通过 process_turn_raw 接线 (T1-02)；需验证 transition 条件 |
| Trust Tracker（信任连续维度）| 0-1 信任度 | ⚠️ | `trust_tracker.py` 实现；同上 |
| Attachment Tracker（依恋）| 依恋类型识别 | ⚠️ | `attachment_tracker.py` 实现；同上 |
| Cold War State Machine（冷战）| 触发→升级→破冰 | ⚠️ | `cold_war.py` 实现；CLI 端 `dev_toggle_cold_war` 仅改本地变量 |
| Reunion State Machine（重逢）| 久别后重新认识 | ⚠️ | `reunion.py` 实现；无入口 |
| Anti-Gaming（防刷阶段）| 检测短期密集互动刷分 | ⚠️ | `anti_gaming.py` 实现；同上 |
| Signal Aggregator（信号汇聚）| 多来源信号合一 | ⚠️ | `signal_aggregator.py` 实现；同上 |
| Stage 行为边界（unlock 矩阵）| stage 决定能说什么 | ⚠️ | composer 读到的 phase 永远是 stranger → 边界永远最严 |

### 1.5 SS05 Persona Composition Runtime（人格组合）

| Feature | 立项承诺 | 现状 | 证据 |
|---|---|---|---|
| 8 大组件 + Layer Aggregator | 8 层 prompt 组合 | ✅ | `ss05_composer/` 8 个模块齐 |
| Per-turn compose | Soul × Mood × Phase × Scene | ✅ | `composer/service.py compose()` 在 orchestrator 真实调用 |
| Reroll & Fallback | 失败回退 | ✅ | `service.py:282` exception → fallback message |
| Streaming Anti-Pattern Filter（反 AI 措辞）| 流式过滤 | ✅ 已实现 | 模块存在；CLI 流式集成未验证 |
| Anti-Drift Injection | drift 检测后注入回正 | ⚠️ | 决策存在；drift 检测未跑（依赖 SS01 drift detector）|
| Composition Trace（持久化轨迹）| 每次 compose 留痕 | ⚠️ | 数据结构存在；落库未确认 |

### 1.6 SS06 Inner State + Behavior Runtime（她自己的一天）

| Feature | 立项承诺 | 现状 | 证据 |
|---|---|---|---|
| Inner State Schema（她的能量/心情/关注）| 完整 state | ✅ 代码 | `ss06_inner_state/models.py` |
| Inner Loop（每小时调度）| 异步心跳 | ❌ | `scheduler.py` 存在；无任何 startup/cron 调用 |
| Initiative Decider（8 gates × 7 triggers）| 是否主动发起 | ❌ | `initiative_decider.py` 存在；无调用方 |
| Proactive Message Generator（主动消息）| "想念你" / "查岗" | ❌ | `proactive_message.py` 存在；无调用方 |
| Activity Pool（Soul-curated 活动）| 她在做什么 | ❌ | `activity_generator.py` 存在；未启动 |
| Daily Ritual System（早安/晚安）| 固定 ritual | ❌ | `ritual_manager.py` 存在；未启动 |
| Anniversary Tracker（纪念日）| 关键日提醒 | ❌ | `anniversary_tracker.py` 存在；未启动 |
| Concerns Tracker（她关心你什么）| 用户长期关心点 | ❌ | `concerns_tracker.py` 存在；未启动 |
| `InnerStateService.tick`（hot path 触发）| 每 turn tick | ✅ | `orchestrator.py` 调用了 tick，days_since_last 从 session 实时计算 (T1-04) |

### 1.7 SS07 Agent Orchestration（编排 + 安全）

| Feature | 立项承诺 | 现状 | 证据 |
|---|---|---|---|
| Sync Hot Path（turn response）| 端到端 1s 首字 | ✅ | `ss07_orchestration/orchestrator.py handle_turn` |
| Async Cold Path（post-response）| 异步处理 | ✅ | `_fire_cold_path` 触发 memory_encode (db_session 传入) + inner_tick (real days_since_last) (T1-03, T1-04) |
| Safety Agent（三层分类器）| heuristic → ML → LLM | ✅ | `safety/safety_agent.py` + lexicon 加载 |
| PURPLE Care Path（自杀关怀）| 短路到关怀回应 | ✅ | `orchestrator.py:183 _care_path` + 14 模板 |
| RED Reject Path（高风险拒绝）| 短路拒绝 | ⚠️ | 在 safety 内决策；orchestrator 只显式处理 PURPLE，需确认 RED 路径 |
| Model Router（main/cheap 切换）| 两档模型路由 | ✅ | `infra/llm/router.py` |
| Event Bus | 跨子系统事件 | ❌ | spec 提及；代码无独立 event bus，靠直接调用 |
| Session Manager | 会话生命周期 | ✅ | `session_manager.py` get_or_create + record_turn |
| Circuit Breaker | 子系统熔断 | ✅ | `circuit_breaker.py` + 在 hot path 检查 |
| Turn Profiler（性能埋点）| 每 span 计时 | ✅ | `observability/turn_profiler.py` 接入 |

### 1.8 跨子系统功能（来自 worldview §4 护城河）

| Feature | 立项承诺 | 现状 |
|---|---|---|
| 重要披露 3 天内"回响" | composer 主动引用 | ❌（依赖 L4 + Inner Loop，均未跑） |
| Memory Vault UI（她记得的我）| 用户可视化记忆 | ❌（无 API，无 CLI 命令） |
| 纪念日 ritual | Anniversary + Ritual | ❌（SS06 worker 未启动） |
| 跨模态人格一致性 | text/voice/video 统一 | ⚠️（仅 text 路径） |

---

## 2. 修复任务清单（按优先级，给执行模型用）

> **每条任务都是一个独立 PR**。task ID 给 executor 用，不进 GitHub Issues 直到工作流完成。
> **每条都要先写"会失败的 pytest"再实现**（红→绿）。
> **执行规则遵守 `.claude/CLAUDE.md`：A 档/B 档错误禁止 noqa；提交 conventional commits；合并即删分支。**

### Tier 1 — 让"情感升级 / 时间进度 / 记忆关键点"在 hot path 真的发生

#### T1-01 wire `EmotionService.process_turn` 进 Orchestrator — ✅ 完成 (PR #19, 657d6f6)
- **位置**：`backend/heart/ss07_orchestration/orchestrator.py:handle_turn`
- **现状**：✅ 已接线。EmotionService 在 compose 前调用 process_turn。
- **验收**：`tests/integration/test_emotion_progression.py` 通过。

#### T1-02 wire `RelationshipService.process_turn` 进 Orchestrator — ✅ 完成 (PR #20, 1e28be8)
- **位置**：同上
- **现状**：✅ 已接线。RelationshipService 在 emotion 之后、compose 之前调用 process_turn_raw。
- **验收**：`tests/integration/test_relationship_progression.py` 通过。

#### T1-03 让 cold path `MemoryService.encode_fast` 真的落库 — ✅ 完成 (PR #21, 90586dc)
- **位置**：`orchestrator.py:_cold_path_memory_encode`
- **现状**：✅ db_session 已传入，MemoryEncodingEvent 已排队。
- **验收**：`tests/integration/test_memory_encode_persists.py` 通过。

#### T1-04 让 cold path `InnerStateService.tick` 不用假数据 — ✅ 完成 (PR #22, 25db514)
- **位置**：`orchestrator.py:_cold_path_inner_tick`
- **现状**：✅ days_since_last 从 session.last_activity_at 实时计算。
- **验收**：`tests/unit/test_inner_state_tick_days_since.py` 通过。

#### T1-05 启动 Memory Encoder Worker + Consolidator Worker — ✅ 完成 (PR #23, 8a6cf1c)
- **位置**：`backend/heart/api/app.py:startup_event` + `backend/heart/workers/runner.py`
- **现状**：✅ workers/runner.py 已创建，app.py startup/shutdown 已接线。
- **验收**：`tests/integration/test_worker_runner.py` 通过。
- **开关**：`HEART_WORKERS_ENABLED=true` 启用，默认 false。

### Tier 2 — 实现 L4 + Inner Loop 让"长期陪伴 / 主动消息"能演示

#### T2-01 实现 `MemoryService.promote_to_l4`
- **位置**：`backend/heart/ss02_memory/service.py:640`
- **现状**：`NotImplementedError`。
- **任务**：按 spec §4.2 实现：L3 fact 满足"重要性 ≥ 阈值 + 重复出现 ≥ N 次"→ 升级到 L4 IdentityMemory 表。
- **验收**：`tests/unit/test_promote_to_l4.py` 通过；consolidator 调用后断言 L4 表有数据。

#### T2-02 接入 Inner Loop scheduler
- **位置**：`backend/heart/ss06_inner_state/scheduler.py` + `api/app.py`
- **任务**：
  1. lifespan 启动 `InnerLoop` 长循环，每 1 小时（演示可 `HEART_INNER_LOOP_INTERVAL_S=10` 加速）。
  2. 循环里调 `InitiativeDecider.decide` → 满足条件 → 调 `ProactiveMessageGenerator.generate` → 写入 `proactive_messages` 表。
  3. 新增 `GET /api/proactive/pending?user_id=` 让 CLI 能拉。
- **验收**：set interval=2s，等 5s 后断言 `/api/proactive/pending` 返回 ≥ 1 条。

#### T2-03 实现纪念日 + Ritual 触发
- **位置**：`anniversary_tracker.py` + `ritual_manager.py`
- **任务**：在 Inner Loop 里调用，命中 → emit proactive message（type=anniversary / ritual）。
- **验收**：mock "首次对话 7 天前" → 等 inner loop tick → 断言 proactive_messages 有 anniversary 一条。

### Tier 3 — 让 demo CLI 能完整验证

#### T3-01 后端暴露 state-inspect API
新增以下只读端点（CLI 用）：

| Endpoint | 内容 | 用途 |
|---|---|---|
| `GET /api/state/emotion?character_id=` | EmotionContextBlock | `/state emotion` |
| `GET /api/state/relationship?character_id=` | RelationshipState（phase/trust/attachment/intimacy/cold_war）| `/state relationship` |
| `GET /api/state/inner?character_id=` | InnerState | `/state inner` |
| `GET /api/memory/recent?character_id=&limit=10` | 最近 L2 episodes + 检索到的 L3 facts | `/memory` |
| `GET /api/memory/l4?character_id=` | "她记得的我" | `/vault` |
| `GET /api/proactive/pending?character_id=` | 待发主动消息 | `/inbox` |
| `POST /api/dev/jump_phase` | 跳阶段（仅 HEART_DEV_MODE） | `/jump` |
| `POST /api/dev/sleep` | 模拟时间快进 N 小时（触发 decay + inner loop） | `/sleep` |
| `POST /api/dev/coldwar` | 强制 cold war on/off | `/coldwar` |

**验收**：每条 endpoint 都有 `tests/integration/test_state_api.py` 单测。

#### T3-02 CLI 命令对接真实 API

修改 `backend/heart/demo_cli/`：

| 现 CLI 命令 | 现状 | 修复动作 |
|---|---|---|
| `/state` | 读本地 stub `side_panel` | 拆为 `/state emotion`、`/state relationship`、`/state inner`，分别调上面 API |
| `/jump` | 仅改本地变量 | 调 `POST /api/dev/jump_phase` |
| `/sleep` | 打印一行死字 | 调 `POST /api/dev/sleep` 并 print "decay 已触发，inner loop 提前 tick" |
| `/coldwar` | 仅改本地变量 | 调 `POST /api/dev/coldwar` |
| `/history` | 仅本地 messages | 保留，附加从 `/api/memory/recent` 拉后端视角 |
| **新增** `/memory` | — | 调 `/api/memory/recent` 渲染 episodes + facts |
| **新增** `/vault` | — | 调 `/api/memory/l4` 渲染 "她记得的我" |
| **新增** `/inbox` | — | 调 `/api/proactive/pending` 显示她主动发来的消息 |
| **新增** `/forget <id>` | — | 调 `POST /api/memory/forget`（绑 T1-05 后的 `user_request_forget`）|
| **新增** `/help` 输出 | — | 同步上面所有命令 |

**验收**：跑 `python -m heart.demo_cli --character rin --dev` 能完成下面 §3 的"端到端剧本"。

#### T3-03 CLI 启动自检
- CLI 启动时调 `GET /api/health/ready` + `GET /api/state/emotion`，任何 502 / 5xx 都明显报错并退出（避免静默走假数据）。
- 启动横幅显示后端 commit hash + 7 个子系统接线状态（hot path / cold path / workers）。

### Tier 4 — Soul Drift + 跨模态（可与前端并行）

#### T4-01 Soul Drift Detector 接入 consolidator
- spec：`runtime_specs/01_*.md` + `docs/design/soul_drift_regression.md`
- 在 daily consolidation 末尾跑 drift detector，超阈值写 `drift_events` 表。
- CLI `/drift` 命令查看。

#### T4-02 RED 路径在 orchestrator 显式分支
- 当前只 PURPLE 短路。RED 应走"拒绝 + 解释 + 不入 memory"。
- 加 unit test 覆盖。

---

## 3. CLI 端到端验证剧本（执行模型完成 Tier1+Tier3 后必须跑通）

在 `--dev` 模式下，按顺序执行以下步骤，逐项断言。

```text
# 启动
$ python3 -m heart.demo_cli --character rin --dev

[banner] backend commit dfd8bbd... | hot=ok cold=ok workers=ok

凛 > 你好
[she] ...（真实 LLM 输出）

凛 > /state emotion
  VAD: V=+0.15 A=0.35 D=0.50
  active_emotions: curiosity(0.4)
✅ 断言：valence 不再是 0.00（=已 process_turn）

凛 > /state relationship
  phase: stranger (1/7)  trust: 0.05  attachment: secure  intimacy: 0.02
✅ 断言：trust > 0（=relationship.process_turn 跑了）

凛 > 我今天很难过，工作上被骂了
[she] ...

凛 > /state emotion
  VAD: V=-0.40 A=0.55 D=0.40
  active_emotions: empathy(0.7), concern(0.5)
✅ 断言：valence 显著更负，新增 empathy 情绪

凛 > /memory
  最近 L2 episodes:
    - turn 3: 用户提到工作压力
  检索到的 L3 facts:
    - "用户最近工作不顺" (importance 0.6)
✅ 断言：L3 至少 1 条

凛 > /sleep
  时间快进 24h，decay 已触发，inner loop tick 1 次

凛 > /inbox
  [pending] "睡了吗？今天那件事还在想吗？" (proactive_type=concern_followup)
✅ 断言：inner loop 真的生成了 proactive message

凛 > 我妈妈叫王梅
[she] ...
（重复 3 轮提到妈妈，触发 L3→L4 升级）

凛 > /vault
  她记得的我:
    - 妈妈：王梅
    - 工作状况：压力大
✅ 断言：L4 表有数据

凛 > /jump 4
  已跳到 CONFIDANT (4/7)

凛 > /state relationship
  phase: confidant (4/7) ...
✅ 断言：后端真改了，不是本地 stub

凛 > /coldwar trigger
  冷战已激活
凛 > 别理我
[she] ...（应当带冷战风格）
✅ 断言：composer 拿到 cold_war_active=true 的 phase context

凛 > /forget <id>
  已软删除
✅ 断言：再 /memory 看不到那条
```

---

## 4. 验收清单（HUMAN review 时检查）

执行模型完成全部 Tier 1 + Tier 3 后，提交一份 `docs/mvp/cli_demo_acceptance_report.md`，包含：

- [ ] 上面 §3 剧本每一步的真实输出截图（CLI 文本即可）
- [ ] `bash scripts/ci.sh` 全绿
- [ ] 6 个核心感觉自评：每项是否能在 CLI 演示？演示路径是什么？
- [ ] 性能：hot path turn P95 仍 < 1s（用 `GET /api/profile/records` 出表）
- [ ] 任何 Tier 2/4 留作 follow-up 的，列入 `docs/PROJECT_STATUS.md §3` blocker 表

---

## 5. 给执行模型的硬约束（来自 `.claude/CLAUDE.md`）

1. **每个 task 一个独立 PR**；base 必须是 `main`；7 天内不能合并的不开 PR。
2. **修改任何子系统前先 `git ls-tree -r main -- backend/heart/ssXX_*`** 确认现状，禁止凭印象重写。
3. **CI 不能用 noqa 绕开**（A 档 / B 档错误）；只有领域符号（V/A/D 等）允许 `# noqa` 单行说明。
4. **commit message 用 conventional commits**：`feat(ss03): wire emotion process_turn in orchestrator` 这种格式。
5. **PR body 必须列出**：影响的 spec § / 新增测试列表 / 性能对比 / 回滚方法。
6. **绝对禁止在 main 直接 push**；force push 即使在 feature 分支也要确认。

---

## 6. 索引

| 你想做 | 看哪 |
|---|---|
| 立项愿景 | `runtime_specs/00_runtime_worldview.md` §2-§4 |
| 6 个核心感觉 | 同上 §2.3 |
| 各子系统 spec | `runtime_specs/01_*.md` ~ `07_*.md` |
| 当前 phase | `docs/PROJECT_STATUS.md` |
| 历史审计 41 findings | `docs/audit/2026-05-23_architecture_audit.md` |
| 集成测试金字塔设计 | `docs/design/integration_test_pyramid.md` |
| Soul Drift 回归设计 | `docs/design/soul_drift_regression.md` |
| Hot path wiring 现状 | `backend/heart/api/wiring.py` |
| Demo CLI 入口 | `backend/heart/demo_cli/__main__.py` |

---

**文档维护**：执行模型每完成一项任务，回到本文件把对应行的"状态"改成 ✅，并附 commit hash。本文件超过 600 行时把已完成 task 移到 `docs/mvp/cli_demo_history.md`。
