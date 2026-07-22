import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useStoryStore } from '../stores/storyStore'
import { useCharactersStore } from '../stores/charactersStore'
import { TabBar } from '../components/ui/TabBar'
import { Skeleton } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/ErrorState'
import { EmptyState } from '../components/ui/EmptyState'
import { ScenarioCard } from '../components/story/ScenarioCard'
import { resolveCharacterProfile } from '../data/uiContent'

/**
 * Explore (探索) — the play center. Hero featured scenario + genre filter chips
 * + scenario grid + a companion (陪伴) strip that links back to persona chat.
 * Read-only in this PR; starting a run lands with the player UI (PR4).
 */
export function ExplorePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const {
    scenarios,
    genres,
    activeGenre,
    loading,
    loaded,
    error,
    loadCatalog,
    setGenre,
  } = useStoryStore()
  const characters = useCharactersStore((s) => s.characters)

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog])

  const pageBg =
    resolvedTheme === 'dark'
      ? '/assets/backgrounds/暗色聊天背景图.png'
      : '/assets/backgrounds/聊天背景图.png'

  const featured = scenarios.find((s) => s.is_featured) ?? null
  const grid = scenarios.filter((s) => s.id !== featured?.id)
  const openScenario = (id: string) => navigate(`/explore/${id}`)

  return (
    <div className="relative w-full h-full overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />

      <div className="relative z-10 h-full flex flex-col">
        <div style={{ height: 'var(--safe-top)' }} />

        {/* Header */}
        <div className="flex items-center justify-between pl-5 pr-4 py-3 shrink-0">
          <div className="flex flex-col">
            <span className="text-[24px] font-bold text-[var(--color-ink)]">探索</span>
            <span className="text-[12px] text-[var(--color-text-secondary)]">
              进入一段由 AI 主持的互动剧情
            </span>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 pb-[160px]">
          {loading && !loaded ? (
            <ExploreSkeleton />
          ) : error && !loaded ? (
            <div className="pt-20">
              <ErrorState
                title="加载失败"
                description="剧情列表没能加载出来，检查网络后重试。"
                onRetry={() => void loadCatalog(true)}
              />
            </div>
          ) : (
            <>
              {/* Featured hero */}
              {featured && (
                <button
                  onClick={() => openScenario(featured.id)}
                  className="relative w-full h-[220px] rounded-[24px] overflow-hidden shadow-[var(--shadow-hero)] mb-5 active:scale-[0.98] transition-transform"
                  style={{ background: 'linear-gradient(135deg, #FFD6E0 0%, #C8B6FF 100%)' }}
                >
                  {featured.cover_url && (
                    <img
                      src={featured.cover_url}
                      alt=""
                      className="absolute inset-0 w-full h-full object-cover"
                    />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent" />
                  <div className="absolute top-3 left-3 inline-flex h-[24px] items-center rounded-full bg-white/85 px-2.5 text-[12px] font-semibold text-[var(--color-primary-600)]">
                    ✨ 今日精选
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 p-4 text-left">
                    <p className="text-[20px] font-bold text-white leading-[1.3] line-clamp-1">
                      {featured.title}
                    </p>
                    <p className="mt-1 text-[13px] text-white/85 leading-[1.5] line-clamp-2">
                      {featured.blurb}
                    </p>
                    <div className="mt-2 flex items-center gap-2 text-[12px] text-white/80">
                      <span className="rounded-full bg-white/20 px-2 py-0.5">{featured.genre}</span>
                      <span>🔥 {featured.play_count} 人玩过</span>
                    </div>
                  </div>
                </button>
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
                <div className="grid grid-cols-2 gap-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="w-full aspect-[3/4] rounded-[20px]" />
                  ))}
                </div>
              ) : grid.length === 0 && !featured ? (
                <div className="pt-16">
                  <EmptyState
                    title="还没有剧情"
                    description="剧情正在整理上架中，先去和角色聊聊天吧。"
                    actionLabel="去聊天"
                    onAction={() => navigate('/chat')}
                  />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
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

              <div className="h-[60px]" aria-hidden="true" />
            </>
          )}
        </div>

        <TabBar />
      </div>
    </div>
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
          ? 'bg-[var(--color-primary)] text-white shadow-[var(--shadow-send)]'
          : 'bg-[var(--color-glass-55)] text-[var(--color-ink)] border border-[var(--color-border-glass)]'
      }`}
    >
      {label}
    </button>
  )
}

function ExploreSkeleton() {
  return (
    <>
      <Skeleton className="w-full h-[220px] rounded-[24px] mb-5" />
      <div className="flex gap-2 mb-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[34px] w-[72px] rounded-full" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="w-full aspect-[3/4] rounded-[20px]" />
        ))}
      </div>
    </>
  )
}
