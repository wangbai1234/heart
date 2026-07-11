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
- [ ] 创建特性分支：`git checkout -b feat/xxx`
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

## 🌿 分支与 PR 治理（硬性约束，违反必须立即停下报告）

### PR 生命周期
- **任何 PR open 超过 7 天必须二选一**：合并 或 关闭。不允许长期挂起。
- **任何时刻，单人 open PR 数 ≤ 3**。超过时禁止开新 PR，必须先收敛旧 PR。
- **PR 必须有明确 base**：默认 base = `main`，仅在显式 stacked PR 工作流时才允许 base ≠ main，且必须在 PR 描述里画依赖图。

### 跨分支 fix 反模式
- **禁止把同一个 fix 横向复制到 N 个功能分支**。
- 正确做法：fix 先合 main，其他功能分支 `git rebase main` 自动拿到修复。
- 如果发现自己正在创建第二个 `xxx-fix` 分支去修同样的事，**立即停下，改走 main hotfix 流程**。

### 分支命名与清理
- 命名规范：`feat/<topic>`、`fix/<topic>`、`docs/<topic>`、`chore/<topic>`。统一 `feat/`，禁止 `feature/` 与 `feat/` 混用。
- **合并即删除**：PR merge 后立即删除 head 分支（本地 + 远程）。GitHub 设置勾选 "Automatically delete head branches"。
- **每周一次** `git remote prune origin` 清理远端死链。

### "事实主干" 反模式
- 禁止把某 feature 分支变成"事实主干"（持续累积 10+ 提交、包含多个不相关功能、被当作开发基线）。
- 一旦发现某分支已偏离原始 scope，必须**立即拆分**为多个聚焦 PR，或合并到 main 后从 main 开新分支。

### 多远端
- 单一权威远端 = `origin`（GitHub）。
- Gitee 等镜像远端**只读 / 单向 push**，不允许在镜像端开发或产生独立提交。

### 平行实现禁令
- **禁止在不同分支上对同一子系统做平行实现**。SS04/SS07/Safety 之所以曾出现 3 套不收敛版本，根因是不同 session 未核查现状就开新分支重写。
- 开始任何 SSxx 模块工作前，**必须先 `git ls-tree -r <候选基线分支> -- backend/heart/ssXX_*`** 看现有实现，禁止"凭印象觉得这是空的"。
- 如发现需要重写已有实现，**PR 描述必须写明"为什么放弃既有版本"**，否则 reviewer 必须 reject。

### Agent 行为铁律
- 跨分支代码状态判断**必须基于 `git show` / `git ls-tree` 实际输出**，禁止基于 commit message / PR title 推断模块是否存在。
- 违反此条产出的报告/方案默认作废。

### 提交前自检（每次 push 前必须问自己）
1. 这个 PR 7 天内能合并吗？不能就不要开。
2. base 是 main 吗？不是的话有没有写依赖说明？
3. 这个修复该走 main hotfix 而非挂到 feature 分支吗？
4. 我现在 open 的 PR 是不是 ≥ 3 个了？
5. 我有没有用 `git ls-tree` 验证过现有实现，而不是凭印象？

---

## 🧯 集成验证分档（替换原"红就停"硬规则）

CI / lint / type-check 报错时按以下四档判定，不同档位不同处置：

| 档 | 类型 | 处置 |
|---|------|------|
| **A** | 功能性错误（pytest 红、import 报错、运行时崩溃） | 立即停下，必须修复或回退。禁止 noqa / config 放宽。 |
| **B** | 集成引入的**新增** lint / type 错误（baseline diff 证明 baseline 无） | 等同档 A，禁止静默。 |
| **C** | 从源分支带入的**既有**债务（baseline diff 证明既有） | 不阻塞，走"债务登记仪式"（见下）。 |
| **D** | 领域约定与 lint rule 冲突（数学符号 `L/N/K` 等） | 局部 `# noqa: <rule> — <领域理由>`，每处一行注释。 |

### 债务登记仪式（档 C 专用，三步缺一不可）
1. **`pyproject.toml` 用 `per-file-ignores` 登记**，配 issue 编号和 sunset date 注释。
2. **开 tracking issue**：列出每条债务的文件 / 行号 / 修复建议 / sunset。
3. **集成 PR body 加 `## Imported Tech Debt` 段落**，引用 issue。

### 禁止
- 全局放宽 ruff / mypy 规则换取单次集成通过（配置降级是单向门，per-file-ignore 是双向门——能改就选双向门）。
- 无理由 `# noqa`（noqa 仅用于档 D）。
- 把档 A/B 错误伪装成档 C 静默掉。
- `per-file-ignores` 或 `[mypy-...]` ignore 不带 issue 链接 + sunset 注释 → **reviewer 必须 reject**。

---

## 🗄️ DB 迁移与环境同步铁律（2026-07 血泪教训）

### 背景（为什么加这一节）
上一轮批 A 修复"合并到 main 却仍报同样的 bug"，根因不是代码错，而是 **dev DB schema 落后代码 4 个迁移版本**，`chat_messages` 缺 `sequence_id/turn_id` 列 → 后端 `except Exception` 静默吞掉 `KeyError` → 用户看到"空气泡"以为修复失败。花了 2 小时才定位。

### 硬性要求（违反必须立即停下）

1. **每次 `git pull` 或切分支后**，必须先跑：
   ```bash
   cd backend && alembic current && alembic heads
   ```
   若 `current` ≠ `heads`，立即执行 `alembic upgrade head`（多 head 时逐个 upgrade），**未升级不得启动 dev server**。

2. **切分支前必先停 dev server**（`Ctrl-C`）。原因：`uvicorn --reload` 只重载 Python 文件，**不重连 DB pool / 不重导 SQLAlchemy metadata**，切到旧分支代码 + 新 schema（或反过来）会撒谎式跑通。切完分支再起服务。

3. **新迁移的 revision 名超过 32 字符**时，第一步 SQL 必须是：
   ```sql
   ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(80);
   ```
   否则 `alembic upgrade` 会因主键长度限制静默截断或报错。

4. **多 head Alembic DAG（分支合流）** 必须显式：
   ```bash
   alembic upgrade <head_a>
   alembic upgrade <head_b>
   ```
   禁止 `alembic upgrade head` 盲跑（会报 "Multiple head revisions"，且部分 CI 环境会跳过静默）。合并两分支的 merge migration 必须在同 PR 内落纸。

5. **禁止 `except Exception:` 静默吞异常**。DB / schema / KeyError 类必须：
   ```python
   except Exception:
       logger.exception("op_failed", extra={"...": ...})
       raise  # 或走 structured error 到前端
   ```
   把错误吞成"看着正常"是欺骗用户，比 crash 更糟。

6. **生产启动时的 migration drift 告警不可绕过**。`heart/infra/migration_check.py` 会 diff disk heads vs `alembic_version`，任何 `migration_drift_detected` ERROR **禁止用 config 屏蔽**，必须当场停下修复。

7. **添加/修改列后必须重启后端服务**（哪怕 `--reload` 在跑）。原因：SQLAlchemy 的 reflected metadata 只在启动时抓，`--reload` 拿不到新列。

### 迁移文件规范

- 新迁移必须 `down_revision` 指向单一 head（避免制造无意的多 head DAG）。
- 迁移里 `CREATE TABLE / ALTER TABLE / INSERT` 必须用 `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` 兜底幂等（dev/prod 重跑不炸）。
- 数据回填（如 seed 音色、backfill 列默认值）**必须放在独立 UPDATE**，不与 DDL 混在同一句，否则 rollback 粒度太粗。
- migration 内禁止 `import heart.xxx` 业务代码（业务变了 migration 会突然跑不起来），只用 `sqlalchemy.text` + raw SQL。

### 提交前 DB 自检（每次 push 前必须问自己）
1. 我的 dev DB `alembic current` 是不是 `alembic heads` 相同？
2. 新迁移 revision 名 ≤ 32 字符？> 32 有没有先 ALTER `alembic_version`？
3. 新迁移会不会造成多 head？造成了有没有加 merge migration？
4. 修改了列，我的 dev server 有没有**完全重启**（不是 --reload）？
5. 我改动过的路径里有没有 `except Exception:` 静默吞异常？

---

## ⚠️ 禁止事项

- ❌ 直接在 main 分支提交（必须用 PR）
- ❌ 提交 `.env` 或密钥文件
- ❌ 不运行测试就 push
- ❌ 删除用户数据相关的表（逻辑删除）
- ❌ 修改已部署的 soul_specs（必须版本化）
- ❌ CI 配置变更 PR 混入业务变更（CI 修复必须独立 PR）
- ❌ **`except Exception:` 不 log 不 re-raise 直接 pass**（欺骗式静默）
- ❌ **dev server 运行中切分支**（hot-reload + 旧 schema = 撒谎式绿灯）
- ❌ **未跑 `alembic current` 就 push 涉及 DB 的 PR**

---

## 📞 需要帮助时

如果遇到问题，我会：
1. 自动修复能修复的（lint errors）
2. 创建 git commit 记录问题
3. 告诉你问题在哪里，需要你人工决策时才问

---

**最后更新**: 2026-07-11
**版本**: 2.1.0（新增 DB 迁移与环境同步铁律）
