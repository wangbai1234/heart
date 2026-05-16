# LLM 配置和使用指南

## 快速开始

### 1. 配置环境变量

编辑 `.env` 文件：

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-xxx...xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 模型配置
MAIN_LLM_MODEL=deepseek-reasoner    # 高质量响应
CHEAP_LLM_MODEL=deepseek-chat        # 便宜快速
```

### 2. 在代码中使用

#### 方式 A: 主响应（高质量）
```python
from heart.infra.llm import get_model_router

router = await get_model_router()

# 同步调用
response = await router.call_main(
    messages=[...],
    agent_name="Composer.generate_response"
)

# 或流式调用
async for chunk in router.stream_main(messages=[...]):
    print(chunk, end="", flush=True)
```

#### 方式 B: 便宜操作（快速低成本）
```python
# 记忆编码、分类、检查等
response = await router.call_cheap(
    messages=[...],
    json_mode=True,  # 强制 JSON 输出
    agent_name="Memory.encode"
)
```

---

## 架构设计

```
┌─────────────────────────────────────────┐
│         All Subsystems (SS01-07)        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       Model Router (统一入口)            │
│  - 日志记录                             │
│  - 成本追踪                             │
│  - 故障转移（V1）                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│    DeepSeek Provider                     │
│  - call()     → 同步调用                │
│  - stream()   → 流式调用                │
│  - estimate_cost() → 成本估算            │
└──────────────┬──────────────────────────┘
               │
               ▼
         DeepSeek API
    (reasoner + chat models)
```

### 模型分配策略

| 场景 | 模型 | 特点 | 成本 |
|------|------|------|------|
| **SS05 Composer** | deepseek-reasoner | 高质量推理、角色一致性 | 高 |
| **SS02 Memory** | deepseek-chat | 编码、向量化 | 低 |
| **SS03 Emotion** | deepseek-chat | 情感分类 | 低 |
| **SS07 Safety** | deepseek-chat | 内容检查、分类 | 低 |
| **SS06 Proactive** | deepseek-chat | 主动消息生成 | 低 |

---

## 成本估算

### DeepSeek 定价（2024）
- **deepseek-reasoner**: $0.55/$2.19 (input/output per 1M tokens)
- **deepseek-chat**: $0.14/$0.28 (input/output per 1M tokens)

### 典型消耗
假设每个用户每天平均 10 轮对话：

```
主响应 (SS05):       200 tokens × 10 turns × $3/1M = ~$0.006/day
便宜操作 (SS02-07):  500 tokens × 10 turns × $0.21/1M = ~$0.001/day
───────────────────────────────────────────────────────
总计:                                         ~$0.007/user/day
                                          或 ~$0.21/user/month
```

**与其他提供商对比**:
- Claude Sonnet: ~$0.5-1.0/user/day
- GPT-4o: ~$0.3-0.5/user/day
- DeepSeek: ~$0.007-0.01/user/day ✅ 最便宜

---

## 代码示例

### 生成主响应
```python
async def chat(user_id: str, message: str):
    router = await get_model_router()
    
    # 获取用户的对话历史
    history = await memory_service.get_conversation(user_id)
    
    # 构建消息
    messages = [
        {"role": "system", "content": character_prompt},
        *history,
        {"role": "user", "content": message},
    ]
    
    # 调用主模型 → 流式返回给前端
    async for chunk in router.stream_main(
        messages=messages,
        temperature=0.7,
        agent_name=f"Chat.{user_id}",
    ):
        await websocket.send_text(chunk)
```

### 记忆编码
```python
async def encode_conversation(conversation_text: str):
    router = await get_model_router()
    
    messages = [
        {
            "role": "system",
            "content": "Extract and structure memory from conversation",
        },
        {"role": "user", "content": conversation_text},
    ]
    
    result = await router.call_cheap(
        messages=messages,
        json_mode=True,
        temperature=0.1,
        agent_name="Memory.encode",
    )
    
    return json.loads(result)
```

### 安全检查
```python
async def check_safety(message: str) -> bool:
    router = await get_model_router()
    
    result = await router.call_cheap(
        messages=[
            {
                "role": "system",
                "content": "Check if message is safe. Return JSON: {is_safe: bool}",
            },
            {"role": "user", "content": message},
        ],
        json_mode=True,
        temperature=0.0,  # 最低温度保证一致
        agent_name="Safety.check",
    )
    
    return json.loads(result)["is_safe"]
```

---

## 迁移到其他模型（V1+）

### 方案 A: 保持 DeepSeek，添加 Claude 作为备选

```python
# router.py 中修改 failover_config

failover_config = {
    "main_strong": {
        "primary": "deepseek-reasoner",
        "fallback": "claude-sonnet-4-6",  # 如果 DeepSeek 宕机
    },
    "cheap": {
        "primary": "deepseek-chat",
        "fallback": "claude-haiku-4-5",
    },
}
```

### 方案 B: 完全迁移到 Claude

1. 创建 `AnthropicProvider` (参考 `DeepSeekProvider`)
2. 在 `config.py` 中切换提供商
3. 无需修改 subsystem 代码！

```python
# 只需改这个
llm_config = LLMProviderConfig(
    # deepseek=...,  # 注释掉
    anthropic=AnthropicConfig(...),  # 改用这个
)
```

### 方案 C: 混合策略（多模型）

```python
class ModelRouter:
    async def call_main(self, messages, ...):
        # 70% 用 DeepSeek（便宜）
        # 30% 用 Claude（质量验证）
        if random.random() < 0.3:
            return await self.anthropic.call(...)
        else:
            return await self.deepseek.call(...)
```

---

## 监控和调试

### 查看日志
```bash
# 查看所有 LLM 调用
tail -f logs/app.log | grep "Calling"

# 查看成本记录
tail -f logs/app.log | grep "LLM usage"
```

### 成本追踪
```python
# 每个用户的每日成本
SELECT user_id, DATE(created_at), SUM(cost) 
FROM llm_calls 
GROUP BY user_id, DATE(created_at)
ORDER BY SUM(cost) DESC;
```

### 性能指标
```
- P95 latency: Model Router 记录
- Token 消耗: provider.py 中统计
- 错误率: circuit breaker 追踪
```

---

## 常见问题

### Q: 如何强制 JSON 输出？
**A:** 使用 `json_mode=True`

```python
await router.call_cheap(
    messages=[...],
    json_mode=True,  # ← 这个
)
```

### Q: 流式调用可以分块返回吗？
**A:** 可以，使用 `stream_main()`:

```python
async for chunk in router.stream_main(messages=[...]):
    await send_to_client(chunk)  # 实时流式返回
```

### Q: 如何限制响应长度？
**A:** 使用 `max_tokens` 参数

```python
await router.call_main(
    messages=[...],
    max_tokens=500,  # 最多 500 token
)
```

### Q: 同一请求内多次调用如何计费？
**A:** 每次调用单独计费，自动记录在 `llm_calls` 表

### Q: 如何测试不同模型的成本差异？
**A:** 使用 `estimate_cost()`:

```python
cost = await router.estimate_cost(
    model_tier=ModelTier.MAIN,
    input_tokens=100,
    output_tokens=200,
)
print(f"Cost: ${cost:.4f}")
```

---

## 最佳实践

✅ **DO**:
- 对高创意性回应用 `call_main()`
- 对结构化任务用 `call_cheap()` + `json_mode=True`
- 总是传 `agent_name` 用于日志追踪
- 记录 token 使用量用于成本分析

❌ **DON'T**:
- 直接导入和调用 LLM SDK
- 在关键路径上用不必要的高端模型
- 忽略 `json_mode` 导致 JSON 解析失败
- 不记录成本数据

---

## 进一步阅读

- 架构设计: `runtime_specs/08_engineering_architecture.md`
- Subsystem 设计: `runtime_specs/0X_*.md`
- API 使用: FastAPI 文档 `http://localhost:8000/api/docs`
