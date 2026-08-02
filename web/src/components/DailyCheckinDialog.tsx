import { useEffect } from 'react'
import { Dialog } from './ui/Dialog'

/**
 * 每日签到弹窗 — shown once per day right after login when the check-in grant
 * lands. The coins are already credited server-side before this renders; the
 * dialog is a notification, not a claim gate. Auto-dismisses after 3s, or the
 * user can tap 知道了 to close immediately.
 */
export function DailyCheckinDialog({
  open,
  coins,
  onClose,
}: {
  open: boolean
  coins: number
  onClose: () => void
}) {
  useEffect(() => {
    if (!open) return
    const t = setTimeout(onClose, 3000)
    return () => clearTimeout(t)
  }, [open, onClose])

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="签到成功"
      actions={
        <button
          onClick={onClose}
          className="flex-1 h-[44px] rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-text-on-primary)] text-[15px] font-medium active:opacity-80"
        >
          知道了
        </button>
      }
    >
      今日签到已到账，获得 {coins} yuoyuo币
    </Dialog>
  )
}
