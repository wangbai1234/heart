import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useCharactersStore } from '../stores/charactersStore'
import { useToastStore } from '../stores/toastStore'
import { ApiError, type CharacterDraftDTO } from '../services/api'

function useToast() {
  return useToastStore((s) => s.show)
}

// ── Types ──────────────────────────────────────────────────────────

type GreetingStyle = 'warm' | 'cool' | 'playful' | 'reserved' | 'intense'

interface SliderField {
  key: keyof CharacterDraftDTO['sliders']
  label: string
  leftLabel: string
  rightLabel: string
}

// ── Constants ──────────────────────────────────────────────────────

const SLIDER_FIELDS: SliderField[] = [
  { key: 'warmth',        label: '亲切度',   leftLabel: '冷静',   rightLabel: '温暖' },
  { key: 'talkativeness', label: '话唠度',   leftLabel: '安静',   rightLabel: '爱说话' },
  { key: 'directness',    label: '直率度',   leftLabel: '含蓄',   rightLabel: '直接' },
  { key: 'humor',         label: '幽默感',   leftLabel: '认真',   rightLabel: '搞怪' },
  { key: 'playfulness',   label: '活泼度',   leftLabel: '稳重',   rightLabel: '活泼' },
  { key: 'steadiness',    label: '稳定度',   leftLabel: '情绪化', rightLabel: '淡定' },
]

const GREETING_STYLES: { value: GreetingStyle; label: string; desc: string; emoji: string }[] = [
  { value: 'warm',     label: '温柔',   desc: '体贴入微，关怀满满',   emoji: '🌸' },
  { value: 'cool',     label: '清冷',   desc: '不急不躁，距离感有魅力', emoji: '🌙' },
  { value: 'playful',  label: '俏皮',   desc: '跳脱有趣，笑声不断',   emoji: '✨' },
  { value: 'reserved', label: '内敛',   desc: '话不多，但句句走心',   emoji: '🍃' },
  { value: 'intense',  label: '浓烈',   desc: '情感丰沛，全情投入',   emoji: '🔥' },
]

const MAX_PERSONA = 1500
const MIN_PERSONA = 20

// ── Helpers ────────────────────────────────────────────────────────

function toApiSlider(v: number): number {
  return Math.round(v) / 100
}

function buildDraft(fields: FormFields): CharacterDraftDTO {
  return {
    display_name: { zh: fields.nameZh.trim() || undefined },
    persona: fields.persona.trim(),
    greeting_style: fields.greetingStyle,
    speech_samples: fields.samples.map((s) => s.trim()).filter(Boolean),
    sliders: {
      warmth:        toApiSlider(fields.sliders.warmth),
      talkativeness: toApiSlider(fields.sliders.talkativeness),
      directness:    toApiSlider(fields.sliders.directness),
      humor:         toApiSlider(fields.sliders.humor),
      playfulness:   toApiSlider(fields.sliders.playfulness),
      steadiness:    toApiSlider(fields.sliders.steadiness),
    },
    locale: 'zh',
  }
}

interface FormFields {
  nameZh: string
  persona: string
  greetingStyle: GreetingStyle
  sliders: Record<keyof CharacterDraftDTO['sliders'], number> // 0-100 UI scale
  samples: string[]
}

function defaultForm(): FormFields {
  return {
    nameZh: '',
    persona: '',
    greetingStyle: 'warm',
    sliders: {
      warmth:        60,
      talkativeness: 50,
      directness:    50,
      humor:         40,
      playfulness:   50,
      steadiness:    60,
    },
    samples: ['', '', ''],
  }
}

function validateForm(f: FormFields): string | null {
  if (!f.nameZh.trim()) return '请输入角色名字'
  if (f.persona.trim().length < MIN_PERSONA) return `人设描述至少需要 ${MIN_PERSONA} 个字`
  if (f.persona.trim().length > MAX_PERSONA) return `人设描述不能超过 ${MAX_PERSONA} 个字`
  return null
}

// ── Sub-components ─────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[13px] font-medium text-[var(--color-text-muted)] uppercase tracking-[0.08em] mb-3 mt-6 px-1">
      {children}
    </h2>
  )
}

function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[rgba(255,255,255,0.72)] backdrop-blur-[18px] rounded-[20px] border border-[rgba(255,255,255,0.60)] shadow-[0_4px_16px_rgba(255,183,197,0.10)] ${className}`}>
      {children}
    </div>
  )
}

interface SliderRowProps {
  field: SliderField
  value: number
  onChange: (v: number) => void
}

function SliderRow({ field, value, onChange }: SliderRowProps) {
  const pct = value
  return (
    <div className="px-5 py-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[14px] font-medium text-[var(--color-ink)]">{field.label}</span>
        <span className="text-[13px] text-[var(--color-text-muted)] tabular-nums w-8 text-right">{pct}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-[var(--color-text-muted)] w-12 text-right shrink-0">{field.leftLabel}</span>
        <div className="relative flex-1 h-[4px] rounded-full bg-[var(--color-slider-track)]">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB]"
            style={{ width: `${pct}%` }}
          />
          <input
            type="range"
            min={0}
            max={100}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[20px] h-[20px] rounded-full bg-white border-[2.5px] border-[#FFB7C5] shadow-[0_2px_8px_rgba(255,143,171,0.30)] pointer-events-none"
            style={{ left: `${pct}%` }}
          />
        </div>
        <span className="text-[11px] text-[var(--color-text-muted)] w-12 shrink-0">{field.rightLabel}</span>
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────

export function CreateCharacterPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // edit mode: ?edit=<characterId>
  const editId = searchParams.get('edit') ?? undefined

  const { characters, createCharacter, updateCharacter } = useCharactersStore()
  const showToast = useToast()

  const [form, setForm] = useState<FormFields>(defaultForm)
  const [submitting, setSubmitting] = useState(false)
  const [step, setStep] = useState<1 | 2>(1) // step 1: basic info, step 2: personality

  // If editing, populate form from catalog's existing character data
  // (draft fields not stored client-side; user sees defaults + can re-fill)
  useEffect(() => {
    if (editId) {
      const char = characters.find((c) => c.id === editId)
      if (char) {
        setForm((prev) => ({ ...prev, nameZh: char.display_name }))
      }
    }
  }, [editId, characters])

  function setSlider(key: keyof FormFields['sliders'], v: number) {
    setForm((prev) => ({ ...prev, sliders: { ...prev.sliders, [key]: v } }))
  }

  function setSample(idx: number, value: string) {
    setForm((prev) => {
      const samples = [...prev.samples]
      samples[idx] = value
      return { ...prev, samples }
    })
  }

  async function handleSubmit() {
    const err = validateForm(form)
    if (err) {
      showToast(err, 'error')
      return
    }

    setSubmitting(true)
    try {
      const draft = buildDraft(form)
      if (editId) {
        await updateCharacter(editId, draft)
        showToast('角色已更新', 'success')
        navigate('/my-characters', { replace: true })
      } else {
        const { id, display_name } = await createCharacter(draft)
        showToast(`「${display_name}」已创建，快去聊天吧`, 'success')
        navigate(`/chat/${id}`, { replace: true })
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '创建失败，请稍后再试'
      showToast(msg, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const isEdit = Boolean(editId)
  const title = isEdit ? '编辑角色' : '创建角色'
  const personaLen = form.persona.trim().length
  const personaOk = personaLen >= MIN_PERSONA && personaLen <= MAX_PERSONA
  const canProceed = form.nameZh.trim().length > 0 && personaOk

  return (
    <div
      className="relative w-full min-h-full flex flex-col overflow-hidden"
      style={{ background: 'linear-gradient(160deg, #FFF0F3 0%, #FFF8F3 40%, #F7F0FF 100%)' }}
    >
      {/* Soft ambient glow top */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[320px] h-[200px] rounded-full bg-[rgba(255,183,197,0.18)] blur-[60px] pointer-events-none" />
      <div className="absolute top-[120px] right-[-40px] w-[200px] h-[200px] rounded-full bg-[rgba(200,182,255,0.12)] blur-[60px] pointer-events-none" />

      {/* Safe area */}
      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      {/* Navigation bar */}
      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button
          onClick={() => step === 2 ? setStep(1) : navigate(-1)}
          className="w-[44px] h-[44px] flex items-center justify-center rounded-full active:bg-[rgba(255,183,197,0.15)] transition-colors"
        >
          <svg width="11" height="19" viewBox="0 0 11 19" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9,2 2,9.5 9,17" />
          </svg>
        </button>

        <span className="text-[17px] font-semibold text-[var(--color-ink)]">{title}</span>

        {/* Step indicator */}
        <div className="flex items-center gap-1.5 pr-1">
          {[1, 2].map((s) => (
            <div
              key={s}
              className={`rounded-full transition-all duration-[240ms] ${
                s === step
                  ? 'w-[20px] h-[6px] bg-[var(--color-primary)]'
                  : 'w-[6px] h-[6px] bg-[rgba(255,183,197,0.35)]'
              }`}
            />
          ))}
        </div>
      </nav>

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-[120px]">

        {step === 1 && (
          <>
            {/* Hero hint */}
            <div className="text-center pt-6 pb-2">
              <p className="text-[13px] text-[var(--color-text-muted)] leading-relaxed">
                给你的专属伴侣取个名字，
                <br />描述她的性格与故事。
              </p>
            </div>

            {/* Name */}
            <SectionTitle>角色名字</SectionTitle>
            <GlassCard>
              <div className="px-5 py-4">
                <input
                  type="text"
                  placeholder="比如：小雪、明月、夏树…"
                  value={form.nameZh}
                  onChange={(e) => setForm((prev) => ({ ...prev, nameZh: e.target.value }))}
                  maxLength={20}
                  className="w-full text-[17px] text-[var(--color-ink)] bg-transparent outline-none placeholder:text-[var(--color-text-placeholder)]"
                />
              </div>
            </GlassCard>

            {/* Persona */}
            <SectionTitle>人设描述</SectionTitle>
            <GlassCard>
              <div className="px-5 pt-4 pb-3">
                <textarea
                  placeholder={`描述她的性格、背景、说话方式…\n\n例：小雪是一个喜欢静静陪伴的女孩，说话温柔却藏着细腻的心思。她喜欢在深夜聊星星，也喜欢在早晨用一句"今天也要加油哦"开启你的一天…`}
                  value={form.persona}
                  onChange={(e) => setForm((prev) => ({ ...prev, persona: e.target.value }))}
                  maxLength={MAX_PERSONA}
                  rows={8}
                  className="w-full text-[15px] leading-[1.7] text-[var(--color-ink)] bg-transparent outline-none resize-none placeholder:text-[var(--color-text-placeholder)]"
                />
                <div className={`text-right text-[12px] mt-1 tabular-nums ${
                  personaLen > MAX_PERSONA
                    ? 'text-[var(--color-error)]'
                    : personaLen < MIN_PERSONA && personaLen > 0
                    ? 'text-[var(--color-warning)]'
                    : 'text-[var(--color-text-muted)]'
                }`}>
                  {personaLen} / {MAX_PERSONA}
                </div>
              </div>
            </GlassCard>

            {/* Speech samples */}
            <SectionTitle>口癖 / 标志性说话方式（选填）</SectionTitle>
            <GlassCard>
              <div className="divide-y divide-[var(--color-divider)]">
                {form.samples.map((s, i) => (
                  <div key={i} className="px-5 py-3 flex items-center gap-3">
                    <span className="text-[12px] text-[var(--color-text-muted)] w-4 shrink-0">{i + 1}</span>
                    <input
                      type="text"
                      placeholder={i === 0 ? '例：你又在想什么呢～' : i === 1 ? '例：嗯，我在的。' : '再添加一句…'}
                      value={s}
                      onChange={(e) => setSample(i, e.target.value)}
                      maxLength={80}
                      className="flex-1 text-[15px] text-[var(--color-ink)] bg-transparent outline-none placeholder:text-[var(--color-text-placeholder)]"
                    />
                  </div>
                ))}
              </div>
            </GlassCard>

            {/* Greeting style */}
            <SectionTitle>相处风格</SectionTitle>
            <div className="grid grid-cols-1 gap-2.5">
              {GREETING_STYLES.map(({ value, label, desc, emoji }) => {
                const active = form.greetingStyle === value
                return (
                  <button
                    key={value}
                    onClick={() => setForm((prev) => ({ ...prev, greetingStyle: value }))}
                    className={`w-full text-left px-5 py-4 rounded-[16px] border transition-all duration-[180ms] active:scale-[0.98] ${
                      active
                        ? 'bg-[rgba(255,183,197,0.22)] border-[rgba(255,183,197,0.55)] shadow-[0_2px_12px_rgba(255,143,171,0.15)]'
                        : 'bg-[rgba(255,255,255,0.72)] border-[rgba(255,255,255,0.60)] shadow-[0_2px_8px_rgba(0,0,0,0.04)]'
                    } backdrop-blur-[12px]`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-[22px]">{emoji}</span>
                      <div className="flex-1 min-w-0">
                        <span className={`text-[15px] font-semibold ${active ? 'text-[#E86083]' : 'text-[var(--color-ink)]'}`}>
                          {label}
                        </span>
                        <p className="text-[13px] text-[var(--color-text-secondary)] mt-[2px] leading-snug">{desc}</p>
                      </div>
                      {active && (
                        <div className="w-[20px] h-[20px] rounded-full bg-gradient-to-br from-[#FFB7C5] to-[#FF8FAB] flex items-center justify-center shrink-0">
                          <svg width="11" height="8" viewBox="0 0 11 8" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="1,4 4,7 10,1" />
                          </svg>
                        </div>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <div className="text-center pt-6 pb-2">
              <p className="text-[13px] text-[var(--color-text-muted)] leading-relaxed">
                调整滑块，塑造她的性格比例。
              </p>
            </div>

            <SectionTitle>性格调节</SectionTitle>
            <GlassCard>
              <div className="divide-y divide-[var(--color-divider)]">
                {SLIDER_FIELDS.map((field) => (
                  <SliderRow
                    key={field.key}
                    field={field}
                    value={form.sliders[field.key]}
                    onChange={(v) => setSlider(field.key, v)}
                  />
                ))}
              </div>
            </GlassCard>

            {/* Preview summary */}
            <SectionTitle>预览</SectionTitle>
            <GlassCard className="px-5 py-4">
              <div className="flex items-start gap-4">
                <div className="w-[52px] h-[52px] rounded-full bg-gradient-to-br from-[#FFB7C5] to-[#C8B6FF] flex items-center justify-center shrink-0 shadow-[0_4px_12px_rgba(255,183,197,0.30)]">
                  <span className="text-[22px]">
                    {GREETING_STYLES.find((s) => s.value === form.greetingStyle)?.emoji ?? '✨'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[16px] font-semibold text-[var(--color-ink)] truncate">
                    {form.nameZh.trim() || '未命名'}
                  </p>
                  <p className="text-[13px] text-[var(--color-text-secondary)] mt-1 leading-[1.6] line-clamp-2">
                    {form.persona.trim() || '人设描述将在这里显示…'}
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    <span className="text-[11px] text-[#E86083] bg-[rgba(255,183,197,0.20)] rounded-full px-2.5 py-[3px]">
                      {GREETING_STYLES.find((s) => s.value === form.greetingStyle)?.label}
                    </span>
                  </div>
                </div>
              </div>
            </GlassCard>
          </>
        )}
      </div>

      {/* Bottom action bar */}
      <div
        className="fixed bottom-0 left-0 right-0 z-30 px-4 pt-3"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 34px), 20px)' }}
      >
        <div className="bg-[rgba(255,255,255,0.82)] backdrop-blur-[20px] rounded-[20px] border border-[rgba(255,255,255,0.70)] shadow-[0_-4px_20px_rgba(255,183,197,0.12)] px-4 py-3">
          {step === 1 ? (
            <button
              onClick={() => {
                if (!canProceed) {
                  if (!form.nameZh.trim()) {
                    // nudge user
                    return
                  }
                }
                setStep(2)
              }}
              disabled={!canProceed}
              className="w-full h-[52px] rounded-[14px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[17px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform disabled:opacity-40 disabled:pointer-events-none"
            >
              下一步 →
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full h-[52px] rounded-[14px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[17px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform disabled:opacity-40 disabled:pointer-events-none flex items-center justify-center gap-2"
            >
              {submitting ? (
                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                isEdit ? '保存更改' : '创建角色 ✨'
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
