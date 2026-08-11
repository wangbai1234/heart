import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'

type QualityLevel = 'sketch' | 'draft' | 'shaped' | 'finished'

interface WorkshopState {
  // Step 1
  displayName: string
  gender: 'male' | 'female' | ''
  coverUrl: string
  tagline: string

  // Step 2
  persona: string
  intro: string
  tags: string[]

  // Step 3 - dossier items
  dossierItems: Array<{ label: string; value: string }>

  // Step 4 - quote
  quote: string
  quoteAttribution: string

  // Step 5 - background
  backgroundType: 'timeline' | 'objects' | 'contrast' | ''
  timelineItems: Array<{ label: string; value: string }>
  objectItems: Array<{ name: string; meaning: string }>
  contrastItems: Array<{ surface: string; depth: string }>

  // Step 6 - opening & premise
  opening: string
  premiseCard: {
    title: string
    content: string
  } | null
  starterPrompts: string[]

  // Step 7 - theme & visibility
  uiChromeThemeId: string
  reviewStatus: 'not_required' | 'pending_review' | 'approved' | 'rejected'
  advancedHtmlMode: boolean
  customHtml: string
}

const EMPTY_STATE: WorkshopState = {
  displayName: '',
  gender: '',
  coverUrl: '',
  tagline: '',
  persona: '',
  intro: '',
  tags: [],
  dossierItems: [],
  quote: '',
  quoteAttribution: '',
  backgroundType: '',
  timelineItems: [],
  objectItems: [],
  contrastItems: [],
  opening: '',
  premiseCard: null,
  starterPrompts: [],
  uiChromeThemeId: '',
  reviewStatus: 'not_required',
  advancedHtmlMode: false,
  customHtml: '',
}

const STORAGE_KEY = 'workshop_draft_state'

function getQualityLevel(state: WorkshopState): QualityLevel {
  if (!state.displayName || !state.persona) return 'sketch'
  if (!state.intro || state.tags.length === 0 || state.dossierItems.length < 3) return 'draft'
  if (!state.quote && !state.backgroundType) return 'shaped'
  return 'finished'
}

const QUALITY_LABELS: Record<QualityLevel, string> = {
  sketch: '素描',
  draft: '半成品',
  shaped: '有模样',
  finished: '成品',
}

export function WorkshopCreatePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  const [step, setStep] = useState(1)
  const [state, setState] = useState<WorkshopState>(() => {
    // Load from localStorage on mount
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        return JSON.parse(saved) as WorkshopState
      } catch {
        return EMPTY_STATE
      }
    }
    return EMPTY_STATE
  })

  const [characterId, setCharacterId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Persist to localStorage on every state change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [state])

  const qualityLevel = getQualityLevel(state)

  const updateField = <K extends keyof WorkshopState>(key: K, value: WorkshopState[K]) => {
    setState(prev => ({ ...prev, [key]: value }))
  }

  const canAdvanceFromStep1 = state.displayName.trim().length > 0
  const canAdvanceFromStep2 = state.persona.trim().length >= 20

  const handleCreateCharacter = async () => {
    if (!canAdvanceFromStep2) return

    setIsSubmitting(true)
    try {
      // POST to create character once persona is filled
      const response = await fetch('/api/characters/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          display_name: state.displayName,
          gender: state.gender || undefined,
          cover_url: state.coverUrl || undefined,
          persona: state.persona,
          tagline: state.tagline || undefined,
          intro: state.intro || undefined,
          tags: state.tags.length > 0 ? state.tags : undefined,
        }),
      })

      if (!response.ok) {
        throw new Error('创建角色失败')
      }

      const created = await response.json()
      setCharacterId(created.id)
      setStep(3)
    } catch (error) {
      console.error('Failed to create character:', error)
      alert('创建角色时出错，请稍后重试')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleNext = () => {
    if (step === 1 && canAdvanceFromStep1) {
      setStep(2)
    } else if (step === 2 && canAdvanceFromStep2) {
      handleCreateCharacter()
    } else if (step === 7 && characterId) {
      // Navigate to character profile page
      navigate(`/characters/${characterId}`)
    } else if (step < 7) {
      setStep(step + 1)
    }
  }

  return (
    <div
      className="relative w-full min-h-full flex flex-col"
      style={{ background: isDark ? 'var(--color-bg-page)' : 'linear-gradient(160deg, #FFF0F3 0%, #FFF8F3 40%, #F7F0FF 100%)' }}
    >
      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      <nav className="relative z-20 flex items-center px-5 h-[44px] shrink-0">
        <button
          onClick={() => step > 1 ? setStep(step - 1) : navigate(-1)}
          className="w-[28px] h-[28px] -ml-1 rounded-full flex items-center justify-center active:bg-[var(--color-glass-55)] transition-colors"
        >
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="8,2 2,8 8,14" />
          </svg>
        </button>
        <div className="flex-1 flex items-center justify-center gap-2 -ml-[28px]">
          <span className="text-[17px] font-semibold text-[var(--color-ink)]">
            角色创作
          </span>
          <span className="text-[13px] text-[var(--color-text-secondary)]">
            {QUALITY_LABELS[qualityLevel]}
          </span>
        </div>
      </nav>

      <div className="relative z-10 flex-1 px-5 pb-8 overflow-auto">
        {step === 1 && <Step1 state={state} updateField={updateField} />}
        {step === 2 && <Step2 state={state} updateField={updateField} />}
        {step === 3 && <StepPlaceholder stepNumber={3} title="档案信息" />}
        {step === 4 && <StepPlaceholder stepNumber={4} title="独白样本" />}
        {step === 5 && <StepPlaceholder stepNumber={5} title="背景故事" />}
        {step === 6 && <StepPlaceholder stepNumber={6} title="开场设计" />}
        {step === 7 && <StepPlaceholder stepNumber={7} title="主题配色" />}
        <div className="h-[env(safe-area-inset-bottom, 0px)]" />
      </div>

      <div className="sticky bottom-0 z-20 px-5 pb-5 pt-3 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)] to-transparent">
        <button
          onClick={handleNext}
          disabled={isSubmitting || (step === 1 && !canAdvanceFromStep1) || (step === 2 && !canAdvanceFromStep2)}
          className="w-full h-[48px] rounded-full bg-gradient-to-r from-[#C8B6FF] to-[#9D7CFF] text-white text-[16px] font-semibold disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] transition-transform"
        >
          {isSubmitting ? '创建中...' : step < 7 ? '下一步' : '完成'}
        </button>
        <div className="h-[env(safe-area-inset-bottom, 0px)]" />
      </div>
    </div>
  )
}

interface StepProps {
  state: WorkshopState
  updateField: <K extends keyof WorkshopState>(key: K, value: WorkshopState[K]) => void
}

function Step1({ state, updateField }: StepProps) {
  return (
    <div className="max-w-[520px] mx-auto pt-6">
      <h2 className="text-[22px] font-bold text-[var(--color-ink)] mb-2">核心身份</h2>
      <p className="text-[14px] text-[var(--color-text-secondary)] mb-6">
        先给角色起个名字，定下性别和封面。这是第一印象。
      </p>

      <div className="space-y-5">
        <div>
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            名字 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={state.displayName}
            onChange={e => updateField('displayName', e.target.value)}
            placeholder="角色叫什么名字？"
            className="w-full h-[44px] px-4 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[#9D7CFF]/30"
          />
        </div>

        <div>
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            性别
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => updateField('gender', 'male')}
              className={`flex-1 h-[44px] rounded-[12px] font-medium transition-colors ${
                state.gender === 'male'
                  ? 'bg-[#9D7CFF] text-white'
                  : 'bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-text-secondary)]'
              }`}
            >
              男
            </button>
            <button
              onClick={() => updateField('gender', 'female')}
              className={`flex-1 h-[44px] rounded-[12px] font-medium transition-colors ${
                state.gender === 'female'
                  ? 'bg-[#9D7CFF] text-white'
                  : 'bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-text-secondary)]'
              }`}
            >
              女
            </button>
          </div>
        </div>

        <div>
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            封面图 URL
          </label>
          <input
            type="url"
            value={state.coverUrl}
            onChange={e => updateField('coverUrl', e.target.value)}
            placeholder="https://example.com/cover.jpg"
            className="w-full h-[44px] px-4 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[#9D7CFF]/30"
          />
        </div>

        <div>
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            一句话钩子
          </label>
          <input
            type="text"
            value={state.tagline}
            onChange={e => updateField('tagline', e.target.value)}
            placeholder="让人第一眼想点进去的一句话"
            className="w-full h-[44px] px-4 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[#9D7CFF]/30"
          />
          <p className="mt-2 text-[13px] text-[var(--color-text-tertiary)]">
            提示：荷尔蒙钩子、危险感、反差感。不是平铺直叙的介绍。
          </p>
        </div>
      </div>
    </div>
  )
}

function Step2({ state, updateField }: StepProps) {
  return (
    <div className="max-w-[520px] mx-auto pt-6">
      <h2 className="text-[22px] font-bold text-[var(--color-ink)] mb-2">人设与介绍</h2>
      <p className="text-[14px] text-[var(--color-text-secondary)] mb-6">
        人设至少20字。intro 和标签会显示在详情页顶部。
      </p>

      <div className="space-y-5">
        <div>
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            人设描述 <span className="text-red-500">*</span>
          </label>
          <textarea
            value={state.persona}
            onChange={e => updateField('persona', e.target.value)}
            placeholder="角色的性格、特质、说话风格、核心设定..."
            rows={6}
            className="w-full px-4 py-3 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[#9D7CFF]/30 resize-none"
          />
          <p className="mt-2 text-[13px] text-[var(--color-text-tertiary)]">
            {state.persona.length}/20 字（最少）
          </p>
        </div>

        <div>
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            简介
          </label>
          <textarea
            value={state.intro}
            onChange={e => updateField('intro', e.target.value)}
            placeholder="一段简短的介绍，会显示在详情页名字下方"
            rows={3}
            className="w-full px-4 py-3 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[#9D7CFF]/30 resize-none"
          />
        </div>

        <div>
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            标签（逗号分隔）
          </label>
          <input
            type="text"
            value={state.tags.join(', ')}
            onChange={e => updateField('tags', e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
            placeholder="温柔, 强攻, 危险"
            className="w-full h-[44px] px-4 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[#9D7CFF]/30"
          />
        </div>
      </div>
    </div>
  )
}

function StepPlaceholder({ stepNumber, title }: { stepNumber: number; title: string }) {
  return (
    <div className="max-w-[520px] mx-auto pt-6">
      <div className="text-center py-12">
        <div className="w-[64px] h-[64px] mx-auto mb-4 rounded-full bg-gradient-to-br from-[#C8B6FF]/20 to-[#9D7CFF]/20 flex items-center justify-center">
          <span className="text-[24px] font-bold text-[#9D7CFF]">{stepNumber}</span>
        </div>
        <h2 className="text-[20px] font-bold text-[var(--color-ink)] mb-2">{title}</h2>
        <p className="text-[14px] text-[var(--color-text-secondary)]">
          此步骤完整功能开发中
        </p>
      </div>
    </div>
  )
}
