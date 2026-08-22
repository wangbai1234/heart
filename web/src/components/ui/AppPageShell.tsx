import type { CSSProperties, ReactNode } from 'react'

interface AppPageShellProps {
  children: ReactNode
  className?: string
}

interface AppPageContentProps {
  children: ReactNode
  className?: string
  size?: 'wide' | 'medium' | 'form'
  style?: CSSProperties
}

const contentWidths = {
  wide: 'max-w-[1180px]',
  medium: 'max-w-[860px]',
  form: 'max-w-[640px]',
}

export function AppPageShell({ children, className = '' }: AppPageShellProps) {
  return (
    <div className={`relative h-full w-full overflow-hidden bg-[var(--color-page-canvas)] ${className}`}>
      {children}
    </div>
  )
}

export function AppPageContent({ children, className = '', size = 'wide', style }: AppPageContentProps) {
  return (
    <div className={`mx-auto w-full ${contentWidths[size]} ${className}`} style={style}>
      {children}
    </div>
  )
}
