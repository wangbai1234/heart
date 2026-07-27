import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useThemeStore } from '../stores/themeStore'
import { Button } from '../components/ui/Button'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Toast } from '../components/ui/Toast'
import { changePassword, setPassword } from '../services/api'

const LockIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
)

export function ChangePasswordPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const { resolvedTheme } = useThemeStore()
  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.webp'
    : '/assets/backgrounds/聊天背景图.webp'

  // OTP-only users have no password yet → 设置密码 (no current password field).
  const hasPassword = user?.has_password ?? false

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<{ visible: boolean; message: string; variant: 'info' | 'error' | 'success' }>({
    visible: false,
    message: '',
    variant: 'info',
  })

  const showToast = (message: string, variant: 'info' | 'error' | 'success' = 'info') =>
    setToast({ visible: true, message, variant })

  const canSubmit =
    next.length >= 8 && next === confirm && (!hasPassword || current.length > 0)

  const handleSubmit = async () => {
    if (loading) return
    if (next.length < 8) {
      showToast('新密码至少 8 位', 'error')
      return
    }
    if (next !== confirm) {
      showToast('两次输入的密码不一致', 'error')
      return
    }
    setLoading(true)
    try {
      if (hasPassword) {
        await changePassword(current, next)
      } else {
        await setPassword(next)
        setUser({ has_password: true })
      }
      showToast('密码已更新', 'success')
      setTimeout(() => navigate(-1), 800)
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '操作失败，请重试', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative w-full h-full overflow-hidden">
      <img src={bgImage} alt="" className="absolute inset-0 h-full w-full object-cover z-0" />

      <div className="relative z-10 w-full h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3" style={{ paddingTop: 'var(--safe-top)' }}>
          <button onClick={() => navigate(-1)} className="w-[44px] h-[44px] flex items-center justify-center active:opacity-60 transition-opacity" aria-label="返回">
            <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="10,2 2,10 10,18" />
            </svg>
          </button>
          <h2 className="text-[17px] font-semibold text-[var(--color-ink)]">{hasPassword ? '修改密码' : '设置密码'}</h2>
          <div style={{ width: 40 }} />
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-8">
          <p className="text-[13px] text-[var(--color-text-secondary)] leading-[1.6] mb-4">
            {hasPassword
              ? '修改后，下次可用新密码登录。'
              : '你当前通过验证码登录。设置密码后，下次可直接用邮箱 + 密码登录。'}
          </p>

          <div className="bg-[var(--color-glass-card)] backdrop-blur-[20px] rounded-[20px] border border-[var(--color-border-glass)] shadow-[var(--shadow-card)] px-4 divide-y divide-[var(--color-divider-inset)] mb-6">
            {hasPassword && (
              <PasswordInput
                icon={LockIcon}
                placeholder="当前密码"
                value={current}
                onChange={setCurrent}
                autoComplete="current-password"
              />
            )}
            <PasswordInput
              icon={LockIcon}
              placeholder="新密码（至少 8 位）"
              value={next}
              onChange={setNext}
              autoComplete="new-password"
            />
            <PasswordInput
              icon={LockIcon}
              placeholder="确认新密码"
              value={confirm}
              onChange={setConfirm}
              autoComplete="new-password"
            />
          </div>

          <p className="text-xs text-[var(--color-text-muted)] -mt-4 mb-6 px-1">
            密码至少 8 位，建议包含字母和数字。
          </p>

          <Button variant="primary" size="lg" loading={loading} disabled={!canSubmit} onClick={handleSubmit}>
            {hasPassword ? '确认修改' : '确认设置'}
          </Button>
        </div>
      </div>

      <Toast
        visible={toast.visible}
        message={toast.message}
        variant={toast.variant}
        onDismiss={() => setToast((t) => ({ ...t, visible: false }))}
      />
    </div>
  )
}
