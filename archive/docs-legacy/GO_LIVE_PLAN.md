# yuoyuo 正式上线准备手册

> **目标**：2 周内正式公网上线。
> **已定架构**：海外 VPS + Docker + Caddy（自动 HTTPS）+ Cloudflare 管 DNS；域名 `yuoyuo.app`；邮件走 Resend；服务大陆用户、暂不备案。
> 本文分三部分：**A. 我（Claude）已完成的** · **B. 交给 mimo 的代码修复** · **C. 需要你本人做的（含 Cloudflare / Resend / VPS 具体步骤 + 采购清单）**。

---

## A. 我已完成的（本轮及此前）

| 项 | 状态 |
|----|------|
| 记忆/情绪/语义召回系统修复（MEMORY_FIX_PLAN PR1–PR4，#87–#94） | ✅ 已合并 main |
| 语义召回基建（EmbeddingService + 写/查 embedding + 回填/清理脚本） | ✅ 已合并（受 `EMBEDDING_API_KEY` 门控） |
| 项目状态文档同步 + 执行手册 `EXECUTION_MANUAL.md`（#95） | ✅ 已合并 |
| 两份真实测试/评估文档的**缺陷分级（P0–P3）**与逐条核验 | ✅ 见 `BUG_TRIAGE_AND_FIX.md` |
| **发现并修正两处文档误判**：encoder-worker "unhealthy" 实为探针端口误报；reasoner 崩溃根因=默认模型选错 | ✅ 已写入工单 |
| 确认**模块 06 匿名邮件 OTP 已在代码里写好**（Resend/Brevo/Fallback + 工厂 + 已接 `/api/auth`），无需从零开发 | ✅ 核验 |
| mimo 修复工单 `docs/BUG_TRIAGE_AND_FIX.md` | ✅ 本轮产出 |
| 本上线手册 `docs/GO_LIVE_PLAN.md` | ✅ 本轮产出 |

---

## B. 交给 mimo 的代码修复（详见 `docs/BUG_TRIAGE_AND_FIX.md`）

排期概览（两周）：

1. **Step 0**：收敛当前 main 未提交的邮件 06 代码 → 拆成 `feat/anonymous-email-otp` + `docs/` PR
2. **P0-A**：默认 LLM 模型 `deepseek-reasoner→deepseek-chat`（10 分钟，先合）
3. **P0-1**：长期记忆召回错误（诊断驱动修复）
4. **P0-B**：生产 infra（`docker-compose.prod.yml` + `Caddyfile` + 前端构建）
5. **P1**：encoder-worker 健康检查 + 抽取成本控制 + DB 备份脚本

> 不修：FastAPI 版本锁（有意约束）、依赖双源、日志收集等 P2/P3——理由见工单，别浪费窗口。

---

## C. 需要你本人做的事

### C0. 采购/账号清单（先把这些办齐，后面才能联调）

| 项 | 用途 | 预估 | 备注 |
|----|------|------|------|
| **Cloudflare 账号 + 注册 `yuoyuo.app`** | 域名 + DNS | 域名 ~¥100/年 | `.app` 由 Google 注册局管理，**强制 HTTPS**（Caddy 自动满足） |
| **海外 VPS**（香港/日本/新加坡，线路对大陆友好，如 CN2 GIA） | 跑后端全栈 | ~¥40–120/月 | **别选 EU 机房**（对大陆延迟高）。2 vCPU / 4GB RAM / 40GB 起步 |
| **Resend 账号** | 发 OTP 邮件 | 免费档 100/天、3k/月，无需信用卡/KYC | 需验证发信域名 |
| **DeepSeek API key** | 真实对话（必需） | 充值制 | 已有 |
| **SiliconFlow API key（可选）** | 语义召回 embedding（bge-m3） | 充值制 | 已有；不配则退回 recency/identity，系统不崩 |
| **MiniMax / MiMo key（可选）** | TTS 语音 | 按量 | 不配则语音不可用，文本正常 |
| **一台能 SSH 的电脑** | 部署运维 | — | 你现在的 Mac 即可 |

---

### C1. 注册 Cloudflare 域名 `yuoyuo.app`（约 15 分钟）

1. 注册/登录 https://dash.cloudflare.com
2. 左侧 **Domain Registration → Register Domains**，搜 `yuoyuo.app`，加入购物车结算（`.app` 约 $14/年）。
3. 注册后 Cloudflare 自动成为该域名的 DNS 托管方（无需改 nameserver）。
4. **DNS 记录**（等你 C3 拿到 VPS 公网 IP 后再填，先知道要填什么）：
   | 类型 | 名称 | 内容 | 代理状态 |
   |------|------|------|---------|
   | A | `yuoyuo.app`（或 `@`） | `<VPS 公网 IP>` | **DNS only（灰云）** |
   | A | `www` | `<VPS 公网 IP>` | **DNS only（灰云）** |
   | A/TXT | `mail`（见 C2 Resend） | Resend 给的记录 | DNS only |

   > ⚠️ **务必用"灰云 / DNS only"，不要开橙云代理**。原因：Cloudflare 橙云 IP 在大陆常被干扰/限速；灰云直连你的 VPS，由 Caddy 直接终止 TLS，大陆可达性更稳。代价是失去 CF 的 DDoS/CDN——上线初期可接受，后续按需再评估。

5. **SSL/TLS 模式**：因为走灰云直连，加密由 VPS 上 Caddy 用 Let's Encrypt 完成，Cloudflare 这里不用管 SSL 模式。

---

### C2. 注册 Resend + 验证发信域名（约 20 分钟 + DNS 生效等待）

代码已实现 Resend 发送（`backend/heart/infra/email/api_sender.py`），你只需配置：

1. 注册 https://resend.com （免费档够用：100 封/天）。
2. **Add Domain**，填 **`mail.yuoyuo.app`**（用子域，别用裸域——代码默认发信地址是 `noreply@mail.yuoyuo.app`）。
3. Resend 会给你几条 DNS 记录（**MX**、**SPF/TXT**、**DKIM/CNAME**、可选 DMARC）。**全部照抄到 Cloudflare DNS**（C1 那个面板，均 DNS only）。
4. 回 Resend 点 **Verify**，等 DNS 生效（几分钟到数小时）到全绿。
5. **创建 API Key**（Resend 后台 → API Keys）→ 这串 key **只填到 VPS 的 `.env`**：
   ```
   EMAIL_PROVIDER=resend
   RESEND_API_KEY=<你的 key>
   EMAIL_FROM=noreply@mail.yuoyuo.app
   EMAIL_FROM_NAME=yuoyuo
   ```
   > 想要更稳可选 `EMAIL_PROVIDER=fallback` 并再配 `BREVO_API_KEY`（Brevo 免费 300/天做备份，代码已支持主→备自动切换）。
6. **绝不把 API key 提交进 Git**——只存服务器 `.env` / secret 管理。

---

### C3. 开 VPS + 部署（等 mimo 的 `feat/prod-deploy` 合并后，约半天）

1. 买 VPS（香港/日本/新加坡，2C4G 起，Ubuntu 22.04+），拿到公网 IP。
2. 把 IP 填进 C1 的 A 记录（`yuoyuo.app` + `www`）。
3. SSH 上去装 Docker + Docker Compose plugin。
4. `git clone` 仓库，`cp .env.example .env`，按 **C4** 填必填变量。
5. **生成 JWT RS256 密钥对**（`.env` 默认 RS256，不配后端起不来）：
   ```bash
   openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt_private.pem
   openssl rsa -pubout -in jwt_private.pem -out jwt_public.pem
   # 把两个文件内容分别贴进 .env 的 JWT_PRIVATE_KEY / JWT_PUBLIC_KEY（保留 PEM 换行）
   ```
   > 想省事本地/内测可临时 `JWT_ALGORITHM=HS256` + `JWT_SECRET_KEY=<≥32位随机>`，但**正式上线建议 RS256**。
6. `cd web && npm run build`（产出 `web/dist`，交给 Caddy 托管）。
7. `docker compose -f docker-compose.prod.yml up -d`（含 `alembic upgrade heads`）。
8. 验证：`curl https://yuoyuo.app/health/ready` → 就绪；手机浏览器打开 `https://yuoyuo.app` 能收到 OTP 邮件、登录、对话。

---

### C4. 生产 `.env` 必填清单（VPS 上，永不入库）

```bash
# 身份（必填，否则后端 fail-fast 起不来）
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY=<PEM>
JWT_PUBLIC_KEY=<PEM>
OTP_PEPPER=<≥32位随机字符串>

# 对话（必填）
DEEPSEEK_API_KEY=<你的 key>
MAIN_LLM_MODEL=deepseek-chat            # ← 必须，别用 reasoner（P0-A）

# 邮件 OTP（必填，上线登录靠它）
EMAIL_PROVIDER=resend
RESEND_API_KEY=<你的 key>
EMAIL_FROM=noreply@mail.yuoyuo.app

# 网络/安全（必填）
CORS_ALLOWED_ORIGINS=https://yuoyuo.app,https://www.yuoyuo.app
DEBUG=false
LOG_LEVEL=WARNING

# 语义召回（可选，不配则退回 recency/identity，系统正常）
EMBEDDING_API_KEY=<SiliconFlow key>
EMBEDDING_DIMENSIONS=1024               # 必须与 DB vector(1024) 一致

# 语音 TTS（可选，不配则无语音）
MINIMAX_API_KEY=
MIMO_API_KEY=

# 爱发电充值（可选，模块3；不配则兑换/充值不可用）
AFDIAN_USER_ID=
AFDIAN_WEBHOOK_TOKEN=
```

---

### C5. 上线前你要亲自过的验收清单

- [ ] `https://yuoyuo.app` 手机浏览器打开，UI 自适应正常
- [ ] 输入邮箱 → **收到 Resend 发的 OTP 邮件**（查收件箱/垃圾箱）→ 登录成功
- [ ] 首登 Profile 补全 + 18+ 校验生效
- [ ] 文本对话正常（不崩、无 `compose_stream_failed`）
- [ ] 记忆召回：多轮后仍能答对早期事实（P0-1 修完后验）
- [ ] 语音（若配了 TTS）能播放
- [ ] 充值/兑换（若配了爱发电）能加积分
- [ ] `docker ps` 所有容器 healthy（含 encoder-worker，P1-2 修完后）
- [ ] DB 有定时备份

---

## D. 风险提醒（Release Manager 视角）

1. **大陆可达性**是最大不确定项：海外 VPS + 灰云直连虽比橙云稳，但仍受线路波动影响。上线后盯真实大陆用户的连通性与延迟；必要时换 CN2 GIA 线路或加国内中转。
2. **不备案的合规灰区**：面向大陆用户 + 海外服务器 + 无 ICP，属灰区，适合内测/小范围。若要规模化面向大陆，需回到"国内服务器 + ICP 备案"路径（2–4 周）。
3. **DeepSeek/SiliconFlow 是国内 API**：从海外 VPS 调用延迟略高但可用；盯首字延迟。
4. **成本**：P1-3 未修前，每轮对话都触发抽取 LLM，DeepSeek 余额消耗快——上线前务必修完 P1-3 或先限流。
5. **`.app` 强制 HTTPS**：Caddy 自动 Let's Encrypt 可满足；确保 80/443 端口对公网开放供 ACME 验证。

---

**下一步**：把 `docs/BUG_TRIAGE_AND_FIX.md` 交给 mimo 从 Step 0 开始执行；你并行去办 C0 采购 + C1 域名 + C2 Resend。两条线在 D8–D10 汇合联调。
