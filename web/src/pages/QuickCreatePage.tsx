import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToastStore } from '../stores/toastStore'
import { ApiError, quickPrefill, uploadCharacterCover } from '../services/api'
import { compressImageToTarget } from '../utils/imageCompress'
import { CreateShell, FieldCard, textInputCls } from '../components/create/CreateShell'

/**
 * 快速创建页 - 批3/4（视觉重构对齐 nimoo quickCreation）
 *
 * 布局参照 nimoo：小尺寸左置封面(112×152, 3:4) + 右侧说明，紧凑字段。
 * 四项必填：封面、名字、性别、人设。按钮任意时刻可点，缺项走 toast 提示。
 * 按钮文案「AI 快速创建」——诚实表达点击即触发 AI 生成，非单纯翻页。
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

  async function handleCoverUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const compressed = await compressImageToTarget(file, 900 * 1024)
      const { cover_url } = await uploadCharacterCover(compressed)
      setCoverUrl(cover_url)
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : '封面上传失败，请重试', 'error')
    } finally {
      setUploading(false)
    }
  }

  /** 校验缺项 → 返回第一条提示文案；全部通过返回 null。 */
  function firstMissing(): string | null {
    if (!coverUrl) return '请上传角色封面'
    if (!name.trim()) return '请填写角色名字'
    if (!gender) return '请选择性别'
    if (persona.trim().length < 20) return '角色描述至少 20 字'
    return null
  }

  async function handleCreate() {
    const missing = firstMissing()
    if (missing) {
      showToast(missing, 'error')
      return
    }
    setPrefilling(true)
    try {
      const prefill = await quickPrefill({
        display_name: name,
        gender: gender as 'male' | 'female',
        persona,
      })
      navigate('/characters/new/quick/confirm', {
        state: { base: { coverUrl, name, gender, persona }, prefill },
      })
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : 'AI 生成失败，请重试', 'error')
    } finally {
      setPrefilling(false)
    }
  }

  const personaLen = persona.length

  return (
    <CreateShell
      title="快速创建"
      backLabel="返回创作中心"
      onBack={() => navigate('/create')}
      footer={
        <div className="fixed bottom-0 left-0 right-0 px-5 pb-[env(safe-area-inset-bottom,20px)] pt-3 z-30 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)] to-transparent">
          <button
            onClick={handleCreate}
            disabled={prefilling}
            className="w-full h-[50px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[16px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.40)] active:scale-[0.98] transition-transform disabled:opacity-60"
          >
            {prefilling ? 'AI 生成中...' : 'AI 快速创建'}
          </button>
        </div>
      }
    >
      <p className="text-[13px] text-[var(--color-text-secondary)] leading-[1.6] mb-4">
        简单填写，AI 帮你把角色卡补全。几十秒后就能直接开聊。
      </p>

      {/* 封面：小尺寸左置 + 右侧说明（对齐 nimoo） */}
      <FieldCard label="角色封面" required>
        <div className="flex gap-3.5">
          <label
            className={`relative shrink-0 w-[104px] h-[140px] rounded-[12px] cursor-pointer overflow-hidden ${
              coverUrl ? '' : 'border-2 border-dashed border-[var(--color-border-glass)] bg-[var(--color-glass-55)]'
            }`}
          >
            {uploading ? (
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
            <li>· 请勿上传涉及未成年或过度暴露的图像</li>
          </ul>
        </div>
      </FieldCard>

      {/* 名字 */}
      <FieldCard label="角色名字" required>
        <input
          value={name}
          onChange={(e) => setName(e.target.value.slice(0, 20))}
          placeholder="给 Ta 起个名字"
          maxLength={20}
          className={`${textInputCls} h-[44px]`}
        />
      </FieldCard>

      {/* 性别 */}
      <FieldCard label="性别" required>
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
      </FieldCard>

      {/* 人设 */}
      <FieldCard label="角色描述" required hint="至少 20 字">
        <textarea
          value={persona}
          onChange={(e) => setPersona(e.target.value.slice(0, 1500))}
          placeholder="一句话介绍你的角色，包括性格、背景、说话方式。例：清冷孤傲的剑修，话少但护短……"
          maxLength={1500}
          rows={4}
          className="w-full px-3.5 py-2.5 rounded-[12px] text-[14px] leading-[1.6] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
        <div className="mt-1 flex items-center justify-between text-[12px]">
          <span className={personaLen > 0 && personaLen < 20 ? 'text-[var(--color-error)]' : 'text-transparent'}>
            {personaLen > 0 && personaLen < 20 ? `还需 ${20 - personaLen} 字` : '·'}
          </span>
          <span className="text-[var(--color-text-muted)]">{personaLen}/1500</span>
        </div>
      </FieldCard>
    </CreateShell>
  )
}
