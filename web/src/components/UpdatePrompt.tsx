import { useEffect, useState } from 'react'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { NoticeDialog } from './ui/NoticeDialog'

// PWA users can't just "点刷新" — a standalone-installed app has no address bar
// and its service worker keeps serving the cached shell across app restarts.
// So a new deploy is invisible until the SW is explicitly told to activate.
//
// With registerType: 'prompt' (vite.config.ts) the SW installs the new version
// but waits. useRegisterSW() flips `needRefresh` when that happens; we show a
// dialog and only reload when the user confirms. `updateServiceWorker(true)`
// calls skipWaiting() on the waiting SW and reloads the page onto it.
export function UpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW()

  const [latestVersion, setLatestVersion] = useState<string | null>(null)

  // On confirm, drop the cover caches before activating the new SW. Cover rules
  // are StaleWhileRevalidate (would otherwise serve the stale cached cover on
  // this first reload, only refreshing on the *next* one). Seed covers reuse a
  // fixed key, so a re-seed changes the bytes but not the URL — purging the
  // cache forces a fresh origin fetch, making the new cover visible on the same
  // reload the user just confirmed. Best-effort; ignore if Cache API is absent.
  async function confirmRefresh() {
    try {
      const names = await caches.keys()
      await Promise.all(
        names.filter((n) => n.includes('covers-cache')).map((n) => caches.delete(n)),
      )
    } catch {
      /* Cache API unavailable / blocked — reload still picks up the new SW */
    }
    await updateServiceWorker(true)
  }

  // When an update is waiting, fetch the freshly-deployed version.json to show
  // the user which version they'll get. version.json is not precached (not in
  // workbox globPatterns), and we bypass every cache layer, so this reflects
  // the new deploy — not the stale bundle this client is still running.
  useEffect(() => {
    if (!needRefresh) return
    let cancelled = false
    fetch(`/version.json?_=${Date.now()}`, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data?.version) setLatestVersion(String(data.version))
      })
      .catch(() => {
        /* best-effort: dialog still works without the exact new version */
      })
    return () => {
      cancelled = true
    }
  }, [needRefresh])

  if (!needRefresh) return null

  return (
    <NoticeDialog
      open={needRefresh}
      onClose={() => setNeedRefresh(false)}
      title="发现新版本"
      actionLabel="确认刷新"
      onAction={() => void confirmRefresh()}
    >
      当前有版本更新，刷新即可使用最新功能
      <br />
      <span className="text-[12px] text-[#9a9aa8]">
        当前版本 v{__APP_VERSION__}
        {latestVersion && latestVersion !== __APP_VERSION__ && (
          <> · 最新 v{latestVersion}</>
        )}
      </span>
    </NoticeDialog>
  )
}
