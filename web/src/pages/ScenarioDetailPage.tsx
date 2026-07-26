import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStoryStore } from '../stores/storyStore'
import { Skeleton } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/ErrorState'
import { StartRunSheet } from '../components/story/StartRunSheet'
import { DEFAULT_COVER } from '../data/uiContent'
import { ApiError } from '../services/api'

/**
 * Scenario detail (探索/:id). Adopts the /character/:id visual language
 * (2026-07-26): full-bleed cover hero with a floating glass back button, glass
 * meta chips, a rounded glass 剧情简介 card, and a gradient primary CTA — while
 * keeping the story-specific gating flow (unlock / upgrade / 继续游玩 +
 * 重新开始 / 开始剧情) and StartRunSheet. `maturity='adult'` shows a 🔞 label
 * only — scenarios are not age-gated.
 */
export function ScenarioDetailPage() {
  const navigate = useNavigate()
  const { scenarioId = '' } = useParams()
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

  // Cover-less scenarios fall back to the shared background image, matching
  // CharacterProfilePage, rather than a bare gradient.
  const cover = scenario?.cover_url || DEFAULT_COVER

  // Floating glass back button (shared with CharacterProfilePage).
  const backButton = (
    <button
      onClick={() => navigate(-1)}
      aria-label="返回"
      className="absolute left-4 z-20 w-[38px] h-[38px] rounded-full bg-black/30 backdrop-blur-[8px] flex items-center justify-center active:scale-[0.95] transition-transform"
      style={{ top: 'calc(var(--safe-top) + 8px)' }}
    >
      <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="10,2 2,10 10,18" />
      </svg>
    </button>
  )

  return (
    <div className="relative w-full h-full overflow-y-auto bg-[var(--color-bg-page)]">
      {backButton}

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
          {/* ── Full-bleed cover ── */}
          <div className="relative w-full h-[62vh] min-h-[380px] overflow-hidden">
            <img
              src={cover}
              alt={scenario.title}
              fetchPriority="high"
              decoding="async"
              className="absolute inset-0 w-full h-full object-cover"
            />
            {/* bottom fade into the sheet below */}
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)]/40 to-transparent" />
          </div>

          {/* ── 关于本剧情 ── */}
          <div className="relative -mt-14 px-5 pb-[140px]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex h-[26px] items-center rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] px-3 text-[12px] font-medium text-[var(--color-text-secondary)]">
                {scenario.genre}
              </span>
              {scenario.maturity === 'adult' && (
                <span className="inline-flex h-[26px] items-center rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] px-3 text-[12px] font-medium text-[var(--color-text-secondary)]">
                  🔞 成人向
                </span>
              )}
              <span className="inline-flex h-[26px] items-center rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] px-3 text-[12px] font-medium text-[var(--color-text-secondary)] tabular-nums">
                🔥 {scenario.play_count} 人玩过
              </span>
            </div>

            <h1 className="mt-3 text-[26px] font-bold text-[var(--color-ink)] leading-tight">
              {scenario.title}
            </h1>

            {/* ── 剧情简介 card ── */}
            <div className="mt-4 rounded-[22px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] p-5">
              <div className="flex items-center gap-2 text-[13px] font-medium text-[var(--color-primary)]">
                <span className="inline-block w-[3px] h-[14px] rounded-full bg-[var(--color-primary)]" />
                剧情简介
              </div>
              <p className="mt-3 text-[15px] leading-[1.7] text-[var(--color-text-secondary)] whitespace-pre-line">
                {scenario.blurb || '（暂无简介）'}
              </p>
            </div>
          </div>

          {/* Sticky CTA. Gating order: not-unlocked → unlock (if tier
              allows) or upgrade-membership; once unlocked, a returning player
              gets 继续游玩 + 重新开始, a first-time player gets 开始剧情. */}
          <div
            className="fixed bottom-0 left-0 right-0 z-20 px-5 pt-3 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)] to-transparent"
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
                    className="w-full h-[52px] rounded-[26px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform disabled:opacity-60"
                  >
                    {unlocking ? '解锁中…' : `解锁 · ${scenario.unlock_cost_coins} 悠悠币`}
                  </button>
                ) : (
                  <button
                    onClick={() => navigate('/membership')}
                    className="w-full h-[52px] rounded-[26px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform"
                  >
                    升级会员解锁
                  </button>
                )}
              </>
            ) : activeRun ? (
              <div className="flex gap-3">
                <button
                  onClick={() => setSheetOpen(true)}
                  className="h-[52px] flex-1 rounded-[26px] bg-[var(--color-glass-75)] backdrop-blur-[12px] border border-[var(--color-border-glass)] text-[var(--color-ink)] text-[16px] font-semibold active:scale-[0.97] transition-transform"
                >
                  重新开始
                </button>
                <button
                  onClick={() => navigate(`/story/${activeRun.run_id}`)}
                  className="h-[52px] flex-[1.4] rounded-[26px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform"
                >
                  继续游玩
                </button>
              </div>
            ) : (
              <button
                onClick={() => setSheetOpen(true)}
                className="w-full h-[52px] rounded-[26px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform"
              >
                开始剧情
              </button>
            )}
          </div>
        </>
      ) : null}

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
      <Skeleton className="w-full h-[62vh] min-h-[380px] rounded-none" />
      <div className="px-5 -mt-14 relative">
        <Skeleton className="h-[26px] w-[80px] rounded-full mb-3" />
        <Skeleton className="h-[28px] w-2/3 rounded-[8px] mb-4" />
        <Skeleton className="h-[120px] w-full rounded-[22px]" />
      </div>
    </>
  )
}
