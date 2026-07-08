# 前端设计规划：主动消息展示 + 语音失败友好提示

> 状态：规划（待 HUMAN 拍板后分批开 PR）
> 来源：`docs/TEST_REPORT_2026-07-08.md` SUG-1 / SUG-2
> 依赖：BUG-4 修复（PR #112）已让 `/api/proactive/pending` 读库、`id` 恒有值、新增 `POST /api/proactive/ack`
> 最后更新：2026-07-08

---

## 背景

第二轮测试暴露两处前端缺口：

- **SUG-1**：TTS / 语音失败**全程静默**，用户无任何感知（MiMo key 过期返回 401 时表现为按钮无反应）。
- **SUG-2**：主动消息后端已生成，但前端**从不轮询、从不展示**，PROA-02~06 因此全部 BLOCKED。

前端栈：`web/`，React 19 + Vite + TS + Zustand 5 + react-router v7；HTTP 封装在 `services/api.ts`；已有**纯展示** `components/ui/Toast.tsx`（无全局 store，各页各自 `useState` 管理）。

---

## B1. 全局 Toast 基础设施（前置，SUG-1 / SUG-2 共用）

**现状**：`ui/Toast.tsx` 只是展示组件；`SettingsPage`/`LoginPage`/`ProfileEditPage`/`CharacterPage`/`RedeemPage` 各自 `useState({visible,message})`。WebSocket / TTS 层发生的错误没有任何页面接管，故完全不可见。

**方案**：
1. 新增 `stores/toastStore.ts`（Zustand）：`show(message, variant?)`、内部队列、自动消散（复用现有 2200ms）。
2. `App.tsx` 根挂单个 `<ToastContainer>` 消费 store，复用 `ui/Toast.tsx` 视觉。
3. 现有各页 local Toast 可逐步迁移（非阻塞，不在本期强制）。

产出文件：`stores/toastStore.ts`（新）、`components/ui/ToastContainer.tsx`（新）、`App.tsx`（挂载）。

---

## B2. SUG-1 — 语音 / TTS 失败友好提示

**现状（全部静默吞掉）**：
- `hooks/useWebSocket.ts` 的 `case 'error'` 只重置 `isStreaming/isPlaying`，无提示。
- `components/VoiceMessageBubble.tsx` 音频拉取 `.catch(() => {})`（含 401）；`<audio>.onerror` / `play().catch()` 静默 `stopPlayback()`。
- 唯一可见反馈是「积分不足」`Dialog`。

**方案**：
- 在 `useWebSocket.ts` 的 `error` 分支与音频加载失败处调用 `toastStore.show(...)`。
- `VoiceMessageBubble.tsx` 音频 401 / 加载失败时给可见的重试入口或提示，而非空按钮。
- 文案集中到 `data/uiContent.ts`（便于统一与后续 i18n），示例：
  - 「yuoyuo 宇宙偷偷偏离了轨道，正在修复…」
  - 「凛正在休息，语音暂时不可用」
  - 「语音服务正在升级，请稍后再试」
- 区分**永久性失败**（供应商 key 失效 → 建议同时收敛为文字回复）与**临时性失败**（超时/网络 → 可重试）。

产出文件：`hooks/useWebSocket.ts`、`components/VoiceMessageBubble.tsx`、`data/uiContent.ts`。

---

## B3. SUG-2 — 主动消息前端轮询 + 展示

**依赖**：BUG-4 修复后 `/pending` 读库、`id` 恒有值、`/ack` 可标记已读。

**方案**：
1. `services/api.ts` 新增：`getPendingProactive(userId, characterId?)`、`ackProactive(userId, ids)`。
2. 新增 `stores/proactiveStore.ts` + `hooks/useProactivePolling.ts`：登录后按间隔轮询（建议 60–120s；用 `document.visibilitychange` 在页面隐藏时暂停，省电省请求）。
3. 展示形态（建议，非打断式）：
   - 聊天列表 `pages/ChatInboxPage.tsx` 对应角色显示**未读红点 + 预览**。
   - 进入该角色会话时，把主动消息作为角色气泡插入 `components/MessageList`，取走后调 `ackProactive`。
   - 避免全局强弹窗（除非产品明确要「通知」语义）。
4. 语气差异（PROA-03 rin vs dorothy）由后端 persona 决定，前端只渲染。

产出文件：`services/api.ts`、`stores/proactiveStore.ts`（新）、`hooks/useProactivePolling.ts`（新）、`pages/ChatInboxPage.tsx`、`components/MessageList`。

---

## 建议交付顺序

1. B1 全局 Toast（前置，独立 PR，低风险）。
2. B2 SUG-1 语音失败提示（依赖 B1）。
3. B3 SUG-2 主动消息轮询 + 展示（依赖 B1 + BUG-4）。

每步独立 PR、base main、合并即删分支。B3 完成后可解锁测试计划 PROA-02~06。
