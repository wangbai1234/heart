# 模块 1 · Chat 系统升级：文本/语音 + 持久化 + 计费接入（构建顺序 ④，核心）

> 依赖：模块 4（token/user）、模块 3（credits 扣费）、模块 2（18+ 门禁）。
> 现状关键差距（务必先读 `00_INDEX §1`）：
> - 路由 `/chat`（`ConversationChatPage`）是 **mock**：canned `setTimeout` 回复 + 装饰性 waveform，**不接 WS、不放真实音频**。
> - 真实 WS/音频管线（`useWebSocket`+`chatStore`+`VoiceMessageBubble`+`audioPlayer`）只在**未路由**的 legacy `ChatPage`。
> - **无 `chat_messages` 表**：历史由记忆重建，无逐条 transcript。
> - **TTS 进程级全局**：无 per-user/per-character 开关；`appStore.voiceChatEnabled` 只存本地、后端不认。
> 本模块三件事：① 每角色 TTS 开关真正生效并落库；② 聊天消息持久化（text/audio 可区分、可回放）；③ 把真实 WS 管线接进路由 UI，并在 turn 边界接入计费。

---

## 1. 需求拆解 → 设计决策

| 需求 | 设计 |
|------|------|
| 默认文本聊天 | WS 默认 modality=text；不出 TTS |
| 用户在「角色后台页」开语音 → AI 回复转语音播放 + 语音 UI | `voiceChatEnabled[characterId]` 落库为 `user_character_settings.voice_enabled`；WS chat 消息带 `voice_enabled`；后端仅当 `voice_enabled && 有 voice service && 余额≥voice 单价` 才跑 `StreamSession` TTS |
| 每角色独立 TTS 开关 | `user_character_settings(user_id, character_id, voice_enabled)`；后台页 `Switch` 写库（乐观更新 + PATCH）|
| chat history 区分 text/audio | `chat_messages.modality ∈ {text, voice}` + `audio_url` |
| audio bubble / waveform / speaking state | 复用 `VoiceMessageBubble`（真实播放）；waveform 由 `audioPlayer` 的 AnalyserNode 驱动（非固定数组）；speaking = 播放中态 |

## 2. 数据结构 / Message Schema

### 2.1 `chat_messages`（迁移 `014_chat_messages.py`，按 `user_id` HASH 分区，沿用既有风格 ×32）
| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID | |
| user_id | UUID | 分区键 + FK(应用层)|
| character_id | TEXT | `rin/dorothy` |
| session_id | UUID | 关联 `sessions` |
| turn_id | UUID | 同一 turn 的 user+assistant 共享 |
| role | TEXT | `user/assistant` |
| content | TEXT | 文本内容（assistant 为完整回复；语音也存文本转写）|
| modality | TEXT | `text/voice`（仅 assistant 可能 voice）|
| audio_url | TEXT | 可空；voice 时指向 S3 上的合成音频（可回放）|
| audio_duration_ms | INT | 可空 |
| credits_charged | INT | 可空；该 turn 扣的积分（记在 assistant 行）|
| created_at | TIMESTAMPTZ | INDEX(user_id, character_id, created_at DESC) |
PK `(id, user_id)`（分区表要求分区键入 PK）。

### 2.2 WS 消息协议（在既有基础上增量，`routes_chat_ws.py`）
客户端→服务端 `chat`：
```json
{ "type": "chat", "text": "...", "character_id": "rin", "turn_id": "<uuid>", "voice_enabled": true }
```
> `user_id` **不再由客户端提供**（模块4 已改为取自 token）。`voice_enabled` 由前端按 `user_character_settings` 传；后端仍以库为准做二次判定（防篡改）。

服务端→客户端事件（既有 + 新增）：
| event | 载荷 | 新增? |
|-------|------|-------|
| `turn_start` | `{turn_id}` | 既有 |
| `text_delta` | `{turn_id, delta}` | 既有 |
| `sentence` | `{turn_id, text, vad, intimacy, sentence_seq}` | 既有 |
| `audio_chunk` | `{turn_id, sentence_seq, seq, data_b64, format, is_last}` | 既有 |
| `turn_end` | `{turn_id, modality, credits_charged, balance}` | **扩展**：带扣费结果与新余额 |
| `insufficient_credits` | `{turn_id, needed, balance}` | **新增** |
| `interrupted` / `error` | … | 既有 |

### 2.3 音频持久化（可回放）
- TTS 流式发送的同时，`StreamSession` 累积 PCM/音频分片；`finish()` 时拼成完整音频（复用现有 `audioConcat` 思路的后端等价物）→ 上传 S3 `chat_audio/{user_id}/{turn_id}.wav` → 写 `chat_messages.audio_url`。
- 回放：`VoiceMessageBubble` 有 `audio_url` 时用 `new Audio(url)`（现成实现），无则不可回放（历史里旧消息）。

## 3. per-character 设置落库
- 表 `user_character_settings`（与模块2 迁移 013 合并）：
  | 列 | 类型 |
  |----|------|
  | user_id | UUID |
  | character_id | TEXT |
  | voice_enabled | BOOL default false |
  | updated_at | TIMESTAMPTZ |
  | PK | `(user_id, character_id)` |
- API `backend/heart/api/routes_characters.py`：
  - `GET /api/characters/{cid}/settings` → `{voice_enabled}`
  - `PATCH /api/characters/{cid}/settings` `{voice_enabled}` → 落库
- 前端：`CharacterBackstagePage` 的 `Switch` 改为「乐观更新 + PATCH」；登录/进页时 `GET` 同步 `appStore.voiceChatEnabled`（本地缓存）。

## 4. API / TTS 调用时机（完整 flow）

```
用户发送（WS chat, 带 voice_enabled）
  ▼
后端 从 token 取 user_id → 校验 age_verified（否→error age_verification_required）
  ▼
读 user_character_settings.voice_enabled（库为准）→ effective_voice = 库值 && voice_service 可用
  ▼
预计花费 = effective_voice ? CREDITS_PER_VOICE_TURN : CREDITS_PER_TEXT_TURN
  ▼
billing.get_balance < 预计花费 → 发 insufficient_credits，结束（不生成、不落库、不扣费）
  ▼
turn_start → orchestrator.process_turn_stream：
   text_delta 流式 → 前端拼字
   每 sentence：若 effective_voice → StreamSession.submit → TTS → audio_chunk 逐帧下发
  ▼
turn_end（正常收尾，非安全拦截/非 fallback）：
   实际 modality = 是否真的产生了音频
   billing.charge_turn(user_id, turn_id, modality)  // 幂等键 turn:{turn_id}
   若 voice：上传合成音频 → audio_url
   落 chat_messages：user 行(role=user,text) + assistant 行(role=assistant, modality, content, audio_url, credits_charged)
   下发 turn_end{modality, credits_charged, balance}
  ▼
安全拦截(RED/PURPLE)/生成异常/fallback：不扣费；assistant 行仍落库(modality=text, credits_charged=0)，标注 safety
```

- **不扣费判定**：orchestrator 返回结果需带标志（`was_fallback` / `safety_blocked`）。已有安全路径（`_write_safety_event`、care/reject path）——扩展 turn 结果结构透出该标志给 WS 层。
- **REST `/api/chat`**（非流式，保留兼容）：同样预检 + 扣 text 单价 + 落库；不产音频。

## 5. 聊天历史加载（跨设备）
- `GET /api/chat/history?character_id=&cursor=&limit=30` → 倒序分页 `chat_messages` → 前端进 `/chat` 时拉取填充。
- 替代当前 `conversationStore` 的 mock 种子；`conversationStore` 改为「从 API 装填 + WS 增量 append」。

## 6. 前端改造（把真实管线接进路由 UI —— 本模块最重工作）

### 6.1 统一到一套 Chat
- **弃用** legacy `pages/ChatPage.tsx`（保留文件但不路由）。把其真实能力迁进路由页。
- 改造 `components/ConversationChatPage.tsx`（`/chat` 实际渲染者）：
  1. **接 `useWebSocket`**：发送走 `sendMessage(text)`（带 `voice_enabled = appStore.voiceChatEnabled[currentCharacterId]`），删除 `setTimeout` 假回复。
  2. **文本流**：`text_delta` 实时拼进当前 assistant 气泡（复用 `chatStore` 或把 `conversationStore` 升级为接 WS 事件）。
  3. **语音气泡**：`msg.kind==='voice'`（有 `audioData`/`audio_url`）→ 用**真实** `VoiceMessageBubble`（现成播放 + 动画条），替换现在的固定 `WAVEFORM_HEIGHTS` 装饰。
  4. **speaking 态**：`chatStore.isPlaying` → 头部 orb / 气泡显示"朗读中"。
  5. **打断**：发送时若在播报 → `interrupt()`。
  6. **历史**：进页 `GET /api/chat/history` 填充。
  7. **计费反馈**：`turn_end.balance` → 同步 `creditsStore`；`insufficient_credits` → `Dialog` 引导 `/redeem`。
- 统一 store：建议将 `conversationStore` 与 `chatStore` 合并/桥接为单一「会话 store」，避免两套并存（当前分裂是主要债）。保留 `ConversationMessage.kind: 'text'|'voice'`。

### 6.2 waveform 真实化
- `VoiceMessageBubble` 播放时用 `audioPlayer.getAnalyser()`（`MSEAudioPlayer`/`WebAudioPlayer` 已提供 AnalyserNode）驱动条形高度；无 analyser（历史 `new Audio()`）时退化为轻量随机动画（现状即如此）。

### 6.3 角色后台页
- `CharacterBackstagePage`「是否开启语音聊天」`Switch`：改为写库（§3）；文案「开启后 AI 回复将转为语音，语音回复消耗 {CREDITS_PER_VOICE_TURN} 积分/条」（用真实单价，替换含糊"额度将增加"）。

## 7. 音频/格式对齐（避免踩坑）
- MiMo 输出 `pcm16 @24kHz mono`；WS 下发 `format:"pcm16"`，前端 `wrapPCM16AsWAV(pcm,24000,1,16)` → `WebAudioPlayer`（已实现，勿动）。
- 回放持久化音频存 WAV（前端 `new Audio()` 能直接放）。
- `chunk` 去重与 `turn_id` 校验逻辑（`useWebSocket` 已有）保留。

## 8. 验收
- 关语音：发消息只出文本流，`turn_end.modality=text`，扣 1，落 2 行 chat_messages。
- 开语音（后台 Switch→库）：发消息出文本 + 逐句 TTS 播放，气泡为真实可回放语音条，扣 5，`audio_url` 可回放。
- 余额不足：`insufficient_credits` → 不生成不扣费 → 引导兑换。
- 安全拦截 turn：不扣费，仍落库并标注。
- 退出重进 `/chat`：`GET /history` 正确回填，语音历史可回放。
- 跨设备：A 设备开语音，B 设备登录同账号该角色也为开（库同步）。
- 打断：播报中发新消息 → 旧音频停、新 turn 起。

---

## ⚙️ Mimo 执行 Prompt（复制交付）

```
你在 Heart 仓库（对外名 yuoyuo）实现「模块1：Chat 文本/语音 + 持久化 + 计费接入」。分支 feat/chat-voice-billing，base=main（体量大，可再拆 3 个子PR：持久化、计费接入、前端接真管线）。依赖模块4/3/2。务必先读 00_INDEX §1 现状：路由 /chat 是 mock、真实管线在未路由的 legacy ChatPage、无 chat_messages 表、TTS 是进程级全局。严格按 04_chat_voice.md。

后端：
1. 迁移 014_chat_messages.py：按 user_id HASH 分区(×32)建 chat_messages，字段严格按 §2.1（modality text/voice、audio_url、credits_charged、turn_id、PK(id,user_id)）。写 downgrade。user_character_settings 若模块2 未建则在此建（§3）。
2. routes_characters.py：GET/PATCH /api/characters/{cid}/settings {voice_enabled} 落库 user_character_settings。
3. routes_chat_ws.py 改造：user_id 取自 token（模块4已改）；chat 消息读 voice_enabled 但以 user_character_settings 库值为准做二次判定；age_verified 门禁；turn 开始预检 billing.get_balance vs 预计花费(voice?5:1)，不足发 insufficient_credits 且不生成不落库不扣费；turn 正常收尾调 billing.charge_turn(user_id,turn_id,modality) 幂等键 turn:{turn_id}，voice 则拼接合成音频上传 S3 写 audio_url，落 chat_messages(user+assistant 两行)，turn_end 扩展带 modality/credits_charged/balance；安全拦截/fallback 不扣费但仍落库标注（扩展 orchestrator 结果透出 was_fallback/safety_blocked 标志）。
4. REST /api/chat 同步做预检+扣 text+落库（不产音频）。
5. GET /api/chat/history?character_id&cursor&limit 倒序分页。

前端：
6. 把真实 WS 管线接进路由页 components/ConversationChatPage.tsx：接 useWebSocket，sendMessage 带 voice_enabled=appStore.voiceChatEnabled[cid]，删除 setTimeout 假回复；text_delta 实时拼气泡；语音消息用真实 VoiceMessageBubble（可回放+AnalyserNode 驱动 waveform），替换固定 WAVEFORM_HEIGHTS；isPlaying→朗读中态；进页 GET /history 回填；turn_end.balance 同步 creditsStore；insufficient_credits→Dialog 引导 /redeem。建议合并 conversationStore 与 chatStore 为单一会话 store，消除两套并存。legacy pages/ChatPage.tsx 停止路由。
7. CharacterBackstagePage 语音 Switch 改写库（乐观更新+PATCH /api/characters/{cid}/settings，进页 GET 同步），文案改真实单价"语音回复消耗5积分/条"。
8. services/api.ts 增 getCharacterSettings/updateCharacterSettings/getChatHistory。

约束：音频链路 pcm16@24kHz + wrapPCM16AsWAV + WebAudioPlayer 勿改；复用 tokens.css，light+dark 双验收；用户可见文案无 心屿/Heart。测试覆盖 §8 全部（关/开语音扣费与落库、余额不足不扣费、安全拦截不扣费、history 回填、跨设备开关同步、打断）。ci.sh 全绿、alembic upgrade heads 干净、npm run build 通过，开 PR。
```
