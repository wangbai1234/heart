import { useState } from 'react'
import type { ActiveNoticeDTO } from '../services/api'

interface RecoveryNoticeDialogProps {
  notice: ActiveNoticeDTO | null
  onAcknowledge: (noticeId: string) => Promise<void>
}

export function RecoveryNoticeDialog({ notice, onAcknowledge }: RecoveryNoticeDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  if (!notice) return null

  const confirm = async () => {
    if (submitting) return
    setSubmitting(true)
    setError('')
    try {
      await onAcknowledge(notice.id)
    } catch {
      setError('确认失败，请检查网络后重试。')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/55 px-2 py-2 backdrop-blur-[2px] sm:px-4 sm:py-5">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="recovery-notice-title"
        className="flex max-h-[calc(100vh-16px)] w-full max-w-[430px] flex-col overflow-hidden rounded-[20px] border border-[var(--color-border-glass)] bg-[var(--color-page-surface)] shadow-[0_20px_60px_rgba(20,16,25,0.28)]"
        style={{ maxHeight: 'calc(100dvh - 16px)' }}
        onTouchStart={(event) => event.stopPropagation()}
        onTouchMove={(event) => event.stopPropagation()}
        onTouchEnd={(event) => event.stopPropagation()}
      >
        <header className="shrink-0 border-b border-[var(--color-divider)] px-5 pb-3 pt-4 sm:pb-4 sm:pt-5">
          <p className="text-[12px] font-semibold text-[var(--color-primary-600)]">
            {notice.eyebrow || '重要公告'}
          </p>
          <h2
            id="recovery-notice-title"
            className="mt-1 text-[20px] font-bold leading-[1.45] text-[var(--color-ink)]"
          >
            {notice.title}
          </h2>
        </header>

        <div
          className="min-h-0 flex-1 touch-pan-y overflow-y-auto overscroll-contain px-5 py-4"
          style={{ WebkitOverflowScrolling: 'touch' }}
        >
          <div className="whitespace-pre-line text-[15px] leading-[1.78] text-[var(--color-ink)]">
            {notice.content}
          </div>
          {notice.qr_image_url && (
            <div className="mt-6 flex flex-col items-center">
              <img
                src={notice.qr_image_url}
                alt="yuoyuo 客服 QQ 3533394028 二维码"
                className="w-full max-w-[250px] rounded-[8px] border border-[var(--color-divider)]"
              />
              <p className="mt-3 text-center text-[13px] leading-6 text-[var(--color-text-secondary)]">
                扫码添加客服，或搜索 QQ：3533394028
              </p>
            </div>
          )}
        </div>

        <footer
          className="relative z-10 shrink-0 border-t border-[var(--color-divider)] bg-[var(--color-page-surface)] px-5 pt-3 shadow-[0_-8px_18px_rgba(20,16,25,0.06)] sm:pt-4"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 12px), 12px)' }}
        >
          {error && <p className="mb-3 text-center text-[13px] text-red-600">{error}</p>}
          <button
            type="button"
            onClick={() => void confirm()}
            disabled={submitting}
            className="h-[46px] w-full rounded-[8px] bg-[var(--color-primary-500)] text-[15px] font-semibold text-white transition-opacity active:opacity-85 disabled:opacity-60"
          >
            {submitting ? '正在确认…' : notice.confirm_label || '我已了解'}
          </button>
        </footer>
      </section>
    </div>
  )
}
