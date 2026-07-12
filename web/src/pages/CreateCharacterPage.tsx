import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useCharactersStore } from '../stores/charactersStore'
import { useToastStore } from '../stores/toastStore'
import {
  ApiError,
  uploadCharacterAvatar,
  getPresetVoices,
  getPresetVoiceSampleUrl,
  setPresetVoice,
  getCharacterDraft,
  uploadVoiceClone,
  getCharacterVoice,
  type CharacterDraftDTO,
  type PresetVoiceDTO,
} from '../services/api'
import { compressImage } from '../utils/imageCompress'

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

function buildDraft(fields: FormFields, avatarUrl?: string): CharacterDraftDTO {
  return {
    display_name: { zh: fields.nameZh.trim() || undefined },
    avatar_url: avatarUrl || undefined,
    persona: fields.persona.trim(),
    greeting_style: fields.greetingStyle,
    gender: fields.gender,
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
  gender: 'female' | 'male'
  sliders: Record<keyof CharacterDraftDTO['sliders'], number> // 0-100 UI scale
  samples: string[]
}

function defaultForm(): FormFields {
  return {
    nameZh: '',
    persona: '',
    greetingStyle: 'warm',
    gender: 'female',
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
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  return (
    <div className={`backdrop-blur-[18px] rounded-[20px] shadow-[0_4px_16px_rgba(255,183,197,0.10)] ${isDark ? 'bg-[var(--color-surface-card)] border border-[var(--color-border-subtle)]' : 'bg-[rgba(255,255,255,0.72)] border border-[rgba(255,255,255,0.60)]'} ${className}`}>
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
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  // edit mode: ?edit=<characterId>
  const editId = searchParams.get('edit') ?? undefined

  const { characters, createCharacter, updateCharacter } = useCharactersStore()
  const showToast = useToast()

  const [form, setForm] = useState<FormFields>(defaultForm)
  const [submitting, setSubmitting] = useState(false)
  const [step, setStep] = useState<1 | 2 | 3>(1) // 1: basic info, 2: personality, 3: voice
  const [avatarUrl, setAvatarUrl] = useState<string>('')
  const [avatarUploading, setAvatarUploading] = useState(false)
  const avatarInputRef = useRef<HTMLInputElement>(null)

  // Voice step state
  const [createdCharacterId, setCreatedCharacterId] = useState<string>('')
  const [presets, setPresets] = useState<PresetVoiceDTO[]>([])
  const [selectedPreset, setSelectedPreset] = useState<string>('')
  const [voiceSaving, setVoiceSaving] = useState(false)
  const [playingPresetId, setPlayingPresetId] = useState<string | null>(null)
  const previewAudioRef = useRef<HTMLAudioElement | null>(null)
  // Object URL for the blob we fetched from /api/voice/presets/:id/sample.
  // Kept alongside previewAudioRef so both are torn down together.
  const previewObjectUrlRef = useRef<string | null>(null)

  // Clone voice upload state
  const cloneInputRef = useRef<HTMLInputElement>(null)
  const [cloneStatus, setCloneStatus] = useState<'idle' | 'uploading' | 'processing' | 'ready' | 'failed'>('idle')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ?voice=<cid> mode: configure voice for an already-created character
  const voiceOnlyId = searchParams.get('voice') ?? ''
  const isVoiceOnly = Boolean(voiceOnlyId && !editId)

  useEffect(() => {
    if (isVoiceOnly) {
      setStep(3)
      setCreatedCharacterId(voiceOnlyId)
    }
  }, [isVoiceOnly, voiceOnlyId])

  useEffect(() => {
    if (step === 3) {
      // Filter presets by the character's gender selected in step 1.
      // isVoiceOnly path skips step 1 entirely, so use undefined = no filter
      // and fall back to showing all voices.
      const genderFilter = isVoiceOnly ? undefined : form.gender
      getPresetVoices(genderFilter).then((res) => setPresets(res.presets)).catch(() => {})
    }
    // Stop preview audio when leaving voice step
    if (step !== 3 && previewAudioRef.current) {
      previewAudioRef.current.pause()
      previewAudioRef.current = null
      if (previewObjectUrlRef.current) {
        URL.revokeObjectURL(previewObjectUrlRef.current)
        previewObjectUrlRef.current = null
      }
      setPlayingPresetId(null)
    }
  }, [step, form.gender, isVoiceOnly])

  // Clean up polling and audio on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (previewAudioRef.current) previewAudioRef.current.pause()
      if (previewObjectUrlRef.current) URL.revokeObjectURL(previewObjectUrlRef.current)
    }
  }, [])

  // Form persistence for new-character mode: restore saved draft on mount,
  // save on every change, clear on successful submit.
  const DRAFT_KEY = 'yuoyuo-create-draft'
  useEffect(() => {
    if (editId || isVoiceOnly) return   // edit mode loads from server; voice-only has no form
    try {
      const raw = sessionStorage.getItem(DRAFT_KEY)
      if (!raw) return
      const saved = JSON.parse(raw) as { form: FormFields; avatarUrl: string; step: 1 | 2 }
      if (saved.form) setForm(saved.form)
      if (saved.avatarUrl) setAvatarUrl(saved.avatarUrl)
      if (saved.step) setStep(saved.step)
    } catch { /* corrupted entry — ignore */ }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (editId || isVoiceOnly || step === 3) return
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ form, avatarUrl, step }))
    } catch { /* storage full — ignore */ }
  }, [form, avatarUrl, step, editId, isVoiceOnly])

  // If editing, load full draft from the server to pre-populate all fields
  useEffect(() => {
    if (!editId) return
    Promise.all([
      getCharacterDraft(editId),
      getCharacterVoice(editId).catch(() => null),
    ]).then(([draft, voiceConfig]) => {
      setForm({
        nameZh: draft.display_name?.zh || '',
        persona: draft.persona || '',
        greetingStyle: (draft.greeting_style as GreetingStyle) || 'warm',
        gender: (draft.gender as 'female' | 'male') || 'female',
        sliders: {
          warmth:        Math.round((draft.sliders?.warmth ?? 0.6) * 100),
          talkativeness: Math.round((draft.sliders?.talkativeness ?? 0.5) * 100),
          directness:    Math.round((draft.sliders?.directness ?? 0.5) * 100),
          humor:         Math.round((draft.sliders?.humor ?? 0.4) * 100),
          playfulness:   Math.round((draft.sliders?.playfulness ?? 0.5) * 100),
          steadiness:    Math.round((draft.sliders?.steadiness ?? 0.6) * 100),
        },
        samples: [
          draft.speech_samples?.[0] || '',
          draft.speech_samples?.[1] || '',
          draft.speech_samples?.[2] || '',
        ],
      })
      if (draft.avatar_url) setAvatarUrl(draft.avatar_url)
      if (voiceConfig?.preset_voice_id) setSelectedPreset(voiceConfig.preset_voice_id)
    }).catch(() => {
      // Fallback: at least load display name from catalog
      const char = characters.find((c) => c.id === editId)
      if (char) setForm((prev) => ({ ...prev, nameZh: char.display_name }))
    })
  }, [editId])

  async function handleAvatarFile(file: File) {
    if (!file.type.startsWith('image/')) {
      showToast('请选择图片文件', 'error')
      return
    }
    setAvatarUploading(true)
    try {
      // Compress to 256×256 WebP so that even if the backend has to fall back
      // to a base64 data URL (S3 not configured), the resulting string stays
      // well under CharacterDraft.avatar_url max_length=200000.
      const compressed = await compressImage(file, 256, 0.85).catch(() => file)
      const { avatar_url } = await uploadCharacterAvatar(compressed)
      setAvatarUrl(avatar_url)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '头像上传失败，请重试'
      showToast(msg, 'error')
    } finally {
      setAvatarUploading(false)
    }
  }

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

  async function handleVoiceSave() {
    // Edit-only path: bind voice to an existing character (isVoiceOnly flow).
    // The creation flow goes through finalizeCreation() instead.
    if (!createdCharacterId) return
    if (!selectedPreset) {
      navigate(`/chat/${createdCharacterId}`, { replace: true })
      return
    }
    setVoiceSaving(true)
    try {
      await setPresetVoice(createdCharacterId, selectedPreset)
      showToast('音色配置成功', 'success')
    } catch {
      showToast('音色配置失败，可稍后在设置中重试', 'error')
    } finally {
      setVoiceSaving(false)
    }
    navigate(`/chat/${createdCharacterId}`, { replace: true })
  }

  // Tracks the id of the sample fetch that should "win" if multiple presets
  // are tapped in quick succession.  Bumped on every play/stop call.
  const previewTicketRef = useRef(0)

  function stopPreview() {
    previewTicketRef.current++
    if (previewAudioRef.current) {
      previewAudioRef.current.pause()
      previewAudioRef.current = null
    }
    if (previewObjectUrlRef.current) {
      URL.revokeObjectURL(previewObjectUrlRef.current)
      previewObjectUrlRef.current = null
    }
    setPlayingPresetId(null)
  }

  async function handlePresetPlay(preset: PresetVoiceDTO) {
    if (!preset.sample_url) return
    if (playingPresetId === preset.id) {
      stopPreview()
      return
    }
    stopPreview()
    const myTicket = ++previewTicketRef.current
    setPlayingPresetId(preset.id)
    try {
      const objectUrl = await getPresetVoiceSampleUrl(preset.id)
      // Another tap superseded us — throw this fetch away.
      if (myTicket !== previewTicketRef.current) {
        URL.revokeObjectURL(objectUrl)
        return
      }
      previewObjectUrlRef.current = objectUrl
      const audio = new Audio(objectUrl)
      previewAudioRef.current = audio
      audio.onended = () => { stopPreview() }
      audio.onerror = () => {
        if (myTicket !== previewTicketRef.current) return
        showToast('试听失败，请稍后再试', 'error')
        stopPreview()
      }
      await audio.play()
    } catch (err) {
      if (myTicket !== previewTicketRef.current) return
      // Surface the backend's provider error when we have one, otherwise fall
      // back to the generic copy. Keeps the toast short (max ~40 chars) so
      // long MiniMax payloads don't overflow the fixed-height bubble.
      const raw = err instanceof Error ? err.message : ''
      const msg = raw && raw.length <= 80 ? raw : '试听失败，请稍后再试'
      showToast(msg, 'error')
      stopPreview()
    }
  }

  /**
   * Guarantee we have a persisted character to bind the clone to. In the
   * creation flow (E1-1 deferred create to step-3 confirm/skip) the row
   * doesn't exist yet — Clone upload has to trigger its own finalize on
   * demand, otherwise the upload UI can never work in step 3. Returns the
   * character id on success or empty string on failure (toast already shown).
   */
  async function ensureCharacterCreated(): Promise<string> {
    if (createdCharacterId) return createdCharacterId
    // Edit flow: character already exists on the server as `editId`.
    if (editId) return editId
    const err = validateForm(form)
    if (err) {
      showToast(err, 'error')
      return ''
    }
    setSubmitting(true)
    try {
      const draft = buildDraft(form, avatarUrl || undefined)
      const { id } = await createCharacter(draft)
      sessionStorage.removeItem(DRAFT_KEY)
      setCreatedCharacterId(id)
      return id
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : '创建角色失败，请重试'
      showToast(msg, 'error')
      return ''
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCloneUpload(file: File) {
    // Ensure the character exists before uploading; in the create flow this
    // finalizes creation so the clone binds to a real row (E1-1 side effect).
    const cid = await ensureCharacterCreated()
    if (!cid) return
    // Match exact browser-reported MIME types.  Chrome tags .wav as audio/wav
    // but Firefox/Safari sometimes report audio/x-wav; iOS Voice Memos exports
    // as audio/mp4.  Empty type (some Android browsers) → fall back to the
    // extension check the backend also does.
    const allowed = new Set([
      'audio/wav',
      'audio/x-wav',
      'audio/wave',
      'audio/mpeg',
      'audio/mp3',
      'audio/ogg',
      'audio/webm',
      'audio/mp4',
      'audio/aac',
      'audio/flac',
    ])
    if (file.type && !allowed.has(file.type)) {
      showToast('请上传 WAV / MP3 / M4A / AAC 音频文件', 'error')
      return
    }
    if (file.size > 20 * 1024 * 1024) {
      showToast('文件不能超过 20MB', 'error')
      return
    }
    setCloneStatus('uploading')
    try {
      await uploadVoiceClone(cid, file)
      setCloneStatus('processing')
      // Poll until ready or failed (max 2 min)
      let attempts = 0
      pollRef.current = setInterval(async () => {
        attempts++
        if (attempts > 24) {
          if (pollRef.current) clearInterval(pollRef.current)
          setCloneStatus('failed')
          return
        }
        try {
          const voice = await getCharacterVoice(cid)
          if (voice.clone_status === 'ready') {
            if (pollRef.current) clearInterval(pollRef.current)
            setCloneStatus('ready')
            showToast('克隆音色已就绪', 'success')
          } else if (voice.clone_status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current)
            setCloneStatus('failed')
            // Show the real MiniMax / config reason if the backend provided
            // one. Falls back to a plain retry hint so users on older
            // deploys (no error_msg) still get feedback.
            const reason = voice.error_msg?.trim()
            showToast(reason ? `克隆失败：${reason}` : '克隆失败，请重试', 'error')
          }
        } catch { /* keep polling */ }
      }, 5000)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '上传失败，请重试'
      showToast(msg, 'error')
      setCloneStatus('failed')
    }
  }

  async function handleSubmit() {
    const err = validateForm(form)
    if (err) {
      showToast(err, 'error')
      return
    }

    if (!editId) {
      // Advance to voice step WITHOUT persisting — character is only created
      // when the user confirms or skips voice at step 3, so aborting on step 3
      // leaves no orphan character on the home list.
      setStep(3)
      return
    }

    setSubmitting(true)
    try {
      const draft = buildDraft(form, avatarUrl || undefined)
      await updateCharacter(editId, draft)
      showToast('角色已更新', 'success')
      navigate('/my-characters', { replace: true })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '创建失败，请稍后再试'
      showToast(msg, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  async function finalizeCreation(presetVoiceId: string | null) {
    const err = validateForm(form)
    if (err) {
      showToast(err, 'error')
      return
    }
    setVoiceSaving(true)
    setSubmitting(true)
    try {
      const draft = buildDraft(form, avatarUrl || undefined)
      const { id } = await createCharacter(draft)
      sessionStorage.removeItem(DRAFT_KEY)
      setCreatedCharacterId(id)
      if (presetVoiceId) {
        try {
          await setPresetVoice(id, presetVoiceId)
          showToast('音色配置成功', 'success')
        } catch {
          showToast('音色配置失败，可稍后在设置中重试', 'error')
        }
      }
      navigate(`/chat/${id}`, { replace: true })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '创建失败，请稍后再试'
      showToast(msg, 'error')
    } finally {
      setVoiceSaving(false)
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
      style={{ background: isDark ? 'var(--color-bg-page)' : 'linear-gradient(160deg, #FFF0F3 0%, #FFF8F3 40%, #F7F0FF 100%)' }}
    >
      {/* Soft ambient glow top */}
      <div className={`absolute top-0 left-1/2 -translate-x-1/2 w-[320px] h-[200px] rounded-full blur-[60px] pointer-events-none ${isDark ? 'bg-[rgba(255,183,197,0.06)]' : 'bg-[rgba(255,183,197,0.18)]'}`} />
      <div className={`absolute top-[120px] right-[-40px] w-[200px] h-[200px] rounded-full blur-[60px] pointer-events-none ${isDark ? 'bg-[rgba(200,182,255,0.04)]' : 'bg-[rgba(200,182,255,0.12)]'}`} />

      {/* Safe area */}
      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      {/* Navigation bar */}
      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button
          onClick={() => {
            if (step === 3 && isVoiceOnly) navigate(-1)
            else if (step === 3) setStep(2)
            else if (step === 2) setStep(1)
            else navigate(-1)
          }}
          className="w-[44px] h-[44px] flex items-center justify-center rounded-full active:bg-[rgba(255,183,197,0.15)] transition-colors"
        >
          <svg width="11" height="19" viewBox="0 0 11 19" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9,2 2,9.5 9,17" />
          </svg>
        </button>

        <span className="text-[17px] font-semibold text-[var(--color-ink)]">
          {step === 3 ? '配置音色' : title}
        </span>

        {/* Step indicator — only for creation flow */}
        {!isVoiceOnly && (
          <div className="flex items-center gap-1.5 pr-1">
            {[1, 2, 3].map((s) => (
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
        )}
        {isVoiceOnly && <div className="w-[44px]" />}
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

            {/* Avatar */}
            <SectionTitle>角色头像（选填）</SectionTitle>
            <div className="flex justify-center mb-2">
              <div className="relative">
                {/* Avatar preview */}
                <button
                  type="button"
                  onClick={() => avatarInputRef.current?.click()}
                  className="w-[88px] h-[88px] rounded-full overflow-hidden flex items-center justify-center active:scale-[0.96] transition-transform"
                  style={{
                    background: avatarUrl
                      ? 'transparent'
                      : 'linear-gradient(135deg, #FFB7C5 0%, #C8B6FF 100%)',
                  }}
                >
                  {avatarUrl ? (
                    <img src={avatarUrl} alt="头像" className="w-full h-full object-cover" />
                  ) : avatarUploading ? (
                    <svg className="animate-spin w-8 h-8 text-white" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : form.nameZh.trim() ? (
                    <span className="text-[34px] font-bold text-white leading-none select-none">
                      {form.nameZh.trim().slice(-1)}
                    </span>
                  ) : (
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="8" r="4" />
                      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
                    </svg>
                  )}
                </button>
                {/* Edit badge */}
                <div className="absolute bottom-0 right-0 w-[26px] h-[26px] rounded-full bg-[#FFB7C5] border-2 border-white flex items-center justify-center pointer-events-none">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </div>
                <input
                  ref={avatarInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleAvatarFile(file)
                  }}
                />
              </div>
            </div>
            <p className="text-center text-[12px] text-[var(--color-text-muted)] mb-2">
              {avatarUrl ? '点击头像更换' : '不上传则使用角色名最后一个字作为头像'}
            </p>

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

            {/* Gender */}
            <SectionTitle>角色性别</SectionTitle>
            <div className="flex gap-3">
              {([['female', '女性', '👩'], ['male', '男性', '👨']] as const).map(([value, label, emoji]) => {
                const active = form.gender === value
                return (
                  <button
                    key={value}
                    onClick={() => setForm((prev) => ({ ...prev, gender: value }))}
                    className={`flex-1 flex items-center justify-center gap-2 py-3.5 rounded-[16px] border transition-all duration-[180ms] active:scale-[0.98] ${
                      active
                        ? 'bg-[rgba(255,183,197,0.22)] border-[rgba(255,183,197,0.55)] shadow-[0_2px_12px_rgba(255,143,171,0.15)]'
                        : isDark
                        ? 'bg-[var(--color-surface-card)] border-[var(--color-border-subtle)]'
                        : 'bg-[rgba(255,255,255,0.72)] border-[rgba(255,255,255,0.60)]'
                    } backdrop-blur-[12px]`}
                  >
                    <span className="text-[20px]">{emoji}</span>
                    <span className={`text-[15px] font-semibold ${active ? 'text-[#E86083]' : 'text-[var(--color-ink)]'}`}>{label}</span>
                  </button>
                )
              })}
            </div>

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
                  className="w-full text-[16px] leading-[1.7] text-[var(--color-ink)] bg-transparent outline-none resize-none placeholder:text-[var(--color-text-placeholder)]"
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
                      className="flex-1 text-[16px] text-[var(--color-ink)] bg-transparent outline-none placeholder:text-[var(--color-text-placeholder)]"
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
                        : isDark
                        ? 'bg-[var(--color-surface-card)] border-[var(--color-border-subtle)] shadow-[0_2px_8px_rgba(0,0,0,0.15)]'
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

        {step === 3 && (
          <>
            <div className="text-center pt-6 pb-4">
              <p className="text-[13px] text-[var(--color-text-muted)] leading-relaxed">
                选择一个预设音色，让她开口说话。
                <br />
                <span className="text-[11px]">也可以跳过，稍后在后台配置。</span>
              </p>
            </div>

            <SectionTitle>预设音色</SectionTitle>
            <div className="space-y-2.5">
              {presets.length === 0 && (
                <p className="text-center text-[13px] text-[var(--color-text-muted)] py-8">
                  加载中…
                </p>
              )}
              {presets.map((preset) => {
                const active = selectedPreset === preset.id
                const isPlaying = playingPresetId === preset.id
                return (
                  <button
                    key={preset.id}
                    onClick={() => setSelectedPreset(active ? '' : preset.id)}
                    className={`w-full text-left px-5 py-4 rounded-[16px] border transition-all duration-[180ms] active:scale-[0.98] backdrop-blur-[12px] ${
                      active
                        ? 'bg-[rgba(255,183,197,0.22)] border-[rgba(255,183,197,0.55)] shadow-[0_2px_12px_rgba(255,143,171,0.15)]'
                        : isDark
                        ? 'bg-[var(--color-surface-card)] border-[var(--color-border-subtle)]'
                        : 'bg-[rgba(255,255,255,0.72)] border-[rgba(255,255,255,0.60)]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-[42px] h-[42px] rounded-full flex items-center justify-center shrink-0 ${
                        active ? 'bg-gradient-to-br from-[#FFB7C5] to-[#FF8FAB]' : 'bg-[rgba(255,183,197,0.18)]'
                      }`}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? 'white' : '#FF7DA1'} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 16a4 4 0 0 0 4-4V8a4 4 0 1 0-8 0v4a4 4 0 0 0 4 4Z" />
                          <path d="M19 11.5a7 7 0 0 1-14 0" />
                          <path d="M12 18.5v3" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-[15px] font-semibold ${active ? 'text-[#E86083]' : 'text-[var(--color-ink)]'}`}>
                          {preset.name}
                        </p>
                        {preset.description && (
                          <p className="text-[12px] text-[var(--color-text-muted)] mt-[2px]">
                            {preset.description}
                          </p>
                        )}
                      </div>
                      {preset.sample_url && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handlePresetPlay(preset) }}
                          className={`w-[36px] h-[36px] rounded-full flex items-center justify-center shrink-0 transition-colors ${
                            isPlaying
                              ? 'bg-[#FF8FAB] text-white'
                              : 'bg-[rgba(255,183,197,0.22)] text-[#FF7DA1]'
                          }`}
                          aria-label={isPlaying ? '暂停试听' : '试听'}
                        >
                          {isPlaying ? (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                              <rect x="6" y="4" width="4" height="16" rx="1" />
                              <rect x="14" y="4" width="4" height="16" rx="1" />
                            </svg>
                          ) : (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                              <polygon points="5,3 19,12 5,21" />
                            </svg>
                          )}
                        </button>
                      )}
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

            {/* Clone voice upload — always rendered in step 3.
                The character id used for the upload is resolved on demand by
                ensureCharacterCreated(): existing createdCharacterId → editId
                → new character finalized from the form. Prior code gated on
                `createdCharacterId &&`, which after E1-1 was empty during the
                whole voice step in the create flow, so the section vanished
                (TEST_REPORT_20260712 §4.3 follow-up). */}
            {(
              <>
                <SectionTitle>或者克隆音色（选填）</SectionTitle>
                <input
                  ref={cloneInputRef}
                  type="file"
                  accept="audio/wav,audio/mpeg,audio/mp3,audio/ogg,audio/webm,audio/mp4"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) { e.target.value = ''; handleCloneUpload(file) }
                  }}
                />
                <button
                  onClick={() => cloneInputRef.current?.click()}
                  disabled={cloneStatus === 'uploading' || cloneStatus === 'processing'}
                  className={`w-full flex items-center gap-4 px-5 py-4 rounded-[16px] border transition-all duration-[180ms] active:scale-[0.98] backdrop-blur-[12px] ${
                    cloneStatus === 'ready'
                      ? 'bg-[rgba(75,200,130,0.12)] border-[rgba(75,200,130,0.40)]'
                      : cloneStatus === 'failed'
                      ? 'bg-[rgba(255,90,90,0.10)] border-[rgba(255,90,90,0.35)]'
                      : isDark
                      ? 'bg-[var(--color-surface-card)] border-[var(--color-border-subtle)]'
                      : 'bg-[rgba(255,255,255,0.72)] border-[rgba(255,255,255,0.60)]'
                  }`}
                >
                  <div className={`w-[42px] h-[42px] rounded-full flex items-center justify-center shrink-0 ${
                    cloneStatus === 'ready' ? 'bg-[rgba(75,200,130,0.20)]' :
                    cloneStatus === 'failed' ? 'bg-[rgba(255,90,90,0.15)]' :
                    'bg-[rgba(255,183,197,0.18)]'
                  }`}>
                    {cloneStatus === 'uploading' || cloneStatus === 'processing' ? (
                      <svg className="animate-spin w-5 h-5 text-[#FF7DA1]" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : cloneStatus === 'ready' ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4BC882" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20,6 9,17 4,12" />
                      </svg>
                    ) : cloneStatus === 'failed' ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5A5A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF7DA1" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17,8 12,3 7,8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                      </svg>
                    )}
                  </div>
                  <div className="flex-1 min-w-0 text-left">
                    <p className={`text-[15px] font-semibold ${
                      cloneStatus === 'ready' ? 'text-[#4BC882]' :
                      cloneStatus === 'failed' ? 'text-[#FF5A5A]' :
                      'text-[var(--color-ink)]'
                    }`}>
                      {cloneStatus === 'idle' && '上传音频克隆音色'}
                      {cloneStatus === 'uploading' && '上传中…'}
                      {cloneStatus === 'processing' && '克隆中，请稍候…'}
                      {cloneStatus === 'ready' && '克隆完成 ✓'}
                      {cloneStatus === 'failed' && '克隆失败，点击重试'}
                    </p>
                    <p className="text-[12px] text-[var(--color-text-muted)] mt-[2px]">
                      WAV / MP3，10–30 秒，最大 20MB
                    </p>
                  </div>
                </button>
              </>
            )}
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
                <div className="w-[52px] h-[52px] rounded-full shrink-0 shadow-[0_4px_12px_rgba(255,183,197,0.30)] overflow-hidden">
                  {avatarUrl ? (
                    <img src={avatarUrl} alt="头像" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-[#FFB7C5] to-[#C8B6FF] flex items-center justify-center">
                      {form.nameZh.trim() ? (
                        <span className="text-[22px] font-bold text-white leading-none">
                          {form.nameZh.trim().slice(-1)}
                        </span>
                      ) : (
                        <span className="text-[22px]">
                          {GREETING_STYLES.find((s) => s.value === form.greetingStyle)?.emoji ?? '✨'}
                        </span>
                      )}
                    </div>
                  )}
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
        <div className={`backdrop-blur-[20px] rounded-[20px] px-4 py-3 ${isDark ? 'bg-[var(--color-surface-card)] border border-[var(--color-border-subtle)] shadow-[0_-4px_20px_rgba(0,0,0,0.15)]' : 'bg-[rgba(255,255,255,0.82)] border border-[rgba(255,255,255,0.70)] shadow-[0_-4px_20px_rgba(255,183,197,0.12)]'}`}>
          {step === 3 ? (
            <div className="flex gap-3">
              <button
                onClick={() => {
                  // Creation flow: character not yet persisted — finalize with no voice.
                  // Voice-only flow (isVoiceOnly): character already exists — just navigate away.
                  if (!createdCharacterId && !isVoiceOnly) {
                    void finalizeCreation(null)
                  } else if (createdCharacterId) {
                    navigate(`/chat/${createdCharacterId}`, { replace: true })
                  } else {
                    navigate(-1)
                  }
                }}
                disabled={submitting || voiceSaving}
                className={`flex-1 h-[52px] rounded-[14px] text-[16px] font-medium disabled:opacity-40 disabled:pointer-events-none ${isDark ? 'bg-[rgba(255,255,255,0.06)] text-[#ECE9F4]' : 'bg-[rgba(255,183,197,0.12)] text-[#2D3248]'}`}
              >
                跳过
              </button>
              <button
                onClick={() => {
                  // Creation flow: create + bind voice atomically.
                  // Voice-only edit flow: bind to existing character.
                  if (!createdCharacterId && !isVoiceOnly) {
                    void finalizeCreation(selectedPreset || null)
                  } else {
                    void handleVoiceSave()
                  }
                }}
                disabled={voiceSaving || submitting || !selectedPreset}
                className="flex-[2] h-[52px] rounded-[14px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[17px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform disabled:opacity-40 disabled:pointer-events-none flex items-center justify-center"
              >
                {voiceSaving || submitting ? (
                  <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : '确认音色'}
              </button>
            </div>
          ) : step === 1 ? (
            <button
              onClick={() => {
                if (!canProceed) {
                  if (!form.nameZh.trim()) {
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
                isEdit ? '保存更改' : '下一步 →'
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
