import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useToastStore } from '../stores/toastStore'
import { ApiError, quickPrefill, uploadCharacterCover } from '../services/api'
import { compressImageToTarget } from '../utils/imageCompress'

/**
 * 快速创建页 - 批3 + 批4
 *
 * 只问四项：封面(3:4)、名字(1-20字)、性别、人设(20-1500字)
 * 下一步调用 AI 预填，跳转确认页(可见性选择在确认页)
 */
export function QuickCreatePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'
  const showToast = useToastStore((s) => s.show)

  const [coverUrl, setCoverUrl] = useState('')
  const [name, setName] = useState('')
  const [gender, setGender] = useState<'male' | 'female' | ''>('')
  const [persona, setPersona] = useState('')
  const [uploading, setUploading] = useState(false)
  const [prefilling, setPrefilling] = useState(false)

  const personaLength = persona.length
  const personaValid = personaLength >= 20 && personaLength <= 1500
  const canSubmit = coverUrl && name.length >= 1 && name.length <= 20 && gender && personaValid

  async function handleCoverUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const compressed = await compressImageToTarget(file, 900 * 1024)
      const { cover_url } = await uploadCharacterCover(compressed)
      setCoverUrl(cover_url)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '封面上传失败，请重试'
      showToast(msg, 'error')
    } finally {
      setUploading(false)
    }
  }

  async function handleNext() {
    if (gender === '' || !canSubmit) {
      if (personaLength < 20) {
        showToast('人设描述至少需要 20 字', 'error')
        return
      }
      showToast('请填写完整信息', 'error')
      return
    }

    // 调用 AI 预填 (此处 gender 已收窄为 'male' | 'female')
    setPrefilling(true)
    try {
      const prefill = await quickPrefill({
        display_name: name,
        gender,
        persona,
      })
      // 携带基础信息 + 预填结果跳转确认页
      navigate('/characters/new/quick/confirm', {
        state: {
          base: { coverUrl, name, gender, persona },
          prefill,
        },
      })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'AI 预填失败，请重试'
      showToast(msg, 'error')
    } finally {
      setPrefilling(false)
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
          onClick={() => navigate(-1)}
          className="w-[28px] h-[28px] -ml-1 rounded-full flex items-center justify-center active:bg-[var(--color-glass-55)] transition-colors"
        >
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="8,2 2,8 8,14" />
          </svg>
        </button>
        <span className="flex-1 text-center text-[17px] font-semibold text-[var(--color-ink)] -ml-[28px]">
          快速创建
        </span>
      </nav>

      <div className="relative z-10 flex-1 overflow-y-auto px-5 pb-[120px] pt-4">
        {/* 封面上传 */}
        <div className="mb-6">
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            封面 <span className="text-[var(--color-text-muted)]">(3:4 竖图)</span>
          </label>
          <label
            className={`block w-full aspect-[3/4] max-h-[400px] rounded-[16px] border-2 border-dashed cursor-pointer overflow-hidden ${
              coverUrl
                ? 'border-transparent'
                : isDark
                  ? 'border-[var(--color-border-glass)] bg-[var(--color-glass-55)]'
                  : 'border-[rgba(255,183,197,0.30)] bg-[rgba(255,183,197,0.06)]'
            }`}
          >
            {uploading ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-[14px] text-[var(--color-text-secondary)]">上传中...</div>
              </div>
            ) : coverUrl ? (
              <img src={coverUrl} alt="封面" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center gap-2">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <path d="M21 15l-5-5L5 21" />
                </svg>
                <span className="text-[13px] text-[var(--color-text-muted)]">点击上传封面</span>
              </div>
            )}
            <input
              type="file"
              accept="image/*"
              onChange={handleCoverUpload}
              className="hidden"
            />
          </label>
        </div>

        {/* 名字 */}
        <div className="mb-6">
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">名字</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value.slice(0, 20))}
            placeholder="给 Ta 起个名字"
            maxLength={20}
            className={`w-full h-[50px] px-4 rounded-[12px] text-[15px] placeholder:text-[var(--color-text-muted)] ${
              isDark
                ? 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
                : 'bg-white/80 border border-[rgba(255,183,197,0.20)] text-[var(--color-ink)]'
            }`}
          />
          <div className="mt-1 text-[12px] text-[var(--color-text-muted)] text-right">{name.length}/20</div>
        </div>

        {/* 性别 */}
        <div className="mb-6">
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">性别</label>
          <div className="flex gap-3">
            <button
              onClick={() => setGender('male')}
              className={`flex-1 h-[50px] rounded-[12px] text-[15px] font-medium transition-all ${
                gender === 'male'
                  ? 'bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white shadow-[0_4px_16px_rgba(255,143,171,0.30)]'
                  : isDark
                    ? 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
                    : 'bg-white/80 border border-[rgba(255,183,197,0.20)] text-[var(--color-ink)]'
              }`}
            >
              男
            </button>
            <button
              onClick={() => setGender('female')}
              className={`flex-1 h-[50px] rounded-[12px] text-[15px] font-medium transition-all ${
                gender === 'female'
                  ? 'bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white shadow-[0_4px_16px_rgba(255,143,171,0.30)]'
                  : isDark
                    ? 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
                    : 'bg-white/80 border border-[rgba(255,183,197,0.20)] text-[var(--color-ink)]'
              }`}
            >
              女
            </button>
          </div>
        </div>

        {/* 人设描述 */}
        <div className="mb-6">
          <label className="block text-[14px] font-medium text-[var(--color-ink)] mb-2">
            人设描述 <span className="text-[var(--color-text-muted)]">(20-1500字)</span>
          </label>
          <textarea
            value={persona}
            onChange={(e) => setPersona(e.target.value.slice(0, 1500))}
            placeholder="描述 Ta 的性格、背景、说话方式..."
            maxLength={1500}
            rows={8}
            className={`w-full px-4 py-3 rounded-[12px] text-[15px] leading-[1.65] placeholder:text-[var(--color-text-muted)] resize-none ${
              isDark
                ? 'bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
                : 'bg-white/80 border border-[rgba(255,183,197,0.20)] text-[var(--color-ink)]'
            }`}
          />
          <div className="mt-1 flex items-center justify-between text-[12px]">
            <span className={personaLength < 20 ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}>
              {personaLength < 20 ? `还需 ${20 - personaLength} 字` : ''}
            </span>
            <span className="text-[var(--color-text-muted)]">{personaLength}/1500</span>
          </div>
        </div>
      </div>

      {/* 底部按钮 */}
      <div className="fixed bottom-0 left-0 right-0 px-5 pb-[env(safe-area-inset-bottom,20px)] pt-3 bg-[var(--color-bg-page)] border-t border-[var(--color-border-subtle)] z-30">
        <button
          onClick={handleNext}
          disabled={!canSubmit || prefilling}
          className="w-full h-[50px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform disabled:opacity-50 disabled:active:scale-100"
        >
          {prefilling ? 'AI 生成中...' : '下一步'}
        </button>
      </div>
    </div>
  )
}
