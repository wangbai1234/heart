import { useEffect, useRef, useState, useCallback, type ComponentType } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { useChatStore, type Message } from '../stores/chatStore'
import { useAuthStore } from '../stores/authStore'
import { CHARACTER_PROFILES, resolveCharacterProfile, shouldShowTimestamp, formatChatTime, type CharacterId } from '../data/uiContent'
import { CHARACTER_UI_CONFIGS } from '../data/characterUIConfig'
import { useCharactersStore } from '../stores/charactersStore'
import { useCompanionsStore } from '../stores/companionsStore'
import { stageLabel, stageWithIntimacy, stageOrderIndex } from '../utils/relationship'
import { useWebSocket } from '../hooks/useWebSocket'
import { useProactiveStore } from '../stores/proactiveStore'
import { getChatHistory, generateOpening, ackProactive, markCharacterRead, transcribeAudio, getCharacterVoice, sendTransfer } from '../services/api'
import { useToastStore } from '../stores/toastStore'
// DISABLED 2026-07-24: 角色↔剧情关联功能暂停，见下方渲染块注释
// import { StoryInviteCard, isHookOnCooldown } from './StoryInviteCard'
import { BreathingDots } from './ui/BreathingDots'
import { NoticeDialog } from './ui/NoticeDialog'
import { Avatar } from './ui/Avatar'
import VoiceMessageBubble from './VoiceMessageBubble'
import { useSwipeNavigation } from '../hooks/useSwipeNavigation'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { VoiceRecordingOverlay } from './VoiceRecordingOverlay'
import { TextTierSheet } from './TextTierSheet'
import { ChatPlusMenu } from './ChatPlusMenu'
import { VoiceChatSheet } from './VoiceChatSheet'
import { TransferSheet } from './TransferSheet'
import { JiYuPremiseCard } from './characterProfiles/JiYuPremiseCard'
import { ChengXuPremiseCard } from './characterProfiles/ChengXuPremiseCard'
import { LiShenPremiseCard } from './characterProfiles/LiShenPremiseCard'
import { GuBeichenPremiseCard } from './characterProfiles/GuBeichenPremiseCard'
import { QinXiaoPremiseCard } from './characterProfiles/QinXiaoPremiseCard'
import { JiangYuezePremiseCard } from './characterProfiles/JiangYuezePremiseCard'
import { JiangYePremiseCard } from './characterProfiles/JiangYePremiseCard'
import { GuXingzhouPremiseCard } from './characterProfiles/GuXingzhouPremiseCard'
import { LiJuePremiseCard } from './characterProfiles/LiJuePremiseCard'
import { ShenYichenPremiseCard } from './characterProfiles/ShenYichenPremiseCard'
import { ShenYuchuanPremiseCard } from './characterProfiles/ShenYuchuanPremiseCard'
import { LuoFeiPremiseCard } from './characterProfiles/LuoFeiPremiseCard'
import { PeiTinglanPremiseCard } from './characterProfiles/PeiTinglanPremiseCard'
import { FuMingxiuPremiseCard } from './characterProfiles/FuMingxiuPremiseCard'
import { XizePremiseCard } from './characterProfiles/XizePremiseCard'
import { JiangLiPremiseCard } from './characterProfiles/JiangLiPremiseCard'
import { LilithPremiseCard } from './characterProfiles/LilithPremiseCard'
import { PeiJuePremiseCard } from './characterProfiles/PeiJuePremiseCard'
import { HuoChengPremiseCard } from './characterProfiles/HuoChengPremiseCard'
import { ZhouJinPremiseCard } from './characterProfiles/ZhouJinPremiseCard'
import { BaiQinghuanPremiseCard } from './characterProfiles/BaiQinghuanPremiseCard'
import { ChengZhiPremiseCard } from './characterProfiles/ChengZhiPremiseCard'
import { getCharacterSettings } from '../services/api'

const EMPTY_MESSAGES: Message[] = []

/** 角色专属前情提要卡映射：首聊无用户消息时出现在开场之上 */
const PREMISE_CARDS: Record<string, ComponentType> = {
  ji_yu: JiYuPremiseCard,
  cheng_xu: ChengXuPremiseCard,
  li_shen: LiShenPremiseCard,
  gu_beichen: GuBeichenPremiseCard,
  qin_xiao: QinXiaoPremiseCard,
  jiang_yueze: JiangYuezePremiseCard,
  jiang_ye: JiangYePremiseCard,
  gu_xingzhou: GuXingzhouPremiseCard,
  li_jue: LiJuePremiseCard,
  shen_yichen: ShenYichenPremiseCard,
  shen_yuchuan: ShenYuchuanPremiseCard,
  luo_fei: LuoFeiPremiseCard,
  pei_tinglan: PeiTinglanPremiseCard,
  fu_mingxiu: FuMingxiuPremiseCard,
  xize: XizePremiseCard,
  jiang_li: JiangLiPremiseCard,
  lilith: LilithPremiseCard,
  pei_jue: PeiJuePremiseCard,
  huo_cheng: HuoChengPremiseCard,
  zhou_jin: ZhouJinPremiseCard,
  bai_qinghuan: BaiQinghuanPremiseCard,
  cheng_zhi: ChengZhiPremiseCard,
}

/** 引导回复气泡：首聊时出现在消息区底部，点击直接发送（帮用户破冰）。
 * 优先取角色专属开场白(characterUIConfig.starterPrompts)，缺省用通用三句。*/
const FALLBACK_STARTER_PROMPTS: [string, string, string] = [
  '你还好吗？',
  '聊聊你的故事？',
  '有点好奇你在做什么',
]

// Map a server chat-history item to a store Message. Voice rows get an
// unambiguous by-message-id audio pointer (keyed on the row id, so it needs no
// role param). Shared by the mount load and the visibilitychange sync so both
// feed reconcileHistory identical shapes.
type HistoryItem = Awaited<ReturnType<typeof getChatHistory>>['items'][number]
function historyItemToMessage(item: HistoryItem): Message {
  const isVoice = item.modality === 'voice'
  return {
    id: item.id,
    turnId: item.turn_id ?? undefined,
    role: item.role as 'user' | 'assistant',
    content: item.content,
    timestamp: new Date(item.created_at).getTime(),
    // Prefer the server-provided kind (TEST_REPORT_20260712 BUG-5). Falls back
    // to modality when the server response is old (no `kind` field).
    kind: item.kind === 'action'
      ? 'action'
      : item.kind === 'call_summary'
        ? 'call_summary'
        : item.kind === 'transfer'
          ? 'transfer'
          : item.kind === 'transfer_receipt'
            ? 'transfer_receipt'
            : isVoice ? 'voice' : 'text',
    audioUrl: isVoice && item.audio_url ? `/api/chat/audio/${item.id}` : undefined,
    audioDuration: item.audio_duration_ms ?? undefined,
    audioFormat: isVoice ? 'wav' : undefined,
  }
}

interface ConversationChatPageProps {
  isDark: boolean
}

export function ConversationChatPage({ isDark }: ConversationChatPageProps) {
  const navigate = useNavigate()
  const params = useParams<{ characterId?: string }>()
  const [input, setInput] = useState('')
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [generatingOpening, setGeneratingOpening] = useState(false)
  const [expandedVoiceTextIds, setExpandedVoiceTextIds] = useState<Set<string>>(new Set())
  // 分支式首聊引导：选中的切入角度索引（null = 未选，展示角度列表）
  const [starterBranch, setStarterBranch] = useState<number | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Input-area sheets (migrated from the deleted /character-backstage page).
  const [textTierOpen, setTextTierOpen] = useState(false)
  const [plusMenuOpen, setPlusMenuOpen] = useState(false)
  const [voiceChatOpen, setVoiceChatOpen] = useState(false)
  const [transferOpen, setTransferOpen] = useState(false)
  const [transferSending, setTransferSending] = useState(false)

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false)
  const [willCancel, setWillCancel] = useState(false)
  const [recordingToast, setRecordingToast] = useState<string | null>(null)
  const cancelZoneRef = useRef<HTMLDivElement | null>(null)
  const recorder = useVoiceRecorder()

  // Bond-center relationship status (Wave 2 event cards). Purely additive —
  // does not touch voice / proactive / WS logic.
  const [upgradeStage, setUpgradeStage] = useState<string | null>(null)
  // DISABLED 2026-07-24: hookDismissed 仅供剧情邀约卡使用，功能暂停
  // const [hookDismissed, setHookDismissed] = useState(false)
  const companions = useCompanionsStore((s) => s.companions)
  const loadCompanions = useCompanionsStore((s) => s.load)

  // Right-swipe from left edge → back to chat list
  useSwipeNavigation({ onRightSwipe: () => navigate('/chat') })

  const storedCharacterId = useAppStore((s) => s.currentCharacterId)
  const setCharacter = useAppStore((s) => s.setCharacter)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const userAvatar = useAuthStore((s) => s.user?.avatar_url ?? null)
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const serverCharacters = useCharactersStore((s) => s.characters)
  const catalogLoaded = useCharactersStore((s) => s.loaded)

  // Known ids = built-ins (always, for cold-load direct links) ∪ server catalog.
  const knownIds = new Set<string>([
    ...Object.keys(CHARACTER_PROFILES),
    ...serverCharacters.map((c) => c.id),
  ])
  const routeCharacterId = params.characterId
  const isValidCharacterId = !!routeCharacterId && knownIds.has(routeCharacterId)
  const currentCharacterId = (isValidCharacterId ? routeCharacterId : storedCharacterId) as CharacterId

  const messages = useChatStore((s) => s.messages[currentCharacterId as CharacterId] ?? EMPTY_MESSAGES)
  const isCleared = useChatStore((s) => s.clearedCharacters.has(currentCharacterId as CharacterId))
  const isStreaming = useChatStore((s) => s.isStreaming[currentCharacterId as CharacterId] ?? false)
  const isPlaying = useChatStore((s) => s.isPlaying)
  const addMessage = useChatStore((s) => s.addMessage)
  const reconcileHistory = useChatStore((s) => s.reconcileHistory)
  const setCharacterId = useChatStore((s) => s.setCharacterId)
  const appendMessage = useChatStore((s) => s.appendMessage)
  const setLastFetchedAt = useChatStore((s) => s.setLastFetchedAt)
  const setMessageAudioUrl = useChatStore((s) => s.setMessageAudioUrl)
  const isGenerating = useChatStore((s) => s.isGenerating[currentCharacterId as CharacterId] ?? false)
  const insufficientCredits = useChatStore((s) => s.insufficientCredits)
  const clearInsufficientCredits = useChatStore((s) => s.clearInsufficientCredits)
  const modelForbidden = useChatStore((s) => s.modelForbidden)
  const clearModelForbidden = useChatStore((s) => s.clearModelForbidden)

  const { sendMessage, interrupt } = useWebSocket()

  // Current text tier (deepseek/grok) for the input-bar entry label.
  const chatModel = useAppStore((s) => s.chatModel[currentCharacterId as CharacterId] ?? 'deepseek')
  const setVoiceChatEnabled = useAppStore((s) => s.setVoiceChatEnabled)
  const textTierLabel = chatModel === 'grok' ? '私密陪伴' : '普通交流'

  // Sync server-side voice_enabled once on mount (previously done by the
  // backstage page). Keeps the +菜单/语音聊天 toggle honest without opening it.
  useEffect(() => {
    if (!isAuthenticated()) return
    getCharacterSettings(currentCharacterId)
      .then((res) => setVoiceChatEnabled(currentCharacterId as CharacterId, res.voice_enabled))
      .catch(() => { /* keep local value */ })
  }, [currentCharacterId, isAuthenticated, setVoiceChatEnabled])

  const currentCharacter = serverCharacters.find((c) => c.id === currentCharacterId)
  const displayName = currentCharacter?.display_name
  const avatarUrl = currentCharacter?.avatar_url
  const profile = resolveCharacterProfile(currentCharacterId, displayName, avatarUrl, {
    coverUrl: currentCharacter?.cover_url,
  })
  const pageBg = isDark
    ? '/assets/backgrounds/暗色聊天背景图.webp'
    : '/assets/backgrounds/聊天背景图.webp'
  // Prefer the character's portrait cover as the chat backdrop; a dark scrim keeps
  // the glass bubbles + text legible over an arbitrary photo. No cover → the
  // static themed background above.
  const coverBg = currentCharacter?.cover_url ?? null

  const currentCompanion = companions.find((c) => c.character_id === currentCharacterId)

  // Load the bond-center aggregation lazily (companionsStore dedupes concurrent
  // loads); used only for the relationship status bar + upgrade card below.
  useEffect(() => {
    loadCompanions()
  }, [loadCompanions])

  // Relationship-upgrade event card: compare the current stage against the
  // last-seen stage for this character (localStorage), purely client-side.
  // First visit for a character just records the baseline — it never pops a
  // card on the very first time we learn the stage.
  useEffect(() => {
    if (!currentCompanion) return
    const stage = currentCompanion.relationship_stage
    const key = `lastStage:${currentCharacterId}`
    const prevStage = localStorage.getItem(key)
    if (prevStage === null) {
      localStorage.setItem(key, stage)
      return
    }
    if (prevStage !== stage && stageOrderIndex(stage) > stageOrderIndex(prevStage)) {
      setUpgradeStage(stage)
    }
    localStorage.setItem(key, stage)
  }, [currentCharacterId, currentCompanion])

  const setInboxUnreadTotal = useAppStore((s) => s.setInboxUnreadTotal)

  // Mark character read on mount + unmount: clears the unread badge for this
  // character on entry AND when leaving via in-app navigation (SPA navigate
  // doesn't fire visibilitychange/pagehide — those are tab-level events).
  useEffect(() => {
    if (!isAuthenticated()) return
    markCharacterRead(currentCharacterId).catch(() => {})
    // Optimistically clear badge; ChatInboxPage will recompute on next open.
    setInboxUnreadTotal(0)
    return () => {
      // Fire-and-forget on unmount; response ignored (component is gone).
      markCharacterRead(currentCharacterId).catch(() => {})
    }
  }, [currentCharacterId, isAuthenticated, setInboxUnreadTotal])

  // Also mark read when new assistant messages arrive during the visit AND
  // when the tab is being hidden.  Without this, mark-read only ever
  // captured last_read_at from mount time; any assistant reply that landed
  // during the visit stayed "unread" until the user re-entered — the "只有再
  // 次进入聊天页 → 再退出 才变成已读" bug from 2026-07-11.
  const lastAssistantId = messages.length > 0 ? messages[messages.length - 1].id : null
  const lastAssistantRole = messages.length > 0 ? messages[messages.length - 1].role : null
  useEffect(() => {
    if (!isAuthenticated()) return
    if (lastAssistantRole !== 'assistant') return
    // Debounce so text_delta storms don't produce a mark-read per token.
    const t = setTimeout(() => {
      markCharacterRead(currentCharacterId).catch(() => {})
    }, 400)
    return () => clearTimeout(t)
  }, [currentCharacterId, isAuthenticated, lastAssistantId, lastAssistantRole])

  useEffect(() => {
    const onHide = () => {
      if (!isAuthenticated()) return
      if (document.visibilityState === 'hidden') {
        markCharacterRead(currentCharacterId).catch(() => {})
      }
    }
    window.addEventListener('pagehide', onHide)
    document.addEventListener('visibilitychange', onHide)
    return () => {
      window.removeEventListener('pagehide', onHide)
      document.removeEventListener('visibilitychange', onHide)
    }
  }, [currentCharacterId, isAuthenticated])

  // Set character ID in chat store
  useEffect(() => {
    // Only redirect an unknown id once the catalog is loaded — otherwise a direct
    // link to a valid (UGC) character would be bounced during the async fetch.
    if (routeCharacterId && !isValidCharacterId && catalogLoaded) {
      navigate('/chat', { replace: true })
      return
    }
    if (currentCharacterId !== storedCharacterId) {
      setCharacter(currentCharacterId)
    }
    setActiveCharacter(currentCharacterId)
    setCharacterId(currentCharacterId)
  }, [currentCharacterId, isValidCharacterId, catalogLoaded, navigate, routeCharacterId, setActiveCharacter, setCharacter, setCharacterId, storedCharacterId])

  // Load chat history from API on mount / character change
  const prevCharRef = useRef(currentCharacterId)
  useEffect(() => {
    if (!isAuthenticated()) return
    setHistoryLoaded(false)
    prevCharRef.current = currentCharacterId

    const existing = useChatStore.getState().messages[currentCharacterId] ?? []
    const stale = Date.now() - (useChatStore.getState().lastFetchedAt[currentCharacterId] ?? 0) > 5 * 60 * 1000
    if (existing.length > 0 && !stale) {
      setHistoryLoaded(true)
      return
    }
    if (isCleared) {
      setHistoryLoaded(true)
      return
    }

    getChatHistory(currentCharacterId, undefined, 50)
      .then(async (data) => {
        const reversed = [...data.items].reverse()

        // Empty history → generate first-encounter opening scene
        if (reversed.length === 0 && !isCleared) {
          setGeneratingOpening(true)
          try {
            const result = await generateOpening(currentCharacterId)
            if (!result.already_exists && result.messages.length > 0) {
              reconcileHistory(currentCharacterId, result.messages.map(m =>
                historyItemToMessage({...m, created_at: m.created_at ?? new Date().toISOString()} as HistoryItem)
              ))
            }
          } catch {
            // Opening generation failed — fall through to empty state
          } finally {
            setGeneratingOpening(false)
            setHistoryLoaded(true)
          }
          return
        }

        // Reconcile (not append) so the server's rows replace the optimistic
        // copies of the same turn instead of duplicating them. reconcileHistory
        // dedups by turnId, protects the live turn, and carries over in-session
        // audioData.
        reconcileHistory(currentCharacterId, reversed.map(historyItemToMessage))
        if (reversed.length > 0) {
          const last = reversed[reversed.length - 1]
          appendMessage(currentCharacterId, {
            id: last.id,
            role: last.role as 'assistant' | 'user',
            content: last.content,
            timestamp: new Date(last.created_at).getTime(),
            kind: last.kind === 'action' ? 'action' : last.modality === 'voice' ? 'voice' : 'text',
            audioDuration: last.audio_duration_ms ?? undefined,
          })
        }
        setLastFetchedAt(currentCharacterId, Date.now())
        setHistoryLoaded(true)
      })
      .catch(() => {
        setHistoryLoaded(true)
      })
  }, [currentCharacterId, isAuthenticated, isCleared])

  // Resolve voice bubbles that were still synthesising when the user left the
  // page. The turn keeps generating server-side (background) and is persisted;
  // the stuck placeholder's id === turn_id, so point it at the by-turn endpoint
  // to pull the now-persisted audio. Without this the bubble sits on "加载中"
  // forever (the reported "退出页面语音卡在加载态" bug). Never touches the turn
  // that is streaming right now.
  useEffect(() => {
    const cid = currentCharacterId
    const msgs = useChatStore.getState().messages[cid as CharacterId] ?? []
    const streamingTurnId = useChatStore.getState().currentTurnId
    for (const m of msgs) {
      if (m.kind !== 'voice' || m.audioData || m.audioUrl || m.id === streamingTurnId) continue
      // Repoint at the by-turn endpoint, role-scoped. Assistant placeholders use
      // id === turn_id; user messages use turnId (their id is `user-${turnId}`).
      if (m.role === 'assistant') {
        setMessageAudioUrl(cid, m.id, `/api/chat/audio/by-turn/${m.id}?role=assistant`)
      } else if (m.turnId) {
        setMessageAudioUrl(cid, m.id, `/api/chat/audio/by-turn/${m.turnId}?role=user`)
      }
    }
    // Re-runs when isStreaming flips false too: on reconnect the WS layer clears
    // the orphaned turn's streaming state (useWebSocket onopen), and only then is
    // the placeholder no longer the "current turn" and safe to resolve.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCharacterId, isStreaming])

  // Surface any pending proactive messages (SS06) once history has loaded, then
  // ack them so they are not re-served. Injected after history to preserve order
  // and to avoid suppressing the history load (which only runs when empty).
  useEffect(() => {
    if (!historyLoaded) return
    const pending = useProactiveStore.getState().drain(currentCharacterId)
    if (pending.length === 0) return
    for (const m of pending) {
      const baseTs = new Date(m.created_at).getTime()
      // Split dialog / action into separate bubbles just like a normal reply.
      // Server sends `segments`; fall back to one text bubble on older servers.
      const segments =
        m.segments && m.segments.length > 0
          ? m.segments
          : [{ kind: 'text' as const, content: m.content }]
      segments.forEach((seg, i) => {
        const proactiveMsg = {
          id: segments.length > 1 ? `${m.id}-${i}` : m.id,
          role: 'assistant' as const,
          content: seg.content,
          // Nudge each bubble's timestamp so ordering is stable within the batch.
          timestamp: baseTs + i,
          kind: seg.kind,
        }
        addMessage(currentCharacterId, proactiveMsg)
        appendMessage(currentCharacterId, proactiveMsg)
      })
    }
    const { user } = useAuthStore.getState()
    if (user?.id) {
      void ackProactive(user.id, pending.map((m) => m.id)).catch(() => {})
    }
  }, [historyLoaded, currentCharacterId, addMessage, appendMessage])

  // Sync on visibilitychange: re-fetch latest messages + mark character read
  useEffect(() => {
    const handler = () => {
      if (document.visibilityState !== 'visible') return
      if (!isAuthenticated()) return
      markCharacterRead(currentCharacterId).catch(() => {})
      getChatHistory(currentCharacterId, undefined, 20)
        .then((data) => {
          const incomingMsgs = [...data.items].reverse()
          // Reconcile by turn (not raw id): optimistic ids never match server
          // UUIDs, so an id-only dedup let the user's own messages duplicate.
          reconcileHistory(currentCharacterId, incomingMsgs.map(historyItemToMessage))
          if (incomingMsgs.length > 0) setLastFetchedAt(currentCharacterId, Date.now())
        })
        .catch(() => {})
    }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [currentCharacterId, isAuthenticated, reconcileHistory, setLastFetchedAt])

  // Auto-scroll on new messages
  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      requestAnimationFrame(() => el.scrollTo(0, el.scrollHeight))
    }
  }, [messages, isStreaming])

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    sendMessage(trimmed)
    setInput('')
  }, [input, isStreaming, sendMessage])

  const handleStarterClick = useCallback((text: string) => {
    if (isStreaming) return
    sendMessage(text)
  }, [isStreaming, sendMessage])

  const handleInterrupt = useCallback(() => {
    interrupt()
  }, [interrupt])

  // 语音通话入口：先校验角色是否已配置音色。未配置 → 提示并跳配置页，不进通话页
  // （通话页无文字回退，进去只会一直失败）。校验用与语音聊天弹窗一致的 has_voice。
  const handleVoiceCall = useCallback(async () => {
    try {
      const res = await getCharacterVoice(currentCharacterId)
      const hasVoice = res.has_voice ?? res.clone_status === 'ready'
      if (!hasVoice) {
        useToastStore.getState().show('该角色暂未配置音色，请先选择一个音色', 'info')
        navigate(`/characters/new?voice=${currentCharacterId}`)
        return
      }
    } catch {
      useToastStore.getState().show('音色状态获取失败，请稍后重试', 'error')
      return
    }
    navigate(`/call/${currentCharacterId}`)
  }, [currentCharacterId, navigate])

  // 转账入口：POST /chat/transfer。后端持久化转账气泡 + 由 LLM 判定角色收/不收，
  // 返回已定状态的转账气泡 + 角色回应气泡。前端直接 append，无需重刷历史。
  const handleTransfer = useCallback(async (amount: number, note: string) => {
    if (transferSending) return
    const cid = currentCharacterId as CharacterId
    setTransferSending(true)
    // Show the transfer bubble immediately in a pending state ("待朋友确认收钱")
    // — the LLM accept/decline decision runs server-side and can take a few
    // seconds; the user should see their transfer land at once, WeChat-style.
    const tempId = `transfer-pending-${Date.now()}`
    const { addMessage, updateMessage, removeMessage, appendMessage } = useChatStore.getState()
    const amtDecimals = amount < 0.01 && amount > 0 ? 3 : 2
    addMessage(cid, {
      id: tempId,
      role: 'user',
      content: JSON.stringify({ amount: Number(amount.toFixed(amtDecimals)), note, status: 'pending', direction: 'out' }),
      timestamp: Date.now(),
      kind: 'transfer',
    })
    try {
      const res = await sendTransfer(cid, amount, note)
      // Resolve the optimistic pending bubble into its final state in place.
      updateMessage(cid, tempId, {
        id: res.transfer.id,
        turnId: res.transfer.turn_id,
        content: res.transfer.content,
      })
      // 角色回应气泡（收据 + 台词/动作）
      for (const r of res.replies) {
        const kind = r.kind === 'transfer_receipt'
          ? 'transfer_receipt'
          : r.kind === 'action' ? 'action' : 'text'
        addMessage(cid, {
          id: r.id,
          turnId: r.turn_id,
          role: 'assistant',
          content: r.content,
          timestamp: Date.now(),
          kind,
        })
      }
      // 同步会话列表预览（HomePage）：取最后一条角色文本气泡
      const lastText = [...res.replies].reverse().find((r) => r.kind === 'text')
      if (lastText) {
        appendMessage(cid, {
          id: lastText.id,
          role: 'assistant',
          content: lastText.content,
          timestamp: Date.now(),
          kind: 'text',
        })
      }
    } catch {
      removeMessage(cid, tempId)
      useToastStore.getState().show('转账失败，请稍后重试', 'error')
    } finally {
      setTransferSending(false)
    }
  }, [currentCharacterId, transferSending])

  const showToast = useCallback((msg: string) => {
    setRecordingToast(msg)
    setTimeout(() => setRecordingToast(null), 2500)
  }, [])

  const handleMicPointerDown = useCallback(
    async (e: React.PointerEvent<HTMLButtonElement>) => {
      if (isStreaming) return
      e.currentTarget.setPointerCapture(e.pointerId)
      setIsRecording(true)
      setWillCancel(false)
      try {
        await recorder.start()
      } catch {
        setIsRecording(false)
        showToast('无法访问麦克风，请检查权限')
      }
    },
    [isStreaming, recorder, showToast],
  )

  const handleMicPointerMove = useCallback(
    (e: React.PointerEvent<HTMLButtonElement>) => {
      if (!isRecording || !cancelZoneRef.current) return
      const rect = cancelZoneRef.current.getBoundingClientRect()
      const inside =
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      setWillCancel(inside)
    },
    [isRecording],
  )

  const handleMicPointerUp = useCallback(
    async (_e: React.PointerEvent<HTMLButtonElement>) => {
      if (!isRecording) return
      setIsRecording(false)
      const cancel = willCancel
      setWillCancel(false)

      const result = await recorder.stop({ cancel })
      if (!result) {
        if (!cancel) showToast('说话时间太短')
        return
      }

      const { wavBlob, durationMs } = result

      try {
        const { transcript, audio_url } = await transcribeAudio(wavBlob, durationMs)
        if (!transcript) {
          showToast('没有识别到语音内容')
          return
        }
        // Blob URL for immediate in-session playback; S3 audio_url persists across navigations.
        const blobUrl = URL.createObjectURL(wavBlob)
        sendMessage(transcript, {
          voiceBubble: { audioData: blobUrl, durationMs, format: 'wav', audioUrl: audio_url },
        })
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : '语音识别失败'
        showToast(msg)
      }
    },
    [isRecording, willCancel, recorder, sendMessage, showToast],
  )

  const toggleVoiceTranscript = useCallback((messageId: string) => {
    setExpandedVoiceTextIds((prev) => {
      const next = new Set(prev)
      if (next.has(messageId)) {
        next.delete(messageId)
      } else {
        next.add(messageId)
      }
      return next
    })
  }, [])

  // 叩问式引导回复（挂在 AI 开场消息末尾，缩进对齐消息列，不是浮在输入框上的控制栏）。
  // 有 starterBranches → 先选切入角度再展开台词；否则平铺 starterPrompts。
  const renderStarterGuide = () => {
    if (!(historyLoaded && !isStreaming && messages.every((m) => m.role !== 'user'))) return null
    const branches = CHARACTER_UI_CONFIGS[currentCharacterId]?.starterBranches
    const chipCls = isDark
      ? 'bg-[rgba(255,255,255,0.07)] text-[rgba(248,242,250,0.9)] border border-[rgba(255,255,255,0.14)] active:bg-[rgba(255,255,255,0.12)]'
      : 'bg-[rgba(255,255,255,0.7)] text-[rgba(33,35,57,0.92)] border border-[rgba(0,0,0,0.06)] active:bg-white'

    const lead = (
      <p className={`text-[12px] mb-2 ${isDark ? 'text-[rgba(248,242,250,0.45)]' : 'text-[rgba(91,93,117,0.7)]'}`}>
        你会怎么回应他
      </p>
    )

    if (branches && branches.length > 0) {
      const active = starterBranch !== null ? branches[starterBranch] : null
      return (
        <div className="mt-1 ml-[48px] mr-2 mb-1">
          {lead}
          {!active ? (
            <div className="flex flex-col gap-1.5">
              {branches.map((b, i) => (
                <button
                  key={b.label}
                  onClick={() => setStarterBranch(i)}
                  className={`group flex items-center justify-between w-full px-4 py-3 rounded-[14px] text-[14px] text-left backdrop-blur-[12px] transition-colors ${chipCls}`}
                >
                  <span>{b.label}</span>
                  <span className="text-[13px] opacity-45 font-light">+</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              <button
                onClick={() => setStarterBranch(null)}
                className={`self-start inline-flex items-center gap-1 text-[12px] mb-0.5 ${isDark ? 'text-[rgba(248,242,250,0.55)]' : 'text-[rgba(91,93,117,0.8)]'}`}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="15,6 9,12 15,18" />
                </svg>
                {active.label}
              </button>
              {active.options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => handleStarterClick(opt)}
                  className={`w-full px-4 py-3 rounded-[14px] text-[14px] text-left backdrop-blur-[12px] transition-colors ${chipCls}`}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="mt-1 ml-[48px] mr-2 mb-1">
        {lead}
        <div className="flex flex-col gap-1.5">
          {(CHARACTER_UI_CONFIGS[currentCharacterId]?.starterPrompts ?? FALLBACK_STARTER_PROMPTS).map((prompt) => (
            <button
              key={prompt}
              onClick={() => handleStarterClick(prompt)}
              className={`w-full px-4 py-3 rounded-[14px] text-[14px] text-left backdrop-blur-[12px] transition-colors ${chipCls}`}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    )
  }

  // Render a single message bubble
  const renderMessage = (msg: Message, showAvatar: boolean, isLastAndGenerating = false) => {
    const isAI = msg.role === 'assistant'
    const avatar = isAI ? profile.avatar : userAvatar

    // While generating (streaming + waiting for message_bubble), always show typing dots
    if (isAI && isLastAndGenerating) {
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isDark
              ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[rgba(255,255,255,0.06)]'
              : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[var(--color-border-glass)]'
          }`}>
            <BreathingDots />
          </div>
        </div>
      )
    }

    // Voice mode loading bubble uses the same shell as text loading. Only a
    // voice message with NEITHER live audio NOR a durable server pointer is
    // genuinely still loading; a rehydrated/historical one has audioUrl.
    if (msg.kind === 'voice' && !msg.audioData && !msg.audioUrl) {
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isDark
              ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[rgba(255,255,255,0.06)]'
              : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[var(--color-border-glass)]'
          }`}>
            <BreathingDots />
          </div>
        </div>
      )
    }

    // Call-summary bubble — WeChat-style centred pill shown after a voice call
    // ends. content holds mm:ss. Replaces the N per-turn voice bubbles (those
    // are hidden server-side via channel='call').
    if (msg.kind === 'call_summary') {
      return (
        <div className="flex justify-center my-1">
          <div className={`inline-flex items-center gap-2 max-w-[80%] px-3.5 py-2 rounded-full text-[13px] ${
            isDark
              ? 'bg-[rgba(255,255,255,0.07)] text-[rgba(228,228,231,0.7)]'
              : 'bg-[rgba(0,0,0,0.05)] text-[rgba(45,50,72,0.66)]'
          }`}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.573 2.81.7A2 2 0 0 1 22 16.92Z" />
            </svg>
            <span>通话时长 {msg.content}</span>
          </div>
        </div>
      )
    }

    // Transfer bubbles (WeChat-style). Outgoing transfer (role=user) sits on the
    // right; the character's receipt (transfer_receipt) sits on the left. Both
    // use an orange gradient card with an envelope glyph + amount + status.
    if (msg.kind === 'transfer' || msg.kind === 'transfer_receipt') {
      let amount = 0
      let noteText = ''
      let status = 'pending'
      try {
        const d = JSON.parse(msg.content)
        amount = Number(d.amount) || 0
        noteText = String(d.note || '')
        status = String(d.status || 'pending')
      } catch { /* keep defaults */ }
      const isReceipt = msg.kind === 'transfer_receipt'
      const isDeclined = status === 'declined'
      // Accounting/WeChat style: thousands separators + 2 decimals (e.g.
      // 11,111.01). The 0.001 easter egg keeps a 3rd decimal so it isn't lost.
      const amtDecimals = amount < 0.01 && amount > 0 ? 3 : 2
      const amtStr = amount.toLocaleString('en-US', {
        minimumFractionDigits: amtDecimals,
        maximumFractionDigits: amtDecimals,
      })
      // Status line — sender vs receiver perspective mirrors WeChat.
      //   user side (transfer):  pending→待朋友确认收钱, accepted→已被领取, declined→已被退还
      //   char side (receipt):   accepted→已收款, declined→已退还
      const statusLabel = isReceipt
        ? (isDeclined ? '已退还' : '已收款')
        : status === 'accepted'
          ? '已被领取'
          : isDeclined
            ? '已被退还'
            : '待朋友确认收钱'
      // Declined transfers (either side) go muted with a return-arrow glyph.
      const dimmed = isDeclined
      return (
        <div className={`flex items-start gap-2 ${isReceipt ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div
            className={`w-[232px] rounded-[10px] overflow-hidden ${dimmed ? 'opacity-60' : ''}`}
            style={{ background: dimmed ? 'linear-gradient(135deg,#C9A278,#B98F63)' : 'linear-gradient(135deg,#F5A623,#E8942E)' }}
          >
            <div className="flex items-center gap-3 px-3.5 py-3">
              {isDeclined ? (
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                  <path d="M9 14 4 9l5-5" />
                  <path d="M4 9h11a5 5 0 0 1 0 10h-1" />
                </svg>
              ) : (
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                  <rect x="2" y="5" width="20" height="14" rx="2" />
                  <path d="M12 5v14M2 10h20" />
                </svg>
              )}
              <div className="min-w-0">
                <div className="text-white text-[17px] font-medium leading-tight">¥{amtStr}</div>
                <div className="text-white/85 text-[12px] mt-0.5 truncate">
                  {noteText || (isDeclined ? '已退还' : isReceipt ? '已收款' : '转账')}
                </div>
              </div>
            </div>
            <div className="px-3.5 py-1.5 bg-black/10 text-white/80 text-[11px]">
              {statusLabel}
            </div>
          </div>
        </div>
      )
    }

    // Action bubble — grey italic narration (parenthetical action / expression / OOC)
    // Rendered without avatar, centre-aligned, low-contrast to keep the reader's
    // eye on the dialog. Independent from voice / TTS.
    if (msg.kind === 'action' && msg.content) {
      return (
        <div className="flex justify-center my-1">
          <div className={`max-w-[80%] px-3 py-1.5 rounded-full text-[13px] italic ${
            isDark
              ? 'bg-[rgba(255,255,255,0.05)] text-[rgba(228,228,231,0.55)]'
              : 'bg-[rgba(0,0,0,0.04)] text-[rgba(45,50,72,0.55)]'
          }`}>
            {msg.content}
          </div>
        </div>
      )
    }

    // Show breathing dots in text bubble when message is empty during streaming
    const isEmpty = msg.content === '' && isStreaming
    if (isEmpty) {
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isAI
              ? isDark
                ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[rgba(255,255,255,0.06)]'
                : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] border border-[var(--color-border-glass)]'
              : isDark
                ? 'bg-gradient-to-br from-[#4A5B8F] to-[#6C7DB5] rounded-[6px_20px_20px_20px]'
                : 'bg-gradient-to-br from-[#A7C7E7] to-[#BFD7EE] rounded-[6px_20px_20px_20px]'
          }`}>
            <BreathingDots />
          </div>
        </div>
      )
    }

    // Voice message with audio — live base64 (this session) or a durable
    // server URL (rehydrated after refresh / loaded from history).
    if (msg.kind === 'voice' && (msg.audioData || msg.audioUrl)) {
      const transcriptExpanded = expandedVoiceTextIds.has(msg.id)
      // Pick the audio source. A user's own recording is a browser blob: URL —
      // always instantly playable, so use it directly. For an AI TTS reply we
      // prefer the DURABLE server pointer (msg.audioUrl) over the live base64
      // blob (msg.audioData): the WS-assembled blob (single Fish mp3 chunk) can
      // fail to decode/plays silently in some browsers (iOS Safari), which is
      // the reported "click does nothing, only a refresh plays it" bug — a
      // refresh drops audioData and replays via exactly this server pointer. We
      // keep the base64 as the fallback so playback still works if the pointer
      // hasn't persisted yet (by-turn 404 race right after turn_end).
      // A user's own recording is a browser blob: URL — instantly playable, so
      // use it directly with the durable pointer as fallback. For an AI reply we
      // use the durable pointer as the primary and DON'T pass base64 as fallback:
      // fetchApiAudio (the fallback path) does fetch(url) and can't consume a
      // base64 string, and the base64 blob is the very source that fails silently
      // — the by-turn endpoint already retries 3x on the post-turn_end 404 race,
      // so it stands on its own and matches the (working) refresh path exactly.
      const isBrowserBlob = msg.audioData?.startsWith('blob:')
      const primarySource = isBrowserBlob
        ? (msg.audioData as string)
        : (msg.audioUrl || msg.audioData || '')
      const fallbackSource = isBrowserBlob ? msg.audioUrl : undefined
      return (
        <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
          {showAvatar ? (
            <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
          ) : (
            <div className="w-[40px] shrink-0" />
          )}
          <div className="max-w-[348px]">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <VoiceMessageBubble
                  audioData={primarySource}
                  duration={msg.audioDuration ?? 3000}
                  format={msg.audioFormat ?? 'wav'}
                  isDark={isDark}
                  // Second source tried if the primary fails. For an AI reply
                  // this is the live base64 blob (primary = durable pointer);
                  // for a user recording it's the durable pointer (primary =
                  // instant blob).
                  fallbackUrl={fallbackSource}
                />
              </div>
              {msg.content && (
                <button
                  type="button"
                  onClick={() => toggleVoiceTranscript(msg.id)}
                  className={`mb-1 shrink-0 rounded-full px-3 py-2 text-[12px] font-medium backdrop-blur-[14px] transition-colors ${
                    isDark
                      ? 'bg-[rgba(255,255,255,0.08)] text-[rgba(248,242,250,0.82)] border border-[rgba(255,255,255,0.08)]'
                      : 'bg-[rgba(255,255,255,0.58)] text-[rgba(91,93,117,0.82)] border border-[rgba(255,255,255,0.74)]'
                  }`}
                >
                  {transcriptExpanded ? '收起文字' : '转文字'}
                </button>
              )}
            </div>
            {msg.content && transcriptExpanded && (
              <div
                className={`mt-2 rounded-[20px] px-4 py-3 text-[13px] leading-[1.65] backdrop-blur-[14px] ${
                  isDark
                    ? 'bg-[rgba(255,255,255,0.06)] text-[rgba(236,230,241,0.76)] border border-[rgba(255,255,255,0.06)]'
                    : 'bg-[rgba(255,255,255,0.52)] text-[rgba(93,95,118,0.84)] border border-[rgba(255,255,255,0.68)]'
                }`}
              >
                {msg.content}
              </div>
            )}
          </div>
        </div>
      )
    }

    // Text message
    return (
      <div className={`flex items-start gap-2 ${isAI ? 'self-start' : 'self-end flex-row-reverse'}`}>
        {showAvatar ? (
          <Avatar src={avatar} size={40} className="shrink-0 mt-[2px]" />
        ) : (
          <div className="w-[40px] shrink-0" />
        )}
        <div
          className={`max-w-[calc(18em+2rem)] px-4 py-[14px] ${
            isAI
              ? isDark
                ? 'bg-[rgba(255,255,255,0.06)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] text-[#EFE7DD] border border-[rgba(255,255,255,0.06)]'
                : 'bg-[var(--color-glass-75)] backdrop-blur-[16px] rounded-[20px_20px_20px_6px] text-[var(--color-ink)] border border-[var(--color-border-glass)]'
              : isDark
                ? 'bg-gradient-to-br from-[#4A5B8F] to-[#6C7DB5] rounded-[6px_20px_20px_20px] text-[#EFE7DD] min-w-[48px]'
                : 'bg-gradient-to-br from-[#A7C7E7] to-[#BFD7EE] rounded-[6px_20px_20px_20px] text-white min-w-[48px]'
          }`}
        >
          <p className="text-[16px] leading-[1.6] whitespace-pre-wrap break-words">
            {msg.content}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {coverBg ? (
        <>
          <img src={coverBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
          <div className={`absolute inset-0 z-0 ${isDark ? 'bg-black/60' : 'bg-black/25'}`} />
          <div className="absolute inset-0 z-0 bg-gradient-to-b from-black/35 via-transparent to-black/45" />
        </>
      ) : (
        <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      )}

      {/* Header */}
      <header
        className={`relative z-20 flex items-center gap-3 px-5 py-3 backdrop-blur-[20px] rounded-b-[20px] ${
          isDark
            ? 'bg-[rgba(26,26,46,0.75)] shadow-[0_2px_12px_rgba(0,0,0,0.12)] border-b border-[rgba(255,255,255,0.06)]'
            : 'bg-[rgba(255,255,255,0.75)] shadow-[0_2px_12px_rgba(0,0,0,0.06)]'
        }`}
        style={{ paddingTop: 'calc(var(--safe-top) + 12px)' }}
      >
        <button onClick={() => navigate('/chat')} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke={isDark ? '#E4E4E7' : 'var(--color-ink)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <img src={profile.avatar} alt={profile.name} className="w-[40px] h-[40px] rounded-full object-cover" />
        <div className="flex-1 min-w-0">
          <p className={`text-[17px] font-semibold ${isDark ? 'text-[#E4E4E7]' : 'text-[var(--color-ink)]'}`}>{profile.name}</p>
          <div className="flex items-center gap-1">
            <div className="w-[6px] h-[6px] rounded-full bg-[var(--color-online)]" />
            <span className={`text-[13px] ${isDark ? 'text-[rgba(228,228,231,0.65)]' : 'text-[var(--color-text-secondary)]'}`}>
              {isStreaming ? '正在回复…' : isPlaying ? '朗读中' : profile.statusLabel}
            </span>
            {currentCompanion && (
              <span className={`text-[12px] ml-1.5 ${isDark ? 'text-[rgba(228,228,231,0.5)]' : 'text-[var(--color-text-secondary)]'}`}>
                · {stageWithIntimacy(currentCompanion.relationship_stage, currentCompanion.intimacy)}
              </span>
            )}
          </div>
        </div>
        {/* header 右侧占位：原「角色后台」入口已下线，设置内联到输入区 */}
        <div className="w-[44px] h-[44px] shrink-0" />
      </header>

      {/* AI-generated content disclaimer */}
      <div className="relative z-20 flex items-center justify-center py-2 px-4 bg-[var(--color-surface)] border-b border-[var(--color-divider)]">
        <span className="text-[11px] text-[var(--color-text-muted)] text-center">
          内容由 AI 生成，对话请遵守社区公约
        </span>
      </div>

      {/* 剧情邀约卡（Wave 3）— DISABLED 2026-07-24：角色↔剧情关联功能已暂停。
          恢复：取消 import、hookDismissed state 与下方注释即可。
      {currentCompanion?.available_story_hook &&
        !hookDismissed &&
        !isHookOnCooldown(currentCharacterId, currentCompanion.available_story_hook) && (
          <div className="relative z-20 mx-3 mt-3">
            <StoryInviteCard
              characterId={currentCharacterId}
              hook={currentCompanion.available_story_hook}
              onDismiss={() => setHookDismissed(true)}
            />
          </div>
        )} */}

      {/* 关系升阶事件卡（纯前端，localStorage 比对，不写回后端） */}
      {upgradeStage && (
        <div className="relative z-20 mx-3 mt-3 rounded-[20px] px-4 py-3 bg-[var(--color-glass-75)] backdrop-blur-[16px] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)] flex items-center justify-between gap-3">
          <div>
            <p className="text-[13px] font-medium text-[var(--color-ink)]">
              你们的关系进入「{stageLabel(upgradeStage)}」
            </p>
            <p className="text-[12px] text-[var(--color-text-secondary)] mt-0.5">她开始更主动地靠近你。</p>
          </div>
          <button
            onClick={() => {
              setUpgradeStage(null)
              navigate('/character')
            }}
            className="shrink-0 h-[32px] px-3 rounded-full bg-[var(--color-primary)] text-white text-[12px] font-medium active:scale-[0.96] transition-transform"
          >
            查看羁绊
          </button>
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        {/* 角色专属前情提要卡：首聊、无用户消息时出现在开场之上 */}
        {historyLoaded &&
          messages.every((m) => m.role !== 'user') &&
          (() => {
            const PremiseCard = PREMISE_CARDS[currentCharacterId]
            return PremiseCard ? <PremiseCard /> : null
          })()}

        {!historyLoaded && (
          <div className="flex-1 flex items-center justify-center">
            <BreathingDots />
          </div>
        )}

        {generatingOpening && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <BreathingDots />
            <span className={`text-[13px] ${isDark ? 'text-[rgba(228,228,231,0.5)]' : 'text-[var(--color-text-muted)]'}`}>
              {profile.shortName}正在向你走来…
            </span>
          </div>
        )}

        {historyLoaded && messages.length === 0 && !generatingOpening && (
          <div className={`text-center text-[13px] py-8 ${isDark ? 'text-[rgba(228,228,231,0.4)]' : 'text-[var(--color-text-muted)]'}`}>
            和{profile.shortName}说点什么吧
          </div>
        )}

        {messages.map((msg, index) => {
          const prev = index > 0 ? messages[index - 1] : null
          const showTime = shouldShowTimestamp(msg, prev)
          const showAvatar = !prev || prev.role !== msg.role || showTime || prev?.kind === 'action'
          const isLastAndGenerating = index === messages.length - 1 && isGenerating

          return (
            <div key={msg.id} className="flex flex-col">
              {showTime && (
                <div className="flex justify-center py-2">
                  <span className={`inline-flex h-[22px] items-center rounded-full px-2.5 text-[11px] ${
                    isDark
                      ? 'bg-[rgba(255,255,255,0.08)] text-[rgba(228,228,231,0.5)]'
                      : 'bg-[rgba(0,0,0,0.06)] text-[var(--color-text-muted)]'
                  }`}>
                    {formatChatTime(msg.timestamp)}
                  </span>
                </div>
              )}
              {renderMessage(msg, showAvatar, isLastAndGenerating)}
            </div>
          )
        })}

        {/* 叩问式引导回复：挂在 AI 开场消息末尾，作为对话的一部分（非浮动控制栏） */}
        {renderStarterGuide()}

        {/* Streaming indicator - avatar is already in the bubble via renderMessage */}
      </div>

      {/* 文字聊天档位入口（输入框左上角） */}
      <div className="relative z-20 mx-4 mb-1.5 flex items-center">
        <button
          onClick={() => setTextTierOpen(true)}
          className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[12px] font-medium backdrop-blur-[14px] active:scale-[0.97] transition-transform ${
            isDark
              ? 'bg-[rgba(255,255,255,0.08)] text-[rgba(248,242,250,0.82)] border border-[rgba(255,255,255,0.08)]'
              : 'bg-[rgba(255,255,255,0.58)] text-[rgba(91,93,117,0.9)] border border-[rgba(255,255,255,0.74)]'
          }`}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span>{textTierLabel}</span>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6,9 12,15 18,9" />
          </svg>
        </button>
      </div>

      {/* Input bar */}
      <div
        className={`relative z-20 mx-3 mb-3 flex items-center gap-3 px-4 py-3 backdrop-blur-[24px] rounded-[28px] border ${
          isDark
            ? 'bg-[rgba(26,26,46,0.7)] border-[rgba(255,255,255,0.08)] shadow-[var(--shadow-sheet)]'
            : 'bg-[var(--color-glass-75)] border-[var(--color-border-glass)] shadow-[var(--shadow-sheet)]'
        }`}
        style={{ marginBottom: 'calc(16px + var(--safe-bottom))' }}
      >
        {/* Interrupt button when streaming, add button otherwise */}
        {isStreaming ? (
          <button
            onClick={handleInterrupt}
            className="w-[40px] h-[40px] flex items-center justify-center shrink-0"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="var(--color-primary)">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            className="w-[40px] h-[40px] flex items-center justify-center shrink-0 touch-none select-none"
            onPointerDown={handleMicPointerDown}
            onPointerMove={handleMicPointerMove}
            onPointerUp={handleMicPointerUp}
            onPointerCancel={handleMicPointerUp}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={isStreaming ? (isDark ? '#444' : '#DDD') : (isDark ? '#999' : '#888')} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="2" width="6" height="11" rx="3" />
              <path d="M5 10a7 7 0 0 0 14 0" />
              <line x1="12" y1="19" x2="12" y2="22" />
              <line x1="8" y1="22" x2="16" y2="22" />
            </svg>
          </button>
        )}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={isStreaming ? '正在回复中…' : `想和${profile.shortName}说点什么…`}
          disabled={isStreaming}
          className={`flex-1 bg-transparent outline-none text-[16px] ${
            isDark ? 'text-[#EFE7DD] placeholder-[rgba(228,228,231,0.3)]' : 'text-[var(--color-ink)] placeholder-[var(--color-text-placeholder)]'
          }`}
        />
        <button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          className={`w-[44px] h-[44px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] flex items-center justify-center shrink-0 shadow-[var(--shadow-send)] active:scale-90 transition-transform ${
            isStreaming || !input.trim() ? 'opacity-50' : ''
          }`}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
        {/* + 菜单：语音聊天 / 语音通话。可见圆与发送键同尺寸(44x44 实心圆)，
            用中性表面色区分主次，不与发送键的粉色渐变撞色。 */}
        <button
          onClick={() => setPlusMenuOpen(true)}
          aria-label="更多"
          className={`w-[44px] h-[44px] rounded-full flex items-center justify-center shrink-0 active:scale-90 transition-transform ${
            isDark ? 'bg-[rgba(255,255,255,0.08)]' : 'bg-[rgba(47,54,74,0.06)]'
          }`}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={isDark ? '#B9B9C0' : '#6B7280'} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="6" x2="12" y2="18" />
            <line x1="6" y1="12" x2="18" y2="12" />
          </svg>
        </button>
      </div>

      {/* 输入区弹窗（文字档位 / +菜单 / 语音聊天开关） */}
      <TextTierSheet
        open={textTierOpen}
        onClose={() => setTextTierOpen(false)}
        characterId={currentCharacterId as CharacterId}
        isDark={isDark}
      />
      <ChatPlusMenu
        open={plusMenuOpen}
        onClose={() => setPlusMenuOpen(false)}
        isDark={isDark}
        onVoiceChat={() => setVoiceChatOpen(true)}
        onVoiceCall={handleVoiceCall}
        onTransfer={() => setTransferOpen(true)}
      />
      <TransferSheet
        open={transferOpen}
        onClose={() => setTransferOpen(false)}
        characterName={profile.shortName}
        isDark={isDark}
        onConfirm={handleTransfer}
      />
      <VoiceChatSheet
        open={voiceChatOpen}
        onClose={() => setVoiceChatOpen(false)}
        characterId={currentCharacterId as CharacterId}
        isDark={isDark}
      />

      {/* Insufficient credits dialog */}
      <NoticeDialog
        open={!!insufficientCredits}
        onClose={clearInsufficientCredits}
        title="yuoyuo币不足"
        actionLabel="去充值"
        onAction={() => { clearInsufficientCredits(); navigate('/wallet') }}
      >
        你的 yuoyuo币不足以继续对话
        <br />
        前往钱包充值后继续
      </NoticeDialog>

      {/* Model requires higher tier */}
      <NoticeDialog
        open={!!modelForbidden}
        onClose={clearModelForbidden}
        title="该模型需会员"
        actionLabel="去升级"
        onAction={() => { clearModelForbidden(); navigate('/membership') }}
      >
        当前等级暂不能使用该模型
        <br />
        升级会员即可解锁更强的对话模型
      </NoticeDialog>

      {/* Voice recording overlay (WeChat-style) */}
      {isRecording && (
        <VoiceRecordingOverlay
          durationMs={0}
          willCancel={willCancel}
          cancelZoneRef={cancelZoneRef}
        />
      )}

      {/* Short toast for voice recording feedback */}
      {recordingToast && (
        <div className="fixed bottom-36 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-xl text-white text-[13px] bg-[rgba(0,0,0,0.65)] backdrop-blur pointer-events-none">
          {recordingToast}
        </div>
      )}
    </div>
  )
}
