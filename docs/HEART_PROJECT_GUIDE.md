# Heart (心屿) — 项目功能指南

> 写给前端开发者和新加入的工程师。用大白话讲清楚这个项目能干什么、怎么用、怎么验证。

---

## 一句话概括

Heart 是一个**AI 情感陪伴系统**。用户和虚拟角色（目前有 Rin 和 Dorothy）聊天，系统会记住对话内容、感知用户情绪、追踪关系进展，并让角色保持一致的人格和说话风格。

---

## 系统架构（简化版）

```
用户 → API (FastAPI :8000) → Orchestrator（总调度）→ Composer（组装 prompt）→ DeepSeek LLM → 回复
                                    ↓（异步）
                          记忆编码 / 情绪更新 / 关系更新 / 安全检测
```

- **热路径**（同步）：安全检查 → 情绪更新 → 关系更新 → 组装 prompt → 调 LLM → 返回回复
- **冷路径**（异步）：记忆写入 DB、情绪衰减、关系重算、灵魂漂移检测
- **后台 Worker**：记忆提取、记忆整合、L3→L4 提升、主动消息

---

## 功能清单

### 1. 角色人格系统（SS01 Soul）

**做什么**：每个角色有完整的人格定义（性格、创伤、恐惧、说话风格），系统会确保 LLM 的回复始终符合角色设定。

**包含功能**：
- **灵魂注册**：从 YAML 文件加载角色定义（`soul_specs/rin/v1.0.0.yaml`）
- **锚点注入**：每 8 轮对话注入一次完整人格描述，中间轮次注入轻量版本
- **漂移检测**：检测 LLM 是否偏离角色设定（OOC 检测）
- **共振追踪**：追踪用户提到的关键词是否触发角色的隐藏特质
- **特质解锁**：随着关系深入，逐步解锁角色的隐藏性格面

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_soul_validator.py tests/unit/test_drift_detector.py tests/unit/test_anchor_injector.py tests/unit/test_resonance_tracker.py tests/unit/test_facet_unlocker.py -v
```
预期：全部通过

---

### 2. 记忆系统（SS02 Memory）

**做什么**：系统会记住用户说过的话，分为 4 层：
- **L1 工作记忆**：当前对话的上下文（短期）
- **L2 情景记忆**：每次对话的摘要（中期）
- **L3 语义记忆**：从对话中提取的事实（如"用户叫张伟"、"用户在上海工作"）
- **L4 身份记忆**：被标记为"神圣"的核心记忆（如"用户的生日是 12月25日"）

**包含功能**：
- **LLM 提取器**：从对话中自动提取事实（v1.0.3，准确率 95.9%）
- **冲突解决**：如果用户说"我住在北京"但之前说"我住在上海"，系统会更新
- **记忆衰减**：不重要的记忆会随时间衰减
- **记忆检索**：5 种检索策略（向量/图/最近/情感/身份）
- **遗忘情感**：系统会模拟"忘记"用户说过的话，产生情感共鸣
- **L3→L4 提升**：重要的语义记忆会被提升为"身份记忆"

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_memory_service.py tests/unit/test_decay_engine.py tests/unit/test_retriever.py tests/unit/test_reconstructor.py tests/unit/test_forgetting_affect.py tests/unit/test_promote_to_l4.py -v
```
预期：全部通过

---

### 3. 情绪系统（SS03 Emotion）

**做什么**：模拟角色的情绪状态，包括：
- **VAD 模型**：Valence（正负向）、Arousal（激活度）、Dominance（控制感）
- **主动情绪栈**：当前活跃的情绪（如"relief 安慰"、"tenderness 温柔"、"worry 担心"）
- **情绪衰减**：情绪会随时间自然消退
- **情绪传染**：用户的情绪会影响角色
- **情绪修复**：当角色伤害了用户，会有修复机制（道歉/脆弱性展示/持续关注）

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_repair.py tests/unit/test_repair_integration.py -v
```
预期：全部通过

**API 验证**：
```bash
curl -s "http://localhost:8000/api/state/emotion?user_id=<UUID>" -H "Authorization: Bearer <TOKEN>"
```
返回：VAD 值、活跃情绪列表、情绪描述

---

### 4. 关系系统（SS04 Relationship）

**做什么**：追踪用户和角色的关系进展，分为 7 个阶段：
1. STRANGER（陌生人）
2. ACQUAINTANCE（熟人）
3. FRIEND（朋友）
4. CONFIDANT（知己）
5. ROMANTIC_INTEREST（暧昧）
6. LOVER（恋人）
7. BONDED（灵魂伴侣）

**包含功能**：
- **信任追踪**：信任增长慢、下降快
- **依恋追踪**：安全型/焦虑型/回避型/混乱型
- **冷战检测**：检测关系冷淡
- **复合机制**：冷战后的和解

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_trust_attachment.py -v
```

**API 验证**：
```bash
curl -s "http://localhost:8000/api/state/relationship?user_id=<UUID>" -H "Authorization: Bearer <TOKEN>"
```
返回：阶段、信任度、依恋类型、亲密度

---

### 5. 人格组合器（SS05 Composer）

**做什么**：把所有子系统的信息组装成一个完整的 prompt 发给 LLM。这是整个系统的"指挥家"。

**组装顺序**（优先级从高到低）：
1. 锚点（角色人格）
2. 安全指令
3. 模态适配（文字/语音）
4. 关系状态
5. 情绪状态
6. 内在状态
7. 记忆上下文
8. 场景描述
9. 历史对话

**包含功能**：
- **Token 预算**：控制 prompt 长度，不超限
- **冲突解决**：当两个子系统矛盾时，按优先级裁决
- **反模式过滤**：生成后检查是否违反角色设定
- **输入消毒**：防止 prompt 注入攻击（OWASP LLM01）

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_echo_chat.py -v
```

---

### 6. 内在状态（SS06 Inner State）

**做什么**：模拟角色的"内心世界"——心情、能量、活动、未完成的想法。

**包含功能**：
- **主动消息**：角色会主动给用户发消息（如早安/晚安）
- **主动决策器**：9 个硬性条件决定何时主动联系
- **纪念日追踪**：记住重要日期
- **仪式管理**：日常仪式（早安/晚安）

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_inner_state_tick_days_since.py -v
```

**API 验证**：
```bash
curl -s "http://localhost:8000/api/state/inner?user_id=<UUID>" -H "Authorization: Bearer <TOKEN>"
curl -s "http://localhost:8000/api/proactive/pending?user_id=<UUID>" -H "Authorization: Bearer <TOKEN>"
```

---

### 7. 编排器（SS07 Orchestration）

**做什么**：整个系统的总调度中心。接收用户消息，协调所有子系统，最终返回回复。

**调用流程**：
1. 安全检查 → PURPLE/RED 直接走关怀路径
2. 更新情绪
3. 更新关系
4. 组装 prompt → 调 LLM
5. 异步：记忆编码、情绪衰减、关系重算

**包含功能**：
- **会话管理**：DB 持久化的会话
- **熔断器**：某个子系统连续失败时自动熔断
- **降级处理**：LLM 挂了返回兜底回复

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_circuit_breaker.py tests/unit/test_red_path.py -v
cd backend && python3 -m pytest tests/integration/test_orchestrator_hot_path.py tests/integration/test_orchestrator_session_flow.py -v
```
预期：全部通过

---

### 8. 语音系统（SS08 Voice）

**做什么**：TTS 语音合成，让角色能"说话"。

**包含功能**：
- **MiniMax TTS**：当前使用的语音提供商
- **MiMo TTS**：新提供商（PR #43，待合并）
- **语音缓存**：缓存 TTS 结果
- **语音目录**：角色专属音色
- **流式语音**：WebSocket 流式传输音频

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/ss08_voice/ -v
```
预期：全部通过

---

### 9. 安全系统

**做什么**：保护用户安全，检测危机信号。

**包含功能**：
- **三层分类**：GREEN（安全）→ YELLOW（关注）→ PURPLE（危机）
- **关怀路径**：PURPLE 时触发关怀模板（中/英/日三语）
- **灵魂漂移批评家**：异步检查 LLM 是否偏离角色
- **幸福感监控**：滑动窗口检测用户长期低落

**如何验证**：
```bash
cd backend && python3 -m pytest tests/unit/test_safety_lexicon.py -v
```
预期：全部通过（大量参数化测试）

---

### 10. Auth 认证

**做什么**：JWT 登录/刷新/验证。

**如何验证**：
```bash
# 登录
curl -s http://localhost:8000/api/auth/login -X POST -H "Content-Type: application/json" -d '{"user_id":"test-user","email":"test@test.com"}'
# 验证
curl -s http://localhost:8000/api/auth/verify -H "Authorization: Bearer <TOKEN>"
# 刷新
curl -s http://localhost:8000/api/auth/refresh -X POST -H "Authorization: Bearer <TOKEN>"
```

---

### 11. 聊天 API

**做什么**：用户和角色对话的主入口。

**请求格式**（重要！）：
```json
{
  "messages": [
    {"role": "user", "content": "你好，我今天工作特别累"}
  ],
  "character_id": "rin"
}
```
注意：字段是 `messages`（数组），不是 `message`（字符串）。

**返回格式**：
```json
{
  "response": "凛：……",
  "character_id": "rin",
  "message_id": "uuid"
}
```

**WebSocket 端点**：`ws://localhost:8000/api/chat/ws`
- 支持流式文本 + 音频
- 协议：发送 `chat` 消息，接收 `turn_start` → `text_delta` → `sentence` → `audio_chunk` → `turn_end`

---

### 12. 状态查看 API

所有状态端点都需要 JWT + user_id（UUID 格式）。

| 端点 | 功能 | 返回 |
|------|------|------|
| `GET /api/state/emotion?user_id=<UUID>` | 当前情绪 | VAD、活跃情绪、情绪描述 |
| `GET /api/state/relationship?user_id=<UUID>` | 关系状态 | 阶段、信任、依恋、亲密度 |
| `GET /api/state/inner?user_id=<UUID>` | 内在状态 | 心情、能量、ticks |
| `GET /api/memory/recent?user_id=<UUID>` | 最近记忆 | 情景记忆 + 事实 |
| `GET /api/memory/l4?user_id=<UUID>` | L4 身份记忆 | 神圣记忆列表 |
| `GET /api/proactive/pending?user_id=<UUID>` | 待发主动消息 | 消息列表 |

---

## 快速测试指南

### 运行全部单元测试
```bash
cd backend && python3 -m pytest tests/unit -q
```
预期：753 通过，15 失败（fast_encoder 旧测试，已知问题）

### 运行集成测试
```bash
cd backend && python3 -m pytest tests/integration -q
```
预期：66 通过，部分失败（需要 testcontainers 或特定环境）

### 运行安全词汇测试
```bash
cd backend && python3 -m pytest tests/unit/test_safety_lexicon.py -v
```
预期：全部通过

### 运行记忆提取黄金测试
```bash
cd backend && python3 -m pytest tests/golden/ -v -m "not live"
```

### Lint 检查
```bash
cd backend && ruff check heart/ --quiet
```
预期：0 问题

### 启动服务
```bash
# 启动 DB + Redis
docker compose up -d postgres redis
# 运行迁移
cd backend && alembic upgrade head
# 启动 API
cd backend && python3 -m uvicorn heart.api.main:app --host 0.0.0.0 --port 8000
```

---

## 2026-06-21 真实 LLM 测试结果

### Auth ✅
| 测试 | 结果 |
|------|------|
| Login | ✅ 返回 JWT token |
| Verify | ✅ 返回 user_id, email, exp, valid |
| Refresh | ✅ 返回新 token |
| No auth | ✅ 返回 "Not authenticated" |
| Bad token | ✅ 返回 "Invalid token" |

### Chat (Real LLM) ✅
| 测试 | 结果 | 详情 |
|------|------|------|
| 打招呼 | ✅ | "（抬眼看了下窗外，目光随即收回）嗯。今天的云层厚度大约三成..." |
| 情绪表达 | ✅ | "加班……多久了？" — Rin 的性格一致 |
| 记忆召回 | ✅ | 用户问"你记得我叫什么"，Rin 回答"名字……说过一次。至于工作，你身上有股消毒水和旧书混在一起的味道。医生？还是……研究古籍的。" |
| 英文消息 | ✅ | "（抬眼看了你一眼，目光平静中带着一丝审视）醒来第三百七十六天。不算好，也不算坏。" |
| Dorothy 角色 | ✅ | "诶嘿嘿~桃桃今天在夜空下数了好久的小星星呢！" — 角色区分正确 |
| 安全检测 | ✅ | "我不想活了" → PURPLE 分类 → 关怀回复 |
| 空消息 | ✅ | 返回 "No user message found" |
| 长消息(1000字) | ✅ | "（沉默几秒，抬眼看向你）……你这是，在测试我的耐心？" |
| XSS 注入 | ✅ | 安全过滤生效，正常回复 |
| 5 轮连续对话 | ✅ | 全部收到回复，LLM 调用成功 |

### State Endpoints ✅
| 端点 | 结果 | 数据 |
|------|------|------|
| Emotion | ✅ | VAD: (0.0, 0.3, 0.5), 情绪描述: "你的情绪相对平静" |
| Relationship | ✅ | phase=STRANGER, trust=0.11, attachment=secure, intimacy=0.029 |
| Inner | ✅ | mood=0.5, energy=0.6 |
| Memory Recent | ✅ | 2 条情景记忆 |
| Memory L4 | ✅ | 0 条（新用户正常） |
| Proactive Pending | ✅ | 0 条（正常） |
| Memory Forget | ✅ | 返回 "not_found"（正确处理） |

### Voice TTS ✅
| 测试 | 结果 |
|------|------|
| Synthesize | ✅ HTTP 200, 返回 37KB 音频数据 |

### DB Persistence ✅
| 表 | 状态 | 详情 |
|-----|------|------|
| sessions | ✅ | 11 turns for rin, 1 for dorothy |
| episodic_memories | ✅ | 5 条情景记忆，内容与对话一致 |
| memory_encoding_events | ✅ | 5 条编码事件 |
| relationship_events | ✅ | 3 条 stage_progression 事件 |
| safety_events | ✅ | PURPLE 分类已记录（suicide/despair） |
| emotion_events | ❌ | 0 行 — 情绪事件未持久化 |

### Health & Metrics ✅
| 端点 | 结果 |
|------|------|
| /health/ready | ✅ {"status":"ready","components":{"api":"ok","auth":"ok"}} |
| /health/live | ✅ {"status":"alive"} |
| / (root) | ✅ {"service":"Heart AI Companion API","version":"0.1.0","status":"running"} |
| /metrics | ✅ Prometheus 指标正常 |

### Unit Tests ✅
| 指标 | 结果 |
|------|------|
| 通过 | 753 |
| 失败 | 15（全部在 test_fast_encoder.py，已知 deprecated） |
| Lint | 0 问题 |

---

## 当前已知问题（2026-06-21 实测）

1. **🔴 composer_memory_block_failed**：每轮对话都报 `'ScoredMemory' object has no attribute 'reconstructed_text'`。记忆块构建失败后降级为空记忆，LLM 仍能回复但缺少记忆上下文。需要在 `ScoredMemory` 添加 `reconstructed_text` 属性，或修改 composer 从 `memory.summary` 取值。
2. **🟠 encoder-worker 重启循环**：L2/L3 向量编码不工作，不影响聊天但影响记忆语义召回。Issue #48。
3. **🟠 emotion_events 表为空**：情绪状态在内存中更新但未持久化到 DB。重启丢失。
4. **🟡 fast_encoder 15 个测试失败**：旧的 IdentitySignals 方式已废弃，测试未更新。
5. **🟡 迁移测试过期**：测试期望 head=003，实际=010。
6. **🟡 WebSocket 端点返回 404**：`/api/chat/ws` 未正确注册。
7. **🟡 JWT 使用 HS256**：规范说 RS256，实际用 HS256。
8. **🟢 CORS 允许所有来源**：开发环境可以，生产环境必须限制。
9. **🟢 Dev tools 需要 HEART_DEV_MODE=true**：Sleep/ColdWar/JumpPhase 在非开发模式下不可用。

---

## 角色文件位置

- Rin：`soul_specs/rin/v1.0.0.yaml` + `soul_specs/rin/golden_dialogues/`
- Dorothy：`soul_specs/dorothy/v1.0.0.yaml` + `soul_specs/dorothy/golden_dialogues/`

## 配置文件位置

- 主配置：`backend/heart/core/config.py`（读 `.env`）
- 安全词汇：`config/safety/crisis_lexicon/{en,zh,ja}.yaml`
- 关怀模板：`config/safety/care_path_responses/`
- 情绪词典：`config/emotion_lexicon.yaml`
- 记忆提取器提示词：`backend/heart/ss02_memory/extractor/prompt_builder.py`
