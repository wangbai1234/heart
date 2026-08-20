import { useEffect } from 'react'
import { NoticeDialog } from './ui/NoticeDialog'

/**
 * 每日签到弹窗 — shown once per day right after login when the check-in grant
 * lands. The coins are already credited server-side before this renders; the
 * dialog is a notification, not a claim gate. Auto-dismisses after 3.5s, or the
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
    const t = setTimeout(onClose, 3500)
    return () => clearTimeout(t)
  }, [open, onClose])

  return (
    <NoticeDialog open={open} onClose={onClose} title="签到成功">
      今日签到已到账
      <br />
      获得 {coins} yuoyuo币，永久有效
    </NoticeDialog>
  )
}
