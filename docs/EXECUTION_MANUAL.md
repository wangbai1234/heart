# Heart（对外名 yuoyuo）项目执行手册

> 单一权威操作文档：如何启动、配置、部署、手机端测试，以及当前系统状态。
> 状态类信息以本文件与 `docs/PROJECT_STATUS.md` 为准；旧的阶段性文档（TEST_RESULTS / MEMORY_FIX_PLAN 等）为历史记录。
> **最后更新：2026-07-06**

---

## 1. 架构与技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 后端 | Python 3.11 + FastAPI | ASGI app = `heart.api.main:app`，端口 **8000** |
| 前端 | React 19 + Vite + Tailwind | `web/`，dev 端口 **5173**，`/api` 代理到 :8000 |
| 数据库 | PostgreSQL 15 + **pgvector** | :5432，语义召回向量存储 |
| 缓存 | Redis 7 | :6379，L1 工作记忆 / 缓存 |
| LLM | DeepSeek（OpenAI 兼容） | 对话生成、事实抽取 |
| Embedding | 托管 bge-m3（SiliconFlow，OpenAI 兼容） | 语义召回，1024 维 |

**手机端 = 手机浏览器打开响应式 Web 应用**。仓库内**没有**原生 App / React Native / Capacitor，
也**尚未**做 PWA（无 manifest / service worker），因此当前**不能"下载安装到桌面/主屏"**（见 §9）。

---

## 2. 环境准备（一次性）

- Python 3.11、Node 20+、Docker（跑 Postgres+Redis）。
- 后端依赖：`cd backend && pip install -e ".[dev]"`（或 `make install`）。
- 前端依赖：`cd web && npm install`。

---

## 3. 环境变量（`.env` 在仓库根，已 gitignore，切勿提交）

从 `.env.example` 复制：`cp .env.example .env`，然后按下表填写。

### 3.1 必填（不填后端起不来或核心功能不可用）

| 变量 | 说明 |
|------|------|
| `JWT_ALGORITHM` | 默认 `RS256`。**RS256 必须同时提供 `JWT_PRIVATE_KEY` + `JWT_PUBLIC_KEY`（PEM）**，否则启动即 `RuntimeError`。若图省事可设 `HS256` + `JWT_SECRET_KEY`（**≥32 字符**，不能是占位默认值）。 |
| `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` | RS256 时必填（PEM）。生成：`openssl genpkey -algorithm RSA -out priv.pem -pkeyopt rsa_keygen_bits:2048 && openssl rsa -pubout -in priv.pem -out pub.pem`。 |
| `DEEPSEEK_API_KEY` | 真实对话必需。`DEEPSEEK_BASE_URL=https://api.deepseek.com`。 |
| `DATABASE_URL` | 默认 `postgresql+asyncpg://heart:heartdev@localhost:5432/heart`（与 docker-compose 一致）。 |
| `REDIS_URL` | 默认 `redis://localhost:6379/0`。 |
| `OTP_PEPPER` | 登录 OTP 用，替换占位默认值。 |

### 3.2 语义召回（可选，不填则退回 recency/identity，系统正常不崩）

| 变量 | 默认 | 说明 |
|------|------|------|
| `EMBEDDING_API_KEY` | 空 | 空 = 语义召回禁用。填入托管 embedding key 即启用。 |
| `EMBEDDING_BASE_URL` | `https://api.siliconflow.cn/v1` | OpenAI 兼容 embeddings endpoint。 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 1024 维模型。 |
| `EMBEDDING_DIMENSIONS` | `1024` | **必须与 DB `vector()` 列一致**（迁移 017）。 |

### 3.3 手机端测试相关

| 变量 | 说明 |
|------|------|
| `CORS_ALLOWED_ORIGINS` | 逗号分隔。**必须包含手机加载 Web 的源**（如 `http://192.168.x.x:5173`），否则跨域被拦。同源反代则无需。默认回退 `http://localhost:3000`。 |

### 3.4 可选（留空不影响手机聊天测试）

邮件 SMTP（`SMTP_*`/`EMAIL_*`）、积分/支付（`AFDIAN_*`/`STRIPE_*`）、对象存储（`S3_*`）、
语音 TTS（`MINIMAX_*`/`MIMO_*`/`ENABLE_VOICE`）、可观测性（`SENTRY_DSN`/`PROMETHEUS_PORT`）、
推送（`FCM_*`/`APNS_*`）。

---

## 4. 本地启动（标准路径）

```bash
# 1) 起依赖（Postgres+pgvector、Redis）
make docker-up            # 等价 docker-compose up -d postgres redis

# 2) 装后端依赖
cd backend && pip install -e ".[dev]"

# 3) 建表 / 迁移（多 head 用 heads 复数）
cd backend && alembic upgrade heads

# 4) 起后端（:8000）
cd backend && uvicorn heart.api.main:app --reload --host 0.0.0.0 --port 8000
#   或一键：bash scripts/local-startup.sh   /   make dev

# 5) 起前端（:5173，/api 代理到 :8000）
cd web && npm install && npm run dev
```

健康检查：`curl http://localhost:8000/health/ready`（检查 DB + Redis）。API 文档：`http://localhost:8000/api/docs`。

---

## 5. 手机端测试（同一局域网）

前端把 API 写死为相对路径 `/api`，WebSocket 用 `location.host`，所以**手机加载的源站必须能把
`/api` 和 `/api/chat/ws` 转到后端 :8000**。两种方式：

- **开发调试（最快）**：`cd web && npm run dev -- --host 0.0.0.0`，手机访问 `http://<电脑局域网IP>:5173`。
  同时把 `http://<电脑局域网IP>:5173` 加入 `.env` 的 `CORS_ALLOWED_ORIGINS`。
- **接近生产**：`npm run build` 生成 `web/dist`，用 Nginx/Caddy 等反代：静态站 + `/api`(含 ws) → :8000（同源，无需改 CORS）。

> 注意：Vite 默认只绑 localhost，手机连不上，必须加 `--host 0.0.0.0`（或走反代）。

---

## 6. 数据库迁移

- 命令（在 `backend/`）：`alembic upgrade heads`（**heads 复数**，仓库存在多 head 情况）。
- 当前最新迁移：**`017_embed_dim_1024`**（`semantic_vector` 768→1024，对齐 bge-m3）。
- 迁移读 `DATABASE_URL` 环境变量（`migrations/env.py`），`alembic.ini` 里的 url 是占位。

---

## 7. 启用语义召回（增量步骤）

语义召回代码已完整实现（PR #91–#94），**默认受 `EMBEDDING_API_KEY` 门控**：不配则退回 recency/identity。

启用三步：
1. `.env` 填 `EMBEDDING_API_KEY`（+ 确认 `EMBEDDING_DIMENSIONS=1024`）。
2. `cd backend && alembic upgrade heads`（含 017）。
3. 回填存量向量：`python3 -m heart.scripts.backfill_embeddings --apply --batch 64`。

配套一次性清理（修 P0-3 脏 L4 "什么吗"）：`python3 -m heart.scripts.cleanup_dirty_l4 --apply`。

> ✅ **本地 docker 环境已执行完毕（2026-07-06）**：017 已应用；572 条 L2 + 196 条 L3 已全部回填
> 1024 维向量；2 条脏 L4 已逻辑降级；实测检索 `strategies_used` 已含 `vector`，语义召回生效。
> 其他环境（staging/prod）需各自重复上述步骤。

---

## 8. 当前系统状态（记忆系统）

`docs/MEMORY_FIX_PLAN.md` 的 PR1–PR4 **已全部实现并合并 main**（PR #87–#94）：

- 召回回写 `recall_count`（此前从不触发）✅
- L2 冷路径用真实情绪 VAD + 多信号 importance（此前硬编码）✅
- 短期上下文窗口 **40→50** ✅
- Resolver 拦截疑问句污染 L4（"什么吗"）+ 清理脚本 ✅
- `EmotionEvent` 持久化（此前从不落库）✅
- **语义召回端到端打通**：EmbeddingService + 写/查向量 + 768→1024 迁移 + 回填 ✅（门控于 key）

**仍保留（设计如此/非 bug，见 fix plan P2）**：scene_context 缺失（低优先）、L2/L3 结构性差异、
`drifting` 关系态。

---

## 9. 响应式 & "下载到桌面"（PWA）现状

- **响应式自适应：支持**。`web/index.html` 有 `viewport` meta，UI 为 mobile-first（TabBar/BottomSheet/
  ChatInboxPage 等），手机浏览器打开可随屏幕自适应。
- **下载安装到桌面/主屏（PWA）：当前不支持**。`web/` 无 `manifest.webmanifest`、无 service worker、
  index.html 未引 manifest。要实现"添加到主屏/安装为应用"，需新增：① Web App Manifest（name/icons/
  `start_url`/`display:standalone`）② service worker（可安装 + 离线）③ index.html 引入并 HTTPS 提供。
  这是一项独立待开发功能（不在本轮记忆修复范围）。

---

## 10. 运维脚本清单（`backend/heart/scripts/`）

| 脚本 | 用途 | 安全默认 |
|------|------|----------|
| `backfill_embeddings.py` | 回填 L2/L3 语义向量 | dry-run，`--apply` 落库 |
| `cleanup_dirty_l4.py` | 逻辑降级脏 L4 身份记忆（M-1 不物删） | dry-run，`--apply` 落库 |
| `seed_demo.py` | 播种演示数据 | — |
| `gen_redemption_codes.py` | 生成兑换码 | — |

---

## 11. 测试 / CI

- 本地全套：`bash scripts/ci.sh`（lint + unit + schema + frontend）。
- 分档单项：`bash scripts/ci.sh lint` / `unit-tests` / `schema-validation` / `frontend`。
- 前端 CI 用 `npm install`（fresh 解析平台原生二进制，见 `docs/PROJECT_STATUS.md` 里 rolldown 说明）。

---

## 12. 常见问题

- **后端启动即报 `RuntimeError: RS256 requires ...`**：JWT 未配密钥。填 `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`
  或改 HS256 + 强 `JWT_SECRET_KEY`（§3.1）。
- **`alembic: Multiple heads`**：用 `alembic upgrade heads`（复数）。
- **手机打不开前端**：Vite 默认绑 localhost → 加 `--host 0.0.0.0`；并把手机源加入 `CORS_ALLOWED_ORIGINS`。
- **语义召回没效果**：检查 `EMBEDDING_API_KEY` 是否配置、是否跑过回填脚本、`EMBEDDING_DIMENSIONS` 是否 = 1024。
- **对话无回复**：`DEEPSEEK_API_KEY` 未配。
