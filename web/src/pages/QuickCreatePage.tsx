import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToastStore } from '../stores/toastStore'
import { ApiError, quickPrefill, uploadCharacterCover } from '../services/api'
import { compressImageToTarget } from '../utils/imageCompress'
import { CreateShell, FieldCard, textInputCls } from '../components/create/CreateShell'

/**
 * 快速创建页 - 批3 + 批4（批6 视觉重构）
 *
 * 只问四项：封面(3:4)、名字(1-20字)、性别、人设(20-1500字)
 * 下一步调用 AI 预填，跳转确认页(可见性选择在确认页)
 */
export function QuickCreatePage() {
  const navigate = useNavigate()
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

    setPrefilling(true)
    try {
      const prefill = await quickPrefill({ display_name: name, gender, persona })
      navigate('/characters/new/quick/confirm', {
        state: { base: { coverUrl, name, gender, persona }, prefill },
      })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'AI 预填失败，请重试'
      showToast(msg, 'error')
    } finally {
      setPrefilling(false)
    }
  }

  return (
    <CreateShell title="快速创建" backLabel="返回创作中心" onBack={() => navigate('/create')}
      footer={
        <div className="fixed bottom-0 left-0 right-0 px-5 pb-[env(safe-area-inset-bottom,20px)] pt-3 z-30 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)] to-transparent">
          <button
            onClick={handleNext}
            disabled={!canSubmit || prefilling}
            className="w-full h-[52px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[0_8px_28px_-4px_rgba(255,143,171,0.45)] active:scale-[0.98] transition-transform disabled:opacity-45 disabled:active:scale-100"
          >
            {prefilling ? 'AI 生成中...' : '下一步'}
          </button>
        </div>
      }
    >
      {/* 引导语 */}
      <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-5 px-1">
        填这四项，剩下交给 AI。几十秒后你会拿到一个能直接聊天的角色。
      </p>

      {/* 封面 hero 上传（模式2 单一 hero 元素） */}
      <div className="mb-5">
        <label
          className={`relative block w-full aspect-[3/4] max-h-[380px] rounded-[20px] cursor-pointer overflow-hidden group ${
            coverUrl
              ? 'shadow-[0_12px_40px_-8px_rgba(0,0,0,0.3)]'
              : 'border-2 border-dashed border-[var(--color-border-glass)] bg-[var(--color-glass-35)]'
          }`}
        >
          {uploading ? (
            <div className="w-full h-full flex items-center justify-center">
              <span className="text-[14px] text-[var(--color-text-secondary)]">上传中...</span>
            </div>
          ) : coverUrl ? (
            <>
              <img src={coverUrl} alt="封面" className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-transparent" />
              <span className="absolute bottom-3 left-4 text-[13px] text-white/90 font-medium">点击更换封面</span>
            </>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center gap-3">
              <div className="w-[56px] h-[56px] rounded-full bg-gradient-to-br from-[#FFB7C5]/30 to-[#FF8FAB]/20 flex items-center justify-center">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <path d="M21 15l-5-5L5 21" />
                </svg>
              </div>
              <span className="text-[14px] text-[var(--color-ink)] font-medium">上传封面</span>
              <span className="text-[12px] text-[var(--color-text-muted)]">建议 3:4 竖图，人物居中</span>
            </div>
          )}
          <input type="file" accept="image/*" onChange={handleCoverUpload} className="hidden" />
        </label>
      </div>

      {/* 名字 */}
      <FieldCard label="名字">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value.slice(0, 20))}
          placeholder="给 Ta 起个名字"
          maxLength={20}
          className={textInputCls}
        />
        <div className="mt-1.5 text-[12px] text-[var(--color-text-muted)] text-right">{name.length}/20</div>
      </FieldCard>

      {/* 性别 */}
      <FieldCard label="性别">
        <div className="flex gap-3">
          {(['male', 'female'] as const).map((g) => (
            <button
              key={g}
              onClick={() => setGender(g)}
              className={`flex-1 h-[48px] rounded-[14px] text-[15px] font-medium transition-all ${
                gender === g
                  ? 'bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white shadow-[0_4px_16px_rgba(255,143,171,0.32)]'
                  : 'bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
              }`}
            >
              {g === 'male' ? '男' : '女'}
            </button>
          ))}
        </div>
      </FieldCard>

      {/* 人设 */}
      <FieldCard label="人设描述" hint="20-1500 字">
        <textarea
          value={persona}
          onChange={(e) => setPersona(e.target.value.slice(0, 1500))}
          placeholder="描述 Ta 的性格、背景、说话方式..."
          maxLength={1500}
          rows={7}
          className={`w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors`}
        />
        <div className="mt-1.5 flex items-center justify-between text-[12px]">
          <span className={personaLength < 20 ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}>
            {personaLength < 20 ? `还需 ${20 - personaLength} 字` : ''}
          </span>
          <span className="text-[var(--color-text-muted)]">{personaLength}/1500</span>
        </div>
      </FieldCard>
    </CreateShell>
  )
}
