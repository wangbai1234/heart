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
    <div className="relative h-full w-full overflow-hidden bg-[#F5D0E0]">
      <img
        src="/assets/backgrounds/加载页.png"
        alt="yuoyuo 加载页"
        className="absolute inset-0 h-full w-full object-cover"
      />
    </div>
  )
}
