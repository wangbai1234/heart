import { useCallback, useEffect, useRef } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useToastStore } from '../stores/toastStore'
import { useStoryStore } from '../stores/storyStore'
import { authNavigate } from '../services/navigation'

/**
 * Story-mode WebSocket (SS09), the real-time turn channel for /story/:runId.
 *
 * A slim clone of useWebSocket: it speaks the SAME frame vocabulary
 * (turn_start / text_delta / message_bubble / turn_end / error) but has no
 * audio, no per-character concurrency — one run per socket. All transcript
 * mutations flow through storyStore so the player page stays a pure view.
 */
const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/story/ws`

interface StoryWsFrame {
  type: string
  turn_id?: string
  delta?: string
  content?: string
  kind?: 'narration' | 'dialogue' | 'action'
  npc_name?: string | null
  ok?: boolean
  code?: string
}

// Wall-clock ceiling for a single turn; if no turn_end/error arrives the UI
// force-clears the "正在续写" state so the player never gets stuck.
const TURN_WATCHDOG_MS = 90_000

const ERROR_COPY: Record<string, string> = {
  engine_unavailable: '剧情引擎暂时不可用，请稍后再试',
  run_not_found: '这局剧情不存在或已结束',
  scenario_not_found: '剧本已下架',
  empty_message: '说点什么再发送吧',
  generation_failed: '生成失败，请重试',
  turn_failed: '生成失败，请重试',
  turn_in_progress: 'GM 正在续写，请稍候',
  insufficient_credits: '余额不足，请充值后继续剧情',
  safety_blocked: '这条内容涉及高风险话题，无法继续。如果你正处于困境，请寻求专业帮助。',
}

export function useStoryWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const connectRef = useRef<(() => void) | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const watchdogRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // The run a frame belongs to. Frames don't carry run_id (the socket is
  // single-run), so we stamp the run the most recent story_chat targeted.
  const activeRunRef = useRef<string | null>(null)
  const activeTurnRef = useRef<string | null>(null)

  const clearWatchdog = useCallback(() => {
    if (watchdogRef.current) {
      clearTimeout(watchdogRef.current)
      watchdogRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    )
      return
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const { accessToken } = useAuthStore.getState()
    if (!accessToken) return

    const ws = new WebSocket(`${WS_BASE}?token=${accessToken}`)
    wsRef.current = ws

    ws.onmessage = (ev) => {
      const msg: StoryWsFrame = JSON.parse(ev.data)
      const runId = activeRunRef.current
      const store = useStoryStore.getState()
      switch (msg.type) {
        case 'turn_start':
          if (msg.turn_id) activeTurnRef.current = msg.turn_id
          if (runId) store.beginTurn(runId)
          break
        case 'text_delta':
          if (runId && msg.delta) store.appendDelta(runId, msg.delta)
          break
        case 'message_bubble':
          if (runId) {
            store.commitBubble(runId, {
              turn_id: msg.turn_id ?? null,
              kind: msg.kind ?? 'narration',
              npc_name: msg.npc_name ?? null,
              content: msg.content ?? '',
            })
          }
          break
        case 'turn_end':
          clearWatchdog()
          if (runId) store.endTurn(runId)
          activeTurnRef.current = null
          break
        case 'error': {
          clearWatchdog()
          if (runId) store.endTurn(runId)
          activeTurnRef.current = null
          const copy = ERROR_COPY[msg.code ?? ''] ?? '出了点问题，请重试'
          useToastStore.getState().show(copy, 'error')
          break
        }
      }
    }

    ws.onclose = async (ev) => {
      clearWatchdog()
      // 1008 = token invalid/expired → refresh once, then reconnect.
      if (ev.code === 1008) {
        try {
          const { refreshToken } = useAuthStore.getState()
          if (refreshToken) {
            const { doRefreshToken } = await import('../services/api')
            await doRefreshToken(refreshToken)
            reconnectTimerRef.current = setTimeout(() => {
              reconnectTimerRef.current = null
              connectRef.current?.()
            }, 500)
            return
          }
        } catch {
          useAuthStore.getState().clearSession()
          authNavigate('/login')
          return
        }
      }
      // 1011 = engine unavailable — don't hammer reconnect; surface once.
      if (ev.code === 1011) return
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null
        connectRef.current?.()
      }, 2000)
    }

    ws.onerror = (err) => {
      console.error('[story-ws] error', err)
    }
  }, [clearWatchdog])

  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  const sendMessage = useCallback(
    (runId: string, text: string): string | null => {
      const trimmed = text.trim()
      if (!trimmed) return null
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        useToastStore.getState().show('连接已断开，正在重连…', 'error')
        connectRef.current?.()
        return null
      }
      if (useStoryStore.getState().generatingByRun[runId]) return null

      const turnId = crypto.randomUUID()
      activeRunRef.current = runId
      activeTurnRef.current = turnId
      useStoryStore.getState().appendPlayerMessage(runId, trimmed, turnId)
      useStoryStore.getState().beginTurn(runId)

      // Watchdog: clear stuck state if the server goes silent.
      clearWatchdog()
      watchdogRef.current = setTimeout(() => {
        watchdogRef.current = null
        useStoryStore.getState().endTurn(runId)
        useToastStore.getState().show('响应超时，请重试', 'error')
      }, TURN_WATCHDOG_MS)

      wsRef.current.send(
        JSON.stringify({ type: 'story_chat', run_id: runId, text: trimmed, turn_id: turnId }),
      )
      return turnId
    },
    [clearWatchdog],
  )

  const interrupt = useCallback(() => {
    const turnId = activeTurnRef.current
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !turnId) return
    wsRef.current.send(JSON.stringify({ type: 'interrupt', turn_id: turnId }))
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      clearWatchdog()
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect, clearWatchdog])

  return { sendMessage, interrupt }
}
