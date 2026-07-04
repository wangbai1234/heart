# 模块 4 · Email OTP 登录 + 真实用户系统（构建顺序 ①，地基）

> 依赖：无。**其余所有模块依赖本模块产出的 `users` 表与真实 token。**
> 现状：登录是桩（`routes.py:login` 直接签 JWT）；前端 `LoginPage` 是 `setTimeout` mock；无 `users` 表；无 refresh；WS 不带凭证。

---

## 1. 目标
把「自报 user_id 换 token」替换为「邮箱 → 6 位验证码 → 登录 → 会话」，并首次建立真实用户实体、access/refresh 双 token、可吊销会话，为计费与账号管理提供身份地基。

## 2. 登录流程（文字版 flow diagram）

```
[前端] 输入 email
   │  POST /api/auth/otp/request { email }
   ▼
[后端] 校验 email 格式 → 限流(每邮箱 5/时 + 每IP 20/时) → 冷却(同邮箱 60s)
   │  生成 6 位数字码 → 存 code_hash(+盐) + expires_at(now+5min) + attempts=0
   │  发邮件（SMTP，模板见 §6）
   ▼  返回 { sent: true, cooldown: 60, expires_in: 300 }  (即便邮箱不存在也返回同结构，防枚举)
[前端] 进入验证码输入态（OTPInput length=6），60s 倒计时后可重发
   │  POST /api/auth/otp/verify { email, code }
   ▼
[后端] 取该邮箱最新未消费码 → 未过期 & attempts<5 & 常数时间比对
   │  ├─ 失败：attempts+1；attempts≥5 或过期 → 作废并要求重发
   │  └─ 成功：标记 consumed_at
   │  users upsert(email)：无则创建（credits_balance = SIGNUP_GRANT_CREDITS，age_verified=false）
   │  写 credit_transactions(type=grant) —— 仅新用户，幂等键 = "signup_grant:{user_id}"
   │  签 access JWT(RS256, sub=user_id, 30min) + refresh token(随机 256bit, 存 auth_sessions 哈希, 30d)
   ▼  返回 { access_token, refresh_token, expires_in, user: {...}, needs_profile: bool }
[前端] 存 token（access 内存+localStorage，refresh 仅 localStorage）
   │  needs_profile=true（新用户/未过 18+）→ 跳 /onboarding/profile（模块2）
   └─ 否则 → /home
```

Refresh：`POST /api/auth/refresh { refresh_token }` → 校验 `auth_sessions` 未吊销未过期 → 轮换（旧 refresh 置 revoked，发新 refresh）+ 新 access。
Logout：`POST /api/auth/logout` → 吊销当前 refresh（`auth_sessions.revoked_at=now`）。

## 3. 数据模型（迁移 `011_users_and_auth.py`）

### 3.1 `users`
| 列 | 类型 | 约束/说明 |
|----|------|-----------|
| id | UUID | PK, default gen_random_uuid() |
| email | CITEXT | UNIQUE NOT NULL（大小写不敏感）|
| display_name | TEXT | 可空，首登补全 |
| avatar_url | TEXT | 可空（模块2 上传后写入）|
| gender | TEXT | 可空，枚举 `female/male/nonbinary/undisclosed` |
| birthdate | DATE | 可空；18+ 校验依据（模块2 写入）|
| age_verified_at | TIMESTAMPTZ | 可空；通过 18+ 后写入 |
| credits_balance | BIGINT | NOT NULL default 0, `CHECK (credits_balance >= 0)` |
| status | TEXT | NOT NULL default `active`，枚举 `active/deleted` |
| created_at | TIMESTAMPTZ | default now() |
| last_login_at | TIMESTAMPTZ | 每次 verify 成功更新 |
| deleted_at | TIMESTAMPTZ | 逻辑删除时间（模块2）|

索引：`UNIQUE(email)`；`INDEX(status)`。

### 3.2 `email_otp_codes`
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID | PK |
| email | CITEXT | NOT NULL, INDEX |
| code_hash | TEXT | NOT NULL（`sha256(code + OTP_PEPPER)`，不存明文）|
| purpose | TEXT | default `login` |
| expires_at | TIMESTAMPTZ | NOT NULL |
| consumed_at | TIMESTAMPTZ | 可空 |
| attempts | SMALLINT | default 0 |
| request_ip | INET | 记录，风控用 |
| created_at | TIMESTAMPTZ | default now() |

索引：`INDEX(email, created_at DESC)`。清理任务：定时删 `expires_at < now() - 1 day`。

### 3.3 `auth_sessions`（refresh token）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID | PK（= refresh token 的 jti）|
| user_id | UUID | FK→users.id, INDEX |
| refresh_token_hash | TEXT | NOT NULL（sha256）|
| issued_at | TIMESTAMPTZ | default now() |
| expires_at | TIMESTAMPTZ | NOT NULL |
| revoked_at | TIMESTAMPTZ | 可空（logout/轮换/注销）|
| user_agent | TEXT | 可空 |
| ip | INET | 可空 |

索引：`INDEX(user_id)`；`INDEX(refresh_token_hash)`。

## 4. API 设计（`backend/heart/api/routes_auth.py`，prefix `/api/auth`）

| Method | Path | 限流 | Body | 返回 |
|--------|------|------|------|------|
| POST | `/otp/request` | 5/min/IP + 应用层每邮箱 5/时、60s 冷却 | `{email}` | `{sent, cooldown, expires_in}` |
| POST | `/otp/verify` | 10/min/IP | `{email, code}` | `{access_token, refresh_token, expires_in, user, needs_profile}` |
| POST | `/refresh` | 30/min/IP | `{refresh_token}` | `{access_token, refresh_token, expires_in}` |
| POST | `/logout` | 30/min/IP | `{refresh_token}` (或 Authorization) | `{ok:true}` |
| GET | `/me` | 60/min | — (Bearer) | `{user}` |

- 旧 `POST /api/auth/login`（stub）：**仅 `HEART_DEV_MODE=true` 时保留**用于测试；生产路由不注册。`routes.py` 里本地那份抛 403 的 `get_current_user` 删除，全量改用 `core/auth.py` 的 401 版本。
- `core/auth.py`：`jwt_algorithm` 默认改 `RS256`；`create_access_token` 加短时效；新增 `create_refresh_token` / `verify_refresh_token` / `rotate_refresh_token`（读写 `auth_sessions`）。access token claim：`{sub, email, exp, iat, typ:"access"}`。
- **WS 鉴权硬化**（`routes_chat_ws.py`）：`_parse_user_id` 删除；`user_id` 一律取 `verify_token(token).sub`，忽略消息体里的 `user_id`。

## 5. 防刷机制（Anti-abuse）
1. **双维度限流**：每邮箱 `OTP_MAX_PER_HOUR=5`（Redis 计数 key `otp:req:{email}` TTL 3600）+ 每 IP slowapi `5/min`。
2. **冷却**：同邮箱两次请求间隔 ≥ `OTP_RESEND_COOLDOWN_SECONDS`（Redis key `otp:cooldown:{email}`）。
3. **试错锁**：`attempts ≥ OTP_MAX_ATTEMPTS` 作废该码，必须重发。
4. **单次有效**：verify 成功即 `consumed_at`，同码不可复用。
5. **常数时间比对** + 只存 `code_hash`（+ pepper），日志不打码。
6. **防枚举**：request 无论邮箱是否存在都返回相同结构与耗时。
7. **注册赠分幂等**：signup grant 幂等键 `signup_grant:{user_id}`，避免并发重复赠分。

## 6. 邮件（`backend/heart/infra/email/`）
- 抽象 `EmailSender`（Protocol）+ `SMTPEmailSender`（`aiosmtplib`）。`EMAIL_PROVIDER=smtp`。
- 模板（纯文本 + 简 HTML，中文）：
  - 主题：`【yuoyuo】你的登录验证码 {code}`
  - 正文：`你好，你的 yuoyuo 登录验证码是 {code}，5 分钟内有效。如果不是你本人操作，请忽略本邮件。`
- 发送失败：request 接口仍返回 `sent:true`（不泄露），但内部记 error 日志 + Prometheus 计数 `otp_email_send_failed_total`。

## 7. 前端改造

### 7.1 新增 REST 客户端 `web/src/services/api.ts`
- `fetch` 封装：`baseURL='/api'`；请求自动带 `Authorization: Bearer <access>`。
- **401 自动 refresh**：拦截 401 → 用 refresh 换新 access → 重放原请求；refresh 也失败 → 清 token + 跳 `/login`。
- 导出：`requestOtp(email)`、`verifyOtp(email, code)`、`refresh()`、`logout()`、`getMe()`。

### 7.2 `web/src/stores/authStore.ts`（新增，persist key `'yuoyuo-auth'`）
```ts
accessToken: string | null
refreshToken: string | null
user: { id, email, display_name, avatar_url, gender, birthdate, credits_balance, age_verified } | null
isAuthenticated: () => !!accessToken
setSession(tokens, user); clearSession(); setUser(patch)
```
- **迁移 `appStore`**：移除 `appStore.isAuthenticated`（boolean）；`AuthGuard` 改读 `authStore.isAuthenticated()`。`voiceChatEnabled` 等 UI 偏好留在 `appStore`。

### 7.3 `web/src/pages/LoginPage.tsx`（改造为两步）
- 第一步：邮箱输入（复用现有 `Input` + 校验正则）→ 「发送验证码」→ `requestOtp`。
- 第二步：**复用 `components/ui/OTPInput.tsx`**（`length=6, groupSize=3`）→ 自动提交 `verifyOtp`；60s 倒计时「重新发送」；「换邮箱」返回第一步。
- 成功：`setSession` → `needs_profile ? /onboarding/profile : /home`。
- 保留底部「我有兑换码 →」→ `/redeem`；法律链接接真实 `/legal/terms`、`/legal/privacy`（模块5）。
- 文案沿用视觉稿 §2.6，但**把"发送登录链接"改为"发送验证码"**、helper 改为「我们会向你的邮箱发送 6 位验证码，5 分钟内有效」。

### 7.4 WS 带 token
- `web/src/hooks/useWebSocket.ts`：`WS_URL` 追加 `?token=${authStore.accessToken}`；连接前若无 token 不连；收到 close code `1008` → 触发 refresh 后重连，仍失败跳登录。

## 8. 验收（DoD 增量）
- 真机：输入邮箱→收码→登录→落 `users` 行 + 赠 100 credits（`credit_transactions` 有 grant）。
- 错码 5 次锁定并要求重发；60s 内重发被拒。
- access 过期后自动 refresh 无感续期；logout 后 refresh 失效。
- WS 用过期 token 连 → 1008 → 前端自动续期重连。
- 单测：request 限流/冷却/防枚举、verify 成功/过期/错码锁定/幂等赠分、refresh 轮换、logout 吊销。

---

## ⚙️ Mimo 执行 Prompt（复制交付）

```
你在 Heart 仓库（产品对外名 yuoyuo，全小写）实现「模块4：Email OTP 登录 + 真实用户系统」。分支 feat/auth-otp，base=main。严格遵守 docs/upgrade/commercial/00_INDEX.md 的全局约定与现状真相，勿信任何"已实现"描述，以实际代码为准。

后端（backend/，Python3.11 FastAPI SQLAlchemy2.0 async Alembic）：
1. 新迁移 backend/migrations/versions/011_users_and_auth.py，down_revision 串到当前最新（先 alembic history 确认 revision id）。建表 users / email_otp_codes / auth_sessions，字段与约束严格按 01_auth_otp.md §3（users.credits_balance CHECK>=0、email CITEXT UNIQUE、逻辑删除列齐全）。写 downgrade。
2. backend/heart/infra/email/：EmailSender Protocol + SMTPEmailSender(aiosmtplib)，env 见 00_INDEX §2.5；中文验证码模板见 §6。
3. backend/heart/api/routes_auth.py（prefix /api/auth）：实现 /otp/request、/otp/verify、/refresh、/logout、/me，签名与限流严格按 §4；防刷严格按 §5（Redis 计数+冷却+试错锁+常数时间比对+只存 sha256(code+pepper)+防枚举+赠分幂等键）。在 main.py include 区注册。
4. core/auth.py：jwt_algorithm 默认 RS256；access 30min + refresh(存 auth_sessions 哈希, 30d, 可轮换可吊销)。删除 routes.py 里那份抛403的 get_current_user，统一用 core/auth.py 版本。旧 /api/auth/login 仅 HEART_DEV_MODE 保留。
5. routes_chat_ws.py：删除 _parse_user_id，user_id 一律取自 verify_token(token).sub，不信任消息体。
6. .env.example 增补 §2.5 的 Auth/Email 段（不写真值）。

前端（web/，React19 Vite Tailwindv4 zustand）：
7. web/src/services/api.ts：fetch 封装，自动带 Bearer，401 自动 refresh 重放，最终失败清 token 跳 /login。导出 requestOtp/verifyOtp/refresh/logout/getMe。
8. web/src/stores/authStore.ts（persist 'yuoyuo-auth'）按 §7.2；把 AuthGuard 从 appStore.isAuthenticated 迁到 authStore.isAuthenticated()。移除 appStore 的 isAuthenticated boolean。
9. web/src/pages/LoginPage.tsx 改两步：邮箱→验证码，复用 components/ui/OTPInput（length6 groupSize3）+ 60s 倒计时重发。文案改"发送验证码"。成功按 needs_profile 跳转。
10. web/src/hooks/useWebSocket.ts：WS_URL 带 ?token=，1008 时 refresh 重连。

约束：复用现有 UI 基元与 tokens.css/index.css，勿硬编码颜色；light+dark 双主题验收；不删记忆/情绪表；无硬删用户数据。测试：为 §4 每个端点写单测（mock 邮件与 Redis），覆盖 §8 场景。完成后 bash scripts/ci.sh 全绿、alembic upgrade heads 干净、npm run build 通过，然后开 PR。
```
