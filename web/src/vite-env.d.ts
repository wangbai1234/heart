/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />
/// <reference types="vite-plugin-pwa/react" />

// Injected at build time by vite `define` (see vite.config.ts). Reads the
// single source of truth: web/public/version.json.
declare const __APP_VERSION__: string
