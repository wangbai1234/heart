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
import { logout as apiLogout, clearConversations, deleteAccount, exportData, getInviteStatus } from '../services/api'
import type { InviteStatus } from '../services/api'
import { AppPageContent, AppPageShell } from '../components/ui/AppPageShell'
import { TabBar } from '../components/ui/TabBar'

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
  const [showSettingsSheet, setShowSettingsSheet] = useState(false)
  const [inviteStatus, setInviteStatus] = useState<InviteStatus | null>(null)
  const [toast, setToast] = useState({ visible: false, message: '' })

  useEffect(() => { refreshCredits() }, [refreshCredits])
  useEffect(() => { refreshMembership() }, [refreshMembership])
  useEffect(() => {
    getInviteStatus().then(setInviteStatus).catch(() => {})
  }, [])

  const TIER_LABELS: Record<string, string> = { free: '体验版', plus: '进阶版', immersive: '沉浸版' }
  const PROFILE_TIER_LABELS: Record<string, string> = { free: '普通用户', plus: '进阶版VIP', immersive: '沉浸版VIP' }
  const MEMBERSHIP_HINTS: Record<string, string> = {
    free: '解锁更多陪伴额度与沉浸体验',
    plus: '进阶权益已生效',
    immersive: '沉浸权益已生效',
  }

  const themeLabel = theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '自动'

  const isDark = resolvedTheme === 'dark'
  const memberGemImage = '/assets/settings/member-crown.webp'

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

  const copyInviteCode = async () => {
    if (!inviteStatus?.invite_code) {
      navigate('/invite')
      return
    }
    try {
      await navigator.clipboard.writeText(inviteStatus.invite_code)
      setToast({ visible: true, message: '邀请码已复制' })
    } catch {
      setToast({ visible: true, message: '复制失败，请前往邀请页复制' })
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
    <AppPageShell className="app-atmosphere flex flex-col">
      {/* Status bar */}
      <div style={{ height: 'var(--safe-top)' }} />

      {/* Navigation bar */}
      <AppPageContent size="medium" className="relative z-20 flex h-[58px] shrink-0 items-center justify-between px-4 sm:px-5">
        <ScaledText as="h1" className="text-[24px] font-bold text-[var(--color-ink)]">
          我的
        </ScaledText>
        <button
          onClick={() => setShowSettingsSheet(true)}
          className="flex h-[40px] w-[40px] items-center justify-center rounded-[10px] bg-[var(--color-page-soft)] transition-colors active:opacity-75"
          aria-label="打开设置"
        >
          <SettingsIcon />
        </button>
      </AppPageContent>

      {/* Scrollable content */}
      <div className="relative z-10 mx-auto min-h-0 w-full max-w-[860px] flex-1 overflow-y-auto px-3 pb-[120px] min-[360px]:px-4 sm:px-5">
        <button
          onClick={() => navigate('/settings/profile')}
          className="mb-3 mt-1 w-full px-1 py-4 text-left transition-opacity active:opacity-75 min-[380px]:py-5"
        >
          <div className="flex items-center gap-3 min-[380px]:gap-4">
            <Avatar src={userAvatar || user?.avatar_url || undefined} size={64} border className="shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                <ScaledText as="p" className="text-[22px] font-semibold text-[var(--color-ink)] truncate">
                  {displayName}
                </ScaledText>
                <ScaledText
                  as="span"
                  className={`shrink-0 text-[11px] font-semibold rounded-full px-2.5 py-[3px] ${
                    membershipTier === 'free'
                      ? 'text-[var(--color-text-secondary)] bg-[var(--color-glass-55)]'
                      : 'bg-[var(--color-primary-500)] text-white'
                  }`}
                >
                  {PROFILE_TIER_LABELS[membershipTier] ?? PROFILE_TIER_LABELS.free}
                </ScaledText>
              </div>
              <ScaledText as="p" className="text-[13px] text-[var(--color-text-secondary)] mt-1 truncate">
                {user?.email || '完善资料，让 yuoyuo 更懂你'}
              </ScaledText>
            </div>
            <ChevronIcon />
          </div>
        </button>

        <div className="grid grid-cols-1 gap-2.5 min-[520px]:grid-cols-2 sm:gap-3">
          <WalletPanel
            balance={balance}
            onRecharge={() => navigate('/wallet')}
            onDetails={() => navigate('/credits/transactions')}
          />

          <button
            onClick={() => navigate('/membership')}
            className={`relative h-full min-h-[148px] w-full overflow-hidden rounded-[14px] border p-4 text-left shadow-[0_6px_22px_rgba(24,24,32,0.10)] transition-opacity active:opacity-90 ${
              isDark
                ? 'border-white/10 bg-[linear-gradient(135deg,#24242B,#39343B_54%,#714A57)]'
                : 'border-[rgba(255,110,138,0.18)] bg-[linear-gradient(135deg,#FFFFFF,#FFF4F6_55%,#F1D4DA)]'
            }`}
          >
          <div className="absolute inset-x-0 top-0 h-px bg-white/60" />
          <img
            src={memberGemImage}
            alt=""
            className="pointer-events-none absolute bottom-[-6px] right-[-2px] h-[78px] w-[78px] object-contain drop-shadow-[0_10px_24px_rgba(90,54,68,0.24)] min-[380px]:h-[88px] min-[380px]:w-[88px]"
          />
          <div className="relative min-h-[116px]">
            <div className="relative z-10 flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2 min-w-0">
                <span className={`w-[34px] h-[34px] rounded-[12px] flex items-center justify-center border ${
                  isDark
                    ? 'border-white/14 bg-white/10'
                    : 'border-white/70 bg-white/75'
                }`}>
                  <CrownIcon tone={isDark ? 'light' : 'brand'} />
                </span>
                <ScaledText as="span" className={`text-[16px] font-semibold ${isDark ? 'text-white' : 'text-[var(--color-ink)]'}`}>
                  会员中心
                </ScaledText>
              </div>
              <span className={`shrink-0 rounded-full px-3 py-2 text-[13px] font-semibold shadow-[0_8px_20px_rgba(255,255,255,0.18)] min-[380px]:px-4 ${isDark ? 'bg-white text-[#8C7188]' : 'bg-[#FF9DB6] text-white'}`}>
                查看权益
              </span>
            </div>
            <div className="ml-[2px] mt-5 max-w-[72%] min-w-0">
              <ScaledText as="p" className={`inline-block rounded-full px-3 py-1 text-[12px] font-semibold ${isDark ? 'bg-white/12 text-white' : 'bg-[rgba(255,143,171,0.20)] text-[#E85577]'}`}>
                {TIER_LABELS[membershipTier] ?? '体验版'}会员
              </ScaledText>
              <ScaledText as="p" className={`text-[14px] mt-3 leading-[1.55] ${isDark ? 'text-white/82' : 'text-[var(--color-text-secondary)]'}`}>
                {MEMBERSHIP_HINTS[membershipTier] ?? MEMBERSHIP_HINTS.free}
              </ScaledText>
            </div>
          </div>
          </button>
        </div>

        <InviteShowcase
          code={inviteStatus?.invite_code}
          invitedCount={inviteStatus?.invited_count ?? 0}
          totalReward={inviteStatus?.total_reward ?? 0}
          isDark={isDark}
          onInvite={() => navigate('/invite')}
        />

        {inviteStatus?.invite_code && (
          <InviteCodeCard code={inviteStatus.invite_code} onCopy={copyInviteCode} onOpen={() => navigate('/invite')} />
        )}
      </div>

      <TabBar />

      <BottomSheet open={showSettingsSheet} onClose={() => setShowSettingsSheet(false)}>
        <div className="max-h-[78vh] overflow-y-auto pb-2">
          <div className="flex items-center justify-between mb-3">
            <ScaledText as="h2" className="text-[18px] font-semibold text-[var(--color-ink)]">
              设置
            </ScaledText>
            <button
              onClick={() => setShowSettingsSheet(false)}
              className="w-[36px] h-[36px] flex items-center justify-center rounded-full active:bg-[rgba(255,183,197,0.14)] transition-colors"
              aria-label="关闭设置"
            >
              <CloseIcon />
            </button>
          </div>

          <SectionLabel>外观</SectionLabel>
          <GroupCard>
            <div className="flex min-h-[56px] flex-wrap items-center justify-between gap-3 px-4 py-3 min-[390px]:flex-nowrap min-[390px]:px-5">
              <div className="flex items-center gap-3">
                <PaletteIcon />
                <ScaledText as="span" className="text-[15px] text-[var(--color-ink)]">
                  主题
                </ScaledText>
              </div>
              <div className="w-full min-[390px]:w-[180px]">
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

          <SectionLabel>通知</SectionLabel>
          <GroupCard>
            <div className="flex min-h-[56px] items-center justify-between gap-3 px-4 py-3 opacity-50 min-[390px]:px-5">
              <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
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
            <SettingRow
              icon={<MoonIcon />}
              label="静音时段"
              value={isMuteNever ? '永不' : `${muteStart}:${muteStartMin} – ${muteEnd}:${muteEndMin}`}
              chevron
              onClick={() => { setShowSettingsSheet(false); setShowMuteSheet(true) }}
            />
          </GroupCard>

          <SectionLabel>隐私与数据</SectionLabel>
          <GroupCard>
            <SettingRow icon={<KeyIcon />} label="修改密码" chevron onClick={() => navigate('/settings/change-password')} />
            <Divider />
            <SettingRow icon={<LogoutIcon />} label="退出登录" onClick={() => { setShowSettingsSheet(false); setShowLogoutDialog(true) }} />
            <Divider />
            <SettingRow icon={<TrashIcon />} label="清除聊天缓存" onClick={() => { setShowSettingsSheet(false); setShowClearDialog(true) }} />
            <Divider />
            <SettingRow icon={<DownloadIcon />} label="导出我的数据" onClick={() => { setShowSettingsSheet(false); void handleExportData() }} />
            <Divider />
            <SettingRow
              icon={<WarningIcon />}
              label="注销账号"
              danger
              onClick={() => { setShowSettingsSheet(false); setDeleteStep(1); setDeleteConfirmText(''); setShowDeleteDialog(true) }}
            />
          </GroupCard>

          <SectionLabel>关于</SectionLabel>
          <GroupCard>
            <SettingRow icon={<InfoIcon />} label="版本" value={`v${__APP_VERSION__}`} />
            <Divider />
            <SettingRow icon={<DocIcon />} label="用户协议" chevron onClick={() => navigate('/legal/terms')} />
            <Divider />
            <SettingRow icon={<DocIcon />} label="隐私政策" chevron onClick={() => navigate('/legal/privacy')} />
            <Divider />
            <SettingRow icon={<MailIcon />} label="联系我们" chevron onClick={() => window.location.href = 'mailto:support@yuoyuo.app'} />
          </GroupCard>
        </div>
      </BottomSheet>

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
    </AppPageShell>
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
    <div className="mb-2 overflow-hidden rounded-[12px] border border-[var(--color-divider)] bg-[var(--color-page-surface)]">
      {children}
    </div>
  )
}

function WalletPanel({
  balance,
  onRecharge,
  onDetails,
}: {
  balance: number
  onRecharge: () => void
  onDetails: () => void
}) {
  return (
    <div className="relative h-full min-h-[148px] overflow-hidden rounded-[14px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4 shadow-[0_6px_22px_rgba(24,24,32,0.08)]">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-[30px] h-[30px] rounded-[11px] bg-[rgba(255,183,197,0.16)] flex items-center justify-center text-[var(--color-primary)]">
            <WalletIcon />
          </span>
          <ScaledText as="h2" className="text-[17px] font-semibold text-[var(--color-ink)]">
            我的钱包
          </ScaledText>
        </div>
        <button onClick={onDetails} className="text-[12px] text-[var(--color-text-secondary)] active:opacity-60 shrink-0">
          yuoyuo币明细
        </button>
      </div>

      <div className="mt-5 flex items-end justify-between gap-2.5">
        <WalletAmount value={balance} label="yuoyuo币余额" />
        <button
          onClick={onRecharge}
          className="h-[38px] shrink-0 rounded-full bg-[var(--color-primary-500)] px-4 text-[13px] font-semibold text-white shadow-[var(--shadow-btn)] transition-transform active:scale-[0.97]"
        >
          充值
        </button>
      </div>
    </div>
  )
}

function WalletAmount({ value, label }: { value: number; label: string }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2">
        <span className="w-[24px] h-[24px] rounded-full flex items-center justify-center text-[13px] font-bold shadow-[0_4px_10px_rgba(58,58,74,0.10)] bg-[linear-gradient(135deg,#FFE08A,#D89B31)] text-white">
          y
        </span>
        <ScaledText as="p" className="text-[24px] font-bold text-[var(--color-ink)] leading-none truncate">
          {value}
        </ScaledText>
      </div>
      <ScaledText as="p" className="text-[13px] text-[var(--color-text-secondary)] mt-3 truncate">
        {label}
      </ScaledText>
    </div>
  )
}

function InviteShowcase({
  code,
  invitedCount,
  totalReward,
  isDark,
  onInvite,
}: {
  code?: string
  invitedCount: number
  totalReward: number
  isDark: boolean
  onInvite: () => void
}) {
  return (
    <button
      onClick={onInvite}
      className={`relative mt-3 min-h-[154px] w-full overflow-hidden rounded-[16px] border p-5 text-left shadow-[0_8px_24px_rgba(73,48,62,0.11)] transition-opacity active:opacity-90 ${
        isDark
          ? 'border-white/10 bg-[linear-gradient(135deg,#2A232A_0%,#3A2933_58%,#5C3C49_100%)]'
          : 'border-white/75 bg-[linear-gradient(135deg,#FFF8F3_0%,#FFE7ED_58%,#F2D4E1_100%)]'
      }`}
    >
      <img
        src="/assets/settings/invite-mascot.webp"
        alt=""
        className="pointer-events-none absolute right-[-18px] top-[-44px] h-[230px] w-[168px] object-contain drop-shadow-[0_10px_18px_rgba(232,85,119,0.16)] min-[380px]:right-[-12px] min-[380px]:top-[-66px] min-[380px]:h-[280px] min-[380px]:w-[204px]"
      />
      <div className="relative flex min-h-[124px] flex-col justify-between pr-[104px] min-[380px]:pr-[145px]">
        <div>
          <ScaledText as="p" className={`text-[14px] font-semibold ${isDark ? 'text-white/82' : 'text-[#C94A6A]'}`}>
            邀请好友
          </ScaledText>
          <ScaledText as="h3" className={`mt-2 text-[20px] font-bold leading-[1.3] ${isDark ? 'text-white' : 'text-[var(--color-ink)]'}`}>
            邀请好友，一起得奖励
          </ScaledText>
          {code && (
            <div className="mt-3 flex items-center gap-3 text-[12px] text-[var(--color-text-muted)]">
              <span>已邀请 {invitedCount}</span>
              <span>累计 {totalReward} 币</span>
            </div>
          )}
        </div>
        <span className="flex h-[36px] min-w-[126px] self-start items-center justify-center rounded-full bg-[var(--color-primary-500)] px-4 text-[13px] font-semibold text-white shadow-[var(--shadow-btn)]">
          邀请好友
        </span>
      </div>
    </button>
  )
}

function InviteCodeCard({
  code,
  onCopy,
  onOpen,
}: {
  code: string
  onCopy: () => void
  onOpen: () => void
}) {
  return (
    <div className="mt-3 rounded-[12px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-5 py-4">
      <div className="flex items-center justify-between gap-3">
        <ScaledText as="p" className="text-[15px] font-semibold text-[var(--color-ink)]">
          我的邀请码
        </ScaledText>
        <button onClick={onOpen} className="text-[12px] text-[var(--color-text-secondary)] active:opacity-60">
          邀请明细
        </button>
      </div>
      <div className="flex items-center justify-between gap-4 mt-4">
        <ScaledText as="p" className="flex-1 text-center text-[26px] font-bold tracking-[0.14em] text-[var(--color-primary)] font-[var(--font-latin)]">
          {code}
        </ScaledText>
        <button
          onClick={onCopy}
          className="h-[44px] px-5 rounded-[14px] bg-[rgba(255,183,197,0.12)] border border-[rgba(255,183,197,0.28)] text-[var(--color-primary)] text-[14px] font-semibold active:scale-[0.97] transition-transform"
        >
          复制
        </button>
      </div>
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
      className="flex min-h-[56px] w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors active:bg-[rgba(255,183,197,0.10)] min-[390px]:px-5"
    >
      <div className="flex min-w-0 items-center gap-3">
        <span className={`shrink-0 ${danger ? 'text-[var(--color-danger)]' : 'text-[var(--color-primary)]'}`}>{icon}</span>
        <ScaledText as="span" className={`text-[15px] ${danger ? 'text-[var(--color-danger)]' : 'text-[var(--color-ink)]'}`}>
          {label}
        </ScaledText>
      </div>
      <div className="flex min-w-0 shrink items-center justify-end gap-2">
        {value && (
          <ScaledText as="span" className="truncate text-[13px] text-[var(--color-text-secondary)]">
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
function SettingsIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
}
function CloseIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
}
function ChevronIcon() {
  return <svg className="shrink-0" width="8" height="14" viewBox="0 0 8 14" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="1,1 7,7 1,13" /></svg>
}
function LogoutIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16,17 21,12 16,7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
}
function KeyIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="7.5" cy="15.5" r="4.5" /><path d="M10.5 12.5L21 2m-4 2 2 2m-5 1 2 2" /></svg>
}
function CrownIcon({ tone = 'brand' }: { tone?: 'brand' | 'light' }) {
  const stroke = tone === 'light' ? '#FFFFFF' : 'var(--color-primary)'
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M2 20h20L19 8l-5 5-2-7-2 7-5-5-3 12z" /></svg>
}
function WalletIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" /><path d="M16 12h2" /><path d="M3 8h14" /></svg>
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
