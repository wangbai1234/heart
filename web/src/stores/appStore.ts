import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type CharacterId = 'rin' | 'taolesi'

interface AppState {
  isAuthenticated: boolean
  isFirstLaunch: boolean
  currentCharacterId: CharacterId
  userAvatar: string | null
  hasSeenOnboarding: boolean

  setAuthenticated: (v: boolean) => void
  setFirstLaunch: (v: boolean) => void
  setCharacter: (id: CharacterId) => void
  setUserAvatar: (url: string | null) => void
  setHasSeenOnboarding: (v: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      isFirstLaunch: true,
      currentCharacterId: 'rin',
      userAvatar: null,
      hasSeenOnboarding: false,

      setAuthenticated: (v) => set({ isAuthenticated: v }),
      setFirstLaunch: (v) => set({ isFirstLaunch: v }),
      setCharacter: (id) => set({ currentCharacterId: id }),
      setUserAvatar: (url) => set({ userAvatar: url }),
      setHasSeenOnboarding: (v) => set({ hasSeenOnboarding: v }),
    }),
    { name: 'yuoyuo-app' },
  ),
)
