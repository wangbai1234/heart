# Orchestrator — Minimum Viable Design

> **Scope**: SS07 §3.4.1 (Orchestrator) + §3.7 (Session Manager) + §3.8 (Circuit Breaker) only.
> Critic / Director / Wellbeing / Event Bus / Model Router-failover **postponed**.
> **Goal**: 把 `routes.py:/api/chat` 内联的 5-step 管线整体迁出，让 routes 只剩 "parse request → call orchestrator → serialize response"。

---

## 1. 现状审计

### 1.1 `ss07_orchestration/` 现状（94 LOC）

只有 `middleware.py::orchestrate_with_invariants` — 一个 wrapper，在 turn 完成后按采样率跑 invariant checks。**它不是 orchestrator，它是 hook**。完全不调度任何 subsystem。

### 1.2 `routes.py:/api/chat` 内联管线（routes.py:136-316）

`chat()` 内部硬编码了完整的 hot path：

| 行号 | 步骤 | 直接调用 |
|------|------|---------|
| 154-185 | session/ctx 构造 | 内联 UUID 解析、`CompositionContext` 构造 |
| 187-189 | auth span | placeholder |
| 192-246 | safety pre-filter | `safety_agent.classify(...)` + PURPLE 分支 + `_write_safety_event` |
| 249-260 | composer 装配 | `build_composer_service(db_session)` |
| 262-275 | composer.compose | `composer.compose(...)` + fallback message |
| 277-294 | memory_encode | `memory_svc.encode_fast(...)` |
| 296-310 | inner_loop tick | `asyncio.ensure_future(asyncio.to_thread(inner_svc.tick, ...))` |

**问题**：
- routes 层知道 5 个 subsystem 的存在和调用顺序 — 紧耦合
- PURPLE care-path 的逻辑（locale/jurisdiction 解析、`_write_safety_event`、构造响应）写在 routes 里
- Composer build 失败、composer.compose 失败的 fallback 文案在 routes 里
- 没有 trace_id 贯穿（用 message_id 凑），没有 circuit breaker，没有 session 概念
- 违反 SS07 O-2（cross-subsystem 通信应通过 adapter/event bus）

---

## 2. 最小可用范围

| 组件 | 本期实现 | 推迟到后续 |
|------|---------|-----------|
| **Orchestrator** | ✅ 顶层调度（替换 routes 内联） | proactive_send / session_start handler |
| **SessionManager** | ✅ load_session（in-memory + lazy）、turn 计数、trace_id 生成 | 跨 device sync、reunion 检测、DB 持久化 |
| **CircuitBreaker** | ✅ 三态机 + per-service 注册（safety / composer / llm） | DB 持久化、跨进程一致性 |
| Safety Agent | 复用现有 `safety/safety_agent.py` | 多层 LLM 分类 |
| Composer | 复用现有 `ss05_composer/service.py` | 不动 |
| Memory / Inner | 复用现有 service | 不动 |
| Director / Critic / Wellbeing / Model Router-failover / Event Bus | ❌ 不实现 | 后续 PR |
| PURPLE care-path | ✅ 走专用分支（不进 composer） | 专用 care prompt、main_strong 强制 |

---

## 3. 组件设计

### 3.1 目录结构

```
backend/heart/ss07_orchestration/
├── __init__.py
├── middleware.py            # 已有，保留（invariant sampling）
├── orchestrator.py          # 新建 ← Orchestrator
├── session_manager.py       # 新建 ← SessionManager
├── circuit_breaker.py       # 新建 ← CircuitBreaker
└── models.py                # 新建 ← TurnRequest / TurnResponse / Session
```

### 3.2 `models.py` — 接口数据类

```python
@dataclass
class TurnRequest:
    user_id: UUID
    character_id: str
    user_message: str
    history: list[dict]          # [{"role", "content"}, ...]
    trace_id: UUID               # = turn_id, 贯穿所有 span
    modality: str = "text"

@dataclass
class TurnResponse:
    response: str
    character_id: str
    trace_id: UUID
    path: Literal["normal", "care", "fallback"]
    safety_severity: str | None  # GREEN / YELLOW / ... / PURPLE

@dataclass
class Session:
    session_id: UUID
    user_id: UUID
    character_id: str
    started_at: datetime
    last_activity_at: datetime
    turn_count: int
    suicide_protocol_active: bool = False
```

> Spec §4.1 中的 device、modality_history、wellbeing 字段全部 **推迟**。本期 in-memory，不入 DB。

### 3.3 `circuit_breaker.py` — 最小三态机

```python
class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 5,
                 window_sec: int = 60, open_sec: int = 30):
        ...
    def record_success(self) -> None: ...
    def record_failure(self) -> None: ...
    def is_open(self) -> bool:  # 副作用：到期自动转 half_open

class BreakerRegistry:
    """Process-singleton, 按 service name 注册."""
    def get(self, name: str) -> CircuitBreaker: ...

# 预注册的 services
_DEFAULTS = {
    "safety":   dict(threshold=5,  window_sec=60, open_sec=30),
    "composer": dict(threshold=3,  window_sec=60, open_sec=30),
    "llm":      dict(threshold=5,  window_sec=60, open_sec=30),
}
```

**fallback 策略**：本期统一返回 Soul-flavored 短句（沿用 routes.py 现有 `name_map` 文案），不做 cached-anchor 之类的高级降级。

### 3.4 `session_manager.py` — 最小实现

```python
class SessionManager:
    def __init__(self):
        self._sessions: dict[tuple[UUID, str], Session] = {}
        self._lock = asyncio.Lock()

    async def load_session(self, user_id: UUID, character_id: str) -> Session:
        """Get-or-create. No cross-device, no DB."""
        ...

    async def record_turn(self, session: Session) -> None:
        """turn_count++, last_activity_at = now."""
        ...
```

> 本期 **不调用** `emotion_service.load_for_session` 之类的状态恢复 —— 那些 service 现在是 stateless / per-call lookup，无需 session-level reload。等 SS03/SS04 引入 session-scoped cache 时再补。

### 3.5 `orchestrator.py` — 核心

```python
class Orchestrator:
    def __init__(
        self,
        safety_agent,
        composer_builder,        # async (db_session) -> ComposerService
        session_manager: SessionManager,
        breakers: BreakerRegistry,
        safety_event_writer,     # async (db, user_id, turn_id, classification)
    ): ...

    async def handle_turn(
        self,
        req: TurnRequest,
        db_session,              # passed through for composer + safety audit
    ) -> TurnResponse:
        session = await self.session_manager.load_session(req.user_id, req.character_id)
        profiler = TurnProfiler(session_id=str(req.user_id))

        with profiler:
            # 1. Safety pre-filter (with breaker)
            classification = await self._safety_pre(req, db_session, profiler)
            if classification and classification.severity.value == "PURPLE":
                return await self._care_path(req, classification, db_session, session)

            # 2. Composer build + compose (with breaker)
            response_text = await self._compose(req, db_session, profiler)

            # 3. Async cold-path tasks (memory + inner). Fire-and-forget.
            self._fire_cold_path(req, profiler)

            await self.session_manager.record_turn(session)

        return TurnResponse(
            response=response_text, character_id=req.character_id,
            trace_id=req.trace_id, path="normal",
            safety_severity=(classification.severity.value if classification else None),
        )

    # ── private ──
    async def _safety_pre(self, req, db, profiler): ...
    async def _care_path(self, req, classification, db, session) -> TurnResponse: ...
    async def _compose(self, req, db, profiler) -> str: ...
    def _fire_cold_path(self, req, profiler) -> None: ...
```

**Breaker 包装模式**（每个 critical 调用复用）：

```python
breaker = self.breakers.get("safety")
if breaker.is_open():
    return None  # skip safety → fail-open? 见 §6 决策
try:
    result = await self.safety_agent.classify(...)
    breaker.record_success()
    return result
except Exception:
    breaker.record_failure()
    raise  # 上层决定 fallback
```

### 3.6 Wiring（注入到 FastAPI）

在 `api/wiring.py` 加：

```python
@lru_cache
def get_session_manager() -> SessionManager: ...

@lru_cache
def get_breaker_registry() -> BreakerRegistry: ...

@lru_cache
def get_orchestrator():
    from heart.ss07_orchestration.orchestrator import Orchestrator
    return Orchestrator(
        safety_agent=get_safety_agent(),
        composer_builder=build_composer_service,
        session_manager=get_session_manager(),
        breakers=get_breaker_registry(),
        safety_event_writer=_write_safety_event,  # 从 routes 抽出
    )
```

---

## 4. Topology

### 4.1 调用拓扑（本期）

```
                    ┌──────────────────────┐
                    │   FastAPI /api/chat  │
                    │   (routes.py)        │
                    └──────────┬───────────┘
                               │ TurnRequest
                               ▼
                    ┌──────────────────────┐
                    │   Orchestrator       │ ◀── SessionManager
                    │   .handle_turn()     │ ◀── BreakerRegistry
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼─────────────────────────────┐
        │ sync hot path        │                             │ async cold path
        ▼                      ▼                             ▼
  ┌──────────┐         ┌──────────────┐              ┌──────────────┐
  │ Safety   │         │ Composer     │              │ Memory.enc   │
  │ Agent    │         │ (SS05)       │              │ Inner.tick   │
  │.classify │         │ .compose     │              │ (fire-fgt)   │
  └────┬─────┘         └──────┬───────┘              └──────────────┘
       │                      │
       │ PURPLE ──► care_path │
       │                      ▼
       │              ┌──────────────┐
       │              │ ModelRouter  │ (existing, no failover yet)
       │              └──────────────┘
       ▼
  ┌──────────────────┐
  │ safety_events    │  (DB write, audit)
  └──────────────────┘
```

### 4.2 调用顺序 + Fallback

```
turn arrives
   │
   ▼
[SessionManager.load_session]   ── always succeeds (in-memory)
   │
   ▼
[Breaker("safety").is_open?]
   ├─ open  → skip classify, treat as GREEN, log "safety_breaker_open"
   └─ closed↓
[SafetyAgent.classify]
   ├─ raises → breaker.record_failure → 503 (fail-closed, §6 决策)
   ├─ PURPLE → _care_path → write safety_event → return care response
   └─ GREEN/YELLOW/ORANGE/RED → continue
   │
   ▼
[Breaker("composer").is_open?]
   ├─ open  → return Soul-flavored fallback msg
   └─ closed↓
[build_composer_service + composer.compose]
   ├─ raises → breaker.record_failure → Soul-flavored fallback msg
   └─ ok → response_text
   │
   ▼
[Fire-and-forget cold path]   ── memory.encode_fast + inner.tick
   │
   ▼
[SessionManager.record_turn]
   │
   ▼
return TurnResponse
```

---

## 5. routes.py 改造 — 要删什么

`/api/chat` 改成约 30 行：

```python
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    last = _last_user_message(request.messages)
    if not last:
        raise HTTPException(400, "No user message found")

    turn_req = TurnRequest(
        user_id=_coerce_uuid(current_user.user_id),
        character_id=request.character_id,
        user_message=last,
        history=[{"role": m.role, "content": m.content} for m in request.messages[:-1]],
        trace_id=uuid4(),
    )
    turn_resp = await orchestrator.handle_turn(turn_req, db_session=db_session)
    return ChatResponse(
        response=turn_resp.response,
        character_id=turn_resp.character_id,
        message_id=str(turn_resp.trace_id),
    )
```

**routes.py 中要删除/迁移的代码**：

| routes.py 位置 | 当前内容 | 去向 |
|---------------|---------|------|
| L156 | `TurnProfiler` 构造 | → `Orchestrator.handle_turn` |
| L171-185 | `CompositionContext` 构造 | → `Orchestrator._compose` |
| L188-189 | `p.span("auth")` 空 span | **删除**（无意义） |
| L192-246 | safety classify + PURPLE 分支 + locale/jurisdiction + `_write_safety_event` 调用 | → `Orchestrator._safety_pre` / `_care_path` |
| L204-211 | `os.getenv("HEART_JURISDICTION")` + `resolve_care_response` | → `Orchestrator._care_path`（routes 不该读环境变量） |
| L237-246 | safety fail-closed 503 | → `Orchestrator._safety_pre`（含 breaker 集成） |
| L249-260 | `build_composer_service` + fallback 文案 | → `Orchestrator._compose` |
| L262-275 | `composer.compose` + fallback 文案 | → `Orchestrator._compose` |
| L277-294 | memory_encode span + `MemoryTurn` 构造 | → `Orchestrator._fire_cold_path` |
| L296-310 | inner_loop tick `asyncio.ensure_future` | → `Orchestrator._fire_cold_path` |
| L348-405 | `_write_safety_event` 函数体 | **保留在 routes.py 或移到 `safety/audit.py`**，但通过 DI 注入给 Orchestrator，**不再由 routes 直接调用** |

**routes.py 保留**：`/auth/*`、`/chat/echo`、`/health/ready`、`/profile/*`、`get_current_user`、`_write_safety_event`（作为可注入的函数）。

`/api/chat` 体积：**~180 行 → ~25 行**。

---

## 6. 关键决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Safety breaker open 时的行为 | **fail-closed**（503）保持现状 | 与现有 `safety_agent_failed_closed` 行为一致；spec O-3 要求 safety 必须运行 |
| Composer breaker open 时 | **fail-soft**，返回 Soul-flavored msg | 与现状一致；用户感知优先 |
| Session 持久化 | **in-memory only**（本期） | SS07 §3.7 的 DB schema 推迟；本期解决"routes 太肥"而非 multi-device |
| trace_id 来源 | **新生成 UUID**，不再复用 message_id | 与 spec §4.2 对齐；为后续 OpenTelemetry 铺路 |
| Cold-path 错误处理 | fire-and-forget，仅 log | 现状即如此；不阻塞响应 |
| 是否在本期接入 `orchestrate_with_invariants` middleware | **是**，在 `Orchestrator.handle_turn` 内包裹 | 已有代码，直接用 |

---

## 7. 测试策略

| 类型 | 文件 | 覆盖 |
|------|------|------|
| unit | `tests/unit/test_circuit_breaker.py` | 三态转换、threshold、open_duration |
| unit | `tests/unit/test_session_manager.py` | get-or-create、turn_count++、并发安全 |
| unit | `tests/unit/test_orchestrator.py` | mock 所有 deps，验证 normal / PURPLE / safety-raise / composer-raise 四条路径 |
| contract | `tests/contract/test_hot_path_wiring.py`（已存在）| 更新断言：routes 调 orchestrator 而非直接调 safety/composer |
| integration | `tests/integration/test_purple_audit_trail.py`（已存在）| 不动，应当继续通过 |

**Done 标准**：
- `/api/chat` 行数 < 30
- routes.py 不再 `import` `safety_agent`、`build_composer_service`、`CompositionContext`、`MemoryTurn`
- 三条 breaker 在 unit test 中可验证 open/close 转换
- `test_purple_audit_trail` 仍绿
- `check_mvp` gates 仍绿

---

## 8. 显式不做的事（避免范围蔓延）

- ❌ Director / Critic / Wellbeing — 即使 spec 列了，本期一律不建空类
- ❌ Event Bus — 暂用直接调用 + asyncio.create_task
- ❌ Model Router failover — `infra/llm/ModelRouter` 不动
- ❌ Multi-device session 同步、reunion 检测
- ❌ Trace 持久化到 `traces` 表 — 仅 in-memory + structlog
- ❌ Soul-flavored fallback library — 沿用 routes 现有 `{"rin": "凛", "dorothy": "Dorothy"}` 简单文案
- ❌ Streaming response — 维持现有 non-streaming 模式（StreamingResponse 改造单开 PR）

---

## 9. 落地顺序（建议 PR 拆分）

1. **PR-1**: `models.py` + `circuit_breaker.py` + `session_manager.py` + unit tests（纯新增，无侵入）
2. **PR-2**: `orchestrator.py` + wiring + unit tests（纯新增）
3. **PR-3**: 改造 `routes.py`（删除内联管线，接 orchestrator）+ 更新 contract test
4. （后续）Director / Critic 各自单 PR
