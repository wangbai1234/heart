# PROJECT STATUS — Heart (心屿)

> **AI Session 入口文档。任何新的 AI session（包括 Claude Code、Cursor、其他 agent）必须优先读完这份文件再开始工作。**
>
> 这份文件是当前真理。其它历史文件可以参考，但当与本文件冲突时，**以本文件为准**。

**最后更新**：2026-07-11
**当前 Phase**：✅ PWA 审计 24 项全清（批 A/B/C/D）＋ 商业外壳 ＋ 记忆系统 ＋ 语义召回。即将进入 Cloudflare Tunnel 本地部署 + 真机全量回归。
**当前分支**：main（PR #128–#158 全部合并）

> 📖 **启动/部署/手机端测试/启用语义召回，一律看 [`docs/EXECUTION_MANUAL.md`](EXECUTION_MANUAL.md)（单一操作手册）。**
> 📖 **拉取最新代码后如何 bring-up 本地环境**，直接看下方 §0.5「拉取最新代码后必做清单」。

---

## 0. 近期进展（2026-07-08 → 2026-07-11）— PWA 审计三批修复全清

> ⚠️ 给新会话：本节的 24 个修复已经**全部合入 main 并本地 CI 通过**。上一版本 PROJECT_STATUS 停留在 PR #125（2026-07-08），下方 §0.6 是完整迁移日志。

### 0.1 本轮修复总览（`.claude/plans/yuoyuo-pwa-snazzy-parnas.md` 审计计划）

24 项审计 → 4 项破坏性回归 + 5 项 UX 致命 + 5 项 UGC 补丁 + 6 项体验补强 + 4 项打磨 = 全部完成。

| 批次 | 主题 | PR 号 |
|---|---|---|
| **A 系列（hotfix）** | Layer 1.5 crash / gender 422 / turn_end 卡死 / voice DB resolver | #135, #136 |
| **B 系列（UX 致命）** | 已读语义 + PWA 角标 / 清空聊天 / 注销漏洞 + 成年判断 / 滑块测试 / Splash 白屏 / iOS 输入放大 | #144–#147, #142, #143, #6251233, #f48fd6b, #935ada9 |
| **C 系列（产品补强）** | 表单持久化 / 全局滑手势 / 自建角标 / 头像上传 spinner / 预设音色真预览 / gender 字段 | #148–#154 |
| **D 系列（打磨）** | 交易页错误 UI / Clone 音色扣费顺序 / Proactive 配额持久化 / 死代码清理 | #155–#158 |

### 0.2 特别关注：PR #150 → #154 的"假修复 → 真修复"（血泪教训）

- PR #150 (C-5 v1) 用 CDN 占位符 URL 填 `preset_voices.sample_url`，让 ▶ 按钮**渲染**——但点击 `audio.play().catch(() => {})` 静默 404，用户点了没反应。
- PR #154 (C-5 v2) **真修**：新增 `GET /api/voice/presets/{preset_id}/sample` 后端 TTS 代理端点（MiniMax 合成 + 进程内缓存），迁移 031 把 sample_url 改为端点路径，前端改 blob URL 加错误 toast。
- **教训**：任何"让按钮出现"的修复必须验证按钮"能工作"。CLAUDE.md 已加"UI 修复必须真机测过"铁律。

### 0.3 数据库迁移变更（关键）

自 2026-07-08 后新增迁移：

- **025** `voice_tables` — `preset_voices` / `character_voices` / `voice_clone_jobs` 表
- **026** `message_kind` — `chat_messages.kind` 列（区分 action bubble / text bubble）
- **027** `preset_voice_gender` — 预设音色加 `gender` 列 + 6 行种子
- **028** `soft_delete_email` — 用户表加 `deleted_at` / `deletion_grace_end` / `original_email`，注销走 30 天冷静期，堵积分套利
- **029** `read_state` — `user_character_read_state` 表（已读语义 + PWA 角标）
- **030** `preset_voice_sample_urls` — （被 031 覆盖，见 §0.2）
- **031** `preset_voice_sample_endpoint` — `sample_url` 改为 `/api/voice/presets/:id/sample`

**当前 alembic heads = 2**（`022_identity_narrative_backfill` + `031_preset_voice_sample_endpoint`）。生产上线前应加一个 merge migration；本地开发环境可 `alembic upgrade <head_a>` 然后 `alembic upgrade <head_b>` 各自 upgrade（CLAUDE.md 铁律）。

### 0.4 环境配置变更

- 无新增 `settings.*` 必填项；`MINIMAX_API_KEY` 是**试听按钮**的硬依赖（未配置 → 端点 503）
- `MINIMAX_GROUP_ID` 可为空（`/t2a_v2` 端点不需要）
- `EMBEDDING_API_KEY` 仍是语义召回的门控开关，未配置 → 退回 recency/identity

### 0.5 拉取最新代码后必做清单

**每次 `git pull` 后，按顺序执行（禁止跳步）：**

```bash
# 1. 停 dev server（CLAUDE.md 铁律：hot-reload + 新 schema = 撒谎式绿灯）
#    如果 uvicorn 在跑，Ctrl-C

cd /Users/wanglixun/heart

# 2. 拉最新代码
git pull origin main

# 3. 装依赖（如果有新依赖）
cd backend && pip install -r requirements.txt
cd ../web && pnpm install    # 或 npm install，取决于本地

# 4. DB migration —— 多 head 必须显式逐个 upgrade
cd ../backend
alembic current                                   # 看当前状态
alembic heads                                     # 看应到达的头
alembic upgrade 022_identity_narrative_backfill   # 第一个 head
alembic upgrade 031_preset_voice_sample_endpoint  # 第二个 head
alembic current                                   # 确认两个 head 都是 (head) 且 applied

# 5. 关键：验证 6 行预设音色都指向 endpoint（PR #154 的核心）
python3 -c "
import asyncio
from sqlalchemy import text
from heart.api.wiring import _get_session_factory
async def main():
    async with _get_session_factory()() as db:
        r = await db.execute(text(
            \"SELECT id, sample_url FROM preset_voices ORDER BY id\"
        ))
        for row in r.mappings():
            assert row['sample_url'].startswith('/api/voice/presets/'), row
            print('OK', dict(row))
asyncio.run(main())
"
# 期望：6 行输出全部是 /api/voice/presets/*/sample

# 6. 起后端（完全冷启，不是 --reload；SQLAlchemy metadata 只在启动时抓）
cd /Users/wanglixun/heart/backend
uvicorn heart.api.main:app --host 0.0.0.0 --port 8000 --reload   # dev 可 --reload

# 7. 起前端
cd /Users/wanglixun/heart/web
pnpm run dev    # 默认 5173

# 8. 起 Cloudflare Tunnel（示例，用你自己的 tunnel name）
cloudflared tunnel run yuoyuo
```

### 0.6 部署前健康自检（Cloudflare Tunnel 前必看）

- [ ] `.env` 里 `MINIMAX_API_KEY` 有值（否则预设音色 ▶ 按钮点了 503）
- [ ] `.env` 里 `EMBEDDING_API_KEY` 有值（否则语义召回退回 recency）
- [ ] `.env` 里 `POSTGRES_*` / `REDIS_URL` / `S3_*` 都能连上
- [ ] `alembic current` 显示两个 `(head)` 都已 applied
- [ ] 后端启动日志无 `migration_drift_detected ERROR`（`heart/infra/migration_check.py`）
- [ ] 后端启动日志无 `TypeError: '<' not supported between instances of 'str' and 'int'`（Layer 1.5 crash 已修，PR #135）
- [ ] `GET http://localhost:8000/api/voice/presets` 返回 6 行，`sample_url` 全是 `/api/voice/presets/*/sample`
- [ ] `GET http://localhost:8000/api/voice/presets/rin_default/sample` 用有效 Bearer token 请求，返回 `audio/mpeg` 且 body 非空（首次 1-3 s，之后走进程内缓存瞬回）
- [ ] `docker ps` 或 systemctl 确认 workers（memory_encoder / memory_extractor / memory_promoter / account_purge / credit_reconciliation）在运行

### 0.7 已知非阻塞项

- **两 alembic head**：本地/staging 无害，生产合并前建议加 merge migration
- **`archive/ci-legacy/` 遗留**：不影响 CI，不动
- **`CONVERSATION_THREADS` 已删**：如果 IDE 缓存报 undefined 引用，忽略
- **`useProactivePolling` 尚未接入 Initiative Decider / ProactiveMessageGenerator**：不阻塞聊天，Wave E 可做
- **桌面浏览器不支持左边缘右滑手势（by design）**：`useSwipeNavigation` 只监听 `touchstart/touchmove/touchend`；桌面鼠标无事件。PWA 主设备是手机，桌面手势不属于 launch 关键路径。若后续需要，在 `useSwipeNavigation.ts` 加 `mousedown/mousemove/mouseup` 平行分支（F-6 设计方案）。

### 0.8 完整 PR 列表（2026-07-08 → 2026-07-11，从旧到新）

```
#128 P0 persona 注入 — UGC 身份写入 system prompt + 后过滤清洗
#129 Wave A — mobile UI + PWA login persistence + proactive 时区
#130 PR B1 — message splitting + centesimal credits
#131 PR B2 — voice system (preset voices + clone + DB resolver)
#132 PR C1+C2 — typing indicator + eliminate hard-refresh redirects
     0c383c9 / e8e673e — PWA 审计 P0/P1/P2 首轮修复（多 bug 混合 commit）
#135 Batch A hotfixes — Layer 1.5 crash / gender 422 / turn_end / voice DB
#136 migration drift 报警 + voice endpoint 回退 VOICE_CATALOG
#137 /character-backstage 音色配置链接跳转
#138 语义消息分块 — action + text bubble + per-bubble billing
#139 语音模式修复 — 保留 voice bubble、单次扣费
#140 音色按角色 gender 过滤
#141 DB 迁移与环境同步铁律入 CLAUDE.md
#142 关闭重注册积分套利 + 30 天注销冷静期恢复
#143 清空聊天真的调后端 API
#144 ChatInput textarea + 全站输入框 font-size ≥ 16px
#145 消灭 PWA 冷启白屏
#146 服务端已读状态 + 全局 PWA 角标
#147 滑块 → prompt 端到端测试覆盖
#148 UGC 自建角标
#149 CharacterDraft 加 gender 字段
#150 预设音色 sample_url 种子（假修，见 §0.2）
#151 表单持久化 + 滚动恢复
#152 全局滑手势
#153 async boto3 S3 上传 + 头像 spinner
#154 预设音色 ▶ 真预览（后端 TTS 代理 + blob URL + toast）  ← 覆盖 #150
#155 Clone 音色成功后扣费（防丢钱）+ MIME 白名单
#156 交易页错误/加载合并按钮
#157 删除 CONVERSATION_THREADS 死代码
#158 Proactive 配额改读 DB + 删死 import
```

---

## 0-legacy. 近期进展（2026-07-06）— 记忆系统已修复，勿再当坏的

> ⚠️ 给新会话：下面这些**已经修完并合并 main**。旧文档 `docs/TEST_RESULTS.md` / `docs/MEMORY_FIX_PLAN.md`
> 描述的"记忆坏了/召回不触发/情绪硬编码/L4 脏数据"**都已修复**，那两份是历史工单，勿据其重做。

- **#86** 商业外壳（Email OTP 登录、积分、Profile、聊天持久化、语音）+ fastapi<0.137 修复。
- **#87** 记忆 PR1：召回回写 `recall_count` + L2 真实情绪/importance + 短期窗口 40→50。
- **#88** CI 修复：前端 `vite build` 崩溃（rolldown 单平台 lockfile 缺 linux 原生二进制）。
- **#89** 记忆 PR2：Resolver 拦截疑问句污染 L4（"什么吗"）+ `cleanup_dirty_l4.py`。
- **#90** 记忆 PR3：`EmotionEvent` 持久化（此前从不落库）。
- **#91–#94** 记忆 PR4：**语义召回端到端打通**——`EmbeddingService`（bge-m3 1024 维）、
  `semantic_vector` 768→1024（迁移 017）、L2/L3 写向量、composer 算 query embedding、回填脚本。
  **门控于 `EMBEDDING_API_KEY`**：不配则退回 recency/identity，系统正常。

**本地 docker 环境已启用语义召回**（迁移 017 已跑、572 L2 + 196 L3 已回填、脏 L4 已清、实测 `vector` 策略生效）。
staging/prod 需各自跑：`alembic upgrade heads` + `backfill_embeddings.py --apply` + 配 key（详见执行手册 §7）。

**仍保留（设计如此/非 bug）**：scene_context 缺失、L2/L3 结构差异、`drifting` 关系态。

**待办功能（未实现）**：`docs/upgrade/commercial/06_anonymous_email_delivery.md`（匿名邮件 OTP 投递，
前置 `EmailSender` 抽象已就绪，可直接开发）；PWA "安装到桌面/主屏"（当前无 manifest/SW，见手册 §9）。

### 2026-07-08 第二轮全功能测试（`docs/TEST_REPORT_2026-07-08.md`：34 PASS / 0 FAIL / 29 BLOCKED）
- **BUG-4（P0）已修复** → PR #112：`proactive_messages` 表缺失致 ritual dedup 静默失败、每分钟堆积早安消息；rituals 亦绕过每日配额。修复＝新建表（迁移 018）+ 持久化 tick/ritual + 真实 dedup + 纳入配额 + `/pending` 读库 + 新增 `/ack`。
- **前端 SUG-1/SUG-2 已实现**（规划见 `docs/design/proactive_frontend_plan.md`）→ PR #114（全局 Toast store）+ #115（语音/TTS 失败友好提示，SUG-1）+ #116（主动消息轮询/展示，SUG-2）。已解锁测试项 PROA-02~06。**遗留（另案）**：主动消息目前仅本 session 展示，写入服务端聊天历史以跨刷新存续属后续后端改动。
- **角色 UGC 重构（SUG-3/BUG-3）** → `docs/design/ugc_character_refactor_plan.md`：
  - **C1 消灭硬编码** ✅ 已合并 → PR #118：live 路径的 `{"rin","dorothy"}` 硬编码收敛到 `ss01_soul/character_content.py` 单一来源（persona/templates/ritual），角色名从 Soul Spec 派生。rin/dorothy 行为不变。
  - **C2 characters 表 + 列表 API** ✅ 已合并 → PR #119：迁移 019 建 `characters` 目录表（回填 rin/dorothy 内置角色，零数据迁移）；`GET /api/characters`（display_name 从 Soul Spec 派生）；`is_known_character` 边界校验接入 `routes_characters` + chat WS。
  - **C3 Soul Spec 改 DB 来源 + 热加载（C3a）** ✅ 已合并 → PR #123：`soul_specs` 表（迁移 020）、`spec_store.py` DB 层、registry `load_db_overlay` + `register_spec` + `invalidate` + `generation` memo、`reload.py` 权威失效入口、wiring 双单例折叠、main.py 启动预热；内置 rin/dorothy 文件路径零改动。
  - **C4 前端动态化** ✅ 已合并 → PR #121：前端角色列表改为运行时消费 `GET /api/characters`（新增 `charactersStore` + `getCharacters()`），`CharacterId` 联合类型降为 `string`，`CHARACTER_PROFILES` 退化为「视觉资源表」并新增 `resolveCharacterProfile` 兜底；catalog 失败/冷启回退内置角色，rin/dorothy 行为不变。纯前端、零后端改动、零数据迁移。
  - **C5 UGC 角色创作后端（C5a）** ✅ 已合并 → PR #124：`draft.py`（CharacterDraft）、`spec_builder.py`（确定性 SoulSpec 展开器，无 LLM）、`persona_screen.py`（创建时阻塞安全审核）、`content_store.py` + 迁移 021（运营文案表）、`character_content.py` 进程内覆盖缓存、`routes_characters.py` POST/PATCH/DELETE UGC CRUD 端点；36 个 spec_builder 单元测试 + 6 个 persona_screen 单元测试。
  - **C5 UGC 角色创作前端（C5b）** ✅ 已合并 → PR #125：`CreateCharacterPage`（/characters/new，2 步表单：名字/人设/口癖/风格 → 6 个性格滑块 + 预览；支持 ?edit= 编辑模式）、`MyCharactersPage`（/my-characters，可见范围/停用管理）；`api.ts` 新增 UGC CRUD 函数；`charactersStore` 扩展 `createCharacter/updateCharacter/setVisibility/disableCharacter`。

---

## 1. 一句话 TL;DR（历史，2026-06-21）

> ✅ SS02 Memory LLM Extractor 重构交付完结。v1.0.3 达到 47/49 (95.9%) strict pass。
> （注：其后已叠加 #86–#94，见上方 §0。）

---

## 2. 当前完成度

### 2.1 子系统实现 (SS01–SS08)

| 模块 | 名称 | 代码 | Spec | 状态 |
|-----|------|------|------|------|
| SS01 | Soul / Identity Anchor | ✅ | `runtime_specs/01_*.md` | 在 main |
| SS02 | Memory (L1-L4) | ✅ | `runtime_specs/02_*.md` | LLM Extractor refactor 验收完成，v1.0.1 prompt 95.9% pass |
| SS03 | Emotion (VAD) | ✅ | `runtime_specs/03_*.md` | 在 main（PR #17 集成） |
| SS04 | Relationship Phase Engine | ✅ | `runtime_specs/04_*.md` | 在 main（PR #17 集成） |
| SS05 | Composer (多层人设组合) | ✅ | `runtime_specs/05_*.md` | 在 main（PR #17 集成） |
| SS06 | Inner State / Behavior | ✅ | `runtime_specs/06_*.md` | 在 main（PR #17 集成） |
| SS07 | Orchestration + Safety | ✅ | `runtime_specs/07_*.md` | 在 main（PR #17 集成） |
| SS08 | Infrastructure (data tier) | 部分 | `runtime_specs/08_*.md` | k8s 配置已在；DB/migrations 在 main |

### 2.2 Phase 完成度

```
Phase 0  Foundation                ✅ 完成
Phase 1  SS01 Soul                 ✅ 完成
Phase 2  SS02 Memory               ✅ 完成
Phase 3  SS03 Emotion              ✅ 完成（已合并 main，PR #17）
Phase 4  SS04 + SS05               ✅ 完成（已合并 main，PR #17）
Phase 5  SS06 Inner State          ✅ 完成（已合并 main，PR #17）
Phase 6  SS07 Orchestration+Safety ✅ 完成（已合并 main，PR #17）
Phase 7  集成 + Soul Drift 回归    ✅ 验证完成（7 Phase 全通过）
Phase 8  Closed Beta               ⏳ 未开始
```

---

## 3. 当前 Blocker（必须先做）

来源：`docs/execution/MEMORY_EXTRACTOR_REFACTOR_AUDIT_AND_v1_0_2_PLAN.md`（审计 + 修复方案）

| # | 阻塞项 | 严重度 | Issue/PR | 状态 |
|---|--------|--------|----------|------|
| - | v1.0.3 prompt + strict scoring | Complete | PR #42 | ✅ 47/49 (95.9%) |
| - | migration 009 typo fix | Hotfix | PR #45 | ✅ alembic upgrade head 全绿 |
| - | MiMo TTS provider | — | PR #43 | ✅ open |
| 1 | consolidator test 顶层 import 阻塞 unit collection | 🟡 P2 | #46 | ⏳ pre-existing |
| 2 | E2E /api/chat returns before session commit | 🟡 P2 | #47 | ⏳ 不阻塞前端 |
| 3 | encoder-worker restart loop | 🟠 P1 | #48 | ⏳ 阻塞 Closed Beta |
| 4 | v1.1.0 backlog (frag-004/mixd-002/adv-005) | 🟡 P2 | #44 | ⏳ prompt 迭代 |

**✅ SS02 Memory LLM Extractor 重构交付完结 @ 2026-06-21**。PR #42 等 review + merge。P0 全清（untracked files 入 git / 分支拆解 / PR 合规 / migration hotfix）。

---

## 4. 当前开发重点（按优先级）

> SS02 Memory Extractor 重构全部 PR 完成。下一步：合 main → 前端栈决策。

1. **合 main** — 当前 `feat/mimo-tts-provider` 分支合入 main，PR + merge。
2. **前端技术栈决策** — 输出 `docs/design/frontend_stack_decision.md`，HUMAN 拍板。
3. **Phase 9 Frontend MVP** — 按选定栈实施 Chat UI / Auth / Push。
4. **Phase 10 Closed Beta** — Staging bring-up / Alpha onboarding / Drift 监控。

**并行债务**：
- coref-004 precision (relation + other FP) → v1.1.0 prompt 迭代
- Prometheus metrics 缺口
- 集成测试金字塔、Soul Drift 回归

---

## 5. 下一步

1. ~~P0-1 untracked 文件 audit + add~~ ✅
2. ~~P0-2 拆分支 feat/ss02-llm-extractor-v1.0.3~~ ✅ PR #42 open
3. ~~P0-3 PR #41 收敛~~ ✅ closed → PR #43 MiMo clean
4. ~~P1-1 收敛 PR #39/#40~~ ✅ closed
5. ~~P1-2 v1.1.0 backlog issue~~ ✅ #44
6. ~~P0-A migration 009 hotfix~~ ✅ PR #45
7. ~~P1-A/B + P2-B issue 登记~~ ✅ #46/#47/#48
8. 👤 **HUMAN 决策** — 前端技术栈（RN+Expo / Flutter / Next.js）
9. ⏳ 等 PR #42 (SS02) + #43 (MiMo) + #45 (migration) merge → 前端启动

详见 `docs/execution/POST_SS02_NEXT_STEPS_2026-06-21.md`

## 6. 当前风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| **encoder-worker restart loop** | Closed Beta 时 L2/L3 pipeline 不通 | #48 登记，Phase 10 前置条件 |
| **E2E session write race** | E2E 不稳定，误报 | #47 登记，commit-then-respond 修 |
| consolidator test collection 阻塞 | unit run 有 15 个 error | #46 登记，lazy import |
| SS05/SS06 测试覆盖不足 | 回归风险 | 并行债务 |

---

## 7. CI / 工程基础设施

**已废弃**：Gitee Go 高级流水线、artifact upload、deploy、release workflow。原因：需要主机组，billing 复杂，当前阶段不需要。

**当前 CI**：`scripts/ci.sh` 单一脚本，本地 / GitHub Actions 行为完全一致。

```bash
bash scripts/ci.sh                # lint + unit-tests + schema-validation
bash scripts/ci.sh lint
bash scripts/ci.sh unit-tests
bash scripts/ci.sh integration-tests   # opt-in，需本地 postgres + redis + API key
```

历史 CI 配置存放：`archive/ci-legacy/`。

---

## 8. 文档导航（最小集）

新 session 推荐阅读顺序：

```
1. docs/PROJECT_STATUS.md          ← 本文件（必读）
2. docs/audit/2026-06-20_dual_mode_skip_rationale.md  ← dual-mode 跳过理由
3. docs/execution/MEMORY_EXTRACTOR_REFACTOR_AUDIT_AND_v1_0_2_PLAN.md  ← 审计 + v1.0.2 方案
4. docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md  ← SS02 refactor 主 spec
5. docs/design/memory_golden_set_design.md  ← Golden Set + strict scoring 定义
```

其余文档详见 [`docs/README.md`](README.md)。

---

## 9. 维护规则

- **每次完成一个 Top 10 item 必须更新本文件 §3 表格**。
- **每个 Phase 切换必须重写本文件 §2/§4/§5**。
- **新增 blocker 必须进 §3，不进 GitHub Issues 不算数**（除非 issues 工作流后续被启用）。
- 这份文件不能超过 200 行；超了说明需要把细节移到 `docs/design/` 或 `docs/audit/`。
- **✅ SS02 Memory LLM Extractor 重构交付完结 @ 2026-06-21** — PR #42 (v1.0.3, 47/49 95.9%)
- **PR open**: #42 (SS02) + #43 (MiMo TTS) + #45 (migration hotfix)
- **Issues**: #44 (v1.1.0) / #46 (consolidator) / #47 (E2E) / #48 (encoder)
- **P0 全清** — untracked files 入 git / 分支拆解 / PR 合规 / migration hotfix
- 验收文档: `docs/execution/SS02_ACCEPTANCE_AND_NEXT_STEPS_2026-06-21.md` + `POST_SS02_NEXT_STEPS_2026-06-21.md`
