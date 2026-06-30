import { Navigate, useLocation } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, hasSeenOnboarding } = useAppStore()
  const location = useLocation()

  const publicPaths = ['/splash', '/onboarding', '/login', '/redeem']
  const isPublic = publicPaths.some((p) => location.pathname.startsWith(p))

  if (isPublic) return <>{children}</>

  if (!isAuthenticated && hasSeenOnboarding) {
    return <Navigate to="/login" replace />
  }

  if (!isAuthenticated && !hasSeenOnboarding) {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}
