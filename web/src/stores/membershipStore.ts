import { create } from 'zustand'
import type { MembershipEntitlements, VoiceCallQuota } from '../services/api'

interface MembershipState {
  tier: string
  expiresAt: string | null
  entitlements: MembershipEntitlements
  monthlyGrant: number
  voiceCall: VoiceCallQuota
  bindingCode: string
  loading: boolean
  loaded: boolean
  refresh: () => Promise<void>
  reset: () => void
}

// Free-tier fallback: universal model access but nothing complimentary.
// Cloning is Fish-only (真人克隆); MiMo clone was retired.
const FREE_ENTITLEMENTS: MembershipEntitlements = {
  models: [
    'gemini-3.1', 'deepseek-v4-flash', 'deepseek-v4-pro',
    'claude-haiku-4.5', 'claude-sonnet-4.6', 'claude-opus-4.6', 'claude-opus-5',
    'grok-4.5', 'grok-4.6', 'gpt-5.6-luna', 'gpt-5.5', 'gpt-5.6-sol',
  ],
  tts: ['mimo', 'fish'],
  clone: ['fish'],
  free: [],
}

const FREE_VOICE_CALL: VoiceCallQuota = {
  free_minutes: 0,
  used_minutes: 0,
  remaining_minutes: 0,
  minute_cost_coins: 20,
}

export const useMembershipStore = create<MembershipState>()((set) => ({
  tier: 'free',
  expiresAt: null,
  entitlements: FREE_ENTITLEMENTS,
  monthlyGrant: 0,
  voiceCall: FREE_VOICE_CALL,
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
        voiceCall: m.voice_call ?? FREE_VOICE_CALL,
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
      voiceCall: FREE_VOICE_CALL,
      bindingCode: '',
      loaded: false,
    }),
}))
