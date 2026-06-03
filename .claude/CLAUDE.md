# Heart Project - Claude Code Configuration

## 项目信息
- **名称**: Heart - AI Companion
- **GitHub**: https://github.com/wangbai1234/heart.git
- **技术栈**: Python 3.11 + FastAPI + PostgreSQL + Redis + Kubernetes
- **当前工作目录**: /Users/wanglixun/heart

---

## 📖 每次 Session 必须执行

无论你是什么模型、何时开始，只要是一个**新 session**，必须先做以下事情（无需等用户提醒）：

### 1. 读取以下文件（按顺序）
- [ ] `docs/PROJECT_STATUS.md` — 当前 phase、blocker、下一步
- [ ] `AGENTS.md` — 项目级规范
- [ ] `.claude/CLAUDE.md` — 本文件（行为规则）

### 2. 工作流
修改代码后，按以下步骤**自动执行**（无需询问）：
- [ ] 运行 `bash scripts/ci.sh`（lint + 测试）
- [ ] `git add + git commit`
- [ ] `git push`
- [ ] `gh pr create`

> ⚠️ 不运行测试就 push 是禁止行为（见底部 ❌ 禁止事项）

---

## 🤖 行为规则 - 直接执行权限

### ✅ 我应该直接做的事（无需询问）：

1. **文件操作**
   - 读取、编辑、创建项目内的所有文件
   - 创建新的模块、测试、配置文件
   - 删除无用的临时文件

2. **Git 操作**
   - 提交代码（git add + git commit）
   - 推送代码到 GitHub（git push）
   - 创建和管理分支（git checkout -b）
   - 查看 git status、git log、git diff

3. **GitHub 操作**
   - 创建 Pull Request（gh pr create）
   - 查看 PR 状态、评论、检查
   - 创建 Issues（如果需要追踪 bug）

4. **本地开发操作**
   - 运行测试（pytest）
   - 运行 linter（ruff、mypy）
   - 构建 Docker 镜像
   - 验证配置文件

### ❌ 需要你确认的事：

1. 推送到 main 分支（force push）
2. 删除重要分支
3. 修改关键基础设施配置（Kubernetes、数据库）
4. 涉及金钱/成本的决策（AWS 资源等）

---

## 📋 工作流程

### 当你给我任务时：
1. ✅ 我直接读取你的代码
2. ✅ 我直接修改文件
3. ✅ 我直接提交到 Git
4. ✅ 我直接创建 PR 到 GitHub
5. ✅ 我报告进度和结果

### 无需等待你的确认（除非涉及上面的 ❌ 项）

---

## 🏗️ 项目结构

```
heart/
├── backend/
│   ├── heart/           # 主代码
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── migrations/      # Alembic 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── config/              # 配置文件（YAML）
├── soul_specs/          # Soul Spec 定义（YAML）
├── infra/kubernetes/    # Kubernetes 部署文件
├── runtime_specs/       # 完整的系统规范文档
├── .github/workflows/   # CI/CD 管道
└── .claude/CLAUDE.md    # 本文件
```

---

## 🚀 标准操作清单

### 创建新功能时：
- [ ] 创建特性分支：`git checkout -b feature/xxx`
- [ ] 编写代码
- [ ] 编写测试
- [ ] 运行 lint 和测试
- [ ] 提交：`git commit -m "feat: description"`
- [ ] 推送：`git push -u origin feature/xxx`
- [ ] 创建 PR：`gh pr create --title "..." --body "..."`

### 修复 bug 时：
- [ ] 创建 bug 分支：`git checkout -b fix/xxx`
- [ ] 修复代码
- [ ] 添加测试验证
- [ ] 提交：`git commit -m "fix: description"`
- [ ] 推送和创建 PR

### 部署到 Kubernetes 时：
- 确保所有 YAML 文件验证通过
- CI 必须全绿（lint + tests + build）
- 创建 PR 供 review

---

## 📝 提交信息规范

```
<type>: <description>

<body>

<footer>
```

**Type**:
- feat: 新功能
- fix: 修复
- refactor: 重构
- test: 测试相关
- ci: CI/CD 相关
- docs: 文档
- chore: 构建、依赖等

**示例**:
```
feat: add memory consolidation worker

- Implement overnight consolidation job
- Add LLM-based fact extraction
- Include Prometheus metrics

Closes #123
```

---

## 🔧 常用命令

```bash
# 查看状态
git status
git log --oneline -10

# 本地测试
cd backend
pytest tests/unit -v
pytest tests/integration -v

# Lint 检查
ruff check heart/
mypy heart/

# 构建 Docker
docker build -f backend/Dockerfile -t heart/backend:test .
```

---

## ⚠️ 禁止事项

- ❌ 直接在 main 分支提交（必须用 PR）
- ❌ 提交 `.env` 或密钥文件
- ❌ 不运行测试就 push
- ❌ 删除用户数据相关的表（逻辑删除）
- ❌ 修改已部署的 soul_specs（必须版本化）
- ❌ CI 配置变更 PR 混入业务变更（CI 修复必须独立 PR）

---

## 📞 需要帮助时

如果遇到问题，我会：
1. 自动修复能修复的（lint errors）
2. 创建 git commit 记录问题
3. 告诉你问题在哪里，需要你人工决策时才问

---

**最后更新**: 2026-06-03
**版本**: 2.0.0
