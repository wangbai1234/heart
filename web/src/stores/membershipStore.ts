import { create } from 'zustand'
import type { MembershipEntitlements } from '../services/api'

interface MembershipState {
  tier: string
  expiresAt: string | null
  entitlements: MembershipEntitlements
  monthlyGrant: number
  bindingCode: string
  loading: boolean
  loaded: boolean
  refresh: () => Promise<void>
  reset: () => void
}

// Free-tier fallback: universal access (deepseek/grok/tts/clone) but nothing complimentary.
const FREE_ENTITLEMENTS: MembershipEntitlements = {
  models: ['deepseek', 'grok'],
  tts: ['mimo', 'fish'],
  clone: ['mimo', 'fish'],
  free: [],
}

export const useMembershipStore = create<MembershipState>()((set) => ({
  tier: 'free',
  expiresAt: null,
  entitlements: FREE_ENTITLEMENTS,
  monthlyGrant: 0,
  bindingCode: '',
  loading: false,
  loaded: false,
  refresh: async () => {
    set({ loading: true })
    try {
      const { getMembership } = await import('../services/api')
      const m = await getMembership()
      set({
        tier: m.tier,
        expiresAt: m.expires_at,
        entitlements: m.entitlements,
        monthlyGrant: m.monthly_grant,
        bindingCode: m.binding_code,
        loaded: true,
      })
    } catch {
      // Silently fall back to free — membership is a soft, lazily-resolved value.
    } finally {
      set({ loading: false })
    }
  },
  reset: () =>
    set({
      tier: 'free',
      expiresAt: null,
      entitlements: FREE_ENTITLEMENTS,
      monthlyGrant: 0,
      bindingCode: '',
      loaded: false,
    }),
}))
