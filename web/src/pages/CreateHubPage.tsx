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
import { AppPageContent, AppPageShell } from '../components/ui/AppPageShell'

function useToast() {
  return useToastStore((s) => s.show)
}

/**
 * 创作中心页 — the primary entry for character creation + user-created character
 * management (moved from /my-characters, which was secondary UI). The center tab
 * now deep-links here.
 *
 * Structure: 顶部大号「+ 创建新角色」主 CTA，下方「我的创造」列表 +
 * 编辑/可见范围/停用菜单，空态兜底。(2026-07-31 product direction: put creator
 * actions front-and-center as we prepare to ship publishing features.)
 */
export function CreateHubPage() {
  const navigate = useNavigate()
  const { characters, loaded, load, setVisibility, disableCharacter, reactivateCharacter, deleteCharacter } =
    useCharactersStore()
  const showToast = useToast()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const scrollRef = useScrollRestore()
  const [disableTarget, setDisableTarget] = useState<CharacterDTO | null>(null)
  const [disabling, setDisabling] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<CharacterDTO | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!loaded) void load()
  }, [loaded, load])

  const myChars = characters.filter((c) => c.is_owner && !c.is_builtin)
  const publishableCount = myChars.filter(
    (c) => c.status !== 'disabled' && (c.visibility === 'public' || c.visibility === 'unlisted'),
  ).length

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

  async function handleReactivate(char: CharacterDTO) {
    try {
      await reactivateCharacter(char.id)
      const msg =
        char.visibility === 'public' || char.visibility === 'unlisted'
          ? `「${char.display_name}」已重新提交审核，通过后展示`
          : `「${char.display_name}」已重新发布`
      showToast(msg, 'success')
    } catch (err) {
      const m = err instanceof ApiError ? err.message : '操作失败，请稍后再试'
      showToast(m, 'error')
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteCharacter(deleteTarget.id)
      showToast(`「${deleteTarget.display_name}」已删除`, 'success')
      setDeleteTarget(null)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '操作失败，请稍后再试'
      showToast(msg, 'error')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AppPageShell className="app-atmosphere flex min-h-full flex-col">
      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      <AppPageContent size="medium" className="flex h-[58px] shrink-0 items-center px-4 sm:px-5">
        <h1 className="text-[24px] font-bold text-[var(--color-ink)]">创作</h1>
      </AppPageContent>

      <div ref={scrollRef} className="relative z-10 mx-auto min-h-0 w-full max-w-[860px] flex-1 overflow-y-auto px-4 pb-[120px] pt-2 sm:px-5">
        <CreatorHero isDark={isDark} onStart={() => navigate('/characters/new/quick')} />
        {myChars.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <ModeSelector />

            <div className="mb-4">
              <p className="text-[15px] font-semibold text-[var(--color-ink)] px-1 mb-1">我的创造</p>
              <p className="text-[13px] text-[var(--color-text-muted)] px-1">
                {publishableCount} / 10 个公开或链接可见角色 · 私密角色不限量
              </p>
            </div>

            <div className="flex flex-col gap-3">
              {myChars.map((char) => (
                <CharacterCard
                  key={char.id}
                  char={char}
                  onEdit={() => {
                    // 根据创建模式选择编辑路由（批7）
                    if (char.creation_mode === 'quick') {
                      // 快速创建编辑走确认页（单页承载全部字段，含封面/名字/性别/描述）
                      navigate(`/characters/new/quick/confirm?edit=${char.id}`)
                    } else {
                      navigate(`/characters/new/workshop?edit=${char.id}`)
                    }
                  }}
                  onVisibility={(v) => handleVisibility(char.id, v)}
                  onDisable={() => setDisableTarget(char)}
                  onReactivate={() => handleReactivate(char)}
                  onDelete={() => setDeleteTarget(char)}
                />
              ))}
            </div>
          </>
        )}
      </div>

      <TabBar />

      <Dialog open={disableTarget !== null} onClose={() => setDisableTarget(null)} title={`停用「${disableTarget?.display_name ?? ''}」？`}>
        <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
          停用后该角色对他人不可见，聊天记录保留。它会以「已停用」保留在这里，你随时可以重新发布。
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

      <Dialog open={deleteTarget !== null} onClose={() => setDeleteTarget(null)} title={`删除「${deleteTarget?.display_name ?? ''}」？`}>
        <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
          删除是永久操作，无法撤销。该角色及其聊天记录、设定将被彻底移除，不会再找回。
        </p>
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => setDeleteTarget(null)}
            className={`flex-1 h-[44px] rounded-full text-[var(--color-ink)] text-[15px] font-medium active:bg-[rgba(0,0,0,0.04)] ${isDark ? 'bg-[var(--color-glass-55)]' : 'bg-[rgba(255,255,255,0.75)]'}`}
          >
            取消
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="flex-1 h-[44px] rounded-full bg-[var(--color-error)] text-white text-[15px] font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {deleting ? (
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              '永久删除'
            )}
          </button>
        </div>
      </Dialog>
    </AppPageShell>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col px-1 pb-12 pt-3 text-left">
      <h2 className="text-[18px] font-semibold text-[var(--color-ink)]">开始你的角色创作</h2>
      <p className="mt-1 text-[13px] leading-[1.5] text-[var(--color-text-secondary)]">从一句想法开始，把 Ta 的性格和故事交给你决定。</p>
      <ModeSelector />
    </div>
  )
}

function CreatorHero({
  isDark,
  onStart,
}: {
  isDark: boolean
  onStart: () => void
}) {
  return (
    <section
      className={`relative mb-5 min-h-[170px] overflow-hidden rounded-[18px] border p-5 shadow-[0_8px_24px_rgba(73,48,62,0.10)] ${
        isDark
          ? 'border-white/10 bg-[linear-gradient(135deg,#2A232A_0%,#3A2933_58%,#5C3C49_100%)]'
          : 'border-white/75 bg-[linear-gradient(135deg,#FFF8F3_0%,#FFE8EF_58%,#F4D5E2_100%)]'
      }`}
    >
      <div className="relative z-10 max-w-[62%]">
        <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${isDark ? 'bg-white/12 text-white/80' : 'bg-white/70 text-[#C94A6A]'}`}>
          创作工作台
        </span>
        <h2 className={`mt-3 text-[20px] font-bold leading-[1.25] ${isDark ? 'text-white' : 'text-[var(--color-ink)]'}`}>
          创造一个会被记住的角色
        </h2>
        <p className={`mt-2 text-[12px] leading-[1.5] ${isDark ? 'text-white/72' : 'text-[var(--color-text-secondary)]'}`}>
          让每一次相遇，都从你的设定开始。
        </p>
        <button
          onClick={onStart}
          className={`mt-4 inline-flex h-[36px] items-center justify-center rounded-full px-4 text-[13px] font-semibold transition-transform active:scale-[0.97] ${isDark ? 'bg-white text-[#A14C68]' : 'bg-[var(--color-primary-500)] text-white shadow-[var(--shadow-btn)]'}`}
        >
          开始创建
        </button>
      </div>
      <div className="pointer-events-none absolute -bottom-4 right-[-12px] flex items-end" aria-hidden="true">
        <img src="/assets/characters/character_ji_yu_avatar.webp" alt="" className="h-[92px] w-[72px] -rotate-[8deg] rounded-[14px] object-cover opacity-80 shadow-[0_8px_18px_rgba(73,48,62,0.18)]" />
        <img src="/assets/characters/character_li_shen_avatar.webp" alt="" className="relative z-10 h-[130px] w-[100px] -translate-x-2 rounded-[16px] border-4 border-white/70 object-cover shadow-[0_12px_26px_rgba(73,48,62,0.22)]" />
        <img src="/assets/characters/character_cheng_xu_avatar.webp" alt="" className="h-[98px] w-[76px] -translate-x-4 rotate-[7deg] rounded-[14px] object-cover opacity-85 shadow-[0_8px_18px_rgba(73,48,62,0.18)]" />
      </div>
    </section>
  )
}

/** 批3: 两档入口 - 快速创建 vs 角色创作 */
function ModeSelector() {
  const navigate = useNavigate()

  return (
    <div className="mb-6 flex w-full flex-col gap-3 sm:grid sm:grid-cols-2">
      <button
        onClick={() => navigate('/characters/new/quick')}
        className="w-full rounded-[12px] border border-[rgba(255,110,138,0.30)] bg-[var(--color-page-surface)] p-4 text-left shadow-[0_4px_16px_rgba(24,24,32,0.06)] transition-opacity active:opacity-85"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-[10px] bg-[rgba(255,110,138,0.14)] text-[var(--color-primary-500)]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-[17px] font-semibold text-[var(--color-ink)] mb-1">快速创建</h3>
            <p className="text-[13px] text-[var(--color-text-secondary)] leading-[1.5]">AI 辅助生成</p>
          </div>
        </div>
      </button>

      <button
        onClick={() => navigate('/characters/new/workshop')}
        className="w-full rounded-[12px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4 text-left shadow-[0_4px_16px_rgba(24,24,32,0.06)] transition-opacity active:opacity-85"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-[10px] bg-[rgba(111,168,207,0.15)] text-[#6FA8CF]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 19l7-7 3 3-7 7-3-3z" />
              <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" />
              <path d="M2 2l7.586 7.586" />
              <circle cx="11" cy="11" r="2" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-[17px] font-semibold text-[var(--color-ink)] mb-1">角色创作</h3>
            <p className="text-[13px] text-[var(--color-text-secondary)] leading-[1.5]">逐步精细设定</p>
          </div>
        </div>
      </button>
    </div>
  )
}
