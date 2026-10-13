# 语言版本目录：本地验收（2026-10-13）

本轮仅本地实现与验收，生产未部署。用户验收后另行执行发布流程。

## 展示规则

- 英语、越南语、孟加拉语各优先展示 50 个完整改编版本，后接 172 个未改编源角色。
- 中文展示原有 222 个角色。对应语言版本存在时，发现页不重复展示其中文源角色，也不混入其它语言版本。
- 语言优先级在推荐、新角色和搜索排序之后稳定应用；组内沿用原排序规则。
- 接口仍保留所有可访问角色 ID；发现页隐藏不影响收藏、既有聊天和直接链接，也不迁移聊天/共同记忆。
- 本地恢复库上一轮 666 个英/日/韩仅改名预览（launch_/intl_）仅从发现页隐藏，保留数据。
- 关系由 character_editions 表记录 source_id/locale，无需为新语言硬编码角色名单；未来版本仍须通过正常审核和可见性控制。

## 本地数据与边界

150 个版本来自 `/home/bai/yuoyuo/localization-top50-20261013/characters.json`，批次 `top50-20261013`，真实排名使用 2026-09-28 快照。

新增迁移 `081_character_editions` 已在本地 heart_review 和隔离测试库 heart_ui_test 应用。
导入保持 private/pending；没有伪造 human_reviewed、reviewer 或正式批准。
只有 LOCAL_CHARACTER_REVIEW 与 INTERNATIONAL_LOCALIZATION 同时开启、且满足已有开发环境和回环网络限制时，可访问注册为 local_preview 的 active/private/pending 版本。
导入器仅接受 loopback 的 heart_review/heart_ui_test；整批事务、源哈希校验、内容幂等校验、禁止覆盖不同内容。版本自身真实访问/播放量从零开始，不复制源角色指标。

后端启动前使用项目虚拟环境，从 backend 目录执行（DATABASE_URL 由本地配置加载，勿打印）：

```bash
python ../scripts/preview_character_editions.py /home/bai/yuoyuo/localization-top50-20261013/characters.json --batch top50-20261013
```

本地服务：`http://localhost:55173/character`，API `127.0.0.1:8000`。
导入的正文包和源用户快照留在 Git 外；代码提交不包含私有数据或凭据。

## 验证

- 全量 scripts/ci.sh：后端单测、lint/type、schema、前端构建及 84 个前端测试。
- 隔离 PostgreSQL + HTTP：导入幂等、源改变拒绝、内容改变拒绝、事务回滚、三语目录替换、私有待审状态保留、详情/访问计数/companion 可读。
- 原国际化/批次导入 E2E 14 项通过；新增导入 E2E 单独进程运行通过。合并运行触及登录接口 10 次/分钟限流，未修改产品限流配置。
- 本地实际包 150 个详情全部 HTTP 200；EN/VI/BN 各 50+172，ZH 222。
- Chromium/WebKit × 桌面1440/手机390，界面语言切换20次，推荐/新角色优先排序、封面标签同一行、无页面横溢出、无JS异常。
- 测试均无新增付费模型请求、无真实邮件、无生产修改。

浏览器验收记录、截图：Windows `F:/CODE/yuoyuo/reports/TOP50_LOCALIZATION_20261013/app-validation.json` 及 `app-*.png`。

## 发布前仍需执行

用户验收内容及本地交互后，再按发布手册制定生产导入/审核、备份及部署步骤。不能把 local_preview 开关搬到生产，也不能把本地数据库快照覆盖线上。
