import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Toast } from '../components/ui/Toast'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })
  const navigate = useNavigate()
  const { setAuthenticated } = useAppStore()

  const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

  const handleSubmit = async () => {
    if (!isValidEmail) return
    setLoading(true)
    try {
      await new Promise((r) => setTimeout(r, 1500))
      setAuthenticated(true)
      navigate('/home', { replace: true })
    } catch {
      setToast({ visible: true, message: '发送失败，请重试' })
    } finally {
      setLoading(false)
    }
  }

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
            我们会向你的邮箱发送一次性登录链接，不需要密码。
          </p>
          <Button
            variant="primary"
            size="lg"
            loading={loading}
            disabled={!isValidEmail}
            onClick={handleSubmit}
          >
            发送登录链接
          </Button>
        </div>

        {/* Legal text */}
        <p className="text-center text-[12px] text-[var(--color-text-secondary)] mb-3">
          继续即代表同意
          <span className="text-[var(--color-primary)] cursor-pointer">《用户协议》</span>
          与
          <span className="text-[var(--color-primary)] cursor-pointer">《隐私政策》</span>
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
