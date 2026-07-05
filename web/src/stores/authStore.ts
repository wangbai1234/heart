import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser } from '../services/api'

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

      setSession: ({ accessToken, refreshToken, user }) =>
        set({ accessToken, refreshToken, user }),

      clearSession: () =>
        set({ accessToken: null, refreshToken: null, user: null }),

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
