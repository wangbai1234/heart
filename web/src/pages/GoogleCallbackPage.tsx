import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { exchangeGoogleTicket } from '../services/api'
import { useAuthStore } from '../stores/authStore'

export function GoogleCallbackPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const started = useRef(false)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    if (started.current) return
    started.current = true
    const ticket = new URLSearchParams(window.location.hash.slice(1)).get('ticket')
    window.history.replaceState(null, '', window.location.pathname)
    if (!ticket) { setFailed(true); return }
    exchangeGoogleTicket(ticket).then(result => {
      useAuthStore.getState().setSession({ accessToken: result.access_token, refreshToken: result.refresh_token, user: result.user })
      useAuthStore.getState().acceptLegalVersion('v1.0')
      const destination = sessionStorage.getItem('yuoyuo-google-return') ?? '/character'
      sessionStorage.removeItem('yuoyuo-google-return')
      const safe = destination.startsWith('/') && !destination.startsWith('//') && !destination.includes('\\') && !destination.startsWith('/auth/')
      navigate(result.needs_profile ? '/settings/profile' : safe ? destination : '/character', { replace: true })
    }).catch(() => setFailed(true))
  }, [navigate])
  return <div className="p-6 text-center"><p>{failed ? t('googleLoginError') : t('loading')}</p>{failed && <button className="mt-4" onClick={() => navigate('/character', { replace: true })}>{t('back')}</button>}</div>
}
