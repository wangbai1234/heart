import { useEffect, useRef } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useProactiveStore } from '../stores/proactiveStore'
import { getPendingProactive } from '../services/api'

const POLL_INTERVAL_MS = 90_000

/**
 * Polls the SS06 proactive-message endpoint while authenticated and the tab is
 * visible, feeding results into proactiveStore. Pauses when the tab is hidden
 * (saves battery + requests) and polls immediately when it becomes visible.
 *
 * Mounted once at the app root (App). No-op until the user is authenticated.
 */
export function useProactivePolling() {
  const inFlight = useRef(false)

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null
    let cancelled = false

    const poll = async () => {
      if (cancelled || inFlight.current) return
      if (document.hidden) return
      const { accessToken, user } = useAuthStore.getState()
      if (!accessToken || !user?.id) return

      inFlight.current = true
      try {
        const data = await getPendingProactive(user.id)
        if (!cancelled && data.messages?.length) {
          useProactiveStore.getState().ingest(data.messages)
        }
      } catch {
        // Best-effort background poll; failures are non-fatal and retried next tick.
      } finally {
        inFlight.current = false
      }
    }

    const onVisibility = () => {
      if (!document.hidden) void poll()
    }

    void poll()
    timer = setInterval(() => void poll(), POLL_INTERVAL_MS)
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      cancelled = true
      if (timer) clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])
}
