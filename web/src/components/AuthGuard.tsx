import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const location = useLocation()

  // '/admin' is public to the user-session guard on purpose: the admin console
  // authenticates with its own X-Admin-Key (backend ADMIN_SECRET_KEY), not a
  // logged-in user, so it must not be bounced to /login.
  const exactPublicPaths = new Set([
    '/',
    '/splash',
    '/login',
    '/register',
    '/forgot-password',
    '/redeem',
    '/age-gate',
    '/character',
  ])
  const isPublic = exactPublicPaths.has(location.pathname)
    || location.pathname.startsWith('/admin')
    || location.pathname.startsWith('/legal/')

  // Public paths are always accessible
  if (isPublic) return <>{children}</>

  // Protected deep links return to the public catalog and open auth in place.
  if (!isAuthenticated()) {
    return (
      <Navigate
        to="/character"
        replace
        state={{ authRequired: true, from: location.pathname + location.search }}
      />
    )
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
