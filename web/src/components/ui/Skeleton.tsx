interface SkeletonProps {
  className?: string
  variant?: 'rect' | 'circle' | 'text'
  width?: number | string
  height?: number | string
}

export function Skeleton({ className = '', variant = 'rect', width, height }: SkeletonProps) {
  const base = 'relative overflow-hidden bg-[var(--color-glass-35)] rounded-[var(--radius-md)]'

  const shapeClass =
    variant === 'circle' ? 'rounded-full' :
    variant === 'text' ? 'rounded-[var(--radius-xs)]' :
    ''

  return (
    <div
      className={`${base} ${shapeClass} ${className}`}
      style={{ width, height }}
    >
      <div className="absolute inset-0 animate-[shimmer_1200ms_infinite] bg-gradient-to-r from-transparent via-white/30 to-transparent" />
    </div>
  )
}
