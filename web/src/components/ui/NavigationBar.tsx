import type { ReactNode } from 'react'

interface NavigationBarProps {
  title?: string
  onBack?: () => void
  rightAction?: ReactNode
  transparent?: boolean
}

export function NavigationBar({ title, onBack, rightAction, transparent }: NavigationBarProps) {
  return (
    <nav
      className={`
        fixed top-0 left-0 right-0 z-[30]
        flex items-center justify-between
        px-5 h-[44px]
        ${transparent
          ? 'bg-transparent'
          : 'bg-[var(--color-glass-55)] backdrop-blur-[var(--blur-glass-md)]'
        }
      `}
      style={{ paddingTop: 'var(--safe-top)' }}
    >
      <div className="w-[44px] h-[44px] flex items-center justify-start">
        {onBack && (
          <button
            onClick={onBack}
            className="w-[44px] h-[44px] flex items-center justify-center active:opacity-60 transition-opacity"
            aria-label="返回"
          >
            <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="10,2 2,10 10,18" />
            </svg>
          </button>
        )}
      </div>
      {title && (
        <span className="text-[17px] font-medium text-[var(--color-ink)]">{title}</span>
      )}
      <div className="w-[44px] h-[44px] flex items-center justify-end">
        {rightAction}
      </div>
    </nav>
  )
}
