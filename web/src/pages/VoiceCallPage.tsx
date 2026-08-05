import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { useAuthStore } from '../stores/authStore'
import { useCharactersStore } from '../stores/charactersStore'
import { resolveCharacterProfile, type CharacterId } from '../data/uiContent'
import { useWebSocket } from '../hooks/useWebSocket'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { useCallAudioPlayer } from '../hooks/useCallAudioPlayer'
import { transcribeAudio } from '../services/api'

interface VoiceCallPageProps {
  isDark: boolean
}

// 全屏语音通话（微信样式）：角色封面做背景，仅保留红色挂断键。
// 半双工 + 点击打断：角色说话时按住键置灰，点屏幕可打断；说完再按住说话。
// 左上角 ··· 控制"是否显示 Ta 说的话"字幕。
export function VoiceCallPage({ isDark: _isDark }: VoiceCallPageProps) {
  const navigate = useNavigate()
  const params = useParams<{ characterId?: string }>()
  const routeId = params.characterId ?? 'rin'
  const characterId = routeId as CharacterId

  const setCharacter = useAppStore((s) => s.setCharacter)
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const setCharacterId = useChatStore((s) => s.setCharacterId)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const serverCharacters = useCharactersStore((s) => s.characters)
  const isStreaming = useChatStore((s) => s.isStreaming[characterId] ?? false)
  const isGenerating = useChatStore((s) => s.isGenerating[characterId] ?? false)
  const messages = useChatStore((s) => s.messages[characterId] ?? [])

  const { sendMessage, interrupt } = useWebSocket()
  const recorder = useVoiceRecorder()
  const { isSpeaking, stop: stopPlayback } = useCallAudioPlayer(characterId)

  const [isRecording, setIsRecording] = useState(false)
  const [showSubtitle, setShowSubtitle] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const busyRef = useRef(false)

  const character = serverCharacters.find((c) => c.id === characterId)
  const profile = resolveCharacterProfile(characterId, character?.display_name, character?.avatar_url, {
    coverUrl: character?.cover_url,
  })
  const cover = character?.cover_url ?? profile.avatar

  // sendMessage reads currentCharacterId from appStore — pin it to this call's
  // character so a turn never leaks into whoever was last on the chat page.
  useEffect(() => {
    setCharacter(characterId)
    setActiveCharacter(characterId)
    setCharacterId(characterId)
  }, [characterId, setCharacter, setActiveCharacter, setCharacterId])

  // Character is "holding the floor" while generating or speaking → mic locked.
  const characterBusy = isStreaming || isGenerating || isSpeaking

  // Latest assistant line for the optional subtitle.
  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
  const subtitleText = lastAssistant?.content ?? ''

  const showToast = useCallback((msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }, [])

  // Tap anywhere while the character speaks → barge-in (stop playback + WS interrupt).
  const handleBargeIn = useCallback(() => {
    if (!characterBusy) return
    stopPlayback()
    interrupt()
  }, [characterBusy, stopPlayback, interrupt])

  const startTalk = useCallback(async () => {
    if (characterBusy || busyRef.current) return
    busyRef.current = true
    setIsRecording(true)
    try {
      await recorder.start()
    } catch {
      setIsRecording(false)
      busyRef.current = false
      showToast('无法访问麦克风，请检查权限')
    }
  }, [characterBusy, recorder, showToast])

  const endTalk = useCallback(async () => {
    if (!isRecording) return
    setIsRecording(false)
    const result = await recorder.stop({ cancel: false })
    busyRef.current = false
    if (!result) {
      showToast('说话时间太短')
      return
    }
    const { wavBlob, durationMs } = result
    try {
      const { transcript, audio_url } = await transcribeAudio(wavBlob, durationMs)
      if (!transcript) {
        showToast('没有识别到语音内容')
        return
      }
      const blobUrl = URL.createObjectURL(wavBlob)
      sendMessage(transcript, {
        voiceBubble: { audioData: blobUrl, durationMs, format: 'wav', audioUrl: audio_url },
        forceVoice: true,
      })
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '语音识别失败')
    }
  }, [isRecording, recorder, sendMessage, showToast])

  const hangUp = useCallback(() => {
    stopPlayback()
    navigate(`/chat/${characterId}`)
  }, [stopPlayback, navigate, characterId])

  if (!isAuthenticated()) {
    navigate('/login', { replace: true })
    return null
  }

  const statusText = isRecording
    ? '正在聆听…'
    : characterBusy
      ? '对方正在说话…'
      : '按住下方按钮说话'

  return (
    <div className="relative w-full h-full overflow-hidden" onClick={handleBargeIn}>
      {/* 封面全景背景 + 深色蒙层 */}
      <img src={cover} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      <div className="absolute inset-0 z-0 bg-black/55" />
      <div className="absolute inset-0 z-0 bg-gradient-to-b from-black/40 via-transparent to-black/70" />

      {/* 左上角 ··· 字幕开关 */}
      <div className="absolute z-20 left-4" style={{ top: 'calc(var(--safe-top) + 12px)' }}>
        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen((v) => !v) }}
          aria-label="通话设置"
          className="w-[44px] h-[44px] flex items-center justify-center rounded-full bg-white/12 backdrop-blur-[14px]"
        >
          <span className="text-[20px] text-white">···</span>
        </button>
        {menuOpen && (
          <div
            onClick={(e) => e.stopPropagation()}
            className="mt-2 w-[220px] rounded-[18px] bg-black/70 backdrop-blur-[18px] border border-white/12 px-4 py-3.5"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-[14px] text-white">是否显示 Ta 说的话</span>
              <button
                onClick={() => setShowSubtitle((v) => !v)}
                className={`relative w-[44px] h-[26px] rounded-full transition-colors ${showSubtitle ? 'bg-[#FF8FAB]' : 'bg-white/25'}`}
              >
                <span className={`absolute top-[3px] left-[3px] w-[20px] h-[20px] rounded-full bg-white transition-transform ${showSubtitle ? 'translate-x-[18px]' : ''}`} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 角色头像 + 名字 + 状态 */}
      <div className="absolute z-10 left-0 right-0 flex flex-col items-center" style={{ top: 'calc(var(--safe-top) + 84px)' }}>
        <img src={profile.avatar} alt={profile.name} className="w-[112px] h-[112px] rounded-full object-cover border-2 border-white/30 shadow-[0_12px_32px_rgba(0,0,0,0.4)]" />
        <p className="mt-4 text-[24px] font-semibold text-white tracking-[-0.01em]">{profile.name}</p>
        <p className="mt-2 text-[15px] text-white/70">{statusText}</p>
      </div>

      {/* 字幕：本轮角色对白（可关闭） */}
      {showSubtitle && subtitleText && (
        <div className="absolute z-10 left-6 right-6 top-1/2 -translate-y-1/2">
          <p className="text-center text-[18px] leading-[1.7] text-white/92 drop-shadow-[0_2px_8px_rgba(0,0,0,0.6)]">
            {subtitleText}
          </p>
        </div>
      )}

      {/* 底部：按住说话 + 红色挂断键 */}
      <div
        className="absolute z-20 left-0 right-0 flex items-center justify-center gap-12"
        style={{ bottom: 'calc(var(--safe-bottom) + 56px)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          disabled={characterBusy}
          onPointerDown={startTalk}
          onPointerUp={endTalk}
          onPointerCancel={endTalk}
          className={`w-[84px] h-[84px] rounded-full flex items-center justify-center touch-none select-none transition-transform ${
            characterBusy ? 'bg-white/15 opacity-50' : isRecording ? 'bg-white/90 scale-110' : 'bg-white/22 backdrop-blur-[14px]'
          }`}
          aria-label="按住说话"
        >
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke={isRecording ? '#FF8FAB' : 'white'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="2" width="6" height="11" rx="3" />
            <path d="M5 10a7 7 0 0 0 14 0" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="8" y1="22" x2="16" y2="22" />
          </svg>
        </button>

        <button
          onClick={hangUp}
          aria-label="挂断"
          className="w-[64px] h-[64px] rounded-full bg-[#FF3B30] flex items-center justify-center shadow-[0_10px_28px_rgba(255,59,48,0.5)] active:scale-90 transition-transform"
        >
          <svg width="30" height="30" viewBox="0 0 24 24" fill="white">
            <path d="M12 9c-1.6 0-3.15.25-4.6.72v3.1c0 .39-.23.74-.56.9-.98.49-1.87 1.12-2.66 1.85-.18.18-.43.28-.7.28-.28 0-.53-.11-.71-.29L.29 13.08a.996.996 0 0 1-.29-.7c0-.28.11-.53.29-.71C3.34 8.78 7.46 7 12 7s8.66 1.78 11.71 4.67c.18.18.29.43.29.71 0 .28-.11.53-.29.71l-1.81 1.81c-.18.18-.43.29-.71.29-.27 0-.52-.11-.7-.28-.79-.74-1.69-1.36-2.67-1.85a1.01 1.01 0 0 1-.56-.9v-3.1C15.15 9.25 13.6 9 12 9z" />
          </svg>
        </button>
      </div>

      {/* 录音/识别轻提示 */}
      {toast && (
        <div className="absolute z-30 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-white text-[13px] bg-black/65 backdrop-blur pointer-events-none" style={{ bottom: 'calc(var(--safe-bottom) + 160px)' }}>
          {toast}
        </div>
      )}
    </div>
  )
}