# 羁绊中心前端执行规格（交 Sonnet 执行）

> 本文档是**可直接照做的施工图**。后端 Wave 0（merge migration）+ Wave 1（`GET /api/companions`）已由 Opus 完成并合入分支 `feat/companion-center-wave0`。你（Sonnet）负责前端 Wave 1 + Wave 2。
>
> **铁律**：
> - 语音聊天（voice mode / TTS）与主动消息（proactive）逻辑**一行都不许动**。只做展示层叠加。
> - `/my-characters` 的权限配置（可见范围 + 停用）与 `/character-backstage` 的单角色设置**保持不动**。
> - 完成后跑 `cd /Users/wanglixun/heart && bash scripts/ci.sh`（若无前端 lint 步骤，至少 `cd web && pnpm build` 保证 TS 编译过）。
> - 全部在 `feat/companion-center-wave0` 分支上继续提交（不要新开分支，不要切 main）。

---

## 后端契约（已上线，直接消费）

`GET /api/companions` → 返回：

```jsonc
{
  "companions": [
    {
      "character_id": "rin",
      "display_name": "神无月凛",
      "avatar_url": null,               // UGC 有值；内置角色为 null，用 resolveCharacterProfile 兜底
      "source": "built_in",             // "built_in" | "user_created"（V1 仅这两种）
      "is_owner": false,
      "is_builtin": true,
      "has_voice": true,
      "companion_status": "companioned", // V1 恒为 companioned
      "relationship_stage": "ROMANTIC_INTEREST", // RAW 大写枚举，前端负责映射
      "intimacy": 0.68,                 // RAW 0..1，前端 ×100 取整
      "last_message_text": "主人，今晚也会来见我吧？",
      "last_message_at": "2026-07-24T13:47:00+00:00", // ISO 或 null
      "last_message_modality": "text",  // "text" | "voice" | null
      "unread_count": 2,
      "has_proactive": true
    }
  ]
}
```

列表已由后端按「有未读/主动 → 最近互动 → 亲密度」排序，`companions[0]` 即「今日陪伴」大卡，其余进长廊。**前端不要再排序。**

关系阶段 RAW 枚举全集：`STRANGER` / `ACQUAINTANCE` / `FRIEND` / `CONFIDANT` / `ROMANTIC_INTEREST` / `LOVER` / `BONDED` / `cold_war`（注意 cold_war 是小写）。

---

## 任务 1：`companionsStore` + 类型 + 映射工具

### 1a. 在 `web/src/services/api.ts` 新增 DTO + fetch 函数

紧挨 `getInboxSummary`（api.ts:359）之后加：

```ts
export interface CompanionDTO {
  character_id: string
  display_name: string
  avatar_url?: string | null
  source: 'built_in' | 'user_created'
  is_owner: boolean
  is_builtin: boolean
  has_voice: boolean
  companion_status: 'locked' | 'encountered' | 'companioned'
  relationship_stage: string   // RAW enum, 见规格
  intimacy: number             // 0..1
  last_message_text: string
  last_message_at: string | null
  last_message_modality: 'text' | 'voice' | null
  unread_count: number
  has_proactive: boolean
}

export async function getCompanions(): Promise<{ companions: CompanionDTO[] }> {
  return request('/companions')
}
```

### 1b. 新建 `web/src/utils/relationship.ts`

阶段映射（含 cold_war → 「闹别扭」独立态，这是产品拍板的）：

```ts
/** RAW 后端关系阶段 → 前端中文标签（恋爱意味但克制）。 */
const STAGE_LABELS: Record<string, string> = {
  STRANGER: '初遇',
  ACQUAINTANCE: '靠近',
  FRIEND: '靠近',            // 设计里 ACQUAINTANCE/FRIEND 同归「靠近」
  CONFIDANT: '心动',
  ROMANTIC_INTEREST: '牵绊',
  LOVER: '相伴',
  BONDED: '共鸣',
  cold_war: '闹别扭',        // 独立态，不混入 6 段进度
  COLD_WAR: '闹别扭',        // 容错：万一后端给大写
}

export function stageLabel(rawStage: string): string {
  return STAGE_LABELS[rawStage] ?? '初遇'
}

/** cold_war 是独立态，不参与「x 段进度」的进度条渲染。 */
export function isColdWar(rawStage: string): boolean {
  return rawStage.toLowerCase() === 'cold_war'
}

/** intimacy 0..1 → 显示百分比整数。 */
export function intimacyPercent(intimacy: number): number {
  return Math.round(Math.max(0, Math.min(1, intimacy)) * 100)
}

/** 「心动 · 68%」组合串（cold_war 不带百分比）。 */
export function stageWithIntimacy(rawStage: string, intimacy: number): string {
  if (isColdWar(rawStage)) return stageLabel(rawStage)
  return `${stageLabel(rawStage)} · ${intimacyPercent(intimacy)}%`
}
```

### 1c. 新建 `web/src/stores/companionsStore.ts`

照抄 `charactersStore.ts` 的结构（inflight 去重 + 静默失败 + loaded/loading）。**不复用 charactersStore**（设计明确要求 companion store 独立，保持 charactersStore 的目录职责纯净）。

```ts
import { create } from 'zustand'
import { getCompanions, type CompanionDTO } from '../services/api'

interface CompanionsState {
  companions: CompanionDTO[]
  loaded: boolean
  loading: boolean
  load: (force?: boolean) => Promise<void>
}

let inflight: Promise<void> | null = null

export const useCompanionsStore = create<CompanionsState>((set, get) => ({
  companions: [],
  loaded: false,
  loading: false,
  load: async (force = false) => {
    if (!force && (get().loaded || get().loading)) return
    if (inflight) return inflight
    set({ loading: true })
    inflight = getCompanions()
      .then(({ companions }) => set({ companions, loaded: true, loading: false }))
      .catch(() => set({ loading: false })) // 保留旧值，页面自行兜底
      .finally(() => { inflight = null })
    return inflight
  },
}))
```

---

## 任务 2：重构 `CharacterPage.tsx` 为羁绊中心

文件：`web/src/pages/CharacterPage.tsx`（整体重写渲染层，保留导航栏结构 + 背景图 + TabBar + 「我的角色」「+」两个按钮的跳转）。

### 数据接线
- `useCompanionsStore((s) => s.companions)` + `load()`（`useEffect` 挂载时 `load()`）。
- 视觉资源（头像/渐变色）继续用 `resolveCharacterProfile(c.character_id, c.display_name, c.avatar_url, { isOwner: c.is_owner && !c.is_builtin })`（uiContent.ts:134，签名已确认）。
- **空/加载兜底**：`companions.length === 0` 时回退到 `useCharactersStore` 的 characters（保持冷启不空屏，与现状一致）。
- 点击卡片沿用现有逻辑：`setCharacter(id)` + `setActiveCharacter(id)` + `navigate('/chat/'+id)`（appStore/chatStore 已 import）。

### 布局（自上而下，参考 docs/UIdesign.md 一节）
标题从「选一个陪伴你的人」改为「角色 / 羁绊」。

1. **今日陪伴大卡**（`companions[0]`）：
   - 大头像（沿用 80px 渐变环，可放大到 96px）+ `display_name`。
   - 若 `unread_count > 0`：右上角红点角标显示未读数。
   - `stageWithIntimacy(stage, intimacy)`（如「心动 · 68%」；cold_war 显示「闹别扭」不带条）。
   - 亲密度进度条：`isColdWar` 时**不渲染进度条**，改用一个灰/冷色的「闹别扭」pill；否则渲染 `intimacyPercent` 宽度的进度条。
   - `last_message_text`（截断单行）；`last_message_modality === 'voice'` 时前面加个小语音图标。
   - 若 `has_proactive`：一行轻提示「最近：主动来找过你」。
   - 三个操作按钮：`[继续聊天]`（→ 进 chat）、`[羁绊档案]`（→ 展开页内详情，见任务 3）、`[剧情邀约]`（**Wave 3 占位**：本次先渲染为 disabled 或不渲染，留 TODO 注释指向 Wave 3）。

2. **陪伴长廊**（`companions.slice(1)`，横向滚动）：
   - 小卡：头像 + 名字 + `stageLabel`（短标签即可，如「心动」）+ 未读红点。
   - 点击 → 该角色设为大卡（本地 state 选中）或直接进 chat。**简单起见：点击直接进 chat**（`navigate('/chat/'+id)`），与现状行为一致，最省风险。

3. **羁绊档案预览**（大卡对应角色）：小卡片列出「当前阶段 / 亲密进度 / 最近一句 / 未读 / 来源」。来源标签：`source === 'built_in'` → 「入驻角色」；`'user_created'` → 「原创」。（`imported`/`story_encounter` V1 无数据，不显示。）

### 排序
**不要在前端排序**，后端已排好。直接 `companions.map(...)`。

### 保留项
- 导航栏「我的角色」→ `/my-characters`、「+」→ `/characters/new` 原样保留。
- `<TabBar />` 保留。
- 背景图逻辑保留。

---

## 任务 3：角色详情「页内展开」（第一版不做独立路由）

在 CharacterPage 内用一个本地 state `expandedId: string | null` 控制。点击大卡「羁绊档案」→ 展开一个面板（可用 `<Dialog>` 或页内 section），结构参考 UIdesign.md 二节：

- 大头像 + `stageWithIntimacy`。
- **最近陪伴**：`last_message_text` + `has_proactive` 状态 + 未读数。
- **共同回忆 / 剧情关联**：Wave 3/4 才有数据源，**本次留静态占位文案 + TODO 注释**，不接后端。
- **声音与陪伴设置**：一个按钮跳 `/character-backstage`（现有单角色设置页；注意先 `setActiveCharacter(id)` 再跳，因为 backstage 读的是 activeCharacter）。

> ⚠️ 不要在这里重做音色/清空聊天 UI —— 那些在 `/character-backstage` 已存在，只做跳转。

---

## 任务 4（Wave 2）：Chat 页事件卡（3 类里的 2 类）

文件：`web/src/components/ConversationChatPage.tsx`。**只加展示组件，不碰 useWebSocket / useVoiceRecorder / proactiveStore 的现有逻辑。**

### 4a. 顶部关系状态条
现有 header（约 ConversationChatPage.tsx:578 一带，显示「朗读中」的地方）旁边，加一行副标题：`stageWithIntimacy`。数据来源：进入 chat 时用 `getCompanions()` 找到该角色，或复用 companionsStore（若已 load）。最省事：从 `useCompanionsStore.getState().companions.find(c => c.character_id === currentCharacterId)` 取，取不到就不显示（优雅降级）。

### 4b. 主动消息事件卡（第 1 类 — 复用现有 drain，不改逻辑）
现有代码（ConversationChatPage.tsx:246-265）已把 proactive 消息作为普通 assistant 气泡注入。**Wave 2 增强（可选、低优先）**：把「主动来找过你」的消息用一个带 `[回应她]` 的轻事件卡样式渲染，而不是普通气泡。
- **实现方式（零风险）**：注入 proactive 消息时给 message 对象打一个 `isProactive: true` 标记（chatStore 的 message 类型加可选字段），气泡渲染处 `if (msg.isProactive)` 用事件卡样式。
- 若改 chatStore 类型有风险，**本任务可跳过**，保持现状（proactive 已能正常显示）。事件卡是锦上添花，不是保留项。

### 4c. 关系升阶事件卡（第 2 类 — 前端比对 localStorage，低风险）
当角色关系阶段变化时，在聊天流中插入一张「你们的关系进入『心动』」卡。
- **实现**：进入 chat（或 companions load 后）读取当前 `relationship_stage`。与 `localStorage['lastStage:'+characterId]` 比对：
  - 若 localStorage 无记录 → 只写入，不弹卡（避免首次进入就弹）。
  - 若不同且**新阶段更高**（按 6 段顺序 index 比较，cold_war 不触发升阶卡）→ 渲染一张一次性事件卡，然后更新 localStorage。
  - 阶段顺序数组：`['STRANGER','ACQUAINTANCE','FRIEND','CONFIDANT','ROMANTIC_INTEREST','LOVER','BONDED']`。
- 卡片文案：`你们的关系进入「${stageLabel(newStage)}」`，副文案「她开始更主动地靠近你。」，按钮 `[查看羁绊]` → 回 `/character` 并展开该角色档案（或简单 `navigate('/character')`）。
- 事件卡作为一个特殊 message 插入聊天流，或作为聊天流顶部/底部的浮层 —— 选实现简单的那种。**不要写回后端**，纯前端展示。

### 4d. 剧情邀约卡（第 3 类）
**Wave 3 才做，本次不实现。** 在事件卡组件里留一个 `// TODO(Wave 3): 剧情邀约卡，依赖 character_story_hooks 后端` 注释即可。

### 保留项自检（改完必须确认）
- [ ] 语音录制（按住麦克风 → STT → 发送）仍工作。
- [ ] 语音播放气泡（VoiceMessageBubble）仍工作。
- [ ] TTS 开关（voiceChatEnabled）仍工作。
- [ ] 主动消息仍能进聊天流（proactiveStore drain 未动）。
- [ ] header「···」→ `/character-backstage` 仍在。

---

## 验收 & 提交

1. `cd web && pnpm build`（TS 必须编译过；有 lint 就一起跑）。
2. `cd /Users/wanglixun/heart && bash scripts/ci.sh`（后端不受影响，应保持绿）。
3. 手动点一遍：角色页大卡渲染、长廊滚动、进 chat、语音、主动消息、关系条显示。
4. 提交（继续在 `feat/companion-center-wave0`）：
   ```
   feat: 羁绊中心前端 — CharacterPage 重构 + companionsStore + Chat 事件卡

   Wave 1 前端:
   - companionsStore + CompanionDTO + relationship 映射工具（含 cold_war→闹别扭）
   - CharacterPage 重构为羁绊中心（今日陪伴大卡 + 长廊 + 档案预览 + 页内展开）
   Wave 2:
   - Chat 顶部关系状态条 + 关系升阶事件卡（localStorage 比对，纯前端）
   - 剧情邀约卡留 Wave 3 TODO

   保留: 语音/主动消息/backstage 设置/my-characters 权限配置 全部未动
   ```

---

## 明确不做（本轮范围外，Opus 后续处理）
- `character_story_hooks` 表 + 剧情邀约触发（Wave 3，Opus 做后端）。
- companion 解锁流程 locked/encountered + 相遇摘要写记忆（Wave 4，Opus 做，单独 PR）。
- 独立「羁绊档案页」路由（详情第二版）。
