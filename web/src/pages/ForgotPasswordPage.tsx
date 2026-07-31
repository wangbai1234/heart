import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Toast } from '../components/ui/Toast'
import { requestOtp, resetPassword } from '../services/api'
import { useVisualViewport } from '../hooks/useVisualViewport'
import { useSafeBack } from '../hooks/useSafeBack'

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
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
)

type Phase = 'email' | 'reset'

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const goBack = useSafeBack('/login')
  const setSession = useAuthStore((s) => s.setSession)
  const { keyboardOpen } = useVisualViewport()

  const [phase, setPhase] = useState<Phase>('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [cooldownEndAt, setCooldownEndAt] = useState(0)
  const [toast, setToast] = useState<{ visible: boolean; message: string; variant: 'info' | 'error' | 'success' }>({
    visible: false,
    message: '',
    variant: 'info',
  })

  const [, forceRender] = useState(0)
  const cooldown = Math.max(0, Math.ceil((cooldownEndAt - Date.now()) / 1000))
  useEffect(() => {
    if (cooldownEndAt <= Date.now()) return
    const t = setInterval(() => forceRender((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [cooldownEndAt])

  const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  const showToast = (message: string, variant: 'info' | 'error' | 'success' = 'info') =>
    setToast({ visible: true, message, variant })

  const handleSendCode = useCallback(async () => {
    if (!isValidEmail) return showToast('请输入有效的邮箱', 'error')
    if (cooldown > 0 || loading) return
    setLoading(true)
    try {
      const res = await requestOtp(email.trim().toLowerCase(), 'password_reset')
      setCooldownEndAt(Date.now() + res.cooldown * 1000)
      setPhase('reset')
      showToast('验证码已发送', 'success')
    } catch {
      showToast('发送失败，请重试', 'error')
    } finally {
      setLoading(false)
    }
  }, [email, isValidEmail, cooldown, loading])

  const canReset = code.trim().length === 6 && password.length >= 8 && password === confirm

  const handleReset = async () => {
    if (loading) return
    if (code.trim().length !== 6) return showToast('请输入 6 位验证码', 'error')
    if (password.length < 8) return showToast('新密码至少 8 位', 'error')
    if (password !== confirm) return showToast('两次输入的密码不一致', 'error')

    setLoading(true)
    try {
      const res = await resetPassword(email.trim().toLowerCase(), code.trim(), password)
      setSession({ accessToken: res.access_token, refreshToken: res.refresh_token, user: res.user })
      showToast('密码已重置', 'success')
      setTimeout(() => {
        if (res.needs_profile) navigate('/settings/profile', { replace: true })
        else navigate('/character', { replace: true })
      }, 600)
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '重置失败，请重试', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative w-full h-full flex flex-col bg-[var(--color-bg-login)] overflow-hidden">
      {/* Header */}
      <div className="flex items-center px-5 pt-4 pb-2" style={{ paddingTop: 'calc(var(--safe-top) + 8px)' }}>
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center active:opacity-60" aria-label="返回">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5" style={{ paddingTop: keyboardOpen ? '8px' : '16px' }}>
        <div className="text-center mb-5">
          <h1 className="text-[28px] font-bold text-[var(--color-ink)] tracking-[0.02em] font-brand">找回密码</h1>
          <p className="text-[14px] text-[var(--color-text-muted)] mt-1">
            {phase === 'email' ? '输入注册邮箱，我们会发送验证码' : `验证码已发送至 ${email}`}
          </p>
        </div>

        <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[24px] border border-[var(--color-border-glass)] shadow-[var(--shadow-hero)] p-5 mb-4">
          {phase === 'email' ? (
            <>
              <Input icon={MailIcon} placeholder="邮箱" value={email} onChange={setEmail} type="email" />
              <div className="h-3" />
              <Button variant="primary" size="lg" loading={loading} disabled={!isValidEmail} onClick={handleSendCode}>
                发送验证码
              </Button>
            </>
          ) : (
            <>
              <div className="divide-y divide-[var(--color-divider-inset)]">
                <div className="flex items-center gap-3 py-3">
                  <span className="text-[var(--color-primary)] shrink-0">{ShieldIcon}</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="6 位验证码"
                    className="flex-1 min-w-0 bg-transparent outline-none text-[var(--color-ink)] placeholder-[var(--color-text-placeholder)] text-base"
                  />
                  <button
                    type="button"
                    onClick={handleSendCode}
                    disabled={cooldown > 0 || loading}
                    className="shrink-0 text-[13px] font-medium text-[var(--color-primary)] disabled:text-[var(--color-text-muted)] active:opacity-60"
                  >
                    {cooldown > 0 ? `${cooldown}s` : '重新发送'}
                  </button>
                </div>
                <PasswordInput icon={LockIcon} placeholder="新密码（至少 8 位）" value={password} onChange={setPassword} autoComplete="new-password" />
                <PasswordInput icon={LockIcon} placeholder="确认新密码" value={confirm} onChange={setConfirm} autoComplete="new-password" />
              </div>
              <p className="text-xs text-[var(--color-text-muted)] mt-2 px-1">
                验证码为 6 位数字；新密码至少 8 位。
              </p>
              <div className="h-4" />
              <Button variant="primary" size="lg" loading={loading} disabled={!canReset} onClick={handleReset}>
                重置密码并登录
              </Button>
            </>
          )}
        </div>

        <p className="text-center text-[13px] text-[var(--color-text-secondary)] mb-6">
          想起密码了？
          <Link to="/login" className="text-[var(--color-primary)] font-medium">返回登录</Link>
        </p>
      </div>

      <div style={{ height: 'var(--safe-bottom)' }} />

      <Toast
        visible={toast.visible}
        message={toast.message}
        variant={toast.variant}
        onDismiss={() => setToast((t) => ({ ...t, visible: false }))}
      />
    </div>
  )
}
