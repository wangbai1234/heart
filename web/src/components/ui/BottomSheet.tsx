import type { ReactNode } from 'react'
import { useEffect } from 'react'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  children: ReactNode
}

export function BottomSheet({ open, onClose, children }: BottomSheetProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[50]">
      <div
        className="absolute inset-0 bg-black/32 animate-[fade-in_360ms_var(--ease-standard)]"
        onClick={onClose}
      />
      <div className="absolute bottom-0 left-0 right-0 bg-[var(--color-surface)] rounded-t-[var(--radius-2xl)] shadow-[var(--shadow-sheet)] animate-[slide-up-bottom_360ms_var(--ease-standard)] pb-[var(--safe-bottom)]">
        <div className="flex justify-center pt-3 pb-2">
          <div className="w-10 h-1 rounded-full bg-[var(--color-divider)]" />
        </div>
        <div className="px-5 pb-4">{children}</div>
      </div>
    </div>
  )
}
