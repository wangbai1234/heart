# 聊天输入区重构 + 全屏语音通话

分支：`feat/chat-input-redesign-voice-call`（一个大 PR，走 PR 不进 main）

## 背景与决策（已确认）

- 删除 `/character-backstage` 页面。其三功能处置：
  - 文字档位（deepseek/grok）→ 迁到输入框**左上角"文字聊天"入口** + BottomSheet
  - 语音开关（`voice_enabled`）→ 迁到发送键右侧 **"+"菜单里的"语音聊天"弹窗**（沿用现有语义）
  - 清空聊天记录 → **直接丢弃**（列表页左滑删除已覆盖）
- 语音通话：全屏页、角色封面做背景、只留红色挂断键；左上角 ··· 控制"是否显示 Ta 说的话"字幕。
- 打断模型：**半双工 + 点击打断**（复用现有 WS `interrupt`）。

## 架构判断

- 语音通话 = 级联式（MiMo ASR → LLM → Fish TTS），**复用现有 chat WS 管线**，不新开后端通道。
  一次通话轮 = 一次普通 chat 轮（强制 `voice_enabled=true`），自动经过 orchestrator/记忆/安全/计费。
- 现有已就位可复用：`useVoiceRecorder`、`transcribeAudio`、`sendMessage(text, {voiceBubble})`、
  WS 的 `audio_chunk`/`turn_end` 流式音频、`RealtimeStreamSession`(Fish 实时 TTS)、`audioPlayer`。
- 通话轮同样写入聊天历史与记忆——对陪伴产品是正向特性（不是 bug）。

---

## 前端改动

### 1. 删页面 + 清路由
- 删 `web/src/pages/CharacterBackstagePage.tsx`
- `App.tsx`：删 import + 删 `/character-backstage` 路由；新增 `/call/:characterId` 路由
- `CharacterProfilePage.tsx`：删 `openBackstage`；底部"声音与陪伴设置"按钮改为直接进聊天页（或删除该二级入口，倾向删除，因设置已内联到聊天页）

### 2. ConversationChatPage 输入区重构（核心）
当前输入栏结构：`[麦克风/停止] [input] [发送]`。改为：

```
第一行（input 上方，小字入口）：
  [文字聊天 ▸ 普通交流]     ← 左上角，点击开 TextTierSheet
输入栏本体：
  [麦克风/停止] [input] [发送] [+]   ← 发送键右侧新增 "+"
```

- 新增 header ··· 处理：用户说不需要清空，改为**移除 header 的 ··· 按钮**（原本跳后台页，已无去处）。
- 新增 state：`textTierSheetOpen` / `voiceMenuOpen` / `voiceChatSheetOpen`。
- `chatModel`/`voiceChatEnabled` 读写沿用 `appStore`（不变）。
- 挂载时拉一次 `getCharacterSettings` 同步 `voice_enabled`（原在后台页做，迁过来）。

### 3. 新组件（web/src/components/）
- `TextTierSheet.tsx` — 复用 `BottomSheet`。两档：普通交流(deepseek)/私密陪伴(grok)。
  逻辑搬自 CharacterBackstagePage：门控 `isModelAllowed`、定价标签 `getTextTierLabel`、
  未解锁跳 `/membership`。选中写 `setChatModel`。
- `ChatPlusMenu.tsx` — 复用 `BottomSheet`。两项：
  1. "语音聊天"（开关型）→ 开 `VoiceChatSheet`
  2. "语音通话" → `navigate('/call/:characterId')`（未配音色则先引导 `/characters/new?voice=`）
- `VoiceChatSheet.tsx` — 复用 `BottomSheet`。承接原后台页的 `voice_enabled` 开关：
  `Switch` + `handleVoiceToggle`（含 409/hasVoice 引导逻辑，整段搬迁）。

### 4. 全屏语音通话页 `web/src/pages/VoiceCallPage.tsx`（新）
- 路由 `/call/:characterId`；封面 `cover_url` 做全屏背景 + 深色蒙层。
- UI：角色头像/名、通话状态文案（"正在聆听"/"对方正在说话…"）、
  底部**红色挂断键**（返回 `/chat/:id`）、按住说话键（角色说话时置灰）。
- 左上角 ··· → 小弹窗"是否显示 Ta 说的话"开关；开启时页面中心显示本轮 AI 对白文本。
- 复用 `useWebSocket`（同一连接）+ `useVoiceRecorder`：
  按住录音 → `transcribeAudio` → `sendMessage(transcript, {voiceBubble, forceVoice:true})`。
- 自动播放：新建 `useCallAudioPlayer` hook —— 监听该角色最新 assistant 语音消息，
  turn_end 后用 `audioPlayer`/bubble 同款逻辑自动播放（不需点击气泡）。
- 半双工：`isStreaming || isPlaying` 时说话键置灰；点屏幕/停止键 → `interrupt()` + 停播放。

### 5. useWebSocket 扩展
- `sendMessage` 增加 `opts.forceVoice?: boolean`：为 true 时忽略 `voiceChatEnabled[cid]`，
  强制 `voice_enabled=true`（通话页专用，不影响文字聊天页）。

---

## 后端改动

**大部分零改动**——通话复用 `routes_chat_ws.py` 的 chat 流程 + `routes_voice.py` 的 `/transcribe`。

- 确认 `fish_realtime_enabled` 生效路径：默认 `False`（回退阻塞式 REST synth）。
  通话要低延迟需 env 开 `FISH_REALTIME_ENABLED=true`。**这是运维/env 决策**，
  代码不强制；方案里提示，PR 描述注明。
- **不改** Fish v1→v2（现有 v1 provider 仍工作；v2 迁移属独立技术债，另案，不混入本 PR）。
- 无 DB 迁移、无 schema 变更。

---

## 验证
- `bash scripts/ci.sh`（lint + 测试）全绿
- 手动核对：删页面后无死链（grep `character-backstage` 归零）
- 前端 `pnpm build` 通过
- 通话页真机路径：录音→转写→AI 语音自动播放→点击打断→挂断返回

## 风险 / 边界
- 语音通话是 network-exposed 新交互，但复用现有已鉴权的 chat WS（token 门控），无新增未鉴权入口。
- "一个大 PR" 与 CLAUDE.md「PR 小且 7 天内合」有张力——已获你确认，走 feature 分支 + PR，不进 main。
- fish 实时未开时通话仍可用（走 REST synth），只是首音延迟偏高。

## 不做（明确排除）
- Fish v1→v2 协议迁移
- 全双工实时 barge-in / 回声消除 / 流式 VAD
- 浏览器直连 Fish（TTS 一律走后端转发）
- 清空聊天记录入口迁移（已由列表页左滑覆盖）
