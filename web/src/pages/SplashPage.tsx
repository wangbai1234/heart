import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'

export function SplashPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const hasSeenOnboarding = useAppStore((s) => s.hasSeenOnboarding)
  const freeze = searchParams.get('qa') === 'freeze'

  useEffect(() => {
    if (freeze) return
    const timer = setTimeout(() => {
      if (isAuthenticated()) {
        navigate('/home', { replace: true })
      } else if (!hasSeenOnboarding) {
        navigate('/onboarding', { replace: true })
      } else {
        navigate('/login', { replace: true })
      }
    }, 2500)

    return () => clearTimeout(timer)
  }, [isAuthenticated, hasSeenOnboarding, navigate, freeze])

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#F5D0E0]">
      <img
        src="/assets/backgrounds/聊天背景图.png"
        alt=""
        className="absolute inset-0 w-full h-full object-cover"
      />
      <div className="absolute inset-0 bg-[rgba(255,255,255,0.14)]" />
      <img
        src="/assets/backgrounds/App Icon.png"
        alt="yuoyuo"
        className="absolute left-1/2 top-1/2 h-[180px] w-[180px] -translate-x-1/2 -translate-y-1/2 object-contain"
      />
    </div>
  )
}
