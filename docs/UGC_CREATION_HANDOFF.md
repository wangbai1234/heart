# UGC 角色创建重构 · 开发交付单

> 创建：2026-08-11 · 交付对象：接手开发的 agent
> 设计依据：`docs/UGC_PRESENTATION_GAPS.md`（缺口分析与方案论证）
> 后端行为层缺口另见：`docs/UGC_COMPATIBILITY_GAPS.md`（2026-07-09）
>
> **本文所有代码位置均已实际读取验证**，非凭 commit message 或印象推断。
> 但代码会变——开工前请按 CLAUDE.md「Agent 行为铁律」用 `git ls-tree` / 实际 Read 复核行号。

---

## 0. 交付边界

**目标**：把用户自建角色的创建功能拆成两档，让「角色创作」档产出的角色能达到内置角色的详情页精美度与聊天开场钩子水准。

**已完成（勿重做）**：批 0 — premise card 六字段 HTML 转义。commit `d6c92de`。

**本单范围**：批 1 – 批 7。

**不在范围**：
- 不把 45 个内置角色的配色搬进数据库（收益小、要动全部 bespoke 组件、有回归风险）
- 不给 UGC 脚本能力（已核实内置角色零 `<script>`，禁脚本无能力落差）
- 不做「角色创作 → 快速创建」反向降级

---

## 1. 必读的既有事实（避免重复发明）

这些能力**已经存在**，按缺口重做会浪费工期：

| 需求 | 既有实现 | 验证位置 |
|------|----------|----------|
| 链接分享 | `visibility` 已是 `public｜unlisted｜private` | `backend/heart/ss01_soul/draft.py:108` |
| 嵌套式乙游开场选项 | `CharacterUIConfig.starterBranches`（先选切入角度→展开台词） | `web/src/data/characterUIConfig.ts` |
| 开场选项不限三条 | 分支路径下每 branch 台词数不限 | 同上 |
| iframe 隔离 | bespoke 详情页与 premise card 本身就走 iframe | `PremiseCardBase.tsx:162-167` |
| 开场白人审定稿 | `opening` 字段 ≤2000 字，明确 "played back verbatim (no LLM)" | `draft.py:90-94` |
| AI 预填的既有模式 | `POST /opening-preview`：主模型生成→创作者审→不落库→后续 verbatim 零运行时 LLM | `routes_characters.py:802-814` |

### 1.1 唯一的「三条」硬锁

`characterUIConfig.ts` 平铺路径类型是元组，锁死三条：

```ts
starterPrompts?: [string, string, string]
```

需求"选项不一定三条、要多样"——分支路径已支持；平铺路径需改 `string[]` + 运行时条数校验（建议 1–5），改完**回归 1 条与 5 条的排版**（现排版按三条设计）。属批 7。

---

## 2. 根因（为什么 UGC 做不到精美）

内置角色精美靠三个按 character id 硬编码的 registry，UGC 的 id 都不在里面：

| 机制 | 位置 |
|------|------|
| bespoke 详情页组件（45 个） | `web/src/components/characterProfiles/index.ts`（74 行 export） |
| `CHROME_PALETTES`（14 槽位配色） | `web/src/pages/CharacterProfilePage.tsx:87` |
| `PREMISE_CARDS`（开场档案卡，45 个） | `web/src/components/ConversationChatPage.tsx:78` |

判定分支 `CharacterProfilePage.tsx:948-952`：

```ts
const BespokeProfile = profile ? BESPOKE_PROFILES[id] : null
const chrome = CHROME_PALETTES[id]
if (profile && BespokeProfile && chrome) { /* bespoke */ }
```

两个条件都要命中才走 bespoke，UGC **必然落 generic**。

更关键：后端 `GET /{character_id}/profile` 返回的 DTO 只有 9 个固定键 + `**presentation`，**无任何 UI 定制字段**（`routes_characters.py:328-339`），前端无源可读。

### 2.1 「人设被抹平」有代码级证据

`_derive_profile_presentation` 的 docstring（`routes_characters.py:215-221`）写明：UGC 的 `identity_anchor.archetype` 是 `spec_builder` 从 `greeting_style` 盖出的英文模板（"Passionate Soul" / "Gentle Companion"），"Surfacing it made most UGC profiles read as identical template text"，因此专门用 `is_builtin` 门控屏蔽掉。

这证明"默认值导致 UGC 千人一面"不是推测，是已经发生过并被打过补丁的问题。所以批 4 的 AI 预填是必要的，不是锦上添花。

`sliders` / `greeting_style` 确实被消费（`spec_builder.py:263-264`），预填的值真能影响行为，不会被下游忽略。`catchphrases` 进 voice_dna（`:294`），空列表时按 `greeting_style` 兜至少 3 条（`:305`）——不 crash 但口吻平淡。

---

## 3. 产品约束（有一条与常见直觉相反）

### 3.1 `unlisted` 需要过审才生效

**这条容易搞错，务必按实际逻辑实现。**

`unlisted` 进审核队列，不是"跳过审核的私享链接"：

- 创建时：`visibility in ("public","unlisted")` → `review_status = "pending"`（`routes_characters.py:722-726`）
- 可见性判定：`visibility IN ('public','unlisted') AND review_status = 'approved'` 才对他人可见（`:293`）
- 切 `private` 才 `not_required`、立即生效（`:989`）

**产品后果**：用户在「快速创建」选"链接分享"后，链接要等过审才能给别人打开。UI 必须明说这点，否则用户会以为功能坏了。

建议 UI 文案（**不带 emoji**，见 CLAUDE.md UI 文案规范）：
- 私密：仅自己可见，立即生效
- 链接分享：审核通过后，拿到链接的人可访问

### 3.2 「快速创建」不给公开

前后端都要校验（后端 validator 见 §4.2），防绕过前端直接打 API。

---

## 4. 批 1：后端 schema（无 DB 迁移）

**文件**：`backend/heart/ss01_soul/draft.py`

`CharacterDraft` 是 **Pydantic `BaseModel` + `extra="forbid"`**（`:48`）——新字段必须显式声明，否则 API 直接拒。

### 4.1 新增字段

全部存进 `soul_specs.draft` 的 JSONB，**不需要 alembic 迁移**。

```python
class ChromeDraft(BaseModel, extra="forbid"):
    """14 槽位配色。字段名与前端 ChromePalette 严格一致
    (web/src/pages/CharacterProfilePage.tsx:70-85)，勿改名。"""
    bg: ColorStr
    coverBg: ColorStr
    scrimGradient: ColorStr
    nameColor: ColorStr
    ageColor: ColorStr
    taglineColor: ColorStr
    chipActiveBg: ColorStr
    chipActiveBorder: ColorStr
    chipActiveText: ColorStr
    chipInactiveBg: ColorStr
    chipInactiveBorder: ColorStr
    chipInactiveText: ColorStr
    ctaGradient: ColorStr
    ctaShadow: ColorStr


class PremiseRowDraft(BaseModel, extra="forbid"):
    label: Annotated[str, Field(max_length=24)]
    value: Annotated[str, Field(max_length=120)]


class PremiseCardDraft(BaseModel, extra="forbid"):
    """字段对齐既有 PremiseCardData
    (web/src/components/characterProfiles/PremiseCardBase.tsx:9-22)。
    注意 warning 是字符串消息，不是布尔开关。"""
    accent: ColorStr
    leadIn: Annotated[str, Field(max_length=400)]
    title: Annotated[str, Field(max_length=60)]
    rows: list[PremiseRowDraft] = Field(default_factory=list, max_length=6)
    note: Optional[Annotated[str, Field(max_length=300)]] = None
    warning: Optional[Annotated[str, Field(max_length=120)]] = None
```

区块联合类型，用 `type` 辨别（上限 12 个）：

```python
class ProfileBlockBase(BaseModel, extra="forbid"):
    type: str

class DossierBlock(ProfileBlockBase):      # 档案表（病历卡/身份档案）
    type: Literal["dossier"]
    title: Annotated[str, Field(max_length=40)]
    rows: list[PremiseRowDraft] = Field(min_length=1, max_length=10)

class QuoteBlock(ProfileBlockBase):        # 大字引文（serif 独白）
    type: Literal["quote"]
    text: Annotated[str, Field(max_length=200)]
    attribution: Optional[Annotated[str, Field(max_length=40)]] = None

class TimelineBlock(ProfileBlockBase):     # 纵向时间线
    type: Literal["timeline"]
    title: Annotated[str, Field(max_length=40)]
    events: list[PremiseRowDraft] = Field(min_length=1, max_length=8)

class ObjectsBlock(ProfileBlockBase):      # 物件隐喻
    type: Literal["objects"]
    title: Annotated[str, Field(max_length=40)]
    items: list[PremiseRowDraft] = Field(min_length=1, max_length=6)

class ContrastBlock(ProfileBlockBase):     # 对照（表里反差）
    type: Literal["contrast"]
    leftLabel: Annotated[str, Field(max_length=20)]
    rightLabel: Annotated[str, Field(max_length=20)]
    pairs: list[PremiseRowDraft] = Field(min_length=1, max_length=6)

class ProseBlock(ProfileBlockBase):        # 纯文本段落
    type: Literal["prose"]
    title: Optional[Annotated[str, Field(max_length=40)]] = None
    text: Annotated[str, Field(max_length=600)]

ProfileBlock = Annotated[
    Union[DossierBlock, QuoteBlock, TimelineBlock, ObjectsBlock, ContrastBlock, ProseBlock],
    Field(discriminator="type"),
]
```

加到 `CharacterDraft`：

```python
creation_mode: Literal["quick", "workshop"] = "quick"
ui_chrome: Optional[ChromeDraft] = None
profile_blocks: list[ProfileBlock] = Field(default_factory=list, max_length=12)
custom_html: Optional[Annotated[str, Field(max_length=51200)]] = None   # 50KB
premise_card: Optional[PremiseCardDraft] = None
starter_config: Optional[StarterConfig] = None
opening_format: Literal["plain", "rich"] = "plain"
```

```python
class StarterFlat(BaseModel, extra="forbid"):
    type: Literal["flat"]
    prompts: list[Annotated[str, Field(max_length=60)]] = Field(min_length=1, max_length=5)

class StarterBranch(BaseModel, extra="forbid"):
    label: Annotated[str, Field(max_length=12)]      # 切入角度
    lines: list[Annotated[str, Field(max_length=60)]] = Field(min_length=1, max_length=3)

class StarterBranched(BaseModel, extra="forbid"):
    type: Literal["branched"]
    branches: list[StarterBranch] = Field(min_length=2, max_length=4)

StarterConfig = Annotated[Union[StarterFlat, StarterBranched], Field(discriminator="type")]
```

### 4.2 两个必须加的 validator

**（a）色值白名单** —— 配色进的是 CSS 通道，HTML 转义在 CSS 上下文无效，只能靠取值白名单。这条同时关掉 `PremiseCardBase` 里 `accent` 插进 `border-left: 2px solid ${accent}` 的注入面（批 0 未覆盖）。

```python
_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}"
    r"|rgba?\([\d\s.,%]+\)"
    r"|linear-gradient\([^;{}()]*(\([^;{}()]*\))?[^;{}()]*\)"
    r"|[\d.]+px\s+[\d.]+px\s+[\d.]+px\s+rgba?\([\d\s.,%]+\))$"
)
ColorStr = Annotated[str, Field(max_length=200), AfterValidator(_check_color)]
```

`_check_color` 不匹配就 `raise ValueError`。注意 `ctaShadow` 是 box-shadow 语法（`0 4px 12px rgba(...)`），不是纯色值——正则最后一支处理它。**禁止出现 `;` `{` `}` `url(` `expression(`**。

**（b）快速创建不得越权**：

```python
@model_validator(mode="after")
def quick_mode_limits(self) -> "CharacterDraft":
    if self.creation_mode == "quick":
        if self.visibility == "public":
            raise ValueError("quick mode cannot be public")
        if self.custom_html or self.profile_blocks or self.premise_card or self.starter_config:
            raise ValueError("quick mode cannot set workshop-only fields")
    return self
```

### 4.3 路由改动

| 端点 | 位置 | 改动 |
|------|------|------|
| `GET /{id}/profile` | `:263` | DTO 补 `ui_chrome` / `profile_blocks` / `custom_html` / `premise_card` / `starter_config` / `opening_format`，从 `draft_json` 取。**前端无源可读的根因就在这** |
| `POST ""` | `:695` | 接受新字段（Pydantic 自动） |
| `PATCH /{id}` | `:879` | 同上 |
| `PATCH /{id}/visibility` | `:946` | 加 quick→public 拦截 |

DTO 返回块在 `:328-339`，`**presentation` 之外的键都是显式列出的，照格式加。

### 4.4 批 1 验收

- [ ] `POST /api/characters` 带 `creation_mode="quick"` + `visibility="public"` → 422
- [ ] 带 `creation_mode="quick"` + `custom_html` → 422
- [ ] `ui_chrome.bg = "red; }body{display:none"` → 422（白名单拦下）
- [ ] `ui_chrome.ctaShadow = "0 4px 12px rgba(255,107,107,0.3)"` → 通过
- [ ] `GET /{id}/profile` 返回新字段
- [ ] 既有 UGC 角色（无新字段）仍正常返回，新字段为 null/空

---

## 5. 批 2：配色（最高优先，单独合完即解决用户痛点）

用户最初的诉求就是"详情页按钮颜色/收藏按钮 UI 已重构，创建功能要能选风格颜色"。**批 2 合完这件事就解决了**，不必等整套。

### 5.1 提炼 8 套预置盘

从 `CHROME_PALETTES`（`CharacterProfilePage.tsx:87` 起）的 45 套实际配色里提炼 8 套，覆盖不同调性。参考方向（**读实际值后再定，勿照抄本表**）：

| 预置 id | 中文名 | 调性来源 |
|---------|--------|---------|
| `medical_cool` | 冷调医疗 | 季屿系 |
| `royal_warm` | 暖调权谋 | 裴决系 |
| `gothic_mist` | 哥特雾灰 | 临渊庄园系 |
| `night_velvet` | 夜色丝绒 | 深蓝+金 |
| `crimson_noir` | 暗红黑金 | 黑红+银 |
| `forest_sage` | 林间灰绿 | 深绿+琥珀 |
| `ocean_depth` | 深海青 | 深青+海沫 |
| `bright_warm` | 明亮暖调 | 浅底+珊瑚橙 |

**新建**：`web/src/data/characterThemePresets.ts`

```ts
import type { ChromePalette } from '../pages/CharacterProfilePage'   // 需 export 该 type

export interface ThemePreset {
  id: string
  name: string          // 中文名，UI 直接显示
  palette: ChromePalette
}
export const THEME_PRESETS: ThemePreset[] = [ /* 8 套 */ ]
export const DEFAULT_THEME_PRESET_ID = 'night_velvet'
```

`ChromePalette` 目前是 `CharacterProfilePage.tsx:70` 的局部 type，需 `export` 出来（或抽到 `web/src/types/`）。**不要新建平行的颜色类型**——之前的设计已定复用它，避免第四套配色结构。

### 5.2 渲染改成三级链

`CharacterProfilePage.tsx:948-952` 现有逻辑改为：

```ts
const BespokeProfile = profile ? BESPOKE_PROFILES[id] : null
// 配色优先级：内置硬编码 → UGC 自选 → 默认盘
const chrome = CHROME_PALETTES[id] ?? profile?.ui_chrome ?? DEFAULT_PALETTE

if (profile && BespokeProfile && CHROME_PALETTES[id]) {
  // 内置 bespoke 分支：判定仍要求硬编码配色命中，行为不变
}
// generic 分支现在也吃 chrome
```

**关键**：内置优先级在前，`CHROME_PALETTES` 命中时行为完全不变 → **45 个 bespoke 组件一行不动，零回归**。

generic 分支原本用固定样式，改为读 `chrome` 的对应槽位（`bg` / `nameColor` / `ctaGradient` / `ctaShadow` / chip 六项等），与 bespoke 分支的用法保持一致（参考 `:954-1059` 的既有写法）。

### 5.3 配色选择器

**新建**：`web/src/components/ThemePresetPicker.tsx`

- 8 个色板缩略图（用 `ctaGradient` + `bg` 做预览色块），单选
- 选中后即时预览：至少展示"名字 + tagline + 和Ta聊天按钮"的缩略效果
- 只暴露"选一套预置"，**不给 14 个槽位逐个填**（用户填不出协调配色，且徒增注入面）
- 后续想给微调，只放开 accent 类槽位，不放开全部

### 5.4 批 2 验收

- [ ] 内置角色详情页视觉**零变化**（逐个抽查 5 个：季屿/裴决/临渊庄园/白清欢/程之）
- [ ] UGC 角色选中预置后，详情页 CTA 按钮渐变+阴影、名字色、chip 配色全部生效
- [ ] 既有 UGC（`ui_chrome` 为 null）落到 `DEFAULT_PALETTE`，不崩不白屏
- [ ] `npx vitest run` 通过；`bash scripts/ci.sh` 全绿

---

## 6. 批 3：两档入口 + 快速创建表单

### 6.1 入口

**不新建 mode picker 页面**。`web/src/pages/CreateHubPage.tsx`（185 行）已是「创作中心」，现在 `:87` / `:91` 都直接 `navigate('/characters/new')`。改成出两张卡：

```
快速创建 —— 填四项，剩下交给 AI，几十秒出一个能聊的角色
角色创作 —— 一步步填，详情页会跟着变好看，可申请公开
```

路由：`/characters/new/quick`、`/characters/new/workshop`。保留 `/characters/new` 重定向到 hub（旧链接不炸）。`:112` 的编辑入口按 `creation_mode` 路由到对应向导。

### 6.2 快速创建只问四项

| 字段 | 约束 | draft 字段 |
|------|------|-----------|
| 封面 | 3:4 竖图，走既有 `POST /characters/cover`（`:654`） | `cover_url` |
| 名字 | 1–20 字 | `display_name.zh` |
| 性别 | 男/女 | `gender` |
| 人设描述 | **20–1500 字**（`persona` 有 `min_length=20`，UI 要拦并提示） | `persona` |

可见性选择放在确认页（默认 `private`），文案按 §3.1。

### 6.3 批 3 验收

- [ ] 人设描述填 19 字时前端拦下并提示，不发请求
- [ ] 创作中心两个入口分别进对应向导
- [ ] 快速创建向导里**找不到**公开选项
- [ ] 旧 `/characters/new` 链接不 404

---

## 7. 批 4：AI 预填 + 确认页

### 7.1 一次调用产出

扩展 `POST /opening-preview`（`:802`）或新开 `POST /characters/quick-prefill`。该端点的既有语义正是要的模式：主模型、创作者审、不落库、后续 verbatim 零运行时 LLM（docstring `:807-813`）。

产出：`age_range`、`greeting_style`、六个 `sliders`、`catchphrases`（3 条）、`opening`、推荐 `ui_chrome` 预置 id。

**不推 `visibility`** —— 私密还是分享是用户真实意图。

### 7.2 确认页分两层

**上层直接可见**（不折叠）：
- **开场白全文** —— 必须过人眼，这是"人审定稿"的全部意义（见 memory `project_opening_scene_redesign`）
- 主题配色色板（可换）
- 可见性开关（文案按 §3.1）

**下层折叠进「更多设定」**：年龄段、相处风格、六个滑块、口癖。折叠标题给一行摘要，如：

```
25-30 · 冷淡 · 话少而直接 · 3 条口癖
```

主按钮「确认创建」。开场白可重新生成，**限 3 次**，超次数只能手工改文字（控成本）。

### 7.3 失败处理（硬要求）

LLM 失败时**绝不能**偷偷套 `warm` + 全 0.5 然后假装成功。那是 CLAUDE.md 明令禁止的欺骗式静默，且 §2.1 已证明会产出千人一面的角色。

- 整体失败：确认页显示明确错误 + 重试按钮，**不落库**
- 部分字段失败：标明缺哪几项，用户重试或手填
- 长期不可用：给"转手动创作模式"出口
- 后端按规范：`logger.exception("quick_prefill_failed", extra={...})` 后 re-raise 或转结构化错误到前端。**禁止 `except Exception: pass`**

### 7.4 音色不进创建流程

`voice_id` 在 `character_voices` 表不在 draft 里，且文字聊天不需要音色。

**注意**：`preset_voices` 表**没有 gender 列**（`migrations/versions/025_voice_tables.py:14-22`）。按性别给默认音色需要二选一：
1. 加 `gender` 列（走迁移，须遵守 CLAUDE.md「DB 迁移铁律」：revision 名 ≤32 字符、`down_revision` 指向单一 head、`IF NOT EXISTS` 幂等）
2. 代码内维护 `{male: [...], female: [...]}` 映射（不动 schema，但要跟 seed 数据对齐）

**推荐方案 2**，理由：音色目录本来就在迁移里 seed，加列还要回填；映射表改起来更轻。落库时按性别取第一个 active 预置写入 `character_voices`，用户后续在角色设置里改。

### 7.5 批 4 验收

- [ ] 拔掉 LLM key，确认页显示错误 + 重试，**数据库无新角色**
- [ ] 预填的 `sliders` 落库后确实进 SoulSpec（对比 `spec_builder.py:263-264` 的消费）
- [ ] 重新生成开场白第 4 次被拒
- [ ] 创建出的角色 `character_voices` 有按性别的默认预置行
- [ ] 确认页不含任何 emoji（CLAUDE.md UI 文案规范）

---

## 8. 批 5：区块渲染器

### 8.1 开工前必做的前置验证

**先手工塞一份 `profile_blocks` 假数据，把区块渲染出来看够不够精美。**

整个批 6（七步引导）的价值都建立在"填完真的好看"这个前提上。前提没验证就投七步引导的开发，是本方案最大的浪费风险。渲染出来不够看就先调版式，别急着做引导。

参考 `docs/` 里的既有设计模式沉淀（memory: `design_character_profile_patterns`）：一角色一语言、克制呼吸感、装饰有意义、serif+sans 配对、留白即设计。区块版式要吃到这些，不能做成朴素表格。

### 8.2 实现

**新建**：`web/src/components/profileBlocks/`
- `BlockRenderer.tsx` —— 按 `type` 分发
- `DossierBlock.tsx` / `QuoteBlock.tsx` / `TimelineBlock.tsx` / `ObjectsBlock.tsx` / `ContrastBlock.tsx` / `ProseBlock.tsx`

**硬要求**：
- 所有用户文本必须过 `escapeHtml`（`web/src/utils/escapeHtml.ts`，批 0 已建）。若某区块要支持换行，用 `escapeHtmlAllowBr`
- 配色从 `ui_chrome` 取，不硬编码颜色
- 区块间距由渲染层统一处理（不同 type 交界处加大间隔），用户不管这个

### 8.3 批 5 验收

- [ ] 六种区块各渲染一遍，视觉达到"不像朴素表格"的标准（人工判断）
- [ ] 塞 `<script>alert(1)</script>` 进任意区块字段，页面不执行脚本
- [ ] `ui_chrome` 换一套预置，区块配色跟着变

---

## 9. 批 6：七步引导 + 高级 HTML

### 9.1 核心设计：反转"先选版式后填内容"

nimoo 的做法本质上仍是让用户写 HTML 或选模板，用户得自己判断内容和版式怎么配。**yuoyuo 反过来：用户填什么内容，系统就生成对应区块。**

| 用户填了什么 | 自动生成 |
|-------------|---------|
| 3 条以上身份/职业/状态 | `dossier` |
| 第一人称独白 | `quote` |
| 时间线式经历 | `timeline` |
| 随身物件清单 | `objects` |
| 表里反差设定 | `contrast` |

用户的视角是"在回答问题"，不是"在配界面"。

### 9.2 七步

1. 核心身份（名字/性别/封面/一句话钩子）
2. 人设描述 + `tagline` + `intro` + `tags`
3. 档案信息 → `dossier` 当场出现
4. 独白 / 语气样本 → `quote` 出现
5. 背景故事，三选：时间线 / 物件 / 对照 → 对应区块出现
6. 开场设计：`opening` + `premise_card` + `starter_config`
7. 主题配色 + 可见性 + 音色

**进度用质感分级不用百分比**：素描 → 半成品 → 有模样 → 成品。每级对应新增区块，用户看到的是"再填一步能得到什么"，不是"还剩多少要做"。

草稿续填走既有 `GET /{id}/draft`（`:855`）+ `PATCH /{id}`（`:879`）。**开工前验证这两个端点是否支持未完成态草稿**（必填字段缺失时能否存），不支持则需放宽或加 `is_draft` 标志。

### 9.3 AI 在这里是按需辅助

与快速创建不同：每个输入框旁一个「帮我写」，用户点了才调用，产出填进该字段供修改。唯一例外——第 5 步可以「根据已填内容推荐时间线」（这步最容易卡住）。

理由：角色创作的用户是要精细控制的，全量预填会干扰他们。

### 9.4 高级 HTML（分层第二层）

区块编辑器覆盖不写代码的用户；额外给「高级模式」开放原始 HTML（≤50KB）。

**沙箱可以不给脚本**：已核实全部 45 个 bespoke 组件 `<script>` 出现次数为 **0**，动效全是 CSS。禁脚本对 UGC 无能力落差。

净化：加 `dompurify` 依赖（**这时才加**，批 0 只需 5 行 `escapeHtml`，提前加是未使用依赖）。移除 `<script>`、`on*` 事件属性、外链资源。iframe 用 `sandbox` 且**不给** `allow-scripts`。

暴露 CSS 变量（`--theme-accent` 等，从 `ui_chrome` 注入）让用户 HTML 吃到配色。提供 3–5 个模板（从既有 bespoke 组件脱敏提炼）。

**区块与高级 HTML 互斥**：有 `custom_html` 优先，否则渲染 `profile_blocks`，都没有则 generic。

### 9.5 关于既有 iframe 的 sandbox（勿顺手改）

`PremiseCardBase.tsx:166` 的 sandbox 是 `allow-same-origin allow-scripts` —— 已知危险组合，但有真实依赖：

- `allow-scripts` 支撑展开/收起（`onclick="parent.postMessage('toggle','*')"`，`:147`）
- `allow-same-origin` 支撑高度测量（`:42-43` 读 `iframe.contentDocument.body.scrollHeight`），去掉则 45 张卡片全塌成默认 200px

收紧方案：把高度测量改成 iframe 内部 postMessage 上报（现成 message 通道已在用，`:53-66`），改完可去 `allow-same-origin`。**单独批次做**，它动全部 45 张卡片的版式测量，有回归风险，别混进业务 PR。

批 0 转义 + 批 1 色值白名单落地后注入面已关闭，sandbox 收紧属纵深防御。

### 9.6 批 6 验收

- [ ] 七步中途退出，重进能续填
- [ ] 填够内容后详情页确实"变好看"（对比第 1 步只填名字时的状态）
- [ ] 高级 HTML 塞 `<script>` / `onerror=` → 净化后不执行
- [ ] 高级 HTML 超 50KB → 明确报错说明超了多少
- [ ] 有 `custom_html` 时 `profile_blocks` 不渲染

---

## 10. 批 7：聊天页开场钩子

### 10.1 开场档案卡

`ConversationChatPage.tsx:1140` 现在只查内置 registry：

```ts
const PremiseCard = PREMISE_CARDS[currentCharacterId]
```

改成：内置命中则用内置组件；否则若 `character.premise_card` 存在，用它喂 `PremiseCardBase`（该基座已支持任意数据，批 0 已加转义）。

渲染时机条件不变（`historyLoaded && messages.every(m => m.role !== 'user')`）。

### 10.2 首聊引导

现有逻辑：`:689` 读 `starterBranches`，`:748` 回退 `starterPrompts`，再回退 `FALLBACK_STARTER_PROMPTS`。

改成四级链：内置 `CHARACTER_UI_CONFIGS[id]` → `character.starter_config` → 通用兜底。

**元组改数组**：`characterUIConfig.ts` 的 `starterPrompts?: [string, string, string]` 改 `string[]`。改完**必须回归 1 条和 5 条的排版**（现排版按三条设计，可能出现拉伸或错位）。这是"选项不一定三条"需求的落点。

### 10.3 富格式开场白

`opening_format = "rich"` 时解析 `<scene>` / `<plot>` / `<dialogue>` 分层排版：

- `scene` —— 斜体、弱化色（场景描写）
- `plot` —— 常规正文（剧情推进）
- `dialogue` —— 加重、可带角色名前缀（台词）

**解析后每段内容仍要 `escapeHtml`**，只有标签本身被消费。`plain` 时原样渲染（既有行为，不变）。

### 10.4 批 7 验收

- [ ] UGC 角色配了 `premise_card` → 首次进聊天页显示，发过消息后不再显示
- [ ] `starter_config` 平铺 1 条 / 3 条 / 5 条，排版都不崩
- [ ] `starter_config` 分支式（2–4 个角度）交互正常
- [ ] 内置角色的开场卡与引导**行为零变化**
- [ ] rich 格式里塞 `<script>` → 不执行

---

## 11. 执行顺序与依赖

| 批 | 内容 | 依赖 | 单独合完的价值 |
|---|------|------|--------------|
| ~~0~~ | ~~premise card 转义~~ | — | **已完成** `d6c92de` |
| 1 | 后端 schema + validator + DTO | — | 无（纯地基） |
| 2 | 配色预置 + 选择器 + generic 吃配色 | 1 | **解决用户最初痛点** |
| 3 | 两档入口 + 快速创建表单 | 1, 2 | 快速创建可用（无 AI 预填） |
| 4 | AI 预填 + 确认页 | 3 | 快速创建质量达标 |
| 5 | 区块渲染器 | 1 | 需先过 §8.1 前置验证 |
| 6 | 七步引导 + 高级 HTML | 5 | 角色创作可用 |
| 7 | 开场钩子 + 元组改数组 | 1 | 聊天页钩子可配 |

批 5 可与批 3/4 并行（依赖不同）。批 2 建议最先做完并单独合。

---

## 12. 开工前必须复核的 5 项

我在设计期没能验证这些，**开工先查，结论可能影响实现**：

1. `GET /{id}/draft`（`:855`）+ `PATCH /{id}`（`:879`）是否支持**未完成态**草稿（必填缺失时能否存）——批 6 七步引导中途退出要能续填
2. `POST /opening-preview`（`:802`）的请求/响应 schema，能否扩展成"一次推全套"，还是新开端点更干净
3. `build_soul_spec_from_draft()` 对空 `catchphrases` 的完整分支（`spec_builder.py:294` `:305` 附近）——确认预填 3 条 vs 空列表的实际差异
4. `preset_voices` 的 seed 数据里有哪些音色、能否按名称/描述判断性别（决定 §7.4 用方案 1 还是 2）
5. generic 详情页分支（`CharacterProfilePage.tsx:1073` 之后）的现有结构，确认接 `chrome` 的改动面有多大

---

## 13. 待定的产品决策（批 5 前定即可，不卡批 1–4）

1. 预置盘做 8 套还是 12 套
2. 第 5 步的时间线/物件/对照：三选一、至少选一、还是可多选
3. 完成度分级是否与公开权限挂钩（如只有"成品"级才能申请公开）

---

## 14. 项目规范红线（CLAUDE.md 摘要，务必遵守）

- **小而低风险改动可直接走 main**，但必须 `bash scripts/ci.sh` 全绿。涉及迁移/密钥/基础设施/CI 配置的**永远走 PR**
- 单人 open PR ≤ 3；PR open 超 7 天必须合或关
- **禁止 `except Exception: pass`** —— 必须 `logger.exception(...)` 后 re-raise 或转结构化错误
- **UI 文案禁用 emoji**（本方案所有面向用户文案都不带）
- 涉及 DB 的改动 push 前先 `alembic current` 对比 `alembic heads`
- 跨分支代码状态判断必须基于 `git ls-tree` / `git show` 实际输出，禁止凭 commit message 推断
- 改动前先用 `git ls-tree -r <branch> -- <path>` 看现有实现，禁止"凭印象觉得这是空的"

---

## 15. 本文档的验证状态

| 类别 | 状态 |
|------|------|
| 所有引用的文件路径与行号 | 已实际 Read / grep 验证（2026-08-11） |
| 45 个 bespoke / 45 个 premise card / 74 行 export | 已 `ls \| wc -l` 计数 |
| `<script>` 零出现 | 已全目录 grep |
| `<br>` 86 处全在 `note` | 已逐字段 grep 审计 |
| `unlisted` 需过审 | 已读 `:293` `:722-726` `:955-989` 确认 |
| `sliders`/`greeting_style` 被消费 | 已读 `spec_builder.py:263-264` |
| "UGC 千人一面"有先例 | 已读 `_derive_profile_presentation` docstring `:215-221` |
| §12 的 5 项 | **未验证**，开工先查 |

行号会随代码变动漂移。接手时先复核，发现不符以实际代码为准并回头更新本文档。

