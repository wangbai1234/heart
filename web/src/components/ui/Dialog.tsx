import type { ReactNode } from 'react'

interface DialogProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  actions?: ReactNode
}

export function Dialog({ open, onClose, title, children, actions }: DialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[50] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-[var(--color-overlay)] animate-[fade-in_280ms_ease-out]"
        onClick={onClose}
      />
      <div className="relative z-10 w-[85%] max-w-[340px] rounded-[var(--radius-2xl)] bg-[var(--color-glass-75)] backdrop-blur-[var(--blur-glass-md)] border border-[var(--color-border-glass)] shadow-[var(--shadow-modal)] p-6 animate-[dialog-enter_280ms_var(--ease-standard)]">
        {title && (
          <h3 className="text-lg font-semibold text-[var(--color-ink)] text-center mb-4">
            {title}
          </h3>
        )}
        <div className="text-sm text-[var(--color-text-secondary)] text-center mb-6">
          {children}
        </div>
        {actions && (
          <div className="flex gap-3">{actions}</div>
        )}
      </div>
    </div>
  )
}
