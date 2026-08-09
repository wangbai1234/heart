import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { OTPInput } from '../components/ui/OTPInput'
import { Toast } from '../components/ui/Toast'
import { SetPasswordModal } from '../components/SetPasswordModal'
import {
  requestOtp,
  verifyOtp,
  loginWithPassword,
  updateProfile,
  logout,
  restoreAccount,
  ApiError,
  type TokenResponse,
} from '../services/api'
import { useVisualViewport } from '../hooks/useVisualViewport'

const SESSION_KEY = 'yuoyuo-login-flow'

interface LoginFlowSnapshot {
  step: Step
  email: string
  cooldownEndAt: number
}

function readSnapshot(): LoginFlowSnapshot | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    return raw ? (JSON.parse(raw) as LoginFlowSnapshot) : null
  } catch {
    return null
  }
}

function writeSnapshot(snap: LoginFlowSnapshot) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(snap))
  } catch {
    // sessionStorage unavailable (e.g. private browsing limit) — ignore
  }
}

function clearSnapshot() {
  sessionStorage.removeItem(SESSION_KEY)
}

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

type Mode = 'password' | 'otp'
type Step = 'email' | 'code' | 'restoration'

export function LoginPage() {
  const snap = readSnapshot()
  const now = Date.now()

  // Password login is the default; OTP is the backward-compat path for
  // existing accounts that never set a password. A saved snapshot means the
  // user was mid-OTP-flow, so resume there.
  const [mode, setMode] = useState<Mode>(snap ? 'otp' : 'password')
  const [step, setStep] = useState<Step>(snap?.step ?? 'email')
  const [email, setEmail] = useState(snap?.email ?? '')
  const [password, setPassword] = useState('')
  // 18+ confirmation — required to sign in. Persisted on-device so a returning
  // user who already confirmed isn't re-prompted every login.
  const alreadyConfirmedAge = (() => {
    try { return localStorage.getItem('yuoyuo-age-confirmed') === '1' } catch { return false }
  })()
  const [ageConfirmed, setAgeConfirmed] = useState(alreadyConfirmedAge)
  const confirmAge = useCallback((checked: boolean) => {
    setAgeConfirmed(checked)
    try {
      if (checked) localStorage.setItem('yuoyuo-age-confirmed', '1')
      else localStorage.removeItem('yuoyuo-age-confirmed')
    } catch { /* storage unavailable — in-memory state still gates the button */ }
  }, [])
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })
  const [restorationGraceEnd, setRestorationGraceEnd] = useState<string | null>(null)
  // After auth, OTP-only users are invited to set a password before we route on.
  const [showSetPassword, setShowSetPassword] = useState(false)
  const [pendingDest, setPendingDest] = useState<string>('/character')
  // cooldown is derived from wall-clock; 0 means "not counting"
  const [cooldownEndAt, setCooldownEndAt] = useState<number>(
    snap && snap.cooldownEndAt > now ? snap.cooldownEndAt : 0
  )
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  const acceptLegalVersion = useAuthStore((s) => s.acceptLegalVersion)
  const { keyboardOpen } = useVisualViewport()

  // Derived cooldown seconds — always from wall-clock, immune to background throttle
  const [, forceRender] = useState(0)
  const cooldown = Math.max(0, Math.ceil((cooldownEndAt - Date.now()) / 1000))

  // Tick every second to update displayed cooldown
  useEffect(() => {
    if (cooldownEndAt <= Date.now()) return
    const t = setInterval(() => forceRender((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [cooldownEndAt])

  // Persist OTP flow state to sessionStorage whenever it changes
  useEffect(() => {
    if (mode !== 'otp') return
    if (step === 'email' && !email && !cooldownEndAt) return
    writeSnapshot({ step, email, cooldownEndAt })
  }, [mode, step, email, cooldownEndAt])

  // Restore state on bfcache restore (iOS Safari back navigation)
  useEffect(() => {
    const handlePageShow = (e: PageTransitionEvent) => {
      if (!e.persisted) return
      const restored = readSnapshot()
      if (!restored) return
      setMode('otp')
      setStep(restored.step)
      setEmail(restored.email)
      setCooldownEndAt(restored.cooldownEndAt)
    }
    window.addEventListener('pageshow', handlePageShow)
    return () => window.removeEventListener('pageshow', handlePageShow)
  }, [])

  const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

  // Shared post-auth routing. OTP-only users (has_password === false) get the
  // SetPasswordModal before we navigate; everyone else routes immediately.
  const finishLogin = useCallback(async (res: TokenResponse) => {
    setSession({
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
      user: res.user,
    })
    acceptLegalVersion('v1.0')
    clearSnapshot()

    if (res.needs_restoration) {
      setRestorationGraceEnd(res.grace_end ?? null)
      setStep('restoration')
      return
    }

    // Sync browser timezone to server on every login (handles cross-timezone travel)
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
      if (tz) await updateProfile({ timezone: tz })
    } catch {
      // Non-fatal: server will use the stored or default timezone
    }

    const dest = res.needs_profile ? '/settings/profile' : '/character'
    if (!res.user.has_password) {
      setPendingDest(dest)
      setShowSetPassword(true)
      return
    }
    navigate(dest, { replace: true })
  }, [setSession, acceptLegalVersion, navigate])

  const handlePasswordLogin = useCallback(async () => {
    if (loading) return
    if (!isValidEmail) { setToast({ visible: true, message: '请输入有效的邮箱' }); return }
    if (password.length === 0) { setToast({ visible: true, message: '请输入密码' }); return }
    if (!ageConfirmed) { setToast({ visible: true, message: '请先勾选确认你已年满 18 周岁' }); return }
    setLoading(true)
    try {
      const res = await loginWithPassword(email.trim().toLowerCase(), password)
      await finishLogin(res)
    } catch (err: unknown) {
      if (err instanceof ApiError && err.code === 'no_password_set') {
        setMode('otp')
        setStep('email')
        setToast({ visible: true, message: '该账号尚未设置密码，请使用验证码登录' })
      } else {
        setToast({ visible: true, message: err instanceof Error ? err.message : '登录失败，请重试' })
      }
    } finally {
      setLoading(false)
    }
  }, [email, password, isValidEmail, loading, finishLogin, ageConfirmed])

  const handleSendOtp = useCallback(async () => {
    if (loading) return
    if (!isValidEmail) { setToast({ visible: true, message: '请输入有效的邮箱' }); return }
    if (!ageConfirmed) { setToast({ visible: true, message: '请先勾选确认你已年满 18 周岁' }); return }
    setLoading(true)
    try {
      const res = await requestOtp(email.trim().toLowerCase(), 'login')
      setCooldownEndAt(Date.now() + res.cooldown * 1000)
      setStep('code')
    } catch (err: unknown) {
      if (err instanceof ApiError && err.code === 'email_not_registered') {
        setToast({ visible: true, message: '该邮箱未注册，正在前往注册页…' })
        setTimeout(() => navigate(`/register?email=${encodeURIComponent(email.trim().toLowerCase())}`), 1500)
      } else {
        setToast({ visible: true, message: '发送失败，请重试' })
      }
    } finally {
      setLoading(false)
    }
  }, [email, isValidEmail, loading, navigate, ageConfirmed])

  const handleVerify = useCallback(async (code: string) => {
    if (code.length !== 6 || loading) return
    setLoading(true)
    try {
      const res = await verifyOtp(email.trim().toLowerCase(), code)
      await finishLogin(res)
    } catch (err: unknown) {
      if (err instanceof ApiError && err.code === 'email_not_registered') {
        setToast({ visible: true, message: '该邮箱未注册，正在前往注册页…' })
        setTimeout(() => navigate(`/register?email=${encodeURIComponent(email.trim().toLowerCase())}`), 1500)
      } else {
        const msg = err instanceof Error ? err.message : '验证码错误，请重试'
        setToast({ visible: true, message: msg })
      }
    } finally {
      setLoading(false)
    }
  }, [email, loading, finishLogin, navigate])

  const handleResend = useCallback(async () => {
    if (cooldown > 0 || loading) return
    setLoading(true)
    try {
      const res = await requestOtp(email.trim().toLowerCase(), 'login')
      setCooldownEndAt(Date.now() + res.cooldown * 1000)
      setToast({ visible: true, message: '验证码已重新发送' })
    } catch (err: unknown) {
      if (err instanceof ApiError && err.code === 'email_not_registered') {
        setToast({ visible: true, message: '该邮箱未注册，正在前往注册页…' })
        setTimeout(() => navigate(`/register?email=${encodeURIComponent(email.trim().toLowerCase())}`), 1500)
      } else {
        setToast({ visible: true, message: '发送失败，请重试' })
      }
    } finally {
      setLoading(false)
    }
  }, [email, cooldown, loading, navigate])

  const switchMode = (next: Mode) => {
    if (next === mode) return
    setMode(next)
    setStep('email')
    setCooldownEndAt(0)
    if (next === 'password') clearSnapshot()
  }

  return (
    <div className="relative w-full h-full flex flex-col bg-[var(--color-bg-login)] overflow-hidden">
      {/* Hero illustration — collapses when keyboard is open */}
      <div
        className="relative w-full shrink-0 overflow-hidden transition-[height] duration-200 ease-out"
        style={{ height: keyboardOpen ? '80px' : '38%' }}
      >
        <img
          src="/assets/backgrounds/background_login_hero.webp"
          alt="yuoyuo"
          className="w-full h-full object-cover object-top"
        />
        <div className="absolute bottom-0 left-0 right-0 h-[80px] bg-gradient-to-t from-[var(--color-bg-login)] to-transparent" />
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5">
        {/* Brand zone — logo art carries the wordmark + tagline */}
        <div className="text-center mb-4 mt-1">
          <img
            src="/assets/ui/wordmark.webp"
            alt="yuoyuo"
            className="mx-auto w-[220px] max-w-[68%] h-auto select-none"
            draggable={false}
          />
        </div>

        {/* Form card */}
        <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[24px] border border-[var(--color-border-glass)] shadow-[var(--shadow-hero)] p-5 mb-4">
          {step === 'restoration' ? (
            <RestorationCard
              graceEnd={restorationGraceEnd}
              loading={loading}
              onRestore={async () => {
                setLoading(true)
                try {
                  await restoreAccount()
                  navigate('/character', { replace: true })
                } catch {
                  setToast({ visible: true, message: '恢复失败，请重试' })
                } finally {
                  setLoading(false)
                }
              }}
              onCancel={async () => {
                const { refreshToken, clearSession } = useAuthStore.getState()
                try { await logout(refreshToken ?? undefined) } catch { /* best-effort */ }
                clearSession()
                setMode('password')
                setStep('email')
                setPassword('')
              }}
            />
          ) : (
            <>
              {/* Mode tabs */}
              <div className="flex mb-5 rounded-[14px] bg-[var(--color-glass-35)] p-1">
                {(['password', 'otp'] as Mode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => switchMode(m)}
                    className={`flex-1 py-2 rounded-[11px] text-[14px] font-medium transition-colors ${
                      mode === m
                        ? 'bg-[var(--color-primary)] text-white shadow-sm'
                        : 'text-[var(--color-text-secondary)]'
                    }`}
                  >
                    {m === 'password' ? '密码登录' : '验证码登录'}
                  </button>
                ))}
              </div>

              {mode === 'password' ? (
                <>
                  <div className="divide-y divide-[var(--color-divider-inset)] mb-2">
                    <Input icon={MailIcon} placeholder="邮箱" value={email} onChange={setEmail} type="email" />
                    <PasswordInput icon={LockIcon} placeholder="密码" value={password} onChange={setPassword} autoComplete="current-password" />
                  </div>
                  <div className="flex justify-end mb-4">
                    <Link to="/forgot-password" className="text-[13px] text-[var(--color-primary)]">忘记密码？</Link>
                  </div>
                  <Button
                    variant="primary"
                    size="lg"
                    loading={loading}
                    disabled={loading}
                    onClick={handlePasswordLogin}
                  >
                    登录
                  </Button>
                </>
              ) : step === 'email' ? (
                <>
                  <Input icon={MailIcon} placeholder="你的邮箱" value={email} onChange={setEmail} type="email" />
                  <p className="text-[12px] text-[var(--color-text-secondary)] mt-2 mb-4 leading-[1.6]">
                    我们会向你的邮箱发送 6 位验证码，5 分钟内有效。
                  </p>
                  <Button
                    variant="primary"
                    size="lg"
                    loading={loading}
                    disabled={loading}
                    onClick={handleSendOtp}
                  >
                    发送验证码
                  </Button>
                </>
              ) : (
                <>
                  <p className="text-[13px] text-[var(--color-text-secondary)] text-center mb-4">
                    验证码已发送至 <span className="text-[var(--color-ink)] font-medium">{email}</span>
                  </p>
                  <div className="flex justify-center mb-4">
                    <OTPInput
                      length={6}
                      groupSize={3}
                      onComplete={handleVerify}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => { setStep('email'); setCooldownEndAt(0) }}
                      className="text-[13px] text-[var(--color-primary)]"
                    >
                      换邮箱
                    </button>
                    {cooldown > 0 ? (
                      <span className="text-[13px] text-[var(--color-text-muted)]">
                        {cooldown}s 后可重发
                      </span>
                    ) : (
                      <button
                        onClick={handleResend}
                        disabled={loading}
                        className="text-[13px] text-[var(--color-primary)]"
                      >
                        重新发送
                      </button>
                    )}
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {/* Register entry */}
        {step !== 'restoration' && (
          <p className="text-center text-[13px] text-[var(--color-text-secondary)] mb-3">
            没有账号？
            <Link to="/register" className="text-[var(--color-primary)] font-medium">点击注册</Link>
          </p>
        )}

        {/* Age (18+) confirmation — centered, stays visible after checking */}
        {step !== 'restoration' && (
          <label className="flex items-center justify-center gap-2 mb-3 cursor-pointer">
            <input
              type="checkbox"
              checked={ageConfirmed}
              onChange={(e) => confirmAge(e.target.checked)}
              className="w-4 h-4 shrink-0 accent-[var(--color-primary)]"
            />
            <span className="text-[12px] text-[var(--color-text-secondary)] leading-[1.6]">
              我确认已<span className="font-semibold text-[var(--color-ink)]">年满 18 周岁</span>（
              <Link to="/legal/age" className="text-[var(--color-primary)]" onClick={(e) => e.stopPropagation()}>年满18周岁确认</Link>
              ）
            </span>
          </label>
        )}

        {/* Legal text */}
        <p className="text-center text-[12px] text-[var(--color-text-secondary)] mb-3">
          继续即代表同意
          <Link to="/legal/terms" className="text-[var(--color-primary)]">《用户协议》</Link>
          与
          <Link to="/legal/privacy" className="text-[var(--color-primary)]">《隐私政策》</Link>
        </p>
      </div>

      {/* Bottom safe area */}
      <div style={{ height: 'var(--safe-bottom)' }} />

      <SetPasswordModal
        open={showSetPassword}
        onClose={() => {
          setShowSetPassword(false)
          navigate(pendingDest, { replace: true })
        }}
      />

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />

    </div>
  )
}

function RestorationCard({
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
  const daysLeft = graceEnd
    ? Math.max(0, Math.ceil((new Date(graceEnd).getTime() - Date.now()) / 86400000))
    : 0

  return (
    <div className="text-center">
      <h2 className="text-[18px] font-semibold text-[var(--color-ink)] mb-2">
        欢迎回来
      </h2>
      <p className="text-[14px] text-[var(--color-text-secondary)] mb-1">
        您的账号正处于冷静期（还剩 {daysLeft} 天），数据仍然保留。
      </p>
      <p className="text-[13px] text-[var(--color-text-muted)] mb-5">
        是否恢复账号并继续使用？
      </p>
      <Button
        variant="primary"
        size="lg"
        loading={loading}
        onClick={onRestore}
      >
        恢复账号
      </Button>
      <button
        onClick={onCancel}
        disabled={loading}
        className="mt-3 w-full text-center text-[14px] text-[var(--color-text-muted)] py-2 active:opacity-60"
      >
        不了，退出登录
      </button>
    </div>
  )
}
