import type { ReactNode } from 'react'
import { useThemeStore } from '../../stores/themeStore'

/** serif 字体栈，与 bespoke 详情页一致（呼应 yuoyuo 品牌） */
export const SERIF = '"Songti SC","STSong",Georgia,serif'

/** 统一输入框样式 */
export const textInputCls =
  'w-full h-[50px] px-4 rounded-[14px] text-[15px] bg-[var(--color-glass-55)] ' +
  'border border-[var(--color-border-glass)] text-[var(--color-ink)] ' +
  'placeholder:text-[var(--color-text-muted)] focus:outline-none ' +
  'focus:border-[var(--color-primary)] focus:bg-[var(--color-glass-75)] transition-colors'

/** 页面外壳：环境光晕 + 渐变底 + 安全区 + sticky 顶栏 */
export function CreateShell({
  title,
  onBack,
  backLabel,
  headerExtra,
  children,
  footer,
}: {
  title: string
  onBack: () => void
  backLabel?: string
  headerExtra?: ReactNode
  children: ReactNode
  footer?: ReactNode
}) {
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  return (
    <div
      className="relative w-full min-h-full flex flex-col overflow-hidden"
      style={{
        background: isDark
          ? 'var(--color-bg-page)'
          : 'linear-gradient(165deg,#FFF0F3 0%,#FFF6F2 38%,#F6F0FF 100%)',
      }}
    >
      {/* 环境光晕：两团柔光营造氛围（模式4 渐变背景 + 模式17 留白） */}
      <div
        className={`absolute -top-[80px] left-1/2 -translate-x-1/2 w-[320px] h-[220px] rounded-full blur-[80px] pointer-events-none ${
          isDark ? 'bg-[rgba(200,182,255,0.10)]' : 'bg-[rgba(255,183,197,0.22)]'
        }`}
      />
      <div
        className={`absolute top-[180px] -right-[60px] w-[240px] h-[240px] rounded-full blur-[90px] pointer-events-none ${
          isDark ? 'bg-[rgba(255,143,171,0.06)]' : 'bg-[rgba(200,182,255,0.16)]'
        }`}
      />

      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      <nav className="relative z-20 flex items-center px-5 h-[48px] shrink-0">
        <button
          onClick={onBack}
          aria-label={backLabel ?? '返回'}
          className="w-[32px] h-[32px] -ml-1 rounded-full flex items-center justify-center active:bg-[var(--color-glass-55)] transition-colors"
        >
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="8,2 2,8 8,14" />
          </svg>
        </button>
        <span className="flex-1 text-center text-[17px] font-semibold text-[var(--color-ink)] -ml-[32px] pointer-events-none">
          {title}
        </span>
      </nav>

      {headerExtra}

      <div className="relative z-10 flex-1 overflow-y-auto px-5 pb-[130px] pt-3 scrollbar-hide">
        {children}
      </div>

      {footer}
    </div>
  )
}

/** 区块标题：serif 大字 + 灰色副标（模式5 字体配对 + 模式2 hero 感） */
export function SectionHeading({ index, title, hint }: { index?: string; title: string; hint?: string }) {
  return (
    <div className="mb-4">
      <div className="flex items-baseline gap-2.5">
        {index && (
          <span
            className="text-[15px] tracking-[0.08em] text-[var(--color-primary)] tabular-nums"
            style={{ fontFamily: SERIF }}
          >
            {index}
          </span>
        )}
        <h2 className="text-[22px] font-semibold text-[var(--color-ink)] leading-tight" style={{ fontFamily: SERIF }}>
          {title}
        </h2>
      </div>
      {hint && <p className="mt-1.5 text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">{hint}</p>}
    </div>
  )
}

/** 字段卡：玻璃卡片 + 呼吸 padding（模式11 毛玻璃 + 模式10 圆角层次） */
export function FieldCard({
  label,
  hint,
  required,
  children,
}: {
  label?: string
  hint?: string
  required?: boolean
  children: ReactNode
}) {
  return (
    <div className="mb-3 rounded-[16px] bg-[var(--color-glass-35)] border border-[var(--color-border-glass)] p-3.5 backdrop-blur-[8px]">
      {label && (
        <label className="flex items-center text-[14px] font-medium text-[var(--color-ink)] mb-2">
          {required && <span className="text-[var(--color-error)] mr-0.5">*</span>}
          {label}
          {hint && <span className="ml-1.5 text-[12px] font-normal text-[var(--color-text-muted)]">{hint}</span>}
        </label>
      )}
      {children}
    </div>
  )
}
