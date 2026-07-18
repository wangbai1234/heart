# yuoyuo 商业化 — 后端设计（Sonnet 执行）

> 状态：规划 · 待落地
> 执行方：Sonnet（Claude Code）
> 依赖：`00_INDEX.md`（货币模型 / 等级矩阵 / 定价 / 迁移清单）
> 上游现状：`heart/billing/__init__.py`（成熟 ledger）、`infra/llm_providers/`（LLM 抽象）、`ss08_voice/`（TTS 抽象）、`routes_webhooks.py`（爱发电对账）
> 最后更新：2026-07-18

---

## 0. 全局约定

- 技术栈：Python 3.11 / FastAPI / SQLAlchemy 2.0 async / Alembic / Postgres(pgvector) / Redis。所有 py 命令在 `backend/` 下跑。
- 新路由 `heart/api/routes_<domain>.py`，在 `heart/api/main.py` include 区注册。
- 新迁移 `backend/migrations/versions/0NN_<slug>.py`，`down_revision` 串当前最新头，revision 名 ≤32 字符。
- 计费一律走 `heart/billing/__init__.py` 现有函数 + 幂等键；**禁止**新建第二套 ledger。
- **禁止 `except Exception:` 静默吞异常**（`.claude/CLAUDE.md`）：DB/schema/计费类必须 `logger.exception(...)` + `raise` 或走结构化错误。
- 定价 / 等级权益 / SKU 映射**全部 config 驱动**，禁硬编码档位。
- 一模块一分支一 PR，base=main。

---

## B1 · 定价 + 权益内核（其余模块地基）

**目标**：把「模型/动作→币成本」「等级→权益」抽成单一可测来源。

- 新增 `heart/billing/pricing.py`：
  - `COST_FEN: dict` — `{"deepseek": 0, "grok": 300, "claude": 1200}`（LLM/次）、`{"mimo": 500, "fish": 800}`（TTS/次）、`{"clone_mimo": 5000, "clone_fish": 10000}`（动作）。值从 `settings` 读，`pricing.py` 只做聚合与查询函数 `llm_cost_fen(model)` / `tts_cost_fen(provider)` / `action_cost_fen(action)`。
- 新增 `heart/membership/__init__.py`（或 `heart/membership/service.py`）：
  - `TIER_ENTITLEMENTS: dict` — `free/plus/immersive` → `{models:[...], tts:[...], clone:[...], monthly_grant_fen:int}`，从 config map 读。**沉浸(immersive) = 进阶超集**：models=[deepseek,grok,claude]、tts=[mimo,fish]、clone=[mimo,fish]、月度 800 币；进阶(plus)=[deepseek,grok]/[mimo,fish]/[mimo,fish]/400 币；免费(free)=[deepseek]/[mimo]/[]/0。
  - `get_effective_tier(db, user_id) -> str`：读 `user_memberships`，**惰性**判定 `now < expires_at ? tier : "free"`。
  - `get_entitlements(tier) -> Entitlements`：返回允许的 models/tts/clone/月度赠币。
  - `assert_model_allowed(tier, model)` / `assert_tts_allowed(tier, provider)` / `assert_clone_allowed(tier, provider)`：越权抛结构化异常（供 API 层转 402/403 事件）。
- config.py 新增（near 计费块 L168-176 与 LLM 块 L38-52）：
  - 定价：`grok_cost_credits=3`、`claude_cost_credits=12`、`mimo_tts_cost_credits=5`、`fish_tts_cost_credits=8`、`clone_mimo_cost_credits=50`、`clone_fish_cost_credits=100`（内部换算 ×100 存 fen 或直接存 fen，二选一，保持与现有 `credits_cost_*` 一致的 fen 语义）。
  - 等级权益：`membership_tiers`（JSON/dict via env 或代码常量 + env 覆盖）。
- 扩展 `GET /api/credits/pricing`（`routes_credits.py:115`）：在现有返回上补 `models:[{id,label,cost,tiers_allowed}]`、`actions:[{id,label,cost}]`、`membership_tiers:[...]`、`shop:[{sku,price,credits,bonus}]`。展示层 ÷100。

**产出**：`billing/pricing.py`（新）、`membership/`（新）、`config.py`（改）、`routes_credits.py`（改）、单测 `tests/unit/test_pricing_entitlements.py`。

---

## B2 · 会员表 + API

- 迁移 `034_memberships.py`：`user_memberships`（`user_id UUID FK→users ON DELETE CASCADE UNIQUE`、`tier TEXT CHECK in (free,plus,immersive)`、`status TEXT`、`started_at`、`expires_at TIMESTAMPTZ`、`source TEXT` afdian/admin/code、`last_grant_at`、`created_at`、`updated_at`）。幂等 `CREATE TABLE IF NOT EXISTS`；写 downgrade。
- `heart/membership/service.py`：`activate_or_extend(db, user_id, tier, days, monthly_grant_fen, source, idempotency_key)`——原子 upsert（延长 `expires_at` = `max(now, expires_at)+days`）+ 调 `billing.grant(monthly_grant_fen, key)`（同 idempotency 保护，避免重复赠币）。
- 新路由 `heart/api/routes_membership.py`（`/api/membership`，Bearer）：`GET /` → `{tier, expires_at, entitlements, monthly_grant}`（tier 走 `get_effective_tier` 惰性）。在 `main.py` 注册。
- （可选）`workers/membership_expiry_worker.py`：仅做 `status` 清理与指标，**权益判定仍以惰性为准**（不依赖 worker 正确性）。

**产出**：迁移 034、`membership/service.py`、`routes_membership.py`、`main.py`（改）、单测（激活/延期/惰性过期/月度赠币幂等）。

---

## B3 · 多模型 provider（Grok + Claude）

⚠️ 只加在 `infra/llm_providers/`，**勿碰空壳 `infra/llm/`**。

- 新增 `infra/llm_providers/grok.py`：`GrokProvider(LLMProvider)`，OpenAI 式 `/v1/chat/completions`，**镜像 `deepseek.py`** 的 httpx 调用/流式/`estimate_cost`/`count_tokens`。
- 新增 `infra/llm_providers/claude.py`：`ClaudeProvider(LLMProvider)`，anthropic `/v1/messages` 适配（request/response/stream 与 OpenAI 不同：`system` 独立字段、`content` block、SSE `event:` 类型）。支持 `claude_api_style` 切 anthropic / openai-compat。
- `registry.py:initialize_registry()`：读新 env 注册 `grok-*` / `claude-*` 模型名 → provider（沿用 `register_provider_instance`）。
- `router.py:ModelRouter`：新增按请求 model 覆盖的方法，如 `stream_for(model, request, failover: list[str])` 与 `call_for(...)`；内部 `registry.get_provider_for_model(model)`；捕获 `ProviderError` 后按 failover 链**逐个降级**，返回 `(response/stream, served_model)`。**默认 failover 链** `["claude","grok","deepseek"]`（按可用性裁剪）。
- config.py L38-52 附近新增：`grok_api_key`、`grok_base_url`、`grok_model`；`claude_api_key`、`claude_base_url`、`claude_model`、`claude_api_style="anthropic"`。`.env.example` 同步补 `GROK_API_KEY` / `CLAUDE_API_KEY`（**占位符，禁真值**）。

**产出**：`grok.py`、`claude.py`（新）、`registry.py`/`router.py`/`config.py`（改）、`.env.example`（改）、单测（`fake` provider 驱动 failover：Claude 抛错→降 Grok→降 DeepSeek，served_model 正确）。

---

## B4 · 按模型计费接入（核心）

改 `heart/api/routes_chat_ws.py`：

- WS `chat` 消息体新增 `model` 字段（缺省 = `deepseek`）。
- `_precheck_billing`（~184）：按**所选 model** 的 `pricing.llm_cost_fen(model)` + 预计 TTS 成本预检余额；不足发 `insufficient_credits` 事件（带 needed/balance），不生成。
- **权益校验**：生成前调 `membership.assert_model_allowed(tier, model)`；越权 → 发结构化 `model_forbidden` 事件（前端引导升级），不生成、不扣费。
- 生成：调 `ModelRouter.stream_for(model, req, failover=[...])`，拿到 `served_model`。
- `_charge_and_insert_bubbles`（~265）：
  - **LLM 费**：每 turn **扣一次**，金额 = `pricing.llm_cost_fen(served_model)`（DeepSeek=0 跳过），幂等键 `turn:{turn_id}:llm`。
  - **TTS 费**：每语音气泡按实际 provider 扣 `pricing.tts_cost_fen(provider)`，幂等键 `turn:{turn_id}:tts:{i}`。
  - action 气泡不扣。安全拦截/失败/兜底不扣（沿用现逻辑）。
- `turn_end` 回带 `served_model` + 最新 `balance`。降级发生时附 `degraded_to` 供前端轻提示。

**产出**：`routes_chat_ws.py`（改）、单测（越权拒、failover 后按 served_model 扣、DeepSeek 0 扣、TTS 按 provider 扣、幂等重放不双扣、余额不足不生成）。

---

## B5 · Fish Audio + MiMo 导演 + 音色第 3 步后端

- 新增 `ss08_voice/fish_provider.py`：`FishAudioProvider(TTSProvider)` — 实时 TTS（`text-to-speech/realtime`）+ 克隆（`voices/create`）+ 音色管理。实现 `synthesize/stream_synthesize/estimate_cost_cents/name="fish"`。
- `api/wiring.py`：`_build_primary_voice_provider`（~275）改为 **MiMo 导演为 primary**（`voice_provider` 默认 mimo）、**MiniMax 为最后兜底**；`_build_fallback_voice_provider`（~314）链：选定 provider → MiMo → MiniMax。Fish 作**可选 provider**（付费门槛，运行时按角色音色配置 + 用户 tier 选中）。
- `service.py` `synthesize_with_fallback`：全失败返回信号，让 chat WS **只回文本、不出音频、不扣 TTS 费**（永不阻塞文本）。
- **克隆按 provider 路由**（不再恒 MiniMax）：
  - 迁移 `036_voice_providers.py`：`character_voices` 加 `clone_provider TEXT`（mimo/fish/minimax）；幂等种子**每性别 5 个 MiMo 预设音色**（provider='mimo'，含 name/description/gender/sample_url 指向 `/api/voice/presets/{id}/sample`）。
  - `routes_voice.py POST /clone`：接受 `provider` 参数；`_CLONE_COST_FEN` 改为 config（`pricing.action_cost_fen("clone_"+provider)`，Fish=100币/10000fen、MiMo=50币）；克隆成功后按 provider 扣费（沿用「成功才扣」）。
  - **服务端强制**：`membership.assert_tts_allowed(tier,"fish")` / `assert_clone_allowed(tier, provider)` — 免费用户请求 Fish → 403 结构化错误（前端已置灰，这是后端兜底）。
- config.py 语音块（L186-213）新增 `fish_audio_api_key`、`fish_base_url`、`fish_model`；`voice_provider` 默认改 `mimo`（与 `.env.example` 对齐，消除现有 mismatch）。`.env.example` 补 `FISH_AUDIO_API_KEY`（占位符）。

**产出**：`fish_provider.py`（新）、`wiring.py`/`service.py`/`routes_voice.py`/`config.py`（改）、迁移 036、`.env.example`/`.env.prod.example`（Fish/定价段已预置，按需校正）、单测（provider 选择、failover 链、Fish 免费用户拒、克隆按 provider 计费、预设 5/性别）。
> ⚠️ 本 PR 让 MiMo 导演成为 primary 后，需把 `scripts/deploy-prod.sh` 里强制 `VOICE_PROVIDER=minimax` 的 sed（约 L139）改为 `mimo`，并放宽「MINIMAX_API_KEY 必填」校验（改为 mimo 模式下不强制），否则生产部署会因缺 MiniMax key 而中止。

---

## B6 · 爱发电 webhook 自动履约

改 `heart/api/routes_webhooks.py`：

- 迁移 `035_afdian_fulfill.py`：`afdian_orders` 加 `user_id UUID`（可空）、`status TEXT`（received/fulfilled/unmatched/failed）、`fulfilled_at`、`fulfillment_type TEXT`（membership/coins）。
- webhook 流程：校验 sign（现 `_verify_afdian_sign`）→ 幂等 upsert `afdian_orders`（现 `ON CONFLICT out_trade_no`）→ **新增履约**：
  1. **解析 `remark` → 绑定 user**：匹配用户绑定码（由 `user.id` 派生的短码，见下）或 email。无匹配 → `status=unmatched`，返回 200，等 admin 手动履约（**不丢单**）。
  2. **SKU/plan_id → 权益 map**（config `AFDIAN_SKU_MAP`）：币包 → `billing.grant(coins_fen, key=f"afdian:{out_trade_no}")`；会员 → `membership.activate_or_extend(tier, 30, monthly_grant_fen, source="afdian", key=f"afdian:{out_trade_no}")`。
  3. 原子幂等（同一 `out_trade_no` 重放不重复履约）；置 `status=fulfilled`、`fulfilled_at`。
- **绑定码**：`user.id` 派生（如 base32 前 8 位），无需新列；`GET /api/membership` 或 `/api/credits/pricing` 返回给前端展示。提供 `resolve_user_by_binding_code(code)`。
- admin 端点 `POST /api/admin/afdian/fulfill`（`X-Admin-Key`，沿用 `routes_admin.py` 风格）：对 `unmatched` 订单手动指定 user 履约。
- 兑换码路径（`redemption_codes`）**保留**作为次要赠礼/客服补偿通道。

**产出**：迁移 035、`routes_webhooks.py`/`routes_admin.py`/`config.py`（改）、单测（sign 校验、幂等重放、remark 绑定成功/失败→unmatched、SKU→会员/币、admin 履约）。

---

## B7 · 邀请系统

- 迁移 `037_invites.py`：`invites`（`id`、`inviter_id UUID FK`、`invitee_id UUID FK UNIQUE`、`code TEXT`、`status TEXT` bound/rewarded、`bound_at`、`first_chat_at`、`base_rewarded_at`、`created_at`）。
- 邀请码：`user.id` 派生（可与绑定码同源或独立），无需新列。
- 新路由 `heart/api/routes_invite.py`（`/api/invite`，Bearer）：
  - `POST /bind {code}`：注册后绑定 inviter（校验非自邀、未绑定过、invitee 唯一）。
  - `GET /status`：我的邀请码/链接、已邀人数、已达阶段、累计奖励。
- **首次成功聊天触发**：chat WS turn 成功钩子里，若当前 user 是某 invite 的 invitee 且 `first_chat_at is null` → 置时间 + `billing.grant(100币, key=f"invite_base_invitee:{invitee}")` 给新人、`grant(100币, key=f"invite_base_inviter:{invitee}")` 给邀请人；置 `status=rewarded`。
- **阶段奖励**：邀请人有效邀请数达 5 → `grant(300币, key=f"invite_stage:{inviter}:5")`；达 10 → `grant(1000币, key=f"invite_stage:{inviter}:10")`。幂等键天然防重。

**产出**：迁移 037、`routes_invite.py`（新）、chat WS 钩子（改）、`main.py`（改）、单测（绑定校验、自邀拒、首聊双向奖励幂等、阶段奖励幂等、防刷）。

---

## 迁移与环境铁律（`.claude/CLAUDE.md` 摘要）

- `down_revision` 串到 `033_chat_messages_is_proactive`（用 `alembic history` 确认实际 revision id）。
- revision 名 ≤32 字符；`IF NOT EXISTS` / `ON CONFLICT DO NOTHING` 幂等；DDL 与回填分离；写 `downgrade`；迁移内禁 `import heart.xxx`。
- 改列后**完全重启后端**（非 --reload）。
- 每次 push 前 `alembic current == heads`。
- **每个新增迁移的 PR 必须同步更新** `scripts/setup.sh` 与 `scripts/deploy-prod.sh` 的迁移目标 revision（当前 pin 到 `033`）到该 PR 引入的最新 head，否则 dev/prod DB 会缺表（脚本内已留 ⚠️ 提示行）。

## 接口契约

所有新端点/字段/枚举以 `api_contract.md` 为准；每个后端 PR body 必须声明「符合 api_contract.md §X」。定价/权益/成本单位见契约 §0（对外币、内部 fen）。

---

## 验收（DoD）

- `bash scripts/ci.sh` 全绿；不引入新 lint/type 债（Tier A/B 立即修）。
- `alembic upgrade head` 干净 + 有 downgrade。
- 单测覆盖：越权模型拒 / failover 后按实际模型扣 / DeepSeek 0 扣 / TTS 按 provider 扣 / 计费幂等不双扣 / 余额不破负 / Fish 免费用户拒 / 克隆按 provider 计费 / webhook sign+幂等+remark 绑定+SKU 履约 / 邀请首聊+阶段幂等 / 对账 `SUM(delta)==balance`。
- 涉付费/身份路径有限流 + 幂等键。
- 每模块独立分支 + PR，base=main，7 天内可合。

---

## ⚙️ Sonnet 执行 Prompt（复制交付）

```
你在 Heart 仓库（对外名 yuoyuo，工作目录 /Users/wanglixun/heart）实现「yuoyuo 商业化后端：会员 + yuoyuo币 + 多模型 + 爱发电自动履约 + 邀请」。严格按 docs/upgrade/yuoyuo_coin/00_INDEX.md 与 backend_plan.md。

开工前必读并核实现状（禁止凭印象）：
- docs/PROJECT_STATUS.md、AGENTS.md、.claude/CLAUDE.md
- heart/billing/__init__.py（复用 grant/deduct_credits/refund，1 显示币=100 fen，勿新建第二 ledger）
- heart/infra/llm_providers/（base/registry/router/deepseek.py；只加在此，勿碰空壳 infra/llm/）
- heart/ss08_voice/（provider/minimax/mimo/pooled/service/voice_resolver）与 api/wiring.py 的 voice/model 工厂
- heart/api/routes_chat_ws.py（_precheck_billing ~184、_charge_and_insert_bubbles ~265）、routes_voice.py（/clone、_CLONE_COST_FEN）、routes_webhooks.py（已解析 remark）、routes_credits.py（/pricing ~115）
- alembic 当前单头 033_chat_messages_is_proactive（backend/migrations/versions/）

分 7 个独立分支/PR（base=main，一模块一 PR，7 天内可合），构建顺序 B1→B3→B4→B2→B6→B5→B7：
B1 billing/pricing.py（model/tts/action→cost_fen，config 驱动）+ heart/membership/（get_effective_tier 惰性、get_entitlements、assert_*_allowed）+ 扩展 GET /api/credits/pricing + config.py 定价&等级 map。
B3 infra/llm_providers/grok.py（OpenAI 式，镜像 deepseek.py）+ claude.py（anthropic /v1/messages，支持 claude_api_style）+ registry 注册 + ModelRouter 加 stream_for/call_for（按请求 model 覆盖 + failover 链 [claude,grok,deepseek]，返回 served_model）+ config/.env.example 加 GROK/CLAUDE key（占位符）。
B4 routes_chat_ws.py：chat payload 加 model；_precheck_billing 按所选 model 预检；生成前 assert_model_allowed 越权发 model_forbidden 事件不生成；stream_for 拿 served_model；LLM 每 turn 扣一次(key turn:{id}:llm，DeepSeek 0 跳过)、TTS 每语音气泡按 provider 扣(key turn:{id}:tts:{i})；turn_end 回带 served_model+balance+degraded_to。
B2 迁移 034_memberships（user_memberships）+ membership/service.py activate_or_extend（原子延期+月度赠币幂等）+ routes_membership.py GET /api/membership + main.py 注册。
B6 迁移 035_afdian_fulfill（afdian_orders 加 user_id/status/fulfilled_at/fulfillment_type）+ routes_webhooks.py 履约：sign→幂等落单→remark 绑定 user（无匹配 status=unmatched 不丢单）→ config AFDIAN_SKU_MAP→membership.activate_or_extend / billing.grant（key afdian:{out_trade_no}）；绑定码由 user.id 派生（无新列）+ resolve_user_by_binding_code；admin POST /api/admin/afdian/fulfill 手动履约。
B5 ss08_voice/fish_provider.py（Fish 实时 TTS+克隆）+ wiring.py 改 MiMo 导演 primary/MiniMax 最后兜底、Fish 可选 provider + service.py 全失败只回文本不扣 TTS 费 + 迁移 036_voice_providers（character_voices.clone_provider + 幂等种子每性别 5 个 mimo 预设）+ routes_voice.py /clone 接受 provider、克隆费改 config（Fish 100币/MiMo 50币）、assert_tts_allowed/assert_clone_allowed 对免费用户拒 Fish + config/.env.example 加 FISH_AUDIO_API_KEY（占位符）、voice_provider 默认改 mimo。
B7 迁移 037_invites + routes_invite.py（POST /bind、GET /status）+ chat WS 首次成功聊天钩子发 100+100 币（幂等键 invite_base_*:{invitee}）+ 阶段 5→300 / 10→1000（幂等键 invite_stage:{inviter}:{n}）。

铁律：禁 except Exception 静默吞异常（logger.exception+raise）；定价/等级/SKU 全 config 驱动禁硬编码档位；所有入账扣费走现有 ledger + 幂等键 + 原子事务；迁移 down_revision 串 033、名 ≤32 字符、IF NOT EXISTS/ON CONFLICT 幂等、DDL 与回填分离、写 downgrade、禁 import 业务代码；改列后完全重启后端。禁止把 yuoyuocoin_plan.md §9 的真实 API key 写进任何被提交文件（只用 .env 占位符），并在 PR 描述提示这些 key 已泄露需轮换。

每个 PR：先跑 bash scripts/ci.sh 全绿 + alembic upgrade head 干净 + 新增单测（覆盖 backend_plan.md 验收清单对应场景）→ git commit → push → gh pr create（base=main，body 写清改了什么/验收/风险）。完成一个再开下一个，勿堆事实主干。
```
