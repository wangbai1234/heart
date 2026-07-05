import { create } from 'zustand'

interface CreditsState {
  balance: number
  loading: boolean
  refresh: () => Promise<void>
  setBalance: (n: number) => void
}

export const useCreditsStore = create<CreditsState>()((set) => ({
  balance: 0,
  loading: false,

  refresh: async () => {
    set({ loading: true })
    try {
      const { getBalance } = await import('../services/api')
      const data = await getBalance()
      set({ balance: data.balance })
    } catch {
      // silently fail — balance will show 0
    } finally {
      set({ loading: false })
    }
  },

  setBalance: (n) => set({ balance: n }),
}))
