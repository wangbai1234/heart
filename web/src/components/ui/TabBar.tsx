import { useNavigate, useLocation } from 'react-router-dom'
import { useThemeStore } from '../../stores/themeStore'

interface TabItem {
  id: string
  label: string
  path: string
  icon: (active: boolean) => React.ReactNode
}

// Regular tabs flank the raised center 创作 button. Order (per product
// direction 2026-07-31, Nimoo-style): 角色 · 探索 · [创作] · 消息 · 设置.
// The former 首页 tab was removed — the home page carried no unique function,
// so the app now lands directly on 角色 after login.
const leftTabs: TabItem[] = [
  {
    id: 'character',
    label: '角色',
    path: '/character',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#FFB7C5' : '#8E8E9A'} strokeWidth="1.7" strokeLinecap="round">
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
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#FFB7C5' : '#8E8E9A'} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9" />
        <polygon points="15.5,8.5 10.5,10.5 8.5,15.5 13.5,13.5" fill={active ? '#FFB7C5' : 'none'} />
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
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#FFB7C5' : '#8E8E9A'} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" />
      </svg>
    ),
  },
  {
    id: 'settings',
    label: '设置',
    path: '/settings',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#FFB7C5' : '#8E8E9A'} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
]

function TabButton({ tab, active, onClick }: { tab: TabItem; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex-1 flex flex-col items-center gap-[2px] py-[10px] active:scale-90 transition-transform"
    >
      {tab.icon(active)}
      <span className={`text-[10px] ${active ? 'text-[var(--color-tab-active)]' : 'text-[#8E8E9A]'}`}>
        {tab.label}
      </span>
      {active && <div className="w-1 h-1 rounded-full bg-[var(--color-tab-active)]" />}
    </button>
  )
}

export function TabBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + '/')
  const createActive = isActive('/create')

  return (
    <div
      className={`fixed bottom-0 left-[5%] right-[5%] z-[30] backdrop-blur-[20px] rounded-[28px] shadow-[0_-2px_16px_rgba(0,0,0,0.06)] border ${
        isDark
          ? 'bg-[rgba(26,26,46,0.85)] border-[rgba(255,255,255,0.08)]'
          : 'bg-[rgba(255,248,243,0.90)] border-[rgba(255,255,255,0.60)]'
      }`}
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
            className={`-mt-[22px] w-[56px] h-[56px] rounded-full flex items-center justify-center bg-gradient-to-br from-[#FFB7C5] to-[#FF8FAB] shadow-[0_8px_20px_-4px_rgba(255,143,171,0.55)] ring-[3px] active:scale-90 transition-transform ${
              isDark ? 'ring-[rgba(26,26,46,0.85)]' : 'ring-[rgba(255,248,243,0.90)]'
            }`}
          >
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.4" strokeLinecap="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
          <span className={`mt-[3px] text-[10px] ${createActive ? 'text-[var(--color-tab-active)]' : 'text-[#8E8E9A]'}`}>
            创作
          </span>
        </div>

        {rightTabs.map((tab) => (
          <TabButton key={tab.id} tab={tab} active={isActive(tab.path)} onClick={() => navigate(tab.path)} />
        ))}
      </div>
    </div>
  )
}
