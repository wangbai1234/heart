import { MessageList } from '../components/MessageList'
import { ChatInput } from '../components/ChatInput'
import { EmotionOrb } from '../components/EmotionOrb'
import { CharacterSelector } from '../components/CharacterSelector'
import { useWebSocket } from '../hooks/useWebSocket'

export function ChatPage() {
  const { sendMessage, interrupt } = useWebSocket()

  return (
    <div className="flex flex-col h-full max-w-2xl mx-auto">
      <header className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <h1 className="text-lg font-semibold">Heart</h1>
        <CharacterSelector />
        <EmotionOrb />
      </header>
      <MessageList />
      <ChatInput onSend={sendMessage} onInterrupt={interrupt} />
    </div>
  )
}
