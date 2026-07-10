/**
 * Module-level navigation singleton.
 * App.tsx calls setNavigate() once on mount; api.ts / useWebSocket.ts call
 * authNavigate() to redirect without a hard page reload.
 */
import type { NavigateFunction } from 'react-router-dom'

let _navigate: NavigateFunction | null = null

export function setNavigate(fn: NavigateFunction) {
  _navigate = fn
}

export function authNavigate(path: string) {
  if (_navigate) {
    _navigate(path, { replace: true })
  } else {
    // Fallback: should not normally reach here after App mounts
    window.location.href = path
  }
}
