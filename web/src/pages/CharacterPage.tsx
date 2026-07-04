import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { Toast } from '../components/ui/Toast'
import { TabBar } from '../components/ui/TabBar'
import { CHARACTER_PROFILES } from '../data/uiContent'

export function CharacterPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const { currentCharacterId, setCharacter } = useAppStore()
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const [selected, setSelected] = useState(currentCharacterId)
  const [toast, setToast] = useState({ visible: false, message: '' })

  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  const handleConfirm = () => {
    setCharacter(selected as 'rin' | 'dorothy')
    setActiveCharacter(selected as 'rin' | 'dorothy')
    setToast({ visible: true, message: '已切换角色，去查看消息' })
    setTimeout(() => navigate(`/chat/${selected}`), 700)
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
          <div className="w-[44px]" />
        </div>

        {/* Character Cards */}
        <div className="relative z-10 flex-1 overflow-y-auto px-4 pt-3 pb-[120px]">
          <div className="flex flex-col gap-3">
            {(Object.values(CHARACTER_PROFILES)).map((char) => {
              const isSelected = selected === char.id
              return (
                <button
                  key={char.id}
                  onClick={() => setSelected(char.id)}
                  className={`relative w-full rounded-[24px] p-5 text-left active:scale-[0.98] transition-all duration-200 border ${
                    isSelected
                      ? 'bg-[var(--color-glass-75)] backdrop-blur-[20px] border-[rgba(255,183,197,0.40)] shadow-[var(--shadow-card)]'
                      : 'bg-[var(--color-glass-55)] backdrop-blur-[16px] border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]'
                  }`}
                >
                  <div className="flex gap-4">
                    {/* Avatar */}
                    <div className="relative shrink-0">
                      <div
                        className="w-[80px] h-[80px] rounded-full p-[3px]"
                        style={{ background: `linear-gradient(135deg, ${char.id === 'rin' ? 'rgba(200,182,255,0.5)' : 'rgba(167,199,231,0.5)'}, transparent)` }}
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
                  </div>

                  {/* Check indicator */}
                  {isSelected && (
                    <div className="absolute top-5 right-5">
                      <div className="w-[36px] h-[36px] rounded-full bg-[var(--color-primary)] flex items-center justify-center shadow-[0_4px_12px_rgba(255,183,197,0.4)]">
                        <svg width="16" height="12" viewBox="0 0 16 12" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="2,6 6,10 14,2" />
                        </svg>
                      </div>
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Floating Bottom CTA */}
        <div
          className="absolute bottom-0 left-0 right-0 z-20 px-5"
          style={{ paddingBottom: 'calc(95px + var(--safe-bottom))' }}
        >
          <button
            onClick={handleConfirm}
            className="w-full py-4 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[17px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.35)] active:scale-[0.97] transition-transform"
          >
            确认选择
          </button>
        </div>

        {/* TabBar */}
        <TabBar />
      </div>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </div>
  )
}
