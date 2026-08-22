import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStoryStore } from '../stores/storyStore'
import { useCharactersStore } from '../stores/charactersStore'
import { TabBar } from '../components/ui/TabBar'
import { Skeleton } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/ErrorState'
import { EmptyState } from '../components/ui/EmptyState'
import { ScenarioCard, genreGradient } from '../components/story/ScenarioCard'
import { resolveCharacterProfile } from '../data/uiContent'
import { AppPageContent, AppPageShell } from '../components/ui/AppPageShell'

/**
 * Explore (探索) — the play center. Hero featured scenario + genre filter chips
 * + scenario grid + a companion (陪伴) strip that links back to persona chat.
 * Read-only in this PR; starting a run lands with the player UI (PR4).
 */
export function ExplorePage() {
  const navigate = useNavigate()
  const {
    scenarios,
    featuredScenarios,
    genres,
    activeGenre,
    loading,
    loaded,
    error,
    recentScenarios,
    loadCatalog,
    loadRecentScenarios,
    setGenre,
  } = useStoryStore()
  const characters = useCharactersStore((s) => s.characters)

  useEffect(() => {
    void loadCatalog()
    void loadRecentScenarios()
  }, [loadCatalog, loadRecentScenarios])

  // 推荐区：显示热度最高的 4 个 featured 剧情，支持左右滑动
  const featuredTop4 = featuredScenarios.slice(0, 4)
  // 剧情网格：显示当前分类的所有剧情（不排除推荐区剧情，用户可能想从分类找到它们）
  const grid = scenarios
  const openScenario = (id: string) => navigate(`/explore/${id}`)

  return (
    <AppPageShell className="app-atmosphere">
      <div className="relative z-10 h-full flex flex-col bg-transparent">
        <div style={{ height: 'var(--safe-top)' }} />

        {/* Header */}
        <AppPageContent className="flex h-[58px] shrink-0 items-center justify-between px-4 sm:px-5">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] text-[var(--color-primary-600)]">今日故事</p>
            <h1 className="mt-0.5 text-[23px] font-bold leading-none text-[var(--color-ink)]">探索</h1>
          </div>
          <span className="rounded-full border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-3 py-1.5 text-[12px] font-medium text-[var(--color-text-secondary)] shadow-[0_3px_12px_rgba(90,54,68,0.05)]">
            今日精选
          </span>
        </AppPageContent>

        {/* Scrollable content */}
        <AppPageContent className="min-h-0 flex-1 overflow-y-auto px-3.5 pb-[124px] sm:px-5">
          {loading && !loaded ? (
            <ExploreSkeleton />
          ) : error && !loaded ? (
            <div className="mx-auto mt-5 max-w-[520px] rounded-[12px] border border-[var(--color-divider)] bg-[var(--color-page-surface)]">
              <ErrorState
                title="加载失败"
                description="剧情列表没能加载出来，检查网络后重试。"
                onRetry={() => void loadCatalog(true)}
              />
            </div>
          ) : (
            <>
              {/* Featured hero carousel - 支持左右滑动的推荐 banner */}
              {featuredTop4.length > 0 && (
                <div className="-mx-1 mb-5 flex snap-x snap-mandatory gap-2.5 overflow-x-auto px-1 pb-1 scrollbar-none">
                  {featuredTop4.map((scenario) => (
                    <button
                      key={scenario.id}
                      onClick={() => openScenario(scenario.id)}
                      className="relative h-[174px] w-full shrink-0 snap-center overflow-hidden rounded-[15px] border border-white/65 shadow-[0_8px_24px_rgba(73,48,62,0.14)] transition-opacity active:opacity-90 sm:h-[220px] sm:w-[680px]"
                      style={{ background: genreGradient(scenario.genre) }}
                    >
                      {scenario.cover_url && (
                        <img
                          src={scenario.cover_url}
                          alt=""
                          loading="lazy"
                          decoding="async"
                          className="absolute inset-0 w-full h-full object-cover"
                        />
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent" />
                      <div className="absolute left-3 top-3 inline-flex h-[23px] items-center rounded-full bg-black/25 px-2.5 text-[11px] font-semibold text-white backdrop-blur-[5px]">
                        热门推荐
                      </div>
                      <div className="absolute bottom-0 left-0 right-0 p-3.5 text-left">
                        <p className="text-[18px] font-bold leading-[1.3] text-white line-clamp-1">
                          {scenario.title}
                        </p>
                        <p className="mt-1 text-[12px] leading-[1.45] text-white/85 line-clamp-2">
                          {scenario.blurb}
                        </p>
                        <div className="mt-1.5 flex items-center gap-2 text-[11px] text-white/80">
                          <span className="rounded-full bg-white/20 px-2 py-0.5">{scenario.genre}</span>
                          <span>{scenario.play_count} 人玩过</span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Recent scenarios (近期玩过) */}
              {recentScenarios.length > 0 && (
                <div className="mb-5">
                  <div className="mb-2.5 flex items-center gap-1.5">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    <span className="text-[16px] font-bold text-[var(--color-ink)]">近期玩过</span>
                  </div>
                  <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-none">
                    {recentScenarios.map((item) => (
                      <button
                        key={item.run_id}
                        onClick={() => navigate(`/explore/${item.scenario_id}`)}
                        className="w-[92px] shrink-0 transition-transform active:scale-[0.97]"
                      >
                        <div
                          className="h-[118px] w-[92px] overflow-hidden rounded-[12px] border border-white/65 shadow-[0_4px_14px_rgba(73,48,62,0.10)]"
                          style={{ background: genreGradient(item.genre) }}
                        >
                          {item.cover_url && (
                            <img
                              src={item.cover_url}
                              alt=""
                              loading="lazy"
                              decoding="async"
                              className="w-full h-full object-cover"
                            />
                          )}
                        </div>
                        <p className="mt-1.5 text-center text-[12px] font-medium text-[var(--color-ink)] line-clamp-1">
                          {item.title}
                        </p>
                        <p className="mt-0.5 text-center text-[10px] font-medium text-[var(--color-primary-600)]">
                          继续游玩
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Genre filter chips */}
              {genres.length > 0 && (
                <div className="flex gap-2 overflow-x-auto pb-1 mb-4 -mx-1 px-1 scrollbar-none">
                  <GenreChip
                    label="全部"
                    active={activeGenre === null}
                    onClick={() => void setGenre(null)}
                  />
                  {genres.map((g) => (
                    <GenreChip
                      key={g.genre}
                      label={`${g.genre} ${g.count}`}
                      active={activeGenre === g.genre}
                      onClick={() => void setGenre(g.genre)}
                    />
                  ))}
                </div>
              )}

              {/* Scenario grid */}
              {loading ? (
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-4 md:grid-cols-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="w-full aspect-[3/4] rounded-[20px]" />
                  ))}
                </div>
              ) : grid.length === 0 && featuredTop4.length === 0 ? (
                <div className="pt-16">
                  <EmptyState
                    title="还没有剧情"
                    description="剧情正在整理上架中，先去和角色聊聊天吧。"
                    actionLabel="去聊天"
                    onAction={() => navigate('/chat')}
                  />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                  {grid.map((s) => (
                    <ScenarioCard key={s.id} scenario={s} onOpen={openScenario} />
                  ))}
                </div>
              )}

              {/* Companion strip */}
              {characters.length > 0 && (
                <div className="mt-7">
                  <div className="flex items-center justify-between pl-1 pr-1 mb-3">
                    <span className="text-[16px] font-bold text-[var(--color-ink)]">找个人陪你</span>
                    <button
                      onClick={() => navigate('/character')}
                      className="text-[13px] text-[var(--color-text-secondary)]"
                    >
                      全部 ›
                    </button>
                  </div>
                  <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-none">
                    {characters.slice(0, 8).map((c) => {
                      const profile = resolveCharacterProfile(
                        c.id,
                        c.display_name,
                        c.avatar_url,
                        { isOwner: c.is_owner },
                      )
                      return (
                        <button
                          key={c.id}
                          onClick={() => navigate(`/chat/${c.id}`)}
                          className="flex flex-col items-center gap-1.5 shrink-0 w-[64px] active:scale-95 transition-transform"
                        >
                          <img
                            src={profile.avatar}
                            alt=""
                            className="w-[60px] h-[60px] rounded-full object-cover border-2 border-white/70 shadow-[var(--shadow-avatar)]"
                          />
                          <span className="text-[12px] text-[var(--color-ink)] line-clamp-1 w-full text-center">
                            {profile.name}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              <div className="h-[20px]" aria-hidden="true" />
            </>
          )}
        </AppPageContent>

        <TabBar />
      </div>
    </AppPageShell>
  )
}

function GenreChip({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`shrink-0 h-[34px] px-3.5 rounded-full text-[13px] font-medium whitespace-nowrap transition-colors ${
        active
          ? 'bg-[var(--color-primary-500)] text-white shadow-[var(--shadow-send)]'
          : 'border border-[var(--color-divider)] bg-[var(--color-page-surface)] text-[var(--color-text-secondary)] shadow-[0_2px_8px_rgba(73,48,62,0.04)]'
      }`}
    >
      {label}
    </button>
  )
}

function ExploreSkeleton() {
  return (
    <>
      <Skeleton className="mb-5 h-[174px] w-full rounded-[15px]" />
      <div className="flex gap-2 mb-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[32px] w-[72px] rounded-full" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="aspect-[3/4] w-full rounded-[14px]" />
        ))}
      </div>
    </>
  )
}
