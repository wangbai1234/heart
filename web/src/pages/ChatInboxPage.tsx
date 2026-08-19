import { useState, useRef, useCallback, useEffect } from 'react'
import { useScrollRestore } from '../hooks/useScrollRestore'
import { useNavigate } from 'react-router-dom'
import { Avatar } from '../components/ui/Avatar'
import { TabBar } from '../components/ui/TabBar'
import { Dialog } from '../components/ui/Dialog'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { useProactiveStore } from '../stores/proactiveStore'
import { useCharactersStore } from '../stores/charactersStore'
import { getInboxSummary } from '../services/api'
import {
  CHARACTER_PROFILES,
  formatConversationTime,
  getMessagePreview,
  resolveCharacterProfile,
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

function SwipeableRow({ children, onDelete }: { children: React.ReactNode; onDelete: () => void }) {
  const [offsetX, setOffsetX] = useState(0)
  const startX = useRef(0)
  const currentOffset = useRef(0)
  const swiping = useRef(false)
  const isOpen = offsetX <= -40

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX
    currentOffset.current = offsetX
    swiping.current = false
  }, [offsetX])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const dx = e.touches[0].clientX - startX.current
    if (Math.abs(dx) > 8) swiping.current = true
    const next = Math.max(-80, Math.min(0, currentOffset.current + dx))
    setOffsetX(next)
  }, [])

  const handleTouchEnd = useCallback(() => {
    setOffsetX(offsetX < -40 ? -80 : 0)
  }, [offsetX])

  return (
    <div className="relative overflow-hidden rounded-[24px]">
      <div className="absolute inset-0 rounded-[24px] bg-transparent" />
      <div
        className={`absolute inset-y-0 right-0 flex items-center justify-end transition-opacity duration-150 ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        style={{ width: 80 }}
      >
        <button
          onClick={(e) => { e.stopPropagation(); onDelete() }}
          className="flex h-full w-full items-center justify-center rounded-r-[24px] bg-[#FF5A5A] text-[14px] font-semibold text-white"
        >
          删除
        </button>
      </div>
      <div
        className="relative z-10 transition-transform duration-200 ease-out"
        style={{ transform: `translateX(${offsetX}px)` }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {children}
      </div>
    </div>
  )
}

export function ChatInboxPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const currentCharacterId = useAppStore((s) => s.currentCharacterId)
  const setCharacter = useAppStore((s) => s.setCharacter)
  const threads = useChatStore((s) => s.threads)
  const messages = useChatStore((s) => s.messages)
  const pendingByChar = useProactiveStore((s) => s.pendingByChar)
  const drainProactive = useProactiveStore((s) => s.drain)
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const clearThread = useChatStore((s) => s.clearThread)
  const clearMessages = useChatStore((s) => s.clearMessages)
  const hideInbox = useChatStore((s) => s.hideInbox)
  const inboxHidden = useChatStore((s) => s.inboxHidden)
  const serverCharacters = useCharactersStore((s) => s.characters)
  const setInboxUnreadTotal = useAppStore((s) => s.setInboxUnreadTotal)
  const scrollRef = useScrollRestore()
  const [deleteTarget, setDeleteTarget] = useState<CharacterId | null>(null)
  const [inboxSummary, setInboxSummary] = useState<Record<string, { lastText: string; lastAt: number; serverUnread: number }>>({})

  useEffect(() => {
    getInboxSummary()
      .then((res) => {
        const map: Record<string, { lastText: string; lastAt: number; serverUnread: number }> = {}
        for (const item of res.items) {
          map[item.character_id] = {
            lastText: item.last_message_text,
            lastAt: item.last_message_at ? new Date(item.last_message_at).getTime() : 0,
            serverUnread: item.unread_count ?? 0,
          }
        }
        setInboxSummary(map)
      })
      .catch(() => {})
  }, [])

  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.webp'
    : '/assets/backgrounds/聊天背景图.webp'

  // Catalog: server list when loaded, built-in profiles as fallback.
  const catalog: Array<{ id: string; displayName?: string; avatarUrl?: string | null; coverUrl?: string | null; isOwner: boolean }> =
    serverCharacters.length > 0
      ? serverCharacters.map((c) => ({ id: c.id, displayName: c.display_name, avatarUrl: c.avatar_url, coverUrl: c.cover_url, isOwner: c.is_owner && !c.is_builtin }))
      : Object.keys(CHARACTER_PROFILES).map((id) => ({ id, isOwner: false }))

  const allConversations = catalog.map(({ id: characterId, displayName, avatarUrl, coverUrl, isOwner }) => {
    const liveMessages = messages[characterId] ?? []
    const threadMessages = threads[characterId] ?? []
    const timeline = (liveMessages.length > 0 ? liveMessages : threadMessages) as TimelineMessage[]
    const previewTimeline = timeline.map((item) => ({
      ...item,
      kind: item.kind ?? 'text',
      audioDuration: item.audioDuration,
    }))
    const lastMessage = timeline[timeline.length - 1]
    const serverSummary = inboxSummary[characterId]

    // Proactive messages (SS06) not yet opened: count as unread and, when newest,
    // drive the preview so the user knows the character reached out.
    const pending = pendingByChar[characterId] ?? []
    const latestPending = pending[pending.length - 1]

    // Use the most authoritative timestamp: proactive > local timeline > server summary
    const localTimestamp = lastMessage?.timestamp ?? 0
    const serverTimestamp = serverSummary?.lastAt ?? 0
    const baseTimestamp = Math.max(localTimestamp, serverTimestamp)
    const lastTimestamp = latestPending
      ? Math.max(baseTimestamp, new Date(latestPending.created_at).getTime())
      : baseTimestamp

    // Preview: proactive > local > server
    const localPreview = getMessagePreview(previewTimeline)
    const preview = latestPending
      ? latestPending.content
      : (localPreview || serverSummary?.lastText || '')

    // Prefer server unread_count (accurate); fall back to proactive-only count when
    // server hasn't responded yet so the badge isn't stuck at 0 before first fetch.
    const unreadCount = serverSummary
      ? serverSummary.serverUnread + pending.length
      : pending.length
    const totalMessages = timeline.length + pending.length + (serverSummary ? 1 : 0)

    return {
      profile: resolveCharacterProfile(characterId, displayName, avatarUrl, { isOwner, coverUrl }),
      characterId,
      preview,
      updatedAt: lastTimestamp ? formatConversationTime(lastTimestamp) : '',
      unreadCount,
      isSelected: currentCharacterId === characterId,
      totalMessages,
      lastTimestamp,
    }
  })

  // Filter out characters with no history at all AND rows the user swiped away
  // on this device (local-only hide), then sort newest-first. Swiped rows are
  // un-hidden by the store as soon as the character sees new activity.
  const conversations = allConversations
    .filter((c) => c.totalMessages > 0 && !inboxHidden.includes(c.characterId))
    .sort((a, b) => b.lastTimestamp - a.lastTimestamp)

  const totalUnreadCount = conversations.reduce((sum, c) => sum + c.unreadCount, 0)

  // Sync badge count to global store so App.tsx can drive useAppBadge even
  // when the user is on a different page.
  useEffect(() => {
    setInboxUnreadTotal(totalUnreadCount)
  }, [totalUnreadCount, setInboxUnreadTotal])

  // Swipe-away is a LOCAL, presentation-only hide: it removes the row from THIS
  // device's inbox and nothing else. No server call — the conversation history
  // and the character's memory stay fully intact (reopening the character, or a
  // new proactive message, brings the row straight back via the store's un-hide
  // on addMessage/reconcileHistory). Persisted to localStorage so the row stays
  // hidden across reloads on this device; a cache clear / new device shows it again.
  const handleDelete = (characterId: CharacterId) => {
    hideInbox(characterId)
    clearThread(characterId)
    clearMessages(characterId)
    drainProactive(characterId)
    setInboxSummary((prev) => {
      const next = { ...prev }
      delete next[characterId]
      return next
    })
    setDeleteTarget(null)
  }

  return (
    <div className="relative h-full overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 h-full w-full object-cover" />

      <div className="relative z-10 flex h-full flex-col">
        <div style={{ height: 'var(--safe-top)' }} />

        <header className="relative px-5 pt-3 pb-2">
          <div className="inline-block">
            <h1 className="text-[20px] font-semibold tracking-[-0.02em] text-[var(--color-ink)] mb-1">最近聊天</h1>
            <div className="h-[3px] w-full bg-gradient-to-r from-[var(--color-primary)] via-[var(--color-primary)]/60 to-transparent rounded-full" />
          </div>
          {totalUnreadCount > 0 && (
            <p className="mt-1.5 text-[13px] font-medium text-[var(--color-text-secondary)]">
              {totalUnreadCount} 条未读
            </p>
          )}
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pb-[180px] pt-4">
          {conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center pt-20">
              <p className="text-[15px] text-[var(--color-text-muted)]">暂无聊天记录</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conversations.map((conversation) => (
                <SwipeableRow
                  key={conversation.characterId}
                  onDelete={() => setDeleteTarget(conversation.characterId)}
                >
                  <button
                    onClick={() => {
                      setCharacter(conversation.characterId)
                      setActiveCharacter(conversation.characterId)
                      navigate(`/chat/${conversation.characterId}`)
                    }}
                    className={`w-full rounded-[24px] border px-5 py-5 text-left backdrop-blur-[16px] transition-all duration-[var(--duration-fast)] active:scale-[0.985] ${
                      conversation.isSelected
                        ? 'border-[var(--color-border-glass)] bg-[var(--color-glass-75)] shadow-[var(--shadow-sheet)] scale-[1.01]'
                        : 'border-[var(--color-border-glass)] bg-[var(--color-glass-65)] shadow-[var(--shadow-soft)] hover:bg-[var(--color-glass-75)]'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <Avatar src={conversation.profile.cover ?? conversation.profile.avatar} size={58} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="truncate text-[17px] font-semibold text-[var(--color-ink)]">
                            {conversation.profile.name}
                          </p>
                          <span
                            className="inline-flex h-6 items-center rounded-md px-2.5 text-[11px] font-medium"
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
                        <p className="mt-3 font-normal text-[14px] text-[var(--color-text-secondary)] line-clamp-2">
                          {conversation.preview}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <p className="text-[12px] text-[var(--color-text-muted)]">{conversation.updatedAt}</p>
                        {conversation.unreadCount > 0 && (
                          <span className="inline-flex min-w-[24px] items-center justify-center rounded-full bg-[var(--color-unread-badge)] px-2 py-[2px] text-[11px] font-semibold text-white">
                            {conversation.unreadCount}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                </SwipeableRow>
              ))}
            </div>
          )}
        </div>

        <TabBar />
      </div>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="确认删除聊天记录？"
        actions={
          <>
            <button
              onClick={() => setDeleteTarget(null)}
              className={`flex-1 rounded-full px-4 py-3 text-[15px] font-medium ${
                resolvedTheme === 'dark'
                  ? 'bg-[rgba(255,255,255,0.06)] text-[#ECE9F4]'
                  : 'bg-[rgba(255,255,255,0.75)] text-[#30344A]'
              }`}
            >
              取消
            </button>
            <button
              onClick={() => {
                if (deleteTarget) {
                  handleDelete(deleteTarget)
                }
              }}
              className="flex-1 rounded-full bg-[#FF5A5A] px-4 py-3 text-[15px] font-semibold text-white"
            >
              删除
            </button>
          </>
        }
      >
        删除后只会隐藏当前设备上的页面消息，服务端聊天记录和角色记忆不会被删除。
      </Dialog>
    </div>
  )
}
