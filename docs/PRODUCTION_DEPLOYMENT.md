# yuoyuo 生产部署操作手册

> 本文是生产发布的唯一入口文档。服务器：`deploy@103.69.128.125:22`，目录：`/home/deploy/heart`。

## 当前生产状态（2026-10-11）

用户明确授权在旧 HostHatch 实例发布。PR #366 合并提交 `5ad64e1` 已上线，生产仓库为干净 `main`。数据库已从 076 升级到 `079_google_identities`；前端版本为 2.0.34，构建使用 `VITE_INTERNATIONAL=true VITE_LOCALIZATION=false`。

当前运行必须带国际 overlay：

```bash
cd /home/deploy/heart
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.international.yml ps
```

- `.env.prod` 中 `INTERNATIONAL_MODE=true`、`INTERNATIONAL_GEO_ENFORCED=true`、`INTERNATIONAL_LOCALIZATION=false`；生产密钥保持权限 600。
- Google 回调为 `https://yuoyuo.app/api/auth/google/callback`，前端回调为 `https://yuoyuo.app/auth/google/callback`。Google Cloud 应用已正式发布，仅请求 openid/email/profile。
- 生产数据卷原地保留，没有导入旧的本地生产快照或本地角色改编稿。
- 升级前备份：`backups/pre-international-20261011T085302Z/`，包含数据库自定义格式 dump、`.env.prod`、旧 Caddyfile、前端 tar 和旧提交号。SHA256 校验和 `pg_restore --list` 检查通过；目录权限 700，数据库和密钥文件 600。
- 旧静态目录保留为 `web/dist-before-international-20261011`，旧提交 `504e925`。
- 健康检查均 200；Google config 为 enabled=true；start 303 跳转 Google，真实回调、PKCE S256、Secure cookie 已核对。内部 CN/缺失来源凭据探针及直接源站请求返回 403，JP 探针 200。尚未使用真实大陆终端验证，也不等于识别用户国籍。

### 当前发布验收

已精确清除 Cloudflare 的 `/sw.js`、`/version.json`、`/manifest.webmanifest` 缓存，并创建启用的 `Bypass PWA release metadata` 规则（ID `e17b0af09080485c8ecd270ea926ad65`），仅对这三个路径旁路 CDN 和浏览器缓存。公网 `/sw.js` 与当前构建文件逐字节一致，响应 `Cache-Control: no-cache` / `CF-Cache-Status: DYNAMIC`。后续发布无需等待 4 小时 CDN TTL。浏览器已打开的旧页面仍需通过服务工作线程更新流程或重新打开页面更新。

用户已亲自验证生产环境 Google 登录正常；登录与注册按钮和真实 Google 授权页也已浏览器验收。代理补丁恢复 www → apex 的 308 跳转，并将 OAuth code/state 与 WebSocket token 一同从访问日志脱敏。

### 后续更新与回滚

2.0.35 修复手机输入聚焦时字号被小字工具类覆盖（移动端输入最低 16px，保留手动缩放），全局隐藏滚动条外观但保留滚动，并恢复 `/rewards`、`/rewards/content` 及邀请、抽奖、奖励券、站内佣金兑换、活动提交与审核接口。这些福利功能不再受国际支付开关控制；爱发电 webhook 仍关闭。无数据库迁移。回归覆盖真实 HTTP/数据库抽奖发奖、全部福利面板读取，以及暂停语言推广和 Google 身份流程。

以下历史 `release-prod.sh` / `deploy-prod.sh` 命令尚未自动加载国际 overlay，不要直接用来重建当前生产，否则会丢失国际代理配置。后续手动更新须先备份、合并 PR、生产快进 main，再用两份 Compose 文件构建、迁移并启动。前端必须显式使用上述两个 Vite 开关。

回滚应用时保留新增数据库表及新用户写入，禁止直接恢复旧 dump 覆盖生产。旧代码可配合旧 `.env.prod`、旧静态目录及基础 Caddy/Compose 恢复；执行前确认回滚到国内访问逻辑是否仍符合用户当前意图。备份中的 dump 为灾难恢复材料，不是常规应用回滚步骤。

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
