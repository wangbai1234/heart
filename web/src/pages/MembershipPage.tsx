import { useEffect, useState } from 'react'
import { useThemeStore } from '../stores/themeStore'
import { useMembershipStore } from '../stores/membershipStore'
import { getPricing, type Pricing, type MembershipTierInfo } from '../services/api'
import { AfdianBindingCard } from '../components/AfdianBindingCard'
import { Skeleton } from '../components/ui/Skeleton'
import { useSafeBack } from '../hooks/useSafeBack'

const TIER_ACCENT: Record<string, string> = {
  free: 'var(--color-text-muted)',
  plus: 'var(--color-primary)',
  immersive: 'var(--color-accent)',
}

const SKU_LABELS: Record<string, string> = {
  plan_plus: '进阶版',
  plan_immersive: '沉浸版',
}

function formatExpiry(iso: string | null): string | null {
  if (!iso) return null
  try {
    const d = new Date(iso)
    return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日到期`
  } catch {
    return null
  }
}

export function MembershipPage() {
  const goBack = useSafeBack('/settings')
  const { resolvedTheme } = useThemeStore()
  const membership = useMembershipStore()
  const [pricing, setPricing] = useState<Pricing | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [selectedTier, setSelectedTier] = useState<string>('plus')

  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.webp'
    : '/assets/backgrounds/聊天背景图.webp'

  useEffect(() => {
    membership.refresh()
    getPricing().then(setPricing).catch(() => setLoadError(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const currentTier = membership.tier
  const expiryLabel = formatExpiry(membership.expiresAt)
  const tiers = pricing?.membership_tiers ?? []

  const paidBindingTier: MembershipTierInfo | undefined =
    tiers.find((t) => t.tier === selectedTier && t.tier !== 'free') ??
    tiers.find((t) => t.tier === 'plus')

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      <img src={bgImage} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      <div style={{ height: 'var(--safe-top)' }} />

      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-medium text-[var(--color-ink)]">会员中心</span>
        <div className="w-[44px]" />
      </nav>

      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-8">
        {/* Current status */}
        <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[20px] border border-[var(--color-border-glass)] shadow-[var(--shadow-card)] p-4 mt-4 mb-5">
          <p className="text-[13px] text-[var(--color-text-secondary)]">当前等级</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span
              className="text-[22px] font-bold"
              style={{ color: TIER_ACCENT[currentTier] ?? 'var(--color-ink)' }}
            >
              {tiers.find((t) => t.tier === currentTier)?.label ?? '体验版'}
            </span>
            {expiryLabel && (
              <span className="text-[13px] text-[var(--color-text-muted)]">{expiryLabel}</span>
            )}
          </div>
        </div>

        {/* Voice-call monthly quota */}
        <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[20px] border border-[var(--color-border-glass)] shadow-[var(--shadow-card)] p-4 mb-5">
          <div className="flex items-center justify-between">
            <p className="text-[13px] text-[var(--color-text-secondary)]">本月语音通话</p>
            <span className="text-[12px] text-[var(--color-text-muted)]">
              超出后 {membership.voiceCall.minute_cost_coins} 币/分钟
            </span>
          </div>
          {membership.voiceCall.free_minutes > 0 ? (
            <>
              <div className="flex items-baseline gap-2 mt-1.5">
                <span className="text-[22px] font-bold text-[var(--color-ink)]">
                  剩余 {membership.voiceCall.remaining_minutes} 分钟
                </span>
                <span className="text-[13px] text-[var(--color-text-muted)]">
                  免费 {membership.voiceCall.free_minutes} 分钟 / 月
                </span>
              </div>
              <div className="mt-3 h-[6px] rounded-full bg-[var(--color-border-glass)] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(100, (membership.voiceCall.remaining_minutes / membership.voiceCall.free_minutes) * 100)}%`,
                    backgroundColor: TIER_ACCENT[currentTier] ?? 'var(--color-primary)',
                  }}
                />
              </div>
            </>
          ) : (
            <p className="text-[14px] text-[var(--color-text-secondary)] mt-1.5">
              按 {membership.voiceCall.minute_cost_coins} 币/分钟计费，升级会员可获得每月免费时长
            </p>
          )}
        </div>

        {loadError && (
          <div className="text-center py-8">
            <p className="text-[var(--color-text-muted)] text-[14px]">定价加载失败</p>
            <button onClick={() => { setLoadError(false); getPricing().then(setPricing).catch(() => setLoadError(true)) }} className="mt-3 text-[13px] text-[var(--color-primary)] active:opacity-60">重试</button>
          </div>
        )}

        {!pricing && !loadError && (
          <div className="space-y-4">
            {[0, 1, 2].map((i) => <Skeleton key={i} height={160} className="rounded-[20px]" />)}
          </div>
        )}

        {/* Tier cards */}
        <div className="space-y-4">
          {tiers.map((t) => {
            const isCurrent = t.tier === currentTier
            const isPaid = t.tier !== 'free'
            const isSelected = isPaid && t.tier === selectedTier
            const accent = TIER_ACCENT[t.tier] ?? 'var(--color-ink)'
            return (
              <div
                key={t.tier}
                onClick={isPaid ? () => setSelectedTier(t.tier) : undefined}
                role={isPaid ? 'button' : undefined}
                className={`bg-[var(--color-glass-card)] backdrop-blur-[20px] rounded-[20px] shadow-[var(--shadow-card)] p-5${isPaid ? ' cursor-pointer active:scale-[0.99] transition-transform' : ''}`}
                style={{ border: isSelected ? `2px solid ${accent}` : '1px solid var(--color-border-glass)' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[18px] font-semibold" style={{ color: accent }}>{t.label}</span>
                  {isCurrent ? (
                    <span className="text-[11px] font-medium px-2 py-[2px] rounded-full text-[var(--color-text-on-primary)]" style={{ backgroundColor: accent }}>
                      当前
                    </span>
                  ) : isSelected ? (
                    <span className="text-[11px] font-medium px-2 py-[2px] rounded-full text-[var(--color-text-on-primary)]" style={{ backgroundColor: accent }}>
                      已选
                    </span>
                  ) : null}
                </div>
                <div className="flex items-baseline gap-1 mb-3">
                  <span className="text-[26px] font-bold text-[var(--color-ink)]">
                    {t.price === 0 ? '免费' : `¥${t.price}`}
                  </span>
                  {t.price > 0 && <span className="text-[13px] text-[var(--color-text-muted)]">/月</span>}
                </div>
                <ul className="space-y-2 mb-2">
                {[
                  ...t.benefits,
                  ...(t.tier === 'free' ? ['每日签到20币，永久有效'] : []),
                  ...(t.tier === 'plus' ? ['每日签到80币，永久有效'] : []),
                  ...(t.tier === 'immersive' ? ['每日签到80币，永久有效', '全部文字模型无限次'] : []),
                ].filter((benefit, index, all) => all.indexOf(benefit) === index).map((b, i) => (
                    <li key={i} className="flex items-start gap-2 text-[14px] text-[var(--color-text-secondary)]">
                      <span className="mt-[6px] w-[5px] h-[5px] rounded-full shrink-0" style={{ backgroundColor: accent }} />
                      {b}
                    </li>
                  ))}
                </ul>
                {t.sku && (
                  <p className="mt-2 text-[12px] text-[var(--color-text-muted)]">
                    爱发电挡位：<span className="text-[var(--color-text-secondary)]">{t.label}（{t.sku}）</span>
                  </p>
                )}
              </div>
            )
          })}
        </div>

        {/* Purchase / binding-code section */}
        {pricing && (
          <div className="mt-6">
            <p className="text-[13px] font-medium text-[var(--color-ink)] mb-2">开通 / 续费</p>
            <AfdianBindingCard
              bindingCode={membership.bindingCode}
              afdianUrl={pricing.afdian_url}
              checkoutUrl={paidBindingTier?.checkout_url}
              skuHint={paidBindingTier?.sku ? SKU_LABELS[paidBindingTier.sku] ?? paidBindingTier.sku : undefined}
            />
            <p className="text-center text-[12px] text-[var(--color-text-muted)] mt-3">
              付款后系统自动开通，通常几分钟内到账。
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
