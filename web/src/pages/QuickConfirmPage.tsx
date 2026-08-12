import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useToastStore } from '../stores/toastStore'
import { useCharactersStore } from '../stores/charactersStore'
import {
  ApiError,
  createCharacter,
  quickPrefill,
  setPresetVoice,
  uploadVoiceClone,
  type QuickPrefillResponse,
} from '../services/api'
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

/**
 * 快速创建确认页 - 批4
 *
 * 上层可见: 开场白全文(人审)、配色色板、可见性开关
 * 下层折叠: 年龄段、相处风格、六个滑块、口癖
 */
export function QuickConfirmPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const showToast = useToastStore((s) => s.show)
  const reloadCharacters = useCharactersStore((s) => s.load)

  const state = location.state as LocationState | null

  // 若无 state（直接访问URL），返回快速创建
  const base = state?.base
  const initialPrefill = state?.prefill

  const [opening, setOpening] = useState(initialPrefill?.opening ?? '')
  const [themeId, setThemeId] = useState(initialPrefill?.theme_preset_id ?? 'night_velvet')
  const [visibility, setVisibility] = useState<'private' | 'unlisted'>('private')
  const [voiceSelection, setVoiceSelection] = useState<VoiceSelection>({ type: null })
  const [voicePickerOpen, setVoicePickerOpen] = useState(false)
  const [moreExpanded, setMoreExpanded] = useState(false)
  const [regenerateCount, setRegenerateCount] = useState(0)
  const [regenerating, setRegenerating] = useState(false)
  const [creating, setCreating] = useState(false)

  // Editable prefill fields - 批 7：更多设定可编辑
  const [ageRange, setAgeRange] = useState(initialPrefill?.age_range ?? '')
  const [greetingStyle, setGreetingStyle] = useState<QuickPrefillResponse['greeting_style']>(
    initialPrefill?.greeting_style ?? 'warm',
  )
  const [sliders, setSliders] = useState<Record<string, number>>(initialPrefill?.sliders ?? {})
  const [catchphrases, setCatchphrases] = useState<string[]>(initialPrefill?.catchphrases ?? [])

  if (!base || !initialPrefill) {
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

  async function handleRegenerate() {
    if (regenerateCount >= MAX_REGENERATE) {
      showToast('重新生成次数已用完，可手动修改开场白', 'error')
      return
    }
    if (!base) return

    setRegenerating(true)
    try {
      const result = await quickPrefill({
        display_name: base.name,
        gender: base.gender,
        persona: base.persona,
      })
      setOpening(result.opening)
      setRegenerateCount((c) => c + 1)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '重新生成失败，请稍后再试'
      showToast(msg, 'error')
    } finally {
      setRegenerating(false)
    }
  }

  async function handleCreate() {
    if (!base || !opening.trim()) {
      showToast('开场白不能为空', 'error')
      return
    }

    const selectedTheme = getThemePresetById(themeId)

    setCreating(true)
    try {
      const result = await createCharacter({
        display_name: { zh: base.name },
        cover_url: base.coverUrl,
        gender: base.gender,
        persona: base.persona,
        creation_mode: 'quick',
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
      })

      // Configure voice if selected
      if (voiceSelection.type === 'preset' && voiceSelection.presetVoiceId) {
        await setPresetVoice(result.id, voiceSelection.presetVoiceId).catch(
          () => {}, // silent fail - user can configure later
        )
      } else if (voiceSelection.type === 'clone' && voiceSelection.cloneFile) {
        await uploadVoiceClone(result.id, voiceSelection.cloneFile).catch(
          () => {}, // silent fail - user can configure later
        )
      }

      await reloadCharacters()
      showToast('角色创建成功', 'success')
      navigate(`/character/${result.id}`, { replace: true, state: { fromCreate: true } })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '创建失败，请重试'
      showToast(msg, 'error')
    } finally {
      setCreating(false)
    }
  }

  const summaryLine = [
    ageRange,
    GREETING_STYLE_LABELS[greetingStyle] ?? greetingStyle,
    `${catchphrases.length} 条口癖`,
  ].join(' · ')

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
          确认创建
        </span>
      </nav>

      <div className="relative z-10 flex-1 overflow-y-auto px-5 pb-[120px] pt-4">
        {/* 开场白全文 - 必须过人眼 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="text-[14px] font-medium text-[var(--color-ink)]">开场白</label>
            <button
              onClick={handleRegenerate}
              disabled={regenerating || regenerateCount >= MAX_REGENERATE}
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

      {/* 底部按钮 */}
      <div className="fixed bottom-0 left-0 right-0 px-5 pb-[env(safe-area-inset-bottom,20px)] pt-3 bg-[var(--color-bg-page)] border-t border-[var(--color-border-subtle)] z-30">
        <button
          onClick={handleCreate}
          disabled={creating || !opening.trim()}
          className="w-full h-[50px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform disabled:opacity-50 disabled:active:scale-100"
        >
          {creating ? '创建中...' : '确认创建'}
        </button>
      </div>

      {/* Voice picker sheet */}
      <VoicePickerSheet
        open={voicePickerOpen}
        onClose={() => setVoicePickerOpen(false)}
        gender={base?.gender}
        onConfirm={setVoiceSelection}
        initialSelection={voiceSelection}
      />
    </div>
  )
}
