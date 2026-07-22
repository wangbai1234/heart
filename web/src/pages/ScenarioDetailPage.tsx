import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useStoryStore } from '../stores/storyStore'
import { NavigationBar } from '../components/ui/NavigationBar'
import { Skeleton } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/ErrorState'
import { StartRunSheet } from '../components/story/StartRunSheet'
import { ApiError } from '../services/api'

/**
 * Scenario detail (探索/:id). Cover + blurb + genre + play count, and the
 * entry point into a run. `maturity='adult'` shows a 🔞 label only — scenarios
 * are not age-gated.
 */
export function ScenarioDetailPage() {
  const navigate = useNavigate()
  const { scenarioId = '' } = useParams()
  const { resolvedTheme } = useThemeStore()
  const { detailById, detailLoading, detailError, loadScenario, loadActiveRun } = useStoryStore()
  const unlockScenario = useStoryStore((s) => s.unlockScenario)
  const activeRun = useStoryStore((s) => s.activeRunByScenario[scenarioId])
  const [sheetOpen, setSheetOpen] = useState(false)
  const [unlocking, setUnlocking] = useState(false)
  const [unlockError, setUnlockError] = useState<string | null>(null)

  const scenario = detailById[scenarioId]

  async function handleUnlock() {
    if (unlocking) return
    setUnlocking(true)
    setUnlockError(null)
    try {
      await unlockScenario(scenarioId)
      // The store flips detail.unlocked → true, so the CTA re-renders to 开始剧情.
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        // Not enough 悠悠币 → send them to recharge; the save is untouched.
        navigate('/wallet')
        return
      }
      setUnlockError(err instanceof Error ? err.message : '解锁失败，请稍后再试')
    } finally {
      setUnlocking(false)
    }
  }

  useEffect(() => {
    if (scenarioId) {
      void loadScenario(scenarioId)
      void loadActiveRun(scenarioId)
    }
  }, [scenarioId, loadScenario, loadActiveRun])

  const pageBg =
    resolvedTheme === 'dark'
      ? '/assets/backgrounds/暗色聊天背景图.png'
      : '/assets/backgrounds/聊天背景图.png'

  return (
    <div className="relative w-full h-full overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      <NavigationBar onBack={() => navigate(-1)} transparent />

      <div className="relative z-10 h-full overflow-y-auto">
        {detailLoading && !scenario ? (
          <DetailSkeleton />
        ) : detailError && !scenario ? (
          <div className="pt-32 px-4">
            <ErrorState
              title="加载失败"
              description="剧情详情没能加载出来。"
              onRetry={() => void loadScenario(scenarioId, true)}
            />
          </div>
        ) : scenario ? (
          <>
            {/* Cover */}
            <div
              className="relative w-full h-[46vh]"
              style={{ background: 'linear-gradient(135deg, #FFD6E0 0%, #C8B6FF 100%)' }}
            >
              {scenario.cover_url && (
                <img
                  src={scenario.cover_url}
                  alt=""
                  className="absolute inset-0 w-full h-full object-cover"
                />
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-surface)] via-transparent to-black/20" />
            </div>

            {/* Body — pulled up over the cover */}
            <div className="relative -mt-10 px-5 pb-[140px]">
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex h-[24px] items-center rounded-full bg-[var(--color-primary)] px-2.5 text-[12px] font-semibold text-white">
                  {scenario.genre}
                </span>
                {scenario.maturity === 'adult' && (
                  <span className="inline-flex h-[24px] items-center rounded-full bg-black/70 px-2 text-[12px] text-white">
                    🔞 成人向
                  </span>
                )}
                <span className="text-[12px] text-[var(--color-text-muted)]">
                  🔥 {scenario.play_count} 人玩过
                </span>
              </div>

              <h1 className="text-[24px] font-bold text-[var(--color-ink)] leading-[1.3] mb-3">
                {scenario.title}
              </h1>

              <div className="rounded-[18px] bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] p-4">
                <p className="text-[13px] font-semibold text-[var(--color-text-secondary)] mb-1.5">
                  剧情简介
                </p>
                <p className="text-[15px] leading-[1.7] text-[var(--color-ink)] whitespace-pre-line">
                  {scenario.blurb || '（暂无简介）'}
                </p>
              </div>
            </div>

            {/* Sticky CTA. Gating order: not-unlocked → unlock (if tier
                allows) or upgrade-membership; once unlocked, a returning player
                gets 继续游玩 + 重新开始, a first-time player gets 开始剧情. */}
            <div
              className="fixed bottom-0 left-0 right-0 z-20 px-5 pt-3 bg-gradient-to-t from-[var(--color-surface)] via-[var(--color-surface)] to-transparent"
              style={{ paddingBottom: 'calc(16px + var(--safe-bottom))' }}
            >
              {unlockError && (
                <p className="mb-2 text-center text-[13px] text-[var(--color-danger,#e5484d)]">
                  {unlockError}
                </p>
              )}
              {!scenario.unlocked ? (
                <>
                  <p className="mb-2 text-center text-[12px] text-[var(--color-text-muted)]">
                    一次性解锁 · 解锁后 {scenario.minute_cost_coins} 悠悠币/分钟
                  </p>
                  {scenario.tier_allowed ? (
                    <button
                      onClick={handleUnlock}
                      disabled={unlocking}
                      className="w-full h-[52px] rounded-[26px] bg-[var(--color-primary)] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.98] transition-transform disabled:opacity-60"
                    >
                      {unlocking ? '解锁中…' : `解锁 · ${scenario.unlock_cost_coins} 悠悠币`}
                    </button>
                  ) : (
                    <button
                      onClick={() => navigate('/membership')}
                      className="w-full h-[52px] rounded-[26px] bg-[var(--color-primary)] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.98] transition-transform"
                    >
                      升级会员解锁
                    </button>
                  )}
                </>
              ) : activeRun ? (
                <div className="flex gap-3">
                  <button
                    onClick={() => setSheetOpen(true)}
                    className="h-[52px] flex-1 rounded-[26px] bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] text-[var(--color-ink)] text-[16px] font-semibold active:scale-[0.98] transition-transform"
                  >
                    重新开始
                  </button>
                  <button
                    onClick={() => navigate(`/story/${activeRun.run_id}`)}
                    className="h-[52px] flex-[1.4] rounded-[26px] bg-[var(--color-primary)] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.98] transition-transform"
                  >
                    继续游玩
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setSheetOpen(true)}
                  className="w-full h-[52px] rounded-[26px] bg-[var(--color-primary)] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.98] transition-transform"
                >
                  开始剧情
                </button>
              )}
            </div>
          </>
        ) : null}
      </div>

      {sheetOpen && scenario && scenario.unlocked && (
        <StartRunSheet
          scenarioId={scenario.id}
          scenarioTitle={scenario.title}
          template={scenario.player_template}
          onClose={() => setSheetOpen(false)}
          onStarted={(runId) => navigate(`/story/${runId}`)}
        />
      )}
    </div>
  )
}

function DetailSkeleton() {
  return (
    <>
      <Skeleton className="w-full h-[46vh] rounded-none" />
      <div className="px-5 -mt-10 relative">
        <Skeleton className="h-[24px] w-[80px] rounded-full mb-3" />
        <Skeleton className="h-[28px] w-2/3 rounded-[8px] mb-4" />
        <Skeleton className="h-[120px] w-full rounded-[18px]" />
      </div>
    </>
  )
}
