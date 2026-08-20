import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Free-text id; the valid set is the server catalog (UGC refactor C4).
type CharacterId = string

interface AppState {
  isFirstLaunch: boolean
  currentCharacterId: CharacterId
  userAvatar: string | null
  hasSeenOnboarding: boolean
  fontScale: number
  muteStart: string
  muteStartMin: string
  muteEnd: string
  muteEndMin: string
  isMuteNever: boolean
  voiceChatEnabled: Record<CharacterId, boolean>
  chatModel: Record<CharacterId, string>
  pushEnabled: boolean
  inboxUnreadTotal: number

  setFirstLaunch: (v: boolean) => void
  setCharacter: (id: CharacterId) => void
  setUserAvatar: (url: string | null) => void
  setHasSeenOnboarding: (v: boolean) => void
  setFontScale: (v: number) => void
  setMuteTime: (start: string, startMin: string, end: string, endMin: string) => void
  setMuteNever: (v: boolean) => void
  setVoiceChatEnabled: (id: CharacterId, enabled: boolean) => void
  setChatModel: (id: CharacterId, model: string) => void
  mergeChatModels: (models: Record<CharacterId, string>) => void
  setPushEnabled: (v: boolean) => void
  setInboxUnreadTotal: (n: number) => void
  // Reset per-user fields on logout / account switch so the next account on
  // this browser never inherits the previous user's avatar, selected character,
  // per-character prefs or unread badge. Device-scoped prefs (fontScale, mute
  // window, pushEnabled) are intentionally preserved — they belong to the
  // device, not the account.
  resetUserState: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      isFirstLaunch: true,
      currentCharacterId: 'rin',
      userAvatar: null,
      hasSeenOnboarding: false,
      fontScale: 50,
      muteStart: '22',
      muteStartMin: '00',
      muteEnd: '08',
      muteEndMin: '00',
      isMuteNever: false,
      voiceChatEnabled: {
        rin: false,
        dorothy: false,
      },
      chatModel: {},
      pushEnabled: false,
      inboxUnreadTotal: 0,

      setFirstLaunch: (v) => set({ isFirstLaunch: v }),
      setCharacter: (id) => set({ currentCharacterId: id }),
      setUserAvatar: (url) => set({ userAvatar: url }),
      setHasSeenOnboarding: (v) => set({ hasSeenOnboarding: v }),
      setFontScale: (v) => set({ fontScale: v }),
      setMuteTime: (start, startMin, end, endMin) => set({
        muteStart: start,
        muteStartMin: startMin,
        muteEnd: end,
        muteEndMin: endMin,
        isMuteNever: false,
      }),
      setMuteNever: (v) => set({ isMuteNever: v }),
      setVoiceChatEnabled: (id, enabled) =>
        set((state) => ({
          voiceChatEnabled: {
            ...state.voiceChatEnabled,
            [id]: enabled,
          },
        })),
      setChatModel: (id, model) =>
        set((state) => ({
          chatModel: {
            ...state.chatModel,
            [id]: model,
          },
        })),
      mergeChatModels: (models) =>
        set((state) => ({ chatModel: { ...state.chatModel, ...models } })),
      setPushEnabled: (v) => set({ pushEnabled: v }),
      setInboxUnreadTotal: (n) => set({ inboxUnreadTotal: n }),
      resetUserState: () =>
        set({
          currentCharacterId: 'rin',
          userAvatar: null,
          voiceChatEnabled: { rin: false, dorothy: false },
          chatModel: {},
          inboxUnreadTotal: 0,
        }),
    }),
    {
      name: 'yuoyuo-app',
      version: 3,
      migrate: (persisted: unknown, version: number) => {
        const state = persisted as Record<string, unknown>
        if (version < 2) {
          // Migrate taolesi → dorothy
          if (state.currentCharacterId === 'taolesi') {
            state.currentCharacterId = 'dorothy'
          }
          const vce = state.voiceChatEnabled as Record<string, boolean> | undefined
          if (vce && 'taolesi' in vce) {
            vce.dorothy = vce.taolesi
            delete vce.taolesi
          }
        }
        if (version < 3) {
          const models = (state.chatModel ?? {}) as Record<string, string>
          for (const [characterId, model] of Object.entries(models)) {
            if (model === 'deepseek' || model === 'deepseek-chat') {
              models[characterId] = 'deepseek-v4-flash'
            } else if (model === 'deepseek-reasoner') {
              models[characterId] = 'deepseek-v4-pro'
            } else if (model === 'grok') {
              models[characterId] = 'grok-4.5'
            }
          }
        }
        return state
      },
    },
  ),
)
