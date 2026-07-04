import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { useThemeStore } from '../stores/themeStore'
import { CHARACTER_PROFILES } from '../data/uiContent'
import { Dialog } from '../components/ui/Dialog'
import { Switch } from '../components/ui/Switch'
import { getCharacterSettings, updateCharacterSettings } from '../services/api'

export function CharacterBackstagePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const currentCharacterId = useAppStore((s) => s.currentCharacterId)
  const voiceChatEnabled = useAppStore((s) => s.voiceChatEnabled[currentCharacterId])
  const setVoiceChatEnabled = useAppStore((s) => s.setVoiceChatEnabled)
  const clearThread = useChatStore((s) => s.clearThread)
  const clearMessages = useChatStore((s) => s.clearMessages)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const profile = CHARACTER_PROFILES[currentCharacterId]

  // Hydrate voice setting from backend on mount
  useEffect(() => {
    getCharacterSettings(currentCharacterId)
      .then((res) => {
        setVoiceChatEnabled(currentCharacterId, res.voice_enabled)
      })
      .catch(() => { /* keep local value */ })
  }, [currentCharacterId])

  const handleVoiceToggle = async (value: boolean) => {
    setVoiceChatEnabled(currentCharacterId, value)
    try {
      await updateCharacterSettings(currentCharacterId, value)
    } catch {
      // Revert on failure
      setVoiceChatEnabled(currentCharacterId, !value)
    }
  }
  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  const cardClassName = resolvedTheme === 'dark'
    ? 'bg-[rgba(29,31,52,0.48)] border-[rgba(255,255,255,0.08)] shadow-[0_24px_60px_rgba(4,7,24,0.2)]'
    : 'bg-[rgba(255,255,255,0.48)] border-[rgba(255,255,255,0.34)] shadow-[0_24px_60px_rgba(255,183,197,0.12)]'

  const iconBubbleClassName = resolvedTheme === 'dark'
    ? 'bg-[rgba(255,183,197,0.12)]'
    : 'bg-[rgba(255,183,197,0.16)]'

  const subtleTextClassName = resolvedTheme === 'dark'
    ? 'text-[rgba(236,233,244,0.68)]'
    : 'text-[rgba(47,54,74,0.54)]'

  const handleClearThread = () => {
    clearThread(currentCharacterId)
    clearMessages(currentCharacterId)
    setConfirmOpen(false)
    navigate('/chat')
  }

  return (
    <div className="relative min-h-full overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 h-full w-full object-cover" />
      <div
        className={resolvedTheme === 'dark'
          ? 'absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(111,120,178,0.18),transparent_46%),linear-gradient(180deg,rgba(11,14,28,0.12),rgba(11,14,28,0.22))]'
          : 'absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(216,202,255,0.24),transparent_48%),linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.18))]'
        }
      />

      <div className="relative z-10 flex min-h-full flex-col px-6 pb-10 pt-6">
        <div style={{ height: 'var(--safe-top)' }} />

        <button
          onClick={() => navigate(`/chat/${currentCharacterId}`)}
          className={`mb-14 flex h-[52px] w-[52px] items-center justify-center rounded-full backdrop-blur-[18px] border ${
            resolvedTheme === 'dark'
              ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.08)]'
              : 'bg-[rgba(255,255,255,0.42)] border-[rgba(255,255,255,0.3)]'
          }`}
          aria-label="返回聊天"
        >
          <svg width="14" height="24" viewBox="0 0 14 24" fill="none" stroke={resolvedTheme === 'dark' ? '#ECE9F4' : '#30344A'} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="11,3 3,12 11,21" />
          </svg>
        </button>

        <section className="mb-14 flex items-center gap-5 px-1">
          <div className={`h-[106px] w-[106px] overflow-hidden rounded-full border-[4px] ${
            resolvedTheme === 'dark'
              ? 'border-[rgba(255,255,255,0.24)] shadow-[0_18px_32px_rgba(6,8,20,0.28)]'
              : 'border-[rgba(255,255,255,0.84)] shadow-[0_18px_32px_rgba(255,183,197,0.18)]'
          }`}>
            <img src={profile.avatar} alt={profile.name} className="h-full w-full object-cover" />
          </div>
          <div className="min-w-0">
            <h1 className={`mb-2 text-[34px] font-semibold tracking-[-0.03em] ${resolvedTheme === 'dark' ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
              {profile.shortName}
            </h1>
            <div className="flex items-center gap-3">
              <span className="h-4 w-4 rounded-full bg-[#67C5F0]" />
              <span className={`text-[18px] font-medium ${subtleTextClassName}`}>{profile.statusLabel}</span>
            </div>
          </div>
        </section>

        <div className="space-y-9">
          <section className={`rounded-[34px] border px-6 py-8 backdrop-blur-[24px] ${cardClassName}`}>
            <div className="flex items-center gap-4">
              <div className={`flex h-[56px] w-[56px] items-center justify-center rounded-full ${iconBubbleClassName}`}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#FF7DA1" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 16a4 4 0 0 0 4-4V8a4 4 0 1 0-8 0v4a4 4 0 0 0 4 4Z" />
                  <path d="M19 11.5a7 7 0 0 1-14 0" />
                  <path d="M12 18.5v3" />
                </svg>
              </div>
              <div className="min-w-0 flex-1">
                <h2 className={`mb-2 text-[18px] leading-[1.22] font-semibold tracking-[-0.02em] ${resolvedTheme === 'dark' ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
                  是否开启语音聊天
                </h2>
                <p className={`max-w-[210px] text-[14px] leading-[1.55] ${subtleTextClassName}`}>
                  开启后 AI 回复将转为语音，语音回复消耗 5 积分/条
                </p>
              </div>
              <div className="shrink-0">
                <Switch checked={voiceChatEnabled} onChange={handleVoiceToggle} />
              </div>
            </div>
          </section>

          <section
            className={`rounded-[34px] border px-6 py-8 backdrop-blur-[24px] ${cardClassName}`}
            role="button"
            tabIndex={0}
            onClick={() => setConfirmOpen(true)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                setConfirmOpen(true)
              }
            }}
          >
            <div className="flex items-center gap-4">
              <div className={`flex h-[56px] w-[56px] items-center justify-center rounded-full ${iconBubbleClassName}`}>
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FF7DA1" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 6h18" />
                  <path d="M8 6V4h8v2" />
                  <path d="M19 6l-1 14H6L5 6" />
                  <path d="M10 11v5" />
                  <path d="M14 11v5" />
                </svg>
              </div>
              <div className="min-w-0 flex-1">
                <h2 className={`mb-2 text-[18px] leading-[1.22] font-semibold tracking-[-0.02em] ${resolvedTheme === 'dark' ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
                  清空聊天记录
                </h2>
                <p className={`max-w-[210px] text-[14px] leading-[1.58] ${subtleTextClassName}`}>
                  只清空页面，记忆数据不会删除，需删除请移步设置页面
                </p>
              </div>
              <div className="shrink-0 pr-2">
                <svg width="18" height="30" viewBox="0 0 18 30" fill="none" stroke={resolvedTheme === 'dark' ? 'rgba(236,233,244,0.46)' : 'rgba(47,54,74,0.34)'} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="4,4 14,15 4,26" />
                </svg>
              </div>
            </div>
          </section>
        </div>

        <Dialog
          open={confirmOpen}
          onClose={() => setConfirmOpen(false)}
          title="确认清空聊天记录？"
          actions={(
            <>
              <button
                onClick={() => setConfirmOpen(false)}
                className={`flex-1 rounded-full px-4 py-3 text-[15px] font-medium ${
                  resolvedTheme === 'dark'
                    ? 'bg-[rgba(255,255,255,0.06)] text-[#ECE9F4]'
                    : 'bg-[rgba(255,255,255,0.75)] text-[#30344A]'
                }`}
              >
                取消
              </button>
              <button
                onClick={handleClearThread}
                className="flex-1 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] px-4 py-3 text-[15px] font-semibold text-white"
              >
                清空
              </button>
            </>
          )}
        >
          页面消息会被立即清空，但角色长期记忆不会被删除。
        </Dialog>
      </div>
    </div>
  )
}
