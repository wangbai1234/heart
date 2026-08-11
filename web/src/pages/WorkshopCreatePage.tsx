import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'

/**
 * 角色创作页 - 批3占位
 *
 * 批6会实现完整的七步引导 + 高级HTML功能
 */
export function WorkshopCreatePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  return (
    <div
      className="relative w-full min-h-full flex flex-col"
      style={{ background: isDark ? 'var(--color-bg-page)' : 'linear-gradient(160deg, #FFF0F3 0%, #FFF8F3 40%, #F7F0FF 100%)' }}
    >
      <div style={{ height: 'env(safe-area-inset-top, 47px)' }} />

      <nav className="relative z-20 flex items-center px-5 h-[44px] shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="w-[28px] h-[28px] -ml-1 rounded-full flex items-center justify-center active:bg-[var(--color-glass-55)] transition-colors"
        >
          <svg width="10" height="16" viewBox="0 0 10 16" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="8,2 2,8 8,14" />
          </svg>
        </button>
        <span className="flex-1 text-center text-[17px] font-semibold text-[var(--color-ink)] -ml-[28px]">
          角色创作
        </span>
      </nav>

      <div className="relative z-10 flex-1 flex items-center justify-center px-5">
        <div className="text-center max-w-[280px]">
          <div className="w-[64px] h-[64px] mx-auto mb-4 rounded-full bg-gradient-to-br from-[#C8B6FF] to-[#9D7CFF] flex items-center justify-center">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 19l7-7 3 3-7 7-3-3z" />
              <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" />
              <path d="M2 2l7.586 7.586" />
              <circle cx="11" cy="11" r="2" />
            </svg>
          </div>
          <h2 className="text-[18px] font-semibold text-[var(--color-ink)] mb-2">批6即将推出</h2>
          <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.65]">
            七步引导、区块编辑器、高级 HTML、详情页一步步变精美
          </p>
          <button
            onClick={() => navigate(-1)}
            className="mt-6 h-[44px] px-6 rounded-full bg-gradient-to-r from-[#C8B6FF] to-[#9D7CFF] text-white text-[15px] font-semibold shadow-[0_6px_20px_rgba(157,124,255,0.30)] active:scale-[0.98] transition-transform"
          >
            返回
          </button>
        </div>
      </div>
    </div>
  )
}
