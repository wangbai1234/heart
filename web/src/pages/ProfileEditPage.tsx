import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useThemeStore } from '../stores/themeStore'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { Toast } from '../components/ui/Toast'
import { BottomSheet } from '../components/ui/BottomSheet'
import { DatePicker } from '../components/ui/DatePicker'
import { getProfile, updateProfile, uploadAvatar } from '../services/api'

function compressImage(file: File, maxSize: number): Promise<File> {
  return new Promise((resolve) => {
    const objectUrl = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      const canvas = document.createElement('canvas')
      let { width, height } = img
      if (width > maxSize || height > maxSize) {
        if (width > height) {
          height = (height / width) * maxSize
          width = maxSize
        } else {
          width = (width / height) * maxSize
          height = maxSize
        }
      }
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d')!.drawImage(img, 0, 0, width, height)
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const webpName = file.name.replace(/\.[^.]+$/, '.webp')
            resolve(new File([blob], webpName, { type: 'image/webp' }))
          } else {
            resolve(file)
          }
        },
        'image/webp',
        0.85,
      )
    }
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      resolve(file)
    }
    img.src = objectUrl
  })
}

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
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const { resolvedTheme } = useThemeStore()
  const pageBg = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'
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
    setLoading(true)
    try {
      const res = await updateProfile({
        display_name: trimmedName,
        gender,
        birthdate: birthdate || undefined,
      })
      if (res.age_verified === false) {
        setUser({ birthdate })
        setToast({ visible: true, message: '未满 18 周岁，无法使用本产品' })
        setTimeout(() => navigate('/age-gate', { replace: true }), 1500)
      } else {
        setUser({ display_name: trimmedName, gender, birthdate, age_verified: res.age_verified === true })
        setToast({ visible: true, message: '保存成功' })
        setTimeout(() => navigate('/home', { replace: true }), 800)
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
    <div className="relative w-full h-full overflow-hidden">
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />
      <div className="relative z-10 w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-4 pb-3" style={{ paddingTop: 'var(--safe-top)' }}>
        <button onClick={() => navigate(-1 as any)} className="w-[44px] h-[44px] flex items-center justify-center active:opacity-60 transition-opacity" aria-label="返回">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <h2 className="text-[17px] font-semibold text-[var(--color-ink)]">编辑资料</h2>
        <div style={{ width: 40 }} />
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-8">
        {/* Age gate notice */}
        <div className="bg-[var(--color-glass-35)] rounded-[16px] p-4 mb-4">
          <p className="text-[12px] text-[var(--color-text-secondary)] leading-[1.6]">
            yuoyuo 是面向成年人的情感陪伴产品。继续即表示你确认已年满 18 周岁。我们会根据你填写的出生日期进行校验。
          </p>
        </div>

        {/* Avatar */}
        <div className="flex flex-col items-center mb-6">
          <label className={`relative ${avatarUploading ? 'cursor-wait' : 'cursor-pointer'}`}>
            <div className="w-20 h-20 rounded-full bg-[var(--color-primary)] flex items-center justify-center text-white text-[28px] font-bold overflow-hidden">
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
            <div className="absolute bottom-0 right-0 w-6 h-6 rounded-full bg-[var(--color-ink)] flex items-center justify-center">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M12 20h9M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
            </div>
          </label>
          <p className="text-[12px] text-[var(--color-text-muted)] mt-2">
            {avatarUploading ? '上传中…' : '点击更换头像'}
          </p>
        </div>

        {/* Form */}
        <div className="space-y-4">
          <div>
            <label className="text-[13px] text-[var(--color-text-secondary)] mb-1 block">昵称</label>
            <Input placeholder="1-20 个字符" value={displayName} onChange={setDisplayName} />
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
              className="w-full px-4 py-3 rounded-[12px] bg-[var(--color-glass-35)] backdrop-blur-[12px] border border-[var(--color-divider-inset)] text-[15px] text-left outline-none focus:border-[var(--color-primary)] transition-colors"
            >
              {birthdate ? (
                <span className="text-[var(--color-ink)]">{formatBirthdate(birthdate)}</span>
              ) : (
                <span className="text-[var(--color-text-placeholder)]">请选择出生日期</span>
              )}
            </button>
          </div>
        </div>

        <div className="mt-6">
          <Button variant="primary" size="lg" loading={loading} onClick={handleSave}>
            保存
          </Button>
        </div>
      </div>

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
    </div>
  )
}
