import { useState } from 'react'
import { useToastStore } from '../stores/toastStore'

interface AfdianBindingCardProps {
  bindingCode: string
  afdianUrl: string
  /** Optional SKU / plan name to remind the user which item to select on 爱发电. */
  skuHint?: string
}

/**
 * Shared "去爱发电开通" block: shows the user's binding code (copyable), the
 * remark instruction, and an outbound link to 爱发电. Used by MembershipPage
 * and WalletPage — the webhook matches the binding code written in the order
 * remark back to this account.
 */
export function AfdianBindingCard({ bindingCode, afdianUrl, skuHint }: AfdianBindingCardProps) {
  const showToast = useToastStore((s) => s.show)
  const [copied, setCopied] = useState(false)

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(bindingCode)
      setCopied(true)
      showToast('绑定码已复制', 'success')
      setTimeout(() => setCopied(false), 1600)
    } catch {
      showToast('复制失败，请手动复制', 'error')
    }
  }

  return (
    <div className="bg-[var(--color-glass-55)] backdrop-blur-[12px] rounded-[16px] border border-[var(--color-border-glass)] p-4">
      <p className="text-[13px] text-[var(--color-text-secondary)] mb-2">
        在爱发电赞助时，请在<span className="text-[var(--color-ink)] font-medium">订单备注</span>里填写你的绑定码，系统将自动为此账号发放权益：
      </p>

      <button
        onClick={copyCode}
        className="w-full flex items-center justify-between px-4 py-3 rounded-[12px] bg-[var(--color-glass-90)] border border-[var(--color-border-glass)] active:scale-[0.98] transition-transform mb-3"
      >
        <span className="text-[20px] font-bold tracking-[0.18em] text-[var(--color-ink)] font-[var(--font-latin)]">
          {bindingCode || '— — — —'}
        </span>
        <span className="text-[13px] font-medium text-[var(--color-primary)]">
          {copied ? '已复制 ✓' : '复制'}
        </span>
      </button>

      {skuHint && (
        <p className="text-[12px] text-[var(--color-text-muted)] mb-3">
          对应挡位：<span className="text-[var(--color-text-secondary)]">{skuHint}</span>
        </p>
      )}

      <a
        href={afdianUrl || '#'}
        target="_blank"
        rel="noopener noreferrer"
        className="block w-full text-center py-3 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-[var(--color-text-on-primary)] text-[15px] font-medium shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform"
      >
        去爱发电开通 →
      </a>
    </div>
  )
}
