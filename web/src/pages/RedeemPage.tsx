import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { OTPInput } from '../components/ui/OTPInput'
import { Button } from '../components/ui/Button'
import { Toast } from '../components/ui/Toast'
import { Dialog } from '../components/ui/Dialog'

export function RedeemPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })
  const [showSuccess, setShowSuccess] = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  const bgImage = resolvedTheme === 'dark'
    ? '/assets/backgrounds/暗色背景图.png'
    : '/assets/backgrounds/亮色背景图.png'

  const isCodeComplete = code.replace(/[^a-zA-Z0-9]/g, '').length === 12

  const handleRedeem = async () => {
    if (!isCodeComplete) return
    setLoading(true)
    try {
      await new Promise((r) => setTimeout(r, 1500))
      setShowSuccess(true)
    } catch {
      setToast({ visible: true, message: '激活失败，请重试' })
    } finally {
      setLoading(false)
    }
  }

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText()
      const cleaned = text.replace(/[^a-zA-Z0-9]/g, '').slice(0, 12).toUpperCase()
      if (cleaned.length > 0) {
        setCode(cleaned)
        setToast({ visible: true, message: '已粘贴' })
      }
    } catch {
      setToast({ visible: true, message: '无法读取剪贴板' })
    }
  }

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {/* Background */}
      <img src={bgImage} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />

      {/* Status bar */}
      <div style={{ height: 'var(--safe-top)' }} />

      {/* Navigation bar */}
      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button onClick={() => navigate(-1)} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-medium text-[var(--color-ink)]">兑换会员</span>
        <div className="w-[44px]" />
      </nav>

      {/* Scrollable content */}
      <div className="relative z-10 flex-1 overflow-y-auto px-4 pb-8">
        {/* Hero Card */}
        <div className="bg-[var(--color-glass-75)] backdrop-blur-[20px] rounded-[24px] border border-[var(--color-border-glass)] shadow-[var(--shadow-hero)] p-6 mt-4 mb-5 text-center">
          <img
            src="/assets/backgrounds/兑换页礼品盒.png"
            alt="礼品盒"
            className="w-[120px] h-[120px] object-contain mx-auto mb-4"
          />
          <h2 className="text-[22px] font-semibold text-[var(--color-ink)] mb-2 font-[var(--font-chinese)]">
            输入兑换码激活会员
          </h2>
          <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.6]">
            在「爱发电」赞助后，你会收到一串 12 位的兑换码。
          </p>
        </div>

        {/* Code Input */}
        <div className="mb-4">
          <OTPInput length={12} groupSize={4} onComplete={(c) => setCode(c)} onChange={(c) => setCode(c)} />
        </div>

        {/* Paste button */}
        <div className="flex justify-center mb-5">
          <button
            onClick={handlePaste}
            className="px-4 py-2 rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] text-[13px] text-[var(--color-ink)] active:scale-[0.97] transition-transform"
          >
            粘贴
          </button>
        </div>

        {/* Activate button */}
        <Button
          variant="primary"
          size="lg"
          loading={loading}
          disabled={!isCodeComplete}
          onClick={handleRedeem}
          className="mb-5"
        >
          立即激活
        </Button>

        {/* Help section */}
        <button
          onClick={() => setShowHelp(!showHelp)}
          className="w-full flex items-center justify-between px-4 py-3 bg-[var(--color-glass-35)] backdrop-blur-[12px] rounded-[16px] mb-3"
        >
          <span className="text-[15px] font-medium text-[var(--color-ink)]">如何获取兑换码</span>
          <svg
            width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round"
            className={`transition-transform duration-200 ${showHelp ? 'rotate-180' : ''}`}
          >
            <polyline points="4,6 8,10 12,6" />
          </svg>
        </button>

        {showHelp && (
          <div className="bg-[var(--color-glass-35)] backdrop-blur-[12px] rounded-[16px] p-4 mb-4 animate-[fade-in-up_220ms_var(--ease-standard)]">
            <div className="flex gap-3 mb-3">
              <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-[12px] font-bold flex items-center justify-center shrink-0">1</span>
              <p className="text-[14px] text-[var(--color-ink)] leading-[1.6]">前往「爱发电」赞助页面</p>
            </div>
            <div className="flex gap-3 mb-3">
              <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-[12px] font-bold flex items-center justify-center shrink-0">2</span>
              <p className="text-[14px] text-[var(--color-ink)] leading-[1.6]">选择心仪的赞助挡位</p>
            </div>
            <div className="flex gap-3 mb-3">
              <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-[12px] font-bold flex items-center justify-center shrink-0">3</span>
              <p className="text-[14px] text-[var(--color-ink)] leading-[1.6]">完成支付后查收兑换码邮件</p>
            </div>
            <div className="flex gap-3 mb-4">
              <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-[12px] font-bold flex items-center justify-center shrink-0">4</span>
              <p className="text-[14px] text-[var(--color-ink)] leading-[1.6]">回到 yuoyuo 输入兑换码</p>
            </div>
            <button className="w-full py-3 rounded-full border border-[var(--color-primary)] text-[var(--color-primary)] text-[15px] font-medium active:scale-[0.97] transition-transform">
              去爱发电 →
            </button>
          </div>
        )}

        {/* Footer */}
        <p className="text-center text-[12px] text-[var(--color-text-muted)] mt-2">
          兑换码一次性有效，激活后不可退还。
        </p>
      </div>

      {/* Success Dialog */}
      <Dialog open={showSuccess} onClose={() => { setShowSuccess(false); navigate('/login', { replace: true }) }} title="激活成功">
        <p>你的会员已成功激活，尽情享受吧！</p>
        <Button
          variant="primary"
          size="sm"
          onClick={() => { setShowSuccess(false); navigate('/login', { replace: true }) }}
          className="mt-4 w-full"
        >
          好的
        </Button>
      </Dialog>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </div>
  )
}
