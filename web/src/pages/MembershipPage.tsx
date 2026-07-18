import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useMembershipStore } from '../stores/membershipStore'
import { getPricing, type Pricing, type MembershipTierInfo } from '../services/api'
import { AfdianBindingCard } from '../components/AfdianBindingCard'
import { Skeleton } from '../components/ui/Skeleton'

const TIER_ACCENT: Record<string, string> = {
  free: 'var(--color-text-muted)',
  plus: 'var(--color-primary)',
  immersive: 'var(--color-accent)',
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
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const membership = useMembershipStore()
  const [pricing, setPricing] = useState<Pricing | null>(null)
  const [loadError, setLoadError] = useState(false)

  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  useEffect(() => {
    membership.refresh()
    getPricing().then(setPricing).catch(() => setLoadError(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const currentTier = membership.tier
  const expiryLabel = formatExpiry(membership.expiresAt)
  const tiers = pricing?.membership_tiers ?? []

  const paidBindingTier: MembershipTierInfo | undefined = tiers.find((t) => t.tier === 'plus')

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
            const accent = TIER_ACCENT[t.tier] ?? 'var(--color-ink)'
            return (
              <div
                key={t.tier}
                className="bg-[var(--color-glass-card)] backdrop-blur-[20px] rounded-[20px] shadow-[var(--shadow-card)] p-5"
                style={{ border: isCurrent ? `2px solid ${accent}` : '1px solid var(--color-border-glass)' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[18px] font-semibold" style={{ color: accent }}>{t.label}</span>
                  {isCurrent && (
                    <span className="text-[11px] font-medium px-2 py-[2px] rounded-full text-[var(--color-text-on-primary)]" style={{ backgroundColor: accent }}>
                      当前
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-1 mb-3">
                  <span className="text-[26px] font-bold text-[var(--color-ink)]">
                    {t.price === 0 ? '免费' : `¥${t.price}`}
                  </span>
                  {t.price > 0 && <span className="text-[13px] text-[var(--color-text-muted)]">/月</span>}
                </div>
                <ul className="space-y-2 mb-2">
                  {t.benefits.map((b, i) => (
                    <li key={i} className="flex items-start gap-2 text-[14px] text-[var(--color-text-secondary)]">
                      <span className="mt-[6px] w-[5px] h-[5px] rounded-full shrink-0" style={{ backgroundColor: accent }} />
                      {b}
                    </li>
                  ))}
                </ul>
                {t.monthly_grant > 0 && (
                  <p className="text-[12px] text-[var(--color-text-muted)]">每月赠 {t.monthly_grant} yuoyuo币</p>
                )}
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
              skuHint={paidBindingTier ? `进阶版（${paidBindingTier.sku}）/ 沉浸版` : undefined}
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
