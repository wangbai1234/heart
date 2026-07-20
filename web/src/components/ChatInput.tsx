import { useState, type KeyboardEvent } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useAppStore } from '../stores/appStore'

interface Props {
  onSend: (text: string) => void
  onInterrupt: () => void
}

export function ChatInput({ onSend, onInterrupt }: Props) {
  const [text, setText] = useState('')
  const currentCharacterId = useAppStore((s) => s.currentCharacterId)
  const isStreaming = useChatStore((s) => s.isStreaming[currentCharacterId] ?? false)

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText('')
  }

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          className="flex-1 resize-none rounded-xl bg-[var(--color-surface-light)] text-[var(--color-text)]
                     placeholder-[var(--color-text-muted)] border border-[var(--color-border)]
                     px-4 py-3 focus:outline-none focus:border-[var(--color-primary)]
                     max-h-32 min-h-[48px] text-[16px]"
          placeholder="Type a message..."
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button
            onClick={onInterrupt}
            className="rounded-xl bg-[var(--color-error)] text-white px-5 py-3
                       hover:opacity-90 transition-opacity shrink-0"
          >
            Stop
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!text.trim()}
            className="rounded-xl bg-[var(--color-primary)] text-white px-5 py-3
                       hover:bg-[var(--color-primary-hover)] transition-colors shrink-0
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send
          </button>
        )}
      </div>
    </div>
  )
}
