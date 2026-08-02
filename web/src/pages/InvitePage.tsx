import { useEffect, useState } from 'react'
import { useThemeStore } from '../stores/themeStore'
import { useToastStore } from '../stores/toastStore'
import { getInviteStatus, type InviteStatus } from '../services/api'
import { Skeleton } from '../components/ui/Skeleton'
import { useSafeBack } from '../hooks/useSafeBack'

export function InvitePage() {
  const goBack = useSafeBack('/character')
  const { resolvedTheme } = useThemeStore()
  const showToast = useToastStore((s) => s.show)
  const [status, setStatus] = useState<InviteStatus | null>(null)
  const [loadError, setLoadError] = useState(false)

  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.webp'
    : '/assets/backgrounds/聊天背景图.webp'

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
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      <img src={bgImage} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      <div style={{ height: 'var(--safe-top)' }} />

      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-medium text-[var(--color-ink)]">邀请好友</span>
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
            <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[20px] border border-[var(--color-border-glass)] shadow-[var(--shadow-hero)] p-6 mt-4 mb-5 text-center">
              <p className="text-[14px] text-[var(--color-text-secondary)] mb-1">邀请好友，双方各得 40 yuoyuo币</p>
              <p className="text-[13px] text-[var(--color-text-muted)] mb-3">好友完成首次聊天后到账</p>
              <button
                onClick={() => copy(status.invite_code, '邀请码')}
                className="inline-flex items-center gap-2 px-5 py-3 rounded-[14px] bg-[var(--color-glass-90)] border border-[var(--color-border-glass)] active:scale-[0.98] transition-transform"
              >
                <span className="text-[24px] font-bold tracking-[0.16em] text-[var(--color-ink)] font-[var(--font-latin)]">
                  {status.invite_code}
                </span>
                <span className="text-[13px] font-medium text-[var(--color-primary)]">复制</span>
              </button>
              <button
                onClick={() => copy(status.invite_url, '邀请链接')}
                className="mt-3 block w-full text-center py-3 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-[var(--color-text-on-primary)] text-[15px] font-medium shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform"
              >
                复制邀请链接
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              <StatCell label="已邀请" value={invited} />
              <StatCell label="待首聊" value={status.pending_count} />
              <StatCell label="累计获得" value={status.total_reward} accent />
            </div>

            {/* Stage progress */}
            <p className="text-[13px] font-medium text-[var(--color-ink)] mb-3">阶段奖励</p>
            <div className="space-y-4">
              {status.stages.map((stage) => {
                const pct = Math.min(100, Math.round((invited / stage.threshold) * 100))
                return (
                  <div key={stage.threshold} className="bg-[var(--color-glass-card)] backdrop-blur-[16px] rounded-[16px] border border-[var(--color-border-glass)] p-4">
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

            <p className="text-center text-[12px] text-[var(--color-text-muted)] mt-6">
              奖励在好友完成首次聊天后自动发放。
            </p>
          </>
        )}
      </div>
    </div>
  )
}

function StatCell({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="bg-[var(--color-glass-card)] backdrop-blur-[16px] rounded-[16px] border border-[var(--color-border-glass)] p-3 text-center">
      <p className={`text-[22px] font-bold ${accent ? 'text-[var(--color-primary)]' : 'text-[var(--color-ink)]'}`}>{value}</p>
      <p className="text-[12px] text-[var(--color-text-muted)] mt-1">{label}</p>
    </div>
  )
}
