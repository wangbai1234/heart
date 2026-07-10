import type { ReactNode } from 'react'

interface InputProps {
  icon?: ReactNode
  placeholder?: string
  value?: string
  onChange?: (v: string) => void
  type?: string
  className?: string
}

export function Input({ icon, placeholder, value, onChange, type = 'text', className = '' }: InputProps) {
  return (
    <div className={`flex items-center gap-3 py-3 ${className}`}>
      {icon && <span className="text-[var(--color-primary)] shrink-0">{icon}</span>}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        className="flex-1 bg-transparent outline-none text-[var(--color-ink)] placeholder-[var(--color-text-placeholder)] text-base touch-manipulation"
      />
    </div>
  )
}
