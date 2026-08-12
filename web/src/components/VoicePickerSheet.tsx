import { useEffect, useRef, useState } from 'react'
import { useThemeStore } from '../stores/themeStore'
import { useMembershipStore } from '../stores/membershipStore'
import { useToastStore } from '../stores/toastStore'
import {
  getPresetVoices,
  getPresetVoiceSampleUrl,
  getPricing,
  type PresetVoiceDTO,
  ApiError,
} from '../services/api'

interface VoicePickerSheetProps {
  open: boolean
  onClose: () => void
  gender?: 'male' | 'female'
  onConfirm: (selection: VoiceSelection) => void
  initialSelection?: VoiceSelection
}

export interface VoiceSelection {
  type: 'preset' | 'clone' | null
  presetVoiceId?: string
  presetName?: string
  cloneFile?: File
}

/**
 * 角色音色选择底部弹窗 - 批7
 *
 * 用于快速创建和角色创作页面的音色配置。
 * 支持：预设音色选择 + 音频/视频克隆上传
 */
export function VoicePickerSheet({
  open,
  onClose,
  gender,
  onConfirm,
  initialSelection,
}: VoicePickerSheetProps) {
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const showToast = useToastStore((s) => s.show)

  const [presets, setPresets] = useState<PresetVoiceDTO[]>([])
  const [selectedPreset, setSelectedPreset] = useState<string>(
    initialSelection?.type === 'preset' ? initialSelection.presetVoiceId || '' : '',
  )
  const [playingPresetId, setPlayingPresetId] = useState<string | null>(null)
  const previewAudioRef = useRef<HTMLAudioElement | null>(null)
  const previewObjectUrlRef = useRef<string | null>(null)

  const cloneInputRef = useRef<HTMLInputElement>(null)
  const [pendingCloneFile, setPendingCloneFile] = useState<File | null>(null)
  const [cloneCost, setCloneCost] = useState<number>(100)
  const canCloneFish = useMembershipStore((s) =>
    s.entitlements.clone.includes('fish'),
  )

  useEffect(() => {
    if (open) {
      getPresetVoices(gender)
        .then((res) => setPresets(res.presets))
        .catch(() => showToast('加载音色列表失败', 'error'))
      getPricing()
        .then((p) => {
          const fish = p.actions.find((a) => a.id === 'clone_fish')?.cost
          setCloneCost(fish ?? 100)
        })
        .catch(() => {})
    }
    // Clean up audio when closing
    if (!open && previewAudioRef.current) {
      previewAudioRef.current.pause()
      previewAudioRef.current = null
      if (previewObjectUrlRef.current) {
        URL.revokeObjectURL(previewObjectUrlRef.current)
        previewObjectUrlRef.current = null
      }
      setPlayingPresetId(null)
    }
  }, [open, gender])

  useEffect(() => {
    return () => {
      if (previewAudioRef.current) previewAudioRef.current.pause()
      if (previewObjectUrlRef.current)
        URL.revokeObjectURL(previewObjectUrlRef.current)
    }
  }, [])

  async function handlePresetPlay(preset: PresetVoiceDTO) {
    if (playingPresetId === preset.id) {
      previewAudioRef.current?.pause()
      setPlayingPresetId(null)
      return
    }
    try {
      if (previewObjectUrlRef.current) {
        URL.revokeObjectURL(previewObjectUrlRef.current)
        previewObjectUrlRef.current = null
      }
      const objectUrl = await getPresetVoiceSampleUrl(preset.id)
      previewObjectUrlRef.current = objectUrl
      const audio = new Audio(objectUrl)
      previewAudioRef.current = audio
      setPlayingPresetId(preset.id)
      audio.onended = () => setPlayingPresetId(null)
      await audio.play()
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : '试听失败，请重试'
      showToast(msg, 'error')
      setPlayingPresetId(null)
    }
  }

  function handleCloneFileSelected(file: File) {
    const isVideo = file.type.startsWith('video/')
    const isAudio = file.type.startsWith('audio/')
    if (!isVideo && !isAudio) {
      showToast('仅支持音频或视频文件', 'error')
      return
    }
    if (isVideo) {
      setPendingCloneFile(file)
    } else {
      confirmClone(file)
    }
  }

  function confirmClone(file: File) {
    setPendingCloneFile(null)
    onConfirm({ type: 'clone', cloneFile: file })
    onClose()
  }

  function handleConfirm() {
    if (!selectedPreset) {
      showToast('请选择一个音色', 'error')
      return
    }
    const preset = presets.find((p) => p.id === selectedPreset)
    onConfirm({
      type: 'preset',
      presetVoiceId: selectedPreset,
      presetName: preset?.name,
    })
    onClose()
  }

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-[100] transition-opacity"
        onClick={onClose}
      />

      {/* Sheet */}
      <div
        className={`fixed inset-x-0 bottom-0 z-[101] rounded-t-[24px] max-h-[85vh] overflow-hidden ${
          isDark ? 'bg-[var(--color-surface-card)]' : 'bg-white'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 px-5 pt-4 pb-3 border-b border-[var(--color-border-subtle)] bg-inherit">
          <div className="flex items-center justify-between">
            <h2 className="text-[17px] font-semibold text-[var(--color-ink)]">
              角色音色
            </h2>
            <button
              onClick={onClose}
              className="w-[32px] h-[32px] rounded-full flex items-center justify-center hover:bg-[var(--color-glass-55)] transition-colors"
              aria-label="关闭"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-text-muted)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(85vh-140px)] px-5 py-4 pb-20">
          <p className="text-[13px] text-[var(--color-text-muted)] mb-4">
            选择一个预设音色，或上传音频克隆（3-10 分钟音频，不含背景音）
          </p>

          {/* Preset voices grid */}
          <div className="grid grid-cols-2 gap-2.5 mb-6">
            {presets.length === 0 && (
              <p className="col-span-2 text-center text-[13px] text-[var(--color-text-muted)] py-8">
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
                  className={`relative p-3 rounded-[12px] border transition-all duration-[180ms] active:scale-[0.97] ${
                    active
                      ? 'bg-[rgba(255,183,197,0.22)] border-[rgba(255,183,197,0.55)] shadow-[0_2px_12px_rgba(255,143,171,0.15)]'
                      : isDark
                        ? 'bg-[var(--color-glass-55)] border-[var(--color-border-subtle)]'
                        : 'bg-[rgba(255,255,255,0.72)] border-[rgba(255,255,255,0.60)]'
                  }`}
                >
                  <div className="flex items-start gap-2 mb-2">
                    <div
                      className={`w-[36px] h-[36px] rounded-full flex items-center justify-center shrink-0 ${
                        active
                          ? 'bg-gradient-to-br from-[#FFB7C5] to-[#FF8FAB]'
                          : 'bg-[rgba(255,183,197,0.18)]'
                      }`}
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={active ? 'white' : '#FF7DA1'}
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M12 16a4 4 0 0 0 4-4V8a4 4 0 1 0-8 0v4a4 4 0 0 0 4 4Z" />
                        <path d="M19 11.5a7 7 0 0 1-14 0" />
                        <path d="M12 18.5v3" />
                      </svg>
                    </div>
                    {active && (
                      <div className="w-[18px] h-[18px] rounded-full bg-gradient-to-br from-[#FFB7C5] to-[#FF8FAB] flex items-center justify-center shrink-0">
                        <svg
                          width="10"
                          height="7"
                          viewBox="0 0 11 8"
                          fill="none"
                          stroke="white"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="1,4 4,7 10,1" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <p
                    className={`text-[14px] font-semibold mb-1 text-left ${
                      active ? 'text-[#E86083]' : 'text-[var(--color-ink)]'
                    }`}
                  >
                    {preset.name}
                  </p>
                  {preset.description && (
                    <p className="text-[11px] text-[var(--color-text-muted)] text-left line-clamp-2 mb-2">
                      {preset.description}
                    </p>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handlePresetPlay(preset)
                    }}
                    className={`w-full h-[28px] rounded-full flex items-center justify-center gap-1 text-[12px] font-medium transition-colors ${
                      isPlaying
                        ? 'bg-[#FF8FAB] text-white'
                        : 'bg-[rgba(255,183,197,0.22)] text-[#FF7DA1]'
                    }`}
                    aria-label={isPlaying ? '暂停试听' : '试听'}
                  >
                    {isPlaying ? (
                      <>
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <rect x="6" y="4" width="4" height="16" rx="1" />
                          <rect x="14" y="4" width="4" height="16" rx="1" />
                        </svg>
                        暂停
                      </>
                    ) : (
                      <>
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <polygon points="5,3 19,12 5,21" />
                        </svg>
                        试听
                      </>
                    )}
                  </button>
                </button>
              )
            })}
          </div>

          {/* Clone voice upload */}
          <div
            className={`p-4 rounded-[12px] border border-dashed ${
              isDark
                ? 'border-[var(--color-border-subtle)] bg-[var(--color-glass-35)]'
                : 'border-[rgba(255,183,197,0.4)] bg-[rgba(255,183,197,0.08)]'
            }`}
          >
            <div className="flex items-start gap-3 mb-3">
              <div className="w-[40px] h-[40px] rounded-full bg-gradient-to-br from-[#FFB7C5] to-[#FF8FAB] flex items-center justify-center shrink-0">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="white"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-semibold text-[var(--color-ink)] mb-1">
                  克隆专属音色
                </p>
                <p className="text-[11px] text-[var(--color-text-muted)] leading-relaxed">
                  上传 3-10 分钟音频（mp3/wav/m4a）或视频（mp4/mov），不含背景音。消耗{' '}
                  {cloneCost} 币
                </p>
              </div>
            </div>
            <button
              onClick={() => cloneInputRef.current?.click()}
              disabled={!canCloneFish}
              className="w-full h-[40px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[14px] font-semibold active:scale-[0.98] transition-transform disabled:opacity-50 disabled:active:scale-100"
            >
              {canCloneFish ? '选择音频或视频' : '升级会员解锁'}
            </button>
            <input
              ref={cloneInputRef}
              type="file"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) {
                  e.target.value = ''
                  handleCloneFileSelected(file)
                }
              }}
            />
          </div>
        </div>

        {/* Footer buttons */}
        <div className="sticky bottom-0 px-5 py-3 border-t border-[var(--color-border-subtle)] bg-inherit flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 h-[44px] rounded-full border border-[var(--color-border)] text-[var(--color-text-secondary)] text-[15px] font-medium active:scale-[0.98] transition-transform"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedPreset}
            className="flex-1 h-[44px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[15px] font-semibold active:scale-[0.98] transition-transform disabled:opacity-50 disabled:active:scale-100"
          >
            确定
          </button>
        </div>
      </div>

      {/* Video-to-audio confirmation dialog */}
      {pendingCloneFile && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-[110]"
            onClick={() => setPendingCloneFile(null)}
          />
          <div
            className={`fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[111] w-[min(340px,90vw)] rounded-[20px] p-5 ${
              isDark ? 'bg-[var(--color-surface-card)]' : 'bg-white'
            }`}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-[17px] font-semibold text-[var(--color-ink)] mb-2">
              视频转音频克隆
            </h3>
            <p className="text-[14px] text-[var(--color-text-secondary)] leading-relaxed mb-5">
              已选择视频文件，系统将提取音频用于克隆。请确保视频中的语音清晰且无背景音。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setPendingCloneFile(null)}
                className="flex-1 h-[42px] rounded-full border border-[var(--color-border)] text-[var(--color-text-secondary)] text-[14px] font-medium"
              >
                取消
              </button>
              <button
                onClick={() => confirmClone(pendingCloneFile)}
                className="flex-1 h-[42px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[14px] font-semibold"
              >
                确认克隆
              </button>
            </div>
          </div>
        </>
      )}
    </>
  )
}
