# 语言上线暂停与 Google 登录（2026-10-11）

用户后续面向孟加拉地区，本轮只暂停 EN/JA/KO；未新增孟加拉语或改动生产。

## 行为

- `INTERNATIONAL_LOCALIZATION=false` / `VITE_LOCALIZATION=false` 为默认。恢复中文界面、原有角色生成/开场/聊天提示词及全角动作括号；关闭 IP 初始语言、账号语言同步和语言选择。旧缓存及旧偏好不影响新输出。
- `INTERNATIONAL_MODE` / `VITE_INTERNATIONAL` 继续控制地理限制、国内商业接口关闭和移动尺寸壳，避免因暂停语言而意外重新开放国内服务或支付。
- 原 222 个审核角色继续展示；本地 `launch_*` / `intl_*` 改编预览暂隐藏。所有角色、付费生成成果与审计记录保留，没有数据库回滚/删除。
- 新角色恢复中文 locale；编辑已有角色保留原语言及其他名称版本。共同记忆查看/添加/纠错、聊天页记忆入口、搜索筛选、世界书保持；共同记忆演示增加中文示例。
- Google 登录与语言、市场开关解耦。完整登录页、注册页、登录/注册弹窗均提供 Google 按钮，继续执行成年确认和协议确认。凭据缺失时按钮禁用且明确提示未启用。
- Google 采用服务端 OIDC authorization-code + PKCE + nonce/state，校验签名、发行者、audience、已验证邮箱；浏览器绑定的票据单次兑换。前端只接受站内返回地址，清除 callback fragment 后再兑换。

## Google 配置状态

Google Cloud 项目 `impressive-tome-492608-j1` 中 `yuoyuo Web` 创建表单已完成。来源为 `https://yuoyuo.app` / `http://127.0.0.1:55173`，回调分别为来源加 `/api/auth/google/callback`。未点击创建：创建长期凭据需要浏览器执行时确认。未配置真实 Client ID/Secret，真实 Google 往返验收尚未完成。

后续密钥只保存到权限 600 的本地私密 `runtime.env`，不能进入版本库/日志。服务器变量为 `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_REDIRECT_URI`；`GOOGLE_FRONTEND_CALLBACK` 为来源加 `/auth/google/callback`。不要把后端回调与前端完成页混淆。正式域名配置不代表已部署。

## 本地验收

- 登录：http://127.0.0.1:55173/login
- 注册：http://127.0.0.1:55173/register
- 共同记忆演示：http://127.0.0.1:55173/_preview/shared-memories
- 实际记忆页：`/character/<character_id>/memories`，需相应用户登录。
- review 后端 :58000，前端 :55173。生产快照库 `heart_review` 不用于自动化测试清理；测试库为 `heart_ui_test`、Redis DB 3。

## 验证

新增回归覆盖缓存语言暂停、中文文案完整性、角色 locale/名称保留、Google 安全返回路径及独立启用。真实 uvicorn/Postgres/Redis 测试验证暂停后的中文 WebSocket 输出及消息落库，以及 Google 错误浏览器/重放拒绝、票据兑换、账号/身份/会话持久化和注册赠送幂等。Google 票据采用测试专用身份，签名校验另由单测覆盖，不冒充真实 Google 登录。

暂停路径 3 项 e2e 通过（3.46 秒）；保留的可选语言与共同记忆路径 7 项 e2e 通过（4.49 秒）。测试使用假模型，无付费模型调用。完整 `bash scripts/ci.sh` 通过：后端 2,003 通过 / 34 跳过，前端 77 通过，lint、类型检查、schema、构建均通过。额外使用 `VITE_INTERNATIONAL=true VITE_LOCALIZATION=false` 构建通过。本地目录实测 222 个原审核角色、0 个三语改编预览；原数据没有删除。
