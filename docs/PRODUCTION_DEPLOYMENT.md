# yuoyuo 生产部署操作手册

## 已上线 2.0.36（2026-10-13，优先于下方历史记录）

用户明确授权发布，PR [#369](https://github.com/wangbai1234/heart/pull/369) 已合并；应用发布提交为 `5d60bfc97e3c2777dc4b09b7d7c6b0fa45670fa8`。前端 2.0.36、数据库 `081_character_editions`。必须使用基础生产 Compose + 国际 overlay；前端 `VITE_INTERNATIONAL=true VITE_LOCALIZATION=true`，后端 `INTERNATIONAL_LOCALIZATION=true`、`LOCALIZATION_ENABLED_LOCALES=zh,en,vi,bn`、`LOCAL_CHARACTER_REVIEW=false`。国际地区限制保持启用，日/韩仍停用，中文、Google 登录和共同记忆保留。

英语/越南语/孟加拉语各 50 个完整角色版本正式导入 `top50-release-20261013`，public/active/approved、local_preview=false。各语言目录前 50 条为对应版本，其后源角色；生产英文/越南文/孟加拉文可见各 193 条，中文 192 条。此计数是发布时快照，不是固定业务约束。原中文源角色、聊天和收藏不覆盖，未导入本地整库或本地筛选可见性。

发布核验：全部服务运行且健康；Alembic current=head；150 个详情、50 张封面成功；应用资源版本 `3dac5a7569dc330bc6e9`，四种语言启用；Google config enabled；内部允许地区 200、CN/缺来源凭据 403。公网健康、version、SW、manifest 200，发布元数据与产物逐字节一致且 no-cache/DYNAMIC；首页引用当前 JS/CSS，首页仅额外包含 Cloudflare 现有分析脚本，应用静态文件校验一致。未修改 DNS、Google Cloud、支付或地区限制。

验证证据：2097 后端单测、84 前端单测、16 个真实 PostgreSQL/HTTP fake-model E2E，lint/type/schema/build 全绿，GitHub CI success；64 组 Chromium/WebKit 布局验证。未在本次部署调用付费模型/真实邮件。实际 Chrome/手机真机、母语专项和法律专项审核未完成；所有者发布授权没有被记为这些审核通过。

回滚备份：`/home/deploy/heart/backups/pre-localization-20261013T110039Z`，包含验证过目录的 1.6G custom DB dump、旧私有环境、前端、130M 应用镜像和校验和，目录 700、私有文件 600。正式包和构建日志：`backups/localization-release-20261013`。常规回滚保留新数据与 080/081 表，关闭语言发布、恢复旧应用/静态资源；必要时按批次逻辑隐藏新版本，不删除角色或用旧数据库覆盖线上。

详细发布授权、导入规则与边界见 [2.0.36 发布记录](international/PRODUCTION_LOCALIZATION_20261013.md)。


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
