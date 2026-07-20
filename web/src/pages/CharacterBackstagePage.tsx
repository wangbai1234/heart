import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { useThemeStore } from '../stores/themeStore'
import { useMembershipStore } from '../stores/membershipStore'
import { resolveCharacterProfile } from '../data/uiContent'
import { useCharactersStore } from '../stores/charactersStore'
import { Dialog } from '../components/ui/Dialog'
import { Switch } from '../components/ui/Switch'
import { getCharacterSettings, updateCharacterSettings, getCharacterVoice, clearCharacterConversations, setCharacterVoiceProvider } from '../services/api'
import { useToastStore } from '../stores/toastStore'

// 文字聊天三档 → LLM 模型。私密/情感为会员模型，按 membership 权益门控。
const TEXT_TIERS = [
  { key: 'daily', model: 'deepseek', title: '日常陪伴', sub: '无限畅聊，适合日常交流与轻松陪伴' },
  { key: 'private', model: 'grok', title: '私密陪伴', sub: '更懂你的私人想法，支持长期记忆交流' },
  { key: 'emotional', model: 'claude', title: '情感陪伴', sub: '更细腻自然的表达，真人陪伴你，支持长期记忆交流' },
] as const

// 语音聊天两档 → TTS provider（角色配置的 voice_provider）。真人语音=Fish 为会员能力。
const VOICE_TIERS = [
  { key: 'daily', provider: 'mimo', title: '日常语音', sub: '清晰自然，满足日常聊天需求' },
  { key: 'real', provider: 'fish', title: '真人语音', sub: '更有情绪和温度，带来真人般交流体验' },
] as const

export function CharacterBackstagePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const currentCharacterId = useAppStore((s) => s.currentCharacterId)
  const voiceChatEnabled = useAppStore((s) => s.voiceChatEnabled[currentCharacterId] ?? false)
  const setVoiceChatEnabled = useAppStore((s) => s.setVoiceChatEnabled)
  const clearThread = useChatStore((s) => s.clearThread)
  const clearMessages = useChatStore((s) => s.clearMessages)
  const currentCharacter = useCharactersStore((s) => s.characters.find((c) => c.id === currentCharacterId))
  const displayName = currentCharacter?.display_name
  const avatarUrl = currentCharacter?.avatar_url
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [hasVoice, setHasVoice] = useState(
    currentCharacter?.has_voice ?? false
  )
  const [voiceConfigured, setVoiceConfigured] = useState(false)
  // Providers this character has a ready voice for + the user's current pick.
  const [availableProviders, setAvailableProviders] = useState<string[]>([])
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [switchingProvider, setSwitchingProvider] = useState(false)

  // 文字模型（后台设定，聊天页据此发送）+ 会员权益
  const chatModel = useAppStore((s) => s.chatModel[currentCharacterId] ?? 'deepseek')
  const setChatModel = useAppStore((s) => s.setChatModel)
  const allowedModels = useMembershipStore((s) => s.entitlements.models)
  const allowedTts = useMembershipStore((s) => s.entitlements.tts)
  const membershipLoaded = useMembershipStore((s) => s.loaded)
  const refreshMembership = useMembershipStore((s) => s.refresh)

  const profile = resolveCharacterProfile(currentCharacterId, displayName, avatarUrl)

  // Hydrate voice setting + voice config from backend on mount
  useEffect(() => {
    if (!membershipLoaded) refreshMembership()

    getCharacterSettings(currentCharacterId)
      .then((res) => {
        setVoiceChatEnabled(currentCharacterId, res.voice_enabled)
      })
      .catch(() => { /* keep local value */ })

    getCharacterVoice(currentCharacterId)
      .then((res) => {
        setHasVoice(res.has_voice ?? res.clone_status === 'ready')
        setVoiceConfigured(res.configured ?? false)
        setAvailableProviders(res.available_providers ?? [])
        // Fall back to voice_provider (primary row) when the per-user selection
        // isn't set yet, then default to mimo.
        setSelectedProvider(res.selected_provider ?? res.voice_provider ?? 'mimo')
      })
      .catch(() => { /* keep local value */ })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCharacterId])

  // 文字档位门控：DeepSeek 永久免费；其余看会员权益。
  const isModelAllowed = (model: string) => model === 'deepseek' || allowedModels.includes(model)
  // 语音档位门控：MiMo 通用；Fish 看会员权益。
  const isVoiceAllowed = (provider: string) => provider === 'mimo' || allowedTts.includes(provider)
  // 当前使用中的语音档位（mimo→日常 / fish→真人；其它 provider 不高亮）。
  const currentVoiceKey =
    selectedProvider === 'fish' ? 'real' : selectedProvider === 'mimo' ? 'daily' : null

  const handleTextTier = (model: string) => {
    if (!isModelAllowed(model)) {
      navigate('/membership')
      return
    }
    setChatModel(currentCharacterId, model)
  }

  const handleVoiceTier = async (tier: (typeof VOICE_TIERS)[number]) => {
    if (!voiceChatEnabled || switchingProvider) return // greyed until voice is on
    if (!isVoiceAllowed(tier.provider)) {
      navigate('/membership') // 真人语音需会员
      return
    }
    if (currentVoiceKey === tier.key) return // already using this engine
    if (!availableProviders.includes(tier.provider)) {
      // This engine has no ready voice for the character — send them to config.
      useToastStore.getState().show('该语音尚未配置，请先配置音色', 'info')
      navigate(`/characters/new?voice=${currentCharacterId}&provider=${tier.provider}`)
      return
    }
    // Both clones pre-exist → instant per-user switch, no re-configuration.
    setSwitchingProvider(true)
    const prev = selectedProvider
    setSelectedProvider(tier.provider) // optimistic
    try {
      await setCharacterVoiceProvider(currentCharacterId, tier.provider as 'mimo' | 'fish')
      useToastStore.getState().show(`已切换到${tier.title}`, 'success')
    } catch (err: any) {
      setSelectedProvider(prev) // rollback
      if (err?.status === 403) navigate('/membership')
      else useToastStore.getState().show('切换失败，请稍后重试', 'error')
    } finally {
      setSwitchingProvider(false)
    }
  }

  const handleVoiceToggle = async (value: boolean) => {
    // Reason we need a toast here: previous UX silently navigated the user
    // to /characters/new when hasVoice=false. Users read that as "the switch
    // was flipped on and I got taken to a random page" — and then chatted
    // expecting voice replies, only to see nothing. Now we announce the
    // dependency explicitly (TEST_REPORT_20260712 §4.5, BUG-2).
    if (value && !hasVoice) {
      useToastStore.getState().show('该角色暂未配置音色，请先选择一个音色', 'info')
      navigate(`/characters/new?voice=${currentCharacterId}`)
      return
    }
    setVoiceChatEnabled(currentCharacterId, value)
    try {
      await updateCharacterSettings(currentCharacterId, value)
    } catch (err: any) {
      // 409 = has_voice denormalized flag was stale on the server side and
      // the character actually has no voice row. Same fix as above.
      if (err?.status === 409) {
        useToastStore.getState().show('请先为该角色配置音色，才能开启语音聊天', 'info')
        setVoiceChatEnabled(currentCharacterId, false)
        navigate(`/characters/new?voice=${currentCharacterId}`)
        return
      }
      // Reconcile against the server's real state before declaring failure. A
      // transient network blip can reject the response even though the write
      // actually applied; blindly rolling the switch back then leaves a
      // misleading "切换失败" + wrong toggle position. Only surface the error if
      // the server confirms the value did not change.
      try {
        const actual = await getCharacterSettings(currentCharacterId)
        setVoiceChatEnabled(currentCharacterId, actual.voice_enabled)
        if (actual.voice_enabled !== value) {
          useToastStore.getState().show('语音开关切换失败，请稍后重试', 'error')
        }
      } catch {
        setVoiceChatEnabled(currentCharacterId, !value)
        useToastStore.getState().show('语音开关切换失败，请稍后重试', 'error')
      }
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

  const handleClearThread = async () => {
    try {
      await clearCharacterConversations(currentCharacterId)
    } catch {
      useToastStore.getState().show('清空失败，请重试', 'error')
      setConfirmOpen(false)
      return
    }
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
          {/* 文字聊天：三档语义化陪伴 → 三个 LLM 模型 */}
          <section className={`rounded-[34px] border px-6 py-7 backdrop-blur-[24px] ${cardClassName}`}>
            <h2 className={`mb-1 text-[18px] font-semibold tracking-[-0.02em] ${resolvedTheme === 'dark' ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
              文字聊天
            </h2>
            <p className={`mb-4 text-[13px] leading-[1.5] ${subtleTextClassName}`}>选择陪伴风格，进阶风格按会员解锁</p>
            <div className="space-y-2.5">
              {TEXT_TIERS.map((t) => {
                const allowed = isModelAllowed(t.model)
                const selected = chatModel === t.model
                return (
                  <button
                    key={t.key}
                    onClick={() => handleTextTier(t.model)}
                    className={`w-full rounded-[18px] border px-4 py-3.5 text-left transition-transform active:scale-[0.99] ${
                      resolvedTheme === 'dark' ? 'bg-[rgba(255,255,255,0.05)]' : 'bg-[rgba(255,255,255,0.5)]'
                    }`}
                    style={{ borderColor: selected ? '#FF8FAB' : (resolvedTheme === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.4)') }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        {!allowed && (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={resolvedTheme === 'dark' ? 'rgba(236,233,244,0.5)' : 'rgba(47,54,74,0.42)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        )}
                        <span className={`text-[15px] font-medium ${allowed ? (resolvedTheme === 'dark' ? 'text-[#F3EFF8]' : 'text-[#2D3248]') : subtleTextClassName}`}>{t.title}</span>
                      </div>
                      {selected ? (
                        <span className="text-[12px] font-semibold text-[#FF7DA1]">使用中</span>
                      ) : allowed ? null : (
                        <span className="text-[12px] font-medium text-[#FF7DA1]">升级会员解锁</span>
                      )}
                    </div>
                    <p className={`mt-1 text-[12.5px] leading-[1.5] ${subtleTextClassName}`}>{t.sub}</p>
                  </button>
                )
              })}
            </div>
          </section>

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
                  {hasVoice ? '是否开启语音聊天' : '配置音色'}
                </h2>
                <p className={`max-w-[210px] text-[14px] leading-[1.55] ${subtleTextClassName}`}>
                  {hasVoice
                    ? '开启后 AI 回复将转为语音，会额外消耗 yuoyuo币'
                    : '先选择预设音色或克隆专属音色，才能开启语音聊天'}
                </p>
              </div>
              <div className="shrink-0">
                {hasVoice ? (
                  <Switch checked={voiceChatEnabled} onChange={handleVoiceToggle} />
                ) : (
                  <button
                    onClick={() => navigate(`/characters/new?voice=${currentCharacterId}`)}
                    className="rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] px-4 py-2 text-[13px] font-semibold text-white"
                  >
                    去配置
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* 语音聊天两档：日常语音(MiMo)/真人语音(Fish)。未配置音色则整段隐藏；
              未开启语音则置灰；真人语音对免费用户锁定。 */}
          {voiceConfigured && (
            <section className={`rounded-[34px] border px-6 py-7 backdrop-blur-[24px] ${cardClassName}`}>
              <h2 className={`mb-1 text-[18px] font-semibold tracking-[-0.02em] ${resolvedTheme === 'dark' ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
                语音聊天
              </h2>
              <p className={`mb-4 text-[13px] leading-[1.5] ${subtleTextClassName}`}>
                {voiceChatEnabled ? '选择语音音质，真人语音需会员' : '先开启上方语音聊天开关'}
              </p>
              <div className="space-y-2.5">
                {VOICE_TIERS.map((t) => {
                  const allowed = isVoiceAllowed(t.provider)
                  const active = currentVoiceKey === t.key
                  const disabled = !voiceChatEnabled || switchingProvider
                  return (
                    <button
                      key={t.key}
                      onClick={() => handleVoiceTier(t)}
                      disabled={disabled}
                      className={`w-full rounded-[18px] border px-4 py-3.5 text-left transition-transform active:scale-[0.99] ${
                        disabled ? 'opacity-45' : ''
                      } ${resolvedTheme === 'dark' ? 'bg-[rgba(255,255,255,0.05)]' : 'bg-[rgba(255,255,255,0.5)]'}`}
                      style={{ borderColor: active && !disabled ? '#FF8FAB' : (resolvedTheme === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.4)') }}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          {!allowed && (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={resolvedTheme === 'dark' ? 'rgba(236,233,244,0.5)' : 'rgba(47,54,74,0.42)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <rect x="3" y="11" width="18" height="11" rx="2" />
                              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                            </svg>
                          )}
                          <span className={`text-[15px] font-medium ${resolvedTheme === 'dark' ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>{t.title}</span>
                        </div>
                        {active && !disabled ? (
                          <span className="text-[12px] font-semibold text-[#FF7DA1]">使用中</span>
                        ) : !allowed ? (
                          <span className="text-[12px] font-medium text-[#FF7DA1]">升级会员解锁</span>
                        ) : null}
                      </div>
                      <p className={`mt-1 text-[12.5px] leading-[1.5] ${subtleTextClassName}`}>{t.sub}</p>
                    </button>
                  )
                })}
              </div>
            </section>
          )}

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
                  只在当前设备隐藏聊天页面内容，服务端记录和记忆都会保留
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
          当前设备上的聊天页面会立即清空，服务端聊天记录和角色记忆不会删除。
        </Dialog>
      </div>
    </div>
  )
}
