import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'

export function SplashPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAuthenticated, hasSeenOnboarding } = useAppStore()
  const freeze = searchParams.get('qa') === 'freeze'

  useEffect(() => {
    if (freeze) return
    const timer = setTimeout(() => {
      if (isAuthenticated) {
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
        src="/assets/backgrounds/静态加载页面.png"
        alt="yuoyuo"
        className="absolute inset-0 w-full h-full object-cover"
      />
    </div>
  )
}
