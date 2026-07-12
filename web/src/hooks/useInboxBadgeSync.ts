import { useEffect } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
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

  useEffect(() => {
    if (!accessToken) return
    let cancelled = false

    const refresh = () => {
      getInboxSummary()
        .then((res) => {
          if (cancelled) return
          const total = res.items.reduce((sum, item) => sum + (item.unread_count ?? 0), 0)
          setInboxUnreadTotal(total)
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

    return () => {
      cancelled = true
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [accessToken, setInboxUnreadTotal])
}
