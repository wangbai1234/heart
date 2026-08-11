import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToastStore } from '../stores/toastStore'
import {
  ApiError,
  createCharacter,
  uploadCharacterCover,
  generateOpeningPreview,
} from '../services/api'
import { compressImageToTarget } from '../utils/imageCompress'
import { CreateShell } from '../components/create/CreateShell'
import { Step1, Step2, Step3, Step4, Step5, Step6, Step7, HTML_MAX } from './workshop/WorkshopSteps'
import {
  EMPTY_STATE,
  STORAGE_KEY,
  QUALITY_LABELS,
  getQualityLevel,
  buildDraft,
  type WorkshopState,
} from './workshop/workshopTypes'

const TABS = ['基础信息', '角色设定', '美化设置'] as const

/**
 * 角色创作页（三 Tab）- 对齐 nimoo singleCard 产品逻辑
 *
 * 基础信息 / 角色设定 / 美化设置三个 Tab 可自由跳转；内容按 Tab 分组复用
 * 既有 Step 组件，localStorage 本地留存草稿，仅在最终「创建」时一次性提交。
 * 必填（封面/名字/性别/人设）缺项跳到对应 Tab 并 toast 提示，按钮始终可点。
 */
export function WorkshopCreatePage() {
  const navigate = useNavigate()
  const showToast = useToastStore((s) => s.show)

  const [tab, setTab] = useState(0)
  const [state, setState] = useState<WorkshopState>(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        return { ...EMPTY_STATE, ...(JSON.parse(saved) as Partial<WorkshopState>) }
      } catch {
        return EMPTY_STATE
      }
    }
    return EMPTY_STATE
  })
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [assisting, setAssisting] = useState(false)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [state])

  const qualityLevel = getQualityLevel(state)
  const htmlOver = state.advancedHtmlMode && new Blob([state.customHtml]).size > HTML_MAX

  const updateField = <K extends keyof WorkshopState>(key: K, value: WorkshopState[K]) => {
    setState((prev) => ({ ...prev, [key]: value }))
  }

  async function handleCoverUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const compressed = await compressImageToTarget(file, 900 * 1024)
      const { cover_url } = await uploadCharacterCover(compressed)
      updateField('coverUrl', cover_url)
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : '封面上传失败，请重试', 'error')
    } finally {
      setUploading(false)
    }
  }

  async function handleAssistOpening() {
    if (state.persona.trim().length < 20) return
    setAssisting(true)
    try {
      const { opening } = await generateOpeningPreview({
        display_name: state.displayName || undefined,
        persona: state.persona,
        tags: state.tags.length ? state.tags : undefined,
      })
      updateField('opening', opening)
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'AI 生成失败，请重试', 'error')
    } finally {
      setAssisting(false)
    }
  }

  /** 校验必填 → 返回 {tab, msg}；全部通过返回 null。 */
  function firstMissing(): { tab: number; msg: string } | null {
    if (!state.coverUrl) return { tab: 0, msg: '请上传角色封面' }
    if (!state.displayName.trim()) return { tab: 0, msg: '请填写角色名字' }
    if (!state.gender) return { tab: 0, msg: '请选择性别' }
    if (state.persona.trim().length < 20) return { tab: 0, msg: '人设描述至少 20 字' }
    return null
  }

  async function handleCreate() {
    const missing = firstMissing()
    if (missing) {
      setTab(missing.tab)
      showToast(missing.msg, 'error')
      return
    }
    if (htmlOver) {
      setTab(2)
      showToast('自定义 HTML 超出 50KB，请精简', 'error')
      return
    }
    setBusy(true)
    try {
      const created = await createCharacter(buildDraft(state))
      localStorage.removeItem(STORAGE_KEY)
      navigate(`/characters/${created.id}`)
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : '创建失败，请重试', 'error')
    } finally {
      setBusy(false)
    }
  }

  /** 底部主按钮：非末 Tab 前进一格，末 Tab 触发创建。 */
  function handlePrimary() {
    if (tab < TABS.length - 1) setTab(tab + 1)
    else handleCreate()
  }

  function handleBack() {
    if (tab > 0) setTab(tab - 1)
    else navigate('/create')
  }

  return (
    <CreateShell
      title="角色创作"
      backLabel={tab > 0 ? '上一步' : '返回创作中心'}
      onBack={handleBack}
      headerExtra={
        <div className="relative z-10 px-5 pb-2">
          <div className="flex items-center justify-between mb-2">
            <div className="flex gap-5">
              {TABS.map((label, i) => (
                <button
                  key={label}
                  onClick={() => setTab(i)}
                  className={`relative text-[15px] pb-1.5 transition-colors ${
                    tab === i
                      ? 'font-semibold text-[var(--color-ink)]'
                      : 'font-normal text-[var(--color-text-muted)]'
                  }`}
                >
                  {label}
                  {tab === i && (
                    <span className="absolute -bottom-px left-0 right-0 h-[2.5px] rounded-full bg-[var(--color-primary)]" />
                  )}
                </button>
              ))}
            </div>
            <span className="text-[12px] text-[var(--color-text-secondary)] shrink-0">
              {QUALITY_LABELS[qualityLevel]}
            </span>
          </div>
          <div className="h-px bg-[var(--color-border-glass)]" />
        </div>
      }
      footer={
        <div className="fixed bottom-0 left-0 right-0 px-5 pb-[env(safe-area-inset-bottom,20px)] pt-3 z-30 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)] to-transparent">
          <button
            onClick={handlePrimary}
            disabled={busy}
            className="w-full h-[52px] rounded-full bg-gradient-to-r from-[#C8B6FF] to-[#9D7CFF] text-white text-[16px] font-semibold shadow-[0_8px_28px_-4px_rgba(157,124,255,0.45)] active:scale-[0.98] transition-transform disabled:opacity-60"
          >
            {busy ? '创建中...' : tab < TABS.length - 1 ? '下一步' : '创建角色'}
          </button>
        </div>
      }
    >
      {tab === 0 && (
        <>
          <Step1 state={state} updateField={updateField} onCoverUpload={handleCoverUpload} uploading={uploading} />
          <Step2 state={state} updateField={updateField} />
        </>
      )}
      {tab === 1 && (
        <>
          <Step3 state={state} updateField={updateField} />
          <Step4 state={state} updateField={updateField} />
          <Step5 state={state} updateField={updateField} />
        </>
      )}
      {tab === 2 && (
        <>
          <Step6 state={state} updateField={updateField} onAssistOpening={handleAssistOpening} assisting={assisting} />
          <Step7 state={state} updateField={updateField} />
        </>
      )}
    </CreateShell>
  )
}
