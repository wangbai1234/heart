import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { OTPInput } from '../components/ui/OTPInput'
import { Toast } from '../components/ui/Toast'
import { requestOtp, verifyOtp } from '../services/api'

type Step = 'email' | 'code'

export function LoginPage() {
  const [step, setStep] = useState<Step>('email')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })
  const [cooldown, setCooldown] = useState(0)
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  const acceptLegalVersion = useAuthStore((s) => s.acceptLegalVersion)

  const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

  // Cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return
    const t = setInterval(() => setCooldown((c) => c - 1), 1000)
    return () => clearInterval(t)
  }, [cooldown])

  const handleSendOtp = useCallback(async () => {
    if (!isValidEmail || loading) return
    setLoading(true)
    try {
      const res = await requestOtp(email.trim().toLowerCase())
      setCooldown(res.cooldown)
      setStep('code')
    } catch {
      setToast({ visible: true, message: '发送失败，请重试' })
    } finally {
      setLoading(false)
    }
  }, [email, isValidEmail, loading])

  const handleVerify = useCallback(async (code: string) => {
    if (code.length !== 6 || loading) return
    setLoading(true)
    try {
      const res = await verifyOtp(email.trim().toLowerCase(), code)
      setSession({
        accessToken: res.access_token,
        refreshToken: res.refresh_token,
        user: res.user,
      })
      acceptLegalVersion('v1.0')
      if (res.needs_profile) {
        navigate('/settings/profile', { replace: true })
      } else {
        navigate('/home', { replace: true })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '验证码错误，请重试'
      setToast({ visible: true, message: msg })
    } finally {
      setLoading(false)
    }
  }, [email, loading, setSession, navigate])

  const handleResend = useCallback(async () => {
    if (cooldown > 0 || loading) return
    setLoading(true)
    try {
      const res = await requestOtp(email.trim().toLowerCase())
      setCooldown(res.cooldown)
      setToast({ visible: true, message: '验证码已重新发送' })
    } catch {
      setToast({ visible: true, message: '发送失败，请重试' })
    } finally {
      setLoading(false)
    }
  }, [email, cooldown, loading])

  return (
    <div className="relative w-full h-full flex flex-col bg-[var(--color-bg-login)] overflow-hidden">
      {/* Hero illustration */}
      <div className="relative w-full shrink-0" style={{ height: '45%' }}>
        <img
          src="/assets/backgrounds/background_login_hero.webp"
          alt="yuoyuo"
          className="w-full h-full object-cover"
        />
        <div className="absolute bottom-0 left-0 right-0 h-[80px] bg-gradient-to-t from-[var(--color-bg-login)] to-transparent" />
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5">
        {/* Brand zone */}
        <div className="text-center mb-5">
          <h1 className="text-[40px] font-bold text-[var(--color-ink)] tracking-[0.02em] font-brand">
            yuoyuo
          </h1>
          <p className="text-[14px] text-[var(--color-text-muted)] mt-1">
            一个会记得你的伙伴
          </p>
        </div>

        {/* Form card */}
        <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[24px] border border-[var(--color-border-glass)] shadow-[var(--shadow-hero)] p-5 mb-4">
          {step === 'email' ? (
            <>
              <Input
                icon={
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="4" width="20" height="16" rx="2" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                }
                placeholder="你的邮箱"
                value={email}
                onChange={setEmail}
                type="email"
              />
              <p className="text-[12px] text-[var(--color-text-secondary)] mt-2 mb-4 leading-[1.6]">
                我们会向你的邮箱发送 6 位验证码，5 分钟内有效。
              </p>
              <Button
                variant="primary"
                size="lg"
                loading={loading}
                disabled={!isValidEmail}
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
                  onClick={() => { setStep('email'); setCooldown(0) }}
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
        </div>

        {/* Legal text */}
        <p className="text-center text-[12px] text-[var(--color-text-secondary)] mb-3">
          继续即代表同意
          <Link to="/legal/terms" className="text-[var(--color-primary)]">《用户协议》</Link>
          与
          <Link to="/legal/privacy" className="text-[var(--color-primary)]">《隐私政策》</Link>
        </p>

        {/* Redeem link */}
        <button
          onClick={() => navigate('/redeem')}
          className="w-full text-center text-[14px] text-[var(--color-ink)] py-3 active:opacity-60"
        >
          我有兑换码，直接激活 →
        </button>
      </div>

      {/* Bottom safe area */}
      <div style={{ height: 'var(--safe-bottom)' }} />

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </div>
  )
}
