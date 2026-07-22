import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useStoryStore } from '../stores/storyStore'
import { NavigationBar } from '../components/ui/NavigationBar'
import { Skeleton } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/ErrorState'
import { StartRunSheet } from '../components/story/StartRunSheet'

/**
 * Scenario detail (探索/:id). Cover + blurb + genre + play count, and the
 * entry point into a run. `maturity='adult'` shows a 🔞 label only — scenarios
 * are not age-gated.
 */
export function ScenarioDetailPage() {
  const navigate = useNavigate()
  const { scenarioId = '' } = useParams()
  const { resolvedTheme } = useThemeStore()
  const { detailById, detailLoading, detailError, loadScenario } = useStoryStore()
  const [sheetOpen, setSheetOpen] = useState(false)

  const scenario = detailById[scenarioId]

  useEffect(() => {
    if (scenarioId) void loadScenario(scenarioId)
  }, [scenarioId, loadScenario])

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

            {/* Sticky CTA */}
            <div
              className="fixed bottom-0 left-0 right-0 z-20 px-5 pt-3 bg-gradient-to-t from-[var(--color-surface)] via-[var(--color-surface)] to-transparent"
              style={{ paddingBottom: 'calc(16px + var(--safe-bottom))' }}
            >
              <button
                onClick={() => setSheetOpen(true)}
                className="w-full h-[52px] rounded-[26px] bg-[var(--color-primary)] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.98] transition-transform"
              >
                开始剧情
              </button>
            </div>
          </>
        ) : null}
      </div>

      {sheetOpen && scenario && (
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
