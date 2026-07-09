import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { Toast } from '../components/ui/Toast'
import { TabBar } from '../components/ui/TabBar'
import { CHARACTER_PROFILES, resolveCharacterProfile, type CharacterProfile } from '../data/uiContent'
import { useCharactersStore } from '../stores/charactersStore'
import { useState } from 'react'

export function CharacterPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const { setCharacter } = useAppStore()
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const serverCharacters = useCharactersStore((s) => s.characters)
  const [toast, setToast] = useState({ visible: false, message: '' })

  const characters: CharacterProfile[] =
    serverCharacters.length > 0
      ? serverCharacters.map((c) => resolveCharacterProfile(c.id, c.display_name, c.avatar_url))
      : Object.values(CHARACTER_PROFILES)

  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  const handleSelectCharacter = (charId: string) => {
    setCharacter(charId)
    setActiveCharacter(charId)
    navigate(`/chat/${charId}`)
  }

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {/* Background */}
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Status bar */}
        <div style={{ height: 'var(--safe-top)' }} />

        {/* Navigation bar */}
        <div className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
          <button onClick={() => navigate('/home')} className="w-[44px] h-[44px] flex items-center justify-center">
            <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="10,2 2,10 10,18" />
            </svg>
          </button>
          <span className="text-[17px] font-medium text-[var(--color-ink)]">选一个陪伴你的人</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/my-characters')}
              className="h-[34px] px-3 rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] text-[13px] text-[var(--color-primary)] font-medium active:scale-[0.96] transition-transform"
            >
              我的角色
            </button>
            <button
              onClick={() => navigate('/characters/new')}
              className="w-[34px] h-[34px] rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] flex items-center justify-center text-[var(--color-primary)] active:scale-[0.96] transition-transform"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="7" y1="1" x2="7" y2="13" />
                <line x1="1" y1="7" x2="13" y2="7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Character Cards */}
        <div className="relative z-10 flex-1 overflow-y-auto px-4 pt-3 pb-[80px]">
          <div className="flex flex-col gap-3">
            {characters.map((char) => (
              <button
                key={char.id}
                onClick={() => handleSelectCharacter(char.id)}
                className="relative w-full rounded-[24px] p-5 text-left active:scale-[0.98] transition-all duration-200 border bg-[var(--color-glass-55)] backdrop-blur-[16px] border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]"
              >
                <div className="flex gap-4">
                  {/* Avatar */}
                  <div className="relative shrink-0">
                    <div
                      className="w-[80px] h-[80px] rounded-full p-[3px]"
                      style={{ background: `linear-gradient(135deg, ${char.tagBg}, transparent)` }}
                    >
                      <img src={char.avatar} alt={char.name} className="w-full h-full rounded-full object-cover" />
                    </div>
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[20px] font-bold text-[var(--color-ink)]">{char.name}</span>
                      <span
                        className="text-[12px] font-medium px-2 py-[3px] rounded-[12px]"
                        style={{ color: char.tagColor, backgroundColor: char.tagBg }}
                      >
                        {char.tag}
                      </span>
                    </div>
                    <p className="text-[13px] text-[var(--color-text-secondary)]">
                      {char.summary}
                    </p>
                  </div>
                  {/* Chevron */}
                  <div className="flex items-center shrink-0 pl-2">
                    <svg width="8" height="14" viewBox="0 0 8 14" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="1,1 7,7 1,13" />
                    </svg>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* TabBar */}
        <TabBar />
      </div>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </div>
  )
}
