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
    document.getElementById('__initial_splash__')?.remove()
  }, [])

  useEffect(() => {
    if (freeze) return
    const delay = isAuthenticated() ? 0 : 1500
    const timer = setTimeout(() => {
      if (isAuthenticated()) {
        const lastRoute = localStorage.getItem('yuoyuo-last-route')
        const skip = ['/splash', '/onboarding', '/login', '/redeem', '/', '']
        if (lastRoute && !skip.includes(lastRoute) && !lastRoute.startsWith('/legal/')) {
          navigate(lastRoute, { replace: true })
        } else {
          navigate('/home', { replace: true })
        }
      } else if (!hasSeenOnboarding) {
        navigate('/onboarding', { replace: true })
      } else {
        navigate('/login', { replace: true })
      }
    }, delay)

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
