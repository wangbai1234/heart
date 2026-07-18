import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useCreditsStore } from '../stores/creditsStore'
import { useMembershipStore } from '../stores/membershipStore'
import { getPricing, type Pricing, type ShopItem } from '../services/api'
import { AfdianBindingCard } from '../components/AfdianBindingCard'
import { Skeleton } from '../components/ui/Skeleton'

export function WalletPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const { balance, refresh: refreshBalance } = useCreditsStore()
  const membership = useMembershipStore()
  const [pricing, setPricing] = useState<Pricing | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [selected, setSelected] = useState<ShopItem | null>(null)

  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  useEffect(() => {
    refreshBalance()
    if (!membership.loaded) membership.refresh()
    getPricing().then(setPricing).catch(() => setLoadError(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const shop = pricing?.shop ?? []

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      <img src={bgImage} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      <div style={{ height: 'var(--safe-top)' }} />

      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button onClick={() => navigate(-1)} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-medium text-[var(--color-ink)]">yuoyuo币钱包</span>
        <div className="w-[44px]" />
      </nav>

      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-8">
        {/* Balance card */}
        <div className="rounded-[20px] bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-accent)] p-5 mt-4 mb-5 shadow-[var(--shadow-card)]">
          <p className="text-[13px] text-white/70">当前余额</p>
          <p className="text-[36px] font-bold text-white mt-1 leading-none">{balance}</p>
          <div className="flex items-center gap-4 mt-4">
            <button onClick={() => navigate('/credits/transactions')} className="text-[13px] text-white/90 underline-offset-2 active:opacity-70">
              账单明细
            </button>
            <button onClick={() => navigate('/redeem')} className="text-[13px] text-white/90 underline-offset-2 active:opacity-70">
              兑换码充值
            </button>
          </div>
        </div>

        {/* Shop */}
        <p className="text-[13px] font-medium text-[var(--color-ink)] mb-3">充值挡位</p>

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
                className="text-left rounded-[16px] p-4 bg-[var(--color-glass-card)] backdrop-blur-[16px] active:scale-[0.98] transition-transform"
                style={{ border: isSel ? '2px solid var(--color-primary)' : '1px solid var(--color-border-glass)' }}
              >
                <p className="text-[13px] text-[var(--color-text-secondary)]">{item.label}</p>
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
              skuHint={selected ? `${selected.label}（${selected.sku}）` : '选择上方挡位后在备注注明'}
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
