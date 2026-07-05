# Heart Backend — 上线前修复方案（基于 MIMO 审计追加）

**日期**: 2026-06-22
**来源审计**: `docs/audit/MIMO_AUDIT_REPORT.md`
**执行者**: opencode
**审批者**: HUMAN（PR-6 / PR-8 决策类）
**合规框架**: `.claude/CLAUDE.md`（1 PR 1 事 / 单人 open ≤ 3 / 7 天合规 / 禁横向复制 fix）

---

## §0 阅读说明（opencode 必读）

1. 本文档替代/追加 `HEART_ISSUES_FIX_PLAN_2026-06-21.md`：前者列出的 9 个 PR 已基本完成（commit `ebb8d32` + #49~#68）。本文档处理审计追加发现的剩余项。
2. 每个 PR 严格"1 件事"。**禁止把 N 个 fix 合一个 PR**，禁止把 lint/typing fix 混进业务 PR。
3. **顺序**：Bucket 1 → 2 → 3 → 4。但 PR 之间满足"无 base 依赖"时可并行，详见 §8 排队图。
4. 每个 PR 跑 `bash scripts/ci.sh` 全绿再推。
5. 分支命名：`fix/` `chore/` `feat/` `docs/` 各取其一，**不能 `feature/`**。
6. base = main。merge 后立即删 head 分支（本地 + 远程）。
7. 任何时刻 open PR 数 ≤ 3。
8. 涉及决策的（PR-6 / PR-8）只产出文档，不动代码，等 HUMAN 签字后再开实施 PR。
9. 若发现本文档与实际代码状态冲突（例如已有 PR 覆盖了某项），**立即停下报告**——不要默默跳过。
10. 测试硬规则：每个 PR 必须新增/更新单元或集成测试覆盖修复点；mypy/ruff 新增错误零容忍。

---

## §1 审计 vs 实际复核差异（25+ 条已抽样 verified）

| 类别 | 项 | 审计声明 | 复核结果 | 处置 |
|---|---|---|---|---|
| 🔴 C1 | `workers/runner.py:181` SQL bind 在字符串字面量内 | "已修复" | ✅ `text("... INTERVAL :interval")` + bindparam 已落地 | 不动 |
| 🔴 C2 | `ss04_relationship/models.py:44` 缺 `stage_thresholds` 列 | "已修复" | ✅ line 143-147 已添加 `JSONB server_default text("'{}'::jsonb")` | 不动 |
| 🔴 C3 | minimax/mimo httpx 资源泄漏 | "已修复" | ✅ `MiniMaxProvider.close()` (line 178-180) + `MiMoProvider.close()` (line 308-310) | 不动 |
| 🟠 H1 | Redis 客户端每请求创建 | "已修复" | ✅ `wiring.py:56-62` 模块级 `_redis_client` 单例 | 不动 |
| 🟠 H2 | readiness 创建新 Engine | "已修复" | ✅ `main.py:148` 改为 `get_engine()` 复用 | 不动 |
| 🟠 H3 | cold_db_session 错误路径不关 | "已修复" | ✅ try/finally 已加 | 不动 |
| 🟠 H4 | 5 处 `except Exception: pass` 吞错 | "已修复" | ✅ 全部换为 `logger.debug(..., exc_info=True)` | 不动 |
| 🟠 H6 | `/api/memory/forget` 无认证 | "已修复" | ✅ `routes_state.py:256` 已加 `Depends(get_current_user)` | 不动 |
| 🟠 H7 | `/api/chat` 无 try/except | "已修复" | ✅ `routes.py:156-172` 已加，500 fallback 返 JSON | 不动 |
| 🟠 H13 | 48 个未使用 import | "已修复" | ✅ ruff F401 已清 | 不动 |
| ⚠️ **SS04 6 模块未接入** | "❌ cold_war/reunion/signal_aggregator/trust_tracker/attachment_tracker/anti_gaming 未接入" | **审计陈述过时**。`service.py:21-36` 已 import 4 个并在 process_turn 调用；只剩 `cold_war.py`(541行) + `reunion.py`(378行) 没接，`special_states.py`(164行) 是其轻量替代 | **PR-6** 出决策矩阵 |
| 🟠 H5 | 10 个路由无认证 | "待评估" | ✅ 至少 6 条核心数据路由确无：`/api/voice/synthesize`、`/api/state/{emotion,relationship,inner}`、`/api/memory/recent`、`/api/proactive/pending`；外加 2 条 debug `/api/profile/{records,reset}` 在 prod 暴露 | **PR-1 / PR-2** 修 |
| 🟠 H8 | `_proactive_messages` 无界 | "待评估" | ✅ `inner_loop_worker.py:29` 模块级 list 无界 | **PR-4** 修 |
| 🟠 H9 | inner_loop N+1 | "待评估" | ✅ `inner_loop_worker.py:130-167` per-user fresh session | **PR-4** 顺手修 |
| 🟠 H10 | `api/app.py` 死代码 | "待清理" | ✅ tests 全走 `heart.api.main`；`app.py` 是孤立 duplicate | **PR-5** 删 |
| 🟠 H11 | `replay_snapshots.user_id` VARCHAR | "待评估" | ✅ 与其余模型 UUID 不一致；生产 86 条数据 | **PR-8** 决策 |
| 🟠 H12 | 14 模型 0 FK | "待评估" | ✅ 性能权衡 + 分区表 FK 限制 | **PR-8** 决策 |
| — Rate limiting | 未配置 | — | ✅ `main.py` 无任何限流中间件 | **PR-3** 加 |
| 🟡 M1-M18 | 18 项中优 | "后续" | 多为低危技术债，部分可直接清 | **PR-9** 集中清 |
| 🟢 L1-L8 | 8 项低优 | "后续" | 多为合法/误报；少量可清 | **PR-10** 集中清 |
| ❌ 误诊 | M14（重复 readiness） | `main.py:145` vs `routes.py:178` | `routes.py:178` 是 stub（返硬编码），`main.py:145` 是真探针。删 stub | **PR-5** 顺手 |
| ❌ 误诊 | M15（`orchestrate_with_invariants` 未调） | — | 确实无调用方 | **PR-5** 顺手 |
| 🔴 M16 | `bundle_dump.py:221` f-string SQL | — | ✅ 潜在 SQLi | **PR-7** 修 |

**结论**：审计已修的 10 项真修了；审计待办的 11 项 + 自己漏掉的 SS04 cold_war/reunion 缺口 → 进本文档。

---

## §2 上线前后端必须达成的硬指标（全局验收）

前端开始联调前，逐条勾选：

- [ ] **A1** — 所有承载用户数据的路由（voice/state/memory/proactive/chat/WS）：无 token → 401；token user_id ≠ query user_id → 403；匹配 → 200（PR-1 集成测试覆盖）
- [ ] **A2** — `/api/profile/*` debug 路由在 `HEART_DEV_MODE=false` 时返 404（PR-2）
- [ ] **A3** — 任一路由连发 ≥ 速率上限请求时返 429（PR-3）
- [ ] **A4** — 压力测试 `_proactive_messages` 增长到 5000 条时实际只保留 1000 条且过期项被剔（PR-4）
- [ ] **A5** — inner_loop_worker tick 100 个活跃用户时 DB session 创建数 = 1（PR-4）
- [ ] **A6** — `heart/api/app.py` 不存在；`uvicorn heart.api.main:app` 正常启动；`routes.py` 无 `/api/health/ready` stub（PR-5）
- [ ] **A7** — `bundle_dump.py` 无 f-string SQL；新增 SQLi payload 测试通过（PR-7）
- [ ] **A8** — PR-6 决策文档已签字（HUMAN 选 A 或 B）
- [ ] **A9** — PR-8 决策文档 4 个 ADR 已签字（HUMAN）
- [ ] **A10** — `bash scripts/ci.sh` 全绿（lint + unit + schema-validation）；mypy 新增错误 0
- [ ] **A11** — 真链路 chat 5 轮：无 500、无 `composer_memory_block_failed`、`sessions.turn_count` 持续递增、每轮 `emotion_events` +1
- [ ] **A12** — `docker ps` encoder-worker 跑 30 分钟无 restart

---

## §3 Bucket 1 — 安全（前端启动前必须）

### PR-1 `fix/api-auth-coverage`

**目标**: 所有承载用户数据的路由强制认证 + user_id 比对。
**目标 Issue**: H5（核心数据路由部分）
**改的文件**:
  - `backend/heart/api/routes_voice.py:25` — `POST /api/voice/synthesize`
  - `backend/heart/api/routes_state.py:31` — `GET /api/state/emotion`
  - `backend/heart/api/routes_state.py:53` — `GET /api/state/relationship`
  - `backend/heart/api/routes_state.py:106` — `GET /api/state/inner`
  - `backend/heart/api/routes_state.py:141+` — `GET /api/memory/recent` 及同文件其他 memory_router 路由
  - `backend/heart/api/routes_proactive.py:23` — `GET /api/proactive/pending`
  - `backend/heart/api/routes_chat_ws.py:215` — WebSocket `/api/chat/ws`（改 `?token=` 或 Sec-WebSocket-Protocol 校验）

**Diff 思路**（HTTP 路由统一 pattern）:
```python
from heart.core.auth import get_current_user, TokenData
from fastapi import Depends, HTTPException

@router.get("/emotion")
async def get_emotion_state(
    user_id: UUID = Query(...),
    character_id: str = Query("rin"),
    current_user: TokenData = Depends(get_current_user),
):
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(403, "Cannot read another user's state")
    # ... 原逻辑
```

WS 单独处理：
```python
@router.websocket("/api/chat/ws")
async def chat_ws(websocket: WebSocket, token: str = Query(...)):
    try:
        user = await verify_token(token)  # 复用 core/auth 的 decoder
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    # ... 原逻辑，所有发到本 ws 的消息必须 user_id == user.user_id
```

**测试**: 新增 `backend/tests/integration/test_api_auth_coverage.py`
- 每条路由参数化 3 case：(no token → 401)、(token uid ≠ query uid → 403)、(match → 200/正常返回)。
- WS：参数化 (token missing → 1008 close)、(token valid → accepts) 两 case。

**本地验收**:
```bash
cd backend && pytest tests/integration/test_api_auth_coverage.py -v
```

**PR 模板**:
- 标题: `fix(api): require auth + uid match on user-data routes (H5)`
- Body:
  - Summary: 7 routes now reject (uid mismatch → 403, no token → 401). WS uses `?token=` query.
  - Test plan: `pytest tests/integration/test_api_auth_coverage.py -v`
  - Audit ref: `docs/audit/MIMO_AUDIT_REPORT.md#H5`

---

### PR-2 `chore/api-gate-debug-routes`

**目标**: `/api/profile/*` 在 prod 默认不挂载，仅 `HEART_DEV_MODE=true` 时启用。
**目标 Issue**: H5（debug 子项）
**改的文件**:
  - `backend/heart/api/routes.py:183-198` — 把 `/profile/records` + `/profile/reset` 从主 `router` 抽到新 `dev_router`
  - `backend/heart/api/main.py:189+` — `include_router(dev_router)` 包在 `if settings.dev_mode:` 内
  - `backend/heart/core/config.py` — 确认有 `dev_mode: bool = Field(default=False, alias="HEART_DEV_MODE")`，若没有则加

**Diff 思路**:
```python
# routes.py
dev_router = APIRouter(prefix="/api/profile", tags=["debug"])

@dev_router.get("/records")
async def get_profile_records(): ...

@dev_router.post("/reset")
async def reset_profile_records(): ...
```
```python
# main.py
if getattr(settings, "dev_mode", False):
    from heart.api.routes import dev_router as profile_dev_router
    app.include_router(profile_dev_router)
```

**测试**:
- `tests/integration/test_dev_routes_gated.py`：dev=false → `/api/profile/records` 404；dev=true → 200。

**本地验收**:
```bash
cd backend && HEART_DEV_MODE=false pytest tests/integration/test_dev_routes_gated.py::test_default_404 -v
cd backend && HEART_DEV_MODE=true pytest tests/integration/test_dev_routes_gated.py::test_enabled_200 -v
```

**PR 模板**:
- 标题: `chore(api): gate debug profile routes behind HEART_DEV_MODE`
- Body: short summary + test plan + audit ref H5.

---

### PR-3 `feat/api-rate-limit`

**目标**: 引入速率限制中间件，覆盖 login / chat / voice / memory。
**目标 Issue**: 审计 §4 "Rate Limiting 未配置"
**前置**: `pip show slowapi`；若未装则 `pip install slowapi`，写进 `backend/requirements.txt`。
**改的文件**:
  - `backend/requirements.txt` — 加 `slowapi>=0.1.9`
  - `backend/heart/api/main.py` — 注册 limiter + middleware
  - `backend/heart/api/routes.py`、`routes_voice.py`、`routes_state.py` — 各热路径加 `@limiter.limit(...)` decorator

**Diff 思路**:
```python
# main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=lambda req: f"{get_remote_address(req)}:{req.headers.get('authorization','')[:32]}")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)
```
```python
# routes.py
@router.post("/chat")
@limiter.limit("30/minute")
async def chat(request: Request, ...):
    ...
```

限额建议（可调）:
| 路由 | 限额 |
|---|---|
| `/api/auth/login` | 10/分钟（防爆破） |
| `/api/chat` | 30/分钟 |
| `/api/voice/synthesize` | 20/分钟 |
| `/api/state/*` / `/api/memory/*` | 60/分钟 |

**测试**:
- `tests/integration/test_rate_limit.py`：模拟 IP 连发到上限 → 429。

**本地验收**: `pytest tests/integration/test_rate_limit.py -v`

**PR 模板**:
- 标题: `feat(api): rate limiting via slowapi`
- Body: 限额表 + middleware 接入位置 + test plan.

---

## §4 Bucket 2 — 稳定性

### PR-4 `fix/ss06-proactive-queue-bound`

**目标**: 修复 `_proactive_messages` 无界增长 + inner_loop tick N+1 查询。
**目标 Issue**: H8 + H9
**改的文件**:
  - `backend/heart/ss06_inner_state/inner_loop_worker.py:29` — list → `deque(maxlen=1000)`
  - `backend/heart/ss06_inner_state/inner_loop_worker.py:32-58` — 修 `get_pending_proactive_messages`，新增过期剔除
  - `backend/heart/ss06_inner_state/inner_loop_worker.py:109-180` — 把 `_tick_all_active_users` 改为单 session + 单 JOIN 查询

**Diff 思路**:
```python
# H8
import collections
_proactive_messages: collections.deque[ProactiveMessage] = collections.deque(maxlen=1000)

def get_pending_proactive_messages(user_id, character_id=None, since=None):
    if since is None:
        since = timedelta(days=7)
    cutoff = datetime.now(timezone.utc) - since
    # 顺手剔除 cutoff 之前的（保留有限大小，不必清理太狠）
    return [
        m for m in _proactive_messages
        if m.user_id == user_id
        and (character_id is None or m.character_id == character_id)
        and m.created_at >= cutoff
    ]
```
```python
# H9 — 改成单查询
async def _tick_all_active_users(self):
    async with self.db_session_factory() as session:
        rows = (await session.execute(text("""
            SELECT s.user_id, s.character_id, s.last_activity_at,
                   r.current_stage, r.intimacy_level
            FROM sessions s
            LEFT JOIN relationship_states r
              ON r.user_id = s.user_id AND r.character_id = s.character_id
            WHERE s.last_activity_at > NOW() - INTERVAL '7 days'
        """))).fetchall()
        # 单 session 内一次性 tick 所有用户
        for row in rows:
            ...  # _check_anniversary 等仍可用该 session
```

**测试**:
- `tests/unit/test_inner_loop_worker.py::test_proactive_queue_bound` — push 1500 条，断言 len == 1000，首条被丢弃
- `tests/unit/test_inner_loop_worker.py::test_expired_messages_filtered` — 注入 8 天前的，断言不在 result
- `tests/integration/test_inner_loop_session_count.py` — 用 sqlalchemy event hook 计数 session creation；100 mock 用户 tick 后断言 == 1

**本地验收**: `pytest tests/unit/test_inner_loop_worker.py tests/integration/test_inner_loop_session_count.py -v`

**PR 模板**:
- 标题: `fix(ss06): bound proactive queue + collapse inner loop N+1`
- Body: 列两个 metric — `deque(maxlen=1000)` 截断 + DB session 数 100→1。

---

### PR-5 `chore/cleanup-dead-code`

**目标**: 删 `app.py`、删 `routes.py` 重复 readiness、删 `middleware.py` 未调函数。
**目标 Issue**: H10 + M14 + M15
**改的文件**:
  - `backend/heart/api/app.py` — **删除整个文件**
  - `backend/heart/api/routes.py:178-180` — 删 `/health/ready` stub（main.py:145 是真探针）
  - `backend/heart/api/middleware.py:28` — 删 `orchestrate_with_invariants` （先 grep 确认零调用方）

**Diff 思路**:
```bash
# 验证 app.py 真无 prod 引用
grep -rn "from heart.api.app\|from heart.api import app" backend/heart/ \
  | grep -v "__pycache__\|tests"
# 期望: 仅 main.py 不引用，无 prod 引用。
# 注意 tests/ 里 test_echo_chat.py / test_state_api.py / test_api_chat_real_pipeline.py 都 import 自 heart.api.main，OK。
rm backend/heart/api/app.py

# 验证 orchestrate_with_invariants 零调用
grep -rn "orchestrate_with_invariants" backend/ | grep -v "middleware.py"
# 期望: 空。
```
若 grep 发现意外引用，**立即停下报告**。

**测试**:
- 不需要新测；跑全套 `pytest tests/` 全绿 + `uvicorn heart.api.main:app --reload` 启动不报。

**本地验收**:
```bash
cd backend && pytest tests/ -q && uvicorn heart.api.main:app --port 8001 &
sleep 3
curl -sf http://localhost:8001/health/live  # 200
curl -sf http://localhost:8001/health/ready  # 200 / 503 (DB unavailable 时)
kill %1
```

**PR 模板**:
- 标题: `chore(api): remove duplicate app.py + dead readiness + unused middleware`
- Body: 3 项删除 + 调用方 grep 证据。

---

### PR-6 `docs/ss04-cold-war-reunion-decision`

**目标**: 决定 `cold_war.py`(541行) + `reunion.py`(378行) 是否接入主链路；不写代码。
**目标 Issue**: 审计漏诊的 SS04 真正缺口
**改的文件**:
  - **新增** `docs/design/ss04_special_states_implementation_choice.md`

**调查清单（必须做完才能写文档）**:
1. 读 `backend/heart/ss04_relationship/special_states.py` 全文（164 行），列出公共 API：
   - `class SpecialState(Enum)`
   - `def evaluate_special_state(...)`
   - `def advance_reunion_turn(...)`
   - 其他
2. 读 `backend/heart/ss04_relationship/cold_war.py`（541 行），列出公共 API + 触发条件、强度衰减、信号冷却、reconciliation 多阶段。
3. 读 `backend/heart/ss04_relationship/reunion.py`（378 行），列出 reunion phases、warmth signals、anniversary triggers。
4. 跑现有测试 `pytest backend/tests/unit/ -k "ss04 or relationship" -v`，记录哪些测试覆盖了 special_states vs cold_war vs reunion。
5. 读 `runtime_specs/04_*.md` §3.5 step 4 — spec 上写的特殊状态机的"应有能力"。

**文档结构**:
```markdown
# SS04 Special States — 实现路线决策

## 1. 背景
service.py:21-36 已接入 anti_gaming/attachment_tracker/signal_aggregator/trust_tracker。
process_turn step 4 走 special_states.py 的轻量实现，cold_war.py / reunion.py 未被任何 prod 代码引用。

## 2. 能力对比
| 能力 | special_states.py | cold_war.py | reunion.py |
| 4 种 enum | ✅ | (作为 cold_war 内部) | (reunion phases) |
| 强度衰减 | ❌ | ✅ | — |
| 信号冷却 | ❌ | ✅ | — |
| Reconciliation 多阶段 | ❌ | ✅ | — |
| Reunion phases | ❌ | — | ✅ |
| Warmth signals | ❌ | — | ✅ |
| Anniversary triggers | ❌ | — | ✅ |
| 测试覆盖 | 19 tests | <调查后填写> | <调查后填写> |

## 3. 选项
### 选项 A — 接入完整版
- 改 service.py:296-333 → 调用 cold_war / reunion 的类
- 跑 19 个 special_states 测试：要么兼容，要么 spec-aligned 替换
- 工作量评估: <X 小时>
- 风险: 行为变化、需要回归 SS04 全套测试

### 选项 B — 文档化 special_states 为正式实现
- 删除 cold_war.py / reunion.py（先确认无 spec 强制要求）
- 在 service.py 顶部加注释说明"轻量实现，跳过强度衰减/信号冷却"
- 工作量评估: 30 分钟

## 4. 推荐
<opencode 给一个倾向 + 理由，最终由 HUMAN 拍板>

## 5. 后续 PR
- 选 A → PR-6a `feat/ss04-wire-cold-war-reunion`
- 选 B → PR-6b `chore/ss04-remove-unused-modules`
```

**测试**: 无（决策文档）

**本地验收**: 文档存在 + 4 张表格 + HUMAN 签字。

**PR 模板**:
- 标题: `docs(ss04): decide cold_war/reunion wiring vs delete`
- Body: 决策矩阵摘要 + "需要 HUMAN review 后另开实施 PR"。

---

### PR-7 `fix/replay-bundle-dump-sql-injection`

**目标**: 把 `replay/bundle_dump.py:221` 的 f-string SQL 改为绑定参数。
**目标 Issue**: M16
**改的文件**: `backend/heart/replay/bundle_dump.py`

**Diff 思路**:
```bash
# 先确认所有 f-string SQL 位置
grep -nE 'f"(SELECT|INSERT|UPDATE|DELETE)' backend/heart/replay/bundle_dump.py
```
对每处:
```python
# before
result = await session.execute(text(f"SELECT * FROM x WHERE id = '{user_id}'"))

# after
result = await session.execute(
    text("SELECT * FROM x WHERE id = :uid"),
    {"uid": str(user_id)},
)
```

**测试**:
- `tests/unit/test_bundle_dump_sql_safety.py`：构造 `user_id="'; DROP TABLE x; --"` 调用 dump，断言不抛、表未变。

**本地验收**: `pytest tests/unit/test_bundle_dump_sql_safety.py -v`

**PR 模板**:
- 标题: `fix(replay): use bindparams instead of f-string SQL (M16)`
- Body: 改了几处 + SQLi payload 测试通过。

---

## §5 Bucket 3 — 数据完整性（决策类）

### PR-8 `docs/data-integrity-decision`

**目标**: 不写代码；输出决策文档让 HUMAN 拍板。
**目标 Issue**: H11 + H12 + M5 + M7
**改的文件**: **新增** `docs/design/data_integrity_decisions_2026-06-22.md`

**包含 4 个 ADR**（每个走 标题/背景/选项/决策/后续 5 段）:

1. **ADR-001 `replay_snapshots.user_id` 类型**
   - 背景：当前 VARCHAR；其余 14 模型用 UUID；生产已落 86 条数据。
   - 选项 A：migration 改 UUID，转换现有数据。
   - 选项 B：保留 VARCHAR，文档化为"特殊例外"。
   - 风险/工作量/建议。

2. **ADR-002 零外键约束**
   - 背景：14 模型 0 FK；分区表 PG FK 限制；当前靠应用层校验。
   - 选项 A：非分区表加 FK（episodes/identity/etc 哪些可加）。
   - 选项 B：全部维持现状 + 强化应用层 invariant 检查。
   - 选项 C：partial FK + DLQ 兜底。

3. **ADR-003 分区表 PK 与 ORM 不一致**
   - 背景：M5 — alembic migration 跟 ORM Mapped 定义的 PK 字段集不同。
   - 列出每个分区表的 alembic PK vs ORM PK 对比。
   - 决策：以 alembic 为准修 ORM，或反之。

4. **ADR-004 `sessions` / `safety_events` 无 ORM 模型**
   - 背景：M7 — 走 raw SQL；类型不安全；难重构。
   - 选项 A：补 ORM model（工作量 ~半天 / 模型）。
   - 选项 B：维持 raw SQL + 用 dataclass 包装查询结果。

**测试**: 无

**本地验收**: 文档存在 + 4 个 ADR + HUMAN 签字。

**PR 模板**:
- 标题: `docs(data): integrity decisions ADR-001..004`
- Body: 4 项摘要 + "前端启动前需 HUMAN 签字"。

---

## §6 Bucket 4 — 技术债（与前端并行）

### PR-9 `chore/medium-debt-cleanup-1`

**目标**: 集中处理 M1-M18 中**可执行**的子集（不引入新业务逻辑）。
**目标 Issue**: M1/M2/M3/M4/M9/M10/M11/M13/M18
**改的文件**: 多处，统一在 1 个 PR

**子任务清单**:
- **M1 TODO** — 给现有 4 个 TODO 加 `# TODO(#issue-N)` issue 链接（不实现）
  - `ss05_composer/token_budget.py:91`
  - `workers/memory_consolidator.py:121`
  - `ss03_emotion/repair.py:419`
  - `ss02_memory/retriever/base.py:238, 263`
- **M2 空函数体** — `grep -rEn "def [a-z_]+\(.*\):\s*$" backend/heart/ -A 2 | grep -B 2 "pass\s*$"`：要么 `raise NotImplementedError("tracked in #N")`，要么删
- **M3 # type: ignore** — `grep -rn "# type: ignore" backend/heart/ | wc -l` 应 ≤ 21；挑无 issue 链接的几个补 `# type: ignore[arg-type]  # see #N`
- **M4 ReplaySnapshot 旧 Column API** — `backend/heart/replay/__init__.py`：`Column(...)` → `Mapped[...] = mapped_column(...)`，对应 type hints
- **M9 宽泛 except** — 16 处 `except Exception` 仅 log：拆为具体 exception 或加 `exc_info=True`
- **M10 fire-and-forget** — `orchestrator.py:672,684`：包 `_safe_wrap(coro)` helper
- **M11 asyncio.gather** — `layer_aggregator.py:259`：加 `return_exceptions=True`，下游过滤 BaseException 实例
- **M13 validate_jwt_secret** — 在 `main.py` lifespan startup 调用 `settings.validate_jwt_secret()`
- **M18 `__import__()`** — 4 处替换为顶层 import（先确认无循环依赖）

**测试**:
- 跑全套 `pytest tests/` 全绿
- `mypy backend/heart/ --strict | wc -l` 不增

**本地验收**: `bash scripts/ci.sh`

**PR 模板**:
- 标题: `chore(debt): medium-tier cleanup batch 1`
- Body: 子任务 checklist + 0 行为变更声明 + CI 通过证明。

---

### PR-10 `chore/low-debt-cleanup`

**目标**: 处理 L1-L8 中可清的（不动业务）。
**目标 Issue**: L1/L2/L4/L7
**改的文件**:
- L1: `ss02_memory/encoder/fast.py:104` — 删 deprecated 注释或加迁移说明
- L2: `ss02_memory/mode.py:16` — 删 stub 注释（regex 已下线）
- L4: 26 处 `except: pass` in except 块 — 加 `logger.debug("nested_handler_failed", exc_info=True)`
- L7: `scripts/seed_demo.py:589, 660` — 错误吞没改 `logger.warning`

**L3/L5/L6/L8 不动**: `NotImplemented` 在 `__lt__/__le__` 是 Python 富比较惯例不是 bug；其余是合法测试工具或合法 stub。

**测试**: 全套 pytest + ruff

**本地验收**: `bash scripts/ci.sh`

**PR 模板**:
- 标题: `chore(debt): low-tier cleanup`
- Body: 改动列表 + 显式说明 L3/L5/L6/L8 不动的理由（避免 reviewer 怀疑漏了）。

---

## §7 全局验收清单（前端启动前 100% 绿）

| # | 检查项 | 命令 / 证据 |
|---|---|---|
| A1 | 认证全覆盖 | `pytest backend/tests/integration/test_api_auth_coverage.py -v` 全绿 |
| A2 | dev 路由 prod 关闭 | `HEART_DEV_MODE=false uvicorn ...; curl -i /api/profile/records` 返 404 |
| A3 | rate limit 生效 | `pytest backend/tests/integration/test_rate_limit.py -v` 全绿 |
| A4 | proactive queue 有界 | `pytest backend/tests/unit/test_inner_loop_worker.py::test_proactive_queue_bound -v` |
| A5 | inner_loop 单 session | `pytest backend/tests/integration/test_inner_loop_session_count.py -v` |
| A6 | app.py 删 + readiness 单一 | `[ ! -f backend/heart/api/app.py ]` + `grep -c "/health/ready" backend/heart/api/routes.py` == 0 |
| A7 | bundle_dump 无 f-string SQL | `grep -E 'f"(SELECT|INSERT|UPDATE|DELETE)' backend/heart/replay/bundle_dump.py` 空 |
| A8 | PR-6 决策签字 | HUMAN approve PR |
| A9 | PR-8 决策签字 | HUMAN approve PR |
| A10 | CI 全绿 | `bash scripts/ci.sh` |
| A11 | 真链路 5 轮稳定 | 手动 `curl POST /api/chat`×5 + 查 `sessions.turn_count` + `emotion_events` |
| A12 | encoder-worker 稳定 | `docker logs heart-encoder-worker --since 30m \| grep -c restart` == 0 |

---

## §8 开 PR 顺序 + 并行图

**约束**: 单人 open ≤ 3。PR 间无 base 依赖（各自从 main 开分支）。

**推荐节奏**（每条线 1 个 PR 同时 open，每合 1 个开下一个）:

```
Phase 1（开始）:
  open  PR-1 (auth)  ║  open  PR-4 (queue+N+1)  ║  open  PR-8 (data ADRs)
  ╔═════════════════════════════════════════════════════════════════════╗
  ║  PR-1 / PR-4 / PR-8 同时进行                                      ║
  ║  PR-8 是文档，最先合（HUMAN 签字后）                             ║
  ╚═════════════════════════════════════════════════════════════════════╝

Phase 2（PR-8 merged → 还剩 2 open，可补 1 个）:
  open PR-2 (debug gate)

Phase 3（PR-1 merged → 补 PR-3）:
  open PR-3 (rate limit)

Phase 4（PR-4 merged → 补 PR-5）:
  open PR-5 (cleanup)

Phase 5（PR-2 或 PR-3 merged → 补 PR-7）:
  open PR-7 (SQLi)

Phase 6（其余 merged 后）:
  open PR-6 (decision doc)  → HUMAN approve

Phase 7（PR-6 决策后）:
  open PR-6a 或 PR-6b（实施）

Phase 8（与前端并行）:
  open PR-9 (medium debt)
  open PR-10 (low debt)
```

每个 PR 预计耗时（不含 review）:
| PR | est. dev time | review block? |
|---|---|---|
| PR-1 | 半天 | HUMAN review auth pattern |
| PR-2 | 1 小时 | 简单 |
| PR-3 | 半天 | 依赖确认 |
| PR-4 | 半天 | 较稳 |
| PR-5 | 1 小时 | 简单 |
| PR-6 | 半天调查 + 0 代码 | HUMAN 决策 ⚠️ |
| PR-7 | 1 小时 | 简单 |
| PR-8 | 半天写 ADR | HUMAN 决策 ⚠️ |
| PR-9 | 1-2 天 | 大 |
| PR-10 | 半天 | 简单 |

---

## §9 附录：文件 + 行号索引

**前端启动前必改**:
- `backend/heart/api/routes_voice.py:25` — voice 路由认证
- `backend/heart/api/routes_state.py:31, 53, 106, 141+` — state/memory 路由认证
- `backend/heart/api/routes_proactive.py:23` — proactive 路由认证
- `backend/heart/api/routes_chat_ws.py:215` — WS 认证
- `backend/heart/api/routes.py:183-198` — debug 路由 dev gate
- `backend/heart/api/main.py` — rate limit middleware 接入
- `backend/heart/ss06_inner_state/inner_loop_worker.py:29, 109-180` — H8 + H9
- `backend/heart/api/app.py` — 删整个文件
- `backend/heart/api/routes.py:178-180` — 删重复 readiness stub
- `backend/heart/api/middleware.py:28` — 删 `orchestrate_with_invariants`
- `backend/heart/replay/bundle_dump.py:221` — SQLi 修复
- 决策对象：H11/H12/M5/M7 — PR-8 doc

**SS04 决策对比涉及文件**:
- `backend/heart/ss04_relationship/service.py:296-333` — 当前调用 special_states 的 entry point
- `backend/heart/ss04_relationship/special_states.py`（164 行）— 当前实现
- `backend/heart/ss04_relationship/cold_war.py`（541 行）— 候选完整版
- `backend/heart/ss04_relationship/reunion.py`（378 行）— 候选完整版

**技术债涉及主要文件**:
- `backend/heart/ss05_composer/token_budget.py:91`、`workers/memory_consolidator.py:121`、`ss03_emotion/repair.py:419`、`ss02_memory/retriever/base.py:238/263` — TODO
- `backend/heart/replay/__init__.py` — ReplaySnapshot 旧 API
- `backend/heart/ss07_orchestration/orchestrator.py:672, 684` — fire-and-forget
- `backend/heart/ss05_composer/layer_aggregator.py:259` — gather return_exceptions
- `backend/heart/core/config.py:133` — validate_jwt_secret 调用点
- `backend/heart/scripts/seed_demo.py:589, 660` — 错误吞没

---

**最后更新**: 2026-06-22
**版本**: v1.0
**前置文档**: `docs/audit/MIMO_AUDIT_REPORT.md`
**配套合规**: `.claude/CLAUDE.md`
