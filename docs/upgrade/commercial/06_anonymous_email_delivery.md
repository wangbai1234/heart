# 模块 4-补 · 匿名化邮件 OTP 投递（替代个人 SMTP）

> 依赖：模块 4（`01_auth_otp.md`）已把登录改为 Email OTP，投递抽象为 `EmailSender` Protocol + `SMTPEmailSender`。
> 本补充**只替换"验证码怎么发出去"这一层**，不改 OTP 生成/校验/防刷逻辑。
> 目标（你的三条硬约束）：发验证码邮件时**不暴露**①个人真实身份 ②私人邮箱归属 ③国内可追踪性（IP / 实名 / ICP / 落地卡）。

---

## 0. 为什么现在的 SMTP 方案不满足

`SMTPEmailSender(aiosmtplib)` 必须挂一个真实邮箱账户来发信，这带来三处泄露：

| 泄露点 | 现状风险 |
|--------|----------|
| **发件账户** | 用个人 Gmail/163/QQ/企业邮 → 邮件头 `From`/`Return-Path`/`Received` 直接带走你的邮箱与真实身份；163/QQ 均需手机实名，天然可追踪。 |
| **发信 IP** | 若在 VPS 或本机自建 SMTP，`Received` 头暴露服务器/家宽 IP，指向服务器注册人或宽带实名。 |
| **域名归属** | 用 `.cn` 或已 ICP 备案域名 → 备案主体=实名，等于把身份写进域名。 |

结论：**问题不在"要不要发邮件"，而在"用谁的通道、从哪个 IP、以谁的名义"**。把这三件事从"你个人"剥离即可。

---

## 1. 目标架构（一句话）

> **专用离岸域名（WHOIS 隐私）+ 第三方事务邮件 API（免费额度免 KYC）+ 子域 DKIM/SPF/DMARC**，
> 应用只调用商家 HTTPS API，**不接触任何邮箱账户、不自建 SMTP、发信 IP = 商家的 IP**。

三条约束如何被逐条满足：

| 约束 | 如何满足 |
|------|----------|
| 不暴露个人身份 | 商家账户与域名以**产品/业务身份**注册；WHOIS 隐私保护；低量走**免费额度→免绑卡免实名 KYC** |
| 不暴露私人邮箱归属 | 发件人是 `noreply@mail.yuoyuo.app` 这类**角色地址**，不是任何私人邮箱；应用不登录任何邮箱 |
| 国内不可追踪 | 域名不走 `.cn`/不 ICP 备案；DNS 在 Cloudflare（DNS-only，已在技术栈）；**发信出口 IP 属于离岸商家**，非你的 VPS/家宽；商家与数据均在**中国大陆司法辖区外** |

---

## 2. 投递商选型（事务邮件 API，非个人 SMTP）

只选**HTTPS API 直发**（不落地 SMTP 凭证、不暴露出口 IP）。按"匿名友好度 + 免绑卡额度 + 接入难度"排序：

| 商家 | 免费额度 | 免费档要绑卡/KYC? | 匿名友好 | 说明 |
|------|----------|-------------------|----------|------|
| **Resend**（首选） | 100 封/天、3k/月 | **免费档无需绑卡** | 高 | API 极简、DKIM 引导清晰、离岸；OTP 量级绰绰有余 |
| **Brevo (Sendinblue)** | 300 封/天 | 免费档免卡 | 中高 | 额度更大；界面稍杂 |
| **MailerSend** | 3k 封/月 | 免费档免卡 | 中高 | 额度大；需域名验证 |
| **AWS SES** | 3k/月(12个月) | **需 AWS 账户+绑卡** | 低（KYC 强） | 最便宜可扩展，但绑卡=身份锚，仅在规模化且有离岸主体/卡时选 |

**推荐：主 = Resend（免费档免卡，身份锚最少）**；备 = Brevo（双商容灾，见 §6）。
> 关键判断：OTP 是**极低量**流量（每用户偶发几封），**免费额度足够长期运行**，从而**根本不触发绑卡/实名 KYC** —— 这是"去身份锚"最有效的一招，比任何技巧都干净。

**明确禁止**：① 在 VPS/本机自建 SMTP（暴露 IP、进垃圾箱、绑服务器实名）；② 个人邮箱中转（QQ/163/Gmail 应用密码）；③ `.cn` 或已备案域名做发件域。

---

## 3. 域名与身份隔离（最关键的一步）

### 3.1 发件域名
- 注册**一个离岸中性域名**（如 `yuoyuo.app` / `.com` / `.io`），或复用产品主域的**发信子域** `mail.yuoyuo.app`（隔离信誉，主域被封不影响）。
- 注册商选**默认 WHOIS 隐私**的：**Cloudflare Registrar（at-cost、强制隐私）** / Porkbun / Namecheap。
- **不做 ICP 备案**（备案=实名主体上链）。DNS 托管在 **Cloudflare（DNS-only 灰云）**，与技术栈文档一致。

### 3.2 身份与支付锚点（"不暴露个人身份"的核心）
- 商家账户注册邮箱 = **同域角色邮箱**（`ops@yuoyuo.app`），非私人邮箱。
- 账户主体名 = **产品名/业务名**，非个人真名。
- **支付**：优先**免费额度→全程免绑卡**；若未来必须付费，用**业务卡 / 虚拟卡（Wise 业务、privacy.com 类）/ 离岸主体**，避免国内个人储蓄卡直连（个人卡=强身份锚 + 可追踪）。
- 残余锚点诚实说明：域名注册人与商家账户**仍指向"某个注册它的人"**。把它压到最小的手段=WHOIS 隐私 + 业务身份 + 免费档免 KYC；若要更强隔离，需**离岸公司主体**承接域名与账户（超出工程范围，属运营决策）。

---

## 4. DNS 与可达性（SPF / DKIM / DMARC，同时也是"隐藏来源 IP"的机制）

在发信子域 `mail.yuoyuo.app` 配置（记录值由商家控制台生成）：

| 记录 | 类型 | 作用 |
|------|------|------|
| SPF | TXT `v=spf1 include:<provider> ~all` | 授权商家 IP 发信 |
| DKIM | CNAME/TXT（商家给的 selector） | 签名，保证不被伪造、进收件箱 |
| DMARC | TXT `_dmarc` `v=DMARC1; p=quarantine; rua=mailto:dmarc@yuoyuo.app` | 策略 + 报告 |

> **为什么这同时解决"国内可追踪性"**：邮件由**商家的离岸 IP 段**发出并签名，收件方 `Received`/`Authentication-Results` 看到的是**商家 IP + 你的域名**，**看不到你的 VPS/家宽 IP、看不到你的私人邮箱**。你的网络位置从邮件链路里彻底消失。
> 加固：API 调用从**新加坡 VPS**（技术栈已定）发起，连"谁在调用 API"的出口也不是你的家宽。

---

## 5. 代码改动（抽象已就绪，改动很小）

模块 4 已定义 `EmailSender` Protocol，只需**新增一个 API 实现并切换选择器**，OTP 业务零改动：

- `backend/heart/infra/email/`
  - 保留 `sender.py` 的 `EmailSender` Protocol。
  - 新增 `api_sender.py`：`ResendEmailSender`（`httpx.AsyncClient` POST `https://api.resend.com/emails`，Bearer=API key，body `{from, to, subject, text, html}`）。可选 `BrevoEmailSender` 作备份。
  - `__init__.py` 工厂 `get_email_sender()`：按 `EMAIL_PROVIDER ∈ {resend, brevo, smtp}` 返回实现；默认 `resend`。
- 发信语义不变：主题 `【yuoyuo】你的登录验证码 {code}`、正文 5 分钟有效（模块4 §6）。
- 失败处理不变：`/otp/request` 仍返回 `sent:true`（防泄露），内部记 `otp_email_send_failed_total`。
- **不再需要** SMTP host/port/user/password 任何一项。

### 5.1 `.env.example` 增补（不写真值）
```
# --- Email delivery (anonymized transactional API) ---
EMAIL_PROVIDER=resend            # resend | brevo | smtp(仅本地调试)
EMAIL_FROM=noreply@mail.yuoyuo.app
EMAIL_FROM_NAME=yuoyuo
RESEND_API_KEY=                  # 仅存服务端 secret，勿入库勿提交
BREVO_API_KEY=                   # 可选备份商
# SMTP_* 仅本地/离线调试用，生产留空
```

---

## 6. 容灾与防刷（沿用 + 增量）
- **双商容灾**：主 `resend` 失败 → 自动回退 `brevo`（同一 `EmailSender` 接口，工厂返回带 fallback 的组合实现）。任一成功即 `sent:true`。
- 防刷完全沿用模块4 §5（每邮箱 5/时 + 每 IP 限流 + 60s 冷却 + 试错锁）——**这也是反滥用发信、保护免费额度不被刷爆的前提**。
- 监控：`otp_email_send_failed_total{provider=}`；免费额度接近上限告警（防止静默丢信）。

## 7. 合规与边界（诚实声明）
- 本方案目的是**保护开发者个人隐私**（不把私人邮箱/真名/家宽 IP 写进产品邮件链路），属正当运维隔离。
- 仍须遵守**反垃圾邮件与商家 ToS**：只向**主动请求验证码的用户本人**发信（OTP 天然满足），不得群发营销。
- 匿名≠免责：真实经营仍受经营地/用户所在地法律约束；域名/商家账户主体的最终归属由运营决定，工程侧只负责把**默认链路里的个人锚点降到最低**。

---

## 8. 验收（DoD）
- 真机：请求 OTP → 收到来自 `noreply@mail.yuoyuo.app` 的验证码邮件，落**收件箱**（非垃圾箱）。
- 邮件原文头 `Received`/`Authentication-Results`：**只见商家 IP + yuoyuo 域名**，无私人邮箱、无 VPS/家宽 IP。
- DKIM=pass、SPF=pass、DMARC=pass（用 `mail-tester.com` 或 Gmail「显示原始邮件」核验，目标≥9/10）。
- 拔掉主商 API key（模拟故障）→ 自动走备份商仍能收到；`/otp/request` 仍返回 `sent:true`。
- 代码中**无任何 SMTP 账户凭证**；`grep -ri "smtp_password\|163\|qq\.com" backend/heart` 无生产引用。

---

## ⚙️ Mimo 执行 Prompt（复制交付）

```
你在 Heart 仓库（对外名 yuoyuo）实现「模块4-补：匿名化邮件 OTP 投递」。分支 feat/email-api-sender，base=main。仅替换邮件投递层，不改 OTP 生成/校验/防刷。严格按 docs/upgrade/commercial/06_anonymous_email_delivery.md。

后端：
1. backend/heart/infra/email/api_sender.py：新增 ResendEmailSender（httpx.AsyncClient 异步 POST https://api.resend.com/emails，Authorization: Bearer RESEND_API_KEY，body {from,to,subject,text,html}，超时+重试1次，非2xx 抛 EmailSendError）。可选 BrevoEmailSender 同接口作备份。
2. backend/heart/infra/email/__init__.py：工厂 get_email_sender() 按 EMAIL_PROVIDER∈{resend,brevo,smtp} 返回实现，默认 resend；提供组合 FallbackEmailSender（主失败→备份，任一成功即视为已发）。
3. 保持 EmailSender Protocol 与验证码模板不变（主题/正文见 01_auth_otp.md §6）；/otp/request 失败仍返回 sent:true 且计数 otp_email_send_failed_total{provider}。
4. core/config.py + .env.example 增补 §5.1 段（EMAIL_PROVIDER/EMAIL_FROM/EMAIL_FROM_NAME/RESEND_API_KEY/BREVO_API_KEY，不写真值，key 仅服务端 secret）。SMTP_* 降级为仅本地调试。
5. 单测：mock httpx，覆盖 resend 成功、resend 失败→brevo 回退成功、双失败仍 sent:true+计数、模板渲染正确、EMAIL_PROVIDER 选择器分支。

约束：不自建 SMTP、不用个人邮箱、发件人用角色地址 noreply@mail.yuoyuo.app；secret 不入库不提交；不改 OTP 防刷逻辑。ci.sh 全绿后开 PR。

运营侧（写进 PR 描述的 checklist，非代码）：注册离岸中性域名（Cloudflare Registrar，默认 WHOIS 隐私，不 ICP 备案）→ Resend 用同域角色邮箱+业务名注册（低量走免费档免绑卡）→ 在 mail.yuoyuo.app 配 SPF/DKIM/DMARC → mail-tester ≥9/10 → 填 RESEND_API_KEY 到服务端 secret。
```

---

## 附：本方案与原 SMTP 的取舍
| 维度 | 原 SMTP（个人邮箱） | 本方案（离岸 API+专用域） |
|------|--------------------|---------------------------|
| 个人身份暴露 | 高（发件账户实名） | 低（业务身份 + 免 KYC 免费档） |
| 私人邮箱归属 | 直接暴露 | 无（角色地址） |
| 国内可追踪 | 高（实名邮箱/IP/可能 ICP） | 低（离岸 IP + 隐私域 + 无备案） |
| 送达率 | 低（个人邮箱易判垃圾） | 高（专业 DKIM 信誉） |
| 接入成本 | 已实现 | 小（仅加一个 API 实现类） |
| 残余锚点 | — | 域名/商家账户注册人（用隐私+业务主体压到最小） |
