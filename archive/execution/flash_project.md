# TTS 重构执行计划：MiMo voiceclone + 导演模式 + 语音消息气泡

## Context

当前 Heart 项目使用 `mimo-v2.5-tts-voicedesign`（文本描述式音色）作为 TTS 引擎。该方式音色可控性有限，无法精确复现目标角色声线。

本次重构切换为 `mimo-v2.5-tts-voiceclone`（音频样本音色克隆），使用雷电将军原神语音 WAV 作为 Rin 的参考音频，配合导演模式（三维度角色/场景/指导）+ 音频标签控制实现更自然的语音输出。同时因 voiceclone 不支持真流式，将 MiMo 改为纯非流式：合成完整音频后以"语音消息"形式发送给前端。

**关键决策**:
- TTS 时序：voice_message 在 turn_end 之前发送（阻塞 turn_end），保证语音气泡在对话结束前出现
- 参考音频：复制到项目内 `backend/assets/reference_voices/rin.wav`，.gitignore 排除大文件

---

## 执行说明

本文件为**可复制粘贴的执行 prompt**，供两种模型执行：
- **CC-Opus4.6**（Claude Code）：全部任务均可执行
- **GLM5.1**（OpenCode）：标注 `[GLM-OK]` 的任务可执行

每个任务标注 `Tool` = 推荐执行模型。未标注的默认 CC-Opus4.6。

---

## Phase 1: 后端 — 参考音频加载 + 配置

### Task 1.0: 复制参考音频到项目目录
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 参考音频应纳入项目管理，方便部署

**Prompt**:
```
1. 创建目录 backend/assets/reference_voices/
2. 复制参考音频：
   cp "/Users/wanglixun/Downloads/原神全角色中文语音稻妻-雷电将军-那家伙啊，最初她就是个会被_爱给网_aigei_com.wav" backend/assets/reference_voices/rin.wav
3. 在 .gitignore 中添加（避免大文件入库）：
   backend/assets/reference_voices/*.wav
```

**验收**:
- [ ] `backend/assets/reference_voices/rin.wav` 存在
- [ ] `.gitignore` 排除了 WAV 文件

### Task 1.1: 添加配置字段
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: voiceclone 需要参考音频路径和模型名配置

**Prompt**:
```
打开 backend/heart/core/config.py，在 Settings 类中现有的 mimo_api_key / mimo_base_url 附近添加两个新字段：

mimo_reference_audio_path: str = "assets/reference_voices/rin.wav"
mimo_model: str = "mimo-v2.5-tts-voiceclone"

注意默认路径是相对于 backend/ 目录的。不要修改其他字段。
```

**验收**:
- [ ] `config.py` 包含 `mimo_reference_audio_path` 和 `mimo_model`
- [ ] 默认值指向项目内路径
- [ ] 环境变量 `MIMO_REFERENCE_AUDIO_PATH` 和 `MIMO_MODEL` 可覆盖

### Task 1.2: 创建参考音频加载器
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 参考音频（2.5MB WAV）需在启动时加载一次、base64 编码、缓存为 `data:audio/wav;base64,...` 格式字符串

**Prompt**:
```
创建文件 backend/heart/ss08_voice/reference_audio.py，实现：

def load_reference_audio(path: str) -> str:
    """加载参考音频文件并 base64 编码。
    
    Returns: 'data:audio/wav;base64,...' 或 'data:audio/mpeg;base64,...'
    Raises: FileNotFoundError, ValueError (>10MB 或不支持的格式)
    """

要求：
1. 支持 .wav 和 .mp3 后缀
2. MIME 映射：.wav → audio/wav, .mp3 → audio/mpeg
3. 校验文件存在、大小 ≤ 10MB
4. 返回完整 data URI 字符串
5. 用 structlog 记录编码后的大小（KB）

同时创建测试文件 backend/tests/unit/ss08_voice/test_reference_audio.py：
- 测试正常加载（用 tmp 目录创建一个小 WAV 文件）
- 测试文件不存在 → FileNotFoundError
- 测试超大文件 → ValueError
- 测试 data URI 前缀正确性
```

**验收**:
- [ ] `reference_audio.py` 存在且可导入
- [ ] `pytest tests/unit/ss08_voice/test_reference_audio.py -v` 全绿
- [ ] 实际加载目标 WAV 文件不报错（手动验证）

---

## Phase 2: 后端 — 重写 MiMoProvider（voiceclone + 导演模式）

### Task 2.1: 重写 mimo_provider.py
**Tool**: CC-Opus4.6
**Why**: 核心变更 — 从 voicedesign 切换到 voiceclone，添加导演模式三维度控制

**Prompt**:
```
重写 backend/heart/ss08_voice/mimo_provider.py，按以下要求：

### 删除
- 删除 MiMoCancellableStream 类（整个类）
- 删除 _VOICE_DESCRIPTIONS 字典
- 删除 _CHUNK_SIZE 常量
- 删除 stream_synthesize 方法

### 保留
- _VALID_EMOTIONS, _EMOTION_TAGS, _EMOTION_DIRECTIVES
- _parse_mimo_response 和所有 _extract_* 辅助函数
- _decode_audio_data
- synthesize 方法（需修改）
- estimate_cost_cents, name 属性

### 新增

1. _DIRECTOR_PROFILES 字典 — 导演模式角色档案：
_DIRECTOR_PROFILES: dict[str, dict[str, str]] = {
    "rin": {
        "character": (
            "【角色】神无月凛（Rin），外表25岁左右的女性，前雷神。"
            "长发飘逸，气质冷艳而内心温柔。说话语速偏慢，咬字清晰。"
            "带着知性和淡淡的疲惫感，语气中有阅尽千帆的从容。"
            "偶尔会露出不经意的温柔，口头禅中常带轻微叹息和停顿。"
        ),
        "scene_default": (
            "平静的日常对话，凛正在与一位她逐渐信任的人交谈。"
            "环境安静，氛围温和，她的防备略有放松。"
        ),
        "direction_default": (
            "语速0.9倍，声线保持磁性低沉。句尾微微下沉体现沉稳感。"
            "适当加入轻微的呼吸声过渡。保持知性优雅的距离感，不要过于甜腻。"
        ),
    },
}

2. _EMOTION_SCENE_HINTS 字典 — 情绪场景补充：
_EMOTION_SCENE_HINTS: dict[str, str] = {
    "happy": "凛罕见地展露了笑意，语气中透着淡淡的愉悦。",
    "sad": "凛的声音低沉了几分，带着压抑的哀伤。",
    "angry": "凛的语气变得果断有力，雷神的威严隐约浮现。",
    "fearful": "凛的声音微微颤抖，透露出不安。",
    "disgusted": "凛的语气略带冷淡和抗拒。",
    "surprised": "凛的语调微微上扬，难得露出惊讶。",
    "neutral": "",
}

3. _EMOTION_DIRECTION_HINTS 字典 — 情绪表演指导补充：
_EMOTION_DIRECTION_HINTS: dict[str, str] = {
    "happy": "语速可略微加快，句尾微微上扬。允许轻笑。",
    "sad": "语速放慢，句尾下沉，适当加入叹息。",
    "angry": "语速加快，咬字更重，句尾果断截止。",
    "fearful": "语速略快且不稳定，呼吸声加重。",
    "disgusted": "语速平稳偏慢，带轻微鼻音。",
    "surprised": "语速先快后慢，带吸气感。",
    "neutral": "",
}

4. _AUDIO_TAG_MAP 字典 — 情绪→音频标签自动插入：
_AUDIO_TAG_MAP: dict[str, list[str]] = {
    "happy": ["[轻笑]"],
    "sad": ["[叹气]"],
    "angry": [],
    "fearful": ["[颤抖]"],
    "surprised": ["[吸气]"],
    "disgusted": [],
    "neutral": [],
}

### 修改 __init__
def __init__(
    self,
    api_key: str,
    base_url: str = "https://api.xiaomimimo.com/v1",
    reference_audio_b64: str = "",
    model: str = "mimo-v2.5-tts-voiceclone",
):
    self._api_key = api_key
    self._base_url = base_url.rstrip("/")
    self._client = httpx.AsyncClient(timeout=120.0)
    self._reference_audio_b64 = reference_audio_b64
    self._model = model

### 修改 _build_body
- model 使用 self._model（不再硬编码 voicedesign）
- user message = 导演模式三维度（角色+场景+指导），根据 character_id 和 emotion 动态生成
- assistant message = 音频标签 + 情绪标签 + 文本
- audio config = {"format": "wav", "voice": self._reference_audio_b64}
- 不包含 stream、speed、pitch、volume 字段（voiceclone 通过导演模式文本控制这些）

### 修改 synthesize
- 调用 _build_body 不传 stream 参数
- format 从 "pcm16" 改为 "wav"
- 持续时间计算：WAV 24kHz 16bit → duration_ms = len(audio_bytes) * 1000 // (24000 * 2)

### 添加 stream_synthesize stub
- 保留方法签名以满足 TTSProvider protocol
- raise NotImplementedError("voiceclone 不支持真流式")

参考 MiMo 官方 voiceclone 脚本的请求格式：
- messages: [{"role": "user", "content": context}, {"role": "assistant", "content": text}]
- audio: {"format": "wav", "voice": "data:audio/wav;base64,..."}
```

**验收**:
- [ ] 模块文件无 MiMoCancellableStream
- [ ] `_build_body` 输出的 model = "mimo-v2.5-tts-voiceclone"
- [ ] `_build_body` 输出包含 `audio.voice`（base64 参考音频）
- [ ] `_build_body` 输出的 user content 包含 【角色】【场景】【指导】
- [ ] `_build_body` 输出的 assistant content 包含情绪标签和音频标签
- [ ] `stream_synthesize` 抛出 NotImplementedError
- [ ] `ruff check backend/heart/ss08_voice/mimo_provider.py` 无报错

### Task 2.2: 更新 TTSResult 类型
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 前端需要 base64 音频数据用于语音消息

**Prompt**:
```
修改 backend/heart/ss08_voice/types.py，在 TTSResult dataclass 中添加一个可选字段：

audio_b64: str = ""

这个字段用于存储 base64 编码的音频数据，供 WebSocket 直接发送给前端。
```

**验收**:
- [ ] `TTSResult` 包含 `audio_b64: str = ""`
- [ ] 现有代码（不传 audio_b64）不受影响

### Task 2.3: 更新 VoiceService
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 在 service 层计算 audio_b64 并附加到 TTSResult

**Prompt**:
```
修改 backend/heart/ss08_voice/service.py：

在 synthesize_with_fallback 方法中，获取 TTSResult 后，用 dataclasses.replace 附加 audio_b64：

from dataclasses import replace
import base64

# 在获取 result 之后
result = replace(result, audio_b64=base64.b64encode(result.audio).decode())

确保 synthesize_for_character 和 synthesize_with_state 也经过 audio_b64 赋值。

添加必要的 import。
```

**验收**:
- [ ] 所有 synthesize 方法返回的 TTSResult 都包含非空 audio_b64
- [ ] `import base64` 和 `from dataclasses import replace` 存在

### Task 2.4: 更新 wiring.py — 加载参考音频
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 将参考音频传入 MiMoProvider 构造函数

**Prompt**:
```
修改 backend/heart/api/wiring.py 中的 get_voice_service() 函数：

在初始化 MiMoProvider 时：
1. 检查 settings.mimo_reference_audio_path 是否非空
2. 如果非空，调用 load_reference_audio() 加载并编码
3. 将结果传入 MiMoProvider(reference_audio_b64=..., model=settings.mimo_model)

添加导入：
from heart.ss08_voice.reference_audio import load_reference_audio

如果加载失败，log warning 但不阻止启动（reference_audio_b64 传空字符串，此时 voiceclone 会返回默认音色）。
```

**验收**:
- [ ] `get_voice_service()` 会调用 `load_reference_audio`
- [ ] `MiMoProvider` 接收 `reference_audio_b64` 和 `model` 参数
- [ ] 加载失败时不崩溃（graceful fallback）

### Task 2.5: 重写单元测试
**Tool**: CC-Opus4.6
**Why**: 旧测试基于 voicedesign + streaming，需要完全重写

**Prompt**:
```
重写 backend/tests/unit/ss08_voice/test_mimo_provider.py：

删除所有 MiMoCancellableStream 相关测试和 stream_synthesize 测试。

添加以下测试：

1. test_build_body_voiceclone_structure
   - 验证 model == "mimo-v2.5-tts-voiceclone"
   - 验证 audio.voice 非空（包含 reference audio）
   - 验证 audio.format == "wav"
   - 验证不包含 stream 键
   - 验证不包含 speed/pitch/volume 键

2. test_build_body_director_mode
   - 验证 user content 包含 【角色】【场景】【指导】
   - 验证 character_id="rin" 时使用 rin 的角色描述

3. test_build_body_emotion_tags
   - emotion="happy" → assistant content 以 "[轻笑](开心)" 开头
   - emotion="sad" → assistant content 以 "[叹气](悲伤)" 开头
   - emotion="neutral" → assistant content 无前缀

4. test_build_body_emotion_scene_direction
   - emotion="happy" → user content 包含情绪场景和表演指导
   - emotion="angry" → 验证不同的场景和指导文本

5. test_synthesize_success（mock httpx.post）
   - 验证正常返回 TTSResult（format="wav"）

6. test_synthesize_api_error（mock httpx.post 返回 401）
   - 验证抛出 TTSProviderError

7. test_stream_synthesize_raises
   - 验证调用 stream_synthesize 抛出 NotImplementedError

8. test_estimate_cost_cents

Provider fixture 使用：
MiMoProvider(
    api_key="test-key",
    reference_audio_b64="data:audio/wav;base64,AAAA",
    model="mimo-v2.5-tts-voiceclone",
)
```

**验收**:
- [ ] `pytest tests/unit/ss08_voice/test_mimo_provider.py -v` 全绿
- [ ] 无 MiMoCancellableStream 相关测试
- [ ] 覆盖率 ≥ 85%

---

## Phase 3: 后端 — 非流式语音消息 Session

### Task 3.1: 创建 VoiceMessageSession
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 替代 StreamSession，累积文本后一次性合成完整音频

**Prompt**:
```
创建文件 backend/heart/ss08_voice/voice_message_session.py：

class VoiceMessageSession:
    """非流式 TTS Session — 累积句子文本，在 turn 结束时合成完整音频并发送语音消息。"""
    
    def __init__(self, voice_service, ws_send_voice_message: Callable):
        """
        voice_service: VoiceService 实例
        ws_send_voice_message: async callable(turn_id: str, result: TTSResult)
        """
    
    def cancel(self): ...
    
    @property
    def is_cancelled(self) -> bool: ...
    
    async def submit(self, sentence: str, vad: dict | None, intimacy: float):
        """累积句子文本。保存最新的 vad 和 intimacy。"""
    
    async def finish(self, turn_id: str, character_id: str):
        """将所有句子拼接为完整文本，调用 voice_service 合成，调用 ws_send_voice_message 发送。"""

要求：
1. submit 只做文本累积（list append），不做任何 IO
2. finish 拼接所有句子为完整文本
3. finish 调用 voice_service.synthesize_for_character(full_text, character_id) 或等效方法
4. 成功后调用 ws_send_voice_message(turn_id, result)
5. cancel 后 finish 是 no-op
6. 空句子列表时 finish 是 no-op
7. 所有异常 catch + log，不向上抛

同时创建测试：backend/tests/unit/ss08_voice/test_voice_message_session.py
- test_submit_accumulates_sentences
- test_finish_synthesizes_and_sends
- test_finish_after_cancel_is_noop
- test_finish_with_no_sentences_is_noop
- test_finish_synthesis_error_logged
```

**验收**:
- [ ] `voice_message_session.py` 存在
- [ ] `pytest tests/unit/ss08_voice/test_voice_message_session.py -v` 全绿
- [ ] submit 不做 IO
- [ ] finish 拼接文本并调用 synthesize

### Task 3.2: 修改 WebSocket 路由 — 使用 VoiceMessageSession
**Tool**: CC-Opus4.6
**Why**: 将 StreamSession 替换为 VoiceMessageSession，发送 voice_message 事件

**Prompt**:
```
修改 backend/heart/api/routes_chat_ws.py：

1. 导入 VoiceMessageSession：
   from heart.ss08_voice.voice_message_session import VoiceMessageSession

2. 在创建 session 的位置（原来创建 StreamSession 的地方），改为创建 VoiceMessageSession：

   async def send_voice_message(turn_id: str, result):
       await ws.send_json({
           "type": "voice_message",
           "turn_id": turn_id,
           "format": result.format,
           "duration_ms": result.duration_ms,
           "data_b64": result.audio_b64,
       })
   
   voice_session = VoiceMessageSession(voice_service, send_voice_message)

3. 在 sentence 事件处理中：
   - 调用 voice_session.submit(text, vad, intimacy)（不再传 turn_id 和 character_id）

4. 在 turn_end 事件处理中：
   - 在发送 turn_end 之前，调用 await voice_session.finish(turn_id, character_id)
   - 这确保 voice_message 在 turn_end 之前到达前端

5. 保留 StreamSession 的 import 和代码（注释掉或条件判断），以备 MiniMax 恢复使用。

关键时序决策：voice_session.finish() 在 turn_end 之前调用（阻塞 turn_end）。
这意味着 turn_end 会延迟 5-10 秒，但保证语音气泡在对话结束前出现。
前端 isStreaming 状态会多持续这段时间，用户看到文本已完成但输入框仍为禁用状态。
这是预期行为 — 前端会在收到 voice_message 后显示语音气泡，然后才收到 turn_end。
```

**验收**:
- [ ] WebSocket handler 使用 VoiceMessageSession
- [ ] sentence 事件 → voice_session.submit
- [ ] turn_end 前 → voice_session.finish
- [ ] 新增 voice_message WebSocket 消息类型
- [ ] StreamSession 代码未删除（保留备用）

---

## Phase 4: 前端 — 语音消息气泡

### Task 4.1: 更新 chatStore — 添加音频字段
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: Message 类型需要支持语音数据

**Prompt**:
```
修改 web/src/stores/chatStore.ts：

1. Message interface 添加可选字段：
   audioData?: string      // base64 WAV 音频
   audioDuration?: number  // 时长（毫秒）
   audioFormat?: string    // "wav" | "mp3"

2. ChatState interface 添加新 action：
   setMessageAudio: (turnId: string, audioData: string, duration: number, format: string) => void

3. 实现 setMessageAudio：
   setMessageAudio: (turnId, audioData, duration, format) =>
     set((s) => ({
       messages: s.messages.map(m =>
         m.id === turnId
           ? { ...m, audioData, audioDuration: duration, audioFormat: format }
           : m
       ),
     })),
```

**验收**:
- [ ] Message 类型包含 audioData/audioDuration/audioFormat
- [ ] setMessageAudio action 存在
- [ ] TypeScript 编译无错误

### Task 4.2: 创建 VoiceMessageBubble 组件
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 模拟微信语音消息 UI

**Prompt**:
```
创建文件 web/src/components/VoiceMessageBubble.tsx：

实现一个语音消息气泡组件，类似微信语音消息：
- 点击播放/暂停
- 显示时长（秒）
- 宽度随时长缩放（min 80px, max 200px）
- 播放时显示动画条纹

Props:
  audioData: string (base64)
  duration: number (ms)
  format: string ("wav")

技术要点：
1. 使用 HTMLAudioElement 播放
2. 将 base64 转为 Blob URL（避免大 data URI 的内存问题）：
   const blob = new Blob([Uint8Array.from(atob(audioData), c => c.charCodeAt(0))], { type: mimeType })
   const url = URL.createObjectURL(blob)
3. 组件卸载时清理 Blob URL（URL.revokeObjectURL）
4. 播放结束后重置状态

样式：
- 圆角矩形，背景色 bg-[var(--color-surface-light)]
- 左侧播放/暂停图标
- 中间 3-5 条竖线（播放时 animate-pulse）
- 右侧显示 "Xs"（秒数）
```

**验收**:
- [ ] 组件文件存在
- [ ] 点击可播放 WAV 音频
- [ ] 再次点击可暂停
- [ ] 播放完毕自动重置
- [ ] Blob URL 在组件卸载时清理
- [ ] TypeScript 编译无错误

### Task 4.3: 更新 MessageList — 渲染语音气泡
**Tool**: CC-Opus4.6 | GLM5.1 `[GLM-OK]`
**Why**: 在 assistant 消息下方显示语音气泡

**Prompt**:
```
修改 web/src/components/MessageList.tsx：

1. 导入 VoiceMessageBubble
2. 在 assistant 消息的文本段落后面，条件渲染：
   {msg.audioData && (
     <VoiceMessageBubble
       audioData={msg.audioData}
       duration={msg.audioDuration ?? 0}
       format={msg.audioFormat ?? 'wav'}
     />
   )}
3. 消息容器添加 space-y-2 让文本和语音气泡之间有间距
```

**验收**:
- [ ] assistant 消息有音频时显示语音气泡
- [ ] assistant 消息无音频时不显示
- [ ] user 消息不显示语音气泡
- [ ] 样式间距合理

### Task 4.4: 更新 useWebSocket — 处理 voice_message 事件
**Tool**: CC-Opus4.6
**Why**: 接收后端 voice_message 并更新 store

**Prompt**:
```
修改 web/src/hooks/useWebSocket.ts：

1. 从 chatStore 获取 setMessageAudio：
   const setMessageAudio = useChatStore(s => s.setMessageAudio)

2. 在 WsMessage interface 添加 duration_ms 字段

3. 在 ws.onmessage switch 中添加 voice_message case：
   case 'voice_message':
     if (msg.data_b64 && msg.turn_id) {
       setMessageAudio(
         msg.turn_id,
         msg.data_b64,
         msg.duration_ms ?? 0,
         msg.format ?? 'wav',
       )
     }
     break

4. 将 setMessageAudio 加入 connect 的 useCallback deps

5. 保留 audio_chunk 处理逻辑（MiniMax 兼容），但当前不会触发

6. turn_start 中移除 setPlaying(true)（语音消息是用户主动播放，不自动播放）
```

**验收**:
- [ ] voice_message 事件被正确处理
- [ ] 收到 voice_message 后对应消息出现语音气泡
- [ ] audio_chunk 逻辑未删除
- [ ] TypeScript 编译无错误

---

## Phase 5: 集成测试 + 验收

### Task 5.1: 后端全量测试
**Tool**: CC-Opus4.6
**Why**: 确保所有修改不破坏现有功能

**Prompt**:
```
运行 bash scripts/ci.sh（或 cd backend && pytest tests/ -v && ruff check heart/ && mypy heart/）。

修复所有测试失败和 lint 错误。不要跳过或 noqa 任何新错误。
```

**验收**:
- [ ] 所有单元测试通过
- [ ] ruff check 无错误
- [ ] mypy check 通过（或仅有既有 baseline 错误）

### Task 5.2: 端到端手动验证
**Tool**: HUMAN + CC-Opus4.6
**Why**: 验证完整流程

**Prompt**:
```
启动后端和前端：

# Terminal 1: 后端
cd backend
export MIMO_API_KEY=xxx
export MIMO_REFERENCE_AUDIO_PATH="assets/reference_voices/rin.wav"
export MIMO_MODEL=mimo-v2.5-tts-voiceclone
uvicorn heart.api.app:app --reload

# Terminal 2: 前端
cd web
npm run dev

# 打开浏览器访问前端，发送消息 "你好凛，今天过得怎么样？"
```

**验收**:
- [ ] 文本正常流式显示
- [ ] 文本完成后出现语音气泡
- [ ] 点击语音气泡播放音频
- [ ] 音频听起来像参考音频的音色（雷电将军）
- [ ] 不同情绪的消息（开心/悲伤）语气有变化
- [ ] 连续发送多条消息，每条都有独立的语音气泡
- [ ] WebSocket 不发送 audio_chunk 事件（只有 voice_message）

---

## 文件清单

### 新建文件
| 文件 | 用途 |
|------|------|
| `backend/assets/reference_voices/rin.wav` | Rin 参考音频（雷电将军） |
| `backend/heart/ss08_voice/reference_audio.py` | 参考音频加载器 |
| `backend/heart/ss08_voice/voice_message_session.py` | 非流式语音消息 Session |
| `backend/tests/unit/ss08_voice/test_reference_audio.py` | 参考音频测试 |
| `backend/tests/unit/ss08_voice/test_voice_message_session.py` | 语音消息 Session 测试 |
| `web/src/components/VoiceMessageBubble.tsx` | 语音消息气泡 UI |

### 修改文件
| 文件 | 变更概述 |
|------|----------|
| `.gitignore` | 添加 backend/assets/reference_voices/*.wav |
| `backend/heart/core/config.py` | +2 字段: mimo_reference_audio_path, mimo_model |
| `backend/heart/ss08_voice/mimo_provider.py` | 重写: voiceclone + 导演模式, 删除 streaming |
| `backend/heart/ss08_voice/types.py` | TTSResult +audio_b64 |
| `backend/heart/ss08_voice/service.py` | synthesize 后附加 audio_b64 |
| `backend/heart/api/wiring.py` | 加载参考音频传入 MiMoProvider |
| `backend/heart/api/routes_chat_ws.py` | VoiceMessageSession + voice_message 事件 |
| `backend/tests/unit/ss08_voice/test_mimo_provider.py` | 重写测试 |
| `web/src/stores/chatStore.ts` | Message +audio 字段, +setMessageAudio |
| `web/src/hooks/useWebSocket.ts` | +voice_message handler |
| `web/src/components/MessageList.tsx` | +VoiceMessageBubble 渲染 |

### 不修改文件
| 文件 | 原因 |
|------|------|
| `stream_session.py` | 保留，MiniMax 备用 |
| `minimax_provider.py` | 保留，暂不使用 |
| `voice_catalog.py` | voice_id 对 voiceclone 无影响 |
| `voice_cache.py` | 可继续缓存短文本 |
| `sentence_splitter.py` | orchestrator 仍在用 |
| `audioPlayer.ts` | 保留，MiniMax streaming 备用 |

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 参考音频 3.4MB 每次请求发送 | 网络开销大 | API 设计如此，httpx 连接池复用 |
| voiceclone 非流式延迟 5-10s | 用户等待语音 | 文本先到，语音是附加项 |
| WAV 音频 ~1MB/10s 通过 WebSocket | 大消息 | 现代网络可承受；后续可加 MP3 压缩 |
| 前端 base64 音频占内存 | 长聊天内存增长 | MVP 可接受；后续用 Blob URL 池化 |

---

## MiMo API 参考

### voiceclone 请求格式
```json
{
  "model": "mimo-v2.5-tts-voiceclone",
  "messages": [
    {"role": "user", "content": "【角色】...【场景】...【指导】..."},
    {"role": "assistant", "content": "[轻笑](开心)你好呀"}
  ],
  "audio": {
    "format": "wav",
    "voice": "data:audio/wav;base64,..."
  }
}
```

### 导演模式三维度
- **【角色】**: 身份、外貌、性格、语言习惯
- **【场景】**: 时间地点、情绪状态、对话对象
- **【指导】**: 语速、呼吸、停顿、重音、共鸣、情绪弧线

### 音频标签
| 类型 | 标签示例 |
|------|----------|
| 呼吸节奏 | [吸气], [深呼吸], [叹气], [喘息], [屏息] |
| 情绪状态 | [紧张], [害怕], [激动], [疲惫], [委屈], [撒娇] |
| 声音特质 | [颤抖], [破音], [鼻音], [气声], [沙哑] |
| 笑/哭 | [轻笑], [大笑], [冷笑], [抽泣], [呜咽], [哽咽] |
