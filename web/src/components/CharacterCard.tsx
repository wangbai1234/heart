import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useThemeStore } from '../stores/themeStore'
import { useToastStore } from '../stores/toastStore'
import { resolveCharacterProfile } from '../data/uiContent'
import { buildShareLink } from '../utils/characterShare'
import type { CharacterDTO } from '../services/api'

const VIS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  public: { label: '公开', color: '#5FC8E8', bg: 'rgba(95,200,232,0.14)' },
  unlisted: { label: '链接可见', color: '#A7C7E7', bg: 'rgba(167,199,231,0.16)' },
  private: { label: '私密', color: '#B0A8B4', bg: 'rgba(176,168,180,0.14)' },
}

interface Props {
  char: CharacterDTO
  onEdit: () => void
  onVisibility: (v: 'public' | 'unlisted' | 'private') => void
  onDisable: () => void
}

/** 自创角色卡片 + 三点菜单(编辑/可见范围/停用) */
export function CharacterCard({ char, onEdit, onVisibility, onDisable }: Props) {
  const profile = resolveCharacterProfile(char.id, char.display_name, char.avatar_url, {
    isOwner: char.is_owner && !char.is_builtin,
    coverUrl: char.cover_url,
    tags: char.tags,
  })
  const vis = VIS_LABELS[char.visibility] ?? VIS_LABELS.private
  const [menuOpen, setMenuOpen] = useState(false)
  const [visMenuOpen, setVisMenuOpen] = useState(false)
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const showToast = useToastStore((s) => s.show)

  // Sharing only makes sense for link-reachable visibilities. A private
  // character 404s for anyone but the owner, so we don't offer a link for it.
  const shareable = char.visibility === 'public' || char.visibility === 'unlisted'
  const approved = char.review_status === 'approved'

  async function handleCopyLink() {
    const url = buildShareLink(char.id)
    try {
      await navigator.clipboard.writeText(url)
      showToast(
        approved ? '链接已复制，分享给好友即可访问' : '链接已复制，审核通过后好友即可访问',
        'success',
      )
    } catch {
      // clipboard API unavailable (non-secure context / older webview)
      showToast(url, 'info')
    }
  }

  return (
    <div
      className={`relative backdrop-blur-[18px] rounded-[20px] shadow-[0_4px_16px_rgba(255,183,197,0.10)] overflow-visible ${
        menuOpen ? 'z-50' : ''
      } ${
        isDark
          ? 'bg-[var(--color-surface-card)] border border-[var(--color-border-subtle)]'
          : 'bg-[rgba(255,255,255,0.78)] border border-[rgba(255,255,255,0.65)]'
      }`}
    >
      <div className="flex items-center gap-4 px-5 py-4">
        <div className="w-[52px] h-[52px] rounded-full overflow-hidden border-[2px] border-[rgba(255,255,255,0.85)] shadow-[0_2px_8px_rgba(255,183,197,0.20)] shrink-0 bg-gradient-to-br from-[#FFB7C5] to-[#C8B6FF] flex items-center justify-center">
          <img
            src={profile.avatar}
            alt={char.display_name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-[16px] font-semibold text-[var(--color-ink)] truncate">{char.display_name}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] font-medium rounded-full px-2.5 py-[3px]" style={{ color: vis.color, background: vis.bg }}>
              {vis.label}
            </span>
          </div>
        </div>

        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="w-[36px] h-[36px] flex items-center justify-center rounded-full active:bg-[rgba(255,183,197,0.15)] transition-colors shrink-0"
          aria-label="更多操作"
        >
          <svg width="4" height="18" viewBox="0 0 4 18" fill="var(--color-text-muted)">
            <circle cx="2" cy="2" r="2" />
            <circle cx="2" cy="9" r="2" />
            <circle cx="2" cy="16" r="2" />
          </svg>
        </button>
      </div>

      {menuOpen &&
        createPortal(
          <>
            <div className="fixed inset-0 z-[100]" onClick={() => { setMenuOpen(false); setVisMenuOpen(false) }} />
            <div
              className={`fixed right-4 top-[62px] z-[101] backdrop-blur-[16px] rounded-[14px] shadow-[0_8px_24px_rgba(0,0,0,0.10)] overflow-hidden min-w-[160px] ${
                isDark
                  ? 'bg-[var(--color-surface-card)] border border-[var(--color-border-subtle)]'
                  : 'bg-white/90 border border-[rgba(255,255,255,0.70)]'
              }`}
            >
              <MenuButton label="编辑角色" icon={<EditIcon />} onClick={() => { setMenuOpen(false); onEdit() }} />
              {shareable && (
                <>
                  <div className="h-px bg-[var(--color-divider)]" />
                  <MenuButton
                    label="复制分享链接"
                    icon={<LinkIcon />}
                    onClick={() => { setMenuOpen(false); setVisMenuOpen(false); void handleCopyLink() }}
                  />
                </>
              )}
              <div className="h-px bg-[var(--color-divider)]" />
              <MenuButton label="可见范围" icon={<EyeIcon />} onClick={() => setVisMenuOpen((v) => !v)} chevron />
              {visMenuOpen && (
                <div
                  className={`border-t border-[var(--color-divider)] ${
                    isDark ? 'bg-[var(--color-surface)]' : 'bg-[rgba(255,248,243,0.95)]'
                  }`}
                >
                  {(['private', 'unlisted', 'public'] as const).map((v) => {
                    const info = VIS_LABELS[v]
                    return (
                      <MenuButton
                        key={v}
                        label={info.label}
                        icon={
                          <span
                            className="w-5 h-5 inline-block rounded-full"
                            style={{ background: info.bg, border: `1.5px solid ${info.color}` }}
                          />
                        }
                        onClick={() => {
                          setMenuOpen(false)
                          setVisMenuOpen(false)
                          onVisibility(v)
                        }}
                        active={char.visibility === v}
                      />
                    )
                  })}
                </div>
              )}
              <div className="h-px bg-[var(--color-divider)]" />
              <MenuButton label="停用角色" icon={<DisableIcon />} danger onClick={() => { setMenuOpen(false); onDisable() }} />
            </div>
          </>,
          document.body
        )}
    </div>
  )
}

function MenuButton({
  label,
  icon,
  onClick,
  danger,
  chevron,
  active,
  disabled,
}: {
  label: string
  icon: React.ReactNode
  onClick: () => void
  danger?: boolean
  chevron?: boolean
  active?: boolean
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 text-[14px] font-medium transition-colors ${
        disabled ? 'opacity-45' : 'active:bg-[rgba(255,183,197,0.12)]'
      } ${danger ? 'text-[var(--color-error)]' : 'text-[var(--color-ink)]'}`}
    >
      <span className="w-5 flex-shrink-0">{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {disabled && <span className="text-[10px] text-[var(--color-text-muted)] font-normal">暂未开放</span>}
      {active && (
        <svg width="12" height="9" viewBox="0 0 12 9" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="1,4.5 4.5,8 11,1" />
        </svg>
      )}
      {chevron && !active && (
        <svg width="6" height="10" viewBox="0 0 6 10" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="1,1 5,5 1,9" />
        </svg>
      )}
    </button>
  )
}

function EditIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function LinkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  )
}

function DisableIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
    </svg>
  )
}

