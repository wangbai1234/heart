import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const location = useLocation()

  // '/admin' is public to the user-session guard on purpose: the admin console
  // authenticates with its own X-Admin-Key (backend ADMIN_SECRET_KEY), not a
  // logged-in user, so it must not be bounced to /login.
  const publicPaths = ['/splash', '/login', '/register', '/forgot-password', '/redeem', '/age-gate', '/admin']
  const isPublic = publicPaths.some((p) => location.pathname.startsWith(p)) || location.pathname.startsWith('/legal/')

  // Public paths are always accessible
  if (isPublic) return <>{children}</>

  // Not authenticated → login (onboarding removed; registration is now the entry)
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
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
