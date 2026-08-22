import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreditsStore } from '../stores/creditsStore'
import { useMembershipStore } from '../stores/membershipStore'
import { getPricing, type Pricing, type ShopItem } from '../services/api'
import { AfdianBindingCard } from '../components/AfdianBindingCard'
import { Skeleton } from '../components/ui/Skeleton'
import { useSafeBack } from '../hooks/useSafeBack'

export function WalletPage() {
  const navigate = useNavigate()
  const goBack = useSafeBack('/settings')
  const { balance, refresh: refreshBalance } = useCreditsStore()
  const membership = useMembershipStore()
  const [pricing, setPricing] = useState<Pricing | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [selected, setSelected] = useState<ShopItem | null>(null)

  useEffect(() => {
    refreshBalance()
    if (!membership.loaded) membership.refresh()
    getPricing().then(setPricing).catch(() => setLoadError(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const shop = pricing?.shop ?? []

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
          <p className="mt-3 text-[12px] text-white/70">签到币与购买币均永久有效</p>
        </div>

        {/* Shop */}
        <div className="mb-3 flex items-end justify-between px-1">
          <p className="text-[15px] font-semibold text-[var(--color-ink)]">充值挡位</p>
          <span className="text-[11px] text-[var(--color-text-muted)]">选择一个适合你的额度</span>
        </div>

        {loadError && (
          <div className="text-center py-8">
            <p className="text-[var(--color-text-muted)] text-[14px]">充值挡位加载失败</p>
            <button onClick={() => { setLoadError(false); getPricing().then(setPricing).catch(() => setLoadError(true)) }} className="mt-3 text-[13px] text-[var(--color-primary)] active:opacity-60">重试</button>
          </div>
        )}

        {!pricing && !loadError && (
          <div className="grid grid-cols-2 gap-3">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} height={104} className="rounded-[16px]" />)}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {shop.map((item) => {
            const isSel = selected?.sku === item.sku
            return (
              <button
                key={item.sku}
                onClick={() => setSelected(item)}
                className="relative overflow-hidden rounded-[14px] bg-[var(--color-page-surface)] p-4 text-left shadow-[0_5px_16px_rgba(73,48,62,0.08)] transition-transform active:scale-[0.98]"
                style={{ border: isSel ? '2px solid var(--color-primary)' : '1px solid var(--color-border-glass)' }}
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-[13px] font-medium text-[var(--color-text-secondary)]">{item.label}</p>
                  <span className="h-[7px] w-[7px] rounded-full bg-[var(--color-primary-400)]" />
                </div>
                <p className="text-[22px] font-bold text-[var(--color-ink)] mt-1 leading-none">
                  {item.credits}
                  <span className="text-[12px] font-normal text-[var(--color-text-muted)] ml-1">yuoyuo币</span>
                </p>
                {item.bonus > 0 && (
                  <p className="text-[11px] text-[var(--color-primary)] mt-1">含赠送 {item.bonus}</p>
                )}
                <p className="text-[15px] font-semibold text-[var(--color-cta-text)] mt-2">¥{item.price}</p>
              </button>
            )
          })}
        </div>

        {/* Purchase / binding-code section */}
        {pricing && (
          <div className="mt-6">
            <p className="text-[13px] font-medium text-[var(--color-ink)] mb-2">去爱发电充值</p>
            <AfdianBindingCard
              bindingCode={membership.bindingCode}
              afdianUrl={pricing.afdian_url}
              checkoutUrl={selected?.checkout_url}
              skuHint={selected ? `${selected.label}（${selected.sku}）` : '请先选择上方挡位'}
              forceAutoBindCopy
            />
            <p className="text-center text-[12px] text-[var(--color-text-muted)] mt-3">
              付款后系统自动到账，通常几分钟内到账。
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
