import type { ReactNode } from 'react'

interface NoticeDialogProps {
  open: boolean
  onClose: () => void
  /** Title line rendered in the frosted panel (kept short — one line). */
  title?: string
  /** Body copy — keep concise so it stays inside the bubble. */
  children: ReactNode
  /** Label for the action button. Defaults to 知道了. */
  actionLabel?: string
  /** Action handler. Defaults to onClose. */
  onAction?: () => void
}

/**
 * 通用通知弹窗 — a decorated heart-bubble frame used for celebratory /
 * informational notices (daily check-in, review results, publish incentive…).
 * The art (heart, frosted panel, bubbles) is baked into
 * /assets/ui/notice-frame.webp as a transparent PNG-style webp with a clean,
 * near-opaque center. Text, close button and the gradient action pill are all
 * rendered in code and positioned inside the panel's measured safe area
 * (x 0.16–0.87, y 0.21–0.84), so any length of copy stays legible and never
 * spills the border.
 *
 * For destructive confirmations (logout / delete) keep using ui/Dialog — this
 * frame is single-action by design.
 */
export function NoticeDialog({
  open,
  onClose,
  title,
  children,
  actionLabel = '知道了',
  onAction,
}: NoticeDialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-[var(--color-overlay)] animate-[fade-in_260ms_ease-out]"
        onClick={onClose}
      />
      <div className="relative z-10 w-[88%] max-w-[360px] aspect-square animate-[dialog-enter_300ms_var(--ease-standard)]">
        <img
          src="/assets/ui/notice-frame.webp"
          alt=""
          className="absolute inset-0 w-full h-full object-contain pointer-events-none select-none"
          draggable={false}
        />

        {/* Close — top-right, inside the panel corner */}
        <button
          onClick={onClose}
          aria-label="关闭"
          className="absolute w-[30px] h-[30px] flex items-center justify-center rounded-full text-[#9B7FB0] active:scale-90 transition-transform"
          style={{ left: '78%', top: '23.5%' }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        {/* Content column — pinned to the panel's safe interior */}
        <div
          className="absolute flex flex-col items-center"
          style={{ left: '17%', right: '17%', top: '28%', bottom: '17%' }}
        >
          {/* Scroll region. my-auto on the inner block centers the text when it
              fits but collapses on overflow so the FIRST line stays reachable
              (a plain justify-center clips the top when content is taller). */}
          <div className="flex-1 min-h-0 w-full overflow-y-auto flex flex-col">
            <div className="my-auto flex flex-col items-center text-center">
              {title && (
                <h3 className="text-[18px] font-semibold text-[#2a2a38] leading-tight mb-2">
                  {title}
                </h3>
              )}
              <div className="text-[13.5px] text-[#5a5a6a] leading-[1.55]">
                {children}
              </div>
            </div>
          </div>

          <button
            onClick={onAction ?? onClose}
            className="shrink-0 mt-4 min-w-[132px] h-[42px] px-7 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[15px] font-semibold shadow-[0_8px_20px_rgba(255,143,171,0.38)] active:scale-[0.97] transition-transform"
          >
            {actionLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
