import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { useChatStore, type Message } from '../stores/chatStore'
import { useAuthStore } from '../stores/authStore'
import { CHARACTER_PROFILES, shouldShowTimestamp, formatChatTime, type CharacterId } from '../data/uiContent'
import { useWebSocket } from '../hooks/useWebSocket'
import { getChatHistory } from '../services/api'
import { BreathingDots } from './ui/BreathingDots'
import { Dialog } from './ui/Dialog'
import { Button } from './ui/Button'
import { Avatar } from './ui/Avatar'
import VoiceMessageBubble from './VoiceMessageBubble'

interface ConversationChatPageProps {
  isDark: boolean
}

export function ConversationChatPage({ isDark }: ConversationChatPageProps) {
  const navigate = useNavigate()
  const params = useParams<{ characterId?: string }>()
  const [input, setInput] = useState('')
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const storedCharacterId = useAppStore((s) => s.currentCharacterId)
  const setCharacter = useAppStore((s) => s.setCharacter)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const userAvatar = useAuthStore((s) => s.user?.avatar_url ?? null)
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)

  const routeCharacterId = params.characterId
  const isValidCharacterId = routeCharacterId === 'rin' || routeCharacterId === 'dorothy'
  const currentCharacterId = (isValidCharacterId ? routeCharacterId : storedCharacterId) as CharacterId

  const messages = useChatStore((s) => s.messages[currentCharacterId as CharacterId] ?? [])
  const isStreaming = useChatStore((s) => s.isStreaming)
  const isPlaying = useChatStore((s) => s.isPlaying)
  const addMessage = useChatStore((s) => s.addMessage)
  const setCharacterId = useChatStore((s) => s.setCharacterId)
  const appendMessage = useChatStore((s) => s.appendMessage)
  const insufficientCredits = useChatStore((s) => s.insufficientCredits)
  const clearInsufficientCredits = useChatStore((s) => s.clearInsufficientCredits)

  const { sendMessage, interrupt } = useWebSocket()

  const profile = CHARACTER_PROFILES[currentCharacterId]
  const pageBg = isDark
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  // Set character ID in chat store
  useEffect(() => {
    if (routeCharacterId && !isValidCharacterId) {
      navigate('/chat', { replace: true })
      return
    }
    if (currentCharacterId !== storedCharacterId) {
      setCharacter(currentCharacterId)
    }
    setActiveCharacter(currentCharacterId)
    setCharacterId(currentCharacterId)
  }, [currentCharacterId, isValidCharacterId, navigate, routeCharacterId, setActiveCharacter, setCharacter, setCharacterId, storedCharacterId])

  // Load chat history from API on mount / character change
  const prevCharRef = useRef(currentCharacterId)
  useEffect(() => {
    if (!isAuthenticated()) return
    setHistoryLoaded(false)
    prevCharRef.current = currentCharacterId

    const existing = useChatStore.getState().messages[currentCharacterId] ?? []
    if (existing.length > 0) {
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
            kind: item.modality === 'voice' ? 'voice' : 'text',
            audioData: item.audio_url ?? undefined,
            audioDuration: item.audio_duration_ms ?? undefined,
          })
        }
        if (reversed.length > 0) {
          const last = reversed[reversed.length - 1]
          appendMessage(currentCharacterId, {
            id: last.id,
            role: last.role as 'assistant' | 'user',
            content: last.content,
            timestamp: new Date(last.created_at).getTime(),
            kind: last.modality === 'voice' ? 'voice' : 'text',
          })
        }
        setHistoryLoaded(true)
      })
      .catch(() => {
        setHistoryLoaded(true)
      })
  }, [currentCharacterId, isAuthenticated])

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

  // Render a single message bubble
  const renderMessage = (msg: Message, showAvatar: boolean) => {
    const isAI = msg.role === 'assistant'
    const avatar = isAI ? profile.avatar : userAvatar

    // Voice message with audio
    if (msg.kind === 'voice' && msg.audioData) {
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div
            className={`max-w-[320px] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] p-3 ${
              isDark
                ? 'bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.08)] shadow-[0_4px_12px_rgba(0,0,0,0.12)]'
                : 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]'
            }`}
          >
            <VoiceMessageBubble
              audioData={msg.audioData}
              duration={msg.audioDuration ?? 3000}
              format={msg.audioFormat ?? 'wav'}
              isDark={isDark}
            />
            {msg.content && (
              <p className={`text-[13px] mt-2 ${isDark ? 'text-[rgba(228,228,231,0.5)]' : 'text-[var(--color-text-secondary)]'}`}>
                {msg.content}
              </p>
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
          className={`max-w-[67%] px-4 py-[14px] ${
            isAI
              ? isDark
                ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] text-[#EFE7DD] border border-[rgba(255,255,255,0.06)]'
                : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] text-[var(--color-ink)] border border-[var(--color-border-glass)]'
              : isDark
                ? 'bg-gradient-to-br from-[#4A5B8F] to-[#6C7DB5] rounded-[6px_20px_20px_20px] text-[#EFE7DD]'
                : 'bg-gradient-to-br from-[#A7C7E7] to-[#BFD7EE] rounded-[6px_20px_20px_20px] text-white'
          }`}
        >
          <p className="text-[16px] leading-[1.6]">{msg.content}</p>
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

          // Skip empty message bubbles during streaming (turn_start without text_delta yet)
          const isLatestEmpty = msg.content === '' && isStreaming && index === messages.length - 1
          if (isLatestEmpty) return null

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
              {renderMessage(msg, showAvatar)}
            </div>
          )
        })}

        {/* Streaming indicator */}
        {isStreaming && (
          <div className={`flex items-end gap-2 self-start`}>
            <Avatar src={profile.avatar} size={40} className="shrink-0 mt-[2px]" />
            <div
              className={`backdrop-blur-[16px] rounded-[20px_20px_20px_6px] px-5 py-3 ${
                isDark
                  ? 'bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.06)]'
                  : 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)]'
              }`}
            >
              <BreathingDots />
            </div>
          </div>
        )}
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
          <button className="w-[40px] h-[40px] flex items-center justify-center shrink-0">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={isDark ? '#666' : '#BBBBBB'} strokeWidth="2" strokeLinecap="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        )}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={isStreaming ? '正在回复中…' : `想和${profile.shortName}说点什么…`}
          disabled={isStreaming}
          className={`flex-1 bg-transparent outline-none text-[15px] ${
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
      <Dialog open={!!insufficientCredits} onClose={clearInsufficientCredits} title="积分不足">
        <p className="text-[14px] text-[var(--color-text-secondary)] mb-4">
          你的积分不足以继续对话。请兑换积分后继续。
        </p>
        <div className="flex gap-3">
          <Button variant="ghost" size="sm" onClick={clearInsufficientCredits} className="flex-1">
            取消
          </Button>
          <Button variant="primary" size="sm" onClick={() => { clearInsufficientCredits(); navigate('/redeem') }} className="flex-1">
            去兑换
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
