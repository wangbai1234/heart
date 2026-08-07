import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Toast } from '../components/ui/Toast'
import { requestOtp, registerWithPassword } from '../services/api'
import { useVisualViewport } from '../hooks/useVisualViewport'

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
const GiftIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 12 20 22 4 22 4 12" />
    <rect x="2" y="7" width="20" height="5" />
    <line x1="12" y1="22" x2="12" y2="7" />
    <path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z" />
    <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z" />
  </svg>
)

export function RegisterPage() {
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  const acceptLegalVersion = useAuthStore((s) => s.acceptLegalVersion)
  const { keyboardOpen } = useVisualViewport()
  const [searchParams] = useSearchParams()

  const [email, setEmail] = useState(searchParams.get('email') || '')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [ageConfirmed, setAgeConfirmed] = useState(false)
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [cooldownEndAt, setCooldownEndAt] = useState(0)
  const [toast, setToast] = useState<{ visible: boolean; message: string; variant: 'info' | 'error' | 'success' }>({
    visible: false,
    message: '',
    variant: 'info',
  })

  // Prefill invite code captured from ?invite=… on any entry URL.
  useEffect(() => {
    const pending = sessionStorage.getItem('yuoyuo-pending-invite')
    if (pending) setInviteCode(pending)
  }, [])

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
    if (!isValidEmail) {
      showToast('请输入有效的邮箱', 'error')
      return
    }
    if (cooldown > 0 || sending) return
    setSending(true)
    try {
      const res = await requestOtp(email.trim().toLowerCase(), 'register')
      setCooldownEndAt(Date.now() + res.cooldown * 1000)
      showToast('验证码已发送', 'success')
    } catch {
      showToast('发送失败，请重试', 'error')
    } finally {
      setSending(false)
    }
  }, [email, isValidEmail, cooldown, sending])

  const handleRegister = async () => {
    if (loading) return
    if (!isValidEmail) return showToast('请输入有效的邮箱', 'error')
    if (code.trim().length !== 6) return showToast('请输入 6 位验证码', 'error')
    if (password.length < 8) return showToast('密码至少 8 位', 'error')
    if (password !== confirm) return showToast('两次输入的密码不一致', 'error')
    if (!ageConfirmed) return showToast('请先确认你已年满 18 周岁', 'error')
    if (!agreed) return showToast('请先同意用户协议与隐私政策', 'error')

    setLoading(true)
    try {
      const res = await registerWithPassword(
        email.trim().toLowerCase(),
        code.trim(),
        password,
        inviteCode.trim() || undefined,
      )
      setSession({ accessToken: res.access_token, refreshToken: res.refresh_token, user: res.user })
      acceptLegalVersion('v1.0')
      sessionStorage.removeItem('yuoyuo-pending-invite')
      if (res.needs_profile) {
        navigate('/settings/profile', { replace: true })
      } else {
        navigate('/character', { replace: true })
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '注册失败，请重试', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative w-full h-full flex flex-col bg-[var(--color-bg-login)] overflow-hidden">
      <div className="flex-1 overflow-y-auto px-5" style={{ paddingTop: keyboardOpen ? '16px' : 'calc(var(--safe-top) + 24px)' }}>
        {/* Brand */}
        <div className="text-center mb-5">
          <h1 className="text-[32px] font-bold text-[var(--color-ink)] tracking-[0.02em] font-brand">
            创建账号
          </h1>
          <p className="text-[14px] text-[var(--color-text-muted)] mt-1">加入 yuoyuo，开启你的虚拟宇宙</p>
        </div>

        {/* Form card */}
        <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[24px] border border-[var(--color-border-glass)] shadow-[var(--shadow-hero)] p-5 mb-4">
          <div className="divide-y divide-[var(--color-divider-inset)]">
            <Input icon={MailIcon} placeholder="邮箱" value={email} onChange={setEmail} type="email" />

            {/* Code + send button */}
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
                disabled={cooldown > 0 || sending || !isValidEmail}
                className="shrink-0 text-[13px] font-medium text-[var(--color-primary)] disabled:text-[var(--color-text-muted)] active:opacity-60"
              >
                {cooldown > 0 ? `${cooldown}s` : sending ? '发送中…' : '获取验证码'}
              </button>
            </div>

            <PasswordInput icon={LockIcon} placeholder="设置密码（至少 8 位）" value={password} onChange={setPassword} autoComplete="new-password" />
            <PasswordInput icon={LockIcon} placeholder="确认密码" value={confirm} onChange={setConfirm} autoComplete="new-password" />
            <Input icon={GiftIcon} placeholder="邀请码（选填）" value={inviteCode} onChange={setInviteCode} />
          </div>

          <p className="text-xs text-[var(--color-text-muted)] mt-2 px-1">
            验证码为 6 位数字；密码至少 8 位。推荐使用 QQ 邮箱注册，验证码会以 QQ 通知形式送达，无需另开邮箱。
          </p>

          {/* Age (18+) confirmation — required */}
          <label className="flex items-start gap-2 mt-4 mb-3 cursor-pointer">
            <input
              type="checkbox"
              checked={ageConfirmed}
              onChange={(e) => setAgeConfirmed(e.target.checked)}
              className="mt-[3px] w-4 h-4 shrink-0 accent-[var(--color-primary)]"
            />
            <span className="text-[12px] text-[var(--color-text-secondary)] leading-[1.6]">
              我确认本人已<span className="font-semibold text-[var(--color-ink)]">年满 18 周岁</span>，并已阅读
              <Link to="/legal/age" className="text-[var(--color-primary)]">《年满18周岁确认》</Link>
              。本产品仅供成年人使用。
            </span>
          </label>

          {/* Legal checkbox */}
          <label className="flex items-start gap-2 mb-4 cursor-pointer">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="mt-[3px] w-4 h-4 shrink-0 accent-[var(--color-primary)]"
            />
            <span className="text-[12px] text-[var(--color-text-secondary)] leading-[1.6]">
              我已阅读并同意
              <Link to="/legal/terms" className="text-[var(--color-primary)]">《用户协议》</Link>
              与
              <Link to="/legal/privacy" className="text-[var(--color-primary)]">《隐私政策》</Link>
            </span>
          </label>

          <Button variant="primary" size="lg" loading={loading} disabled={loading} onClick={handleRegister}>
            注册
          </Button>
        </div>

        <p className="text-center text-[13px] text-[var(--color-text-secondary)] mb-6">
          已有账号？
          <Link to="/login" className="text-[var(--color-primary)] font-medium">去登录</Link>
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
