import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getGoogleLoginConfig } from '../services/api'

export function safeGoogleReturnTo(path: unknown): string {
  return typeof path === 'string' && path.startsWith('/') && !path.startsWith('//')
    && !path.includes('\\') && !/^\/(auth|login|register)(\/|\?|$)/.test(path)
    ? path : '/character'
}

/** Available independently of language rollout. Age/consent stay with the parent form. */
export function GoogleSignInButton({ beforeStart, returnTo = '/character', disabled = false }: {
  beforeStart: () => boolean
  returnTo?: unknown
  disabled?: boolean
}) {
  const { t } = useTranslation()
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [starting, setStarting] = useState(false)
  useEffect(() => {
    let active = true
    void getGoogleLoginConfig().then(value => { if (active) setEnabled(value.enabled) })
      .catch(() => { if (active) setEnabled(false) })
    return () => { active = false }
  }, [])
  return <div className="my-3">
    <button type="button" disabled={!enabled || disabled || starting}
      className="w-full min-h-11 flex items-center justify-center gap-3 rounded-xl border border-[var(--color-border-glass)] text-[16px] disabled:opacity-50"
      onClick={() => {
        if (!beforeStart()) return
        try { sessionStorage.setItem('yuoyuo-google-return', safeGoogleReturnTo(returnTo)) } catch { /* Optional return path. */ }
        setStarting(true)
        window.location.assign('/api/auth/google/start')
      }}>
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 48 48">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6C44.4 38.03 46.98 31.87 46.98 24.55z" />
        <path fill="#FBBC05" d="M10.53 28.59C10.05 27.13 9.78 25.59 9.78 24s.27-3.13.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24s.92 7.54 2.56 10.78l7.97-6.19z" />
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.73-6c-2.15 1.45-4.92 2.3-8.18 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
      </svg>
      {t('continueWithGoogle')}
    </button>
    {enabled === false && <p role="status" className="mt-1 text-center text-xs text-[var(--color-text-muted)]">{t('googleUnavailable', { defaultValue: 'Google sign-in is not enabled yet.' })}</p>}
  </div>
}
