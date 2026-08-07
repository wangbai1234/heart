import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { CharacterProfileDTO } from '../services/api'
import { useCharactersStore } from '../stores/charactersStore'
import { useCompanionsStore } from '../stores/companionsStore'
import { useAppStore } from '../stores/appStore'
import { useFavoritesStore } from '../stores/favoritesStore'
import { DEFAULT_COVER } from '../data/uiContent'
import { stageWithIntimacy, isColdWar, intimacyPercent } from '../utils/relationship'
import { useSafeBack } from '../hooks/useSafeBack'

/**
 * 角色档案页 (Nimoo-style rich profile) at /character/:id.
 *
 * Full-bleed cover → 关于TA (tagline + tag chips + intimacy + gradient「和Ta聊天」)
 * → scroll into 叙引 card (archetype badge · name · accented one-liner · intro ·
 * personality axes). Per product direction: NO 评论 / 脉络 tabs, NO share button.
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
  const { toggle: toggleFavorite, has: isFavorite } = useFavoritesStore()

  // Seed synchronously from the store cache so a re-entry paints instantly with
  // no spinner (system covers/copy never change). A cold entry starts null and
  // fetches below.
  const [profile, setProfile] = useState<CharacterProfileDTO | null>(
    () => useCharactersStore.getState().profileById[id] ?? null,
  )
  const [error, setError] = useState(false)

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

  // Cover-less characters fall back to the shared background image (product
  // direction 2026-07-25) rather than a blurred avatar placeholder.
  const cover = profile?.cover_url || DEFAULT_COVER

  const openChat = () => {
    setCharacter(id)
    navigate(`/chat/${id}`)
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

        {/* back button (no share button, by design) */}
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
      </div>

      {/* ── 叙引 detail card ── */}
      {profile && (profile.archetype_label || profile.one_liner || profile.intro || profile.personality.length > 0) && (
        <div className="mx-4 mb-4 rounded-[22px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] p-5">
          <div className="flex items-center gap-2 text-[13px] font-medium text-[var(--color-primary)]">
            <span className="inline-block w-[3px] h-[14px] rounded-full bg-[var(--color-primary)]" />
            叙引
          </div>

          {profile.archetype_label && (
            <span className="mt-3 inline-flex h-[24px] items-center rounded-full bg-[var(--color-primary)]/10 px-3 text-[12px] font-medium text-[var(--color-primary)]">
              {profile.archetype_label}
            </span>
          )}

          <h2 className="mt-3 text-[22px] font-bold text-[var(--color-ink)] leading-tight">
            {profile.display_name}
          </h2>

          {profile.one_liner && (
            <div className="mt-3 flex gap-3">
              <span className="mt-1 shrink-0 w-[3px] self-stretch rounded-full bg-gradient-to-b from-[#FF7EB3] to-[#9F7AEA]" />
              <p className="text-[16px] font-medium text-[var(--color-ink)] leading-relaxed">{profile.one_liner}</p>
            </div>
          )}

          {profile.intro && (
            <p className="mt-4 text-[14px] leading-relaxed text-[var(--color-text-secondary)] whitespace-pre-wrap">
              {profile.intro}
            </p>
          )}

          {profile.personality.length > 0 && (
            <div className="mt-5 flex flex-col gap-3">
              {profile.personality.map((axis) => (
                <div key={axis.label}>
                  <div className="flex items-center justify-between text-[13px] text-[var(--color-text-secondary)]">
                    <span>{axis.label}</span>
                    {axis.value != null && <span className="text-[var(--color-text-muted)]">{Math.round(axis.value * 100)}%</span>}
                  </div>
                  {axis.value != null && (
                    <div className="mt-1 h-[6px] w-full rounded-full bg-[var(--color-glass-55)] overflow-hidden">
                      <div className="h-full rounded-full bg-[var(--color-primary)]" style={{ width: `${Math.round(axis.value * 100)}%` }} />
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
