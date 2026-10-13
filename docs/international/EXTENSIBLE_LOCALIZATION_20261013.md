# 英语、越南语、孟加拉语国际化实施与扩展手册

更新：2026-10-13。本地实施已应用 WSL 活动仓库 `/home/bai/yuoyuo/heart`，分支 `feat/extensible-localization`，基于生产 2.0.35 的提交 `413ff49888343e92f98cf8187851d4c98af40438`。本文覆盖旧检查点中的“仅暂存、未执行”状态。

## 1. 交付状态与边界

- 已实现 en / vi / bn 的注册、界面资源、账号偏好、角色字段、生成语言指令和发布检查。中文保留，日语/韩语仍注册但未开放推广。
- 六语均为 1,172 / 1,172 个资源键，空值、未知键、占位符错误均为零。越南语、孟加拉语为完整助手译稿，不等于母语质量通过。
- 默认有效语言仅中文。其他语言的注册表状态为 `draft`，推广为 `paused`；本地预览必须显式开启。没有上线新语言、修改生产或推送远端。
- 旧角色没有自动翻译或批量导入。新离线任务流程不调用模型。本轮未发送真实邮件、未调用付费业务模型，未把角色导入 `heart_review`。
- 生产访问限制、支付、Google Cloud 配置不在本次变更范围。中文 UI、Google 登录、共同记忆、原布局均保留。

## 2. 上次操作审计及本次对应修复

历史审计发现 222 个源角色、666 个英日韩版本处于待所有者审核阶段；记录有 1,103 次调用、4,727,038 reported tokens，此统计不是账单。旧产物有大量 backstory、soul、speech_samples/catchphrases 缺项；详细分母和抽样口径见 Windows `reports/I18N_AUDIT_AND_ROADMAP_20261012.md`，不能把缺项计数视为独立角色数。

| 上次问题 | 本次机制 |
|---|---|
| 固定英日韩，多个语言一次返回，失败难重试 | 注册表作为语言来源；每个源角色 × 目标语言独立 task_id |
| 字段缺失、超长后静默裁剪 | 完整 CharacterDraft 校验；源有值字段和嵌套列表不得遗漏；超长直接失败 |
| 名字/人设漂移 | 本地化名称映射；身份、年龄、性别、评分和配置等受保护字段不可改变；语义忠实由真人审核 |
| 审核前导入，难追溯 | 审核绑定源、资源和候选 SHA256；仅本地审核库、private/pending 副本；不覆盖原角色 |
| 批次中途失败留半成品 | 单事务、源行锁、导入 ledger、幂等检查；源或候选变化拒绝复用旧审核 |
| 设备语言被账号/迟到请求覆盖 | 显式设备选择独立存储，账号切换版本号、共享加载、保存锁和 patch 合并 |
| 上线开关与资源不一致 | 前后端 registry/resource 版本对齐；不一致时不开放语言写入；发布检查要求真实审核记录 |
| 非中文语音误调用/计费 | HTTP/WS 在 provider 和计费前检查；当前只验证中文语音，外语普通聊天保留文字 |

旧 `backend/scripts/localize_review_catalog.py` 的 generate/apply CLI 已禁用；其 export 仍是历史 222 源专用，不能当作未来通用导出器。不要再运行 Windows `implementation-source/apply.py` 覆盖当前仓库；该暂存区已过时。一次性实施脚本多数非幂等，不能重跑。

## 3. 架构与运行行为

`config/locales.json` 定义 code、aliases、nativeName、promptName、specLocale、formatLocale、direction、fallback、status 和 promotion。`scripts/generate_locales.py` 生成后端 `heart/locales.py` 和前端 `i18n/registry.ts`。资源版本包含注册表、legacy 和所有语言资源；生成器使用当前 Python 环境内的固定版本 Ruff，缺依赖时明确失败。

后端 `enabled_locales()` 默认返回 zh。开启本地化后仍需 `LOCALIZATION_ENABLED_LOCALES` 显式允许；draft 只允许本地角色审核模式。注册表 default=en 表示国际化协商的默认值，不表示英文默认开放。浏览器 Accept-Language 优先，IP 仅作回退；繁中不错误映射为简中，q=0 不选中。

设备选择使用 localStorage `yuoyuo-explicit-locale`。账号偏好不改写该键；退出恢复设备选择。回复模式为 auto / interface / character / fixed。暂停的存量语言偏好保留，实际运行回退；新写未开放语言被拒绝。

角色支持 vi/bn 字段和通用 `localized` 名称映射。聊天、剧情、主动消息和仪式消息接入语言指令。剧情仍使用 `【旁白】`、`**角色名**`、`（动作）` 协议，解析不随界面语言改变。来源中文内容不会因缺译被清空。

前端根据注册表自动加载 JSON，日期按语言格式化。孟加拉语使用项目内 Noto Sans Bengali 字体和 OFL 许可证，避免依赖设备安装该字体。新增语言的语音不会因为改环境变量就自动宣称支持；需要独立 provider/语言验收与能力代码变更。

## 4. 本地复现验证

所有 Linux 命令在 WSL Ubuntu-24.04 活动仓库执行。不要将业务 `.env` 内容或凭据输出到日志。

```bash
cd /home/bai/yuoyuo/heart
source backend/.venv/bin/activate

# 固定测试模式，避免本地 .env 的国际支付策略影响基线单测。
INTERNATIONAL_MODE=false INTERNATIONAL_LOCALIZATION=false \
VITE_INTERNATIONAL=false VITE_LOCALIZATION=false bash scripts/ci.sh

bash scripts/check-international.sh
python scripts/generate_locales.py --check
python scripts/check_locale_resources.py --report /tmp/locale-resource-report.json

# 目前必须失败：三语尚未有真实审核证据。
python scripts/check_locale_resources.py --release en vi bn
```

最终完整 CI：后端 **2,036 passed / 34 skipped**，前端 **80 passed**；Ruff、mypy（272 个源文件）、TypeScript、Vite、schema/资源检查通过。国际化开启构建及前端 80 项、国际后端 38 项通过。CI 对 mypy 原本为非阻断，但本轮日志确认无错误。

独立 `heart_ui_test` + Redis DB 13 + fake LLM 的真实 HTTP/WS/数据库测试：启用态 **14 passed**、暂停态 **3 passed**。覆盖三语注册、vi/bn 角色创建/编辑/聊天/语音拒绝、共同记忆权限和纠错、批次事务/幂等/stale 拒绝、080 迁移回填/重复执行/降级保留、Google PKCE/重放和本地票据交换。Google 和模型为测试替身，不证明真实外部 provider 可用。

证据日志：`/tmp/i18n-ci-verified.log`、`/tmp/i18n-international-final.log`、`/tmp/i18n-active-e2e.log`、`/tmp/i18n-paused-e2e.log`、`/tmp/i18n-release-gate.log`。发布检查按预期拒绝三语草稿与缺少审核记录；这不是把失败掩盖为通过。

## 5. 角色离线任务与审核导入

### 源快照

仅从本地审核库只读导出获准的源角色；使用 `heart.localization.batch.SOURCE_SQL` 对每个选定 ID 查询，把返回 mapping 转成 JSON 数组 `sources.json`。每行包含 `id, owner_user_id, cover_url, visibility, status, review_status, tags, draft, spec`。日期/UUID 使用字符串。不要导出用户邮件或聊天。源 draft 不完整时，先重建并审核，不能把缺字段当作翻译后的空值。

这一步目前没有新增通用 export CLI；历史 export 命令有固定 222 条和旧审核表约束。任何新的导出脚本都必须校验 loopback + `heart_review`，并保留不可变快照。

### 建任务和检查候选

```bash
cd /home/bai/yuoyuo/heart/backend
# /tmp/locale-batch-v1/sources.json 由前一步生成，勿覆盖已有不同版本。
PYTHONPATH=. .venv/bin/python scripts/localization_batch.py plan \
  --sources /tmp/locale-batch-v1/sources.json --locales en vi bn \
  --folder /tmp/locale-batch-v1

PYTHONPATH=. .venv/bin/python scripts/localization_batch.py validate \
  --folder /tmp/locale-batch-v1
```

计划文件为 `tasks.json`；每项候选保存为 `<task_id>.json`：

```json
{
  "task_id": "从 tasks.json 复制的完整值",
  "draft": {"说明": "此处须为完整 CharacterDraft，不能使用这个示意对象"},
  "editorial_notes": "译者记录术语、文化改写和待核验项"
}
```

candidate 的 `draft.locale` 与 `draft.response_language` 必须为目标 code；对应显示名必须有值。保留所有有值的源文案字段、嵌套对象键和列表成员。不能用删除背景、缩短样例列表或截断来解决 schema 错误。结构检查不证明翻译正确或完整传达含义，真人仍须逐字段比对。

### 审核记录

真人审核后才可加入 `review`，字段如下：

```json
{
  "task_id": "与任务一致",
  "source_sha256": "与任务一致",
  "resource_version": "与任务一致",
  "candidate_sha256": "使用 batch.digest(candidate 去掉 review) 计算",
  "approved": true,
  "reviewer": "实际审核人标识",
  "reviewed_at": "实际带时区 ISO 8601 时间",
  "checks": {
    "field_fidelity": true,
    "name_consistency": true,
    "safety": true,
    "output_format": true,
    "rights": true
  }
}
```

以上为格式说明，不能复制为审批事实；测试中的 `SYNTHETIC TEST ONLY` 证据不得用于实际内容。源、资源或候选变化后重新建任务/审核。合并重试只按 task_id 处理，不能覆盖已导入的不同候选。

```bash
# 仅当现有安全配置确实指向 loopback heart_review 时执行。
PYTHONPATH=. .venv/bin/python scripts/localization_batch.py import-review \
  --folder /tmp/locale-batch-v1
```

导入器再次查询并锁住实时源行、检查 hash；同一事务创建 `loc_<locale>_<hash>` 的 private/pending 副本与 ledger。重复相同导入幂等，冲突拒绝，批次中任何失败整体回滚。导入不是发布；公开展示须走后续既有内容审核。本轮只在隔离测试库验证过该机制。

## 6. 今后新增一种语言

1. 明确目标地区和 code/alias。语言不等于国籍或支付地区；不要借语言开关改变地域/支付策略。
2. 在 `config/locales.json` 新增 draft/paused 项，填写原生名称、提示名称、日期地区、方向和回退。新 script/RTL 语言需要额外布局、字体及方向审核，不能只加 JSON。
3. 建立 `web/src/i18n/locales/<code>.json`，对齐英文资源键，保留插值变量。补全后端 `REPLIES`、主动消息和邮件等独立模板；这些仍需人工扩展，注册表不是所有语言内容的自动生成器。
4. 运行生成器和资源检查；后端生成的 Locale 类型及前端选择器随注册表更新，固定展示字段以通用 localized map 扩展。
5. 用独立源 × 语言任务翻译角色，审核每个候选；禁止直接复用旧英日韩合并生成器。
6. 执行完整 CI、开启/暂停态 E2E、目标语言浏览器布局及真机核心流程；验证拒绝/关怀、剧情协议、重试、账号切换、共同记忆和禁用语音行为。
7. 审核最终 UI 文案、法律/运营实体、真实模型输出及真机布局，记录对应资源 hash。先标 reviewed，生成版本并重测，最后按下面发布门槛开放。

## 7. 发布门槛、启用与回退

UI 审核证据放在 `config/locale-reviews/<code>.json`：`resourceSha256` 必须等于资源报告中的该语言 hash，含真实 `reviewer`、`reviewedAt`、`decision: approved`，`checks` 中 `nativeLanguage/legal/coreFlows/modelOutput/mobileLayout` 均为真实通过。脚本只能检查字段与绑定，不能验证审核人的身份或实际审查行为，需代码评审保护这些记录。

当前阻塞项：vi/bn 母语审核；英文与目标国家法律/年龄政策审核（译稿仍含待确认运营实体/邮箱及历史日韩条款）；真实 LLM 的语言忠实、人物一致性和安全/危机响应；真实邮件可达性；手机键盘/字体/触控真机验收；角色审核与公开上线选择。词条齐全和 fake LLM 测试不能代替这些结果。ASR/TTS 暂仅中文，三语可先以文字能力验收发布。

未来获准部署时：先备份并测试 080 兼容迁移，部署同一 registry/resource 版本的前后端；运行 `--release` 通过后，再配置 `INTERNATIONAL_LOCALIZATION=true`、`LOCALIZATION_ENABLED_LOCALES=zh,en,vi,bn`，前端构建 `VITE_INTERNATIONAL=true VITE_LOCALIZATION=true`。只开放实际审核通过的子集，允许按 en → vi → bn 分批。生产不可开启 `LOCAL_CHARACTER_REVIEW` 来绕过草稿门槛。`promotion` 字段仅记录状态，推广开关/活动需要另行决策。

回退优先收缩 `LOCALIZATION_ENABLED_LOCALES` 或关闭国际化开关，保留用户已存偏好和扩展数据。080 的 downgrade 有意不缩窄字段、不删除 response_mode；Alembic 降级标记不代表旧程序可兼容。已有 vi/bn 数据时不能直接切回只认识旧三语的二进制，需保留兼容版本或前向修复。版本不匹配时客户端关闭语言写入，避免向错误版本写新枚举。

## 8. 审批服务恢复

历史日志确认 503 时调用 `gpt-5.6-luna`。已设置 Windows `.codex/config.toml` 的 `model_catalog_json`，完整目录 11 项 `auto_review_model_override` 均为 `gpt-5.6-sol`，并同步 CC Switch 当前提供商配置；主模型仍为 `gpt-6.1-sol`，备份保留。重启后配置仍正确，WSL 执行恢复。本轮 approval=never 未触发真实审批请求，所以不宣称 Sol 服务端审批调用已经验证成功。


## 9. 最终浏览器验收与补充

Chromium / WebKit × en / vi / bn × 390×844 / 1440×1000 × 登录 / 注册 / 隐私页，共 **36 组通过**。检查实际路径、document lang/dir、横向溢出、页面错误、隐私正文和孟加拉字体加载；并人工查看 vi/bn 手机注册页、桌面登录和隐私页截图，修复 Google 禁用提示漏译和词句/链接粘连。当前完整资源数因此为 **1,172**。截图和机器结果在 Windows `reports/i18n-visual-20261013/`。

这些浏览器测试使用本地 API fixtures，只验证布局与本地化渲染；业务闭环由前述 17 个真实 HTTP/WS/数据库用例验证。没有把浏览器模拟视为真实 iPhone/Android、邮件、Google provider 或 LLM 的验收。建议发布前在实际目标设备补做键盘、滚动、触控和辅助功能检查。

可复用脚本已保存到仓库：

```bash
cd /home/bai/yuoyuo/heart
source backend/.venv/bin/activate
python scripts/check_localization_ui.py --output /tmp/locale-ui-check
```

需要已安装 Playwright Chromium/WebKit 及系统依赖；脚本独占 localhost:55174，结束会关闭自己启动的 Vite 和浏览器。依赖安装的网络故障已解决，未改系统默认 APT 源；临时使用 HTTPS 源和校验后的镜像下载包。

最终补查还修复了保存偏好初次加载期间切账号的竞态，新增回归测试，前端计数增至 **80**。完整 CI 后，最终文案和资源版本改动又通过 schema、普通/国际构建、80 项前端、38 项国际后端和30项扩展/批次单测。没有以较早的通过记录代替最终资源检查。
