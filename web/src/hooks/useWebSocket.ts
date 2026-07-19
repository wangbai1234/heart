import { useCallback, useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useAppStore } from '../stores/appStore'
import { useAuthStore } from '../stores/authStore'
import { wrapPCM16AsWAV } from '../services/audioPlayer'
import { FEEDBACK_COPY, type CharacterId } from '../data/uiContent'
import { useToastStore } from '../stores/toastStore'
import { authNavigate } from '../services/navigation'

const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/chat/ws`

interface WsMessage {
  type: string
  turn_id?: string
  delta?: string
  text?: string
  content?: string
  sequence_id?: number
  data_b64?: string
  seq?: number
  sentence_seq?: number
  is_last?: boolean
  format?: string
  vad?: { energy?: number; mood?: string }
  intimacy?: number
  msg?: string
  code?: string
  modality?: string
  credits_charged?: number
  balance?: number
  needed?: number
  kind?: 'text' | 'action'
  model?: string
  served_model?: string
  degraded_to?: string
  tier?: string
}

const MODEL_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  grok: 'Grok',
  claude: 'Claude',
}
function modelLabel(slug: string): string {
  return MODEL_LABELS[slug] ?? slug
}

function b64ToArrayBuffer(b64: string): ArrayBuffer {
  const bin = atob(b64)
  const buf = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i)
  return buf.buffer
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
  return btoa(binary)
}

function estimateChunkDurationMs(buffer: ArrayBuffer, format?: string) {
  if (format === 'pcm16') {
    return Math.max(1, Math.round(buffer.byteLength / (24000 * 2) * 1000))
  }
  return Math.max(1, Math.round(buffer.byteLength * 8 / 128))
}

// Wall-clock ceiling for a single turn.  If no state-clearing event
// (turn_end / error / interrupted / insufficient_credits) arrives within
// this window after turn_start, the frontend force-clears generating and
// shows a toast so the UI never gets stuck at "正在回复".
// Voice turns typically finish in <10 s; 60 s is a generous ceiling.
const TURN_WATCHDOG_MS = 60_000

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const connectRef = useRef<(() => void) | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const seenChunks = useRef<Set<string>>(new Set())
  const activeCharRef = useRef<CharacterId>('rin')
  const pendingVoiceTurnRef = useRef(false)
  const watchdogRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const addMessage = useChatStore(s => s.addMessage)
  const appendToLast = useChatStore(s => s.appendToLast)
  const setGenerating = useChatStore(s => s.setGenerating)
  const setStreaming = useChatStore(s => s.setStreaming)
  const setPlaying = useChatStore(s => s.setPlaying)
  const setCurrentTurnId = useChatStore(s => s.setCurrentTurnId)
  const setPendingAssistantTurnId = useChatStore(s => s.setPendingAssistantTurnId)
  const setVad = useChatStore(s => s.setVad)
  const appendMessageAudio = useChatStore(s => s.appendMessageAudio)
  const finalizeMessageAudio = useChatStore(s => s.finalizeMessageAudio)
  const isStreaming = useChatStore(s => s.isStreaming)

  const connect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN
                       || wsRef.current.readyState === WebSocket.CONNECTING)) return
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const { accessToken } = useAuthStore.getState()
    if (!accessToken) {
      return
    }

    const ws = new WebSocket(`${WS_BASE}?token=${accessToken}`)
    wsRef.current = ws

    ws.onopen = () => {}

    const armWatchdog = (cid: CharacterId) => {
      if (watchdogRef.current) clearTimeout(watchdogRef.current)
      watchdogRef.current = setTimeout(() => {
        watchdogRef.current = null
        setGenerating(cid, false)
        setStreaming(false)
        setPlaying(false)
        setCurrentTurnId(null)
        setPendingAssistantTurnId(null)
        pendingVoiceTurnRef.current = false
        useToastStore.getState().show('响应超时，请重试', 'error')
      }, TURN_WATCHDOG_MS)
    }

    const clearWatchdog = () => {
      if (watchdogRef.current) {
        clearTimeout(watchdogRef.current)
        watchdogRef.current = null
      }
    }

    ws.onmessage = async (ev) => {
      const msg: WsMessage = JSON.parse(ev.data)
      const cid = activeCharRef.current
      switch (msg.type) {
        case 'turn_start':
          seenChunks.current.clear()
          setPendingAssistantTurnId(null)
          setCurrentTurnId(msg.turn_id ?? null)
          addMessage(cid, {
            id: msg.turn_id ?? crypto.randomUUID(),
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            kind: pendingVoiceTurnRef.current ? 'voice' : 'text',
          })
          setGenerating(cid, true)
          setStreaming(true)
          setPlaying(false)
          armWatchdog(cid)
          break
        case 'text_delta':
          appendToLast(cid, msg.delta ?? '')
          break
        case 'sentence':
          setVad({
            energy: msg.vad?.energy ?? 0,
            mood: msg.vad?.mood ?? 'neutral',
            intimacy: msg.intimacy ?? 0,
          })
          break
        case 'audio_chunk':
          if (msg.data_b64) {
            const currentTurnId = useChatStore.getState().currentTurnId
            if (msg.turn_id !== currentTurnId) return
            // Mark message as voice on first audio chunk
            const msgs = useChatStore.getState().messages[cid] ?? []
            const lastMsg = msgs[msgs.length - 1]
            if (lastMsg && lastMsg.id === currentTurnId && lastMsg.kind !== 'voice') {
              const updated = msgs.map(m => m.id === currentTurnId ? { ...m, kind: 'voice' as const } : m)
              useChatStore.setState((s) => ({
                messages: { ...s.messages, [cid]: updated },
              }))
            }
            const key = `${msg.turn_id}:${msg.sentence_seq ?? 0}:${msg.seq}`
            if (seenChunks.current.has(key)) return
            seenChunks.current.add(key)
            const rawBuffer = b64ToArrayBuffer(msg.data_b64)
            const durationMs = estimateChunkDurationMs(rawBuffer, msg.format)
            const audioFormat = msg.format === 'pcm16' ? 'wav' : 'mp3'
            let storedB64 = msg.data_b64
            if (msg.format === 'pcm16') {
              storedB64 = arrayBufferToBase64(wrapPCM16AsWAV(rawBuffer))
            }
            appendMessageAudio(cid, currentTurnId, storedB64, durationMs, msg.seq ?? 0, audioFormat)
          }
          break
        case 'message_bubble': {
          // Semantic split: msg.kind ∈ {'text','action'}. Default to 'text'
          // if the server didn't send a kind (older backend).
          const bubbleKind: 'text' | 'action' = msg.kind === 'action' ? 'action' : 'text'
          // Replace the streaming placeholder (sequence_id=0) OR add new bubble.
          if (msg.sequence_id === 0) {
            // Clear generating flag — bubbles are arriving, stop the dots
            setGenerating(cid, false)
            useChatStore.setState((s) => {
              const msgs = s.messages[cid] ?? []
              const updated = msgs.map((m, idx) => {
                if (idx !== msgs.length - 1 || m.role !== 'assistant') return m
                // Preserve kind='voice' if audio_chunk already arrived — the
                // voice bubble owns the audio and its display kind must win
                // over an incoming 'text'. Action bubbles never race with
                // voice, so bubbleKind='action' still applies.
                const nextKind: 'text' | 'voice' | 'action' =
                  m.kind === 'voice' && bubbleKind === 'text' ? 'voice' : bubbleKind
                return { ...m, content: msg.content ?? '', kind: nextKind }
              })
              return { messages: { ...s.messages, [cid]: updated } }
            })
          } else {
            addMessage(cid, {
              id: `${msg.turn_id ?? ''}-${msg.sequence_id ?? 0}`,
              role: 'assistant',
              content: msg.content ?? '',
              timestamp: Date.now(),
              kind: bubbleKind,
            })
          }
          break
        }
        case 'turn_end':
          clearWatchdog()
          setGenerating(cid, false)
          if (msg.turn_id) {
            finalizeMessageAudio(cid, msg.turn_id)
            if (msg.modality) {
              const normalizedKind = msg.modality === 'voice' ? 'voice' : 'text'
              useChatStore.setState((s) => ({
                messages: {
                  ...s.messages,
                  [cid]: (s.messages[cid] ?? []).map((message) =>
                    // Only overwrite kind for the placeholder message (id === turn_id)
                    // AND only if it isn't already an action bubble.
                    message.id === msg.turn_id && message.kind !== 'action'
                      ? { ...message, kind: normalizedKind }
                      : message,
                  ),
                },
              }))
            }
          }
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          setPendingAssistantTurnId(null)
          // Sync last assistant message to threads for HomePage
          {
            const msgs = useChatStore.getState().messages[cid] ?? []
            const lastMsg = msgs[msgs.length - 1]
            if (lastMsg && lastMsg.role === 'assistant') {
              const { appendMessage } = useChatStore.getState()
              appendMessage(cid, {
                id: lastMsg.id,
                role: 'assistant',
                content: lastMsg.content,
                timestamp: lastMsg.timestamp,
                kind: lastMsg.kind === 'voice' ? 'voice' : 'text',
                duration: lastMsg.duration,
                audioDuration: lastMsg.audioDuration,
              })
            }
          }
          // Sync credits balance if provided
          if (msg.balance !== undefined) {
            const { setBalance } = (await import('../stores/creditsStore')).useCreditsStore.getState()
            setBalance(msg.balance)
          }
          // Silent model degradation: tell the user which model actually served
          // the turn (never surface a technical error).
          if (msg.degraded_to) {
            useToastStore.getState().show(`已切换到 ${modelLabel(msg.degraded_to)}`, 'info')
          }
          pendingVoiceTurnRef.current = false
          break
        case 'insufficient_credits':
          clearWatchdog()
          setGenerating(cid, false)
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          setPendingAssistantTurnId(null)
          pendingVoiceTurnRef.current = false
          {
            const { setInsufficientCredits } = useChatStore.getState()
            setInsufficientCredits(msg.needed ?? 0, msg.balance ?? 0)
          }
          break
        case 'model_forbidden':
          clearWatchdog()
          setGenerating(cid, false)
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          setPendingAssistantTurnId(null)
          pendingVoiceTurnRef.current = false
          {
            const { setModelForbidden } = useChatStore.getState()
            setModelForbidden(msg.model ?? '', msg.tier ?? 'free')
          }
          break
        case 'interrupted':
          clearWatchdog()
          setGenerating(cid, false)
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          setPendingAssistantTurnId(null)
          pendingVoiceTurnRef.current = false
          break
        case 'error': {
          clearWatchdog()
          setGenerating(cid, false)
          setStreaming(false)
          setPlaying(false)
          setPendingAssistantTurnId(null)
          pendingVoiceTurnRef.current = false
          const errCode = msg.code
          let errMsg: string = FEEDBACK_COPY.streamError
          if (errCode === 'SOUL_NOT_LOADED') {
            errMsg = '角色加载中，请稍后重试'
          } else if (errCode === 'SERVICE_UNAVAILABLE') {
            errMsg = '服务暂时不可用，请稍后重试'
          } else if (errCode === 'BILLING_CHECK_FAILED') {
            errMsg = '账户验证失败，请重试'
          } else if (errCode === 'VOICE_NOT_CONFIGURED') {
            errMsg = '该角色暂未配置音色，已切换为文字模式'
            // Also flip local voice_enabled back off so the next message
            // doesn't re-fire the same broken voice code path. Server side
            // still holds voice_enabled=true (we don't PATCH here) but the
            // client-side gate is enough to keep the user unstuck. When
            // they re-open the character backstage the switch will be shown
            // off; toggling on again will 409 and offer to configure.
            const errCharacterId = (msg as { character_id?: string }).character_id ?? cid
            if (errCharacterId) {
              useAppStore.getState().setVoiceChatEnabled(errCharacterId as CharacterId, false)
            }
          } else if (errCode === 'EMPTY_RESPONSE') {
            errMsg = '生成失败，请重试'
          } else if (errCode === 'PERSIST_FAILED') {
            errMsg = '消息保存失败，请重试'
          }
          useToastStore.getState().show(errMsg, 'error')
          break
        }
      }
    }

    ws.onclose = async (ev) => {
      // 1008 = token invalid/expired → try refresh once
      if (ev.code === 1008) {
        try {
          const { refreshToken } = useAuthStore.getState()
          if (refreshToken) {
            // Use the shared refresh dedup from api.ts
            const { doRefreshToken } = await import('../services/api')
            await doRefreshToken(refreshToken)
            // Reconnect with new token
            reconnectTimerRef.current = setTimeout(() => {
              reconnectTimerRef.current = null
              connectRef.current?.()
            }, 500)
            return
          }
        } catch {
          // Refresh failed — clear session, redirect via React Router
          useAuthStore.getState().clearSession()
          authNavigate('/login')
          return
        }
      }
      // Normal reconnect
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null
        connectRef.current?.()
      }, 2000)
    }

    ws.onerror = (err) => {
      console.error('[ws] error', err)
    }
  }, [addMessage, appendMessageAudio, appendToLast, finalizeMessageAudio, setGenerating, setStreaming, setPlaying, setCurrentTurnId, setPendingAssistantTurnId, setVad])

  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  const sendMessage = useCallback(
    (text: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
      if (isStreaming) return

      const { currentCharacterId } = useAppStore.getState()
      const characterId = currentCharacterId
      activeCharRef.current = characterId
      const { voiceChatEnabled, chatModel } = useAppStore.getState()
      const voiceEnabled = voiceChatEnabled?.[characterId] ?? false
      const model = chatModel?.[characterId] ?? 'deepseek'
      pendingVoiceTurnRef.current = voiceEnabled
      const turnId = crypto.randomUUID()
      addMessage(characterId, {
        id: `user-${turnId}`,
        role: 'user',
        content: text,
        timestamp: Date.now(),
      })
      // Sync user message to threads for HomePage
      {
        const { appendMessage: appendThread } = useChatStore.getState()
        appendThread(characterId, {
          id: `user-${turnId}`,
          role: 'user',
          content: text,
          timestamp: Date.now(),
          kind: 'text',
        })
      }
      setStreaming(true)
      setPendingAssistantTurnId(turnId)

      wsRef.current.send(
        JSON.stringify({
          type: 'chat',
          text,
          character_id: characterId,
          turn_id: turnId,
          voice_enabled: voiceEnabled,
          model,
        }),
      )
    },
    [addMessage, setStreaming, setPendingAssistantTurnId, isStreaming],
  )

  const interrupt = useCallback(() => {
    const turnId = useChatStore.getState().currentTurnId
    if (!wsRef.current || !turnId) return
    wsRef.current.send(JSON.stringify({ type: 'interrupt', turn_id: turnId }))
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      if (watchdogRef.current) {
        clearTimeout(watchdogRef.current)
        watchdogRef.current = null
      }
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  return { sendMessage, interrupt }
}
