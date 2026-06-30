interface AvatarProps {
  src?: string | null
  alt?: string
  size?: number
  className?: string
  /** Add a 2px white border (for profile avatars per spec) */
  border?: boolean
}

export function Avatar({ src, alt = '', size = 40, className = '', border = false }: AvatarProps) {
  const borderStyle = border ? 'border-2 border-white' : ''

  if (!src) {
    return (
      <div
        className={`rounded-full bg-[var(--color-glass-55)] backdrop-blur-[var(--blur-glass-sm)] flex items-center justify-center ${borderStyle} ${className}`}
        style={{ width: size, height: size }}
      >
        <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
        </svg>
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      className={`rounded-full object-cover ${borderStyle} ${className}`}
      style={{ width: size, height: size }}
    />
  )
}
