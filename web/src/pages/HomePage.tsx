import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useAuthStore } from '../stores/authStore'
import { Avatar } from '../components/ui/Avatar'
import { TabBar } from '../components/ui/TabBar'
import { Skeleton } from '../components/ui/Skeleton'
import { HOME_ANNOUNCEMENTS, getHeroBanner, type HomeAnnouncement } from '../data/uiContent'
import { useSwipeNavigation } from '../hooks/useSwipeNavigation'

export function HomePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  // Block right-swipe on home page — no previous route to go back to
  useSwipeNavigation({ onRightSwipe: null })
  const userAvatar = useAuthStore((s) => s.user?.avatar_url ?? null)
  const loading = false
  const [activeAnnouncement, setActiveAnnouncement] = useState<HomeAnnouncement | null>(null)
  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'
  const heroBg = getHeroBanner(resolvedTheme)
  const latestAnnouncements = [...HOME_ANNOUNCEMENTS]
    .sort((left, right) => right.publishedAt - left.publishedAt)
    .slice(0, 3)

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
                  { icon: GiftIcon, label: '兑换会员', color: '#FFB7C5', path: '/membership' },
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

              {/* Recent Announcements */}
              <div className="mb-4">
                <div className="flex items-center justify-between pl-1 pr-1 mb-3">
                  <span className="text-[16px] font-bold text-[var(--color-ink)]">最近公告</span>
                </div>

                <div className="bg-[var(--color-glass-35)] backdrop-blur-[12px] rounded-[20px] border border-[var(--color-border-glass)] overflow-hidden">
                  {latestAnnouncements.map((announcement, index) => (
                    <button
                      key={announcement.id}
                      onClick={() => setActiveAnnouncement(announcement)}
                      className="w-full text-left px-4 py-4 active:bg-[rgba(255,183,197,0.10)] transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-[44px] h-[44px] rounded-[16px] bg-[rgba(255,183,197,0.18)] flex items-center justify-center shrink-0">
                          <NoticeIcon />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="mb-1 flex items-center gap-2">
                            <span className="inline-flex h-6 items-center rounded-full bg-[rgba(255,183,197,0.18)] px-2.5 text-[12px] font-medium text-[var(--color-primary)]">
                              {announcement.tag}
                            </span>
                            <span className="text-[12px] text-[var(--color-text-muted)]">
                              {new Intl.DateTimeFormat('zh-CN', {
                                month: 'numeric',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false,
                              }).format(new Date(announcement.publishedAt))}
                            </span>
                          </div>
                          <p className="text-[15px] font-semibold leading-[1.45] text-[var(--color-ink)]">
                            {announcement.title}
                          </p>
                          <p className="mt-1 text-[13px] leading-[1.65] text-[var(--color-text-secondary)]">
                            {announcement.summary}
                          </p>
                        </div>
                        <div className="shrink-0 pl-1 flex items-center self-center">
                          <svg width="7" height="12" viewBox="0 0 7 12" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="1,1 6,6 1,11" />
                          </svg>
                        </div>
                      </div>
                      {index < latestAnnouncements.length - 1 && (
                        <div className="mt-4 h-px bg-[var(--color-divider)]" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <div className="h-[140px]" aria-hidden="true" />
            </>
          )}
        </div>

        {/* TabBar */}
        <TabBar />
      </div>

      {/* Announcement Detail Modal */}
      {activeAnnouncement && (
        <div
          className="absolute inset-0 z-50 flex items-end"
          onClick={() => setActiveAnnouncement(null)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />

          {/* Sheet — fixed height so body is always scrollable */}
          <div
            className="relative w-full h-[62vh] bg-[var(--color-surface-card)] rounded-t-[28px] flex flex-col shadow-[0_-8px_40px_rgba(0,0,0,0.18)]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-1 shrink-0">
              <div className="w-[40px] h-[4px] rounded-full bg-[var(--color-divider)]" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-5 pb-3 shrink-0 border-b border-[var(--color-divider)]">
              <span className="inline-flex h-[22px] items-center rounded-full bg-[rgba(255,183,197,0.20)] px-2.5 text-[12px] font-medium text-[var(--color-primary)]">
                {activeAnnouncement.tag}
              </span>
              <button
                onClick={() => setActiveAnnouncement(null)}
                className="w-[32px] h-[32px] rounded-full bg-[var(--color-glass-35)] flex items-center justify-center"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round">
                  <line x1="1" y1="1" x2="13" y2="13" />
                  <line x1="13" y1="1" x2="1" y2="13" />
                </svg>
              </button>
            </div>

            {/* Scrollable body — grows to fill remaining sheet height */}
            <div
              className="overflow-y-auto px-5 py-4 flex-1 min-h-0"
              style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 16px), 20px)' }}
            >
              <h2 className="text-[18px] font-bold text-[var(--color-ink)] leading-[1.4] mb-3">
                {activeAnnouncement.title}
              </h2>
              <p className="text-[12px] text-[var(--color-text-muted)] mb-4">
                {new Intl.DateTimeFormat('zh-CN', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false,
                }).format(new Date(activeAnnouncement.publishedAt))}
              </p>
              <div className="text-[15px] leading-[1.75] text-[var(--color-ink)] whitespace-pre-line">
                {activeAnnouncement.content || activeAnnouncement.summary}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function NoticeIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3a4 4 0 0 0-4 4v1.2A7 7 0 0 1 5.4 14L4 15.3V17h16v-1.7L18.6 14A7 7 0 0 1 16 8.2V7a4 4 0 0 0-4-4Z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </svg>
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
