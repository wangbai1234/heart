import { useEffect, useRef } from 'react'

export type ToastVariant = 'info' | 'error' | 'success'

interface ToastProps {
  message: string
  visible: boolean
  onDismiss?: () => void
  /** Visual accent. Defaults to neutral 'info'. */
  variant?: ToastVariant
  /** Stack position when multiple toasts are shown (0 = topmost). */
  offsetIndex?: number
}

const VARIANT_BORDER: Record<ToastVariant, string> = {
  info: 'var(--color-border-glass)',
  error: 'var(--color-error)',
  success: 'var(--color-mint, var(--color-border-glass))',
}

export function Toast({ message, visible, onDismiss, variant = 'info', offsetIndex = 0 }: ToastProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (visible && onDismiss) {
      timerRef.current = setTimeout(onDismiss, 2200)
      return () => {
        if (timerRef.current) clearTimeout(timerRef.current)
      }
    }
  }, [visible, onDismiss])

  if (!visible) return null

  return (
    <div
      className="fixed left-1/2 -translate-x-1/2 z-[40] animate-[fade-in-up_220ms_var(--ease-standard)]"
      style={{ top: `calc(var(--safe-top) + 8px + ${offsetIndex * 52}px)` }}
    >
      <div
        className="px-5 py-3 rounded-full bg-[var(--color-glass-75)] backdrop-blur-[var(--blur-glass)] border shadow-[var(--shadow-card)] text-sm text-[var(--color-ink)] whitespace-nowrap"
        style={{ borderColor: VARIANT_BORDER[variant] }}
      >
        {message}
      </div>
    </div>
  )
}
