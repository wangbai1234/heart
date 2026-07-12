import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import './index.css'

// Dev-mode service worker cleanup. In dev vite-plugin-pwa never registers a
// SW (devOptions.enabled defaults to false), but a stale SW from a prior
// `npm run preview` / prod-build test can survive in the browser. That old
// SW intercepts navigation fetches; the workbox-window `activated` handler
// installed by registerType:'autoUpdate' then fires window.location.reload()
// (vite-plugin-pwa react.js:48) — every reload re-triggers activation and
// the page enters an infinite reload loop that shows as "flashing" between
// /home and the inline splash overlay. See TEST_REPORT_20260712 §7.
if (import.meta.env.DEV && 'serviceWorker' in navigator) {
  navigator.serviceWorker
    .getRegistrations()
    .then((regs) => {
      if (regs.length === 0) return
      // Best-effort: unregister + purge caches, then hard-reload once so the
      // page is served fresh without any SW in the loop.
      const cleanup = Promise.all([
        Promise.all(regs.map((r) => r.unregister())),
        'caches' in window
          ? caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
          : Promise.resolve(),
      ])
      const wasControlled = !!navigator.serviceWorker.controller
      cleanup.finally(() => {
        console.info('[dev] Cleared', regs.length, 'stale service worker(s)')
        if (wasControlled) {
          // Only reload if a SW was actively controlling this page — a stale
          // registration that never took over doesn't need a reload.
          window.location.reload()
        }
      })
    })
    .catch(() => {
      // best-effort; keep going
    })
}

// StrictMode disabled: voice streaming playback triggers MSE SourceBuffer
// residual reuse under dev double-mount. Re-enable once player lifecycle
// is fully idempotent.
createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
)
