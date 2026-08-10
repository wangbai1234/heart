# 付费系统改版 2026-08

把扣费从「按 model 一刀切」升级为「按 (会员档 × 项目) 免费矩阵」，删除情感陪伴/claude，
调整注册赠币与邀请阶梯，新增每日签到。**已确认：进阶版语音也免费；签到=自动到账+提示弹窗。**

## 最终定价矩阵

| 项目 | 体验版 free | 进阶版 ¥29 | 沉浸版 ¥69 |
|---|---|---|---|
| 普通交流 deepseek | 1币/条 | 免费 | 免费 |
| 私密陪伴 grok | grok价(env,默认3) | grok价(env) | 免费 |
| 语音 TTS(mimo/fish) | 按币 | 免费 | 免费 |
| 语音克隆 | 按币 | 按币 | 免费 |
| ASR | 5币 | 免费 | 免费 |
| 剧情解锁 | 40币 | 免费 | 免费 |
| 剧情聊天(按分钟) | 1币/分 | 1币/分 | 免费 |
| 月赠币 | 0 | 300 | 700 |

claude/情感陪伴全线移除。月赠币沿用「购买/续费即时发放」(afdian 30天SKU 天然=每月)，不新建 cron。

---

## 一、免费矩阵核心机制（新增，最关键）

### 1. `config.py` 扩展 `membership_tiers_config`，每档加 `free` 列表
```
free:      free=[]                                             monthly_grant=0
plus:      free=["deepseek","tts","asr","story_unlock"]        monthly_grant=300
immersive: free=["deepseek","grok","tts","clone","asr","story_unlock","story_chat"] monthly_grant=700
```
models/tts/clone 三档全放开为 `["deepseek","grok"]`/`["mimo","fish"]`/`["mimo","fish"]`
（体验版也能用 grok/克隆，只是要扣币——不再 403 挡人）。

### 2. `membership/__init__.py`
- `Entitlements` dataclass 加 `free: list[str]`；`_parse_tiers` 解析。
- 新增 `is_free_for_tier(tier: str, item: str) -> bool`（查该档 free 列表）。
- `assert_model_allowed` 等保留（现在各档 models 都含 grok，等于放行；claude 已移除故 claude 会被挡——符合"删除情感陪伴"）。

### 3. `config.py` 新增 `deepseek_cost_credits: int = 1`（普通交流基础价，仅体验版实际扣）

### 4. `billing/pricing.py` 全部函数加 `tier` 参数，命中 free 列表返回 0
- `llm_cost_fen(model, tier="free")`：deepseek 用 `deepseek_cost_credits`；命中 free→0
- `tts_cost_fen(provider, tier)`、`action_cost_fen(action, tier)`（clone）、`story_unlock_cost_fen(tier)`、`story_minute_cost_fen(tier)` 同理
- item 映射：deepseek→"deepseek"、grok→"grok"、tts→"tts"、clone_*→"clone"、asr→"asr"、
  story_unlock→"story_unlock"、story_minute→"story_chat"

### 5. 各扣费点传 tier
- `routes_chat_ws.py`: `_precheck_billing` 已有 tier → 传给 llm/tts cost；
  `_post_turn_billing`/`_charge_llm_cost`/`_charge_tts_cost` 加 tier 参数
  （在 `_post_turn_billing` 开的 db session 里 `get_effective_tier` 后下传）
- `routes_voice.py` ASR L1144: `get_effective_tier` 后 `asr` 命中 free→cost=0
- `routes_story.py` unlock L177 已有 tier → `story_unlock_cost_fen(tier)`
- `ss09_story/service.py`: `_preflight`/`charge_playtime` resolve tier → 传 `story_minute_cost_fen(tier)`；
  per-turn `llm_cost_fen(model, tier)`（story deepseek 仍 0，因 story 计费在按分钟）

---

## 二、删除情感陪伴 / claude

- `config.py` membership_tiers_config: 三档 models 均去掉 claude
- `infra/llm_providers/router.py` L26 `DEFAULT_FAILOVER = ["grok","deepseek"]`（去 claude）
- `routes_credits.py` `/pricing` models 数组去掉 claude 项(L160-165)
- 前端 `CharacterBackstagePage.tsx`：
  - `TEXT_TIERS` 删 emotional 项；daily 改 `title:'普通交流'` 且 `sub:''`（删小字）
  - private `sub:'回复更快，更聪明'`
  - `getTextTierLabel` 删 emotional 分支；标签改为 tier-aware（见五）
  - 删 claude 相关 pricing 字段引用
- 保留 `infra/llm_providers/claude.py` 文件（不删，避免 import 断；只是不再进 failover/权益）

---

## 三、注册赠币 + 邀请阶梯（纯 config/env，无迁移）

- `signup_grant_credits` 10000→**4000**（40币）；`.env` L110 同步
- `invite_referral_grant_coins` 100→**40**；`.env` L259
- `invite_milestone_5_coins` 300→**50**；`.env` L260
- `invite_milestone_10_coins` 1000→**120**；`.env` L261
- 前端硬编码文案 `InvitePage.tsx:75`「双方各得 100 yuoyuo币」→「各得 40 yuoyuo币」
- 阶梯 5/10 两档结构不变，只改数值

---

## 四、会员价格 + benefits 文案

- `config.py`/`.env`: plus 39→**29**，immersive 79→**69**
- `routes_credits.py` `/pricing` benefits 三档文案改为你给的原文：
  - **体验版**: ["支持体验游玩所有功能"]
  - **进阶版**: ["免费无限次文字聊天","免费解锁所有剧情","免费无限次语音聊天","每月额外赠送300yuoyuo币","解锁长久记忆功能"]
  - **沉浸版**: ["免费无限次聊天，回复更快更聪明","免费解锁所有剧情","免费无限次语音克隆","免费无限次剧情聊天","免费无限次语音聊天","每月额外赠送700yuoyuo币","解锁长久记忆功能"]
- `.env` 注释里 MEMBERSHIP_TIERS_CONFIG 示例 + monthly_grant 数值同步(400/800→300/700)

---

## 五、前端标签 tier-aware（普通交流对会员显示"免费"）

- `MembershipPage.tsx` L142 用后端返回的 monthly_grant 展示（进阶/沉浸端点现返回 0 抑制，需
  改为真实 300/700 或保持 benefits 文案已含——**采用**：benefits 已含月赠句，端点 monthly_grant
  保持 0 不重复展示，无需动 MembershipPage）
- `CharacterBackstagePage.tsx` `getTextTierLabel`：
  - deepseek(普通交流): 若当前档 free 含 deepseek→"免费"，否则`${deepseekCost}币/条`
  - grok(私密陪伴): 若当前档 free 含 grok→"免费"，否则`${grokCost}币/条`
  - 需前端拿到当前 tier 的 free 列表：`getMembership()` entitlements 加 `free` 字段
- `routes_membership.py` GET entitlements 加 `"free": ent.free`
- `membershipStore.ts` + `api.ts` Membership 类型加 `free: string[]`
- `getPricing` 的 deepseekCost 从新 `/pricing` models[deepseek].cost 读（体验版视角=1）

---

## 六、每日签到（自动到账+提示弹窗）

### 后端（无迁移，复用 credit_transactions 幂等）
- 新增 `routes_credits.py` `POST /api/credits/checkin`：
  - 幂等键 `checkin:{user_id}:{YYYY-MM-DD}`（UTC+8 当日）
  - `billing.grant(20*100, type_str="checkin", ref_type="checkin")`
  - 返回 `{granted: bool, coins: 20, balance, already: bool}`
  - `grant` 的 ON CONFLICT(idempotency_key) 天然防重复：已签到→granted=false
- `config.py` 加 `daily_checkin_coins: int = 20`；`.env` 加 `DAILY_CHECKIN_COINS=20`

### 前端
- `api.ts` 加 `dailyCheckin(): Promise<{granted:boolean;coins:number;balance:number;already:boolean}>`
- 新组件 `web/src/components/DailyCheckinDialog.tsx`（复用 `Dialog`）：
  - 标题「签到成功」，正文「获得 20 yuoyuo币」，3 秒 setTimeout 自动关 + 手动「知道了」按钮
  - 无 emoji（CLAUDE.md 铁律）
- `App.tsx` 登录后 useEffect（类比 invite bind，L118-124）：
  - accessToken 出现→调 dailyCheckin；granted=true 才弹窗；用 localStorage
    `yuoyuo-checkin-YYYYMMDD` 防同日重复请求；成功后 `creditsStore.refresh()`

---

## 七、验证
- `bash scripts/ci.sh`（lint + 单测）——pricing.py 签名变更会波及现有单测，需同步修
- 重点单测：billing pricing tier-aware、membership free 解析、checkin 幂等
- 手动核对 `/api/credits/pricing` 与 `/api/membership` 返回结构对前端契约

## 八、提交
小改动多、无 schema/迁移变更，但涉及计费面广 → **开 `feat/pricing-overhaul` 分支走 PR**，
不直接 main。commit 按类型拆分（feat: 免费矩阵 / feat: 签到 / chore: 定价数值）。

## 风险/权衡
- pricing.py 加 tier 参数是破坏性签名变更，所有 caller + 单测需同步（已列全 caller）
- .env 是真实密钥文件，只改定价键，不碰 key，不 commit .env
- deepseek 现在对体验版收 1 币：老的"deepseek 恒免费"假设在 story/failover 兜底处需确认不误伤
  （story per-turn deepseek 保持 0，兜底 failover 到 deepseek 不额外收——按 model+tier，体验版兜底到
  deepseek 仍收 1 币，属预期：体验版本就该为普通交流付费）
