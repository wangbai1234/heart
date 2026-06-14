import { useCallback, useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'
import { createAudioPlayer, wrapPCM16AsWAV, type AudioPlayer } from '../services/audioPlayer'

const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/chat/ws`

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
  // Holds a player whose turn has ended but whose audio is still draining.
  // Stopped (audio cut) when the next turn starts via ensurePlayer().
  const drainingPlayerRef = useRef<AudioPlayer | null>(null)
  const seenChunks = useRef<Set<string>>(new Set())
  const audioPreBuffer = useRef<ArrayBuffer[] | null>(null)

  const addMessage = useChatStore(s => s.addMessage)
  const appendToLast = useChatStore(s => s.appendToLast)
  const setStreaming = useChatStore(s => s.setStreaming)
  const setPlaying = useChatStore(s => s.setPlaying)
  const setCurrentTurnId = useChatStore(s => s.setCurrentTurnId)
  const setVad = useChatStore(s => s.setVad)
  const isStreaming = useChatStore(s => s.isStreaming)

  const ensurePlayer = useCallback(async (format?: string): Promise<AudioPlayer> => {
    // Stop any draining player from the previous turn (its audio is cut on new turn start).
    if (drainingPlayerRef.current) {
      console.log('[ws] ensurePlayer: stopping draining player')
      try { drainingPlayerRef.current.stop() } catch { /* ignore */ }
      drainingPlayerRef.current = null
    }
    if (playerRef.current && playerRef.current.isAlive()) return playerRef.current
    if (playerRef.current) { try { playerRef.current.stop() } catch { /* ignore */ } }
    console.log('[ws] ensurePlayer: creating new player, format:', format ?? 'unknown')
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

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[ws] connected')
    }

    ws.onmessage = async (ev) => {
      const msg: WsMessage = JSON.parse(ev.data)
      switch (msg.type) {
        case 'turn_start':
          console.log('[ws] turn_start received, turn_id:', msg.turn_id)
          seenChunks.current.clear()
          setCurrentTurnId(msg.turn_id ?? null)
          addMessage({
            id: msg.turn_id ?? crypto.randomUUID(),
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
          })
          setPlaying(true)
          break
        case 'text_delta':
          appendToLast(msg.delta ?? '')
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
            if (msg.turn_id !== currentTurnId) {
              console.log('[ws] audio_chunk rejected: turn_id mismatch', msg.turn_id, '!==', currentTurnId)
              return
            }
            const key = `${msg.turn_id}:${msg.sentence_seq ?? 0}:${msg.seq}`
            if (seenChunks.current.has(key)) {
              console.log('[ws] audio_chunk rejected: duplicate', key)
              return
            }
            seenChunks.current.add(key)
            let buf = b64ToArrayBuffer(msg.data_b64)
            if (msg.format === 'pcm16') {
              buf = wrapPCM16AsWAV(buf)
            }
            // Pre-buffer: wait for 1 chunk before creating player and starting playback.
            // Reduced from 2 to 1 after lowering chunk size from 48KB to 8KB (1s → 170ms).
            const preBufferCount = 1
            if (!playerRef.current || !playerRef.current.isAlive()) {
              if (seenChunks.current.size < preBufferCount && !msg.is_last) {
                // Accumulate in a temp buffer instead of playing immediately
                if (!audioPreBuffer.current) audioPreBuffer.current = []
                audioPreBuffer.current.push(buf)
                console.log('[ws] audio_chunk pre-buffered', key, 'count:', audioPreBuffer.current.size)
                return
              }
              await ensurePlayer(msg.format)
              // Flush pre-buffered chunks
              if (audioPreBuffer.current) {
                for (const preBuf of audioPreBuffer.current) {
                  playerRef.current!.enqueue(preBuf)
                }
                audioPreBuffer.current = null
              }
            }
            console.log('[ws] audio_chunk enqueued', key, 'size:', buf.byteLength, 'fmt:', msg.format)
            playerRef.current!.enqueue(buf)
          }
          break
        case 'turn_end':
          // Move player to draining state so buffered audio plays out naturally.
          // ensurePlayer() on the next turn_start will stop it before starting fresh.
          console.log('[ws] turn_end received, player alive:', playerRef.current?.isAlive())
          if (playerRef.current) {
            drainingPlayerRef.current = playerRef.current
            playerRef.current = null
          }
          setStreaming(false)
          setPlaying(false)
          setCurrentTurnId(null)
          break
        case 'interrupted':
          console.log('[ws] interrupted received')
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
          console.error('[ws] error:', msg.msg)
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

    ws.onclose = () => {
      console.log('[ws] disconnected, reconnecting in 2s...')
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
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

      const { characterId } = useChatStore.getState()
      const turnId = crypto.randomUUID()
      addMessage({
        id: `user-${turnId}`,
        role: 'user',
        content: text,
        timestamp: Date.now(),
      })
      setStreaming(true)

      wsRef.current.send(
        JSON.stringify({
          type: 'chat',
          text,
          character_id: characterId,
          turn_id: turnId,
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
