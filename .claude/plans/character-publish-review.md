# 角色发布与审核系统

## 目标（用户四点确认）
1. 全站 UI 文案 `伴侣` → `角色`
2. 创建角色第一步加可见性选择：公开 / 仅链接 / 私密 + 审核提示
3. 管理员审核：**只加后端 API，命令行操作**（无 web 后台）
4. 用户审核进度 + 驳回原因 UI + 两种弹窗
5. **只按通过数算奖励，不限制创建**；**公开和仅链接都走审核**，私密即时无审核无奖励

## 奖励规则
- 每个角色审核通过：赠 100 yuoyuo 币（按 character_id 幂等）
- 累计通过 ≥ 5 个：额外送 1 个月进阶版(plus) 会员（一次性，milestone 表守卫）

---

## A. 文案清扫（4 处）
- `web/src/data/uiContent.ts:301,303` 专属伴侣/AI 伴侣 → 角色
- `web/src/pages/CreateCharacterPage.tsx:873`
- `web/src/pages/MyCharactersPage.tsx:356`
- `web/src/pages/CreateHubPage.tsx:171`

## B. DB 迁移 `056_character_review.py`（down_revision=055）
`characters` 表新增列（全部 IF NOT EXISTS 幂等）：
- `review_status TEXT NOT NULL DEFAULT 'not_required'` CHECK IN (pending/approved/rejected/not_required)
- `review_reason TEXT NULL`
- `submitted_at TIMESTAMPTZ NULL`
- `reviewed_at TIMESTAMPTZ NULL`
- `result_ack_at TIMESTAMPTZ NULL`（结果弹窗已读时间）

回填：built-in(owner IS NULL) → approved；存量 UGC 全私密 → not_required。

新表 `user_reward_milestones`(user_id, milestone TEXT, granted_at)，PK(user_id, milestone)，INSERT ON CONFLICT DO NOTHING 保证 5-通过里程碑只发一次。

## C. 后端逻辑
- `draft.py`：`CharacterDraft` 加 `visibility: Optional[Literal["public","unlisted","private"]] = "private"`
- `routes_characters.py`:
  - `create_character`：删除 `_UGC_MAX_PER_USER` 限制；INSERT 用 draft.visibility；public/unlisted → review_status='pending' + submitted_at=now；private → not_required
  - `set_character_visibility` PATCH：转 public/unlisted → pending + submitted_at + 清 result_ack_at；转 private → not_required
  - `list_characters` / `get_character_profile`：非 owner 可见门槛加 `review_status='approved'`
  - 新增 `GET /characters/review/updates` → 返回本人所有 UGC 的 {id,name,review_status,review_reason,submitted_at,reviewed_at,needs_ack}, approved_count
  - 新增 `POST /characters/review/ack` {character_id} → 设 result_ack_at=now
- `character_catalog.py`：CharacterRow/CharacterEntry 加 review_status/review_reason；visible_to 加 approved 门槛；owner 才回传 review_reason
- 奖励发放（审核通过时）：`grant(100*100, idem="char_review:{cid}", type_str="grant", ref_type="character_review")` + 计通过数≥5 时插 milestone 成功则 `activate_or_extend(plus, 30)`

## D. 管理员 API（`routes_admin.py`, X-Admin-Key）
- `GET /admin/characters/pending` → 列出 pending（含 name/owner/avatar_url/submitted_at）
- `POST /admin/characters/{id}/approve` → approved + reviewed_at + 触发奖励
- `POST /admin/characters/{id}/reject` {reason} → rejected + review_reason + reviewed_at
- 附 `scripts/review_characters.sh`：封装 curl（列出/通过/驳回）便于命令行操作

## E. 前端
- `api.ts`：CharacterDTO 加 review_status?/review_reason?；新增 getReviewUpdates()/ackReview()；VisibilityUpdate 已存在
- `CreateCharacterPage.tsx` step1：可见性单选(公开/仅链接/私密) + 提示「该角色审核后会被公开，所有人可见你的角色」；buildDraft 带 visibility
- `MyCharactersPage.tsx`：解锁 `LOCKED_VIS`（允许 public/unlisted）；卡片加审核状态徽章（审核中/已通过/未通过+原因）
- `App.tsx` 两个弹窗（登录后 useEffect）：
  1. 审核结果通知：getReviewUpdates 有 needs_ack 的 → 逐个弹（通过/驳回/奖励），点确认调 ackReview
  2. 每日激励弹窗：approved_count==0 时，localStorage 日戳每天一次，讲「创建并公开角色得 100 币，满 5 个送会员」
  - 复用 DailyCheckinDialog / Dialog 组件；无 emoji

## F. 验证与提交
- `bash scripts/ci.sh`（lint+测试）
- dev DB `alembic upgrade head` 后完全重启后端
- 走 feature 分支 `feat/character-publish-review` + PR（改动跨迁移+多文件，非小改动）
