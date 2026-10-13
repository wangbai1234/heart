import { create } from 'zustand'
import { applyAccountLocale, accountLocaleRevision, invalidateAccountLocaleRequests, restoreDeviceLocale } from '../i18n'
import { getLanguagePreferences, saveLanguagePreferences, type LanguagePreferences } from '../services/api'
import { useAuthStore } from './authStore'

interface LanguageState {
  preferences: LanguagePreferences | null
  busy: boolean
  load: () => Promise<void>
  save: (patch: Partial<LanguagePreferences>) => Promise<void>
}
let generation = 0
let pending: Promise<void> | undefined
export const useLanguageStore = create<LanguageState>((set, get) => ({
  preferences: null,
  busy: false,
  load: () => {
    if (pending) return pending
    if (get().preferences || !useAuthStore.getState().user) return Promise.resolve()
    const epoch = generation, revision = accountLocaleRevision()
    const user = useAuthStore.getState().user?.id
    set({ busy: true })
    const request = (async () => {
      try {
        const preferences = await getLanguagePreferences()
        if (generation !== epoch || useAuthStore.getState().user?.id !== user) return
        set({ preferences })
        await applyAccountLocale(preferences.interface_language, revision)
      } finally {
        if (generation === epoch) { pending = undefined; set({ busy: false }) }
      }
    })()
    pending = request
    return request
  },
  save: async patch => {
    // One shared lock protects every control. Merge patches into the latest
    // saved snapshot, so changing the header cannot overwrite reply settings.
    if (get().busy || !useAuthStore.getState().user) return
    const epoch = generation, user = useAuthStore.getState().user?.id
    if (!get().preferences) await get().load()
    if (generation !== epoch || useAuthStore.getState().user?.id !== user) return
    const preferences = get().preferences
    if (!preferences || get().busy) return
    invalidateAccountLocaleRequests()
    const revision = accountLocaleRevision()
    set({ busy: true })
    try {
      const saved = await saveLanguagePreferences({ ...preferences, ...patch })
      if (generation !== epoch || useAuthStore.getState().user?.id !== user) return
      set({ preferences: saved })
      await applyAccountLocale(saved.interface_language, revision)
    } finally { if (generation === epoch) set({ busy: false }) }
  },
}))

useAuthStore.subscribe((state, previous) => {
  if (state.user?.id === previous.user?.id) return
  generation++
  pending = undefined
  invalidateAccountLocaleRequests()
  useLanguageStore.setState({ preferences: null, busy: false })
  void restoreDeviceLocale()
})
