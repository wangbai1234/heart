import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { useChatStore, type Message } from '../stores/chatStore'
import { useAuthStore } from '../stores/authStore'
import { CHARACTER_PROFILES, resolveCharacterProfile, shouldShowTimestamp, formatChatTime, type CharacterId } from '../data/uiContent'
import { useCharactersStore } from '../stores/charactersStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { useProactiveStore } from '../stores/proactiveStore'
import { getChatHistory, ackProactive, markCharacterRead, transcribeAudio } from '../services/api'
import { BreathingDots } from './ui/BreathingDots'
import { Dialog } from './ui/Dialog'
import { Button } from './ui/Button'
import { Avatar } from './ui/Avatar'
import VoiceMessageBubble from './VoiceMessageBubble'
import { useSwipeNavigation } from '../hooks/useSwipeNavigation'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { VoiceRecordingOverlay } from './VoiceRecordingOverlay'

const EMPTY_MESSAGES: Message[] = []

interface ConversationChatPageProps {
  isDark: boolean
}

export function ConversationChatPage({ isDark }: ConversationChatPageProps) {
  const navigate = useNavigate()
  const params = useParams<{ characterId?: string }>()
  const [input, setInput] = useState('')
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [expandedVoiceTextIds, setExpandedVoiceTextIds] = useState<Set<string>>(new Set())
  const scrollRef = useRef<HTMLDivElement>(null)

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false)
  const [willCancel, setWillCancel] = useState(false)
  const [recordingToast, setRecordingToast] = useState<string | null>(null)
  const cancelZoneRef = useRef<HTMLDivElement | null>(null)
  const recorder = useVoiceRecorder()

  // Right-swipe from left edge → back to chat list
  useSwipeNavigation({ onRightSwipe: () => navigate('/home') })

  const storedCharacterId = useAppStore((s) => s.currentCharacterId)
  const setCharacter = useAppStore((s) => s.setCharacter)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const userAvatar = useAuthStore((s) => s.user?.avatar_url ?? null)
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const serverCharacters = useCharactersStore((s) => s.characters)
  const catalogLoaded = useCharactersStore((s) => s.loaded)

  // Known ids = built-ins (always, for cold-load direct links) ∪ server catalog.
  const knownIds = new Set<string>([
    ...Object.keys(CHARACTER_PROFILES),
    ...serverCharacters.map((c) => c.id),
  ])
  const routeCharacterId = params.characterId
  const isValidCharacterId = !!routeCharacterId && knownIds.has(routeCharacterId)
  const currentCharacterId = (isValidCharacterId ? routeCharacterId : storedCharacterId) as CharacterId

  const messages = useChatStore((s) => s.messages[currentCharacterId as CharacterId] ?? EMPTY_MESSAGES)
  const isCleared = useChatStore((s) => s.clearedCharacters.has(currentCharacterId as CharacterId))
  const isStreaming = useChatStore((s) => s.isStreaming[currentCharacterId as CharacterId] ?? false)
  const isPlaying = useChatStore((s) => s.isPlaying)
  const addMessage = useChatStore((s) => s.addMessage)
  const setCharacterId = useChatStore((s) => s.setCharacterId)
  const appendMessage = useChatStore((s) => s.appendMessage)
  const setLastFetchedAt = useChatStore((s) => s.setLastFetchedAt)
  const setMessageAudioUrl = useChatStore((s) => s.setMessageAudioUrl)
  const isGenerating = useChatStore((s) => s.isGenerating[currentCharacterId as CharacterId] ?? false)
  const insufficientCredits = useChatStore((s) => s.insufficientCredits)
  const clearInsufficientCredits = useChatStore((s) => s.clearInsufficientCredits)
  const modelForbidden = useChatStore((s) => s.modelForbidden)
  const clearModelForbidden = useChatStore((s) => s.clearModelForbidden)

  const { sendMessage, interrupt } = useWebSocket()

  const currentCharacter = serverCharacters.find((c) => c.id === currentCharacterId)
  const displayName = currentCharacter?.display_name
  const avatarUrl = currentCharacter?.avatar_url
  const profile = resolveCharacterProfile(currentCharacterId, displayName, avatarUrl)
  const pageBg = isDark
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  const setInboxUnreadTotal = useAppStore((s) => s.setInboxUnreadTotal)

  // Mark character read on mount + unmount: clears the unread badge for this
  // character on entry AND when leaving via in-app navigation (SPA navigate
  // doesn't fire visibilitychange/pagehide — those are tab-level events).
  useEffect(() => {
    if (!isAuthenticated()) return
    markCharacterRead(currentCharacterId).catch(() => {})
    // Optimistically clear badge; ChatInboxPage will recompute on next open.
    setInboxUnreadTotal(0)
    return () => {
      // Fire-and-forget on unmount; response ignored (component is gone).
      markCharacterRead(currentCharacterId).catch(() => {})
    }
  }, [currentCharacterId, isAuthenticated, setInboxUnreadTotal])

  // Also mark read when new assistant messages arrive during the visit AND
  // when the tab is being hidden.  Without this, mark-read only ever
  // captured last_read_at from mount time; any assistant reply that landed
  // during the visit stayed "unread" until the user re-entered — the "只有再
  // 次进入聊天页 → 再退出 才变成已读" bug from 2026-07-11.
  const lastAssistantId = messages.length > 0 ? messages[messages.length - 1].id : null
  const lastAssistantRole = messages.length > 0 ? messages[messages.length - 1].role : null
  useEffect(() => {
    if (!isAuthenticated()) return
    if (lastAssistantRole !== 'assistant') return
    // Debounce so text_delta storms don't produce a mark-read per token.
    const t = setTimeout(() => {
      markCharacterRead(currentCharacterId).catch(() => {})
    }, 400)
    return () => clearTimeout(t)
  }, [currentCharacterId, isAuthenticated, lastAssistantId, lastAssistantRole])

  useEffect(() => {
    const onHide = () => {
      if (!isAuthenticated()) return
      if (document.visibilityState === 'hidden') {
        markCharacterRead(currentCharacterId).catch(() => {})
      }
    }
    window.addEventListener('pagehide', onHide)
    document.addEventListener('visibilitychange', onHide)
    return () => {
      window.removeEventListener('pagehide', onHide)
      document.removeEventListener('visibilitychange', onHide)
    }
  }, [currentCharacterId, isAuthenticated])

  // Set character ID in chat store
  useEffect(() => {
    // Only redirect an unknown id once the catalog is loaded — otherwise a direct
    // link to a valid (UGC) character would be bounced during the async fetch.
    if (routeCharacterId && !isValidCharacterId && catalogLoaded) {
      navigate('/chat', { replace: true })
      return
    }
    if (currentCharacterId !== storedCharacterId) {
      setCharacter(currentCharacterId)
    }
    setActiveCharacter(currentCharacterId)
    setCharacterId(currentCharacterId)
  }, [currentCharacterId, isValidCharacterId, catalogLoaded, navigate, routeCharacterId, setActiveCharacter, setCharacter, setCharacterId, storedCharacterId])

  // Load chat history from API on mount / character change
  const prevCharRef = useRef(currentCharacterId)
  useEffect(() => {
    if (!isAuthenticated()) return
    setHistoryLoaded(false)
    prevCharRef.current = currentCharacterId

    const existing = useChatStore.getState().messages[currentCharacterId] ?? []
    const stale = Date.now() - (useChatStore.getState().lastFetchedAt[currentCharacterId] ?? 0) > 5 * 60 * 1000
    if (existing.length > 0 && !stale) {
      setHistoryLoaded(true)
      return
    }
    if (isCleared) {
      setHistoryLoaded(true)
      return
    }

    getChatHistory(currentCharacterId, undefined, 50)
      .then((data) => {
        const reversed = [...data.items].reverse()
        for (const item of reversed) {
          addMessage(currentCharacterId, {
            id: item.id,
            role: item.role as 'user' | 'assistant',
            content: item.content,
            timestamp: new Date(item.created_at).getTime(),
            // Prefer the server-provided kind (added in the fix for
            // TEST_REPORT_20260712 BUG-5). Falls back to modality when the
            // server response is old (no `kind` field).
            kind: item.kind === 'action' ? 'action' : item.modality === 'voice' ? 'voice' : 'text',
            // Durable pointer (persisted) rather than audioData, so the voice
            // bubble survives the next refresh too. VoiceMessageBubble fetches
            // /api/ URLs with auth.
            audioUrl: item.modality === 'voice' && item.audio_url ? `/api/chat/audio/${item.id}` : undefined,
            audioDuration: item.audio_duration_ms ?? undefined,
            audioFormat: item.modality === 'voice' ? 'wav' : undefined,
          })
        }
        if (reversed.length > 0) {
          const last = reversed[reversed.length - 1]
          appendMessage(currentCharacterId, {
            id: last.id,
            role: last.role as 'assistant' | 'user',
            content: last.content,
            timestamp: new Date(last.created_at).getTime(),
            kind: last.kind === 'action' ? 'action' : last.modality === 'voice' ? 'voice' : 'text',
            audioDuration: last.audio_duration_ms ?? undefined,
          })
        }
        setLastFetchedAt(currentCharacterId, Date.now())
        setHistoryLoaded(true)
      })
      .catch(() => {
        setHistoryLoaded(true)
      })
  }, [currentCharacterId, isAuthenticated, isCleared])

  // Resolve voice bubbles that were still synthesising when the user left the
  // page. The turn keeps generating server-side (background) and is persisted;
  // the stuck placeholder's id === turn_id, so point it at the by-turn endpoint
  // to pull the now-persisted audio. Without this the bubble sits on "加载中"
  // forever (the reported "退出页面语音卡在加载态" bug). Never touches the turn
  // that is streaming right now.
  useEffect(() => {
    const cid = currentCharacterId
    const msgs = useChatStore.getState().messages[cid as CharacterId] ?? []
    const streamingTurnId = useChatStore.getState().currentTurnId
    for (const m of msgs) {
      if (
        m.role === 'assistant' &&
        m.kind === 'voice' &&
        !m.audioData &&
        !m.audioUrl &&
        m.id !== streamingTurnId
      ) {
        setMessageAudioUrl(cid, m.id, `/api/chat/audio/by-turn/${m.id}`)
      }
    }
    // Re-runs when isStreaming flips false too: on reconnect the WS layer clears
    // the orphaned turn's streaming state (useWebSocket onopen), and only then is
    // the placeholder no longer the "current turn" and safe to resolve.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCharacterId, isStreaming])

  // Surface any pending proactive messages (SS06) once history has loaded, then
  // ack them so they are not re-served. Injected after history to preserve order
  // and to avoid suppressing the history load (which only runs when empty).
  useEffect(() => {
    if (!historyLoaded) return
    const pending = useProactiveStore.getState().drain(currentCharacterId)
    if (pending.length === 0) return
    for (const m of pending) {
      const proactiveMsg = {
        id: m.id,
        role: 'assistant' as const,
        content: m.content,
        timestamp: new Date(m.created_at).getTime(),
        kind: 'text' as const,
      }
      addMessage(currentCharacterId, proactiveMsg)
      appendMessage(currentCharacterId, proactiveMsg)
    }
    const { user } = useAuthStore.getState()
    if (user?.id) {
      void ackProactive(user.id, pending.map((m) => m.id)).catch(() => {})
    }
  }, [historyLoaded, currentCharacterId, addMessage, appendMessage])

  // Sync on visibilitychange: re-fetch latest messages + mark character read
  useEffect(() => {
    const handler = () => {
      if (document.visibilityState !== 'visible') return
      if (!isAuthenticated()) return
      markCharacterRead(currentCharacterId).catch(() => {})
      getChatHistory(currentCharacterId, undefined, 20)
        .then((data) => {
          const incomingMsgs = [...data.items].reverse()
          const existing = useChatStore.getState().messages[currentCharacterId] ?? []
          const existingIds = new Set(existing.map((m) => m.id))
          const fresh = incomingMsgs.filter((item) => !existingIds.has(item.id))
          for (const item of fresh) {
            addMessage(currentCharacterId, {
              id: item.id,
              role: item.role as 'user' | 'assistant',
              content: item.content,
              timestamp: new Date(item.created_at).getTime(),
              // Prefer the server-provided kind (added in the fix for
              // TEST_REPORT_20260712 BUG-5). Falls back to modality when
              // the server response is old (no `kind` field).
              kind: item.kind === 'action' ? 'action' : item.modality === 'voice' ? 'voice' : 'text',
              audioUrl: item.modality === 'voice' && item.audio_url ? `/api/chat/audio/${item.id}` : undefined,
              audioDuration: item.audio_duration_ms ?? undefined,
            })
          }
          if (fresh.length > 0) setLastFetchedAt(currentCharacterId, Date.now())
        })
        .catch(() => {})
    }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [currentCharacterId, isAuthenticated, addMessage, setLastFetchedAt])

  // Auto-scroll on new messages
  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      requestAnimationFrame(() => el.scrollTo(0, el.scrollHeight))
    }
  }, [messages, isStreaming])

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    sendMessage(trimmed)
    setInput('')
  }, [input, isStreaming, sendMessage])

  const handleInterrupt = useCallback(() => {
    interrupt()
  }, [interrupt])

  const showToast = useCallback((msg: string) => {
    setRecordingToast(msg)
    setTimeout(() => setRecordingToast(null), 2500)
  }, [])

  const handleMicPointerDown = useCallback(
    async (e: React.PointerEvent<HTMLButtonElement>) => {
      if (isStreaming) return
      e.currentTarget.setPointerCapture(e.pointerId)
      setIsRecording(true)
      setWillCancel(false)
      try {
        await recorder.start()
      } catch {
        setIsRecording(false)
        showToast('无法访问麦克风，请检查权限')
      }
    },
    [isStreaming, recorder, showToast],
  )

  const handleMicPointerMove = useCallback(
    (e: React.PointerEvent<HTMLButtonElement>) => {
      if (!isRecording || !cancelZoneRef.current) return
      const rect = cancelZoneRef.current.getBoundingClientRect()
      const inside =
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      setWillCancel(inside)
    },
    [isRecording],
  )

  const handleMicPointerUp = useCallback(
    async (_e: React.PointerEvent<HTMLButtonElement>) => {
      if (!isRecording) return
      setIsRecording(false)
      const cancel = willCancel
      setWillCancel(false)

      const result = await recorder.stop({ cancel })
      if (!result) {
        if (!cancel) showToast('说话时间太短')
        return
      }

      const { wavBlob, durationMs } = result
      const blobUrl = URL.createObjectURL(wavBlob)

      try {
        const { transcript } = await transcribeAudio(wavBlob, durationMs)
        if (!transcript) {
          URL.revokeObjectURL(blobUrl)
          showToast('没有识别到语音内容')
          return
        }
        sendMessage(transcript, {
          voiceBubble: { audioData: blobUrl, durationMs, format: 'wav' },
        })
      } catch (err: unknown) {
        URL.revokeObjectURL(blobUrl)
        const msg = err instanceof Error ? err.message : '语音识别失败'
        showToast(msg)
      }
    },
    [isRecording, willCancel, recorder, sendMessage, showToast],
  )

  const toggleVoiceTranscript = useCallback((messageId: string) => {
    setExpandedVoiceTextIds((prev) => {
      const next = new Set(prev)
      if (next.has(messageId)) {
        next.delete(messageId)
      } else {
        next.add(messageId)
      }
      return next
    })
  }, [])

  // Render a single message bubble
  const renderMessage = (msg: Message, showAvatar: boolean, isLastAndGenerating = false) => {
    const isAI = msg.role === 'assistant'
    const avatar = isAI ? profile.avatar : userAvatar

    // While generating (streaming + waiting for message_bubble), always show typing dots
    if (isAI && isLastAndGenerating) {
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isDark
              ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[rgba(255,255,255,0.06)]'
              : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[var(--color-border-glass)]'
          }`}>
            <BreathingDots />
          </div>
        </div>
      )
    }

    // Voice mode loading bubble uses the same shell as text loading. Only a
    // voice message with NEITHER live audio NOR a durable server pointer is
    // genuinely still loading; a rehydrated/historical one has audioUrl.
    if (msg.kind === 'voice' && !msg.audioData && !msg.audioUrl) {
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isDark
              ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[rgba(255,255,255,0.06)]'
              : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[var(--color-border-glass)]'
          }`}>
            <BreathingDots />
          </div>
        </div>
      )
    }

    // Action bubble — grey italic narration (parenthetical action / expression / OOC)
    // Rendered without avatar, centre-aligned, low-contrast to keep the reader's
    // eye on the dialog. Independent from voice / TTS.
    if (msg.kind === 'action' && msg.content) {
      return (
        <div className="flex justify-center my-1">
          <div className={`max-w-[80%] px-3 py-1.5 rounded-full text-[13px] italic ${
            isDark
              ? 'bg-[rgba(255,255,255,0.05)] text-[rgba(228,228,231,0.55)]'
              : 'bg-[rgba(0,0,0,0.04)] text-[rgba(45,50,72,0.55)]'
          }`}>
            {msg.content}
          </div>
        </div>
      )
    }

    // Show breathing dots in text bubble when message is empty during streaming
    const isEmpty = msg.content === '' && isStreaming
    if (isEmpty) {
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isAI
              ? isDark
                ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[rgba(255,255,255,0.06)]'
                : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[var(--color-border-glass)]'
              : isDark
                ? 'bg-gradient-to-br from-[#4A5B8F] to-[#6C7DB5] rounded-[6px_20px_20px_20px]'
                : 'bg-gradient-to-br from-[#A7C7E7] to-[#BFD7EE] rounded-[6px_20px_20px_20px]'
          }`}>
            <BreathingDots />
          </div>
        </div>
      )
    }

    // Voice message with audio — live base64 (this session) or a durable
    // server URL (rehydrated after refresh / loaded from history).
    if (msg.kind === 'voice' && (msg.audioData || msg.audioUrl)) {
      const transcriptExpanded = expandedVoiceTextIds.has(msg.id)
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className="max-w-[348px]">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <VoiceMessageBubble
                  audioData={msg.audioData ?? msg.audioUrl ?? ''}
                  duration={msg.audioDuration ?? 3000}
                  format={msg.audioFormat ?? 'wav'}
                  isDark={isDark}
                />
              </div>
              {msg.content && (
                <button
                  type="button"
                  onClick={() => toggleVoiceTranscript(msg.id)}
                  className={`mb-1 shrink-0 rounded-full px-3 py-2 text-[12px] font-medium backdrop-blur-[14px] transition-colors ${
                    isDark
                      ? 'bg-[rgba(255,255,255,0.08)] text-[rgba(248,242,250,0.82)] border border-[rgba(255,255,255,0.08)]'
                      : 'bg-[rgba(255,255,255,0.58)] text-[rgba(91,93,117,0.82)] border border-[rgba(255,255,255,0.74)]'
                  }`}
                >
                  {transcriptExpanded ? '收起文字' : '转文字'}
                </button>
              )}
            </div>
            {msg.content && transcriptExpanded && (
              <div
                className={`mt-2 rounded-[20px] px-4 py-3 text-[13px] leading-[1.65] backdrop-blur-[14px] ${
                  isDark
                    ? 'bg-[rgba(255,255,255,0.06)] text-[rgba(236,230,241,0.76)] border border-[rgba(255,255,255,0.06)]'
                    : 'bg-[rgba(255,255,255,0.52)] text-[rgba(93,95,118,0.84)] border border-[rgba(255,255,255,0.68)]'
                }`}
              >
                {msg.content}
              </div>
            )}
          </div>
        </div>
      )
    }

    // Text message
    return (
      <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
        {showAvatar ? (
          <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
        ) : (
          <div className="w-[40px] shrink-0" />
        )}
        <div
          className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isAI
              ? isDark
                ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] text-[#EFE7DD] border border-[rgba(255,255,255,0.06)]'
                : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] text-[var(--color-ink)] border border-[var(--color-border-glass)]'
              : isDark
                ? 'bg-gradient-to-br from-[#4A5B8F] to-[#6C7DB5] rounded-[6px_20px_20px_20px] text-[#EFE7DD] min-w-[48px]'
                : 'bg-gradient-to-br from-[#A7C7E7] to-[#BFD7EE] rounded-[6px_20px_20px_20px] text-white min-w-[48px]'
          }`}
        >
          <p className="text-[16px] leading-[1.6] whitespace-pre-wrap break-words">
            {msg.content}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />

      {/* Header */}
      <header
        className={`relative z-20 flex items-center gap-3 px-5 py-3 backdrop-blur-[20px] rounded-b-[20px] ${
          isDark
            ? 'bg-[rgba(26,26,46,0.75)] shadow-[0_2px_12px_rgba(0,0,0,0.12)] border-b border-[rgba(255,255,255,0.06)]'
            : 'bg-[rgba(255,255,255,0.75)] shadow-[0_2px_12px_rgba(0,0,0,0.06)]'
        }`}
        style={{ paddingTop: 'calc(var(--safe-top) + 12px)' }}
      >
        <button onClick={() => navigate('/chat')} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke={isDark ? '#E4E4E7' : 'var(--color-ink)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <img src={profile.avatar} alt={profile.name} className="w-[40px] h-[40px] rounded-full object-cover" />
        <div className="flex-1 min-w-0">
          <p className={`text-[17px] font-semibold ${isDark ? 'text-[#E4E4E7]' : 'text-[var(--color-ink)]'}`}>{profile.name}</p>
          <div className="flex items-center gap-1">
            <div className="w-[6px] h-[6px] rounded-full bg-[var(--color-online)]" />
            <span className={`text-[13px] ${isDark ? 'text-[rgba(228,228,231,0.65)]' : 'text-[var(--color-text-secondary)]'}`}>
              {isStreaming ? '正在回复…' : isPlaying ? '朗读中' : profile.statusLabel}
            </span>
          </div>
        </div>
        <button onClick={() => navigate('/character-backstage')} className="w-[44px] h-[44px] flex items-center justify-center" aria-label="打开角色后台">
          <span className={`text-[20px] ${isDark ? 'text-[#E4E4E7]' : 'text-[var(--color-ink)]'}`}>···</span>
        </button>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        {!historyLoaded && (
          <div className="flex-1 flex items-center justify-center">
            <BreathingDots />
          </div>
        )}

        {historyLoaded && messages.length === 0 && (
          <div className={`text-center text-[13px] py-8 ${isDark ? 'text-[rgba(228,228,231,0.4)]' : 'text-[var(--color-text-muted)]'}`}>
            和{profile.shortName}说点什么吧
          </div>
        )}

        {messages.map((msg, index) => {
          const prev = index > 0 ? messages[index - 1] : null
          const showTime = shouldShowTimestamp(msg, prev)
          const showAvatar = !prev || prev.role !== msg.role || showTime
          const isLastAndGenerating = index === messages.length - 1 && isGenerating

          return (
            <div key={msg.id} className="flex flex-col">
              {showTime && (
                <div className="flex justify-center py-2">
                  <span className={`inline-flex h-[22px] items-center rounded-full px-2.5 text-[11px] ${
                    isDark
                      ? 'bg-[rgba(255,255,255,0.08)] text-[rgba(228,228,231,0.5)]'
                      : 'bg-[rgba(0,0,0,0.06)] text-[var(--color-text-muted)]'
                  }`}>
                    {formatChatTime(msg.timestamp)}
                  </span>
                </div>
              )}
              {renderMessage(msg, showAvatar, isLastAndGenerating)}
            </div>
          )
        })}

        {/* Streaming indicator - avatar is already in the bubble via renderMessage */}
      </div>

      {/* Input bar */}
      <div
        className={`relative z-20 mx-3 mb-3 flex items-center gap-3 px-4 py-3 backdrop-blur-[24px] rounded-[28px] border ${
          isDark
            ? 'bg-[rgba(26,26,46,0.7)] border-[rgba(255,255,255,0.08)] shadow-[var(--shadow-sheet)]'
            : 'bg-[var(--color-glass-75)] border-[var(--color-border-glass)] shadow-[var(--shadow-sheet)]'
        }`}
        style={{ marginBottom: 'calc(16px + var(--safe-bottom))' }}
      >
        {/* Interrupt button when streaming, add button otherwise */}
        {isStreaming ? (
          <button
            onClick={handleInterrupt}
            className="w-[40px] h-[40px] flex items-center justify-center shrink-0"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="var(--color-primary)">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            className="w-[40px] h-[40px] flex items-center justify-center shrink-0 touch-none select-none"
            onPointerDown={handleMicPointerDown}
            onPointerMove={handleMicPointerMove}
            onPointerUp={handleMicPointerUp}
            onPointerCancel={handleMicPointerUp}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={isStreaming ? (isDark ? '#444' : '#DDD') : (isDark ? '#999' : '#888')} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="2" width="6" height="11" rx="3" />
              <path d="M5 10a7 7 0 0 0 14 0" />
              <line x1="12" y1="19" x2="12" y2="22" />
              <line x1="8" y1="22" x2="16" y2="22" />
            </svg>
          </button>
        )}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={isStreaming ? '正在回复中…' : `想和${profile.shortName}说点什么…`}
          disabled={isStreaming}
          className={`flex-1 bg-transparent outline-none text-[16px] ${
            isDark ? 'text-[#EFE7DD] placeholder-[rgba(228,228,231,0.3)]' : 'text-[var(--color-ink)] placeholder-[var(--color-text-placeholder)]'
          }`}
        />
        <button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          className={`w-[44px] h-[44px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] flex items-center justify-center shrink-0 shadow-[var(--shadow-send)] active:scale-90 transition-transform ${
            isStreaming || !input.trim() ? 'opacity-50' : ''
          }`}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>

      {/* Insufficient credits dialog */}
      <Dialog open={!!insufficientCredits} onClose={clearInsufficientCredits} title="yuoyuo币不足">
        <p className="text-[14px] text-[var(--color-text-secondary)] mb-4">
          你的 yuoyuo币不足以继续对话。前往钱包充值后继续。
        </p>
        <div className="flex gap-3">
          <Button variant="ghost" size="sm" onClick={clearInsufficientCredits} className="flex-1">
            取消
          </Button>
          <Button variant="primary" size="sm" onClick={() => { clearInsufficientCredits(); navigate('/wallet') }} className="flex-1">
            去充值
          </Button>
        </div>
      </Dialog>

      {/* Model requires higher tier */}
      <Dialog open={!!modelForbidden} onClose={clearModelForbidden} title="该模型需会员">
        <p className="text-[14px] text-[var(--color-text-secondary)] mb-4">
          当前等级暂不能使用该模型，升级会员即可解锁更强的对话模型。
        </p>
        <div className="flex gap-3">
          <Button variant="ghost" size="sm" onClick={clearModelForbidden} className="flex-1">
            取消
          </Button>
          <Button variant="primary" size="sm" onClick={() => { clearModelForbidden(); navigate('/membership') }} className="flex-1">
            去升级
          </Button>
        </div>
      </Dialog>

      {/* Voice recording overlay (WeChat-style) */}
      {isRecording && (
        <VoiceRecordingOverlay
          durationMs={0}
          willCancel={willCancel}
          cancelZoneRef={cancelZoneRef}
        />
      )}

      {/* Short toast for voice recording feedback */}
      {recordingToast && (
        <div className="fixed bottom-36 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-xl text-white text-[13px] bg-[rgba(0,0,0,0.65)] backdrop-blur pointer-events-none">
          {recordingToast}
        </div>
      )}
    </div>
  )
}
