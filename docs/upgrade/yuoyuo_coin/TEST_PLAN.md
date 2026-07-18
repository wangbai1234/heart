# yuoyuo 商业化 V1 — 测试方案（交付 mimo 执行）

> 状态：**后端阻断缺陷已修复 · 可进入功能验收**（详见 §0/§1）。本方案兼做「回归测试清单」+「修复验证清单」。
> 范围：会员 + yuoyuo币 + 多模型 + Fish 语音/克隆 + 爱发电自动履约 + 邀请。
> 依据：`00_INDEX.md` / `backend_plan.md` / `frontend_plan.md` / `api_contract.md`
> 后端代码：main（PR #205–#217，B1–B7 + 缺陷 A–H 修复已合并；P6 在 PR #218 待合并）。前端代码：**仓库内不存在**（见 §0.4 缺陷 I）。
> 最后更新：2026-07-19（据实读代码重新验收；替代 07-18 旧版）

---

## 0. 验收结论摘要（先读）

### 0.1 修复进度（对照 07-18 缺陷 A–I，均已实读代码核实）

| 缺陷 | 描述 | 当前状态 | 证据（文件:行） |
|----|------|---------|----------------|
| A | 会员查询读不存在的 `status` 列，聊天全崩 | ✅ 已修（改用 `expires_at > NOW()`） | `heart/membership/__init__.py:78` |
| B | 默认 `deepseek` slug 未注册，主链路路由失败 | ✅ 已修（注册裸 slug） | `heart/infra/llm_providers/registry.py:224` |
| C | TTS 未按 provider 计费 / 语音双扣 | ✅ **已修**（本轮）：per-message 计费归零，一 turn 只按 LLM(模型) + TTS(provider) 计费；语音不再叠扣旧 `voice_message` 价；DeepSeek 文本 0 币 | `routes_chat_ws.py:_derive_segments_and_cost/_precheck_billing` |
| D | 会员月度赠币从不发放 | ✅ 已修（`monthly_grant` 幂等发放） | `heart/membership/service.py:94-100` |
| E | Fish/克隆权益零拦截 | ✅ **已修**（本轮）：克隆侧 `assert_clone_allowed` 已接；TTS 侧新增 precheck 闸门——tier 不允许当前 TTS provider 时该 turn **静默降级为纯文本**（不阻塞文本） | 克隆: `routes_voice.py:386`；TTS: `routes_chat_ws.py:_precheck_billing` |
| F | activate 非幂等、插多行 | ✅ 已修（update-then-insert upsert） | `heart/membership/service.py:56-79` |
| G | 邀请端点不符契约 | ✅ 已修（新增 `/status`+`/bind`；旧 `/use` 保留兼容） | `heart/api/routes_invite.py:26,94` |
| H | pricing/membership 响应结构不符契约 | ◑ 声称已修（#213），**mimo 须抽验响应结构对齐 `api_contract.md`** | — |
| 036 种子 | 每性别 5 个 MiMo 预设未种子 | ✅ 已修（种子在 `038_mimo_preset_seeds`；`voice_provider` 列在 036） | 10 preset 单测 pass |
| P6 | admin 手动履约无法指定 user | ✅ 代码已写（`admin_fulfill_order` 收 user_id），**PR #218 待合并** | `heart/afdian/fulfillment.py:174` |

### 0.2 层级结论

| 层 | 结论 | 说明 |
|----|------|------|
| 后端 B1–B7 | **阻断已清 + C/E 已修，可功能验收** | A/B 阻断 + C 双扣 + E TTS 闸门本轮全部修复；全量单测 1361 passed。功能验收剩「跑通实测」而非「已知缺陷」 |
| 前端 F1–F6 | **未落地** | 仓库内无 membership/wallet/invite 页面，`api.ts` 无 `getMembership/getInviteStatus/getShopTiers`。07-18「工作区未提交」的说法与当前不符——**这些文件不存在** |
| 脚本/环境 | **迁移目标需上调** | `setup.sh`/`deploy-prod.sh` 仍 pin `037_invites`，但当前 head 是 `038_mimo_preset_seeds` → 按脚本装则 10 个预设音色不入库（见 §0.3） |

### 0.3 ⚠️ 三个必须先处理的环境/脚本问题

1. ✅ **脚本迁移目标已上调**（本轮修复）：`scripts/setup.sh` 与 `scripts/deploy-prod.sh` 现执行 `alembic upgrade 038_mimo_preset_seeds`，预设音色会随 setup 入库。若用旧脚本装过，手动 `alembic upgrade 038_mimo_preset_seeds` 补齐。
2. **Alembic 多头**：`alembic heads` 返回两个头（`022_identity_narrative_backfill` + `038_mimo_preset_seeds`）。**禁用 `alembic upgrade head`**（报 Multiple head revisions）。yuoyuo 链自身线性单头 `033→034→…→038`，升级请**显式指定 `038_mimo_preset_seeds`**。
3. **改列后必须完全重启后端**（非 `--reload`），切分支前先停 dev server（见 `.claude/CLAUDE.md` DB 铁律）。

### 0.4 给 mimo 的话

后端 A/B 阻断 + C 语音双扣 + E TTS 免费闸门**均已修复**（全量单测 1361 passed），可直接从 §2 冒烟进入功能验收，不必再修后端逻辑。标 ✅ 的用例请做**回归/实测验证**（确认修复真生效、无回退），重点跑通 §1 的 C、E 实测判定。前端 F1–F6 **无代码可测**，§10 暂缓，须先由前端开发落地。仅剩 H（响应结构抽验）为非代码核对项。

### 0.1 测试环境准备

```bash
# 1) 同步代码 + 依赖
cd /Users/wanglixun/heart && git pull
bash scripts/setup.sh            # 或手动：见下

# 2) 迁移到最新 head（本次已把脚本目标从 033 提升到 037_invites）
cd backend && .venv/bin/python -m alembic current   # 期望最终含 037_invites (head)
#   ⚠️ 见 §1 缺陷 A：升到 034+ 后聊天会崩，务必先修 A 再升级/重启

# 3) 关键：改动列后必须【完全重启】后端（不是 --reload），否则 SQLAlchemy 反射拿不到新列
#    切分支前先停 dev server（见 .claude/CLAUDE.md DB 铁律）

# 4) 起服务
bash scripts/dev.sh
```

### 0.2 测试账号 / 密钥

- 至少 3 个测试用户：`free`（免费）、`plus`（进阶）、`immersive`（沉浸）。会员态可用 admin 端点或直接改 `user_memberships` 造数。
- 模型 key：`.env` 已配 Grok / Claude（经 micuapi.ai 代理，openai-compat）。Fish：`FISH_API_KEY` 留空则 Fish 相关用例走「未配置→降级」路径（见 §7）。
- 管理密钥：`X-Admin-Key`（见 `routes_admin.py`）。

### 0.3 本次已修正项（无需再测名字，只测生效）

| 项 | 修正 |
|----|------|
| `FISH_AUDIO_API_KEY` 命名不匹配 | 代码读的是 `FISH_API_KEY`（`core/config.py:244`）。已把 `.env.example`/`.env.prod.example` 改为 `FISH_API_KEY`；本地 `.env` 删除失效的 `FISH_AUDIO_API_KEY` 行 |
| `GROK_BASE_URL` 多余 `/v1` | grok.py 自动拼 `/v1/chat/completions`，base 只填域名根。模板已改 `https://api.x.ai`，`GROK_MODEL` 改 `grok-3-mini-fast`（对齐代码默认） |
| env 模板重复键 | `.env.example` 里 GROK/CLAUDE/AFDIAN 曾出现两遍，已去重（`grep uniq -d` 现为空） |
| `CLAUDE_API_STYLE` 填成模型名 | 本地 `.env` 原为 `claude-haiku-4-5`（错），已改 `openai-compat` + 新增 `CLAUDE_MODEL=claude-haiku-4-5`，`CLAUDE_BASE_URL` 去掉行首空格 |
| 脚本迁移目标 pin 死 033 | `setup.sh` / `deploy-prod.sh` 已追加 `alembic upgrade 037_invites` |

---

## 1. 残留待确认点（A/B/C/E 已修，以下为剩余重点）

> 07-18 的阻断缺陷 A、B 已在 #212 修复；C（语音双扣）、E（TTS 免费闸门）本轮修复。以下是实读代码后仍需 mimo 重点**实测跑通**的点（非已知缺陷）。

### 已修 C — 语音双扣（本轮修复，须实测确认）
- 修法：`_derive_segments_and_cost` 返回 per-message cost = 0；`_precheck_billing` 余额下限改为 `LLM(模型) + TTS(provider)`，不再用旧 `credits_cost_voice_message`。
- 实测判定：一条 mimo 语音 turn 的 `credit_transactions` 只出现 `turn:{id}:tts`（5 币）+（付费模型时）`turn:{id}:llm`；**无 `msg:{i}` 扣费行**。DeepSeek 纯文本 turn 扣 0 币。

### 已修 E — Fish TTS 免费闸门（本轮修复，须实测确认）
- 修法：`_precheck_billing` 在语音开启时读取当前 TTS primary provider，`assert_tts_allowed(tier, provider)` 失败则该 turn `effective_voice=False`（**降级纯文本，不阻塞、不报错**），日志 `voice_downgraded_tier_forbidden`。
- 实测判定：免费用户 + Fish 为 primary → 收到纯文本回复、无语音、无扣 TTS 费、无技术错误；plus/immersive 用户 + Fish → 正常出语音扣 8 币。
- 局限：TTS provider 是进程级单例、非按用户选择，故闸门在"当前 primary 不被 tier 允许"时触发；克隆侧走 `assert_clone_allowed`（独立路径）。

### 残留 H（中）— pricing/membership 响应结构须抽验
- #213 声称已对齐 `api_contract.md §1.1–1.4`。mimo 须抽验 `GET /api/credits/pricing`、`GET /api/membership` 的实际 JSON 结构（字段名、SKU 命名、`binding_code`/`expires_at`/`entitlements` 嵌套）是否与契约逐字对齐——前端联调以此为准。

### 缺陷 I（前端）— F1–F6 无代码
- 仓库内**不存在** membership/wallet/invite 页面，`web/src/services/api.ts` 无 `getMembership/getInviteStatus/getShopTiers`。§10 暂无可测对象，须先由前端开发落地并开 PR。

---

## 2. 冒烟测试（Smoke — 5 分钟，判断能否继续）

| # | 步骤 | 期望 | 已知 |
|---|------|------|------|
| S1 | `alembic upgrade 038_mimo_preset_seeds`（**勿用 `head`**，多头会报错） | 无报错，`alembic current` 含 `038_mimo_preset_seeds` | ✅ 迁移干净；脚本已 pin 038 |
| S2 | 完全重启后端，`curl /health/live` | 200 | ✅ |
| S3 | 免费用户发一条文字消息 | 正常回复，扣 0 币，`served_model=deepseek` | ✅ A/B 已修，应通过 |
| S4 | `GET /api/membership`（免费用户） | 200 `tier=free` | ✅ A 已修，应通过 |
| S5 | `SELECT count(*) FROM preset_voices WHERE provider='mimo'` | = 10（每性别 5 个） | ⚠️ 须确认 038 已应用，否则为 0 |

> S3/S4 现应通过（A/B 已修）。若仍失败，先确认 §0.3 的迁移/重启事项，再登记为回退缺陷。

---

## 3. 后端 API 契约测试（逐端点）

> 对照 `api_contract.md`。凡「实际结构 ≠ 契约」记为缺陷 H 的子项，前端联调需以此为准。

| # | 端点 | 步骤 | 期望（契约） | 已知 |
|---|------|------|-------------|------|
| A1 | `GET /api/credits/pricing` | 匿名/登录调用 | 含 `signup_grant, models[], actions[], membership_tiers[], shop[], afdian_url` | ⚠️ H：shop SKU 名/币值、tts 位置、membership 字段名与契约不符 |
| A2 | `GET /api/membership` | 三种 tier 各调 | `{tier, expires_at, entitlements{models,tts,clone}, monthly_grant, binding_code}` | ✅ A 已修（应 200）；◑ H：结构须抽验对齐契约 |
| A3 | `GET /api/invite/status` | 登录调用 | `{invite_code, invite_url, invited_count, pending_count, total_reward, stages[]}` | ✅ G 已修（`/status` 已实现）；抽验字段齐全 |
| A4 | `POST /api/invite/bind {code}` | 新用户绑定 | 200，自邀/重复绑定报结构化错误 | ✅ G 已修（`/bind` 已实现） |
| A5 | `POST /api/webhooks/afdian` | 见 §8 | sign 校验 + 幂等落单 + 履约 | ⚠️ 见 §8 |
| A6 | `POST /api/admin/afdian/fulfill` | admin 手动履约 unmatched | 按 `{out_trade_no, user_id}` 指定用户履约 | ✅ P6 已修（收 user_id 跳过 remark）；⚠️ 代码在 **PR #218，未合并**，测前须合入 main |

---

## 4. 计费与账本（billing ledger）

| # | 场景 | 步骤 | 期望 | 已知 |
|---|------|------|------|------|
| B1 | DeepSeek 文本免费 | 免费用户发文字 | 扣 0 币 | ✅ B 已修，应通过 |
| B2 | Grok 扣费 | 进阶用户选 Grok 发消息 | 每 turn 扣 3 币，`turn:{id}:llm` 幂等键 | 应通过（B 已修） |
| B3 | Claude 扣费 | 沉浸用户选 Claude | 每 turn 扣 12 币 | 应通过 |
| B4 | 降级按实际模型计费 | 造 Claude 失败 | 降级 DeepSeek→扣 0；`degraded_to` 回传 | 需实测 |
| B5 | **TTS 按 provider 扣** | 出一条 mimo 语音气泡 / fish 语音气泡 | mimo 扣 5、fish 扣 8，**且不双扣**；文本 turn 0 币 | ✅ C 已修，须实测：`credit_transactions` 只有 `tts`/`llm` 行，无 `msg:{i}` 行 |
| B6 | 幂等不双扣 | 同一 turn 重放 | 余额只扣一次 | 需实测 |
| B7 | 对账一致 | 跑 `credit_reconciliation_worker` | `credits_balance == SUM(delta)` | ✅ ledger 本身成熟 |
| B8 | 余额不足 | 造低余额发付费模型 | `insufficient_credits{needed,balance}`，不生成、不扣 | 需实测 |

---

## 5. 会员与权益

| # | 场景 | 步骤 | 期望 | 已知 |
|---|------|------|------|------|
| M1 | 惰性过期 | 造 `expires_at < now` 的会员 | 判定为 free | ✅ A 已修，应通过 |
| M2 | 越权模型拒 | 免费用户请求 Grok | `model_forbidden{required_tier}`，不生成不扣 | 应通过（`model_forbidden` 已接） |
| M3 | 权益矩阵 | 三档各查 entitlements | free=[deepseek]/[mimo]/[]；plus 加 grok+fish+clone；immersive 加 claude | 校验 `MEMBERSHIP_TIERS_CONFIG` 生效 |
| M4 | **月度赠币** | 激活/续费进阶 | 到账 +400 币（沉浸 +800） | ✅ **D 已修**，须实测到账（幂等键 `membership_grant:*`） |
| M5 | 续费延期 | 对已有会员再激活 | `expires_at = max(now,expires_at)+30d`，**不新增行** | ✅ **F 已修**（upsert），须实测不插新行 |

---

## 6. 多模型与降级

| # | 场景 | 期望 | 已知 |
|---|------|------|------|
| L1 | 模型可选范围随 tier | 前端置灰 + 服务端 `assert_model_allowed` 双保险 | M2 |
| L2 | failover 链 | Claude→Grok→DeepSeek 静默降级，不显技术错误 | 需实测（router 单测已覆盖，但用了 fake deepseek，见缺陷 B） |
| L3 | served_model 回传 | `turn_end.served_model` 与实际一致，按它计费 | 依赖 B |
| L4 | Claude openai-compat 代理 | 经 micuapi.ai 正常出文本 | 需实测（本次刚修 `.env` style） |

---

## 7. 语音（Fish / MiMo / 克隆）

| # | 场景 | 期望 | 已知 |
|---|------|------|------|
| V1 | MiMo 导演为主 | 语音走 MiMo 优先 | ⚠️ wiring 已改 MiMo-primary，但 `voice_provider` 默认仍 `minimax`；确认实际 primary |
| V2 | 全 TTS 失败只回文本 | 语音失败不阻塞文本、不扣 TTS 费 | 需实测 |
| V3 | Fish 未配置 | `FISH_API_KEY` 空 → 走降级链，不崩 | ✅ 应成立 |
| V4 | **Fish 对免费用户拒** | 免费用户克隆 Fish → 403；免费用户 Fish TTS → 降级纯文本 | ✅ E 已修：克隆侧 `assert_clone_allowed` 403；TTS 侧 precheck 降级纯文本（不阻塞、不报错），须实测 |
| V5 | **克隆按 provider 路由** | 选 mimo→MiMo 克隆；选 fish→Fish 克隆 | ✅ E 已修（provider 路由 + `voice_provider` 列 036），须实测两条路由 |
| V6 | 克隆计费 | MiMo 克隆 50 币 / Fish 100 币，成功才扣 | 应通过（费用 config + provider 路由已落地） |
| V7 | 每性别 5 个 MiMo 预设 | 第 3 步按性别返回 5 个预设 | ✅ 已修（种子在 `038`），**前提 038 已应用**（见 §0.3/S5） |

---

## 8. 爱发电自动履约

| # | 场景 | 步骤 | 期望 | 已知 |
|---|------|------|------|------|
| P1 | sign 校验 | 伪造/正确 sign 各发 | 错误拒、正确过 | ✅ 现有逻辑 |
| P2 | 幂等落单 | 同 `out_trade_no` 重放 | 不重复履约 | 需实测 |
| P3 | remark 绑定 | 备注填 binding_code | 正确绑定 user | 需实测 |
| P4 | 无匹配不丢单 | 备注留空 | `unmatched` 落库、等人工 | 需实测 |
| P5 | SKU→会员/币包 | 配 `AFDIAN_SKU_MAP` | 会员延期 + **赠币** / 币包到账 | ✅ D 已修，会员分支现应赠币；须实测 |
| P6 | admin 手动履约 | 对 unmatched `{out_trade_no, user_id}` 指定 user | 成功履约、`fulfilled_at` 落库 | ✅ 已修（`admin_fulfill_order`）；⚠️ 在 **PR #218 未合并**，须先合入 |

> SKU JSON 示例（`AFDIAN_SKU_MAP`，注意币包用 `coins` 不是 `credits`）：
> `{"plan_plus":{"type":"membership","tier":"plus","days":30},"pack_18":{"type":"coins","coins":220}}`

---

## 9. 邀请

| # | 场景 | 期望 | 已知 |
|---|------|------|------|
| I1 | 绑定校验 | 自邀拒、重复绑拒、invitee 唯一 | ✅ G 已修（`/bind` 已实现），须实测三类拒绝 |
| I2 | 首聊双向奖励 | 新人 +100、邀请人 +100，幂等 | 需实测 |
| I3 | 阶段奖励 | 满 5 → +300；满 10 → +1000，幂等 | 需实测 |
| I4 | status 展示 | 邀请码/链接/已邀数/进度/累计币 | ✅ G 已修（`/status` 已实现），须实测字段齐全 |

---

## 10. 前端 UI（逐页 + 双主题）

> 🔴 **前端商业化 UI 在仓库内不存在**（缺陷 I）：无 membership/wallet/invite 页面，`api.ts` 无 `getMembership/getInviteStatus/getShopTiers`。**本节暂无可测对象**，须先由前端开发落地并开 PR，再按下表（含 light+dark 双主题）验收。下表为落地后的验收标准，非当前状态。

| # | 页面 | 验收点 | 已知 |
|---|------|--------|------|
| F1 | 全站文案 | 「积分」全改「yuoyuo币」（`grep 积分 web/src` 应为空） | ✅ |
| F2 | `/membership` | 三档卡（数据来自 pricing）、当前档高亮、绑定码 + 爱发电指引 | ✅ 功能；⚠️ 硬编码色 |
| F3 | `/wallet` | 余额 + 商城 4 挡（来自 pricing.shop）、每挡去爱发电 | ✅ 功能；⚠️ 硬编码色 |
| F4 | 聊天模型选择器 | DeepSeek/Grok/Claude，按 tier 置灰、标币价；WS 事件 `model_forbidden/served_model/degraded_to/insufficient_credits` | ✅ 功能；置灰用文字徽标非锁图标（轻微偏差） |
| F5 | `/invite` | 邀请码/链接/进度/累计；`?invite=` 登录后绑定 | ✅ 功能；依赖后端 `/status`（缺陷 G，需 mock 或后端修） |
| F6 | 建角色第 3 步 | 每性别 5 个 MiMo 预设 + MiMo/Fish 两克隆，Fish 免费置灰 | ⚠️ 预设是扁平列表**未按性别分组**；克隆两选项 + Fish 置灰 OK |
| F7 | token 规范 | 无硬编码色 | ❌ 缺陷 I：MembershipPage/InvitePage/TransactionsPage/CreateCharacterPage 多处 `rgba()`/hex |

---

## 11. 回归（陪伴核心不受影响）

| # | 验收点 | 期望 |
|---|--------|------|
| R1 | 免费 DeepSeek 聊天 | 与商业化前一致（修 B 后） |
| R2 | 记忆 / 主动消息 / inner loop worker | 正常 |
| R3 | 现有语音（rin/dorothy MiniMax 克隆音色） | 不因 MiMo-primary 改动而失效（V1 重点确认） |
| R4 | 注册赠币 | 100 币（`signup_grant_credits=10000` fen 不变） |
| R5 | 兑换码路径 | 保留可用 |

---

## 12. 缺陷登记表模板

| ID | 用例 | 现象 | 期望 | 严重度 | 文件:行 | 状态 |
|----|------|------|------|--------|---------|------|
| （示例）A | S3 | 发消息报 BILLING_CHECK_FAILED | 正常回复 | 阻断 | membership/__init__.py:83 | 待修 |

---

## 附 A：当前剩余工作（2026-07-19 重新验收后）
后端逻辑残留已清空，剩下的是"合并 + 实测 + 前端落地"：
1. **合并 PR #218**（P6 admin 手动履约）→ 否则 §8/A6 无法测。（需 owner 授权合并）
2. **实测 C/E**：按 §1 的实测判定跑通（不再是代码缺陷，是验证）。
3. **抽验 H**：pricing/membership 响应结构逐字对齐 `api_contract.md`（非代码核对项）。
4. **前端 F1–F6**：从零落地（当前仓库无代码），开 PR 后再走 §10。

> 本轮（fix/yuoyuo-coin-billing-residuals）已修：C 语音双扣、E TTS 免费闸门、脚本迁移目标 037→038。

## 附 B：修复历史（供追溯）
- #212 修 A/B（阻断）· #213 修 G/H · #214 修 D/F · #215 修 C（turn-end 侧）· #216 修 E（克隆侧）· #217 P5 预设种子（038）· #218 P6 admin 履约（**待合并**）· 本轮 fix/yuoyuo-coin-billing-residuals：C 双扣归零 + E TTS 闸门 + 脚本 038。
