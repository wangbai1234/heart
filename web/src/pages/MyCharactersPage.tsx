import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCharactersStore } from '../stores/charactersStore'
import { useToastStore } from '../stores/toastStore'
import { resolveCharacterProfile } from '../data/uiContent'

function useToast() {
  return useToastStore((s) => s.show)
}
import { ApiError, type CharacterDTO } from '../services/api'
import { Dialog } from '../components/ui/Dialog'

// ── Visibility label helpers ────────────────────────────────────────

const VIS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  public:   { label: '公开',   color: '#5FC8E8', bg: 'rgba(95,200,232,0.14)' },
  unlisted: { label: '链接可见', color: '#A7C7E7', bg: 'rgba(167,199,231,0.16)' },
  private:  { label: '私密',   color: '#B0A8B4', bg: 'rgba(176,168,180,0.14)' },
}

// ── CharacterCard ───────────────────────────────────────────────────

interface CharacterCardProps {
  char: CharacterDTO
  onEdit: () => void
  onVisibility: (v: 'public' | 'unlisted' | 'private') => void
  onDisable: () => void
}

function CharacterCard({ char, onEdit, onVisibility, onDisable }: CharacterCardProps) {
  const profile = resolveCharacterProfile(char.id, char.display_name)
  const vis = VIS_LABELS[char.visibility] ?? VIS_LABELS.private
  const [menuOpen, setMenuOpen] = useState(false)
  const [visMenuOpen, setVisMenuOpen] = useState(false)

  return (
    <div className="relative bg-[rgba(255,255,255,0.78)] backdrop-blur-[18px] rounded-[20px] border border-[rgba(255,255,255,0.65)] shadow-[0_4px_16px_rgba(255,183,197,0.10)] overflow-visible">
      <div className="flex items-center gap-4 px-5 py-4">
        {/* Avatar */}
        <div className="w-[52px] h-[52px] rounded-full overflow-hidden border-[2px] border-[rgba(255,255,255,0.85)] shadow-[0_2px_8px_rgba(255,183,197,0.20)] shrink-0">
          <img
            src={profile.avatar}
            alt={char.display_name}
            className="w-full h-full object-cover"
            onError={(e) => {
              // fallback gradient placeholder
              const el = e.currentTarget
              el.style.display = 'none'
            }}
          />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-[16px] font-semibold text-[var(--color-ink)] truncate">{char.display_name}</p>
          <div className="flex items-center gap-2 mt-1">
            <span
              className="text-[11px] font-medium rounded-full px-2.5 py-[3px]"
              style={{ color: vis.color, background: vis.bg }}
            >
              {vis.label}
            </span>
          </div>
        </div>

        {/* Menu trigger */}
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

      {/* Action menu (absolute dropdown) */}
      {menuOpen && (
        <>
          {/* backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => { setMenuOpen(false); setVisMenuOpen(false) }}
          />
          <div className="absolute right-4 top-[62px] z-50 bg-white/90 backdrop-blur-[16px] rounded-[14px] border border-[rgba(255,255,255,0.70)] shadow-[0_8px_24px_rgba(0,0,0,0.10)] overflow-hidden min-w-[160px]">
            <MenuButton
              label="编辑角色"
              icon={<EditIcon />}
              onClick={() => { setMenuOpen(false); onEdit() }}
            />
            <div className="h-px bg-[var(--color-divider)]" />
            <MenuButton
              label="可见范围"
              icon={<EyeIcon />}
              onClick={() => setVisMenuOpen((v) => !v)}
              chevron
            />
            {visMenuOpen && (
              <div className="bg-[rgba(255,248,243,0.95)] border-t border-[var(--color-divider)]">
                {(['private', 'unlisted', 'public'] as const).map((v) => {
                  const info = VIS_LABELS[v]
                  return (
                    <MenuButton
                      key={v}
                      label={info.label}
                      icon={<span className="w-5 h-5 inline-block rounded-full" style={{ background: info.bg, border: `1.5px solid ${info.color}` }} />}
                      onClick={() => { setMenuOpen(false); setVisMenuOpen(false); onVisibility(v) }}
                      active={char.visibility === v}
                    />
                  )
                })}
              </div>
            )}
            <div className="h-px bg-[var(--color-divider)]" />
            <MenuButton
              label="停用角色"
              icon={<DisableIcon />}
              danger
              onClick={() => { setMenuOpen(false); onDisable() }}
            />
          </div>
        </>
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
}: {
  label: string
  icon: React.ReactNode
  onClick: () => void
  danger?: boolean
  chevron?: boolean
  active?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 text-[14px] font-medium active:bg-[rgba(255,183,197,0.12)] transition-colors ${
        danger ? 'text-[var(--color-error)]' : 'text-[var(--color-ink)]'
      }`}
    >
      <span className="w-5 flex-shrink-0">{icon}</span>
      <span className="flex-1 text-left">{label}</span>
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

// ── Main page ───────────────────────────────────────────────────────

export function MyCharactersPage() {
  const navigate = useNavigate()
  const { characters, loaded, load, setVisibility, disableCharacter } = useCharactersStore()
  const showToast = useToast()

  const [disableTarget, setDisableTarget] = useState<CharacterDTO | null>(null)
  const [disabling, setDisabling] = useState(false)

  useEffect(() => {
    if (!loaded) void load()
  }, [loaded, load])

  const myChars = characters.filter((c) => c.is_owner && !c.is_builtin)

  async function handleVisibility(id: string, vis: 'public' | 'unlisted' | 'private') {
    try {
      await setVisibility(id, vis)
      showToast(`可见范围已更新为「${VIS_LABELS[vis].label}」`, 'success')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '操作失败，请稍后再试'
      showToast(msg, 'error')
    }
  }

  async function handleDisable() {
    if (!disableTarget) return
    setDisabling(true)
    try {
      await disableCharacter(disableTarget.id)
      showToast(`「${disableTarget.display_name}」已停用`, 'success')
      setDisableTarget(null)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '操作失败，请稍后再试'
      showToast(msg, 'error')
    } finally {
      setDisabling(false)
    }
  }

  return (
    <div
      className="relative w-full min-h-full flex flex-col"
      style={{ background: 'linear-gradient(160deg, #FFF0F3 0%, #FFF8F3 40%, #F7F0FF 100%)' }}
    >
      {/* Ambient glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[280px] h-[180px] rounded-full bg-[rgba(255,183,197,0.18)] blur-[60px] pointer-events-none" />

      {/* Safe area */}
      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      {/* Nav bar */}
      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="w-[44px] h-[44px] flex items-center justify-center rounded-full active:bg-[rgba(255,183,197,0.15)] transition-colors"
        >
          <svg width="11" height="19" viewBox="0 0 11 19" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9,2 2,9.5 9,17" />
          </svg>
        </button>
        <span className="text-[17px] font-semibold text-[var(--color-ink)]">我的角色</span>
        <div className="w-[44px]" />
      </nav>

      {/* Content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-[120px] pt-2">
        {myChars.length === 0 ? (
          <EmptyState onCreateClick={() => navigate('/characters/new')} />
        ) : (
          <>
            {/* Character count hint */}
            <p className="text-[13px] text-[var(--color-text-muted)] px-1 mb-4 mt-2">
              {myChars.length} / 5 个角色
            </p>

            <div className="flex flex-col gap-3">
              {myChars.map((char) => (
                <CharacterCard
                  key={char.id}
                  char={char}
                  onEdit={() => navigate(`/characters/new?edit=${char.id}`)}
                  onVisibility={(v) => handleVisibility(char.id, v)}
                  onDisable={() => setDisableTarget(char)}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Bottom create button */}
      {myChars.length < 5 && (
        <div
          className="fixed bottom-0 left-0 right-0 z-30 px-4 pt-3"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 34px), 20px)' }}
        >
          <div className="bg-[rgba(255,255,255,0.82)] backdrop-blur-[20px] rounded-[20px] border border-[rgba(255,255,255,0.70)] shadow-[0_-4px_20px_rgba(255,183,197,0.12)] px-4 py-3">
            <button
              onClick={() => navigate('/characters/new')}
              className="w-full h-[52px] rounded-[14px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[17px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform"
            >
              + 创建新角色
            </button>
          </div>
        </div>
      )}

      {/* Disable confirm dialog */}
      <Dialog
        open={disableTarget !== null}
        onClose={() => setDisableTarget(null)}
        title={`停用「${disableTarget?.display_name ?? ''}」？`}
      >
        <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
          停用后该角色将从列表中隐藏，聊天记录保留。你可以在账号设置中重新启用。
        </p>
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => setDisableTarget(null)}
            className="flex-1 h-[44px] rounded-full bg-[rgba(255,255,255,0.75)] text-[var(--color-ink)] text-[15px] font-medium active:bg-[rgba(0,0,0,0.04)]"
          >
            取消
          </button>
          <button
            onClick={handleDisable}
            disabled={disabling}
            className="flex-1 h-[44px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[15px] font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {disabling ? (
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : '确认停用'}
          </button>
        </div>
      </Dialog>
    </div>
  )
}

// ── Empty state ────────────────────────────────────────────────────

function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center pt-20 pb-12 px-6 text-center">
      {/* Illustration bubble */}
      <div className="w-[88px] h-[88px] rounded-full bg-gradient-to-br from-[rgba(255,183,197,0.28)] to-[rgba(200,182,255,0.20)] border border-[rgba(255,255,255,0.70)] shadow-[0_8px_24px_rgba(255,183,197,0.18)] flex items-center justify-center mb-6">
        <span className="text-[40px]">✨</span>
      </div>
      <h2 className="text-[20px] font-semibold text-[var(--color-ink)] mb-2">还没有自创角色</h2>
      <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.65] mb-8 max-w-[260px]">
        创建属于你的专属伴侣，设计她的名字、性格与说话方式。
      </p>
      <button
        onClick={onCreateClick}
        className="h-[50px] px-8 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform"
      >
        立刻创建
      </button>
    </div>
  )
}

// ── Icons ──────────────────────────────────────────────────────────

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

function DisableIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
    </svg>
  )
}
