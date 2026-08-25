import { create } from 'zustand'
import {
  activateRewardCoupon,
  drawLottery,
  getCommissionBalance,
  getInviteStatus,
  getLotteryStatus,
  getRewardCoupons,
  spendCommission,
  type CommissionBalance,
  type InviteStatus,
  type LotteryDrawResult,
  type LotteryStatus,
  type MembershipRewardCoupon,
} from '../services/api'

interface RewardsState {
  invite: InviteStatus | null
  lottery: LotteryStatus | null
  coupons: MembershipRewardCoupon[]
  commission: CommissionBalance | null
  loading: boolean
  error: boolean
  refresh: () => Promise<void>
  draw: () => Promise<LotteryDrawResult>
  activateCoupon: (id: number) => Promise<void>
  spend: (target: 'membership' | 'coins', sku: string) => Promise<void>
}

export const useRewardsStore = create<RewardsState>((set, get) => ({
  invite: null,
  lottery: null,
  coupons: [],
  commission: null,
  loading: false,
  error: false,

  refresh: async () => {
    set({ loading: true, error: false })
    try {
      const [invite, lottery, couponResult, commission] = await Promise.all([
        getInviteStatus(),
        getLotteryStatus(),
        getRewardCoupons(),
        getCommissionBalance(),
      ])
      set({ invite, lottery, coupons: couponResult.coupons, commission })
    } catch {
      set({ error: true })
    } finally {
      set({ loading: false })
    }
  },

  draw: async () => {
    const chance = get().lottery?.chances[0]
    if (!chance) throw new Error('no_chance')
    const result = await drawLottery(chance.id)
    await get().refresh()
    return result
  },

  activateCoupon: async (id) => {
    await activateRewardCoupon(id)
    await get().refresh()
  },

  spend: async (target, sku) => {
    await spendCommission(target, sku, crypto.randomUUID())
    await get().refresh()
  },
}))
