import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthGuard } from './components/AuthGuard'
import { SplashPage } from './pages/SplashPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { LoginPage } from './pages/LoginPage'
import { HomePage } from './pages/HomePage'
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
import { useThemeStore } from './stores/themeStore'
import { useAppStore } from './stores/appStore'

function ChatRouter() {
  const { resolvedTheme } = useThemeStore()
  return resolvedTheme === 'dark' ? <ChatDarkPage /> : <ChatLightPage />
}

export function App() {
  const { fontScale } = useAppStore()

  useEffect(() => {
    const nextScale = (0.92 + fontScale * 0.0016).toFixed(3)
    document.documentElement.style.setProperty('--app-font-scale', nextScale)
  }, [fontScale])

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
        <Route path="/character-backstage" element={<CharacterBackstagePage />} />
        <Route path="/character" element={<CharacterPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/profile" element={<ProfileEditPage />} />
        <Route path="/credits/transactions" element={<TransactionsPage />} />
        <Route path="/age-gate" element={<AgeGatePage />} />
        <Route path="/legal/:type" element={<LegalPage />} />
        <Route path="/qa/states" element={<UIStatePreviewPage />} />
        <Route path="*" element={<Navigate to="/splash" replace />} />
      </Routes>
    </AuthGuard>
  )
}
