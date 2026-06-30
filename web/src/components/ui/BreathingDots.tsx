interface BreathingDotsProps {
  className?: string
  /** Animation cycle duration. Default 600ms for typing indicator. Use 1200ms for splash. */
  cycleDuration?: number
}

export function BreathingDots({ className = '', cycleDuration = 600 }: BreathingDotsProps) {
  return (
    <div className={`flex items-center gap-[6px] ${className}`}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="rounded-full"
          style={{
            width: 10,
            height: 10,
            backgroundColor: '#FFB7C5',
            animation: `breathe-dot ${cycleDuration}ms ease-in-out infinite`,
            animationDelay: `${i * (cycleDuration / 4)}ms`,
          }}
        />
      ))}
    </div>
  )
}
