import { useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import type { ReactElement } from 'react'
import { setNavigate } from './services/navigation'
import { AuthGuard } from './components/AuthGuard'
import { SplashPage } from './pages/SplashPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { LoginPage } from './pages/LoginPage'
import { HomePage } from './pages/HomePage'
import { ChatInboxPage } from './pages/ChatInboxPage'
import { ChatLightPage } from './pages/ChatLightPage'
import { ChatDarkPage } from './pages/ChatDarkPage'
import { CharacterPage } from './pages/CharacterPage'
import { CharacterBackstagePage } from './pages/CharacterBackstagePage'
import { SettingsPage } from './pages/SettingsPage'
import { ProfileEditPage } from './pages/ProfileEditPage'
import { TransactionsPage } from './pages/TransactionsPage'
import { RedeemPage } from './pages/RedeemPage'
import { MembershipPage } from './pages/MembershipPage'
import { WalletPage } from './pages/WalletPage'
import { InvitePage } from './pages/InvitePage'
import { AgeGatePage } from './pages/AgeGatePage'
import { LegalPage } from './pages/LegalPage'
import { UIStatePreviewPage } from './pages/UIStatePreviewPage'
import { CreateCharacterPage } from './pages/CreateCharacterPage'
import { MyCharactersPage } from './pages/MyCharactersPage'
import { ToastContainer } from './components/ui/ToastContainer'
import { useProactivePolling } from './hooks/useProactivePolling'
import { useThemeStore } from './stores/themeStore'
import { useAppStore } from './stores/appStore'
import { useAuthStore } from './stores/authStore'
import { useCharactersStore } from './stores/charactersStore'
import { useAppBadge } from './hooks/useAppBadge'
import { useInboxBadgeSync } from './hooks/useInboxBadgeSync'
import { useSwipeNavigation } from './hooks/useSwipeNavigation'

function ChatConversationRouter() {
  const { resolvedTheme } = useThemeStore()
  return resolvedTheme === 'dark' ? <ChatDarkPage /> : <ChatLightPage />
}

// Catch-all target. Unknown routes previously all bounced to /splash, which
// re-triggered the splash timer chain. For authenticated sessions we jump
// directly to /home so a stray unknown path can never fight the SplashPage
// timer over which route wins (TEST_REPORT_20260712 §7).
function NotFoundRedirect(): ReactElement {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return <Navigate to={isAuthenticated() ? '/home' : '/splash'} replace />
}

const SKIP_SAVE_ROUTES = new Set(['/splash', '/onboarding', '/login', '/redeem', '/age-gate', '/'])

export function App() {
  const { fontScale } = useAppStore()
  const inboxUnreadTotal = useAppStore((s) => s.inboxUnreadTotal)
  const accessToken = useAuthStore((s) => s.accessToken)

  // Global badge: drives navigator.setAppBadge regardless of which page is active.
  useAppBadge(inboxUnreadTotal)
  // Global badge sync: without this hook the total only updates when the user
  // opens the inbox page. Users who live on /home or /chat had a stuck badge
  // (TEST_REPORT_20260712 §6.4).
  useInboxBadgeSync()
  // Global back gesture: priority=0 yields to any page that registers its own
  // priority=1 handler (HomePage blocks, ConversationChatPage overrides target).
  useSwipeNavigation({ priority: 0 })
  const loadCharacters = useCharactersStore((s) => s.load)
  const navigate = useNavigate()
  const location = useLocation()

  // Wire module-level navigate so api.ts / useWebSocket.ts can redirect
  // without a hard page reload (preserves React state and bfcache).
  useEffect(() => {
    setNavigate(navigate)
  }, [navigate])

  // Tear down the inline splash overlay from index.html once React has
  // committed its first render.  Previously SplashPage owned this, but any
  // route that mounts without going through /splash first — e.g. PWA
  // "restore last route" landing directly on /chat, or a hard-refresh at
  // a bookmarked URL — left the fixed z-index:9999 overlay covering the
  // whole viewport, which looked exactly like being "stuck on /splash".
  useEffect(() => {
    document.getElementById('__initial_splash__')?.remove()
  }, [])

  // Save last route so PWA can restore it on next open
  useEffect(() => {
    if (!SKIP_SAVE_ROUTES.has(location.pathname) && !location.pathname.startsWith('/legal/')) {
      localStorage.setItem('yuoyuo-last-route', location.pathname + location.search)
    }
  }, [location])

  useProactivePolling()

  // Load the server character catalog once the user is authenticated (UGC C4).
  useEffect(() => {
    if (accessToken) void loadCharacters()
  }, [accessToken, loadCharacters])

  // Capture ?invite=<code> from any entry URL (e.g. /login?invite=XXX) so it
  // survives the login redirect.
  useEffect(() => {
    const code = new URLSearchParams(location.search).get('invite')
    if (code) sessionStorage.setItem('yuoyuo-pending-invite', code)
  }, [location.search])

  // Once authenticated, bind any pending invite code (F5). Best-effort: self-
  // invite / already-bound errors are silently ignored.
  useEffect(() => {
    if (!accessToken) return
    const code = sessionStorage.getItem('yuoyuo-pending-invite')
    if (!code) return
    sessionStorage.removeItem('yuoyuo-pending-invite')
    void import('./services/api').then(({ bindInvite }) => bindInvite(code).catch(() => {}))
  }, [accessToken])

  useEffect(() => {
    const nextScale = (0.92 + fontScale * 0.0016).toFixed(3)
    document.documentElement.style.setProperty('--app-font-scale', nextScale)
  }, [fontScale])

  return (
    <AuthGuard>
      <ToastContainer />
      <Routes>
        <Route path="/" element={<Navigate to="/splash" replace />} />
        <Route path="/splash" element={<SplashPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/redeem" element={<RedeemPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/chat" element={<ChatInboxPage />} />
        <Route path="/chat/:characterId" element={<ChatConversationRouter />} />
        <Route path="/character-backstage" element={<CharacterBackstagePage />} />
        <Route path="/character" element={<CharacterPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/profile" element={<ProfileEditPage />} />
        <Route path="/credits/transactions" element={<TransactionsPage />} />
        <Route path="/membership" element={<MembershipPage />} />
        <Route path="/wallet" element={<WalletPage />} />
        <Route path="/invite" element={<InvitePage />} />
        <Route path="/age-gate" element={<AgeGatePage />} />
        <Route path="/legal/:type" element={<LegalPage />} />
        <Route path="/qa/states" element={<UIStatePreviewPage />} />
        <Route path="/characters/new" element={<CreateCharacterPage />} />
        <Route path="/my-characters" element={<MyCharactersPage />} />
        <Route path="*" element={<NotFoundRedirect />} />
      </Routes>
    </AuthGuard>
  )
}
