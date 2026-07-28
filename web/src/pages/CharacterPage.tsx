import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { TabBar } from '../components/ui/TabBar'
import {
  resolveCharacterProfile,
  CHARACTER_ROLE_TAGS,
  DEFAULT_COVER,
  DISCOVERY_RECOMMENDED,
  DISCOVERY_ALL,
  type CharacterProfile,
} from '../data/uiContent'
import { useCharactersStore } from '../stores/charactersStore'
import { useCompanionsStore } from '../stores/companionsStore'
import { stageWithIntimacy, isColdWar } from '../utils/relationship'
import type { CompanionDTO } from '../services/api'

/** Visibility badge config for owned UGC character cards. */
const VIS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  public:   { label: '公开',   color: '#5FC8E8', bg: 'rgba(95,200,232,0.35)' },
  unlisted: { label: '链接可见', color: '#A7C7E7', bg: 'rgba(167,199,231,0.35)' },
  private:  { label: '私密',   color: '#FFFFFF', bg: 'rgba(255,255,255,0.25)' },
}

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
  companion?: CompanionDTO
  chatUserCount?: number
}

export function CharacterPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const serverCharacters = useCharactersStore((s) => s.characters)
  const loadCharacters = useCharactersStore((s) => s.load)
  const companions = useCompanionsStore((s) => s.companions)
  const loadCompanions = useCompanionsStore((s) => s.load)

  const [activeTag, setActiveTag] = useState<string>(DISCOVERY_RECOMMENDED)
  const [showSearch, setShowSearch] = useState(false)
  const [query, setQuery] = useState('')

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
          companion: companionById.get(c.id),
          chatUserCount: c.chat_user_count,
          profile: resolveCharacterProfile(c.id, c.display_name, c.avatar_url, {
            isOwner,
            coverUrl: c.cover_url,
            tags: c.tags,
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

  // Filter chips: leading editorial filters (推荐 / 全部) + data-derived role
  // tags, ordered by the canonical CHARACTER_ROLE_TAGS priority so curated
  // categories lead, then any remaining tags in first-seen order. `推荐` never
  // appears as a data tag here — it's the editorial lead filter.
  const tagChips = useMemo(() => {
    const present = new Set<string>()
    for (const it of items) {
      for (const t of it.profile.tags ?? []) {
        if (t && t !== DISCOVERY_RECOMMENDED) present.add(t)
      }
    }
    const ordered: string[] = []
    for (const t of CHARACTER_ROLE_TAGS) {
      if (present.has(t)) {
        ordered.push(t)
        present.delete(t)
      }
    }
    // leftover non-curated tags, first-seen order
    for (const it of items) {
      for (const t of it.profile.tags ?? []) {
        if (t && t !== DISCOVERY_RECOMMENDED && present.has(t)) {
          ordered.push(t)
          present.delete(t)
        }
      }
    }
    return [DISCOVERY_RECOMMENDED, DISCOVERY_ALL, ...ordered]
  }, [items])

  // Virtual heat mapping: sort by real chat_user_count DESC, map rank → 500-5000
  const heatMap = useMemo(() => {
    const withHeat = items
      .map((it, idx) => ({ id: it.id, real: it.chatUserCount ?? 0, idx }))
      .filter((x) => x.real > 0)
    withHeat.sort((a, b) => b.real - a.real)
    const map = new Map<string, number>()
    const n = withHeat.length
    if (n === 0) return map
    withHeat.forEach((x, rank) => {
      // Linear interpolation: rank 0 → 5000, rank (n-1) → 500
      const virtual = n === 1 ? 2750 : Math.round(5000 - (rank / (n - 1)) * 4500)
      map.set(x.id, virtual)
    })
    return map
  }, [items])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items.filter((it) => {
      const tags = it.profile.tags ?? []
      // Tag/category filter only applies when there is no search query.
      // Typing should search across the full catalog regardless of the active tab.
      if (!q) {
        if (activeTag === DISCOVERY_RECOMMENDED) {
          // Editorial: built-ins + anything explicitly tagged 推荐 on import.
          if (!(it.isBuiltin || tags.includes(DISCOVERY_RECOMMENDED))) return false
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
  }, [items, activeTag, query])

  const pageBg =
    resolvedTheme === 'dark'
      ? '/assets/backgrounds/暗色聊天背景图.webp'
      : '/assets/backgrounds/聊天背景图.webp'

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />

      <div className="relative z-10 h-full flex flex-col">
        <div style={{ height: 'var(--safe-top)' }} />

        {/* Navigation bar */}
        <div className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
          <button onClick={() => navigate('/home')} className="w-[44px] h-[44px] -ml-3 flex items-center justify-center">
            <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="10,2 2,10 10,18" />
            </svg>
          </button>
          <span className="text-[17px] font-medium text-[var(--color-ink)]">角色</span>
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
              onClick={() => navigate('/my-characters')}
              className="h-[34px] px-3 rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] text-[13px] text-[var(--color-primary)] font-medium active:scale-[0.96] transition-transform"
            >
              我的角色
            </button>
            <button
              onClick={() => navigate('/characters/new')}
              aria-label="创建角色"
              className="w-[34px] h-[34px] rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] flex items-center justify-center text-[var(--color-primary)] active:scale-[0.96] transition-transform"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="7" y1="1" x2="7" y2="13" />
                <line x1="1" y1="7" x2="13" y2="7" />
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
        <div className="relative z-10 flex-1 overflow-y-auto px-4 pt-1 pb-[80px]">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-2 pb-20">
              <span className="text-[15px] text-[var(--color-text-secondary)]">
                {items.length === 0 ? '正在加载角色…' : '没有找到匹配的角色'}
              </span>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {filtered.map((it) => (
                <DiscoveryCard key={it.id} item={it} heatMap={heatMap} onOpen={() => navigate(`/character/${it.id}`)} />
              ))}
            </div>
          )}
        </div>

        <TabBar />
      </div>
    </div>
  )
}

function DiscoveryCard({ item, heatMap, onOpen }: { item: GridItem; heatMap: Map<string, number>; onOpen: () => void }) {
  const { profile, isOwner, companion, visibility, chatUserCount } = item
  const tags = profile.tags ?? []
  const chatted = !!companion && companion.companion_status !== 'locked'
  const hook = profile.tagline || profile.summary || ''
  const virtualHeat = chatUserCount && chatUserCount > 0 ? heatMap.get(item.id) : undefined

  // Visibility badge for owned UGC characters
  const visInfo = isOwner ? VIS_BADGE[visibility ?? 'private'] ?? VIS_BADGE.private : null

  return (
    <button
      onClick={onOpen}
      className="group relative flex flex-col text-left w-full rounded-[20px] overflow-hidden bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)] active:scale-[0.97] transition-transform"
    >
      <div
        className="relative w-full aspect-[3/4]"
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

        {/* intimacy badge (chatted only) — unread lives on the messages surface,
            not the browse catalog, so we intentionally don't show it here. */}
        {chatted && (
          <span className="absolute top-2 right-2 inline-flex h-[22px] items-center rounded-full bg-[var(--color-primary)] px-2 text-[11px] font-medium text-white shadow-[var(--shadow-soft)]">
            {isColdWar(companion!.relationship_stage)
              ? '闹别扭'
              : stageWithIntimacy(companion!.relationship_stage, companion!.intimacy)}
          </span>
        )}

        {/* name + hook + tags overlay */}
        <div className="absolute inset-x-0 bottom-0 p-2.5">
          <p className="text-[15px] font-bold leading-tight text-white line-clamp-1">{profile.name}</p>
          {hook && <p className="mt-0.5 text-[11px] leading-tight text-white/80 line-clamp-1">{hook}</p>}
          {/* Heat indicator (virtual value 500-5000, preserves real ranking) */}
          {virtualHeat !== undefined && (
            <div className="mt-1 flex items-center gap-1">
              <span className="text-[11px] text-white/85">🔥</span>
              <span className="text-[11px] text-white/85">{formatPlays(virtualHeat)}</span>
            </div>
          )}
          {/* Tags row — show all tags instead of slice(0,3) */}
          {tags.length > 0 && (
            <p className="mt-1 text-[10px] leading-tight text-white/70 line-clamp-1">{tags.join(' · ')}</p>
          )}
        </div>
      </div>
    </button>
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
