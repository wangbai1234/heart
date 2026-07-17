# 修复方案：记忆晋升 + 主动消息

**日期**: 2026-07-17  
**执行人**: mimo  
**优先级**: P0 问题二选一，先做记忆晋升（改动小、风险低）

---

## 问题一：L4 身份记忆永远为空

### 根因（已确认，非推测）

`MemoryPromoterWorker` 文件 `backend/heart/workers/memory_promoter_worker.py` 存在且实现完整，但 **`backend/heart/workers/runner.py` 的 `start_workers()` 从未 import 或 spawn 它**。

`docker-compose.yml:64-67` 的注释声称 encoder-worker 会运行 promoter，这是**错误注释**，与代码不符。

阈值配置（`config/memory_promoter.yaml`）：
- K1 `min_mentions = 3`
- K2 `min_confidence = 0.80`
- K3 `min_age_days = 1`
- K4 `min_cross_sessions = 2`

用户 1513913499@qq.com 当前 L3 有 `has_name=王白`（confidence=0.8, is_identity_level=true），但因为 worker 从未运行所以 L4 为空。

---

### 修复步骤

#### Step 1 — 在 runner.py 接线 MemoryPromoterWorker

**文件**: `backend/heart/workers/runner.py`

在现有 `consolidator` worker 注册块之后（大约第 88 行），仿照以下模式添加：

```python
# 接线前：在顶部 import 区补充
from heart.workers.memory_promoter_worker import MemoryPromoterWorker

# 在 start_workers() 函数体内，consolidator 之后添加
if settings.heart_workers_enabled:
    promoter = MemoryPromoterWorker(
        db_session_factory=db_session_factory,
        redis_client=redis_client,
    )
    tasks.append(asyncio.create_task(promoter.start(), name="memory_promoter"))
    logger.info("worker_started", worker="memory_promoter")
```

`MemoryPromoterWorker.__init__` 签名见 `memory_promoter_worker.py:28`，内含 Redis SETNX 锁（`heart:memory_promoter:lock`），多实例安全。

**注意**：看实际的 `MemoryPromoterWorker.__init__` 参数，以仓库代码为准，不要套模板。

#### Step 2 — 补 .env.example（避免下个 dev 不知道有这些配置）

**文件**: `.env.example`

在 `HEART_WORKERS_ENABLED` 附近添加：

```
MEMORY_PROMOTER_ENABLED=true
MEMORY_PROMOTER_INTERVAL_SECS=300
MEMORY_PROMOTER_MIN_MENTIONS=3
MEMORY_PROMOTER_MIN_CROSS_SESSIONS=2
MEMORY_PROMOTER_MIN_CONFIDENCE=0.8
MEMORY_PROMOTER_MIN_AGE_DAYS=1
```

#### Step 3 — 修 docker-compose.yml 注释

**文件**: `docker-compose.yml:64-67`

把"encoder-worker 运行 memory_promoter"的错误描述改为实际运行的 worker 列表（encoder / extractor / consolidator / promoter），接线完成后才能加 promoter。

#### Step 4 — 一次性救活 1513913499@qq.com 的 L4

创建临时脚本 `backend/scripts/backfill_l4_one_user.py`：

```python
"""一次性对指定用户手动运行 L3→L4 晋升"""
import asyncio
from heart.ss02_memory.promoter import Promoter  # 查实际类名

async def main():
    user_id = "1513913499@qq.com"  # 或数字 id，查 users 表
    # 临时把阈值降到 1，跑完再改回来
    # 或直接调 Promoter.run_batch(user_id=user_id, override_thresholds={min_mentions:1, min_cross_sessions:1})
    ...

asyncio.run(main())
```

更简单的做法：临时修改 `config/memory_promoter.yaml`：
```yaml
min_mentions: 1
min_cross_sessions: 1
min_age_days: 0
```
重启服务等一个 interval（300s），确认 L4 有记录后改回原值并重启。

#### Step 5 — 单元测试

**文件**: `backend/tests/unit/workers/test_runner.py`（新建或已有）

断言 `start_workers()` 返回的 task list 中包含名为 `memory_promoter` 的 task。

---

### 验收标准

```sql
-- 运行 worker 接线 + 300 秒后查
SELECT * FROM memory_identity_facts WHERE user_id = <id>;
-- 应该出现 has_name=王白 这条记录
```

---

## 问题二：主动消息重构

### 根因（已确认）

| 症状 | 根因 |
|------|------|
| 每天多条"早安/晚安" | `_check_ritual_triggers` 空闲 >12h 必触发，`DAILY_QUOTA=3` per-character 不是 per-user |
| 内容高度重复 | LLM 失败回落 `random.choice(8条模板)`，`character_content.py:55-82` |
| 无上下文 | `_build_proactive_prompt` 不含 chat_messages 原文；ritual 路径 `recent_context=""` 硬编码空 |
| 已完整实现的 `InitiativeDecider` + `ProactiveMessageGenerator` 未接线 | 生产走的是另一条简版路径 |

---

### 重构方案（不新建独立系统，复用现有 send-message 链路）

核心原则：**不重写新系统**，在现有 orchestrator → composer → send 链路入口注入 `inactive_time` context，让 composer 自动继承所有已有上下文（soul YAML、SS03 情绪、SS04 关系、L3/L4 记忆、近期 chat 历史）。

#### Step 1 — 替换触发概率为新规则

**文件**: `backend/heart/ss06_inner_state/inner_loop_worker.py`

替换 / 短路现有两条触发链（`InnerStateService.tick()` 的概率算法 + `_check_ritual_triggers` 的强制触发）为：

```python
def _should_trigger_proactive(hours_since_last_user_reply: float) -> bool:
    """按用户不活跃时长决定是否触发主动消息。"""
    import random
    if hours_since_last_user_reply < 1:
        return False
    elif hours_since_last_user_reply < 5:
        prob = 0.05
    elif hours_since_last_user_reply < 10:
        prob = 0.10
    elif hours_since_last_user_reply < 24:
        prob = 0.40
    else:
        prob = 0.80
    return random.random() < prob
```

**关键**：`hours_since_last_user_reply` 必须从 `chat_messages WHERE role='user' ORDER BY created_at DESC LIMIT 1` 算，**不能用** `sessions.last_activity_at`（AI 消息也会更新它）。

建议把 tick 间隔从 3600s 改为 1800s（30min），否则 24h 触发要等到下个整点。

#### Step 2 — 加 ProactiveContext 参数，走 orchestrator 链路

**文件**: `backend/heart/ss07_orchestration/orchestrator.py`

在 `process_turn_stream`（或同等入口）增加可选参数：

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProactiveContext:
    inactive_hours: float
    trigger_reason: str = "idle"

async def process_turn_stream(
    ...,
    proactive_context: Optional[ProactiveContext] = None,
):
    ...
```

把 `proactive_context` 往下透传到 `ComposerService`。

#### Step 3 — 在 composer 拼接 idle hint

**文件**: `backend/heart/ss05_composer/service.py`（或 `compose_stream` 的 system prompt 组装处）

```python
if proactive_context:
    system_prompt += f"""

当前用户已经 {proactive_context.inactive_hours:.1f} 小时没有回复消息。
请结合：
1. 最近聊天内容；
2. 用户兴趣和记忆；
3. 当前角色人格；
4. 你们之间的关系状态；
主动生成一条自然消息。不要说"早安/晚安/在吗"这类客套话，也不要报菜名式罗列你知道的信息。"""
```

这样主动消息就自动获得 composer 已有的所有上下文：voice_dna、SS03 情绪、SS04 关系、SS05 场景、近期 chat history、L3/L4 记忆。

#### Step 4 — chat_messages 加 is_proactive 列（迁移）

**新建迁移**: `backend/migrations/versions/025_chat_messages_add_is_proactive.py`

```sql
-- upgrade
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS is_proactive BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_chat_messages_is_proactive ON chat_messages(user_id, is_proactive) WHERE is_proactive = TRUE;

-- downgrade
DROP INDEX IF EXISTS idx_chat_messages_is_proactive;
ALTER TABLE chat_messages DROP COLUMN IF EXISTS is_proactive;
```

主动消息落到 `chat_messages`（`is_proactive=True`），让后续 chat context 自然包含它。原 `proactive_messages` 表保留做审计/去重索引，不删。

**迁移前提醒**：revision 名如果超过 32 字符，第一步 SQL 要先 `ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(80)`。

#### Step 5 — 频控改写

**文件**: `backend/heart/ss06_inner_state/proactive_repo.py` 和 `service.py`

| 当前 | 改为 |
|------|------|
| `DAILY_PROACTIVE_QUOTA=3` per-character | `DAILY_PROACTIVE_QUOTA=2` per-user（跨角色总计） |
| `CROSS_CHARACTER_COOLDOWN_MINUTES=30` | 改为 240 分钟（4 小时） |
| 精确字符串去重 | 保持，另加：过去 3 天已有主动消息则跳过（简单保底） |

#### Step 6 — 灰度开关

**文件**: `backend/heart/core/config.py`

```python
proactive_v2_enabled: bool = False  # 改 true 启用新路径
```

`inner_loop_worker.py` 按此开关选择走新触发逻辑还是旧逻辑。验证 3 天后（内测账号）改为 true。

---

### 不要做

- ❌ 不接线 `InitiativeDecider` / `ProactiveMessageGenerator`（8 gates 会绕过简单阈值表）
- ❌ 不删老 `service.py` 主动消息代码（灰度期回滚用）
- ❌ 不改 `scripts/dev.sh`（workers 在 uvicorn 同进程内跑，无需单独起）
- ❌ 不新建独立的主动消息 HTTP 触发接口

---

### 验收标准

**记忆晋升**
- `SELECT count(*) FROM memory_identity_facts` 在用户有 ≥1 L3 identity fact 后 300 秒内 > 0

**主动消息**
- 跑 1000 次模拟，`inactive=0.5h` 触发率 0%，`inactive=2h` 约 5%，`inactive=12h` 约 40%，`inactive=30h` 约 80%（±2 个百分点）
- 连续 3 天生产日志中，同一用户同一天主动消息 ≤ 2 条
- 没有出现"早安"/"晚安"/"在吗"字面字符串（可 grep chat_messages WHERE is_proactive=true）
- `PROACTIVE_V2_ENABLED=false` 时旧路径完整可用

---

### PR 规划（mimo 参考）

```
PR #1: fix/memory-promoter-wire
  改动: runner.py 注册, .env.example, docker-compose 注释
  大小: ~50 行
  风险: 极低（仅增量注册 worker）

PR #2: feat/proactive-v2
  改动: orchestrator, composer, inner_loop, proactive_repo, migration 025
  大小: ~300-400 行
  风险: 中（灰度开关默认 false，无流量风险）
  前置: PR #1 合并
```

---

*作者: Claude Code (Sonnet 4.6) | 生成时间: 2026-07-17*
