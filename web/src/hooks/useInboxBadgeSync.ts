import { useEffect, useRef } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
import { useProactiveStore } from '../stores/proactiveStore'
import { getInboxSummary } from '../services/api'

// Polling cadence for the app-icon badge. Sixty seconds is a compromise
// between "badge updates before the user notices it's stale" and "we're
// not thrashing the API for a passive glance ornament." The hook also
// re-syncs on visibilitychange visible + when a fresh auth token arrives,
// which covers the common paths (tab focus, PWA foreground, login).
const POLL_INTERVAL_MS = 60_000

/**
 * Keeps `useAppStore.inboxUnreadTotal` in sync with the server-side unread
 * count so `useAppBadge` (mounted at the App root) reflects reality even
 * when the user has never opened the inbox page.
 *
 * Prior state: `inboxUnreadTotal` was only written by ChatInboxPage's mount
 * effect, so a user who lives on /home or /chat never saw the badge update
 * for incoming proactive messages (TEST_REPORT_20260712 §6.4).
 */
export function useInboxBadgeSync() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const setInboxUnreadTotal = useAppStore((s) => s.setInboxUnreadTotal)
  // Cache the last server-side unread so a proactive-store change can recompute
  // the total without waiting for the next network refresh.
  const serverUnreadRef = useRef(0)

  useEffect(() => {
    if (!accessToken) return
    let cancelled = false

    // Match ChatInboxPage's count: server unread + pending proactive messages
    // (SS06) not yet opened. Without the proactive term the tab badge
    // under-counts a character who just reached out until the user opens inbox.
    const recompute = () => {
      const pendingByChar = useProactiveStore.getState().pendingByChar
      const pendingTotal = Object.values(pendingByChar).reduce(
        (sum, list) => sum + list.length,
        0,
      )
      setInboxUnreadTotal(serverUnreadRef.current + pendingTotal)
    }

    const refresh = () => {
      getInboxSummary()
        .then((res) => {
          if (cancelled) return
          serverUnreadRef.current = res.items.reduce(
            (sum, item) => sum + (item.unread_count ?? 0),
            0,
          )
          recompute()
        })
        .catch(() => {
          // Best-effort; the badge is not load-bearing, don't spam the user
          // with toasts if the network flakes.
        })
    }

    refresh()
    const interval = window.setInterval(refresh, POLL_INTERVAL_MS)

    const onVisibility = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', onVisibility)

    // React to proactive polls landing between network refreshes: when a new
    // proactive message is ingested (or drained on open), recompute the badge
    // immediately off the cached server count.
    const unsubscribe = useProactiveStore.subscribe(recompute)

    return () => {
      cancelled = true
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibility)
      unsubscribe()
    }
  }, [accessToken, setInboxUnreadTotal])
}
