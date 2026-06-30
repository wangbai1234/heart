import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChatBubble } from '../components/ui/ChatBubble'
import { BreathingDots } from '../components/ui/BreathingDots'

const WAVEFORM_HEIGHTS = [8, 14, 10, 18, 12, 20, 8, 16, 10, 22, 14, 8, 18, 12, 20, 10, 16, 8, 14, 22]

const messages = [
  { id: 1, type: 'ai' as const, text: '早上好，昨晚睡得怎么样？' },
  { id: 2, type: 'user' as const, text: '做了个奇怪的梦。' },
  { id: 3, type: 'ai' as const, text: '讲给我听呀～我陪着你。' },
  { id: 4, type: 'ai' as const, text: '', isVoice: true, duration: '0:18' },
  { id: 5, type: 'user' as const, text: '好。' },
]

export function ChatLightPage() {
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [localMessages, setLocalMessages] = useState(messages)
  const [typing, setTyping] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [localMessages, typing])

  const handleSend = () => {
    if (!input.trim()) return
    const newMsg = { id: Date.now(), type: 'user' as const, text: input }
    setLocalMessages((prev) => [...prev, newMsg])
    setInput('')
    setTyping(true)
    setTimeout(() => {
      setTyping(false)
      setLocalMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, type: 'ai' as const, text: '我明白你的感受，让我陪你聊聊吧。' },
      ])
    }, 2000)
  }

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {/* Background */}
      <img
        src="/assets/backgrounds/亮色背景图.png"
        alt=""
        className="absolute inset-0 w-full h-full object-cover z-0"
      />

      {/* Header */}
      <header
        className="relative z-20 flex items-center gap-3 px-5 py-3 bg-[rgba(255,255,255,0.75)] backdrop-blur-[20px] rounded-b-[20px] shadow-[0_2px_12px_rgba(0,0,0,0.06)]"
        style={{ paddingTop: 'calc(var(--safe-top) + 12px)' }}
      >
        <button onClick={() => navigate('/home')} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <img src="/assets/characters/character_shenwuyue_avatar.png" alt="小屿" className="w-[40px] h-[40px] rounded-full object-cover" />
        <div className="flex-1">
          <p className="text-[17px] font-semibold text-[var(--color-ink)]">小屿</p>
          <div className="flex items-center gap-1">
            <div className="w-[6px] h-[6px] rounded-full bg-[var(--color-online)]" />
            <span className="text-[13px] text-[var(--color-text-secondary)]">温柔在线</span>
          </div>
        </div>
        <button className="w-[44px] h-[44px] flex items-center justify-center">
          <span className="text-[20px] text-[var(--color-ink)]">···</span>
        </button>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        <div className="text-center text-[12px] text-[var(--color-text-muted)] py-2">
          今天 · 上午 9:41
        </div>

        {localMessages.map((msg) => {
          if (msg.isVoice) {
            return (
              <div key={msg.id} className="self-start max-w-[320px] bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] shadow-[var(--shadow-soft)] p-4 border border-[var(--color-border-glass)]">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-[36px] h-[36px] rounded-full bg-[var(--color-glass-55)] flex items-center justify-center">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="var(--color-primary)">
                      <polygon points="5,3 19,12 5,21" />
                    </svg>
                  </div>
                  <div className="flex-1 flex items-end gap-[2px]">
                    {WAVEFORM_HEIGHTS.map((h, i) => (
                      <div
                        key={i}
                        className="w-[3px] rounded-full bg-gradient-to-t from-[var(--color-primary)] to-[var(--color-accent)]"
                        style={{ height: `${h}px` }}
                      />
                    ))}
                  </div>
                  <span className="text-[13px] text-[var(--color-text-muted)]">{msg.duration}</span>
                </div>
                <p className="text-center text-[12px] text-[var(--color-text-muted)]">AI 朗读 · 可点击播放</p>
              </div>
            )
          }
          return <ChatBubble key={msg.id} type={msg.type}>{msg.text}</ChatBubble>
        })}

        {typing && (
          <div className="self-start bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] shadow-[var(--shadow-soft)] px-5 py-3 border border-[var(--color-border-glass)]">
            <BreathingDots />
          </div>
        )}
      </div>

      {/* Composer */}
      <div
        className="relative z-20 mx-3 mb-3 flex items-center gap-3 px-4 py-3 bg-[var(--color-glass-75)] backdrop-blur-[24px] rounded-[28px] shadow-[var(--shadow-sheet)] border border-[var(--color-border-glass)]"
        style={{ marginBottom: 'calc(16px + var(--safe-bottom))' }}
      >
        <button className="w-[40px] h-[40px] flex items-center justify-center shrink-0">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#BBBBBB" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="想和小屿说点什么…"
          className="flex-1 bg-transparent outline-none text-[var(--color-ink)] placeholder-[var(--color-text-placeholder)] text-[15px]"
        />
        <button
          onClick={handleSend}
          className="w-[44px] h-[44px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] flex items-center justify-center shrink-0 shadow-[var(--shadow-send)] active:scale-90 transition-transform"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
