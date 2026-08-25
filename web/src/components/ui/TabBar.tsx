import { useNavigate, useLocation } from 'react-router-dom'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { useAuthPromptStore } from '../../stores/authPromptStore'

interface TabItem {
  id: string
  label: string
  path: string
  icon: (active: boolean) => React.ReactNode
}

// Regular tabs flank the raised center 创作 button. Order (per product
// direction 2026-08-25): 角色 · 福利 · [创作] · 消息 · 我的.
// The former 首页 tab was removed — the home page carried no unique function,
// so the app now lands directly on 角色 after login.
const leftTabs: TabItem[] = [
  {
    id: 'character',
    label: '角色',
    path: '/character',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--color-tab-active)' : 'var(--color-tab-inactive)'} strokeWidth="2" strokeLinecap="round">
        <circle cx="12" cy="8" r="4" />
        <path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7" />
      </svg>
    ),
  },
  {
    id: 'rewards',
    label: '福利',
    path: '/rewards',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--color-tab-active)' : 'var(--color-tab-inactive)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 12v9H4v-9" />
        <path d="M2 7h20v5H2z" />
        <path d="M12 7v14" />
        <path d="M12 7H7.5A2.5 2.5 0 1 1 10 4.5C10 6 12 7 12 7Z" />
        <path d="M12 7h4.5A2.5 2.5 0 1 0 14 4.5C14 6 12 7 12 7Z" />
      </svg>
    ),
  },
]

const rightTabs: TabItem[] = [
  {
    id: 'chat',
    label: '消息',
    path: '/chat',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--color-tab-active)' : 'var(--color-tab-inactive)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" />
      </svg>
    ),
  },
  {
    id: 'settings',
    label: '我的',
    path: '/settings',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill={active ? 'rgba(255,183,197,0.16)' : 'none'} stroke={active ? 'var(--color-tab-active)' : 'var(--color-tab-inactive)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="8" r="4" />
        <path d="M4.5 21c.8-4.2 3.7-6.5 7.5-6.5s6.7 2.3 7.5 6.5" />
        <path d="M8.5 19.4c.9-.8 2.1-1.2 3.5-1.2s2.6.4 3.5 1.2" opacity={active ? 1 : 0.6} />
      </svg>
    ),
  },
]

function TabButton({
  tab,
  active,
  onClick,
  badgeCount = 0,
}: {
  tab: TabItem
  active: boolean
  onClick: () => void
  badgeCount?: number
}) {
  return (
    <button
      onClick={onClick}
      className="flex h-[58px] flex-1 flex-col items-center justify-center gap-[3px] active:scale-95 transition-transform duration-[var(--duration-fast)]"
    >
      <div className="relative transition-colors duration-[var(--duration-fast)]">
        {tab.icon(active)}
        {badgeCount > 0 && (
          <span
            className="absolute -top-1 -right-1.5 min-w-[16px] h-[16px] px-1 flex items-center justify-center rounded-full bg-[#FF4D6D] text-white text-[10px] font-medium leading-none shadow-[0_1px_3px_rgba(0,0,0,0.2)]"
            aria-label={`${badgeCount} 条未读`}
          >
            {badgeCount > 99 ? '99+' : badgeCount}
          </span>
        )}
      </div>
      <span className={`text-[11px] transition-colors duration-[var(--duration-fast)] ${active ? 'text-[var(--color-tab-active)] font-semibold' : 'text-[var(--color-tab-inactive)]'}`}>
        {tab.label}
      </span>
    </button>
  )
}

export function TabBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const inboxUnreadTotal = useAppStore((s) => s.inboxUnreadTotal)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const showAuthPrompt = useAuthPromptStore((state) => state.show)
  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + '/')
  const createActive = isActive('/create')
  const openTab = (path: string) => {
    if (path === '/character' || isAuthenticated()) {
      navigate(path)
      return
    }
    showAuthPrompt(path)
  }

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-[30] border-t border-[var(--color-divider)] bg-[var(--color-page-surface)]/94 backdrop-blur-[20px] shadow-[0_-6px_22px_rgba(20,20,28,0.06)] md:left-1/2 md:right-auto md:bottom-4 md:w-[calc(100%_-_32px)] md:max-w-[720px] md:-translate-x-1/2 md:rounded-[18px] md:border"
      style={{ paddingBottom: 'var(--safe-bottom)' }}
    >
      <div className="flex h-[62px] items-center px-2">
        {leftTabs.map((tab) => (
          <TabButton key={tab.id} tab={tab} active={isActive(tab.path)} onClick={() => openTab(tab.path)} />
        ))}

        <div className="relative flex h-[58px] flex-1 items-center justify-center">
          <button
            onClick={() => openTab('/create')}
            aria-label="创作"
            className={`relative -mt-[18px] flex h-[58px] w-[58px] items-center justify-center rounded-full border-4 border-[var(--color-page-surface)] transition-all active:scale-95 ${
              createActive
                ? 'bg-[var(--color-primary-500)] text-white shadow-[0_7px_18px_rgba(255,110,138,0.34)]'
                : 'bg-[var(--color-primary-100)] text-[var(--color-primary-600)] shadow-[0_5px_14px_rgba(255,110,138,0.20)]'
            }`}
          >
            <div>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
              </svg>
            </div>
          </button>
          <span className={`absolute bottom-0 text-[11px] transition-colors duration-[var(--duration-fast)] ${createActive ? 'text-[var(--color-tab-active)] font-semibold' : 'text-[var(--color-tab-inactive)]'}`}>
            创作
          </span>
        </div>

        {rightTabs.map((tab) => (
          <TabButton
            key={tab.id}
            tab={tab}
            active={isActive(tab.path)}
            onClick={() => openTab(tab.path)}
            badgeCount={tab.id === 'chat' ? inboxUnreadTotal : 0}
          />
        ))}
      </div>
    </div>
  )
}
