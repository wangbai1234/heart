import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface FavoritesState {
  favorites: Set<string> // character IDs
  toggle: (characterId: string) => void
  has: (characterId: string) => boolean
}

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      favorites: new Set(),
      toggle: (id) => {
        set((s) => {
          const next = new Set(s.favorites)
          if (next.has(id)) next.delete(id)
          else next.add(id)
          return { favorites: next }
        })
      },
      has: (id) => get().favorites.has(id),
    }),
    {
      name: 'yuoyuo-favorites',
      storage: {
        getItem: (key) => {
          try {
            const raw = localStorage.getItem(key)
            if (!raw) return null
            const parsed = JSON.parse(raw)
            return { ...parsed, state: { ...parsed.state, favorites: new Set(parsed.state.favorites) } }
          } catch {
            return null
          }
        },
        setItem: (key, value) => {
          try {
            const serialized = { ...value, state: { ...value.state, favorites: Array.from(value.state.favorites) } }
            localStorage.setItem(key, JSON.stringify(serialized))
          } catch { /* ignore */ }
        },
        removeItem: (key) => {
          try { localStorage.removeItem(key) } catch { /* ignore */ }
        },
      },
    },
  ),
)
