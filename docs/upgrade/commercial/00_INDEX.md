# yuoyuo · 商用化升级执行方案（Execution Plan for Mimo）

> 产品名对外统一 **yuoyuo**（全小写）。`心屿 / Heart` 仅内部代号，任何用户可见文案禁止出现。

> ⚠️ **2026-07-06 状态订正**（§1 "现状真相"部分条目已过时，以此为准）：
> 短期窗口 40→**50 条**；最新迁移不再是 010，而是 **017**（`semantic_vector` 768→1024）；
> 语义召回已端到端实现并合并（#91–#94，门控于 `EMBEDDING_API_KEY`），记忆引擎已被本轮显著修改
> （非"基本不改"）。JWT 默认 **RS256**（以 `core/config.py` 校验为准）。
> 模块 06（匿名邮件 OTP）仍待实现。完整现状/操作见 [`../../EXECUTION_MANUAL.md`](../../EXECUTION_MANUAL.md)
> 与 [`../../PROJECT_STATUS.md`](../../PROJECT_STATUS.md) §0。
> 本目录是一份「工程设计级」执行方案，面向 AI Coding Agent（Mimo）逐模块落地。
> **不含最终代码实现**；每个模块文件末尾都有一段「⚙️ Mimo 执行 Prompt」可直接复制交付。

---

## 0. 阅读顺序

| 文件 | 模块 | 对应需求 | 构建顺序 |
|------|------|----------|----------|
| `00_INDEX.md`（本文） | 全局约定 · 现状真相 · 数据迁移 · 时序 · 验收 | — | 先读 |
| `01_auth_otp.md` | **模块 4** Email OTP 登录 + 真实用户系统 | Login 改造 | **① 地基** |
| `02_credits_afdian.md` | **模块 3** 积分系统 + 爱发电兑换 | 计费 | ② 依赖① |
| `03_profile_settings.md` | **模块 2** Profile + Settings + 18+ + 注销 | 账号 | ③ 依赖①② |
| `04_chat_voice.md` | **模块 1** Chat 文本/语音 + 持久化 + 计费接入 | 核心 | ④ 依赖①②③ |
| `05_legal_tos_privacy.md` | **模块 5** 用户协议 + 隐私政策（全文） | 合规 | ⑤ 可并行 |

> **构建顺序不可颠倒**：模块 4（真实身份 + `users` 表）是其余所有模块的地基。当前系统没有 `users` 表、没有 token，一切用户数据都无处挂靠。

---

## 1. 现状真相（Grounded Baseline — 落地前必须知道的差距）

以下均为逐文件核实，**不是推断**。Mimo 落地时以此为准，勿信任何"已实现"的口头描述。

### 1.1 后端（`backend/heart/`）
- **没有 `users` 表**。全库迁移（`migrations/versions/001–010`）里只有记忆/情绪/关系/会话/安全表。用户身份完全靠调用方自报。
- **登录是桩**：`POST /api/auth/login {user_id, email?}` → 直接签发 JWT。**无邮箱验证、无 OTP、无密码**。`email` 仅写进 token claim。
- **JWT 默认 HS256**（`config.py` `jwt_algorithm="HS256"`），非 AGENTS.md 所称 RS256；30 天有效期；**无服务端 session 存储、无吊销、无 refresh 轮换**。
- **已有聊天记录表 `chat_messages`**。聊天消息会持久化到服务端；`GET /api/chat/history` 从表里分页读取。WS 主聊天链路在进入编排层前，会注入**最近 40 条同角色对话**到 `TurnRequest.history`，用于短期上下文连续性；长期记忆仍由 L1/L2/L3/L4 负责。
- **TTS 是进程级全局开关**：是否出语音只取决于 `MIMO_API_KEY`/`MINIMAX_API_KEY` 是否配置。**没有 per-user / per-character 的 TTS 开关**。默认 provider = MiMo（`voice_provider="mimo"`）。
- **没有任何 credits / transactions / subscription / redemption / payment 表或路由**。`config.py` 里只有未被引用的 Stripe 占位符。
- **角色是 YAML soul spec**（`soul_specs/{rin,dorothy}/v1.0.0.yaml`），非 DB 行。soul spec 里**没有 TTS 设置**。
- **WS `/api/chat/ws`** 用 query 参数 `?token=` 验证 JWT，但 `user_id` 取自消息体、**未与 token 交叉校验**（安全缺陷，本次修）。
- 限流是 slowapi 按 IP：login `10/min`、chat `30/min`、voice `20/min`、state `60/min`。WS 无限流。
- `get_current_user` 有两份实现：`routes.py`（抛 403）vs `core/auth.py`（抛 401），不一致，本次统一。

### 1.2 前端（`web/src/`）
- **前端没有 token**：`appStore.isAuthenticated` 只是持久化的 boolean；`LoginPage`/`RedeemPage` 是 `setTimeout` mock，**不发任何请求**；WS 不带任何凭证。
- **没有 REST 客户端**：全代码仅一条同源 WebSocket（`/api/chat/ws`），dev proxy → `localhost:8000`。需要从零建 `services/api.ts`。
- **两套互不相通的 Chat**：路由 `/chat`（`components/ConversationChatPage.tsx`）是 **mock**——用 `conversationStore` + `setTimeout` 假回复 + 装饰性 waveform，**不接 WS、不放真实音频**；真实 WS/音频管线（`useWebSocket` + `chatStore` + `MessageList` + `VoiceMessageBubble` + `audioPlayer`）只挂在**未被路由**的 legacy `pages/ChatPage.tsx`。**把真实管线接进路由 UI 是模块 1 的核心工作**。
- **会员/积分 UI 全是硬编码假字符串**：设置页"会员 · 至 2026-12-31"、后台"积分消耗额度将增加"都无状态支撑。
- **角色 id 不一致**：app 用 `'rin' | 'taolesi'`，legacy `CharacterSelector` 用 `'dorothy'`，后端 soul spec 是 `rin` + `dorothy`。**本次统一为 `rin` + `dorothy`**（见 §3.4）。
- **per-character 语音开关 UI 已存在**：`appStore.voiceChatEnabled: Record<CharacterId, boolean>`（持久化），在 `CharacterBackstagePage`。目前只存本地、后端不认。模块 1 让它真正生效并落库。
- 已有丰富 UI 基元（可直接复用，勿重造）：`OTPInput` `Avatar` `SegmentedControl` `Slider` `TabBar` `BottomSheet` `Switch` `Dialog` `Toast` `Button` `Input` `ChatBubble` `BreathingDots` `MuteTimePicker` `NavigationBar` + 状态组件（Empty/Error/Offline/Loading/Skeleton）。
- 设计 token 已就绪：`web/src/styles/tokens.css`（`@theme`）+ `web/src/index.css`（含 `[data-theme="dark"]`）。所有新 UI **必须复用这些 token**，禁止硬编码颜色。

### 1.3 结论
本次升级 ≈ 在成熟的「情绪/记忆引擎」之上，**从零搭建商用外壳**：真实身份、计费、账号管理、聊天持久化、合规。引擎（SS01–08）基本不改，只在 orchestrator/WS 边界接入计费与开关。

---

## 2. 全局工程约定（所有模块通用，Mimo 必须遵守）

### 2.1 技术栈与文件落点
- 后端：Python 3.11 / FastAPI / SQLAlchemy 2.0 async / Alembic / PostgreSQL(pgvector) / Redis 7。所有 py 命令在 `backend/` 下跑。
- 前端：React 19 / Vite / Tailwind v4 / zustand / react-router v7。同源 `/api`，dev proxy → `:8000`。
- 新增后端路由文件命名 `backend/heart/api/routes_<domain>.py`，在 `main.py` 的 include 区注册。
- 新增迁移 `backend/migrations/versions/0NN_<slug>.py`，`down_revision` 串到当前最新（见 §4）。用 `alembic upgrade heads`（可能多头）。
- 新增前端页面 `web/src/pages/`，路由在 `web/src/App.tsx` 注册且套 `AuthGuard`。
- 新增前端 store `web/src/stores/`，跨会话需持久化的用 zustand persist（参考现有 `appStore` key `'yuoyuo-app'`）。

### 2.2 命名与文案
- 用户可见文案里**产品名恒为 `yuoyuo`**；禁止 `心屿 / Heart / YuoYuo / YUOYUO`。
- 角色 canonical id：`rin`（神无月凛）、`dorothy`（桃乐丝）。**废弃 `taolesi`**——前端做一次性映射迁移（§3.4）。
- 金额单位：积分叫 **credits（积分）**，整数，最小粒度 1。人民币用 `¥`。

### 2.3 安全与合规红线（贯穿所有模块）
- **禁止硬删用户数据**（AGENTS.md）：注销/清理一律逻辑删除 + 定时清除，见模块 2。
- **18+ 硬门槛**：未满 18 周岁禁止使用（模块 2 强制校验）。
- JWT 迁移为 **RS256**（`.env` 已备 `jwt_private_key/jwt_public_key` 位）；access token 短时效（30min）+ refresh token（30d，可吊销）。
- 所有写操作幂等（幂等键），所有扣费走 append-only ledger，余额可由 ledger 重算。
- WS 鉴权：`user_id` 一律取自 token（`sub`），**不再信任消息体**。
- 密钥/`.env` 永不入库。

### 2.4 Definition of Done（每个模块 PR 合并前都要过）
1. `bash scripts/ci.sh`（lint + unit + schema）全绿；新代码不引入新的 lint/type 债（Tier A/B 立即修）。
2. 新增/改动路由有单元测试（mock LLM/TTS/邮件），关键流程有 integration 测试。
3. `alembic upgrade heads` 干净，且写反向 `downgrade`。
4. 前端 `npm run build` 通过；新 UI 在 light + dark 双主题都验收（token 生效）。
5. 涉及付费/身份/删除的路径有速率限制与幂等键。
6. 每模块一条独立分支 `feat/<topic>` + 一个 PR，base=main，7 天内可合。

### 2.5 环境变量（本次新增，写入 `.env.example`，勿写真值）
```
# --- Auth / OTP ---
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY=            # PEM，RS256 私钥
JWT_PUBLIC_KEY=             # PEM，RS256 公钥
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
OTP_TTL_SECONDS=300         # 验证码 5 分钟
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_PER_HOUR=5          # 每邮箱每小时最多请求
OTP_MAX_ATTEMPTS=5          # 每码最多试错

# --- Email provider (transactional SMTP) ---
EMAIL_PROVIDER=smtp
SMTP_HOST=
SMTP_PORT=465
SMTP_USERNAME=
SMTP_PASSWORD=
EMAIL_FROM="yuoyuo <no-reply@yuoyuo.app>"

# --- Credits / Afdian ---
SIGNUP_GRANT_CREDITS=100
CREDITS_PER_TEXT_TURN=1
CREDITS_PER_VOICE_TURN=5
AFDIAN_USER_ID=
AFDIAN_WEBHOOK_TOKEN=       # 用于校验 webhook sign
AFDIAN_SPONSOR_URL=https://afdian.com/a/yuoyuo

# --- Storage (avatar / voice audio) ---
# 复用现有 S3/MinIO 配置段
```

---

## 3. 跨模块共享数据模型总览

新增表（各模块文件有完整字段定义；此处给全局关系图与迁移边界）：

```
users ─┬─< email_otp_codes           (模块4)
       ├─< auth_sessions             (模块4，refresh token)
       ├─< credit_transactions       (模块3，append-only 台账)
       ├─< redemption_codes.redeemed_by (模块3)
       ├─< user_character_settings   (模块1，per-character voice 开关落库)
       ├─< chat_messages             (模块1，聊天持久化)
       └─< account_deletion_requests (模块2，注销宽限期)

redemption_codes  (模块3，独立码池，可无 user 归属直到兑换)
afdian_orders     (模块3，webhook 对账，幂等)
```

- `users.credits_balance BIGINT` 为**缓存余额**，与 `credit_transactions` 在同一事务内原子更新；余额恒 = ledger 之和（校验任务）。加 `CHECK (credits_balance >= 0)`。
- 所有面向用户的表都带 `user_id UUID`（FK → `users.id`）。已有的记忆/情绪表用 `user_id` 但**无 FK 到 users**（历史），本次**不强加 FK**（避免动到分区表），仅在应用层保证一致。

### 3.4 角色 id 统一迁移（一次性）
- 前端 `appStore` persist key `'yuoyuo-app'` 里旧值可能是 `'taolesi'`。加 zustand `migrate`：`taolesi → dorothy`。
- `CharacterId` 类型统一为 `'rin' | 'dorothy'`。`data/uiContent.ts`、`CharacterSelector`、`conversationStore` 全部对齐。
- 后端 canonical id 已是 `rin`/`dorothy`，无需迁移。

---

## 4. 数据库迁移清单（本次新增，按依赖顺序）

当前最新迁移是 `010_memory_regex_shadow.py`。新增：

| 迁移 | 表 | 模块 |
|------|----|----|
| `011_users_and_auth.py` | `users`, `email_otp_codes`, `auth_sessions` | 4 |
| `012_credits_and_redemption.py` | `credit_transactions`, `redemption_codes`, `afdian_orders` | 3 |
| `013_account_and_char_settings.py` | `account_deletion_requests`, `user_character_settings` | 2/1 |
| `014_chat_messages.py` | `chat_messages`（按 `user_id` HASH 分区，沿用既有风格） | 1 |

> 每个迁移 `down_revision` 串到前一个；`011.down_revision='010_memory_regex_shadow'`（用实际 revision id，落地时 `alembic history` 确认）。

---

## 5. 端到端时序（商用后一次完整会话）

```
首次打开 → Splash → Onboarding(3屏) → Login(邮箱→OTP) ─┐
                                                        ↓
                          [无 users 行则创建 + 赠 100 credits + 记录 age_gate 待完成]
                                                        ↓
        首登强制 Profile 补全（昵称/性别/生日）→ 18+ 校验 ── <18 → 硬拦截页（禁止使用）
                                                        ↓ ≥18
                                    Home → 选角色 → Chat
                                                        ↓
        发消息：前端带 access token(WS ?token=) → 后端从 token 取 user_id
                                                        ↓
        turn 开始：预检 credits 余额 → 不足则 error 事件 → 前端引导去 Redeem
                                                        ↓ 足够
        orchestrator 出文本流；若该角色 voice_enabled 且余额够 → StreamSession 出 TTS
                                                        ↓
        turn 成功：原子扣 credits（text=1 / voice=5）+ 写 credit_transactions + 落 chat_messages
                                                        ↓
        余额不足引导 → Redeem 输码 → credits 增加 → 回 Chat 继续
```

---

## 6. 交付与治理（遵循 `.claude/CLAUDE.md`）
- 一模块一分支一 PR，base=main，7 天内可合；不堆"事实主干"。
- CI 配置变更与业务变更**分开 PR**。
- 合并即删分支（本地 + 远端）。
- 本方案 5 个模块 → 至少 5 个独立可回滚 PR；模块 1（Chat）体量大，可再拆「持久化」「计费接入」「前端接真管线」三个子 PR。
