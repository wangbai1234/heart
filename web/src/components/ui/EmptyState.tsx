import type { ReactNode } from 'react'
import { Button } from './Button'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({ icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      {icon && <div className="mb-4 text-[var(--color-text-muted)]">{icon}</div>}
      <h3 className="text-lg font-semibold text-[var(--color-ink)] mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-[var(--color-text-secondary)] mb-6 max-w-[260px]">{description}</p>
      )}
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
