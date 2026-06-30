import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthGuard } from './components/AuthGuard'
import { SplashPage } from './pages/SplashPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { LoginPage } from './pages/LoginPage'
import { HomePage } from './pages/HomePage'
import { ChatLightPage } from './pages/ChatLightPage'
import { ChatDarkPage } from './pages/ChatDarkPage'
import { CharacterPage } from './pages/CharacterPage'
import { SettingsPage } from './pages/SettingsPage'
import { RedeemPage } from './pages/RedeemPage'
import { UIStatePreviewPage } from './pages/UIStatePreviewPage'
import { useThemeStore } from './stores/themeStore'

function ChatRouter() {
  const { resolvedTheme } = useThemeStore()
  return resolvedTheme === 'dark' ? <ChatDarkPage /> : <ChatLightPage />
}

export function App() {
  return (
    <AuthGuard>
      <Routes>
        <Route path="/" element={<Navigate to="/splash" replace />} />
        <Route path="/splash" element={<SplashPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/redeem" element={<RedeemPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/chat" element={<ChatRouter />} />
        <Route path="/character" element={<CharacterPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/qa/states" element={<UIStatePreviewPage />} />
        <Route path="*" element={<Navigate to="/splash" replace />} />
      </Routes>
    </AuthGuard>
  )
}
