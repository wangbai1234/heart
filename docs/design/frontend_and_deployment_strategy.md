# Heart 前端技术栈 + 部署策略 选型

## Context

你是个人开发者，目标是把 Heart（AI 伴侣）交付给国内用户，并通过付费/赞助变现。四个硬约束：

1. **用户在中国大陆** —— 网络访问、CDN PoP、备案、支付通道都受影响
2. **个人开发者** —— 没有 ICP 备案、没有营业执照、没有 App Store 公司账号、没有支付平台对公账户
3. **想接微信/支付宝** —— 但官方支付平台审核门槛要求企业资质
4. **App 审核难** —— iOS 审核对 AI 伴侣类应用敏感，国内安卓商店要软著、政策合规

你提的栈：**Flutter → PWA → Cloudflare Pages → 新加坡服务器 → 爱发电（微信+支付宝）→ 兑换码**。

我的结论：**方向对，但 Flutter 是错的，CF Pages 也要调整**。下面是逐项分析和我推荐的最佳栈。

---

## 关键事实

项目已经有一个相当成熟的前端，不是空地：

- `web/` 目录 **React 19 + Vite 8 + TypeScript + Tailwind v4 + zustand + react-router-dom v7**
- 约 1063 行 TSX/TS，含：
  - `hooks/useWebSocket.ts`（已经接通 `/api/chat/ws`）
  - `services/audioPlayer.ts`、`audioConcat.ts`（语音流式播放/拼接）
  - `components/`：EmotionOrb、MessageList、CharacterSelector、ChatInput、VoiceMessageBubble
  - `pages/ChatPage.tsx`、`stores/chatStore.ts`
- 后端配套已就绪：`backend/heart/api/routes_chat_ws.py`（WebSocket）、`routes_voice.py`、`ss08_voice/stream_session.py`

→ **换 Flutter = 把这些全部重写**，包括 WebSocket、音频流式拼接、Tailwind 样式、zustand store。代价 1-2 周 + 持续维护成本。

---

## 逐项评估你的提案

### ❌ Flutter PWA —— 不推荐

| 问题 | 说明 |
|------|------|
| **重写代价高** | 上述 ~1000 行 React 代码全部作废 |
| **包体过大** | Flutter Web (CanvasKit) 首屏 2-3 MB，HTML renderer 文字渲染差。PWA 弱网首屏体验糟糕 |
| **移动 web 兼容差** | iOS Safari PWA 限制 + 微信内置浏览器（X5/Chromium 改）对 Flutter canvas 兼容性历史不佳，IME/手势/滚动都有坑 |
| **想要的"一套代码"未必兑现** | 你后面还是要 PWA 形态用，Flutter Web 的优势（同一份代码出原生 app）你没打算用 App Store —— 失去主要卖点 |

**真正的"一套代码三端"答案**：**React + Capacitor 7**。Capacitor 把现有 React PWA 包成 Android APK / iOS IPA，复用全部组件、WebSocket、音频代码。零重写。

### ⚠️ Cloudflare Pages —— 部分推荐

- ✅ 免备案、免费、全球 CDN
- ❌ **CF 在中国大陆没有 PoP**。`*.pages.dev` 子域被运营商 DNS 污染严重，部分省份直接超时
- ⚠️ 自定义域名 + CF 代理：延迟 200-800ms，时段不稳

**调整**：
- 用自定义域名（在 Cloudflare Registrar 或 Porkbun/Namecheap 买 `.com`/`.app`，**不要** `.top/.xyz`）
- 静态资源可以两条路：
  - **方案 A**：CF Pages（境外用户）+ 国内访问失败时 fallback 到下面的新加坡 VPS 直挂静态
  - **方案 B**（更简单）：直接把静态前端用 Caddy 挂在新加坡 VPS 上，Cloudflare 只做 DNS（不开橙云代理），延迟可控
- 备选托管：**EdgeOne 海外版**（腾讯）或 **七牛云海外** —— 都免备案，但配置稍重

### ✅ 新加坡服务器 —— 推荐，需指定线路

- 普通新加坡 VPS（Vultr / DO / AWS Lightsail）到大陆延迟 70-300ms，看运营商和省份
- **认准 CN2 GIA / AS9929 / CMI 线路**：搬瓦工 The Plan、RackNerd、华纳云等
- 备选：**东京**（对北方/联通用户更快）、**香港**（便宜 VPS 容易被运营商减速）

### ✅ 爱发电 + 兑换码 —— 推荐主路径

- 个人开发者最合规、最稳的中国大陆收款方式
- 爱发电支持「自动发卡」—— 用户赞助后自动邮件/页面下发兑换码，UX 跳转一次就完成
- 唯一缺点是不能在 app 内直接调起支付，但这是中国大陆个人开发者无法绕开的法规边界

**备选/补充**：
- 灰色：虎皮椒/Z-Pay 等聚合个码 —— 能直接唤起微信/支付宝，但商户码会被风控封停，**不建议作为主路径**
- 国际化：Stripe（注册需香港/美国主体）、Paddle、Lemon Squeezy —— 后期做大再说
- 兜底：PayPal —— 国内用户接受度低，但海外用户友好

### 爱发电支付 UX 闭环设计

由于爱发电是外部平台，用户需要在 App 外完成支付再回到 App 兑换，这个跳转会丢失部分用户。以下设计最小化这个断层：

```
用户首次打开 App
    ↓
弹窗引导（仅首次）：
  "心屿需要通过「爱发电」平台赞助获取会员资格，
   支持微信/支付宝，赞助后获得兑换码即可激活。"
  [去赞助]  [稍后再说]
    ↓
App 内常驻入口：
  侧边栏/设置页 → "兑换会员" 按钮（始终可见）
    ↓
爱发电赞助页面（外部）：
  顶部醒目提示：
  "赞助后请查看邮箱/页面中的兑换码，回到心屿 App 输入即可激活会员。"
    ↓
用户回到 App → "兑换会员" → 输入兑换码 → 激活成功
```

**关键文件**：
- `web/src/pages/RedeemPage.tsx` —— 兑换码输入页
- `web/src/components/FirstVisitGuide.tsx`（新增）—— 首次弹窗引导组件
- `web/src/stores/userStore.ts` —— 记录 `hasSeenGuide` 本地标记

### ❌→✅ App 分发的真正答案

| 平台 | 你说"难" | 真实可行路径 |
|------|---------|-------------|
| **Web** | —— | PWA（manifest + service worker） |
| **Android** | 应用商店审核 | **Capacitor 编译 APK，官网直接下载**；可选上架**酷安**（个人开发者友好，无软著门槛） |
| **iOS** | App Store 审核 | **TestFlight 公开链接**（10k 用户上限，足够 MVP；不需要正式上架审核） |

→ Capacitor 让你**完全绕开**国内安卓应用商店和 iOS 正式审核流程。

---

## 最终栈（已锁定决策）

```
前端：React 19 + Vite + Tailwind v4 + zustand  （保留现有 web/）
  ├─ + vite-plugin-pwa            → PWA 形态（web 端 + 主屏图标）
  └─ + Capacitor 7                → APK + iOS IPA（同一份代码）

静态托管：新加坡 VPS Caddy 挂静态 + Cloudflare 只做 DNS（关闭橙云代理）
  域名：海外注册商（Cloudflare Registrar / Porkbun），.com / .app

后端：新加坡 VPS（CN2 GIA 或 CMI 线路）
  └─ Docker Compose（沿用现有 docker-compose.yml）
  └─ Caddy 反代 + Let's Encrypt 自动 TLS
  └─ FastAPI + PostgreSQL(pgvector) + Redis（已有）

支付：爱发电（赞助挡位 → 自动发卡）→ 兑换码激活会员
  └─ 后端加 redemption_codes 表 + 激活 API

分发（MVP 期）：
  ├─ Web: PWA（heart.example.com，添加到主屏）
  ├─ Android: Capacitor 编 APK，官网直链下载 + 可选上架酷安
  └─ iOS: TestFlight 公开链接（≤ 10000 用户，免审核）
```

### 与你原方案的对照

| 你 | 我 | 理由 |
|---|---|---|
| Flutter PWA | React PWA + Capacitor | 复用 1063 行已有代码，包体小，移动 web 兼容好 |
| Cloudflare Pages | CF 自定义域名 **或** VPS Caddy + CF DNS | `*.pages.dev` 国内不稳，自定义域名规避 |
| 新加坡服务器 | ✅ + 指定 CN2 GIA 线路 | 同意 |
| 爱发电 + 兑换码 | ✅ + Stripe 国际化备选 | 同意 |
| —— | + Capacitor | 关键补充：一份代码同时出 APK + iOS |

---

## 关键文件 / 复用点

如果走这套栈，**修改集中在**：

- `web/vite.config.ts` —— 加 `vite-plugin-pwa` 配置（manifest、workbox）
- `web/public/manifest.webmanifest`（新增）—— PWA 安装清单
- `web/capacitor.config.ts`（新增）—— Capacitor 配置，target backend URL
- `web/android/`、`web/ios/`（Capacitor 生成）—— 包装层，几乎不动
- `backend/heart/api/`—— 新增 `routes_redemption.py`（兑换码激活）
- `backend/migrations/versions/0XX_redemption_codes.py`（新增）—— 表结构
- 部署脚本：`scripts/deploy_singapore.sh`（新增），把后端跑在 VPS

**已有可复用**：
- `web/src/hooks/useWebSocket.ts`、`services/audioPlayer.ts`、`services/audioConcat.ts` —— 移动端一字不改
- `docker-compose.yml`、`Makefile` —— VPS 部署直接复用
- `backend/heart/safety/` —— 内容安全已有，对国内合规友好

---

## 验证路径（实施后如何确认可行）

1. **PWA 安装**：在 iPhone Safari / Android Chrome 打开站点，"添加到主屏幕"，离线打开，确认 service worker 命中
2. **Capacitor 出包**：`npx cap add android && npx cap build` 出 APK，真机装上能跑
3. **国内访问**：用国内 VPN/移动数据测试 CF 自定义域名 vs `*.pages.dev` 延迟 + 可达性
4. **WebSocket 跨域**：APK 装在手机上从 4G 网络连新加坡后端，chat WS 稳定不断流
5. **支付闭环**：爱发电赞助 → 自动发码邮件 → app 内输入码 → 后端 `routes_redemption` 写入 user_subscriptions 表 → 前端 entitlement 更新

---

## 离线降级策略

PWA 的 Service Worker 会缓存历史聊天和静态资源，但无法缓存 WebSocket 连接。Token 过期、网络波动、服务器不可达时需要优雅降级，不能白屏。

### WebSocket 断连检测与重试

```
WebSocket 连接失败
    ↓
立即重试（第 1 次）
    ↓ 失败
等待 2s 后重试（第 2 次）
    ↓ 失败
等待 5s 后重试（第 3 次）
    ↓ 失败
停止重试，显示降级 UI：
  ⚠️ "网络不稳定，请检查连接后刷新"
  [重试]  [查看历史聊天]
```

**实现要点**（修改 `web/src/hooks/useWebSocket.ts`）：
- 连接失败计数器 `retryCount`，超过 3 次停止重连
- 指数退避间隔：0ms → 2000ms → 5000ms
- 断连期间用户发送的消息本地缓存，重连后自动重发
- 显示降级 UI 时历史聊天仍可正常浏览（来自 SW 缓存）

### Token 过期处理

```
WebSocket 收到 401/403
    ↓
清除本地 token
跳转到登录页（而非白屏）
    ↓
用户重新登录后自动恢复聊天上下文
```

### 离线缓存策略（Service Worker）

| 缓存内容 | 策略 | 说明 |
|----------|------|------|
| 静态资源 (JS/CSS/图标) | CacheFirst | 首次加载后离线可用 |
| 历史聊天页面 | NetworkFirst + fallback to cache | 有网用网，无网显示缓存 |
| API 请求 | NetworkOnly | 不缓存，保证数据新鲜 |
| WebSocket | 不缓存 | 实时连接，断了就是断了 |

---

## 你已确认的决策（2026-06-23）

- ✅ 前端：保留 React，加 PWA + Capacitor，**不**换 Flutter
- ✅ 静态托管：VPS Caddy + Cloudflare 仅做 DNS（不开橙云代理）
- ✅ iOS：MVP 期只走 TestFlight 公开链接，不上 App Store

## 实施步骤建议（按顺序、每步独立可验证）

1. **PWA 化现有 web**
   - `cd web && npm i -D vite-plugin-pwa`
   - 改 `vite.config.ts` 加 `VitePWA({ registerType: 'autoUpdate', ... })`
   - 加 `public/icons/`（192/512 PNG）、`manifest.webmanifest`
   - `npm run build && npm run preview` → 浏览器开发者工具 Application → 确认 Service Worker 注册成功
   - **产出**：手机浏览器能"添加到主屏幕"，离线打开
2. **新加坡 VPS 部署**
   - 选 CN2 GIA 线路 VPS（搬瓦工 / RackNerd Tokyo / Vultr Tokyo 备选）
   - `git clone` + `docker compose up -d` 跑后端
   - Caddy 反代：`api.heart.example.com → :8000`、`heart.example.com → /var/www/web/dist`
   - **产出**：从国内手机 4G 能打开站点 + WebSocket 连通
3. **Capacitor 出 Android APK**
   - `npm i @capacitor/core @capacitor/cli && npx cap init`
   - `npx cap add android`，把 `server.url` 指到 `api.heart.example.com`
   - `npm run build && npx cap sync && npx cap open android` → Android Studio 出 APK
   - **产出**：APK 在真机能跑、能聊天、音频能播
4. **支付 + 兑换码**
   - 后端：新增 `backend/heart/api/routes_redemption.py` + 迁移 `0XX_redemption_codes.py`（表字段：code、tier、expires_at、redeemed_by、redeemed_at）
   - 后台脚本：批量生成兑换码 CSV，导入爱发电"自动发卡"商品
   - 前端：`pages/RedeemPage.tsx` 输入码 → 调 `POST /api/redemption/redeem`
   - **产出**：在爱发电赞助 → 邮件收到码 → app 输入码 → 后端写入 user_subscriptions
5. **iOS Capacitor + TestFlight**
   - `npx cap add ios` + Xcode 打包
   - 个人开发者账号（$99/年）→ App Store Connect → TestFlight → 公开链接
   - **产出**：iPhone 通过 TestFlight 安装能跑

## 关键文件 / 复用点

**新增**：
- `web/vite.config.ts`（修改加 PWA 插件）
- `web/public/manifest.webmanifest`、`web/public/icons/`
- `web/capacitor.config.ts`、`web/android/`、`web/ios/`（Capacitor 生成）
- `web/src/pages/RedeemPage.tsx`（兑换码输入页）
- `web/src/components/FirstVisitGuide.tsx`（新增）—— 首次弹窗引导
- `web/src/stores/userStore.ts`（修改）—— 添加 `hasSeenGuide` 本地标记
- `backend/heart/api/routes_redemption.py`
- `backend/migrations/versions/0XX_redemption_codes.py`
- `scripts/deploy_singapore.sh`（VPS 一键部署）
- `infra/caddy/Caddyfile`（反代 + 静态文件配置）

**复用、零改动**：
- `web/src/hooks/useWebSocket.ts`、`services/audioPlayer.ts`、`services/audioConcat.ts`
- `backend/heart/api/routes_chat_ws.py`、`routes_voice.py`、`ss08_voice/stream_session.py`
- `docker-compose.yml`、`Makefile`
- `backend/heart/safety/`（内容安全）

## 验证（实施后如何确认整体可行）

| 维度 | 验证方式 | 通过标准 |
|------|---------|---------|
| PWA 安装 | iPhone Safari / Android Chrome 打开 → 添加到主屏 → 离线打开 | SW 命中，离线能看历史聊天 |
| Capacitor APK | 真机装 APK，4G 网络连后端 | chat 文本 + 语音流式正常 |
| 国内可达性 | 多省份 / 三大运营商访问站点 | P50 < 300ms，P95 < 800ms |
| WebSocket 稳定性 | 4G 网络持续 10 分钟聊天 | 不断流、断线后自动重连 |
| 支付闭环 | 爱发电赞助 → 收码 → 兑换 | 后端订阅记录正确写入 |
| 支付 UX | 首次打开 → 弹窗引导 → 关闭后常驻兑换入口 | 弹窗只出现一次，兑换入口始终可见 |
| 离线降级 | 关闭网络 → 打开 App → 查看历史聊天 → 恢复网络 | 离线能浏览，重连后自动恢复 |
| WebSocket 重连 | 模拟断网 10s → 恢复 → 继续聊天 | 自动重连，消息不丢失 |
| TestFlight | 公开链接 5 人内测 | iPhone 能装、能跑、不崩 |

