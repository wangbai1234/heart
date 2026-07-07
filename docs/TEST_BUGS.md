# 测试发现的 Bug 清单

> 测试时间：2026-07-07 14:34 - 15:01
> 测试环境：本地开发环境（Docker + FastAPI + Next.js）
> 测试用户：test@yuoyuo.app
> 测试角色：神无月凛 (rin)

---

## Bug #1：面试担忧事实召回失败（P0 - 高优先级）

**严重程度：** 高
**影响：** 用户体验差，AI 回答与实际不符

### 现象
- 用户在对话中说"我今天在杭州，下周二要面试，最担心自我介绍"
- 清空聊天记录后，追问"你还记得我之前说最担心什么吗？"
- AI 回答："有一天醒来，发现自己已经跟不上世界的节奏了"
- **实际应答：** "自我介绍"

### 数据库验证
| 表 | 记录 | 状态 |
|---|---|---|
| `episodic_memories` | "我今天在杭州，下周二要面试，最担心自我介绍" | ✅ 已存储（importance=1, recall_count=10） |
| `fact_nodes` | `worries_about` → "自我介绍" | ✅ 已存储（confidence=1, importance=0.8） |
| `fact_nodes` | `concerned_about` → "自我介绍" | ✅ 已存储（confidence=0.95, importance=0.7） |

### 问题定位
- **存储层面：** 正确 ✅
- **召回层面：** 故障 ❌
  - `fact_nodes.recall_count = 0`（从未被召回）
  - `fact_nodes.last_recalled_at = null`（从未被检索到）
  - AI 回答内容"跟不上世界的节奏"在数据库中**不存在**（幻觉）

### 可能原因
1. 语义搜索未将"最担心什么"匹配到 `worries_about`/`concerned_about` 谓词
2. 该事实的语义向量（`semantic_vector`）未正确生成
3. 召回管道因相关性分数过低跳过了该事实
4. 召回上下文窗口限制，该事实未被选入 prompt

### 复现步骤
1. 清空聊天记录（角色后台 → 清空 → 确认）
2. 返回角色列表，选择神无月凛
3. 发送"你还记得我之前说最担心什么吗？"
4. 观察 AI 回答

### 期望行为
AI 应回答："你最担心的是自我介绍"或类似内容

---

## Bug #2：宠物名召回成功但面试担忧召回失败（相关问题）

**严重程度：** 中
**影响：** 不同类型事实的召回效果不一致

### 现象
- 同一用户、同一角色、同一清空操作后
- 追问"你还记得我宠物叫什么吗？" → **正确回答"年糕"** ✅
- 追问"你还记得我之前说最担心什么吗？" → **错误回答"跟不上世界的节奏"** ❌

### 数据库对比
| 事实 | predicate | recall_count | 召回结果 |
|------|-----------|--------------|----------|
| 宠物名 | `has_pet` → "一只叫年糕的猫" | 0 | ✅ 正确 |
| 面试担忧 | `worries_about` → "自我介绍" | 0 | ❌ 错误 |

### 分析
- 两个事实的 `recall_count` 均为 0
- 但宠物名能正确召回，面试担忧不能
- 可能原因：
  1. `has_pet` 谓词的语义匹配度更高
  2. "宠物叫什么"比"最担心什么"更易匹配
  3. 召回管道对不同谓词的处理逻辑不一致

---

## Bug #3：`worries_about` 和 `concerned_about` 重复存储（P2 - 低优先级）

**严重程度：** 低
**影响：** 数据冗余，可能干扰召回

### 现象
同一语义内容（"担心自我介绍"）被存储为两条不同的 fact：
- `worries_about` → "自我介绍"（confidence=1, importance=0.8）
- `concerned_about` → "自我介绍"（confidence=0.95, importance=0.7）

### 问题
1. 两条记录内容重复
2. 谓词不同但语义相同
3. 可能导致召回时竞争或混淆

### 期望行为
- 要么合并为一条记录
- 要么有明确的去重机制

---

## 已修复的问题（历史记录）

### Bug #4：超窗口早期信息丢失（已修复 ✅）
**之前现象：** AI 在 40+ 条消息后说错宠物名"铜钱"
**当前状态：** 已修复，AI 正确回忆"年糕"

### Bug #5：清空聊天记录操作路径问题（已修复 ✅）
**之前现象：** 直接导航到 `/chat/rin` 后消息仍显示
**当前状态：** 用户操作路径问题，正确路径（角色列表 → 选择角色）下功能正常

### Bug #6：流式响应错误（已修复 ✅）
**之前现象：** `compose_stream_failed` 错误
**当前状态：** 已修复，本次测试未出现

---

## 待验证的问题

### Test 4：长期记忆沉淀
**状态：** 已建立事实（"我在杭州工作，是一名程序员"），等待 30 分钟后验证
**待执行：** 追问"我在哪里工作？是什么职业？"

---

## 优先级排序

| Bug | 严重程度 | 优先级 | 状态 |
|-----|----------|--------|------|
| #1 面试担忧召回失败 | 高 | P0 | 待修复 |
| #2 召回效果不一致 | 中 | P1 | 待修复 |
| #3 `worries_about` 和 `concerned_about` 重复存储 | 低 | P2 | 待优化 |
| #4 超窗口信息丢失 | 高 | P0 | ✅ 已修复 |
| #5 清空操作路径 | 中 | P1 | ✅ 已修复 |
| #6 流式响应错误 | 高 | P0 | ✅ 已修复 |
| FR #1 主动消息改为 LLM 生成 | 中 | P1 | 待实现 |

---

## 功能需求

### FR #1：主动消息改为 LLM 生成（P1 - 中优先级）

**当前状态：** 内置模板随机选择
**期望状态：** 调用 LLM 根据当前上下文生成个性化内容

### 当前实现分析

**文件位置：** `backend/heart/ss06_inner_state/service.py`

**当前逻辑（L163-164）：**
```python
templates = PROACTIVE_TEMPLATES.get(character_id, PROACTIVE_TEMPLATES["rin"])
content = random.choice(templates)
```

**当前模板示例：**
```python
PROACTIVE_TEMPLATES = {
    "rin": [
        "今天看见一只猫，和你有点像。",
        "……突然想你了。没什么事，就是想告诉你。",
        "下雨了。记得带伞。",
        ...
    ],
    "dorothy": [
        "嗨嗨~桃桃刚才看到一个超好笑的视频！分享给你！",
        "你今天怎么样呀？桃桃突然好想你！",
        ...
    ],
}
```

### 改造方案

#### 1. 新增 LLM 生成函数

在 `service.py` 中新增 `_generate_proactive_content()` 函数：

```python
async def _generate_proactive_content(
    self,
    user_id: UUID,
    character_id: str,
    trigger_type: str,
    relationship_stage: str,
    intimacy: float,
    days_since_last_interaction: float,
) -> str:
    """调用 LLM 生成个性化主动消息"""
    
    # 1. 加载角色 Soul Spec
    soul_spec = await _load_soul_spec(character_id)
    
    # 2. 加载最近对话上下文（最近 10 轮）
    recent_context = await self._load_recent_context(user_id, character_id, limit=10)
    
    # 3. 加载用户事实（从 fact_nodes）
    user_facts = await self._load_user_facts(user_id, character_id)
    
    # 4. 构建 prompt
    prompt = f"""你是{character_id}，现在需要主动给用户发一条消息。

## 触发原因
{trigger_type}

## 关系状态
- 关系阶段：{relationship_stage}
- 亲密度：{intimacy}
- 距离上次互动：{days_since_last_interaction} 天

## 最近对话
{recent_context}

## 用户信息
{user_facts}

## 要求
1. 符合角色性格（参考 Soul Spec）
2. 自然、个性化，不要模板化
3. 长度控制在 1-2 句话
4. 不要太频繁打扰用户
"""
    
    # 5. 调用 LLM
    response = await llm_provider.generate(
        model=settings.cheap_llm_model,  # 使用便宜模型
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.8,
    )
    
    return response.content
```

#### 2. 修改 tick() 方法

将 `service.py:163-164` 的模板选择逻辑改为：

```python
# 原代码
templates = PROACTIVE_TEMPLATES.get(character_id, PROACTIVE_TEMPLATES["rin"])
content = random.choice(templates)

# 改为
content = await self._generate_proactive_content(
    user_id=user_id,
    character_id=character_id,
    trigger_type=trigger_type,
    relationship_stage=relationship_stage,
    intimacy=intimacy,
    days_since_last_interaction=days_since_last_interaction,
)
```

#### 3. 更新 tick() 方法签名

由于 `_generate_proactive_content()` 是异步函数，需要将 `tick()` 方法改为异步：

```python
# 原代码
def tick(self, ...) -> Optional[ProactiveMessage]:

# 改为
async def tick(self, ...) -> Optional[ProactiveMessage]:
```

#### 4. 更新 InnerLoopWorker

在 `inner_loop_worker.py` 中调用 `tick()` 时添加 `await`：

```python
# 原代码
msg = self.inner_state_service.tick(...)

# 改为
msg = await self.inner_state_service.tick(...)
```

#### 5. 添加 LLM 调用限制

为避免频繁调用 LLM，添加以下限制：

```python
# 1. 每日 LLM 调用次数限制
MAX_LLM_CALLS_PER_DAY = 10

# 2. 缓存生成结果（5 分钟内重复触发使用缓存）
_proactive_cache: Dict[str, tuple[str, datetime]] = {}

# 3. 降级策略：LLM 失败时回退到模板
try:
    content = await self._generate_proactive_content(...)
except Exception as e:
    logger.error("proactive_llm_failed", error=str(e))
    templates = PROACTIVE_TEMPLATES.get(character_id, PROACTIVE_TEMPLATES["rin"])
    content = random.choice(templates)
```

### 需要修改的文件

| 文件 | 修改内容 |
|------|----------|
| `backend/heart/ss06_inner_state/service.py` | 添加 `_generate_proactive_content()` 函数，修改 `tick()` 方法为异步 |
| `backend/heart/ss06_inner_state/inner_loop_worker.py` | 更新 `tick()` 调用添加 `await` |
| `backend/heart/core/config.py` | 添加 `PROACTIVE_LLM_MODEL` 配置（可选，默认使用 `cheap_llm_model`） |

### 注意事项

1. **异步改造**：`tick()` 方法需要改为异步，影响所有调用方
2. **LLM 成本**：主动消息会增加 LLM 调用成本，需要监控
3. **降级策略**：LLM 失败时回退到模板，保证功能可用
4. **缓存机制**：避免短时间内重复生成相似内容

---

## 建议修复方向

### Bug #1 修复建议
1. 检查语义向量生成逻辑，确保 `worries_about`/`concerned_about` 的向量正确
2. 检查召回管道的谓词匹配逻辑
3. 检查相关性分数计算，确保高 importance 的事实不被跳过
4. 添加调试日志，记录召回过程中的候选事实和得分

### Bug #2 修复建议
1. 对比 `has_pet` 和 `worries_about` 的召回路径差异
2. 检查不同谓词类型的语义匹配权重
3. 确保所有高 importance 事实都有同等召回机会

### Bug #3 修复建议
1. 在记忆提取阶段添加去重逻辑
2. 合并语义相同的事实（如 `worries_about` 和 `concerned_about`）
3. 或者在召回时处理竞争情况

---

**文档创建时间：** 2026-07-07 15:15
**创建者：** AI Assistant
