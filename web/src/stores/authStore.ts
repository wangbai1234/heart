import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser } from '../services/api'
import { useChatStore } from './chatStore'
import { useAppStore } from './appStore'

// Purge every per-user store (in-memory + its persisted localStorage key, which
// the persist middleware rewrites from the reset in-memory state) so no account
// on this browser can rehydrate a previous account's chat history, openings or
// avatar. Called on logout and whenever a different user logs in. Neither store
// imports authStore, so these static imports form no cycle.
function purgeUserScopedStores() {
  useChatStore.getState().resetUserState()
  useAppStore.getState().resetUserState()
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
  acceptedLegalVersion: string | null

  isAuthenticated: () => boolean
  setSession: (params: { accessToken: string; refreshToken: string; user: AuthUser }) => void
  clearSession: () => void
  setUser: (patch: Partial<AuthUser>) => void
  acceptLegalVersion: (version: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      acceptedLegalVersion: null,

      isAuthenticated: () => !!get().accessToken,

      setSession: ({ accessToken, refreshToken, user }) => {
        // Detect an account switch on the same browser: if a *different* user id
        // is signing in over a still-hydrated session (or a token refresh that
        // somehow carries a new id), purge the previous user's scoped stores
        // before adopting the new session. Same-id refreshes never purge.
        const prev = get().user
        if (prev && prev.id !== user.id) {
          purgeUserScopedStores()
        }
        set({ accessToken, refreshToken, user })
      },

      clearSession: () => {
        purgeUserScopedStores()
        set({ accessToken: null, refreshToken: null, user: null })
      },

      setUser: (patch) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...patch } : null,
        })),

      acceptLegalVersion: (version) =>
        set({ acceptedLegalVersion: version }),
    }),
    {
      name: 'yuoyuo-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        acceptedLegalVersion: state.acceptedLegalVersion,
      }),
    },
  ),
)
