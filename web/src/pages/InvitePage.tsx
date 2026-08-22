import { useEffect, useState } from 'react'
import { useToastStore } from '../stores/toastStore'
import { getInviteStatus, type InviteStatus } from '../services/api'
import { Skeleton } from '../components/ui/Skeleton'
import { useSafeBack } from '../hooks/useSafeBack'

export function InvitePage() {
  const goBack = useSafeBack('/character')
  const showToast = useToastStore((s) => s.show)
  const [status, setStatus] = useState<InviteStatus | null>(null)
  const [loadError, setLoadError] = useState(false)

  const load = () => {
    setLoadError(false)
    getInviteStatus().then(setStatus).catch(() => setLoadError(true))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text)
      showToast(`${label}已复制`, 'success')
    } catch {
      showToast('复制失败，请手动复制', 'error')
    }
  }

  const invited = status?.invited_count ?? 0

  return (
    <div className="app-atmosphere relative flex h-full w-full flex-col overflow-hidden">
      <div style={{ height: 'var(--safe-top)' }} />

      <nav className="relative z-20 flex h-[52px] shrink-0 items-center justify-between border-b border-white/40 px-5">
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-semibold text-[var(--color-ink)]">邀请好友</span>
        <div className="w-[44px]" />
      </nav>

      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-8">
        {loadError && (
          <div className="text-center py-12">
            <p className="text-[var(--color-text-muted)] text-[14px]">加载失败</p>
            <button onClick={load} className="mt-3 text-[13px] text-[var(--color-primary)] active:opacity-60">重试</button>
          </div>
        )}

        {!status && !loadError && (
          <div className="space-y-4 mt-4">
            <Skeleton height={140} className="rounded-[20px]" />
            <Skeleton height={80} className="rounded-[20px]" />
            <Skeleton height={120} className="rounded-[20px]" />
          </div>
        )}

        {status && (
          <>
            {/* Invite code hero */}
            <div className="relative mt-4 mb-5 overflow-hidden rounded-[20px] border border-[var(--color-border-glass)] bg-[var(--color-page-surface)] p-5 shadow-[var(--shadow-card)]">
              <div className="pointer-events-none absolute right-0 top-0 h-[150px] w-[180px] bg-[linear-gradient(115deg,transparent,rgba(255,183,197,0.22))]" />
              <div className="relative min-h-[132px] pr-[112px]">
                <p className="text-[11px] font-semibold tracking-[0.14em] text-[var(--color-primary-600)]">YUOYUO 邀请计划</p>
                <h1 className="mt-2 text-[22px] font-semibold leading-[1.35] text-[var(--color-ink)]">邀请朋友，一起聊得更久</h1>
                <p className="mt-2 text-[13px] leading-[1.6] text-[var(--color-text-secondary)]">你和好友各得 40 yuoyuo币，好友完成首次聊天后到账。</p>
                <img src="/assets/settings/invite-mascot.webp" alt="" className="pointer-events-none absolute -right-2 -top-2 h-[122px] w-[122px] object-contain" />
              </div>
              <div className="relative mt-4 border-t border-[var(--color-divider)] pt-4">
                <p className="mb-2 text-[12px] text-[var(--color-text-muted)]">我的邀请码</p>
                <button
                  onClick={() => copy(status.invite_code, '邀请码')}
                  className="flex w-full items-center justify-between rounded-[13px] border border-[var(--color-border-glass)] bg-[var(--color-page-soft)] px-4 py-3 active:scale-[0.99] transition-transform"
                >
                  <span className="text-[23px] font-bold tracking-[0.16em] text-[var(--color-ink)] font-[var(--font-latin)]">
                    {status.invite_code}
                  </span>
                  <span className="text-[13px] font-medium text-[var(--color-primary-600)]">复制</span>
                </button>
                <button
                  onClick={() => copy(status.invite_url, '邀请链接')}
                  className="mt-3 block w-full rounded-[13px] bg-[var(--color-primary-500)] py-3 text-center text-[15px] font-medium text-white shadow-[var(--shadow-btn)] active:scale-[0.98] transition-transform"
                >
                  复制邀请链接
                </button>
              </div>
            </div>

            {/* Stats */}
            <div className="mb-6 grid grid-cols-3 divide-x divide-[var(--color-divider)] overflow-hidden rounded-[18px] border border-[var(--color-border-glass)] bg-[var(--color-page-surface)]/88 py-3 shadow-[var(--shadow-soft)]">
              <div className="text-center">
                <p className="text-[21px] font-bold text-[var(--color-ink)]">{invited}</p>
                <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">已邀请</p>
              </div>
              <div className="text-center">
                <p className="text-[21px] font-bold text-[var(--color-ink)]">{status.pending_count}</p>
                <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">待首聊</p>
              </div>
              <div className="text-center">
                <p className="text-[21px] font-bold text-[var(--color-primary-600)]">{status.total_reward}</p>
                <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">累计 yuoyuo币</p>
              </div>
            </div>

            {/* Stage progress */}
            <div className="mb-3 flex items-end justify-between px-1">
              <p className="text-[15px] font-semibold text-[var(--color-ink)]">阶段奖励</p>
              <span className="text-[11px] text-[var(--color-text-muted)]">完成首次聊天后到账</span>
            </div>
            <div className="overflow-hidden rounded-[18px] border border-[var(--color-border-glass)] bg-[var(--color-page-surface)]/88 shadow-[var(--shadow-soft)]">
              {status.stages.map((stage) => {
                const pct = Math.min(100, Math.round((invited / stage.threshold) * 100))
                return (
                  <div key={stage.threshold} className="border-b border-[var(--color-divider)] p-4 last:border-b-0">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[14px] text-[var(--color-ink)]">
                        邀请满 {stage.threshold} 人
                      </span>
                      <span className={`text-[13px] font-medium ${stage.reached ? 'text-[var(--color-success)]' : 'text-[var(--color-primary)]'}`}>
                        {stage.reached ? `已领取 +${stage.bonus}` : `+${stage.bonus} yuoyuo币`}
                      </span>
                    </div>
                    <div className="h-[8px] rounded-full bg-[var(--color-glass-35)] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-accent)] transition-[width] duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <p className="text-[11px] text-[var(--color-text-muted)] mt-1">{Math.min(invited, stage.threshold)}/{stage.threshold}</p>
                  </div>
                )
              })}
            </div>

            <p className="mt-5 text-center text-[12px] text-[var(--color-text-muted)]">奖励在好友完成首次聊天后自动发放。</p>
          </>
        )}
      </div>
    </div>
  )
}
