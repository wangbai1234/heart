# yuoyuo 商业化 — 前后端接口契约（单一真理）

> 状态：规划 · 契约锚点
> 用途：**前端（GPT）与后端（Sonnet）共同锚点**。两侧实现以本文件的字段名/类型/枚举为准；有歧义先改本文件再改代码。
> 依赖：`00_INDEX.md`（定价/等级）、`backend_plan.md`（B1–B7）、`frontend_plan.md`（F1–F6）
> 最后更新：2026-07-18

---

## 0. 通用约定

- BASE_URL = `/api`；除 webhook 外均需 `Authorization: Bearer <access_token>`。
- **金额单位**：对外 JSON 一律 **yuoyuo币（整数，显示单位）**；后端内部存 **fen**（1 币 = 100 fen），API 层 ÷100 输出、×100 入账。
- 时间：ISO-8601 UTC 字符串（如 `2026-08-17T10:00:00Z`）。
- 错误：REST 用 HTTP 状态码 + `{"detail": "<code>"}`；WS 用结构化事件（见 §3）。
- 幂等：所有入账/扣费带 `idempotency_key`（后端保证，前端无需关心）。

### 0.1 枚举常量（前后端硬对齐）
| 概念 | 取值 |
|------|------|
| `tier`（会员等级） | `free` \| `plus`（进阶¥39） \| `immersive`（沉浸¥79） |
| `model`（文字模型） | `deepseek` \| `grok` \| `claude` |
| `tts_provider` | `mimo` \| `fish` \| `minimax` |
| `clone_provider` | `mimo` \| `fish` |
| `credit_transaction.type` | `grant` \| `redeem` \| `consume_llm` \| `consume_tts` \| `consume_clone` \| `refund` \| `adjust` \| `invite` \| `membership_grant` |

### 0.2 定价表（契约，配置驱动，展示单位=币）
| key | model/provider/action | 币 | fen |
|-----|----------------------|----|-----|
| `deepseek` | 文字 | 0 | 0 |
| `grok` | 文字 | 3 | 300 |
| `claude` | 文字 | 12 | 1200 |
| `mimo` | TTS | 5 | 500 |
| `fish` | TTS | 8 | 800 |
| `clone_mimo` | 声音克隆 | 50 | 5000 |
| `clone_fish` | 声音克隆 | 100 | 10000 |

### 0.3 等级权益（契约）
| tier | models | tts | clone | 月度赠币 |
|------|--------|-----|-------|---------|
| `free` | [deepseek] | [mimo] | [] | 0 |
| `plus` | [deepseek, grok] | [mimo, fish] | [mimo, fish] | 400 |
| `immersive` | [deepseek, grok, claude] | [mimo, fish] | [mimo, fish] | 800 |

---

## 1. REST 端点

### 1.1 `GET /api/credits/pricing`（扩展现有）
> 前端 F2/F3/F4/F6 唯一定价来源，**禁前端硬编码**。展示单位=币。

响应 200：
```json
{
  "signup_grant": 100,
  "models": [
    {"id": "deepseek", "label": "DeepSeek", "cost": 0,  "tiers_allowed": ["free","plus","immersive"]},
    {"id": "grok",     "label": "Grok",     "cost": 3,  "tiers_allowed": ["plus","immersive"]},
    {"id": "claude",   "label": "Claude",   "cost": 12, "tiers_allowed": ["immersive"]}
  ],
  "actions": [
    {"id": "tts_mimo",   "label": "MiMo 语音",  "cost": 5},
    {"id": "tts_fish",   "label": "Fish 语音",  "cost": 8},
    {"id": "clone_mimo", "label": "MiMo 克隆",  "cost": 50},
    {"id": "clone_fish", "label": "Fish 克隆",  "cost": 100}
  ],
  "membership_tiers": [
    {"tier": "free",      "label": "体验用户", "price": 0,  "monthly_grant": 0,
     "models": ["deepseek"], "tts": ["mimo"], "clone": [],
     "benefits": ["DeepSeek 无限文字", "MiMo 语音", "永久记忆", "注册赠 100 币"]},
    {"tier": "plus",      "label": "进阶版",   "price": 39, "monthly_grant": 400, "sku": "plan_plus",
     "models": ["deepseek","grok"], "tts": ["mimo","fish"], "clone": ["mimo","fish"],
     "benefits": ["解锁 Grok", "Fish 语音", "自建角色克隆", "每月赠 400 币"]},
    {"tier": "immersive", "label": "沉浸版",   "price": 79, "monthly_grant": 800, "sku": "plan_immersive",
     "models": ["deepseek","grok","claude"], "tts": ["mimo","fish"], "clone": ["mimo","fish"],
     "benefits": ["解锁 Claude", "Fish 语音", "自建角色克隆", "每月赠 800 币"]}
  ],
  "shop": [
    {"sku": "pack_6",   "label": "小份补给", "price": 6,   "credits": 60,   "bonus": 0},
    {"sku": "pack_18",  "label": "陪伴补给", "price": 18,  "credits": 220,  "bonus": 20},
    {"sku": "pack_48",  "label": "深度补给", "price": 48,  "credits": 650,  "bonus": 170},
    {"sku": "pack_128", "label": "长期陪伴", "price": 128, "credits": 2000, "bonus": 720}
  ],
  "afdian_url": "https://afdian.com/a/yuoyuo"
}
```
> 说明：`credits` 为该挡到账**总币数**（已含 `bonus`）；`bonus` 仅用于展示「赠送 X」。

### 1.2 `GET /api/membership`
响应 200：
```json
{
  "tier": "plus",
  "expires_at": "2026-08-17T10:00:00Z",   // free 时为 null
  "monthly_grant": 400,
  "entitlements": {
    "models": ["deepseek","grok"],
    "tts": ["mimo","fish"],
    "clone": ["mimo","fish"]
  },
  "binding_code": "YQ7X2K9A"               // 爱发电备注填写此码
}
```
> `tier` 为**惰性生效值**（`now < expires_at ? tier : "free"`）。前端 `membershipStore` 消费。

### 1.3 `GET /api/invite/status`
响应 200：
```json
{
  "invite_code": "YQ7X2K9A",
  "invite_url": "https://yuoyuo.app/login?invite=YQ7X2K9A",
  "invited_count": 3,               // 有效邀请数（已完成首聊）
  "pending_count": 1,               // 已注册未首聊
  "total_reward": 300,              // 累计获得币
  "stages": [
    {"threshold": 5,  "bonus": 300,  "reached": false},
    {"threshold": 10, "bonus": 1000, "reached": false}
  ]
}
```

### 1.4 `POST /api/invite/bind`
请求：`{"code": "YQ7X2K9A"}`
响应 200：`{"ok": true}` ／ 4xx `{"detail": "invalid_code | already_bound | self_invite"}`
> 登录后若 URL 带 `?invite=`，前端调用一次。首聊奖励由后端在首次成功 turn 触发，前端无需管。

### 1.5 `GET /api/voice/presets?gender=male|female`
响应 200（本次每性别 **5 个 MiMo 预设**）：
```json
{
  "presets": [
    {"id":"mimo_male_calm","name":"沉稳","description":"低沉稳重","provider":"mimo","gender":"male","sample_url":"/api/voice/presets/mimo_male_calm/sample"}
    // ... 共 5 个
  ]
}
```
> `provider` 字段前端展示为标签。试听走现有 `GET /api/voice/presets/{id}/sample`（blob）。

### 1.6 `POST /api/voice/clone`（multipart，扩展现有）
请求：`multipart/form-data` — `character_id`、`file`（音频 ≤20MB）、**新增 `provider`**（`mimo|fish`，缺省 `mimo`）。
响应 200：`{"ok": true, "clone_status": "processing", "balance": 350}`（成功后异步克隆完成才扣费）
错误：
- 402 `{"detail":"insufficient_credits"}`（余额 < 该 provider 克隆费）
- 403 `{"detail":"tier_forbidden"}`（免费用户请求 `fish`；前端已置灰，这是后端兜底）
> 费用：`clone_mimo`=50 币、`clone_fish`=100 币（来自 pricing）。

### 1.7 `POST /api/webhooks/afdian`（无鉴权，sign 校验）
爱发电服务器回调。后端：校验 sign → 幂等落 `afdian_orders` → 解析 `remark` 匹配 `binding_code`/email → 按 `AFDIAN_SKU_MAP` 履约（会员延 30 天+月度赠币 / 币包 grant，幂等键 `afdian:{out_trade_no}`）→ 无匹配置 `status=unmatched`。
响应恒 200：`{"ec": 200, "em": "success"}`（爱发电要求）。
> 前端不直接对接；用户在爱发电备注填 `binding_code` 即可。

### 1.8 `POST /api/admin/afdian/fulfill`（`X-Admin-Key`）
请求：`{"out_trade_no": "...", "user_id": "..."}` — 人工把 `unmatched` 订单指派给用户并履约。响应 `{"ok": true, "fulfilled": {"type":"membership|coins", ...}}`。

---

## 2. WebSocket 聊天协议 `/api/chat/ws?token=<access_token>`

### 2.1 客户端 → 服务端（`chat`，**新增 `model`**）
```json
{"type":"chat","text":"...","character_id":"rin","turn_id":"<uuid>","voice_enabled":true,"model":"grok"}
```
> `model` 缺省 `deepseek`。前端按 `membershipStore.entitlements.models` 置灰不可选项，但后端仍二次校验。

### 2.2 服务端 → 客户端事件（新增/变更加粗）
| event `type` | 载荷 | 说明 |
|--------------|------|------|
| `turn_start` | `{turn_id}` | 现有 |
| `text_delta` | `{turn_id, delta}` | 现有 |
| `sentence` | `{turn_id, text}` | 现有 |
| `audio_chunk` | `{turn_id, seq, b64}` | 现有 |
| `message_bubble` | `{turn_id, kind, text, credits_charged}` | 现有；`kind`=`text\|action\|voice` |
| **`turn_end`** | `{turn_id, balance, served_model, degraded_to?}` | **新增 `served_model`**（实际服务模型）+ **`degraded_to`**（发生 failover 时=最终模型，否则缺省）；`balance` 单位=币 |
| **`insufficient_credits`** | `{needed, balance}` | 现有；余额不足未生成，引导 `/wallet` |
| **`model_forbidden`** | `{model, required_tier}` | **新增**；越权选用模型，引导 `/membership` |
| `interrupted` | `{turn_id}` | 现有 |
| `error` | `{message}` | 现有；**技术错误不展示给用户**（LLM/TTS 已内部降级） |

### 2.3 计费与降级语义（前端只需按事件反应）
- **LLM**：每 turn 一次调用，按 `served_model` 扣（DeepSeek=0）。若 `degraded_to` 存在（Claude→Grok→DeepSeek 兜底），按最终模型计费 → 前端可轻提示「已切换到 {degraded_to}」，**不显技术错误**。
- **TTS**：每语音气泡按实际 `tts_provider` 扣；全失败则只回文本、无 `audio_chunk`、不扣 TTS 费（**永不阻塞文本**）。
- `turn_end.balance` → 前端 `creditsStore.setBalance` 静默同步。

---

## 3. 错误 / 结构化事件对照（前端处置）
| 场景 | 通道 | code/event | 前端动作 |
|------|------|-----------|---------|
| 余额不足 | WS / REST 402 | `insufficient_credits` | 「币不足」Dialog → `/wallet` |
| 模型越权 | WS | `model_forbidden` | 「需会员」Dialog → `/membership` |
| Fish 克隆越权 | REST 403 | `tier_forbidden` | Toast + 跳 `/membership`（前端已置灰兜底） |
| 邀请码无效 | REST 4xx | `invalid_code/already_bound/self_invite` | Toast 分文案 |
| LLM/TTS 内部失败 | 后端内部 | —（已降级） | 无感知；仅 `degraded_to` 轻提示 |

---

## 4. 前端 store ↔ 端点映射（消费关系）
| store / 页面 | 端点 |
|--------------|------|
| `creditsStore.balance` | `GET /api/credits/balance`（现有）+ WS `turn_end.balance` |
| `membershipStore` | `GET /api/membership`（tier/entitlements/binding_code） |
| Pricing（F2/F3/F4/F6） | `GET /api/credits/pricing` |
| `/wallet` 商城 | `getPricing().shop` |
| `/membership` | `getPricing().membership_tiers` + `getMembership()` |
| `/invite` | `GET /api/invite/status` + `POST /api/invite/bind` |
| 聊天模型选择器 | `getPricing().models` + `membershipStore.entitlements.models` + WS `model` |
| 音色第3步 | `GET /api/voice/presets?gender=` + `POST /api/voice/clone{provider}` |

---

## 5. 契约变更纪律
- 任一侧需改字段名/枚举/结构 → **先在本文件改并 @ 对侧**，再落代码。
- 后端每个新端点 PR 的 body 必须声明「符合 api_contract.md §X」；不符则 reviewer reject。
- 前端 mock 阶段按本文件造假数据，后端上线后仅替换数据源、不改组件契约。
