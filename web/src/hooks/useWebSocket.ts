import { useCallback, useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useAppStore } from '../stores/appStore'
import { useAuthStore } from '../stores/authStore'
import { createAudioPlayer, wrapPCM16AsWAV, type AudioPlayer } from '../services/audioPlayer'
import type { CharacterId } from '../data/uiContent'

const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/chat/ws`

interface WsMessage {
  type: string
  turn_id?: string
  delta?: string
  text?: string
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

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const connectRef = useRef<(() => void) | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const playerRef = useRef<AudioPlayer | null>(null)
  const drainingPlayerRef = useRef<AudioPlayer | null>(null)
  const seenChunks = useRef<Set<string>>(new Set())
  const audioPreBuffer = useRef<ArrayBuffer[] | null>(null)
  const activeCharRef = useRef<CharacterId>('rin')

  const addMessage = useChatStore(s => s.addMessage)
  const appendToLast = useChatStore(s => s.appendToLast)
  const setStreaming = useChatStore(s => s.setStreaming)
  const setPlaying = useChatStore(s => s.setPlaying)
  const setCurrentTurnId = useChatStore(s => s.setCurrentTurnId)
  const setVad = useChatStore(s => s.setVad)
  const isStreaming = useChatStore(s => s.isStreaming)

  const ensurePlayer = useCallback(async (format?: string): Promise<AudioPlayer> => {
    if (drainingPlayerRef.current) {
      try { drainingPlayerRef.current.stop() } catch { /* ignore */ }
      drainingPlayerRef.current = null
    }
    if (playerRef.current && playerRef.current.isAlive()) return playerRef.current
    if (playerRef.current) { try { playerRef.current.stop() } catch { /* ignore */ } }
    const p = createAudioPlayer(format)
    await p.init()
    p.onBufferedMs(() => {})
    playerRef.current = p
    return p
  }, [])

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
      console.log('[ws] no token, skipping connect')
      return
    }

    const ws = new WebSocket(`${WS_BASE}?token=${accessToken}`)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[ws] connected')
    }

    ws.onmessage = async (ev) => {
      const msg: WsMessage = JSON.parse(ev.data)
      const cid = activeCharRef.current
      switch (msg.type) {
        case 'turn_start':
          seenChunks.current.clear()
          setCurrentTurnId(msg.turn_id ?? null)
          addMessage(cid, {
            id: msg.turn_id ?? crypto.randomUUID(),
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
          })
          setStreaming(true)
          setPlaying(true)
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
            let buf = b64ToArrayBuffer(msg.data_b64)
            if (msg.format === 'pcm16') {
              buf = wrapPCM16AsWAV(buf)
            }
            const preBufferCount = 2
            if (!playerRef.current || !playerRef.current.isAlive()) {
              if (seenChunks.current.size < preBufferCount && !msg.is_last) {
                if (!audioPreBuffer.current) audioPreBuffer.current = []
                audioPreBuffer.current.push(buf)
                return
              }
              await ensurePlayer(msg.format)
              if (audioPreBuffer.current) {
                for (const preBuf of audioPreBuffer.current) {
                  playerRef.current!.enqueue(preBuf)
                }
                audioPreBuffer.current = null
              }
            }
            playerRef.current!.enqueue(buf)
          }
          break
        case 'turn_end':
          if (playerRef.current) {
            drainingPlayerRef.current = playerRef.current
            playerRef.current = null
          }
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
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
              })
            }
          }
          // Sync credits balance if provided
          if (msg.balance !== undefined) {
            const { setBalance } = (await import('../stores/creditsStore')).useCreditsStore.getState()
            setBalance(msg.balance)
          }
          break
        case 'insufficient_credits':
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          {
            const { setInsufficientCredits } = useChatStore.getState()
            setInsufficientCredits(msg.needed ?? 0, msg.balance ?? 0)
          }
          break
        case 'interrupted':
          if (drainingPlayerRef.current) {
            try { drainingPlayerRef.current.stop() } catch { /* ignore */ }
            drainingPlayerRef.current = null
          }
          playerRef.current?.stop()
          playerRef.current = null
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          break
        case 'error':
          if (drainingPlayerRef.current) {
            try { drainingPlayerRef.current.stop() } catch { /* ignore */ }
            drainingPlayerRef.current = null
          }
          playerRef.current?.stop()
          playerRef.current = null
          setStreaming(false)
          setPlaying(false)
          break
      }
    }

    ws.onclose = async (ev) => {
      console.log('[ws] disconnected', ev.code, ev.reason)
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
          // Refresh failed — clear session, go to login
          useAuthStore.getState().clearSession()
          window.location.href = '/login'
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
  }, [addMessage, appendToLast, setStreaming, setPlaying, setCurrentTurnId, setVad, ensurePlayer])

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
    [addMessage, setStreaming, isStreaming],
  )

  const interrupt = useCallback(() => {
    const turnId = useChatStore.getState().currentTurnId
    if (!wsRef.current || !turnId) return
    playerRef.current?.stop()
    playerRef.current = null
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
      if (drainingPlayerRef.current) {
        try { drainingPlayerRef.current.stop() } catch { /* ignore */ }
        drainingPlayerRef.current = null
      }
      playerRef.current?.stop()
      playerRef.current = null
    }
  }, [connect])

  return { sendMessage, interrupt }
}
