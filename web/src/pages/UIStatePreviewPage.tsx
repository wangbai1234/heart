import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { Dialog } from '../components/ui/Dialog'
import { Toast } from '../components/ui/Toast'
import { BottomSheet } from '../components/ui/BottomSheet'
import { Loading } from '../components/ui/Loading'
import { Skeleton } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { OfflineState } from '../components/ui/OfflineState'
import { Button } from '../components/ui/Button'
import { BreathingDots } from '../components/ui/BreathingDots'

const sections = [
  'offline',
  'empty',
  'dialog',
  'toast',
  'bottomsheet',
  'loading',
  'skeleton',
  'breathing',
] as const

type Section = (typeof sections)[number]

export function UIStatePreviewPage() {
  const navigate = useNavigate()
  const { resolvedTheme, setTheme } = useThemeStore()
  const [activeSection, setActiveSection] = useState<Section>('offline')
  const [showDialog, setShowDialog] = useState(false)
  const [showToast, setShowToast] = useState(false)
  const [showSheet, setShowSheet] = useState(false)

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden bg-[var(--color-surface)]">
      {/* Status bar */}
      <div style={{ height: 'var(--safe-top)' }} />

      {/* Header */}
      <nav className="flex items-center justify-between px-5 h-[44px] shrink-0">
        <button onClick={() => navigate(-1)} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-medium text-[var(--color-ink)]">QA States</span>
        <button
          onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
          className="w-[44px] h-[44px] flex items-center justify-center"
        >
          <span className="text-[14px] text-[var(--color-primary)]">{resolvedTheme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>
      </nav>

      {/* Section tabs */}
      <div className="flex gap-2 px-4 py-2 overflow-x-auto shrink-0">
        {sections.map((s) => (
          <button
            key={s}
            onClick={() => setActiveSection(s)}
            className={`px-3 py-1.5 rounded-full text-[12px] whitespace-nowrap transition-colors ${
              activeSection === s
                ? 'bg-[var(--color-primary)] text-white'
                : 'bg-[var(--color-glass-55)] text-[var(--color-ink)]'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Preview area */}
      <div className="flex-1 overflow-y-auto">
        {activeSection === 'offline' && (
          <div className="py-8">
            <OfflineState />
          </div>
        )}

        {activeSection === 'empty' && (
          <div className="py-8">
            <EmptyState
              title="我们刚认识，先聊点什么吧？"
              description="选择一个话题开始对话"
              actionLabel="开始聊天"
              onAction={() => {}}
            />
          </div>
        )}

        {activeSection === 'dialog' && (
          <div className="flex flex-col items-center gap-4 py-8 px-4">
            <p className="text-[14px] text-[var(--color-text-secondary)] text-center">点击按钮预览 Dialog</p>
            <Button variant="primary" size="sm" onClick={() => setShowDialog(true)}>
              打开 Dialog
            </Button>
          </div>
        )}

        {activeSection === 'toast' && (
          <div className="flex flex-col items-center gap-4 py-8 px-4">
            <p className="text-[14px] text-[var(--color-text-secondary)] text-center">点击按钮预览 Toast (2.2s auto-dismiss)</p>
            <Button variant="primary" size="sm" onClick={() => setShowToast(true)}>
              显示 Toast
            </Button>
          </div>
        )}

        {activeSection === 'bottomsheet' && (
          <div className="flex flex-col items-center gap-4 py-8 px-4">
            <p className="text-[14px] text-[var(--color-text-secondary)] text-center">点击按钮预览 BottomSheet</p>
            <Button variant="primary" size="sm" onClick={() => setShowSheet(true)}>
              打开 BottomSheet
            </Button>
          </div>
        )}

        {activeSection === 'loading' && (
          <div className="flex flex-col items-center gap-6 py-8">
            <Loading size={32} />
            <Loading size={24} />
          </div>
        )}

        {activeSection === 'skeleton' && (
          <div className="flex flex-col gap-3 px-4 py-8">
            <Skeleton className="w-full h-[200px] rounded-[24px]" />
            <div className="flex gap-3">
              <Skeleton className="flex-1 h-[80px] rounded-[16px]" />
              <Skeleton className="flex-1 h-[80px] rounded-[16px]" />
            </div>
            <Skeleton className="w-full h-[60px] rounded-[16px]" />
            <Skeleton className="w-3/4 h-[20px] rounded-[8px]" />
            <Skeleton className="w-1/2 h-[20px] rounded-[8px]" />
          </div>
        )}

        {activeSection === 'breathing' && (
          <div className="flex flex-col items-center gap-6 py-8">
            <div className="bg-[var(--color-glass-75)] rounded-[20px] px-6 py-4">
              <BreathingDots />
            </div>
            <p className="text-[13px] text-[var(--color-text-muted)]">Typing indicator (600ms cycle)</p>
          </div>
        )}
      </div>

      {/* Dialog */}
      <Dialog open={showDialog} onClose={() => setShowDialog(false)} title="确认退出登录？">
        <p>退出后需要重新通过邮箱链接登录。</p>
        <div className="flex gap-3 mt-4">
          <Button variant="ghost" size="sm" onClick={() => setShowDialog(false)} className="flex-1">
            取消
          </Button>
          <Button variant="primary" size="sm" onClick={() => setShowDialog(false)} className="flex-1">
            确认退出
          </Button>
        </div>
      </Dialog>

      {/* Toast */}
      <Toast visible={showToast} message="兑换成功，会员已激活。" onDismiss={() => setShowToast(false)} />

      {/* BottomSheet */}
      <BottomSheet open={showSheet} onClose={() => setShowSheet(false)}>
        <h3 className="text-[18px] font-semibold text-[var(--color-ink)] mb-4">选择主题</h3>
        {['浅色', '深色', '跟随系统'].map((opt, i) => (
          <button
            key={opt}
            onClick={() => setShowSheet(false)}
            className="w-full flex items-center gap-3 py-3 px-2 active:bg-[rgba(255,183,197,0.10)] rounded-xl"
          >
            <div className={`w-5 h-5 rounded-full border-2 ${i === 0 ? 'border-[var(--color-primary)] bg-[var(--color-primary)]' : 'border-[var(--color-divider-inset)]'} flex items-center justify-center`}>
              {i === 0 && <div className="w-2 h-2 rounded-full bg-white" />}
            </div>
            <span className="text-[15px] text-[var(--color-ink)]">{opt}</span>
          </button>
        ))}
        <Button variant="primary" size="sm" onClick={() => setShowSheet(false)} className="mt-4 w-full">
          完成
        </Button>
      </BottomSheet>
    </div>
  )
}
