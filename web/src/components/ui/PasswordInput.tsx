import { useState, type ReactNode } from 'react'

interface PasswordInputProps {
  icon?: ReactNode
  placeholder?: string
  value?: string
  onChange?: (v: string) => void
  className?: string
  autoComplete?: string
}

/**
 * Password field with a show/hide eye toggle. Styled to match `Input`
 * (transparent bg, left icon, --color-ink text) so it slots into the same
 * glass form cards without introducing any new palette. Used across the
 * register / login / forgot-password / change-password flows.
 */
export function PasswordInput({
  icon,
  placeholder,
  value,
  onChange,
  className = '',
  autoComplete = 'current-password',
}: PasswordInputProps) {
  const [show, setShow] = useState(false)

  return (
    <div className={`flex items-center gap-3 py-3 ${className}`}>
      {icon && <span className="text-[var(--color-primary)] shrink-0">{icon}</span>}
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className="flex-1 min-w-0 bg-transparent outline-none text-[var(--color-ink)] placeholder-[var(--color-text-placeholder)] text-base touch-manipulation"
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="shrink-0 text-[var(--color-text-muted)] active:opacity-60 touch-manipulation"
        aria-label={show ? '隐藏密码' : '显示密码'}
      >
        {show ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  )
}
