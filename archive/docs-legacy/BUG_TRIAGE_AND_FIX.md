# yuoyuo 上线前缺陷修复工单（交付 mimo 执行）

> **目标**：2 周内修完所有 P0/P1，**正式公网上线**（海外 VPS + Caddy + Cloudflare DNS，面向大陆用户、暂不备案）。
> **依据**：`docs/PROJECT_STARTUP_AND_DEPLOYMENT_EVALUATION.md` + `docs/TEST_RESULTS.md`，全部经真实代码核验（非推断）。
> **治理**：严格遵守 `.claude/CLAUDE.md`——一关注点一分支一 PR，base=main，`bash scripts/ci.sh` 全绿再 push，合并即删分支，禁止直接提交 main，禁止提交 `.env`/密钥。
>
> **执行顺序**：Step 0（收敛当前脏 main）→ P0-A → P0-1 → P1 → P0-B。P0-B（生产 infra）可与 P0-1/P1 并行。

---

## Step 0 — 先收敛当前 main 的未提交改动（最优先，别再往下做之前先做这个）

**现状（已核验）**：当前 `main` 分支工作区是脏的，且**混了多个关注点**。这些改动其实是**模块 06 匿名邮件 OTP 已经写好的代码**（Resend/Brevo/Fallback + factory + 已接入 `/api/auth`），加上兑换页和文档：

| 文件 | 性质 | 归属关注点 |
|------|------|-----------|
| `backend/heart/infra/email/api_sender.py`（新增） | ResendEmailSender / BrevoEmailSender + 重试 | 邮件 06 |
| `backend/heart/infra/email/__init__.py` | FallbackEmailSender + `get_email_sender()` 工厂 | 邮件 06 |
| `backend/heart/infra/email/sender.py` | `render_otp_email` 等 | 邮件 06 |
| `backend/heart/api/routes_auth.py` | OTP 请求/校验接线邮件发送 | 邮件 06 |
| `backend/heart/api/routes.py`（−64 行） | 疑似删除旧 dev_auth 桩 | 邮件 06 / 清理 |
| `backend/heart/core/config.py` | `email_provider/resend_api_key/brevo_api_key/email_from...` | 邮件 06 |
| `backend/tests/unit/test_email_sender.py`（新增） | 邮件发送单测 | 邮件 06 |
| `.env.example` | 补 EMAIL/EMBEDDING/OTP/JWT 段 | 配置 |
| `web/src/pages/RedeemPage.tsx` | 兑换页 | 前端 |
| `docs/MANUAL_TEST_GUIDE.md` `docs/TEST_RESULTS.md` | 文档 | 文档 |
| `docs/PROJECT_STARTUP_AND_DEPLOYMENT_EVALUATION.md`（未跟踪） | 部署评估 | 文档 |

> ✅ 结论：**模块 06 匿名邮件基本已实现**（不用从零开发），只差配置 + 域名验证（见 GO_LIVE_PLAN）。

**要做的**（按关注点拆分，不要一个大杂烩 PR）：

1. **确认无密钥泄露**：`git status` 确认没有 `.env` / `.env1` / 任何真实 key 被 `git add`。`.env1` 用户已删。
2. **PR-A `feat/anonymous-email-otp`**（base=main）：暂存邮件 06 相关文件（`infra/email/*`、`routes_auth.py`、`routes.py`、`config.py` 的 email 段、`test_email_sender.py`、`.env.example` 的 EMAIL 段）。
   - 补/确认单测：Resend 成功、429/5xx 重试、Fallback 主失败切备份、`get_email_sender()` 各 provider 分支。
   - `bash scripts/ci.sh` 全绿 → PR。
3. **PR-B `docs/sync-launch-status`**（base=main）：三份文档 + 本工单 + GO_LIVE_PLAN。
4. `web/src/pages/RedeemPage.tsx` 若与积分/兑换后端联调完成则并入对应功能 PR；否则单独 `feat/redeem-page`。
5. **用 `git add -p` 精确拆分**，别把 email 代码和文档塞进同一个 commit。

> ⚠️ 禁止把这一摊直接 `git commit` 到 main。当前 `HEAD` 已在 main，先 `git switch -c feat/anonymous-email-otp` 再选择性 add。

---

## P0-A — 默认 LLM 模型导致 out-of-box 崩溃（10 分钟，最先合）

**分支** `fix/default-llm-model`

**根因（已核验）**：默认主模型是 `deepseek-reasoner`，其流式响应会崩（`compose_stream_failed: 'Attempted to access streaming response content, without having called read()'`）。任何人按默认配置启动，核心聊天必崩。

**改动**：
- `backend/heart/core/config.py:43` `main_llm_model: str = "deepseek-reasoner"` → `"deepseek-chat"`
- `backend/heart/core/config.py:44` `cheap_llm_model` 统一为 `"deepseek-chat"`（上线前主链路完全避开 reasoner）
- `.env.example:25` `MAIN_LLM_MODEL=deepseek-reasoner` → `deepseek-chat`
- `backend/heart/infra/llm_providers/registry.py:139` `os.getenv("MAIN_LLM_MODEL", "deepseek-reasoner")` → 默认 `"deepseek-chat"`

**测试**：新增单测——默认配置经 fake provider 跑通 `compose_stream`，不抛异常。

**可选（单独 issue，非上线必须）**：真正修 reasoner 流式——错误来自 stream 未读时访问 `response.text/.json`；定位 `deepseek_pro.py` 的 `raise_for_status`/`reasoning_content` 处理，改成先 `await response.aread()` 再取 body。

**DoD**：`ci.sh` 绿；复制 `.env.example` 后默认能正常对话。

---

## P0-1 — 长期记忆召回错误（"年糕"答成"铜钱"）（诊断驱动，别盲改）

**分支** `fix/memory-recall-accuracy`

**背景**：语义召回基建已在 #91–#94 合并（写入/查询 embedding + 回填），但**实测仍复现错误召回**。这是"已接线但结果不准"，属定位 + 调优。**先诊断，让改动对准 trace 结果**，不要凭猜改权重。

**Step 1｜先排除 encoder-worker 没在写 L3（与 P1-2 联动）**
- 确认 `heart-encoder-worker` 真在消费队列：DB 查 `fact_nodes` 是否有 `has_pet 年糕` 且 `semantic_vector IS NOT NULL`、`recall_count`。
- 若 worker 根本没处理 → 这才是真根因，直接修 worker（见 P1-2），本条其余步骤再议。

**Step 2｜加检索 trace（debug flag，可留作长期可观测性）**
- 在 `backend/heart/ss02_memory/service.py` 的 `retrieve()` 和 `ss05_composer/service.py` 的 memory_block 组装处，打印：候选 `memory_id + 来源层(L2/L3/L4) + score_breakdown + 最终注入 prompt 的文本块`。
- 跑 45 轮复现（`docs/MANUAL_TEST_GUIDE.md` 测试 2），看"年糕"事实死在哪一环：

| 现象 | 定位 | 修复 |
|------|------|------|
| 年糕 L3 **没被检回** | query embedding 相关性差 / vector 未覆盖 L3 | 查询文本带"宠物/猫/名字"关键词；提高 semantic 权重；确认 `retriever/vector.py` 确实搜 L2+L3 |
| 检回但**没进 prompt** | composer 未注入或被 top_k 挤掉 | memory_block 把 L3 `object` 值原样注入；对 `confidence=1` 的身份/事实型 L3 提权或强制纳入 |
| 注入了但**模型编造** | prompt 无"忠于事实"约束 | prompt 加"优先使用已存事实，禁止编造用户信息（姓名/宠物名等）" |

**Step 3｜存量数据**（若目标 DB 未跑过）
- `python -m heart.scripts.backfill_embeddings --apply`（回填 embedding）
- `python -m heart.scripts.cleanup_dirty_l4 --apply`（清 L4 脏数据）

**测试**：新增 integration——注入"我养了一只猫叫年糕" + 44 条噪声 → `retrieve()` 结果 top_k 含该 L3 事实，`object == "年糕"`。

**DoD**：45 轮复现脚本能答对"年糕"；trace 显示该事实被检回并注入。**诚实预期：可能需 >1 轮迭代，但必须在上线前收敛。**

---

## P1-2 — encoder-worker "unhealthy" + 队列消费验证（0.5 天）

**分支** `fix/encoder-worker-health`

**根因（已核验，文档判断有误）**：`heart-encoder-worker` 显示 unhealthy 是**探针端口打错的误报**，不是功能故障——`backend/Dockerfile:41` 的 HEALTHCHECK 探 `http://localhost:8000/health/ready`，但 `docker-compose.yml:73` 该容器实际跑在 `--port 8080`，探针必然失败。

**改动**：
- 在 `docker-compose.yml` 给 `encoder-worker` 加**独立 healthcheck** 探 `:8080/health/ready`（覆盖 Dockerfile 那条错端口的），或统一端口。
- **同时验证**它真在消费 L2/L3 队列（与 P0-1 Step 1 合并做）——若发现根本没起 worker（只是起了个 8080 的 API 副本），需修 `HEART_WORKERS_ENABLED` 的实际生效逻辑。

**DoD**：`docker ps` 该容器 healthy；日志能看到消费队列 / 写 L3。

---

## P1-3 — Memory Extractor 每轮一次 LLM（成本/限流）（1 天）

**分支** `fix/extractor-cost-control`

**根因**：抽取 worker 按 per-turn 触发，45 条消息 ≈ 90 次 API 调用。高并发会 429，账户余额快速消耗。上线后是真实成本与稳定性风险。

**改动**：
- 确认 hint-gating 真的挡住闲聊（grep `queue_llm_encoding` 触发条件；闲聊应 0 抽取）。
- 加**去抖/批处理窗口**：累计 N 轮或 T 秒合并抽取一次，而非每轮。
- worker 层加并发限流 + 429 退避重试。
- 抽取模型已是 `deepseek-chat`（`memory_extractor_llm_model`，`config.py:84`），保持。

**测试**：N 条闲聊 → 0 次抽取调用；M 条有信息量 → 合批 ≤1 次调用。

**DoD**：`ci.sh` 绿；日志显示闲聊不触发 LLM。

---

## P0-B — 生产上线 infra（可与上面并行，独立 infra PR）

**分支** `feat/prod-deploy`（infra 变更独立 PR，不混业务）

面向：**海外 VPS + Docker + Caddy + Cloudflare DNS，服务大陆用户暂不备案**。前端 `services/api.ts` 用同源 `/api`、WS 用 `location.host`（`useWebSocket.ts:8`，https→wss），**因此生产必须同源反代**：Caddy 同时托管前端静态资源 + 反代 `/api`、`/api/chat/ws` 到后端。

**交付物**：
1. **`docker-compose.prod.yml`**：`api`(8000) + `encoder-worker`(8080) + `postgres`(pgvector) + `redis` + `caddy`(80/443)。api/worker 不再 `ports` 暴露公网，只在 `heart-network` 内网；只有 Caddy 对外。
2. **`Caddyfile`**：
   ```
   yuoyuo.app, www.yuoyuo.app {
     handle /api/* { reverse_proxy api:8000 }        # 含 WS，Caddy 默认支持 Upgrade
     handle { root * /srv/web; try_files {path} /index.html; file_server }
   }
   ```
   Caddy 自动向 Let's Encrypt 申请 TLS（.app 强制 HTTPS，Caddy 开箱即用）。
3. **前端静态构建**：`cd web && npm run build` → `web/dist` 挂进 Caddy 的 `/srv/web`（compose volume 或多阶段镜像）。
4. **生产环境变量**（VPS 上的 `.env`，不入库）：
   - `JWT_ALGORITHM=RS256` + `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`（PEM，见 GO_LIVE_PLAN 生成步骤）
   - `CORS_ALLOWED_ORIGINS=https://yuoyuo.app,https://www.yuoyuo.app`
   - `DEBUG=false` `LOG_LEVEL=WARNING`
   - `EMAIL_PROVIDER=resend`（或 `fallback`）+ `RESEND_API_KEY` + `EMAIL_FROM=noreply@mail.yuoyuo.app`
   - `DEEPSEEK_API_KEY` / `EMBEDDING_API_KEY`（可选）/ `OTP_PEPPER`（≥32 随机）
5. **迁移**：部署脚本含 `alembic upgrade heads`（多 head）。
6. **备份（P1，上线前）**：`pg_dump` 定时（cron/compose sidecar）+ 恢复 runbook 写进 `docs/`。

**注意（大陆访问）**：Cloudflare 橙云代理常被大陆干扰 → 建议 **DNS-only（灰云）** 直连 VPS，由 Caddy 直接终止 TLS；VPS 选 **香港/日本/新加坡** 且线路对大陆友好（CN2 GIA 之类），避免 EU 机房高延迟。详见 GO_LIVE_PLAN。

**DoD**：`docker compose -f docker-compose.prod.yml up -d` 起全栈；`curl https://yuoyuo.app/health/ready` 就绪；浏览器能登录/对话/出语音。

---

## 不修（P2/P3，附理由，勿浪费两周窗口）

| 项 | 级别 | 为什么不动 |
|----|------|-----------|
| FastAPI 版本锁 `<0.137` | P3 | **有意约束**：slowapi 0.1.10 与 fastapi≥0.137 不兼容，锁定在保护限流。升级会引入回归 |
| pyproject / requirements 双源 | P2 | 当前两者都能装，是漂移隐患非现患。上线后统一（用 pyproject 生成 requirements） |
| 日志收集 / 迁移自动化 / docker-compose 语法 | P2 | 运维硬化，上线后增量 |
| TEST_RESULTS 时间戳 / "40条"过时 | P3 | 纯文档，随 docs PR 顺手清 |
| `.env` 含真实密钥 | 非 bug | 已 gitignore=预期行为。唯一动作：轮换曾在明文出现过的 key |
| scene_context 缺失 / L2-L3 结构差异 / drifting 态 | P2/P3 | MEMORY_FIX_PLAN 已判定设计如此/非 bug |

---

## 建议排期（两周）

| 天 | 内容 |
|----|------|
| D1 | Step 0 收敛脏 main（邮件 06 PR + 文档 PR）+ P0-A 默认模型（合并） |
| D2–D3 | P0-B infra 骨架（compose.prod + Caddyfile + 前端构建）在测试域名跑通 |
| D3–D6 | P0-1 记忆召回诊断 + 修复（含 P1-2 worker 验证） |
| D6–D8 | P1-3 抽取成本 + P1 备份脚本 |
| D8–D10 | 联调：Cloudflare DNS + Resend 域名验证 + 真机全链路 |
| D10–D12 | 回归、压测、灰度、监控告警 |
| D12–D14 | 正式上线 + 观察 |

> 每个 PR：base=main、7 天内可合、单人 open PR ≤3、`ci.sh` 全绿、合并即删分支。
