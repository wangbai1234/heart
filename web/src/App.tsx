import { useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
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

function ChatConversationRouter() {
  const { resolvedTheme } = useThemeStore()
  return resolvedTheme === 'dark' ? <ChatDarkPage /> : <ChatLightPage />
}

const SKIP_SAVE_ROUTES = new Set(['/splash', '/onboarding', '/login', '/redeem', '/age-gate', '/'])

export function App() {
  const { fontScale } = useAppStore()
  const accessToken = useAuthStore((s) => s.accessToken)
  const loadCharacters = useCharactersStore((s) => s.load)
  const navigate = useNavigate()
  const location = useLocation()

  // Wire module-level navigate so api.ts / useWebSocket.ts can redirect
  // without a hard page reload (preserves React state and bfcache).
  useEffect(() => {
    setNavigate(navigate)
  }, [navigate])

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
        <Route path="/age-gate" element={<AgeGatePage />} />
        <Route path="/legal/:type" element={<LegalPage />} />
        <Route path="/qa/states" element={<UIStatePreviewPage />} />
        <Route path="/characters/new" element={<CreateCharacterPage />} />
        <Route path="/my-characters" element={<MyCharactersPage />} />
        <Route path="*" element={<Navigate to="/splash" replace />} />
      </Routes>
    </AuthGuard>
  )
}
