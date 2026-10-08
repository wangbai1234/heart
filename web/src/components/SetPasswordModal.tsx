import { useTranslation } from 'react-i18next'
import { uiText } from '../i18n/text'
import { useState } from 'react'
import { Dialog } from './ui/Dialog'
import { Button } from './ui/Button'
import { PasswordInput } from './ui/PasswordInput'
import { setPassword } from '../services/api'
import { useAuthStore } from '../stores/authStore'

const LockIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
)

/**
 * Prompt shown to OTP-only users (has_password === false) right after login,
 * inviting them to set a password for faster future logins. Fully skippable.
 * Styled entirely via the shared Dialog / Button / PasswordInput — no new palette.
 */
export function SetPasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  useTranslation()
  const [password, setPwd] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const setUser = useAuthStore((s) => s.setUser)

  const handleSubmit = async () => {
    if (loading) return
    if (password.length < 8) {
      setError(uiText('ui10'))
      return
    }
    if (password !== confirm) {
      setError(uiText('ui11'))
      return
    }
    setLoading(true)
    setError('')
    try {
      await setPassword(password)
      setUser({ has_password: true })
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : uiText('ui116'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={uiText('ui117')}
      actions={
        <>
          <Button variant="ghost" size="md" className="flex-1" onClick={onClose} disabled={loading}>
            {uiText('ui118')}</Button>
          <Button variant="primary" size="md" className="flex-1" onClick={handleSubmit} loading={loading}>
            {uiText('ui119')}</Button>
        </>
      }
    >
      <div className="text-left">
        <p className="text-[13px] text-[var(--color-text-secondary)] mb-3 text-center">
          {uiText('ui120')}</p>
        <div className="rounded-[16px] border border-[var(--color-border-glass)] bg-[var(--color-glass-35)] px-4 divide-y divide-[var(--color-divider-inset)]">
          <PasswordInput
            icon={LockIcon}
            placeholder={uiText('ui27')}
            value={password}
            onChange={setPwd}
            autoComplete="new-password"
          />
          <PasswordInput
            icon={LockIcon}
            placeholder={uiText('ui28')}
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
          />
        </div>
        <p className="text-[12px] text-[var(--color-text-muted)] mt-2 text-center">{uiText('ui10')}</p>
        {error && <p className="text-[12px] text-[var(--color-error)] mt-2 text-center">{error}</p>}
      </div>
    </Dialog>
  )
}
