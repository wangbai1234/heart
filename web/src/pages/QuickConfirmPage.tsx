import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useToastStore } from '../stores/toastStore'
import { useCharactersStore } from '../stores/charactersStore'
import {
  ApiError,
  createCharacter,
  updateCharacter,
  getCharacterDraft,
  quickPrefill,
  setPresetVoice,
  uploadVoiceClone,
  uploadCharacterCover,
  type QuickPrefillResponse,
} from '../services/api'
import { compressImageToTarget } from '../utils/imageCompress'
import { THEME_PRESETS, getThemePresetById } from '../data/characterThemePresets'
import { VoicePickerSheet, type VoiceSelection } from '../components/VoicePickerSheet'

interface BaseInfo {
  coverUrl: string
  name: string
  gender: 'male' | 'female'
  persona: string
}

interface LocationState {
  base: BaseInfo
  prefill: QuickPrefillResponse
}

const GREETING_STYLE_LABELS: Record<string, string> = {
  warm: '温暖',
  cool: '冷淡',
  playful: '俏皮',
  reserved: '含蓄',
  intense: '热烈',
}

const SLIDER_LABELS: Record<string, string> = {
  warmth: '温暖度',
  talkativeness: '健谈度',
  directness: '直接度',
  humor: '幽默感',
  playfulness: '俏皮度',
  steadiness: '沉稳度',
}

const MAX_REGENERATE = 3
const PREFILL_CLIENT_TIMEOUT_MS = 60_000

function splitTags(value: string): string[] {
  return value.split(/[、,，]/).map((item) => item.trim()).filter(Boolean).slice(0, 5)
}

function splitSpeechSamples(value: string): string[] {
  return value.split('\n').map((item) => item.trim()).filter(Boolean).slice(0, 5)
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && (error.name === 'AbortError' || error.name === 'TimeoutError')
}

/**
 * 快速创建确认页 - 批4
 *
 * 上层可见: 开场白全文(人审)、配色色板、可见性开关
 * 下层折叠: 年龄段、相处风格、六个滑块、口癖
 */
export function QuickConfirmPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const editId = searchParams.get('edit')
  const isEdit = !!editId
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const showToast = useToastStore((s) => s.show)
  const reloadCharacters = useCharactersStore((s) => s.load)

  const state = location.state as LocationState | null

  // 新建流程从 location.state 拿基础信息；编辑流程从 draft 拉取后回填。
  const navBase = state?.base
  const initialPrefill = state?.prefill

  // 基础信息改为可编辑（编辑页需要能改封面/名字/性别/描述）
  const [coverUrl, setCoverUrl] = useState(navBase?.coverUrl ?? '')
  const [name, setName] = useState(navBase?.name ?? '')
  const [gender, setGender] = useState<'male' | 'female'>(navBase?.gender ?? 'female')
  const [persona, setPersona] = useState(navBase?.persona ?? '')
  const [uploadingCover, setUploadingCover] = useState(false)

  const [opening, setOpening] = useState(initialPrefill?.opening ?? '')
  const [themeId, setThemeId] = useState(initialPrefill?.theme_preset_id ?? 'night_velvet')
  const [visibility, setVisibility] = useState<'private' | 'unlisted'>('private')
  const [voiceSelection, setVoiceSelection] = useState<VoiceSelection>({ type: null })
  const [voicePickerOpen, setVoicePickerOpen] = useState(false)
  const [moreExpanded, setMoreExpanded] = useState(false)
  const [regenerateCount, setRegenerateCount] = useState(0)
  const [regenerating, setRegenerating] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [enrichingElapsed, setEnrichingElapsed] = useState(0)
  const [creating, setCreating] = useState(false)
  const prefillAbortRef = useRef<AbortController | null>(null)
  // 编辑模式：拉取草稿并回填全部字段
  const [loadingDraft, setLoadingDraft] = useState(isEdit)

  // Editable prefill fields - 批 7：更多设定可编辑
  const [ageRange, setAgeRange] = useState(initialPrefill?.age_range ?? '')
  const [greetingStyle, setGreetingStyle] = useState<QuickPrefillResponse['greeting_style']>(
    initialPrefill?.greeting_style ?? 'warm',
  )
  const [sliders, setSliders] = useState<Record<string, number>>(initialPrefill?.sliders ?? {})
  const [catchphrases, setCatchphrases] = useState<string[]>(initialPrefill?.catchphrases ?? [])
  const [tagline, setTagline] = useState(initialPrefill?.tagline ?? '')
  const [intro, setIntro] = useState(initialPrefill?.intro ?? '')
  const [oneLiner, setOneLiner] = useState(initialPrefill?.one_liner ?? '')
  const [archetypeLabel, setArchetypeLabel] = useState(initialPrefill?.archetype_label ?? '')
  const [backstory, setBackstory] = useState(initialPrefill?.backstory ?? '')
  const [tagsText, setTagsText] = useState((initialPrefill?.tags ?? []).join('、'))
  const [speechSamplesText, setSpeechSamplesText] = useState(
    (initialPrefill?.speech_samples ?? []).join('\n'),
  )
  const [soulProfile, setSoulProfile] = useState<QuickPrefillResponse['soul_profile'] | undefined>(
    initialPrefill?.soul_profile,
  )

  useEffect(() => {
    if (!editId) return
    let cancelled = false
    getCharacterDraft(editId)
      .then((draft) => {
        if (cancelled) return
        setCoverUrl(draft.cover_url ?? '')
        setName(draft.display_name?.zh ?? '')
        if (draft.gender) setGender(draft.gender)
        setPersona(draft.persona ?? '')
        setOpening(draft.opening ?? '')
        setAgeRange(draft.age_range ?? '')
        setGreetingStyle(draft.greeting_style ?? 'warm')
        if (draft.sliders) setSliders(draft.sliders)
        setCatchphrases(draft.catchphrases ?? [])
        setTagline(draft.tagline ?? '')
        setIntro(draft.intro ?? '')
        setOneLiner(draft.one_liner ?? '')
        setArchetypeLabel(draft.archetype_label ?? '')
        setBackstory(draft.backstory ?? '')
        setTagsText((draft.tags ?? []).join('、'))
        setSpeechSamplesText((draft.speech_samples ?? []).join('\n'))
        setSoulProfile(draft.soul_profile)
        if (draft.visibility === 'unlisted') setVisibility('unlisted')
        // 主题：按背景色反查预置
        const matched = THEME_PRESETS.find((p) => p.palette.bg === draft.ui_chrome?.bg)
        if (matched) setThemeId(matched.id)
      })
      .catch((err) => {
        showToast(err instanceof ApiError ? err.message : '加载角色数据失败', 'error')
      })
      .finally(() => {
        if (!cancelled) setLoadingDraft(false)
      })
    return () => {
      cancelled = true
    }
  }, [editId, showToast])

  useEffect(() => {
    if (!enriching) {
      setEnrichingElapsed(0)
      return
    }
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      setEnrichingElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [enriching])

  useEffect(() => () => prefillAbortRef.current?.abort(), [])

  // 新建流程缺 state（直接访问URL）→ 回快速创建。编辑流程不受此限。
  if (!isEdit && (!navBase || !initialPrefill)) {
    return (
      <div className="w-full h-full flex items-center justify-center px-6 text-center">
        <div>
          <p className="text-[15px] text-[var(--color-text-secondary)] mb-4">
            页面数据丢失，请重新开始快速创建
          </p>
          <button
            onClick={() => navigate('/characters/new/quick')}
            className="h-[44px] px-6 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[15px] font-semibold"
          >
            返回
          </button>
        </div>
      </div>
    )
  }

  if (loadingDraft) {
    return (
      <div className="w-full h-full flex items-center justify-center text-[14px] text-[var(--color-text-secondary)]">
        加载中...
      </div>
    )
  }

  async function handleCoverUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingCover(true)
    try {
      const compressed = await compressImageToTarget(file, 900 * 1024)
      const { cover_url } = await uploadCharacterCover(compressed)
      setCoverUrl(cover_url)
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : '封面上传失败，请重试', 'error')
    } finally {
      setUploadingCover(false)
    }
  }

  async function handleRegenerate() {
    if (regenerateCount >= MAX_REGENERATE) {
      showToast('重新生成次数已用完，可手动修改开场白', 'error')
      return
    }
    if (!name.trim() || !persona.trim()) {
      showToast('请先填写名字和角色描述', 'error')
      return
    }

    setRegenerating(true)
    try {
      const result = await requestQuickPrefill()
      setOpening(result.opening)
      setRegenerateCount((c) => c + 1)
    } catch (err) {
      const msg = isAbortError(err)
        ? '生成超时或已取消，请重试'
        : err instanceof ApiError ? err.message : '重新生成失败，请稍后再试'
      showToast(msg, 'error')
    } finally {
      setRegenerating(false)
    }
  }

  async function requestQuickPrefill(): Promise<QuickPrefillResponse> {
    prefillAbortRef.current?.abort()
    const controller = new AbortController()
    prefillAbortRef.current = controller
    const timer = window.setTimeout(() => controller.abort(), PREFILL_CLIENT_TIMEOUT_MS)
    try {
      return await quickPrefill({ display_name: name, gender, persona }, controller.signal)
    } finally {
      window.clearTimeout(timer)
      if (prefillAbortRef.current === controller) prefillAbortRef.current = null
    }
  }

  async function handleEnrich() {
    if (regenerateCount >= MAX_REGENERATE) {
      showToast('AI 完善次数已用完，仍可手动修改设定', 'error')
      return
    }
    if (!name.trim() || persona.trim().length < 20) {
      showToast('请先填写名字和至少 20 字的角色描述', 'error')
      return
    }

    setEnriching(true)
    try {
      const result = await requestQuickPrefill()
      setAgeRange(result.age_range)
      setGreetingStyle(result.greeting_style)
      setSliders(result.sliders)
      setTagline(result.tagline)
      setIntro(result.intro)
      setOneLiner(result.one_liner)
      setArchetypeLabel(result.archetype_label)
      setBackstory(result.backstory)
      setTagsText(result.tags.join('、'))
      setCatchphrases(result.catchphrases)
      setSpeechSamplesText(result.speech_samples.join('\n'))
      setSoulProfile(result.soul_profile)
      setOpening(result.opening)
      setThemeId(result.theme_preset_id)
      setRegenerateCount((count) => count + 1)
      showToast('角色档案已完善，请确认后保存', 'success')
    } catch (err) {
      const message = isAbortError(err)
        ? 'AI 完善超时或已取消，请重试'
        : err instanceof ApiError ? err.message : 'AI 完善失败，请稍后再试'
      showToast(message, 'error')
    } finally {
      setEnriching(false)
    }
  }

  async function handleCreate() {
    if (!coverUrl) {
      showToast('请上传角色封面', 'error')
      return
    }
    if (!name.trim()) {
      showToast('请填写角色名字', 'error')
      return
    }
    if (persona.trim().length < 20) {
      showToast('角色描述至少 20 字', 'error')
      return
    }
    if (!opening.trim()) {
      showToast('开场白不能为空', 'error')
      return
    }

    const selectedTheme = getThemePresetById(themeId)

    setCreating(true)
    try {
      const draft = {
        display_name: { zh: name },
        cover_url: coverUrl,
        gender,
        persona,
        tagline: tagline.trim() || undefined,
        intro: intro.trim() || undefined,
        one_liner: oneLiner.trim() || undefined,
        archetype_label: archetypeLabel.trim() || undefined,
        backstory: backstory.trim() || undefined,
        tags: splitTags(tagsText),
        speech_samples: splitSpeechSamples(speechSamplesText),
        soul_profile: soulProfile,
        creation_mode: 'quick' as const,
        greeting_style: greetingStyle,
        age_range: ageRange,
        sliders: sliders as {
          warmth: number
          talkativeness: number
          directness: number
          humor: number
          playfulness: number
          steadiness: number
        },
        catchphrases,
        opening,
        ui_chrome: selectedTheme?.palette ?? null,
        visibility,
      }

      const targetId = isEdit && editId
        ? (await updateCharacter(editId, draft)).id
        : (await createCharacter(draft)).id

      // Configure voice if selected（编辑模式下未改动则不动，保留原音色）
      if (voiceSelection.type === 'preset' && voiceSelection.presetVoiceId) {
        await setPresetVoice(targetId, voiceSelection.presetVoiceId).catch(
          () => {}, // silent fail - user can configure later
        )
      } else if (voiceSelection.type === 'clone' && voiceSelection.cloneFile) {
        await uploadVoiceClone(targetId, voiceSelection.cloneFile).catch(
          () => {}, // silent fail - user can configure later
        )
      }

      await reloadCharacters()
      showToast(isEdit ? '修改已保存' : '角色创建成功', 'success')
      navigate(`/character/${targetId}`, { replace: true, state: { fromCreate: true } })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : isEdit ? '保存失败，请重试' : '创建失败，请重试'
      showToast(msg, 'error')
    } finally {
      setCreating(false)
    }
  }

  const summaryLine = [
    ageRange,
    GREETING_STYLE_LABELS[greetingStyle] ?? greetingStyle,
    `${splitTags(tagsText).length} 个标签`,
    `${catchphrases.length} 条口癖`,
  ].join(' · ')

  const enrichingLabel = enrichingElapsed < 5
    ? '正在构建角色档案...'
    : enrichingElapsed < 10
      ? '正在完善人物经历与语言风格...'
      : '当前模型响应较慢，正在尝试备用模型...'

  return (
    <div
      className="relative w-full min-h-full flex flex-col"
      style={{ background: isDark ? 'var(--color-bg-page)' : 'linear-gradient(160deg, #FFF0F3 0%, #FFF8F3 40%, #F7F0FF 100%)' }}
    >
      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      <nav className="relative z-20 flex items-center px-5 h-[44px] shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="w-[28px] h-[28px] -ml-1 rounded-full flex items-center justify-center active:bg-[var(--color-glass-55)] transition-colors"
        >
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="8,2 2,8 8,14" />
          </svg>
        </button>
        <span className="flex-1 text-center text-[17px] font-semibold text-[var(--color-ink)] -ml-[28px]">
          {isEdit ? '编辑角色' : '确认创建'}
        </span>
      </nav>

      <div className="relative z-10 flex-1 overflow-y-auto px-5 pb-[120px] pt-4">
        {/* 基础信息 —— 封面 / 名字 / 性别 / 角色描述（编辑页需可改） */}
        <div className="mb-6 space-y-4">
          <div>
            <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">角色封面</label>
            <div className="flex gap-3.5">
              <label
                className={`relative shrink-0 w-[104px] h-[140px] rounded-[12px] cursor-pointer overflow-hidden ${
                  coverUrl ? '' : 'border-2 border-dashed border-[var(--color-border-glass)] bg-[var(--color-glass-55)]'
                }`}
              >
                {uploadingCover ? (
                  <div className="w-full h-full flex items-center justify-center text-[12px] text-[var(--color-text-secondary)]">上传中</div>
                ) : coverUrl ? (
                  <img src={coverUrl} alt="封面" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-1.5">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                    <span className="text-[12px] text-[var(--color-text-muted)]">上传图片</span>
                  </div>
                )}
                <input type="file" accept="image/*" onChange={handleCoverUpload} className="hidden" />
              </label>
              <ul className="flex-1 text-[12px] leading-[1.6] text-[var(--color-text-muted)] space-y-1.5 pt-0.5">
                <li>· 建议上传 3:4 或 9:16 竖图，人物居中</li>
                <li>· 图片同时用作封面和聊天背景</li>
                <li>· 点击封面可替换</li>
              </ul>
            </div>
          </div>

          <div>
            <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">角色名字</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value.slice(0, 20))}
              placeholder="给 Ta 起个名字"
              maxLength={20}
              className="w-full h-[44px] px-4 rounded-[12px] text-[15px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
            />
          </div>

          <div>
            <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">性别</label>
            <div className="flex gap-2.5">
              {(['male', 'female'] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => setGender(g)}
                  className={`flex-1 h-[42px] rounded-[12px] text-[15px] font-medium transition-all ${
                    gender === g
                      ? 'bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white shadow-[0_4px_14px_rgba(255,143,171,0.30)]'
                      : 'bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
                  }`}
                >
                  {g === 'male' ? '男' : '女'}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">角色描述</label>
            <textarea
              value={persona}
              onChange={(e) => setPersona(e.target.value.slice(0, 1500))}
              placeholder="一句话介绍你的角色，包括性格、背景、说话方式。"
              maxLength={1500}
              rows={4}
              className="w-full px-3.5 py-2.5 rounded-[12px] text-[14px] leading-[1.6] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
            />
            <div className="mt-1 flex items-center justify-between text-[12px]">
              <span className={persona.length > 0 && persona.length < 20 ? 'text-[var(--color-error)]' : 'text-transparent'}>
                {persona.length > 0 && persona.length < 20 ? `还需 ${20 - persona.length} 字` : '·'}
              </span>
              <span className="text-[var(--color-text-muted)]">{persona.length}/1500</span>
            </div>
          </div>
        </div>

        {/* 开场白全文 - 必须过人眼 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="text-[14px] font-medium text-[var(--color-ink)]">开场白</label>
            <button
              onClick={handleRegenerate}
              disabled={regenerating || enriching || regenerateCount >= MAX_REGENERATE}
              className="text-[13px] font-medium text-[var(--color-primary)] disabled:opacity-40 active:scale-[0.96] transition-transform"
            >
              {regenerating
                ? '生成中...'
                : regenerateCount >= MAX_REGENERATE
                  ? '已达重生上限'
                  : `重新生成 (${MAX_REGENERATE - regenerateCount})`}
            </button>
          </div>
          <textarea
            value={opening}
            onChange={(e) => setOpening(e.target.value.slice(0, 2000))}
            rows={8}
            maxLength={2000}
            className={`w-full px-4 py-3 rounded-[12px] text-[15px] leading-[1.7] resize-none ${
              isDark
                ? 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
                : 'bg-white/80 border border-[rgba(255,183,197,0.20)] text-[var(--color-ink)]'
            }`}
          />
          <div className="mt-1 text-[12px] text-[var(--color-text-muted)] text-right">{opening.length}/2000</div>
        </div>

        {/* 主题配色色板 */}
        <div className="mb-6">
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">主题配色</label>
          <div className="grid grid-cols-4 gap-3">
            {THEME_PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => setThemeId(preset.id)}
                className={`relative rounded-[12px] overflow-hidden aspect-square border-2 transition-all ${
                  themeId === preset.id ? 'border-[var(--color-primary)] scale-105' : 'border-transparent'
                }`}
                style={{ background: preset.palette.bg }}
              >
                <div className="absolute inset-x-1 bottom-1 h-[8px] rounded-full" style={{ background: preset.palette.ctaGradient }} />
                <div className="absolute top-1.5 left-1.5 w-[10px] h-[10px] rounded-full" style={{ background: preset.palette.taglineColor }} />
              </button>
            ))}
          </div>
          <div className="mt-2 text-[12px] text-[var(--color-text-secondary)]">
            {getThemePresetById(themeId)?.name}
          </div>
        </div>

        {/* 可见性 */}
        <div className="mb-6">
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">谁可以看到</label>
          <div className="flex flex-col gap-2">
            <button
              onClick={() => setVisibility('private')}
              className={`w-full p-4 rounded-[12px] text-left transition-all ${
                visibility === 'private'
                  ? 'bg-[rgba(255,143,171,0.10)] border-2 border-[var(--color-primary)]'
                  : isDark
                    ? 'bg-[var(--color-glass-75)] border-2 border-transparent'
                    : 'bg-white/80 border-2 border-transparent'
              }`}
            >
              <div className="text-[15px] font-medium text-[var(--color-ink)]">私密</div>
              <div className="text-[13px] text-[var(--color-text-secondary)] mt-0.5">仅自己可见，立即生效</div>
            </button>
            <button
              onClick={() => setVisibility('unlisted')}
              className={`w-full p-4 rounded-[12px] text-left transition-all ${
                visibility === 'unlisted'
                  ? 'bg-[rgba(255,143,171,0.10)] border-2 border-[var(--color-primary)]'
                  : isDark
                    ? 'bg-[var(--color-glass-75)] border-2 border-transparent'
                    : 'bg-white/80 border-2 border-transparent'
              }`}
            >
              <div className="text-[15px] font-medium text-[var(--color-ink)]">链接分享</div>
              <div className="text-[13px] text-[var(--color-text-secondary)] mt-0.5">审核通过后，拿到链接的人可访问</div>
            </button>
          </div>
        </div>

        {/* 角色声音 */}
        <div className="mb-6">
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">角色声音</label>
          <button
            onClick={() => setVoicePickerOpen(true)}
            className={`w-full p-4 rounded-[12px] flex items-center justify-between ${
              isDark ? 'bg-[var(--color-glass-75)]' : 'bg-white/80'
            }`}
          >
            <div className="text-left">
              <div className="text-[14px] font-medium text-[var(--color-ink)]">
                {voiceSelection.type === 'preset'
                  ? voiceSelection.presetName
                  : voiceSelection.type === 'clone'
                    ? '克隆音色（上传中）'
                    : '请选择'}
              </div>
              {!voiceSelection.type && (
                <div className="text-[12px] text-[var(--color-text-secondary)] mt-0.5">
                  可选，让角色开口说话
                </div>
              )}
            </div>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-text-muted)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="9,6 15,12 9,18" />
            </svg>
          </button>
        </div>

        {/* 更多设定 - 折叠 */}
        <div className="mb-6">
          <button
            onClick={() => setMoreExpanded((v) => !v)}
            className={`w-full p-4 rounded-[12px] flex items-center justify-between ${
              isDark ? 'bg-[var(--color-glass-75)]' : 'bg-white/80'
            }`}
          >
            <div className="text-left">
              <div className="text-[14px] font-medium text-[var(--color-ink)]">更多设定</div>
              <div className="text-[12px] text-[var(--color-text-secondary)] mt-0.5">{summaryLine}</div>
            </div>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-text-muted)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`transition-transform ${moreExpanded ? 'rotate-180' : ''}`}
            >
              <polyline points="6,9 12,15 18,9" />
            </svg>
          </button>

          {moreExpanded && (
            <div className={`mt-2 p-4 rounded-[12px] ${isDark ? 'bg-[var(--color-glass-55)]' : 'bg-white/60'}`}>
              <div className="mb-4 flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleEnrich}
                  disabled={enriching || regenerating || regenerateCount >= MAX_REGENERATE}
                  className="min-w-0 flex-1 min-h-[42px] rounded-[11px] border border-[rgba(255,143,171,0.35)] bg-[rgba(255,143,171,0.10)] px-3 py-2 text-[13px] leading-snug font-medium text-[#E86083] disabled:opacity-60 active:scale-[0.98] transition-transform"
                >
                  {enriching ? enrichingLabel : 'AI 完善全部设定'}
                </button>
                {enriching && (
                  <button
                    type="button"
                    onClick={() => prefillAbortRef.current?.abort()}
                    className="shrink-0 h-[42px] px-3 rounded-[11px] border border-[var(--color-border-subtle)] text-[13px] text-[var(--color-text-secondary)] active:scale-[0.96] transition-transform"
                  >
                    取消
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2.5 mb-3">
                <label className="block min-w-0">
                  <span className="block text-[13px] text-[var(--color-text-secondary)] mb-1">身份标签</span>
                  <input
                    type="text"
                    value={archetypeLabel}
                    maxLength={40}
                    onChange={(e) => setArchetypeLabel(e.target.value)}
                    placeholder="例如：急诊科医生"
                    className="w-full min-w-0 px-3 py-2 rounded-[10px] text-[14px] bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                  />
                </label>
                <label className="block min-w-0">
                  <span className="block text-[13px] text-[var(--color-text-secondary)] mb-1">角色短句</span>
                  <input
                    type="text"
                    value={tagline}
                    maxLength={60}
                    onChange={(e) => setTagline(e.target.value)}
                    placeholder="封面下的一句话"
                    className="w-full min-w-0 px-3 py-2 rounded-[10px] text-[14px] bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                  />
                </label>
              </div>

              <label className="block mb-3">
                <span className="block text-[13px] text-[var(--color-text-secondary)] mb-1">关于TA</span>
                <textarea
                  value={intro}
                  maxLength={500}
                  rows={4}
                  onChange={(e) => setIntro(e.target.value)}
                  placeholder="身份、性格、习惯与当下生活"
                  className="w-full px-3 py-2 rounded-[10px] text-[14px] leading-relaxed resize-none bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                />
              </label>

              <label className="block mb-3">
                <span className="block text-[13px] text-[var(--color-text-secondary)] mb-1">叙引</span>
                <textarea
                  value={oneLiner}
                  maxLength={120}
                  rows={3}
                  onChange={(e) => setOneLiner(e.target.value)}
                  placeholder="人物矛盾、故事悬念或关系切口"
                  className="w-full px-3 py-2 rounded-[10px] text-[14px] leading-relaxed resize-none bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                />
              </label>

              <label className="block mb-3">
                <span className="block text-[13px] text-[var(--color-text-secondary)] mb-1">人物经历</span>
                <textarea
                  value={backstory}
                  maxLength={1500}
                  rows={5}
                  onChange={(e) => setBackstory(e.target.value)}
                  placeholder="重要经历，以及它如何塑造现在的TA"
                  className="w-full px-3 py-2 rounded-[10px] text-[14px] leading-relaxed resize-none bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                />
              </label>

              <label className="block mb-3">
                <span className="block text-[13px] text-[var(--color-text-secondary)] mb-1">角色标签</span>
                <input
                  type="text"
                  value={tagsText}
                  onChange={(e) => setTagsText(e.target.value)}
                  placeholder="用顿号分隔，最多 5 个"
                  className="w-full px-3 py-2 rounded-[10px] text-[14px] bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                />
              </label>

              <label className="block mb-3">
                <span className="block text-[13px] text-[var(--color-text-secondary)] mb-1">说话样本</span>
                <textarea
                  value={speechSamplesText}
                  rows={4}
                  onChange={(e) => setSpeechSamplesText(e.target.value)}
                  placeholder="每行一句，最多 5 句"
                  className="w-full px-3 py-2 rounded-[10px] text-[14px] leading-relaxed resize-none bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                />
              </label>

              <div className="my-4 h-px bg-[var(--color-border-subtle)]" />

              {/* 年龄段 */}
              <div className="mb-3">
                <label className="block text-[13px] text-[var(--color-text-secondary)] mb-1">年龄段</label>
                <input
                  type="text"
                  value={ageRange}
                  onChange={(e) => setAgeRange(e.target.value)}
                  placeholder="例如：20-25"
                  className="w-full px-3 py-2 rounded-[10px] text-[14px] bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
                />
              </div>

              {/* 相处风格 */}
              <div className="mb-3">
                <label className="block text-[13px] text-[var(--color-text-secondary)] mb-2">相处风格</label>
                <div className="flex flex-wrap gap-2">
                  {(['warm', 'cool', 'playful', 'reserved', 'intense'] as const).map((style) => (
                    <button
                      key={style}
                      onClick={() => setGreetingStyle(style)}
                      className={`px-3 py-1.5 rounded-full text-[13px] font-medium transition-all ${
                        greetingStyle === style
                          ? 'bg-[rgba(255,183,197,0.25)] text-[#E86083] border border-[rgba(255,183,197,0.55)]'
                          : 'bg-[var(--color-glass-35)] text-[var(--color-text-secondary)] border border-transparent'
                      }`}
                    >
                      {GREETING_STYLE_LABELS[style]}
                    </button>
                  ))}
                </div>
              </div>

              <div className="my-3 h-px bg-[var(--color-border-subtle)]" />

              {/* 六个滑块 */}
              {Object.entries(sliders).map(([key, val]) => (
                <div key={key} className="mb-3">
                  <div className="flex items-center justify-between text-[13px] mb-1.5">
                    <span className="text-[var(--color-text-secondary)]">{SLIDER_LABELS[key] ?? key}</span>
                    <span className="text-[var(--color-text-muted)] tabular-nums">{Math.round(val * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={val}
                    onChange={(e) => setSliders({ ...sliders, [key]: Number.parseFloat(e.target.value) })}
                    className="w-full h-[4px] rounded-full appearance-none bg-[var(--color-glass-55)] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-[14px] [&::-webkit-slider-thumb]:h-[14px] [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[var(--color-primary)] [&::-webkit-slider-thumb]:cursor-pointer"
                  />
                </div>
              ))}

              <div className="my-3 h-px bg-[var(--color-border-subtle)]" />

              {/* 口癖 */}
              <div className="text-[13px] text-[var(--color-text-secondary)] mb-2">口癖</div>
              <div className="flex flex-wrap gap-2 mb-2">
                {catchphrases.map((cp, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[var(--color-glass-75)] text-[12px] text-[var(--color-ink)]"
                  >
                    <span>{cp}</span>
                    <button
                      onClick={() => setCatchphrases(catchphrases.filter((_, idx) => idx !== i))}
                      className="w-[14px] h-[14px] rounded-full flex items-center justify-center hover:bg-[var(--color-glass-55)] transition-colors"
                      aria-label="删除"
                    >
                      <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
              <input
                type="text"
                placeholder="输入口癖后按回车添加"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                    setCatchphrases([...catchphrases, e.currentTarget.value.trim()])
                    e.currentTarget.value = ''
                  }
                }}
                className="w-full px-3 py-2 rounded-[10px] text-[13px] bg-[var(--color-glass-35)] border border-[var(--color-border-subtle)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
              />
            </div>
          )}
        </div>
      </div>

      {/* 底部按钮 —— 音色弹窗打开时隐藏，避免与弹窗内「确定」按钮重叠 */}
      {!voicePickerOpen && (
        <div className="fixed bottom-0 left-0 right-0 px-5 pb-[env(safe-area-inset-bottom,20px)] pt-3 bg-[var(--color-bg-page)] border-t border-[var(--color-border-subtle)] z-30">
          <button
            onClick={handleCreate}
            disabled={creating || !opening.trim()}
            className="w-full h-[50px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform disabled:opacity-50 disabled:active:scale-100"
          >
            {creating ? (isEdit ? '保存中...' : '创建中...') : isEdit ? '保存修改' : '确认创建'}
          </button>
        </div>
      )}

      {/* Voice picker sheet */}
      <VoicePickerSheet
        open={voicePickerOpen}
        onClose={() => setVoicePickerOpen(false)}
        gender={gender}
        onConfirm={setVoiceSelection}
        initialSelection={voiceSelection}
      />
    </div>
  )
}
