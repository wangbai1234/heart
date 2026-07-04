# 07 · 验收报告 + 返工执行文档（Mimo 5 模块交付）

> 验收对象：Mimo 对模块 1–5 的实现（当前**未提交**堆在 `feat/auth-otp` 一个分支的 working tree）。
> 验收方法：5 个独立审计逐模块对照各自 DoD **实读代码**（file:line 为证），两个最致命 bug 已人工二次复核。
> 本文 = 缺陷清单（含 file:line + 修法）+ 按依赖排序的返工计划 + 每阶段可直接交付 Mimo 的 prompt。

---

## 0. 总判定

| 模块 | 判定 | 阻断级问题 |
|------|------|-----------|
| M4 登录 OTP | 🔴 NOT-READY | 迁移 011 外键建在 `users` 之前 → `alembic upgrade` 崩 |
| M3 积分 | 🔴 NOT-READY | 计费 SQL 引用不存在的列 `updated.balance_after` → 所有入账/扣费崩 |
| M1 聊天/语音 | 🔴 NOT-READY | 安全兜底回合被错扣费；语音开关不写库→语音全链路死 |
| M2 资料/18+ | 🟠 SHIP-WITH-FIXES | **红线**：服务端 18+ 拦截缺失（仅前端挡，可绕过）|
| M5 法律 | 🔴 NOT-READY | 内部律师 TODO 泄漏进用户可见页面并被渲染 |

### 0.1 根因（比单个 bug 更重要）
1. **CI 假绿**：`bash scripts/ci.sh` 861 passed，但 auth/billing 单测全 mock 数据库 → 两个"碰真 Postgres 必崩"的致命 bug + 计费错误零拦截。**必须补一条跑真 PG 的集成测试作为门禁**（见 §Phase 1）。
2. **服务端信任边界缺失**：18+ 门禁（M2/M1）只在前端 `AuthGuard`，直连 API/WS 即绕过。产品核心合规红线目前是装饰。
3. **计费不可信**：真库上写不进（M3），能写处又在安全兜底时错扣（M1）。

### 0.2 交付流程问题
Mimo 把 5 个模块改动**全部堆在 `feat/auth-otp` 且未提交**（60+ 文件），违反执行文档"每模块独立分支+独立 PR"。返工前先固化基线（§4 分支策略）。

---

## 1. 缺陷清单（按模块，file:line + 修法）

### M4 · Email OTP（`01_auth_otp.md`）
| # | 级别 | 位置 | 问题 | 修法 |
|---|------|------|------|------|
| 4-1 | 🔴CRITICAL | `migrations/versions/011_users_and_auth.py:44` vs `:56` | `credit_transactions` 的 `FK REFERENCES users(id)` 建在 `users` 表**之前** → `alembic upgrade` 报 *relation "users" does not exist*。**已人工复核。** | 先建 `users` 块（:53-79），再建 `credit_transactions`（:27-51）。 |
| 4-2 | 🟠MEDIUM | `stores/appStore.ts:7,34,50` + `pages/SplashPage.tsx:8,14` | 规范要求删除的 `appStore.isAuthenticated` 仍在且 `setAuthenticated` 从未被调用；Splash 仍读它（恒 false）→ **已登录用户 2.5s 后被弹回 /login**。 | SplashPage 改用 `useAuthStore().isAuthenticated()`；删除 `appStore.isAuthenticated/setAuthenticated`。 |
| 4-3 | 🟠MEDIUM | `services/api.ts:23-52`、`hooks/useWebSocket.ts:191-208` | 并发 401 各自拿同一 refresh 去换；第一个轮换后旧 token 作废，第二个用作废 token → 触发复用检测 `routes_auth.py:430-441` **吊销全部会话** → 用户被登出。 | refresh 加单飞（共享 Promise 去重）。 |
| 4-4 | 🟡LOW-MED | `routes_auth.py:490,512` | `/logout`、`/me` 无限流（规范 §4 要 30/min、60/min）。 | 加 `@limiter.limit`。 |
| 4-5 | 🟡LOW | `routes_auth.py:261-265` | verify 无 code 行时立即返回、有行时才做 DB 工作 → 计时侧信道泄露"该邮箱是否有待验证码"。 | 等化工作/耗时。 |
| 4-6 | 🟡LOW | `routes_auth.py:315-321` | 新用户 insert 无 `ON CONFLICT` → 同邮箱并发首登抛 IntegrityError。 | `ON CONFLICT (email) DO NOTHING` + 回查。 |
| 4-7 | ⚪测试 | `tests/unit/test_auth_otp.py:21` | DoD 场景（限流/冷却/防枚举/成功/过期/锁定/幂等/轮换/吊销）**全部 skip unless DATABASE_URL** → 零覆盖。 | 见 Phase 1 集成测试。 |

### M3 · 积分 + 爱发电（`02_credits_afdian.md`）
| # | 级别 | 位置 | 问题 | 修法 |
|---|------|------|------|------|
| 3-1 | 🔴CRITICAL | `heart/billing/__init__.py:68,71`（同型 `:156/159`、`:208/211`、`:271/274`） | CTE `RETURNING credits_balance` 但 SELECT 读 `updated.balance_after`（不存在）→ grant/redeem/charge_turn/refund 全报 42703。**已人工复核。** | CTE 改 `RETURNING credits_balance AS balance_after`，或 SELECT 引用 `updated.credits_balance`。四处都改。 |
| 3-2 | 🟠HIGH | `pages/RedeemPage.tsx:24-35` | 仍是 mock：`setTimeout(1500)` 假成功，从不调 `redeemCode`、不更新 `creditsStore`、无 无效/已用/过期 分支、成功还跳 `/login`。 | 调 `api.redeemCode(code)`；成功 `creditsStore.setBalance(res.balance)`+Toast+`navigate(-1)`；400 detail 映射三种错误文案。 |
| 3-3 | 🟠MEDIUM | `routes_credits.py:94`、`rate_limit.py:8` | redeem 仅 IP 10/min，无每用户 5/min；`/balance /transactions /pricing` 完全无限流（规范 60/min）；限流只按 IP。 | 加每用户 5/min（key 用 user_id）+ 三端点 60/min。 |
| 3-4 | 🟠MEDIUM | `workers/credit_reconciliation_worker.py:34,67` | 对账只 `logger.warning`，无 Prometheus `credit_balance_drift_total`（规范 §6.6）。 | 加 Counter 指标。 |
| 3-5 | 🟡LOW-MED | `routes_webhooks.py:34-48`、`:96-100` | 爱发电 sign 的 md5 公式是臆造的（对含 stringified `data` 的顶层键计算），与真实爱发电不符；且吞掉 DB 错误仍返回 200。 | 按爱发电官方文档实现验签；insert 失败别静默（记 error）。正确点：不直接给用户加分（已符合）。 |
| 3-6 | ⚪偏差 | `011:28-51`；`billing/__init__.py`；`heart/scripts/gen_redemption_codes.py` | `credit_transactions` 建在 011 非 012；billing 逻辑在 `__init__.py` 非 `service.py`；生成脚本在 `backend/heart/scripts/` 非 `backend/scripts/`。功能 OK，与文档不符。 | 可保留现状但在 PR 注明，或对齐文档。不阻断。 |

### M1 · 聊天/语音 + 持久化 + 计费（`04_chat_voice.md`）
| # | 级别 | 位置 | 问题 | 修法 |
|---|------|------|------|------|
| 1-1 | 🔴CRITICAL | `ss07_orchestration/orchestrator.py:224,229,247,253,281` + `routes_chat_ws.py:282-285` | 流式 `turn_end` 不带 `path`，但 WS 靠 `event.get("path") in (care,reject)` 判定不扣费 → 恒 False → **PURPLE/RED/兜底回合照样扣费**（违反 DoD#4、§4）。 | orchestrator 流式 `turn_end` 带 `path`/`was_fallback`；WS 对 care/reject/fallback 一律不扣费。 |
| 1-2 | 🟠HIGH | `pages/CharacterBackstagePage.tsx:107`、`appStore.ts:64-71`、`services/api.ts:242-246`(未用) | 语音开关只改本地，**从不 PATCH 落库**、进页不 GET；后端以库为准（`routes_chat_ws.py:149-156`）→ 语音永远开不起来、跨设备失效、5 分回合永不发生。 | onChange 乐观更新+`updateCharacterSettings` PATCH；mount 时 `getCharacterSettings` 水合。 |
| 1-3 | 🟠HIGH | `routes_chat_ws.py:239-251` | assistant 落库 INSERT 缺 `audio_url/audio_duration_ms`；无 PCM→S3 上传 → 语音不可回放（违反 §2.3/DoD#2,#5）。 | 累积 PCM→拼 WAV→上传 S3→写 `audio_url`。 |
| 1-4 | 🟠HIGH | `hooks/useWebSocket.ts:158-163`、`ConversationChatPage.tsx` | 前端 `insufficient_credits` 是空实现（注释未落地），`showInsufficientDialog` 从不置 true → 余额不足弹窗永不出现。 | 收到事件→置 dialog→引导 `/redeem`；同步 `creditsStore`。 |
| 1-5 | 🟠MEDIUM | `chatStore.ts:104`(0 caller)、`useWebSocket.ts:96-101`、`ConversationChatPage.tsx:115` | 实时语音不写入消息（`setMessageAudio` 无人调用）；`turn_start` 消息无 `kind:'voice'`；路由页用内联 `<audio>` 而非 AnalyserNode 驱动的 `VoiceMessageBubble`。 | 语音 turn 建 `kind:'voice'` 消息；`audio_chunk`→`setMessageAudio`；渲染真实 `VoiceMessageBubble`。 |
| 1-6 | 🟠MEDIUM | `routes_chat_ws.py` / `middleware.py`（缺） | 聊天无 `age_verified` 门禁（规范 §4 要 `age_verification_required`）。**与 M2-1 合并为一个共享依赖修复。** | WS connect 时校验 age_verified，否则 close/error。 |
| 1-7 | 🟠MEDIUM | `routes.py:121-160` | REST `/api/chat` 无预检/扣费/落库（§4/§8 要求）。 | 补预检+扣 text+落库；或显式弃用该端点并在文档注明。 |
| 1-8 | 🟡LOW-MED | `routes_chat_ws.py:97-101` + `:208-216` | 发了两次 `turn_end`（先裸的、后带 modality/credits/balance 的）→ 违反协议。 | 只发富信息那条。 |
| 1-9 | 🟡LOW | `routes_chat_ws.py:174-176` | 预检异常时 `return (False, True)` **失败开放**→ 绕过余额门禁按 text 继续。 | 改失败关闭（异常→拒绝/报错）。 |
| 1-10 | 🟡LOW | `routes_chat_ws.py:366` | modality 按 `stream_session` 是否存在判定，而非是否真产音频 → 无音频也扣 5。 | 按实际产出音频判 voice。 |
| 1-11 | 🟡LOW | `routes_chat_ws.py:35-47` vs `useWebSocket.ts:119-124` | 后端 `send_audio` 默认 `fmt="mp3"` 且不带 `sentence_seq`；前端按 `pcm16` 包 WAV、去重用 `sentence_seq`。协议漂移。 | 统一 `pcm16@24k` + 必带 `sentence_seq`（规范 §7）。 |

### M2 · 资料/设置/18+/注销（`03_profile_settings.md`）
| # | 级别 | 位置 | 问题 | 修法 |
|---|------|------|------|------|
| 2-1 | 🔴CRITICAL(红线) | `routes_voice.py:31`、`routes_chat_ws.py:486`、`routes_credits.py`（均缺） | `age_verification_required` 后端**全无**；业务路由不校验 `age_verified_at` → 18+ 仅前端 `AuthGuard` 挡，直连 API/WS 即绕过。 | 建共享 FastAPI 依赖：加载 `age_verified_at`，NULL→403 `age_verification_required`；挂 chat/voice/credits 消费路由（豁免 profile/export/delete）；WS 在 connect 校验。**统一覆盖 1-6。** |
| 2-2 | 🟠MEDIUM | `pages/AgeGatePage.tsx:28` + `components/AuthGuard.tsx:28` | 多了个"重新填写出生日期"按钮，跳 `/settings/profile` 但被 AuthGuard 立刻弹回 `/age-gate`（死按钮）；违反 §2.2"单按钮"。 | 删除该按钮（只留"退出登录"）。 |
| 2-3 | 🟡LOW | `pages/ProfileEditPage.tsx:45-46` | <18 保存后只 Toast，不 `setUser(birthdate)` 也不跳 `/age-gate`，靠 store birthdate 恰好为空才被困住，脆弱。 | 显式写 birthdate + 跳 `/age-gate`。 |
| 2-4 | 🟡LOW | `pages/ProfileEditPage.tsx:58-68`、`:126` | 头像无前端压缩至 ≤512px（§1.1）；生日用原生 `<input type=date>` 非滚轮。后端 5MB/类型校验已在（`routes_profile.py:131-137`），非安全漏洞。 | 加压缩；生日改 BottomSheet 滚轮。 |
| 2-5 | 🟡LOW | `routes_account.py:131-174` | 导出缺 `chat_messages` + 记忆摘要（§4.3）。 | 补齐导出内容。 |
| 2-6 | 🟡LOW | `workers/account_purge_worker.py:81-139` | 清除任务 docstring 称删头像文件但**无 S3 删除**、也不清 `avatar_url` → 注销后头像 PII 残留。 | 清除时删 S3 头像 + 置空 `avatar_url`。 |
| 2-7 | ⚪NIT | `pages/SettingsPage.tsx:27` | 推送 Switch 用本地 `useState` 未落 `appStore`；无"即将上线"灰置；缺"联系我们"行（§3）。 | 按 §3 补齐。 |

### M5 · 用户协议/隐私（`05_legal_tos_privacy.md`）
| # | 级别 | 位置 | 问题 | 修法 |
|---|------|------|------|------|
| 5-1 | 🔴BLOCKER | `public/legal/terms.md:5`、`privacy.md:5`（+ `terms.md:66,70`、`privacy.md:38,71`）经 `LegalPage.tsx:33` 渲染 | 给运营/律师看的内部 `TODO(运营): 上线前需律师复核` 与 `<!-- TODO -->` 注释**留在用户可见 md 里并被当正文渲染出来**（含字面 `>`/`<!-- -->`）。直接违反 §Mimo prompt line 175。 | 从 public md 删除所有内部 TODO/注释；律师复核说明只留在 `docs/` 内部。 |
| 5-2 | 🟠HIGH | `stores/authStore.ts:5-45`（partialize:38-43） | `acceptedLegalVersion` 完全未实现 → 版本变更重新同意机制失效（§1 line13 / prompt step5）。 | 加字段+setter，登录/同意时记录当前版本，持久化。 |
| 5-3 | 🟠HIGH | `pages/OnboardingPage.tsx`（缺） | 第 2 屏法律入口缺失（§line12 / prompt step4）。 | 加 `/legal/*` 链接。 |
| 5-4 | 🟠MEDIUM | `terms.md:3,64,65`、`privacy.md:37,39` | `【】` 占位被擅自填成 `2026-07-04`/`中华人民共和国`/`新加坡`/`180 天`/邮箱等 → 律师复核前把未定值当定稿，法律风险更高。 | 恢复 `【】` 占位；除非运营已确认，否则不填实值。 |
| 5-5 | 🟠MEDIUM | `pages/LegalPage.tsx:27-34` | 自渲染器只处理整行 `#/##/**/---`，行内 `**bold**`、`-`/数字列表、`>` 引用、HTML 注释均按裸文本渲染（也是 5-1 泄漏被显示的根因）。 | 换 `react-markdown` 或扩展渲染器覆盖行内/列表/引用/注释剥离。 |

---

## 2. 返工计划（按依赖排序）

> 原则：先修让"什么都跑不起来"的地基，再修"钱不可信"，再修"合规红线"，最后修展示层。每阶段独立可验，改完就能证明。

```
Phase 0  地基：M4 迁移能 upgrade                          [4-1]
Phase 1  钱能写进真库 + 补集成测试门禁（根因修复）         [3-1] + 真PG集成测试
Phase 2  服务端 18+ 门禁（共享依赖，一次覆盖 M2+M1）        [2-1 = 1-6]
Phase 3  聊天计费正确性 + 语音全链路                       [1-1,1-2,1-3,1-4,1-5,1-7..1-11]
Phase 4  账号/前端收尾                                     [4-2,4-3,4-4..4-6, 2-2..2-7]
Phase 5  法律页                                           [5-1..5-5]
```

**为什么这个顺序**：Phase 0 不修，`alembic upgrade` 崩，后面全测不了；Phase 1 不修，任何充值/扣费一碰真库就崩，且**补的集成测试正是当初能拦住 4-1/3-1 的东西**；Phase 2 是合规红线且被 M1、M2 共用，先抽成一个依赖避免重复；Phase 3 依赖 Phase 1（扣费函数）+ Phase 2（门禁）；Phase 4/5 是收尾。

### 分支策略（先固化基线）
当前 5 模块改动未提交、互相纠缠在一个 working tree。建议：
1. 在 `feat/auth-otp` 上先 `git add -A && git commit`（原样固化 Mimo 交付为基线，便于 diff 回溯）。
2. 从 main 开 `fix/commercial-acceptance`，cherry-pick 该基线，按 Phase 顺序**分 commit 修复**。
3. 收尾时按模块拆 stacked PR，或一个集成 PR（PR 描述引用本报告）。**不要**再把新修复散到多个 feature 分支（违反 CLAUDE.md 跨分支 fix 反模式）。

---

## 3. 每阶段 Mimo 返工 Prompt（复制交付）

### ⚙️ Phase 0 — 迁移地基
```
你在 Heart 仓库修复验收报告 07 的 Phase 0。分支 fix/commercial-acceptance，base=main。只做一件事：
修 backend/migrations/versions/011_users_and_auth.py 的建表顺序 —— 当前 credit_transactions(:27-51) 的外键 REFERENCES users(id) 建在 users 表(:53-79) 之前，alembic upgrade 会报 relation "users" does not exist。把 users 的 CREATE TABLE 块移到 credit_transactions 之前（email_otp_codes/auth_sessions 保持在 users 之后）。downgrade 顺序相应保证先删 FK 持有者再删 users。
验证：本地起一个 postgres，alembic upgrade head 与 downgrade base 均干净。不改任何字段定义。
```

### ⚙️ Phase 1 — 计费列 + 真库集成测试门禁（根因）
```
你在 Heart 仓库修复 07 的 Phase 1。承接 Phase 0。
1. 修 backend/heart/billing/__init__.py 四处 CTE：grant/redeem/charge_turn/refund 里 `WITH updated AS (UPDATE users ... RETURNING credits_balance)` 之后 SELECT 引用了不存在的 `updated.balance_after`。改为 CTE `RETURNING credits_balance AS balance_after`（或 SELECT 改用 updated.credits_balance）。四处都改。
2. 新增集成测试 backend/tests/integration/test_billing_real_db.py（需 DATABASE_URL，走真 Postgres）：alembic upgrade head → 建一个 user → grant 100 → redeem 一个码 → charge_turn text/voice → 断言 credit_transactions 行数/幂等（同 turn_id 二次不重扣）/余额不破负/并发同码只成功一次。这条测试的目的就是拦住 3-1/4-1 这类"mock 测不到"的 bug。
3. 在 scripts/ci.sh 的说明里标注：合并前必须在有 DATABASE_URL 的环境跑一次 integration-tests（不改默认 all 的行为，避免本地无库时红）。
约束：不放宽 ruff/mypy；ci.sh all 仍全绿；有库时 integration-tests 全绿。
```

### ⚙️ Phase 2 — 服务端 18+ 门禁（共享依赖，覆盖 2-1 = 1-6）
```
你在 Heart 仓库修复 07 的 Phase 2（合规红线）。
1. 新增共享依赖 backend/heart/api/deps.py::require_age_verified：从当前用户加载 age_verified_at，为 NULL 则 raise HTTPException(403, "age_verification_required")。
2. 挂到所有"业务消费"路由：REST /api/chat、routes_voice.py 的 synthesize、routes_credits.py 的消费类端点。豁免 profile/export/delete/auth。
3. WebSocket routes_chat_ws.py：连接建立后（取到 user_id 之后）校验 age_verified_at，为空则发 error {code:"age_verification_required"} 并 close(1008)，不进入生成。
4. 单测：未验证用户对每类受保护端点得 403 / WS 被拒；已验证用户放行。
约束：不信任前端任何 age 字段；age 计算/写入仍只在 routes_profile.py 服务端（保持现状）。ci.sh 全绿。
```

### ⚙️ Phase 3 — 聊天计费正确性 + 语音全链路
```
你在 Heart 仓库修复 07 的 Phase 3。承接 Phase 1(扣费)/Phase 2(门禁)。严格按 04_chat_voice.md。
计费正确性：
1. [1-1] orchestrator.py 流式 turn_end 事件带上 path 和 was_fallback；routes_chat_ws.py:282-285 对 care/reject/fallback 一律不扣费（当前恒 False→错扣）。
2. [1-9] 预检异常改失败关闭（不再 return (False,True) 放行）。
3. [1-10] modality 按"是否真产生音频"判定，不按 stream_session 是否存在。
4. [1-8] 只发一条富信息 turn_end（删裸的那条）。
语音全链路：
5. [1-2] CharacterBackstagePage 语音 Switch：onChange 乐观更新 + PATCH /api/characters/{cid}/settings；进页 GET 水合。删除"只改本地"。
6. [1-3] TTS 累积 PCM→拼 WAV→上传 S3 chat_audio/{user_id}/{turn_id}.wav→assistant 落库写 audio_url/audio_duration_ms。
7. [1-4] 前端 insufficient_credits→置 dialog→引导 /redeem，并同步 creditsStore。
8. [1-5] 语音 turn 建 kind:'voice' 消息，audio_chunk→chatStore.setMessageAudio，渲染真实 VoiceMessageBubble（AnalyserNode 波形），替换内联 <audio>。
9. [1-11] 统一音频 pcm16@24k + 必带 sentence_seq。
10. [1-7] REST /api/chat 补预检+扣 text+落库；若决定弃用则从路由移除并在文档注明。
验收：关语音扣1落2行；开语音（DB 开关）扣5且 audio_url 可回放；安全兜底回合不扣费仍落库；余额不足弹窗出现且不生成；跨设备开关同步。ci.sh 全绿 + Phase1 集成测试全绿。
```

### ⚙️ Phase 4 — 账号 + 前端收尾
```
你在 Heart 仓库修复 07 的 Phase 4。
M4：[4-2] SplashPage 改用 authStore.isAuthenticated()，删除 appStore.isAuthenticated/setAuthenticated（现让已登录用户被弹回登录）；[4-3] api.ts + useWebSocket refresh 加单飞去重（并发 401 不再触发全会话吊销）；[4-4] /logout 30/min、/me 60/min 限流；[4-5] verify 等化计时；[4-6] 用户 insert 加 ON CONFLICT(email) DO NOTHING+回查。
M2：[2-2] 删 AgeGate 死按钮（只留退出登录）；[2-3] <18 保存显式写 birthdate+跳 /age-gate；[2-4] 头像前端压缩≤512px、生日改滚轮；[2-5] 导出补 chat_messages+记忆摘要；[2-6] 清除任务删 S3 头像+置空 avatar_url；[2-7] 推送 Switch 落 appStore+"即将上线"灰置+补联系我们行。
约束：复用 tokens.css 双主题；ci.sh 全绿。
```

### ⚙️ Phase 5 — 法律页
```
你在 Heart 仓库修复 07 的 Phase 5。严格按 05_legal_tos_privacy.md。
1. [5-1] 从 web/public/legal/terms.md 与 privacy.md 删除所有内部 TODO(运营)/<!-- --> 注释与"律师复核"说明（这些只能留在 docs/ 内部，绝不进 public 用户可见文件）。
2. [5-4] 把被填实的值恢复为 【】 占位（生效日期/管辖/服务器地/期限/邮箱），除非运营已确认具体值。
3. [5-2] authStore 增 acceptedLegalVersion（持久化），登录"继续即同意"时记录当前版本。
4. [5-3] OnboardingPage 第2屏加 /legal/terms、/legal/privacy 链接。
5. [5-5] LegalPage 改用 react-markdown（或扩展渲染器）正确渲染行内 **bold**、- / 数字列表、> 引用，并剥离 HTML 注释。
验收：登录前可读两页；页面无任何内部 TODO/注释可见；无 心屿/Heart；light+dark 可读。ci.sh 全绿。
```

---

## 4. 返工完成的验收口径（DoD of DoD）
- `alembic upgrade head` + `downgrade base` 在真 Postgres 干净往返。
- 新增 `test_billing_real_db.py` 覆盖 grant/redeem/charge/幂等/不破负/并发，且**在有库环境跑绿**。
- 未 18+ 验证用户对 chat(WS)/voice/credits 消费一律 403/1008；已验证放行。
- 安全兜底回合不扣费；语音开关落库并跨设备生效；语音消息可回放；余额不足有弹窗。
- `grep -rn "TODO(运营)\|<!--" web/public/legal/` 无命中；法律页版本记录生效。
- `bash scripts/ci.sh all` 全绿 + 有库时 `integration-tests` 全绿。

> 本报告所有 file:line 基于验收时 `feat/auth-otp` 未提交 working tree；返工前请先固化基线（§2 分支策略）后再逐 Phase 修复。
