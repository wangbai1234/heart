/**
 * Module-level navigation singleton.
 * App.tsx calls setNavigate() once on mount; API and WebSocket clients use the
 * shared auth prompt flow without coupling themselves to React Router hooks.
 */
import type { NavigateFunction } from 'react-router-dom'
import { useAuthPromptStore } from '../stores/authPromptStore'

let _navigate: NavigateFunction | null = null
const PENDING_AUTH_RETURN_TO = 'yuoyuo-pending-auth-return-to'

export function setNavigate(fn: NavigateFunction | null) {
  _navigate = fn
}

function safeReturnTo(path: string): string {
  return path.startsWith('/') && !path.startsWith('//') && !path.startsWith('/login')
    ? path
    : '/character'
}

function currentReturnTo(): string {
  return safeReturnTo(`${window.location.pathname}${window.location.search}`)
}

/** Clear-page redirects break guest browsing. Reauthenticate over the catalog instead. */
export function promptAuthentication(returnTo = currentReturnTo()) {
  const destination = safeReturnTo(returnTo)

  if (_navigate) {
    useAuthPromptStore.getState().show(destination)
    _navigate('/character', { replace: true })
    return
  }

  // Requests can fail before App wires React Router during a cold PWA start.
  sessionStorage.setItem(PENDING_AUTH_RETURN_TO, destination)
  window.location.replace('/character')
}

export function consumePendingAuthentication(): string | null {
  const returnTo = sessionStorage.getItem(PENDING_AUTH_RETURN_TO)
  if (!returnTo) return null
  sessionStorage.removeItem(PENDING_AUTH_RETURN_TO)
  return safeReturnTo(returnTo)
}
