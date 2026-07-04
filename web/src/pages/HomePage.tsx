import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { Avatar } from '../components/ui/Avatar'
import { TabBar } from '../components/ui/TabBar'
import { Skeleton } from '../components/ui/Skeleton'
import { CHARACTER_PROFILES, formatConversationTime, getConversationPreview, getHeroBanner, type CharacterId } from '../data/uiContent'

export function HomePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const { userAvatar, setCharacter } = useAppStore()
  const threads = useChatStore((s) => s.threads)
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const loading = false
  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色背景图.png'
    : '/assets/backgrounds/亮色背景图.png'
  const heroBg = getHeroBanner(resolvedTheme)
  const recentConversations = (Object.keys(CHARACTER_PROFILES) as CharacterId[]).map((id) => {
    const profile = CHARACTER_PROFILES[id]
    const messages = threads[id]
    const lastMessage = messages[messages.length - 1]
    return {
      id,
      name: profile.name,
      avatar: profile.avatar,
      preview: getConversationPreview(messages),
      time: lastMessage ? formatConversationTime(lastMessage.timestamp) : '刚刚',
      unread: true,
    }
  })

  const openConversation = (id: CharacterId) => {
    setCharacter(id)
    setActiveCharacter(id)
    navigate('/chat')
  }

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Background */}
      <img
        src={pageBg}
        alt=""
        className="absolute inset-0 w-full h-full object-cover z-0"
      />

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Status bar spacer */}
        <div style={{ height: 'var(--safe-top)' }} />

        {/* Header */}
        <div className="flex items-center justify-between pl-5 pr-4 py-3 shrink-0">
          <span className="text-[28px] font-bold text-[var(--color-ink)] font-brand tracking-[0.02em]">
            yuoyuo
          </span>
          <button onClick={() => navigate('/settings')}>
            <Avatar src={userAvatar} size={36} border />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 pb-[280px]">
          {loading ? (
            <>
              <Skeleton className="w-full h-[280px] rounded-[24px] mb-4" />
              <div className="flex gap-3 mb-4">
                <Skeleton className="flex-1 h-[90px] rounded-[16px]" />
                <Skeleton className="flex-1 h-[90px] rounded-[16px]" />
                <Skeleton className="flex-1 h-[90px] rounded-[16px]" />
              </div>
            </>
          ) : (
            <>
              {/* Hero Card */}
              <div className="relative w-full h-[260px] rounded-[24px] overflow-hidden shadow-[var(--shadow-hero)] mb-4">
                <img
                  src={heroBg}
                  alt=""
                  className="absolute inset-0 w-full h-full object-cover"
                />
              </div>

              {/* Quick Actions */}
              <div className="flex gap-3 mb-5">
                {[
                  { icon: GiftIcon, label: '兑换会员', color: '#FFB7C5', path: '/redeem' },
                  { icon: PersonIcon, label: '切换角色', color: '#C8B6FF', path: '/character' },
                  { icon: GearIcon, label: '设置', color: '#A7C7E7', path: '/settings' },
                ].map((action) => (
                  <button
                    key={action.label}
                    onClick={() => navigate(action.path)}
                    className="flex-1 flex flex-col items-center gap-2 py-2.5 bg-[var(--color-glass-55)] backdrop-blur-[12px] rounded-[20px] border border-[rgba(255,183,197,0.20)] shadow-[var(--shadow-soft)] active:scale-[0.96] transition-transform"
                  >
                    <action.icon color={action.color} />
                    <span className="text-[13px] text-[var(--color-ink)]">{action.label}</span>
                  </button>
                ))}
              </div>

              {/* Recent Conversations */}
              <div className="mb-4">
                <div className="flex items-center justify-between pl-1 pr-1 mb-3">
                  <span className="text-[16px] font-bold text-[var(--color-ink)]">最近的话</span>
                  <span className="text-[13px] text-[var(--color-text-secondary)]">查看全部</span>
                </div>

                <div className="bg-[var(--color-glass-35)] backdrop-blur-[12px] rounded-[20px] border border-[var(--color-border-glass)] overflow-hidden">
                  {recentConversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => openConversation(conv.id)}
                      className="w-full flex items-center gap-[14px] py-2.5 px-4 active:bg-[rgba(255,183,197,0.12)] transition-colors"
                    >
                      <Avatar src={conv.avatar} size={52} />
                      <div className="flex-1 min-w-0 text-left">
                        <p className="text-[16px] font-semibold text-[var(--color-ink)]">{conv.name}</p>
                        <p className="text-[14px] text-[var(--color-text-secondary)] truncate">{conv.preview}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <span className="text-[13px] text-[var(--color-text-muted)]">{conv.time}</span>
                        {conv.unread && (
                          <div className="w-2 h-2 rounded-full bg-[var(--color-unread-badge)]" />
                        )}
                      </div>
                    </button>
                  ))}
                  {recentConversations.length > 1 && (
                    <div className="h-px bg-[var(--color-divider)] ml-[70px]" />
                  )}
                </div>
              </div>

              <div className="h-[140px]" aria-hidden="true" />
            </>
          )}
        </div>

        {/* TabBar */}
        <TabBar />
      </div>
    </div>
  )
}

/* ── Icons ─────────────────────────────────────────────────────── */
function GiftIcon({ color }: { color: string }) {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="9" width="20" height="13" rx="2" stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M2 9h20v4H2V9Z" stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
      <line x1="12" y1="9" x2="12" y2="22" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
      <path d="M12 9C12 9 9 7 9 5C9 3.3 10.3 2 12 2C13.7 2 15 3.3 15 5C15 7 12 9 12 9Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M12 9C12 9 15 7 15 5C15 3.3 13.7 2 12 2C10.3 2 9 3.3 9 5C9 7 12 9 12 9Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}

function PersonIcon({ color }: { color: string }) {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke={color} strokeWidth="1.7" strokeLinecap="round" />
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke={color} strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}

function GearIcon({ color }: { color: string }) {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" stroke={color} strokeWidth="1.7" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" stroke={color} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
