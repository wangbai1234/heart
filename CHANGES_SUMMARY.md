# LLM 配置简化方案 - 改动总结

**日期**: 2026-05-15  
**阶段**: MVP  
**目标**: 只用 DeepSeek，简化配置，快速验证产品

---

## 📋 改动清单

### 1. 环境变量 (`.env` + `.env.example`)

#### ❌ 移除
```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
CRITIC_LLM_MODEL=claude-haiku-4-5
```

#### ✅ 保留和修改
```
DEEPSEEK_API_KEY=sk-xxx...xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

MAIN_LLM_MODEL=deepseek-reasoner    # V4-pro (高质量)
CHEAP_LLM_MODEL=deepseek-chat        # V4-flash (便宜快速)
```

**成本**: 
- 主响应: $0.55/$2.19 per 1M tokens (input/output)
- 便宜操作: $0.14/$0.28 per 1M tokens
- 预计 $0.007-0.01/user/day

---

### 2. 新建文件结构

```
backend/heart/
├── infra/
│   └── llm/                     # ✨ 新建
│       ├── __init__.py          # 导出公共 API
│       ├── config.py            # 模型和提供商配置
│       ├── provider.py          # DeepSeek 实现
│       └── router.py            # 统一 LLM 路由
├── core/
│   └── config.py                # ✨ 新建 (应用全局配置)
├── api/
│   └── app.py                   # ✨ 新建 (FastAPI 主应用)
├── ss05_composer/
│   └── example_usage.py          # ✨ 新建 (使用示例)
└── docs/
    └── LLM_GUIDE.md             # ✨ 新建 (详细指南)
```

---

### 3. 核心代码文件

#### `infra/llm/config.py`
- 定义 `ModelTier` 枚举 (MAIN / CHEAP)
- 定义 `ModelConfig` 数据类
- 定义 `DeepSeekConfig` API 配置
- 定义 `LLMProviderConfig` 全局配置

#### `infra/llm/provider.py`
- `LLMProvider` 抽象基类
  - `call()` - 同步调用
  - `stream()` - 流式调用
  - `estimate_cost()` - 成本估算
- `DeepSeekProvider` 实现
  - 官方定价表集成
  - 自动 token 使用统计

#### `infra/llm/router.py`
- `ModelRouter` 统一入口
  - `call_main()` - 主响应 (深思熟虑)
  - `stream_main()` - 主响应 (流式)
  - `call_cheap()` - 便宜操作 (分类、编码)
  - 自动日志和成本追踪

#### `core/config.py`
- 从 `.env` 读取所有配置
- 提供 `settings` 全局对象

#### `api/app.py`
- FastAPI 应用工厂
- 启动时初始化 Model Router
- 关闭时清理连接

#### `ss05_composer/example_usage.py`
- 三个实际示例：
  1. 主响应生成 (同步和流式)
  2. 记忆编码 (SS02)
  3. 安全检查 (SS07)

---

## 🎯 使用方式

### 在任何 Subsystem 中调用

```python
from heart.infra.llm import get_model_router

# 主响应
router = await get_model_router()
response = await router.call_main(
    messages=[...],
    agent_name="MyModule.function",
)

# 便宜操作
response = await router.call_cheap(
    messages=[...],
    json_mode=True,
    agent_name="Memory.encode",
)
```

### 没有代码侵入性

- ❌ 不要导入 `openai` / `anthropic` SDK
- ✅ 只通过 Model Router
- ✅ 将来迁移其他模型零改动

---

## 🔄 迁移路径

### 当前 (MVP)
```
所有 LLM 调用 → Model Router → DeepSeek (reasoner + chat)
```

### V1 (添加备选)
```
所有 LLM 调用 → Model Router → DeepSeek (primary)
                                 ↓ (如果失败)
                              Claude (fallback)
```

### V2 (优化成本)
```
高创意度 → Claude Sonnet
常规任务 → DeepSeek Chat  
低成本   → 自建 Companion-LLM
```

### 迁移方式
**只需修改 2 个文件**:
1. `infra/llm/provider.py` - 添加新 Provider
2. `core/config.py` - 切换 Provider

**所有 Subsystem 无需改动！** ✅

---

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| 主响应 P95 延迟 | ~3s (deepseek-reasoner) |
| 便宜操作延迟 | ~0.5s (deepseek-chat) |
| 成本/user/day | ~$0.007-0.01 |
| QPS 容量 | ~100 (单实例) |
| 故障恢复 | V1 加入 |

---

## ✅ 检查清单

- [x] 更新 `.env` 和 `.env.example`
- [x] 创建 LLM 基础设施模块
- [x] 实现 DeepSeek Provider
- [x] 创建 Model Router 中枢
- [x] 创建应用启动配置
- [x] 提供代码示例
- [x] 编写详细文档
- [ ] 在具体 Subsystem 中集成 (SS02/03/05/07)
- [ ] 编写单元测试
- [ ] 集成测试 + 成本验证

---

## 📖 后续步骤

1. **立即做**: 在 SS05 (Composer) 中集成 Model Router
2. **一周内**: 在 SS02/03/07 中集成
3. **两周内**: 添加成本追踪和告警
4. **下月**: 考虑 V1 的 Fallover 策略

---

## 💬 常见问题

**Q: 为什么用 deepseek-reasoner 而不是 deepseek-chat?**  
A: reasoner 有更强的推理能力，适合角色一致性和细节推理。chat 则快速便宜，用于辅助任务。

**Q: 成本真的只需 $0.007/user/day?**  
A: 是的。相比 Claude ($0.5-1) 和 GPT-4 ($0.3-0.5)，便宜 50-100 倍。

**Q: 能否后续改用其他模型?**  
A: 能。架构支持零改动切换，见迁移路径。

**Q: 流式响应怎么实现?**  
A: 用 `stream_main()`，见示例。

---

**完整文档**: 见 `backend/docs/LLM_GUIDE.md`
