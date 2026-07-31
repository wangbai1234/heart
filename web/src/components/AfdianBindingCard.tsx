import { useState } from 'react'
import { useToastStore } from '../stores/toastStore'

interface AfdianBindingCardProps {
  bindingCode: string
  /** 兜底：爱发电主页链接（未配置 checkoutUrl 时使用，需手填备注）。 */
  afdianUrl: string
  /** 选中挡位的 order/create 深链（后端 pricing 下发）；有则免备注即充即到。 */
  checkoutUrl?: string | null
  /** Optional SKU / plan name to remind the user which item to select on 爱发电. */
  skuHint?: string
}

/**
 * 拼出带 custom_order_id 的爱发电下单深链：绑定码同时写进 custom_order_id 和
 * remark 两个参数（webhook 优先读 custom_order_id，remark 作兜底），用户全程零输入。
 */
function buildCheckoutUrl(checkoutUrl: string, code: string): string {
  if (!code) return checkoutUrl
  const sep = checkoutUrl.includes('?') ? '&' : '?'
  const c = encodeURIComponent(code)
  return `${checkoutUrl}${sep}custom_order_id=${c}&remark=${c}`
}

export function AfdianBindingCard({
  bindingCode,
  afdianUrl,
  checkoutUrl,
  skuHint,
}: AfdianBindingCardProps) {
  const showToast = useToastStore((s) => s.show)
  const [copied, setCopied] = useState(false)

  // 有深链 → 免备注即充即到；否则回退主页 + 手填备注（旧流程）。
  const autoBind = Boolean(checkoutUrl)
  const href = autoBind
    ? buildCheckoutUrl(checkoutUrl as string, bindingCode)
    : afdianUrl || '#'

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
      {autoBind ? (
        <p className="text-[13px] text-[var(--color-text-secondary)] mb-3">
          点击下方按钮直接前往爱发电付款，系统已自动绑定此账号，
          <span className="text-[var(--color-ink)] font-medium">无需填写备注</span>
          ，付款后权益会自动到账。
        </p>
      ) : (
        <>
          <p className="text-[13px] text-[var(--color-text-secondary)] mb-2">
            在爱发电赞助时，请在
            <span className="text-[var(--color-ink)] font-medium">订单备注</span>
            里填写你的绑定码，系统将自动为此账号发放权益：
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
        </>
      )}

      {skuHint && (
        <p className="text-[12px] text-[var(--color-text-muted)] mb-3">
          对应挡位：<span className="text-[var(--color-text-secondary)]">{skuHint}</span>
        </p>
      )}

      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="block w-full text-center py-3 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-[var(--color-text-on-primary)] text-[15px] font-medium shadow-[var(--shadow-btn)] active:scale-[0.97] transition-transform"
      >
        去爱发电开通 →
      </a>
    </div>
  )
}
