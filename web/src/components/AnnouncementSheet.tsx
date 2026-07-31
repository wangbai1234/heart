import { useState } from 'react'
import { HOME_ANNOUNCEMENTS, type HomeAnnouncement } from '../data/uiContent'

/**
 * 公告面板 — a bottom-sheet list of product announcements + a detail sheet.
 *
 * Extracted from the retired HomePage (2026-07-31): the home tab was removed,
 * so its only real content (公告) now lives behind the 角色 page's 公告 button.
 * `open` toggles the list sheet; tapping a row opens the full detail sheet.
 */
export function AnnouncementSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [active, setActive] = useState<HomeAnnouncement | null>(null)
  const announcements = [...HOME_ANNOUNCEMENTS].sort((a, b) => b.publishedAt - a.publishedAt)

  if (!open) return null

  const closeAll = () => {
    setActive(null)
    onClose()
  }

  return (
    <div className="absolute inset-0 z-50 flex items-end" onClick={closeAll}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />

      <div
        className="relative w-full max-h-[72vh] bg-[var(--color-surface-card)] rounded-t-[28px] flex flex-col shadow-[0_-8px_40px_rgba(0,0,0,0.18)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-center pt-3 pb-1 shrink-0">
          <div className="w-[40px] h-[4px] rounded-full bg-[var(--color-divider)]" />
        </div>

        <div className="flex items-center justify-between px-5 pb-3 shrink-0 border-b border-[var(--color-divider)]">
          <span className="text-[17px] font-semibold text-[var(--color-ink)]">公告</span>
          <button
            onClick={closeAll}
            className="w-[32px] h-[32px] rounded-full bg-[var(--color-glass-35)] flex items-center justify-center"
            aria-label="关闭"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round">
              <line x1="1" y1="1" x2="13" y2="13" />
              <line x1="13" y1="1" x2="1" y2="13" />
            </svg>
          </button>
        </div>

        <div
          className="overflow-y-auto flex-1 min-h-0 px-4 py-3"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 16px), 20px)' }}
        >
          {announcements.map((a, index) => (
            <button
              key={a.id}
              onClick={() => setActive(a)}
              className="w-full text-left px-2 py-4 active:bg-[rgba(255,183,197,0.10)] transition-colors rounded-[14px]"
            >
              <div className="flex items-start gap-3">
                <div className="w-[44px] h-[44px] rounded-[16px] bg-[rgba(255,183,197,0.18)] flex items-center justify-center shrink-0">
                  <NoticeIcon />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="inline-flex h-6 items-center rounded-full bg-[rgba(255,183,197,0.18)] px-2.5 text-[12px] font-medium text-[var(--color-primary)]">
                      {a.tag}
                    </span>
                    <span className="text-[12px] text-[var(--color-text-muted)]">{formatDate(a.publishedAt)}</span>
                  </div>
                  <p className="text-[15px] font-semibold leading-[1.45] text-[var(--color-ink)]">{a.title}</p>
                  <p className="mt-1 text-[13px] leading-[1.65] text-[var(--color-text-secondary)]">{a.summary}</p>
                </div>
                <div className="shrink-0 pl-1 flex items-center self-center">
                  <svg width="7" height="12" viewBox="0 0 7 12" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="1,1 6,6 1,11" />
                  </svg>
                </div>
              </div>
              {index < announcements.length - 1 && <div className="mt-4 h-px bg-[var(--color-divider)]" />}
            </button>
          ))}
        </div>
      </div>

      {active && <AnnouncementDetail announcement={active} onClose={() => setActive(null)} />}
    </div>
  )
}

function AnnouncementDetail({ announcement, onClose }: { announcement: HomeAnnouncement; onClose: () => void }) {
  return (
    <div className="absolute inset-0 z-[60] flex items-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />
      <div
        className="relative w-full h-[62vh] bg-[var(--color-surface-card)] rounded-t-[28px] flex flex-col shadow-[0_-8px_40px_rgba(0,0,0,0.18)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-center pt-3 pb-1 shrink-0">
          <div className="w-[40px] h-[4px] rounded-full bg-[var(--color-divider)]" />
        </div>
        <div className="flex items-center justify-between px-5 pb-3 shrink-0 border-b border-[var(--color-divider)]">
          <span className="inline-flex h-[22px] items-center rounded-full bg-[rgba(255,183,197,0.20)] px-2.5 text-[12px] font-medium text-[var(--color-primary)]">
            {announcement.tag}
          </span>
          <button
            onClick={onClose}
            className="w-[32px] h-[32px] rounded-full bg-[var(--color-glass-35)] flex items-center justify-center"
            aria-label="关闭"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round">
              <line x1="1" y1="1" x2="13" y2="13" />
              <line x1="13" y1="1" x2="1" y2="13" />
            </svg>
          </button>
        </div>
        <div
          className="overflow-y-auto px-5 py-4 flex-1 min-h-0"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 16px), 20px)' }}
        >
          <h2 className="text-[18px] font-bold text-[var(--color-ink)] leading-[1.4] mb-3">{announcement.title}</h2>
          <p className="text-[12px] text-[var(--color-text-muted)] mb-4">{formatDateLong(announcement.publishedAt)}</p>
          <div className="text-[15px] leading-[1.75] text-[var(--color-ink)] whitespace-pre-line">
            {announcement.content || announcement.summary}
          </div>
        </div>
      </div>
    </div>
  )
}

function formatDate(ts: number): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(ts))
}

function formatDateLong(ts: number): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(ts))
}

function NoticeIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3a4 4 0 0 0-4 4v1.2A7 7 0 0 1 5.4 14L4 15.3V17h16v-1.7L18.6 14A7 7 0 0 1 16 8.2V7a4 4 0 0 0-4-4Z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </svg>
  )
}
