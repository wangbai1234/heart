# Gitee Go UI 流水线配置指南

**日期**: 2026-05-24
**版本**: 2.0（替代 GITEE_GO_SETUP.md 中的 YAML 方案）
**触发因素**: 发现 `.gitee/workflows/ci.yml` 未被 Gitee Go 读取（GitHub Actions 语法不兼容）

---

## 0. TL;DR

```
Gitee Go ≠ GitHub Actions
- GitHub Actions YAML 不被识别
- Gitee Go 使用 UI 配置 + 插件系统
- 我们的解决方案: shell entry script (scripts/ci.sh) + UI shell step
```

---

## 1. 问题诊断

### 1.1 之前的错误（已纠正）

我们最初将 `.github/workflows/ci.yml` 复制为 `.gitee/workflows/ci.yml`，假设 Gitee Go 兼容 GitHub Actions 语法。**这是错误的**。

实际证据（来自 BranchPipeline 失败日志）:
```
plugins/python/1.0/step.sh          ← Gitee 默认 Python 插件
pip3 install -r requirements.txt    ← 在根目录寻找（错误位置）
python3 ./main.py                   ← 寻找根目录的 main.py（不存在）
```

`.gitee/workflows/ci.yml` 完全没有被读取，UI 流水线使用了 Gitee 内置的默认 Python 模板。

### 1.2 当前方案

```
.gitee/workflows/ci.yml      → REFERENCE ONLY（不被 Gitee 执行）
scripts/ci.sh                → 实际 CI 入口（被 Gitee UI 流水线调用）
Gitee Go UI Pipelines        → 调用 scripts/ci.sh <stage>
```

---

## 2. Gitee Go UI 流水线配置（核心）

### 2.1 重新配置 BranchPipeline

**目标**: 在每个非 main 分支推送时运行 lint + unit-tests + schema-validation

**操作步骤**:

1. 登录 Gitee → 进入仓库 `https://gitee.com/wangbai1234/heart`
2. 顶部菜单点击 **流水线**（或 **Gitee Go**）
3. 找到 **BranchPipeline**，点击 **编辑**
4. **删除现有的 Python 步骤**（这就是失败的来源）
5. 添加新步骤：
   - 类型: **执行 Shell**（或 **自定义命令**）
   - 步骤名: `CI - Lint + Unit Tests + Schema Validation`
   - Shell 内容:
     ```bash
     bash scripts/ci.sh lint
     bash scripts/ci.sh unit-tests
     bash scripts/ci.sh schema-validation
     ```
   - 镜像（如果可配置）: `python:3.11-slim`

6. 保存

**触发条件**:
- 分支模式: `feat/*`, `fix/*`, `refactor/*`, `chore/*`, `docs/*`
- 触发事件: Push

---

### 2.2 重新配置 PRPipeline

**目标**: 在 PR 创建/更新时运行完整 CI（lint + unit + integration + schema + build）

**操作步骤**:

1. Gitee → 流水线 → **PRPipeline** → 编辑
2. 删除现有所有默认步骤
3. 添加以下步骤（按顺序）:

   **Step 1: Lint**
   ```bash
   bash scripts/ci.sh lint
   ```

   **Step 2: Unit Tests**
   ```bash
   bash scripts/ci.sh unit-tests
   ```

   **Step 3: Integration Tests**（需要 services + secrets）
   ```bash
   # 需要在 UI 上配置 services:
   #   - PostgreSQL 15 (with pgvector)
   #   - Redis 7
   # 需要在 UI 上配置环境变量:
   #   DATABASE_URL=postgresql://heart_test:test_password@postgres:5432/heart_test
   #   REDIS_URL=redis://redis:6379/0
   #   DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}  # 已配置为通用变量
   #   DEEPSEEK_BASE_URL=https://api.deepseek.com
   #   MAIN_LLM_MODEL=deepseek-reasoner
   #   CHEAP_LLM_MODEL=deepseek-chat

   bash scripts/ci.sh integration-tests
   ```

   **Step 4: Schema Validation**
   ```bash
   bash scripts/ci.sh schema-validation
   ```

   **Step 5: Docker Build**
   ```bash
   bash scripts/ci.sh build-docker
   ```

4. 保存

**触发条件**:
- 事件: Pull Request opened, synchronized
- 目标分支: `main`, `develop`

---

### 2.3 重新配置 MasterPipeline

**目标**: 在合并到 main/develop 时运行完整 CI + 可选的部署步骤

**操作步骤**:

1. Gitee → 流水线 → **MasterPipeline** → 编辑
2. 删除现有所有默认步骤
3. 添加以下步骤:

   **Step 1: Full CI**
   ```bash
   bash scripts/ci.sh all
   ```

   **Step 2: Integration Tests**（配置 services + secrets 同 PRPipeline）
   ```bash
   bash scripts/ci.sh integration-tests
   ```

   **Step 3: Docker Build**
   ```bash
   bash scripts/ci.sh build-docker
   ```

   **Step 4 (可选): Push images to Gitee Registry**
   ```bash
   # 仅在配置了 Gitee Container Registry 时启用
   docker tag heart/backend:test gitee-registry.example.com/wangbai1234/heart-backend:${COMMIT_SHA}
   docker push gitee-registry.example.com/wangbai1234/heart-backend:${COMMIT_SHA}
   ```

4. 保存

**触发条件**:
- 事件: Push
- 分支: `main`, `develop`

---

## 3. Services 配置（仅 PRPipeline + MasterPipeline 需要）

### 3.1 PostgreSQL (with pgvector)

在 Gitee Go UI 上配置服务（如果支持）:
- 镜像: `pgvector/pgvector:pg15`
- 端口: `5432`
- 环境变量:
  - `POSTGRES_USER=heart_test`
  - `POSTGRES_PASSWORD=test_password`
  - `POSTGRES_DB=heart_test`

**如果 Gitee Go 不支持 services**:

在 `scripts/ci.sh` 的 `stage_integration_tests` 函数开头添加 Docker compose 启动逻辑：
```bash
docker run -d --name postgres-ci \
    -e POSTGRES_USER=heart_test \
    -e POSTGRES_PASSWORD=test_password \
    -e POSTGRES_DB=heart_test \
    -p 5432:5432 \
    pgvector/pgvector:pg15

docker run -d --name redis-ci \
    -p 6379:6379 \
    redis:7-alpine
```

### 3.2 Redis

- 镜像: `redis:7-alpine`
- 端口: `6379`

---

## 4. 环境变量与 Secrets

### 4.1 全局变量（已配置）

- `DEEPSEEK_API_KEY` ✅ 已设置为通用变量

### 4.2 流水线级变量（需要添加）

在每个 Pipeline 的环境变量配置中添加:

| 变量名 | 值 | 用途 |
|--------|---|------|
| `PYTHON_VERSION` | `3.11` | Python 版本 |
| `DATABASE_URL` | `postgresql://heart_test:test_password@localhost:5432/heart_test` | 集成测试 DB |
| `REDIS_URL` | `redis://localhost:6379/0` | 集成测试 Redis |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | LLM endpoint |
| `MAIN_LLM_MODEL` | `deepseek-reasoner` | 主 LLM |
| `CHEAP_LLM_MODEL` | `deepseek-chat` | 廉价 LLM |

---

## 5. 验证步骤

### 5.1 测试 BranchPipeline

```bash
# 创建测试分支
git checkout -b test/gitee-go-fix
git commit --allow-empty -m "test: trigger BranchPipeline"
git push gitee test/gitee-go-fix

# 然后去 Gitee UI 查看 BranchPipeline 运行
# 预期: lint + unit-tests + schema-validation 全部 ✓
```

### 5.2 测试 PRPipeline

```bash
# 在 Gitee 上创建 PR
# test/gitee-go-fix → main
# 预期: 完整 CI 跑通（包括 integration tests）
```

### 5.3 测试 MasterPipeline

```bash
# 合并 PR 后自动触发
# 预期: 完整 CI + Docker build 全部 ✓
```

---

## 6. 故障排查

### 6.1 scripts/ci.sh: Permission denied

**原因**: 脚本没有执行权限

**修复**:
```bash
# 在 Shell step 开头添加
chmod +x scripts/ci.sh
bash scripts/ci.sh <stage>
```

### 6.2 找不到 requirements.txt

**原因**: 当前目录不是仓库根目录

**修复**: `scripts/ci.sh` 内部已用 `REPO_ROOT` 计算绝对路径，不应该再有此问题。如果仍发生，确认 Gitee Go 的工作目录设置为仓库根目录（默认）。

### 6.3 DEEPSEEK_API_KEY not set

**症状**: integration-tests 报错 `DEEPSEEK_API_KEY is required`

**修复**:
- 确认全局变量 `DEEPSEEK_API_KEY` 已配置
- 确认在 PRPipeline/MasterPipeline 的环境变量中**引用**了此变量

### 6.4 Docker build 失败

**症状**: `docker: command not found` 或权限错误

**修复**:
- 确认 Gitee Go runner 支持 Docker in Docker
- 或者在 Shell step 配置中选择支持 Docker 的镜像

### 6.5 集成测试连接 DB 失败

**症状**: `connection refused on localhost:5432`

**修复**:
- 确认 PostgreSQL service 已在 Pipeline UI 配置
- 或者使用本指南 §3.1 的 fallback 方案（脚本内 docker run）

---

## 7. 与现有文档的关系

| 文档 | 状态 | 用途 |
|------|------|------|
| `.gitee/workflows/ci.yml` | ⚠️ Reference only | GitHub Actions 兼容性参考，**Gitee 不会读** |
| `scripts/ci.sh` | ✅ 实际入口 | 被 Gitee UI 流水线调用 |
| `docs/GITEE_GO_SETUP.md` | ⚠️ 部分过时 | YAML 方案已废弃，secrets 配置仍有效 |
| `docs/GITEE_GO_UI_SETUP.md` | ✅ 本文档 | UI 流水线配置权威指南 |
| `docs/GITEE_PUSH_GUIDE.md` | ✅ 仍有效 | Git 认证配置 |

---

## 8. 未来扩展（Phase 7+）

Phase 7 §1.2/§1.4 实施时会新增以下 stages，只需在 `scripts/ci.sh` 中添加函数：

```bash
# 未来添加
stage_governance_lint() {
    # Phase 7 Top 10 #10 - 检查 SafetyAgent wiring, CarePathHandler, etc.
}

stage_voice_drift() {
    # Phase 7 §1.4 - 跑 voice drift regression
}

stage_tier_c_smoke() {
    # Phase 7 §1.2 - LLM live smoke tests
}
```

然后在对应的 Gitee Go UI Pipeline 中添加一个新 Shell step:
```bash
bash scripts/ci.sh governance-lint
bash scripts/ci.sh voice-drift
```

**无需重新配置整个流水线** → ✅ Future scalability 保留。

---

## 9. 检查清单（给 HUMAN）

立即（今天）:
```
□ 在 Gitee UI 重新配置 BranchPipeline（§2.1）
□ 在 Gitee UI 重新配置 PRPipeline（§2.2）
□ 在 Gitee UI 重新配置 MasterPipeline（§2.3）
□ 配置 services（PostgreSQL + Redis，§3）
□ 添加环境变量（§4.2）
□ 推送测试分支验证 BranchPipeline（§5.1）
```

本周内:
```
□ 创建测试 PR 验证 PRPipeline
□ 合并测试 PR 验证 MasterPipeline
□ 所有 6 个 stages 在 Gitee Go 上跑通
□ 更新 docs/PHASE_7_READINESS_CHECKLIST.md Blocker #1 为 ✅ 完全验证
```

---

## 10. 历史教训

**Lesson Learned**: 平台迁移前必须验证语法兼容性，不能假设。

下次迁移 CI/CD 平台时：
1. 先在小型测试仓库验证 YAML 是否被读取
2. 阅读平台官方文档，不要假设 GitHub Actions 兼容
3. 如发现不兼容，立即设计 shell-based abstraction layer（如 scripts/ci.sh）

**记入 session_log.md 的 Regret 字段**: 应为 3，原因 = 假设 Gitee Go 兼容 GitHub Actions YAML，导致一次返工。

---

**版本**: 2.0
**最后更新**: 2026-05-24
**作者**: CC-Opus-4.7（Incident Response Mode）
**Status**: Active — 这是 Gitee Go CI 的权威配置文档
