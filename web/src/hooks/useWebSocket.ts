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
  modality?: string
  credits_charged?: number
  balance?: number
  needed?: number
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

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const connectRef = useRef<(() => void) | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const seenChunks = useRef<Set<string>>(new Set())
  const activeCharRef = useRef<CharacterId>('rin')
  const pendingVoiceTurnRef = useRef(false)

  const addMessage = useChatStore(s => s.addMessage)
  const appendToLast = useChatStore(s => s.appendToLast)
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
          setStreaming(true)
          setPlaying(false)
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
        case 'message_bubble':
          // Replace the streaming placeholder (sequence_id=0) or add new bubble
          if (msg.sequence_id === 0) {
            // Replace the empty streaming message added by turn_start
            useChatStore.setState((s) => {
              const msgs = s.messages[cid] ?? []
              const updated = msgs.map((m, idx) =>
                idx === msgs.length - 1 && m.role === 'assistant'
                  ? { ...m, content: msg.content ?? '' }
                  : m
              )
              return { messages: { ...s.messages, [cid]: updated } }
            })
          } else {
            addMessage(cid, {
              id: `${msg.turn_id ?? ''}-${msg.sequence_id ?? 0}`,
              role: 'assistant',
              content: msg.content ?? '',
              timestamp: Date.now(),
              kind: 'text',
            })
          }
          break
        case 'turn_end':
          if (msg.turn_id) {
            finalizeMessageAudio(cid, msg.turn_id)
            if (msg.modality) {
              const normalizedKind = msg.modality === 'voice' ? 'voice' : 'text'
              useChatStore.setState((s) => ({
                messages: {
                  ...s.messages,
                  [cid]: (s.messages[cid] ?? []).map((message) =>
                    message.id === msg.turn_id ? { ...message, kind: normalizedKind } : message,
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
          pendingVoiceTurnRef.current = false
          break
        case 'insufficient_credits':
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
        case 'interrupted':
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          setPendingAssistantTurnId(null)
          pendingVoiceTurnRef.current = false
          break
        case 'error':
          setStreaming(false)
          setPlaying(false)
          setPendingAssistantTurnId(null)
          pendingVoiceTurnRef.current = false
          // Previously swallowed silently (SUG-1) — surface a friendly toast.
          useToastStore.getState().show(FEEDBACK_COPY.streamError, 'error')
          break
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
  }, [addMessage, appendMessageAudio, appendToLast, finalizeMessageAudio, setStreaming, setPlaying, setCurrentTurnId, setPendingAssistantTurnId, setVad])

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
      const { voiceChatEnabled } = useAppStore.getState()
      const voiceEnabled = voiceChatEnabled?.[characterId] ?? false
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
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  return { sendMessage, interrupt }
}
