import { useNavigate, useLocation } from 'react-router-dom'
import { useAppStore } from '../../stores/appStore'

interface TabItem {
  id: string
  label: string
  path: string
  icon: (active: boolean) => React.ReactNode
}

// Regular tabs flank the raised center 创作 button. Order (per product
// direction 2026-07-31, Nimoo-style): 角色 · 探索 · [创作] · 消息 · 我的.
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
    id: 'explore',
    label: '探索',
    path: '/explore',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--color-tab-active)' : 'var(--color-tab-inactive)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9" />
        <polygon points="15.5,8.5 10.5,10.5 8.5,15.5 13.5,13.5" fill={active ? 'var(--color-tab-active)' : 'none'} />
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
      className="flex-1 flex flex-col items-center gap-[2px] py-[10px] active:scale-90 hover:scale-105 transition-all duration-[var(--duration-fast)]"
    >
      <div className="relative transition-all duration-[var(--duration-fast)] hover:brightness-110">
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
      <span className={`text-[11px] transition-all duration-[var(--duration-fast)] ${active ? 'text-[var(--color-tab-active)] font-medium' : 'text-[var(--color-tab-inactive)]'}`}>
        {tab.label}
      </span>
      {active && <div className="w-4 h-[2px] rounded-full bg-[var(--color-tab-active)] transition-all duration-[var(--duration-fast)]" />}
    </button>
  )
}

export function TabBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const inboxUnreadTotal = useAppStore((s) => s.inboxUnreadTotal)
  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + '/')
  const createActive = isActive('/create')

  return (
    <div
      className="fixed bottom-0 left-[5%] right-[5%] z-[30] backdrop-blur-[20px] rounded-[28px] shadow-[0_-2px_8px_rgba(0,0,0,0.04),0_-4px_16px_rgba(0,0,0,0.06)] border transition-shadow duration-[var(--duration-normal)] bg-[var(--color-glass-90)] border-[var(--color-border-glass)]"
      style={{ marginBottom: 'calc(16px + var(--safe-bottom))' }}
    >
      <div className="flex items-end px-2">
        {leftTabs.map((tab) => (
          <TabButton key={tab.id} tab={tab} active={isActive(tab.path)} onClick={() => navigate(tab.path)} />
        ))}

        {/* Raised center 创作 button — the primary Nimoo-style entry to the
            creation hub. Floats above the bar so it reads as the focal action. */}
        <div className="flex-1 flex flex-col items-center">
          <button
            onClick={() => navigate('/create')}
            aria-label="创作"
            className="relative -mt-[22px] w-[58px] h-[58px] rounded-full flex items-center justify-center bg-gradient-to-br from-[#FFB7C5] via-[#FFA8BA] to-[#FF8FAB] shadow-[0_8px_24px_-4px_rgba(255,143,171,0.5),0_2px_8px_rgba(255,143,171,0.3)] before:absolute before:inset-[-3px] before:rounded-full before:bg-[var(--color-glass-90)] before:z-[-1] active:scale-95 hover:scale-105 hover:shadow-[0_12px_32px_-4px_rgba(255,143,171,0.6),0_4px_12px_rgba(255,143,171,0.4)] transition-all duration-300 ease-[var(--ease-standard)] group overflow-hidden"
          >
            {/* Shimmer effect */}
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />

            {/* Inner glow */}
            <div className="absolute inset-[2px] rounded-full bg-gradient-to-t from-white/20 to-transparent" />

            {/* Icon with subtle animation */}
            <div className="relative z-10 group-hover:rotate-12 transition-transform duration-300">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
              </svg>
            </div>

            {/* Pulse ring on hover */}
            <div className="absolute inset-0 rounded-full bg-[var(--color-primary)] opacity-0 group-hover:opacity-20 group-hover:scale-150 transition-all duration-500" />
          </button>
          <span className={`mt-[3px] text-[11px] transition-all duration-[var(--duration-fast)] ${createActive ? 'text-[var(--color-tab-active)] font-semibold' : 'text-[var(--color-tab-inactive)]'}`}>
            创作
          </span>
        </div>

        {rightTabs.map((tab) => (
          <TabButton
            key={tab.id}
            tab={tab}
            active={isActive(tab.path)}
            onClick={() => navigate(tab.path)}
            badgeCount={tab.id === 'chat' ? inboxUnreadTotal : 0}
          />
        ))}
      </div>
    </div>
  )
}
