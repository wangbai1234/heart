import { create } from 'zustand'

interface AuthPromptState {
  open: boolean
  returnTo: string
  show: (returnTo?: string) => void
  close: () => void
}

export const useAuthPromptStore = create<AuthPromptState>((set) => ({
  open: false,
  returnTo: '/character',
  show: (returnTo = '/character') => set({ open: true, returnTo }),
  close: () => set({ open: false }),
}))
