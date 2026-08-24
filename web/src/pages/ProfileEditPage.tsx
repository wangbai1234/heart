import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { Toast } from '../components/ui/Toast'
import { BottomSheet } from '../components/ui/BottomSheet'
import { DatePicker } from '../components/ui/DatePicker'
import { getProfile, updateProfile, uploadAvatar } from '../services/api'
import { compressImage } from '../utils/imageCompress'
import { useSafeBack } from '../hooks/useSafeBack'
import { AppPageContent, AppPageShell } from '../components/ui/AppPageShell'

function formatBirthdate(iso: string): string {
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return ''
  return `${m[1]}年${parseInt(m[2])}月${parseInt(m[3])}日`
}

const GENDER_OPTIONS = [
  { label: '女', value: 'female' },
  { label: '男', value: 'male' },
  { label: '其他', value: 'nonbinary' },
  { label: '不透露', value: 'undisclosed' },
]

export function ProfileEditPage() {
  const navigate = useNavigate()
  const goBack = useSafeBack('/settings')
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [gender, setGender] = useState(user?.gender || 'undisclosed')
  const [birthdate, setBirthdate] = useState(user?.birthdate || '')
  const [loading, setLoading] = useState(false)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })
  const [showDatePicker, setShowDatePicker] = useState(false)

  useEffect(() => {
    getProfile().then((data) => {
      const u = data.user
      setDisplayName(u.display_name || '')
      setGender(u.gender || 'undisclosed')
      setBirthdate(u.birthdate || '')
    }).catch(() => {})
  }, [])

  const handleSave = async () => {
    const trimmedName = displayName.trim()
    if (!trimmedName) {
      setToast({ visible: true, message: '请输入昵称' })
      return
    }
    if ([...trimmedName].length > 20) {
      setToast({ visible: true, message: '昵称最多 20 个字符' })
      return
    }
    if (!birthdate) {
      setToast({ visible: true, message: '请选择出生日期' })
      return
    }
    setLoading(true)
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
      const res = await updateProfile({
        display_name: trimmedName,
        gender,
        birthdate,
        ...(timezone ? { timezone } : {}),
      })
      if (res.age_verified === false) {
        setUser({ birthdate })
        setToast({ visible: true, message: '未满 18 周岁，无法使用本产品' })
        setTimeout(() => navigate('/age-gate', { replace: true }), 1500)
      } else {
        setUser({ display_name: trimmedName, gender, birthdate, age_verified: res.age_verified === true })
        setToast({ visible: true, message: '保存成功' })
        setTimeout(() => navigate('/character', { replace: true }), 800)
      }
    } catch (err: any) {
      setToast({ visible: true, message: err.message || '保存失败' })
    } finally {
      setLoading(false)
    }
  }

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setAvatarUploading(true)
    try {
      const compressed = await compressImage(file, 512).catch(() => file)
      const res = await uploadAvatar(compressed)
      setUser({ avatar_url: res.avatar_url })
      setToast({ visible: true, message: '头像更新成功' })
    } catch {
      setToast({ visible: true, message: '头像上传失败' })
    } finally {
      setAvatarUploading(false)
    }
  }

  return (
    <AppPageShell>
      <div className="flex h-full w-full flex-col">
      {/* Header */}
      <AppPageContent size="form" className="flex items-center justify-between px-2 pb-2" style={{ paddingTop: 'var(--safe-top)' }}>
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center active:opacity-60 transition-opacity" aria-label="返回">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <h1 className="text-[17px] font-semibold text-[var(--color-ink)]">编辑资料</h1>
        <div style={{ width: 40 }} />
      </AppPageContent>

      <AppPageContent size="form" className="min-h-0 flex-1 overflow-y-auto px-5 pb-8">
        {/* Avatar */}
        <div className="mb-8 flex flex-col items-center pt-5">
          <label className={`relative ${avatarUploading ? 'cursor-wait' : 'cursor-pointer'}`}>
            <div className="flex h-[88px] w-[88px] items-center justify-center overflow-hidden rounded-full bg-[var(--color-primary-300)] text-[28px] font-bold text-white shadow-[0_8px_24px_rgba(24,24,32,0.12)]">
              {avatarUploading ? (
                <svg className="animate-spin w-8 h-8 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : user?.avatar_url ? (
                <img src={user.avatar_url} alt="avatar" className="w-full h-full object-cover" />
              ) : (
                (displayName || '游')[0]
              )}
            </div>
            <input type="file" accept="image/*" className="hidden" disabled={avatarUploading} onChange={handleAvatarUpload} />
            <div className="absolute bottom-0 right-0 flex h-7 w-7 items-center justify-center rounded-full border-2 border-[var(--color-page-canvas)] bg-[var(--color-ink)]">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M12 20h9M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
            </div>
          </label>
          <p className="text-[12px] text-[var(--color-text-muted)] mt-2">
            {avatarUploading ? '上传中…' : '点击更换头像'}
          </p>
        </div>

        {/* Form */}
        <div className="space-y-5">
          <div>
            <label className="text-[13px] text-[var(--color-text-secondary)] mb-1 block">昵称</label>
            <Input
              placeholder="1-20 个字符"
              value={displayName}
              onChange={setDisplayName}
              className="rounded-[10px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-4 focus-within:border-[var(--color-primary-400)]"
            />
          </div>

          <div>
            <label className="text-[13px] text-[var(--color-text-secondary)] mb-2 block">性别</label>
            <SegmentedControl
              options={GENDER_OPTIONS.map(o => o.label)}
              value={GENDER_OPTIONS.find(o => o.value === gender)?.label ?? '不透露'}
              onChange={(label) => {
                const opt = GENDER_OPTIONS.find(o => o.label === label)
                if (opt) setGender(opt.value)
              }}
            />
          </div>

          <div>
            <label className="text-[13px] text-[var(--color-text-secondary)] mb-1 block">出生日期</label>
            <button
              type="button"
              onClick={() => setShowDatePicker(true)}
              className="w-full rounded-[10px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-4 py-3 text-left text-[15px] outline-none transition-colors focus:border-[var(--color-primary-400)]"
            >
              {birthdate ? (
                <span className="text-[var(--color-ink)]">{formatBirthdate(birthdate)}</span>
              ) : (
                <span className="text-[var(--color-text-placeholder)]">请选择出生日期</span>
              )}
            </button>
            <div className="mt-3 flex items-start gap-2 rounded-[10px] bg-[var(--color-page-soft)] px-3 py-2.5">
              <svg className="mt-0.5 shrink-0 text-[var(--color-text-muted)]" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 11v5" />
                <path d="M12 8h.01" />
              </svg>
              <p className="text-[12px] leading-[1.55] text-[var(--color-text-secondary)]">
                出生日期仅用于确认你已年满 18 周岁。
              </p>
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 mt-8 bg-[var(--color-page-canvas)] pb-3 pt-3">
          <Button variant="primary" size="lg" loading={loading} onClick={handleSave} className="rounded-[12px] bg-[var(--color-primary-500)] shadow-[0_8px_22px_rgba(255,110,138,0.24)]">
            保存
          </Button>
        </div>
      </AppPageContent>

      <div style={{ height: 'var(--safe-bottom)' }} />

      {/* Date Picker BottomSheet */}
      <BottomSheet open={showDatePicker} onClose={() => setShowDatePicker(false)}>
        <DatePicker
          value={birthdate}
          onChange={setBirthdate}
          onConfirm={() => setShowDatePicker(false)}
        />
      </BottomSheet>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
      </div>
    </AppPageShell>
  )
}
