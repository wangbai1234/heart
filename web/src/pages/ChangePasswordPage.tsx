import { useTranslation } from 'react-i18next'
import { uiText } from '../i18n/text'
import { useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'
import { PasswordInput } from '../components/ui/PasswordInput'
import { Toast } from '../components/ui/Toast'
import { changePassword, setPassword } from '../services/api'
import { useSafeBack } from '../hooks/useSafeBack'

const LockIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
)

export function ChangePasswordPage() {
  useTranslation()
  const goBack = useSafeBack('/settings')
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
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
      showToast(uiText('ui141'), 'error')
      return
    }
    if (next !== confirm) {
      showToast(uiText('ui11'), 'error')
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
      showToast(uiText('ui142'), 'success')
      setTimeout(goBack, 800)
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : uiText('ui143'), 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-atmosphere relative h-full w-full overflow-hidden">

      <div className="relative z-10 w-full h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3" style={{ paddingTop: 'var(--safe-top)' }}>
          <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center active:opacity-60 transition-opacity" aria-label={uiText('ui127')}>
            <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="10,2 2,10 10,18" />
            </svg>
          </button>
          <h2 className="text-[17px] font-semibold text-[var(--color-ink)]">{hasPassword ? uiText('ui144') : uiText('ui145')}</h2>
          <div style={{ width: 40 }} />
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-8">
          <p className="text-[13px] text-[var(--color-text-secondary)] leading-[1.6] mb-4">
            {hasPassword
              ? uiText('ui146')
              : uiText('ui147')}
          </p>

          <div className="bg-[var(--color-glass-card)] backdrop-blur-[20px] rounded-[20px] border border-[var(--color-border-glass)] shadow-[var(--shadow-card)] px-4 divide-y divide-[var(--color-divider-inset)] mb-6">
            {hasPassword && (
              <PasswordInput
                icon={LockIcon}
                placeholder={uiText('ui148')}
                value={current}
                onChange={setCurrent}
                autoComplete="current-password"
              />
            )}
            <PasswordInput
              icon={LockIcon}
              placeholder={uiText('ui149')}
              value={next}
              onChange={setNext}
              autoComplete="new-password"
            />
            <PasswordInput
              icon={LockIcon}
              placeholder={uiText('ui150')}
              value={confirm}
              onChange={setConfirm}
              autoComplete="new-password"
            />
          </div>

          <p className="text-xs text-[var(--color-text-muted)] -mt-4 mb-6 px-1">
            {uiText('ui151')}</p>

          <Button variant="primary" size="lg" loading={loading} disabled={!canSubmit} onClick={handleSubmit}>
            {hasPassword ? uiText('ui152') : uiText('ui153')}
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
