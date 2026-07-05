interface ChatBubbleProps {
  type: 'ai' | 'user'
  children: React.ReactNode
  className?: string
}

export function ChatBubble({ type, children, className = '' }: ChatBubbleProps) {
  const isAI = type === 'ai'

  return (
    <div
      className={`
        max-w-[67%] px-4 py-[14px]
        ${isAI
          ? 'self-start bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] shadow-[var(--shadow-soft)] border border-[var(--color-border-glass)]'
          : 'self-end bg-gradient-to-br from-[#A7C7E7] to-[#BFD7EE] rounded-[6px_20px_20px_20px] text-white'
        }
        ${className}
      `}
    >
      <p className={`text-[16px] leading-[1.6] ${isAI ? 'text-[var(--color-ink)]' : 'text-white'}`}>
        {children}
      </p>
    </div>
  )
}
