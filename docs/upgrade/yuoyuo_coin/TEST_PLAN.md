# yuoyuo 商业化 V1 — 测试方案（交付 mimo 执行）

> 状态：**验收未通过 · 存在阻断缺陷**（详见 §1）。本方案兼做「回归测试清单」+「缺陷确认清单」。
> 范围：会员 + yuoyuo币 + 多模型 + Fish 语音/克隆 + 爱发电自动履约 + 邀请。
> 依据：`00_INDEX.md` / `backend_plan.md` / `frontend_plan.md` / `api_contract.md`
> 后端代码：main（PR #205–#211，B1–B7 已合并）。前端代码：**尚未提交/未开 PR**，仅存工作区（见 §1）。
> 最后更新：2026-07-18

---

## 0. 验收结论摘要（先读）

| 层 | 结论 | 说明 |
|----|------|------|
| 后端 B1–B7 | **需修复，不可上线** | 迁移 034 应用后**聊天主链路即被阻断**（缺陷 A/B）；TTS 计费、会员月度赠币、克隆按 provider 路由、Fish 权益拦截均未落地 |
| 前端 F1–F6 | **功能完成但未交付** | `npm run build` 通过、接口契约字段对齐；但代码**全部在工作区未提交、未开 PR**；多处硬编码颜色（违背 token 规范）；F6 预设未按性别分组 |
| 脚本/环境 | **已修正** | 迁移目标 033→037、`FISH_API_KEY` 命名、env 模板去重，均已修正（见 §0.3） |

> **给 mimo 的话**：请**先按 §1 修掉 A、B 两个阻断缺陷**，否则从「发一条消息」开始就会失败，后续用例无法进行。修完 A/B 后按 §2 冒烟，再按 §3–§11 逐项验收。标 ❌ 的用例是「已定位的已知缺陷」，用于确认而非探索。

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

## 1. 已知阻断缺陷（P0 — 测试前必须处理）

> 以下均为**读实际代码确认**的缺陷，非推测。建议先修 A、B（改动极小）再开始测试。

### 缺陷 A（阻断）— 会员查询读了不存在的列，聊天全崩
- 现象：迁移 034 应用后，任何聊天 turn 都被拦为 `BILLING_CHECK_FAILED`，`GET /api/membership` 返回 500。
- 根因：`034_memberships.py` 只建 `user_id / tier / expires_at`，**无 `status` 列**；但 `heart/membership/__init__.py:83` 查询含 `AND status = 'active'` → `UndefinedColumn`。
- 最小修法（二选一）：① 去掉查询里的 `AND status = 'active'`（推荐，惰性过期只需 `expires_at > now()`）；② 或给 034 加 `status` 列并回填（若 034 尚未在任何环境应用）。
- 验证：修后 `GET /api/membership`（免费用户）返回 200 且 `tier=free`；聊天可正常发出。

### 缺陷 B（阻断）— 默认模型 `deepseek` 未注册，免费主链路路由失败
- 现象：无 Grok/Claude key 时默认 turn 报 `All models exhausted`；有 key 时**免费用户的 deepseek 消息被 Claude 承接并扣 1200 fen**，绕过免费权益。
- 根因：`registry.py` 只注册了 `deepseek-chat`/`deepseek-reasoner`，未注册裸 slug `deepseek`；而全栈默认 `model="deepseek"`（`ss07_orchestration/models.py:27`）。Grok/Claude 反而注册了裸 slug。
- 最小修法：在 `registry.py` 把 `deepseek` 加入某个 DeepSeek provider 的 `models=[...]`（与 grok/claude 一致）。
- 验证：免费用户发消息由 DeepSeek 承接，`turn_end.served_model=="deepseek"`，扣 0 币。

### 其余高优缺陷（不阻断启动，但影响验收结论；见对应章节）
- **C（高）** TTS 未按 provider 计费：`routes_chat_ws.py:290` 仍扣旧的 `credits_cost_voice_message`，从不调用 `tts_cost_fen`（mimo 5 / fish 8 差异不生效）。→ §4/§7
- **D（高）** 会员月度赠币从未发放：`activate_or_extend` 不调 `billing.grant`。→ §5/§8
- **E（高）** 克隆恒走 MiniMax、不按 provider 路由；`assert_tts_allowed/assert_clone_allowed` 定义了但**零调用**（Fish 对免费用户无服务端拦截）。→ §7
- **F（中）** `activate_or_extend` 非幂等、非 upsert，重复 webhook 会插多行会员。→ §8
- **G（中）** 邀请端点是 `GET /api/invite` + `POST /api/invite/use`，与契约 `GET /status` + `POST /bind` 不符；无 counts/stages。→ §9
- **H（中）** `/api/credits/pricing`、`/api/membership` 返回结构与 `api_contract.md` 不一致（SKU 命名、字段名、缺 `binding_code`/`expires_at`/`entitlements` 嵌套）。→ §3
- **I（前端）** F1–F6 全部未提交、未开 PR；多页硬编码颜色；F6 预设未按性别分组。→ §10

---

## 2. 冒烟测试（Smoke — 5 分钟，判断能否继续）

| # | 步骤 | 期望 | 已知 |
|---|------|------|------|
| S1 | `alembic upgrade 037_invites` | 无报错，`alembic current` 含 `037_invites (head)` | ✅（迁移本身干净） |
| S2 | 完全重启后端，`curl /health/live` | 200 | ✅ |
| S3 | 免费用户发一条文字消息 | 正常回复，扣 0 币，`served_model=deepseek` | ❌ 缺陷 A/B 未修则失败 |
| S4 | `GET /api/membership`（免费用户） | 200 `tier=free` | ❌ 缺陷 A 未修则 500 |
| S5 | 前端 `npm run build` | 通过 | ✅ |

> S3/S4 失败即回到 §1 修 A/B，勿继续。

---

## 3. 后端 API 契约测试（逐端点）

> 对照 `api_contract.md`。凡「实际结构 ≠ 契约」记为缺陷 H 的子项，前端联调需以此为准。

| # | 端点 | 步骤 | 期望（契约） | 已知 |
|---|------|------|-------------|------|
| A1 | `GET /api/credits/pricing` | 匿名/登录调用 | 含 `signup_grant, models[], actions[], membership_tiers[], shop[], afdian_url` | ⚠️ H：shop SKU 名/币值、tts 位置、membership 字段名与契约不符 |
| A2 | `GET /api/membership` | 三种 tier 各调 | `{tier, expires_at, entitlements{models,tts,clone}, monthly_grant, binding_code}` | ⚠️ H：实际扁平、缺 `expires_at/entitlements/binding_code`；❌ A：未修则 500 |
| A3 | `GET /api/invite/status` | 登录调用 | `{invite_code, invite_url, invited_count, pending_count, total_reward, stages[]}` | ❌ G：实际是 `GET /api/invite`，无 counts/stages |
| A4 | `POST /api/invite/bind {code}` | 新用户绑定 | 200，自邀/重复绑定报结构化错误 | ❌ G：实际是 `POST /api/invite/use` |
| A5 | `POST /api/webhooks/afdian` | 见 §8 | sign 校验 + 幂等落单 + 履约 | ⚠️ 见 §8 |
| A6 | `POST /api/admin/afdian/fulfill` | admin 手动履约 unmatched | 按 `{out_trade_no, user_id}` 指定用户履约 | ⚠️ 缺陷：实际按 remark 重解析，无法对无绑定码订单指定 user |

---

## 4. 计费与账本（billing ledger）

| # | 场景 | 步骤 | 期望 | 已知 |
|---|------|------|------|------|
| B1 | DeepSeek 文本免费 | 免费用户发文字 | 扣 0 币 | ❌ 依赖缺陷 B |
| B2 | Grok 扣费 | 进阶用户选 Grok 发消息 | 每 turn 扣 3 币，`turn:{id}:llm` 幂等键 | 需 B 修复后测 |
| B3 | Claude 扣费 | 沉浸用户选 Claude | 每 turn 扣 12 币 | 同上 |
| B4 | 降级按实际模型计费 | 造 Claude 失败 | 降级 DeepSeek→扣 0；`degraded_to` 回传 | 同上 |
| B5 | **TTS 按 provider 扣** | 出一条 mimo 语音气泡 / fish 语音气泡 | mimo 扣 5、fish 扣 8 | ❌ **缺陷 C：仍扣旧 voice_message 价，provider 差异不生效** |
| B6 | 幂等不双扣 | 同一 turn 重放 | 余额只扣一次 | 需实测 |
| B7 | 对账一致 | 跑 `credit_reconciliation_worker` | `credits_balance == SUM(delta)` | ✅ ledger 本身成熟 |
| B8 | 余额不足 | 造低余额发付费模型 | `insufficient_credits{needed,balance}`，不生成、不扣 | 需实测 |

---

## 5. 会员与权益

| # | 场景 | 步骤 | 期望 | 已知 |
|---|------|------|------|------|
| M1 | 惰性过期 | 造 `expires_at < now` 的会员 | 判定为 free | ❌ 缺陷 A 未修则崩 |
| M2 | 越权模型拒 | 免费用户请求 Grok | `model_forbidden{required_tier}`，不生成不扣 | 需 A/B 修复后测 |
| M3 | 权益矩阵 | 三档各查 entitlements | free=[deepseek]/[mimo]/[]；plus 加 grok+fish+clone；immersive 加 claude | 校验 `MEMBERSHIP_TIERS_CONFIG` 生效 |
| M4 | **月度赠币** | 激活/续费进阶 | 到账 +400 币（沉浸 +800） | ❌ **缺陷 D：从不赠币** |
| M5 | 续费延期 | 对已有会员再激活 | `expires_at = max(now,expires_at)+30d`，**不新增行** | ❌ 缺陷 F：实际每次插新行 |

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
| V4 | **Fish 对免费用户拒** | 免费用户请求 Fish TTS/克隆 → 403 `tier_forbidden` | ❌ **缺陷 E：`assert_tts_allowed/assert_clone_allowed` 零调用，无拦截** |
| V5 | **克隆按 provider 路由** | 选 mimo→MiMo 克隆；选 fish→Fish 克隆 | ❌ **缺陷 E：恒走 MiniMax；Fish 无克隆实现** |
| V6 | 克隆计费 | MiMo 克隆 50 币 / Fish 100 币，成功才扣 | 部分：费用读 config 了，但 provider 路由未落地 |
| V7 | 每性别 5 个 MiMo 预设 | 第 3 步按性别返回 5 个预设 | ❌ 缺陷：迁移 036 **未种子任何预设**（只加列） |

---

## 8. 爱发电自动履约

| # | 场景 | 步骤 | 期望 | 已知 |
|---|------|------|------|------|
| P1 | sign 校验 | 伪造/正确 sign 各发 | 错误拒、正确过 | ✅ 现有逻辑 |
| P2 | 幂等落单 | 同 `out_trade_no` 重放 | 不重复履约 | 需实测 |
| P3 | remark 绑定 | 备注填 binding_code | 正确绑定 user | 需实测 |
| P4 | 无匹配不丢单 | 备注留空 | `unmatched` 落库、等人工 | 需实测 |
| P5 | SKU→会员/币包 | 配 `AFDIAN_SKU_MAP` | 会员延期 + **赠币** / 币包到账 | ❌ 会员分支不赠币（缺陷 D）；币包分支 OK |
| P6 | admin 手动履约 | 对 unmatched 指定 user | 成功 | ⚠️ 缺陷：无法对无绑定码订单指定 user |

> SKU JSON 示例（`AFDIAN_SKU_MAP`，注意币包用 `coins` 不是 `credits`）：
> `{"plan_plus":{"type":"membership","tier":"plus","days":30},"pack_18":{"type":"coins","coins":220}}`

---

## 9. 邀请

| # | 场景 | 期望 | 已知 |
|---|------|------|------|
| I1 | 绑定校验 | 自邀拒、重复绑拒、invitee 唯一 | 逻辑在，但端点名不符契约（缺陷 G） |
| I2 | 首聊双向奖励 | 新人 +100、邀请人 +100，幂等 | 需实测 |
| I3 | 阶段奖励 | 满 5 → +300；满 10 → +1000，幂等 | 需实测 |
| I4 | status 展示 | 邀请码/链接/已邀数/进度/累计币 | ❌ 缺陷 G：`/status` 未实现 |

---

## 10. 前端 UI（逐页 + 双主题）

> ⚠️ 前端代码**尚未提交**（缺陷 I）。测前先让前端 commit + 开 PR，或在当前工作区直接测。每页均需 **light + dark 双主题**。

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

## 附：建议的修复顺序（若决定先修再测）
1. **A**（membership 去 status 过滤）→ **B**（注册 deepseek slug）：解锁全部聊天，~10 行改动。
2. **C**（TTS 按 provider 计费）+ **E**（Fish/克隆权益拦截 + provider 路由）：付费语音价值点。
3. **D**（会员月度赠币）+ **F**（activate_or_extend 幂等 upsert）：付费核心权益。
4. **G**（邀请 /status + /bind 契约）+ **H**（pricing/membership 结构对齐契约）：前后端联调前必须。
5. **036 预设种子**（每性别 5 个 MiMo）+ 前端 **I**（提交/开 PR + 去硬编码色 + F6 分组）。
</content>
</invoke>
