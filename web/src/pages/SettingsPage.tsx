import { useTranslation } from 'react-i18next'
import { uiText } from '../i18n/text'
import { LanguagePreferences } from '../components/LanguagePreferences'
import { international } from '../i18n/text'
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
  useTranslation()
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
    if (international) return
    getInviteStatus().then(setInviteStatus).catch(() => {})
  }, [])

  const TIER_LABELS: Record<string, string> = { get free() { return uiText('ui503') }, get plus() { return uiText('ui504') }, get immersive() { return uiText('ui505') } }
  const PROFILE_TIER_LABELS: Record<string, string> = { get free() { return uiText('ui506') }, get plus() { return uiText('ui507') }, get immersive() { return uiText('ui508') } }
  const MEMBERSHIP_HINTS: Record<string, string> = {
    get free() { return uiText('ui509') },
    get plus() { return uiText('ui510') },
    get immersive() { return uiText('ui511') },
  }

  const themeLabel = theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '自动'

  const isDark = resolvedTheme === 'dark'
  const memberGemImage = '/assets/settings/member-crown.webp'

  const displayName = user?.display_name || user?.email?.split('@')[0] || uiText('ui515')

  const handleLogout = async () => {
    try { await apiLogout(refreshToken || undefined) } catch { /* ignore */ }
    clearSession()
    setShowLogoutDialog(false)
    navigate('/character', { replace: true })
  }

  const handleClearConversations = async () => {
    try {
      await clearConversations()
      setToast({ visible: true, get message() { return uiText('ui516') } })
    } catch {
      setToast({ visible: true, get message() { return uiText('ui517') } })
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
      setToast({ visible: true, get message() { return uiText('ui518') } })
    } catch {
      setToast({ visible: true, get message() { return uiText('ui519') } })
    }
  }

  const copyInviteCode = async () => {
    if (!inviteStatus?.invite_code) {
      navigate('/invite')
      return
    }
    try {
      await navigator.clipboard.writeText(inviteStatus.invite_code)
      setToast({ visible: true, get message() { return uiText('ui520') } })
    } catch {
      setToast({ visible: true, get message() { return uiText('ui521') } })
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
      navigate('/character', { replace: true })
    } catch {
      setToast({ visible: true, get message() { return uiText('ui522') } })
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
          {uiText('ui135')}</ScaledText>
        <button
          onClick={() => setShowSettingsSheet(true)}
          className="flex h-[40px] w-[40px] items-center justify-center rounded-[10px] bg-[var(--color-page-soft)] transition-colors active:opacity-75"
          aria-label={uiText('ui523')}
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
                {user?.email || uiText('ui524')}
              </ScaledText>
            </div>
            <ChevronIcon />
          </div>
        </button>

        <div className="grid grid-cols-1 gap-2.5 min-[520px]:grid-cols-2 sm:gap-3">
          <WalletPanel
            balance={balance}
            onWallet={() => navigate('/wallet')}
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
                  {uiText('ui525')}</ScaledText>
              </div>
              <span className={`shrink-0 rounded-full px-3 py-2 text-[13px] font-semibold shadow-[0_8px_20px_rgba(255,255,255,0.18)] min-[380px]:px-4 ${isDark ? 'bg-white text-[#8C7188]' : 'bg-[#FF9DB6] text-white'}`}>
                {uiText('ui526')}</span>
            </div>
            <div className="ml-[2px] mt-5 max-w-[72%] min-w-0">
              <ScaledText as="p" className={`inline-block rounded-full px-3 py-1 text-[12px] font-semibold ${isDark ? 'bg-white/12 text-white' : 'bg-[rgba(255,143,171,0.20)] text-[#E85577]'}`}>
                {TIER_LABELS[membershipTier] ?? uiText('ui503')}{uiText('ui527')}</ScaledText>
              <ScaledText as="p" className={`text-[14px] mt-3 leading-[1.55] ${isDark ? 'text-white/82' : 'text-[var(--color-text-secondary)]'}`}>
                {MEMBERSHIP_HINTS[membershipTier] ?? MEMBERSHIP_HINTS.free}
              </ScaledText>
            </div>
          </div>
          </button>
        </div>

        {!international && <InviteShowcase
          code={inviteStatus?.invite_code}
          invitedCount={inviteStatus?.invited_count ?? 0}
          totalReward={inviteStatus?.total_reward ?? 0}
          isDark={isDark}
          onInvite={() => navigate('/invite')}
        />}

        {inviteStatus?.invite_code && (
          <InviteCodeCard code={inviteStatus.invite_code} onCopy={copyInviteCode} onOpen={() => navigate('/invite')} />
        )}
      </div>

      <TabBar />

      <BottomSheet open={showSettingsSheet} onClose={() => setShowSettingsSheet(false)}>
        <div className="max-h-[78vh] overflow-y-auto pb-2">
          <div className="flex items-center justify-between mb-3">
            <ScaledText as="h2" className="text-[18px] font-semibold text-[var(--color-ink)]">
              {uiText('ui528')}</ScaledText>
            <button
              onClick={() => setShowSettingsSheet(false)}
              className="w-[36px] h-[36px] flex items-center justify-center rounded-full active:bg-[rgba(255,183,197,0.14)] transition-colors"
              aria-label={uiText('ui529')}
            >
              <CloseIcon />
            </button>
          </div>

          {international && <LanguagePreferences />}
          <SectionLabel>{uiText('ui530')}</SectionLabel>
          <GroupCard>
            <div className="flex min-h-[56px] flex-wrap items-center justify-between gap-3 px-4 py-3 min-[390px]:flex-nowrap min-[390px]:px-5">
              <div className="flex items-center gap-3">
                <PaletteIcon />
                <ScaledText as="span" className="text-[15px] text-[var(--color-ink)]">
                  {uiText('ui531')}</ScaledText>
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
                  {uiText('ui532')}</ScaledText>
              </div>
              <Slider value={fontScale} onChange={setFontScale} labelClassName="settings-scale-text" />
            </div>
          </GroupCard>

          <SectionLabel>{uiText('ui533')}</SectionLabel>
          <GroupCard>
            <div className="flex min-h-[56px] items-center justify-between gap-3 px-4 py-3 opacity-50 min-[390px]:px-5">
              <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                <BellIcon />
                <ScaledText as="span" className="text-[15px] text-[var(--color-ink)]">
                  {uiText('ui534')}</ScaledText>
                <ScaledText as="span" className="text-[11px] text-[var(--color-text-muted)]">
                  {uiText('ui535')}</ScaledText>
              </div>
              <Switch checked={pushEnabled} onChange={setPushEnabled} disabled />
            </div>
            <Divider />
            <SettingRow
              icon={<MoonIcon />}
              label={uiText('ui536')}
              value={isMuteNever ? uiText('ui537') : `${muteStart}:${muteStartMin} – ${muteEnd}:${muteEndMin}`}
              chevron
              onClick={() => { setShowSettingsSheet(false); setShowMuteSheet(true) }}
            />
          </GroupCard>

          <SectionLabel>{uiText('ui538')}</SectionLabel>
          <GroupCard>
            <SettingRow icon={<KeyIcon />} label={uiText('ui144')} chevron onClick={() => navigate('/settings/change-password')} />
            <Divider />
            <SettingRow icon={<LogoutIcon />} label={uiText('ui140')} onClick={() => { setShowSettingsSheet(false); setShowLogoutDialog(true) }} />
            <Divider />
            <SettingRow icon={<TrashIcon />} label={uiText('ui539')} onClick={() => { setShowSettingsSheet(false); setShowClearDialog(true) }} />
            <Divider />
            <SettingRow icon={<DownloadIcon />} label={uiText('ui540')} onClick={() => { setShowSettingsSheet(false); void handleExportData() }} />
            <Divider />
            <SettingRow
              icon={<WarningIcon />}
              label={uiText('ui541')}
              danger
              onClick={() => { setShowSettingsSheet(false); setDeleteStep(1); setDeleteConfirmText(''); setShowDeleteDialog(true) }}
            />
          </GroupCard>

          <SectionLabel>{uiText('ui542')}</SectionLabel>
          <GroupCard>
            <SettingRow icon={<InfoIcon />} label={uiText('ui543')} value={`v${__APP_VERSION__}`} />
            <Divider />
            <SettingRow icon={<DocIcon />} label={uiText('ui544')} chevron onClick={() => navigate('/legal/terms')} />
            <Divider />
            <SettingRow icon={<DocIcon />} label={uiText('ui545')} chevron onClick={() => navigate('/legal/privacy')} />
            <Divider />
            <SettingRow icon={<MailIcon />} label={uiText('ui546')} chevron onClick={() => window.location.href = 'mailto:support@yuoyuo.app'} />
          </GroupCard>
        </div>
      </BottomSheet>

      {/* Logout Dialog */}
      <Dialog open={showLogoutDialog} onClose={() => setShowLogoutDialog(false)} title={uiText('ui547')}>
        <ScaledText as="p" className="text-[15px] text-[var(--color-text-secondary)] leading-[1.6]">
          {uiText('ui548')}</ScaledText>
        <div className="flex gap-3 mt-4">
          <Button variant="ghost" size="sm" onClick={() => setShowLogoutDialog(false)} className="flex-1">
            {uiText('ui108')}</Button>
          <Button variant="danger" size="sm" onClick={handleLogout} className="flex-1">
            {uiText('ui549')}</Button>
        </div>
      </Dialog>

      {/* Clear Conversations Dialog */}
      <Dialog open={showClearDialog} onClose={() => setShowClearDialog(false)} title={uiText('ui539')}>
        <ScaledText as="p" className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
          {uiText('ui550')}</ScaledText>
        <div className="flex gap-3 mt-4">
          <Button variant="ghost" size="sm" onClick={() => setShowClearDialog(false)} className="flex-1">
            {uiText('ui108')}</Button>
          <Button variant="primary" size="sm" onClick={handleClearConversations} className="flex-1">
            {uiText('ui551')}</Button>
        </div>
      </Dialog>

      {/* Delete Account Dialog — 2-step */}
      <Dialog
        open={showDeleteDialog}
        onClose={() => { setShowDeleteDialog(false); setDeleteStep(1); setDeleteConfirmText('') }}
        title={deleteStep === 1 ? uiText('ui541') : uiText('ui552')}
      >
        {deleteStep === 1 ? (
          <>
            <ScaledText as="p" className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
              {uiText('ui553')}</ScaledText>
            <ScaledText as="p" className="text-[14px] text-[var(--color-danger)] leading-[1.7] mt-2">
              {uiText('ui554')}{balance} {uiText('ui555')}</ScaledText>
            <div className="flex gap-3 mt-4">
              <Button variant="ghost" size="sm" onClick={() => setShowDeleteDialog(false)} className="flex-1">
                {uiText('ui556')}</Button>
              <Button variant="danger" size="sm" onClick={handleDeleteAccount} className="flex-1" style={{ background: 'var(--color-danger)' }}>
                {uiText('ui557')}</Button>
            </div>
          </>
        ) : (
          <>
            <ScaledText as="p" className="text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              {uiText('ui558')}<strong className="text-[var(--color-ink)]">{user?.email}</strong> {uiText('ui559')}</ScaledText>
            <input
              type="email"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder={uiText('ui560')}
              className="w-full px-4 py-3 rounded-[12px] bg-[var(--color-glass-55)] border border-[var(--color-divider-inset)] text-[16px] text-[var(--color-ink)] outline-none mb-4"
            />
            <div className="flex gap-3">
              <Button variant="ghost" size="sm" onClick={() => setDeleteStep(1)} className="flex-1">
                {uiText('ui127')}</Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== user?.email}
                className="flex-1"
              >
                {uiText('ui561')}</Button>
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
            setToast({ visible: true, message: isMuteNever ? uiText('ui562') : uiText('dynamic35', { v0: muteStart, v1: muteStartMin, v2: muteEnd, v3: muteEndMin }) })
          }}
        />
      </BottomSheet>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </AppPageShell>
  )
}

function SectionLabel({ children }: { children: ReactNode }) {
  useTranslation()
  return (
    <div className="text-[13px] text-[var(--color-text-muted)] px-1 mt-5 mb-2">
      <ScaledText as="span" className="settings-scale-text">
        {children}
      </ScaledText>
    </div>
  )
}

function GroupCard({ children }: { children: ReactNode }) {
  useTranslation()
  return (
    <div className="mb-2 overflow-hidden rounded-[12px] border border-[var(--color-divider)] bg-[var(--color-page-surface)]">
      {children}
    </div>
  )
}

function WalletPanel({
  balance,
  onWallet,
  onDetails,
}: {
  balance: number
  onWallet: () => void
  onDetails: () => void
}) {
  useTranslation()
  return (
    <div className="relative h-full min-h-[148px] overflow-hidden rounded-[14px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4 shadow-[0_6px_22px_rgba(24,24,32,0.08)]">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-[30px] h-[30px] rounded-[11px] bg-[rgba(255,183,197,0.16)] flex items-center justify-center text-[var(--color-primary)]">
            <WalletIcon />
          </span>
          <ScaledText as="h2" className="text-[17px] font-semibold text-[var(--color-ink)]">
            {uiText('ui563')}</ScaledText>
        </div>
        <button onClick={onDetails} className="text-[12px] text-[var(--color-text-secondary)] active:opacity-60 shrink-0">
          {uiText('ui564')}</button>
      </div>

      <div className="mt-5 flex items-end justify-between gap-2.5">
        <WalletAmount value={balance} label={uiText('ui565')} />
        <button
          onClick={onWallet}
          className="h-[38px] shrink-0 rounded-full bg-[var(--color-primary-500)] px-4 text-[13px] font-semibold text-white shadow-[var(--shadow-btn)] transition-transform active:scale-[0.97]"
        >
          {uiText('ui566')}</button>
      </div>
    </div>
  )
}

function WalletAmount({ value, label }: { value: number; label: string }) {
  useTranslation()
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
  useTranslation()
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
            {uiText('ui567')}</ScaledText>
          <ScaledText as="h3" className={`mt-2 text-[20px] font-bold leading-[1.3] ${isDark ? 'text-white' : 'text-[var(--color-ink)]'}`}>
            {uiText('ui568')}</ScaledText>
          {code && (
            <div className="mt-3 flex items-center gap-3 text-[12px] text-[var(--color-text-muted)]">
              <span>{uiText('ui569')}{invitedCount}</span>
              <span>{uiText('ui570')}{totalReward} {uiText('ui571')}</span>
            </div>
          )}
        </div>
        <span className="flex h-[36px] min-w-[126px] self-start items-center justify-center rounded-full bg-[var(--color-primary-500)] px-4 text-[13px] font-semibold text-white shadow-[var(--shadow-btn)]">
          {uiText('ui567')}</span>
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
  useTranslation()
  return (
    <div className="mt-3 rounded-[12px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-5 py-4">
      <div className="flex items-center justify-between gap-3">
        <ScaledText as="p" className="text-[15px] font-semibold text-[var(--color-ink)]">
          {uiText('ui572')}</ScaledText>
        <button onClick={onOpen} className="text-[12px] text-[var(--color-text-secondary)] active:opacity-60">
          {uiText('ui573')}</button>
      </div>
      <div className="flex items-center justify-between gap-4 mt-4">
        <ScaledText as="p" className="flex-1 text-center text-[26px] font-bold tracking-[0.14em] text-[var(--color-primary)] font-[var(--font-latin)]">
          {code}
        </ScaledText>
        <button
          onClick={onCopy}
          className="h-[44px] px-5 rounded-[14px] bg-[rgba(255,183,197,0.12)] border border-[rgba(255,183,197,0.28)] text-[var(--color-primary)] text-[14px] font-semibold active:scale-[0.97] transition-transform"
        >
          {uiText('ui574')}</button>
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
  useTranslation()
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
  useTranslation()
  return <div className="h-px bg-[var(--color-divider-inset)] ml-[56px]" />
}

type ScaledTextProps = {
  as: ElementType
  children: ReactNode
  className?: string
  center?: boolean
}

function ScaledText({ as: Component, children, className = '' }: ScaledTextProps) {
  useTranslation()
  return (
    <Component className={className}>
      {children}
    </Component>
  )
}

/* ── Icons ─────────────────────────────────────────────────────── */
function SettingsIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
}
function CloseIcon() {
  useTranslation()
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
}
function ChevronIcon() {
  useTranslation()
  return <svg className="shrink-0" width="8" height="14" viewBox="0 0 8 14" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="1,1 7,7 1,13" /></svg>
}
function LogoutIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16,17 21,12 16,7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
}
function KeyIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="7.5" cy="15.5" r="4.5" /><path d="M10.5 12.5L21 2m-4 2 2 2m-5 1 2 2" /></svg>
}
function CrownIcon({ tone = 'brand' }: { tone?: 'brand' | 'light' }) {
  useTranslation()
  const stroke = tone === 'light' ? '#FFFFFF' : 'var(--color-primary)'
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M2 20h20L19 8l-5 5-2-7-2 7-5-5-3 12z" /></svg>
}
function WalletIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" /><path d="M16 12h2" /><path d="M3 8h14" /></svg>
}
function PaletteIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="8" r="1.5" fill="var(--color-primary)" /><circle cx="8" cy="12" r="1.5" fill="var(--color-primary)" /><circle cx="16" cy="12" r="1.5" fill="var(--color-primary)" /><circle cx="12" cy="16" r="1.5" fill="var(--color-primary)" /></svg>
}
function TextAIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M6 20L12 4l6 16" /><path d="M8 14h8" /></svg>
}
function BellIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
}
function MoonIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
}
function TrashIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><polyline points="3,6 5,6 21,6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
}
function DownloadIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7,10 12,15 17,10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
}
function WarningIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-danger)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
}
function InfoIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" /></svg>
}
function DocIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14,2 14,8 20,8" /></svg>
}
function MailIcon() {
  useTranslation()
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" /><polyline points="22,4 12,13 2,4" /></svg>
}
