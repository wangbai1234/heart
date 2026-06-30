import { useEffect, useRef } from 'react'

interface ToastProps {
  message: string
  visible: boolean
  onDismiss?: () => void
}

export function Toast({ message, visible, onDismiss }: ToastProps) {
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
    <div className="fixed top-[calc(var(--safe-top)+8px)] left-1/2 -translate-x-1/2 z-[40] animate-[fade-in-up_220ms_var(--ease-standard)]">
      <div className="px-5 py-3 rounded-full bg-[var(--color-glass-75)] backdrop-blur-[var(--blur-glass)] border border-[var(--color-border-glass)] shadow-[var(--shadow-card)] text-sm text-[var(--color-ink)] whitespace-nowrap">
        {message}
      </div>
    </div>
  )
}
