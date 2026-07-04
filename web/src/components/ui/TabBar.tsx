import { useNavigate, useLocation } from 'react-router-dom'
import { useThemeStore } from '../../stores/themeStore'

interface TabItem {
  id: string
  label: string
  path: string
  icon: (active: boolean) => React.ReactNode
}

const tabs: TabItem[] = [
  {
    id: 'home',
    label: '首页',
    path: '/home',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path
          d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H15v-6H9v6H4a1 1 0 0 1-1-1V9.5Z"
          fill={active ? '#FFB7C5' : 'none'}
          stroke={active ? '#FFB7C5' : '#8E8E9A'}
          strokeWidth="1.7"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    id: 'chat',
    label: '聊天',
    path: '/chat',
    icon: (active) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#FFB7C5' : '#8E8E9A'} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" />
      </svg>
    ),
  },
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

export function TabBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  return (
    <div
      className={`fixed bottom-0 left-[5%] right-[5%] z-[30] backdrop-blur-[20px] rounded-[28px] shadow-[0_-2px_16px_rgba(0,0,0,0.06)] border ${
        isDark
          ? 'bg-[rgba(26,26,46,0.85)] border-[rgba(255,255,255,0.08)]'
          : 'bg-[rgba(255,248,243,0.90)] border-[rgba(255,255,255,0.60)]'
      }`}
      style={{ marginBottom: 'calc(16px + var(--safe-bottom))' }}
    >
      <div className="flex px-2">
        {tabs.map((tab) => {
          const active = location.pathname === tab.path || location.pathname.startsWith(tab.path + '/')
          return (
            <button
              key={tab.id}
              onClick={() => navigate(tab.path)}
              className="flex-1 flex flex-col items-center gap-[2px] py-[10px] active:scale-90 transition-transform"
            >
              {tab.icon(active)}
              <span className={`text-[10px] ${active ? 'text-[var(--color-tab-active)]' : 'text-[#8E8E9A]'}`}>
                {active ? tab.label : ''}
              </span>
              {active && (
                <div className="w-1 h-1 rounded-full bg-[var(--color-tab-active)]" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
