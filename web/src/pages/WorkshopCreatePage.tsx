import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToastStore } from '../stores/toastStore'
import {
  ApiError,
  createCharacter,
  updateCharacter,
  uploadCharacterCover,
  generateOpeningPreview,
} from '../services/api'
import { compressImageToTarget } from '../utils/imageCompress'
import { CreateShell } from '../components/create/CreateShell'
import {
  Step1,
  Step2,
  Step3,
  Step4,
  Step5,
  Step6,
  Step7,
  HTML_MAX,
} from './workshop/WorkshopSteps'
import {
  EMPTY_STATE,
  STORAGE_KEY,
  QUALITY_LABELS,
  getQualityLevel,
  buildDraft,
  type WorkshopState,
} from './workshop/workshopTypes'

/**
 * 角色创作页（七步引导）- 批 6
 *
 * 反转 nimoo 的"先选版式后填内容"：用户填什么内容，系统生成对应区块。
 * 进度用质感分级（素描→半成品→有模样→成品），不用百分比。
 * 第 1-2 步创建角色，之后每步 PATCH 全量草稿（后端整体替换）。
 */
export function WorkshopCreatePage() {
  const navigate = useNavigate()
  const showToast = useToastStore((s) => s.show)

  const [step, setStep] = useState(1)
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
  const [characterId, setCharacterId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [assisting, setAssisting] = useState(false)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [state])

  const qualityLevel = getQualityLevel(state)

  const updateField = <K extends keyof WorkshopState>(key: K, value: WorkshopState[K]) => {
    setState((prev) => ({ ...prev, [key]: value }))
  }

  const canAdvance1 = state.displayName.trim().length > 0
  const canAdvance2 = state.persona.trim().length >= 20
  const htmlOver = state.advancedHtmlMode && new Blob([state.customHtml]).size > HTML_MAX

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

  /** 第 2 步首次提交创建角色；之后每步 PATCH 全量草稿。 */
  async function persistDraft(): Promise<boolean> {
    const draft = buildDraft(state)
    try {
      if (!characterId) {
        const created = await createCharacter(draft)
        setCharacterId(created.id)
      } else {
        await updateCharacter(characterId, draft)
      }
      return true
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : '保存失败，请重试', 'error')
      return false
    }
  }

  async function handleNext() {
    if (step === 1) {
      if (!canAdvance1) return showToast('请先填写名字', 'error')
      setStep(2)
      return
    }
    if (step === 2 && !canAdvance2) return showToast('人设描述至少需要 20 字', 'error')
    if (step === 7 && htmlOver) return showToast('自定义 HTML 超出 50KB，请精简', 'error')

    setBusy(true)
    const ok = await persistDraft()
    setBusy(false)
    if (!ok) return

    if (step === 7) {
      localStorage.removeItem(STORAGE_KEY)
      if (characterId) navigate(`/characters/${characterId}`)
      return
    }
    setStep(step + 1)
  }

  function handleBack() {
    if (step > 1) setStep(step - 1)
    else navigate('/create')
  }

  return (
    <CreateShell
      title="角色创作"
      backLabel={step > 1 ? '上一步' : '返回创作中心'}
      onBack={handleBack}
      headerExtra={
        <div className="relative z-10 px-5 pb-1 flex items-center justify-center gap-3">
          <div className="flex gap-1.5">
            {[1, 2, 3, 4, 5, 6, 7].map((n) => (
              <span
                key={n}
                className={`h-[3px] rounded-full transition-all ${
                  n === step ? 'w-[20px] bg-[var(--color-primary)]' : n < step ? 'w-[10px] bg-[var(--color-primary)]/50' : 'w-[10px] bg-[var(--color-border-glass)]'
                }`}
              />
            ))}
          </div>
          <span className="text-[12px] text-[var(--color-text-secondary)]">{QUALITY_LABELS[qualityLevel]}</span>
        </div>
      }
      footer={
        <div className="fixed bottom-0 left-0 right-0 px-5 pb-[env(safe-area-inset-bottom,20px)] pt-3 z-30 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)] to-transparent">
          <button
            onClick={handleNext}
            disabled={busy || (step === 1 && !canAdvance1) || (step === 2 && !canAdvance2)}
            className="w-full h-[52px] rounded-full bg-gradient-to-r from-[#C8B6FF] to-[#9D7CFF] text-white text-[16px] font-semibold shadow-[0_8px_28px_-4px_rgba(157,124,255,0.45)] active:scale-[0.98] transition-transform disabled:opacity-45 disabled:active:scale-100"
          >
            {busy ? '保存中...' : step < 7 ? '下一步' : '完成创作'}
          </button>
        </div>
      }
    >
      {step === 1 && <Step1 state={state} updateField={updateField} onCoverUpload={handleCoverUpload} uploading={uploading} />}
      {step === 2 && <Step2 state={state} updateField={updateField} />}
      {step === 3 && <Step3 state={state} updateField={updateField} />}
      {step === 4 && <Step4 state={state} updateField={updateField} />}
      {step === 5 && <Step5 state={state} updateField={updateField} />}
      {step === 6 && <Step6 state={state} updateField={updateField} onAssistOpening={handleAssistOpening} assisting={assisting} />}
      {step === 7 && <Step7 state={state} updateField={updateField} />}
    </CreateShell>
  )
}
