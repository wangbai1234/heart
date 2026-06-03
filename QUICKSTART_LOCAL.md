# ⚡ 本地快速启动 — Heart 项目

> 5 分钟内从 0 启动一个完整的开发环境。

## 前置条件

- **Docker Desktop** (macOS/Windows) 或 **Docker + docker-compose** (Linux)
- **Python 3.11+**（检查：`python3.11 --version`）
- **Git** + 本仓库已克隆

## 一键启动

```bash
# 复制环境文件
cp .env.example .env

# 一键启动（docker + 依赖安装 + DB迁移 + 启动 API server）
bash scripts/local-startup.sh
```

等待 `Uvicorn running on http://127.0.0.1:8000` 出现后，打开浏览器访问：

### API 文档
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 快速测试

在另一个终端：

```bash
# 1. 健康检查
curl http://localhost:8000/health/live

# 2. 获取 JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_001","email":"test@example.com"}' | jq -r .access_token)

# 3. Echo bot 测试
curl -X POST http://localhost:8000/api/chat/echo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"character_id":"rin","messages":[{"role":"user","content":"你好"}]}'
```

## 各种模式

### 仅初始化环境（不启动 server）

```bash
bash scripts/local-startup.sh --setup
# 然后手动启动：
cd backend
python3.11 -m uvicorn heart.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 自动化测试

```bash
bash scripts/local-startup.sh --test
```

会自动跑：
- `/health/live`
- `/health/ready`
- `/api/auth/login` + `/api/auth/verify`
- `/api/chat/echo`

### 清理环境

```bash
bash scripts/local-startup.sh --clean
# 停止所有 Docker 容器，清除 Python 缓存
```

## 结构

```
运行中的 API 暴露：
├── GET  /health/live             心跳（Kubernetes 存活检查）
├── GET  /health/ready            就绪检查（含 DB/Redis 验证）
├── GET  /metrics                 Prometheus 指标
├── GET  /                        服务信息
└── /api/
    ├── POST /auth/login          鉴权：获取 JWT token
    ├── POST /auth/refresh        刷新 token
    ├── GET  /auth/verify         验证 token（需授权）
    └── POST /chat/echo           Echo bot 测试（需授权）

后台服务：
├── PostgreSQL 15 (port 5432)   数据库（user: heart / pass: heartdev）
├── Redis 7 (port 6379)          缓存 & 事件队列
└── uvicorn (port 8000)          FastAPI 开发服务器（--reload 模式）
```

## 其它命令

```bash
# 仅跑 unit tests（不启动 server）
bash scripts/ci.sh unit-tests

# 同时 lint + unit tests
bash scripts/ci.sh

# 查看 DB（需 psql，或用 Docker 进去）
docker-compose exec postgres psql -U heart -d heart

# 查看 Redis
docker-compose exec redis redis-cli

# 查看日志
docker-compose logs -f
```

## 故障排除

| 问题 | 排查 |
|------|------|
| `Connection refused:8000` | 检查 server 是否启动，或换个端口（脚本改为 8001） |
| `Database unavailable` | `docker-compose ps` 看 postgres 是否 healthy，或 `docker-compose logs postgres` |
| `jwt module not found` | 重跑 `pip install -e ".[dev]"` |
| `psql: command not found` | 正常——macOS 没自带 psql。用 `docker-compose exec postgres psql` 代替 |
| `alembic: Multiple heads` | 已在 scripts/ci.sh 中处理，但如果手动迁移遇到，用 `alembic upgrade heads` |
| Docker 占用端口 8000 | 改 Makefile 中的端口，或 `lsof -i :8000; kill -9 <PID>` |

## 当前可测试的功能

✅ **已实现 + HTTP 暴露**：
- 身份验证（JWT）
- Echo bot（Phase 0 回声机器人）
- 数据库连接
- Redis 连接
- Prometheus metrics
- 结构化日志

⏳ **已实现但未 HTTP 暴露**：
- SS01 Soul（drift detection, anchor injection）
- SS02 Memory（decay, reconstructor, forgetting affect）
- SS03 Emotion（repair, state machine）
- SS04-SS07（在 `feature/ss04-stage-engine` 分支上，但需合并 + Phase 7 工作才能上线）

对这些想做集成测试？切到 super-branch 并跑 unit 测试：

```bash
# 在当前分支
bash scripts/ci.sh unit-tests

# 或只测某个模块
cd backend
pytest tests/unit/ss01_soul -v
pytest tests/unit/ss02_memory -v
```

## 更多文档

- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — 当前开发状态
- [`README.md`](README.md) — 项目概览
- [`runtime_specs/`](runtime_specs/) — 系统设计文档
- [`engineering_execution/`](engineering_execution/) — 工程方法论

---

**反馈** → GitHub Issues 或 local git notes
