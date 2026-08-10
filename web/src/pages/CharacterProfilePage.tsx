import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { CharacterProfileDTO } from '../services/api'
import { useCharactersStore } from '../stores/charactersStore'
import { useCompanionsStore } from '../stores/companionsStore'
import { useAppStore } from '../stores/appStore'
import { useFavoritesStore } from '../stores/favoritesStore'
import { useToastStore } from '../stores/toastStore'
import { DEFAULT_COVER } from '../data/uiContent'
import { stageWithIntimacy, isColdWar, intimacyPercent, stageLabel, stageOrderIndex } from '../utils/relationship'
import { buildShareLink } from '../utils/characterShare'
import { useSafeBack } from '../hooks/useSafeBack'

/** 关系路线的 6 个可视节点（ACQUAINTANCE/FRIEND 合归「靠近」）。 */
const ROUTE_NODES = ['STRANGER', 'FRIEND', 'CONFIDANT', 'ROMANTIC_INTEREST', 'LOVER', 'BONDED'] as const
const ROUTE_HINT: Record<string, string> = {
  STRANGER: '第一次照面，你还只是个陌生人',
  FRIEND: '话变多了，Ta开始留意你的情绪',
  CONFIDANT: '有些话，Ta只想说给你听',
  ROMANTIC_INTEREST: '心跳藏不住了，关系差一步',
  LOVER: '你成了Ta生活里绕不开的人',
  BONDED: '再没有谁能替代此刻的彼此',
}

type Theme = { accent: string; deep: string; deep2: string; hero: string }
/** 按角色标签选主题：暗金(危险/病娇) / 酒玫瑰(强势/占有) / 樱粉(默认治愈)。 */
function pickTheme(tags: string[]): Theme {
  const s = tags.join(' ')
  if (/病娇|悬疑|危险|黑暗|禁忌|救赎|执念|偏执/.test(s))
    return { accent: '#B08A4F', deep: '#1b1420', deep2: '#0e0a11', hero: '#EDE3D4' }
  if (/霸总|占有|强势|追妻|热恋|独占|野性|禁欲/.test(s))
    return { accent: '#C9506A', deep: '#271521', deep2: '#150a0f', hero: '#F0DCE0' }
  return { accent: '#FF8FAB', deep: '#2a2029', deep2: '#191320', hero: '#F3E4EA' }
}

/**
 * 角色档案页 (Nimoo-style rich profile) at /character/:id.
 *
 * Full-bleed cover → 关于TA (tagline + tag chips + intimacy + gradient「和Ta聊天」)
 * → scroll into 叙引 card (archetype badge · name · accented one-liner · intro ·
 * personality axes). Per product direction: NO 评论 / 脉络 tabs. A share button
 * (top-right of the cover) copies the profile link for link-reachable
 * characters (public / unlisted+approved), so 「链接可见」 can actually spread.
 *
 * All copy comes from the public profile API, which deliberately never exposes
 * internal persona (core_wound / core_fear …). Missing fields degrade to
 * empty and simply don't render.
 */
export function CharacterProfilePage() {
  const navigate = useNavigate()
  const goBack = useSafeBack('/character')
  const { id = '' } = useParams<{ id: string }>()
  const setCharacter = useAppStore((s) => s.setCharacter)
  const companions = useCompanionsStore((s) => s.companions)
  const loadCompanions = useCompanionsStore((s) => s.load)
  const loadProfile = useCharactersStore((s) => s.loadProfile)
  const storeCharacters = useCharactersStore((s) => s.characters)
  const showToast = useToastStore((s) => s.show)
  const { toggle: toggleFavorite, has: isFavorite } = useFavoritesStore()

  // Seed synchronously from the store cache so a re-entry paints instantly with
  // no spinner (system covers/copy never change). A cold entry starts null and
  // fetches below.
  const [profile, setProfile] = useState<CharacterProfileDTO | null>(
    () => useCharactersStore.getState().profileById[id] ?? null,
  )
  const [error, setError] = useState(false)
  const [aboutExpanded, setAboutExpanded] = useState(false)

  useEffect(() => {
    void loadCompanions()
  }, [loadCompanions])

  useEffect(() => {
    let alive = true
    const cached = useCharactersStore.getState().profileById[id]
    // Show cache immediately (or blank for a cold id); never flash a spinner
    // over already-good data.
    setProfile(cached ?? null)
    setError(false)
    loadProfile(id)
      .then((p) => {
        if (alive && p) setProfile(p)
        else if (alive && !p && !cached) setError(true)
      })
    return () => {
      alive = false
    }
  }, [id, loadProfile])

  const companion = useMemo(
    () => companions.find((c) => c.character_id === id),
    [companions, id],
  )
  const chatted = !!companion && companion.companion_status !== 'locked'

  const theme = useMemo(() => pickTheme(profile?.tags ?? []), [profile?.tags])

  // Cover-less characters fall back to the shared background image (product
  // direction 2026-07-25) rather than a blurred avatar placeholder.
  const cover = profile?.cover_url || DEFAULT_COVER

  const openChat = () => {
    setCharacter(id)
    navigate(`/chat/${id}`)
  }

  // Shareability: a private character 404s for anyone but its owner, so never
  // offer a link for one. We only *know* the visibility for characters in the
  // caller's own catalog (own UGC + public). A character reached purely by link
  // that isn't in the store must be public/unlisted+approved to have loaded at
  // all — so default to shareable when the store has no row for it.
  const storeChar = useMemo(
    () => storeCharacters.find((c) => c.id === id),
    [storeCharacters, id],
  )
  const shareable = !storeChar || storeChar.visibility !== 'private'
  const approved = !storeChar || storeChar.is_builtin || storeChar.review_status === 'approved'

  async function handleShare() {
    const url = buildShareLink(id)
    try {
      await navigator.clipboard.writeText(url)
      showToast(
        approved ? '链接已复制，分享给好友即可访问' : '链接已复制，审核通过后好友即可访问',
        'success',
      )
    } catch {
      showToast(url, 'info')
    }
  }

  if (error) {
    return (
      <div className="relative w-full h-full flex flex-col items-center justify-center gap-3 bg-[var(--color-bg-page)]">
        <span className="text-[15px] text-[var(--color-text-secondary)]">角色不存在或已下架</span>
        <button
          onClick={() => navigate('/character')}
          className="h-[38px] px-5 rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[14px] text-[var(--color-ink)]"
        >
          返回
        </button>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full overflow-y-auto bg-[var(--color-bg-page)]">
      {/* ── Full-bleed cover ── */}
      <div className="relative w-full h-[62vh] min-h-[380px] overflow-hidden">
        <img src={cover} alt={profile?.display_name ?? ''} className="absolute inset-0 w-full h-full object-cover" />
        {/* bottom fade into the sheet below */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)]/40 to-transparent" />

        {/* back + share buttons */}
        <div className="absolute left-0 top-0 z-10" style={{ height: 'var(--safe-top)' }} />
        <button
          onClick={goBack}
          aria-label="返回"
          className="absolute left-4 z-10 w-[38px] h-[38px] rounded-full bg-black/30 backdrop-blur-[8px] flex items-center justify-center active:scale-[0.95] transition-transform"
          style={{ top: 'calc(var(--safe-top) + 8px)' }}
        >
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        {/* Share button — only for link-reachable characters (never private). */}
        {profile && shareable && (
          <button
            onClick={handleShare}
            aria-label="分享角色"
            className="absolute right-4 z-10 w-[38px] h-[38px] rounded-full bg-black/30 backdrop-blur-[8px] flex items-center justify-center active:scale-[0.95] transition-transform"
            style={{ top: 'calc(var(--safe-top) + 8px)' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
          </button>
        )}
      </div>

      {/* ── 关于TA ── */}
      <div className="relative -mt-14 px-5 pb-4">
        <h1 className="text-[26px] font-bold text-[var(--color-ink)] leading-tight">
          {profile?.display_name ?? '　'}
        </h1>
        {profile?.creator_name && (
          <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">by @{profile.creator_name}</p>
        )}

        {profile?.age_range && (
          <span className="mt-2 inline-flex h-[24px] items-center rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] px-3 text-[12px] font-medium text-[var(--color-text-secondary)] tabular-nums">
            {profile.age_range} 岁
          </span>
        )}

        {profile?.tagline && (
          <p className="mt-3 text-[15px] leading-relaxed text-[var(--color-text-secondary)]">{profile.tagline}</p>
        )}

        {profile && profile.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {profile.tags.map((t) => (
              <span
                key={t}
                className="h-[26px] px-3 inline-flex items-center rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[12px] text-[var(--color-text-secondary)]"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {/* 关于TA card — truncated intro */}
        {profile && (profile.tagline || profile.intro) && (
          <div className="mt-5 rounded-[20px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] p-4">
            <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: theme.accent }}>
              <span className="inline-block w-[3px] h-[14px] rounded-full" style={{ background: theme.accent }} />
              关于TA
            </div>
            {profile.tagline && (
              <p className="mt-3 text-[15px] leading-relaxed text-[var(--color-ink)]">{profile.tagline}</p>
            )}
            {profile.intro && (
              <>
                <p
                  className={`mt-3 text-[14px] leading-relaxed text-[var(--color-text-secondary)] whitespace-pre-wrap ${
                    !aboutExpanded && 'line-clamp-4'
                  }`}
                >
                  {profile.intro}
                </p>
                {profile.intro.length > 120 && (
                  <button
                    onClick={() => setAboutExpanded((p) => !p)}
                    className="mt-2 text-[13px] font-medium active:scale-[0.96] transition-transform"
                    style={{ color: theme.accent }}
                  >
                    {aboutExpanded ? '收起' : '更多'}
                  </button>
                )}
              </>
            )}
          </div>
        )}

        {/* intimacy + chat CTA */}
        <div className="mt-5 flex items-center gap-3">
          {chatted && (
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between text-[12px] text-[var(--color-text-secondary)]">
                <span>
                  {isColdWar(companion!.relationship_stage)
                    ? '闹别扭'
                    : stageWithIntimacy(companion!.relationship_stage, companion!.intimacy)}
                </span>
              </div>
              <div className="mt-1.5 h-[6px] w-full rounded-full bg-[var(--color-glass-55)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--color-primary)]"
                  style={{ width: `${intimacyPercent(companion!.intimacy)}%` }}
                />
              </div>
            </div>
          )}
          {/* Favorite button — heart icon, left of 开始聊天 */}
          <button
            onClick={() => toggleFavorite(id)}
            className="shrink-0 w-[48px] h-[48px] rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] flex items-center justify-center active:scale-[0.96] transition-transform"
            aria-label={isFavorite(id) ? '取消收藏' : '收藏'}
          >
            {isFavorite(id) ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="#FF6B9D" stroke="#FF6B9D" strokeWidth="1.5">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
            )}
          </button>
          <button
            onClick={openChat}
            className={`h-[48px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform ${
              chatted ? 'px-7' : 'flex-1'
            }`}
          >
            开始聊天
          </button>
        </div>

        {/* 关系路线 timeline — 6 nodes with current stage highlighted */}
        {chatted && companion && !isColdWar(companion.relationship_stage) && (
          <div className="mt-5 rounded-[20px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] p-4">
            <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: theme.accent }}>
              <span className="inline-block w-[3px] h-[14px] rounded-full" style={{ background: theme.accent }} />
              关系路线
            </div>
            <div className="mt-4 relative">
              {/* Progress connector line */}
              <div className="absolute top-[18px] left-[18px] right-[18px] h-[2px] bg-[var(--color-glass-55)]">
                <div
                  className="h-full transition-[width] duration-300"
                  style={{
                    width: `${(Math.max(0, stageOrderIndex(companion.relationship_stage)) / (ROUTE_NODES.length - 1)) * 100}%`,
                    background: theme.accent,
                  }}
                />
              </div>
              {/* Stage nodes */}
              <div className="relative flex justify-between">
                {ROUTE_NODES.map((stage, idx) => {
                  const reached = stageOrderIndex(companion.relationship_stage) >= idx
                  const isCurrent = companion.relationship_stage === stage || (stage === 'FRIEND' && companion.relationship_stage === 'ACQUAINTANCE')
                  return (
                    <div key={stage} className="flex flex-col items-center w-[60px]">
                      <div
                        className={`w-[36px] h-[36px] rounded-full flex items-center justify-center text-[13px] font-semibold transition-[background,color,box-shadow] duration-300 ${
                          isCurrent ? 'shadow-[0_0_12px_rgba(255,255,255,0.3)]' : ''
                        }`}
                        style={{
                          background: reached ? theme.accent : 'var(--color-glass-55)',
                          color: reached ? '#fff' : 'var(--color-text-muted)',
                        }}
                      >
                        {idx + 1}
                      </div>
                      <span className="mt-2 text-[12px] text-center leading-tight text-[var(--color-text-secondary)]">
                        {stageLabel(stage)}
                      </span>
                      {isCurrent && (
                        <span className="mt-1 text-[11px] text-center text-[var(--color-text-muted)] leading-snug">
                          {ROUTE_HINT[stage]}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── 叙引 dossier card (premium dark) ── */}
      {profile && (profile.one_liner || profile.archetype_label || profile.age_range || profile.personality.length > 0) && (
        <div
          className="mx-4 mb-4 rounded-[22px] border p-6 relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${theme.deep} 0%, ${theme.deep2} 100%)`,
            borderColor: theme.accent + '40',
          }}
        >
          {/* 叙引 header */}
          <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: theme.accent }}>
            <span className="inline-block w-[3px] h-[14px] rounded-full" style={{ background: theme.accent }} />
            叙引
          </div>

          {/* Hero one-liner */}
          {profile.one_liner && (
            <div className="mt-5 flex gap-3">
              <span
                className="mt-1 shrink-0 w-[3px] self-stretch rounded-full"
                style={{ background: `linear-gradient(to bottom, ${theme.accent}, ${theme.accent}80)` }}
              />
              <p
                className="text-[18px] leading-relaxed font-serif"
                style={{ color: theme.hero, fontFamily: '"Songti SC", "Noto Serif SC", serif' }}
              >
                {profile.one_liner}
              </p>
            </div>
          )}

          {/* Identity namecard */}
          {(profile.archetype_label || profile.age_range || profile.tags.length > 0) && (
            <div className="mt-5 rounded-[16px] bg-white/5 border border-white/10 p-4">
              <div className="text-[12px] font-medium mb-3" style={{ color: theme.accent }}>
                身份档案
              </div>
              <div className="flex flex-wrap gap-2">
                {profile.archetype_label && (
                  <span
                    className="inline-flex h-[26px] items-center rounded-full px-3 text-[12px] font-medium"
                    style={{ background: theme.accent + '20', color: theme.accent }}
                  >
                    {profile.archetype_label}
                  </span>
                )}
                {profile.age_range && (
                  <span
                    className="inline-flex h-[26px] items-center rounded-full px-3 text-[12px] font-medium tabular-nums"
                    style={{ background: 'rgba(255,255,255,0.08)', color: '#D4C7BA' }}
                  >
                    {profile.age_range} 岁
                  </span>
                )}
                {profile.tags.slice(0, 3).map((t) => (
                  <span
                    key={t}
                    className="inline-flex h-[26px] items-center rounded-full px-3 text-[12px]"
                    style={{ background: 'rgba(255,255,255,0.08)', color: '#D4C7BA' }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Personality axes */}
          {profile.personality.length > 0 && (
            <div className="mt-5 flex flex-col gap-3">
              {profile.personality.map((axis) => (
                <div key={axis.label}>
                  <div className="flex items-center justify-between text-[13px]" style={{ color: '#B9A99A' }}>
                    <span>{axis.label}</span>
                    {axis.value != null && <span style={{ color: '#7A6F60' }}>{Math.round(axis.value * 100)}%</span>}
                  </div>
                  {axis.value != null && (
                    <div className="mt-1.5 h-[6px] w-full rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-[width] duration-300"
                        style={{ width: `${Math.round(axis.value * 100)}%`, background: theme.accent }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}


      <div style={{ height: 'var(--safe-bottom)' }} />
    </div>
  )
}
