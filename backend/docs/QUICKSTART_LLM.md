# LLM 快速启动 (3 分钟)

## 1️⃣ 配置 API Key

编辑 `.env`:
```bash
DEEPSEEK_API_KEY=sk-your-key-here
```

从这里获取 key: https://platform.deepseek.com/api_keys

## 2️⃣ 验证配置

```bash
# 在 Python 中测试
python3 << 'EOF'
import os
from heart.core.config import settings
print(f"✅ DeepSeek API Key: {settings.deepseek_api_key[:20]}...")
print(f"✅ Main Model: {settings.main_llm_model}")
print(f"✅ Cheap Model: {settings.cheap_llm_model}")
EOF
```

## 3️⃣ 在代码中使用

### 简单例子
```python
from heart.infra.llm import get_model_router

async def test():
    router = await get_model_router()
    
    # 主响应
    response = await router.call_main(
        messages=[{"role": "user", "content": "你好"}],
        agent_name="Test",
    )
    print(response)

# 运行
import asyncio
asyncio.run(test())
```

### 流式响应
```python
async def test_stream():
    router = await get_model_router()
    
    async for chunk in router.stream_main(
        messages=[{"role": "user", "content": "说个故事"}],
        agent_name="Story",
    ):
        print(chunk, end="", flush=True)

asyncio.run(test_stream())
```

## 🎯 核心 API

```python
# 获取路由器
router = await get_model_router()

# ━━━━━━━━━━━━━━━━━━━━━━━
# 主响应 (高质量)
# ━━━━━━━━━━━━━━━━━━━━━━━

# 同步
text = await router.call_main(
    messages=[...],                    # 对话历史
    temperature=0.7,                   # 创意度 (0=确定, 1=创意)
    max_tokens=2000,                   # 最大输出
    agent_name="MyModule.func",        # 标签 (日志)
)

# 流式 (用于前端实时显示)
async for chunk in router.stream_main(messages=[...]):
    send_to_client(chunk)

# ━━━━━━━━━━━━━━━━━━━━━━━
# 便宜操作 (快速/成本低)
# ━━━━━━━━━━━━━━━━━━━━━━━

# 同步 + JSON
result = await router.call_cheap(
    messages=[...],
    temperature=0.1,                   # 低温度 = 一致性强
    max_tokens=1000,
    json_mode=True,                    # 强制 JSON 输出
    agent_name="Memory.encode",
)
import json
data = json.loads(result)
```

## 📊 成本

| 用途 | 模型 | 成本 |
|------|------|------|
| 主响应 | deepseek-reasoner | $0.55/$2.19 per 1M |
| 编码/分类 | deepseek-chat | $0.14/$0.28 per 1M |

**典型用户**: ~$0.007/day = $0.21/month ✅

## 🔧 常用参数

```python
# 温度 (creativity)
temperature=0.0   # ❄️  确定性强 (分类、编码)
temperature=0.7   # 🔥 创意度高 (角色响应)

# Token 限制
max_tokens=500    # 短回复
max_tokens=2000   # 长回复

# 格式
json_mode=True    # 强制 JSON 输出

# 标签
agent_name="SS05.composer"  # 日志/监控用
```

## 📍 日志

所有调用自动记录:

```
[INFO] [SS05.composer] Calling main model: deepseek-reasoner
[INFO] LLM usage: model=deepseek-reasoner, input=150, output=245, cost=$0.0012
```

## ❌ 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `RuntimeError: ModelRouter not initialized` | 未启动应用 | 使用 `uvicorn` 或 `make dev` |
| `401 Unauthorized` | API Key 错误 | 检查 `.env` 中的 DEEPSEEK_API_KEY |
| `json.JSONDecodeError` | JSON 解析失败 | 确保传了 `json_mode=True` |
| 响应为空 | Token 不足 | 增加 `max_tokens` |

## 📚 更多信息

- 详细指南: `backend/docs/LLM_GUIDE.md`
- 代码示例: `backend/heart/ss05_composer/example_usage.py`
- 改动总结: `docs/archive/2026-05-15_llm_simplification.md`

## 🚀 下一步

1. 在 SS05 (Composer) 中集成 Model Router
2. 添加成本追踪
3. 实现具体业务逻辑

---

**问题?** 查看 `LLM_GUIDE.md` 的 FAQ 部分
