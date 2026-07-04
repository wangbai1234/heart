import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'

export function AgeGatePage() {
  const navigate = useNavigate()
  const clearSession = useAuthStore((s) => s.clearSession)

  const handleLogout = () => {
    clearSession()
    navigate('/login', { replace: true })
  }

  return (
    <div className="w-full h-full flex flex-col items-center justify-center px-8" style={{ background: 'var(--color-bg)' }}>
      <div className="text-center max-w-[320px]">
        <div className="text-[48px] mb-4">😔</div>
        <h2 className="text-[22px] font-bold text-[var(--color-ink)] mb-4">
          很抱歉
        </h2>
        <p className="text-[15px] text-[var(--color-text-secondary)] leading-[1.8] mb-2">
          yuoyuo 仅供年满 18 周岁的用户使用。
        </p>
        <p className="text-[15px] text-[var(--color-text-secondary)] leading-[1.8] mb-8">
          根据你提供的出生日期，你目前未满 18 周岁，暂时无法使用本产品。感谢你的理解，期待未来与你相遇。
        </p>
        <div className="flex flex-col gap-3">
          <Button variant="secondary" size="lg" onClick={handleLogout}>
            退出登录
          </Button>
        </div>
      </div>
    </div>
  )
}
