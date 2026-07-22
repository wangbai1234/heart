import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useStoryStore, type StoryMessageVM } from '../stores/storyStore'
import { useStoryWebSocket } from '../hooks/useStoryWebSocket'
import { NavigationBar } from '../components/ui/NavigationBar'
import { Skeleton } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/ErrorState'

/**
 * Turn-based story player (/story/:runId).
 *
 * Renders the run transcript with role/kind-layered bubbles — GM narration
 * (centered grey italic), NPC dialogue (left, labelled with the speaker),
 * action hints (dim inline), and the player's own lines (right, primary). The
 * live GM turn streams into a transient narration bubble until the server's
 * split `message_bubble` frames replace it. All state lives in storyStore; this
 * page only reads it and forwards input to the story WebSocket.
 */
export function StoryPlayerPage() {
  const navigate = useNavigate()
  const { runId = '' } = useParams()
  const { resolvedTheme } = useThemeStore()

  const runMeta = useStoryStore((s) => s.runMetaById[runId])
  const messages = useStoryStore((s) => s.messagesByRun[runId])
  const streamText = useStoryStore((s) => s.streamTextByRun[runId])
  const generating = useStoryStore((s) => s.generatingByRun[runId] ?? false)
  const runLoading = useStoryStore((s) => s.runLoading)
  const runError = useStoryStore((s) => s.runError)
  const loadRun = useStoryStore((s) => s.loadRun)

  const { sendMessage, interrupt } = useStoryWebSocket()
  const [draft, setDraft] = useState('')
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (runId) void loadRun(runId)
  }, [runId, loadRun])

  // Keep pinned to the newest content as the turn streams / bubbles land.
  useLayoutEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, streamText, generating])

  const pageBg =
    resolvedTheme === 'dark'
      ? '/assets/backgrounds/暗色聊天背景图.png'
      : '/assets/backgrounds/聊天背景图.png'

  const handleSend = () => {
    const text = draft.trim()
    if (!text || generating) return
    const sent = sendMessage(runId, text)
    if (sent) setDraft('')
  }

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const showSkeleton = runLoading && !messages
  const showError = runError && !messages

  return (
    <div className="relative w-full h-full overflow-hidden flex flex-col">
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      <NavigationBar
        title={runMeta?.title ?? '剧情'}
        onBack={() => navigate('/explore')}
      />

      <div
        ref={scrollRef}
        className="relative z-10 flex-1 overflow-y-auto px-4"
        style={{ paddingTop: 'calc(52px + var(--safe-top))' }}
      >
        {showSkeleton ? (
          <PlayerSkeleton />
        ) : showError ? (
          <div className="pt-20">
            <ErrorState
              title="加载失败"
              description="这局剧情没能加载出来。"
              onRetry={() => void loadRun(runId, true)}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-3 pb-4">
            {(messages ?? []).map((m) => (
              <StoryBubble key={m.id} msg={m} />
            ))}
            {/* Live streaming GM turn (before split bubbles arrive). */}
            {streamText !== null && streamText !== undefined && streamText.length > 0 && (
              <NarrationBubble content={streamText} streaming />
            )}
            {generating && (streamText === null || streamText === '') && <TypingDots />}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div
        className="relative z-10 flex-shrink-0 border-t border-[var(--color-border-glass)] bg-[var(--color-glass-55)] backdrop-blur-[12px] px-3 pt-2.5"
        style={{ paddingBottom: 'calc(10px + var(--safe-bottom))' }}
      >
        <div className="flex items-end gap-2">
          <textarea
            className="flex-1 resize-none rounded-[20px] bg-[var(--color-surface)] text-[var(--color-ink)] placeholder-[var(--color-text-muted)] border border-[var(--color-border-glass)] px-4 py-2.5 focus:outline-none focus:border-[var(--color-primary)] max-h-32 min-h-[44px] text-[15px]"
            placeholder="描述你的行动或对白…"
            rows={1}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKey}
          />
          {generating ? (
            <button
              onClick={interrupt}
              className="shrink-0 h-[44px] rounded-[22px] bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] px-5 text-[15px] font-medium active:scale-[0.97] transition-transform"
            >
              停止
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!draft.trim()}
              className="shrink-0 h-[44px] rounded-[22px] bg-[var(--color-primary)] text-white px-5 text-[15px] font-semibold active:scale-[0.97] transition-transform disabled:opacity-40"
            >
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function StoryBubble({ msg }: { msg: StoryMessageVM }) {
  if (msg.role === 'player') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-[18px] rounded-br-[6px] bg-[var(--color-primary)] text-white px-4 py-2.5 text-[15px] leading-[1.6] whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    )
  }
  if (msg.kind === 'dialogue') {
    return (
      <div className="flex flex-col items-start max-w-[85%]">
        {msg.npcName && (
          <span className="ml-1 mb-1 text-[12px] font-semibold text-[var(--color-text-secondary)]">
            {msg.npcName}
          </span>
        )}
        <div className="rounded-[18px] rounded-tl-[6px] bg-[var(--color-surface)] border border-[var(--color-border-glass)] text-[var(--color-ink)] px-4 py-2.5 text-[15px] leading-[1.6] whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    )
  }
  if (msg.kind === 'action') {
    return (
      <div className="flex justify-center">
        <p className="max-w-[85%] text-center text-[13px] italic text-[var(--color-text-muted)] leading-[1.6] whitespace-pre-wrap">
          （{msg.content}）
        </p>
      </div>
    )
  }
  return <NarrationBubble content={msg.content} />
}

function NarrationBubble({ content, streaming }: { content: string; streaming?: boolean }) {
  return (
    <div className="flex justify-center">
      <p className="max-w-[88%] text-center text-[14px] leading-[1.75] text-[var(--color-text-secondary)] whitespace-pre-wrap">
        {content}
        {streaming && <span className="animate-pulse">▍</span>}
      </p>
    </div>
  )
}

function TypingDots() {
  return (
    <div className="flex justify-center py-2">
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 rounded-full bg-[var(--color-text-muted)] animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}

function PlayerSkeleton() {
  return (
    <div className="flex flex-col gap-3 pt-6">
      <Skeleton className="h-[60px] w-3/4 mx-auto rounded-[18px]" />
      <Skeleton className="h-[44px] w-2/3 rounded-[18px]" />
      <Skeleton className="h-[52px] w-1/2 self-end rounded-[18px]" />
    </div>
  )
}
