import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useCharactersStore } from '../stores/charactersStore'
import { useToastStore } from '../stores/toastStore'
import { useScrollRestore } from '../hooks/useScrollRestore'
import { TabBar } from '../components/ui/TabBar'
import { Dialog } from '../components/ui/Dialog'
import { CharacterCard } from '../components/CharacterCard'
import { ApiError, type CharacterDTO } from '../services/api'

function useToast() {
  return useToastStore((s) => s.show)
}

/**
 * 创作中心页 — the primary entry for character creation + user-created character
 * management (moved from /my-characters, which was secondary UI). The center tab
 * now deep-links here.
 *
 * Structure: 顶部大号「+ 创建新角色」主 CTA，下方「我的创造 (n/5)」列表 +
 * 编辑/可见范围/停用菜单，空态兜底。(2026-07-31 product direction: put creator
 * actions front-and-center as we prepare to ship publishing features.)
 */
export function CreateHubPage() {
  const navigate = useNavigate()
  const { characters, loaded, load, setVisibility, disableCharacter } = useCharactersStore()
  const showToast = useToast()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const scrollRef = useScrollRestore()
  const [disableTarget, setDisableTarget] = useState<CharacterDTO | null>(null)
  const [disabling, setDisabling] = useState(false)

  useEffect(() => {
    if (!loaded) void load()
  }, [loaded, load])

  const myChars = characters.filter((c) => c.is_owner && !c.is_builtin)
  const atLimit = myChars.length >= 5

  async function handleVisibility(id: string, vis: 'public' | 'unlisted' | 'private') {
    try {
      await setVisibility(id, vis)
      if (vis === 'public' || vis === 'unlisted') {
        const label = vis === 'public' ? '公开' : '链接可见'
        showToast(`已提交审核，通过后将以「${label}」展示`, 'success')
      } else {
        showToast('可见范围已更新为「私密」', 'success')
      }
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
      style={{ background: isDark ? 'var(--color-bg-page)' : 'linear-gradient(160deg, #FFF0F3 0%, #FFF8F3 40%, #F7F0FF 100%)' }}
    >
      <div className={`absolute top-0 left-1/2 -translate-x-1/2 w-[280px] h-[180px] rounded-full blur-[60px] pointer-events-none ${isDark ? 'bg-[rgba(255,183,197,0.06)]' : 'bg-[rgba(255,183,197,0.18)]'}`} />

      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      <nav className="relative z-20 flex items-center justify-center px-5 h-[44px] shrink-0">
        <span className="text-[17px] font-semibold text-[var(--color-ink)]">创作中心</span>
      </nav>

      <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 pb-[120px] pt-4">
        {myChars.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <ModeSelector atLimit={atLimit} />

            <div className="mb-4">
              <p className="text-[15px] font-semibold text-[var(--color-ink)] px-1 mb-1">我的创造</p>
              <p className="text-[13px] text-[var(--color-text-muted)] px-1">{myChars.length} / 5 个角色</p>
            </div>

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

      <TabBar />

      <Dialog open={disableTarget !== null} onClose={() => setDisableTarget(null)} title={`停用「${disableTarget?.display_name ?? ''}」？`}>
        <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
          停用后该角色将从列表中隐藏，聊天记录保留。你可以在账号设置中重新启用。
        </p>
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => setDisableTarget(null)}
            className={`flex-1 h-[44px] rounded-full text-[var(--color-ink)] text-[15px] font-medium active:bg-[rgba(0,0,0,0.04)] ${isDark ? 'bg-[var(--color-glass-55)]' : 'bg-[rgba(255,255,255,0.75)]'}`}
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
            ) : (
              '确认停用'
            )}
          </button>
        </div>
      </Dialog>
    </div>
  )
}

function EmptyState() {
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  return (
    <div className="flex flex-col items-center justify-center pt-20 pb-12 px-6 text-center">
      <div
        className={`w-[88px] h-[88px] rounded-full bg-gradient-to-br from-[rgba(255,183,197,0.28)] to-[rgba(200,182,255,0.20)] flex items-center justify-center mb-6 ${
          isDark ? 'border border-[var(--color-border-subtle)] shadow-[0_8px_24px_rgba(0,0,0,0.20)]' : 'border border-[rgba(255,255,255,0.70)] shadow-[0_8px_24px_rgba(255,183,197,0.18)]'
        }`}
      >
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>
      <h2 className="text-[20px] font-semibold text-[var(--color-ink)] mb-2">还没有自创角色</h2>
      <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.65] mb-8 max-w-[260px]">
        创建属于你的专属角色，设计 Ta 的名字、性格与说话方式。
      </p>
      <ModeSelector atLimit={false} />
    </div>
  )
}

/** 批3: 两档入口 - 快速创建 vs 角色创作 */
function ModeSelector({ atLimit }: { atLimit: boolean }) {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  if (atLimit) {
    return (
      <div className="w-full mb-6 h-[64px] rounded-[20px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-text-muted)] text-[18px] font-bold flex items-center justify-center">
        已达上限(5个角色)
      </div>
    )
  }

  return (
    <div className="w-full mb-6 flex flex-col gap-3">
      <button
        onClick={() => navigate('/characters/new/quick')}
        className={`w-full p-5 rounded-[20px] text-left active:scale-[0.98] transition-transform ${
          isDark
            ? 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)]'
            : 'bg-white/80 backdrop-blur-sm border border-[rgba(255,183,197,0.20)] shadow-[0_4px_16px_rgba(255,183,197,0.12)]'
        }`}
      >
        <div className="flex items-start gap-3">
          <div className="shrink-0 w-[44px] h-[44px] rounded-full bg-gradient-to-br from-[#FFB7C5] to-[#FF8FAB] flex items-center justify-center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-[17px] font-semibold text-[var(--color-ink)] mb-1">快速创建</h3>
            <p className="text-[13px] text-[var(--color-text-secondary)] leading-[1.5]">
              填四项，剩下交给 AI，几十秒出一个能聊的角色
            </p>
          </div>
        </div>
      </button>

      <button
        onClick={() => navigate('/characters/new/workshop')}
        className={`w-full p-5 rounded-[20px] text-left active:scale-[0.98] transition-transform ${
          isDark
            ? 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)]'
            : 'bg-white/80 backdrop-blur-sm border border-[rgba(200,182,255,0.20)] shadow-[0_4px_16px_rgba(200,182,255,0.12)]'
        }`}
      >
        <div className="flex items-start gap-3">
          <div className="shrink-0 w-[44px] h-[44px] rounded-full bg-gradient-to-br from-[#C8B6FF] to-[#9D7CFF] flex items-center justify-center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 19l7-7 3 3-7 7-3-3z" />
              <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" />
              <path d="M2 2l7.586 7.586" />
              <circle cx="11" cy="11" r="2" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-[17px] font-semibold text-[var(--color-ink)] mb-1">角色创作</h3>
            <p className="text-[13px] text-[var(--color-text-secondary)] leading-[1.5]">
              一步步填，详情页会跟着变好看，可申请公开
            </p>
          </div>
        </div>
      </button>
    </div>
  )
}

