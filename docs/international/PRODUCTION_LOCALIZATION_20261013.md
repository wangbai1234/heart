# 2.0.36 国际化正式发布（2026-10-13）

项目所有者明确授权“可以进行部署了”。本次发布 zh/en/vi/bn，日语和韩语仍停用；中文 UI、Google 登录、共同记忆和地区访问策略保留。

## 发布内容

- 完整英语、越南语、孟加拉语 UI、原生提示词与账号语言偏好。
- 三语各 50 个完整角色版本，按选定语言优先；其它源角色随后展示。排名使用用户批准的 2026-09-28 真实访问快照。
- 原中文源角色和历史聊天/收藏 ID 不覆盖；每个版本使用独立角色 ID，访问统计从零开始。
- 手机与电脑卡片文字预算、控件边界、单行封面标签修复，保留用户缩放及字号设置。

## 发布证据与边界

`config/releases/localization-20261013.json` 绑定本次所有者发布授权、资源版本、三语资源哈希和 150 条正式包的整体哈希。包保存在 Git 外，不提交业务角色正文。母语专项审核、法律专项审核和真实 Chrome/手机真机验收尚未完成；这次发布授权不被记录为这些审核已经通过。

严格专项审核入口 `check_locale_resources.py --release` 保留原规则。本次使用单独的所有者授权发布检查：

```bash
backend/.venv/bin/python scripts/check_authorized_release.py <production-characters.json> \
  --receipt config/releases/localization-20261013.json
```

它检查完整资源、占位符、资源哈希、正式包哈希、语言条数、生产媒体路径和真实授权记录。新注册语言仍默认 draft；必须明确发布与 enable allowlist，不能自动上线新语言。

正式导入 `scripts/publish_character_editions.py --apply` 使用独立生产入口；本地 `import_preview` 的隔离数据库限制保留。导入在一个事务内执行，绑定生产源实时哈希，拒绝重复 ID/语言配对、源变更、包变更或已导入内容变更。正式版本 public/active/approved，`local_preview=false`；approved 表示所有者批准上线，不声称母语专家审核。

生产只读比较的 50 个源角色正文和 spec 均与本地快照一致。zhou_jian 的 draft.creation_mode 仅本地 workshop / 生产 quick 有差异；记录生产实时源哈希，完整新版本保持公开发布所需的 workshop 模式，源角色不更改。

自动浏览器布局 64 组通过。新增正式导入通过真实 PostgreSQL/HTTP 验证：公开目录、同语言优先、私有预览不误上线、源变更拒绝、第二条错误导致整体回滚、重复执行不创建重复数据。模型使用 fake，不调用付费模型或真实邮件。

## 生产步骤与回滚

发布代码必须经 PR 合并 main。生产先备份数据库、自定义 dump 目录、私有环境、前端和当前应用镜像，再 fast-forward main。

使用 `docker-compose.prod.yml` + `docker-compose.international.yml` 构建 api/encoder-worker，运行 `alembic upgrade heads` 到 081，事务导入精确正式包，设置 `INTERNATIONAL_LOCALIZATION=true`、`LOCALIZATION_ENABLED_LOCALES=zh,en,vi,bn`、`LOCAL_CHARACTER_REVIEW=false`，完整冷启。

前端构建 `VITE_INTERNATIONAL=true VITE_LOCALIZATION=true`，版本 2.0.36。核验公网 version、SW、静态资源、应用语言资源版本、150 个正式版本及封面/详情、Google enabled 和既有地域拒绝探针。不得启用生产调试登录或本地预览白名单。

回滚优先关闭 INTERNATIONAL_LOCALIZATION、收缩 allowlist，恢复旧应用镜像及旧静态文件；保留 080/081、新用户数据和新角色。必要时按 `batch_id=top50-release-20261013` 逻辑转 private/pending 隐藏版本，不删除角色/聊天，不用旧数据库 dump 覆盖生产。

## 已上线 2.0.36（2026-10-13，优先于下方历史记录）

用户明确授权发布，PR [#369](https://github.com/wangbai1234/heart/pull/369) 已合并；应用发布提交为 `5d60bfc97e3c2777dc4b09b7d7c6b0fa45670fa8`。前端 2.0.36、数据库 `081_character_editions`。必须使用基础生产 Compose + 国际 overlay；前端 `VITE_INTERNATIONAL=true VITE_LOCALIZATION=true`，后端 `INTERNATIONAL_LOCALIZATION=true`、`LOCALIZATION_ENABLED_LOCALES=zh,en,vi,bn`、`LOCAL_CHARACTER_REVIEW=false`。国际地区限制保持启用，日/韩仍停用，中文、Google 登录和共同记忆保留。

英语/越南语/孟加拉语各 50 个完整角色版本正式导入 `top50-release-20261013`，public/active/approved、local_preview=false。各语言目录前 50 条为对应版本，其后源角色；生产英文/越南文/孟加拉文可见各 193 条，中文 192 条。此计数是发布时快照，不是固定业务约束。原中文源角色、聊天和收藏不覆盖，未导入本地整库或本地筛选可见性。

发布核验：全部服务运行且健康；Alembic current=head；150 个详情、50 张封面成功；应用资源版本 `3dac5a7569dc330bc6e9`，四种语言启用；Google config enabled；内部允许地区 200、CN/缺来源凭据 403。公网健康、version、SW、manifest 200，发布元数据与产物逐字节一致且 no-cache/DYNAMIC；首页引用当前 JS/CSS，首页仅额外包含 Cloudflare 现有分析脚本，应用静态文件校验一致。未修改 DNS、Google Cloud、支付或地区限制。

验证证据：2097 后端单测、84 前端单测、16 个真实 PostgreSQL/HTTP fake-model E2E，lint/type/schema/build 全绿，GitHub CI success；64 组 Chromium/WebKit 布局验证。未在本次部署调用付费模型/真实邮件。实际 Chrome/手机真机、母语专项和法律专项审核未完成；所有者发布授权没有被记为这些审核通过。

回滚备份：`/home/deploy/heart/backups/pre-localization-20261013T110039Z`，包含验证过目录的 1.6G custom DB dump、旧私有环境、前端、130M 应用镜像和校验和，目录 700、私有文件 600。正式包和构建日志：`backups/localization-release-20261013`。常规回滚保留新数据与 080/081 表，关闭语言发布、恢复旧应用/静态资源；必要时按批次逻辑隐藏新版本，不删除角色或用旧数据库覆盖线上。

详细发布授权、导入规则与边界见 [2.0.36 发布记录](PRODUCTION_LOCALIZATION_20261013.md)。

