import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// Single source of truth for the human-readable app version. Bumped
// automatically on frontend commits by scripts/bump-web-version.sh (wired as a
// pre-commit hook). Copied verbatim into dist/version.json (it lives under
// public/), so a running client can fetch the *latest deployed* version and
// show it in the update prompt.
const versionUrl = new URL('./public/version.json', import.meta.url)
const APP_VERSION = JSON.parse(readFileSync(fileURLToPath(versionUrl), 'utf8')).version as string

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(APP_VERSION),
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      // 'prompt' (not 'autoUpdate'): a new deploy no longer silently reloads
      // the page. Instead useRegisterSW() surfaces a "有新版本，是否刷新" dialog
      // (see src/components/UpdatePrompt.tsx) and the user chooses when to apply.
      registerType: 'prompt',
      // Precache the built app shell; SPA routes fall back to index.html offline.
      includeAssets: ['apple-touch-icon.png', 'favicon-96.png'],
      manifest: {
        name: 'yuoyuo',
        short_name: 'yuoyuo',
        description: 'yuoyuo — AI companion',
        theme_color: '#0f0f14',
        background_color: '#0f0f14',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          { src: '/pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: '/pwa-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,woff2}', 'pwa-*.png', 'favicon-96.png', 'apple-touch-icon.png'],
        // Keep the precache to the app shell — large background art is loaded at
        // runtime, not precached (otherwise install pulls ~17MB up front).
        globIgnores: ['assets/backgrounds/**'],
        navigateFallback: '/index.html',
        // Never let the SW cache/serve API or WebSocket traffic.
        navigateFallbackDenylist: [/^\/api/],
        runtimeCaching: [
          {
            // Stale-while-revalidate for auth check: SW serves cached response
            // immediately on PWA cold start (eliminates the auth round-trip wait),
            // then updates the cache in the background.
            urlPattern: /^\/api\/auth\/me$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'auth-me-cache',
              expiration: { maxEntries: 1, maxAgeSeconds: 60 },
            },
          },
          {
            // Story cover images (top priority). Cover bytes for a given slug do
            // not change → CacheFirst so a refresh serves straight from the SW
            // cache with zero network, eliminating the cross-border round-trip.
            urlPattern: /\/api\/story\/covers\//,
            handler: 'CacheFirst',
            options: {
              cacheName: 'story-covers-cache',
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // User / character avatars — content-addressed (UUID filename), so
            // CacheFirst is safe and gives instant refreshes.
            urlPattern: /\/api\/profile\/avatar-file\//,
            handler: 'CacheFirst',
            options: {
              cacheName: 'avatars-cache',
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Large full-screen background art. Kept out of precache (globIgnores)
            // to avoid a ~17MB install, but cached at runtime so it loads once and
            // then serves from cache on every subsequent page/refresh.
            urlPattern: /\/assets\/backgrounds\/.*\.(?:webp|png)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'backgrounds-cache',
              expiration: { maxEntries: 40, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api/chat/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/api/story/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
