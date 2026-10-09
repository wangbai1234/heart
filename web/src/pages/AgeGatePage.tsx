import { useTranslation } from 'react-i18next'
import { uiText } from '../i18n/text'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'

export function AgeGatePage() {
  useTranslation()
  const navigate = useNavigate()
  const clearSession = useAuthStore((s) => s.clearSession)

  const handleLogout = () => {
    clearSession()
    navigate('/character', { replace: true })
  }

  return (
    <div className="w-full h-full flex flex-col items-center justify-center px-8" style={{ background: 'var(--color-bg)' }}>
      <div className="text-center max-w-[320px]">
        <h2 className="text-[22px] font-bold text-[var(--color-ink)] mb-4">
          {uiText('ui137')}</h2>
        <p className="text-[15px] text-[var(--color-text-secondary)] leading-[1.8] mb-2">
          {uiText('ui138')}</p>
        <p className="text-[15px] text-[var(--color-text-secondary)] leading-[1.8] mb-8">
          {uiText('ui139')}</p>
        <div className="flex flex-col gap-3">
          <Button variant="secondary" size="lg" onClick={handleLogout}>
            {uiText('ui140')}</Button>
        </div>
      </div>
    </div>
  )
}
