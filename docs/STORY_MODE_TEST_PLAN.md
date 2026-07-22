# 剧情模式（Story Mode / SS09）完整测试文档

> 面向 **wanglixun + mimo** 的端到端手工测试手册。
> 覆盖 7 个已合并 PR：迁移+读API / 探索页 / 引擎+WS / 播放器 / 摘要+安全+扣费 / 导入管线 / 首页精选卡。
>
> **测试目标**：把 Heart 从「AI 角色聊天」升级为「AI 陪伴 + AI 互动剧情平台」后，验证"首页发现 → 探索页 → 详情填主控卡 → 回合制开局 → 续玩恢复"的完整闭环，以及安全预检、扣费、成人向 age-gate、长局滚动摘要。

---

## 0. 前置准备

### 0.1 启动本地环境

```bash
# 仓库根目录
cd /Users/wanglixun/heart

# 一键起 postgres + redis + uvicorn(:8000) + vite(:5173)
bash scripts/dev.sh
```

- 前端：http://localhost:5173
- 后端：http://localhost:8000 （API 前缀 `/api`，文档 `/docs`）
- 前端已配置代理：`/api` → `:8000`，`/api/*/ws` → `ws://:8000`

### 0.2 数据库迁移必须到位（CLAUDE.md DB 铁律）

```bash
cd backend
alembic current      # 必须包含 042_story_scenarios
alembic heads        # current 应等于 heads；不等就 alembic upgrade head
```

> ⚠️ 若中途切过分支/拉过代码，**先停 uvicorn 再重启**（`--reload` 不会重连 DB pool、不会重抓 SQLAlchemy metadata）。改过列后必须**完整重启**后端，不能只靠热重载。

### 0.3 导入剧本（PR6 导入管线）

迁移 042 已内置 **2 个 all-ages 种子剧本**（`雨停，天晴`、`联姻对象？好难选啊`），可直接测基本流程。
要测全量 46 个（含成人向），跑导入器：

```bash
cd backend

# 1) 先干跑采样 5 个，核对题材/分级抽取是否合理
python scripts/import_scenarios.py --dry-run --limit 5

# 2) 全量导入为 draft（默认）
python scripts/import_scenarios.py

# 3) 人工过审后发布（翻 published）
python scripts/import_scenarios.py --publish
```

- 源目录默认 `/Users/wanglixun/Downloads/剧情设定/`（46 个 `.txt`）。
- **原文注入**：`.txt` 原文逐字作为 GM 系统提示，未做规整/净化。
- 幂等：`slug`=文件名、`source_hash` 未变则跳过。重复跑安全。
- 分级：检测到 18禁/成人开关 → `maturity='adult'`，否则 `all_ages`。

> 导入需真实 DB + LLM key（`DEEPSEEK_API_KEY`）。`--dry-run` 不写库但仍调 LLM 展示抽取。

### 0.4 测试账号

- 准备 **两个账号**：
  - **账号 A（未验龄）**：验证成人向剧本被 age-gate 拦。
  - **账号 B（已验龄）**：走 `/age-gate` 完成年龄验证后，验证成人向可进。
- 若要测扣费：确保账号有余额（默认剧情模型 `deepseek` 计费为 0，**免费**；付费模型才扣费——见 §6）。

---

## 1. 首页精选卡（PR7）

| # | 步骤 | 期望结果 |
|---|------|---------|
| 1.1 | 登录后进入首页 | 「快捷入口」下方出现 **「今日剧情推荐」** 卡片（若已有 `is_featured=true` 且 `published` 的剧本）。 |
| 1.2 | 观察卡片内容 | 显示 🔥题材 chip + 标题 + 简介 + `已有 N 人游玩`（play_count=0 时显示「抢先体验」；≥1万显示「1.2万」样式）。 |
| 1.3 | 点卡片主体 | 跳转到 `/explore/:scenarioId` 剧本详情页。 |
| 1.4 | 点右上「更多」 | 跳转 `/explore` 探索页。 |
| 1.5 | 无精选剧本时 | 卡片**静默隐藏**，首页不留空槽、不报错、不阻塞加载。 |
| 1.6 | 断网/后端 500 | 卡片静默隐藏，首页其余部分正常（best-effort，不阻塞）。 |
| 1.7 | 账号 A（未验龄）看到成人向精选 | 卡片显示 `🔞 18+` 锁标；点击进详情走验龄引导（见 §5）。 |

---

## 2. 探索页（PR2）

| # | 步骤 | 期望结果 |
|---|------|---------|
| 2.1 | 底部 TabBar 点「探索」 | 进入 `/explore`。 |
| 2.2 | 观察顶部 | 精选剧本 **hero 大卡**（`is_featured` 优先）。 |
| 2.3 | 题材筛选 chips | 显示各题材 + 计数（校园恋爱/悬疑/末日无限流/修仙/古风宫斗/现代豪门/西幻/其他）。 |
| 2.4 | 点某题材 chip | 网格只显示该题材剧本；再点「全部」恢复。 |
| 2.5 | 剧本卡片 | 封面 + 标题 + 题材 chip + 🔥play_count。 |
| 2.6 | 成人向卡片（账号 A） | 显示 🔞 锁；简介被替换为「🔞 需完成年龄验证后查看」。 |
| 2.7 | 加载失败 | 显示 ErrorState + 重试按钮，点击可重新拉取。 |
| 2.8 | 点任意卡片 | 进入 `/explore/:scenarioId` 详情。 |

---

## 3. 剧本详情 + 开局（PR2 详情 + PR4 主控卡）

| # | 步骤 | 期望结果 |
|---|------|---------|
| 3.1 | 详情页 | 封面/标题/题材/简介展示正常。 |
| 3.2 | 点「开始剧情」 | 弹出 **主控卡底部 sheet（StartRunSheet）**。 |
| 3.3 | 主控卡字段 | 姓名(必填)/年龄/性别(必填,下拉)/外貌/性格/星座/MBTI/身份/生平。 |
| 3.4 | 必填未填直接提交 | 阻止提交并提示（姓名、性别必填）。 |
| 3.5 | 填完提交 | `POST /api/story/runs`，成功后跳 `/story/:runId`，播放器已带 **开场旁白气泡**。 |
| 3.6 | 该剧本 play_count | 开局后 +1（回到探索页/首页刷新可见）。 |

---

## 4. 回合制播放器（PR4 + PR3 引擎/WS）

| # | 步骤 | 期望结果 |
|---|------|---------|
| 4.1 | 进入播放器 | 开场为 GM `【旁白】`（居中灰斜体气泡）。 |
| 4.2 | 输入行动/对白，发送 | 我方消息右侧气泡；GM 开始「续写」流式 `text_delta`（带光标 ▍）。 |
| 4.3 | GM 回合结束 | 流式气泡被服务端**切分气泡**替换：`【旁白】`→居中旁白；`**角色名**`→左侧 NPC 对白（带名字标签）；`（动作）`→居中暗色斜体。 |
| 4.4 | 连续多轮 | 每轮结束都停下等待主控输入，绝不替主控行动。 |
| 4.5 | 生成中点「停止」 | 发 `interrupt`，停止本轮续写。 |
| 4.6 | 模型不守格式（无标记） | **降级为单条 narration**，不崩局、不报错。 |
| 4.7 | 断线 | 自动重连；token 过期(1008)自动刷新重连；引擎不可用(1011)不狂重连、提示一次。 |
| 4.8 | 90s 无响应 | 看门狗清除「续写中」状态并提示「响应超时，请重试」。 |
| 4.9 | 返回后重进 `/story/:runId` | **续玩**：完整流水按 seq 恢复（`GET /api/story/runs/{run_id}`）。 |
| 4.10 | 发空消息 | 前端拦截，不发送；后端也返回 `empty_message`。 |

---

## 5. 成人向 age-gate（决策 3）

| # | 步骤 | 期望结果 |
|---|------|---------|
| 5.1 | 账号 A（未验龄）点成人向剧本 | 卡片/详情显示锁；尝试开局被引导到 `/age-gate`。 |
| 5.2 | 账号 A 直接 WS 连成人向 run | 服务端握手校验：发 `error{code:'age_gate_required'}` 并关闭连接（前端提示「这是成人向剧情，需要先完成年龄验证」）。 |
| 5.3 | 账号 A 直接 `POST /api/story/runs` 成人向 | 被 `require_age_verified` 依赖拦（服务端纵深防御，返回未验龄错误）。 |
| 5.4 | 账号 B 完成 `/age-gate` 验龄 | 成人向剧本解锁：卡片去锁、简介正常、可开局可对话。 |
| 5.5 | 成人/言情内容本身 | **不被安全层误杀**（言情/成人非安全类别，见 §6.3）。内容保留，不做 SFW 净化。 |

---

## 6. 安全预检 + 扣费（PR5）

### 6.1 扣费对齐

| # | 步骤 | 期望结果 |
|---|------|---------|
| 6.1a | 默认 `deepseek` 模型开局对话 | **免费**（`llm_cost_fen('deepseek')=0`），余额不变，不触发 billing。 |
| 6.1b | 付费模型（如 claude/grok）且余额充足 | 每轮生成成功后扣费一次；幂等键 `story_turn:<turn_id>:llm`、类型 `consume_llm`。 |
| 6.1c | 付费模型余额不足 | **生成前**拦截，发 `error{code:'insufficient_credits'}`，前端提示「余额不足，请充值后继续剧情」；不生成、不扣费。 |
| 6.1d | 重连/重试同一 turn | 幂等键保证不重复扣费。 |

### 6.2 安全预检（仅拦最高危）

| # | 输入 | 期望结果 |
|---|------|---------|
| 6.2a | 自残/自杀危机类表达（PURPLE） | 发 `error{code:'safety_blocked'}`；提示「这条内容涉及高风险话题，无法继续。如果你正处于困境，请寻求专业帮助。」；**不生成、不落库**。 |
| 6.2b | 违法/伤害他人（RED） | 同上，拦截。 |
| 6.2c | 普通剧情推进（GREEN/YELLOW/ORANGE） | 正常放行。 |
| 6.2d | 言情/亲密/成人向表达 | **放行**（非安全词库类别，符合决策 3）。 |
| 6.2e | 安全分类器异常 | **fail-open**（记录日志，不拦截，不崩局）。 |

### 6.3 滚动摘要（长局上下文控制）

| # | 步骤 | 期望结果 |
|---|------|---------|
| 6.3a | 同一局连续玩 **16+ 轮**（超过 `SUMMARIZE_TRIGGER = RECENT_TURNS_WINDOW×2`） | 后台在 `turn_end` 之后把较早轮次折叠进 `story_runs.summary`，推进 `summary_watermark`；玩家侧无感、不卡顿。 |
| 6.3b | 摘要后继续对话 | GM 仍记得前情（摘要注入系统提示），上下文不爆窗。 |
| 6.3c | 摘要 LLM 失败 | 静默跳过本次折叠，不影响当前局继续。 |

> 验证摘要是否发生：`SELECT summary, summary_watermark, turn_count FROM story_runs WHERE id='<run_id>';` —— watermark 应 > 0 且 summary 非空。

---

## 7. REST API 直测（可选，用 `/docs` 或 curl）

前缀 `/api/story`，除 `/scenarios`、`/genres` 外均需 Bearer token。

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/story/scenarios?genre=&featured=&limit=&offset=` | 已发布剧本列表；成人向未验龄返回 `locked:true`。 |
| GET | `/api/story/genres` | 题材 + 计数。 |
| GET | `/api/story/scenarios/{id}` | 详情 + `player_template`。 |
| POST | `/api/story/runs` | body `{scenario_id, player_identity}` → `{run_id, ...opening bubbles}`；成人向挂 `require_age_verified`。 |
| GET | `/api/story/runs` | 我的局（active 优先）。 |
| GET | `/api/story/runs/{run_id}` | run 元信息 + 分页流水（按 seq）。 |
| DELETE | `/api/story/runs/{run_id}` | 逻辑删除（`status='deleted'`）。 |

WebSocket：`ws://localhost:8000/api/story/ws?token=<accessToken>`
- client→server：`{type:'story_chat', run_id, text, turn_id}`、`{type:'interrupt', turn_id}`
- server→client：`turn_start` / `text_delta` / `message_bubble{kind,npc_name?}` / `turn_end{ok}` / `error{code}`

**错误码对照**（前端 toast 文案）：

| code | 文案 |
|---|---|
| `engine_unavailable` | 剧情引擎暂时不可用，请稍后再试 |
| `age_gate_required` | 这是成人向剧情，需要先完成年龄验证 |
| `run_not_found` | 这局剧情不存在或已结束 |
| `empty_message` | 说点什么再发送吧 |
| `generation_failed` | 生成失败，请重试 |
| `insufficient_credits` | 余额不足，请充值后继续剧情 |
| `safety_blocked` | 这条内容涉及高风险话题，无法继续。如果你正处于困境，请寻求专业帮助。 |

---

## 8. 导入器抽取质量核对（PR6，mimo 重点）

用 `--dry-run` 采样，人工核对 LLM 抽取的卡片元数据是否合理（**不影响正文，仅影响展示卡**）：

```bash
cd backend
python scripts/import_scenarios.py --dry-run --only 登仙        # 单个
python scripts/import_scenarios.py --dry-run --limit 10         # 前 10 个
```

核对清单（每个样本）：
- [ ] `title` 简洁贴切（≤16 字），错了不影响玩，仅卡片显示。
- [ ] `genre` 归入 8 类枚举合理（错标→改后重导，`source_hash` 变化会触发更新）。
- [ ] `blurb` ≤40 字、不剧透关键反转。
- [ ] `maturity` 分级正确：**明显成人向必须 `adult`**（漏标=合规风险，重点核！）。
- [ ] 至少覆盖不同题材/分级各 1 个样本。

> 抽取错了怎么办：直接改 DB（`UPDATE story_scenarios SET genre=..., maturity=... WHERE slug=...`），或修正后用 `--publish` 重导（幂等 upsert）。**正文 `gm_system_prompt` 永远是原文，不受抽取影响。**

---

## 9. 回归红线（务必顺带确认没被剧情模式影响）

- [ ] 原聊天功能（`/chat/:characterId`）正常：文字/语音/主动消息不受影响。
- [ ] 剧情表 `story_*` 与聊天表 `chat_messages`/`sessions` **完全独立**，互不干扰。
- [ ] 剧情走独立 WS `/api/story/ws`，不影响 `/api/chat/ws`。
- [ ] TabBar 新增「探索」标签不破坏原有导航。

---

## 10. 问题上报模板

发现问题时请附：

```
【环境】账号(A未验龄/B已验龄) + 剧本 slug + run_id
【步骤】第几节第几步（如 4.3）
【期望】...
【实际】...
【附件】前端 toast 文案截图 / 浏览器 Console 报错 / 后端 uvicorn 日志片段
【DB 状态】（涉及扣费/摘要时）相关 story_runs / balance 行
```

> ⚠️ 若出现「空气泡」「音频/内容已过期」「明明修了还报同样 bug」类现象，**先查 §0.2 迁移是否到位、后端是否完整重启**（历史血泪教训：schema 落后 + `--reload` 不重连 = 撒谎式绿灯）。

---

**关联 PR**：#251–#257（PR1–PR7）
**最后更新**：2026-07-22
