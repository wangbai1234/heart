import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'

export function SplashPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const hasSeenOnboarding = useAppStore((s) => s.hasSeenOnboarding)
  const freeze = searchParams.get('qa') === 'freeze'
  // Fires exactly once per component mount. Deps in the original useEffect
  // used `isAuthenticated` (a function reference from zustand) which is stable
  // in steady state but re-created briefly during PWA cold-start rehydration.
  // The re-fire scheduled a second timer and, on some Chrome devtools sessions,
  // manifested as the /splash page flashing while the second navigate fought
  // with the first (TEST_REPORT_20260712 §7).
  const firedRef = useRef(false)

  // Note: the inline splash overlay is torn down from App.tsx so it's
  // removed regardless of which route mounts first.  Nothing to do here.

  useEffect(() => {
    if (freeze) return
    if (firedRef.current) return
    firedRef.current = true

    const delay = isAuthenticated() ? 0 : 1500
    const timer = setTimeout(() => {
      if (isAuthenticated()) {
        const lastRoute = localStorage.getItem('yuoyuo-last-route')
        const skip = ['/splash', '/onboarding', '/login', '/redeem', '/age-gate', '/', '']
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
