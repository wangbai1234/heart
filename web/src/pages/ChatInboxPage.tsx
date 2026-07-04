import { useNavigate } from 'react-router-dom'
import { Avatar } from '../components/ui/Avatar'
import { TabBar } from '../components/ui/TabBar'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import {
  CHARACTER_PROFILES,
  CONVERSATION_THREADS,
  formatConversationTime,
  getMessagePreview,
  getUnreadMessageCount,
  type CharacterId,
} from '../data/uiContent'

type TimelineMessage = {
  role: 'assistant' | 'user'
  content: string
  timestamp: number
  kind?: 'text' | 'voice'
  duration?: string
  audioDuration?: number
}

export function ChatInboxPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const currentCharacterId = useAppStore((s) => s.currentCharacterId)
  const setCharacter = useAppStore((s) => s.setCharacter)
  const threads = useChatStore((s) => s.threads)
  const messages = useChatStore((s) => s.messages)
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)

  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  const conversations = (Object.keys(CHARACTER_PROFILES) as CharacterId[]).map((characterId) => {
    const liveMessages = messages[characterId] ?? []
    const threadMessages = threads[characterId] ?? []
    const fallbackMessages = CONVERSATION_THREADS[characterId] ?? []
    const timeline = (liveMessages.length > 0 ? liveMessages : threadMessages.length > 0 ? threadMessages : fallbackMessages) as TimelineMessage[]
    const previewTimeline = timeline.map((item) => ({
      ...item,
      kind: item.kind ?? 'text',
    }))
    const lastMessage = timeline[timeline.length - 1]
    const unreadCount = getUnreadMessageCount(timeline)

    return {
      profile: CHARACTER_PROFILES[characterId],
      characterId,
      preview: getMessagePreview(previewTimeline),
      updatedAt: lastMessage ? formatConversationTime(lastMessage.timestamp) : '刚刚',
      unreadCount,
      isSelected: currentCharacterId === characterId,
      totalMessages: timeline.length,
    }
  })

  return (
    <div className="relative h-full overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 h-full w-full object-cover" />

      <div className="relative z-10 flex h-full flex-col">
        <div style={{ height: 'var(--safe-top)' }} />

        <header className="flex items-center justify-between px-5 py-3">
          <div>
            <p className="text-[12px] tracking-[0.12em] text-[var(--color-text-muted)]">MESSAGES</p>
            <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-[var(--color-ink)]">聊天列表</h1>
          </div>
          <button
            onClick={() => navigate('/character')}
            className="inline-flex h-[42px] items-center rounded-full border border-[var(--color-border-glass)] bg-[var(--color-glass-55)] px-4 text-[13px] text-[var(--color-ink)] backdrop-blur-[12px] active:scale-[0.97] transition-transform"
          >
            切换角色
          </button>
        </header>

        <div className="px-4">
          <div className="rounded-[24px] border border-[var(--color-border-glass)] bg-[var(--color-glass-35)] px-4 py-4 backdrop-blur-[16px] shadow-[var(--shadow-soft)]">
            <p className="text-[14px] font-medium text-[var(--color-ink)]">现在进入聊天会先展示消息列表</p>
            <p className="mt-2 text-[13px] leading-[1.65] text-[var(--color-text-secondary)]">
              选择一个角色查看最近消息与未读状态，再进入具体会话页面继续聊天。
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-[180px] pt-4">
          <div className="space-y-3">
            {conversations.map((conversation) => (
              <button
                key={conversation.characterId}
                onClick={() => {
                  setCharacter(conversation.characterId)
                  setActiveCharacter(conversation.characterId)
                  navigate(`/chat/${conversation.characterId}`)
                }}
                className={`w-full rounded-[24px] border px-4 py-4 text-left backdrop-blur-[16px] transition-transform active:scale-[0.985] ${
                  conversation.isSelected
                    ? 'border-[rgba(255,183,197,0.38)] bg-[var(--color-glass-75)] shadow-[var(--shadow-card)]'
                    : 'border-[var(--color-border-glass)] bg-[var(--color-glass-35)] shadow-[var(--shadow-soft)]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Avatar src={conversation.profile.avatar} size={58} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-[17px] font-semibold text-[var(--color-ink)]">
                        {conversation.profile.name}
                      </p>
                      <span
                        className="inline-flex h-6 items-center rounded-full px-2.5 text-[11px] font-medium"
                        style={{
                          color: conversation.profile.tagColor,
                          backgroundColor: conversation.profile.tagBg,
                        }}
                      >
                        {conversation.profile.tag}
                      </span>
                    </div>
                    <p className="mt-1 text-[13px] text-[var(--color-text-secondary)]">
                      {conversation.profile.statusLabel}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-[12px] text-[var(--color-text-muted)]">{conversation.updatedAt}</p>
                    {conversation.unreadCount > 0 ? (
                      <span className="mt-2 inline-flex min-w-[24px] items-center justify-center rounded-full bg-[var(--color-unread-badge)] px-2 py-[2px] text-[11px] font-semibold text-white">
                        {conversation.unreadCount}
                      </span>
                    ) : (
                      <span className="mt-2 inline-flex rounded-full bg-[rgba(255,255,255,0.36)] px-2.5 py-[2px] text-[11px] text-[var(--color-text-muted)]">
                        已读
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-4 rounded-[18px] bg-[rgba(255,255,255,0.3)] px-3.5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-[14px] font-medium text-[var(--color-ink)]">
                      {conversation.preview}
                    </p>
                    <span className="shrink-0 text-[12px] text-[var(--color-text-muted)]">
                      {conversation.totalMessages} 条
                    </span>
                  </div>
                  <p className="mt-2 text-[12px] leading-[1.55] text-[var(--color-text-secondary)]">
                    点击进入与{conversation.profile.shortName}的具体聊天页面。
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <TabBar />
      </div>
    </div>
  )
}
