import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
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
