import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import type { ReactElement } from 'react'
import { consumePendingAuthentication, setNavigate } from './services/navigation'
import { AuthGuard } from './components/AuthGuard'
import { SplashPage } from './pages/SplashPage'
import { RegisterPage } from './pages/RegisterPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ChangePasswordPage } from './pages/ChangePasswordPage'
import { ChatInboxPage } from './pages/ChatInboxPage'
import { ChatLightPage } from './pages/ChatLightPage'
import { ChatDarkPage } from './pages/ChatDarkPage'
import { CharacterPage } from './pages/CharacterPage'
import { CharacterProfilePage } from './pages/CharacterProfilePage'
import { VoiceCallPage } from './pages/VoiceCallPage'
import { SettingsPage } from './pages/SettingsPage'
import { ProfileEditPage } from './pages/ProfileEditPage'
import { TransactionsPage } from './pages/TransactionsPage'
import { RedeemPage } from './pages/RedeemPage'
import { MembershipPage } from './pages/MembershipPage'
import { WalletPage } from './pages/WalletPage'
import { AgeGatePage } from './pages/AgeGatePage'
import { LegalPage } from './pages/LegalPage'
import { UIStatePreviewPage } from './pages/UIStatePreviewPage'
import { MyCharactersPage } from './pages/MyCharactersPage'
import { CreateHubPage } from './pages/CreateHubPage'
import { QuickCreatePage } from './pages/QuickCreatePage'
import { QuickConfirmPage } from './pages/QuickConfirmPage'
import { WorkshopCreatePage } from './pages/WorkshopCreatePage'
import { ExplorePage } from './pages/ExplorePage'
import { ScenarioDetailPage } from './pages/ScenarioDetailPage'
import { StoryPlayerPage } from './pages/StoryPlayerPage'
import { RewardsPage } from './pages/RewardsPage'
import { AdminReviewPage } from './pages/AdminReviewPage'
import { ToastContainer } from './components/ui/ToastContainer'
import { UpdatePrompt } from './components/UpdatePrompt'
import { DailyCheckinDialog } from './components/DailyCheckinDialog'
import { ReviewResultDialog, PublishIncentiveDialog } from './components/ReviewDialogs'
import type { ReviewUpdateDTO } from './services/api'
import { useCreditsStore } from './stores/creditsStore'
import { useProactivePolling } from './hooks/useProactivePolling'
import { useThemeStore } from './stores/themeStore'
import { useAppStore } from './stores/appStore'
import { useAuthStore } from './stores/authStore'
import { useCharactersStore } from './stores/charactersStore'
import { useAuthPromptStore } from './stores/authPromptStore'
import { useModelsStore } from './stores/modelsStore'
import { useAppBadge } from './hooks/useAppBadge'
import { useInboxBadgeSync } from './hooks/useInboxBadgeSync'
import { useSwipeNavigation } from './hooks/useSwipeNavigation'
import { AuthModal } from './components/AuthModal'

function ChatConversationRouter() {
  const { resolvedTheme } = useThemeStore()
  return resolvedTheme === 'dark' ? <ChatDarkPage /> : <ChatLightPage />
}

function VoiceCallRouter() {
  const { resolvedTheme } = useThemeStore()
  return <VoiceCallPage isDark={resolvedTheme === 'dark'} />
}

// Catch-all target. Unknown routes previously all bounced to /splash, which
// re-triggered the splash timer chain. For authenticated sessions we jump
// directly to /character (the new landing page after removing /home) so a
// stray unknown path can never fight the SplashPage timer over which route
// wins (TEST_REPORT_20260712 §7).
function NotFoundRedirect(): ReactElement {
  return <Navigate to="/character" replace />
}

function LegacyLoginRedirect(): ReactElement {
  const location = useLocation()
  return (
    <Navigate
      to={{ pathname: '/character', search: location.search }}
      replace
      state={{ authRequired: true, from: '/character' }}
    />
  )
}

const SKIP_SAVE_ROUTES = new Set(['/splash', '/login', '/register', '/forgot-password', '/redeem', '/age-gate', '/'])

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
  const refreshModels = useModelsStore((s) => s.refresh)
  const mergeChatModels = useAppStore((s) => s.mergeChatModels)
  const navigate = useNavigate()
  const location = useLocation()
  const showAuthPrompt = useAuthPromptStore((state) => state.show)
  const [checkinOpen, setCheckinOpen] = useState(false)
  const [checkinCoins, setCheckinCoins] = useState(0)
  // Character review: queue of unacked terminal results + daily incentive popup.
  const [reviewQueue, setReviewQueue] = useState<ReviewUpdateDTO[]>([])
  const [incentiveOpen, setIncentiveOpen] = useState(false)

  // Wire module-level navigate so api.ts / useWebSocket.ts can redirect
  // without a hard page reload (preserves React state and bfcache).
  useEffect(() => {
    setNavigate(navigate)
    return () => setNavigate(null)
  }, [navigate])

  useEffect(() => {
    const returnTo = consumePendingAuthentication()
    if (returnTo) showAuthPrompt(returnTo)
  }, [showAuthPrompt])

  useEffect(() => {
    const routeState = location.state as { authRequired?: boolean; from?: string } | null
    if (!routeState?.authRequired) return
    showAuthPrompt(routeState.from)
    navigate('/character', { replace: true, state: null })
  }, [location.state, navigate, showAuthPrompt])

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

  // Hydrate the server catalog and cross-device per-character selections.
  // An empty server map leaves migrated local choices intact; characters with
  // no choice naturally use Gemini 3.1.
  useEffect(() => {
    if (!accessToken) return
    void refreshModels().catch(() => {})
    void import('./services/api').then(({ getModelPreferences }) =>
      getModelPreferences()
        .then((result) => mergeChatModels(result.preferences))
        .catch(() => {}),
    )
  }, [accessToken, mergeChatModels, refreshModels])

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

  // Daily check-in: on first authenticated load of the day, claim the reward
  // (server is idempotent per calendar day) and show the notification dialog
  // only when a fresh grant landed. A localStorage day-stamp guards against
  // re-requesting on every route change within the same day.
  useEffect(() => {
    if (!accessToken) return
    const day = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(new Date())
    if (localStorage.getItem('yuoyuo-checkin-day') === day) return
    void import('./services/api').then(({ dailyCheckin }) =>
      dailyCheckin()
        .then((res) => {
          localStorage.setItem('yuoyuo-checkin-day', day)
          if (res.granted) {
            setCheckinCoins(res.coins)
            setCheckinOpen(true)
            void useCreditsStore.getState().refresh()
          }
        })
        .catch(() => {}),
    )
  }, [accessToken])

  // Character review popups: on authenticated load, fetch the caller's review
  // updates. Any terminal result the user hasn't confirmed becomes a queued
  // result popup (server-acked on confirm, so it never re-fires). If the user
  // has no approved characters yet, show a once-per-day publish incentive popup.
  useEffect(() => {
    if (!accessToken) return
    void import('./services/api').then(({ getReviewUpdates }) =>
      getReviewUpdates()
        .then((res) => {
          const pending = res.characters.filter((c) => c.needs_ack)
          if (pending.length > 0) {
            setReviewQueue(pending)
            return
          }
          // No result to confirm — consider the daily incentive popup.
          if (res.approved_count === 0) {
            const day = new Date().toISOString().slice(0, 10)
            if (localStorage.getItem('yuoyuo-publish-incentive-day') !== day) {
              localStorage.setItem('yuoyuo-publish-incentive-day', day)
              setIncentiveOpen(true)
            }
          }
        })
        .catch(() => {}),
    )
  }, [accessToken])

  // Confirm the front result in the queue: ack it server-side, then advance.
  const confirmReviewResult = () => {
    const current = reviewQueue[0]
    if (current) {
      void import('./services/api').then(({ ackReviewResult }) =>
        ackReviewResult(current.id).catch(() => {}),
      )
      if (current.review_status === 'approved') {
        void useCreditsStore.getState().refresh()
      }
    }
    setReviewQueue((q) => q.slice(1))
  }

  useEffect(() => {
    const nextScale = (0.92 + fontScale * 0.0016).toFixed(3)
    document.documentElement.style.setProperty('--app-font-scale', nextScale)
  }, [fontScale])

  return (
    <AuthGuard>
      <ToastContainer />
      <AuthModal />
      <UpdatePrompt />
      <DailyCheckinDialog open={checkinOpen} coins={checkinCoins} onClose={() => setCheckinOpen(false)} />
      <ReviewResultDialog item={reviewQueue[0] ?? null} onConfirm={confirmReviewResult} />
      <PublishIncentiveDialog
        open={incentiveOpen && reviewQueue.length === 0}
        onClose={() => setIncentiveOpen(false)}
      />
      <Routes>
        <Route path="/" element={<Navigate to="/character" replace />} />
        <Route path="/splash" element={<SplashPage />} />
        <Route path="/login" element={<LegacyLoginRedirect />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/redeem" element={<RedeemPage />} />
        <Route path="/home" element={<Navigate to="/character" replace />} />
        <Route path="/create" element={<CreateHubPage />} />
        <Route path="/chat" element={<ChatInboxPage />} />
        <Route path="/chat/:characterId" element={<ChatConversationRouter />} />
        <Route path="/call/:characterId" element={<VoiceCallRouter />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/explore/:scenarioId" element={<ScenarioDetailPage />} />
        <Route path="/story/:runId" element={<StoryPlayerPage />} />
        <Route path="/rewards" element={<RewardsPage />} />
        <Route path="/character" element={<CharacterPage />} />
        <Route path="/character/:id" element={<CharacterProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/profile" element={<ProfileEditPage />} />
        <Route path="/settings/change-password" element={<ChangePasswordPage />} />
        <Route path="/credits/transactions" element={<TransactionsPage />} />
        <Route path="/membership" element={<MembershipPage />} />
        <Route path="/wallet" element={<WalletPage />} />
        <Route path="/invite" element={<Navigate to="/rewards" replace />} />
        <Route path="/age-gate" element={<AgeGatePage />} />
        <Route path="/legal/:type" element={<LegalPage />} />
        <Route path="/qa/states" element={<UIStatePreviewPage />} />
        <Route path="/characters/new" element={<Navigate to="/create" replace />} />
        <Route path="/characters/new/quick" element={<QuickCreatePage />} />
        <Route path="/characters/new/quick/confirm" element={<QuickConfirmPage />} />
        <Route path="/characters/new/workshop" element={<WorkshopCreatePage />} />
        <Route path="/my-characters" element={<MyCharactersPage />} />
        <Route path="/admin/review" element={<AdminReviewPage />} />
        <Route path="*" element={<NotFoundRedirect />} />
      </Routes>
    </AuthGuard>
  )
}
