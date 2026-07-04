# 模块 3 · 积分系统（Credits）+ 爱发电兑换（构建顺序 ②）

> 依赖：模块 4（`users` 表、真实身份）。
> 现状：**零基础**——无任何 credits/transaction/redemption/payment 表或路由，仅 `config.py` 有未引用的 Stripe 占位符。前端会员/积分 UI 全是硬编码假字符串。
> 定位：不是订阅会员，是**积分制（credits）**；积分来源 = 爱发电赞助 → 兑换码。

---

## 1. 计费模型（Pricing Model）

### 1.1 消耗单价（env 可调，默认值）
| 动作 | credits | 依据 |
|------|---------|------|
| 一次文本 AI 回复（text turn 成功） | `CREDITS_PER_TEXT_TURN=1` | DeepSeek 便宜，1 分/回合足够覆盖 |
| 一次语音 AI 回复（voice turn，含 TTS） | `CREDITS_PER_VOICE_TURN=5` | TTS 显著更贵（MiMo ≈ len×0.02 分/字）；含文本生成 |

规则：
- **按成功的 AI 回复扣费**，不按用户发送扣。turn 失败/被安全拦截（RED/PURPLE care path）**不扣费**。
- voice turn = 文本 + TTS 一次性计 5（不叠加 text 的 1）。
- 扣费在 turn 成功收尾时**一次性原子扣**，金额随 turn 实际 modality 决定（语音真出了音频才算 voice）。

### 1.2 赠送与充值挡位
- **注册赠分**：`SIGNUP_GRANT_CREDITS=100`（≈ 100 条文本或 20 条语音），每用户一次（幂等）。
- **爱发电挡位 → credits**（在爱发电后台配置商品名，此处为兑换码面额建议）：

| 赞助档 | 价格 | 兑换码面额 credits | 约合 |
|--------|------|--------------------|------|
| 尝鲜 | ¥6 | 300 | ~300 文本 / 60 语音 |
| 常用 | ¥30 | 1800（含 +200 赠） | 约 6 折单价 |
| 超值 | ¥68 | 4500（含 +700 赠） | 更优 |
| 豪华 | ¥128 | 9000（含 +1600 赠） | 最优 |

> 面额与价格由运营调；代码只认 `redemption_codes.credits_value`，不硬编码档位。

### 1.3 余额不足策略
- turn 开始**预检**余额：`balance < 本次预计花费` → 不进入生成，返回 `insufficient_credits` 事件（WS）/402（REST），前端引导去 `/redeem`。
- 预计花费 = 该角色 `voice_enabled ? CREDITS_PER_VOICE_TURN : CREDITS_PER_TEXT_TURN`。
- （可选，默认关）每日免费额度 `DAILY_FREE_CREDITS`：留 env 位，MVP 关闭。

## 2. 兑换与充值流程

### 2.1 主路径：兑换码池（爱发电「自动发卡」）
```
运营：批量生成 redemption_codes（status=active, credits_value, batch_id）
     → 导出 CSV → 上传爱发电"自动发卡"商品库存
用户：爱发电赞助 → 平台自动发一个未售码（邮件/页面）
用户：回 app /redeem 输码 → POST /api/credits/redeem { code }
后端：锁行(SELECT ... FOR UPDATE) → 校验 active & 未过期 & 未被兑
     → 事务内：redemption_codes 置 redeemed(by=user, at=now)
              + credit_transactions(type=redeem, delta=+value, idempotency=code)
              + users.credits_balance += value
     → 返回新余额
```

### 2.2 次路径：爱发电 Webhook 对账（可选，防伪 + 库存核销）
```
爱发电 → POST /api/webhooks/afdian
后端：校验 sign（md5(拼接参数 + AFDIAN_WEBHOOK_TOKEN)，见爱发电文档）
     → 幂等：afdian_orders.out_trade_no UNIQUE，重复直接 200
     → 记录订单（金额/SKU/时间/买家备注）用于对账与风控
     → 返回 {"ec":200}
```
> Webhook **不直接给用户加分**（爱发电订单无法可靠对应到 app 内 user）；仅用于「哪些码已售/异常订单」对账与防刷分析。加分只经兑换码路径，保证「码 = 唯一记账凭证」。

## 3. 数据模型（迁移 `012_credits_and_redemption.py`）

### 3.1 `credit_transactions`（append-only 台账，唯一真相）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID | PK |
| user_id | UUID | FK→users, INDEX |
| delta | BIGINT | 正=入账，负=消费 |
| balance_after | BIGINT | 写入后余额快照（审计）|
| type | TEXT | `grant/redeem/consume_text/consume_voice/refund/adjust` |
| ref_type | TEXT | 可空：`turn/redemption/afdian/manual` |
| ref_id | TEXT | 可空：turn_id / code / order_no |
| idempotency_key | TEXT | UNIQUE NOT NULL（防重复入账/扣费）|
| metadata | JSONB | 可空 |
| created_at | TIMESTAMPTZ | default now(), INDEX(user_id, created_at DESC) |

- 幂等键约定：赠分 `signup_grant:{user_id}`；兑换 `redeem:{code}`；消费 `turn:{turn_id}`。
- **余额一致性**：任何写台账的操作必须在**同一 DB 事务**内 `UPDATE users SET credits_balance = credits_balance + :delta WHERE id=:uid AND credits_balance + :delta >= 0`；受影响行=0（会破负）→ 回滚 + 402。

### 3.2 `redemption_codes`
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID | PK |
| code | TEXT | UNIQUE NOT NULL（12 位，去混淆字符集 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`）|
| credits_value | BIGINT | NOT NULL, >0 |
| batch_id | TEXT | INDEX，批次追溯 |
| status | TEXT | `active/redeemed/disabled`，default active |
| redeemed_by | UUID | 可空 FK→users |
| redeemed_at | TIMESTAMPTZ | 可空 |
| expires_at | TIMESTAMPTZ | 可空（可永久）|
| created_at | TIMESTAMPTZ | default now() |

索引：`UNIQUE(code)`；`INDEX(status)`；`INDEX(batch_id)`。

### 3.3 `afdian_orders`（对账）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID | PK |
| out_trade_no | TEXT | UNIQUE NOT NULL（幂等）|
| plan_id | TEXT | 可空 |
| sku_detail | JSONB | 可空 |
| total_amount | NUMERIC(10,2) | |
| remark | TEXT | 买家留言（可能含 app 内标识）|
| raw_payload | JSONB | 原始报文留档 |
| received_at | TIMESTAMPTZ | default now() |

## 4. API 设计

`backend/heart/api/routes_credits.py`（prefix `/api/credits`，均需 Bearer 除 webhook）：

| Method | Path | 限流 | Body | 返回 |
|--------|------|------|------|------|
| GET | `/balance` | 60/min | — | `{balance}` |
| GET | `/transactions?cursor&limit` | 60/min | — | `{items:[{delta,type,ref_type,balance_after,created_at}], next_cursor}` |
| POST | `/redeem` | 10/min + 每用户每分钟 5 次 | `{code}` | `{ok, credited, balance}` / 4xx |
| GET | `/pricing` | 60/min | — | `{signup_grant, per_text, per_voice, tiers:[...], afdian_url}` |

`backend/heart/api/routes_webhooks.py`（prefix `/api/webhooks`）：
| Method | Path | 说明 |
|--------|------|------|
| POST | `/afdian` | 校验 sign → upsert `afdian_orders`（幂等）→ 返回 `{"ec":200}` |

内部服务 `backend/heart/billing/service.py`：`grant/redeem/charge_turn/refund/get_balance`，全部走 §3.1 原子事务 + 幂等键。供 orchestrator（模块1）调用 `charge_turn`。

运营脚本 `backend/scripts/gen_redemption_codes.py`：`--count N --value C --batch B --expires ISO` → 写库 + 导出 CSV 供上传爱发电。

## 5. 消耗策略与接入点（与模块1 对接）
- **预检**（turn 开始）：orchestrator/WS 调 `billing.get_balance(user_id)` 与预计花费比较；不足 → 发 `insufficient_credits` 事件，不生成。
- **扣费**（turn 成功收尾）：调 `billing.charge_turn(user_id, turn_id, modality)`，幂等键 `turn:{turn_id}`。同一 turn 重复回调不会重复扣。
- **不扣费**：安全拦截、生成异常、fallback 兜底回复（`_FALLBACK_MESSAGES`）——由 orchestrator 结果标志决定。

## 6. 防刷 / 风控（Risk）
1. **兑换码**：单次有效（行锁 + status 检查）；错误码尝试限流（每用户 5/min）；码集去混淆字符 + 足够熵（12 位 base32 ≈ 60bit）；批次可 `disabled` 一键作废。
2. **台账幂等**：所有入账/扣费带 `idempotency_key UNIQUE`，天然去重（并发/重试安全）。
3. **余额不破负**：DB 层 `CHECK(credits_balance>=0)` + 条件 UPDATE，双保险。
4. **赠分一次**：`signup_grant:{user_id}` 幂等，禁止多设备/重登刷赠分。
5. **Webhook 校验**：强制 sign 校验 + `out_trade_no` 幂等；异常订单落 `afdian_orders` 供人工核查。
6. **对账任务**：定时校验 `sum(delta) == users.credits_balance`，不一致告警（Prometheus `credit_balance_drift_total`）。
7. **速率**：redeem 与 webhook 均限流；WS turn 扣费天然受 chat 限流约束。

## 7. 前端改造
- `web/src/stores/creditsStore.ts`（新增，不持久化，登录后拉取）：`balance:number`，`refresh()` 调 `GET /api/credits/balance`；turn 成功后 WS 回带新余额则同步。
- `web/src/services/api.ts` 增 `getBalance/getTransactions/redeem(code)/getPricing`。
- `web/src/pages/RedeemPage.tsx`（现为 mock）：接真实 `redeem`——`OTPInput length=12 groupSize=4`（已支持）；成功 `Toast` + 更新 `creditsStore` + 返回来源页；失败区分「无效/已用/过期」文案。保留「去爱发电 →」外链 `AFDIAN_SPONSOR_URL`。
- **余额展示**：`SettingsPage` 会员卡改为**真实积分余额**（替换硬编码"会员 · 至 2026-12-31"）；新增「积分明细」入口 → `TransactionsPage`（`/credits/transactions`，列表 + 无限滚动，复用 `Skeleton`）。
- **余额不足引导**：Chat 收到 `insufficient_credits` → `Dialog`「积分不足，去兑换？」→ `/redeem`。

## 8. 验收
- 生成码 → redeem → 余额+面额、`credit_transactions` 有 redeem 行、码转 redeemed。
- 同码二次 redeem 被拒（已用）；并发 redeem 同码只成功一次。
- 文本 turn 扣 1、语音 turn 扣 5；同 turn_id 重复扣费幂等无副作用。
- 余额为 0 时发起 turn → `insufficient_credits`，不产生回复、不扣费。
- Webhook 重复 out_trade_no 幂等返回 200，仅一条 `afdian_orders`。
- 对账任务：ledger 之和 == 缓存余额。

---

## ⚙️ Mimo 执行 Prompt（复制交付）

```
你在 Heart 仓库（对外名 yuoyuo）实现「模块3：积分系统 + 爱发电兑换」。分支 feat/credits-afdian，base=main。依赖模块4的 users 表与真实身份，先确认 011 迁移已在。严格按 docs/upgrade/commercial/02_credits_afdian.md。

后端：
1. 迁移 012_credits_and_redemption.py：建 credit_transactions（append-only，idempotency_key UNIQUE，balance_after 快照）/ redemption_codes（code UNIQUE 12位去混淆字符集）/ afdian_orders（out_trade_no UNIQUE）。字段严格按 §3。写 downgrade。
2. backend/heart/billing/service.py：grant/redeem/charge_turn/refund/get_balance。所有入账扣费在同一事务内：写台账 + 条件 UPDATE users.credits_balance（+delta 且 >=0，受影响0行则回滚报余额不足）+ 幂等键（signup_grant:{uid} / redeem:{code} / turn:{turn_id}）。
3. routes_credits.py（/api/credits）：GET /balance、GET /transactions(游标分页)、POST /redeem（行锁 SELECT FOR UPDATE + status 校验 + 每用户5/min 限流）、GET /pricing。限流按 §4。
4. routes_webhooks.py（/api/webhooks/afdian）：校验爱发电 sign(md5)、afdian_orders 幂等 upsert、返回 {"ec":200}。webhook 不直接加分。
5. backend/scripts/gen_redemption_codes.py：--count/--value/--batch/--expires → 写库 + 导出 CSV。
6. .env.example 增补 §2.5 Credits/Afdian 段。对账定时任务（校验 sum(delta)==balance）与 Prometheus 指标。
7. 预留 orchestrator 接入点：billing.get_balance 预检 + billing.charge_turn 收尾扣费（模块1 会调用，本模块先提供并单测）。

前端：
8. creditsStore.ts（登录后拉余额）；services/api.ts 增 getBalance/getTransactions/redeem/getPricing。
9. RedeemPage.tsx 接真实 redeem（复用 OTPInput length12 groupSize4），成功 Toast+更新余额，失败区分无效/已用/过期。保留去爱发电外链。
10. SettingsPage 会员卡换真实积分余额；新增 TransactionsPage(/credits/transactions) 明细列表。

约束：不硬编码档位（只认 code.credits_value）；不硬编码颜色（用 tokens.css）；light+dark 双验收。测试覆盖 §8 全部场景（含并发同码只成功一次、扣费幂等、余额不破负、webhook 幂等）。完成后 ci.sh 全绿、alembic upgrade heads 干净、npm run build 通过，开 PR。
```
