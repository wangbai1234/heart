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
        className="relative w-full max-h-[78vh] overflow-hidden rounded-t-[24px] border-t border-[var(--color-border-glass)] bg-[var(--color-page-surface)] shadow-[0_-12px_36px_rgba(30,24,34,0.16)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative flex flex-col items-center justify-center pt-3 pb-4 shrink-0">
          <div className="h-[4px] w-[38px] rounded-full bg-[var(--color-divider)]" />
          <div className="mt-4 flex w-full items-center justify-between border-b border-[var(--color-divider)] px-5 pb-4">
            <div>
              <p className="text-[18px] font-semibold leading-tight text-[var(--color-ink)]">公告</p>
              <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">yuoyuo 的最新动态</p>
            </div>
            <span className="mr-2 text-[12px] text-[var(--color-text-muted)]">{announcements.length} 条</span>
            <button
              onClick={closeAll}
              className="flex h-[32px] w-[32px] items-center justify-center rounded-full bg-[var(--color-page-soft)] text-[var(--color-ink)] active:scale-95"
              aria-label="关闭"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="1" y1="1" x2="13" y2="13" />
                <line x1="13" y1="1" x2="1" y2="13" />
              </svg>
            </button>
          </div>
        </div>

        <div
          className="relative max-h-[calc(78vh-132px)] overflow-y-auto px-4 pb-3"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 16px), 20px)' }}
        >
          {announcements.map((a) => (
            <button
              key={a.id}
              onClick={() => setActive(a)}
              className="group w-full border-b border-[var(--color-divider)] px-2 py-4 text-left transition-colors last:border-b-0 active:bg-[rgba(255,183,197,0.08)]"
            >
              <div className="flex items-start gap-3">
                <span className="mt-[7px] h-[7px] w-[7px] shrink-0 rounded-full bg-[var(--color-primary-500)]" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-[12px] font-medium text-[var(--color-primary-600)]">
                      {a.tag}
                    </span>
                    <span className="text-[12px] text-[var(--color-text-muted)]">{formatDate(a.publishedAt)}</span>
                  </div>
                  <p className="text-[15px] font-semibold leading-[1.45] text-[var(--color-ink)]">{a.title}</p>
                  <p className="mt-1 text-[13px] leading-[1.65] text-[var(--color-text-secondary)]">{a.summary}</p>
                </div>
                <div className="flex shrink-0 items-center self-center pl-1 text-[var(--color-chevron)] transition-transform group-active:translate-x-0.5">
                  <svg width="7" height="12" viewBox="0 0 7 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="1,1 6,6 1,11" />
                  </svg>
                </div>
              </div>
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
        className="relative flex h-[68vh] w-full flex-col overflow-hidden rounded-t-[24px] border-t border-[var(--color-border-glass)] bg-[var(--color-page-surface)] shadow-[0_-12px_36px_rgba(30,24,34,0.16)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-center pt-3 pb-1 shrink-0">
          <div className="h-[4px] w-[38px] rounded-full bg-[var(--color-divider)]" />
        </div>
        <div className="relative flex items-center justify-between border-b border-[var(--color-divider)] px-5 pb-4 pt-3">
          <div>
            <p className="text-[12px] font-medium text-[var(--color-primary-600)]">{announcement.tag}</p>
            <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">{formatDateLong(announcement.publishedAt)}</p>
          </div>
          <button
            onClick={onClose}
            className="flex h-[32px] w-[32px] items-center justify-center rounded-full bg-[var(--color-page-soft)]"
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
          <h2 className="mb-4 text-[21px] font-bold leading-[1.4] text-[var(--color-ink)]">{announcement.title}</h2>
          <div className="mb-5 h-[3px] w-[34px] rounded-full bg-[var(--color-primary-400)]" />
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
