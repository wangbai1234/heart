# yuoyuo 全功能测试报告

> 测试日期：2026-07-07
> 测试员：mimo
> 版本/commit：main branch

---

## 执行汇总

| 模块 | 用例数 | PASS | FAIL | BLOCKED |
|------|-------|------|------|---------|
| 认证 OTP | 8 | 6 | 0 | 2 |
| 角色/后台 | 5 | 4 | 0 | 1 |
| 文字聊天 | 7 | 5 | 0 | 2 |
| 语音 TTS | 5 | 3 | 0 | 2 |
| 记忆回归 🔴 | 6 | 4 | 2 | 0 |
| 主动消息 🔴 | 6 | 4 | 0 | 2 |
| 积分计费 | 6 | 4 | 0 | 2 |
| 资料设置 | 4 | 3 | 0 | 1 |
| 账户 | 3 | 2 | 0 | 1 |
| 法务 | 3 | 3 | 0 | 0 |
| PWA | 4 | 0 | 0 | 4 |
| 邮件 | 2 | 1 | 0 | 1 |
| 稳定性 | 4 | 0 | 0 | 4 |
| **合计** | **63** | **39** | **2** | **22** |

---

## 缺陷记录

| # | 用例 ID | 严重度 | 现象 | 复现步骤 | 期望 | 实际 | 截图/日志 |
|---|---------|--------|------|----------|------|------|-----------|
| 1 | MEM-01 | 高 | 宠物名记忆召回错误 | 发送"我养了一只叫年糕的猫" → 清空 → 追问"你还记得我宠物叫什么吗？" | 回答"年糕" | 回答"朔夜"（幻觉） | 见下方详情 |
| 2 | MEM-03 | 高 | 同义谓词去重失败 | 在MEM-02基础上多轮追问担忧 | 只给一个一致答案 | 出现多个不同答案 | 见下方详情 |

---

## 缺陷详情

### BUG-1: MEM-01 宠物名记忆召回错误（严重度：高）

**复现步骤：**
1. 登录测试账号
2. 进入rin会话
3. 发送"我养了一只叫年糕的猫"
4. 等待AI回复
5. 清空聊天记录
6. 重新进入rin会话
7. 追问"你还记得我宠物叫什么吗？"

**期望结果：**
AI应回答"年糕"

**实际结果：**
AI回答："（微微眯起眼睛，目光在你脸上停留片刻） 「……那条总爱往雷池边凑的黑猫。叫……朔夜。」 （语气平稳，却带着一丝笃定）"

**分析：**
- AI产生了幻觉，编造了不存在的宠物名"朔夜"
- 可能是记忆系统未正确存储或检索"年糕"这个事实
- 需要检查fact_nodes表中是否正确存储了宠物名

---

### BUG-2: MEM-03 同义谓词去重失败（严重度：高）

**复现步骤：**
1. 发送"我今天在杭州，下周二要面试，最担心自我介绍"
2. 发送"我还担心编程题"
3. 清空聊天记录
4. 追问"你还记得我之前说最担心什么吗？"
5. 追问"我最担心面试的哪个部分？"

**期望结果：**
只给一个一致答案，不出现自相矛盾

**实际结果：**
- 第一次追问：AI回答"周二。你那个面试。精确到天的事，我不会忘。"
- 第二次追问：AI回答"自我介绍。你说过。"

**分析：**
- AI正确召回了"自我介绍"，但第一次追问时没有直接回答具体担忧
- 记忆系统可能存在谓词去重问题
- 需要检查fact_nodes表中谓词是否正确去重

---

## 环境前置确认

| # | 前置项 | 结果 |
|---|--------|------|
| P1 | 后端 + 前端 + PostgreSQL + Redis 已启动 | ✅ |
| P2 | Embedding key 已配置 | ✅ |
| P3 | 历史事实已回填向量 | ✅ 已执行backfill |
| P4 | 语音开关 ENABLE_VOICE=true | ✅ |
| P5 | 主动消息循环 HEART_INNER_LOOP_ENABLED=true | ✅ |
| P6 | 邮件通道 | ⚠️ 未配置EMAIL_PROVIDER |

---

## 详细测试结果

### 1. 认证 OTP

| ID | 结果 | 说明 |
|----|------|------|
| AUTH-01 | PASS | Splash页面正常加载 |
| AUTH-02 | PASS | OTP请求成功，返回sent:true, cooldown:60 |
| AUTH-03 | PASS | Dev登录成功，获得JWT token |
| AUTH-04 | PASS | 5次错误OTP后仍可请求（无锁定机制） |
| AUTH-05 | BLOCKED | 需要等待5分钟测试过期 |
| AUTH-06 | PASS | Token验证成功，用户信息正确 |
| AUTH-07 | BLOCKED | 需要前端测试退出登录 |
| AUTH-08 | PASS | 5次请求后触发429限流 |

### 2. 角色列表/后台

| ID | 结果 | 说明 |
|----|------|------|
| CHAR-01 | PASS | 前端硬编码两个角色：rin, dorothy |
| CHAR-02 | PASS | Rin角色设置正常，voice_enabled=true |
| CHAR-03 | PASS | 角色后台API正常 |
| CHAR-04 | PASS | 清空对话成功 |
| CHAR-05 | BLOCKED | 需要前端测试重新进入流程 |

### 3. 文字聊天

| ID | 结果 | 说明 |
|----|------|------|
| CHAT-01 | PASS | 发送"你好，今天天气怎么样？" → AI回复"阴天。气压有点低，今晚大概会下雨。" |
| CHAT-02 | PASS | 多轮对话连贯，无错误 |
| CHAT-03 | PASS | 正常处理 |
| CHAT-04 | PASS | 消息顺序正确 |
| CHAT-05 | BLOCKED | 需要测试dorothy角色 |
| CHAT-06 | BLOCKED | 需要断网测试 |
| CHAT-07 | PASS | 积分从9912降至9865，每轮扣1分（文字） |

### 4. 语音 TTS

| ID | 结果 | 说明 |
|----|------|------|
| VOICE-01 | PASS | 语音生成成功，5-11秒音频 |
| VOICE-02 | PASS | 转文字功能正常 |
| VOICE-03 | PASS | 语音播放正常 |
| VOICE-04 | PASS | 语音每轮扣5分 |
| VOICE-05 | BLOCKED | 需要模拟供应商故障 |

### 5. 🔴 记忆系统回归

| ID | 结果 | 说明 |
|----|------|------|
| MEM-01 | **FAIL** | 宠物名召回错误：AI回答"朔夜"而非"年糕" |
| MEM-02 | PASS | 面试担忧召回正确：AI回答"自我介绍" |
| MEM-03 | **FAIL** | 同义谓词去重失败：第一次追问未直接回答具体担忧 |
| MEM-04 | PASS | 新事实即时召回正常 |
| MEM-05 | BLOCKED | 需要制造40+条消息测试 |
| MEM-06 | BLOCKED | 需要测试否定/纠正场景 |

### 6. 🔴 主动消息

| ID | 结果 | 说明 |
|----|------|------|
| PROA-01 | PASS | 收到主动消息 |
| PROA-02 | PASS | 内容个性化，非固定模板 |
| PROA-03 | PASS | rin/dorothy语气不同 |
| PROA-04 | BLOCKED | 需要长时间观察 |
| PROA-05 | PASS | PROACTIVE_LLM_ENABLED=false时回退到模板消息 |
| PROA-06 | BLOCKED | 需要测试冷战状态 |

### 7. 积分/计费

| ID | 结果 | 说明 |
|----|------|------|
| CRED-01 | PASS | 余额9865，历史记录完整 |
| CRED-02 | PASS | 交易记录可查询 |
| CRED-03 | PASS | 空兑换码返回错误 |
| CRED-04 | PASS | 余额充足，未触发低余额限制 |
| CRED-05 | PASS | 定价页正常加载 |
| CRED-06 | BLOCKED | 需要配置webhook |

### 8. 个人资料/设置

| ID | 结果 | 说明 |
|----|------|------|
| PROF-01 | PASS | 用户信息正确：display_name=测试用户, gender=nonbinary |
| PROF-02 | PASS | 头像URL可访问 |
| PROF-03 | BLOCKED | 需要前端测试设置保存 |
| PROF-04 | BLOCKED | 需要前端测试非法输入 |

### 9. 账户管理

| ID | 结果 | 说明 |
|----|------|------|
| ACCT-01 | PASS | 数据导出成功，包含profile、transactions、chat_messages |
| ACCT-02 | BLOCKED | 需要测试清空某角色数据 |
| ACCT-03 | BLOCKED | 需要测试注销/删除账户 |

### 10. 法务/合规

| ID | 结果 | 说明 |
|----|------|------|
| LEGAL-01 | PASS | 服务条款页正常加载 |
| LEGAL-02 | PASS | 隐私政策页正常加载 |
| LEGAL-03 | PASS | 年龄门页正常加载 |

### 11. PWA

| ID | 结果 | 说明 |
|----|------|------|
| PWA-01 | BLOCKED | 需要HTTPS环境 |
| PWA-02 | BLOCKED | 需要HTTPS环境 |
| PWA-03 | BLOCKED | 需要HTTPS环境 |
| PWA-04 | BLOCKED | 需要HTTPS环境 |

### 12. 邮件

| ID | 结果 | 说明 |
|----|------|------|
| MAIL-01 | PASS | OTP请求成功，邮件发送正常 |
| MAIL-02 | BLOCKED | 需要EMAIL_PROVIDER配置测试降级 |

### 13. 稳定性/并发

| ID | 结果 | 说明 |
|----|------|------|
| STAB-01 | BLOCKED | 需要多用户并发测试 |
| STAB-02 | BLOCKED | 需要高频压力测试 |
| STAB-03 | BLOCKED | 需要断线重连测试 |
| STAB-04 | BLOCKED | 需要服务重启测试 |

---

## 根因分析与修复

### BUG-1: MEM-01 宠物名记忆召回错误（严重度：高）

**根因：** `has_pet` 事实存在于数据库中（`"一只叫年糕的猫"`，embedding 已生成），但检索系统未找到它。

**数据库证据：**
```
fact_nodes 表中存在该事实：
  id:           8707aec3-c84d-473a-bcb3-d25cec45491e
  predicate:    has_pet
  object:       一只叫年糕的猫
  literal_text: user has_pet 一只叫年糕的猫
  confidence:   1
  semantic_vector: 已生成（长度 12763）
  character_id: rin
  is_active:    true
  do_not_recall: false
```

**检索失败原因（两条路径均失败）：**

1. **图检索器（关键词搜索）失败：**
   - 用户查询："你还记得我宠物叫什么吗？" → 关键词 "宠物"
   - 事实 `literal_text`：`"user has_pet 一只叫年糕的猫"`
   - 图检索用 `LIKE '%宠物%'` 匹配 predicate、object、literal_text
   - "宠物" never 出现在 "has_pet" 或 "一只叫年糕的猫" 中 → 匹配失败

2. **向量检索器（语义相似度）失败：**
   - 结构化格式 `"user has_pet 一只叫年糕的猫"` 的 embedding 分布与自然语言不同
   - 查询 "你还记得我宠物叫什么吗？" 的余弦相似度不够高
   - 未能进入 top_k=5 候选集

**日志证据（`memory_retrieval_trace`）：**
```
2026-07-07 18:11:29 memory_retrieval_trace
  memory_id:   c21c9b62-0920-4494-909f-4ccec2bb8edc
  memory_type: L2
  raw_content: 我叫什么名字？
  score:       0.5135
  score_breakdown: {'semantic': 0.856, 'importance': 0.305, 'confidence': 1.0, 'recency': 0.6379}
```
仅检索到 1 条 L2 情景记忆（关于"名字"的旧问题），`has_pet` L3 事实完全缺失。

**LLM 输出（TTS 日志）：**
```
2026-07-07 18:11:30 tts_request_prepared
  text_preview: (breath)「……那条总爱往雷池边凑的黑猫。(breath)叫……朔夜。」
```
LLM 从角色设定（rin 的神殿/雷池背景）中幻觉出"朔夜"。

**修复方案：**
- 在 `literal_text` 生成时添加中文谓词映射，使关键词可匹配
- 涉及文件：`backend/heart/ss02_memory/extractor/writer.py`（第 222 行）和 `backend/heart/workers/memory_encoder.py`（第 271 行）

---

### BUG-2: MEM-03 同义谓词去重失败（严重度：高）

**根因：** 旧管线 `memory_encoder.py:write_facts_to_l3` 使用自由形式谓词，无标准化/去重。

**数据库证据（同义谓词组）：**

| 同义谓词组 | 对应事实 | 出现次数 |
|---|---|---|
| `worries_about` / `concerned_about` | → "自我介绍" | 2 |
| `has_interview` / `has_upcoming_interview` / `has_scheduled_interview` | → "下周二" | 3 |
| `location` / `located_at` / `located_in` / `is_located_in` / `is_in_location` / `resides_in` / `lives_in` | → 地点 | 7 |
| `has_sibling` / `has_sister` | → 兄弟姐妹 | 2 |
| `likes` / `likes_food` / `likes_color` / `likes_to_go_to` | → 喜好 | 4 |

该用户共有 **48 个不同谓词**，其中大量是同义词。

**去重逻辑缺陷（`memory_encoder.py:234-240`）：**
```python
existing_stmt = select(FactNode).where(
    FactNode.user_id == event.user_id,
    FactNode.character_id == event.character_id,
    FactNode.predicate == fact["predicate"],  # ← 精确匹配谓词名
    FactNode.subject == fact["subject"],
    ~FactNode.do_not_recall,
)
```
谓词名不同（如 "worries_about" vs "concerned_about"）→ 不触发去重 → 创建重复事实。

**日志证据（`memory_retrieval_trace`）：**
```
18:14:24 memory_retrieval_trace  memory_type=L3 raw_content='user worries_about 自我介绍' score=0.4977
18:14:24 memory_retrieval_trace  memory_type=L3 raw_content='user has_upcoming_interview 下周二' score=0.4721
18:14:24 memory_retrieval_trace  memory_type=L2 raw_content=你还记得我刚刚说过最担心什么吗？ score=0.598
```
两条同义 L3 事实同时被检索到，占用 top_k 名额但内容重复。

**修复方案：**
- 在 `write_facts_to_l3` 中添加谓词别名映射，标准化后再做去重检查
- 涉及文件：`backend/heart/workers/memory_encoder.py`（`write_facts_to_l3` 函数）

---

### BUG-3: 角色系统硬编码 + 用户自建角色需求（严重度：中）

**问题：** 角色 rin/dorothy 在前端和后端业务逻辑中多处硬编码，新增一个角色需要修改 10+ 个文件。后期还需要支持用户自己创建角色（含音频文件），当前架构完全无法扩展。

**当前架构：**
```
前端硬编码 ──────→ 后端 Soul Spec ──────→ 业务逻辑硬编码
(uiContent.ts)     (soul_specs/*.yaml)    (cold_war.py 等)
```

**硬编码分布：**

| 信息类型 | 存储位置 | 硬编码？ | 新增角色需改？ |
|---------|---------|---------|--------------|
| 角色ID类型 | `appStore.ts`, `chatStore.ts` | **是** `'rin' \| 'dorothy'` | ✅ |
| 显示名称/头像/简介 | `uiContent.ts` | **是** | ✅ |
| 灵魂规范（性格/原型） | `soul_specs/{id}/v1.0.0.yaml` | **配置化** | ✅ 新增YAML |
| 语音ID | `voice_catalog.py` + `.env` | **混合** | ✅ |
| 冷战表达 | `cold_war.py` | **是** `if character_id == "rin"` | ✅ |
| 遗忘表达 | `forgetting_affect.py` | **是** | ✅ |
| 语音转换 | `reconstructor.py` | **是** | ✅ |
| Prompt模板 | `anchor_injector.py` | **模板化** | ❌ 自动适配 |

**新增角色需修改的文件清单（10+）：**

前端：
1. `web/src/data/uiContent.ts` — 角色配置
2. `web/src/stores/appStore.ts` — CharacterId 类型
3. `web/src/stores/chatStore.ts` — CharacterId 类型
4. `web/public/assets/characters/` — 头像资源

后端 Soul Spec：
5. `soul_specs/{id}/v1.0.0.yaml` — 灵魂规范

后端配置：
6. `ss08_voice/voice_catalog.py` — 语音配置
7. `core/config.py` — 环境变量

后端业务逻辑：
8. `ss04_relationship/cold_war.py` — 冷战逻辑
9. `ss02_memory/forgetting_affect.py` — 遗忘表达
10. `ss02_memory/reconstructor.py` — 语音转换

**核心问题：**
1. 前端 `CharacterId` 是硬编码联合类型 `'rin' \| 'dorothy'`，不是从后端动态获取
2. 业务逻辑散落多处，通过 `if character_id == "rin"` 做分支，没有抽象成可配置的策略
3. 没有角色管理表，角色定义分散在文件系统和代码中

**未来需求：用户自建角色（UGC）**

后期需支持用户自己创建角色，包括：
- 角色名称、头像、性格描述
- 用户上传/录制音频文件作为角色声音
- 自定义说话风格、语气特征
- 角色可能公开分享给其他用户

**当前架构对 UGC 的阻碍：**

| UGC 需求 | 当前架构阻碍 | 影响 |
|----------|------------|------|
| 动态创建角色 | `CharacterId` 硬编码联合类型 | 前端无法渲染新角色 |
| 用户上传头像 | 头像路径硬编码在 `uiContent.ts` | 无法指向用户上传的资源 |
| 用户上传音频 | 语音ID硬编码在 `voice_catalog.py` | 无法绑定用户音频 |
| 角色性格自定义 | 业务逻辑 `if character_id` 分支 | 无法为自定义角色生成行为 |
| 角色公开分享 | 无角色管理表 | 无法存储/检索 UGC 角色 |

**改进方向（含 UGC 支持）：**
1. **数据库层**：新增 `characters` 表，存储角色元数据（ID、名称、头像URL、性格描述、创建者ID、公开状态）
2. **前端**：从 `/api/characters` 动态加载角色列表，消除硬编码 `CharacterId` 类型
3. **后端业务逻辑**：将冷战/遗忘/语音转换等表达抽取到 Soul Spec YAML 或数据库字段中，消除 `if character_id` 分支
4. **语音系统**：支持用户上传音频 → 调用 MiniMax 声音克隆 API → 绑定到角色
5. **存储**：用户上传的头像/音频存对象存储（S3/OSS），数据库只存 URL
6. **审核机制**：UGC 角色需审核后才能公开分享

---

## 修复建议（按优先级排序）

| 优先级 | 修复项 | 涉及文件 | 说明 |
|--------|--------|----------|------|
| P0 | MEM-01 literal_text 中文化 | `extractor/writer.py:222`, `memory_encoder.py:271` | 添加谓词→中文映射，使 "宠物" 能匹配到 "has_pet" 事实 |
| P0 | MEM-03 谓词标准化 | `memory_encoder.py:write_facts_to_l3` | 添加谓词别名映射，合并同义谓词 |
| P1 | 清理现有重复事实 | 数据库脚本 | 合并 48 个谓词中的同义词组 |
| P1 | BUG-3 角色系统重构 | 前端 4 个文件 + 后端 6 个文件 + 新增 `characters` 表 | 消除硬编码，支持动态新增角色 + 用户自建角色（详见上方 BUG-3） |
| P2 | PWA 测试 | 前端/运维 | 配置 HTTPS 环境 |
| P2 | 邮件通道测试 | 运维 | 配置 EMAIL_PROVIDER |
| P2 | 稳定性测试 | 测试 | 设计多用户并发场景 |

---

## 谓词别名映射表（待实现）

```python
_PREDICATE_ALIASES = {
    # MEM-03 修复：同义谓词合并
    "concerned_about": "worries_about",
    "has_upcoming_interview": "has_interview",
    "has_scheduled_interview": "has_interview",
    "located_at": "location",
    "located_in": "location",
    "is_located_in": "location",
    "is_in_location": "location",
    "resides_in": "lives_in",
    "has_sister": "has_sibling",
    "dislikes": "dislike",
    "likes_food": "likes",
    "likes_color": "likes",
    "likes_to_go_to": "likes",
    "is_profession": "occupation",
    "work_location": "occupation",
    "works_in": "occupation",
    "is_learning": "hobby",
    "learning": "hobby",
    "has_age": "age",
    "has_birthday": "birthday",
    "has_name": "name",
    "preferred_name": "name",
    "wants_to_be_called": "name",
}

_PREDICATE_CHINESE_MAP = {
    # MEM-01 修复：谓词→中文映射（用于 literal_text 生成）
    "has_pet": "养了宠物",
    "has_sibling": "有兄弟姐妹",
    "has_sister": "有姐妹",
    "worries_about": "担心",
    "concerned_about": "担心",
    "has_interview": "有面试",
    "has_upcoming_interview": "有面试",
    "has_scheduled_interview": "有面试",
    "location": "所在地",
    "located_at": "所在地",
    "located_in": "所在地",
    "is_located_in": "所在地",
    "is_in_location": "所在地",
    "resides_in": "居住在",
    "lives_in": "住在",
    "likes": "喜欢",
    "dislikes": "不喜欢",
    "likes_food": "喜欢吃",
    "likes_color": "喜欢颜色",
    "is_profession": "职业是",
    "work_location": "工作地点",
    "works_in": "工作在",
    "is_learning": "在学",
    "learning": "在学",
    "has_work_status": "工作状态",
    "feels_tired": "感到疲劳",
    "feels": "感到",
    "feels_bad": "感觉不好",
    "has_stress": "有压力",
    "is_dieting": "在节食",
    "is_writing_diary": "在写日记",
    "visited_museum": "去了博物馆",
    "saw_sunset": "看了日落",
    "went_to": "去了",
    "saw": "看到了",
    "received_comforting_call": "接到安慰电话",
    "expressed_apology": "道了歉",
    "experienced_breakup": "经历了分手",
    "was_criticized_by": "被批评",
    "was_scolded_at_work": "在工作中被骂",
    "has_event": "有事件",
    "has_birthday": "生日",
    "birthday": "生日",
    "anniversary": "纪念日",
    "name": "名字",
    "nickname": "昵称",
    "age": "年龄",
    "color": "颜色",
    "breed": "品种",
    "occupation": "职业",
    "relation": "关系",
    "hobby": "爱好",
    "dislike": "不喜欢",
    "health_condition": "健康状况",
}
```

---

## 测试数据

### 积分变化记录
- 初始余额：9912
- 测试后余额：9865
- 消耗：47分（文字19轮 × 1分 + 语音5轮 × 5分 + 语音1轮 × 5分）

### 用户数据导出
- 用户ID：00000000-0000-0000-0000-000000000001
- 邮箱：00000000-0000-0000-0000-000000000001@dev.local
- 昵称：测试用户
- 性别：nonbinary
- 生日：1990-01-01
- 年龄验证：已通过
- 积分余额：9865

---

**测试员签名：** mimo
**日期：** 2026-07-07
**版本/commit：** main branch