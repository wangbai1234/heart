import type { ElementType, ReactNode } from 'react'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { useAuthStore } from '../stores/authStore'
import { useCreditsStore } from '../stores/creditsStore'
import { useMembershipStore } from '../stores/membershipStore'
import { Avatar } from '../components/ui/Avatar'
import { Switch } from '../components/ui/Switch'
import { Slider } from '../components/ui/Slider'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { Dialog } from '../components/ui/Dialog'
import { Button } from '../components/ui/Button'
import { Toast } from '../components/ui/Toast'
import { BottomSheet } from '../components/ui/BottomSheet'
import { MuteTimePicker } from '../components/ui/MuteTimePicker'
import { logout as apiLogout, clearConversations, deleteAccount, exportData } from '../services/api'

export function SettingsPage() {
  const navigate = useNavigate()
  const { theme, setTheme, resolvedTheme } = useThemeStore()
  const { userAvatar, fontScale, setFontScale, muteStart, muteStartMin, muteEnd, muteEndMin, isMuteNever, setMuteTime, setMuteNever, pushEnabled, setPushEnabled } = useAppStore()
  const user = useAuthStore((s) => s.user)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const clearSession = useAuthStore((s) => s.clearSession)
  const { balance, refresh: refreshCredits } = useCreditsStore()
  const membershipTier = useMembershipStore((s) => s.tier)
  const refreshMembership = useMembershipStore((s) => s.refresh)
  const [showLogoutDialog, setShowLogoutDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deleteStep, setDeleteStep] = useState<1 | 2>(1)
  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [showClearDialog, setShowClearDialog] = useState(false)
  const [showMuteSheet, setShowMuteSheet] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })

  useEffect(() => { refreshCredits() }, [refreshCredits])
  useEffect(() => { refreshMembership() }, [refreshMembership])

  const TIER_LABELS: Record<string, string> = { free: '体验版', plus: '进阶版', immersive: '沉浸版' }

  const themeLabel = theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '自动'

  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色聊天背景图.png'
    : '/assets/backgrounds/聊天背景图.png'

  const displayName = user?.display_name || user?.email?.split('@')[0] || '用户'

  const handleLogout = async () => {
    try { await apiLogout(refreshToken || undefined) } catch { /* ignore */ }
    clearSession()
    setShowLogoutDialog(false)
    navigate('/login', { replace: true })
  }

  const handleClearConversations = async () => {
    try {
      await clearConversations()
      setToast({ visible: true, message: '聊天缓存已清除' })
    } catch {
      setToast({ visible: true, message: '清除失败，请重试' })
    }
    setShowClearDialog(false)
  }

  const handleExportData = async () => {
    try {
      const data = await exportData()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `yuoyuo-export-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
      setToast({ visible: true, message: '数据导出成功' })
    } catch {
      setToast({ visible: true, message: '导出失败，请重试' })
    }
  }

  const handleDeleteAccount = async () => {
    if (deleteStep === 1) {
      setDeleteStep(2)
      return
    }
    // Step 2: confirm
    if (deleteConfirmText !== (user?.email || '')) return
    try {
      await deleteAccount(user?.email || '')
      clearSession()
      navigate('/login', { replace: true })
    } catch {
      setToast({ visible: true, message: '注销失败，请重试' })
    }
    setShowDeleteDialog(false)
    setDeleteStep(1)
    setDeleteConfirmText('')
  }

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {/* Background */}
      <img
        src={bgImage}
        alt=""
        className="absolute inset-0 w-full h-full object-cover z-0"
      />

      {/* Status bar */}
      <div style={{ height: 'var(--safe-top)' }} />

      {/* Navigation bar */}
      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button onClick={() => navigate(-1)} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <ScaledText as="span" className="text-[18px] font-medium text-[var(--color-ink)]" center>
          设置
        </ScaledText>
        <div className="w-[44px]" />
      </nav>

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-10">
        {/* Profile Card — clickable */}
        <button
          onClick={() => navigate('/settings/profile')}
          className="w-full bg-[var(--color-glass-card)] backdrop-blur-[20px] rounded-[24px] shadow-[var(--shadow-card)] p-5 flex items-center gap-4 mb-5 mt-4 border border-[var(--color-border-glass)] text-left active:scale-[0.99] transition-transform"
        >
          <Avatar src={userAvatar || user?.avatar_url || undefined} size={56} border />
          <div className="flex-1 min-w-0">
            <ScaledText as="p" className="text-[18px] font-semibold text-[var(--color-ink)]">
              {displayName}
            </ScaledText>
            <ScaledText as="span" className="inline-block mt-1 text-[12px] font-medium text-[var(--color-primary)] bg-[rgba(255,183,197,0.20)] rounded-full px-3 py-[2px]">
              {balance} yuoyuo币
            </ScaledText>
          </div>
          <span className="text-[var(--color-chevron)]">{'>'}</span>
        </button>

        {/* 我的会员 */}
        <SectionLabel>我的会员</SectionLabel>
        <GroupCard>
          <SettingRow icon={<CrownIcon />} label="会员中心" value={TIER_LABELS[membershipTier] ?? '体验版'} chevron onClick={() => navigate('/membership')} />
          <SettingRow icon={<WalletIcon />} label="yuoyuo币钱包" value={`${balance}`} chevron onClick={() => navigate('/wallet')} />
          <SettingRow icon={<InviteIcon />} label="邀请好友" chevron onClick={() => navigate('/invite')} />
        </GroupCard>

        {/* 角色创作 */}
        <SectionLabel>角色创作</SectionLabel>
        <GroupCard>
          <SettingRow icon={<PencilSparkleIcon />} label="我的自创角色" chevron onClick={() => navigate('/my-characters')} />
          <SettingRow icon={<PlusCircleIcon />} label="创建新角色" chevron onClick={() => navigate('/characters/new')} />
        </GroupCard>

        {/* 外观 */}
        <SectionLabel>外观</SectionLabel>
        <GroupCard>
          <div className="flex items-center justify-between px-5 h-[56px]">
            <div className="flex items-center gap-3">
              <PaletteIcon />
              <ScaledText as="span" className="text-[15px] text-[var(--color-ink)]">
                主题
              </ScaledText>
            </div>
            <div className="w-[180px]">
              <SegmentedControl
                options={['浅色', '深色', '自动']}
                value={themeLabel}
                onChange={(v) => {
                  const map = { '浅色': 'light', '深色': 'dark', '自动': 'system' } as const
                  setTheme(map[v as keyof typeof map])
                }}
                textClassName="settings-scale-text"
              />
            </div>
          </div>
          <Divider />
          <div className="px-5 py-4">
            <div className="flex items-center gap-3 mb-3">
              <TextAIcon />
              <ScaledText as="span" className="text-[15px] text-[var(--color-ink)]">
                字体大小
              </ScaledText>
            </div>
            <Slider value={fontScale} onChange={setFontScale} labelClassName="settings-scale-text" />
          </div>
        </GroupCard>

        {/* 通知 */}
        <SectionLabel>通知</SectionLabel>
        <GroupCard>
          <div className="flex items-center justify-between px-5 h-[56px] opacity-50">
            <div className="flex items-center gap-3">
              <BellIcon />
              <ScaledText as="span" className="text-[15px] text-[var(--color-ink)]">
                推送提醒
              </ScaledText>
              <ScaledText as="span" className="text-[11px] text-[var(--color-text-muted)]">
                即将上线
              </ScaledText>
            </div>
            <Switch checked={pushEnabled} onChange={setPushEnabled} disabled />
          </div>
          <Divider />
          <SettingRow icon={<MoonIcon />} label="静音时段" value={isMuteNever ? '永不' : `${muteStart}:${muteStartMin} – ${muteEnd}:${muteEndMin}`} chevron onClick={() => setShowMuteSheet(true)} />
        </GroupCard>

        {/* 隐私与数据 */}
        <SectionLabel>隐私与数据</SectionLabel>
        <GroupCard>
          <SettingRow icon={<LogoutIcon />} label="退出登录" onClick={() => setShowLogoutDialog(true)} />
          <Divider />
          <SettingRow icon={<TrashIcon />} label="清除聊天缓存" onClick={() => setShowClearDialog(true)} />
          <Divider />
          <SettingRow icon={<DownloadIcon />} label="导出我的数据" onClick={handleExportData} />
          <Divider />
          <SettingRow icon={<WarningIcon />} label="注销账号" danger onClick={() => { setDeleteStep(1); setDeleteConfirmText(''); setShowDeleteDialog(true) }} />
        </GroupCard>

        {/* 关于 */}
        <SectionLabel>关于</SectionLabel>
        <GroupCard>
          <SettingRow icon={<InfoIcon />} label="版本" value="1.0.0" />
          <SettingRow icon={<DocIcon />} label="用户协议" chevron onClick={() => navigate('/legal/terms')} />
          <SettingRow icon={<DocIcon />} label="隐私政策" chevron onClick={() => navigate('/legal/privacy')} />
          <SettingRow icon={<MailIcon />} label="联系我们" chevron onClick={() => window.location.href = 'mailto:support@yuoyuo.app'} />
        </GroupCard>
      </div>

      {/* Logout Dialog */}
      <Dialog open={showLogoutDialog} onClose={() => setShowLogoutDialog(false)} title="确认退出登录？">
        <ScaledText as="p" className="text-[15px] text-[var(--color-text-secondary)] leading-[1.6]">
          退出后需要重新通过邮箱链接登录。
        </ScaledText>
        <div className="flex gap-3 mt-4">
          <Button variant="ghost" size="sm" onClick={() => setShowLogoutDialog(false)} className="flex-1">
            取消
          </Button>
          <Button variant="danger" size="sm" onClick={handleLogout} className="flex-1">
            确认退出
          </Button>
        </div>
      </Dialog>

      {/* Clear Conversations Dialog */}
      <Dialog open={showClearDialog} onClose={() => setShowClearDialog(false)} title="清除聊天缓存">
        <ScaledText as="p" className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
          这会清空当前设备与云端的聊天对话记录。yuoyuo 对你的长期了解（TA 记住的关于你的事）不会被删除——如需彻底删除，请使用「注销账号」。此操作不可撤销。
        </ScaledText>
        <div className="flex gap-3 mt-4">
          <Button variant="ghost" size="sm" onClick={() => setShowClearDialog(false)} className="flex-1">
            取消
          </Button>
          <Button variant="primary" size="sm" onClick={handleClearConversations} className="flex-1">
            确认清除
          </Button>
        </div>
      </Dialog>

      {/* Delete Account Dialog — 2-step */}
      <Dialog
        open={showDeleteDialog}
        onClose={() => { setShowDeleteDialog(false); setDeleteStep(1); setDeleteConfirmText('') }}
        title={deleteStep === 1 ? '注销账号' : '确认永久删除'}
      >
        {deleteStep === 1 ? (
          <>
            <ScaledText as="p" className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
              注销后，yuoyuo 会在 30 天后永久删除你的全部数据：聊天记录、TA 对你的所有记忆、情绪与关系进展、你的 yuoyuo币余额。此后无法恢复。
            </ScaledText>
            <ScaledText as="p" className="text-[14px] text-[var(--color-danger)] leading-[1.7] mt-2">
              你当前还有 {balance} yuoyuo币，注销后将一并清空且不予退还。
            </ScaledText>
            <div className="flex gap-3 mt-4">
              <Button variant="ghost" size="sm" onClick={() => setShowDeleteDialog(false)} className="flex-1">
                再想想
              </Button>
              <Button variant="danger" size="sm" onClick={handleDeleteAccount} className="flex-1" style={{ background: 'var(--color-danger)' }}>
                我了解，继续注销
              </Button>
            </div>
          </>
        ) : (
          <>
            <ScaledText as="p" className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              请输入你的邮箱 <strong className="text-[var(--color-ink)]">{user?.email}</strong> 以确认永久删除。
            </ScaledText>
            <input
              type="email"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="输入邮箱确认"
              className="w-full px-4 py-3 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-divider-inset)] text-[16px] text-[var(--color-ink)] outline-none mb-4"
            />
            <div className="flex gap-3">
              <Button variant="ghost" size="sm" onClick={() => setDeleteStep(1)} className="flex-1">
                返回
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== user?.email}
                className="flex-1"
              >
                确认注销
              </Button>
            </div>
          </>
        )}
      </Dialog>

      {/* Mute Time Picker */}
      <BottomSheet open={showMuteSheet} onClose={() => setShowMuteSheet(false)}>
        <MuteTimePicker
          startHour={muteStart}
          startMin={muteStartMin}
          endHour={muteEnd}
          endMin={muteEndMin}
          isNever={isMuteNever}
          onChangeTime={setMuteTime}
          onChangeNever={setMuteNever}
          onConfirm={() => {
            setShowMuteSheet(false)
            setToast({ visible: true, message: isMuteNever ? '已设为永不静音' : `静音时段已设为 ${muteStart}:${muteStartMin} – ${muteEnd}:${muteEndMin}` })
          }}
        />
      </BottomSheet>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </div>
  )
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="text-[13px] text-[var(--color-text-muted)] px-1 mt-5 mb-2">
      <ScaledText as="span" className="settings-scale-text">
        {children}
      </ScaledText>
    </div>
  )
}

function GroupCard({ children }: { children: ReactNode }) {
  return (
    <div className="bg-[var(--color-glass-card)] backdrop-blur-[20px] rounded-[20px] shadow-[var(--shadow-card)] overflow-hidden border border-[var(--color-border-glass)] mb-2">
      {children}
    </div>
  )
}

function SettingRow({
  icon,
  label,
  value,
  chevron,
  danger,
  onClick,
}: {
  icon: ReactNode
  label: string
  value?: string
  chevron?: boolean
  danger?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between px-5 h-[56px] active:bg-[rgba(255,183,197,0.10)] transition-colors"
    >
      <div className="flex items-center gap-3">
        <span className={danger ? 'text-[var(--color-danger)]' : 'text-[var(--color-primary)]'}>{icon}</span>
        <ScaledText as="span" className={`text-[15px] ${danger ? 'text-[var(--color-danger)]' : 'text-[var(--color-ink)]'}`}>
          {label}
        </ScaledText>
      </div>
      <div className="flex items-center gap-2">
        {value && (
          <ScaledText as="span" className="text-[13px] text-[var(--color-text-secondary)]">
            {value}
          </ScaledText>
        )}
        {chevron && (
          <svg width="8" height="14" viewBox="0 0 8 14" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1,1 7,7 1,13" />
          </svg>
        )}
      </div>
    </button>
  )
}

function Divider() {
  return <div className="h-px bg-[var(--color-divider-inset)] ml-[56px]" />
}

type ScaledTextProps = {
  as: ElementType
  children: ReactNode
  className?: string
  center?: boolean
}

function ScaledText({ as: Component, children, className = '' }: ScaledTextProps) {
  return (
    <Component className={className}>
      {children}
    </Component>
  )
}

/* ── Icons ─────────────────────────────────────────────────────── */
function LogoutIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16,17 21,12 16,7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
}
function CrownIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M2 20h20L19 8l-5 5-2-7-2 7-5-5-3 12z" /></svg>
}
function WalletIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" /><path d="M16 12h2" /><path d="M3 8h14" /></svg>
}
function InviteIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><line x1="19" y1="8" x2="19" y2="14" /><line x1="22" y1="11" x2="16" y2="11" /></svg>
}
function PaletteIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="8" r="1.5" fill="var(--color-primary)" /><circle cx="8" cy="12" r="1.5" fill="var(--color-primary)" /><circle cx="16" cy="12" r="1.5" fill="var(--color-primary)" /><circle cx="12" cy="16" r="1.5" fill="var(--color-primary)" /></svg>
}
function TextAIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M6 20L12 4l6 16" /><path d="M8 14h8" /></svg>
}
function BellIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
}
function MoonIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
}
function TrashIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><polyline points="3,6 5,6 21,6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
}
function DownloadIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7,10 12,15 17,10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
}
function WarningIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-danger)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
}
function InfoIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" /></svg>
}
function DocIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14,2 14,8 20,8" /></svg>
}
function MailIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" /><polyline points="22,4 12,13 2,4" /></svg>
}
function PencilSparkleIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" /></svg>
}
function PlusCircleIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" /></svg>
}
