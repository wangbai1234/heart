import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStoryStore, type StoryMessageVM } from '../stores/storyStore'
import { useStoryWebSocket } from '../hooks/useStoryWebSocket'
import { NavigationBar } from '../components/ui/NavigationBar'
import { Skeleton } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/ErrorState'
import { splitGmText } from '../utils/storyBubbles'

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

  const runMeta = useStoryStore((s) => s.runMetaById[runId])
  const messages = useStoryStore((s) => s.messagesByRun[runId])
  const streamText = useStoryStore((s) => s.streamTextByRun[runId])
  const generating = useStoryStore((s) => s.generatingByRun[runId] ?? false)
  const paused = useStoryStore((s) => s.pausedByRun[runId] ?? false)
  const runLoading = useStoryStore((s) => s.runLoading)
  const runError = useStoryStore((s) => s.runError)
  const loadRun = useStoryStore((s) => s.loadRun)

  const { sendMessage, interrupt } = useStoryWebSocket(runId)
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

  const handleSend = () => {
    const text = draft.trim()
    if (!text || generating || paused) return
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

  // Live-parse the in-flight stream into the SAME bubble structure the server
  // will commit, so correct 旁白/对话/action bubbles render during generation and
  // the final message_bubble frames land seamlessly (no grey-text-then-flash).
  const liveGroups =
    generating && streamText
      ? groupMessages(
          splitGmText(streamText).map((b, i) => ({
            id: `live-${i}`,
            turnId: null,
            seq: Number.MAX_SAFE_INTEGER,
            role: (b.kind === 'dialogue' ? 'npc' : 'gm') as StoryMessageVM['role'],
            kind: b.kind,
            npcName: b.npcName,
            content: b.content,
          })),
        )
      : []

  return (
    <div className="app-atmosphere relative flex h-full w-full flex-col overflow-hidden">
      <NavigationBar
        title={runMeta?.title ?? '剧情'}
        onBack={() => navigate('/explore')}
      />

      {/* AI-generated content disclaimer — fixed just below the (fixed) nav bar */}
      <div
        className="fixed left-0 right-0 z-[29] flex items-center justify-center py-1.5 px-4 bg-[var(--color-glass-55)] backdrop-blur-[var(--blur-glass-md)] border-b border-[var(--color-divider)]"
        style={{ top: 'calc(44px + var(--safe-top))' }}
      >
        <span className="text-[11px] text-[var(--color-text-muted)] text-center">
          内容由 AI 生成，对话请遵守社区公约
        </span>
      </div>

      <div
        ref={scrollRef}
        className="relative z-10 flex-1 overflow-y-auto px-4"
        style={{ paddingTop: 'calc(84px + var(--safe-top))' }}
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
            {/* 将连续的同角色消息分组，避免 action + dialogue 被分开显示 */}
            {groupMessages(messages ?? []).map((group, idx) => (
              <MessageGroup key={group.id || idx} group={group} />
            ))}
            {/* 流式输出：生成中把累积文本实时切成结构化气泡（与服务端最终提交的
                结构一致），收到 message_bubble 后无缝替换，不再出现灰色小字后整体刷新。 */}
            {liveGroups.length > 0
              ? liveGroups.map((group, idx) => (
                  <MessageGroup key={`live-${group.id || idx}`} group={group} />
                ))
              : generating && <TypingDots />}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div
        className="relative z-10 flex-shrink-0 border-t border-[var(--color-border-glass)] bg-[var(--color-glass-55)] backdrop-blur-[12px] px-3 pt-2.5"
        style={{ paddingBottom: 'calc(10px + var(--safe-bottom))' }}
      >
        {/* Per-minute billing ran dry → freeze input + prompt recharge. The run
            is saved; a successful charge after top-up auto-resumes it. */}
        {paused && (
          <div className="mb-2.5 flex items-center gap-3 rounded-[16px] bg-[var(--color-primary)]/10 border border-[var(--color-primary)]/30 px-3.5 py-2.5">
            <span className="flex-1 text-[13px] leading-[1.5] text-[var(--color-ink)]">
              余额不足，剧情已暂停。充值后可继续游玩，进度已保存。
            </span>
            <button
              onClick={() => navigate('/wallet')}
              className="shrink-0 h-[36px] rounded-[18px] bg-[var(--color-primary)] text-white px-4 text-[14px] font-semibold active:scale-[0.97] transition-transform"
            >
              去充值
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          <textarea
            className="flex-1 resize-none rounded-[20px] bg-[var(--color-surface)] text-[var(--color-ink)] placeholder-[var(--color-text-muted)] border border-[var(--color-border-glass)] px-4 py-2.5 focus:outline-none focus:border-[var(--color-primary)] max-h-32 min-h-[44px] text-[16px] disabled:opacity-50"
            placeholder={paused ? '充值后继续剧情…' : '描述你的行动或对白…'}
            rows={1}
            value={draft}
            disabled={paused}
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
              disabled={!draft.trim() || paused}
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

/**
 * 将连续的同角色消息分组，使 action + dialogue 能在同一气泡容器内显示。
 *
 * 示例：[action(NPC1), dialogue(NPC1), action(NPC1)] → 一组
 *       [dialogue(NPC2)] → 另一组
 */
interface MessageGroup {
  id: string
  role: string
  npcName: string | null
  messages: StoryMessageVM[]
}

function groupMessages(messages: StoryMessageVM[]): MessageGroup[] {
  const groups: MessageGroup[] = []
  let currentGroup: MessageGroup | null = null

  for (const msg of messages) {
    // Player 消息总是独立成组
    if (msg.role === 'player') {
      if (currentGroup) groups.push(currentGroup)
      groups.push({
        id: msg.id,
        role: msg.role,
        npcName: null,
        messages: [msg],
      })
      currentGroup = null
      continue
    }

    // NPC/GM 消息：同角色且相邻 → 合并到当前组
    const sameRole = currentGroup && currentGroup.role === msg.role
    const sameNpc = currentGroup && currentGroup.npcName === msg.npcName

    if (sameRole && sameNpc) {
      currentGroup!.messages.push(msg)
    } else {
      if (currentGroup) groups.push(currentGroup)
      currentGroup = {
        id: msg.id,
        role: msg.role,
        npcName: msg.npcName,
        messages: [msg],
      }
    }
  }

  if (currentGroup) groups.push(currentGroup)
  return groups
}

function MessageGroup({ group }: { group: MessageGroup }) {
  // Player 消息：右侧蓝色气泡
  if (group.role === 'player') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-[18px] rounded-br-[6px] bg-[var(--color-primary)] text-white px-4 py-2.5 text-[15px] leading-[1.6] whitespace-pre-wrap break-words">
          {group.messages[0].content}
        </div>
      </div>
    )
  }

  // NPC/GM 消息：action 和 dialogue 分别渲染
  return (
    <div className="flex flex-col gap-2 items-start max-w-[85%]">
      {/* NPC 名称（有且至少一条 dialogue 有非空台词才显示，避免空气泡上方的孤立名字） */}
      {group.npcName && group.messages.some((m) => m.kind === 'dialogue' && m.content.trim()) && (
        <span className="ml-1 text-[12px] font-semibold text-[var(--color-text-secondary)]">
          {group.npcName}
        </span>
      )}

      {/* 逐条渲染 action 和 dialogue */}
      {group.messages.map((msg, idx) => {
        if (msg.kind === 'action') {
          // Action：小灰色药丸，置于页面中间（不靠左）
          return (
            <div key={idx} className="w-full flex justify-center">
              <span className="inline-block px-3 py-1 text-[12px] leading-[1.5] text-[var(--color-text-muted)] bg-[var(--color-surface)] rounded-full border border-[var(--color-border)]">
                {msg.content}
              </span>
            </div>
          )
        }

        if (msg.kind === 'dialogue') {
          // Dialogue：白色气泡，去掉双引号
          const cleanContent = msg.content.replace(/^[""]|[""]$/g, '')
          // 空台词不渲染气泡（清理历史遗留的空 dialogue 行，杜绝空气泡）。
          if (!cleanContent.trim()) return null
          return (
            <div
              key={idx}
              className="rounded-[18px] rounded-tl-[6px] bg-[var(--color-surface)] border border-[var(--color-border-glass)] text-[var(--color-ink)] px-4 py-2.5 text-[15px] leading-[1.6] whitespace-pre-wrap break-words"
            >
              {cleanContent}
            </div>
          )
        }

        // Narration：居中灰色文字
        return (
          <div key={idx} className="w-full flex justify-center">
            <p className="max-w-[88%] text-center text-[14px] leading-[1.75] text-[var(--color-text-secondary)] whitespace-pre-wrap">
              {msg.content}
            </p>
          </div>
        )
      })}
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
