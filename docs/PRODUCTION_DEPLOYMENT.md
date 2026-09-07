# yuoyuo 生产部署操作手册

> 本文是生产发布的唯一入口文档。服务器：`deploy@103.69.128.125:22`，目录：`/home/deploy/heart`。

## 当前阻塞（2026-09-07）

新服务器已在原目录安全恢复 Git 元数据，但历史发布曾直接 rsync/上传源码，线上代码并不等于
GitHub `origin/main`。为避免覆盖线上修复，服务器目前停在本地恢复分支：

```text
production-snapshot/103-69-128-125-20260907-033454
2fe1ce2ddc9d4fa6835e33007ca3ae51b971b772
```

关键配置备份位于服务器：

```text
/home/deploy/heart/.deploy-backups/git-init-20260907-033230
```

在生产差异归并并推送 GitHub `main` 之前，后端 Git 部署会主动停止。不要强制 checkout/reset，
也不要删除上述快照分支。当前容器仍使用初始化前的相同文件，服务未因 Git 恢复而重启。

## 标准发布命令（Mac 仓库根目录）

```bash
bash scripts/release-prod.sh --status
bash scripts/release-prod.sh --frontend
bash scripts/release-prod.sh --backend
bash scripts/release-prod.sh --full
bash scripts/release-prod.sh --logs api
```

前端静态目录由 Caddy 直接挂载，rsync 后无需重启 Caddy。后端发布必须来自已提交并合并的
`origin/main`；脚本会拒绝生产非 `main`、受跟踪文件有漂移或非快进更新。

## 每次发布前的规则

1. 代码通过 PR 合并到 `main`，不要直接提交或推送 main。
2. 后端改动先运行相应测试；涉及真实 HTTP/数据库路径时运行 Tier E E2E。
3. `.env.prod`、数据库卷、MinIO 卷、`covers_src/`、`scenarios_src/` 不进入 Git。
4. 数据库迁移固定执行 `alembic upgrade heads`（复数）。
5. 发布后必须确认容器健康及 `https://yuoyuo.app/health/live`。

## 生产快照归并步骤

```bash
git fetch ssh://deploy@103.69.128.125/home/deploy/heart \
  production-snapshot/103-69-128-125-20260907-033454:refs/remotes/production/recovery-20260907
git diff origin/main..production/recovery-20260907 -- backend web scripts docker-compose.prod.yml Caddyfile
```

将仍需要的线上改动整理到 `codex/` 功能分支，经测试和 PR 合入 main。确认 main 已包含生产必需
改动后，选择维护窗口，在服务器执行：

```bash
cd /home/deploy/heart
git fetch origin main
git switch main
git merge --ff-only origin/main
bash scripts/deploy-prod.sh --update-backend
```

切换前必须保留生产快照和 `.env.prod` 备份，并确认 `git status --short --untracked-files=no` 为空。
