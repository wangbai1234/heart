import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useScrollRestore } from '../hooks/useScrollRestore'
import { usePullToRefresh } from '../hooks/usePullToRefresh'
import { TabBar } from '../components/ui/TabBar'
import { AppPageShell } from '../components/ui/AppPageShell'
import { NoticeDialog } from '../components/ui/NoticeDialog'
import { Dialog } from '../components/ui/Dialog'
import { AnnouncementSheet } from '../components/AnnouncementSheet'
import { useToastStore } from '../stores/toastStore'
import { parseCharacterId } from '../utils/characterShare'
import {
  resolveCharacterProfile,
  DEFAULT_COVER,
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

/** Primary discovery modes (large tabs). */
const MODE_RECOMMENDED = '推荐'
const MODE_NEWEST = '新角色'
const MODE_FAVORITES = '收藏'
const MODE_MINE = '我的'
const DISCOVERY_MODES = [MODE_RECOMMENDED, MODE_NEWEST, MODE_FAVORITES, MODE_MINE] as const

/** Secondary tag chips (fixed order) shown under the mode tabs. `全部` = no tag filter. */
const TAG_ALL = '全部'
const PINNED_TAGS = ['全性向', '女性向', '男性向', '校园', '都市', '古风', '模拟器', '病娇', '反差', '霸总'] as const
/**
 * 「筛选」popup 里展示的标签 —— 固定写死、固定顺序（产品指定）。
 * 每行 4 个（见 popup 的 grid-cols-4），做屏幕自适应。
 */
const EXTRA_FILTER_TAGS = [
  '年上', '偏执', '纯爱', '占有欲',
  '治愈', '限左', '强制爱', 'GL',
  '忠犬', '高自由', 'BG', '洁',
] as const

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
  createdAt?: string | null
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

const FEATURED_CHARACTER_ORDER = [
  'char_b8ed4c9b', // 祝淮昭
  'char_ae43cbad', // 裴承望
  'he_linchuan',
  'wen_yanqing',
  'li_shen',
  'ji_yu',
  'cheng_xu',
  'gu_beichen',
  'qin_xiao',
  'li_jue',
  'jiang_yueze',
  'gu_xingzhou',
  'jiang_ye',
] as const
const FEATURED_CHARACTER_INDEX = new Map<string, number>(FEATURED_CHARACTER_ORDER.map((id, index) => [id, index]))
const EDITORIAL_HEAT_OVERRIDES = new Map<string, number>([
  ['char_b8ed4c9b', 6388], // 祝淮昭
  ['char_ae43cbad', 6216], // 裴承望
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
  const { has: isFavorite } = useFavoritesStore()

  const showToast = useToastStore((s) => s.show)

  const [activeMode, setActiveMode] = useState<string>(MODE_RECOMMENDED)
  const [activeTag, setActiveTag] = useState<string>(TAG_ALL)
  const [showSearch, setShowSearch] = useState(false)
  const [showAnnounce, setShowAnnounce] = useState(false)
  const [showFilter, setShowFilter] = useState(false)
  const [showOpenLink, setShowOpenLink] = useState(false)
  const [linkInput, setLinkInput] = useState('')
  const [query, setQuery] = useState('')
  const scrollRef = useScrollRestore()

  // Pull-to-refresh: dragging down at the top of the grid force-refreshes the
  // catalog + companions. This is the explicit manual gesture that replaces
  // nagging the user with an "刷新角色页" prompt for newly-approved characters.
  const { bind: pullRef, pull, refreshing, threshold } = usePullToRefresh(async () => {
    await Promise.all([loadCharacters(true), loadCompanions(true)])
  })

  // Fan one callback ref out to both the scroll-restore and pull-to-refresh
  // hooks (they each want the same scrollable element).
  const gridRef = useCallback(
    (el: HTMLDivElement | null) => {
      ;(scrollRef as React.MutableRefObject<HTMLDivElement | null>).current = el
      pullRef.current = el
    },
    [scrollRef, pullRef],
  )

  async function handlePasteLink() {
    try {
      const text = await navigator.clipboard.readText()
      if (text.trim()) setLinkInput(text.trim())
      else showToast('剪贴板是空的', 'info')
    } catch {
      showToast('无法读取剪贴板，请手动粘贴', 'info')
    }
  }

  function handleOpenLink() {
    const cid = parseCharacterId(linkInput)
    if (!cid) {
      showToast('链接无效，请粘贴完整的角色分享链接', 'error')
      return
    }
    setShowOpenLink(false)
    setLinkInput('')
    navigate(`/character/${cid}`)
  }

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
    // The page can be revisited after quick creation while both stores are
    // already marked as loaded. Force a fresh snapshot so the new owned
    // character is immediately available under「我的」without pull-to-refresh.
    void loadCharacters(true)
    void loadCompanions(true)
  }, [loadCharacters, loadCompanions])

  // PWA users keep the app open for days, so a one-time mount load means a
  // character approved after they last opened the app never appears (the store
  // is already `loaded`, so a plain load() no-ops). Force-refresh the catalog
  // whenever the discovery page regains visibility / focus so freshly-approved
  // characters surface without a hard reload. (Same pattern as ConversationChatPage.)
  useEffect(() => {
    const refresh = () => {
      if (document.hidden) return
      void loadCharacters(true)
      void loadCompanions(true)
    }
    document.addEventListener('visibilitychange', refresh)
    window.addEventListener('focus', refresh)
    return () => {
      document.removeEventListener('visibilitychange', refresh)
      window.removeEventListener('focus', refresh)
    }
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
          createdAt: c.created_at,
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
        createdAt: undefined,
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

  // Pinned tags row — fixed order (全部 + 女性向/男性向/.../霸总), always shown.
  const pinnedTagChips = useMemo(() => [TAG_ALL, ...PINNED_TAGS], [])

  // Extra tags for the「筛选」popup — fixed, hardcoded list (see EXTRA_FILTER_TAGS).
  const extraFilterChips = useMemo(() => [...EXTRA_FILTER_TAGS], [])

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
    let base: GridItem[] = []

    // **TIER-1: MODE** — base set per mode
    if (activeMode === MODE_RECOMMENDED) {
      // 推荐 = 全部可发现角色（public+approved + built-ins + own）。编辑精选只作为
      //「排序」体现（featured 置顶 + 女性向优先，见下方 SORT），不再作为「过滤」把
      // 别的用户公开+审核通过的角色挡在外面——否则 推荐+全部 下这些角色永远不出现。
      base = rankedItems.filter(isDiscoverable)
    } else if (activeMode === MODE_NEWEST) {
      // 新角色 = 所有可见角色（内置+UGC）按 created_at DESC
      base = rankedItems.filter((it) => isDiscoverable(it))
    } else if (activeMode === MODE_FAVORITES) {
      // 收藏 = user's favorited characters (can include private/unlisted own UGC)
      base = rankedItems.filter((it) => isFavorite(it.id))
    } else if (activeMode === MODE_MINE) {
      // 我的 = all own characters (public + unlisted + private), bypass discovery gate
      base = rankedItems.filter((it) => it.isOwner)
    } else {
      base = rankedItems.filter(isDiscoverable)
    }

    // **TIER-2: TAG** — apply tag filter on top of mode set
    if (activeTag !== TAG_ALL) {
      base = base.filter((it) => (it.profile.tags ?? []).includes(activeTag))
    }

    // **SEARCH** — text match on name/tags/tagline
    if (q) {
      base = base.filter((it) => {
        const hay = `${it.profile.name} ${(it.profile.tags ?? []).join(' ')} ${it.profile.tagline ?? ''}`.toLowerCase()
        return hay.includes(q)
      })
    }

    // **SORT** — mode-specific
    if (activeMode === MODE_NEWEST && !q) {
      // Sort by created_at DESC for「新角色」
      base.sort((a, b) => {
        const aTime = a.createdAt ? new Date(a.createdAt).getTime() : 0
        const bTime = b.createdAt ? new Date(b.createdAt).getTime() : 0
        return bTime - aTime
      })
    } else if (activeMode === MODE_RECOMMENDED && !q) {
      // 推荐: 精选置顶优先级最高（不受性向影响），其余角色再按「女性向」靠前。
      base.sort((a, b) => {
        const aFeatured = FEATURED_CHARACTER_INDEX.get(a.id)
        const bFeatured = FEATURED_CHARACTER_INDEX.get(b.id)
        if (aFeatured !== undefined || bFeatured !== undefined) {
          if (aFeatured === undefined) return 1
          if (bFeatured === undefined) return -1
          return aFeatured - bFeatured
        }
        const aFem = (a.profile.tags ?? []).includes('女性向') ? 0 : 1
        const bFem = (b.profile.tags ?? []).includes('女性向') ? 0 : 1
        return aFem - bFem
      })
    }

    return base
  }, [rankedItems, activeMode, activeTag, query, isFavorite])

  const isDark = resolvedTheme === 'dark'
  const activeModeText = isDark ? 'text-[var(--color-ink)]' : 'text-[#3A3A4A]'
  const inactiveModeText = isDark ? 'text-[var(--color-text-secondary)]' : 'text-[rgba(58,58,74,0.52)]'
  const inactiveTagText = isDark ? 'text-[var(--color-text-secondary)]' : 'text-[rgba(58,58,74,0.66)]'
  const filterPanelClass = isDark
    ? 'bg-[var(--color-page-surface)] border-[var(--color-divider)]'
    : 'bg-[var(--color-page-surface)] border-[var(--color-divider)]'
  const filterPanelTitle = isDark ? 'text-[var(--color-ink)]' : 'text-[#3A3A4A]'
  const filterPanelHint = isDark ? 'text-[var(--color-text-muted)]' : 'text-[rgba(58,58,74,0.45)]'
  const filterChipIdle = isDark
    ? 'bg-white/[0.04] text-[var(--color-text-secondary)] border-[var(--color-border-glass)]'
    : 'bg-white/30 text-[rgba(58,58,74,0.62)] border-[rgba(58,58,74,0.12)]'
  const headerActionClass = isDark
    ? 'border border-white/10 bg-white/[0.08] text-[var(--color-text-secondary)]'
    : 'border border-white/65 bg-white/68 text-[var(--color-text-secondary)] shadow-[0_3px_12px_rgba(90,54,68,0.06)]'

  return (
    <AppPageShell className="app-atmosphere">
      <div className="relative z-10 h-full flex flex-col">
        <div style={{ height: 'calc(var(--safe-top) + 4px)' }} />

        <div className="character-discovery-chrome relative z-20 shrink-0">
        {/* Navigation bar — brand logo (login-page style) + search / announcement. */}
        <div className="relative z-20 mx-auto flex h-[54px] w-full max-w-[1180px] shrink-0 items-center justify-between gap-2.5 px-4 sm:px-5">
          <img
            src="/assets/ui/wordmark.png"
            alt="yuoyuo"
            className="h-[38px] w-auto shrink-0 select-none"
            draggable={false}
          />
          <div className="flex items-center gap-1.5">
            {showSearch ? (
              <div className="flex items-center gap-1.5">
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="搜索角色 / 标签"
                  className="h-[40px] w-[132px] rounded-[10px] border border-[var(--color-divider)] bg-[var(--color-page-soft)] px-3.5 text-[14px] text-[var(--color-ink)] outline-none transition-colors placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-primary-400)] min-[380px]:w-[176px]"
                />
                <button
                  onClick={() => { setShowSearch(false); setQuery('') }}
                  aria-label="关闭搜索"
                  className={`flex h-[40px] w-[40px] items-center justify-center rounded-[12px] transition-colors active:scale-95 ${headerActionClass}`}
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <line x1="4" y1="4" x2="12" y2="12" />
                    <line x1="12" y1="4" x2="4" y2="12" />
                  </svg>
                </button>
              </div>
            ) : (
              <>
                <button
                  onClick={() => setShowSearch(true)}
                  aria-label="搜索"
                  className={`flex h-[40px] w-[40px] items-center justify-center rounded-[12px] transition-colors active:scale-95 ${headerActionClass}`}
                >
                  <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                    <circle cx="7" cy="7" r="5" />
                    <line x1="11" y1="11" x2="15" y2="15" />
                  </svg>
                </button>
                <button
                  onClick={() => { setLinkInput(''); setShowOpenLink(true) }}
                  aria-label="打开分享链接"
                  className="flex h-[40px] w-[40px] items-center justify-center rounded-[10px] bg-[var(--color-page-soft)] text-[var(--color-text-secondary)] transition-colors active:scale-95"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                  </svg>
                </button>
                <button
                  onClick={() => setShowAnnounce(true)}
                  aria-label="公告"
                  className={`relative flex h-[40px] w-[40px] items-center justify-center rounded-[12px] transition-colors active:scale-95 ${headerActionClass}`}
                >
                  <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M8 2.5a3 3 0 0 0-3 3v.9A5.25 5.25 0 0 1 3.2 10.5L2 11.5v1.25h12v-1.25l-1.2-1a5.25 5.25 0 0 1-1.8-4.1v-.9a3 3 0 0 0-3-3Z" />
                    <path d="M6.5 14a1.5 1.5 0 0 0 3 0" />
                  </svg>
                  {/* Red dot for new announcement - TODO: connect to actual state */}
                  {false && (
                    <span className="absolute top-0 right-0 w-2 h-2 bg-[#FF4D6D] rounded-full border-2 border-[var(--color-surface)]" />
                  )}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Primary mode tabs (推荐 / 新角色 / 收藏 / 我的) — large, underline-active. */}
        <div className="relative z-20 mx-auto flex w-full max-w-[1180px] shrink-0 items-center gap-6 overflow-x-auto border-b border-black/[0.045] px-4 pb-1 pt-0.5 no-scrollbar sm:px-5">
          {DISCOVERY_MODES.map((mode) => (
            <button
              key={mode}
              onClick={() => setActiveMode(mode)}
              className={`relative shrink-0 pb-2 text-[16px] transition-colors ${
                activeMode === mode
                  ? `font-bold ${activeModeText}`
                  : `font-semibold ${inactiveModeText}`
              }`}
            >
              {mode}
              {activeMode === mode && (
                <span className="absolute bottom-0 left-1/2 h-[3px] w-[20px] -translate-x-1/2 rounded-full bg-[var(--color-primary-500)]" />
              )}
            </button>
          ))}
        </div>

        {/* Secondary tag chips (scrollable) + funnel filter button (right, fixed) */}
        <div className="relative z-30 mx-auto w-full max-w-[1180px] shrink-0 px-3 pb-2 pt-1 sm:px-4">
          <div className="flex min-h-[40px] items-center gap-1.5">
            <div className="flex-1 min-w-0 flex gap-1.5 overflow-x-auto overflow-y-hidden touch-pan-x no-scrollbar">
              {pinnedTagChips.map((tag) => (
                <button
                  key={tag}
                  onClick={() => setActiveTag(tag)}
                    className={`relative h-[32px] shrink-0 rounded-full px-3.5 text-[13px] transition-colors ${
                    activeTag === tag
                      ? 'bg-[var(--color-primary-500)] text-white font-semibold'
                      : `bg-transparent ${inactiveTagText} font-medium`
                  }`}
                >
                  {tag}
                  {activeTag === tag && (
                    <span className="sr-only">已选择</span>
                  )}
                </button>
              ))}
            </div>
            {extraFilterChips.length > 0 && (
              <button
                onClick={() => setShowFilter((v) => !v)}
                aria-label="筛选"
                className={`relative shrink-0 w-[38px] h-[38px] flex items-center justify-center transition-colors active:scale-[0.94] ${
                  showFilter || !pinnedTagChips.includes(activeTag)
                    ? 'text-[var(--color-primary)]'
                    : isDark ? 'text-[var(--color-text-secondary)]' : 'text-[rgba(58,58,74,0.66)]'
                }`}
              >
                <svg width="21" height="21" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 3.5h12l-4.6 5.2v3.4l-2.8 1.4V8.7L2 3.5Z" />
                </svg>
                {/* active-tag dot when a filtered tag is applied */}
                {!pinnedTagChips.includes(activeTag) && !showFilter && (
                  <span className="absolute top-0.5 right-0.5 w-[7px] h-[7px] rounded-full bg-[var(--color-primary)]" />
                )}
              </button>
            )}
          </div>

          {/* 更多标签 dropdown panel — anchored below the chips row (reference layout) */}
          {showFilter && (
            <>
              <button
                aria-label="关闭筛选"
                onClick={() => setShowFilter(false)}
                className="fixed inset-0 z-20 cursor-default bg-black/20"
              />
              <div className={`absolute left-0 right-0 top-full z-30 rounded-b-[16px] border-t px-4 pb-4 pt-3.5 shadow-[0_18px_40px_rgba(0,0,0,0.14)] ${filterPanelClass}`}>
                <div className="flex items-baseline justify-between gap-3 mb-3">
                  <div className="min-w-0 flex items-baseline gap-2.5">
                    <p className={`shrink-0 text-[17px] font-bold leading-none ${filterPanelTitle}`}>更多标签</p>
                    <p className={`min-w-0 text-[13px] font-semibold leading-none truncate ${filterPanelHint}`}>点击标签筛选</p>
                  </div>
                  {!pinnedTagChips.includes(activeTag) && (
                    <button
                      onClick={() => { setActiveTag(TAG_ALL); setShowFilter(false) }}
                      className="shrink-0 text-[13px] font-semibold text-[var(--color-primary-600)]"
                    >
                      重置
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-4 gap-x-2 gap-y-2 max-h-[42vh] overflow-y-auto no-scrollbar">
                  {extraFilterChips.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => { setActiveTag(tag); setShowFilter(false) }}
                      className={`min-w-0 h-[38px] px-1 rounded-[13px] text-[14px] leading-none border transition-colors truncate ${
                        activeTag === tag
                          ? 'bg-[var(--color-primary)] text-white border-transparent font-bold'
                          : `${filterChipIdle} font-semibold`
                      }`}
                      title={tag}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
        </div>

        {/* Discovery grid */}
        <div ref={gridRef} className="relative z-10 mx-auto min-h-0 w-full max-w-[1180px] flex-1 overflow-y-auto overscroll-y-contain px-3.5 pb-[120px] pt-1.5 sm:px-5">
          {/* Pull-to-refresh indicator — height tracks finger pull, snaps to a
              spinner while refreshing. */}
          {(pull > 0 || refreshing) && (
            <div
              className="flex items-center justify-center overflow-hidden text-[var(--color-text-secondary)]"
              style={{ height: refreshing ? threshold : pull, transition: refreshing ? 'height 0.2s' : undefined }}
            >
              <svg
                className={refreshing ? 'animate-spin' : ''}
                width="20" height="20" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                style={refreshing ? undefined : { transform: `rotate(${Math.min(pull / threshold, 1) * 270}deg)` }}
              >
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
            </div>
          )}
          {filtered.length === 0 ? (
            items.length === 0 ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 md:grid-cols-4 xl:grid-cols-5" aria-label="正在加载角色">
                {Array.from({ length: 10 }).map((_, index) => (
                  <div key={index} className="aspect-[3/4] animate-pulse rounded-[12px] bg-[var(--color-page-soft)]" />
                ))}
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-2 pb-20 text-center">
                <span className="text-[15px] text-[var(--color-text-secondary)]">没有找到匹配的角色</span>
              </div>
            )
          ) : (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-4 md:grid-cols-4 xl:grid-cols-5">
              {filtered.map((it) => (
                <DiscoveryCard
                  key={it.id}
                  item={it}
                  heatMap={heatMap}
                  onOpen={() => navigate(`/character/${it.id}`)}
                />
              ))}
            </div>
          )}
        </div>

        <TabBar />
      </div>

      <NoticeDialog
        open={showNotice}
        onClose={dismissNotice}
        title="温馨提示"
        actionLabel="我已满18岁，知道了"
      >
        <p className="leading-[1.6]">
          yuoyuo 是一款面向<span className="font-semibold text-[#2a2a38]">成年人</span>的 AI 情感陪伴产品，
          <span className="font-semibold text-[#2a2a38]">仅供年满 18 周岁的用户使用</span>。
        </p>
        <p className="leading-[1.6] mt-2">
          所有角色均为虚构，回复由 AI 生成。聊天时请<span className="font-semibold text-[#2a2a38]">遵守社区公约</span>，
          不得诱导生成违法或不良内容。
        </p>
        <p className="leading-[1.6] mt-2 text-[#8a8a98]">
          继续使用即表示你已阅读并同意
          <Link to="/legal/age" className="text-[var(--color-primary)]">《年满18周岁确认》</Link>。
        </p>
      </NoticeDialog>

      <AnnouncementSheet open={showAnnounce} onClose={() => setShowAnnounce(false)} />

      <Dialog
        open={showOpenLink}
        onClose={() => setShowOpenLink(false)}
        title="打开分享链接"
        actions={
          <>
            <button
              onClick={() => setShowOpenLink(false)}
              className="flex-1 h-[44px] rounded-full bg-[var(--color-glass-55)] text-[var(--color-ink)] text-[15px] font-medium active:bg-[rgba(0,0,0,0.04)]"
            >
              取消
            </button>
            <button
              onClick={handleOpenLink}
              disabled={!linkInput.trim()}
              className="flex-1 h-[44px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[15px] font-semibold disabled:opacity-50"
            >
              打开
            </button>
          </>
        }
      >
        <p className="text-left leading-[1.6] mb-3">
          粘贴好友分享的角色链接，直接在应用内打开 Ta 的档案。
        </p>
        <div className="flex items-center gap-2">
          <input
            value={linkInput}
            onChange={(e) => setLinkInput(e.target.value)}
            placeholder="粘贴角色链接"
            className="flex-1 min-w-0 h-[44px] px-3.5 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[15px] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[var(--color-primary)]"
          />
          <button
            onClick={handlePasteLink}
            className="shrink-0 h-[44px] px-4 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[14px] text-[var(--color-ink)] active:scale-[0.97] transition-transform"
          >
            粘贴
          </button>
        </div>
      </Dialog>
    </AppPageShell>
  )
}

function DiscoveryCard({
  item,
  heatMap,
  onOpen,
}: {
  item: GridItem
  heatMap: Map<string, number>
  onOpen: () => void
}) {
  const { profile, isOwner, visibility } = item
  const tags = profile.tags ?? []
  const hook = profile.tagline || profile.summary || ''
  const virtualHeat = heatMap.get(item.id)

  // Visibility badge for owned UGC characters
  const visInfo = isOwner ? VIS_BADGE[visibility ?? 'private'] ?? VIS_BADGE.private : null

  // Cover shows the character's first two tags (as authored/ordered), not a
  // priority-reordered subset — product direction 2026-08-17.
  const displayTags = tags.slice(0, 2)

  return (
    <div className="group relative flex w-full flex-col overflow-hidden rounded-[14px] border border-white/70 bg-transparent shadow-[0_5px_18px_rgba(73,48,62,0.12)] transition-shadow duration-[var(--duration-normal)] hover:shadow-[0_8px_26px_rgba(73,48,62,0.16)]">
      <button
        onClick={onOpen}
        className="relative aspect-[0.72] w-full text-left transition-opacity active:opacity-90"
        style={{ background: `linear-gradient(135deg, ${profile.tagBg}, transparent)` }}
      >
        <CoverFill cover={profile.cover} alt={profile.name} />

        {/* bottom scrim for legibility */}
        <div className="absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-black/48 via-black/18 to-transparent" />

        {/* visibility badge for owned UGC characters */}
        {visInfo && (
          <span
            className="absolute top-2 left-2 inline-flex h-[22px] items-center rounded-full px-2 text-[11px] font-medium backdrop-blur-[4px]"
            style={{ background: visInfo.bg, color: visInfo.color }}
          >
            {visInfo.label}
          </span>
        )}

        {/* name + hook + interaction data overlay */}
        <div className="absolute inset-x-0 bottom-0 space-y-1 p-2.5">
          <p className="text-[15px] font-bold leading-tight text-white line-clamp-1 text-left">{profile.name}</p>
          {hook && (
            <p className="text-[12px] leading-[1.5] text-white/95 font-medium line-clamp-2 text-left">
              {hook}
            </p>
          )}
          <div className="flex items-center justify-between gap-2 min-w-0">
            {/* Heat indicator (editorial overrides + virtual value, preserves real ranking) */}
            {virtualHeat !== undefined && (
              <div className="flex items-center gap-1 flex-shrink-0">
                <svg className="text-white/85" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2c-1.5 4-4 6-7 7 1 5 3 8 7 11 4-3 6-6 7-11-3-1-5.5-3-7-7z" />
                </svg>
                <span className="text-[11px] text-white/85 whitespace-nowrap">{formatPlays(virtualHeat)}</span>
              </div>
            )}
            {/* Tags row — show only top 2 */}
            {displayTags.length > 0 && (
              <div className="flex gap-2 min-w-0 flex-shrink">
                {displayTags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex h-[20px] max-w-[72px] items-center truncate rounded-full border border-white/20 bg-black/16 px-2 text-[11px] text-white/88"
                    title={tag}
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
      className={`absolute inset-0 w-full h-full object-cover filter brightness-[0.96] contrast-[0.92] transition-opacity duration-300 ${
        loaded ? 'opacity-100' : 'opacity-0'
      }`}
    />
  )
}
