# UGC 角色呈现层缺口与创建功能重构方案

> 创建：2026-08-11 · 基于代码精读（非凭记忆），每条附验证位置
> 范围：UGC 角色的**详情页 UI + 聊天页开场钩子**，与内置 37 个 bespoke 角色的对比
> 配套：`UGC_COMPATIBILITY_GAPS.md`（2026-07-09）覆盖后端行为层，本文覆盖呈现层，两者互补不重叠

---

## 1. 根因：profile DTO 无 UI 字段

内置角色详情页精美，靠的是三样东西，UGC 一样都拿不到：

| 机制 | 代码位置 | 键 | UGC 能否拿到 |
|------|----------|-----|-------------|
| bespoke 详情页组件 | `web/src/components/characterProfiles/index.ts`（75 行 export） | 按 character id 硬编码 | 拿不到 |
| `CHROME_PALETTES`（14 槽位配色） | `web/src/pages/CharacterProfilePage.tsx:87` | 按 character id 硬编码 | 拿不到 |
| `PREMISE_CARDS`（开场档案卡） | `web/src/components/ConversationChatPage.tsx:78` | 按 character id 硬编码 | 拿不到 |

判定分支在 `CharacterProfilePage.tsx:948-952`：

```
const BespokeProfile = profile ? BESPOKE_PROFILES[id] : null
const chrome = CHROME_PALETTES[id]
if (profile && BespokeProfile && chrome) { /* bespoke 分支 */ }
```

两个条件都要满足才走 bespoke。UGC 角色的 id 不在任何 registry 里，**必然落到 generic 模板**。

后端 `GET /{character_id}/profile`（`routes_characters.py:263`）返回的 DTO 只有展示字段（name/tagline/intro/cover/age_range/gender/tags 等），**没有任何 UI 定制字段**。所以就算前端想读，也无源可读。

这就是"用户自建角色做不到这种精美程度"的完整机制解释。

---

## 2. 已经存在、不需要重新发明的东西

这部分很重要——避免把已有能力当缺口重做：

| 需求 | 既有实现 | 说明 |
|------|----------|------|
| 链接分享 | `CharacterDraft.visibility` 已是 `public｜unlisted｜private`（`draft.py:108`） | "链接分享"就是既有的 `unlisted`，不是新概念 |
| 嵌套式开场选项 | `CharacterUIConfig.starterBranches`（`characterUIConfig.ts`） | 乙游式"先选切入角度→展开台词"已建模，只是用户不可编辑 |
| 开场选项不限三条 | 分支路径下每个 branch 的台词数不限 | 见下节的唯一例外 |
| iframe 隔离 | bespoke 详情页本身就走 iframe | UGC 用 iframe 是沿用既有模式，不是新架构 |
| 开场白人审定稿 | `opening` 字段（≤2000 字，文档明确 "played back verbatim (no LLM)"，`draft.py:90-94`） | 与既有决策一致，勿设计成运行时生成 |

### 唯一的"三条"硬锁

`characterUIConfig.ts` 里平铺路径的类型是：

```
starterPrompts?: [string, string, string]
```

元组类型锁死三条。分支路径不受限。所以"选项不一定是三条、要多样"这个需求：分支路径已支持，平铺路径需把元组改成 `string[]` 并加运行时条数校验（建议 1–5），改完要回归 1 条和 5 条的排版。

---

## 3. 阻塞级安全缺陷（引入 UGC 前必须修）

**文件**：`web/src/components/characterProfiles/PremiseCardBase.tsx:88`

```
`<div class="row"><span class="label">${r.label}</span><span class="value">${r.value}</span></div>`
```

这段拼出的 HTML 字符串最终进 `srcDoc`（`:92` 构造、`:164` 注入）。`label` / `value` / `leadIn` / `title` / `note` / `warning` 六个字段**全无转义**，`web/package.json` 里也没有任何 HTML 净化库。

今天安全，仅因为数据源是手写的内置卡片。用户一旦能编辑开场卡片，这六个字段全是脚本注入入口。

**这一项必须独立先修、独立提交**，不与业务改动混在一个 PR（见第 7 节批 0）。

---

## 4. 功能一：「快速创建」

### 4.1 为什么不能只靠默认值

`CharacterDraft` 容忍字段缺失，但缺失后的结果不可接受：

| 字段 | 缺失时行为 | 后果 |
|------|-----------|------|
| `greeting_style` | 默认 `warm`（`draft.py:82`） | 所有快速创建角色都是"暖"，十个角色一个味 |
| `sliders` | 六项全 `0.5`（`draft.py:40-45`） | 性格完全中性，聊起来没区别 |
| `opening` | 空 | 角色没有开场白，且既有决策禁止运行时 LLM 兜底 |
| `catchphrases` | 空列表 | voice_dna 缺样本，口吻平淡 |
| `intro` / `tagline` | 回退到 `persona`（`routes_characters._derive_profile_presentation`） | 可接受，无需处理 |
| `age_range` | 纯展示字段，不入 persona | 可接受但详情页少一行信息 |

前两项是"人设被抹平"，第三项与既有的开场白决策直接冲突。nimoo 能只问 4 个字段是因为它运行时生成兜底；yuoyuo 已否掉那条路，所以不能照搬。

### 4.2 方案：4 字段表单 → 创建时一次 AI 预填 → 确认页 → 落库

**表单只问 4 项**：封面、名字、性别、人设描述（`persona` 有 `min_length=20`，描述不能太短）。

**AI 一次调用产出**：`age_range`、`greeting_style`、六个 `sliders`、`catchphrases`、`opening`、推荐主题配色（从 8 套预置里挑，如阴郁人设配哥特雾灰、明快配暖调）。

**可见性不由 AI 推**：私密还是链接分享是用户真实意图，默认 `private`。

### 4.3 确认页分两层，避免"看起来很重"

- **上层直接可见**：开场白全文（必须过人眼，这是"人审定稿"的全部意义）、主题配色色板、可见性开关
- **下层折叠进「更多设定」**：年龄段、相处风格、六个滑块、口癖，用一行摘要展示 AI 的选择（如"25-30 · 冷淡 · 话少而直接 · 3 条口癖"），点开可编辑

主按钮是「确认创建」，改是可选动作。开场白可重新生成，限 3 次，超次数只能手工改文字。

### 4.4 失败处理（不得静默兜底）

LLM 失败时**绝不能**偷偷套 `warm` + 全 0.5 然后假装成功——那正是 CLAUDE.md 禁止的欺骗式静默，用户会拿到一个被抹平的角色而不自知。

- 整体失败：确认页显示明确错误 + 重试按钮，不落库
- 部分字段失败：标明哪几项没拿到，用户重试或手填
- 长期不可用：给"转手动创作模式"的出口
- 日志按规范 `logger.exception(...)` 后 re-raise 或转结构化错误到前端

### 4.5 硬约束

- 只允许 `private` / `unlisted`，**不给 `public`**。前后端都要校验（后端见第 6 节 `creation_mode` validator），防止绕过前端直接打 API
- 不给 HTML 编辑、不给开场卡编辑
- 详情页走 generic 分支，但应用所选主题配色
- 音色不进创建流程：`voice_id` 在 `DbCharacter` 上不在 draft 里，且文字聊天不需要音色。落库时按性别给默认预置音色，用户后续在角色设置里改

---

## 5. 功能二：「角色创作」

### 5.1 核心矛盾

要详情页精美，就要用户产出足够内容——内置角色精美是因为那 37 个组件是手写的，各有一套排版语言。UGC 想达到同等水准，避不开让用户填更多。

所以设计目标**不是减少输入**（那是快速创建的职责），而是让填的过程本身有即时回报：每填一段，详情页当场变好看一点。

### 5.2 关键决策：反转"先选版式后填内容"

nimoo 的做法本质上还是让用户写 HTML 或选模板，用户得自己判断内容和版式怎么配。yuoyuo 反过来：**用户填什么内容，系统就生成对应区块**。

| 用户填了什么 | 自动生成什么区块 |
|-------------|----------------|
| 3 条以上身份/职业/状态信息 | 档案表（病历卡、身份档案那类） |
| 第一人称独白 | 大字引文区块（serif 排版） |
| 时间线式经历 | 纵向时间线 |
| 随身物件清单 | 物件隐喻区块 |
| 对立面/反差设定 | 对照区块 |

用户的视角是"在回答问题"，不是"在配界面"。

### 5.3 七步引导，每步一个问题 + 实时预览

进度不用百分比，用质感分级：**素描 → 半成品 → 有模样 → 成品**。每级对应新增区块，用户看到的是"再填一步能得到什么"，不是"还剩多少要做"。

1. 核心身份（名字/性别/封面/一句话钩子）
2. 人设描述 + tagline + intro + tags
3. 档案信息（→ 档案表当场出现）
4. 独白 / 语气样本（→ 引文区块出现）
5. 背景故事，三选：时间线 / 物件 / 对照（→ 对应区块出现）
6. 开场设计：开场白 + 开场档案卡 + 首聊引导
7. 主题配色 + 可见性 + 音色

草稿续填靠既有的 `GET /{character_id}/draft`（`routes_characters.py:855`）与 `PATCH /{character_id}`（`:879`）。

### 5.4 AI 在这里是"按需辅助"不是全量预填

与快速创建不同：每个输入框旁一个「帮我写」，用户点了才调用，产出直接填进该字段供修改。唯一例外是第 5 步可以「根据已填内容推荐时间线」——这步最容易卡住。

理由：角色创作的用户是要精细控制的，全量预填会干扰他们。

### 5.5 高级 HTML（分层的第二层）

区块编辑器覆盖不写代码的用户；额外给「高级模式」开放原始 HTML（≤50KB）。

**沙箱可以不给脚本**：已核对全部 37 个 bespoke 组件，`<script>` 出现次数为 0，动效全是 CSS。所以禁脚本对 UGC **不产生能力落差**，可以直接上最严设置。

关于既有 iframe 的 sandbox（**修正 2026-08-11 初稿的错误论断**）：`PremiseCardBase.tsx:166` 实际**有** `sandbox` 属性，值是 `allow-same-origin allow-scripts`。这个组合是已知的危险配置（两者同时给，沙箱可被脚本绕过访问父页 DOM）。但它有真实功能依赖：

- `allow-scripts` 支撑卡片的展开/收起（`onclick="parent.postMessage('toggle','*')"`）
- `allow-same-origin` 支撑高度测量（`:42-43` 读 `iframe.contentDocument.body.scrollHeight`），去掉则 `contentDocument` 返回 null，46 张卡片全部塌成默认 200px

**收紧方案（独立批次，不并入批 0）**：把高度测量从"父页读 contentDocument"改成"iframe 内部 postMessage 上报高度"——现成的 message 通道已经在用了。改完即可去掉 `allow-same-origin`。之所以单独走：它动的是全部 46 张卡片的版式测量，有回归风险，不该和转义修复混在一个 PR。

批 0 + 批 1 色值白名单落地后，注入面已经关闭（文本节点转义 + CSS 通道白名单），sandbox 收紧属纵深防御而非主漏洞。

存储前净化：移除 `<script>`、`on*` 事件属性、外链资源。公开需过审；私密/链接分享可跳过审核但仍须净化。提供 CSS 变量文档（`--theme-accent` 等）让用户的 HTML 能吃到所选配色。

区块与高级 HTML **互斥**：有 `custom_html` 优先用它，否则渲染 `profile_blocks`，都没有则 generic。

---

## 6. 后端 schema 改动

`CharacterDraft` 是 **Pydantic `BaseModel` + `extra="forbid"`**（`draft.py:48`），新字段必须显式声明，否则 API 直接拒。新增：

| 字段 | 类型 | 用途 |
|------|------|------|
| `creation_mode` | `Literal["quick","workshop"]` = `"quick"` | 区分两档，驱动校验 |
| `ui_chrome` | `Optional[ChromeDraft]` | 14 槽位配色，**复用前端既有 `ChromePalette` 结构** |
| `profile_blocks` | `list[ProfileBlock]`（默认空，上限 12） | 区块编辑器数据，`type` 字段辨别联合类型 |
| `custom_html` | `Optional[str]`（≤50KB） | 高级模式 |
| `premise_card` | `Optional[PremiseCardDraft]` | 字段对齐既有 `PremiseCardData`；注意 `warning` 是**字符串消息不是布尔** |
| `starter_config` | `Optional[StarterConfig]` | 平铺 1–5 条 或 分支式 |
| `opening_format` | `Literal["plain","rich"]` = `"plain"` | rich 时解析 `<scene>/<plot>/<dialogue>` 分层排版 |

全部存在 `soul_specs.draft` 的 JSONB 里，**无需 DB 迁移**。

### 6.1 两个必须加的 validator

**快速创建不得越权**（防绕过前端直接打 API）：

```
@model_validator(mode="after")
def quick_mode_limits(self):
    if self.creation_mode == "quick":
        if self.visibility == "public":
            raise ValueError("quick mode cannot be public")
        if self.custom_html or self.profile_blocks or self.premise_card:
            raise ValueError("quick mode cannot set workshop-only fields")
    return self
```

`PATCH /{character_id}/visibility`（`:946`）也要加同样的 quick→public 拦截。

**色值白名单**（配色进的是 CSS 通道，是注入面）：`ChromeDraft` 每个槽位只允许 `#hex` / `rgb()` / `rgba()` / `linear-gradient()` 正则匹配，禁任意字符串。这条把 `accent` 的注入风险一并解决（`PremiseCardBase` 把 `accent` 插进 CSS 属性值，转义函数救不了 CSS 上下文，只能靠白名单）。

### 6.2 路由改动

- `GET /{character_id}/profile`（`:263`）：DTO 补上新字段，前端才有源可读
- `POST ""`（`:695`）与 `PATCH /{character_id}`（`:879`）：接受新字段
- 复用 `POST /opening-preview`（`:802`）作 AI 辅助入口，或按需新开一个"推荐全套"端点

### 6.3 前端渲染改动

`CharacterProfilePage.tsx:948` 的分支改成三级链：

```
内置 bespoke（BESPOKE_PROFILES + CHROME_PALETTES 都命中）
  → UGC 定制（custom_html 或 profile_blocks）
  → generic
```

配色同样链式回退：`CHROME_PALETTES[id]` → `profile.ui_chrome` → 默认盘。内置优先级在前，**37 个 bespoke 组件一行不动**。

`ConversationChatPage.tsx:1140` 的开场卡：先查 `PREMISE_CARDS[id]`，没有则用 `character.premise_card` 喂 `PremiseCardBase`。

---

## 7. 分批实施

| 批 | 内容 | 依赖 |
|---|------|------|
| **0** | `PremiseCardBase` 六个字段转义 + 新建 `web/src/utils/escapeHtml.ts`。**独立 PR，不混业务** | 无 |
| **1** | 后端 draft 新字段 + validator + profile DTO 扩展 | 无 |
| **2** | 从 37 个角色配色提炼 8 套预置盘 + 配色选择器 + generic 分支应用配色 | 批 1 |
| **3** | `CreateHubPage` 出两档入口 + 快速创建 4 字段表单 | 批 1、2 |
| **4** | AI 预填一次调用 + 确认页（含失败处理） | 批 3 |
| **5** | 区块渲染器（7 种版式） | 批 1 |
| **6** | 七步引导 + 高级 HTML + `dompurify` | 批 5 |
| **7** | 开场卡编辑器 + starter 编辑器 + `starterPrompts` 元组改 `string[]` | 批 1 |

**批 2 单独合完，自建角色就能选按钮配色了**——这是解决你最初那个"按钮颜色不适配"痛点的最短路径，不用等整套做完。

`dompurify` 放批 6 而非批 0：转义只需 5 行的 `escapeHtml`，`dompurify` 是净化用户任意 HTML 时才用得上，提前加是未使用依赖。

**批 5 开工前先做一次验证**：手工塞一份 `profile_blocks` 假数据，确认区块渲染出来够不够看。整个七步引导的价值都建立在"填完真的好看"这个前提上，前提没验证就投开发是最大的浪费。

---

## 8. 待验证项（工具故障期间未能核对，开工前先查）

1. `build_soul_spec_from_draft()` 如何消费 `sliders` 与 `greeting_style`——确认 AI 预填的值真能影响行为，而不是被下游忽略
2. 空 `catchphrases` 在 voice_dna 构建里是否有特殊分支
3. 按性别给默认预置音色的逻辑是否已存在，还是要新写
4. `GET /{character_id}/draft` 是否支持未完成态草稿（七步引导中途退出要能续填）
5. `POST /opening-preview` 能否扩展成"一次推全套"，还是需要新端点

---

## 9. 待定决策（不卡前面几批，批 5 前定即可）

1. 预置调色盘做 8 套精选还是 12 套覆盖更广
2. 第 5 步的时间线 / 物件 / 对照，是三选一、至少选一，还是可多选
3. 完成度分级要不要与公开权限挂钩（例如只有"成品"级才允许申请公开）

---

## 10. 不作为

- 不把 37 个内置角色的配色搬进数据库。收益是"少一处重复"，代价是动全部 bespoke 组件 + 回归风险，不值当。以后想搬随时可以，架构没堵死。
- 不给 UGC 脚本能力。已核实内置角色零 `<script>`，禁脚本无能力落差。
- 不做反向降级（角色创作 → 快速创建）。升级是单向的：快速创建可升级进工坊，已填字段带过去从第 3 步续填，`creation_mode` 改 `workshop` 并解锁可见性选项。反向没有意义。

---

## 11. 批 0 完成记录（2026-08-11）

- 新建 `web/src/utils/escapeHtml.ts`：`escapeHtml`（严格）+ `escapeHtmlAllowBr`（仅放行 `<br>`）
- `PremiseCardBase.tsx` 六个字段接上转义：`label`/`value`/`leadIn`/`title`/`warning` 用严格版，`note` 用允许 `<br>` 版
- 新建 `web/src/utils/escapeHtml.test.ts`：11 个测试，覆盖 script 中和、属性逃逸、二次转义、`<br>` 三种写法与大小写、`<brx>` 近似标签、真实 note 内容

**为何 `note` 需要例外**：审计全部 46 个内置 premise card，`<br>` 共 86 处且**全部集中在 `note`**，其余五字段零标签。全量转义会让 44 个文件的换行变成可见的 `&lt;br&gt;`。

**未纳入批 0**：`accent` 走 CSS 通道（`border-left: 2px solid ${accent}`），转义在 CSS 上下文无效，须靠色值白名单——已排进批 1 的 `ChromeDraft` 校验。sandbox 收紧见第 5.5 节。

