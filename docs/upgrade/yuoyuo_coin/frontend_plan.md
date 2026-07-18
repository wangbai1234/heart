# yuoyuo 商业化 — 前端设计（GPT 执行）

> 状态：规划 · 待落地
> 执行方：GPT
> 依赖：`00_INDEX.md`（货币模型 / 等级矩阵 / 定价 / 商城挡位）+ `backend_plan.md`（新端点契约）
> 上游现状：`web/src/services/api.ts`（含未用的 `getPricing()`）、`creditsStore`/`authStore`/`chatStore`/`toastStore`、`pages/CreateCharacterPage.tsx`
> 最后更新：2026-07-18

---

## 0. 全局约定

- 技术栈：React 19 / Vite / Tailwind v4 / zustand / react-router v7。PWA。同源 `/api`，dev proxy → `:8000`。
- **禁硬编码颜色**：一律用 `web/src/styles/tokens.css` 的 token；**light + dark 双主题验收**。
- 复用现有 ui 基元（`components/ui/`：`Button/Dialog/BottomSheet/Toast/OTPInput/Switch/Slider/SegmentedControl/Avatar/TabBar/Skeleton` 等），勿重造。
- 复用现有 store：`creditsStore`（余额）、`authStore`（`user`）、`toastStore`（全局提示）、`chatStore`（`insufficientCredits`）。
- 新页面放 `web/src/pages/`，路由在 `web/src/App.tsx` 注册并套 `AuthGuard`；跨会话持久化用 zustand persist。
- **文案产品名恒 `yuoyuo`**；货币显示恒「yuoyuo币」（本次由「积分」改名）。
- 所有金额从后端 `getPricing()` 拉取，**禁前端硬编码档位/价格**（后端 ÷100 已是显示币值）。

---

## F1 · 文案改造：积分 → yuoyuo币（可即刻起，纯前端）

把用户可见的「积分」统一改为「yuoyuo币」（配币图标）：
- `pages/SettingsPage.tsx`（余额 pill、「我的会员」区行文案）
- `pages/TransactionsPage.tsx`（余额卡 + `TYPE_LABELS`：consume_text/voice 等）
- `pages/RedeemPage.tsx`（标题/提示）
- `components/ConversationChatPage.tsx`（「积分不足」Dialog）
- `data/uiContent.ts`（静态文案）

**产出**：以上文件文案改动 + 币图标资源（可用现有 assets 或 inline SVG，走 token 色）。

---

## F2 · 会员页 `/membership`

- 新页 `pages/MembershipPage.tsx`：三档卡（免费 / 进阶 ¥39 / 沉浸 ¥79），每档列权益（模型/TTS/克隆/月度赠币，数据来自 `getPricing().membership_tiers`）。当前等级高亮（来自新 `getMembership()`）。
- **开通区**：展示**用户绑定码** + 「在爱发电备注填写此码」指引 + 对应 SKU 名称 + 「去爱发电开通 →」外链（`afdian_url`）。绑定码来自 `getMembership()`（后端由 user.id 派生）。
- `SettingsPage` 加**会员状态卡**（当前 tier + 到期日 + 「管理会员」→ `/membership`），替换现硬编码。
- 新 store `stores/membershipStore.ts`（不持久化，登录后拉）：`tier`、`expiresAt`、`entitlements`、`bindingCode`、`refresh()`。
- `services/api.ts` 新增 `getMembership()` → `{tier, expires_at, entitlements, monthly_grant, binding_code}`；扩展 `getPricing()` 类型含 `membership_tiers/models/actions/shop`。

**产出**：`MembershipPage.tsx`（新）、`membershipStore.ts`（新）、`api.ts`（改）、`App.tsx`（改路由）、`SettingsPage.tsx`（改）。

---

## F3 · yuoyuo币钱包 + 商城 `/wallet`

- 扩展或新建：把 `TransactionsPage`（`/credits/transactions`）升级为钱包，或新建 `pages/WalletPage.tsx`（`/wallet`）——余额卡（复用现渐变卡）+ **商城 4 挡**（¥6/¥18/¥48/¥128，来自 `getPricing().shop`，展示到账+赠送）+ 明细入口。
- 每挡「去爱发电 →」：同 F2 展示绑定码 + SKU + 外链。
- 保留 `RedeemPage`（兑换码）作为次要入口（客服补偿/赠礼）。

**产出**：`WalletPage.tsx`（新，或 `TransactionsPage` 升级）、`api.ts`（`getPricing` 类型）、`App.tsx`/`SettingsPage.tsx`（入口）。

---

## F4 · 聊天模型选择器 + 按币计费展示（依赖 B3/B4）

- `components/ConversationChatPage.tsx` 顶栏加**模型选择器**（`SegmentedControl` 或下拉 `BottomSheet`）：DeepSeek / Grok / Claude，每项标注每次币价（来自 `getPricing().models`）。
- **按 tier 置灰**：`membershipStore.entitlements.models` 不含的模型 → 置灰 + 锁图标 + 点击提示「升级会员解锁」→ 跳 `/membership`。DeepSeek 永远可选。
- 选中的 model 存 per-character（`appStore` 或 `chatStore`，缺省 deepseek）。
- `hooks/useWebSocket.ts` `sendMessage`：payload 加 `model` 字段。
- 处理新 WS 事件：
  - `model_forbidden` → Dialog「该模型需会员」→ `/membership`。
  - `turn_end.served_model` → 消息旁展示**模型徽标**；若 `degraded_to` 存在 → 轻 Toast「已切换到 {model}」（**不显技术错误**）。
  - `insufficient_credits` → 复用现「币不足」Dialog（改文案）→ `/wallet`。
- `turn_end.balance` → `creditsStore.setBalance`（现已有，静默同步）。

**产出**：`ConversationChatPage.tsx`/`ChatInput.tsx`（改）、`useWebSocket.ts`（改）、model 选择状态、model 徽标组件（新，走 token）。

---

## F5 · 邀请页 `/invite`（依赖 B7）

- 新页 `pages/InvitePage.tsx`：我的邀请码 + 分享链接（复制按钮 + `toastStore` 反馈）、已邀人数、进度条（X/5、X/10 阶段奖励）、累计获得币。数据来自 `getInviteStatus()`。
- 注册流程：若带 `?invite=<code>`，登录成功后调 `bindInvite(code)`（`POST /api/invite/bind`）。
- 入口：`SettingsPage` 加「邀请好友」行。
- `services/api.ts` 新增 `getInviteStatus()` / `bindInvite(code)`。

**产出**：`InvitePage.tsx`（新）、`api.ts`（改）、`App.tsx`/`SettingsPage.tsx`（入口）、登录流程绑定钩子。

---

## F6 · 自建角色第 3 步音色改造（依赖 B5）

改 `pages/CreateCharacterPage.tsx` 第 3 步（`step===3`）：

- **预设音色区**（替换现扁平 `presets.map()` ~837-912）：
  - 后端按 `getPresetVoices(form.gender)` 返回**该性别 5 个 MiMo 音色**（provider='mimo'）。
  - UI 按 provider/风格**分组展示 5 张卡**，每卡显示 `name` + `description` + provider 标签（如「MiMo · 风格名」）+ 试听（`sample_url` → `getPresetVoiceSampleUrl`，blob 播放，失败 toast，复用现逻辑）+ 选中态。
- **克隆区**（替换现单一块 ~914-991）：改为**两个选项**：
  - **MiMo 克隆**：上传音频 → `uploadVoiceClone(characterId, file, 'mimo')`，状态 idle/uploading/processing/ready/failed（复用现状态机）。标注消耗币价（来自 `getPricing().actions`）。
  - **Fish 克隆**：同上但 `provider='fish'`；**免费用户置灰** + 「升级会员可使用」标签（判断 `membershipStore.entitlements.clone` 是否含 'fish'）→ 点击跳 `/membership`。标注 100 币。
- `services/api.ts`：`uploadVoiceClone(characterId, file, provider)` 加 `provider` 参数（默认 'mimo' 兼容）。
- 确认按钮启用条件：选中预设 **或** 任一克隆 ready（沿用现逻辑）。

**产出**：`CreateCharacterPage.tsx`（改第 3 步）、`api.ts`（`uploadVoiceClone` 加参数、`PresetVoiceDTO` 展示 provider/gender）、复用 `membershipStore`。

---

## 验收（DoD）

- `npm run build` 通过；新 UI **light + dark 双主题**验收（token 生效，无硬编码色）。
- F1：全站「积分」文案已改「yuoyuo币」。
- F2/F3：会员/商城页展示绑定码 + SKU + 去爱发电外链；金额全来自 `getPricing()`，无硬编码档位。
- F4：模型选择器按 tier 置灰 + 锁；越权点击提示升级；发送带 model；徽标/降级轻提示；币不足引导 `/wallet`。
- F5：邀请码/进度/绑定可用。
- F6：第 3 步每性别 5 个 MiMo 预设 + MiMo/Fish 两克隆，Fish 对免费用户置灰 + 升级提示。
- 一模块一分支一 PR，base=main。

---

## ⚙️ GPT 执行 Prompt（复制交付）

```
你为 yuoyuo（Heart 仓库前端，web/，React19+Vite+Tailwindv4+zustand+react-router7，PWA）实现「商业化前端：yuoyuo币改名 + 会员页 + 币钱包商城 + 聊天模型选择器 + 邀请 + 音色第3步改造」。严格按 docs/upgrade/yuoyuo_coin/00_INDEX.md 与 frontend_plan.md。

开工前核实现状（禁凭印象）：
- web/src/services/api.ts（已有 getPricing() 未被调用、getBalance/getTransactions/redeemCode/getPresetVoices/uploadVoiceClone；AuthUser 含 credits_balance）
- web/src/stores/（creditsStore.balance、authStore.user、chatStore.insufficientCredits、toastStore、themeStore）
- web/src/App.tsx（路由 + AuthGuard）、web/src/styles/tokens.css（禁硬编码色）、web/src/components/ui/（复用基元）
- web/src/pages/CreateCharacterPage.tsx（第3步：预设 presets.map ~837-912、单一克隆块 ~914-991；PresetVoiceDTO 已含 provider/gender）
- web/src/components/ConversationChatPage.tsx + hooks/useWebSocket.ts（sendMessage payload、turn_end/insufficient_credits 事件）

分模块独立分支/PR（base=main，一模块一 PR）：
F1 积分→yuoyuo币 文案+币图标：SettingsPage、TransactionsPage、RedeemPage、ConversationChatPage 的不足 Dialog、data/uiContent.ts（可即刻起，纯前端）。
F2 MembershipPage.tsx(/membership)：三档权益/价格卡(数据来自 getPricing().membership_tiers)、当前等级高亮、开通区展示绑定码+爱发电备注指引+SKU+外链；新 membershipStore(tier/expiresAt/entitlements/bindingCode/refresh)；api.ts 加 getMembership()、扩展 getPricing 类型；SettingsPage 加会员状态卡替换硬编码。
F3 WalletPage.tsx(/wallet)（或升级 TransactionsPage）：余额卡+商城4挡(getPricing().shop，展示到账+赠送)+每挡去爱发电(绑定码+SKU+外链)；保留 RedeemPage 兑换码为次要入口。
F4 ConversationChatPage 顶栏模型选择器(DeepSeek/Grok/Claude，标每次币价 from getPricing().models)：按 membershipStore.entitlements.models 置灰+锁+「升级会员」跳/membership，DeepSeek 恒可选；选中 model 存 per-character；useWebSocket.sendMessage payload 加 model；处理事件 model_forbidden→Dialog、turn_end.served_model→模型徽标、degraded_to→轻 Toast「已切换到X」(不显技术错误)、insufficient_credits→复用不足 Dialog 跳/wallet；turn_end.balance→creditsStore.setBalance。
F5 InvitePage.tsx(/invite)：邀请码+分享链接(复制+toast)、已邀数、进度(X/5、X/10)、累计币；带 ?invite= 登录后 bindInvite；SettingsPage 加入口；api.ts 加 getInviteStatus()/bindInvite(code)。
F6 CreateCharacterPage 第3步：预设区改为按性别5个MiMo音色分组卡(name+description+provider标签+试听 getPresetVoiceSampleUrl blob+选中态，替换扁平 map)；克隆区改两选项——MiMo克隆(uploadVoiceClone(cid,file,'mimo'))+Fish克隆(provider='fish'，免费用户置灰+「升级会员可使用」跳/membership，标100币，判断 membershipStore.entitlements.clone 含 fish)；api.ts uploadVoiceClone 加 provider 参数(默认mimo)。

铁律：禁硬编码颜色(用 tokens.css)、禁硬编码价格档位(全部来自 getPricing())、light+dark 双主题验收；复用现有 ui 基元与 store 勿重造；文案产品名恒 yuoyuo、货币恒 yuoyuo币。每 PR：npm run build 通过 + 双主题自检 → 提交 → 开 PR(base=main，body 写改动/验收/依赖的后端端点)。F1 可先做；F2/F3 依赖后端 B1/B2/B6，F4 依赖 B3/B4，F6 依赖 B5——依赖未就绪时先用 mock 数据搭 UI 并在 PR body 标注。
```
