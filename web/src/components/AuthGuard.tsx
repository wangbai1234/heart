import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const hasSeenOnboarding = useAppStore((s) => s.hasSeenOnboarding)
  const location = useLocation()

  const publicPaths = ['/splash', '/onboarding', '/login', '/redeem', '/age-gate']
  const isPublic = publicPaths.some((p) => location.pathname.startsWith(p)) || location.pathname.startsWith('/legal/')

  // Public paths are always accessible
  if (isPublic) return <>{children}</>

  // Not authenticated → redirect
  if (!isAuthenticated()) {
    return <Navigate to={hasSeenOnboarding ? '/login' : '/onboarding'} replace />
  }

  // Authenticated but needs profile completion
  if (user && !user.birthdate && location.pathname !== '/settings/profile') {
    return <Navigate to="/settings/profile" replace />
  }

  // Authenticated but not age-verified
  if (user && user.birthdate && !user.age_verified && location.pathname !== '/age-gate') {
    return <Navigate to="/age-gate" replace />
  }

  return <>{children}</>
}
