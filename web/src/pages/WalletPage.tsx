import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreditsStore } from '../stores/creditsStore'
import { useMembershipStore } from '../stores/membershipStore'
import { useSafeBack } from '../hooks/useSafeBack'

export function WalletPage() {
  const navigate = useNavigate()
  const goBack = useSafeBack('/settings')
  const { balance, refresh: refreshBalance } = useCreditsStore()
  const membership = useMembershipStore()

  useEffect(() => {
    refreshBalance()
    if (!membership.loaded) membership.refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="app-atmosphere relative flex h-full w-full flex-col overflow-hidden">
      <div style={{ height: 'var(--safe-top)' }} />

      <nav className="relative z-20 flex h-[52px] shrink-0 items-center justify-between border-b border-white/40 px-5">
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-semibold text-[var(--color-ink)]">yuoyuo币钱包</span>
        <div className="w-[44px]" />
      </nav>

      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-8">
        {/* Balance card */}
        <div className="relative mt-4 mb-5 overflow-hidden rounded-[18px] border border-white/30 bg-[linear-gradient(135deg,#FF9FB3_0%,#FF7898_58%,#A7C7E7_100%)] p-5 shadow-[0_12px_30px_rgba(232,85,119,0.22)]">
          <div className="pointer-events-none absolute inset-y-0 right-0 w-[44%] bg-[linear-gradient(110deg,transparent,rgba(255,255,255,0.16))]" />
          <p className="text-[13px] text-white/70">当前余额</p>
          <p className="text-[36px] font-bold text-white mt-1 leading-none">{balance}</p>
          <div className="mt-4">
            <button onClick={() => navigate('/credits/transactions')} className="text-[13px] text-white/90 underline-offset-2 active:opacity-70">
              账单明细
            </button>
          </div>
          <p className="mt-3 text-[12px] text-white/70">签到和活动获得的 yuoyuo币均永久有效</p>
        </div>

        <div className="mt-5 rounded-[18px] border border-[var(--color-border-glass)] bg-[var(--color-glass-55)] p-4">
          <p className="text-[15px] font-semibold text-[var(--color-ink)]">免费额度</p>
          <p className="mt-2 text-[13px] leading-[1.7] text-[var(--color-text-secondary)]">
            当前不提供购买服务。你可以通过每日签到、邀请和活动获得 yuoyuo币；已有余额仍可正常使用。
          </p>
          <button
            onClick={() => navigate('/rewards')}
            className="mt-3 text-[13px] font-medium text-[var(--color-primary)] active:opacity-60"
          >
            查看可领取的奖励 →
          </button>
        </div>
      </div>
    </div>
  )
}
