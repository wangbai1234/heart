import type { ReactNode } from 'react'
import { Button } from './Button'

interface ErrorStateProps {
  icon?: ReactNode
  title: string
  description?: string
  retryLabel?: string
  onRetry?: () => void
}

export function ErrorState({ icon, title, description, retryLabel = '重试', onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      {icon && <div className="mb-4 text-[var(--color-error)]">{icon}</div>}
      <h3 className="text-lg font-semibold text-[var(--color-ink)] mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-[var(--color-text-secondary)] mb-6 max-w-[260px]">{description}</p>
      )}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  )
}
