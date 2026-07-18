# yuoyuo 商业化体系 V1.0 — 会员 + yuoyuo币 + 多模型（总体设计）

> 状态：规划（Planning）· 待落地
> 来源：`docs/yuoyuocoin_plan.md`（V1.0 商业化方案）+ 三份逐文件核实的代码勘察
> 依赖：现有商业外壳（`docs/upgrade/commercial/`，PR #86 起已合并）——真实用户、credits ledger、语音系统、爱发电对账
> 交付：前端交 GPT（见 `frontend_plan.md`）、后端交 Sonnet（见 `backend_plan.md`）
> 最后更新：2026-07-18

---

## 0. 阅读顺序

| 文件 | 内容 | 执行方 |
|------|------|--------|
| `00_INDEX.md`（本文） | 货币模型 · 等级矩阵 · 定价 · 迁移清单 · 时序 · 构建顺序 · 风险 · 验收 | 先读 |
| `api_contract.md` | **前后端接口契约（单一真理）**：REST + WS 字段/枚举/定价 | 前后端共读 |
| `backend_plan.md` | 后端 7 个 PR（B1–B7）+ 末尾 **Sonnet 执行 Prompt** | Sonnet |
| `frontend_plan.md` | 前端 6 个模块（F1–F6）+ 末尾 **GPT 执行 Prompt** | GPT |

> **产品名对外恒为 `yuoyuo`**（全小写）；`心屿 / Heart` 仅内部代号，用户可见文案禁止出现。

---

## 1. 现状真相（Grounded Baseline — 逐文件核实，落地以此为准）

**不要从零搭建计费**——商业外壳已成熟，本次是在其上叠加会员 + 多模型 + 支付闭环。

### 1.1 后端（`backend/heart/`）
- **credits ledger 已成熟**：`heart/billing/__init__.py` = `get_balance / grant / redeem / charge_turn / deduct_credits(amount, idempotency_key, type) / refund`。全部原子 CTE（同事务更新 `users.credits_balance` + 插入 `credit_transactions`）+ 幂等键 + `InsufficientCreditsError`。内部单位 **fen**，1 显示积分 = 100 fen；API 层 ÷100 展示。
- **对账 worker**：`workers/credit_reconciliation_worker.py` 每小时校验 `users.credits_balance == COALESCE(SUM(credit_transactions.delta), 0)`。
- **LLM 抽象干净但只有 DeepSeek**：`infra/llm_providers/`（`base.py` 抽象类、`registry.py` model→provider、`router.py` `ModelRouter` 定死 main/cheap、`deepseek.py`/`deepseek_pro.py`、`pool.py`）。⚠️ **债务：`infra/llm/` 是空壳，勿动；新 provider 只加在 `infra/llm_providers/`**（AGENTS.md）。
- **语音双 provider**：`ss08_voice/`（`provider.py` Protocol、`minimax_provider`/`mimo_provider`/`pooled_provider`、`service.py` `synthesize_with_fallback`、`voice_director.py` 韵律导演、`voice_resolver.py` 读 DB）。当前 wiring **MiniMax 优先、MiMo 兜底**；**克隆恒走 MiniMax**；clone 费 = `_CLONE_COST_FEN = 80_000`（800 币）。
- **会员 / 订阅 / tier：全空白**（greenfield）。用户表无 plan/tier 列。
- **支付**：`routes_webhooks.py POST /api/webhooks/afdian` 仅校验 sign + 幂等落 `afdian_orders` **对账，不加币**（注释「Credits are added via redemption codes」）。**已解析 `remark` 字段**。
- **迁移线性单头** `033_chat_messages_is_proactive`；本次新增从 `034` 起。

### 1.2 前端（`web/src/`）
- React 19 + Vite + Tailwind v4 + zustand + react-router v7；PWA。
- `services/api.ts` 已有 **`getPricing()`（已定义、未被任何 UI 调用）**，返回 `{signup_grant, per_text, per_voice, afdian_url, tiers}`——现成挂点。
- store：`creditsStore`（`balance`）、`authStore`（`user.credits_balance`）、`chatStore`（`insufficientCredits`）、`appStore`、`toastStore`、`themeStore`。
- **无** coin/会员/模型选择/邀请 UI；只有单一 `积分` 概念。
- 音色第 3 步 `pages/CreateCharacterPage.tsx`：预设区 = 扁平 `presets.map()`（~837-912，后端返回什么就渲染什么，无分组/无固定数量）；克隆区 = **单一**上传块（~914-991，仅 MiniMax/mimo 克隆，无 Fish、无置灰）。`PresetVoiceDTO` 已含 `provider/gender` 字段但 UI 未展示。

### 1.3 结论
本次 = 在成熟计费/语音之上叠加：**会员等级 + 多模型选择计费 + Fish 语音 + 爱发电自动履约 + 邀请**。陪伴引擎（SS01–08）不改。

---

## 2. 货币模型（已决策）

**yuoyuo币 = 复用现有 credits，不新建第二货币。**

- **1 yuoyuo币 = 1 显示积分 = 100 fen**。
- 复用整套 ledger（`credit_transactions` + `users.credits_balance`）、`deduct_credits/grant/refund`、对账 worker。
- 仅改**显示层文案**（前端「积分」→「yuoyuo币」）与**定价数据**。
- 注册赠币 = 100 币（现 `signup_grant_credits = 10000` fen = 100 币，**已匹配，无需改**）。

> 好处：0 迁移风险，复用幂等/原子/对账全套保障；坏处：无。

---

## 3. 用户等级矩阵（会员体系）

| | 免费（体验） | 进阶版 ¥39/月 | 沉浸版 ¥79/月 |
|---|---|---|---|
| **文字模型** | DeepSeek（免费无限） | DeepSeek + **Grok** | DeepSeek + Grok + **Claude** |
| **TTS** | MiMo | MiMo + **Fish Audio** | MiMo + **Fish Audio** |
| **声音克隆** | ❌ | MiMo 克隆 + **Fish 克隆** | MiMo 克隆 + **Fish 克隆** |
| **永久记忆** | ✓ | ✓ | ✓ |
| **月度赠币** | — | **400 币 / 30 天** | **800 币 / 30 天** |
| **高级模型优先调用** | — | ✓ | ✓ |

> **已确认**：沉浸版为进阶版超集（同时解锁 Grok 与 Claude）。等级权益以 config map 驱动，不硬编码于业务逻辑。

---

## 4. 定价表（配置驱动，币 ×100 = fen）

### 4.1 AI 能力按次消耗
| 动作 | 成本估算 | yuoyuo币 / 次 | 备注 |
|------|---------|--------------|------|
| DeepSeek 文字 | ≈0 | **0**（不扣） | 免费无限，降低流失 |
| Grok 文字 | ≈¥0.012 | **3** | OpenAI 式 `/v1/chat/completions` |
| Claude 文字 | ≈¥0.8 | **12** | anthropic `/v1/messages`，成本高需保护 |
| MiMo TTS | ≈0 | **5** | 导演模式主力 |
| Fish Audio TTS | ≈¥0.3 | **8** | 付费门槛 |
| MiMo 声音克隆 | — | **50** | 文档未定价，已定 50 币 |
| Fish 声音克隆 | ≈¥5 | **100** | 高价值功能（现状 clone=800币，改此值） |

> 计费粒度：**LLM 每 turn 一次调用扣一次**（按**实际服务模型**，failover 降级到 DeepSeek 则 0）；**TTS 按 provider 每语音气泡扣**。均走 `deduct_credits` + 幂等键。

### 4.2 邀请奖励
- 注册赠 **100 币**（每用户一次，幂等）。
- 有效邀请（好友注册 + 完成首次聊天）：邀请人 **+100**、新人 **+100**。
- 阶段奖励：邀请 5 人 **+300**；邀请 10 人 **+1000**（幂等键 `invite_stage:{inviter}:{5|10}`）。

---

## 5. 商城与会员挡位（爱发电 SKU）

### 5.1 yuoyuo币商城
| 商品 | 价格 | 到账 | 赠送 |
|------|------|------|------|
| ☕ 小份补给 | ¥6 | 60 币 | — |
| 🌙 陪伴补给 | ¥18 | 220 币 | +20 |
| ⭐ 深度补给 | ¥48 | 650 币 | +170 |
| 🌌 长期陪伴 | ¥128 | 2000 币 | +720 |

### 5.2 会员订阅
| 商品 | 价格 | 权益 |
|------|------|------|
| 进阶版 | ¥39 | 进阶等级 30 天 + 赠 400 币 |
| 沉浸版 | ¥79 | 沉浸等级 30 天 + 赠 800 币 |

> 挡位/价格由运营调，代码只认 config 的 SKU→权益 map，不硬编码档位。

---

## 6. 数据库迁移清单（034–037，线性串 033）

| 迁移 | 表/变更 | 模块 |
|------|---------|------|
| `034_memberships` | `user_memberships`（user_id、tier、status、started_at、expires_at、source、last_grant_at） | B2 |
| `035_afdian_fulfill` | `afdian_orders` 加 `user_id / status / fulfilled_at / fulfillment_type` | B6 |
| `036_voice_providers` | `character_voices.clone_provider`；幂等种子**每性别 5 个 MiMo 预设音色**（provider='mimo'） | B5 |
| `037_invites` | `invites`（inviter_id、invitee_id UNIQUE、code、status、bound_at、first_chat_at、base_rewarded_at） | B7 |

规范：`down_revision` 串前一迁移；revision 名 ≤32 字符；`IF NOT EXISTS`/`ON CONFLICT DO NOTHING` 幂等；DDL 与数据回填分离；写 `downgrade`；迁移内禁 `import heart.xxx`（只用 `sqlalchemy.text`）。

---

## 7. 端到端时序（商业化后一次完整会话）

```
免费用户 DeepSeek 免费聊天（0 币，永久无限）
        ↓ 想用更聪明的模型
聊天顶栏点模型选择器 → Grok/Claude 置灰 + 「升级会员」
        ↓
会员页 /membership → 展示【绑定码】+ 备注填写指引 + 去爱发电按钮
        ↓
爱发电购买「进阶版 ¥39」，备注填入绑定码
        ↓
爱发电 webhook → 校验 sign → 幂等落单 → 解析 remark 绑定 user
        → SKU 映射：进阶等级 +30天 + 赠 400 币（原子幂等 key=afdian:{out_trade_no}）
        ↓
用户回 app：会员状态卡显示「进阶 · 至 X」，币余额 +400
        ↓
聊天选 Grok → 后端校验权益通过 → 生成 → turn 成功扣 3 币 → turn_end 回带 served_model+balance
        ↓（若 Claude/Grok 异常）
静默 failover Claude→Grok→DeepSeek，按实际服务模型计费，不显技术错误
        ↓
自建角色第 3 步：Fish 音色/克隆已解锁（免费用户置灰）
```

---

## 8. 异常降级策略

- **LLM**：优先级 Claude → Grok → DeepSeek。高级模型失败自动降级，**用 DeepSeek 兜底回复，不展示技术错误**；按**实际服务模型**计费。
- **TTS**：文本生成成功 → TTS（选定 provider → MiMo → MiniMax）→ 全失败则**直接返回文本内容**，语音失败**永不阻塞文本**、不扣 TTS 费。

---

## 9. 构建顺序

- **后端**：B1（定价+权益内核）→ B3（多模型 provider）→ B4（按模型计费）→ B2（会员表/API）→ B6（爱发电自动履约）→ B5（Fish+MiMo导演+音色）→ B7（邀请）。
- **前端**：F1（文案改造，可即刻起）；F2/F3 依赖 B1/B2/B6；F4 依赖 B3/B4；F6 依赖 B5；F5 依赖 B7。
- 一模块一分支一 PR，base=main，7 天内可合（`.claude/CLAUDE.md`）。CI 配置变更与业务变更分开 PR。

---

## 10. 风险与红线

- ⚠️ **密钥泄露**：`docs/yuoyuocoin_plan.md` §9 明文粘贴了 Grok / Claude / MiMo / Fish 真实 key。**任何被提交文件只用 `.env` 占位符**；这些 key 已明文暴露，**上线前必须轮换**。
- **爱发电 webhook 对应易错**：备注绑定失败的订单落库置 `status=unmatched`，提供 admin 手动履约端点，**绝不静默丢单**。
- **退款**：自动履约不含退款，落 order + 人工 admin 处理。
- **既有行为变更**：现状每条文本扣 0.5 币（`credits_cost_text_message=50`）→ 新方案 DeepSeek 文本 **0 币无限**；现状 clone 800 币 → 改 config。上线需公告。
- **DB 铁律**（`.claude/CLAUDE.md`）：多 head 显式逐个 upgrade；改列后完全重启后端（非 --reload）；禁 `except Exception:` 静默吞异常。

---

## 11. 验收总纲

- 后端 `bash scripts/ci.sh` 全绿；`alembic upgrade head` 干净 + 有 downgrade；新端点单测（mock LLM/TTS/webhook）；对账 `SUM(delta)==balance`。
- 前端 `npm run build` 通过；light + dark 双主题；模型选择器按 tier 置灰；音色第 3 步 5/性别 + Fish 置灰。
- E2E：见 §7 全链路可跑通。

各模块细化验收见 `backend_plan.md` / `frontend_plan.md`。
