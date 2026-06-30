import { useChatStore } from '../stores/chatStore'
import VoiceMessageBubble from './VoiceMessageBubble'

export function MessageList() {
  const messages = useChatStore((s) => s.messages)

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
          <p className="text-lg">Start a conversation...</p>
        </div>
      )}
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[70%] rounded-2xl px-4 py-3 space-y-2 ${
              msg.role === 'user'
                ? 'bg-[var(--color-primary)] text-white'
                : 'bg-[var(--color-surface-light)] text-[var(--color-text)]'
            }`}
          >
            <p className="whitespace-pre-wrap break-words">{msg.content}</p>
            {msg.role === 'assistant' && msg.audioData && (
              <VoiceMessageBubble
                audioData={msg.audioData}
                duration={msg.audioDuration ?? 0}
                format={msg.audioFormat ?? 'wav'}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
