# 模块 2 · Profile 编辑 + Settings 系统 + 18+ 校验 + 注销（构建顺序 ③）

> 依赖：模块 4（`users` 表）、模块 3（credits 展示）。
> 现状：`SettingsPage` 全是硬编码假数据（名字"晨曦"、"会员 · 至 2026-12-31"）；"清除聊天缓存/导出/注销"均为 no-op；无 Profile 编辑页；无 18+ 校验。
> 红线：**无硬删用户数据**（逻辑删除）；**18+ 硬门槛**。

---

## 1. Profile 编辑页

### 1.1 页面 `web/src/pages/ProfileEditPage.tsx`（路由 `/settings/profile`）
可编辑字段：
| 字段 | 控件 | 校验 |
|------|------|------|
| 头像 avatar | `Avatar` + 上传（点击→文件选择）| ≤5MB，jpg/png/webp；前端压缩到 ≤512px |
| 昵称 display_name | `Input` | 1–20 字符，去首尾空白，禁纯空白 |
| 性别 gender | `SegmentedControl` | 枚举 `female/male/nonbinary/undisclosed`（女/男/其他/不透露）|
| 年龄/生日 birthdate | 日期选择（`BottomSheet` + 滚轮，复用 `MuteTimePicker` 的 wheel 模式改造）| 必填；用于 18+ |

- 顶部入口：`SettingsPage` 的 Profile 卡整块可点 → `/settings/profile`（现有 chevron 生效）。
- 保存：`PATCH /api/profile`，成功更新 `authStore.user` + `Toast`。

### 1.2 头像上传
- `POST /api/profile/avatar`（multipart）→ 存 S3/MinIO（复用现有 S3 配置段）→ 返回 `{avatar_url}` → 前端写回。
- 后端校验 content-type + 大小；生成 `avatars/{user_id}/{uuid}.webp`；覆盖旧文件（旧 url 记 `account_deletion_requests`? 否——仅替换）。

## 2. 18+ 年龄限制（强门槛）

### 2.1 规则
- **首次登录后强制补全 Profile**（`needs_profile=true` 来自模块4 verify）→ 必须填 `birthdate`。
- 计算周岁：`age = floor((today - birthdate)/365.2425)`。
- **age ≥ 18** → 写 `users.age_verified_at=now()`，放行进 `/home`。
- **age < 18** → **硬拦截页**（`web/src/pages/AgeGatePage.tsx`，路由 `/age-gate`），禁止进入任何功能；`AuthGuard` 检查 `user.age_verified` 为否且已填未成年生日 → 强制停在 `/age-gate`。后端所有业务路由（chat/voice/credits 消费）对 `age_verified_at IS NULL` 的用户返回 403 `age_verification_required`。
- 后端 `PATCH /api/profile` 收到 birthdate 时服务端**再算一次**周岁，未满 18 → 拒绝写 `age_verified_at` 并返回 `{age_verified:false}`；≥18 → 写入。**不信任前端**。

### 2.2 强提示文案（必须生成，直接用）
- 门槛确认（Profile 补全页顶部）：
  > 「yuoyuo 是面向成年人的情感陪伴产品。继续即表示你确认已年满 18 周岁。我们会根据你填写的出生日期进行校验。」
- 拦截页 `AgeGatePage` 正文：
  > 「很抱歉，yuoyuo 仅供年满 18 周岁的用户使用。」
  > 「根据你提供的出生日期，你目前未满 18 周岁，暂时无法使用本产品。感谢你的理解，期待未来与你相遇。」
  > 底部单按钮：「退出登录」（清 session 回 `/login`）。

## 3. Settings 系统（真实化 `SettingsPage`）

保留视觉稿 §2.5 的分组结构，把假数据接真接口：

| 分组 | 行 | 行为 |
|------|----|----|
| Profile 卡 | 头像+昵称+**真实积分余额**（替换会员假字符串）| 点击 → `/settings/profile` |
| 我的会员 | 兑换会员 | → `/redeem`（模块3）|
| | 积分余额 / 明细 | → `/credits/transactions`（模块3）|
| 外观 | 主题（`SegmentedControl` 浅/深/自动）| 已可用，保留 |
| | 字体大小（`Slider`）| 已可用，保留 |
| 通知 | 推送提醒 `Switch` | MVP 存本地 `appStore`（推送未接则灰置+"即将上线"）|
| | 静音时段 | `BottomSheet` + `MuteTimePicker`（已可用）|
| 隐私与数据 | **清除聊天缓存** | §4.1，二次确认 |
| | 导出我的数据 | §4.3 |
| | **注销账号** | §4.2，强警告，soft rose 非纯红 |
| 关于 | 版本 / 用户协议 / 隐私政策 / 联系我们 | 协议隐私 → `/legal/*`（模块5）|

## 4. 隐私与数据操作

### 4.1 清除聊天缓存
- 语义澄清：本产品**没有逐条 transcript 表**（历史由记忆重建）。模块1 引入 `chat_messages` 后，"清除聊天缓存"= 清空该用户的**可见聊天消息 + L1 Redis 工作记忆 + 前端本地会话**，**默认不删** L2/L3/L4 长期记忆（那属于"注销账号"或"遗忘特定记忆"）。
- API：`POST /api/account/clear-conversations { character_id? }` → 逻辑清空 `chat_messages`（打 `cleared_at` 或删该用户行——聊天消息非"用户核心数据"，可硬删本表，但为审计建议软标记）+ 清 Redis L1 + 返回 ok。
- **二次确认 + 数据说明文案**（`Dialog`，必须用）：
  > 标题：「清除聊天缓存」
  > 正文：「这会清空当前设备与云端的聊天对话记录。yuoyuo 对你的长期了解（TA 记住的关于你的事）不会被删除——如需彻底删除，请使用『注销账号』。此操作不可撤销。」
  > 按钮：主「确认清除」/ 次「取消」

### 4.2 注销账号（逻辑删除 + 宽限期）
- **无硬删**：`POST /api/account/delete` →
  1. `users.status='deleted'`, `deleted_at=now()`；`email` 匿名化为 `deleted+{uuid}@invalid`（释放原邮箱可重注册）。
  2. 吊销全部 `auth_sessions`（revoked_at=now）。
  3. 写 `account_deletion_requests(user_id, requested_at, purge_after=now()+30d, status='pending')`。
  4. 立即登出前端。
- **定时清除任务**（`backend/heart/workers/`）：`purge_after < now()` 且 `status='pending'` → 物理/匿名化清除该用户的记忆(L2/L3/L4)、情绪/关系状态、chat_messages、头像文件，置 `status='purged'`。30 天内可申诉恢复（人工）。
- **强警告文案**（`Dialog`，两段式确认，必须用）：
  > 第一屏 标题：「注销账号」
  > 正文：「注销后，yuoyuo 会在 30 天后**永久删除**你的全部数据：聊天记录、TA 对你的所有记忆、情绪与关系进展、你的积分余额。此后无法恢复。」
  > 「你当前还有 {balance} 积分，注销后将一并清空且不予退还。」
  > 按钮：主（soft rose）「我了解，继续注销」/ 次「再想想」
  > 第二屏（确认输入）：要求输入邮箱或勾选「我确认永久删除我的账号与数据」→ 「确认注销」。

### 4.3 导出我的数据（GDPR-style）
- `POST /api/account/export` → 异步生成 JSON（profile + credits ledger + chat_messages + 记忆摘要）→ 邮件下载链接或 `GET /api/account/export/{id}` 取。MVP 可同步返回 JSON 附件。

## 5. 数据模型（迁移 `013_account_and_char_settings.py`）
`account_deletion_requests`：
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | |
| user_id | UUID FK→users | INDEX |
| requested_at | TIMESTAMPTZ | |
| purge_after | TIMESTAMPTZ | now()+30d |
| status | TEXT | `pending/purged/cancelled` |
| completed_at | TIMESTAMPTZ | 可空 |

（`user_character_settings` 表定义在模块1 §3，与本迁移合并落库。）

Profile 相关字段（`display_name/avatar_url/gender/birthdate/age_verified_at`）已在模块4 `users` 表建好，本模块只填充。

## 6. API 汇总（`backend/heart/api/routes_profile.py` + `routes_account.py`）
| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/profile` | 返回 user |
| PATCH | `/api/profile` | 改 name/gender/birthdate（服务端重算 18+）|
| POST | `/api/profile/avatar` | multipart 上传 → avatar_url |
| POST | `/api/account/clear-conversations` | 清聊天缓存 |
| POST | `/api/account/delete` | 逻辑注销 + 排期清除 |
| POST | `/api/account/export` | 导出数据 |
- 全部 Bearer；`age_verification_required` 门禁对未验证用户返回 403（导出/删除/profile 除外，允许未成年注销与查看）。

## 7. 前端改造要点
- 新增页面：`ProfileEditPage.tsx`、`AgeGatePage.tsx`、`TransactionsPage.tsx`（模块3）。路由注册 + `AuthGuard`。
- `AuthGuard`：登录后若 `!user.age_verified && user.birthdate 已填且未成年` → 强制 `/age-gate`；若 `needs_profile`（无 birthdate）→ `/onboarding/profile`。
- `SettingsPage`：Profile 卡与会员区接 `authStore.user` + `creditsStore.balance`；隐私区三项接真实 API + 上述文案 `Dialog`。
- 复用基元：`Avatar` `SegmentedControl` `Slider` `Switch` `BottomSheet` `Dialog` `Toast` `Button`。

## 8. 验收
- 首登无生日 → 强制补全；填 <18 → 服务端拒验证 → 拦截页，chat/voice 返回 403。
- 填 ≥18 → `age_verified_at` 落库 → 放行。
- 改昵称/性别/头像持久化，重登仍在。
- 清除聊天缓存：`chat_messages` 清空 + L1 清，长期记忆仍在。
- 注销：两段确认 → status=deleted + 邮箱匿名 + sessions 吊销 + 排期行写入；30 天任务清数据；原邮箱可重新注册。

---

## ⚙️ Mimo 执行 Prompt（复制交付）

```
你在 Heart 仓库（对外名 yuoyuo）实现「模块2：Profile + Settings + 18+ + 注销」。分支 feat/profile-settings，base=main。依赖模块4(users)、模块3(credits)。严格按 docs/upgrade/commercial/03_profile_settings.md，红线：无硬删用户数据（逻辑删除+30天排期清除）、18+ 硬门槛服务端校验。

后端：
1. 迁移 013_account_and_char_settings.py：建 account_deletion_requests（+ 模块1 的 user_character_settings，可合并）。字段按 §5 / 模块1 §3。写 downgrade。
2. routes_profile.py：GET/PATCH /api/profile（PATCH 收 birthdate 时服务端重算周岁，<18 拒写 age_verified_at 返回 age_verified:false，>=18 写入，不信前端）、POST /api/profile/avatar（multipart→S3/MinIO，校验类型≤5MB，路径 avatars/{uid}/{uuid}.webp）。
3. routes_account.py：POST /api/account/clear-conversations（清 chat_messages+L1 Redis，保留长期记忆）、POST /api/account/delete（users.status=deleted+deleted_at+email 匿名化+吊销所有 auth_sessions+写 account_deletion_requests purge_after=+30d）、POST /api/account/export（导出 JSON）。
4. workers 定时清除任务：purge_after<now 且 pending → 清该用户记忆/情绪/关系/chat_messages/头像 → status=purged。
5. 门禁：age_verified_at IS NULL 的用户访问 chat/voice/credits 消费类路由返回 403 age_verification_required（profile/export/delete 除外）。

前端：
6. 新页 ProfileEditPage(/settings/profile)：头像上传(前端压缩≤512px)、昵称 Input(1-20)、性别 SegmentedControl、生日 BottomSheet 滚轮。保存 PATCH /api/profile 更新 authStore.user。
7. 新页 AgeGatePage(/age-gate)：文案严格用 §2.2；单按钮退出登录。AuthGuard 按 §7 加 needs_profile / age-gate 分流。
8. SettingsPage 真实化：Profile 卡接 authStore.user + 真实积分余额（删假会员串）；隐私与数据三项接真实 API，二次确认 Dialog 文案严格用 §4.1/§4.2（注销两段式确认，soft rose 非纯红，展示将清空的积分）。
9. services/api.ts 增 getProfile/updateProfile/uploadAvatar/clearConversations/deleteAccount/exportData。

约束：复用现有 UI 基元与 tokens.css，light+dark 双验收。测试覆盖 §8（服务端 18+ 拒绝、门禁 403、逻辑删除+排期、清缓存不删长期记忆）。ci.sh 全绿、alembic upgrade heads 干净、npm run build 通过，开 PR。所有用户可见文案不得出现 心屿/Heart。
```
