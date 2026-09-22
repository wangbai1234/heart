import { useEffect } from 'react'
import { useMembershipStore } from '../stores/membershipStore'
import { useSafeBack } from '../hooks/useSafeBack'

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
  const goBack = useSafeBack('/settings')
  const membership = useMembershipStore()

  useEffect(() => {
    membership.refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const currentTier = membership.tier
  const expiryLabel = formatExpiry(membership.expiresAt)

  return (
    <div className="app-atmosphere relative flex h-full w-full flex-col overflow-hidden">
      <div style={{ height: 'var(--safe-top)' }} />

      <nav className="relative z-20 flex h-[44px] shrink-0 items-center justify-between px-5">
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
              {currentTier === 'immersive' ? '沉浸版' : currentTier === 'plus' ? '进阶版' : '体验版'}
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
              当前账户
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
              当前没有可用的免费通话时长；后续将逐步开放免费调用。
            </p>
          )}
        </div>

        <div className="rounded-[18px] border border-[var(--color-border-glass)] bg-[var(--color-glass-55)] p-4 text-[13px] leading-[1.7] text-[var(--color-text-secondary)]">
          {currentTier === 'free'
            ? '当前为体验版。新会员开通入口已关闭，后续会逐步开放免费调用。'
            : '你已获得的会员权益会按原到期时间继续保留，不会因为入口关闭而失效。'}
        </div>
      </div>
    </div>
  )
}
