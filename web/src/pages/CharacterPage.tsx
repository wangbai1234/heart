import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useScrollRestore } from '../hooks/useScrollRestore'
import { TabBar } from '../components/ui/TabBar'
import { Dialog } from '../components/ui/Dialog'
import { Button } from '../components/ui/Button'
import { AnnouncementSheet } from '../components/AnnouncementSheet'
import {
  resolveCharacterProfile,
  CHARACTER_STYLE_TAGS,
  CHARACTER_ROLE_TAGS,
  DEFAULT_COVER,
  DISCOVERY_RECOMMENDED,
  DISCOVERY_ALL,
  type CharacterProfile,
} from '../data/uiContent'
import { useCharactersStore } from '../stores/charactersStore'
import { useCompanionsStore } from '../stores/companionsStore'
import { useFavoritesStore } from '../stores/favoritesStore'
import type { CompanionDTO } from '../services/api'

/** Visibility badge config for owned UGC character cards. */
const VIS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  public:   { label: '公开',   color: '#5FC8E8', bg: 'rgba(95,200,232,0.35)' },
  unlisted: { label: '链接可见', color: '#A7C7E7', bg: 'rgba(167,199,231,0.35)' },
  private:  { label: '私密',   color: '#FFFFFF', bg: 'rgba(255,255,255,0.25)' },
}

const DISCOVERY_FAVORITES = '收藏'

/**
 * 角色发现页 (Nimoo-style discovery catalog).
 *
 * Replaces the old 「羁绊中心」 (chatted-only hero + gallery) with a browsable
 * 2-column portrait grid over the full public catalog + own UGC. A companion
 * overlay (keyed by character_id) surfaces 亲密度 on characters the user has
 * chatted with. Style-filter chips + a search entry narrow the grid client-side.
 *
 * Per product direction (2026-07-25): no 创作者 tab, no notification bell; the
 * existing 「我的角色」/「创建角色」 entries are kept (我的角色 later drives
 * publish/edit/disable). Covers use cover_url; missing covers derive a blurred
 * avatar fallback. Card → /character/:id profile.
 */

interface GridItem {
  id: string
  profile: CharacterProfile
  isOwner: boolean
  isBuiltin: boolean
  visibility?: string
  reviewStatus?: string
  companion?: CompanionDTO
  chatUserCount?: number
}

/**
 * Whether a grid item may appear in the discovery (广场) list. Rule:
 * built-ins and public+approved characters are visible to everyone; anything
 * else (own private / pending / unlisted / rejected UGC) is hidden here and
 * managed only in「我的角色」. A character the user has actually interacted with
 * (companioned/encountered) still shows so an existing bond never vanishes.
 */
function isDiscoverable(it: GridItem): boolean {
  if (it.isBuiltin) return true
  if (it.visibility === 'public' && it.reviewStatus === 'approved') return true
  return !!it.companion && it.companion.companion_status !== 'locked'
}

const FEATURED_CHARACTER_ORDER = ['gu_beichen', 'qin_xiao', 'li_jue', 'jiang_yueze', 'gu_xingzhou', 'jiang_ye'] as const
const FEATURED_CHARACTER_INDEX = new Map<string, number>(FEATURED_CHARACTER_ORDER.map((id, index) => [id, index]))
const DISCOVERY_TAG_PRIORITY = [
  ...CHARACTER_ROLE_TAGS,
  ...CHARACTER_STYLE_TAGS,
  '都市',
  '夜色',
  '职场',
  '异国',
  '欧风',
  '拳手',
  '管家',
  '血族',
  '血仆',
  '调酒师',
  '赌王',
  '学霸',
  '贵公子',
  '危险关系',
  '救赎',
  '占有欲',
  '克制',
  '忠犬',
  '暗恋',
  '博弈',
] as const
const EDITORIAL_HEAT_OVERRIDES = new Map<string, number>([
  ['zhou_jin', 5867],
  ['song_ye', 4218],
  ['pei_tinglan', 5732],
  ['vito_rosetti', 3976],
  ['xie_ci', 5421],
  ['fu_mingxiu', 5894],
  ['shen_liao', 4685],
  ['xize', 3512],
  ['lu_wenjing', 5238],
  ['luo_fei', 4879],
  ['jiang_ran', 4356],
  ['gu_yanli', 5608],
  ['xu_zhihan', 3167],
])

function stableShuffleScore(id: string): number {
  let hash = 0
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 131 + id.charCodeAt(i)) % 1000003
  }
  return hash
}

export function CharacterPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const serverCharacters = useCharactersStore((s) => s.characters)
  const loadCharacters = useCharactersStore((s) => s.load)
  const companions = useCompanionsStore((s) => s.companions)
  const loadCompanions = useCompanionsStore((s) => s.load)
  const { toggle: toggleFavorite, has: isFavorite } = useFavoritesStore()

  const [activeTag, setActiveTag] = useState<string>(DISCOVERY_RECOMMENDED)
  const [showSearch, setShowSearch] = useState(false)
  const [showAnnounce, setShowAnnounce] = useState(false)
  const [query, setQuery] = useState('')
  const scrollRef = useScrollRestore()

  // First-arrival compliance reminder (18+ / community guidelines). Shows once
  // per device after the user lands on the discovery page (i.e. right after
  // registration + profile setup auto-redirects here). Independent one-time flag.
  const [showNotice, setShowNotice] = useState(false)
  useEffect(() => {
    try {
      if (localStorage.getItem('yuoyuo-compliance-notice') !== '1') setShowNotice(true)
    } catch { /* storage unavailable — skip the reminder rather than block entry */ }
  }, [])
  const dismissNotice = () => {
    setShowNotice(false)
    try { localStorage.setItem('yuoyuo-compliance-notice', '1') } catch { /* ignore */ }
  }

  useEffect(() => {
    void loadCharacters()
    void loadCompanions()
  }, [loadCharacters, loadCompanions])

  // companion lookup by character_id → overlays intimacy / unread onto catalog rows.
  const companionById = useMemo(() => {
    const m = new Map<string, CompanionDTO>()
    for (const c of companions) m.set(c.character_id, c)
    return m
  }, [companions])

  // Base list = server catalog (public + own UGC). Cold-start fallback: derive a
  // grid straight from companions so the page is never empty before /characters
  // resolves.
  const items: GridItem[] = useMemo(() => {
    if (serverCharacters.length > 0) {
      return serverCharacters.map((c) => {
        const isOwner = c.is_owner && !c.is_builtin
        return {
          id: c.id,
          isOwner,
          isBuiltin: c.is_builtin,
          visibility: c.visibility,
          reviewStatus: c.review_status,
          companion: companionById.get(c.id),
          chatUserCount: c.chat_user_count,
          profile: resolveCharacterProfile(c.id, c.display_name, c.avatar_url, {
            isOwner,
            coverUrl: c.cover_url,
            tags: c.tags,
            tagline: c.tagline ?? undefined,
          }),
        }
      })
    }
    return companions.map((c) => {
      const isOwner = c.is_owner && !c.is_builtin
      return {
        id: c.character_id,
        isOwner,
        isBuiltin: c.is_builtin,
        visibility: c.visibility,
        companion: c,
        chatUserCount: undefined,
        profile: resolveCharacterProfile(c.character_id, c.display_name, c.avatar_url, {
          isOwner,
          coverUrl: c.cover_url,
          tags: c.tags,
        }),
      }
    })
  }, [serverCharacters, companions, companionById])

  const rankedItems = useMemo(() => {
    return [...items].sort((left, right) => {
      const leftFeatured = FEATURED_CHARACTER_INDEX.get(left.id)
      const rightFeatured = FEATURED_CHARACTER_INDEX.get(right.id)
      if (leftFeatured !== undefined || rightFeatured !== undefined) {
        if (leftFeatured === undefined) return 1
        if (rightFeatured === undefined) return -1
        return leftFeatured - rightFeatured
      }
      return stableShuffleScore(left.id) - stableShuffleScore(right.id)
    })
  }, [items])

  // Filter chips: leading editorial filters (推荐 / 全部 / 收藏) + data-derived role
  // tags, ordered by the canonical CHARACTER_ROLE_TAGS priority so curated
  // categories lead, then any remaining tags in first-seen order. `推荐` never
  // appears as a data tag here — it's the editorial lead filter.
  const tagChips = useMemo(() => {
    const present = new Set<string>()
    for (const it of rankedItems) {
      for (const t of it.profile.tags ?? []) {
        if (t && t !== DISCOVERY_RECOMMENDED) present.add(t)
      }
    }
    const ordered: string[] = []
    for (const t of DISCOVERY_TAG_PRIORITY) {
      if (present.has(t)) {
        ordered.push(t)
        present.delete(t)
      }
    }
    // leftover non-curated tags, first-seen order
    for (const it of rankedItems) {
      for (const t of it.profile.tags ?? []) {
        if (t && t !== DISCOVERY_RECOMMENDED && present.has(t)) {
          ordered.push(t)
          present.delete(t)
        }
      }
    }
    return [DISCOVERY_RECOMMENDED, DISCOVERY_FAVORITES, DISCOVERY_ALL, ...ordered]
  }, [rankedItems])

  // Editorial heat mapping: featured characters are fixed at the front, the
  // remainder follow a stable pseudo-random order.
  const heatMap = useMemo(() => {
    const withHeat = rankedItems.map((it) => ({ id: it.id }))
    const map = new Map<string, number>()
    const n = withHeat.length
    if (n === 0) return map
    withHeat.forEach((x, rank) => {
      const override = EDITORIAL_HEAT_OVERRIDES.get(x.id)
      if (override !== undefined) {
        map.set(x.id, override)
        return
      }
      const virtual = n === 1 ? 2750 : Math.round(5000 - (rank / (n - 1)) * 4500)
      map.set(x.id, virtual)
    })
    return map
  }, [rankedItems])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const result = rankedItems.filter((it) => {
      // Discovery gate: hide own private / pending / unlisted UGC from 广场.
      if (!isDiscoverable(it)) return false
      const tags = it.profile.tags ?? []
      if (!q) {
        if (activeTag === DISCOVERY_FAVORITES) {
          // Show only favorited characters
          if (!isFavorite(it.id)) return false
        } else if (activeTag === DISCOVERY_RECOMMENDED) {
          if (!(it.isOwner || it.isBuiltin || tags.includes(DISCOVERY_RECOMMENDED))) return false
        } else if (activeTag !== DISCOVERY_ALL && !tags.includes(activeTag)) {
          return false
        }
      }
      if (q) {
        const hay = `${it.profile.name} ${tags.join(' ')} ${it.profile.tagline ?? ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
    if (activeTag === DISCOVERY_RECOMMENDED && !q) {
      result.sort((a, b) => {
        const aFem = (a.profile.tags ?? []).includes('女性向') ? 0 : 1
        const bFem = (b.profile.tags ?? []).includes('女性向') ? 0 : 1
        return aFem - bFem
      })
    }
    return result
  }, [rankedItems, activeTag, query, isFavorite])

  const pageBg =
    resolvedTheme === 'dark'
      ? '/assets/backgrounds/暗色聊天背景图.webp'
      : '/assets/backgrounds/聊天背景图.webp'

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />

      <div className="relative z-10 h-full flex flex-col">
        <div style={{ height: 'var(--safe-top)' }} />

        {/* Navigation bar — no back button (角色 is a main tab / landing page).
            Right side: search toggle + announcement bell (Nimoo-style). */}
        <div className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSearch((v) => !v)}
              aria-label="搜索"
              className={`w-[34px] h-[34px] rounded-full backdrop-blur-[12px] border border-[var(--color-border-glass)] flex items-center justify-center active:scale-[0.96] transition-transform ${
                showSearch ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-glass-55)] text-[var(--color-primary)]'
              }`}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <circle cx="7" cy="7" r="5" />
                <line x1="11" y1="11" x2="15" y2="15" />
              </svg>
            </button>
            <button
              onClick={() => setShowAnnounce(true)}
              aria-label="公告"
              className="w-[34px] h-[34px] rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] flex items-center justify-center text-[var(--color-primary)] active:scale-[0.96] transition-transform"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 2.5a3 3 0 0 0-3 3v.9A5.25 5.25 0 0 1 3.2 10.5L2 11.5v1.25h12v-1.25l-1.2-1a5.25 5.25 0 0 1-1.8-4.1v-.9a3 3 0 0 0-3-3Z" />
                <path d="M6.5 14a1.5 1.5 0 0 0 3 0" />
              </svg>
            </button>
          </div>
        </div>

        {/* Search box (toggled) */}
        {showSearch && (
          <div className="relative z-20 px-4 pb-1 pt-1 shrink-0">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索角色名字或标签"
              className="w-full h-[38px] px-4 rounded-full bg-[var(--color-glass-75)] backdrop-blur-[12px] border border-[var(--color-border-glass)] text-[14px] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[var(--color-primary)]"
            />
          </div>
        )}

        {/* Style-filter chips */}
        {tagChips.length > 1 && (
          <div className="relative z-20 shrink-0 flex gap-2 overflow-x-auto px-4 py-2 no-scrollbar">
            {tagChips.map((tag) => (
              <button
                key={tag}
                onClick={() => setActiveTag(tag)}
                className={`shrink-0 h-[30px] px-3.5 rounded-full text-[13px] font-medium border transition-colors ${
                  activeTag === tag
                    ? 'bg-[var(--color-primary)] text-white border-transparent'
                    : 'bg-[var(--color-glass-55)] text-[var(--color-text-secondary)] border-[var(--color-border-glass)]'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}

        {/* Discovery grid */}
        <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 pt-1 pb-[80px]">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-2 pb-20">
              <span className="text-[15px] text-[var(--color-text-secondary)]">
                {items.length === 0 ? '正在加载角色…' : '没有找到匹配的角色'}
              </span>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {filtered.map((it) => (
                <DiscoveryCard
                  key={it.id}
                  item={it}
                  heatMap={heatMap}
                  isFavorite={isFavorite(it.id)}
                  onToggleFavorite={() => toggleFavorite(it.id)}
                  onOpen={() => navigate(`/character/${it.id}`)}
                />
              ))}
            </div>
          )}
        </div>

        <TabBar />
      </div>

      <Dialog
        open={showNotice}
        onClose={dismissNotice}
        title="温馨提示"
        actions={
          <Button variant="primary" size="sm" className="flex-1" onClick={dismissNotice}>
            我已满18岁，知道了
          </Button>
        }
      >
        <p className="leading-[1.7] text-left">
          yuoyuo 是一款面向<span className="font-semibold text-[var(--color-ink)]">成年人</span>的 AI 情感陪伴产品，
          <span className="font-semibold text-[var(--color-ink)]">仅供年满 18 周岁的用户使用</span>。
        </p>
        <p className="leading-[1.7] text-left mt-2">
          所有角色均为虚构，回复由 AI 生成。聊天时请<span className="font-semibold text-[var(--color-ink)]">遵守社区公约</span>，
          不得诱导生成违法或不良内容。
        </p>
        <p className="leading-[1.7] text-left mt-2 text-[var(--color-text-muted)]">
          继续使用即表示你已阅读并同意
          <Link to="/legal/age" className="text-[var(--color-primary)]">《年满18周岁确认》</Link>。
        </p>
      </Dialog>

      <AnnouncementSheet open={showAnnounce} onClose={() => setShowAnnounce(false)} />
    </div>
  )
}

function DiscoveryCard({
  item,
  heatMap,
  isFavorite,
  onToggleFavorite,
  onOpen,
}: {
  item: GridItem
  heatMap: Map<string, number>
  isFavorite: boolean
  onToggleFavorite: () => void
  onOpen: () => void
}) {
  const { profile, isOwner, visibility } = item
  const tags = profile.tags ?? []
  const hook = profile.tagline || profile.summary || ''
  const virtualHeat = heatMap.get(item.id)

  // Visibility badge for owned UGC characters
  const visInfo = isOwner ? VIS_BADGE[visibility ?? 'private'] ?? VIS_BADGE.private : null

  // Show only the top 2 tags that are in the priority list, or the first 2 if none match
  const priorityTags = tags.filter((t) => DISCOVERY_TAG_PRIORITY.includes(t as any)).slice(0, 2)
  const displayTags = priorityTags.length > 0 ? priorityTags : tags.slice(0, 2)

  return (
    <div className="group relative flex flex-col text-left w-full rounded-[20px] overflow-hidden bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]">
      <button
        onClick={onOpen}
        className="relative w-full aspect-[3/4] active:scale-[0.97] transition-transform"
        style={{ background: `linear-gradient(135deg, ${profile.tagBg}, transparent)` }}
      >
        <CoverFill cover={profile.cover} alt={profile.name} />

        {/* bottom scrim for legibility */}
        <div className="absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-black/72 via-black/28 to-transparent" />

        {/* visibility badge for owned UGC characters */}
        {visInfo && (
          <span
            className="absolute top-2 left-2 inline-flex h-[22px] items-center rounded-full px-2 text-[11px] font-medium backdrop-blur-[4px]"
            style={{ background: visInfo.bg, color: visInfo.color }}
          >
            {visInfo.label}
          </span>
        )}

        {/* Heart favorite toggle button — top-right */}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onToggleFavorite()
          }}
          className="absolute top-2 right-2 w-[28px] h-[28px] rounded-full bg-black/30 backdrop-blur-[4px] flex items-center justify-center active:scale-[0.92] transition-transform"
          aria-label={isFavorite ? '取消收藏' : '收藏'}
        >
          {isFavorite ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="#FF6B9D" stroke="#FF6B9D" strokeWidth="1.5">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
            </svg>
          )}
        </button>

        {/* name + hook + interaction data overlay */}
        <div className="absolute inset-x-0 bottom-0 p-2.5 space-y-1">
          <p className="text-[16px] font-bold leading-tight text-white line-clamp-1">{profile.name}</p>
          {hook && (
            <p className="text-[12px] leading-[1.4] text-white/90 italic line-clamp-2">
              "{hook}"
            </p>
          )}
          <div className="flex items-center justify-between gap-2">
            {/* Heat indicator (editorial overrides + virtual value, preserves real ranking) */}
            {virtualHeat !== undefined && (
              <div className="flex items-center gap-1">
                <svg className="text-white/85" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
                </svg>
                <span className="text-[11px] text-white/85">{formatPlays(virtualHeat)}</span>
              </div>
            )}
            {/* Tags row — show only top 2 */}
            {displayTags.length > 0 && (
              <div className="flex gap-1.5">
                {displayTags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center h-[18px] px-2 rounded-full bg-white/15 backdrop-blur-[2px] text-[10px] text-white/80"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </button>
    </div>
  )
}

function formatPlays(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}w 人玩过`
  return `${n} 人玩过`
}

/**
 * Cover image that fades in over the gradient placeholder. When no cover_url is
 * available we fall back to the shared DEFAULT_COVER background image (product
 * direction 2026-07-25: UGC characters no longer have an avatar, so a cover-less
 * card shows the page background rather than a blurred placeholder portrait).
 */
function CoverFill({ cover, alt }: { cover?: string | null; alt: string }) {
  const [loaded, setLoaded] = useState(false)
  const src = cover || DEFAULT_COVER
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      onLoad={() => setLoaded(true)}
      className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
        loaded ? 'opacity-100' : 'opacity-0'
      }`}
    />
  )
}
