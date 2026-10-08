import { useTranslation } from 'react-i18next'
import { InterfaceLanguageSelect } from './LanguagePreferences'
import { international } from '../i18n/text'
import { uiText } from '../i18n/text'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { PasswordInput } from './ui/PasswordInput'
import { Toast } from './ui/Toast'
import {
  ApiError,
  loginWithPassword,
  logout,
  registerWithPassword,
  requestOtp,
  restoreAccount,
  updateProfile,
  verifyOtp,
} from '../services/api'
import { useAuthPromptStore } from '../stores/authPromptStore'
import { useAuthStore } from '../stores/authStore'

type Panel = 'login' | 'register'
type LoginMode = 'password' | 'otp'
type OtpStep = 'email' | 'code'
type ModalStep = 'auth' | 'restoration'

const MailIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <polyline points="22,6 12,13 2,6" />
  </svg>
)

const LockIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
)

const ShieldIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
    <path d="m9 12 2 2 4-4" />
  </svg>
)

const GiftIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="8" width="18" height="13" rx="2" />
    <path d="M12 8v13M2 8h20v4H2z" />
    <path d="M12 8H7.5A2.5 2.5 0 1 1 10 5.5C10 7 12 8 12 8ZM12 8h4.5A2.5 2.5 0 1 0 14 5.5C14 7 12 8 12 8Z" />
  </svg>
)

function safeReturnTo(path: string): string {
  return path.startsWith('/') && !path.startsWith('//') && !path.startsWith('/login')
    ? path
    : '/character'
}

export function AuthModal() {
  useTranslation()
  const navigate = useNavigate()
  const open = useAuthPromptStore((state) => state.open)
  const returnTo = useAuthPromptStore((state) => state.returnTo)
  const close = useAuthPromptStore((state) => state.close)
  const setSession = useAuthStore((state) => state.setSession)
  const clearSession = useAuthStore((state) => state.clearSession)
  const acceptLegalVersion = useAuthStore((state) => state.acceptLegalVersion)
  const [modalStep, setModalStep] = useState<ModalStep>('auth')
  const [restorationGraceEnd, setRestorationGraceEnd] = useState<string | null>(null)
  const [panel, setPanel] = useState<Panel>('login')
  const [loginMode, setLoginMode] = useState<LoginMode>('password')
  const [otpStep, setOtpStep] = useState<OtpStep>('email')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [code, setCode] = useState('')
  const [ageConfirmed, setAgeConfirmed] = useState(false)
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [cooldownEndAt, setCooldownEndAt] = useState(0)
  const [toast, setToast] = useState({ visible: false, message: '', variant: 'info' as 'info' | 'error' | 'success' })
  const [, refreshClock] = useState(0)

  const cooldown = Math.max(0, Math.ceil((cooldownEndAt - Date.now()) / 1000))
  const validEmail = useMemo(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email), [email])

  useEffect(() => {
    if (!open || cooldownEndAt <= Date.now()) return
    const timer = window.setInterval(() => refreshClock((value) => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [open, cooldownEndAt])

  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = previous }
  }, [open])

  useEffect(() => {
    if (!open) {
      setModalStep('auth')
      setRestorationGraceEnd(null)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const pending = sessionStorage.getItem('yuoyuo-pending-invite')
    if (pending) setInviteCode(pending.toUpperCase())
  }, [open])

  if (!open) return null

  const showToast = (message: string, variant: 'info' | 'error' | 'success' = 'info') =>
    setToast({ visible: true, message, variant })

  const finishAuth = async (result: Awaited<ReturnType<typeof loginWithPassword>>) => {
    setSession({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
      user: result.user,
    })
    acceptLegalVersion('v1.0')
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
      if (timezone) await updateProfile({ timezone })
    } catch {
      // Timezone sync is best-effort and must not block entry.
    }
    close()
    navigate(result.needs_profile ? '/settings/profile' : safeReturnTo(returnTo))
  }

  const handleAuthResult = async (result: Awaited<ReturnType<typeof loginWithPassword>>) => {
    if (!result.needs_restoration) {
      await finishAuth(result)
      return
    }

    setSession({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
      user: result.user,
    })
    acceptLegalVersion('v1.0')
    setRestorationGraceEnd(result.grace_end ?? null)
    setModalStep('restoration')
  }

  const handlePasswordLogin = async () => {
    if (!validEmail) return showToast(uiText('ui0'), 'error')
    if (!password) return showToast(uiText('ui1'), 'error')
    if (!ageConfirmed || !agreed) return showToast(uiText('ui2'), 'error')
    setLoading(true)
    try {
      const result = await loginWithPassword(email.trim().toLowerCase(), password)
      await handleAuthResult(result)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'no_password_set') {
        setLoginMode('otp')
        setOtpStep('email')
        showToast(uiText('ui3'), 'info')
      } else {
        showToast(error instanceof Error ? error.message : uiText('ui4'), 'error')
      }
    } finally {
      setLoading(false)
    }
  }

  const sendCode = async (purpose: 'login' | 'register') => {
    if (!validEmail) return showToast(uiText('ui0'), 'error')
    if (cooldown > 0 || loading) return
    setLoading(true)
    try {
      const result = await requestOtp(email.trim().toLowerCase(), purpose)
      setCooldownEndAt(Date.now() + result.cooldown * 1000)
      if (purpose === 'login') setOtpStep('code')
      showToast(uiText('ui5'), 'success')
    } catch (error) {
      if (purpose === 'login' && error instanceof ApiError && error.code === 'email_not_registered') {
        setPanel('register')
        showToast(uiText('ui6'), 'info')
      } else {
        showToast(error instanceof Error ? error.message : uiText('ui7'), 'error')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleOtpLogin = async () => {
    if (code.length !== 6) return showToast(uiText('ui8'), 'error')
    if (!ageConfirmed || !agreed) return showToast(uiText('ui2'), 'error')
    setLoading(true)
    try {
      const result = await verifyOtp(email.trim().toLowerCase(), code)
      await handleAuthResult(result)
    } catch (error) {
      showToast(error instanceof Error ? error.message : uiText('ui9'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async () => {
    if (!validEmail) return showToast(uiText('ui0'), 'error')
    if (code.length !== 6) return showToast(uiText('ui8'), 'error')
    if (password.length < 8) return showToast(uiText('ui10'), 'error')
    if (password !== confirmPassword) return showToast(uiText('ui11'), 'error')
    if (!ageConfirmed || !agreed) return showToast(uiText('ui2'), 'error')
    setLoading(true)
    try {
      const result = await registerWithPassword(
        email.trim().toLowerCase(),
        code,
        password,
        inviteCode.trim().toUpperCase() || undefined,
      )
      sessionStorage.removeItem('yuoyuo-pending-invite')
      await finishAuth(result)
    } catch (error) {
      showToast(error instanceof Error ? error.message : uiText('ui12'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const switchPanel = (next: Panel) => {
    setPanel(next)
    setCode('')
    setPassword('')
    setConfirmPassword('')
    setCooldownEndAt(0)
  }

  const dismiss = () => {
    if (modalStep === 'restoration') {
      const refreshToken = useAuthStore.getState().refreshToken
      void logout(refreshToken ?? undefined).catch(() => undefined)
      clearSession()
    }
    close()
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-3 min-[380px]:p-5" role="dialog" aria-modal="true" aria-label={uiText('ui13')}>
      <button className="absolute inset-0 bg-black/62 backdrop-blur-[8px]" onClick={dismiss} aria-label={uiText('ui14')} />
      <div className="relative flex max-h-[min(760px,calc(100dvh-24px))] w-full max-w-[400px] flex-col overflow-hidden rounded-[18px] border border-white/10 bg-[#17171C] text-white shadow-[0_24px_80px_rgba(0,0,0,0.48)]">
        <button onClick={dismiss} className="absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full text-white/55 transition-colors hover:bg-white/8 hover:text-white" aria-label={uiText('ui15')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="m6 6 12 12M18 6 6 18" /></svg>
        </button>

        <div className="shrink-0 px-5 pb-3 pt-5 text-center min-[380px]:px-6">
          <img src="/assets/ui/wordmark.png" alt="yuoyuo" className="mx-auto h-[46px] w-auto" />
          <p className="mt-1 text-[13px] text-white/56">{uiText('ui16')}</p>
          {international && <InterfaceLanguageSelect />}
        </div>

        {modalStep === 'auth' && (
          <div className="mx-5 grid shrink-0 grid-cols-2 rounded-[10px] bg-white/[0.055] p-1 min-[380px]:mx-6">
            {(['login', 'register'] as const).map((item) => (
              <button key={item} onClick={() => switchPanel(item)} className={`h-9 rounded-[8px] text-[14px] font-semibold transition-colors ${panel === item ? 'bg-[#FF7E9F] text-white' : 'text-white/52'}`}>
                {item === 'login' ? uiText('ui17') : uiText('ui18')}
              </button>
            ))}
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-4 min-[380px]:px-6">
          {modalStep === 'restoration' ? (
            <RestorationPanel
              graceEnd={restorationGraceEnd}
              loading={loading}
              onRestore={async () => {
                setLoading(true)
                try {
                  await restoreAccount()
                  try {
                    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
                    if (timezone) await updateProfile({ timezone })
                  } catch {
                    // Timezone sync is best-effort and must not block entry.
                  }
                  close()
                  navigate(safeReturnTo(returnTo))
                } catch (error) {
                  showToast(error instanceof Error ? error.message : uiText('ui19'), 'error')
                } finally {
                  setLoading(false)
                }
              }}
              onCancel={async () => {
                if (loading) return
                setLoading(true)
                const refreshToken = useAuthStore.getState().refreshToken
                try {
                  await logout(refreshToken ?? undefined)
                } catch {
                  // Logging out locally is sufficient if the network request fails.
                }
                clearSession()
                setPassword('')
                setModalStep('auth')
                setRestorationGraceEnd(null)
                setLoading(false)
              }}
            />
          ) : panel === 'login' ? (
            <>
              <div className="mb-3 flex gap-5 border-b border-white/8 text-[13px]">
                <button onClick={() => { setLoginMode('password'); setOtpStep('email'); setCode('') }} className={`pb-2 ${loginMode === 'password' ? 'border-b-2 border-[#FF7E9F] text-white' : 'text-white/45'}`}>{uiText('ui20')}</button>
                <button onClick={() => { setLoginMode('otp'); setOtpStep('email'); setCode('') }} className={`pb-2 ${loginMode === 'otp' ? 'border-b-2 border-[#FF7E9F] text-white' : 'text-white/45'}`}>{uiText('ui21')}</button>
              </div>
              <div className="divide-y divide-white/8 rounded-[10px] border border-white/10 bg-white/[0.035] px-3">
                <Input icon={MailIcon} placeholder={uiText('ui22')} value={email} onChange={setEmail} type="email" />
                {loginMode === 'password' ? (
                  <PasswordInput icon={LockIcon} placeholder={uiText('ui23')} value={password} onChange={setPassword} autoComplete="current-password" />
                ) : otpStep === 'email' ? null : (
                  <CodeRow code={code} setCode={setCode} cooldown={cooldown} loading={loading} onSend={() => void sendCode('login')} />
                )}
              </div>
              {loginMode === 'password' ? (
                <div className="mb-4 mt-2 flex justify-end"><Link to="/forgot-password" onClick={close} className="text-[12px] text-[#FF9AB3]">{uiText('ui24')}</Link></div>
              ) : otpStep === 'email' ? (
                <Button className="mt-4" variant="primary" size="lg" loading={loading} onClick={() => void sendCode('login')}>{uiText('ui25')}</Button>
              ) : (
                <button className="mb-4 mt-2 text-[12px] text-[#FF9AB3]" onClick={() => { setOtpStep('email'); setCode('') }}>{uiText('ui26')}</button>
              )}
              {(loginMode === 'password' || otpStep === 'code') && (
                <Button variant="primary" size="lg" loading={loading} onClick={() => void (loginMode === 'password' ? handlePasswordLogin() : handleOtpLogin())}>{uiText('ui17')}</Button>
              )}
            </>
          ) : (
            <>
              <div className="divide-y divide-white/8 rounded-[10px] border border-white/10 bg-white/[0.035] px-3">
                <Input icon={MailIcon} placeholder={uiText('ui22')} value={email} onChange={setEmail} type="email" />
                <CodeRow code={code} setCode={setCode} cooldown={cooldown} loading={loading} onSend={() => void sendCode('register')} />
                <PasswordInput icon={LockIcon} placeholder={uiText('ui27')} value={password} onChange={setPassword} autoComplete="new-password" />
                <PasswordInput icon={LockIcon} placeholder={uiText('ui28')} value={confirmPassword} onChange={setConfirmPassword} autoComplete="new-password" />
                <Input
                  icon={GiftIcon}
                  placeholder={uiText('ui29')}
                  value={inviteCode}
                  onChange={(value) => setInviteCode(value.replace(/\s/g, '').toUpperCase().slice(0, 16))}
                />
              </div>
              <Button className="mt-4" variant="primary" size="lg" loading={loading} onClick={() => void handleRegister()}>{uiText('ui30')}</Button>
            </>
          )}

          {modalStep === 'auth' && (
            <>
              <label className="mt-4 flex cursor-pointer items-start gap-2.5 text-left">
                <input type="checkbox" checked={ageConfirmed} onChange={(event) => setAgeConfirmed(event.target.checked)} className="mt-0.5 h-4 w-4 shrink-0 accent-[#FF7E9F]" />
                <span className="text-[12px] leading-[1.55] text-white/58">{uiText('ui31')}</span>
              </label>
              <label className="mt-2 flex cursor-pointer items-start gap-2.5 text-left">
                <input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} className="mt-0.5 h-4 w-4 shrink-0 accent-[#FF7E9F]" />
                <span className="text-[12px] leading-[1.55] text-white/58">
                  {uiText('ui32')}<Link to="/legal/terms" onClick={close} className="text-[#FF9AB3]">{uiText('ui33')}</Link>{uiText('ui34')}<Link to="/legal/privacy" onClick={close} className="text-[#FF9AB3]">{uiText('ui35')}</Link>
                </span>
              </label>
            </>
          )}
        </div>
      </div>
      <Toast visible={toast.visible} message={toast.message} variant={toast.variant} onDismiss={() => setToast((state) => ({ ...state, visible: false }))} />
    </div>
  )
}

function RestorationPanel({
  graceEnd,
  loading,
  onRestore,
  onCancel,
}: {
  graceEnd: string | null
  loading: boolean
  onRestore: () => void
  onCancel: () => void
}) {
  useTranslation()
  const daysLeft = graceEnd
    ? Math.max(0, Math.ceil((new Date(graceEnd).getTime() - Date.now()) / 86400000))
    : 0

  return (
    <div className="py-2 text-center">
      <h2 className="text-[18px] font-semibold text-white">{uiText('ui36')}</h2>

      <p className="mt-3 text-[14px] leading-[1.7] text-white/62">
        {uiText('ui37')}{daysLeft} {uiText('ui38')}</p>
      <p className="mt-1 text-[13px] text-white/42">{uiText('ui39')}</p>
      <Button className="mt-5" variant="primary" size="lg" loading={loading} onClick={onRestore}>
        {uiText('ui40')}</Button>
      <button
        type="button"
        onClick={onCancel}
        disabled={loading}
        className="mt-3 w-full py-2 text-[14px] text-white/42 transition-colors hover:text-white/65 disabled:opacity-50"
      >
        {uiText('ui41')}</button>
    </div>
  )
}

function CodeRow({ code, setCode, cooldown, loading, onSend }: { code: string; setCode: (value: string) => void; cooldown: number; loading: boolean; onSend: () => void }) {
  useTranslation()
  return (
    <div className="flex min-h-[52px] items-center gap-3 py-2">
      <span className="shrink-0 text-[#FF9AB3]">{ShieldIcon}</span>
      <input inputMode="numeric" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} maxLength={6} placeholder={uiText('ui42')} className="min-w-0 flex-1 bg-transparent text-[16px] text-white outline-none placeholder:text-white/28" />
      <button type="button" disabled={cooldown > 0 || loading} onClick={onSend} className="shrink-0 text-[12px] font-semibold text-[#FF9AB3] disabled:text-white/25">
        {cooldown > 0 ? `${cooldown}s` : uiText('ui43')}
      </button>
    </div>
  )
}
