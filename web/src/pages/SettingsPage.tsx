import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { Avatar } from '../components/ui/Avatar'
import { Switch } from '../components/ui/Switch'
import { Slider } from '../components/ui/Slider'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { Dialog } from '../components/ui/Dialog'
import { Button } from '../components/ui/Button'
import { Toast } from '../components/ui/Toast'

export function SettingsPage() {
  const navigate = useNavigate()
  const { theme, setTheme, resolvedTheme } = useThemeStore()
  const { userAvatar, setAuthenticated } = useAppStore()
  const [fontSize, setFontSize] = useState(60)
  const [activeReminder, setActiveReminder] = useState(true)
  const [showLogoutDialog, setShowLogoutDialog] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })

  const themeLabel = theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '自动'

  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色背景图.png'
    : '/assets/backgrounds/亮色背景图.png'

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
        <span className="text-[18px] font-medium text-[var(--color-ink)]">设置</span>
        <div className="w-[44px]" />
      </nav>

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-10">
        {/* Profile Card */}
        <div className="bg-[var(--color-glass-card)] backdrop-blur-[20px] rounded-[24px] shadow-[var(--shadow-card)] p-5 flex items-center gap-4 mb-5 mt-4 border border-[var(--color-border-glass)]">
          <Avatar src={userAvatar} size={56} border />
          <div className="flex-1 min-w-0">
            <p className="text-[18px] font-semibold text-[var(--color-ink)]">晨曦</p>
            <span className="inline-block mt-1 text-[12px] font-medium text-[var(--color-primary)] bg-[rgba(255,183,197,0.20)] rounded-full px-3 py-[2px]">
              会员 · 至 2026-12-31
            </span>
          </div>
          <span className="text-[var(--color-chevron)]">{'>'}</span>
        </div>

        {/* 我的会员 */}
        <SectionLabel>我的会员</SectionLabel>
        <GroupCard>
          <SettingRow icon={<GiftIcon />} label="兑换会员" chevron />
          <SettingRow icon={<CrownIcon />} label="订阅状态" value="至 2026-12-31" />
        </GroupCard>

        {/* 外观 */}
        <SectionLabel>外观</SectionLabel>
        <GroupCard>
          <div className="flex items-center justify-between px-5 h-[56px]">
            <div className="flex items-center gap-3">
              <PaletteIcon />
              <span className="text-[15px] text-[var(--color-ink)]">主题</span>
            </div>
            <div className="w-[180px]">
              <SegmentedControl
                options={['浅色', '深色', '自动']}
                value={themeLabel}
                onChange={(v) => {
                  const map = { '浅色': 'light', '深色': 'dark', '自动': 'system' } as const
                  setTheme(map[v as keyof typeof map])
                }}
              />
            </div>
          </div>
          <Divider />
          <div className="px-5 py-4">
            <div className="flex items-center gap-3 mb-3">
              <TextAIcon />
              <span className="text-[15px] text-[var(--color-ink)]">字体大小</span>
            </div>
            <Slider value={fontSize} onChange={setFontSize} />
          </div>
        </GroupCard>

        {/* 通知 */}
        <SectionLabel>通知</SectionLabel>
        <GroupCard>
          <div className="flex items-center justify-between px-5 h-[56px]">
            <div className="flex items-center gap-3">
              <BellIcon />
              <span className="text-[15px] text-[var(--color-ink)]">推送提醒</span>
            </div>
            <Switch checked={activeReminder} onChange={setActiveReminder} />
          </div>
          <Divider />
          <SettingRow icon={<MoonIcon />} label="静音时段" value="22:00 – 8:00" />
        </GroupCard>

        {/* 隐私与数据 */}
        <SectionLabel>隐私与数据</SectionLabel>
        <GroupCard>
          <SettingRow icon={<TrashIcon />} label="清除聊天缓存" />
          <SettingRow icon={<DownloadIcon />} label="导出我的数据" />
          <SettingRow icon={<WarningIcon />} label="注销账号" danger onClick={() => setShowLogoutDialog(true)} />
        </GroupCard>

        {/* 关于 */}
        <SectionLabel>关于</SectionLabel>
        <GroupCard>
          <SettingRow icon={<InfoIcon />} label="版本" value="1.0.0" />
          <SettingRow icon={<DocIcon />} label="用户协议 / 隐私政策" chevron />
          <SettingRow icon={<HeadsetIcon />} label="联系我们" chevron />
        </GroupCard>
      </div>

      {/* Dialog */}
      <Dialog open={showLogoutDialog} onClose={() => setShowLogoutDialog(false)} title="确认退出登录？">
        <p>退出后需要重新通过邮箱链接登录。</p>
        <div className="flex gap-3 mt-4">
          <Button variant="ghost" size="sm" onClick={() => setShowLogoutDialog(false)} className="flex-1">
            取消
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => {
              setAuthenticated(false)
              setShowLogoutDialog(false)
              navigate('/login', { replace: true })
            }}
            className="flex-1"
          >
            确认退出
          </Button>
        </div>
      </Dialog>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[13px] text-[var(--color-text-muted)] px-1 mt-5 mb-2">
      {children}
    </div>
  )
}

function GroupCard({ children }: { children: React.ReactNode }) {
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
  icon: React.ReactNode
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
        <span className={`text-[15px] ${danger ? 'text-[var(--color-danger)]' : 'text-[var(--color-ink)]'}`}>{label}</span>
      </div>
      <div className="flex items-center gap-2">
        {value && <span className="text-[13px] text-[var(--color-text-secondary)]">{value}</span>}
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

/* ── Icons ─────────────────────────────────────────────────────── */
function GiftIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="9" width="20" height="13" rx="2" /><path d="M2 9h20v4H2V9Z" /><line x1="12" y1="9" x2="12" y2="22" /><path d="M12 9C12 9 9 7 9 5C9 3.3 10.3 2 12 2C13.7 2 15 3.3 15 5C15 7 12 9 12 9Z" /><path d="M12 9C12 9 15 7 15 5C15 3.3 13.7 2 12 2C10.3 2 9 3.3 9 5C9 7 12 9 12 9Z" /></svg>
}
function CrownIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M2 20h20L19 8l-5 5-2-7-2 7-5-5-3 12z" /></svg>
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
function HeadsetIcon() {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6" /><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" /></svg>
}
