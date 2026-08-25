# 邀请裂变 + 抽奖 + 返佣 — 工程拆解（执行文档）

> 面向执行者（其他模型/工程师）。产品方案见 [`invite_lottery_commission_v1.md`](invite_lottery_commission_v1.md)，本文只讲**怎么落地**：数据表、迁移、API 契约、前端页面、PR 边界、幂等规范。
>
> **执行前必读**：本文引用的现状（迁移 head、函数签名、字段）都已核对过，但你在动手前仍须 `git ls-tree` / `Read` 复核，禁止凭本文推断。若发现现状与本文不符，停下报告，不要硬改。
>
> 最后更新：2026-08-25

---

## 0. 现状基线（已核对，动手前复核）

| 事项 | 现状 | 位置 |
|---|---|---|
| 迁移 head | **单 head = `065_user_masks`**，新迁移 `down_revision` 指向它 | `backend/migrations/versions/` |
| 币钱包发放 | `grant(db, user_id, amount_fen, idempotency_key, type_str, ref_type, ref_id, metadata) -> int`，幂等（`credit_transactions.idempotency_key` ON CONFLICT DO NOTHING） | `heart/billing/__init__.py:46` |
| 会员发放 | `activate_or_extend(db, user_id, tier, days, granted_by) -> datetime`，upsert 续期 | `heart/membership/service.py:17` |
| 付费订单履约 | `fulfill_order()` → `_apply_sku()`（membership/coins），afdian webhook 调用 | `heart/afdian/fulfillment.py:203,320` |
| 现有邀请 | `record_invite_signup()`（绑定）、`handle_first_chat()`（首聊发双方 40 币 + 5/10 里程碑） | `heart/invite/service.py` |
| 首聊触发点 | chat WS turn 提交后 best-effort 调 `handle_first_chat` | `heart/api/routes_chat_ws.py:759` |
| 会员定价/命名 | `plus`=29 元、`immersive`=69 元；签到 plus/immersive 均 80 币/天 | `heart/core/config.py:272-287` |
| 成年门禁 | `users.age_verified_at` / `users.birthdate` | `heart/api/routes_auth.py:422` |
| 注册赠币 | `signup_grant_credits=4000` fen = 40 币 | `config.py:206` |
| 前端底部 Tab | 角色·探索·[创作]·消息·我的 | `web/src/components/ui/TabBar.tsx:14` |
| 内部记账单位 | fen（分），1 显示币 = 100 fen；佣金以**分（元）**独立记 | 全局约定 |

**账户模型（关键）**：三个独立账户，不要混。
- **悠悠币钱包** = `users.credits_balance` + `credit_transactions`（单位 fen，1 币=100 fen）。
- **会员** = `user_memberships`（tier + expires_at）。
- **佣金余额** = 新增 `commission_ledger`（单位分，1 元=100 分）。**佣金是元储值，不写 credit_transactions**，消费时才转成币/会员/角色卡。

---

## 1. PR 拆分总览

7 个 PR，尽量独立可合、可回滚。依赖关系标注在每个 PR 头部。

| PR | 标题 | 依赖 | 风险 | 可独立上线 |
|---|---|---|---|---|
| **PR-0** | chore: 剧情前端入口下线 + 福利 Tab 占位 | 无 | 低 | ✅ 先合 |
| **PR-1** | feat: 邀请有效性升级 + 抽奖机会账本（后端） | 无 | 中 | ✅ |
| **PR-2** | feat: 抽奖奖池 + 抽奖引擎（后端） | PR-1 | 中 | ✅ |
| **PR-3** | feat: 会员体验卡钱包（后端） | PR-2 | 低 | ✅ |
| **PR-4** | feat: 返佣生成 + 佣金余额账本 + 消费抵扣（后端） | 无（可与 PR-1 并行） | 中 | ✅ |
| **PR-5** | feat: 福利页前端（邀请 + 抽奖 + 佣金） | PR-1..4 API | 中 | 需后端先上 |
| **PR-6** | feat: 风控信号 + 后台配置（后端 + admin） | PR-1..4 | 中 | ✅ 增量 |

每个 PR 独立跑 `bash scripts/ci.sh` 全绿再合。迁移相关 PR 遵守 CLAUDE.md「DB 迁移铁律」：单 head、`IF NOT EXISTS`、revision 名 ≤ 32 字符。

---

## PR-0 — 剧情前端入口下线 + 福利 Tab 占位

**目标**：把底部「探索」Tab 换成「福利」入口，story 后端不动（可逆）。先合，给后续抽奖页占位。

改动（前端 only）：
1. `web/src/components/ui/TabBar.tsx`：`leftTabs` 里的 `explore`（探索）项改为 `rewards`（福利），`path: '/rewards'`，换图标（礼物/福袋类线性图标，遵守 UI 文案规范不用 emoji）。
2. 新增 `web/src/pages/RewardsPage.tsx` 占位页（PR-5 填充真内容），先渲染「敬请期待」空状态 + TabBar。
3. `web/src/App.tsx`：新增 `<Route path="/rewards" element={<RewardsPage />} />`。
4. story 路由处理：`/explore`、`/explore/:scenarioId`、`/story/:runId` **保留组件与路由**，但：
   - 用特性开关 `VITE_STORY_ENABLED`（默认 `false`）包裹导航暴露；
   - 移除/隐藏角色卡内 `StoryInviteCard` 的渲染（`web/src/components/StoryInviteCard.tsx` 引用处，用同一开关）。
5. **后端零改动**：`routes_story.py` / `routes_story_ws.py` / SS09 定价保留。

验收：底部 Tab 显示「福利」，点击进占位页；老的 `/story/:runId` 直接访问仍可用（story 后端在），但 UI 无入口。

> 不要物理删除 story 代码或表——不可逆，等抽奖跑满一个月数据后再议（产品决策）。

---

## PR-1 — 邀请有效性升级 + 抽奖机会账本

**目标**：把"发一句话得奖"升级为多条件有效邀请；有效达标时**发放抽奖机会**（不再发固定币）；拆掉里程碑。

### 迁移 `066_invite_lottery_chances`
```sql
-- 扩展 user_invite_uses：达标进度 + 状态 + 风险
ALTER TABLE user_invite_uses
  ADD COLUMN IF NOT EXISTS msg_count      INT         NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS ai_reply_count INT         NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS first_msg_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS qualified_at   TIMESTAMPTZ,   -- 有效邀请达标时刻
  ADD COLUMN IF NOT EXISTS status         VARCHAR(16) NOT NULL DEFAULT 'pending',
      -- pending | qualified | rejected | review
  ADD COLUMN IF NOT EXISTS risk_level     VARCHAR(8)  NOT NULL DEFAULT 'low';
      -- low | mid | high

-- 抽奖机会账本
CREATE TABLE IF NOT EXISTS invite_draw_chances (
  id           BIGSERIAL   PRIMARY KEY,
  user_id      UUID        NOT NULL,          -- 邀请人
  source       VARCHAR(24) NOT NULL,          -- 'invite:<use_id>'
  granted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at   TIMESTAMPTZ NOT NULL,          -- granted_at + 30d
  consumed_at  TIMESTAMPTZ,                   -- NULL = 未使用
  draw_id      BIGINT,                        -- 消费后回填 lottery_draws.id
  idem_key     VARCHAR(64) NOT NULL UNIQUE    -- 'chance:invite:<use_id>'
);
CREATE INDEX IF NOT EXISTS idx_draw_chances_user_avail
  ON invite_draw_chances (user_id, expires_at) WHERE consumed_at IS NULL;
```

### 有效邀请判定（`heart/invite/service.py` 重写 `handle_first_chat` → `handle_invite_progress`）
在 chat WS turn 提交后调用（复用现有触发点 `routes_chat_ws.py:759`），逐条累加进度：
- 每条被邀请人主动消息：`msg_count += 1`，首条记 `first_msg_at`；
- 每次完整非报错 AI 回复：`ai_reply_count += 1`；
- 达标条件（原子 UPDATE，`WHERE qualified_at IS NULL`）：
  `msg_count >= 3 AND ai_reply_count >= 2 AND NOW()-first_msg_at >= 120s AND 有效字符≥15 AND 注册后 7d 内 AND 成年门禁通过`。
- 达标时：`status='qualified'`、`qualified_at=NOW()`，然后**按风险等级**：
  - low → 立即调 `_grant_chance(inviter_id, use_id)`；
  - mid → `status='review'`，不发，进 24h 待审队列（PR-6）；
  - high → `status='rejected'`，进复核。

### 抽奖机会发放（每日上限 + 幂等）
```
_grant_chance(inviter_id, use_id):
  今日已发数 = COUNT(invite_draw_chances WHERE user_id=inviter AND granted_at::date(Asia/Shanghai)=today)
  上限 = {free:5, plus:10, immersive:20}[get_effective_tier(inviter)]
  if 今日已发 >= 上限: 记 use 为 qualified 但不发机会（保留返佣资格），return
  INSERT invite_draw_chances(..., idem_key='chance:invite:'+use_id, expires_at=NOW()+30d)
    ON CONFLICT (idem_key) DO NOTHING
```

### 删除/迁移旧逻辑
- **删掉** `handle_first_chat` 里的双方各 40 币 grant + 5/10 里程碑 grant。
- `GET /api/invite/status` 的 `stages`（里程碑）字段废弃或改为返回抽奖机会数。
- 保留 `record_invite_signup`（绑定逻辑）不变，仅加"注册后 24h 内、首付前"约束。

### 单元测试
- 达标边界（2 条不达标、3 条达标、120s 卡点、字符数不足）；
- 每日上限触顶后不发但保留 qualified；
- 幂等（同 use_id 重复调不重复发机会）。

---

## PR-2 — 抽奖奖池 + 抽奖引擎

**目标**：奖池版本化 + 服务端安全随机抽奖 + 单用户中奖限制 + 库存。

### 迁移 `067_lottery_pool`
```sql
CREATE TABLE IF NOT EXISTS lottery_pool_versions (
  id          BIGSERIAL   PRIMARY KEY,
  name        VARCHAR(64) NOT NULL,
  status      VARCHAR(12) NOT NULL DEFAULT 'draft',  -- draft|active|closed
  total_chances INT       NOT NULL,                  -- 首期 10000
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  activated_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS lottery_prizes (
  id            BIGSERIAL   PRIMARY KEY,
  pool_id       BIGINT      NOT NULL REFERENCES lottery_pool_versions(id),
  code          VARCHAR(32) NOT NULL,      -- coin_20 / coin_200 / vip_plus_3d / vip_immersive_1m ...
  kind          VARCHAR(16) NOT NULL,      -- 'coins' | 'membership'
  payload       JSONB       NOT NULL,      -- {"coins":20} 或 {"tier":"plus","days":3}
  weight        INT         NOT NULL,      -- /10000
  face_value_fen INT        NOT NULL,      -- 面值成本（分），用于预算
  total_stock   INT,                       -- NULL=不限
  daily_stock   INT,                       -- NULL=不限
  per_user_limit_json JSONB,               -- {"days":30,"max":2}
  fallback_prize_code VARCHAR(32),         -- 命中受限时降级发的奖（如 coin_20）
  enabled       BOOLEAN     NOT NULL DEFAULT TRUE,
  UNIQUE (pool_id, code)
);
CREATE TABLE IF NOT EXISTS lottery_draws (
  id          BIGSERIAL   PRIMARY KEY,
  user_id     UUID        NOT NULL,
  pool_id     BIGINT      NOT NULL,
  chance_id   BIGINT      NOT NULL UNIQUE,  -- 一次机会一次结果
  prize_code  VARCHAR(32) NOT NULL,
  prize_kind  VARCHAR(16) NOT NULL,
  payload     JSONB       NOT NULL,
  face_value_fen INT      NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  idem_key    VARCHAR(64) NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_lottery_draws_user ON lottery_draws (user_id, created_at);
```
种子：插入首期 pool（`total_chances=10000`）+ 10 个 prize 行（权重见产品方案 §4）。种子放独立 UPDATE/INSERT，`ON CONFLICT DO NOTHING`。

### 抽奖引擎 `heart/lottery/service.py`（新建）
```
draw(db, user_id, chance_id):
  # 全程一个 DB 事务 + SELECT ... FOR UPDATE
  1. 校验 chance 属于 user、未消费、未过期；已消费则返回 lottery_draws 里既有结果（幂等）
  2. 载入 active pool 的 enabled prizes
  3. r = secrets.randbelow(sum(weights))  ← 服务端安全随机，禁止前端传结果
  4. 按权重区间定位 prize
  5. 库存/单用户限制校验：
     - daily_stock/total_stock 不足 → 降级到 fallback_prize_code
     - per_user_limit（近 N 天该奖中奖数达上限）→ 降级到 fallback
  6. 原子：UPDATE invite_draw_chances SET consumed_at=NOW(), draw_id=? WHERE id=? AND consumed_at IS NULL
     （RETURNING 空 = 并发已被抢，重查返回既有结果）
  7. INSERT lottery_draws(idem_key='draw:'+chance_id)
  8. 履约发奖：
     - coins → grant(db, user, coins*100, idem='draw_reward:'+draw_id, type_str='grant', ref_type='lottery')
     - membership → 进体验卡钱包（PR-3），不直接激活
  9. commit
```
**关键**：结果由服务端定，`chance_id` 幂等，前端只播动画。

### API
- `POST /api/lottery/draw` body `{chance_id}` → `{prize_code, kind, payload, balance?}`。同 chance_id 重复请求返回同一结果。
- `GET /api/lottery/status` → `{available_chances, next_expiry_at, pool_prizes:[...展示用...]}`。

### 测试
- 权重分布（大样本卡方，容忍区间内）；
- 库存耗尽降级；单用户限制降级；
- 幂等（同 chance_id 并发只出一个结果、只发一次奖）；
- 过期机会不可抽。

---

## PR-3 — 会员体验卡钱包

**目标**：抽奖中的 VIP 奖品不直接激活，进"待激活体验卡"钱包，用户手动激活；激活时走现有 `activate_or_extend`。

### 迁移 `068_membership_coupons`
```sql
CREATE TABLE IF NOT EXISTS membership_reward_coupons (
  id          BIGSERIAL   PRIMARY KEY,
  user_id     UUID        NOT NULL,
  tier        VARCHAR(16) NOT NULL,      -- plus | immersive
  days        INT         NOT NULL,      -- 3 | 30
  source      VARCHAR(32) NOT NULL,      -- 'lottery:<draw_id>'
  granted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  activate_by TIMESTAMPTZ NOT NULL,      -- granted_at + 90d
  activated_at TIMESTAMPTZ,              -- NULL = 未激活
  status      VARCHAR(12) NOT NULL DEFAULT 'active',  -- active|activated|expired
  idem_key    VARCHAR(64) NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_coupons_user ON membership_reward_coupons (user_id, status);
```

### 逻辑 `heart/membership/coupons.py`（新建）
- `grant_coupon(db, user, tier, days, source, idem_key)`：抽奖 membership 命中时调，`ON CONFLICT (idem_key) DO NOTHING`。
- `activate_coupon(db, user, coupon_id)`：
  - 校验 `status='active'` 且 `NOW() < activate_by`；
  - 已有付费会员时按产品规则"当前会员到期后激活"（`activate_or_extend` 本就 upsert 续期，从 `max(NOW(), expires_at)` 顺延，天然满足）；
  - `activate_or_extend(db, user, tier, days, granted_by='coupon:'+id)`；
  - `UPDATE ... SET status='activated', activated_at=NOW()`。
- 过期扫描（可选 worker 或懒判定）：`activate_by < NOW()` 且未激活 → `status='expired'`。

### API
- `GET /api/rewards/coupons` → 待激活/已激活/已过期列表。
- `POST /api/rewards/coupons/{id}/activate` → 激活。

### 测试：重复激活幂等；过期不可激活；已有会员顺延。

---

## PR-4 — 返佣生成 + 佣金余额账本 + 消费抵扣

**目标**：被邀请人 30 天内付费 → 生成待结算佣金（元）→ 冻结 15 天 → 转佣金余额 → 可买会员/积分/(未来)角色卡。**无提现。**

### 迁移 `069_commission`
```sql
CREATE TABLE IF NOT EXISTS commission_entries (
  id            BIGSERIAL   PRIMARY KEY,
  inviter_id    UUID        NOT NULL,
  invitee_id    UUID        NOT NULL,
  order_id      VARCHAR(64) NOT NULL,       -- afdian out_trade_no
  paid_fen      INT         NOT NULL,       -- 实付（分，元制：¥29=2900）
  commission_fen INT        NOT NULL,       -- floor(paid_fen*10%)
  status        VARCHAR(12) NOT NULL DEFAULT 'pending',  -- pending|settled|cancelled
  settle_at     TIMESTAMPTZ NOT NULL,       -- created_at + 15d（中风险 +30d）
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  settled_at    TIMESTAMPTZ,
  idem_key      VARCHAR(64) NOT NULL UNIQUE  -- 'commission:'+order_id
);
CREATE INDEX IF NOT EXISTS idx_commission_inviter ON commission_entries (inviter_id, status);

-- 佣金余额账本（元制，单位分；与悠悠币钱包分离）
CREATE TABLE IF NOT EXISTS commission_ledger (
  id          BIGSERIAL   PRIMARY KEY,
  user_id     UUID        NOT NULL,
  delta_fen   INT         NOT NULL,        -- 入账正、消费负、冲正负
  balance_fen INT         NOT NULL,        -- 快照
  reason      VARCHAR(24) NOT NULL,        -- 'settle' | 'spend_membership' | 'spend_coins' | 'spend_card' | 'reverse'
  ref_id      VARCHAR(64),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  idem_key    VARCHAR(80) NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_commission_ledger_user ON commission_ledger (user_id, created_at);
```
> 佣金余额 = `commission_ledger` 最新 `balance_fen`，或单独在 users 加 `commission_balance_fen INT DEFAULT 0`（推荐后者，读快）。用与 `grant()` 相同的 CTE upsert 模式保证原子 + 幂等。

### 佣金生成（挂在付费履约后）
在 `heart/afdian/fulfillment.py` 的 `_apply_sku` **成功后**加钩子（best-effort，异常 log 不影响履约）：
```
on_paid_order(db, invitee_id, order_id, paid_fen):
  use = SELECT * FROM user_invite_uses WHERE invitee_id=? AND status='qualified'
  if not use: return
  if NOW() > invitee.created_at + 30d: return          # 归因窗口
  commission_fen = paid_fen // 10                       # 10%，floor
  risk = use.risk_level
  settle_at = NOW() + (30d if risk=='mid' else 15d)
  INSERT commission_entries(idem_key='commission:'+order_id) ON CONFLICT DO NOTHING
```
> 只算现金实付会员/币充值订单；优惠券/赠品/体验卡/佣金抵扣订单不返（用 order 的 sku 类型过滤——佣金抵扣产生的"订单"不带 afdian out_trade_no，天然不进这里）。

### 结算 worker（`heart/workers/commission_settle.py`，新建 or 挂到现有 reconcile）
定时扫 `status='pending' AND settle_at <= NOW()`：
- 转佣金余额：`commission_ledger` 入账 `+commission_fen`，`reason='settle'`，`idem='settle:'+entry_id`；
- `UPDATE commission_entries SET status='settled', settled_at=NOW()`。

### 退款/拒付冲正
afdian 退款 webhook → 找到 `commission_entries`：
- pending → `status='cancelled'`；
- settled → `commission_ledger` 记 `-commission_fen`（`reason='reverse'`，允许 balance 记负）。已消费掉的不追回，余额记负后续佣金先补。

### 佣金消费（抵扣）API
- `GET /api/commission/balance` → `{balance_fen, entries:[待结算/已结算...]}`。
- `POST /api/commission/spend` body `{target:'membership'|'coins'|'card', sku}`：
  - 事务内 `SELECT ... FOR UPDATE` 佣金余额，校验足额；
  - membership → 扣 `sku.price*100` 分，`activate_or_extend(...)`，`ledger reason='spend_membership'`；
  - coins → 扣对应分，`grant(coins*100, ref_type='commission_exchange')`，`reason='spend_coins'`；
  - card → 角色卡功能上线后接（预留 `reason='spend_card'`）；
  - `idem='spend:'+client_token`，防重复提交。

### 测试：10% floor 取整；30 天窗口边界；冻结 15/30d；退款冲正（pending vs settled）；消费足额/不足；消费幂等；余额记负后续补齐。

---

## PR-5 — 福利页前端

**目标**：填充 PR-0 的 `/rewards` 占位页，三块内容：邀请 · 抽奖 · 佣金。依赖 PR-1..4 的 API。

页面结构（`web/src/pages/RewardsPage.tsx` + 子组件）：
- **顶部**：邀请码 + 分享按钮（复用现有 `bindInvite` 流程与 `invite_url`）；今日剩余抽奖次数 + 最近到期时间。
- **邀请进度**：好友列表（已注册/互动中/已生效/审核中，读 `GET /api/invite/status`）。
- **抽奖转盘**：读 `GET /api/lottery/status` 渲染奖池；`POST /api/lottery/draw` 抽奖，前端播转盘动画**只展示服务端返回结果**。次数为 0 时禁用。
- **体验卡钱包**：`GET /api/rewards/coupons` + 激活按钮。
- **佣金**：`GET /api/commission/balance` 显示"佣金 ¥X"；入口跳到会员/充值页时透传"用佣金抵扣"选项。

前端服务层 `web/src/services/api.ts` 新增：`getLotteryStatus / drawLottery / getCoupons / activateCoupon / getCommissionBalance / spendCommission`。

新建 store：`web/src/stores/rewardsStore.ts`（次数、奖池、佣金余额）。

约束：所有文案纯文字无 emoji（CLAUDE.md UI 规范）；金额展示佣金用「元」、抽奖币奖励用「悠悠币」，不要混。转盘结果动画结束前不改余额显示，避免"未抽先加"。

---

## PR-6 — 风控信号 + 后台配置

**目标**：贴合纯邮箱注册现状的轻量风控 + admin 配置。增量，可最后做。

### 风控（`heart/invite/risk.py`，新建）
V1 可用信号（无手机号/实名）：设备指纹、IP、注册时序、行为特征、（充值时）支付账号。
- 迁移 `070_referral_risk`：`referral_risk_events`（event_type, subject_id, signals JSONB, score, created_at）。
- 达标时算 risk_level：
  - 同设备指纹 7d 注册 ≥3 → mid/high；
  - 同 IP 24h 注册 ≥5（叠加其他信号才升级，单 IP 不封）→ mid；
  - 机械聊天特征（30s 内完成、重复内容）→ 已在 PR-1 有效性判定挡掉；
  - 邀请双方相同支付身份（充值后才知）→ 佣金 high，冻结 30d。
- 中风险待审队列：admin 手动放行/拒绝；high 直接冻结进复核。

### admin 配置（`heart/api/routes_admin.py` 扩展）
- 奖池管理：CRUD `lottery_pool_versions`/`lottery_prizes`；**已 active 的池不可改概率，只能发新版本**（新建 draft → activate → 旧池 closed）。
- 邀请规则：有效性阈值、各等级次数上限、机会有效期（存 config 或 settings 表）。
- 返佣规则：比例、有效期、冻结期、兑换比例。
- 预算监控：奖池已发面值 / total、实际中奖分布 vs 配置概率偏差告警。

### 告警（产品方案 §7）：异常邀请率>5%、被邀请 D1/D7 低>20%、单次面值偏离¥3.7375>10%、退款率>3%、高价值奖品库存<20%。

---

## 幂等键规范（全局，必须遵守）

| 场景 | idempotency_key |
|---|---|
| 发抽奖机会 | `chance:invite:<use_id>` |
| 抽奖结果 | `draw:<chance_id>` |
| 抽奖币奖励入钱包 | `draw_reward:<draw_id>` |
| 体验卡发放 | `coupon:lottery:<draw_id>` |
| 佣金生成 | `commission:<order_id>` |
| 佣金结算入余额 | `settle:<entry_id>` |
| 佣金冲正 | `reverse:<entry_id>` |
| 佣金消费 | `spend:<client_token>` |

所有发奖/抽奖/返佣/冲正的 DB 写入必须带唯一幂等键（复用 `credit_transactions`/新账本的 `ON CONFLICT (idem_key) DO NOTHING`）。时区统一 Asia/Shanghai 算自然日。

---

## 执行顺序建议

1. **PR-0**（剧情下线）先合，独立、低风险、给入口占位。
2. **PR-1 + PR-4 并行**（都不互相依赖）：邀请机会账本 / 返佣账本。
3. **PR-2**（抽奖引擎，依赖 PR-1）→ **PR-3**（体验卡，依赖 PR-2）。
4. **PR-5**（前端，等 PR-1..4 API 就绪）。
5. **PR-6**（风控 + admin，增量收尾）。

每个 PR：`bash scripts/ci.sh` 全绿 → commit（规范见 CLAUDE.md）→ push → PR。迁移 PR 额外自检：`alembic current` == `alembic heads`、单 head、revision 名 ≤ 32 字符、`IF NOT EXISTS` 幂等、改列后完全重启后端（非 --reload）。

## 禁止事项（针对本任务）
- ❌ 物理删除 story 后端/表（不可逆，产品要求保留）。
- ❌ 抽奖结果由前端决定或前端传入——必须服务端安全随机。
- ❌ 佣金写进 `credit_transactions`（佣金是元储值，独立账本）。
- ❌ 佣金任何形式的现金提现（合规红线）。
- ❌ `except Exception: pass` 静默吞异常（CLAUDE.md 铁律）。
- ❌ 已 active 奖池直接改概率（必须发新版本）。

