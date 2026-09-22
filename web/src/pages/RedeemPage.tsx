import { useState } from 'react'
import { useCreditsStore } from '../stores/creditsStore'
import { redeemCode } from '../services/api'
import { OTPInput } from '../components/ui/OTPInput'
import { Button } from '../components/ui/Button'
import { Toast } from '../components/ui/Toast'
import { NoticeDialog } from '../components/ui/NoticeDialog'
import { useSafeBack } from '../hooks/useSafeBack'

export function RedeemPage() {
  const goBack = useSafeBack('/wallet')
  const creditsStore = useCreditsStore()
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState({ visible: false, message: '' })
  const [showSuccess, setShowSuccess] = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  const isCodeComplete = code.replace(/[^a-zA-Z0-9]/g, '').length === 12

  const handleRedeem = async () => {
    if (!isCodeComplete) return
    setLoading(true)
    try {
      const res = await redeemCode(code.replace(/[^a-zA-Z0-9]/g, '').toUpperCase())
      creditsStore.setBalance(res.balance)
      setShowSuccess(true)
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || ''
      if (msg.includes('expired')) {
        setToast({ visible: true, message: '兑换码已过期，请检查或联系客服' })
      } else if (msg.includes('already') || msg.includes('used') || msg.includes('redeemed')) {
        setToast({ visible: true, message: '该兑换码已被使用' })
      } else {
        setToast({ visible: true, message: '兑换码无效，请检查后重试' })
      }
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
    <div className="app-atmosphere relative flex h-full w-full flex-col overflow-hidden">

      {/* Status bar */}
      <div style={{ height: 'var(--safe-top)' }} />

      {/* Navigation bar */}
      <nav className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center">
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
            src="/assets/backgrounds/兑换页礼品盒.webp"
            alt="礼品盒"
            className="w-[120px] h-[120px] object-contain mx-auto mb-4"
          />
          <h2 className="text-[22px] font-semibold text-[var(--color-ink)] mb-2 font-[var(--font-chinese)]">
            输入兑换码激活权益
          </h2>
          <p className="text-[14px] text-[var(--color-text-secondary)] leading-[1.6]">
            仅支持已经获得的 12 位兑换码，新兑换码发放入口目前已关闭。
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
          <span className="text-[15px] font-medium text-[var(--color-ink)]">兑换码说明</span>
          <svg
            width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round"
            className={`transition-transform duration-200 ${showHelp ? 'rotate-180' : ''}`}
          >
            <polyline points="4,6 8,10 12,6" />
          </svg>
        </button>

        {showHelp && (
          <div className="bg-[var(--color-glass-35)] backdrop-blur-[12px] rounded-[16px] p-4 mb-4 animate-[fade-in-up_220ms_var(--ease-standard)]">
            <p className="text-[14px] text-[var(--color-ink)] leading-[1.7]">
              兑换码只能使用一次。输入后会立即写入当前账号；如果你是历史会员，请使用原账号登录后再激活。
            </p>
          </div>
        )}

        {/* Footer */}
        <p className="text-center text-[12px] text-[var(--color-text-muted)] mt-2">
          兑换码一次性有效，激活后不可退还。
        </p>
      </div>

      {/* Success Dialog */}
      <NoticeDialog
        open={showSuccess}
        onClose={() => { setShowSuccess(false); goBack() }}
        title="激活成功"
        actionLabel="好的"
      >
        兑换成功
        <br />
        当前余额 {creditsStore.balance} yuoyuo币，尽情享受吧
      </NoticeDialog>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />
    </div>
  )
}
